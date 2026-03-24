"""
Script: 05_tag_and_score_poll_questions.py

For each poll question:
  1. Match stem text to study guide subcategories via keyword overlap
  2. Count how many poll questions map to each subcategory (presenter_count)
  3. Normalize to 0-1 scale -> presenter_score
  4. Merge with Yield_Score: adjusted = Yield_Score*0.80 + presenter_score*0.20
  5. Re-derive tiers from adjusted score
  6. Output:
     - poll_questions_tagged.csv  (question + matched subcat)
     - subcategory_presenter_scores.csv  (subcat-level aggregation)
     - session_hy_inserts_v2_adjusted.json  (updated inserts with new tiers)
"""

import pandas as pd, json, re, os, sys
sys.stdout.reconfigure(encoding='utf-8')

POLL_CSV    = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\02_working\poll_questions_raw.csv'
STUDY_GUIDE = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\07_archive\study_guide_v2_scores.csv'
INSERTS_V2  = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\02_working\session_hy_inserts_v2.json'
SUBCAT_XWALK= r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\02_working\session_subcat_crosswalk.csv'

OUT_TAGGED  = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\02_working\poll_questions_tagged.csv'
OUT_SCORES  = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\02_working\subcategory_presenter_scores.csv'
OUT_JSON    = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\02_working\session_hy_inserts_v2_adjusted.json'
RAW_DIR     = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\07_archive'

TIER1_CUT = 1.0
TIER2_CUT = 0.5
ITE_WEIGHT = 1.0   # tiebreaker mode — ITE score unchanged
PRES_WEIGHT = 0.0  # presenter used only at boundaries

# ── Load ──────────────────────────────────────────────────────────────
poll   = pd.read_csv(POLL_CSV)
sg     = pd.read_csv(STUDY_GUIDE)
sg['Yield_Score'] = sg['Yield_Score_v2']  # use volume-floor corrected score
xwalk  = pd.read_csv(SUBCAT_XWALK, dtype=str)

with open(INSERTS_V2, encoding='utf-8') as f:
    inserts = json.load(f)

# Only use questions that have at least a stem
poll = poll[poll['stem'].notna() & (poll['stem'].str.strip() != '')].copy()

# ── Build keyword index from study guide ──────────────────────────────
def tokenize(text):
    """Lowercase alphanum tokens, length >= 4."""
    return set(re.findall(r'[a-z]{4,}', str(text).lower()))

sg_tokens = {}
for _, r in sg.iterrows():
    sc = str(r['Subcategory'])
    # Combine subcategory name + clinical focuses for matching
    combined = sc + ' ' + str(r.get('Key_ClinicalFocuses', ''))
    sg_tokens[sc] = tokenize(combined)

# ── Tag each poll question ────────────────────────────────────────────
# For each question, find best-matching subcategory from the session's
# own crosswalk first (constrained match), then fall back to global best.

# Build session -> allowed subcategories map
sess_subcats = {}
for _, row in xwalk.iterrows():
    snum = str(row['session_number']).strip()
    raw  = str(row['subcategory_matches'])
    if raw.lower() == 'nan':
        sess_subcats[snum] = []
    else:
        sess_subcats[snum] = [s.strip() for s in raw.split(',')]

def best_match(stem_text, allowed_subcats):
    """Return (subcat, overlap_score) for best matching subcat."""
    stem_toks = tokenize(stem_text)
    if not stem_toks:
        return None, 0.0
    best_sc, best_score = None, 0.0
    for sc in allowed_subcats:
        if sc not in sg_tokens:
            continue
        overlap = len(stem_toks & sg_tokens[sc])
        score   = overlap / max(len(sg_tokens[sc]), 1)
        if score > best_score:
            best_sc, best_score = sc, score
    return best_sc, best_score

tagged_rows = []
for _, q in poll.iterrows():
    snum = str(int(q['session_number']))
    allowed = sess_subcats.get(snum, [])
    sc, score = best_match(str(q['stem']), allowed)
    # Minimum threshold — don't force a match if overlap is trivial
    if score < 0.05:
        sc = None
    tagged_rows.append({
        **q.to_dict(),
        'matched_subcategory': sc,
        'match_score': round(score, 3)
    })

