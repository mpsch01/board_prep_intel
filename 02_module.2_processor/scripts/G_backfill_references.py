"""
G_backfill_references.py
========================
Join question_ref_pairs.csv into ABFM_ITE_Enriched.csv → populate References column.

References format per cell:
  "Author et al: Title. Journal Year;vol(issue):pages. [Tier] | 2) ..."

Also writes a per-question ref summary for quick QA.
"""

import csv, os
from pathlib import Path
from collections import defaultdict

SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
PAIRS_CSV  = SCRIPT_DIR.parent / "outputs" / "question_ref_pairs.csv"              # output of F_extract_question_refs.py
ENRICHED   = PROJECT_ROOT / "key_data_files" / "ABFM_ITE_Enriched.csv"             # TODO: not yet migrated
OUT_ENRICH = PROJECT_ROOT / "key_data_files" / "ABFM_ITE_Enriched.csv"             # TODO: not yet migrated
RAW_DIR    = SCRIPT_DIR.parent / "outputs" / "raw_files"
QA_OUT     = RAW_DIR / "ref_backfill_qa.csv"

os.makedirs(RAW_DIR, exist_ok=True)

# ── QID offset map: pairs use Q20XX-001..200, Enriched uses cumulative offsets
# 2020: offset 0 (001-200), 2021: offset 200 (201-400),
# 2022: offset 400 (401-600), 2023: offset 600 (601-800)
YEAR_OFFSET = {2020: 0, 2021: 200, 2022: 400, 2023: 600, 2025: 0}

def translate_qid(qid, year):
    """Convert pairs QID to Enriched QID format."""
    offset = YEAR_OFFSET.get(year, 0)
    if offset == 0:
        return qid
    # Extract numeric part and add offset
    import re
    m = re.match(r'(Q\d{4}-)(\d+)', qid)
    if m:
        num = int(m.group(2)) + offset
        return f'{m.group(1)}{num:03d}'
    return qid

# ── Load pairs → dict keyed by QuestionID ─────────────────────────────────────
print('Loading question_ref_pairs.csv...')
pairs = defaultdict(list)
with open(PAIRS_CSV, newline='', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        year  = int(row['ExamYear'])
        qid   = translate_qid(row['QuestionID'], year)
        ref   = row['RefMatched'] if row['RefMatched'] else row['RefRaw']
        tier  = row['Tier']
        idx   = int(row['RefIndex'])
        pairs[qid].append((idx, ref, tier))

# Sort each QID's refs by index
for qid in pairs:
    pairs[qid].sort(key=lambda x: x[0])

print(f'  {len(pairs)} questions have ref data')

# ── Build formatted reference string per question ─────────────────────────────
def format_refs(ref_list):
    parts = []
    for i, (idx, ref, tier) in enumerate(ref_list, 1):
        label = f'[{tier}]' if tier != 'Unmatched' else ''
        entry = f'{ref} {label}'.strip() if label else ref
        if i == 1:
            parts.append(entry)
        else:
            parts.append(f'{i}) {entry}')
    return ' | '.join(parts)

# ── Read Enriched, inject References, write back ───────────────────────────────
print('Reading ABFM_ITE_Enriched.csv...')
rows = []
with open(ENRICHED, newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    for row in reader:
        rows.append(row)

print(f'  {len(rows)} question rows')

filled = 0
qa_rows = []
for row in rows:
    qid = row.get('Question ID') or row.get('QuestionID', '')
    if qid in pairs:
        ref_str = format_refs(pairs[qid])
        row['References'] = ref_str
        filled += 1
        # QA entry
        for idx, ref, tier in pairs[qid]:
            qa_rows.append({
                'QuestionID': qid,
                'ExamYear':   row['ExamYear'],
                'RefIndex':   idx,
                'Tier':       tier,
                'Ref':        ref[:120]
            })

print(f'  {filled} questions backfilled with references')
print(f'  {len(rows)-filled} questions have no ref data (2025 or missing)')

# Write enriched CSV back
print(f'Writing updated Enriched CSV...')
with open(OUT_ENRICH, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(rows)
print('  Done.')

# Write QA CSV
print(f'Writing QA file -> {QA_OUT}')
with open(QA_OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=['QuestionID','ExamYear','RefIndex','Tier','Ref'])
    w.writeheader()
    w.writerows(qa_rows)

# Tier summary
tier_counts = defaultdict(int)
for row in qa_rows:
    tier_counts[row['Tier']] += 1

print('\n=== BACKFILL SUMMARY ===')
print(f'  Questions with refs   : {filled}')
print(f'  Questions without refs: {len(rows)-filled}')
print(f'  Total ref links       : {len(qa_rows)}')
print('  Tier breakdown:')
for tier in ['Must-Read','Core','Supplementary','Unmatched']:
    print(f'    {tier:<15}: {tier_counts[tier]}')
print('\nDone.')
