#!/usr/bin/env python3
"""
vector_sync.py — Sync SQLite vector embeddings → Supabase pgvector

Uses psycopg2 COPY for bulk insert of 1536-dimensional float arrays.
The Supabase REST API is too slow for bulk vector upserts.

Usage:
    python vector_sync.py                          # sync all three vector tables
    python vector_sync.py --tables question_icd10  # selective

Environment variables:
    SUPABASE_DB_URL   postgresql://postgres:[password]@db.[ref].supabase.co:5432/postgres

Requirements:
    pip install psycopg2-binary python-dotenv tqdm
"""

import argparse
import io
import os
import sqlite3
import sys
from pathlib import Path

from dotenv import load_dotenv
from tqdm import tqdm

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
DB_PATH = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"

load_dotenv(PROJECT_ROOT / ".env")

SUPABASE_DB_URL = os.environ.get("SUPABASE_DB_URL", "")
if not SUPABASE_DB_URL:
    print("ERROR: SUPABASE_DB_URL must be set (postgresql:// connection string).")
    sys.exit(1)

VECTOR_SYNC_DEFS = [
    {
        "sqlite_table": "article_icd10_vec",
        "pg_table": "article_icd10_vec",
        "pk_col": "article_id",
        "vec_col": "embedding",
        "pk_type": "TEXT",
    },
    {
        "sqlite_table": "question_icd10_vec",
        "pg_table": "question_icd10_vec",
        "pk_col": "qid",
        "vec_col": "embedding",
        "pk_type": "TEXT",
        "extra_cols": [("source_bank", "TEXT")],
    },
    {
        "sqlite_table": "icd10_vec",
        "pg_table": "icd10_vec",
        "pk_col": "icd10_code",
        "vec_col": "embedding",
        "pk_type": "TEXT",
    },
]


def load_sqlite_vectors(sqlite_table: str, extra_cols: list = None) -> list[dict]:
    """Read all rows from a SQLite vector table."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(f"SELECT * FROM {sqlite_table}").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def embedding_to_pg_literal(embedding_bytes: bytes) -> str:
    """
    Convert SQLite-vec stored binary embedding to PostgreSQL vector literal.
    sqlite-vec stores float32 arrays as raw binary (little-endian).
    """
    import struct
    n = len(embedding_bytes) // 4
    floats = struct.unpack(f"<{n}f", embedding_bytes)
    return "[" + ",".join(f"{v:.8f}" for v in floats) + "]"


def sync_vector_table(defn: dict) -> None:
    try:
        import psycopg2
    except ImportError:
        print("ERROR: psycopg2-binary is required. Run: pip install psycopg2-binary")
        sys.exit(1)

    sqlite_table = defn["sqlite_table"]
    pg_table = defn["pg_table"]
    pk_col = defn["pk_col"]
    vec_col = defn["vec_col"]
    extra_cols = defn.get("extra_cols", [])

    print(f"  {sqlite_table} → {pg_table}", end=" ", flush=True)

    rows = load_sqlite_vectors(sqlite_table)
    total = len(rows)
    print(f"({total:,} rows)")

    conn = psycopg2.connect(SUPABASE_DB_URL)
    cur = conn.cursor()

    # Truncate and reload (full resync — embeddings are deterministic)
    cur.execute(f"TRUNCATE TABLE {pg_table};")

    extra_col_names = [c[0] for c in extra_cols]
    all_cols = [pk_col] + extra_col_names + [vec_col]
    col_list = ", ".join(all_cols)

    for row in tqdm(rows, desc=f"  {pg_table}", leave=False):
        pk_val = row[pk_col]
        extra_vals = [row.get(c[0]) for c in extra_cols]
        raw_embedding = row[vec_col]

        if raw_embedding is None:
            continue

        vec_literal = embedding_to_pg_literal(raw_embedding)

        placeholders = ", ".join(["%s"] * len(extra_vals)) if extra_vals else ""
        if extra_vals:
            cur.execute(
                f"INSERT INTO {pg_table} ({col_list}) VALUES (%s, {placeholders}, %s::vector)",
                [pk_val] + extra_vals + [vec_literal],
            )
        else:
            cur.execute(
                f"INSERT INTO {pg_table} ({col_list}) VALUES (%s, %s::vector)",
                [pk_val, vec_literal],
            )

    conn.commit()
    cur.close()
    conn.close()
    print(f"  ✓ {total:,} vectors loaded into {pg_table}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync SQLite vectors → Supabase pgvector")
    parser.add_argument("--tables", nargs="*", help="sqlite-vec table names to sync")
    args = parser.parse_args()

    if not DB_PATH.exists():
        print(f"ERROR: Database not found at {DB_PATH}")
        sys.exit(1)

    defs = VECTOR_SYNC_DEFS
    if args.tables:
        requested = set(args.tables)
        defs = [d for d in VECTOR_SYNC_DEFS if d["sqlite_table"] in requested]

    print(f"DB path: {DB_PATH}")
    print(f"Syncing {len(defs)} vector table(s)")
    print()

    for defn in defs:
        sync_vector_table(defn)

    print("\nVector sync complete.")


if __name__ == "__main__":
    main()
