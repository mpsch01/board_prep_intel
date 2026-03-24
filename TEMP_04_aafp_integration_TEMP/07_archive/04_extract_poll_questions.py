"""
Script: 04_extract_poll_questions.py
Extracts AES/poll questions from all 48 session PDFs.
Output: poll_questions_raw.csv (one row per question)
"""

import pdfplumber, re, csv, os, sys
sys.stdout.reconfigure(encoding='utf-8')

PDF_DIR = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\01_source\slides'
OUTPUT  = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\02_working\poll_questions_raw.csv'
RAW_DIR = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\07_archive'
os.makedirs(RAW_DIR, exist_ok=True)

# Patterns
AES_FLAG   = re.compile(r'AES\s*Question', re.IGNORECASE)
Q_HEADER   = re.compile(r'^Question\s+(\d+)\s*$', re.IGNORECASE)
ANSWER_OPT = re.compile(r'^([A-D])\.\s+(.+)', re.IGNORECASE)

def parse_session_num(fname):
    m = re.match(r'^(\d+)-', fname)
    return int(m.group(1)) if m else None

def extract_questions_from_pdf(filepath):
    """
    Returns list of dicts:
      {question_num, stem, choices: {A,B,C,D}, page_num}
    Strategy: scan pages for AES Question flag or Question N header.
    Collect lines until next AES flag or next content slide header.
    """
    questions = []
    fname = os.path.basename(filepath)
    snum  = parse_session_num(fname)

    with pdfplumber.open(filepath) as pdf:
        # First pass: collect all page texts
        pages = []
        for i, page in enumerate(pdf.pages):
            txt = page.extract_text() or ''
            pages.append((i+1, txt))

        # Build a flat list of (page_num, line) pairs
        flat = []
        for pnum, txt in pages:
            for line in txt.splitlines():
                line = line.strip()
                if line:
                    flat.append((pnum, line))

        # Walk flat list, collect question blocks
        i = 0
        pending_aes = False  # saw AES Question flag, next Question N starts the block
        current_q   = None

        while i < len(flat):
            pnum, line = flat[i]

            # AES Question marker
            if AES_FLAG.search(line):
                pending_aes = True
                i += 1
                continue

            # Question N header
            qm = Q_HEADER.match(line)
            if qm:
                # Save previous question if any
                if current_q and current_q['stem']:
                    questions.append(current_q)
                qnum = int(qm.group(1))
                current_q = {
                    'session_number': snum,
                    'session_file':   fname,
                    'question_num':   qnum,
                    'page_num':       pnum,
                    'stem':           '',
                    'choice_A': '', 'choice_B': '',
                    'choice_C': '', 'choice_D': ''
                }
                pending_aes = False
                i += 1
                continue

            # If we have an active question, collect stem / choices
            if current_q is not None:
                am = ANSWER_OPT.match(line)
                if am:
                    letter = am.group(1).upper()
                    current_q[f'choice_{letter}'] = am.group(2).strip()
                else:
                    # Stop collecting stem if we hit a new slide header signal
                    # (all caps line > 4 words that isn't a choice = likely new slide)
                    words = line.split()
                    if (len(words) > 5 and line == line.upper() and
                            not any(c in line for c in ['?', ','])):
                        # Looks like a new content slide header — stop
                        questions.append(current_q)
                        current_q = None
                    else:
                        # Add to stem
                        if current_q['stem']:
                            current_q['stem'] += ' ' + line
                        else:
                            current_q['stem'] = line

            i += 1

        # Don't forget last question
        if current_q and current_q['stem']:
            questions.append(current_q)

    return questions

# --- Run all PDFs ---
all_questions = []
pdf_files = sorted([f for f in os.listdir(PDF_DIR) if f.endswith('.pdf')])

for fname in pdf_files:
    fpath = os.path.join(PDF_DIR, fname)
    try:
        qs = extract_questions_from_pdf(fpath)
        all_questions.extend(qs)
        print(f'  {fname}: {len(qs)} questions extracted')
    except Exception as e:
        print(f'  ERROR {fname}: {e}')

# Write raw output
fields = ['session_number','session_file','question_num','page_num',
          'stem','choice_A','choice_B','choice_C','choice_D']

with open(OUTPUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(all_questions)

# Also save to raw_files for reference
import shutil
shutil.copy(OUTPUT, os.path.join(RAW_DIR, 'poll_questions_raw.csv'))

print(f'\nTotal questions extracted: {len(all_questions)}')
print(f'Output: {OUTPUT}')
