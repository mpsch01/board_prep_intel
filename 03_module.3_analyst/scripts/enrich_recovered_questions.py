"""
enrich_recovered_questions.py
------------------------------
Classifies body_system + blueprint for the 10 recovered questions using
OpenAI text-embedding-3-small + KNN majority vote against question_full_vec.

Approach:
  1. Embed each new question (stem + correct answer only, since body_system
     and blueprint are unknown) using OpenAI text-embedding-3-small.
  2. Find K=7 nearest neighbors in question_full_vec (the existing 1,629
     already-classified questions).
  3. Majority vote on body_system and blueprint from neighbors.
  4. Write results + body_system_merged to DB.

This is consistent with how the body-system-qc SVM pipeline works —
same embedding model, same vector space.

USAGE:
    py 03_module.3_analyst/scripts/enrich_recovered_questions.py
    py 03_module.3_analyst/scripts/enrich_recovered_questions.py --dry-run

COST: ~$0.0001 (10 short embeddings at $0.02/M tokens)

LOCKED CONVENTIONS:
    - body_system: 15 post-2024 ABFM canonical categories
    - blueprint:   5 ABFM blueprint categories
    - body_system_merged: same value as body_system (forward mapping)
    - Dynamic paths: SCRIPT_DIR / PROJECT_ROOT
    - Embedding model: text-embedding-3-small (1536d) — same as question_full_vec
"""

import json
import os
import sqlite3
import struct
import sys
from collections import Counter
from pathlib import Path

import openai

# ── Paths ────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH      = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"

# ── Config ────────────────────────────────────────────────────────────────────
TARGET_QIDS = [
    "QID-2020-0134", "QID-2020-0138",
    "QID-2021-0050", "QID-2021-0168",
    "QID-2022-0175",
    "QID-2023-0004",
    "QID-2024-0017", "QID-2024-0117", "QID-2024-0140", "QID-2024-0187",
]

EMBED_MODEL = "text-embedding-3-small"
EMBED_DIM   = 1536
K_NEIGHBORS = 7   # majority vote window


def blob_to_vec(blob: bytes) -> list[float]:
    """Deserialize BLOB → list of floats (little-endian float32)."""
    n = len(blob) // 4
    return list(struct.unpack(f"<{n}f", blob))


def cosine_sim(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = sum(x * x for x in a) ** 0.5
    mag_b = sum(x * x for x in b) ** 0.5
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def build_embed_text(question_text: str, correct_text: str) -> str:
    """
    Build embedding text using only stem + answer — no body_system/blueprint
    since those are what we're trying to infer. Matches compute_embeddings.py
    format (without the enrichment fields).
    """
    parts = []
    if question_text:
        parts.append(question_text[:600])
    if correct_text:
        parts.append(f"Answer: {correct_text}")
    return " | ".join(parts)


def get_embedding(client: openai.OpenAI, text: str) -> list[float]:
    """Get OpenAI embedding for a single text string."""
    resp = client.embeddings.create(model=EMBED_MODEL, input=[text])
    return resp.data[0].embedding


def knn_classify(
    query_vec: list[float],
    corpus: list[tuple],  # list of (qid, body_system, blueprint, embedding_blob)
    k: int,
) -> tuple[str, str, list[tuple]]:
    """
    Find K nearest neighbors by cosine similarity.
    Returns (body_system, blueprint, top_k_neighbors).
    """
    scored = []
    for qid, bs, bp, blob in corpus:
        if not blob:
            continue
        neighbor_vec = blob_to_vec(blob)
        sim = cosine_sim(query_vec, neighbor_vec)
        scored.append((sim, qid, bs, bp))

    scored.sort(key=lambda x: x[0], reverse=True)
    top_k = scored[:k]

    # Majority vote
    bs_votes = Counter(x[2] for x in top_k if x[2])
    bp_votes = Counter(x[3] for x in top_k if x[3])

    body_system = bs_votes.most_common(1)[0][0] if bs_votes else "Nonspecific"
    blueprint   = bp_votes.most_common(1)[0][0] if bp_votes else "Acute Care and Diagnosis"

    return body_system, blueprint, top_k


def main():
    dry_run = "--dry-run" in sys.argv

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set in environment")
        sys.exit(1)

    client = openai.OpenAI(api_key=api_key)
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row

    print("=" * 65)
    print("Classifying 10 recovered questions via OpenAI KNN")
    print(f"Model: {EMBED_MODEL} | K={K_NEIGHBORS} neighbors")
    print("=" * 65)

    # Load full question_full_vec corpus (existing classified questions)
    print("\nLoading question_full_vec corpus...")
    corpus = db.execute("""
        SELECT v.qid, q.body_system, q.blueprint, v.embedding
        FROM question_full_vec v
        JOIN questions q ON v.qid = q.qid
        WHERE q.body_system IS NOT NULL AND q.blueprint IS NOT NULL
          AND q.qid NOT IN ({})
    """.format(",".join(f"'{q}'" for q in TARGET_QIDS))).fetchall()

    corpus = [(r["qid"], r["body_system"], r["blueprint"], r["embedding"])
              for r in corpus]
    print(f"  Corpus size: {len(corpus)} classified questions")

    updates = []

    for qid in TARGET_QIDS:
        row = db.execute(
            "SELECT qid, question_text, correct_text, correct_letter, body_system, blueprint "
            "FROM questions WHERE qid = ?", (qid,)
        ).fetchone()

        if not row:
            print(f"\n  {qid}: NOT FOUND in DB — skipping")
            continue

        if row["body_system"] and row["blueprint"]:
            print(f"\n  {qid}: already classified (bs={row['body_system'][:30]}) — skipping")
            continue

        print(f"\n  {qid} — embedding...")
        embed_text = build_embed_text(row["question_text"], row["correct_text"])
        query_vec  = get_embedding(client, embed_text)

        bs, bp, top_k = knn_classify(query_vec, corpus, K_NEIGHBORS)

        print(f"    body_system = {bs}")
        print(f"    blueprint   = {bp}")
        print(f"    Top-3 neighbors:")
        for sim, nqid, nbs, nbp in top_k[:3]:
            print(f"      {nqid} (sim={sim:.3f}) → {nbs} | {nbp}")

        updates.append((bs, bp, qid))

    print(f"\n\nClassifications ready: {len(updates)}")

    if dry_run:
        print("DRY RUN — no DB writes")
        db.close()
        return

    if updates:
        for bs, bp, qid in updates:
            db.execute(
                "UPDATE questions SET body_system=?, blueprint=?, body_system_merged=? WHERE qid=?",
                (bs, bp, bs, qid)
            )
        db.commit()
        print(f"Applied {len(updates)} updates to DB")

    # Verification
    print("\nVerification:")
    for qid in TARGET_QIDS:
        r = db.execute(
            "SELECT qid, body_system, blueprint FROM questions WHERE qid=?", (qid,)
        ).fetchone()
        if r:
            print(f"  {r['qid']}: {(r['body_system'] or 'NULL')[:28]} | {(r['blueprint'] or 'NULL')[:32]}")

    db.close()
    print("\nDone. Next step: preprocess_concept_tags.py")


if __name__ == "__main__":
    main()
