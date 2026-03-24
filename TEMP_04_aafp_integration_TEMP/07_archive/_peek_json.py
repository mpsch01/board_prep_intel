import json, sys
sys.stdout.reconfigure(encoding='utf-8')
d = json.load(open(r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\02_working\session_hy_inserts_v7.json'))
s = d['02']
q = s['questions'][0]
print('Keys:', list(q.keys()))
print('Sample Q:', q)
print()
print('Sample ref:', s['refs'][0])
