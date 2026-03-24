import pandas as pd, json
from pathlib import Path

BASE = Path(r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\01_source\updated_data_docs')

# Master v2
df = pd.read_excel(BASE / 'ABFM_ITE_Master_v2.xlsx')
print('=== MASTER V2 ===')
print(f'Shape: {df.shape}')
print(f'Columns: {list(df.columns)}')
print(f'Years: {sorted(df.ExamYear.unique())}')
print(f'Subcategory counts:\n{df.Subcategory.value_counts().head(12).to_string()}')
print(f'\nBodySystem counts:\n{df.BodySystem.value_counts().head(12).to_string()}')
print(f'\nBlueprintCategory (gold):\n{df.BlueprintCategory.value_counts().to_string()}')
print()

# v6 inserts
with open(BASE / 'session_hy_inserts_v6.json') as f:
    v6 = json.load(f)
print('=== SESSION INSERTS V6 ===')
sessions = list(v6.values())
q_total   = sum(s['question_count'] for s in sessions)
r_total   = sum(len(s['refs']) for s in sessions)
mr        = sum(s['must_read_count'] for s in sessions)
core      = sum(s['core_count'] for s in sessions)
unmatched = sum(sum(1 for r in s['refs'] if r['tier']=='Unmatched') for s in sessions)
no_q      = sum(1 for s in sessions if s['question_count']==0)
print(f'Sessions total: {len(v6)}')
print(f'Questions placed: {q_total}  (sessions with 0 Qs: {no_q})')
print(f'Refs total: {r_total}  (Must-Read={mr}, Core={core}, Unmatched={unmatched})')
print(f'\nPer-session question year distribution:')
yr_counts = {}
for s in sessions:
    for q in s['questions']:
        yr = q['year']
        yr_counts[yr] = yr_counts.get(yr, 0) + 1
for yr in sorted(yr_counts):
    print(f'  {yr}: {yr_counts[yr]} questions placed')
print()

# QRP
qrp = pd.read_csv(BASE / 'question_ref_pairs.csv')
print('=== QRP ===')
print(f'Shape: {qrp.shape}')
print(f'Columns: {list(qrp.columns)}')
print(f'Tier breakdown:\n{qrp.Tier.value_counts().to_string()}')
print(f'\nYear breakdown:\n{qrp.ExamYear.value_counts().sort_index().to_string()}')
