"""
db_guided_extractor.py — DB-guided clinical extraction using ITE intelligence clues
=====================================================================================
v1.0  |  2026-03-15

For each migration JSON with an empty extraction block:
  1. Parses ART-ID from source.file_name codon
  2. Queries ite_intelligence.db for article metadata + all linked questions
  3. Assembles a "clue package" (concept_tags, question stems, explanations, thresholds)
  4. Loads raw pdfplumber text from raw_txt/
  5. Sends ONE focused Claude call: raw text + clue package → structured extraction + synthesis
  6. Merges result into existing JSON (preserving ite_intelligence block)

Design principle: DB data acts as extraction guide ("flashlight"), Claude makes final connections.
All deterministic work is done pre-call; the LLM only handles what requires intelligence.

Run:
  python scripts/db_guided_extractor.py --file "path/to/single_extracted.json"
  python scripts/db_guided_extractor.py --dir "clinical_guidelines/03_enriched_JSON" [--dry-run] [--force]
  python scripts/db_guided_extractor.py --dir "clinical_guidelines/03_enriched_JSON" --limit 5

Requires: ANTHROPIC_API_KEY env var (or .env file in project root)
"""

import sqlite3, json, re, os, argparse, time, sys
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter

try:
    import anthropic
except ImportError:
    raise ImportError("Run: pip install anthropic")

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# ── Config ────────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).resolve().parent.parent.parent   # board_prep_intel/ (3 hops: scripts/ → M2 → root)
DB_PATH     = BASE_DIR / "00_database" / "db" / "ite_intelligence.db"
LOG_DIR     = BASE_DIR / "00_database" / "logs"
# Legacy fallback extractor — superseded by ite_intelligence_enricher.py for new runs
MODEL       = "claude-sonnet-4-6"
MAX_RAW_CHARS = 120_000   # ~30K tokens; truncate raw text beyond this
MAX_RETRIES = 2
RETRY_DELAY = 5

# ── Extraction output schema (matches build_summary.js sections 3-11) ────
EXTRACTION_SCHEMA = """{
  "summary": "string — 2-3 sentence clinical bottom line",
  "population": {
    "age_criteria": "string",
    "risk_criteria": "string",
    "disease_definition": "string",
    "exclusions": "string",
    "severity_staging": "string"
  },
  "key_thresholds": [
    {"parameter": "string", "value": "string or number", "unit": "string", "context": "string"}
  ],
  "recommendations": [
    {"recommendation": "string", "evidence_level": "string", "strength": "string", "notes": "string"}
  ],
  "medications": [
    {"drug": "string", "class": "string", "dose": "string", "indication": "string"}
  ],
  "red_flags": ["string"],
  "follow_up": "string",
  "escalation_path": "string",
  "synthesis": {
    "clinical_bottom_line": "string — 1-2 sentence summary for a resident",
    "practice_pearls": ["string — high-yield clinical pearls, prioritize repeatedly tested concepts"],
    "definitions_and_thresholds": [
      {"term": "string", "definition": "string"}
    ],
    "medication_groups": [
      {"group_name": "string", "narrative": "string", "drugs": ["string"]}
    ],
    "critical_alerts": [
      {"alert": "string", "why_it_matters": "string"}
    ]
  }
}"""


# ── DB Queries ────────────────────────────────────────────────────────────
def get_article_metadata(conn, art_id):
    """Pull article-level metadata from articles table."""
    cur = conn.cursor()
    cur.execute("""
        SELECT clean_ref, article_id, author1, author2, year, title,
               source_type, categories, blueprint_cats, tier,
               citation_count, unique_years, exam_years, qid_list,
               citation_display
        FROM articles
        WHERE article_id = ?
    """, (art_id,))
    row = cur.fetchone()
    if not row:
        return None
    cols = ["clean_ref", "article_id", "author1", "author2", "year", "title",
            "source_type", "categories", "blueprint_cats", "tier",
            "citation_count", "unique_years", "exam_years", "qid_list",
            "citation_display"]
    return dict(zip(cols, row))


