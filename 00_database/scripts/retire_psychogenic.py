#!/usr/bin/env python3
"""
retire_psychogenic.py
=====================
One-time migration: retire 'Psychogenic' as a body_system category.

All occurrences are renamed to the current canonical name: 'Psychiatric/Behavioral'.

Columns updated:
  - questions.body_system_merged  (120 rows)
  - aafp_questions.body_system    (82 rows)

NOTE: questions.body_system is LEFT UNCHANGED — it stores the raw value
from the original ABFM PDF (e.g. 'Psychogenic' from 2018-2021 exams).
That is source data and is historically accurate.

Run from any directory:
    python retire_psychogenic.py

Or with an explicit DB path:
    python retire_psychogenic.py --db C:/path/to/ite_intelligence.db
"""

import sqlite3
import sys
import argparse
from pathlib import Path

SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DEFAULT_DB   = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"


def main():
    ap = argparse.ArgumentParser(description="Retire 'Psychogenic' body system category")
    ap.add_argument("--db", default=str(DEFAULT_DB), help="Path to ite_intelligence.db")
    ap.add_argument("--dry-run", action="store_true", help="Show counts only, no changes")
    args = ap.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"ERROR: DB not found at {db_path}", file=sys.stderr)
        sys.exit(1)

    print(f"\nDB: {db_path}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}\n")

    conn = sqlite3.connect(str(db_path), timeout=15)
    conn.execute("PRAGMA journal_mode=WAL")
    cur = conn.cursor()

    # --- Pre-flight counts ---
    cur.execute("""
        SELECT body_system_merged, COUNT(*)
        FROM questions
        WHERE body_system_merged IN ('Psychogenic', 'Psychiatric/Behavioral')
        GROUP BY body_system_merged
    """)
    q_before = cur.fetchall()
    print("questions.body_system_merged BEFORE:")
    for row in q_before:
        print(f"  {row[0]!r}: {row[1]}")

    cur.execute("""
        SELECT body_system, COUNT(*)
        FROM aafp_questions
        WHERE body_system = 'Psychogenic'
        GROUP BY body_system
    """)
    a_before = cur.fetchall()
    print("\naafp_questions.body_system BEFORE:")
    for row in a_before:
        print(f"  {row[0]!r}: {row[1]}")

    if args.dry_run:
        print("\n[DRY RUN] No changes made.\n")
        conn.close()
        return

    # --- Updates ---
    cur.execute("""
        UPDATE questions
        SET body_system_merged = 'Psychiatric/Behavioral'
        WHERE body_system_merged IN ('Psychogenic', 'Psychiatric/Behavioral')
    """)
    q_count = cur.rowcount
    print(f"\nquestions.body_system_merged updated: {q_count} rows")

    cur.execute("""
        UPDATE aafp_questions
        SET body_system = 'Psychiatric/Behavioral'
        WHERE body_system = 'Psychogenic'
    """)
    a_count = cur.rowcount
    print(f"aafp_questions.body_system updated:   {a_count} rows")

    conn.commit()

    # --- Post-flight counts ---
    cur.execute("""
        SELECT body_system_merged, COUNT(*)
        FROM questions
        WHERE body_system_merged = 'Psychiatric/Behavioral'
        GROUP BY body_system_merged
    """)
    print("\nquestions.body_system_merged AFTER:")
    for row in cur.fetchall():
        print(f"  {row[0]!r}: {row[1]}")

    cur.execute("""
        SELECT body_system, COUNT(*)
        FROM aafp_questions
        WHERE body_system = 'Psychiatric/Behavioral'
        GROUP BY body_system
    """)
    print("\naafp_questions.body_system AFTER:")
    for row in cur.fetchall():
        print(f"  {row[0]!r}: {row[1]}")

    # --- Confirm Psychogenic is gone ---
    cur.execute("""
        SELECT COUNT(*) FROM questions WHERE body_system_merged = 'Psychogenic'
    """)
    remaining_q = cur.fetchone()[0]
    cur.execute("""
        SELECT COUNT(*) FROM aafp_questions WHERE body_system = 'Psychogenic'
    """)
    remaining_a = cur.fetchone()[0]

    print(f"\n✓ Psychogenic remaining in questions.body_system_merged: {remaining_q}")
    print(f"✓ Psychogenic remaining in aafp_questions.body_system:    {remaining_a}")

    if remaining_q == 0 and remaining_a == 0:
        print("\n✅ Migration complete — Psychogenic fully retired.\n")
    else:
        print("\n⚠ WARNING: Some Psychogenic rows remain.\n", file=sys.stderr)

    conn.close()


if __name__ == "__main__":
    main()
