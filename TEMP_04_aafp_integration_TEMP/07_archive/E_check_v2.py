import json
with open(r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\02_working\session_hy_inserts_v2_adjusted.json', encoding='utf-8') as f:
    v2 = json.load(f)
# Show keys and structure for first session
first = list(v2.items())[0]
print('Top-level keys per session:', list(first[1].keys()))
print()
print('Sample session 02:')
s = v2.get('02', list(v2.values())[0])
for k, v in s.items():
    if k in ('ite_questions','must_read_refs','core_refs'):
        print(f'  {k}: [{len(v)} items] first= {str(v[0])[:120] if v else "[]"}')
    else:
        print(f'  {k}: {v}')
