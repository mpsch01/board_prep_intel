"""
submit_batch_aafp.py
=====================
Submits all 1,221 AAFP BRQ questions for body_system classification
using the same Claude + SVM pipeline as the ITE classifier.

Training data: ITE 2022-2023 ground truth (body_system_training_set.json)
Target:        aafp_questions table / aafp_question_full_vec embeddings
Output:        aafp_classifications.json (same format as claude_classifications.json)

Usage:
    python submit_batch_aafp.py
    python submit_batch_aafp.py --dry-run   # preview without submitting

Then retrieve with:
    python retrieve_batch_aafp_results.py --batch-id msgbatch_XXXX --wait
"""

import os
import sys
import json
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Optional

import numpy as np

SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH      = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"
OUTPUT_DIR   = PROJECT_ROOT / "03_module.3_analyst" / "outputs" / "body_system_labels"

MODEL      = "claude-sonnet-4-6"
MAX_TOKENS = 512
K_EXAMPLES = 5

sys.path.insert(0, str(SCRIPT_DIR))
from run_claude_classifier import (
    SYSTEM_PROMPT, FINAL_TAXONOMY,
    deserialize_embedding, load_training_set, cosine_similarity,
    retrieve_few_shot_examples, select_canonical_examples, build_claude_prompt,
)
from submit_batch_classification import load_all_embeddings


def load_aafp_questions(db_path: Path) -> dict:
    """Load all AAFP questions from aafp_questions table."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    rows = conn.execute("""
        SELECT aafp_qid, stem, choices, correct_letter, correct_text, body_system
        FROM aafp_questions
        ORDER BY aafp_qid
    """).fetchall()
    conn.close()

    questions = {}
    for row in rows:
        qid = row["aafp_qid"]
        # Parse choices JSON (same format as ITE: [{"letter": "A", "text": "..."}, ...])
        choices_raw = row["choices"] or "[]"
        try:
            import json as _json
            choices = _json.loads(choices_raw) if isinstance(choices_raw, str) else choices_raw
        except Exception:
            choices = []
        questions[qid] = {
            "qid":              qid,
            "question_text":    row["stem"] or "",   # map stem -> question_text for prompt builder
            "choices":          choices,
            "correct_letter":   row["correct_letter"] or "",
            "correct_text":     row["correct_text"] or "",
            "body_system_db":   row["body_system"] or "",
        }
    return questions


def load_aafp_embeddings(db_path: Path, qids: list[str]) -> dict:
    """Load embeddings from aafp_question_full_vec table."""
    conn = sqlite3.connect(str(db_path))
    placeholders = ",".join("?" * len(qids))
    rows = conn.execute(
        f"SELECT aafp_qid, embedding FROM aafp_question_full_vec "
        f"WHERE aafp_qid IN ({placeholders})",
        qids
    ).fetchall()
    conn.close()
    return {
        row[0]: deserialize_embedding(row[1])
        for row in rows if row[1]
    }


def main():
    parser = argparse.ArgumentParser(
        description="Submit AAFP body system classification batch"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview without submitting")
    parser.add_argument("--k", type=int, default=K_EXAMPLES)
    args = parser.parse_args()

    if not args.dry_run:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            print("ERROR: ANTHROPIC_API_KEY not set", file=sys.stderr)
            sys.exit(1)
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load ITE training set (same ground truth for both banks)
    print("[1/5] Loading ITE training set (2022-2023 ground truth)...")
    training_data      = load_training_set(OUTPUT_DIR)
    training_questions = training_data["questions"]
    training_qids      = [q["qid"] for q in training_questions]
    print(f"      {len(training_questions)} training questions")

    print("[2/5] Loading ITE training embeddings...")
    training_embeddings = load_all_embeddings(DB_PATH, training_qids)
    print(f"      {len(training_embeddings)} embeddings loaded")

    print("[3/5] Selecting canonical examples...")
    canonical_examples = select_canonical_examples(training_questions, training_embeddings)
    print(f"      {len(canonical_examples)} canonical examples (all 15 categories)")

    print("[4/5] Loading AAFP questions...")
    questions = load_aafp_questions(DB_PATH)
    print(f"      {len(questions)} AAFP questions")

    # Distribution of current body_system_method
    methods = defaultdict(int)
    for q in questions.values():
        methods[q.get("body_system_db", "unknown")] = methods.get(q.get("body_system_db", "unknown"), 0) + 1

    print("\n[5/5] Loading AAFP embeddings...")
    aafp_qids = list(questions.keys())
    aafp_embeddings = load_aafp_embeddings(DB_PATH, aafp_qids)
    print(f"      {len(aafp_embeddings)} embeddings loaded")

    # Build batch requests
    print(f"\nBuilding {len(questions)} batch requests...")
    batch_requests = []
    missing_embed = 0

    for qid, question in questions.items():
        target_embedding = aafp_embeddings.get(qid)
        if target_embedding is None:
            missing_embed += 1

        few_shot = retrieve_few_shot_examples(
            qid, target_embedding,
            question["question_text"],
            training_questions, training_embeddings,
            k=args.k,
        )

        user_prompt = build_claude_prompt(question, canonical_examples, few_shot)

        batch_requests.append({
            "custom_id": qid,
            "params": {
                "model":      MODEL,
                "max_tokens": MAX_TOKENS,
                "system":     SYSTEM_PROMPT,
                "messages":   [{"role": "user", "content": user_prompt}],
            },
        })

    print(f"  {len(batch_requests)} requests built ({missing_embed} without embeddings)")

    # Cost estimate
    est_tokens  = len(batch_requests) * 3150
    est_cost    = (est_tokens / 1_000_000) * 1.50
    print(f"  Estimated cost: ~${est_cost:.2f} (Sonnet batch rate)")

    if args.dry_run:
        print("\n[DRY RUN] No batch submitted.")
        print(f"Sample prompt (first question):")
        print(batch_requests[0]["params"]["messages"][0]["content"][:600])
        return

    print(f"\nSubmitting batch of {len(batch_requests)} AAFP questions...")
    batch = client.messages.batches.create(requests=batch_requests)

    batch_id = batch.id
    print(f"  Batch ID:  {batch_id}")
    print(f"  Status:    {batch.processing_status}")

    # Save metadata
    meta = {
        "batch_id":      batch_id,
        "submitted_at":  datetime.now().isoformat(),
        "model":         MODEL,
        "bank":          "aafp",
        "total_requests": len(batch_requests),
        "status":        batch.processing_status,
        "qid_to_db_body_system": {
            qid: q["body_system_db"] for qid, q in questions.items()
        },
    }
    meta_path = OUTPUT_DIR / f"batch_meta_{batch_id}.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"  Metadata:  {meta_path}")

    print(f"""
Retrieve results when ready:
    python retrieve_batch_results.py --batch-id {batch_id} --wait
""")


if __name__ == "__main__":
    main()
