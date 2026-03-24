"""
Script E: rematch_refs_and_questions.py  (v2)

Uses session_hy_inserts_v2_adjusted.json as the BASE for all session metadata
(tier, yield scores, subcategory details, poll questions, etc.)
Replaces ONLY: must_read_refs and top_questions using keyword-overlap matching.

Output: session_hy_inserts_v3.json
"""

import csv, json, re, os
from collections import defaultdict

KW_LIB   = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\keyword_library\session_keyword_library.json'
REFS_CSV  = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\ite_refs\03_database\ITE_Reference_Tiers_Final.csv'
QS_CSV    = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\ite_exam\03_database\ABFM_ITE_Enriched.csv'
V2_JSON   = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\02_working\session_hy_inserts_v2_adjusted.json'
OUT_JSON  = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\02_working\session_hy_inserts_v3.json'
RAW_OUT   = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\keyword_library\raw_files\match_scores_debug.json'

REF_THRESHOLD_MUST  = 0.12
REF_THRESHOLD_CORE  = 0.06
REF_MIN_MATCHES     = 2
MAX_MUST_PER_SESSION = 5
MAX_QS_PER_SESSION   = 8
KW_MIN_COMPOSITE     = 0.15

STOPWORDS = set("""
a about also am an and any are as at be been but by can
could did do does each even for from get had have he her
him his how if in into is it its just know let may more
most much need no not of on one only or other our out
per should so some that the their them then there these
they this those though time to too two up us was way we
well were what when where which who will with would year
""".split())

CATEGORY_SESSION_MAP = {
    'Cardiovascular':       ['02','03','04','05','06','10','11','12','21','48'],
    'Respiratory':          ['42','43','44','45','46','07'],
    'Endocrine':            ['13','14','15'],
    'Nephrologic':          ['24','25'],
    'Gastrointestinal':     ['16','17'],
    'Musculoskeletal':      ['31','32','33','34','47'],
    'Neurologic':           ['26','36'],
    'Psychogenic':          ['36','39','40','41'],
    'Reproductive:Female':  ['27','28','29','30'],
    'Reproductive:Male':    ['49'],
    'Integumentary':        ['09'],
    'Hematologic/Immune':   ['21','22','23','12'],
    'Population-Based Care':['07','08','37','38','22'],
    'Patient-Based Systems':['08','18','19','20','37','48'],
    'Special Sensory':      ['35'],
}

def tokenize(text):
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    return [t for t in text.split() if t not in STOPWORDS and len(t) > 2]

def all_tokens(text):
    toks = tokenize(text)
    bigrams = [f'{toks[i]} {toks[i+1]}' for i in range(len(toks)-1)]
    return set(toks + bigrams)

def session_kw_lookup(lib_entry):
    return {kw['term'].lower(): kw['composite']
            for kw in lib_entry.get('keywords', [])
            if kw['composite'] >= KW_MIN_COMPOSITE}

def overlap_score(text_tokens, kw_lookup):
    score, matched = 0.0, []
    for term, composite in kw_lookup.items():
        if term in text_tokens:
            score += composite
            matched.append(term)
    return score, matched

def category_ok(abfm_cat_str, snum):
    if not abfm_cat_str:
        return True
    cats = [c.strip() for c in abfm_cat_str.split(',')]
    for cat in cats:
        if snum in CATEGORY_SESSION_MAP.get(cat, []):
            return True
    return all(cat not in CATEGORY_SESSION_MAP for cat in cats)

# ── Load data ─────────────────────────────────────────────────────────
print('Loading data...')
with open(KW_LIB, encoding='utf-8') as f:
    lib = json.load(f)
with open(REFS_CSV, encoding='utf-8') as f:
    refs = list(csv.DictReader(f))
with open(QS_CSV, encoding='utf-8') as f:
    questions = list(csv.DictReader(f))
with open(V2_JSON, encoding='utf-8') as f:
    v2 = json.load(f)
print(f'  {len(refs)} refs | {len(questions)} questions | {len(v2)} v2 sessions')

# Build question lookup by ID
q_by_id = {q['Question ID']: q for q in questions}

# Pre-tokenize
print('Tokenizing...')
ref_tokens = [all_tokens(r['CleanRef']) for r in refs]
q_tokens   = [all_tokens(q.get('QuestionStem','') + ' ' + q.get('Explanation',''))
               for q in questions]

