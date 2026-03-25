"""
ite_intelligence_enricher.py — Enrich extraction JSONs with ITE exam intelligence
==================================================================================
Phase 2 | ITE Intelligence Pipeline  —  v4 (post-codon migration)

For each extraction JSON:
  1. Looks up the article in ite_intelligence.db (2-strategy lookup)
  2. Retrieves all linked questions with stems, keywords, exam years
  3. Calls Claude API once to generate ite_intelligence{} block
  4. Writes the block back into the JSON

DB Lookup strategies (v4 — codon-first):
  0. Codon filename — parse ART-ID directly from filename (#@#ART-XXXX@#@)
  1. source.clean_ref — exact match on clean_ref field (v1.1+ JSONs)

  All other strategies (author_year, title_year, org_year, vector_similarity)
  removed in v4. If neither strategy matches, the file is logged as no_match
  for manual review.

Run:
  python scripts/ite_intelligence_enricher.py --dir outputs/afp_peds_uspstf_batch
  python scripts/ite_intelligence_enricher.py --file outputs/batch/001_file.json
  python scripts/ite_intelligence_enricher.py --dir outputs/afp_peds_uspstf_batch --dry-run

Requires: ANTHROPIC_API_KEY env var (or .env file in project root)
"""

import sqlite3, json, re, os, argparse, time
from pathlib import Path
from datetime import datetime, timezone

try:
    import anthropic
except ImportError:
    raise ImportError("Run: pip install anthropic")

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR  = Path(__file__).resolve().parent.parent
DB_PATH   = BASE_DIR / "00_database" / "db" / "ite_intelligence.db"
LOG_DIR   = BASE_DIR / "logs"
MODEL     = "claude-sonnet-4-20250514"


