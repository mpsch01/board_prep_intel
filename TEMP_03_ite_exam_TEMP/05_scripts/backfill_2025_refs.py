"""
backfill_2025_refs.py
=====================
Backfills Reference column in ABFM_ITE_Master_v2.xlsx for 2025 questions.

Uses refs_2025_extracted.csv (RefIndex=1 only = primary ref per question).
Only fills rows where Reference is currently null/empty — never overwrites
existing references.

Also appends ALL extracted 2025 refs to question_ref_pairs.csv for 
downstream use by E_v2_question_driven.py.

Outputs:
  - Updates ite_exam/03_database/ABFM_ITE_Master_v2.xlsx in place
  - Updates ite_refs/02_working/question_ref_pairs.csv (appends 2025 rows)
  - Prints backfill report

Author: Pipeline auto-generated 2026-03-03
"""

import sys
from pathlib import Path
import pandas as pd

BASE = Path(r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep')
MASTER_XLSX    = BASE / 'ite_exam' / '03_database' / 'ABFM_ITE_Master_v2.xlsx'
REFS_CSV       = BASE / 'ite_exam' / '02_working' / 'refs_2025_extracted.csv'
QRP_CSV        = BASE / 'ite_refs' / '02_working' / 'question_ref_pairs.csv'

print("Loading files...")
master = pd.read_excel(MASTER_XLSX, engine='openpyxl')
refs   = pd.read_csv(REFS_CSV)
qrp    = pd.read_csv(QRP_CSV)

print(f"  Master rows: {len(master)}")
print(f"  Refs extracted: {len(refs)}")
print(f"  QRP rows (existing): {len(qrp)}")

# ── Current ref coverage for 2025 ────────────────────────────────────────────
mask_2025 = master['ExamYear'] == 2025
null_before = master.loc[mask_2025, 'Reference'].isna().sum()
print(f"\n2025 ref coverage BEFORE backfill:")
print(f"  Null: {null_before}/200  ({null_before/2:.1f}%)")
print(f"  Filled: {200 - null_before}/200")

# ── Build primary ref lookup (RefIndex == 1) ──────────────────────────────────
primary_refs = refs[refs['RefIndex'] == 1].set_index('QuestionID')['RawRef'].to_dict()
print(f"\nPrimary refs available: {len(primary_refs)}")

# ── Backfill into master ───────────────────────────────────────────────────────
filled = 0
skipped_existing = 0
skipped_no_ref = 0

for idx, row in master[mask_2025].iterrows():
    qid = row['QuestionID']
    current_ref = row['Reference']
    
    # Only fill if currently null/empty
    if pd.isna(current_ref) or str(current_ref).strip() == '':
        if qid in primary_refs:
            master.at[idx, 'Reference'] = primary_refs[qid]
            filled += 1
        else:
            skipped_no_ref += 1
    else:
        skipped_existing += 1

null_after = master.loc[mask_2025, 'Reference'].isna().sum()
print(f"\nBackfill results:")
print(f"  Rows filled        : {filled}")
print(f"  Skipped (existing) : {skipped_existing}")
print(f"  Skipped (no source): {skipped_no_ref}")
print(f"\n2025 ref coverage AFTER backfill:")
print(f"  Null: {null_after}/200  ({null_after/2:.1f}%)")
print(f"  Filled: {200 - null_after}/200")

# ── Save updated master ────────────────────────────────────────────────────────
master.to_excel(MASTER_XLSX, index=False, engine='openpyxl')
print(f"\nMaster saved: {MASTER_XLSX}")

# ── Update question_ref_pairs.csv ─────────────────────────────────────────────
# Remove existing 2025 rows from QRP to avoid duplication
qrp_no_2025 = qrp[~qrp['QuestionID'].str.startswith('Q2025')]
print(f"\nQRP: removing {len(qrp) - len(qrp_no_2025)} existing 2025 rows")

# Build new 2025 rows from all extracted refs (not just primary)
new_qrp_rows = []
for _, row in refs.iterrows():
    new_qrp_rows.append({
        'QuestionID': row['QuestionID'],
        'Reference': row['RawRef'],
        'RefSource': '2025_critique_extracted',
        'Tier': None,  # Will be matched later
        'MatchScore': None
    })

new_qrp = pd.DataFrame(new_qrp_rows)

# Check column alignment
existing_cols = set(qrp.columns)
print(f"\nExisting QRP columns: {list(qrp.columns)}")
print(f"New 2025 rows columns: {list(new_qrp.columns)}")

# Align columns
for col in qrp.columns:
    if col not in new_qrp.columns:
        new_qrp[col] = None
new_qrp = new_qrp[qrp.columns]

qrp_updated = pd.concat([qrp_no_2025, new_qrp], ignore_index=True)
print(f"\nQRP updated: {len(qrp)} → {len(qrp_updated)} rows")
print(f"  New 2025 rows added: {len(new_qrp)}")

qrp_updated.to_csv(QRP_CSV, index=False)
print(f"QRP saved: {QRP_CSV}")

print("\n✅ Backfill complete.")
