"""
backfill_aafp_article_icd10.py
================================
Fills article_icd10 entries for AAFP articles that have question links
but no existing ICD-10 coverage.

Data flow:
    aafp_question_icd10 -> aafp_qid_art_xref -> article_icd10

Mirror of build_ite_question_icd10.py (ITE side propagated articles -> questions;
AAFP side propagates questions -> articles).

Safety:
    - INSERT OR IGNORE: never overwrites existing article_icd10 entries.
      ITE articles already tagged are untouched even if AAFP questions cite them.
    - Only fills articles with zero existing article_icd10 rows.

Tier-aware cap (same as ITE script):
    - All primary + secondary codes kept.
    - Related codes capped at RELATED_CAP per article (ranked by question frequency).

QC output:
    - Articles filled vs. total AAFP articles
    - Gap log: articles with no question link (unreachable by propagation)
    - Codes-per-article distribution
    - Relevance distribution

Usage:
    python backfill_aafp_article_icd10.py            # full run
    python backfill_aafp_article_icd10.py --dry-run  # preview, no writes
"""

import sys
import sqlite3
import argparse
from pathlib import Path

# ---------------------------------------------------------------------------
# PATH SETUP
# ---------------------------------------------------------------------------
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH      = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"

# Cap: all primary + secondary kept; related capped per article by question frequency.
RELATED_CAP = 3

# ---------------------------------------------------------------------------
# PROPAGATION QUERY
# ---------------------------------------------------------------------------
# For each (article_id, icd10_code), take best relevance across linked questions.
# Only targets articles with ZERO existing article_icd10 rows.
PROPAGATE_SQL = """
SELECT
    article_id,
    icd10_code,
    icd10_desc,
    CASE MIN(relevance_rank)
        WHEN 0 THEN 'primary'
        WHEN 1 THEN 'secondary'
        WHEN 2 THEN 'related'
        ELSE 'related'
    END AS relevance
FROM (
    SELECT
        x.article_id,
        q.icd10_code,
        q.icd10_desc,
        CASE q.relevance
            WHEN 'primary'   THEN 0
            WHEN 'secondary' THEN 1
            WHEN 'related'   THEN 2
            ELSE 3
        END AS relevance_rank
    FROM aafp_qid_art_xref x
    JOIN aafp_question_icd10 q ON x.aafp_qid = q.aafp_qid
    WHERE x.article_id NOT IN (
        SELECT DISTINCT article_id FROM article_icd10
    )
)
GROUP BY article_id, icd10_code
ORDER BY article_id, MIN(relevance_rank), icd10_code
"""

# ---------------------------------------------------------------------------
# TIER-AWARE CAP
# ---------------------------------------------------------------------------

def apply_related_cap(cur):
    """
    Cap 'related' codes at RELATED_CAP per article.
    Ranked by how many AAFP questions contributed the code (most shared survives).
    Primary and secondary untouched.
    """
    # Only cap articles we just inserted (those NOT in article_icd10 before run).
    # Since we used INSERT OR IGNORE, new rows are only for previously-untagged articles.
    cur.execute(f"""
        DELETE FROM article_icd10
        WHERE relevance = 'related'
          AND article_id IN (
              SELECT DISTINCT x.article_id
              FROM aafp_qid_art_xref x
              LEFT JOIN (
                  SELECT DISTINCT article_id FROM article_icd10
                  WHERE relevance != 'related'
              ) existing ON x.article_id = existing.article_id
          )
          AND (article_id || '|' || icd10_code) NOT IN (
              SELECT article_id || '|' || icd10_code
              FROM (
                  SELECT
                      x.article_id,
                      q.icd10_code,
                      ROW_NUMBER() OVER (
                          PARTITION BY x.article_id
                          ORDER BY COUNT(DISTINCT x.aafp_qid) DESC, q.icd10_code
                      ) AS rn
                  FROM aafp_qid_art_xref x
                  JOIN aafp_question_icd10 q ON x.aafp_qid = q.aafp_qid
                  WHERE q.relevance = 'related'
                  GROUP BY x.article_id, q.icd10_code
              )
              WHERE rn <= {RELATED_CAP}
          )
    """)
    removed = cur.rowcount
    print(f"Related cap (top {RELATED_CAP} by frequency): removed {removed} related codes")
    return removed


# ---------------------------------------------------------------------------
# QC REPORT
# ---------------------------------------------------------------------------

