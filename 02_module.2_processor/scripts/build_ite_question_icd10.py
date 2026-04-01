"""
build_ite_question_icd10.py
============================
Builds the question_icd10 table for ITE questions by propagating ICD-10 codes
from article_icd10 through qid_art_xref.

Data flow:
    article_icd10 → qid_art_xref → question_icd10

When a question links to multiple articles that share the same ICD-10 code,
the best relevance is kept (primary > secondary > related).

QC output:
    - Coverage: questions tagged vs. total
    - Gap log: QIDs with zero codes (no article link vs. untagged article)
    - Codes-per-question distribution
    - Relevance distribution (input vs. output comparison)

Usage:
    python build_ite_question_icd10.py            # full run (drop + rebuild)
    python build_ite_question_icd10.py --dry-run  # QC only, no DB writes
"""

import sys
import sqlite3
import argparse
from pathlib import Path
from collections import Counter

# ---------------------------------------------------------------------------
# PATH SETUP
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"

# Relevance priority: lower number = better
RELEVANCE_RANK = {"primary": 0, "secondary": 1, "related": 2}

# Tier-aware cap: all primary + secondary kept; related capped per question.
# Ranked by contributing article frequency (most-shared codes survive).
RELATED_CAP = 3

# ---------------------------------------------------------------------------
# SCHEMA
# ---------------------------------------------------------------------------
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS question_icd10 (
    qid         TEXT NOT NULL,
    icd10_code  TEXT NOT NULL,
    icd10_desc  TEXT,
    relevance   TEXT,
    PRIMARY KEY (qid, icd10_code)
)
"""

# ---------------------------------------------------------------------------
# PROPAGATION QUERY
# ---------------------------------------------------------------------------
# For each (qid, icd10_code), select the best relevance across all linked articles.
# CASE ranks primary=0, secondary=1, related=2 so MIN() picks the best.
PROPAGATE_SQL = """
SELECT
    x.qid,
    a.icd10_code,
    a.icd10_desc,
    CASE a.relevance
        WHEN 'primary'   THEN 0
        WHEN 'secondary' THEN 1
        WHEN 'related'   THEN 2
        ELSE 3
    END AS relevance_rank,
    a.relevance
FROM qid_art_xref x
JOIN article_icd10 a ON x.article_id = a.article_id
"""

BEST_RELEVANCE_SQL = """
SELECT
    qid,
    icd10_code,
    -- keep icd10_desc from the best-relevance source row
    icd10_desc,
    CASE MIN(relevance_rank)
        WHEN 0 THEN 'primary'
        WHEN 1 THEN 'secondary'
        WHEN 2 THEN 'related'
        ELSE 'related'
    END AS relevance
