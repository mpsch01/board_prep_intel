"""
retrieve_batch_results.py
==========================
Retrieves and processes results from an Anthropic Message Batch submission.
Run this after submit_batch_classification.py once the batch is complete.

Usage:
    python retrieve_batch_results.py --batch-id msgbatch_01abc123
    python retrieve_batch_results.py --batch-id msgbatch_01abc123 --status-only
    python retrieve_batch_results.py --list   # list all recent batches

Output:
    claude_classifications.json  — same format as run_claude_classifier.py
    Appends to existing file if present (for partial re-runs).

Environment:
    ANTHROPIC_API_KEY: required
"""

import os
import sys
import json
import re
import argparse
import sqlite3
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Optional

# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
OUTPUT_DIR   = PROJECT_ROOT / "03_module.3_analyst" / "outputs" / "body_system_labels"

sys.path.insert(0, str(SCRIPT_DIR))
from run_claude_classifier import (
    FINAL_TAXONOMY,
    validate_classification,
    compute_centroid_distance,
    route_classification,
    load_training_set,
    deserialize_embedding,
)
from submit_batch_classification import load_all_embeddings

DB_PATH = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"


def load_batch_meta(batch_id: str) -> Optional[dict]:
    """Load the batch metadata file saved during submission."""
    meta_path = OUTPUT_DIR / f"batch_meta_{batch_id}.json"
    if meta_path.exists():
        with open(meta_path, encoding="utf-8") as f:
            return json.load(f)
    return None