def get_linked_questions(conn, clean_ref):
    """Pull all linked questions with full detail."""
    cur = conn.cursor()
    cur.execute("""
        SELECT q.qid, q.exam_year, q.body_system, q.blueprint,
               q.question_text, q.choices, q.correct_letter, q.correct_text,
               q.explanation, q.concept_tags, q.stem_keywords,
               q.explanation_keywords, q.all_keywords
        FROM question_ref_pairs p
        JOIN questions q ON p.qid = q.qid
        WHERE p.clean_ref = ?
        ORDER BY q.exam_year, p.qid
    """, (clean_ref,))
    rows = cur.fetchall()
    cols = ["qid", "exam_year", "body_system", "blueprint",
            "question_text", "choices", "correct_letter", "correct_text",
            "explanation", "concept_tags", "stem_keywords",
            "explanation_keywords", "all_keywords"]
    return [dict(zip(cols, r)) for r in rows]


# ── Clue Package Assembly ─────────────────────────────────────────────────
def build_clue_package(article, questions):
    """
    Assemble all DB intelligence into a structured clue package.
    This is the "flashlight" that guides Claude's extraction.
    """
    # Parse all concept_tags across questions
    all_diagnoses = []
    all_drugs = []
    all_guidelines = []
    all_thresholds = []
    all_summaries = []

    for q in questions:
        try:
            tags = json.loads(q.get("concept_tags") or "{}")
            all_diagnoses.extend(tags.get("diagnoses", []))
            all_drugs.extend(tags.get("drugs", []))
            all_guidelines.extend(tags.get("guidelines", []))
            all_thresholds.extend(tags.get("thresholds", []))
            if tags.get("concept_summary"):
                all_summaries.append(tags["concept_summary"])
        except (json.JSONDecodeError, TypeError):
            pass

    # Frequency-ranked concepts (hot zones)
    dx_freq = Counter(d.lower().strip() for d in all_diagnoses)
    drug_freq = Counter(d.lower().strip() for d in all_drugs)
    threshold_freq = Counter(t.lower().strip() for t in all_thresholds)

    # Exam year trend
    years = sorted(set(q["exam_year"] for q in questions if q.get("exam_year")))
    if len(years) >= 2:
        recent = sum(1 for y in years if y >= 2023)
        older = sum(1 for y in years if y < 2023)
        trend = "increasing" if recent > older else "stable" if recent == older else "decreasing"
    else:
        trend = "single-year" if years else "unknown"

    return {
        "article": {
            "title": article.get("title", ""),
            "authors": f"{article.get('author1', '')} {article.get('author2', '') or ''}".strip(),
            "year": article.get("year"),
            "source_type": article.get("source_type", ""),
            "categories": article.get("categories", ""),
            "blueprint_cats": article.get("blueprint_cats", ""),
            "tier": article.get("tier", ""),
            "citation_count": article.get("citation_count", 0),
            "exam_years": article.get("exam_years", ""),
            "unique_years": article.get("unique_years", 0),
        },
        "exam_intelligence": {
            "total_questions_linked": len(questions),
            "exam_years_tested": years,
            "trend": trend,
            "hot_zone_diagnoses": [f"{dx} (×{c})" for dx, c in dx_freq.most_common(10)],
            "hot_zone_drugs": [f"{d} (×{c})" for d, c in drug_freq.most_common(10)],
            "recurring_thresholds": [f"{t} (×{c})" for t, c in threshold_freq.most_common(10)],
            "concept_summaries": all_summaries[:5],
        },
        "question_details": [
            {
                "qid": q["qid"],
                "exam_year": q["exam_year"],
                "body_system": q["body_system"],
                "question_stem": (q.get("question_text") or "")[:500],
                "correct_answer": q.get("correct_text", ""),
                "explanation": (q.get("explanation") or "")[:600],
                "concept_tags_raw": q.get("concept_tags", ""),
            }
            for q in questions
        ],
    }


