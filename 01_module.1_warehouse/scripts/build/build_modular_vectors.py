"""
build_modular_vectors.py — Modular BLOB Vector Tables
==================================================================
Builds plain BLOB format vector tables for blueprint labels, body system labels,
and question concept tags. These tables are accessible anywhere (no sqlite-vec
extension required).

Tables:
    blueprint_label_vec       — 5 rows, one embedding per blueprint category
    bodysystem_label_vec      — 5 rows, one embedding per body system
    question_concepttag_vec   — one row per ITE + AAFP question, concept_tags embedding

Usage:
    python build_modular_vectors.py                    # build everything
    python build_modular_vectors.py --labels-only      # just blueprint + body_system labels
    python build_modular_vectors.py --concept-tags-only # just question concept tags
    python build_modular_vectors.py --new-only         # skip questions already embedded
    python build_modular_vectors.py --dry-run          # show what would be embedded, no API calls
    python build_modular_vectors.py --db /path/to/db   # custom DB path

Requires:
    pip install openai
    Environment variable: OPENAI_API_KEY

Cost estimate: ~$0.04 for 10 labels + ~$0.08 for 2,850 questions (ITE + AAFP)
             Total: ~$0.12 for full run
Runtime: ~90 seconds full, ~60 seconds concept-tags-only
"""

import sqlite3
import json
import sys
import os
import time
import argparse
import struct
from pathlib import Path

# ---------------------------------------------------------------------------
# CONFIG — tune these knobs
# ---------------------------------------------------------------------------
SCRIPT_DIR    = Path(__file__).resolve().parent
PROJECT_ROOT  = SCRIPT_DIR.parent.parent.parent          # build/ -> scripts/ -> M1/ -> PROJECT_ROOT
DB_PATH       = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"
EMBED_MODEL   = "text-embedding-3-small"   # 1536 dimensions, $0.02/M tokens
EMBED_DIM     = 1536
BATCH_SIZE    = 100                        # OpenAI supports up to 2048 per call
MAX_TOKENS    = 8191                       # model context limit per input

# Canonical blueprint labels (5)
BLUEPRINT_LABELS = [
    "Acute Care and Diagnosis",
    "Chronic Care Management",
    "Emergent and Urgent Care",
    "Foundations of Care",
    "Preventive Care",
]

# Canonical body system labels (5)
BODYSYSTEM_LABELS = [
    "Cardiovascular",
    "Injuries/Musculoskeletal",
    "Psychiatric/Behavioral",
    "Respiratory",
    "Sexual and Reproductive",
]

# ---------------------------------------------------------------------------
# Text builders — deterministic representations for embedding
# ---------------------------------------------------------------------------

def build_concepttag_text(tags_raw: str) -> str:
    """
    Build a text representation of concept tags for embedding.
    Extracts concept_summary, diagnoses, drugs, and guidelines.
    Returns empty string if tags_raw is NULL or empty.
    """
    if not tags_raw or not tags_raw.strip():
        return ""

    try:
        tags = json.loads(tags_raw)
        parts = []

        # Concept summary (most valuable)
        summary = tags.get("concept_summary", "")
        if summary:
            parts.append(summary)

        # Diagnoses
        diagnoses = tags.get("diagnoses", [])
        if diagnoses:
            parts.append(f"Diagnoses: {', '.join(str(d) for d in diagnoses)}")

        # Drugs
        drugs = tags.get("drugs", [])
        if drugs:
            parts.append(f"Drugs: {', '.join(str(d) for d in drugs)}")

        # Guidelines (cap at 5)
        guidelines = tags.get("guidelines", [])
        if guidelines:
            parts.append(f"Guidelines: {', '.join(str(g) for g in guidelines[:5])}")

        text = " | ".join(parts)

        # Truncate to stay within token limits (~4 chars per token)
        max_chars = MAX_TOKENS * 3  # conservative estimate
        if len(text) > max_chars:
            text = text[:max_chars]

        return text
    except (json.JSONDecodeError, TypeError):
        return ""


# ---------------------------------------------------------------------------
# Schema creation
# ---------------------------------------------------------------------------

