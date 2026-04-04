#!/usr/bin/env python3
"""
ite_check_columns.py

QA audit — checks for null/missing values in ITE pipeline CSV outputs.
Run after each pipeline step to catch silent gaps.

Usage:
    python ite_check_columns.py

Reads from: _archive_/02_question_bank/

Migrated from TEMP_06_ite_pipeline_TEMP (BATON 007)
"""

import pandas as pd
import os
from pathlib import Path

SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
QBANK_DIR    = PROJECT_ROOT / "_archive_" / "02_question_bank"

# CONFIG — add or remove entries as the pipeline evolves
# Each entry: (filename, [columns to null-check], preview_column)
PIPELINE_FILES = [
    (
        "ITE_2025_Raw.csv",
        ["QuestionStem", "CorrectAnswer", "Explanation"],
        "QuestionStem",
    ),
    (
        "ITE_2025_Categorized.csv",
        ["QuestionStem", "CorrectAnswer", "Explanation", "PrimaryCategory"],
        "QuestionStem",
    ),
    (
        "ABFM_ITE_Master.csv",
        ["QuestionStem", "CorrectAnswer", "Explanation", "PrimaryCategory"],
        "QuestionStem",
    ),
]


def audit_file(filename, check_cols, stem_col):
    file_path = QBANK_DIR / filename
    if not os.path.exists(file_path):
        print(f"\nWARNING  SKIPPED: {filename} not found at {file_path}")
        return

    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        print(f"\nERROR reading {filename}: {e}")
        return

    print(f"\n--- QA AUDIT: {filename} ---")
    print(f"Total Rows: {len(df)}")

    for col in check_cols:
        if col not in df.columns:
            print(f"  {col}: ERROR COLUMN MISSING")
            continue
        nulls = df[col].isna().sum()
        print(f"  {col}: {'OK CLEAN' if nulls == 0 else f'WARNING  {nulls} NULLS FOUND'}")

    if not df.empty and stem_col in df.columns:
        print(f"\n  --- CONTENT PREVIEW (row 1) ---")
        print(f"  ID:   {df.iloc[0].get('Question ID', df.iloc[0].get('id', 'N/A'))}")
        print(f"  Stem: {str(df.iloc[0][stem_col])[:200]}...")


def main():
    print(f"QA Audit — ITE Pipeline CSVs")
    print(f"Reading from: {QBANK_DIR}")
    for filename, check_cols, stem_col in PIPELINE_FILES:
        audit_file(filename, check_cols, stem_col)
    print("\n--- AUDIT COMPLETE ---")


if __name__ == "__main__":
    main()