tagged_df = pd.DataFrame(tagged_rows)
tagged_df.to_csv(OUT_TAGGED, index=False, encoding='utf-8')

# ── Aggregate presenter counts per subcategory ─────────────────────────
matched = tagged_df[tagged_df['matched_subcategory'].notna()]
counts  = matched.groupby('matched_subcategory').size().reset_index(name='presenter_count')

# Normalize to 0-1
max_count = counts['presenter_count'].max()
counts['presenter_score'] = (counts['presenter_count'] / max_count).round(4)

# Merge with study guide yield scores
sg_slim = sg[['Subcategory','Yield_Score','Trend_Slope','Total_Questions_6yr']].copy()
counts  = counts.merge(sg_slim, left_on='matched_subcategory', right_on='Subcategory', how='left')
# Tiebreaker: ITE score is authoritative.
# Boundary zone = within 0.15 of a tier cutoff (1.0 or 0.5).
# In the zone: >= POLL_THRESHOLD polls -> bump up; 0 polls -> bump down.
# Outside the zone: score unchanged.
BOUNDARY   = 0.15
POLL_THRESHOLD = 3  # minimum polls to earn an upward nudge
NUDGE      = 0.16   # enough to cross a 0.15-wide boundary zone

def apply_tiebreaker(yield_score, presenter_count):
    score = float(yield_score)
    polls = int(presenter_count) if pd.notna(presenter_count) else 0
    for cutoff in [TIER1_CUT, TIER2_CUT]:
        if abs(score - cutoff) <= BOUNDARY:
            # Nudge up: below cutoff, enough polls, and not exactly AT cutoff
            if score < cutoff and polls >= POLL_THRESHOLD:
                return round(max(score + NUDGE, 0.0), 4)
            # Nudge down: at or above cutoff, zero polls
            # Exception: never nudge down if score is exactly at the cutoff
            # (score == cutoff means it already earned its tier by ITE data alone)
            if score > cutoff and polls == 0:
                return round(max(score - NUDGE, 0.0), 4)
    return round(max(score, 0.0), 4)

counts['adjusted_score'] = counts.apply(
    lambda r: apply_tiebreaker(r['Yield_Score'], r['presenter_count']), axis=1
)

counts.to_csv(OUT_SCORES, index=False, encoding='utf-8')
import shutil
shutil.copy(OUT_SCORES, os.path.join(RAW_DIR, 'subcategory_presenter_scores.csv'))
shutil.copy(OUT_TAGGED, os.path.join(RAW_DIR, 'poll_questions_tagged.csv'))

# ── Update inserts JSON with adjusted tiers ───────────────────────────
# Build lookup: subcat -> adjusted_score
adj_lookup = {r['matched_subcategory']: r['adjusted_score']
              for _, r in counts.iterrows()}
pres_lookup = {r['matched_subcategory']: int(r['presenter_count'])
               for _, r in counts.iterrows()}

def assign_tier(score):
    if score >= TIER1_CUT: return 'Tier 1'
    if score >= TIER2_CUT: return 'Tier 2'
    return 'Standard'

adjusted_inserts = {}
tier_changes = []

