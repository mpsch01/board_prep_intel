ITE Question Bank Project (v1)
==============================

Folders:
- data/                # Put inputs here
  - master_bank.csv    # Your authoritative, evolving bank (upload here)
  - raw_text/          # Plain-text exports of questions & answers (e.g., 2025)
  - raw_docs/          # Word/PDF sources like critique books (2020–2024)
- outputs/             # Generated banks, diffs, and reports

Core commands (examples):
1) Build from text Q&A (e.g., 2025 raw txt):
   python scripts/build_from_text.py        --questions data/raw_text/raw_questions_2025.txt        --answers data/raw_text/raw_answers_2025.txt        --year 2025        --out outputs/ite_2025_bank.csv

2) Build from DOCX critique book (e.g., combined 2020–2024):
   python scripts/build_from_docx.py        --docx data/raw_docs/ITE_2020-24_combined.docx        --year 2024        --out outputs/ite_2024_from_docx.csv

3) Merge new bank into master (dedupe by id, prefer newer year, or prefer DOCX source):
   python scripts/merge_into_master.py        --master data/master_bank.csv        --incoming outputs/ite_2024_from_docx.csv        --priority incoming        --out outputs/master_bank_updated.csv

4) Diff two banks (by id; flags answer mismatch, stem drift):
   python scripts/diff_banks.py        --left outputs/ite_2024_from_docx.csv        --right data/master_bank.csv        --out outputs/diff_2024_vs_master.csv

Schema:
id, year, stem, A, B, C, D, E, F, correct, explanation, tags, confidence

Tip: Keep master authoritative; use outputs/master_bank_updated.csv to replace it only after spot-checking diffs.
