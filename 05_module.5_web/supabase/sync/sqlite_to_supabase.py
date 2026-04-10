#!/usr/bin/env python3
"""
sqlite_to_supabase.py — Sync ite_intelligence.db → Supabase (PostgreSQL)

Reads from the local SQLite database and upserts all content tables into
Supabase via the REST API.  Run this after any M1/M2/M3 pipeline run that
changes articles, questions, or intelligence layers.

Usage:
    python sqlite_to_supabase.py                  # sync all tables
    python sqlite_to_supabase.py --tables articles questions    # selective sync
    python sqlite_to_supabase.py --dry-run        # count rows only, no writes

Environment variables (set in .env or shell):
    SUPABASE_URL            https://xxxxx.supabase.co
    SUPABASE_SERVICE_KEY    eyJhbGc...  (service_role key — bypasses RLS)

Requirements:
    pip install supabase python-dotenv tqdm
"""

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from supabase import create_client, Client
from tqdm import tqdm

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent  # supabase/sync/ → 05_module.5_web/ → repo root
DB_PATH = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
load_dotenv(PROJECT_ROOT / ".env")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in environment.")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Table sync definitions
# Each entry: (sqlite_table, supabase_table, primary_key_columns)
# JSON text columns in SQLite need to be parsed before upsert.
# ---------------------------------------------------------------------------
SYNC_TABLES: list[dict] = [
    {
        "sqlite": "articles",
        "supabase": "articles",
        "pk": ["article_id"],
        "json_cols": ["exam_years", "concept_tags"],
    },
    {
        "sqlite": "questions",
        "supabase": "questions",
        "pk": ["qid"],
        "json_cols": ["choices", "concept_tags"],
    },
    {
        "sqlite": "aafp_questions",
        "supabase": "aafp_questions",
        "pk": ["aafp_qid"],
        "json_cols": ["choices", "concept_tags"],
    },
    {
        "sqlite": "qid_art_xref",
        "supabase": "qid_art_xref",
        "pk": ["qid", "article_id"],
        "json_cols": [],
    },
    {
        "sqlite": "aafp_qid_art_xref",
        "supabase": "aafp_qid_art_xref",
        "pk": ["aafp_qid", "article_id"],
        "json_cols": [],
    },
    {
        "sqlite": "icd10_rollup",
        "supabase": "icd10_rollup",
        "pk": ["parent_code"],
        "json_cols": [],
    },
    {
        "sqlite": "icd10_code_xref",
        "supabase": "icd10_code_xref",
        "pk": ["icd10_code"],
        "json_cols": [],
    },
    {
        "sqlite": "article_icd10",
        "supabase": "article_icd10",
        "pk": ["article_id", "icd10_code"],
        "json_cols": [],
    },
    {
        "sqlite": "question_icd10",
        "supabase": "question_icd10",
        "pk": ["qid", "icd10_code"],
        "json_cols": [],
    },
    {
        "sqlite": "aafp_question_icd10",
        "supabase": "aafp_question_icd10",
        "pk": ["aafp_qid", "icd10_code"],
        "json_cols": [],
    },
    {
        "sqlite": "clinical_pathways",
        "supabase": "clinical_pathways",
        "pk": ["article_id", "icd10_code"],
        "json_cols": [],
    },
    {
        "sqlite": "article_citation_trend",
        "supabase": "article_citation_trend",
        "pk": ["article_id"],
        "json_cols": [],
    },
    {
        "sqlite": "article_currency",
        "supabase": "article_currency",
        "pk": ["article_id"],
        "json_cols": ["title_signals"],
    },
]

# Vector tables are NOT synced via REST (too slow for 1536-dim vectors).
# Use the separate vector_sync.py script for pgvector data.
VECTOR_TABLES = ["article_icd10_vec", "question_icd10_vec", "icd10_vec"]

