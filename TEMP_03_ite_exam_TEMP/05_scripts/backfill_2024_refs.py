"""
backfill_2024_refs_from_pairs.py
The 51 null Q2024 rows in master already have raw refs in question_ref_pairs.csv
(Tier='Unmatched' — failed the 0.70 fuzzy threshold vs tier DB).
This script aggregates those raw refs and backfills the master Reference column.
Also checks the 4 Q2024 IDs not found in pairs at all.
"""
import pandas as pd, sys, shutil
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

BASE   = Path(r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep')
PAIRS  = BASE / 'ite_refs' / '02_working' / 'question_ref_pairs.csv'
MASTER = BASE / 'ite_exam' / '03_database' / 'ABFM_ITE_Master_v2.xlsx'

# ── Load ──────────────────────────────────────────────────────────────────────
df = pd.read_excel(MASTER, dtype=str)
null_ref = df['Reference'].isna() | (df['Reference'].str.strip() == '') | (df['Reference'] == 'nan')
null_q24 = df[(df['ExamYear']=='2024') & null_ref]['QuestionID'].tolist()
print(f"Null Q2024 to fill: {len(null_q24)}")

pairs = pd.read_csv(PAIRS, dtype=str)
q24_pairs = pairs[pairs['QuestionID'].isin(null_q24)]

# ── Aggregate raw refs per QID (join with ' | ') ──────────────────────────────
ref_lookup = {}
for qid, grp in q24_pairs.groupby('QuestionID'):
    raw_refs = grp['RefRaw'].dropna().tolist()
    clean = [r.strip() for r in raw_refs if r.strip() and len(r.strip()) > 10]
    if clean:
        ref_lookup[qid] = ' | '.join(clean)

print(f"QIDs with raw refs found: {len(ref_lookup)}/51")
missing = [q for q in null_q24 if q not in ref_lookup]
print(f"QIDs with no refs at all: {len(missing)} — {missing}")

# ── Backup ─────────────────────────────────────────────────────────────────────
ts = datetime.now().strftime("%Y%m%d_%H%M%S")
bkdir = BASE / 'ite_exam' / '07_archive' / 'db_previous_versions'
bkdir.mkdir(parents=True, exist_ok=True)
bkpath = bkdir / f'ABFM_ITE_Master_v2_pre_q2024_backfill_{ts}.xlsx'
shutil.copy2(MASTER, bkpath)
print(f"\nBackup: {bkpath.name}")

# ── Apply ──────────────────────────────────────────────────────────────────────
filled = 0
for idx, row in df.iterrows():
    qid = row['QuestionID']
    if qid not in ref_lookup:
        continue
    curr = row.get('Reference','')
    if pd.isna(curr) or str(curr).strip() in ('','nan'):
        df.at[idx, 'Reference'] = ref_lookup[qid]
        filled += 1

print(f"Filled: {filled} Q2024 rows")

# ── Final coverage ─────────────────────────────────────────────────────────────
null_after = df['Reference'].isna() | (df['Reference'].str.strip()=='') | (df['Reference']=='nan')
print(f"\nOverall ref coverage after backfill:")
for yr in ['2020','2021','2022','2023','2024','2025']:
    m = (df['ExamYear']==yr)
    n = (m & null_after).sum()
    t = m.sum()
    print(f"  {yr}: {t-n}/{t} ({(t-n)/t*100:.1f}%)")
print(f"\nTotal: {len(df)-null_after.sum()}/{len(df)} ({(len(df)-null_after.sum())/len(df)*100:.1f}%)")

# ── Save ───────────────────────────────────────────────────────────────────────
df.to_excel(MASTER, index=False, engine='openpyxl')
print(f"\nSaved: {MASTER}")
print("Done.")
