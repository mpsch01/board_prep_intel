import json

data = json.load(open(r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\02_working\session_hy_inserts_v4.json', encoding='utf-8'))

check_sessions = ['06', '13', '26', '42', '47']
for sid in check_sessions:
    s = data[sid]
    print(f"[{sid}] {s['session_title']}")
    print(f"     Qs={s['question_count']}  Must-Read={s['must_read_count']}  Core={s['core_count']}")
    for q in s['questions']:
        print(f"     Q{q['year']}-{q['qid']}  score={q['kw_score']:.3f}  hits={q['kw_hits']}")
        print(f"       focus: {q['focus'][:90]}")
    print("     REFS:")
    for r in s['refs'][:5]:
        print(f"       [{r['tier']}] {r['ref'][:90]}")
    print()
