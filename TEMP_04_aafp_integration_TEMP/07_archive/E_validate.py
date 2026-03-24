import json

with open(r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\02_working\session_hy_inserts_v3.json', encoding='utf-8') as f:
    v3 = json.load(f)

# Session 02 - what's the must-read?
print("=== SESSION 02 MUST-READ REFS ===")
for r in v3['02']['must_read_refs']:
    print(f"  Score={r['match_score']} | Terms={r['matched_terms']}")
    print(f"  {r['citation'][:100]}")
    print()

# Session 19 - why no questions?
print("=== SESSION 19 TOP QUESTIONS ===")
print(f"  Count: {len(v3['19']['top_questions'])}")
print(f"  Session: {v3['19']['session_name']}")

# Session 37 - same
print("=== SESSION 37 TOP QUESTIONS ===")
print(f"  Count: {len(v3['37']['top_questions'])}")
print(f"  Session: {v3['37']['session_name']}")

# Session 03 - check no must-read is actually appropriate
print("\n=== SESSION 03 MUST-READ REFS (ACS/Hyperlipidemia) ===")
print(f"  Must-read count: {len(v3['03']['must_read_refs'])}")
print(f"  Core refs: {len(v3['03'].get('core_refs',[]))}")
for r in v3['03'].get('core_refs',[])[:3]:
    print(f"  Core: {r['citation'][:80]}")
