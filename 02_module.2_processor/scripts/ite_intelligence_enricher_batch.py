"""
ite_intelligence_enricher_batch.py — Batch API enricher for ITE intelligence blocks
=====================================================================================
v4 (post-codon migration) — matches ite_intelligence_enricher.py v4

Use this for large runs (35+ files). 50% cheaper than sequential API calls.

THREE-PHASE WORKFLOW:
  Phase 1 — Submit:
    python scripts/ite_intelligence_enricher_batch.py --submit --dir "PATH_TO_JSON_DIR"
    Runs DB lookup for all JSONs, bundles matched files into one Batch API call,
    saves batch_id + per-file metadata to a state file, prints batch_id.

  Phase 2 — Poll (run anytime after submit):
    python scripts/ite_intelligence_enricher_batch.py --poll
    Checks batch status. Prints processing_status + request counts.

  Phase 3 — Write (run after batch ends):
    python scripts/ite_intelligence_enricher_batch.py --write
    Pulls all results, writes ite_intelligence blocks back into JSONs,
    logs summary (enriched / no_match / skipped / errors).

OPTIONS:
  --dir PATH       Directory of *_extracted.json files
  --file PATH      Single JSON file (submit only)
  --state PATH     State file path (default: auto-named in logs/)
  --force          Re-enrich files that already have ite_intelligence block
  --dry-run        Submit phase: show what would be submitted, don't call API

DB Lookup strategies (v4 — codon-first):
  0. Codon filename — parse ART-ID directly from filename (#@#ART-XXXX@#@)
  1. source.clean_ref — exact match on clean_ref field

Requires: ANTHROPIC_API_KEY env var
"""

import sqlite3, json, re, os, sys, argparse, time
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

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")


# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR  = Path(__file__).resolve().parent.parent
DB_PATH   = BASE_DIR / "00_database" / "db" / "ite_intelligence.db"
LOG_DIR   = BASE_DIR / "logs"
# Default JSON dir — relative to project root, no hardcoded Windows paths
JSON_DIR  = BASE_DIR.parent.parent / "clinical_guidelines" / "03_enriched_JSON"
MODEL     = "claude-sonnet-4-20250514"


# ── Shared helpers ─────────────────────────────────────────────────────────
def _parse_concept_tags(raw):
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
    if not raw:
        return []
    try:
        obj = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return [{"text": str(raw)[:200], "color": "white"}]
    diagnoses = obj.get("diagnoses", [])
    summary   = obj.get("concept_summary", "")
    rank = {"green": 0, "yellow": 1, "red": 2}
    sorted_dx = sorted(diagnoses,
        key=lambda d: rank.get(concept_colors.get(d.lower().strip(), "yellow"), 1))
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


# ── Confidence Computation (v4 — FLAG 6 fix) ──────────────────────────────
def compute_enrichment_confidence(match_method, citation_count):
    """
    Programmatic confidence — never delegated to Claude.
    v4 logic (post-codon migration):
      codon_filename  → always "high"
      clean_ref       → always "high"
      anything else   → "low" (should not occur in v4)
    """
    if match_method == "codon_filename":
        return "high"
    if match_method == "clean_ref":
        return "high"
    return "low"


# ── DB Lookup (v4: codon + clean_ref only) ─────────────────────────────────
def lookup_article(conn, json_path, source_block):
    cur = conn.cursor()

    # Strategy 0: Codon filename — parse ART-ID from filename
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


