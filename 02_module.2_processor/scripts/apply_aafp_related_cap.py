#!/usr/bin/env python3
"""
apply_aafp_related_cap.py
02_module.2_processor/scripts/

Applies a tier-aware cap to aafp_question_icd10:
  - ALL primary codes kept
  - ALL secondary codes kept
  - 'related' codes: keep top RELATED_CAP per question,
    ranked by global frequency (how many questions share that code)

This mirrors the cap applied to question_icd10 (ITE side).
Safe to re-run -- idempotent.

Run:
    python scripts\apply_aafp_related_cap.py
"""

import sqlite3, sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH      = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"

RELATED_CAP = 3

def main():
    print("=" * 60)
    print("apply_aafp_related_cap.py")
    print(f"Cap: keep top {RELATED_CAP} related codes per question")
    print("=" * 60)

    conn = sqlite3.connect(DB_PATH, timeout=10)
    try:
        cur = conn.cursor()

        # --- Pre-cap state ---------------------------------------------------
        cur.execute("SELECT COUNT(*) FROM aafp_question_icd10 WHERE relevance = 'related'")
        related_before = cur.fetchone()[0]

        cur.execute("""
            SELECT COUNT(*) FROM (
                SELECT aafp_qid, COUNT(*) AS n
                FROM aafp_question_icd10
                WHERE relevance = 'related'
                GROUP BY aafp_qid
                HAVING n > ?
            )
        """, (RELATED_CAP,))
        questions_over_cap = cur.fetchone()[0]

        print(f"\nPre-cap:")
        print(f"  Related rows total         : {related_before:,}")
        print(f"  Questions over cap (>{RELATED_CAP}) : {questions_over_cap}")

        if questions_over_cap == 0:
            print("\nNo questions exceed the cap -- nothing to delete.")
            return

        # --- Apply cap -------------------------------------------------------
        # Rank related codes per question by global frequency
        # (how many questions share that code across the whole bank).
        # Most broadly-used codes are most likely to be genuinely relevant.
        cur.execute(f"""
            DELETE FROM aafp_question_icd10
            WHERE relevance = 'related'
              AND (aafp_qid || '|' || icd10_code) NOT IN (
                  SELECT aafp_qid || '|' || icd10_code
                  FROM (
                      SELECT
                          q.aafp_qid,
                          q.icd10_code,
                          ROW_NUMBER() OVER (
                              PARTITION BY q.aafp_qid
                              ORDER BY COUNT(q2.aafp_qid) DESC, q.icd10_code
                          ) AS rn
                      FROM aafp_question_icd10 q
                      JOIN aafp_question_icd10 q2
                           ON q2.icd10_code = q2.icd10_code
                           AND q2.relevance = 'related'
                      WHERE q.relevance = 'related'
                      GROUP BY q.aafp_qid, q.icd10_code
                  )
                  WHERE rn <= {RELATED_CAP}
              )
        """)
        deleted = cur.rowcount
        conn.commit()

        # --- Post-cap state --------------------------------------------------
        cur.execute("SELECT COUNT(*) FROM aafp_question_icd10 WHERE relevance = 'related'")
        related_after = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM aafp_question_icd10")
        total = cur.fetchone()[0]

        cur.execute("""
            SELECT relevance, COUNT(*) FROM aafp_question_icd10
            GROUP BY relevance ORDER BY relevance
        """)
        rel_counts = dict(cur.fetchall())

        print(f"\nPost-cap:")
        print(f"  Related rows removed       : {deleted:,}")
        print(f"  Related rows remaining     : {related_after:,}")
        print()
        print(f"aafp_question_icd10 final state:")
        print(f"  Total rows                 : {total:,}")
        for rel in ("primary", "secondary", "related"):
            cnt = rel_counts.get(rel, 0)
            pct = cnt / max(total, 1) * 100
            print(f"  {rel:<12}             : {cnt:>5}  ({pct:.1f}%)")

    except Exception as e:
        conn.rollback()
        print(f"\nFATAL ERROR: {e}")
        raise
    finally:
        conn.close()

    print("\nDone.")

if __name__ == "__main__":
    main()
