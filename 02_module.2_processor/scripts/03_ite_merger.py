#!/usr/bin/env python3
"""
03_ite_merger.py

Merges a categorized new-year ITE CSV into the multi-year master bank.

Usage:
    python 03_ite_merger.py --year 2025
    python 03_ite_merger.py --year 2026

Reads:  archive_canonical/02_question_bank/ITE_{YEAR}_Categorized.csv
        archive_canonical/02_question_bank/ABFM_ITE_Master.csv
Writes: archive_canonical/02_question_bank/ABFM_ITE_Master.csv (updated)

Migrated from TEMP_06_ite_pipeline_TEMP (BATON 007)
"""

import argparse
import pandas as pd
from pathlib import Path

SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
QBANK_DIR    = PROJECT_ROOT / "archive_canonical" / "02_question_bank"

# CONFIG
EXAM_YEAR = "2025"


def merge_year(year):
    incoming_path = QBANK_DIR / f"ITE_{year}_Categorized.csv"
    master_path   = QBANK_DIR / "ABFM_ITE_Master.csv"

    if not incoming_path.exists():
        print(f"ERROR: Incoming file not found: {incoming_path}")
        return

    incoming = pd.read_csv(incoming_path, dtype=str)

    if not master_path.exists():
        print(f"INFO: No master bank found — creating from {incoming_path.name}")
        incoming.to_csv(master_path, index=False)
        print(f"OK: {len(incoming)} questions written to {master_path}")
        return

    master = pd.read_csv(master_path, dtype=str)

    cols = ["Question ID", "ExamYear", "QuestionStem", "CorrectAnswer",
            "Explanation", "PrimaryCategory"]
    for df in (master, incoming):
        for c in cols:
            if c not in df.columns:
                df[c] = ""
        # keep only known cols that exist
        existing = [c for c in cols if c in df.columns]
        df[existing] = df[existing]

    by_id = {}
    for _, r in master.iterrows():
        by_id[str(r.get("Question ID", ""))] = r.to_dict()
    for _, r in incoming.iterrows():
        rid = str(r.get("Question ID", ""))
        by_id[rid] = r.to_dict()   # incoming wins on conflict

    merged = pd.DataFrame(by_id.values())
    try:
        merged = merged.sort_values("Question ID")
    except Exception:
        pass

    merged.to_csv(master_path, index=False, encoding="utf-8")
    print(f"OK: Merged -> {master_path} ({len(merged)} total rows, {len(incoming)} new)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", default=EXAM_YEAR)
    args = ap.parse_args()
    merge_year(args.year)


if __name__ == "__main__":
    main()
