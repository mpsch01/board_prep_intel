"""
build_xref_2018_2019.py

Populates qid_art_xref for exam years 2018 and 2019.

Root cause of gap: qid_art_xref was never populated for these years.
The data is complete — 653/653 question_ref_pairs rows for 2018-2019
join cleanly to articles on clean_ref (confirmed pre-run analysis).

Inserts:
    INSERT INTO qid_art_xref (qid, article_id, tier, exam_year, author1, year)
    SELECT DISTINCT qrp.qid, a.article_id, qrp.tier, qrp.exam_year, a.author1, a.year
    FROM question_ref_pairs qrp
    JOIN articles a ON qrp.clean_ref = a.clean_ref
    WHERE qrp.exam_year IN (2018, 2019)
    AND NOT EXISTS (existing row check)

Run from 02_module.2_processor/:
    python scripts/build_xref_2018_2019.py
    python scripts/build_xref_2018_2019.py --dry-run
"""

import argparse
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH      = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"
LOG_DIR      = PROJECT_ROOT / "00_database" / "logs"


def main():
    parser = argparse.ArgumentParser(description="Populate qid_art_xref for 2018-2019")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview inserts without writing to DB")
    args = parser.parse_args()

    if not DB_PATH.exists():
        print(f"ERROR: DB not found at {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # ── Pre-run counts ──────────────────────────────────────────────────────
    cur.execute("SELECT exam_year, COUNT(*) FROM qid_art_xref "
                "WHERE exam_year IN (2018, 2019) GROUP BY exam_year")
    pre_counts = {r[0]: r[1] for r in cur.fetchall()}

    print("=" * 60)
    print("build_xref_2018_2019.py")
    print(f"  DB        : {DB_PATH}")
    print(f"  Dry run   : {args.dry_run}")
    print(f"  Pre-run qid_art_xref counts:")
    print(f"    2018: {pre_counts.get(2018, 0)}")
    print(f"    2019: {pre_counts.get(2019, 0)}")
    print("=" * 60)

    # ── Build insert candidates ─────────────────────────────────────────────
    cur.execute("""
        SELECT DISTINCT
            qrp.qid,
            a.article_id,
            qrp.tier,
            qrp.exam_year,
            a.author1,
            a.year
        FROM question_ref_pairs qrp
        JOIN articles a ON qrp.clean_ref = a.clean_ref
        WHERE qrp.exam_year IN (2018, 2019)
          AND NOT EXISTS (
              SELECT 1 FROM qid_art_xref x
              WHERE x.qid = qrp.qid AND x.article_id = a.article_id
          )
        ORDER BY qrp.exam_year, qrp.qid
    """)
    candidates = cur.fetchall()

    print(f"  Rows to insert: {len(candidates)}")

    # ── Year breakdown preview ──────────────────────────────────────────────
    by_year = {}
    for row in candidates:
        y = row["exam_year"]
        by_year[y] = by_year.get(y, 0) + 1
    for yr in sorted(by_year):
        print(f"    {yr}: {by_year[yr]} rows")

    # ── QID coverage preview ────────────────────────────────────────────────
    qids_covered = set(r["qid"] for r in candidates)
    cur.execute("SELECT COUNT(DISTINCT qid) FROM questions WHERE exam_year IN (2018, 2019)")
    total_qids = cur.fetchone()[0]
    print(f"  QIDs covered: {len(qids_covered)} / {total_qids}")

    if args.dry_run:
        print("\n  [DRY RUN] No changes written.")
        print("\n  Sample rows:")
        for row in candidates[:5]:
            print(f"    {row['qid']} | {row['article_id']} | {row['tier']} | {row['exam_year']}")
        conn.close()
        return

    # ── Insert ──────────────────────────────────────────────────────────────
    cur.executemany("""
        INSERT OR IGNORE INTO qid_art_xref (qid, article_id, tier, exam_year, author1, year)
        VALUES (?, ?, ?, ?, ?, ?)
    """, [(r["qid"], r["article_id"], r["tier"], r["exam_year"],
           r["author1"], r["year"]) for r in candidates])

    inserted = cur.rowcount
    conn.commit()

    # ── Post-run counts ─────────────────────────────────────────────────────
    cur.execute("SELECT exam_year, COUNT(*) FROM qid_art_xref "
                "WHERE exam_year IN (2018, 2019) GROUP BY exam_year")
    post_counts = {r[0]: r[1] for r in cur.fetchall()}

    print(f"\n  INSERT COMPLETE")
    print(f"  Rows inserted : {len(candidates)}")
    print(f"  Post-run qid_art_xref counts:")
    print(f"    2018: {pre_counts.get(2018, 0)} → {post_counts.get(2018, 0)}")
    print(f"    2019: {pre_counts.get(2019, 0)} → {post_counts.get(2019, 0)}")

    # ── Write log ───────────────────────────────────────────────────────────
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"build_xref_2018_2019_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(log_path, "w") as f:
        f.write(f"build_xref_2018_2019.py\n")
        f.write(f"Run: {datetime.now().isoformat()}\n")
        f.write(f"Inserted: {len(candidates)}\n")
        f.write(f"2018: {pre_counts.get(2018,0)} -> {post_counts.get(2018,0)}\n")
        f.write(f"2019: {pre_counts.get(2019,0)} -> {post_counts.get(2019,0)}\n")
        f.write(f"QIDs covered: {len(qids_covered)} / {total_qids}\n")
    print(f"  Log: {log_path}")

    conn.close()


if __name__ == "__main__":
    main()
