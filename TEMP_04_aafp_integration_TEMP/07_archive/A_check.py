import json
with open(r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\keyword_library\raw_files\outline_terms.json') as f:
    data = json.load(f)

# Show first 30 terms for session 02 and session 14
for snum in ['02', '14']:
    s = data[snum]
    print(f"Session {snum}: {s['session_name']}")
    print(f"  Terms (first 30): {s['terms'][:30]}")
    print()
