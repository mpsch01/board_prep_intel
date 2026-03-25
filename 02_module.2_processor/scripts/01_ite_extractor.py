#!/usr/bin/env python3
"""
01_ite_extractor.py

Extracts questions and explanations from ABFM ITE Questions + Critique PDFs
for a single exam year. Outputs a raw CSV to archive_canonical/02_question_bank/.

Usage:
    python 01_ite_extractor.py                    # uses EXAM_YEAR constant below
    python 01_ite_extractor.py --year 2026        # override year

Source PDFs expected in: 02_module.2_processor/source/ite_source/
  {YEAR}_ITE_Questions.pdf
  {YEAR}_ITE_Critique.pdf

Output: archive_canonical/02_question_bank/ITE_{YEAR}_Raw.csv

Migrated from TEMP_06_ite_pipeline_TEMP (BATON 007)
"""

import re
import argparse
import pandas as pd
import os
import pdfplumber
from pathlib import Path

SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
ITE_SOURCE   = PROJECT_ROOT / "02_module.2_processor" / "source" / "ite_source"
QBANK_DIR    = PROJECT_ROOT / "archive_canonical" / "02_question_bank"

# CONFIG — update for each new exam year (or override with --year)
EXAM_YEAR = "2025"


def extract_from_pdf(q_path, c_path, year="2025"):
    questions_data = {}
    q_header_regex  = re.compile(r'^(\d+)\.\s+(.*)')
    answer_choice_regex = re.compile(r'^[A-E]\)')
    item_header_regex   = re.compile(r'^Item\s+(\d+)$')
    answer_regex        = re.compile(r'^ANSWER:\s*([A-E])')
    footer_regex        = re.compile(r'^\d{4}\s+ITE\s+RATIONALE\s+BOOK', re.IGNORECASE)

    # --- PASS 1: QUESTIONS ---
    print("DEBUG: Reading Questions PDF...")
    if not os.path.exists(q_path):
        print(f"ERROR: Questions file not found: {q_path}")
        return pd.DataFrame()
    try:
        lines = []
        with pdfplumber.open(q_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    lines.extend(text.splitlines())

        current_id = None
        for line in lines:
            text = line.strip()
            if not text:
                continue

            m = q_header_regex.match(text)
            if m:
                item_num   = m.group(1).zfill(3)
                current_id = f"Q{year}-{item_num}"
                questions_data[current_id] = {
                    "Question ID":    current_id,
                    "ExamYear":       year,
                    "QuestionStem":   m.group(2).strip(),
                    "CorrectAnswer":  "",
                    "Explanation":    ""
                }
                continue

            if current_id:
                questions_data[current_id]["QuestionStem"] = (
                    questions_data[current_id]["QuestionStem"] + " " + text
                ).strip()

    except Exception as e:
        print(f"ERROR reading questions PDF: {e}")
        return pd.DataFrame()

    # --- PASS 2: CRITIQUE ---
    print(f"DEBUG: Found {len(questions_data)} stems. Reading Critique PDF...")
    if not os.path.exists(c_path):
        print(f"ERROR: Critique file not found: {c_path}")
        return pd.DataFrame()
    try:
        lines = []
        with pdfplumber.open(c_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    lines.extend(text.splitlines())

        current_id    = None
        in_references = False

        for line in lines:
            text = line.strip()
            if not text:
                continue

            if footer_regex.match(text):
                continue

            m = item_header_regex.match(text)
            if m:
                current_id    = f"Q{year}-{m.group(1).zfill(3)}"
                in_references = False
                continue

            if current_id is None:
                continue

            a_match = answer_regex.match(text)
            if a_match:
                if current_id in questions_data:
                    questions_data[current_id]["CorrectAnswer"] = a_match.group(1)
                continue

            if text == "References":
                in_references = True
                continue

            if not in_references and current_id in questions_data:
                questions_data[current_id]["Explanation"] = (
                    questions_data[current_id]["Explanation"] + " " + text
                ).strip()

    except Exception as e:
        print(f"ERROR reading critique PDF: {e}")
        return pd.DataFrame()

    valid   = {k: v for k, v in questions_data.items() if v["QuestionStem"].strip()}
    skipped = len(questions_data) - len(valid)
    if skipped:
        print(f"WARNING: {skipped} question(s) had empty stems and were skipped.")

    return pd.DataFrame(list(valid.values()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", default=EXAM_YEAR, help="Exam year (default: EXAM_YEAR constant)")
    args = ap.parse_args()
    year = args.year

    q_pdf   = ITE_SOURCE / f"{year}_ITE_Questions.pdf"
    c_pdf   = ITE_SOURCE / f"{year}_ITE_Critique.pdf"
    out_csv = QBANK_DIR  / f"ITE_{year}_Raw.csv"

    QBANK_DIR.mkdir(parents=True, exist_ok=True)

    df = extract_from_pdf(q_pdf, c_pdf, year=year)
    if not df.empty:
        df.to_csv(out_csv, index=False)
        print(f"OK SUCCESS: {len(df)} questions extracted to {out_csv}")
    else:
        print("ERROR: No questions extracted.")


if __name__ == "__main__":
    main()
