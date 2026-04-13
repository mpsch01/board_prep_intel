"""
batch_db_extract.py — Batch API wrapper for DB-guided clinical extraction
==========================================================================
v1.0  |  2026-03-15

Uses the Anthropic Message Batches API (50% cheaper) to run DB-guided extraction
on all 141 migration JSONs that have codon filenames but empty extraction blocks.

THREE-PHASE WORKFLOW:
  Phase 1 — Submit:
    python scripts/batch_db_extract.py --submit --dir "clinical_guidelines/03_enriched_JSON"
    Assembles clue packages from DB, bundles into one Batch API call,
    saves batch_id + per-file metadata to a state file.

  Phase 2 — Poll (run anytime after submit):
    python scripts/batch_db_extract.py --poll
    Checks batch status. Prints processing_status + request counts.

  Phase 3 — Write (run after batch ends):
    python scripts/batch_db_extract.py --write
    Pulls all results, merges extraction+synthesis blocks into JSONs.

OPTIONS:
  --dir PATH       Directory of *_extracted.json files
  --state PATH     State file path (default: auto-named in logs/)
  --force          Re-extract files that already have extraction block
  --dry-run        Submit phase: show what would be submitted, don't call API
  --limit N        Max files to submit (0 = all)

Requires: ANTHROPIC_API_KEY env var
"""

import sqlite3, json, re, os, sys, argparse, time
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

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

# ── Paths ─────────────────────────────────────────────────────────────────
BASE_DIR  = Path(__file__).resolve().parent.parent.parent   # 00_#PROJECT_OVERHAUL/
DB_PATH   = BASE_DIR / "00_database" / "db" / "ite_intelligence.db"
LOG_DIR   = BASE_DIR / "00_database" / "logs"
JSON_DIR  = BASE_DIR / "extracted_json"                     # override with --dir in practice
MODEL     = "claude-sonnet-4-6"
MAX_RAW_CHARS = 120_000

# ── Import core logic from db_guided_extractor ───────────────────────────
# We reuse the clue assembly and prompt building functions
sys.path.insert(0, str(Path(__file__).resolve().parent))
from db_guided_extractor import (
    get_article_metadata,
    get_linked_questions,
    build_clue_package,
    build_prompt,
    resolve_raw_text_path,
    parse_art_id,
    EXTRACTION_SCHEMA,
)