BATCH_SIZE = 500   # Supabase REST upsert batch size


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def sqlite_rows_as_dicts(conn: sqlite3.Connection, table: str) -> list[dict]:
    """Read all rows from a SQLite table as a list of dicts."""
    allowed_tables = {t["sqlite"] for t in SYNC_TABLES}
    if table not in allowed_tables:
        raise ValueError(f"Table '{table}' is not in the sync allowlist.")
    # Table name validated against allowlist — safe to interpolate.
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(f"SELECT * FROM {table}")  # noqa: S608
    return [dict(row) for row in cursor.fetchall()]


def parse_json_cols(rows: list[dict], json_cols: list[str]) -> list[dict]:
    """
    Parse TEXT JSON columns so Supabase receives proper JSONB objects
    rather than raw strings.  Silently skips NULL values.
    """
    for row in rows:
        for col in json_cols:
            if col in row and isinstance(row[col], str):
                try:
                    row[col] = json.loads(row[col])
                except (json.JSONDecodeError, TypeError):
                    pass  # leave as-is if unparseable
    return rows


def coerce_booleans(rows: list[dict]) -> list[dict]:
    """Convert SQLite INTEGER 0/1 booleans in is_watch_list to Python bool."""
    for row in rows:
        if "is_watch_list" in row and row["is_watch_list"] is not None:
            row["is_watch_list"] = bool(row["is_watch_list"])
    return rows


def upsert_batch(client: Client, table: str, rows: list[dict]) -> int:
    """Upsert a batch of rows into Supabase.  Returns number of rows upserted."""
    if not rows:
        return 0
    try:
        client.table(table).upsert(rows).execute()
    except Exception as exc:
        raise RuntimeError(f"Supabase upsert failed for table '{table}': {exc}") from exc
    return len(rows)


# ---------------------------------------------------------------------------
# Main sync
# ---------------------------------------------------------------------------

def sync_table(client: Client, conn: sqlite3.Connection, defn: dict, dry_run: bool) -> None:
    sqlite_table = defn["sqlite"]
    supabase_table = defn["supabase"]
    json_cols = defn.get("json_cols", [])

    rows = sqlite_rows_as_dicts(conn, sqlite_table)
    rows = parse_json_cols(rows, json_cols)
    rows = coerce_booleans(rows)

    total = len(rows)
    print(f"  {sqlite_table} → {supabase_table}: {total:,} rows", end="")

    if dry_run:
        print("  [dry-run, skipping write]")
        return

    upserted = 0
    for i in tqdm(range(0, total, BATCH_SIZE), desc=f"  {supabase_table}", leave=False):
        batch = rows[i : i + BATCH_SIZE]
        upserted += upsert_batch(client, supabase_table, batch)

    print(f"  ✓ {upserted:,} upserted")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync SQLite → Supabase")
    parser.add_argument(
        "--tables",
        nargs="*",
        help="SQLite table names to sync (default: all content tables)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Count rows without writing to Supabase",
    )
    args = parser.parse_args()

    if not DB_PATH.exists():
        print(f"ERROR: Database not found at {DB_PATH}")
        sys.exit(1)

    # Filter sync list if --tables specified
    tables_to_sync = SYNC_TABLES
    if args.tables:
        requested = set(args.tables)
        tables_to_sync = [t for t in SYNC_TABLES if t["sqlite"] in requested]
        unknown = requested - {t["sqlite"] for t in tables_to_sync}
        if unknown:
            print(f"WARNING: Unknown tables (not in sync list): {unknown}")
            print(f"Vector tables must be synced separately: {VECTOR_TABLES}")

    print(f"DB path: {DB_PATH}")
    print(f"Supabase: {SUPABASE_URL}")
    print(f"Tables to sync: {len(tables_to_sync)}")
    if args.dry_run:
        print("[DRY RUN — no writes]")
    print()

    client: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    conn = sqlite3.connect(str(DB_PATH))
    try:
        for defn in tables_to_sync:
            sync_table(client, conn, defn, args.dry_run)
    finally:
        conn.close()

    print()
    print("Sync complete.")
    if VECTOR_TABLES:
        print(
            f"NOTE: Vector tables ({', '.join(VECTOR_TABLES)}) require a separate sync.\n"
            "Run vector_sync.py to migrate embeddings via psycopg2 COPY."
        )


if __name__ == "__main__":
    main()