def parse_classification(response_text: str) -> Optional[dict]:
    """Parse Claude's JSON response, with fallback regex extraction."""
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass
    # Fallback: extract JSON object from response
    match = re.search(r"\{[^{}]*\}", response_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Retrieve results from an Anthropic Message Batch"
    )
    parser.add_argument("--batch-id", type=str, help="Batch ID from submit_batch_classification.py")
    parser.add_argument("--status-only", action="store_true", help="Print status without downloading results")
    parser.add_argument("--list", action="store_true", help="List recent batches")
    parser.add_argument("--wait", action="store_true", help="Poll every 90 seconds until batch completes, then process results automatically")
    parser.add_argument("--poll-interval", type=int, default=90, help="Seconds between status checks when --wait is used (default: 90)")
    parser.add_argument("--output-dir", type=str, default=str(OUTPUT_DIR))
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    from anthropic import Anthropic
    client = Anthropic(api_key=api_key)
    out_dir = Path(args.output_dir)

    # ── List mode ──────────────────────────────────────────────────────────────
    if args.list:
        print("Recent batches:")
        for batch in client.messages.batches.list(limit=10):
            counts = batch.request_counts
            print(
                f"  {batch.id}  {batch.processing_status:<12}"
                f"  submitted={batch.created_at}"
                f"  processing={counts.processing}"
                f"  succeeded={counts.succeeded}"
                f"  errored={counts.errored}"
            )
        return

    if not args.batch_id:
        parser.error("--batch-id is required (or use --list to find it)")

    # ── Check status (with optional polling loop) ──────────────────────────────
    import time

    def print_status(batch):
        c = batch.request_counts
        print(f"  [{datetime.now().strftime('%H:%M:%S')}]  "
              f"status={batch.processing_status}  "
              f"processing={c.processing}  succeeded={c.succeeded}  "
              f"errored={c.errored}", flush=True)

    batch = client.messages.batches.retrieve(args.batch_id)

    if args.wait and batch.processing_status != "ended":
        print(f"Batch ID:  {args.batch_id}")
        print(f"Polling every {args.poll_interval}s until complete (Ctrl+C to stop)...")
        print()
        while batch.processing_status != "ended":
            print_status(batch)
            time.sleep(args.poll_interval)
            batch = client.messages.batches.retrieve(args.batch_id)
        print_status(batch)
        print("\nBatch complete — processing results...\n")

    else:
        counts = batch.request_counts
        print(f"Batch ID:  {args.batch_id}")
        print(f"Status:    {batch.processing_status}")
        print(f"Requests:  processing={counts.processing}  "
              f"succeeded={counts.succeeded}  "
              f"errored={counts.errored}  "
              f"expired={counts.expired}")

        if args.status_only:
            if batch.processing_status != "ended":
                print("\nNot ready yet. Re-run without --status-only when complete.")
                print(f"Or use --wait to poll automatically:")
                print(f"  python retrieve_batch_results.py --batch-id {args.batch_id} --wait")
            return

        if batch.processing_status != "ended":
            print(f"\nBatch is still {batch.processing_status}. Options:")
            print(f"  Poll automatically: python retrieve_batch_results.py --batch-id {args.batch_id} --wait")
            print(f"  Check manually:     python retrieve_batch_results.py --batch-id {args.batch_id}")
            return

    # ── Load batch metadata ────────────────────────────────────────────────────
    meta = load_batch_meta(args.batch_id)
    qid_to_year    = meta.get("qid_to_year", {}) if meta else {}
    qid_to_db_body = meta.get("qid_to_db_body_system", {}) if meta else {}

    # ── Load training set for centroid distance computation ───────────────────
    print("\nLoading training data for centroid computation...")
    training_data      = load_training_set(out_dir)
    training_questions = training_data["questions"]
    training_qids      = [q["qid"] for q in training_questions]
    training_embeddings = load_all_embeddings(DB_PATH, training_qids)

    # Load target embeddings for classified questions
    all_result_qids = []
    for result in client.messages.batches.results(args.batch_id):
        all_result_qids.append(result.custom_id)
    target_embeddings = load_all_embeddings(DB_PATH, all_result_qids)

    # ── Process results ────────────────────────────────────────────────────────
    counts = batch.request_counts
    print(f"Processing {counts.succeeded} succeeded results...")

    results       = []
    routing_summary = defaultdict(int)
    errors        = []

    for result in client.messages.batches.results(args.batch_id):
        qid = result.custom_id

        if result.result.type != "succeeded":
            errors.append({"qid": qid, "error": result.result.type})
            continue

        response_text = result.result.message.content[0].text
        classification = parse_classification(response_text)

        if not classification:
            errors.append({"qid": qid, "error": "JSON parse failed", "raw": response_text[:200]})
            continue

        is_valid, err_msg = validate_classification(classification)
        if not is_valid:
            errors.append({"qid": qid, "error": err_msg, "raw": response_text[:200]})
            continue

        body_system  = classification["body_system"]
        confidence   = float(classification.get("confidence", 0.0))
        reasoning    = classification.get("reasoning", "")
        alternative  = classification.get("alternative")

        # Centroid distance cross-check
        target_vec = target_embeddings.get(qid)
        centroid_distance = compute_centroid_distance(
            target_vec, body_system, training_questions, training_embeddings
        )
        centroid_flag = (
            centroid_distance is not None
            and centroid_distance > 0.4
            and confidence >= 0.85
        )

        route = route_classification(confidence, centroid_distance)
        routing_summary[route] += 1

        results.append({
            "qid":                  qid,
            "exam_year":            qid_to_year.get(qid, 0),
            "body_system_current_db": qid_to_db_body.get(qid, ""),
            "body_system_proposed": body_system,
            "confidence":           confidence,
            "reasoning":            reasoning,
            "alternative":          alternative,
            "route":                route,
            "centroid_distance":    centroid_distance,
            "centroid_flag":        centroid_flag,
        })

        print(f"  {qid} → {body_system} (conf={confidence:.2f}, route={route})")

    # ── Write output ───────────────────────────────────────────────────────────
    output = {
        "generated":      datetime.now().isoformat(),
        "batch_id":       args.batch_id,
        "model":          "claude-sonnet-4-6",
        "training_years": [2022, 2023],
        "total_classified": len(results),
        "errors":         len(errors),
        "routing_summary": dict(routing_summary),
        "results":        sorted(results, key=lambda r: (r["exam_year"], r["qid"])),
    }

    out_path = out_dir / "claude_classifications.json"
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")

    # ── Summary ────────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"Results processed: {len(results)}")
    print(f"Errors:            {len(errors)}")
    print(f"Routing:")
    for route, n in sorted(routing_summary.items()):
        pct = 100 * n / len(results) if results else 0
        print(f"  {route:<15} {n:4d}  ({pct:.0f}%)")
    print(f"\nWritten: {out_path}")

    if errors:
        err_path = out_dir / f"batch_errors_{args.batch_id}.json"
        err_path.write_text(json.dumps(errors, indent=2), encoding="utf-8")
        print(f"Errors:  {err_path}")


if __name__ == "__main__":
    main()