# ── Phase 1: Submit ──────────────────────────────────────────────────────
def phase_submit(client, conn, files, force, dry_run, state_path, limit):
    print(f"  Scanning {len(files)} files...")
    requests   = []
    state_meta = {}
    no_codon   = []
    no_db      = []
    no_text    = []
    skipped    = []

    for fpath in files:
        try:
            with open(fpath, encoding="utf-8") as f:
                doc = json.load(f)
        except Exception as e:
            print(f"  [SKIP] {fpath.name} -- load error: {e}")
            skipped.append(str(fpath))
            continue

        # Check if extraction already exists
        if not force:
            ext = doc.get("extraction", {})
            if ext and ext.get("summary", "").strip():
                skipped.append(str(fpath))
                continue

        # Parse ART-ID from codon filename
        source_fn = doc.get("source", {}).get("file_name", "")
        art_id = parse_art_id(source_fn)
        if not art_id:
            no_codon.append(fpath.name)
            continue

        # Get DB metadata
        article = get_article_metadata(conn, art_id)
        if not article:
            no_db.append(f"{fpath.name} ({art_id})")
            continue

        # Get linked questions
        questions = get_linked_questions(conn, article["clean_ref"])

        # Build clue package
        clue_package = build_clue_package(article, questions)

        # Load raw text
        raw_path = resolve_raw_text_path(fpath, doc)
        if not raw_path:
            no_text.append(fpath.name)
            continue

        raw_text = raw_path.read_text(encoding='utf-8')
        if len(raw_text) > MAX_RAW_CHARS:
            raw_text = raw_text[:MAX_RAW_CHARS] + "\n\n[... text truncated at extraction limit ...]"

        # Build prompt
        prompt = build_prompt(clue_package, raw_text)

        # Create batch request
        base_id   = re.sub(r"[^a-zA-Z0-9_-]", "_", fpath.stem)[:55]
        custom_id = f"{base_id}_{len(requests):04d}"

        requests.append({
            "custom_id": custom_id,
            "params": {
                "model": MODEL,
                "max_tokens": 4096,
                "temperature": 0.1,
                "messages": [{"role": "user", "content": prompt}]
            }
        })
        state_meta[custom_id] = {
            "file_path":     str(fpath),
            "art_id":        art_id,
            "clean_ref":     article["clean_ref"],
            "source_fn":     source_fn,
            "n_questions":   len(questions),
            "prompt_chars":  len(prompt),
            "raw_chars":     len(raw_text),
            "clue_stats": {
                "hot_diagnoses": clue_package["exam_intelligence"]["hot_zone_diagnoses"],
                "hot_drugs":     clue_package["exam_intelligence"]["hot_zone_drugs"],
                "exam_years":    clue_package["exam_intelligence"]["exam_years_tested"],
                "trend":         clue_package["exam_intelligence"]["trend"],
            }
        }

        if limit > 0 and len(requests) >= limit:
            break

    print(f"  Matched:  {len(requests)}")
    print(f"  No codon: {len(no_codon)}")
    print(f"  No DB:    {len(no_db)}")
    print(f"  No text:  {len(no_text)}")
    print(f"  Skipped:  {len(skipped)}")

    if no_db:
        for x in no_db:
            print(f"    [no_db] {x}")

    if not requests:
        print("  Nothing to submit.")
        return

    # Cost estimate
    total_prompt_chars = sum(m["prompt_chars"] for m in state_meta.values())
    est_input_tokens = total_prompt_chars / 4  # rough char-to-token ratio
    est_output_tokens = len(requests) * 2000   # ~2K output tokens per response
    est_cost_full = (est_input_tokens * 3 / 1_000_000) + (est_output_tokens * 15 / 1_000_000)
    est_cost_batch = est_cost_full * 0.5

    print(f"\n  Estimated cost (Batch API, 50% discount): ~${est_cost_batch:.2f}")
    print(f"  (vs. sequential: ~${est_cost_full:.2f})")

    if dry_run:
        print(f"\n  DRY RUN -- would submit {len(requests)} requests to Batch API")
        for r in requests[:5]:
            m = state_meta[r["custom_id"]]
            print(f"    {r['custom_id'][:50]} | {m['art_id']} | {m['n_questions']}Qs | {m['prompt_chars']:,}ch")
        if len(requests) > 5:
            print(f"    ... and {len(requests)-5} more")
        return

    print(f"\n  Submitting {len(requests)} requests to Batch API...")
    batch = client.messages.batches.create(requests=requests)
    batch_id = batch.id

    state = {
        "batch_id":     batch_id,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "total":        len(requests),
        "model":        MODEL,
        "no_codon":     no_codon,
        "no_db":        no_db,
        "no_text":      no_text,
        "skipped_count": len(skipped),
        "meta":         state_meta,
    }
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

    print(f"\n  Batch submitted successfully.")
    print(f"  Batch ID : {batch_id}")
    print(f"  Requests : {len(requests)}")
    print(f"  State    : {state_path}")
    print(f"\n  Poll with:")
    print(f"    python scripts/batch_db_extract.py --poll")
    print(f"  Write results with:")
    print(f"    python scripts/batch_db_extract.py --write")


# ── Phase 2: Poll ────────────────────────────────────────────────────────
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


