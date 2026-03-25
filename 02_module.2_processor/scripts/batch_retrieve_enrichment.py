"""
batch_retrieve_enrichment.py — Poll or retrieve Batch API enrichment results
=============================================================================
v1.0  |  2026-03-25  |  Written for batch msgbatch_01F8EYo8LCGy9iH2D6kARGPQ

Two commands only:
  --poll    Check current status of the batch (no writes)
  --get     Retrieve all results and write ite_intelligence{} blocks into JSONs

Usage:
  python3 02_module.2_processor/scripts/batch_retrieve_enrichment.py --poll
  python3 02_module.2_processor/scripts/batch_retrieve_enrichment.py --get
  python3 02_module.2_processor/scripts/batch_retrieve_enrichment.py --get --wait

  --wait    Poll every 60s until batch ends, then auto-run --get

Requires: ANTHROPIC_API_KEY env var
"""

import sqlite3, json, re, sys, argparse, time, math
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

# ── Config ─────────────────────────────────────────────────────────────────
BATCH_ID     = "msgbatch_01F8EYo8LCGy9iH2D6kARGPQ"
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH      = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"
JSON_DIR     = PROJECT_ROOT / "extracted_json"
LOG_DIR      = SCRIPT_DIR.parent / "logs"
MODEL        = "claude-sonnet-4-20250514"


