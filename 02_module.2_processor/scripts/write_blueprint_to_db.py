#!/usr/bin/env python3
"""
write_blueprint_to_db.py
Reads blueprint_classifications_v2.xlsx and writes the blueprint labels
for 2020-2023 ITE questions into the questions.blueprint column.

Run from Windows after blueprint_api_classifier_v2.py has completed.

Usage:
    python 02_module.2_processor\\scripts\\write_blueprint_to_db.py
    python 02_module.2_processor\\scripts\\write_blueprint_to_db.py --dry-run
"""

import sqlite3
import argparse
import re
import pandas as pd
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH      = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"
INPUT_XLSX   = PROJECT_ROOT / "02_module.2_processor" / "source" / "blueprint_classifications_v2.xlsx"

# ── Category name normalization ────────────────────────────────────────────────
VALID_CATEGORIES = {
    "Acute Care and Diagnosis",
    "Chronic Care Management",
    "Emergent and Urgent Care",
    "Preventive Care",
    "Foundations of Care",
}


def derive_db_qid(xlsx_qid: str, year: int) -> str:
    """
    xlsx uses sequential numbering across years:
      2020: Q2020-001 to Q2020-200  → DB QID-2020-0001 to QID-2020-0200
      2021: Q2021-201 to Q2021-400  → DB QID-2021-0001 to QID-2021-0200
      2022: Q2022-401 to Q2022-600  → DB QID-2022-0001 to QID-2022-0200
      2023: Q2023-601 to Q2023-800  → DB QID-2023-0001 to QID-2023-0200
    """
    seq_num = int(xlsx_qid.split("-")[-1])
    offset = (year - 2020) * 200
    db_qnum = seq_num - offset
    return f"QID-{year}-{db_qnum:04d}"


def normalize_text(text: str) -> str:
    """Normalize text for lightweight workbook/DB consistency checks."""
    collapsed = re.sub(r"\s+", " ", (text or "").strip()).lower()
    return re.sub(r"[^a-z0-9]+", "", collapsed)


def text_matches_db(workbook_text: str, db_text: str) -> bool:
    """Return True when the workbook row clearly corresponds to the DB row."""
    workbook_norm = normalize_text(workbook_text)
    db_norm = normalize_text(db_text)
    if not workbook_norm or not db_norm:
        return False
    probe_len = min(120, len(workbook_norm), len(db_norm))
    if probe_len < 40:
        return False
    return (
        workbook_norm.startswith(db_norm[:probe_len]) or
        db_norm.startswith(workbook_norm[:probe_len]) or
        workbook_norm[:probe_len] in db_norm or
        db_norm[:probe_len] in workbook_norm
    )


