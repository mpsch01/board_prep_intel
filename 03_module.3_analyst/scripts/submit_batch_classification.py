"""
submit_batch_classification.py
===============================
Builds all classification prompts and submits them as a single Anthropic Message
Batch request. 50% cheaper than sequential API calls, no rate limiting concerns.

Workflow:
    1. Run this script  → builds prompts, submits batch, saves batch ID to disk
    2. Wait (minutes to hours, rarely >24h)
    3. Run retrieve_batch_results.py --batch-id <id>  → downloads and processes results

Cost estimate: ~1,000 questions × ~2,500 tokens/question × $0.0015/1K tokens (Sonnet batch)
               ≈ $3–4 for the full unlabeled set

Usage:
    python submit_batch_classification.py
    python submit_batch_classification.py --years 2018 2019 2020 2021
    python submit_batch_classification.py --years 2024 2025
    python submit_batch_classification.py --dry-run   # preview prompt count, no submission

Environment:
    ANTHROPIC_API_KEY: required
"""

import os
import sys
import json
import argparse
import sqlite3
import struct
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Optional

import numpy as np

# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH      = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"
OUTPUT_DIR   = PROJECT_ROOT / "03_module.3_analyst" / "outputs" / "body_system_labels"

TRAINING_YEARS  = [2022, 2023]
DEFAULT_TARGETS = [2018, 2019, 2020, 2021, 2024, 2025]
MODEL           = "claude-sonnet-4-6"
MAX_TOKENS      = 512
K_EXAMPLES      = 5   # dynamic retrieved examples per question

# ── Import shared logic from run_claude_classifier.py ─────────────────────────
# Rather than duplicating, import the key functions directly.
sys.path.insert(0, str(SCRIPT_DIR))
from run_claude_classifier import (
    SYSTEM_PROMPT,
    FINAL_TAXONOMY,
    open_db,
    deserialize_embedding,
    load_training_set,
    cosine_similarity,
    retrieve_few_shot_examples,
    select_canonical_examples,
    build_claude_prompt,
)