# ── TF-IDF (ported from ite_intelligence_enricher.py) ──────────────────────
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
    sv = sorted(scores.values())
    lo, hi = sv[len(sv) // 3], sv[(2 * len(sv)) // 3]
    return {c: ("green" if s >= hi else "yellow" if s >= lo else "red") for c, s in scores.items()}


def _parse_concept_tags(raw):
    if not raw:
        return ""
    try:
        obj = json.loads(raw)
        parts = []
        if obj.get("diagnoses"):
            parts.append(", ".join(obj["diagnoses"]))
        if obj.get("concept_summary"):
            parts.append(obj["concept_summary"])
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
    sorted_dx = sorted(diagnoses, key=lambda d: rank.get(concept_colors.get(d.lower().strip(), "yellow"), 1))
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


# ── DB helpers ──────────────────────────────────────────────────────────────
def get_questions_for_clean_ref(conn, clean_ref):
    cur = conn.cursor()
    cur.execute("""
        SELECT p.qid, q.exam_year, q.question_text, q.all_keywords, q.explanation, q.concept_tags
        FROM question_ref_pairs p
        JOIN questions q ON p.qid = q.qid
        WHERE p.clean_ref = ?
        ORDER BY q.exam_year, p.qid
    """, (clean_ref,))
    rows = cur.fetchall()
    return [{"qid": r[0], "exam_year": r[1], "stem": r[2] or "",
             "keywords": r[3] or "", "explanation": r[4] or "",
             "concept_tags": r[5] or ""} for r in rows]


def get_citation_display(conn, clean_ref):
    cur = conn.cursor()
    cur.execute("SELECT citation_display FROM articles WHERE clean_ref=?", (clean_ref,))
    row = cur.fetchone()
    return (row[0] or "").strip() if row else ""


# ── File resolution ─────────────────────────────────────────────────────────
def build_json_lookup(json_dir):
    """
    Returns two dicts:
      stem_map  : filename stem (no ext) -> Path
      artid_map : art_id string          -> Path
    """
    stem_map, artid_map = {}, {}
    for p in json_dir.glob("*.json"):
        stem_map[p.stem] = p
        try:
            doc = json.load(open(p, encoding="utf-8"))
            art_id = doc.get("source", {}).get("art_id", "")
            if art_id:
                artid_map[art_id] = p
        except Exception:
            pass
    return stem_map, artid_map


def resolve_json_path(custom_id, stem_map, artid_map):
    """
    Try filename stem first, then art_id match, then prefix match.
    batch_submit truncated long filenames to 64 chars:
      first_55_chars_of_stem + "_" + 8_char_hash  (total 64)
    So we also try matching on the prefix before the last underscore.
    """
    # Exact match
    if custom_id in stem_map:
        return stem_map[custom_id]
    # Strip common suffixes if submit script added them
    for suffix in ("_extracted", "_enriched"):
        if custom_id.endswith(suffix) and custom_id[:-len(suffix)] in stem_map:
            return stem_map[custom_id[:-len(suffix)]]
    # Try art_id format (e.g. "ART-0437")
    if custom_id in artid_map:
        return artid_map[custom_id]
    # Prefix match for truncated custom_ids (filename truncated to fit 64-char limit)
    # custom_id format: stem[:55] + "_" + hash8  → prefix = stem[:55]
    if "_" in custom_id:
        prefix = custom_id.rsplit("_", 1)[0]
        if len(prefix) >= 20:  # guard against spurious short prefixes
            matches = [path for stem, path in stem_map.items() if stem.startswith(prefix)]
            if len(matches) == 1:
                return matches[0]
    # custom_id might be "filename::art_id" or similar — try splitting
    for sep in ("::", "||"):
        if sep in custom_id:
            parts = custom_id.split(sep)
            for part in parts:
                if part in stem_map:
                    return stem_map[part]
                if part in artid_map:
                    return artid_map[part]
    return None


# ── Poll ────────────────────────────────────────────────────────────────────
def cmd_poll(client):
    print(f"Checking batch: {BATCH_ID}")
    batch = client.beta.messages.batches.retrieve(BATCH_ID)
    status = batch.processing_status
    rc = batch.request_counts
    print(f"\nStatus      : {status}")
    print(f"Processing  : {rc.processing}")
    print(f"Succeeded   : {rc.succeeded}")
    print(f"Errored     : {rc.errored}")
    print(f"Canceled    : {rc.canceled}")
    print(f"Expired     : {rc.expired}")
    if hasattr(batch, 'ended_at') and batch.ended_at:
        print(f"Ended at    : {batch.ended_at}")
    return status


# ── Get ─────────────────────────────────────────────────────────────────────
def cmd_get(client):
    # Verify DB exists
    if not DB_PATH.exists():
        print(f"ERROR: DB not found at {DB_PATH}")
        sys.exit(1)
    if not JSON_DIR.exists():
        print(f"ERROR: JSON dir not found at {JSON_DIR}")
        sys.exit(1)

    # Check batch is done
    batch = client.beta.messages.batches.retrieve(BATCH_ID)
    status = batch.processing_status
    print(f"Batch status: {status}")
    if status != "ended":
        print(f"Batch not yet ended (status={status}). Use --poll to monitor, or --wait to block.")
        sys.exit(0)

    print("Building file lookup...")
    stem_map, artid_map = build_json_lookup(JSON_DIR)
    print(f"  {len(stem_map)} JSONs indexed by stem, {len(artid_map)} by art_id")

    conn = sqlite3.connect(DB_PATH)

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    raw_log_path = LOG_DIR / f"batch_results_raw_{ts}.jsonl"

    results = {
        "written": [], "skipped_already_enriched": [],
        "no_file_match": [], "parse_error": [], "db_no_questions": [], "api_error": []
    }

    print(f"\nStreaming batch results (saving raw to {raw_log_path.name})...")
    raw_log = open(raw_log_path, "w", encoding="utf-8")
    total = 0

    for result in client.beta.messages.batches.results(BATCH_ID):
        total += 1
        custom_id = result.custom_id
        raw_log.write(json.dumps({"custom_id": custom_id, "result": result.model_dump()}) + "\n")

        # Resolve JSON file
        json_path = resolve_json_path(custom_id, stem_map, artid_map)
        if not json_path:
            print(f"  [NO_FILE] custom_id={custom_id}")
            results["no_file_match"].append(custom_id)
            continue

        # Load JSON
        try:
            doc = json.load(open(json_path, encoding="utf-8"))
        except Exception as e:
            results["parse_error"].append({"file": json_path.name, "error": str(e)})
            continue

        # Skip if already enriched
        if doc.get("ite_intelligence", {}).get("citation_count"):
            results["skipped_already_enriched"].append(json_path.name)
            continue

        # Parse ite_block from API response
        if result.result.type != "succeeded":
            print(f"  [API_ERROR] {json_path.name}: {result.result.type}")
            results["api_error"].append({"file": json_path.name, "type": result.result.type})
            continue

        raw_text = result.result.message.content[0].text.strip()
        raw_text = re.sub(r'^```json\s*', '', raw_text)
        raw_text = re.sub(r'\s*```$', '', raw_text)
        try:
            ite_block = json.loads(raw_text)
        except json.JSONDecodeError as e:
            print(f"  [PARSE_ERR] {json_path.name}: {e}")
            results["parse_error"].append({"file": json_path.name, "error": str(e), "raw": raw_text[:200]})
            continue

        # Ensure required fields
        for field in ["exam_years_cited", "question_ids", "citation_count",
                      "high_yield_concepts", "concept_summary", "tier_rationale"]:
            if field not in ite_block:
                ite_block[field] = None

        # Resolve clean_ref for DB lookups
        source     = doc.get("source", {})
        clean_ref  = source.get("clean_ref", "")
        match_method = source.get("backfill_matched_on", "clean_ref") if source.get("art_id") else "codon_filename"

        # DB: get questions for TF-IDF + linked_qids
        questions = get_questions_for_clean_ref(conn, clean_ref) if clean_ref else []
        if not questions:
            # Try art_id lookup
            art_id = source.get("art_id", "")
            if art_id:
                cur = conn.cursor()
                cur.execute("SELECT clean_ref FROM articles WHERE article_id=?", (art_id,))
                row = cur.fetchone()
                if row:
                    clean_ref = row[0]
                    questions = get_questions_for_clean_ref(conn, clean_ref)

        if not questions:
            print(f"  [NO_QS] {json_path.name} — no DB questions found, writing block without linked_qids")
            results["db_no_questions"].append(json_path.name)

        # TF-IDF concept colors
        concept_colors = _compute_concept_tfidf(conn, clean_ref, questions) if questions else {}

        # Build linked_qids
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
        ite_block["exam_years"] = sorted(set(q["exam_year"] for q in questions)) if questions else []

        # Provenance tags
        ite_block["enrichment_confidence"] = "high" if match_method in ("codon_filename", "clean_ref") else "low"
        ite_block["_match_method"]   = match_method
        ite_block["_enriched_at"]    = datetime.now(timezone.utc).isoformat()
        ite_block["_enriched_via"]   = "batch_api"

        # Write citation_display into source block
        if clean_ref:
            cit = get_citation_display(conn, clean_ref)
            if cit:
                doc.setdefault("source", {})["citation_display"] = cit

        doc["ite_intelligence"] = ite_block
        if "metadata" in doc:
            doc["metadata"]["schema_version"] = "unified_v1.1"

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2, ensure_ascii=False)

        concepts_preview = (ite_block.get("high_yield_concepts") or [])[:2]
        print(f"  [OK] {json_path.name} — {len(questions)} Qs, concepts: {concepts_preview}")
        results["written"].append(json_path.name)

    raw_log.close()
    conn.close()

    # Summary
    print(f"\n{'='*60}")
    print(f"BATCH RETRIEVAL COMPLETE")
    print(f"{'='*60}")
    print(f"Total results     : {total}")
    print(f"Written           : {len(results['written'])}")
    print(f"Already enriched  : {len(results['skipped_already_enriched'])}")
    print(f"No file match     : {len(results['no_file_match'])}")
    print(f"DB no questions   : {len(results['db_no_questions'])}")
    print(f"Parse errors      : {len(results['parse_error'])}")
    print(f"API errors        : {len(results['api_error'])}")

    if results["no_file_match"]:
        print(f"\nUnmatched custom_ids (first 5):")
        for cid in results["no_file_match"][:5]:
            print(f"  {cid}")
        if len(results["no_file_match"]) > 5:
            print(f"  ... and {len(results['no_file_match']) - 5} more")

    log_path = LOG_DIR / f"batch_retrieve_{ts}.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump({"batch_id": BATCH_ID, "timestamp": ts, "totals": {
            "total": total,
            "written": len(results["written"]),
            "skipped": len(results["skipped_already_enriched"]),
            "no_file_match": len(results["no_file_match"]),
            "db_no_questions": len(results["db_no_questions"]),
            "parse_errors": len(results["parse_error"]),
            "api_errors": len(results["api_error"]),
        }, "details": results}, f, indent=2)
    print(f"\nLog: {log_path}")


# ── Main ────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Poll or retrieve Batch API enrichment results")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--poll", action="store_true", help="Check batch status")
    group.add_argument("--get",  action="store_true", help="Retrieve results and write to JSONs")
    parser.add_argument("--wait", action="store_true",
                        help="With --get: poll until ended, then retrieve")
    args = parser.parse_args()

    client = anthropic.Anthropic()

    if args.poll:
        cmd_poll(client)

    elif args.get:
        if args.wait:
            print(f"Waiting for batch {BATCH_ID} to end (polling every 60s)...")
            while True:
                status = cmd_poll(client)
                if status == "ended":
                    print("\nBatch ended. Retrieving results...")
                    break
                print(f"  Still processing... next check in 60s")
                time.sleep(60)
        cmd_get(client)


if __name__ == "__main__":
    main()