def create_schema(conn):
    """Create all three modular vector tables (idempotent)."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS blueprint_label_vec (
            blueprint TEXT PRIMARY KEY,
            embedding BLOB NOT NULL,
            model     TEXT,
            built_at  TEXT DEFAULT (datetime('now'))
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS bodysystem_label_vec (
            body_system TEXT PRIMARY KEY,
            embedding   BLOB NOT NULL,
            model       TEXT,
            built_at    TEXT DEFAULT (datetime('now'))
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS question_concepttag_vec (
            qid         TEXT PRIMARY KEY,
            source_bank TEXT NOT NULL,  -- 'ite' or 'aafp'
            embedding   BLOB NOT NULL,
            model       TEXT,
            built_at    TEXT DEFAULT (datetime('now'))
        )
    """)

    conn.commit()


# ---------------------------------------------------------------------------
# Embedding computation
# ---------------------------------------------------------------------------

def get_embeddings(client, texts: list[str]) -> list[list[float]]:
    """Call OpenAI embeddings API for a batch of texts."""
    resp = client.embeddings.create(model=EMBED_MODEL, input=texts)
    return [item.embedding for item in resp.data]


def embed_labels(conn, client, dry_run=False):
    """Embed blueprint and body system labels."""
    all_labels = [("blueprint", BLUEPRINT_LABELS), ("bodysystem", BODYSYSTEM_LABELS)]
    total_embedded = 0
    total_tokens = 0

    for label_type, labels in all_labels:
        print(f"\n{'='*60}")
        print(f"{label_type.upper()} LABELS: {len(labels)} to embed")
        print(f"{'='*60}")

        if dry_run:
            for label in labels[:3]:
                print(f"  {label}")
            print(f"  ... ({len(labels)} total)")
            continue

        # Embed all labels in one batch
        embeddings = get_embeddings(client, labels)
        total_tokens += sum(len(label.split()) * 1.3 for label in labels)

        if label_type == "blueprint":
            for label, emb in zip(labels, embeddings):
                blob = struct.pack(f"{len(emb)}f", *emb)
                conn.execute(
                    "INSERT OR REPLACE INTO blueprint_label_vec(blueprint, embedding, model) VALUES (?, ?, ?)",
                    (label, blob, EMBED_MODEL)
                )
            print(f"  Embedded {len(labels)} blueprint labels")
        else:  # bodysystem
            for label, emb in zip(labels, embeddings):
                blob = struct.pack(f"{len(emb)}f", *emb)
                conn.execute(
                    "INSERT OR REPLACE INTO bodysystem_label_vec(body_system, embedding, model) VALUES (?, ?, ?)",
                    (label, blob, EMBED_MODEL)
                )
            print(f"  Embedded {len(labels)} body system labels")

        total_embedded += len(labels)

    conn.commit()
    return total_embedded, int(total_tokens)


