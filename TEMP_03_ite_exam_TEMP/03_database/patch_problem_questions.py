"""
patch_problem_questions.py
Manually patches the 8 flagged supplement questions in ite_questions_clean.json
"""
import sys, json, re
sys.stdout.reconfigure(encoding='utf-8')

JSON_PATH = r"C:\Users\mpsch\Desktop\claude_knowledge\board_prep\ite_exam\03_database\ite_questions_clean.json"

with open(JSON_PATH, encoding='utf-8') as f:
    qs = json.load(f)

q_by_id = {q['question_id']: q for q in qs}

# ── Manual patches ─────────────────────────────────────────────────────────────

# Q2022-494 — clean newline format, parser just missed correct answer (A)
# Choices ARE parsed correctly, just needs correct_text fixed
q = q_by_id['Q2022-494']
q['correct_text'] = next((c['text'] for c in q['choices'] if c['letter'] == 'A'), '')
q['needs_review'] = False
print(f"Q2022-494: correct_text = '{q['correct_text'][:60]}'")

# Q2021-206 — stray page markers in stem, choices fine, just fix correct_text (E)
q = q_by_id['Q2021-206']
# Clean stray markers from question_text
q['question_text'] = re.sub(r'\n\d+\nItem #\d+\n\d+', '', q['question_text']).strip()
q['correct_text'] = next((c['text'] for c in q['choices'] if c['letter'] == 'E'), '')
q['needs_review'] = False
print(f"Q2021-206: correct_text = '{q['correct_text'][:60]}'")

# Q2022-487 — only 4 choices (A-D), no E. Correct is B. Perfectly usable.
q = q_by_id['Q2022-487']
q['correct_text'] = next((c['text'] for c in q['choices'] if c['letter'] == 'B'), '')
q['needs_review'] = len(q['choices']) < 2 or not q['correct_text']
print(f"Q2022-487: {len(q['choices'])} choices, correct_text = '{q['correct_text'][:60]}'")

# Q2022-489 — has ï‚³ artifact (≥ sign) in one choice. Fix encoding, correct is D.
q = q_by_id['Q2022-489']
for c in q['choices']:
    c['text'] = c['text'].replace('ï‚³', '≥').replace('ï€­', '-').replace('ï‚·', '·')
q['question_text'] = q['question_text'].replace('ï‚³', '≥')
q['correct_text'] = next((c['text'] for c in q['choices'] if c['letter'] == 'D'), '')
q['needs_review'] = False
print(f"Q2022-489: correct_text = '{q['correct_text'][:60]}'")

# Q2022-487 appears in sessions 14, 15, 16 — already patched above

# Q2020-049 — 4 choices (A-D), correct is B. Perfectly usable.
q = q_by_id['Q2020-049']
q['correct_text'] = next((c['text'] for c in q['choices'] if c['letter'] == 'B'), '')
q['needs_review'] = len(q['choices']) < 2 or not q['correct_text']
print(f"Q2020-049: {len(q['choices'])} choices, correct_text = '{q['correct_text'][:60]}'")

# Q2020-036 — genuinely garbled lab table (ï€® artifacts). REPLACE with Q2020-037.
# Find a good substitute from same body system
q_broken = q_by_id['Q2020-036']
print(f"\nQ2020-036 body_system: {q_broken['body_system']}, subcategory: {q_broken['subcategory']}")
# Find clean substitute from same body system
candidates = [q for q in qs
              if q['body_system'] == q_broken['body_system']
              and not q['needs_review']
              and q['question_id'] != 'Q2020-036'
              and q['exam_year'] >= 2022]  # prefer recent
candidates.sort(key=lambda x: x['exam_year'], reverse=True)
if candidates:
    sub = candidates[0]
    print(f"Substitute for Q2020-036: {sub['question_id']} ({sub['body_system']}, {sub['subcategory']})")
    # Store substitute ID as a note
    q_broken['substitute_qid'] = sub['question_id']
    q_broken['needs_review'] = True  # keep flagged, injection script will use substitute

print("\n── Summary ──")
still_broken = [q for q in qs if q['needs_review'] and q['question_id'] in
                ['Q2022-494','Q2021-206','Q2022-487','Q2022-489','Q2020-049','Q2020-036']]
print(f"Still needs_review after patches: {[q['question_id'] for q in still_broken]}")

with open(JSON_PATH, 'w', encoding='utf-8') as f:
    json.dump(qs, f, ensure_ascii=False, indent=2)
print(f"\nSaved patched JSON.")
