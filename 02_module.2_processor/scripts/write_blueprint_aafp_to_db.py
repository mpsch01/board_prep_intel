#!/usr/bin/env python3
"""
write_blueprint_aafp_to_db.py
==============================
Reads blueprint_classifications_aafp.xlsx and writes blueprint labels
to aafp_questions.blueprint in the DB.

Adds blueprint column if it doesn't exist (ALTER TABLE).
Matches on aafp_qid. Dry-run by default.

Run:
    python write_blueprint_aafp_to_db.py            # dry-run
    python write_blueprint_aafp_to_db.py --live     # write to DB
"""

import sqlite3
import sys
import pandas as pd
from pathlib import Path

SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH      = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"
DEFAULT_INPUT = PROJECT_ROOT / "02_module.2_processor" / "source" / "blueprint_classifications_aafp.xlsx"

VALID_CATEGORIES = {
    "Acute Care and Diagnosis",
    "Chronic Care Management",
    "Emergent and Urgent Care",
    "Preventive Care",
    "Foundations of Care",
}

DRY_RUN = "--live" not in sys.argv


def main():
    print(f"{'DRY RUN' if DRY_RUN else 'LIVE RUN'}")
    print(f"Input:  {DEFAULT_INPUT}")
    print(f"DB:     {DB_PATH}\n")

    if not DEFAULT_INPUT.exists():
        print(f"ERROR: Input file not found: {DEFAULT_INPUT}")
        sys.exit(1)

    df = pd.read_excel(DEFAULT_INPUT)
    print(f"Loaded {len(df)} rows from xlsx.")

    # Validate
    review_rows = df[df["blueprint_category"].str.startswith("REVIEW", na=True)]
    valid_rows  = df[df["blueprint_category"].isin(VALID_CATEGORIES)]
    print(f"  Valid categories:  {len(valid_rows)}")
    print(f"  REVIEW/invalid:    {len(review_rows)}")
    if len(review_rows):
        print("  REVIEW items (will be skipped):")
        for _, r in review_rows.iterrows():
            print(f"    {r['aafp_qid']}: {r['blueprint_category']}")
    print()

    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    # Add blueprint column if missing
    cur.execute("PRAGMA table_info(aafp_questions)")
    existing = {r[1] for r in cur.fetchall()}
    if "blueprint" not in existing:
        print("Adding blueprint column to aafp_questions...")
        if not DRY_RUN:
            cur.execute("ALTER TABLE aafp_questions ADD COLUMN blueprint TEXT")

    # Cross-check: which aafp_qids are in the DB?
    cur.execute("SELECT aafp_qid FROM aafp_questions")
    db_qids = {r[0] for r in cur.fetchall()}
    in_db     = valid_rows[valid_rows["aafp_qid"].isin(db_qids)]
    not_in_db = valid_rows[~valid_rows["aafp_qid"].isin(db_qids)]
    print(f"  Matched to DB:     {len(in_db)}/{len(valid_rows)}")
    if len(not_in_db):
        print(f"  Not in DB ({len(not_in_db)}):")
        for _, r in not_in_db.iterrows():
            print(f"    {r['aafp_qid']}")
    print()

    if DRY_RUN:
        print("DRY RUN — no writes. Run with --live to execute.")
        conn.close()
        return

    # Write
    updated = 0
    for _, row in in_db.iterrows():
        cur.execute(
            "UPDATE aafp_questions SET blueprint = ? WHERE aafp_qid = ?",
            (row["blueprint_category"], row["aafp_qid"])
        )
        updated += cur.rowcount

    conn.commit()
    print(f"Updated: {updated} rows")

    # QC
    cur.execute("SELECT COUNT(*) FROM aafp_questions WHERE blueprint IS NOT NULL AND blueprint != ''")
    filled = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM aafp_questions")
    total  = cur.fetchone()[0]
    print(f"\nPost-write QC — blueprint filled: {filled}/{total}")

    print("\nDistribution:")
    cur.execute("SELECT blueprint, COUNT(*) FROM aafp_questions GROUP BY blueprint ORDER BY COUNT(*) DESC")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]}")

    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