def embed_concept_tags(conn, client, dry_run=False, new_only=False):
    """Embed concept_tags for all ITE and AAFP questions."""
    print(f"\n{'='*60}")
    print(f"QUESTION CONCEPT TAGS")
    print(f"{'='*60}")

    # Fetch ITE questions
    if new_only:
        ite_questions = conn.execute("""
            SELECT q.qid, q.concept_tags
            FROM questions q
            LEFT JOIN question_concepttag_vec v ON q.qid = v.qid
            WHERE v.qid IS NULL
            ORDER BY q.qid
        """).fetchall()
        print(f"  [new-only mode] {len(ite_questions)} ITE questions without embeddings")
    else:
        ite_questions = conn.execute("""
            SELECT qid, concept_tags
            FROM questions
            ORDER BY qid
        """).fetchall()

    # Fetch AAFP questions
    if new_only:
        aafp_questions = conn.execute("""
            SELECT q.aafp_qid, q.concept_tags
            FROM aafp_questions q
            LEFT JOIN question_concepttag_vec v ON q.aafp_qid = v.qid
            WHERE v.qid IS NULL
            ORDER BY q.aafp_qid
        """).fetchall()
        print(f"  [new-only mode] {len(aafp_questions)} AAFP questions without embeddings")
    else:
        aafp_questions = conn.execute("""
            SELECT aafp_qid, concept_tags
            FROM aafp_questions
            ORDER BY aafp_qid
        """).fetchall()

    total_questions = len(ite_questions) + len(aafp_questions)
    print(f"  Total: {total_questions} questions to embed (ITE: {len(ite_questions)}, AAFP: {len(aafp_questions)})")

    if dry_run:
        count = 0
        for q in ite_questions[:3]:
            text = build_concepttag_text(q[1] or "")
            if text:
                print(f"    {q[0]} (ITE): {text[:100]}...")
                count += 1
        for q in aafp_questions[:3]:
            text = build_concepttag_text(q[1] or "")
            if text:
                print(f"    {q[0]} (AAFP): {text[:100]}...")
                count += 1
        if count < 6:
            remaining = total_questions - count
            print(f"    ... and {remaining} more")
        return 0, 0

    # Filter out questions with empty concept_tags (no embedding generated)
    ite_with_tags = [q for q in ite_questions if build_concepttag_text(q[1] or "")]
    aafp_with_tags = [q for q in aafp_questions if build_concepttag_text(q[1] or "")]

    questions_to_embed = ite_with_tags + aafp_with_tags
    skipped_empty = total_questions - len(questions_to_embed)

    if skipped_empty > 0:
        print(f"  Skipping {skipped_empty} questions with empty concept_tags")

    print(f"  Processing {len(questions_to_embed)} questions with content...")

    total_tokens = 0
    embedded = 0

    # Process in batches
    for i in range(0, len(ite_with_tags), BATCH_SIZE):
        batch = ite_with_tags[i:i+BATCH_SIZE]
        texts = [build_concepttag_text(q[1] or "") for q in batch]
        qids  = [q[0] for q in batch]

        embeddings = get_embeddings(client, texts)
        total_tokens += sum(len(t.split()) * 1.3 for t in texts)

        for qid, emb in zip(qids, embeddings):
            blob = struct.pack(f"{len(emb)}f", *emb)
            conn.execute(
                "INSERT OR REPLACE INTO question_concepttag_vec(qid, source_bank, embedding, model) VALUES (?, ?, ?, ?)",
                (qid, 'ite', blob, EMBED_MODEL)
            )

        embedded += len(batch)
        batch_num = (i // BATCH_SIZE) + 1
        print(f"    Batch {batch_num}: embedded {len(batch)} ITE questions ({embedded}/{len(ite_with_tags)})")

    # Process AAFP in batches
    for i in range(0, len(aafp_with_tags), BATCH_SIZE):
        batch = aafp_with_tags[i:i+BATCH_SIZE]
        texts = [build_concepttag_text(q[1] or "") for q in batch]
        qids  = [q[0] for q in batch]

        embeddings = get_embeddings(client, texts)
        total_tokens += sum(len(t.split()) * 1.3 for t in texts)

        for qid, emb in zip(qids, embeddings):
            blob = struct.pack(f"{len(emb)}f", *emb)
            conn.execute(
                "INSERT OR REPLACE INTO question_concepttag_vec(qid, source_bank, embedding, model) VALUES (?, ?, ?, ?)",
                (qid, 'aafp', blob, EMBED_MODEL)
            )

        embedded += len(batch)
        batch_num = (len(ite_with_tags) // BATCH_SIZE) + ((i // BATCH_SIZE) + 1)
        print(f"    Batch {batch_num}: embedded {len(batch)} AAFP questions ({embedded}/{len(questions_to_embed)})")

    conn.commit()
    return embedded, int(total_tokens)


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def verify(conn):
    """Quick sanity checks after embedding."""
    print(f"\n{'='*60}")
    print("VERIFICATION")
    print(f"{'='*60}")

    blueprint_count = conn.execute("SELECT COUNT(*) FROM blueprint_label_vec").fetchone()[0]
    bodysystem_count = conn.execute("SELECT COUNT(*) FROM bodysystem_label_vec").fetchone()[0]
    concepttag_count = conn.execute("SELECT COUNT(*) FROM question_concepttag_vec").fetchone()[0]

    ite_total = conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
    aafp_total = conn.execute("SELECT COUNT(*) FROM aafp_questions").fetchone()[0]
    total_questions = ite_total + aafp_total

    print(f"  blueprint_label_vec:      {blueprint_count}/{len(BLUEPRINT_LABELS)} labels")
    print(f"  bodysystem_label_vec:     {bodysystem_count}/{len(BODYSYSTEM_LABELS)} labels")
    print(f"  question_concepttag_vec:  {concepttag_count}/{total_questions} questions")

    # Breakdown by source bank
    ite_count = conn.execute(
        "SELECT COUNT(*) FROM question_concepttag_vec WHERE source_bank = 'ite'"
    ).fetchone()[0]
    aafp_count = conn.execute(
        "SELECT COUNT(*) FROM question_concepttag_vec WHERE source_bank = 'aafp'"
    ).fetchone()[0]

    print(f"      ITE:  {ite_count}/{ite_total}")
    print(f"      AAFP: {aafp_count}/{aafp_total}")

    # Coverage warnings
    if blueprint_count < len(BLUEPRINT_LABELS):
        print(f"\n  WARNING: {len(BLUEPRINT_LABELS) - blueprint_count} blueprint labels missing embeddings")
    if bodysystem_count < len(BODYSYSTEM_LABELS):
        print(f"\n  WARNING: {len(BODYSYSTEM_LABELS) - bodysystem_count} body system labels missing embeddings")
    if concepttag_count < total_questions:
        print(f"\n  WARNING: {total_questions - concepttag_count} questions missing embeddings")

    if (blueprint_count == len(BLUEPRINT_LABELS) and
        bodysystem_count == len(BODYSYSTEM_LABELS) and
        concepttag_count == total_questions):
        print(f"\n  ALL CLEAR — 100% embedding coverage across all modular tables")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Build modular BLOB vector tables for ITE Intelligence DB"
    )
    parser.add_argument(
        "--db",
        type=str,
        default=str(DB_PATH),
        help="Path to SQLite DB"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be embedded, no API calls"
    )
    parser.add_argument(
        "--labels-only",
        action="store_true",
        help="Only embed blueprint and body system labels"
    )
    parser.add_argument(
        "--concept-tags-only",
        action="store_true",
        help="Only embed concept tags for questions"
    )
    parser.add_argument(
        "--new-only",
        action="store_true",
        help="Skip questions already in question_concepttag_vec (incremental update)"
    )
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"ERROR: Database not found at {db_path}")
        sys.exit(1)

    print(f"ITE Intelligence — Modular Vector Pipeline")
    print(f"{'='*60}")
    print(f"Database:         {db_path}")
    print(f"Model:            {EMBED_MODEL} ({EMBED_DIM} dimensions)")
    print(f"Batch size:       {BATCH_SIZE} items per API call")
    print(f"Dry run:          {args.dry_run}")
    print(f"Labels only:      {args.labels_only}")
    print(f"Concept tags only:{args.concept_tags_only}")
    print(f"New only:         {args.new_only}")
    print(f"{'='*60}")

    # Connect to DB (no sqlite-vec needed)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # Create schema
    create_schema(conn)

    # Initialize OpenAI client
    client = None
    if not args.dry_run:
        from openai import OpenAI
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            print("ERROR: OPENAI_API_KEY not set in environment.")
            sys.exit(1)
        client = OpenAI(api_key=api_key)
        print(f"OpenAI:           connected")

    start = time.time()
    total_embedded = 0
    total_tokens = 0

    # Determine which phases to run
    labels_only = args.labels_only
    concepttags_only = args.concept_tags_only

    # Embed labels (unless concept-tags-only)
    if not concepttags_only:
        n, t = embed_labels(conn, client, dry_run=args.dry_run)
        total_embedded += n
        total_tokens += t

    # Embed concept tags (unless labels-only)
    if not labels_only:
        n, t = embed_concept_tags(conn, client, dry_run=args.dry_run, new_only=args.new_only)
        total_embedded += n
        total_tokens += t

    elapsed = time.time() - start

    if not args.dry_run:
        verify(conn)

    # Summary
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"  Items embedded: {total_embedded}")
    print(f"  Est. tokens:    {total_tokens:,}")
    est_cost = total_tokens * 0.02 / 1_000_000
    print(f"  Est. cost:      ${est_cost:.4f}")
    print(f"  Elapsed:        {elapsed:.1f}s")

    conn.close()
    print(f"\nDone.")


if __name__ == "__main__":
    main()