# ── Phase 3: Write ───────────────────────────────────────────────────────
def phase_write(client, state_path):
    with open(state_path, encoding="utf-8") as f:
        state = json.load(f)
    batch_id = state["batch_id"]
    meta     = state["meta"]

    batch = client.messages.batches.retrieve(batch_id)
    if batch.processing_status != "ended":
        print(f"  Batch not yet complete (status: {batch.processing_status}). Run --poll first.")
        return

    print(f"  Pulling results for batch {batch_id}...")
    success = errors = parse_errors = 0
    results_log = []

    for result in client.messages.batches.results(batch_id):
        custom_id = result.custom_id
        if custom_id not in meta:
            print(f"  [WARN] Unknown custom_id: {custom_id}")
            continue

        m     = meta[custom_id]
        fpath = Path(m["file_path"])

        if result.result.type != "succeeded":
            print(f"  [ERROR] {fpath.name} -- {result.result.type}")
            errors += 1
            results_log.append({"file": fpath.name, "status": "api_error",
                                "error": result.result.type})
            continue

        raw_text = result.result.message.content[0].text.strip()
        # Strip markdown fencing if present
        if raw_text.startswith("```"):
            raw_text = re.sub(r'^```(?:json)?\s*', '', raw_text)
            raw_text = re.sub(r'\s*```$', '', raw_text)

        try:
            extraction_result = json.loads(raw_text)
        except json.JSONDecodeError as e:
            print(f"  [PARSE ERROR] {fpath.name} -- {e}")
            parse_errors += 1
            results_log.append({"file": fpath.name, "status": "parse_error",
                                "error": str(e)})
            continue

        # Load existing JSON
        try:
            with open(fpath, encoding="utf-8") as f:
                doc = json.load(f)
        except Exception as e:
            print(f"  [ERROR] {fpath.name} -- could not reload JSON: {e}")
            errors += 1
            continue

        # Build extraction block with metadata
        extraction = {
            "summary":         extraction_result.get("summary", ""),
            "population":      extraction_result.get("population", {}),
            "key_thresholds":  extraction_result.get("key_thresholds", []),
            "recommendations": extraction_result.get("recommendations", []),
            "medications":     extraction_result.get("medications", []),
            "red_flags":       extraction_result.get("red_flags", []),
            "follow_up":       extraction_result.get("follow_up", ""),
            "escalation_path": extraction_result.get("escalation_path", ""),
            "synthesis":       extraction_result.get("synthesis", {}),
            "_extraction_method": "db_guided_batch_v1",
            "_extracted_at":   datetime.now(timezone.utc).isoformat(),
            "_clue_stats": {
                "questions_used": m["n_questions"],
                "exam_years":    m["clue_stats"]["exam_years"],
                "trend":         m["clue_stats"]["trend"],
            }
        }

        doc["extraction"] = extraction

        # Update metadata if present
        if "metadata" in doc:
            doc["metadata"]["extraction_method"] = "db_guided_batch_v1"
            doc["metadata"]["extraction_timestamp"] = extraction["_extracted_at"]

        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2, ensure_ascii=False)

        # Quick stats
        n_recs   = len(extraction_result.get("recommendations", []))
        n_meds   = len(extraction_result.get("medications", []))
        n_thresh = len(extraction_result.get("key_thresholds", []))
        n_pearls = len(extraction_result.get("synthesis", {}).get("practice_pearls", []))

        print(f"  [OK] {fpath.name[:60]} | {n_recs}R {n_meds}M {n_thresh}T {n_pearls}P")
        success += 1
        results_log.append({
            "file": fpath.name, "status": "success", "art_id": m["art_id"],
            "recommendations": n_recs, "medications": n_meds,
            "thresholds": n_thresh, "pearls": n_pearls,
        })

    print(f"\n{'═' * 60}")
    print(f"  WRITE COMPLETE")
    print(f"  Success:      {success}")
    print(f"  API errors:   {errors}")
    print(f"  Parse errors: {parse_errors}")
    print(f"{'═' * 60}")

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"batch_extraction_write_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(log_file, "w") as f:
        json.dump({
            "batch_id": batch_id,
            "success": success,
            "errors": errors,
            "parse_errors": parse_errors,
            "results": results_log,
        }, f, indent=2)
    print(f"  Log: {log_file}")


# ── Main ─────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Batch API DB-guided clinical extraction v1.0"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--submit", action="store_true", help="Phase 1: Assemble clues + submit batch")
    group.add_argument("--poll",   action="store_true", help="Phase 2: Check batch status")
    group.add_argument("--write",  action="store_true", help="Phase 3: Pull results + merge into JSONs")
    parser.add_argument("--dir",   type=str, help="Directory of *_extracted.json files")
    parser.add_argument("--state", type=str, help="State file path (default: auto-named in logs/)")
    parser.add_argument("--force", action="store_true", help="Re-extract files with existing extraction")
    parser.add_argument("--dry-run", action="store_true", help="Submit: preview without API call")
    parser.add_argument("--limit", type=int, default=0, help="Max files to submit (0 = all)")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("[ERROR] ANTHROPIC_API_KEY not set.")
        return 1

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    state_path = Path(args.state) if args.state else \
        LOG_DIR / "batch_extraction_state.json"

    client = anthropic.Anthropic(api_key=api_key)

    print("=" * 60)
    print("DB-Guided Extractor — Batch API Mode v1.0")
    print(f"  Model: {MODEL}")
    print("=" * 60)

    if args.poll:
        if not state_path.exists():
            print(f"[ERROR] State file not found: {state_path}")
            return 1
        phase_poll(client, state_path)
        return 0

    if args.write:
        if not state_path.exists():
            print(f"[ERROR] State file not found: {state_path}")
            return 1
        phase_write(client, state_path)
        return 0

    # --submit
    if not DB_PATH.exists():
        print(f"[ERROR] DB not found: {DB_PATH}")
        return 1

    target_dir = Path(args.dir) if args.dir else JSON_DIR
    files = sorted(target_dir.glob("*_extracted.json"))

    if not files:
        print(f"[ERROR] No *_extracted.json files found in: {target_dir}")
        return 1

    print(f"  Target : {target_dir}")
    print(f"  Files  : {len(files)}")
    print(f"  Force  : {args.force}")
    print(f"  Dry run: {args.dry_run}")
    print(f"  Limit  : {args.limit or 'all'}")
    print(f"  State  : {state_path}")

    conn = sqlite3.connect(str(DB_PATH))
    phase_submit(client, conn, files, args.force, args.dry_run, state_path, args.limit)
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
