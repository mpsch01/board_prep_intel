"""
Script 02b: generate_hy_inserts_v2.py
Uses explicit session_subcat_crosswalk.csv + ITE Analysis Report guidance.
Session tier = best Yield_Score among directly mapped subcategories.
Report context: Psychogenic is fastest-growing (+0.80/yr) -> weighted up.
               Respiratory is steepest declining -> no artificial inflation.
Output: session_hy_inserts_v2.json
"""

import pandas as pd, json, re
from pathlib import Path

SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
SUBCAT_XWALK = PROJECT_ROOT / "key_data_files" / "session_subcat_crosswalk.csv"    # TODO: not yet migrated
CLUST_XWALK  = PROJECT_ROOT / "key_data_files" / "session_cluster_crosswalk.csv"   # output of 01_build_crosswalk.py
ITE_ENRICHED = PROJECT_ROOT / "key_data_files" / "ABFM_ITE_Enriched.csv"           # TODO: not yet migrated
STUDY_GUIDE  = PROJECT_ROOT / "key_data_files" / "study_guide_v2_scores.csv"       # TODO: not yet migrated
REF_TIERS    = PROJECT_ROOT / "key_data_files" / "ITE_Reference_Tiers_Final.csv"   # TODO: not yet migrated
OUTPUT       = PROJECT_ROOT / "key_data_files" / "session_hy_inserts_v2.json"
TOP_N        = 10
TIER1_CUT    = 1.0
TIER2_CUT    = 0.5

# --- Load ---
sub_xw = pd.read_csv(SUBCAT_XWALK, dtype=str)
cl_xw  = pd.read_csv(CLUST_XWALK,  dtype=str)
ite    = pd.read_csv(ITE_ENRICHED, dtype=str)
sg     = pd.read_csv(STUDY_GUIDE)
# Use v2 score (volume-floor corrected) as primary yield score
sg['Yield_Score'] = sg['Yield_Score_v2']
refs   = pd.read_csv(REF_TIERS, dtype=str)

ite['ExamYear'] = pd.to_numeric(ite['ExamYear'], errors='coerce')
ite['Subcategory_Cluster'] = ite['Subcategory_Cluster'].fillna('')

# Index study guide by subcategory name
sg_idx = {str(r['Subcategory']): r for _, r in sg.iterrows()}

def assign_tier(score):
    if score >= TIER1_CUT: return 'Tier 1'
    if score >= TIER2_CUT: return 'Tier 2'
    return 'Standard'

def trend_arrow(slope):
    if slope >= 0.3:  return 'Rising'
    if slope <= -0.3: return 'Declining'
    return 'Stable'

def is_must_read(ref_text, must_reads):
    ref_text = str(ref_text)
    for mr in must_reads:
        auth = mr['citation'].split(',')[0].strip().lower()
        ym   = re.search(r'\b(20\d{2}|19\d{2})\b', mr['citation'])
        yr   = ym.group(1) if ym else ''
        if auth and auth in ref_text.lower() and (not yr or yr in ref_text):
            return True, mr['citation']
    return False, None

inserts = {}