FROM (
    SELECT
        x.qid,
        a.icd10_code,
        a.icd10_desc,
        CASE a.relevance
            WHEN 'primary'   THEN 0
            WHEN 'secondary' THEN 1
            WHEN 'related'   THEN 2
            ELSE 3
        END AS relevance_rank
    FROM qid_art_xref x
    JOIN article_icd10 a ON x.article_id = a.article_id
    JOIN articles ar ON x.article_id = ar.article_id
    WHERE ar.source_type != 'Textbook'   -- exclude: broad coverage = noise
)
GROUP BY qid, icd10_code
ORDER BY qid, relevance_rank, icd10_code
"""


# ---------------------------------------------------------------------------
# QC HELPERS
# ---------------------------------------------------------------------------

def qc_report(cur, rows_inserted):
    """Print a full QC report after propagation."""

    print("\n" + "=" * 60)
    print("QC REPORT — question_icd10 propagation")
    print("=" * 60)

    # Total ITE questions
    cur.execute("SELECT COUNT(*) FROM questions")
    total_q = cur.fetchone()[0]

    # Questions that received at least one ICD-10 code
    cur.execute("SELECT COUNT(DISTINCT qid) FROM question_icd10")
    tagged_q = cur.fetchone()[0]
    gap_q = total_q - tagged_q

    print(f"\nCOVERAGE")
    print(f"  Total ITE questions : {total_q}")
    print(f"  Tagged (>=1 code)   : {tagged_q}  ({tagged_q/total_q*100:.1f}%)")
    print(f"  Zero codes (gap)    : {gap_q}  ({gap_q/total_q*100:.1f}%)")
    print(f"  Rows inserted       : {rows_inserted}")

    # Gap breakdown: no article link vs. linked but untagged article
    cur.execute("""
        SELECT COUNT(*) FROM questions
        WHERE qid NOT IN (SELECT DISTINCT qid FROM qid_art_xref)
    """)
    no_link = cur.fetchone()[0]
    cur.execute("""
        SELECT COUNT(*) FROM questions
        WHERE qid NOT IN (SELECT DISTINCT qid FROM question_icd10)
          AND qid IN (SELECT DISTINCT qid FROM qid_art_xref)
    """)
    linked_but_untagged = cur.fetchone()[0]

    print(f"\nGAP BREAKDOWN")
    print(f"  No article link at all     : {no_link}")
    print(f"  Linked but article untagged: {linked_but_untagged}")

    # Year breakdown of gap
    print(f"\nGAP BY EXAM YEAR")
    cur.execute("""
        SELECT exam_year, COUNT(*) as cnt
        FROM questions
        WHERE qid NOT IN (SELECT DISTINCT qid FROM question_icd10)
        GROUP BY exam_year ORDER BY exam_year
    """)
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]} questions with no ICD-10")

    # Codes per question distribution
    cur.execute("""
        SELECT codes_per_q, COUNT(*) as num_questions
        FROM (
            SELECT qid, COUNT(*) as codes_per_q
            FROM question_icd10
            GROUP BY qid
        )
        GROUP BY codes_per_q ORDER BY codes_per_q
    """)
    dist = cur.fetchall()

    print(f"\nCODES PER QUESTION DISTRIBUTION")
    total_tagged = sum(r[1] for r in dist)
    cumulative = 0
    for cnt, num_q in dist:
        cumulative += num_q
        bar = "#" * min(cnt, 30)
        print(f"  {cnt:>2} codes: {num_q:>4} questions  ({cumulative/total_tagged*100:.0f}% cumulative)")

    # Relevance distribution
    cur.execute("""
        SELECT relevance, COUNT(*) FROM question_icd10
        GROUP BY relevance ORDER BY COUNT(*) DESC
    """)
    rel_out = cur.fetchall()
    total_rows = sum(r[1] for r in rel_out)

    print(f"\nRELEVANCE DISTRIBUTION (output question_icd10)")
    for rel, cnt in rel_out:
        print(f"  {rel:<12}: {cnt:>5} rows  ({cnt/total_rows*100:.1f}%)")

    # Compare to source distribution
    cur.execute("""
        SELECT relevance, COUNT(*) FROM article_icd10
        GROUP BY relevance ORDER BY COUNT(*) DESC
    """)
    rel_src = cur.fetchall()
    total_src = sum(r[1] for r in rel_src)

    print(f"\nRELEVANCE DISTRIBUTION (source article_icd10 — for comparison)")
    for rel, cnt in rel_src:
        print(f"  {rel:<12}: {cnt:>5} rows  ({cnt/total_src*100:.1f}%)")

    # Density flag: questions with unusually many codes
    cur.execute("""
        SELECT qid, COUNT(*) as cnt FROM question_icd10
        GROUP BY qid HAVING cnt > 12
        ORDER BY cnt DESC
    """)
    dense = cur.fetchall()
    if dense:
        print(f"\nDENSITY FLAGS (>12 codes — review these)")
        for qid, cnt in dense:
            print(f"  {qid}: {cnt} codes")
    else:
        print(f"\nDENSITY FLAGS: none (all questions <= 12 codes)")

    print("\n" + "=" * 60)


# ---------------------------------------------------------------------------
# TIER-AWARE CAP
# ---------------------------------------------------------------------------

def apply_related_cap(cur):
    """
    Cap 'related' codes at RELATED_CAP per question.
    Ranking: by contributing article frequency (descending), then icd10_code (alpha tiebreak).
    Primary and secondary codes are untouched.
    """
    cur.execute(f"""
        DELETE FROM question_icd10
        WHERE relevance = 'related'
          AND (qid || '|' || icd10_code) NOT IN (
              SELECT qid || '|' || icd10_code
              FROM (
                  SELECT
                      x.qid,
                      a.icd10_code,
                      ROW_NUMBER() OVER (
                          PARTITION BY x.qid
                          ORDER BY COUNT(DISTINCT x.article_id) DESC, a.icd10_code
                      ) AS rn
                  FROM qid_art_xref x
                  JOIN article_icd10 a  ON x.article_id = a.article_id
                  JOIN articles ar      ON x.article_id = ar.article_id
                  WHERE ar.source_type != 'Textbook'
                    AND a.relevance = 'related'
                  GROUP BY x.qid, a.icd10_code
              )
              WHERE rn <= {RELATED_CAP}
          )
    """)
    removed = cur.rowcount
    print(f"Related cap (top {RELATED_CAP} by frequency): removed {removed} related codes")
    return removed


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Build question_icd10 via article propagation")
    parser.add_argument("--dry-run", action="store_true",
                        help="Run QC only — no DB writes")
    args = parser.parse_args()

    print(f"DB: {DB_PATH}")
    if not DB_PATH.exists():
        print("ERROR: DB not found")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    try:
        if args.dry_run:
            print("DRY RUN — no writes will occur")
            print("\nPropagation preview (first 10 rows):")
            cur.execute(BEST_RELEVANCE_SQL + " LIMIT 10")
            for row in cur.fetchall():
                print(f"  {row[0]}  {row[1]}  {row[3]:<12}  {row[2][:60] if row[2] else ''}")

            cur.execute(f"SELECT COUNT(*) FROM ({BEST_RELEVANCE_SQL})")
            total = cur.fetchone()[0]
            print(f"\nWould insert {total} rows into question_icd10")
            return

        # --- CREATE TABLE ---
        cur.execute(CREATE_TABLE_SQL)

        # --- DROP EXISTING DATA (idempotent rebuild) ---
        cur.execute("DELETE FROM question_icd10")
        print("Cleared existing question_icd10 rows")

        # --- PROPAGATE ---
        print("Propagating ICD-10 codes from article_icd10 via qid_art_xref...")
        cur.execute(f"""
            INSERT INTO question_icd10 (qid, icd10_code, icd10_desc, relevance)
            {BEST_RELEVANCE_SQL}
        """)
        rows_inserted = cur.rowcount
        print(f"Inserted {rows_inserted} rows")

        # --- TIER-AWARE CAP ---
        apply_related_cap(cur)

        conn.commit()

        # --- QC ---
        qc_report(cur, rows_inserted)

        print("\nDone. Review QC above before proceeding to Batch API gap-fill.")

    except Exception as e:
        conn.rollback()
        print(f"\nERROR: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
