"""
build_poll_inserts.py  (v2 — deduplicated)
==========================================
Key fix: for each (session, question_num), keep the row WITH choices.
If neither has choices, keep the one with the longer stem.
"""
import pandas as pd
import json, re, sys
sys.stdout.reconfigure(encoding='utf-8')

RAW_CSV  = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\03_poll_questions\poll_questions_raw.csv'
KW_JSON  = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\keyword_library\session_keyword_library.json'
OUT_JSON = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\03_poll_questions\poll_inserts.json'

with open(KW_JSON, encoding='utf-8') as f:
    kw_lib = json.load(f)
session_titles = {sid: v['session_name'] for sid, v in kw_lib.items()}

df = pd.read_csv(RAW_CSV)
print(f"Loaded {len(df)} rows across {df.session_number.nunique()} sessions (before dedup)")

def has_choices(row):
    return any(pd.notna(row.get(f'choice_{l}', None)) and str(row.get(f'choice_{l}','')).strip() not in ('','nan')
               for l in ['A','B','C','D'])

def clean_stem(raw_stem):
    s = str(raw_stem).strip()
    idx = s.find('?')
    if idx == -1:
        return s, False
    candidate = s[:idx+1].strip()
    if len(candidate) < 20:
        idx2 = s.find('?', idx+1)
        if idx2 != -1:
            candidate = s[:idx2+1].strip()
    return candidate, len(candidate) < 50

def clean_choice(raw):
    s = str(raw).strip()
    if s.lower() in ('nan','none',''):
        return None
    return re.sub(r'\s+', ' ', s)[:200]

# Deduplicate: per (session_number, question_num), prefer row with choices
df['_has_choices'] = df.apply(has_choices, axis=1)
df['_stem_len']    = df['stem'].str.len()

# Sort so rows WITH choices come first, then take first per group
df_sorted = df.sort_values(['session_number','question_num','_has_choices','_stem_len'],
                            ascending=[True, True, False, False])
df_dedup = df_sorted.drop_duplicates(subset=['session_number','question_num'], keep='first')
print(f"After dedup: {len(df_dedup)} questions across {df_dedup.session_number.nunique()} sessions")

result = {}
flags  = []

for _, row in df_dedup.iterrows():
    sid   = str(int(row['session_number'])).zfill(2)
    q_num = int(row['question_num'])

    stem_clean, ctx_short = clean_stem(row['stem'])

    choices = {}
    for letter in ['A','B','C','D']:
        val = clean_choice(row.get(f'choice_{letter}', ''))
        if val:
            choices[letter] = val

    poll_id = f"POLL-{sid}-{q_num:02d}"
    if ctx_short:
        flags.append(poll_id)

    q_entry = {
        "poll_id":       poll_id,
        "source":        f"Session {sid} \u2014 AAFP Board Prep Poll Question",
        "stem":          stem_clean,
        "choices":       choices,
        "context_short": ctx_short
    }

    if sid not in result:
        title = session_titles.get(sid, f"Session {sid}")
        result[sid] = {"session_id": sid, "session_title": title,
                       "poll_count": 0, "questions": []}

    result[sid]["questions"].append(q_entry)
    result[sid]["poll_count"] += 1

with open(OUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"\nWrote {len(result)} sessions, {sum(v['poll_count'] for v in result.values())} questions")
print(f"Context-short flags ({len(flags)}): {flags}")

# Spot-check session 06
s06 = result.get('06', {})
print(f"\nSession 06 sample (first 3):")
for q in s06.get('questions', [])[:3]:
    print(f"  {q['poll_id']}: stem={q['stem'][:60]}  choices={list(q['choices'].keys())}")
