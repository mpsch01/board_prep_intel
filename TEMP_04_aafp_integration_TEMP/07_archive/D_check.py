import json

with open(r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\keyword_library\session_keyword_library.json') as f:
    lib = json.load(f)

# Session 02 - show all terms, check for hypertension
s02 = lib['02']
terms = [k['term'] for k in s02['keywords']]
print("Session 02 all terms:")
for k in s02['keywords']:
    print(f"  {k['term']:30s}  composite={k['composite']:.3f}  time={k['time_sec']:.0f}s  outline={k['in_outline']}")

print()
print("'hypertension' present?", any('hypertension' in t.lower() for t in terms))
print("'blood pressure' present?", any('blood pressure' in t.lower() for t in terms))
