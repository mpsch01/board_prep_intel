"""
build_clean_question_bank.py
Parses ABFM_ITE_Master_v2.xlsx into a clean injection-ready JSON.
Outputs: board_prep/ite_exam/03_database/ite_questions_clean.json
"""
import sys, re, json, pandas as pd
from collections import Counter
sys.stdout.reconfigure(encoding='utf-8')

SRC  = r"C:\Users\mpsch\Desktop\claude_knowledge\board_prep\ite_exam\03_database\ABFM_ITE_Master_v2.xlsx"
OUT  = r"C:\Users\mpsch\Desktop\claude_knowledge\board_prep\ite_exam\03_database\ite_questions_clean.json"

# ── Encoding fix ──────────────────────────────────────────────────────────────
ENCODING_MAP = {
    'â€"': '–', 'â€"': '—', 'â€˜': '\u2018', 'â€™': '\u2019',
    'â€œ': '\u201c', 'â€': '\u201d', 'Â°': '°', 'Â½': '½',
    'Â¼': '¼', 'Â¾': '¾', 'â€¢': '•', 'Î±': 'α', 'Î²': 'β',
    'Î³': 'γ', 'Î¼': 'μ', 'Âµ': 'µ',
}

def fix_encoding(text):
    if not isinstance(text, str): return ''
    for bad, good in ENCODING_MAP.items():
        text = text.replace(bad, good)
    return text.strip()

# ── Stem format detection ─────────────────────────────────────────────────────
def detect_format(stem):
    if re.search(r'\nA\) .+\nB\)', stem):
        return 'newline'
    elif re.search(r'A\) .{3,} B\) .{3,}', stem):
        return 'inline'
    elif re.search(r'ï€®', stem):
        return 'garbled'
    return 'other'

# ── Choice parsers ────────────────────────────────────────────────────────────
def parse_newline(stem):
    """Choices on separate lines: \nA) text\nB) text"""
    # Strip trailing blank answer block first
    clean = re.sub(r'(\n[A-E]\) *\n?){3,}\s*$', '', stem.strip())
    # Split on choice labels
    parts = re.split(r'\n([A-E])\) ', clean)
    if len(parts) < 3:
        return clean, []
    question_text = parts[0].strip()
    choices = []
    for i in range(1, len(parts)-1, 2):
        letter = parts[i]
        text   = parts[i+1].strip() if i+1 < len(parts) else ''
        choices.append({'letter': letter, 'text': fix_encoding(text)})
    return fix_encoding(question_text), choices

def parse_inline(stem):
    """Choices run together: A) text B) text C) text"""
    # Find where choices start
    m = re.search(r'(A\) .+)', stem, re.DOTALL)
    if not m:
        return fix_encoding(stem.strip()), []
    question_text = fix_encoding(stem[:m.start()].strip())
    choices_raw   = m.group(1)
    # Split on letter boundaries
    parts = re.split(r'\s+([B-E])\) ', choices_raw)
    choices = [{'letter': 'A', 'text': fix_encoding(parts[0][2:].strip())}]
    for i in range(1, len(parts)-1, 2):
        choices.append({'letter': parts[i], 'text': fix_encoding(parts[i+1].strip())})
    return question_text, choices

# ── Main ──────────────────────────────────────────────────────────────────────
df = pd.read_excel(SRC)
print(f"Loaded {len(df)} questions")

results = []
stats = Counter()

for _, row in df.iterrows():
    stem      = str(row['QuestionStem']) if pd.notna(row['QuestionStem']) else ''
    correct   = str(row['CorrectAnswer']).strip() if pd.notna(row['CorrectAnswer']) else ''
    expl      = fix_encoding(str(row['Explanation'])) if pd.notna(row['Explanation']) else ''
    fmt       = detect_format(stem)
    stats[fmt] += 1

    if fmt == 'newline':
        q_text, choices = parse_newline(stem)
    elif fmt == 'inline':
        q_text, choices = parse_inline(stem)
    else:
        q_text  = fix_encoding(stem.strip())
        choices = []

    correct_text = next((c['text'] for c in choices if c['letter'] == correct), None)

    results.append({
        'question_id':   str(row['QuestionID']),
        'exam_year':     int(row['ExamYear']) if pd.notna(row['ExamYear']) else 0,
        'body_system':   str(row['BodySystem']) if pd.notna(row['BodySystem']) else '',
        'subcategory':   str(row['Subcategory']) if pd.notna(row['Subcategory']) else '',
        'blueprint':     str(row['BlueprintCategory']) if pd.notna(row['BlueprintCategory']) else '',
        'format':        fmt,
        'question_text': q_text,
        'choices':       choices,
        'correct_letter': correct,
        'correct_text':  correct_text or '',
        'explanation':   expl,
        'reference':     fix_encoding(str(row['Reference'])) if pd.notna(row['Reference']) else '',
        'needs_review':  fmt in ('garbled', 'other') or correct_text is None or len(choices) < 4,
    })

# Stats
print(f"\nFormat distribution: {dict(stats)}")
needs_review = sum(1 for r in results if r['needs_review'])
no_correct   = sum(1 for r in results if not r['correct_text'])
print(f"Needs review: {needs_review}")
print(f"Missing correct answer text: {no_correct}")
print(f"Ready for injection: {len(results) - needs_review}")

with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"\nSaved: {OUT}")