for snum, sess in inserts.items():
    new_sess = dict(sess)
    # Update each subcat detail with adjusted score
    new_details = []
    for sd in sess['subcat_details']:
        sc = sd['subcategory']
        orig_score = sd['yield_score']
        pres_count = pres_lookup.get(sc, 0)
        adj_score  = apply_tiebreaker(orig_score, pres_count)
        new_sd = dict(sd)
        new_sd['yield_score_original'] = orig_score
        new_sd['presenter_poll_count'] = pres_count
        new_sd['adjusted_score'] = round(adj_score, 4)
        new_sd['tier'] = assign_tier(adj_score)
        new_sd['yield_score'] = round(adj_score, 4)  # update primary score
        new_details.append(new_sd)

    new_details.sort(key=lambda x: x['adjusted_score'], reverse=True)

    new_best  = new_details[0]['adjusted_score'] if new_details else 0.0
    new_tier  = assign_tier(new_best)
    orig_tier = sess['session_tier']

    if new_tier != orig_tier:
        tier_changes.append({
            'session': snum,
            'name': sess['session_name'][:55],
            'orig_tier': orig_tier,
            'new_tier': new_tier,
            'orig_score': sess['best_yield_score'],
            'new_score': round(new_best, 4)
        })

    new_sess['subcat_details']       = new_details
    new_sess['best_yield_score']     = round(new_best, 4)
    new_sess['session_tier']         = new_tier
    new_sess['tier1_subcategories']  = [s['subcategory'] for s in new_details if s['tier'] == 'Tier 1']
    new_sess['tier2_subcategories']  = [s['subcategory'] for s in new_details if s['tier'] == 'Tier 2']
    new_sess['top_subcategory']      = new_details[0] if new_details else {}

    # Attach full poll questions for this session (for outline injection later)
    sess_poll = tagged_df[tagged_df['session_number'] == int(snum)]
    poll_list = []
    for _, pq in sess_poll.iterrows():
        poll_list.append({
            'question_num': int(pq['question_num']),
            'page_num':     int(pq['page_num']),
            'stem':         str(pq['stem']),
            'choice_A':     str(pq.get('choice_A', '')),
            'choice_B':     str(pq.get('choice_B', '')),
            'choice_C':     str(pq.get('choice_C', '')),
            'choice_D':     str(pq.get('choice_D', '')),
            'matched_subcat': str(pq.get('matched_subcategory', '')),
        })
    new_sess['poll_questions'] = poll_list

    adjusted_inserts[snum] = new_sess

with open(OUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(adjusted_inserts, f, indent=2, ensure_ascii=False)

# ── Print summary ─────────────────────────────────────────────────────
t1 = [(k,v) for k,v in adjusted_inserts.items() if v['session_tier']=='Tier 1']
t2 = [(k,v) for k,v in adjusted_inserts.items() if v['session_tier']=='Tier 2']
st = [(k,v) for k,v in adjusted_inserts.items() if v['session_tier']=='Standard']

print(f'Poll questions tagged (matched): {matched.shape[0]} / {len(poll)}')
print(f'Subcategories with presenter data: {len(counts)}')
print(f'\nTIER DISTRIBUTION (tiebreaker mode):')
print(f'  Tier 1:   {len(t1)} sessions')
print(f'  Tier 2:   {len(t2)} sessions')
print(f'  Standard: {len(st)} sessions')

if tier_changes:
    print(f'\nTIER CHANGES vs. ITE-only scoring:')
    for tc in tier_changes:
        print(f'  Sess {tc["session"]} {tc["orig_tier"]} --> {tc["new_tier"]}  '
              f'({tc["orig_score"]:.2f} -> {tc["new_score"]:.2f})  {tc["name"]}')
else:
    print('\nNo tier changes — presenter emphasis confirmed existing ITE tiers.')

print()
print('='*70)
print('FULL SESSION TIER LIST — REVIEW COPY')
print('='*70)

def print_tier_block(label, sessions):
    print(f'\n{label}')
    print('-'*70)
    for k, v in sorted(sessions, key=lambda x: x[1]['best_yield_score'], reverse=True):
        score    = v['best_yield_score']
        orig     = v.get('subcat_details', [{}])[0].get('yield_score_original', score)
        t1subs   = v['tier1_subcategories']
        t2subs   = v['tier2_subcategories']
        std_subs = [s['subcategory'] for s in v['subcat_details'] if s['tier']=='Standard']
        top3     = (t1subs + t2subs + std_subs)[:3]
        polls    = sum(s.get('presenter_poll_count', 0) for s in v['subcat_details'])
        changed  = any(tc['session']==k for tc in tier_changes)
        flag     = ' *** CHANGED' if changed else ''
        print(f'  [{score:.2f}] Sess {k}: {v["session_name"][:52]}{flag}')
        print(f'         Top subcats : {", ".join(top3)}')
        print(f'         Poll Qs     : {polls}')

print_tier_block('TIER 1  [adjusted score >= 1.0]', t1)
print_tier_block('TIER 2  [adjusted score 0.5 – 0.99]', t2)
print_tier_block('STANDARD  [adjusted score < 0.5]', st)

print(f'\nOutput JSON: {OUT_JSON}')
