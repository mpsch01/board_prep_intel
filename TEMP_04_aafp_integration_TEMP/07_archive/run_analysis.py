import pandas as pd
import numpy as np
import json, re, pickle
from pathlib import Path

BASE = Path(r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\01_source\updated_data_docs')
OUT  = Path(r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\01_source\updated_data_docs')

df  = pd.read_excel(BASE / 'ABFM_ITE_Master_v2.xlsx')
qrp = pd.read_csv(BASE / 'question_ref_pairs.csv')
with open(BASE / 'session_hy_inserts_v6.json') as f:
    v6 = json.load(f)

df['ExamYear'] = df['ExamYear'].astype(int)
years = sorted(df['ExamYear'].unique())

# ── 1. BODY SYSTEM × YEAR ─────────────────────────────────────────────────────
bs_year     = df.groupby(['ExamYear','BodySystem']).size().unstack(fill_value=0)
bs_year_pct = bs_year.div(bs_year.sum(axis=1), axis=0).mul(100).round(1)

bs_trend = {}
for col in bs_year.columns:
    slope = np.polyfit(np.arange(len(bs_year)), bs_year[col].values, 1)[0]
    bs_trend[col] = round(float(slope), 3)
bs_trend_df = pd.DataFrame.from_dict(bs_trend, orient='index', columns=['slope_per_yr']).sort_values('slope_per_yr', ascending=False)

# ── 2. SUBCATEGORY × YEAR ─────────────────────────────────────────────────────
sc_year     = df.groupby(['ExamYear','Subcategory']).size().unstack(fill_value=0)
sc_year_pct = sc_year.div(sc_year.sum(axis=1), axis=0).mul(100).round(1)

sc_trend = {}
for col in sc_year.columns:
    slope = np.polyfit(np.arange(len(sc_year)), sc_year[col].values, 1)[0]
    sc_trend[col] = round(float(slope), 3)
sc_trend_df = pd.DataFrame.from_dict(sc_trend, orient='index', columns=['slope_per_yr']).sort_values('slope_per_yr', ascending=False)

# ── 3. BLUEPRINT × YEAR (predicted, all 1200) ─────────────────────────────────
bp_year     = df.groupby(['ExamYear','BlueprintCategory_Predicted']).size().unstack(fill_value=0)
bp_year_pct = bp_year.div(bp_year.sum(axis=1), axis=0).mul(100).round(1)

# ── 4. HIGH-YIELD COMBOS ──────────────────────────────────────────────────────
combo        = df.groupby(['BodySystem','Subcategory']).size().reset_index(name='count')
combo['pct'] = (combo['count'] / 1200 * 100).round(2)
combo_sorted = combo.sort_values('count', ascending=False).reset_index(drop=True)
combo_sorted.index += 1
top20        = combo_sorted.head(20).copy()

combo_pivot = df.groupby(['BodySystem','Subcategory']).size().unstack(fill_value=0)

c25 = df[df.ExamYear==2025].groupby(['BodySystem','Subcategory']).size().reset_index(name='n2025')
c20 = df[df.ExamYear==2020].groupby(['BodySystem','Subcategory']).size().reset_index(name='n2020')
combo_delta = pd.merge(c25, c20, on=['BodySystem','Subcategory'], how='outer').fillna(0)
combo_delta['delta'] = (combo_delta['n2025'] - combo_delta['n2020']).astype(int)
combo_delta = combo_delta.sort_values('delta', ascending=False).reset_index(drop=True)

# ── 5. REFERENCE TIER ANALYSIS ────────────────────────────────────────────────
tier_year     = qrp.groupby(['ExamYear','Tier']).size().unstack(fill_value=0)
tier_year_pct = tier_year.div(tier_year.sum(axis=1), axis=0).mul(100).round(1)

ref_counts = qrp.groupby('RefMatched').agg(
    citations=('QuestionID','count'),
    tier=('Tier','first'),
    years_seen=('ExamYear', lambda x: len(x.unique()))
).reset_index()
ref_counts = ref_counts[ref_counts['RefMatched'].str.len() > 20].sort_values('citations', ascending=False)
top_refs = ref_counts.head(25).reset_index(drop=True)
top_refs.index += 1

def classify_ref(ref):
    r = str(ref).lower()
    if any(x in r for x in ['uspstf','u.s. preventive']):      return 'USPSTF'
    if any(x in r for x in ['cdc','centers for disease']):     return 'CDC'
    if any(x in r for x in ['aafp','american academy of fam']): return 'AAFP'
    if any(x in r for x in ['aha','acc','american heart','american college of card']): return 'AHA/ACC'
    if any(x in r for x in ['ada ','american diabetes']):      return 'ADA'
    if any(x in r for x in ['acog','american college of ob']): return 'ACOG'
    if any(x in r for x in ['idsa','infectious disease']):     return 'IDSA'
    if 'am fam physician' in r or ' afp ' in r:                return 'AFP'
    if any(x in r for x in ['n engl j med','nejm']):           return 'NEJM'
    if any(x in r for x in ['jama','lancet','bmj','ann intern med','annals']): return 'Major Journal'
    if any(x in r for x in ['harrison','tintinalli','lange','uptodate']): return 'Textbook'
    return 'Specialty Journal'

qrp['source_type'] = qrp['RefMatched'].apply(classify_ref)
src_tier = qrp.groupby(['source_type','Tier']).size().unstack(fill_value=0).reset_index()
src_total = qrp.groupby('source_type').size().reset_index(name='total')
src_counts = pd.merge(src_total, src_tier, on='source_type').sort_values('total', ascending=False)

# ── 6. SESSION COVERAGE ───────────────────────────────────────────────────────
sess_rows = []
for sid, s in v6.items():
    refs  = s['refs']
    tiers = [r['tier'] for r in refs]
    scores = [q['kw_score'] for q in s['questions']]
    yr_ct  = {}
    for q in s['questions']:
        yr_ct[q['year']] = yr_ct.get(q['year'], 0) + 1
    row = {
        'session_id':    int(sid),
        'session_title': s['session_title'],
        'q_count':       s['question_count'],
        'ref_total':     len(refs),
        'must_read':     tiers.count('Must-Read'),
        'core':          tiers.count('Core'),
        'unmatched':     tiers.count('Unmatched'),
        'pct_tiered':    round((tiers.count('Must-Read')+tiers.count('Core'))/max(len(tiers),1)*100,1),
        'avg_kw_score':  round(np.mean(scores) if scores else 0, 3),
        'min_kw_score':  round(min(scores, default=0), 3),
    }
    for yr in years:
        row[str(yr)] = yr_ct.get(yr, 0)
    sess_rows.append(row)
sess_df = pd.DataFrame(sess_rows).sort_values('session_id').reset_index(drop=True)

# ── SAVE ──────────────────────────────────────────────────────────────────────
with open(r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\01_source\updated_data_docs\analysis_cache.pkl', 'wb') as f:
    pickle.dump({
        'bs_year': bs_year, 'bs_year_pct': bs_year_pct, 'bs_trend_df': bs_trend_df,
        'sc_year': sc_year, 'sc_year_pct': sc_year_pct, 'sc_trend_df': sc_trend_df,
        'bp_year': bp_year, 'bp_year_pct': bp_year_pct,
        'top20': top20, 'combo_pivot': combo_pivot, 'combo_delta': combo_delta,
        'tier_year': tier_year, 'tier_year_pct': tier_year_pct,
        'top_refs': top_refs, 'src_counts': src_counts,
        'sess_df': sess_df,
    }, f)

print("=== BODY SYSTEM TRENDS ===")
print(bs_trend_df.to_string())
print("\n=== SUBCATEGORY TRENDS ===")
print(sc_trend_df.to_string())
print("\n=== BLUEPRINT % BY YEAR ===")
print(bp_year_pct.to_string())
print("\n=== TOP 20 COMBOS ===")
print(top20[['BodySystem','Subcategory','count','pct']].to_string())
print("\n=== COMBO DELTA 2025 vs 2020 ===")
print(combo_delta.head(15)[['BodySystem','Subcategory','n2025','n2020','delta']].to_string())
print("\n=== TIER BY YEAR (count) ===")
print(tier_year.to_string())
print("\n=== TIER % BY YEAR ===")
print(tier_year_pct.to_string())
print("\n=== SOURCE TYPE ===")
print(src_counts.to_string())
print("\n=== SESSION REF QUALITY (sorted by pct_tiered) ===")
print(sess_df[['session_id','session_title','q_count','ref_total','must_read','core','unmatched','pct_tiered','avg_kw_score']].to_string())