def qc_report(cur, rows_inserted):
    print("\n" + "=" * 60)
    print("QC REPORT -- backfill_aafp_article_icd10")
    print("=" * 60)

    # Total AAFP articles (ART-1398+)
    cur.execute("""
        SELECT COUNT(*) FROM articles
        WHERE CAST(REPLACE(article_id, 'ART-', '') AS INTEGER) >= 1398
    """)
    total_aafp = cur.fetchone()[0]

    # Articles now tagged (have at least one entry from this backfill)
    cur.execute("""
        SELECT COUNT(DISTINCT x.article_id)
        FROM aafp_qid_art_xref x
        JOIN article_icd10 a ON x.article_id = a.article_id
        WHERE CAST(REPLACE(x.article_id, 'ART-', '') AS INTEGER) >= 1398
    """)
    tagged = cur.fetchone()[0]

    # Articles still unreachable (no question link)
    cur.execute("""
        SELECT COUNT(*) FROM articles
        WHERE CAST(REPLACE(article_id, 'ART-', '') AS INTEGER) >= 1398
          AND article_id NOT IN (SELECT DISTINCT article_id FROM aafp_qid_art_xref)
    """)
    no_link = cur.fetchone()[0]

    print(f"\nCOVERAGE (AAFP articles ART-1398+)")
    print(f"  Total AAFP articles         : {total_aafp}")
    print(f"  Now have ICD-10 (via xref)  : {tagged}")
    print(f"  Still no ICD-10 (no link)   : {no_link}")
    print(f"  Rows inserted               : {rows_inserted}")

    # Codes per article
    cur.execute("""
        SELECT codes_per_art, COUNT(*) as num_articles
        FROM (
            SELECT a.article_id, COUNT(*) as codes_per_art
            FROM article_icd10 a
            JOIN aafp_qid_art_xref x ON a.article_id = x.article_id
            WHERE CAST(REPLACE(a.article_id, 'ART-', '') AS INTEGER) >= 1398
            GROUP BY a.article_id
        )
        GROUP BY codes_per_art ORDER BY codes_per_art
    """)
    dist = cur.fetchall()
    if dist:
        print(f"\nCODES PER ARTICLE DISTRIBUTION (newly filled)")
        total = sum(r[1] for r in dist)
        cumulative = 0
        for cnt, num in dist:
            cumulative += num
            print(f"  {cnt:>2} codes: {num:>3} articles  ({cumulative/total*100:.0f}% cumulative)")

    # Relevance distribution of new rows
    cur.execute("""
        SELECT a.relevance, COUNT(*) FROM article_icd10 a
        WHERE CAST(REPLACE(a.article_id, 'ART-', '') AS INTEGER) >= 1398
        GROUP BY a.relevance ORDER BY COUNT(*) DESC
    """)
    rel = cur.fetchall()
    if rel:
        total_rel = sum(r[1] for r in rel)
        print(f"\nRELEVANCE DISTRIBUTION (new AAFP article entries)")
        for r, cnt in rel:
            print(f"  {r:<12}: {cnt:>4}  ({cnt/total_rel*100:.1f}%)")

    print("\n" + "=" * 60)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Backfill article_icd10 for AAFP articles via question propagation"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview only — no DB writes")
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
            cur.execute(PROPAGATE_SQL + " LIMIT 10")
            for row in cur.fetchall():
                print(f"  {row[0]}  {row[1]}  {row[3]:<12}  {str(row[2])[:60]}")
            cur.execute(f"SELECT COUNT(*) FROM ({PROPAGATE_SQL})")
            total = cur.fetchone()[0]
            print(f"\nWould insert up to {total} rows into article_icd10")
            return

        # --- PROPAGATE (INSERT OR IGNORE: never touches existing entries) ---
        print("Propagating aafp_question_icd10 -> aafp_qid_art_xref -> article_icd10...")
        cur.execute(f"""
            INSERT OR IGNORE INTO article_icd10 (article_id, icd10_code, icd10_desc, relevance)
            {PROPAGATE_SQL}
        """)
        rows_inserted = cur.rowcount
        print(f"Inserted {rows_inserted} rows (existing entries untouched)")

        # --- TIER-AWARE CAP ---
        apply_related_cap(cur)

        conn.commit()

        # --- QC ---
        qc_report(cur, rows_inserted)

        print("\nDone.")
        print(f"Note: Articles with no question link (~362) remain untagged.")
        print(f"Those require content-based tagging (API) — deferred.")

    except Exception as e:
        conn.rollback()
        print(f"\nERROR: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