# ── Prompt builder (v4 — upgraded tier_rationale, FLAG 5 fix) ─────────────
def build_prompt(payload, article_title):
    citation_count = len(payload["questions"])
    exam_years     = sorted(set(q["exam_year"] for q in payload["questions"]))
    years_span     = f"{exam_years[0]}–{exam_years[-1]}" if len(exam_years) > 1 else str(exam_years[0])
    n_years        = len(exam_years)
    tier           = payload["tier"]
    first_concept  = ""
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

    return f"""You are analyzing how a clinical article has been tested on the ABFM In-Training Examination (ITE).

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


# ── TF-IDF concept coloring ───────────────────────────────────────────────
def _compute_concept_tfidf(conn, clean_ref, questions):
    import math
    cur = conn.cursor()
    all_concepts, per_q_concepts = [], []
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
    tf = {c: sum(1 for qc in per_q_concepts if c in qc) / n_questions for c in unique_concepts}
    cur.execute("SELECT COUNT(DISTINCT clean_ref) FROM articles")
    total_articles = cur.fetchone()[0] or 1
    idf = {}
    for concept in unique_concepts:
        cur.execute("""
            SELECT COUNT(DISTINCT p.clean_ref) FROM question_ref_pairs p
            JOIN questions q ON p.qid = q.qid
            WHERE LOWER(q.concept_tags) LIKE ?
        """, (f"%{concept}%",))
        doc_freq = cur.fetchone()[0] or 1
        idf[concept] = math.log(total_articles / doc_freq)
    scores = {c: tf[c] * idf[c] for c in unique_concepts}
    if len(scores) < 2:
        return {c: "green" for c in scores}
    sorted_scores = sorted(scores.values())
    low_cut  = sorted_scores[len(sorted_scores) // 3]
    high_cut = sorted_scores[(2 * len(sorted_scores)) // 3]
    result = {}
    for concept, score in scores.items():
        if score >= high_cut:   result[concept] = "green"
        elif score >= low_cut:  result[concept] = "yellow"
        else:                   result[concept] = "red"
    return result


# ── Phase 1: Submit ───────────────────────────────────────────────────────
def phase_submit(client, conn, files, force, dry_run, state_path):
    print(f"  Scanning {len(files)} files against DB...")
    requests   = []
    state_meta = {}
    no_match   = []
    skipped    = []

    for fpath in files:
        try:
            with open(fpath, encoding="utf-8") as f:
                doc = json.load(f)
        except Exception as e:
            print(f"  [SKIP] {fpath.name} -- load error: {e}")
            skipped.append(str(fpath))
            continue

        if not force and doc.get("ite_intelligence") and doc["ite_intelligence"].get("citation_count"):
            skipped.append(str(fpath))
            continue

        source  = doc.get("source", {})
        title   = source.get("title", fpath.stem)
        payload = lookup_article(conn, fpath, source)

        if not payload:
            no_match.append(fpath.name)
            continue

        base_id   = re.sub(r"[^a-zA-Z0-9_-]", "_", fpath.stem)[:55]
        custom_id = f"{base_id}_{len(requests):04d}"
        prompt    = build_prompt(payload, title)

        requests.append({
            "custom_id": custom_id,
            "params": {
                "model": MODEL,
                "max_tokens": 800,
                "messages": [{"role": "user", "content": prompt}]
            }
        })
        state_meta[custom_id] = {
            "file_path":    str(fpath),
            "clean_ref":    payload["clean_ref"],
            "match_method": payload["match_method"],
            "tier":         payload["tier"],
            "citation_display": payload.get("citation_display", ""),
            "questions":    payload["questions"]
        }

    print(f"  DB matches: {len(requests)} | No match: {len(no_match)} | Skipped: {len(skipped)}")
    for nm in no_match:
        print(f"    [no_match] {nm}")

    if not requests:
        print("  Nothing to submit.")
        return

    if dry_run:
        print(f"\n  DRY RUN -- would submit {len(requests)} requests to Batch API")
        for r in requests[:5]:
            print(f"    {r['custom_id']}")
        if len(requests) > 5:
            print(f"    ... and {len(requests)-5} more")
        return

    print(f"\n  Submitting {len(requests)} requests to Batch API...")
    batch = client.messages.batches.create(requests=requests)
    batch_id = batch.id

    state = {
        "batch_id":    batch_id,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "total":       len(requests),
        "no_match":    no_match,
        "skipped":     skipped,
        "meta":        state_meta
    }
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

    print(f"\n  Batch submitted successfully.")
    print(f"  Batch ID : {batch_id}")
    print(f"  Requests : {len(requests)}")
    print(f"  State    : {state_path}")
    print(f"\n  Poll with:")
    print(f"    python scripts/ite_intelligence_enricher_batch.py --poll")
    print(f"  Write results with:")
    print(f"    python scripts/ite_intelligence_enricher_batch.py --write")


# ── Phase 2: Poll ─────────────────────────────────────────────────────────
def phase_poll(client, state_path):
    with open(state_path, encoding="utf-8") as f:
        state = json.load(f)
    batch_id = state["batch_id"]
    batch    = client.messages.batches.retrieve(batch_id)
    counts   = batch.request_counts

    print(f"  Batch ID  : {batch_id}")
    print(f"  Status    : {batch.processing_status}")
    print(f"  Submitted : {state['submitted_at']}")
    print(f"  Total     : {state['total']}")
    print(f"  Processing: {counts.processing}")
    print(f"  Succeeded : {counts.succeeded}")
    print(f"  Errored   : {counts.errored}")
    print(f"  Canceled  : {counts.canceled}")
    print(f"  Expired   : {counts.expired}")

    if batch.processing_status == "ended":
        print(f"\n  Batch COMPLETE -- run --write to save results.")
    else:
        print(f"\n  Still processing -- poll again in a few minutes.")


# ── Phase 3: Write ────────────────────────────────────────────────────────
def phase_write(client, conn, state_path):
    with open(state_path, encoding="utf-8") as f:
        state = json.load(f)
    batch_id = state["batch_id"]
    meta     = state["meta"]

    batch = client.messages.batches.retrieve(batch_id)
    if batch.processing_status != "ended":
        print(f"  Batch not yet complete (status: {batch.processing_status}). Run --poll first.")
        return

    print(f"  Pulling results for batch {batch_id}...")
    enriched = errors = 0
    method_counts = {}

    for result in client.messages.batches.results(batch_id):
        custom_id = result.custom_id
        if custom_id not in meta:
            print(f"  [WARN] Unknown custom_id: {custom_id}")
            continue

        m         = meta[custom_id]
        fpath     = Path(m["file_path"])
        questions = m["questions"]

        if result.result.type != "succeeded":
            print(f"  [ERROR] {fpath.name} -- {result.result.type}")
            errors += 1
            continue

        raw_text = result.result.message.content[0].text.strip()
        raw_text = re.sub(r'^```json\s*', '', raw_text)
        raw_text = re.sub(r'\s*```$', '', raw_text)

        try:
            ite_block = json.loads(raw_text)
        except json.JSONDecodeError as e:
            print(f"  [ERROR] {fpath.name} -- JSON parse failed: {e}")
            errors += 1
            continue

        confidence = compute_enrichment_confidence(m["match_method"], len(questions))
        ite_block["enrichment_confidence"] = confidence
        ite_block["_match_method"]         = m["match_method"]
        ite_block["_enriched_at"]          = datetime.now(timezone.utc).isoformat()

        concept_colors = _compute_concept_tfidf(conn, m["clean_ref"], questions)
        ite_block["linked_qids"] = [
            {
                "qid":            q["qid"],
                "exam_year":      q["exam_year"],
                "question_stem":  q["stem"][:200] if q.get("stem") else "",
                "concept_tested": _parse_concept_tags(q.get("concept_tags", "")),
                "concept_colors": _build_concept_colors(q.get("concept_tags", ""), concept_colors)
            }
            for q in questions
        ]
        ite_block["exam_years"] = sorted(set(q["exam_year"] for q in questions))

        try:
            with open(fpath, encoding="utf-8") as f:
                doc = json.load(f)
        except Exception as e:
            print(f"  [ERROR] {fpath.name} -- could not reload JSON: {e}")
            errors += 1
            continue

        doc["ite_intelligence"] = ite_block
        if m.get("citation_display"):
            doc.setdefault("source", {})["citation_display"] = m["citation_display"]
        if "metadata" in doc:
            doc["metadata"]["schema_version"] = "unified_v1.1"

        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2, ensure_ascii=False)

        method_counts[m["match_method"]] = method_counts.get(m["match_method"], 0) + 1
        enriched += 1
        print(f"  [OK] {fpath.name} ({m['match_method']}, {len(questions)} Qs)")

    print(f"\n  WRITE COMPLETE")
    print(f"  Enriched : {enriched}")
    print(f"  Errors   : {errors}")
    print(f"  Methods  : {method_counts}")

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"enricher_batch_write_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(log_file, "w") as f:
        json.dump({"batch_id": batch_id, "enriched": enriched,
                   "errors": errors, "method_counts": method_counts}, f, indent=2)
    print(f"  Log      : {log_file}")


# ── Main ──────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Batch API ITE Intelligence Enricher v4")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--submit", action="store_true", help="Phase 1: DB lookup + submit batch")
    group.add_argument("--poll",   action="store_true", help="Phase 2: Check batch status")
    group.add_argument("--write",  action="store_true", help="Phase 3: Pull results + write JSONs")
    parser.add_argument("--dir",   type=str, help="Directory of *_extracted.json files")
    parser.add_argument("--file",  type=str, help="Single JSON file (submit only)")
    parser.add_argument("--state", type=str, help="State file path (default: auto-named in logs/)")
    parser.add_argument("--force", action="store_true", help="Re-enrich already-enriched files")
    parser.add_argument("--dry-run", action="store_true", help="Submit: preview without API call")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("[ERROR] ANTHROPIC_API_KEY not set."); return

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    state_path = Path(args.state) if args.state else \
        LOG_DIR / "batch_enricher_state.json"

    client = anthropic.Anthropic(api_key=api_key)

    print("=" * 60)
    print("ITE Intelligence Enricher -- Batch API Mode v4 (codon-first)")
    print(f"  Strategies: codon_filename -> clean_ref -> no_match")
    print("=" * 60)

    if args.poll:
        if not state_path.exists():
            print(f"[ERROR] State file not found: {state_path}"); return
        phase_poll(client, state_path)
        return

    if args.write:
        if not state_path.exists():
            print(f"[ERROR] State file not found: {state_path}"); return
        conn = sqlite3.connect(DB_PATH)
        phase_write(client, conn, state_path)
        conn.close()
        return

    # --submit
    if not DB_PATH.exists():
        print(f"[ERROR] DB not found: {DB_PATH}"); return

    target_dir = Path(args.dir) if args.dir else JSON_DIR
    if args.file:
        files = [Path(args.file)]
    else:
        files = sorted(target_dir.glob("*_extracted.json"))

    if not files:
        print(f"[ERROR] No *_extracted.json files found in: {target_dir}"); return

    print(f"  Target : {target_dir}")
    print(f"  Files  : {len(files)}")
    print(f"  Force  : {args.force}")
    print(f"  Dry run: {args.dry_run}")
    print(f"  State  : {state_path}")

    conn = sqlite3.connect(DB_PATH)
    phase_submit(client, conn, files, args.force, args.dry_run, state_path)
    conn.close()


if __name__ == "__main__":
    main()
