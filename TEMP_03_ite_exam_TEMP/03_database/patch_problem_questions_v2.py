"""
patch_problem_questions_v2.py
Re-parses problem questions directly from master bank and patches clean JSON.
"""
import sys, json, re, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')

JSON_PATH = r"C:\Users\mpsch\Desktop\claude_knowledge\board_prep\ite_exam\03_database\ite_questions_clean.json"
XLSX_PATH = r"C:\Users\mpsch\Desktop\claude_knowledge\board_prep\ite_exam\03_database\ABFM_ITE_Master_v2.xlsx"

ENCODING_MAP = {
    'â€"': '–', 'â€"': '—', 'â€˜': '\u2018', 'â€™': '\u2019',
    'â€œ': '\u201c', 'â€': '\u201d', 'Â°': '°', 'Â½': '½',
    'â€¢': '•', 'Î±': 'α', 'Î²': 'β', 'Î³': 'γ', 'Î¼': 'μ',
    'ï‚³': '≥', 'ï€­': '-', 'ï‚·': '·', 'Âµ': 'µ',
}
def fix_enc(t):
    if not isinstance(t, str): return ''
    for b, g in ENCODING_MAP.items(): t = t.replace(b, g)
    return t.strip()

def parse_newline(stem):
    clean = re.sub(r'(\n[A-E]\) *\n?){3,}\s*$', '', stem.strip())
    clean = re.sub(r'\n\d+\nItem #\d+\n\d+', '', clean).strip()
    parts = re.split(r'\n([A-E])\) ', clean)
    if len(parts) < 3:
        return fix_enc(clean), []
    q_text = parts[0].strip()
    choices = []
    for i in range(1, len(parts)-1, 2):
        choices.append({'letter': parts[i], 'text': fix_enc(parts[i+1].strip() if i+1 < len(parts) else '')})
    return fix_enc(q_text), choices

def parse_inline(stem):
    m = re.search(r'(A\) .+)', stem, re.DOTALL)
    if not m: return fix_enc(stem.strip()), []
    q_text = fix_enc(stem[:m.start()].strip())
    parts = re.split(r'\s+([B-E])\) ', m.group(1))
    choices = [{'letter': 'A', 'text': fix_enc(parts[0][2:].strip())}]
    for i in range(1, len(parts)-1, 2):
        choices.append({'letter': parts[i], 'text': fix_enc(parts[i+1].strip())})
    return q_text, choices

# Load data
df = pd.read_excel(XLSX_PATH)
df_dict = {str(r['QuestionID']): r for _, r in df.iterrows()}

with open(JSON_PATH, encoding='utf-8') as f:
    qs = json.load(f)
q_by_id = {q['question_id']: q for q in qs}

TARGET_QIDS = ['Q2022-494', 'Q2021-206', 'Q2022-487', 'Q2022-489', 'Q2020-049']

for qid in TARGET_QIDS:
    row = df_dict[qid]
    stem = str(row['QuestionStem'])
    correct = str(row['CorrectAnswer']).strip()
    expl = fix_enc(str(row['Explanation'])) if pd.notna(row['Explanation']) else ''

    # Try newline parser first, fall back to inline
    q_text, choices = parse_newline(stem)
    if len(choices) < 2:
        q_text, choices = parse_inline(stem)

    correct_text = next((c['text'] for c in choices if c['letter'] == correct), '')

    # Update the JSON entry
    q = q_by_id[qid]
    q['question_text'] = q_text
    q['choices'] = choices
    q['correct_letter'] = correct
    q['correct_text'] = correct_text
    q['explanation'] = expl
    q['needs_review'] = not correct_text or len(choices) < 2

    status = 'FIXED' if not q['needs_review'] else 'STILL BROKEN'
    print(f"{qid} [{status}]: {len(choices)} choices, correct={correct}, text='{correct_text[:50]}'")

# Handle Q2020-036 substitute
q_broken = q_by_id['Q2020-036']
candidates = [q for q in qs
              if q['body_system'] == q_broken['body_system']
              and not q['needs_review']
              and q['question_id'] != 'Q2020-036'
              and q['exam_year'] >= 2022]
candidates.sort(key=lambda x: x['exam_year'], reverse=True)
if candidates:
    q_broken['substitute_qid'] = candidates[0]['question_id']
    print(f"\nQ2020-036 substitute: {candidates[0]['question_id']} ({candidates[0]['subcategory']})")

with open(JSON_PATH, 'w', encoding='utf-8') as f:
    json.dump(qs, f, ensure_ascii=False, indent=2)

# Final check
still_broken = [q for q in qs if q['needs_review'] and q['question_id'] in TARGET_QIDS + ['Q2020-036']]
print(f"\nFinal needs_review: {[q['question_id'] for q in still_broken]}")
print("Done.")
