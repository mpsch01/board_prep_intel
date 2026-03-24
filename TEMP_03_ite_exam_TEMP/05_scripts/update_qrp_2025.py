import pandas as pd
from pathlib import Path

BASE = Path(r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep')
REFS_CSV = BASE / 'ite_exam' / '02_working' / 'refs_2025_extracted.csv'
QRP_CSV  = BASE / 'ite_refs' / '02_working' / 'question_ref_pairs.csv'

refs = pd.read_csv(REFS_CSV)
qrp  = pd.read_csv(QRP_CSV)

print(f"QRP before: {len(qrp)} rows")
print(f"Existing 2025 rows: {qrp['QuestionID'].str.startswith('Q2025').sum()}")

# Remove existing 2025 rows
qrp_no_2025 = qrp[~qrp['QuestionID'].str.startswith('Q2025')].copy()
print(f"QRP after removing 2025: {len(qrp_no_2025)} rows")

# Build new 2025 rows matching QRP schema
# Columns: QuestionID, QuestionID_raw, ExamYear, RefIndex, RefRaw, RefMatched, Tier, MatchScore
new_rows = []
for _, row in refs.iterrows():
    new_rows.append({
        'QuestionID':     row['QuestionID'],
        'QuestionID_raw': row['QuestionID'],
        'ExamYear':       2025,
        'RefIndex':       int(row['RefIndex']),
        'RefRaw':         row['RawRef'],
        'RefMatched':     None,
        'Tier':           'Unmatched',
        'MatchScore':     0.0
    })

new_2025 = pd.DataFrame(new_rows)
print(f"New 2025 rows: {len(new_2025)}")
print(f"Questions covered: {new_2025['QuestionID'].nunique()}")

qrp_updated = pd.concat([qrp_no_2025, new_2025], ignore_index=True)
print(f"QRP after update: {len(qrp_updated)} rows")

qrp_updated.to_csv(QRP_CSV, index=False)
print(f"Saved: {QRP_CSV}")
print("Done.")
