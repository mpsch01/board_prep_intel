"""
update_citation_trends.py  v1
==============================
Populate / refresh the article_citation_trend companion table.

Source:  qid_art_xref (article_id + exam_year per question-article link)
Output:  article_citation_trend (one row per article that has ever been cited)

Run:
    python update_citation_trends.py            # full refresh
    python update_citation_trends.py --report   # print top watch-list after refresh

Trigger:
    After each new exam year is integrated into qid_art_xref.
    Also safe to run at any time — always does a full DELETE + re-insert.

Computed fields:
    years_cited         comma-separated sorted distinct exam years  e.g. "2022,2023,2025"
    distinct_year_count count of those years
    first_cited_year    earliest exam year
    most_recent_year    most recent exam year
    consecutive_streak  length of unbroken streak ending at most_recent_year
                        e.g. years [2020,2022,2023,2024,2025] → streak = 4
    is_watch_list       1 if consecutive_streak >= 2, else 0
"""

import sqlite3
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent          # maintain/ → scripts/ → M1/ → root
DB_PATH      = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"

WATCH_THRESHOLD = 2   # consecutive years to earn watch-list status


# ── Core logic ─────────────────────────────────────────────────────────────────
def compute_streak(sorted_years: list[int]) -> int:
    """
    Longest unbroken consecutive streak ending at the most recent year.
    e.g. [2020, 2022, 2023, 2024, 2025] → 4  (2022-2025 consecutive)
         [2020, 2021]                    → 2
         [2020]                          → 1
         [2018, 2020, 2022]              → 1  (no streak at tail)
    """
    if not sorted_years:
        return 0
    streak = 1
    for i in range(len(sorted_years) - 1, 0, -1):
        if sorted_years[i] - sorted_years[i - 1] == 1:
            streak += 1
        else:
            break
    return streak


def build_trend_rows(conn: sqlite3.Connection) -> list[tuple]:
    """
    Pull all article_id + exam_year pairs from qid_art_xref,
    compute trend fields per article, return as list of tuples
    ready for INSERT.
    """
    cur = conn.cursor()
    cur.execute("""
        SELECT article_id, exam_year
        FROM   qid_art_xref
        WHERE  article_id IS NOT NULL
        ORDER  BY article_id, exam_year
    """)

    # Aggregate years per article
    article_years: dict[str, set[int]] = {}
    for article_id, exam_year in cur.fetchall():
        if exam_year is not None:
            article_years.setdefault(article_id, set()).add(int(exam_year))

    rows = []
    for article_id, year_set in article_years.items():
        years_sorted        = sorted(year_set)
        distinct_year_count = len(years_sorted)
        first_cited_year    = years_sorted[0]
        most_recent_year    = years_sorted[-1]
        consecutive_streak  = compute_streak(years_sorted)
        is_watch_list       = 1 if consecutive_streak >= WATCH_THRESHOLD else 0
        years_cited         = ",".join(str(y) for y in years_sorted)

        rows.append((
            article_id,
            years_cited,
            distinct_year_count,
            first_cited_year,
            most_recent_year,
            consecutive_streak,
            is_watch_list,
        ))

    return rows


# ── DB write ───────────────────────────────────────────────────────────────────
def refresh(conn: sqlite3.Connection) -> int:
    """Full DELETE + re-insert. Returns count of rows written."""
    cur = conn.cursor()
    cur.execute("DELETE FROM article_citation_trend")

    rows = build_trend_rows(conn)

    cur.executemany("""
        INSERT INTO article_citation_trend
            (article_id, years_cited, distinct_year_count,
             first_cited_year, most_recent_year, consecutive_streak, is_watch_list)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, rows)

    conn.commit()
    return len(rows)


# ── Report ─────────────────────────────────────────────────────────────────────
def print_report(conn: sqlite3.Connection):
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM article_citation_trend")
    total = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM article_citation_trend WHERE is_watch_list=1")
    watch = cur.fetchone()[0]

    cur.execute("""
        SELECT MAX(distinct_year_count), MAX(consecutive_streak)
        FROM article_citation_trend
    """)
    max_yrs, max_streak = cur.fetchone()

    print(f"\n{'='*55}")
    print(f"  article_citation_trend — Summary")
    print(f"{'='*55}")
    print(f"  Articles tracked      : {total}")
    print(f"  On watch list (≥{WATCH_THRESHOLD}yr) : {watch}  ({watch/total*100:.1f}%)")
    print(f"  Max years cited       : {max_yrs}")
    print(f"  Max consecutive streak: {max_streak}")

    print(f"\n  {'─'*50}")
    print(f"  Distribution by distinct_year_count:")
    cur.execute("""
        SELECT distinct_year_count, COUNT(*) as n
        FROM article_citation_trend
        GROUP BY distinct_year_count
        ORDER BY distinct_year_count DESC
    """)
    for cnt, n in cur.fetchall():
        bar = '█' * min(n // 5, 40)
        print(f"    {cnt} year(s) : {n:4d}  {bar}")

    print(f"\n  {'─'*50}")
    print(f"  Top 20 by consecutive streak (watch list leaders):")
    cur.execute("""
        SELECT a.article_id, act.years_cited, act.consecutive_streak,
               act.distinct_year_count, a.clean_ref
        FROM article_citation_trend act
        JOIN articles a ON a.article_id = act.article_id
        ORDER BY act.consecutive_streak DESC, act.distinct_year_count DESC
        LIMIT 20
    """)
    print(f"  {'ART-ID':<12} {'Streak':>6}  {'Yrs':>3}  Years             Ref (truncated)")
    print(f"  {'-'*80}")
    for art_id, years, streak, yr_cnt, clean_ref in cur.fetchall():
        ref_short = (clean_ref or '')[:55]
        print(f"  {art_id:<12} {streak:>6}  {yr_cnt:>3}  {years:<18}  {ref_short}")

    print(f"{'='*55}\n")


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Refresh article_citation_trend from qid_art_xref."
    )
    parser.add_argument('--report', action='store_true',
                        help="Print summary report after refresh")
    args = parser.parse_args()

    print(f"Connecting to {DB_PATH.name}...")
    conn = sqlite3.connect(DB_PATH)

    print("Refreshing article_citation_trend...")
    count = refresh(conn)
    print(f"  {count} articles written.")

    if args.report:
        print_report(conn)

    conn.close()
    print("Done.")


if __name__ == '__main__':
    main()
