#!/usr/bin/env python3
"""
aafp_question_reuse_investigation.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Investigates AAFP BRQ questions that are likely reused or paraphrased
in the ITE exam, using pre-computed ite_nearest_dist cosine distances.

Distance thresholds:
  < 0.22  → HIGH suspicion (likely verbatim or near-verbatim)
  0.22–0.27 → MODERATE suspicion (likely paraphrased)
  0.27–0.30 → LOW suspicion (possibly related topic)

Usage:
  python aafp_question_reuse_investigation.py
  python aafp_question_reuse_investigation.py --full    ← show all stems (not just < 0.22)
  python aafp_question_reuse_investigation.py --csv     ← save results to CSV

Run from Windows (NTFS):
  cd 00_#PROJECT_OVERHAUL
  python 03_module.3_analyst/scripts/aafp_question_reuse_investigation.py
"""

import csv
import sqlite3
import sys
from pathlib import Path

SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH      = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"

SHOW_FULL    = "--full" in sys.argv
SAVE_CSV     = "--csv"  in sys.argv

# Distance buckets
THRESH_HIGH  = 0.22
THRESH_MOD   = 0.27
THRESH_LOW   = 0.30


def bucket(dist):
    if dist < THRESH_HIGH:
        return "HIGH"
    elif dist < THRESH_MOD:
        return "MODERATE"
    else:
        return "LOW"


def truncate(text, n=120):
    if not text:
        return "(none)"
    text = text.strip()
    return text[:n] + "..." if len(text) > n else text


def main():
    if not DB_PATH.exists():
        print("ERROR: DB not found:", DB_PATH)
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # ── Pull all AAFP questions with ite_nearest_dist < threshold ─────────────
    cur.execute("""
        SELECT
            aq.aafp_qid,
            aq.stem               AS aafp_stem,
            aq.ite_nearest_qid    AS ite_qid,
            aq.ite_nearest_dist   AS dist,
            aq.body_system,
            q.question_text       AS ite_stem,
            q.exam_year           AS ite_year,
            q.body_system         AS category
        FROM aafp_questions aq
        LEFT JOIN questions q ON q.qid = aq.ite_nearest_qid
        WHERE aq.ite_nearest_dist IS NOT NULL
          AND aq.ite_nearest_dist < ?
        ORDER BY aq.ite_nearest_dist ASC
    """, (THRESH_LOW,))

    rows = cur.fetchall()
    conn.close()

    if not rows:
        print("No results found. Check that ite_nearest_dist is populated.")
        sys.exit(0)

    # ── Bucket summary ─────────────────────────────────────────────────────────
    high  = [r for r in rows if r["dist"] < THRESH_HIGH]
    mod   = [r for r in rows if THRESH_HIGH <= r["dist"] < THRESH_MOD]
    low   = [r for r in rows if THRESH_MOD  <= r["dist"] < THRESH_LOW]

    print()
    print("=" * 70)
    print("  AAFP QUESTION REUSE INVESTIGATION")
    print("=" * 70)
    print()
    print("  Distance buckets (ite_nearest_dist):")
    print("    HIGH     < 0.22  :", len(high),  "pairs  ← likely verbatim/near-verbatim")
    print("    MODERATE 0.22–0.27:", len(mod),  "pairs  ← likely paraphrased")
    print("    LOW      0.27–0.30:", len(low),  "pairs  ← possibly same topic")
    print()
    print("  TOTAL pairs < 0.30 :", len(rows))
    print()

    # ── HIGH suspicion pairs — full stems ──────────────────────────────────────
    show_full_cutoff = THRESH_LOW if SHOW_FULL else THRESH_HIGH
    show_rows = [r for r in rows if r["dist"] < show_full_cutoff]

    if show_rows:
        label = "ALL PAIRS < 0.30" if SHOW_FULL else "HIGH-SUSPICION PAIRS (dist < 0.22)"
        print("=" * 70)
        print(" ", label)
        print("=" * 70)

        for i, r in enumerate(show_rows, 1):
            dist_val = r["dist"]
            bkt      = bucket(dist_val)
            ite_yr   = r["ite_year"] or "?"
            lag_str  = "ITE yr=" + str(ite_yr)

            print()
            print("  [{:03d}]  dist={:.4f}  [{}]  body_system={}".format(
                i, dist_val, bkt, r["body_system"] or "?"
            ))
            print("  AAFP {}   ITE {}  ({})".format(
                r["aafp_qid"],
                r["ite_qid"] or "?",
                lag_str
            ))
            print()
            print("  AAFP STEM:")
            print("    " + (r["aafp_stem"] or "(none)").strip().replace("\n", "\n    "))
            print()
            print("  ITE  STEM:")
            print("    " + (r["ite_stem"] or "(none)").strip().replace("\n", "\n    "))
            print()
            print("  " + "-" * 66)

    # ── Summary table — all pairs (truncated) ──────────────────────────────────
    print()
    print("=" * 70)
    print("  FULL LIST (truncated stems)")
    print("=" * 70)
    print()
    header = "{:<6} {:<8} {:<10} {:<20} {:<8} {:}"
    print(header.format("RANK", "DIST", "BUCKET", "AAFP_QID", "ITE_YR", "BODY_SYSTEM"))
    print("  " + "-" * 66)

    for i, r in enumerate(rows, 1):
        print("{:<6} {:.4f}  {:<10} {:<20} {:<8} {}".format(
            i,
            r["dist"],
            bucket(r["dist"]),
            r["aafp_qid"],
            r["ite_year"]   or "?",
            r["body_system"] or "?"
        ))
        print("       AAFP: " + truncate(r["aafp_stem"], 80))
        print("       ITE:  " + truncate(r["ite_stem"],  80))
        print()

    # ── Year-lag distribution (only HIGH + MOD) ────────────────────────────────
    # aafp_questions has no year column — skip lag distribution
    lag_counts = {}
    if lag_counts:
        print("=" * 70)
        print("  YEAR-LAG DISTRIBUTION (HIGH + MODERATE pairs)")
        print("  (positive = ITE question came AFTER AAFP BRQ)")
        print("=" * 70)
        for lag in sorted(lag_counts):
            bar = "#" * lag_counts[lag]
            print("  {:+3}yr : {} ({})".format(lag, bar, lag_counts[lag]))
        print()

    # ── CSV output ─────────────────────────────────────────────────────────────
    if SAVE_CSV:
        csv_path = PROJECT_ROOT / "00_database" / "readable_db_files" / "aafp_question_reuse_20260328.csv"
        fieldnames = [
            "rank", "dist", "bucket", "aafp_qid",
            "ite_nearest_qid", "ite_year", "body_system", "category",
            "aafp_stem", "ite_stem"
        ]
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for i, r in enumerate(rows, 1):
                writer.writerow({
                    "rank":             i,
                    "dist":             round(r["dist"], 6),
                    "bucket":           bucket(r["dist"]),
                    "aafp_qid":         r["aafp_qid"],
                    "ite_nearest_qid":  r["ite_qid"]  or "",
                    "ite_year":         r["ite_year"]  or "",
                    "body_system":      r["body_system"] or "",
                    "category":         r["category"]  or "",
                    "aafp_stem":        (r["aafp_stem"] or "").strip(),
                    "ite_stem":         (r["ite_stem"]  or "").strip(),
                })
        print("CSV saved:", csv_path)
        print()

    print("Done.")


if __name__ == "__main__":
    main()
