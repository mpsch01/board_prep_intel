"""
build_icd10_embeddings.py — ICD-10 Vector Embedding Layer

Embeds all unique ICD-10 code descriptions using OpenAI text-embedding-3-small.
Then derives composite ICD-10 feature vectors for articles and questions (ITE + AAFP)
by computing a weighted average of each entity's tagged code vectors.

New tables created:
  icd10_vec          — one embedding per unique ICD-10 code (API cost here)
  article_icd10_vec  — one aggregate embedding per article (derived, zero API cost)
  question_icd10_vec — one aggregate embedding per question, ITE + AAFP (derived, zero API cost)

Weight scheme for averaging:
  primary   = 3
  secondary = 2
  related   = 1

Usage:
  python build_icd10_embeddings.py --all         # Full run: embed + derive + report
  python build_icd10_embeddings.py --embed        # Phase 1 only: call OpenAI, build icd10_vec
  python build_icd10_embeddings.py --derive       # Phase 2 only: derive article/question vectors
  python build_icd10_embeddings.py --report       # Phase 3 only: coverage stats
  python build_icd10_embeddings.py --dry-run      # Preview counts, no writes, no API calls

Requirements:
  pip install openai numpy
  OPENAI_API_KEY must be set as an environment variable.
"""

import argparse
import os
import sqlite3
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

# ── Paths ────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH      = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"

# ── Embedding config ─────────────────────────────────────────────────────────
EMBED_MODEL = "text-embedding-3-small"
EMBED_DIM   = 1536
BATCH_SIZE  = 100   # safe batch size for rate limits

# Relevance weights: primary > secondary > related
RELEVANCE_WEIGHTS = {"primary": 3, "secondary": 2, "related": 1}


# ── Vector helpers ───────────────────────────────────────────────────────────

def vec_to_blob(vec: np.ndarray) -> bytes:
    return vec.astype(np.float32).tobytes()

def blob_to_vec(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32).copy()

def weighted_avg(vecs_weights: list) -> np.ndarray:
    """Weighted average of (np.ndarray, weight) pairs."""
    total = sum(w for _, w in vecs_weights)
    if total == 0:
        return np.zeros(EMBED_DIM, dtype=np.float32)
    result = np.zeros(EMBED_DIM, dtype=np.float32)
    for vec, w in vecs_weights:
        result += vec * w
    return result / total


# ── Phase 1: Embed ICD-10 codes ──────────────────────────────────────────────