# ── Helpers ────────────────────────────────────────────────────────────────
def _compute_concept_tfidf(conn, clean_ref, questions):
    """
    Compute TF-IDF scores for each diagnosis concept across all questions for this article.
    TF  = fraction of this article's questions that mention the concept
    IDF = log(total_articles / articles_whose_questions_contain_this_concept)
    Returns dict: {concept_str: "green"|"yellow"|"red"}
    """
    import math
    cur = conn.cursor()

    # Collect all diagnosis concepts from this article's questions
    all_concepts = []
    per_q_concepts = []
    for q in questions:
        tags = q.get("concept_tags", "")
        diagnoses = []
        try:
            obj = json.loads(tags) if tags else {}
            diagnoses = [d.lower().strip() for d in obj.get("diagnoses", [])]
        except (json.JSONDecodeError, TypeError):
            pass
        per_q_concepts.append(diagnoses)
        all_concepts.extend(diagnoses)

    if not all_concepts:
        return {}

    unique_concepts = list(set(all_concepts))
    n_questions = len(questions)

    # TF: fraction of this article's questions containing each concept
    tf = {}
    for concept in unique_concepts:
        count = sum(1 for q_concepts in per_q_concepts if concept in q_concepts)
        tf[concept] = count / n_questions

    # IDF: log(total_articles / articles whose linked questions contain this concept)
    cur.execute("SELECT COUNT(DISTINCT clean_ref) FROM articles")
    total_articles = cur.fetchone()[0] or 1

    idf = {}
    for concept in unique_concepts:
        cur.execute("""
            SELECT COUNT(DISTINCT p.clean_ref)
            FROM question_ref_pairs p
            JOIN questions q ON p.qid = q.qid
            WHERE LOWER(q.concept_tags) LIKE ?
        """, (f"%{concept}%",))
        doc_freq = cur.fetchone()[0] or 1
        idf[concept] = math.log(total_articles / doc_freq)

    # TF-IDF score
    scores = {c: tf[c] * idf[c] for c in unique_concepts}

    # Bucket into green/yellow/red by tertile
    if len(scores) < 2:
        return {c: "green" for c in scores}
    sorted_scores = sorted(scores.values())
    low_cut  = sorted_scores[len(sorted_scores) // 3]
    high_cut = sorted_scores[(2 * len(sorted_scores)) // 3]
    result = {}
    for concept, score in scores.items():
        if score >= high_cut:
            result[concept] = "green"
        elif score >= low_cut:
            result[concept] = "yellow"
        else:
            result[concept] = "red"
    return result

def _parse_concept_tags(raw):
    """Convert concept_tags JSON string to readable display text."""
    if not raw:
        return ""
    try:
        obj = json.loads(raw)
        parts = []
        diagnoses = obj.get("diagnoses", [])
        if diagnoses:
            parts.append(", ".join(diagnoses))
        summary = obj.get("concept_summary", "")
        if summary:
            parts.append(summary)
        return " | ".join(parts) if parts else raw
    except (json.JSONDecodeError, TypeError):
        return str(raw)[:200]

def _build_concept_colors(raw, concept_colors):
    """
    Build list of {text, color} segments for the Concept Tested cell.
    Diagnosis tags sorted green -> yellow -> red by TF-IDF rank.
    Summary text appended in white after a pipe separator.
    """
    if not raw:
        return []
    try:
        obj = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return [{"text": str(raw)[:200], "color": "white"}]

    diagnoses = obj.get("diagnoses", [])
    summary   = obj.get("concept_summary", "")

    # Sort diagnoses by color rank: green first, then yellow, then red
    rank = {"green": 0, "yellow": 1, "red": 2}
    sorted_dx = sorted(
        diagnoses,
        key=lambda d: rank.get(concept_colors.get(d.lower().strip(), "yellow"), 1)
    )

    segments = []
    for i, d in enumerate(sorted_dx):
        color = concept_colors.get(d.lower().strip(), "yellow")
        segments.append({"text": d, "color": color})
        if i < len(sorted_dx) - 1:
            segments.append({"text": " | ", "color": "white"})
    if summary:
        if segments:
            segments.append({"text": " | ", "color": "white"})
        segments.append({"text": summary, "color": "white"})
    return segments


# ── DB Lookup (v4: codon + clean_ref only) ─────────────────────────────────
def lookup_article(conn, json_path, source_block):
    cur = conn.cursor()

    # Strategy 0: Codon filename — parse ART-ID from filename
    # Codon format: Author_Year#@#ART-XXXX@#@.pdf
    file_name = source_block.get("file_name", "") or json_path.stem
    codon_match = re.search(r'#@#(ART-\d+)@#@', file_name)
    if codon_match:
        art_id = codon_match.group(1)
        cur.execute("SELECT clean_ref, tier FROM articles WHERE article_id=?", (art_id,))
        row = cur.fetchone()
        if row:
            return _build_payload(conn, row[0], row[1], "codon_filename")

    # Strategy 1: clean_ref field (v1.1+ schema)
    clean_ref = source_block.get("clean_ref", "").strip()
    if clean_ref:
        cur.execute("SELECT clean_ref, tier FROM articles WHERE clean_ref=?", (clean_ref,))
        row = cur.fetchone()
        if row:
            return _build_payload(conn, row[0], row[1], "clean_ref")

    # No match — log for manual review
    return None


def _build_payload(conn, clean_ref, tier, match_method):
    cur = conn.cursor()
    cur.execute("""
        SELECT p.qid, q.exam_year, q.question_text, q.all_keywords, q.explanation, q.concept_tags
        FROM question_ref_pairs p
        JOIN questions q ON p.qid = q.qid
        WHERE p.clean_ref = ?
        ORDER BY q.exam_year, p.qid
    """, (clean_ref,))
    questions = cur.fetchall()
    if not questions:
        return None
    # Pull citation_display from articles table for page-1 citation rendering
    cur.execute("SELECT citation_display FROM articles WHERE clean_ref=?", (clean_ref,))
    cit_row = cur.fetchone()
    citation_display = (cit_row[0] or "").strip() if cit_row else ""
    return {
        "clean_ref": clean_ref, "tier": tier, "match_method": match_method,
        "citation_display": citation_display,
        "questions": [
            {"qid": q[0], "exam_year": q[1], "stem": (q[2] or ""),
             "keywords": q[3] or "", "explanation": (q[4] or ""),
             "concept_tags": q[5] or ""}
            for q in questions
        ]
    }


# ── Claude API Call ────────────────────────────────────────────────────────
def build_ite_intelligence(client, payload, article_title):
    # Pre-compute data facts Claude must reference in tier_rationale
    citation_count = len(payload["questions"])
    exam_years     = sorted(set(q["exam_year"] for q in payload["questions"]))
    years_span     = f"{exam_years[0]}–{exam_years[-1]}" if len(exam_years) > 1 else str(exam_years[0])
    n_years        = len(exam_years)
    tier           = payload["tier"]

    # Pull one concrete concept from the first question's concept_tags for grounding
    first_concept = ""
    try:
        tags_raw = payload["questions"][0].get("concept_tags", "")
        tags_obj = json.loads(tags_raw) if tags_raw else {}
        diagnoses = tags_obj.get("diagnoses", [])
        first_concept = diagnoses[0] if diagnoses else tags_obj.get("concept_summary", "")[:60]
    except (json.JSONDecodeError, TypeError, IndexError):
        pass

    questions_text = "\n".join([
        f"  [{q['exam_year']}] {q['qid']}\n"
        f"    Stem: {q['stem'][:800]}\n"
        f"    Keywords: {q['keywords'][:150]}\n"
        f"    Explanation: {q['explanation'][:1000]}"
        for q in payload["questions"]
    ])

    prompt = f"""You are analyzing how a clinical article has been tested on the ABFM In-Training Examination (ITE).

ARTICLE: {article_title}
DB REF:  {payload['clean_ref']}
TIER:    {tier}
LINKED EXAM QUESTIONS ({citation_count} total across {n_years} exam year(s): {years_span}):

{questions_text}

Generate a JSON object with EXACTLY these fields:
{{
  "exam_years_cited": [list of unique exam years as integers, sorted],
  "question_ids": [list of all QID strings],
  "citation_count": {citation_count},
  "high_yield_concepts": [4-8 specific clinical concepts actually tested],
  "concept_summary": "2-3 sentence summary of WHAT the ABFM has actually tested from this article — be specific about clinical decisions, thresholds, or drug choices that were tested",
  "tier_rationale": "One sentence that MUST include ALL of these data points: (1) the exact citation count {citation_count}, (2) the exam year span {years_span}, (3) the tier designation '{tier}', and (4) at least one specific clinical concept from the questions (e.g. '{first_concept}'). Do NOT use generic language like 'various topics' or 'multiple concepts'. Name the actual clinical content. Example: 'Cited {citation_count} time(s) across {years_span} ITE exams at {tier} tier; questions focused on [specific diagnosis/treatment/threshold from the stems].'"
}}

Return ONLY valid JSON. No markdown fences. No explanation text."""

    message = client.messages.create(
        model=MODEL, max_tokens=800,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = re.sub(r'^```json\s*', '', message.content[0].text.strip())
    raw = re.sub(r'\s*```$', '', raw)
    result = json.loads(raw)
    for f in ["exam_years_cited","question_ids","citation_count",
              "high_yield_concepts","concept_summary","tier_rationale"]:
        if f not in result:
            result[f] = None
    return result


# ── Confidence Computation (FLAG 6 fix — v4) ──────────────────────────────
def compute_enrichment_confidence(match_method, citation_count):
    """
    Programmatic confidence — never delegated to Claude.
    v4 logic (post-codon migration):
      codon_filename  → always "high" (ART-ID parsed directly from filename)
      clean_ref       → always "high" (exact DB primary key match)
      anything else   → "low" (should not occur in v4, logged for review)
    """
    if match_method == "codon_filename":
        return "high"
    if match_method == "clean_ref":
        return "high"
    return "low"


# ── Process One File ───────────────────────────────────────────────────────
def process_file(client, conn, json_path, dry_run):
    try:
        with open(json_path, encoding="utf-8") as f:
            doc = json.load(f)
    except Exception as e:
        return {"file": json_path.name, "status": "error", "reason": f"JSON load: {e}"}

    if doc.get("ite_intelligence") and doc["ite_intelligence"].get("citation_count"):
        return {"file": json_path.name, "status": "skipped", "reason": "already enriched"}

    source  = doc.get("source", {})
    title   = source.get("title", json_path.stem)
    payload = lookup_article(conn, json_path, source)

    if not payload:
        return {"file": json_path.name, "status": "no_match",
                "reason": "not found in DB or no linked questions"}

    if dry_run:
        return {"file": json_path.name, "status": "dry_run_match",
                "clean_ref": payload["clean_ref"][:80],
                "match_method": payload["match_method"], "tier": payload["tier"],
                "question_count": len(payload["questions"]),
                "exam_years": sorted(set(q["exam_year"] for q in payload["questions"]))}

    try:
        confidence = compute_enrichment_confidence(
            payload["match_method"], len(payload["questions"])
        )
        ite_block = build_ite_intelligence(client, payload, title)
        ite_block["enrichment_confidence"] = confidence
        ite_block["_match_method"] = payload["match_method"]
        ite_block["_enriched_at"]  = datetime.now(timezone.utc).isoformat()
        # Compute TF-IDF scores for concept color-coding
        concept_colors = _compute_concept_tfidf(conn, payload["clean_ref"], payload["questions"])
        # Add structured linked_qids for DOCX table rendering
        ite_block["linked_qids"] = [
            {
                "qid":           q["qid"],
                "exam_year":     q["exam_year"],
                "question_stem": q["stem"][:200] if q.get("stem") else "",
                "concept_tested": _parse_concept_tags(q.get("concept_tags", "")),
                "concept_colors": _build_concept_colors(q.get("concept_tags", ""), concept_colors)
            }
            for q in payload["questions"]
        ]
        ite_block["exam_years"] = sorted(set(q["exam_year"] for q in payload["questions"]))
    except Exception as e:
        return {"file": json_path.name, "status": "api_error", "reason": str(e)}

    doc["ite_intelligence"] = ite_block
    # Write citation_display into source block for page-1 rendering in DOCX
    if payload.get("citation_display"):
        doc.setdefault("source", {})["citation_display"] = payload["citation_display"]
    if "metadata" in doc:
        doc["metadata"]["schema_version"] = "unified_v1.1"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)

    return {"file": json_path.name, "status": "enriched",
            "clean_ref": payload["clean_ref"][:80],
            "match_method": payload["match_method"],
            "question_count": len(payload["questions"]),
            "high_yield": ite_block.get("high_yield_concepts", [])[:3]}


# ── Main ───────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Enrich extraction JSONs with ITE intelligence")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dir",  type=str, help="Directory of extraction JSONs")
    group.add_argument("--file", type=str, help="Single extraction JSON")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--delay", type=float, default=0.5)
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key and not args.dry_run:
        print("ANTHROPIC_API_KEY not set. Run: set ANTHROPIC_API_KEY=sk-ant-..."); return
    if not DB_PATH.exists():
        print(f"DB not found: {DB_PATH}"); return

    files = [Path(args.file)] if args.file else sorted(Path(args.dir).glob("*_extracted.json"))
    if not files:
        print("No *_extracted.json files found"); return

    print("=" * 60)
    print(f"ITE Intelligence Enricher  v4 (codon-first)")
    print(f"  Files: {len(files)}  |  Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    if not args.dry_run:
        print(f"  Model: {MODEL}  |  Delay: {args.delay}s")
    print(f"  Strategies: codon_filename → clean_ref → no_match")
    print("=" * 60)

    client = anthropic.Anthropic(api_key=api_key) if not args.dry_run else None
    conn   = sqlite3.connect(DB_PATH)

    results = []
    enriched = no_match = skipped = errors = 0
    method_counts = {}

    for i, fpath in enumerate(files, 1):
        result = process_file(client, conn, fpath, args.dry_run)
        results.append(result)
        status = result["status"]
        method = result.get("match_method", "")
        if method:
            method_counts[method] = method_counts.get(method, 0) + 1

        if status in ("enriched", "dry_run_match"):
            enriched += 1
            icon = "[OK]" if status == "enriched" else "[DRY]"
            print(f"  [{i:3}/{len(files)}] {icon} {fpath.name[:52]}")
            print(f"           -> {result.get('question_count',0)} Qs | "
                  f"{result.get('exam_years',[])} | {method}")
            hy = result.get("high_yield", [])
            if hy:
                print(f"             concepts: {hy}")
            if not args.dry_run:
                time.sleep(args.delay)
        elif status == "no_match":
            no_match += 1
        elif status == "skipped":
            skipped += 1
        else:
            errors += 1
            print(f"  [{i:3}/{len(files)}] ERR {fpath.name[:45]} — {result.get('reason','')}")

    conn.close()
    print(f"\n{'-'*60}")
    if args.dry_run:
        print(f"DRY RUN COMPLETE")
        print(f"  Would enrich: {enriched}/{len(files)}")
        print(f"  No DB match:  {no_match}")
        print(f"  Match methods: {method_counts}")
    else:
        print(f"ENRICHMENT COMPLETE")
        print(f"  Enriched: {enriched}  No match: {no_match}  "
              f"Skipped: {skipped}  Errors: {errors}")
        print(f"  Methods: {method_counts}")

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    tag = "dryrun" if args.dry_run else "live"
    log_file = LOG_DIR / f"enricher_{tag}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(log_file, "w") as f:
        json.dump({"run_at": datetime.now().isoformat(), "dry_run": args.dry_run,
                   "target": str(args.dir or args.file), "total": len(files),
                   "enriched": enriched, "no_match": no_match, "skipped": skipped,
                   "errors": errors, "method_counts": method_counts,
                   "results": results}, f, indent=2)
    print(f"  Log: {log_file}")


if __name__ == "__main__":
    main()