def load_questions_to_classify(db_path: Path, target_years: list[int]) -> dict:
    """Load unlabeled questions from DB for the given years."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    placeholders = ",".join("?" * len(target_years))
    rows = conn.execute(f"""
        SELECT qid, exam_year, question_text, choices,
               correct_letter, correct_text, body_system
        FROM questions
        WHERE exam_year IN ({placeholders})
        ORDER BY exam_year, qid
    """, target_years).fetchall()
    conn.close()

    questions = {}
    for row in rows:
        choices_raw = row["choices"]
        if isinstance(choices_raw, str):
            try:
                choices = json.loads(choices_raw)
            except Exception:
                choices = []
        else:
            choices = choices_raw or []

        questions[row["qid"]] = {
            "qid":              row["qid"],
            "exam_year":        row["exam_year"],
            "question_text":    row["question_text"] or "",
            "choices":          choices,
            "correct_letter":   row["correct_letter"] or "",
            "correct_text":     row["correct_text"] or "",
            "body_system_db":   row["body_system"] or "",
        }
    return questions


def load_all_embeddings(db_path: Path, qids: list[str]) -> dict:
    """Load embeddings for a list of QIDs in one DB query."""
    conn = sqlite3.connect(str(db_path))
    placeholders = ",".join("?" * len(qids))
    rows = conn.execute(
        f"SELECT qid, embedding FROM question_full_vec WHERE qid IN ({placeholders})",
        qids
    ).fetchall()
    conn.close()
    return {
        row[0]: deserialize_embedding(row[1])
        for row in rows
        if row[1]
    }


def build_batch_requests(
    questions: dict,
    training_questions: list,
    training_embeddings: dict,
    target_embeddings: dict,
    canonical_examples: dict,
    k: int = K_EXAMPLES,
) -> list[dict]:
    """
    Build all batch request dicts for the Anthropic Message Batches API.

    Each request has:
      custom_id: the QID (used to match results back to questions)
      params:    model, max_tokens, system, messages
    """
    requests = []
    for qid, question in questions.items():
        target_embedding = target_embeddings.get(qid)

        few_shot = retrieve_few_shot_examples(
            qid,
            target_embedding,
            question["question_text"],
            training_questions,
            training_embeddings,
            k=k,
        )

        user_prompt = build_claude_prompt(question, canonical_examples, few_shot)

        requests.append({
            "custom_id": qid,
            "params": {
                "model":      MODEL,
                "max_tokens": MAX_TOKENS,
                "system":     SYSTEM_PROMPT,
                "messages":   [{"role": "user", "content": user_prompt}],
            },
        })

    return requests


def main():
    parser = argparse.ArgumentParser(
        description="Submit body system classification as an Anthropic Message Batch"
    )
    parser.add_argument(
        "--years", type=int, nargs="+", default=DEFAULT_TARGETS,
        help=f"Years to classify (default: {DEFAULT_TARGETS})"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview prompt count and cost estimate without submitting"
    )
    parser.add_argument(
        "--k", type=int, default=K_EXAMPLES,
        help=f"Dynamic few-shot examples per question (default: {K_EXAMPLES})"
    )
    args = parser.parse_args()

    if not args.dry_run:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            print("ERROR: ANTHROPIC_API_KEY not set in environment", file=sys.stderr)
            sys.exit(1)
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── Load training set ──────────────────────────────────────────────────────
    print("[1/5] Loading training set...")
    training_data     = load_training_set(OUTPUT_DIR)
    training_questions = training_data["questions"]
    training_qids      = [q["qid"] for q in training_questions]
    print(f"      {len(training_questions)} training questions")

    # ── Load training embeddings ───────────────────────────────────────────────
    print("[2/5] Loading training embeddings...")
    training_embeddings = load_all_embeddings(DB_PATH, training_qids)
    print(f"      {len(training_embeddings)} embeddings loaded")

    # ── Select canonical examples (one per category) ───────────────────────────
    print("[3/5] Selecting canonical examples...")
    canonical_examples = select_canonical_examples(training_questions, training_embeddings)
    print(f"      {len(canonical_examples)} canonical examples (all 15 categories)")

    # ── Load questions to classify ─────────────────────────────────────────────
    print(f"[4/5] Loading questions for years {args.years}...")
    questions = load_questions_to_classify(DB_PATH, args.years)
    print(f"      {len(questions)} questions to classify")

    by_year = defaultdict(int)
    for q in questions.values():
        by_year[q["exam_year"]] += 1
    for yr in sorted(by_year):
        print(f"        {yr}: {by_year[yr]} questions")

    # Load target embeddings
    target_embeddings = load_all_embeddings(DB_PATH, list(questions.keys()))
    print(f"      {len(target_embeddings)} target embeddings loaded")

    # ── Build batch requests ───────────────────────────────────────────────────
    print("[5/5] Building batch requests...")
    batch_requests = build_batch_requests(
        questions, training_questions, training_embeddings,
        target_embeddings, canonical_examples, k=args.k
    )
    print(f"      {len(batch_requests)} requests built")

    # Estimate tokens and cost
    # Rough estimate: system prompt ~600 tokens + Part A ~1500 tokens + Part B ~750 tokens
    # + target question ~200 tokens + output ~100 tokens = ~3150 tokens/question
    est_tokens_per_q = 3150
    est_total_tokens = len(batch_requests) * est_tokens_per_q
    est_cost = (est_total_tokens / 1_000_000) * 1.50   # Sonnet batch: $1.50/M input tokens
    print(f"\n  Estimated tokens:  {est_total_tokens:,}")
    print(f"  Estimated cost:    ~${est_cost:.2f} (Sonnet batch rate, input only)")

    if args.dry_run:
        print("\n[DRY RUN] No batch submitted. Remove --dry-run to submit.")
        return

    # ── Submit batch ───────────────────────────────────────────────────────────
    print(f"\n[→] Submitting batch of {len(batch_requests)} requests to Anthropic...")
    batch = client.messages.batches.create(requests=batch_requests)

    batch_id = batch.id
    status   = batch.processing_status
    print(f"  ✓ Batch submitted!")
    print(f"  Batch ID:  {batch_id}")
    print(f"  Status:    {status}")

    # Save batch metadata to disk
    meta = {
        "batch_id":       batch_id,
        "submitted_at":   datetime.now().isoformat(),
        "model":          MODEL,
        "target_years":   args.years,
        "total_requests": len(batch_requests),
        "status":         status,
        "qid_to_year":    {qid: q["exam_year"] for qid, q in questions.items()},
        "qid_to_db_body_system": {
            qid: q["body_system_db"] for qid, q in questions.items()
        },
    }
    meta_path = OUTPUT_DIR / f"batch_meta_{batch_id}.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"  Metadata:  {meta_path}")

    print(f"""
Next step — check status and retrieve results when ready:
    python retrieve_batch_results.py --batch-id {batch_id}

Or check status only:
    python retrieve_batch_results.py --batch-id {batch_id} --status-only
""")


if __name__ == "__main__":
    main()