def phase_embed(conn, client, dry_run=False):
    """
    Pull all unique ICD-10 codes from article_icd10 and aafp_question_icd10.
    Embed their descriptions via OpenAI. Store in icd10_vec.
    Skips codes already present (idempotent — safe to re-run).
    """
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS icd10_vec (
            icd10_code  TEXT PRIMARY KEY,
            icd10_desc  TEXT,
            embedding   BLOB NOT NULL,
            model       TEXT,
            dim         INTEGER
        )
    """)

    # Collect all unique (code, desc) from both sources
    c.execute("""
        SELECT icd10_code, icd10_desc FROM article_icd10
        WHERE icd10_code IS NOT NULL
        UNION
        SELECT icd10_code, icd10_desc FROM aafp_question_icd10
        WHERE icd10_code IS NOT NULL
    """)
    all_codes = {}
    for code, desc in c.fetchall():
        if code not in all_codes:
            all_codes[code] = desc or code  # fallback to code if desc is NULL

    # Identify what's already embedded
    c.execute("SELECT icd10_code FROM icd10_vec")
    already_done = {row[0] for row in c.fetchall()}
    to_embed = [(code, desc) for code, desc in all_codes.items() if code not in already_done]

    print(f"\n  Unique ICD-10 codes in DB:  {len(all_codes)}")
    print(f"  Already embedded:           {len(already_done)}")
    print(f"  To embed this run:          {len(to_embed)}")

    if dry_run:
        print(f"\n  [DRY RUN] Would call OpenAI for {len(to_embed)} codes")
        return

    if not to_embed:
        print("  Nothing to do — all codes already embedded.")
        return

    embedded = 0
    skipped  = 0

    for i in range(0, len(to_embed), BATCH_SIZE):
        batch = to_embed[i:i + BATCH_SIZE]
        texts = [desc for _, desc in batch]

        try:
            response = client.embeddings.create(model=EMBED_MODEL, input=texts)
            for j, item in enumerate(response.data):
                code = batch[j][0]
                desc = batch[j][1]
                vec  = np.array(item.embedding, dtype=np.float32)
                c.execute("""
                    INSERT OR REPLACE INTO icd10_vec
                        (icd10_code, icd10_desc, embedding, model, dim)
                    VALUES (?, ?, ?, ?, ?)
                """, (code, desc, vec_to_blob(vec), EMBED_MODEL, EMBED_DIM))
                embedded += 1

            conn.commit()
            end = min(i + BATCH_SIZE, len(to_embed))
            print(f"  Embedded codes {i + 1}–{end} of {len(to_embed)} ✓")

        except Exception as e:
            print(f"  ERROR on batch starting at {i}: {e}")
            skipped += len(batch)

        if i + BATCH_SIZE < len(to_embed):
            time.sleep(0.5)  # brief pause between batches

    total = len(already_done) + embedded
    print(f"\n  Phase 1 complete — {embedded} new embeddings, {skipped} errors")
    print(f"  Total icd10_vec rows: {total}")


# ── Phase 2: Derive article and question vectors ──────────────────────────────

def phase_derive(conn, dry_run=False):
    """
    Compute weighted-average ICD-10 feature vectors for:
      - Articles  (via article_icd10)
      - AAFP qs   (via aafp_question_icd10, direct)
      - ITE qs    (via qid_art_xref → article_icd10)
    Zero API calls — pure math on icd10_vec.
    """
    c = conn.cursor()

    # Load all code vectors into memory
    c.execute("SELECT icd10_code, embedding FROM icd10_vec")
    icd10_vecs = {row[0]: blob_to_vec(row[1]) for row in c.fetchall()}
    print(f"\n  icd10_vec loaded: {len(icd10_vecs)} code vectors")

    if not icd10_vecs:
        print("  ERROR: icd10_vec is empty — run --embed first")
        sys.exit(1)

    # ── article_icd10_vec ─────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS article_icd10_vec (
            article_id  TEXT PRIMARY KEY,
            embedding   BLOB NOT NULL,
            code_count  INTEGER,
            model       TEXT
        )
    """)
    c.execute("DELETE FROM article_icd10_vec")

    c.execute("""
        SELECT article_id, icd10_code, relevance
        FROM article_icd10
        WHERE icd10_code IS NOT NULL
        ORDER BY article_id
    """)
    art_tags = defaultdict(list)
    for art_id, code, rel in c.fetchall():
        art_tags[art_id].append((code, rel))

    art_written = art_skipped = 0
    for art_id, tags in art_tags.items():
        vw = [(icd10_vecs[code], RELEVANCE_WEIGHTS.get(rel, 1))
              for code, rel in tags if code in icd10_vecs]
        if not vw:
            art_skipped += 1
            continue
        agg = weighted_avg(vw)
        if not dry_run:
            c.execute("""
                INSERT OR REPLACE INTO article_icd10_vec
                    (article_id, embedding, code_count, model)
                VALUES (?, ?, ?, ?)
            """, (art_id, vec_to_blob(agg), len(vw), EMBED_MODEL))
        art_written += 1

    if not dry_run:
        conn.commit()
    print(f"\n  article_icd10_vec:  {art_written} written, {art_skipped} skipped (no matching codes)")

    # ── question_icd10_vec ────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS question_icd10_vec (
            qid         TEXT PRIMARY KEY,
            source_bank TEXT NOT NULL,
            embedding   BLOB NOT NULL,
            code_count  INTEGER,
            model       TEXT
        )
    """)
    c.execute("DELETE FROM question_icd10_vec")

    # AAFP: direct question-level ICD-10
    c.execute("""
        SELECT aafp_qid, icd10_code, relevance
        FROM aafp_question_icd10
        WHERE icd10_code IS NOT NULL
        ORDER BY aafp_qid
    """)
    aafp_tags = defaultdict(list)
    for qid, code, rel in c.fetchall():
        aafp_tags[qid].append((code, rel))

    aafp_written = aafp_skipped = 0
    for qid, tags in aafp_tags.items():
        vw = [(icd10_vecs[code], RELEVANCE_WEIGHTS.get(rel, 1))
              for code, rel in tags if code in icd10_vecs]
        if not vw:
            aafp_skipped += 1
            continue
        agg = weighted_avg(vw)
        if not dry_run:
            c.execute("""
                INSERT OR REPLACE INTO question_icd10_vec
                    (qid, source_bank, embedding, code_count, model)
                VALUES (?, 'aafp', ?, ?, ?)
            """, (qid, vec_to_blob(agg), len(vw), EMBED_MODEL))
        aafp_written += 1

    if not dry_run:
        conn.commit()
    print(f"  question_icd10_vec (AAFP): {aafp_written} written, {aafp_skipped} skipped")

    # ITE: question → qid_art_xref → article_icd10 (deduplicate codes per question)
    c.execute("""
        SELECT q.qid, ai.icd10_code, ai.relevance
        FROM questions q
        JOIN qid_art_xref x  ON q.qid = x.qid
        JOIN article_icd10 ai ON x.article_id = ai.article_id
        WHERE ai.icd10_code IS NOT NULL
        ORDER BY q.qid
    """)
    ite_tags = defaultdict(dict)  # qid → {code: best_relevance}
    rel_rank = {"primary": 3, "secondary": 2, "related": 1}
    for qid, code, rel in c.fetchall():
        existing = ite_tags[qid].get(code)
        if existing is None or rel_rank.get(rel, 1) > rel_rank.get(existing, 1):
            ite_tags[qid][code] = rel  # keep highest relevance per code

    ite_written = ite_skipped = 0
    for qid, code_rel_map in ite_tags.items():
        vw = [(icd10_vecs[code], RELEVANCE_WEIGHTS.get(rel, 1))
              for code, rel in code_rel_map.items() if code in icd10_vecs]
        if not vw:
            ite_skipped += 1
            continue
        agg = weighted_avg(vw)
        if not dry_run:
            c.execute("""
                INSERT OR REPLACE INTO question_icd10_vec
                    (qid, source_bank, embedding, code_count, model)
                VALUES (?, 'ite', ?, ?, ?)
            """, (qid, vec_to_blob(agg), len(vw), EMBED_MODEL))
        ite_written += 1

    if not dry_run:
        conn.commit()
    print(f"  question_icd10_vec (ITE):  {ite_written} written, {ite_skipped} skipped")


# ── Phase 3: Report ───────────────────────────────────────────────────────────

def phase_report(conn):
    c = conn.cursor()

    print("\n  ── icd10_vec ─────────────────────────────────────────")
    row = c.execute("SELECT COUNT(*), model FROM icd10_vec GROUP BY model").fetchone()
    if row:
        print(f"  {row[0]} codes embedded   model: {row[1]}")
    else:
        print("  (empty)")

    print("\n  ── article_icd10_vec ─────────────────────────────────")
    row = c.execute("SELECT COUNT(*), AVG(code_count) FROM article_icd10_vec").fetchone()
    if row and row[0]:
        cited = c.execute(
            "SELECT COUNT(*) FROM articles WHERE citation_count > 0 AND source_type != 'stub'"
        ).fetchone()[0]
        print(f"  {row[0]} articles  avg {row[1]:.1f} codes/article  ({100.0 * row[0] / max(cited, 1):.1f}% of cited articles)")
    else:
        print("  (empty)")

    print("\n  ── question_icd10_vec ────────────────────────────────")
    for bank, tbl, col in [
        ("ite",  "questions",      "qid"),
        ("aafp", "aafp_questions", "aafp_qid"),
    ]:
        row = c.execute("""
            SELECT COUNT(*), AVG(code_count)
            FROM question_icd10_vec
            WHERE source_bank = ?
        """, (bank,)).fetchone()
        total = c.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        if row and row[0]:
            print(f"  {bank.upper():4}: {row[0]:5} questions  avg {row[1]:.1f} codes/q  ({100.0 * row[0] / max(total, 1):.1f}% coverage)")
        else:
            print(f"  {bank.upper():4}: (empty)")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="ICD-10 Vector Embedding Layer — icd10_vec + article_icd10_vec + question_icd10_vec"
    )
    parser.add_argument("--embed",   action="store_true", help="Phase 1: embed ICD-10 codes via OpenAI")
    parser.add_argument("--derive",  action="store_true", help="Phase 2: derive article + question vectors")
    parser.add_argument("--report",  action="store_true", help="Phase 3: coverage stats")
    parser.add_argument("--all",     action="store_true", help="Run all three phases in order")
    parser.add_argument("--dry-run", action="store_true", help="Preview counts only — no writes, no API calls")
    args = parser.parse_args()

    if not any([args.embed, args.derive, args.report, args.all]):
        parser.print_help()
        sys.exit(1)

    run_embed  = args.embed  or args.all
    run_derive = args.derive or args.all
    run_report = args.report or args.all

    print(f"Database: {DB_PATH}")
    print(f"Model:    {EMBED_MODEL}  ({EMBED_DIM}d)")
    if args.dry_run:
        print("MODE:     DRY RUN — no writes, no API calls")

    conn = sqlite3.connect(str(DB_PATH), timeout=10)

    try:
        if run_embed:
            print(f"\n{'='*60}")
            print("  PHASE 1: EMBED — ICD-10 descriptions → icd10_vec")
            print(f"{'='*60}")
            if args.dry_run:
                # Still need to count without API
                phase_embed(conn, client=None, dry_run=True)
            else:
                api_key = os.environ.get("OPENAI_API_KEY")
                if not api_key:
                    print("ERROR: OPENAI_API_KEY not set in environment variables")
                    sys.exit(1)
                try:
                    from openai import OpenAI
                except ImportError:
                    print("ERROR: openai not installed — run: pip install openai")
                    sys.exit(1)
                client = OpenAI(api_key=api_key)
                phase_embed(conn, client=client, dry_run=False)

        if run_derive:
            print(f"\n{'='*60}")
            print("  PHASE 2: DERIVE — Aggregate ICD-10 vectors for articles + questions")
            print(f"{'='*60}")
            phase_derive(conn, dry_run=args.dry_run)

        if run_report:
            print(f"\n{'='*60}")
            print("  PHASE 3: REPORT — Coverage stats")
            print(f"{'='*60}")
            phase_report(conn)

    finally:
        conn.close()

    print("\nDone.")


if __name__ == "__main__":
    main()
