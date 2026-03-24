import json
d = json.load(open(r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\keyword_library\session_keyword_library.json'))
keys = list(d.keys())[:3]
print('Top-level keys:', keys)
sid = keys[0]
val = d[sid]
print('Type of value:', type(val))
print('Sample:', str(val)[:400])