# ── Prompt Construction ───────────────────────────────────────────────────
def build_prompt(clue_package, raw_text):
    """Build the single focused extraction prompt."""
    art = clue_package["article"]
    intel = clue_package["exam_intelligence"]
    qs = clue_package["question_details"]

    # Build question details section
    q_lines = []
    for q in qs:
        q_lines.append(f"""  [{q['qid']}] (Year {q['exam_year']}, {q['body_system']})
    Stem: {q['question_stem']}
    Correct answer: {q['correct_answer']}
    Explanation: {q['explanation']}
    Concept tags: {q['concept_tags_raw']}""")

    questions_text = "\n\n".join(q_lines) if q_lines else "  (No linked questions)"

    prompt = f"""You are extracting structured clinical content from a medical article for a family medicine board exam preparation system.

## ARTICLE METADATA
- Title: {art['title']}
- Authors: {art['authors']}
- Year: {art['year']}
- Source type: {art['source_type']}
- Clinical domain(s): {art['categories']}
- Blueprint categories: {art['blueprint_cats']}
- ITE tier: {art['tier']}
- Citation count: {art['citation_count']} (across {art['unique_years']} exam years: {art['exam_years']})

## ITE EXAM INTELLIGENCE
This article has been directly referenced by {intel['total_questions_linked']} ITE question(s) across exam years {', '.join(str(y) for y in intel['exam_years_tested'])}.
Testing trend: {intel['trend']}

### High-frequency tested concepts (ranked by how often ABFM tested them):
- Diagnoses: {', '.join(intel['hot_zone_diagnoses']) or 'none identified'}
- Drugs: {', '.join(intel['hot_zone_drugs']) or 'none identified'}
- Thresholds: {', '.join(intel['recurring_thresholds']) or 'none identified'}

### Concept summaries from linked questions:
{chr(10).join('- ' + s for s in intel['concept_summaries']) if intel['concept_summaries'] else '- none'}

## LINKED EXAM QUESTIONS (what ABFM actually tested from this article)
{questions_text}

## RAW ARTICLE TEXT
<article_text>
{raw_text}
</article_text>

## INSTRUCTIONS
Extract structured clinical content from the article text above. The exam intelligence tells you exactly which concepts matter most for board preparation — prioritize those.

Rules:
1. For recommendations, if one directly addresses a tested question's concept, add "(Tested: [QID])" in the notes field.
2. For key_thresholds, prioritize any thresholds that appear in the exam intelligence "recurring_thresholds" list.
3. For practice_pearls in the synthesis, lead with concepts that have been repeatedly tested or show increasing exam frequency.
4. For medications, include dosing and indication details when available in the article text.
5. If the article text doesn't contain information for a field, use an empty string or empty array — don't fabricate content.
6. The summary should be 2-3 sentences covering the article's core clinical message.
7. The clinical_bottom_line in synthesis should be 1-2 sentences a resident can use for quick review.

Return ONLY valid JSON matching this exact schema (no markdown fencing, no commentary):
{EXTRACTION_SCHEMA}"""

    return prompt


# ── Claude API Call ───────────────────────────────────────────────────────
def call_claude(client, prompt, dry_run=False):
    """Make one focused Claude call. Returns parsed extraction dict."""
    if dry_run:
        return {"_dry_run": True, "prompt_length": len(prompt)}

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            text = response.content[0].text.strip()

            # Strip markdown fencing if present
            if text.startswith("```"):
                text = re.sub(r'^```(?:json)?\s*', '', text)
                text = re.sub(r'\s*```$', '', text)

            result = json.loads(text)
            return result

        except json.JSONDecodeError as e:
            if attempt < MAX_RETRIES:
                print(f"    [RETRY {attempt+1}] JSON parse error: {e}")
                time.sleep(RETRY_DELAY)
            else:
                raise ValueError(f"Claude returned invalid JSON after {MAX_RETRIES+1} attempts: {e}")

        except anthropic.RateLimitError:
            wait = RETRY_DELAY * (attempt + 1) * 2
            print(f"    [RATE LIMIT] Waiting {wait}s...")
            time.sleep(wait)

        except anthropic.APIError as e:
            if attempt < MAX_RETRIES:
                print(f"    [API ERROR] {e} — retrying in {RETRY_DELAY}s...")
                time.sleep(RETRY_DELAY)
            else:
                raise