def main():
    parser = argparse.ArgumentParser(description="Write blueprint labels to DB")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be written without touching the DB")
    parser.add_argument("--years", nargs="+", type=int,
                        default=[2020, 2021, 2022, 2023],
                        help="Which exam years to update (default: 2020 2021 2022 2023)")
    args = parser.parse_args()

    # ── Load classifications ───────────────────────────────────────────────────
    print(f"Loading: {INPUT_XLSX}")
    clf = pd.read_excel(INPUT_XLSX)
    clf["year"] = clf["year"].astype(int)
    clf = clf[clf["year"].isin(args.years)].copy()
    print(f"  {len(clf)} rows for years {args.years}")

    # Validate all categories
    bad = clf[~clf["blueprint_category"].isin(VALID_CATEGORIES)]
    if len(bad):
        print(f"\nERROR: {len(bad)} rows have unrecognized categories:")
        print(bad[["question_id", "blueprint_category"]].to_string())
        return

    if "db_qid" not in clf.columns:
        print("  Workbook missing db_qid column; deriving legacy qids from question_id.")
        clf["db_qid"] = clf.apply(
            lambda r: derive_db_qid(r["question_id"], r["year"]), axis=1
        )
    clf["db_qid"] = clf["db_qid"].fillna("").astype(str).str.strip()

    if "db_match_status" not in clf.columns:
        clf["db_match_status"] = "legacy_unverified"

    if "question_stem" in clf.columns:
        clf["question_stem"] = clf["question_stem"].fillna("").astype(str)
    else:
        clf["question_stem"] = ""

    # ── Connect to DB ──────────────────────────────────────────────────────────
    print(f"\nConnecting to DB: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Verify DB has the right questions
    cur.execute(
        "SELECT exam_year, COUNT(*) FROM questions "
        "WHERE exam_year IN (2020,2021,2022,2023) GROUP BY exam_year ORDER BY exam_year"
    )
    db_counts = dict(cur.fetchall())
    print(f"  DB question counts: {db_counts}")

    db_rows = cur.execute(
        "SELECT qid, exam_year, question_text FROM questions "
        "WHERE exam_year IN (2020,2021,2022,2023)"
    ).fetchall()
    db_by_qid = {
        qid: {"exam_year": exam_year, "question_text": question_text or ""}
        for qid, exam_year, question_text in db_rows
    }

    clf["db_exists"] = clf["db_qid"].isin(db_by_qid)
    clf["text_verified"] = clf.apply(
        lambda r: (
            text_matches_db(r["question_stem"], db_by_qid[r["db_qid"]]["question_text"])
            if r["db_exists"] and r["question_stem"]
            else False
        ),
        axis=1
    )
    print(
        "  Workbook qid coverage: "
        f"{int(clf['db_exists'].sum())}/{len(clf)} rows matched a live DB qid"
    )
    if len(clf):
        verified = int((clf["db_exists"] & clf["text_verified"]).sum())
        print(f"  Stem verification: {verified}/{int(clf['db_exists'].sum())} matched rows")

    missing_qids = clf[~clf["db_exists"]]
    if len(missing_qids):
        print("\nRows with no matching DB qid:")
        for _, row in missing_qids.head(10).iterrows():
            print(f"  {row['question_id']} -> {row['db_qid'] or 'NO DB QID'}")

    # Spot-check: verify QID mapping resolves to real DB records
    print("\nSpot-checking QID mapping...")
    sample = clf[clf["db_exists"]].groupby("year").head(2)
    for _, row in sample.iterrows():
        db_row = db_by_qid[row["db_qid"]]
        xlsx_stem = str(row.get("question_stem", ""))[:60].replace("\n", " ")
        db_stem   = str(db_row["question_text"])[:60].replace("\n", " ")
        match = "OK" if row["text_verified"] else "WARN"
        print(f"  [{match}] {row['question_id']} -> {row['db_qid']} | DB: {row['db_qid']}")
        print(f"      xlsx stem: {xlsx_stem}")
        print(f"      db   stem: {db_stem}")

    # ── Current blueprint coverage ─────────────────────────────────────────────
    cur.execute(
        "SELECT exam_year, blueprint, COUNT(*) FROM questions "
        "WHERE exam_year IN (2020,2021,2022,2023) "
        "GROUP BY exam_year, blueprint ORDER BY exam_year, blueprint"
    )
    print("\nCurrent DB blueprint distribution (2020-2023):")
    for row in cur.fetchall():
        print(f"  {row}")

    to_write = clf[clf["db_exists"]].copy()

    if args.dry_run:
        print("\n[DRY RUN] Would write the following distribution:")
        print(to_write["blueprint_category"].value_counts().to_string())
        print(f"\n[DRY RUN] Rows skipped due to missing DB qid: {len(clf) - len(to_write)}")
        conn.close()
        return

    # ── Write to DB ────────────────────────────────────────────────────────────
    print(f"\nWriting {len(to_write)} blueprint labels to DB...")
    updated = 0
    not_found = []

    for _, row in to_write.iterrows():
        result = cur.execute(
            "UPDATE questions SET blueprint=? WHERE qid=?",
            (row["blueprint_category"], row["db_qid"])
        )
        if result.rowcount == 1:
            updated += 1
        else:
            not_found.append(row["question_id"])

    conn.commit()
    print(f"  Updated {updated} rows")
    if not_found:
        print(f"  Unmatched QIDs: {len(not_found)} -> {not_found[:10]}")

    # ── Post-write QC ──────────────────────────────────────────────────────────
    print("\nPost-write QC - blueprint distribution by year:")
    cur.execute(
        "SELECT exam_year, blueprint, COUNT(*) as n "
        "FROM questions "
        "WHERE exam_year IN (2020,2021,2022,2023) "
        "GROUP BY exam_year, blueprint "
        "ORDER BY exam_year, blueprint"
    )
    rows = cur.fetchall()
    current_year = None
    year_total = 0
    for r in rows:
        if r[0] != current_year:
            if current_year is not None:
                year_n = db_counts.get(current_year, year_total)
                print(f"    Total: {year_total}/{year_n}")
            current_year = r[0]
            year_total = 0
            print(f"\n  Year {r[0]}:")
        year_n = db_counts.get(r[0], 200)
        pct = r[2] / year_n * 100
        print(f"    {r[1]}: {r[2]} ({pct:.1f}%)")
        year_total += r[2]
    if current_year is not None:
        year_n = db_counts.get(current_year, year_total)
        print(f"    Total: {year_total}/{year_n}")

    # Column-level coverage check
    print("\nColumn coverage check:")
    cur.execute(
        "SELECT exam_year, "
        "COUNT(*) as total, "
        "SUM(CASE WHEN blueprint IS NOT NULL THEN 1 ELSE 0 END) as filled "
        "FROM questions "
        "WHERE exam_year IN (2018,2019,2020,2021,2022,2023,2024,2025) "
        "GROUP BY exam_year ORDER BY exam_year"
    )
    for r in cur.fetchall():
        status = "ok" if r[1] == r[2] else f"{r[1]-r[2]} missing"
        print(f"  {r[0]}: {r[2]}/{r[1]} filled [{status}]")

    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
