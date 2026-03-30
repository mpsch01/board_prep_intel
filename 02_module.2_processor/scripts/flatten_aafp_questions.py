#!/usr/bin/env python3
"""
flatten_aafp_questions.py
=========================
Merges aafp_explanations (1:1) into aafp_questions, then drops:
  - TABLE aafp_explanations   (data now lives in aafp_questions)
  - COLUMN aafp_questions.subcategory  (legacy noise — see BATON 025)

Net result: aafp_questions becomes the single cohesive AAFP row,
mirroring the structure of the ITE questions table.

Columns added to aafp_questions:
  correct_letter       TEXT  — "A"/"B"/"C"/"D"/"E"
  correct_text         TEXT  — human-readable correct answer
  explanation          TEXT  — plain-text explanation (no HTML)
  explanation_keywords TEXT  — comma-separated keywords from explanation

Run:
    python flatten_aafp_questions.py            # dry-run (default)
    python flatten_aafp_questions.py --live     # execute changes
"""

import sqlite3
import sys
from pathlib import Path

SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH      = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"

DRY_RUN = "--live" not in sys.argv

def run():
    print(f"{'DRY RUN — no changes written' if DRY_RUN else 'LIVE RUN — writing to DB'}")
    print(f"DB: {DB_PATH}\n")

    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    # ── Pre-flight checks ──────────────────────────────────────────────
    cur.execute("SELECT COUNT(*) FROM aafp_questions")
    q_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM aafp_explanations")
    e_count = cur.fetchone()[0]
    print(f"Pre-flight:")
    print(f"  aafp_questions rows:    {q_count}")
    print(f"  aafp_explanations rows: {e_count}")

    cur.execute("PRAGMA table_info(aafp_questions)")
    existing_cols = {r[1] for r in cur.fetchall()}
    print(f"  Existing aafp_questions columns: {sorted(existing_cols)}")

    new_cols = ['correct_letter', 'correct_text', 'explanation', 'explanation_keywords']
    already_present = [c for c in new_cols if c in existing_cols]
    to_add          = [c for c in new_cols if c not in existing_cols]
    has_subcategory = 'subcategory' in existing_cols

    print(f"\nColumns to ADD:    {to_add}")
    print(f"Already present:   {already_present}")
    print(f"subcategory exists (will drop): {has_subcategory}")
    print()

    if DRY_RUN:
        print("── DRY RUN PLAN ──────────────────────────────────────────────")
        for col in to_add:
            print(f"  ALTER TABLE aafp_questions ADD COLUMN {col} TEXT")
        print(f"  UPDATE aafp_questions SET correct_letter, correct_text,")
        print(f"         explanation, explanation_keywords FROM aafp_explanations")
        print(f"         WHERE aafp_questions.aafp_qid = aafp_explanations.aafp_qid")
        print(f"  DROP TABLE aafp_explanations")
        if has_subcategory:
            print(f"  ALTER TABLE aafp_questions DROP COLUMN subcategory")
        print()

        # Preview counts
        cur.execute("""
            SELECT COUNT(*) FROM aafp_questions q
            JOIN aafp_explanations e ON q.aafp_qid = e.aafp_qid
            WHERE e.explanation IS NOT NULL AND e.explanation != ''
        """)
        joinable = cur.fetchone()[0]
        print(f"  Rows joinable with explanation: {joinable}/{q_count}")
        print("\nRun with --live to execute.")
        conn.close()
        return

    # ── LIVE: Step 1 — Add columns ────────────────────────────────────
    for col in to_add:
        print(f"  Adding column: {col}")
        cur.execute(f"ALTER TABLE aafp_questions ADD COLUMN {col} TEXT")

    # ── LIVE: Step 2 — Populate from aafp_explanations ───────────────
    print("  Populating from aafp_explanations...")
    cur.execute("""
        UPDATE aafp_questions
        SET
            correct_letter       = (SELECT e.correct_letter       FROM aafp_explanations e WHERE e.aafp_qid = aafp_questions.aafp_qid),
            correct_text         = (SELECT e.correct_text         FROM aafp_explanations e WHERE e.aafp_qid = aafp_questions.aafp_qid),
            explanation          = (SELECT e.explanation          FROM aafp_explanations e WHERE e.aafp_qid = aafp_questions.aafp_qid),
            explanation_keywords = (SELECT e.explanation_keywords FROM aafp_explanations e WHERE e.aafp_qid = aafp_questions.aafp_qid)
    """)
    updated = cur.rowcount
    print(f"  Rows updated: {updated}")

    # ── LIVE: Step 3 — Verify ─────────────────────────────────────────
    cur.execute("SELECT COUNT(*) FROM aafp_questions WHERE explanation IS NOT NULL AND explanation != ''")
    filled = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM aafp_questions WHERE correct_letter IS NOT NULL")
    letters = cur.fetchone()[0]
    print(f"  Verification — explanation filled: {filled}/{q_count}")
    print(f"  Verification — correct_letter filled: {letters}/{q_count}")

    if filled < q_count:
        print(f"\nWARNING: {q_count - filled} rows missing explanation — aborting drop steps.")
        conn.rollback()
        conn.close()
        return

    # ── LIVE: Step 4 — Drop aafp_explanations ────────────────────────
    print("  Dropping TABLE aafp_explanations...")
    cur.execute("DROP TABLE aafp_explanations")

    # ── LIVE: Step 5 — Drop subcategory column ───────────────────────
    if has_subcategory:
        print("  Dropping COLUMN aafp_questions.subcategory...")
        cur.execute("ALTER TABLE aafp_questions DROP COLUMN subcategory")

    conn.commit()

    # ── Post-flight QC ────────────────────────────────────────────────
    print("\n── POST-FLIGHT QC ────────────────────────────────────────────")
    cur.execute("PRAGMA table_info(aafp_questions)")
    final_cols = [r[1] for r in cur.fetchall()]
    print(f"  aafp_questions final columns: {final_cols}")
    cur.execute("SELECT COUNT(*) FROM aafp_questions")
    print(f"  aafp_questions row count: {cur.fetchone()[0]}")

    # Confirm aafp_explanations is gone
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='aafp_explanations'")
    gone = cur.fetchone() is None
    print(f"  aafp_explanations dropped: {gone}")

    print("\nDone.")
    conn.close()

if __name__ == "__main__":
    run()