# ── Score refs against all sessions ───────────────────────────────────
print('Matching refs...')
session_refs = defaultdict(list)  # snum -> [(score, ref_idx, matched)]

for snum, lib_entry in lib.items():
    kw = session_kw_lookup(lib_entry)
    for i, r in enumerate(refs):
        sc, matched = overlap_score(ref_tokens[i], kw)
        thresh = REF_THRESHOLD_MUST if r['Tier'] == 'Must-Read' else REF_THRESHOLD_CORE
        min_m  = REF_MIN_MATCHES if r['Tier'] == 'Must-Read' else 1
        if sc >= thresh and len(matched) >= min_m:
            session_refs[snum].append((sc, i, matched))

for snum in session_refs:
    session_refs[snum].sort(reverse=True)

# ── Score questions against all sessions ──────────────────────────────
print('Matching questions...')
session_qs = defaultdict(list)  # snum -> [(score, q_idx, matched)]

for snum, lib_entry in lib.items():
    kw = session_kw_lookup(lib_entry)
    for i, q in enumerate(questions):
        sc, matched = overlap_score(q_tokens[i], kw)
        if sc >= 0.20 and category_ok(q.get('PrimaryCategory',''), snum):
            session_qs[snum].append((sc, i, matched))

for snum in session_qs:
    session_qs[snum].sort(reverse=True)

# ── Build v3 — clone v2, replace refs and questions ───────────────────
print('\nBuilding v3 inserts...')
results = {}
debug_refs = {}

for snum in sorted(v2.keys()):
    base = dict(v2[snum])  # full copy of v2 session data

    # ── New must-read refs ─────────────────────────────────────────────
    new_must, new_core = [], []
    seen_refs = set()
    for sc, i, matched in session_refs.get(snum, []):
        r = refs[i]
        cit = r['CleanRef']
        if cit in seen_refs:
            continue
        seen_refs.add(cit)
        entry = {
            'citation':      cit,
            'tier':          r['Tier'],
            'categories':    r['Categories'],
            'cited_count':   r.get('CitationCount',''),
            'unique_years':  r.get('UniqueYears',''),
            'match_score':   round(sc, 4),
            'matched_terms': matched[:5]
        }
        if r['Tier'] == 'Must-Read' and len(new_must) < MAX_MUST_PER_SESSION:
            new_must.append(entry)
        elif r['Tier'] in ('Core','Supplementary') and len(new_core) < MAX_MUST_PER_SESSION:
            new_core.append(entry)

    base['must_read_refs'] = new_must
    base['core_refs']      = new_core
    debug_refs[snum]       = [(r['citation'][:60], r['match_score'], r['matched_terms']) for r in new_must]

    # ── New top questions ──────────────────────────────────────────────
    new_qs, seen_ids = [], set()
    for sc, i, matched in session_qs.get(snum, []):
        if len(new_qs) >= MAX_QS_PER_SESSION:
            break
        q   = questions[i]
        qid = q.get('Question ID', f'Q{i}')
        if qid in seen_ids:
            continue
        seen_ids.add(qid)
        new_qs.append({
            'question_id':   qid,
            'exam_year':     q.get('ExamYear',''),
            'cluster':       q.get('Subcategory_Cluster',''),
            'category':      q.get('PrimaryCategory',''),
            'match_score':   round(sc, 4),
            'matched_terms': matched[:5]
        })

    base['top_questions'] = new_qs
    results[snum] = base

    n_must = len(new_must)
    n_core = len(new_core)
    n_qs   = len(new_qs)
    print(f'  {snum}: must={n_must} core={n_core} qs={n_qs}  |  '
          f'{base.get("session_name","")[:38]}')

# ── Write outputs ─────────────────────────────────────────────────────
with open(OUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

with open(RAW_OUT, 'w', encoding='utf-8') as f:
    json.dump(debug_refs, f, indent=2, ensure_ascii=False)

total_must = sum(len(v.get('must_read_refs',[])) for v in results.values())
total_core = sum(len(v.get('core_refs',[])) for v in results.values())
total_qs   = sum(len(v.get('top_questions',[])) for v in results.values())
empty_must = sum(1 for v in results.values() if not v.get('must_read_refs'))

print(f'\nDone.')
print(f'Output: {OUT_JSON}')
print(f'  Must-read refs:  {total_must} across {48-empty_must}/48 sessions')
print(f'  Core refs:       {total_core}')
print(f'  Questions:       {total_qs}')
print(f'  Sessions w/o must-read: {empty_must}')