# ── JSON Merge ────────────────────────────────────────────────────────────
def merge_extraction(json_path, extraction_result, clue_package):
    """
    Merge extraction + synthesis into existing JSON.
    Preserves: source, classification, navigator_v1, ite_intelligence, metadata.
    Adds: extraction{} block with synthesis nested inside.
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Build the extraction block
    extraction = {
        "summary": extraction_result.get("summary", ""),
        "population": extraction_result.get("population", {}),
        "key_thresholds": extraction_result.get("key_thresholds", []),
        "recommendations": extraction_result.get("recommendations", []),
        "medications": extraction_result.get("medications", []),
        "red_flags": extraction_result.get("red_flags", []),
        "follow_up": extraction_result.get("follow_up", ""),
        "escalation_path": extraction_result.get("escalation_path", ""),
        "synthesis": extraction_result.get("synthesis", {}),
        "_extraction_method": "db_guided_v1",
        "_extracted_at": datetime.now(timezone.utc).isoformat(),
        "_clue_stats": {
            "questions_used": clue_package["exam_intelligence"]["total_questions_linked"],
            "exam_years": clue_package["exam_intelligence"]["exam_years_tested"],
            "trend": clue_package["exam_intelligence"]["trend"],
            "hot_diagnoses": len(clue_package["exam_intelligence"]["hot_zone_diagnoses"]),
            "hot_drugs": len(clue_package["exam_intelligence"]["hot_zone_drugs"]),
        }
    }

    data["extraction"] = extraction

    # Update metadata if present
    if "metadata" in data:
        data["metadata"]["extraction_method"] = "db_guided_v1"
        data["metadata"]["extraction_timestamp"] = extraction["_extracted_at"]

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return data


# ── File Processing ───────────────────────────────────────────────────────
def needs_extraction(json_path):
    """Check if this JSON needs DB-guided extraction."""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        ext = data.get("extraction", {})
        if ext and ext.get("summary", "").strip():
            return False  # Already has extraction
        # Must have a codon filename to link to DB
        fn = data.get("source", {}).get("file_name", "")
        if "#@#ART-" not in fn:
            return False  # No DB link possible
        return True
    except Exception:
        return False


def parse_art_id(file_name):
    """Extract ART-ID from codon filename."""
    m = re.search(r'#@#(ART-\d+)@#@', file_name)
    return m.group(1) if m else None


def resolve_raw_text_path(json_path, data):
    """
    Find raw text file. Tries:
    1. raw_txt/ sibling folder with matching slug name
    2. ingest.raw_text_path (converted from Windows to local)
    """
    json_dir = Path(json_path).parent
    stem = Path(json_path).stem.replace("_extracted", "")
    raw_path = json_dir / "raw_txt" / f"{stem}.raw.txt"
    if raw_path.exists():
        return raw_path

    # Fallback: try ingest path converted to local
    ingest_path = data.get("ingest", {}).get("raw_text_path", "")
    if ingest_path:
        # Convert Windows path to local (legacy fallback for pre-migration paths)
        local = ingest_path.replace("C:\\Users\\mpsch\\Desktop\\claude_knowledge\\",
                                     str(BASE_DIR) + "/")
        local = local.replace("\\", "/")
        if Path(local).exists():
            return Path(local)

    return None


def process_file(json_path, conn, client, dry_run=False, force=False):
    """Process a single JSON file through DB-guided extraction."""
    json_path = Path(json_path)
    fname = json_path.name

    # Load JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Check if extraction needed
    if not force:
        ext = data.get("extraction", {})
        if ext and ext.get("summary", "").strip():
            return {"status": "skipped", "reason": "already_extracted", "file": fname}

    # Parse ART-ID
    source_fn = data.get("source", {}).get("file_name", "")
    art_id = parse_art_id(source_fn)
    if not art_id:
        return {"status": "skipped", "reason": "no_codon", "file": fname}

    # Get DB metadata
    article = get_article_metadata(conn, art_id)
    if not article:
        return {"status": "error", "reason": f"ART-ID {art_id} not found in DB", "file": fname}

    # Get linked questions
    questions = get_linked_questions(conn, article["clean_ref"])

    # Build clue package
    clue_package = build_clue_package(article, questions)

    # Load raw text
    raw_path = resolve_raw_text_path(json_path, data)
    if not raw_path:
        return {"status": "error", "reason": "raw_text_not_found", "file": fname}

    raw_text = raw_path.read_text(encoding='utf-8')
    if len(raw_text) > MAX_RAW_CHARS:
        raw_text = raw_text[:MAX_RAW_CHARS] + "\n\n[... text truncated at extraction limit ...]"

    # Build prompt
    prompt = build_prompt(clue_package, raw_text)

    # Call Claude
    print(f"  [{art_id}] {source_fn[:60]}...")
    print(f"    Clues: {len(questions)} questions, {len(clue_package['exam_intelligence']['hot_zone_diagnoses'])} dx, "
          f"{len(clue_package['exam_intelligence']['hot_zone_drugs'])} drugs")
    print(f"    Raw text: {len(raw_text):,} chars | Prompt: {len(prompt):,} chars")

    if dry_run:
        return {"status": "dry_run", "file": fname, "art_id": art_id,
                "questions": len(questions), "prompt_chars": len(prompt)}

    extraction_result = call_claude(client, prompt)

    # Merge into JSON
    merge_extraction(json_path, extraction_result, clue_package)

    # Quick validation
    n_recs = len(extraction_result.get("recommendations", []))
    n_meds = len(extraction_result.get("medications", []))
    n_thresh = len(extraction_result.get("key_thresholds", []))
    n_pearls = len(extraction_result.get("synthesis", {}).get("practice_pearls", []))
    print(f"    ✓ Extracted: {n_recs} recs, {n_meds} meds, {n_thresh} thresholds, {n_pearls} pearls")

    return {"status": "success", "file": fname, "art_id": art_id,
            "recommendations": n_recs, "medications": n_meds,
            "thresholds": n_thresh, "pearls": n_pearls}


# ── Main ──────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="DB-guided clinical extraction using ITE intelligence clues"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", type=str, help="Single JSON file to process")
    group.add_argument("--dir", type=str, help="Directory of JSON files to process")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be processed without calling API")
    parser.add_argument("--force", action="store_true",
                        help="Re-extract even if extraction block already exists")
    parser.add_argument("--limit", type=int, default=0,
                        help="Max files to process (0 = all)")
    parser.add_argument("--delay", type=float, default=1.0,
                        help="Seconds between API calls (rate limiting)")
    args = parser.parse_args()

    # Validate DB
    if not DB_PATH.exists():
        print(f"ERROR: Database not found: {DB_PATH}")
        return 2

    conn = sqlite3.connect(str(DB_PATH))

    # Init API client
    client = None
    if not args.dry_run:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            print("ERROR: ANTHROPIC_API_KEY not set")
            return 2
        client = anthropic.Anthropic(api_key=api_key)

    # Collect files
    if args.file:
        files = [Path(args.file)]
    else:
        json_dir = Path(args.dir)
        files = sorted(json_dir.glob("*_extracted.json"))

    # Filter to those needing extraction
    if not args.force:
        eligible = [f for f in files if needs_extraction(f)]
    else:
        # Force mode: only require codon filename
        eligible = []
        for f in files:
            try:
                d = json.load(open(f, 'r', encoding='utf-8'))
                fn = d.get("source", {}).get("file_name", "")
                if "#@#ART-" in fn:
                    eligible.append(f)
            except Exception:
                pass

    if args.limit > 0:
        eligible = eligible[:args.limit]

    print("=" * 70)
    print(f"DB-Guided Extractor v1.0")
    print(f"  Database:  {DB_PATH}")
    print(f"  Model:     {MODEL}")
    print(f"  Files:     {len(eligible)} eligible (of {len(files)} total)")
    print(f"  Dry run:   {args.dry_run}")
    print(f"  Force:     {args.force}")
    print("=" * 70)

    if not eligible:
        print("No files need extraction.")
        return 0

    # Ensure log dir
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    results = []
    success = 0
    skipped = 0
    errors = 0
    start_time = time.time()

    for i, fp in enumerate(eligible, 1):
        print(f"\n[{i}/{len(eligible)}] {fp.name[:70]}")
        try:
            result = process_file(fp, conn, client, dry_run=args.dry_run, force=args.force)
            results.append(result)
            if result["status"] == "success":
                success += 1
            elif result["status"] in ("skipped", "dry_run"):
                skipped += 1
            else:
                errors += 1

            # Rate limiting between API calls
            if not args.dry_run and result["status"] == "success" and i < len(eligible):
                time.sleep(args.delay)

        except Exception as e:
            print(f"    [FATAL] {e}")
            results.append({"status": "error", "reason": str(e), "file": fp.name})
            errors += 1

    elapsed = time.time() - start_time

    # Summary
    print(f"\n{'═' * 70}")
    print(f"COMPLETE  |  {elapsed:.1f}s elapsed")
    print(f"  Success:  {success}")
    print(f"  Skipped:  {skipped}")
    print(f"  Errors:   {errors}")
    print(f"{'═' * 70}")

    # Write log
    log_path = LOG_DIR / f"db_guided_extraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump({
            "run_timestamp": datetime.now(timezone.utc).isoformat(),
            "model": MODEL,
            "dry_run": args.dry_run,
            "force": args.force,
            "files_eligible": len(eligible),
            "success": success,
            "skipped": skipped,
            "errors": errors,
            "elapsed_seconds": round(elapsed, 1),
            "results": results,
        }, f, indent=2, ensure_ascii=False)
    print(f"  Log:      {log_path}")

    conn.close()
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
