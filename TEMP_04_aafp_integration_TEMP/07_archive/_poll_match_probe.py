"""
Quick matchability probe:
Take manually extracted poll questions from session 04 (HTN)
and score them against the keyword library to see if they
behave like ITE questions in terms of session assignment.
"""
import json, re, sys
sys.stdout.reconfigure(encoding='utf-8')

KW_PATH = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\keyword_library\session_keyword_library.json'
with open(KW_PATH, encoding='utf-8') as f:
    kw_lib = json.load(f)

# Manually reconstructed poll questions from session 04 transcript
poll_questions = [
    {
        "id": "POLL-04-01",
        "session_source": "Session 04 - Hypertension",
        "stem": "A 48-year-old female presents as a new patient with BP 172/110 in both arms. BMI 24, unremarkable exam, no medications. Chemistry notable for potassium 3.3. If her hypertension should prove refractory to treatment, which one of the following is most likely to reveal the cause of her elevated blood pressure?",
        "answer": "Aldosterone to renin ratio",
        "topic": "Secondary hypertension / primary hyperaldosteronism"
    },
    {
        "id": "POLL-04-02",
        "session_source": "Session 04 - Hypertension",
        "stem": "A 58-year-old woman has home BP 155/95 confirmed by multiple readings and office BP similar. She exercises, follows a low-salt diet, rarely drinks alcohol. Which one of the following medications would be most appropriate as initial therapy?",
        "answer": "Chlorthalidone",
        "topic": "First-line antihypertensive therapy"
    },
    {
        "id": "POLL-04-03",
        "session_source": "Session 04 - Hypertension",
        "stem": "A 62-year-old man presents for followup of hypertension on 4 medications. BP remains above goal. Which of the following adjustments would be most appropriate to bring his blood pressure to goal?",
        "answer": "Add spironolactone (resistant hypertension fifth agent)",
        "topic": "Resistant hypertension management"
    },
    {
        "id": "POLL-04-04",
        "session_source": "Session 04 - Hypertension",
        "stem": "A 57-year-old male with type 2 diabetes, BP 148/94, baseline creatinine 1.25. Which antihypertensive agent is most appropriate?",
        "answer": "ACE inhibitor or ARB",
        "topic": "HTN management in diabetes/CKD"
    },
]

def score_question(stem, kw_lib):
    stem_lower = stem.lower()
    results = []
    for sid, session in kw_lib.items():
        title = session.get('session_name', '')
        score = 0
        hits  = []
        for kw in session.get('keywords', []):
            k = kw.get('term','').lower()
            w = kw.get('composite', kw.get('tfidf_norm', 1))
            if k and k in stem_lower:
                score += w
                hits.append(k)
        if score > 0:
            results.append((score, sid, title, hits))
    results.sort(reverse=True)
    return results[:5]

print("=== POLL QUESTION MATCHABILITY PROBE ===\n")
for q in poll_questions:
    print(f"[{q['id']}] {q['topic']}")
    print(f"  Correct answer: {q['answer']}")
    top = score_question(q['stem'], kw_lib)
    print(f"  Top session matches:")
    for score, sid, title, hits in top:
        print(f"    Session {sid} ({title}): score={score:.2f}  hits={hits[:5]}")
    if top:
        best_sid = top[0][1]
        expected = "04"
        flag = "✔ CORRECT SESSION" if best_sid == expected else f"✗ Expected 04, got {best_sid}"
        print(f"  Result: {flag}")
    print()