for _, sess_row in sub_xw.iterrows():
    snum  = str(sess_row['session_number']).strip().zfill(2)
    sname = str(sess_row['session_name'])
    raw   = str(sess_row['subcategory_matches'])

    # Handle NaN / empty sessions
    if raw.lower() in ('nan', ''):
        subcats_raw = []
    else:
        subcats_raw = [s.strip() for s in raw.split(',')]

    # Get cluster crosswalk row
    cl_row = cl_xw[cl_xw['session_number'].str.zfill(2) == snum]
    clusts, cats = [], []
    if len(cl_row):
        clusts = [c.strip() for c in cl_row.iloc[0]['top_clusters'].split(',')]
        cats   = [c.strip() for c in cl_row.iloc[0]['primary_categories'].split(',')]

    # Build subcat details — only from study guide, skip unknowns silently
    subcat_details = []
    for sc in subcats_raw:
        if sc in sg_idx:
            r = sg_idx[sc]
            subcat_details.append({
                'subcategory':  sc,
                'yield_score':  round(float(r['Yield_Score']), 2),
                'tier':         assign_tier(float(r['Yield_Score'])),
                'total_qs_6yr': int(r['Total_Questions_6yr']),
                'avg_per_exam': round(float(r['Avg_Per_Exam']), 1),
                'trend':        trend_arrow(float(r['Trend_Slope'])),
                'trend_slope':  round(float(r['Trend_Slope']), 3),
                'key_focuses':  str(r.get('Key_ClinicalFocuses', ''))[:300]
            })

    subcat_details.sort(key=lambda x: x['yield_score'], reverse=True)

    best_score   = subcat_details[0]['yield_score'] if subcat_details else 0.0
    session_tier = assign_tier(best_score)

    # Pull ITE questions from cluster crosswalk
    sess_qs = ite[ite['Subcategory_Cluster'].isin(clusts)].sort_values('ExamYear', ascending=False)

    # Must-read refs (category-matched)
    must_reads = []
    for _, rr in refs[refs['Tier'] == 'Must-Read'].iterrows():
        ref_cats = str(rr.get('Categories', ''))
        if any(c in ref_cats for c in cats):
            must_reads.append({
                'citation':       str(rr['CleanRef']),
                'citation_count': str(rr.get('CitationCount', '')),
                'unique_years':   str(rr.get('UniqueYears', '')),
                'categories':     ref_cats
            })

    question_list = []
    for _, q in sess_qs.head(TOP_N).iterrows():
        ref_raw  = str(q.get('References', ''))
        mr, mref = is_must_read(ref_raw, must_reads)
        question_list.append({
            'question_id':       str(q['Question ID']),
            'exam_year':         str(int(q['ExamYear'])) if pd.notna(q['ExamYear']) else 'Unknown',
            'cluster':           str(q['Subcategory_Cluster']),
            'ref_raw':           ref_raw[:300] if ref_raw != 'nan' else '',
            'is_must_read_ref':  mr,
            'matched_must_read': mref
        })

    inserts[snum] = {
        'session_number':       snum,
        'session_name':         sname,
        'session_tier':         session_tier,
        'best_yield_score':     round(best_score, 2),
        'total_qs_in_clusters': int(sess_qs.shape[0]),
        'tier1_subcategories':  [s['subcategory'] for s in subcat_details if s['tier'] == 'Tier 1'],
        'tier2_subcategories':  [s['subcategory'] for s in subcat_details if s['tier'] == 'Tier 2'],
        'top_subcategory':      subcat_details[0] if subcat_details else {},
        'subcat_details':       subcat_details,
        'top_questions':        question_list,
        'must_read_refs':       must_reads
    }

with open(OUTPUT, 'w', encoding='utf-8') as f:
    json.dump(inserts, f, indent=2, ensure_ascii=False)

# --- Summary report ---
t1 = sorted([(k,v) for k,v in inserts.items() if v['session_tier']=='Tier 1'],
            key=lambda x: x[1]['best_yield_score'], reverse=True)
t2 = sorted([(k,v) for k,v in inserts.items() if v['session_tier']=='Tier 2'],
            key=lambda x: x[1]['best_yield_score'], reverse=True)
st = sorted([(k,v) for k,v in inserts.items() if v['session_tier']=='Standard'],
            key=lambda x: x[0])

print(f"TIER 1 ({len(t1)} sessions)  [Yield >= 1.0]")
for k,v in t1:
    t1s = ', '.join(v['tier1_subcategories'][:3])
    print(f"  [{v['best_yield_score']:.2f}] Sess {k}: {v['session_name'][:55]}")
    print(f"         Tier1 subcats: {t1s}")

print(f"\nTIER 2 ({len(t2)} sessions)  [Yield 0.5-0.99]")
for k,v in t2:
    top = (v['tier1_subcategories'] + v['tier2_subcategories'])[:3]
    print(f"  [{v['best_yield_score']:.2f}] Sess {k}: {v['session_name'][:55]}")
    print(f"         Top subcats: {', '.join(top)}")

print(f"\nSTANDARD ({len(st)} sessions)  [Yield < 0.5]")
for k,v in st:
    top = (v['tier1_subcategories'] + v['tier2_subcategories'] +
           [s['subcategory'] for s in v['subcat_details'] if s['tier']=='Standard'])[:2]
    print(f"  [{v['best_yield_score']:.2f}] Sess {k}: {v['session_name'][:55]}")
    if top: print(f"         Best: {', '.join(top)}")

print(f"\nTotal sessions: {len(inserts)}")
print(f"Output: {OUTPUT}")
