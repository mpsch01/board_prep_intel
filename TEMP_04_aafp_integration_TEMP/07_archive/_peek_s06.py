import json, sys
sys.stdout.reconfigure(encoding='utf-8')
p = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\03_poll_questions\poll_inserts.json'
with open(p, encoding='utf-8') as f:
    d = json.load(f)
s = d['06']
for q in s['questions'][:6]:
    print(f"--- {q['poll_id']} ---")
    print(f"  stem: {q['stem'][:120]}")
    print(f"  ctx_short: {q['context_short']}")
    print(f"  choices: {list(q['choices'].keys()) if q['choices'] else 'NONE'}")
    print()
