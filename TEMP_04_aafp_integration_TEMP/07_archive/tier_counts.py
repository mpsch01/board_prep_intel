import json
with open(r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\02_working\session_hy_inserts_v2_adjusted.json', encoding='utf-8') as f:
    inserts = json.load(f)

from collections import Counter
tiers = Counter(v['session_tier'] for v in inserts.values())
total = sum(tiers.values())

print(f'Tier 1   : {tiers["Tier 1"]:3d} sessions  ({tiers["Tier 1"]/total*100:.1f}%)')
print(f'Tier 2   : {tiers["Tier 2"]:3d} sessions  ({tiers["Tier 2"]/total*100:.1f}%)')
print(f'Standard : {tiers["Standard"]:3d} sessions  ({tiers["Standard"]/total*100:.1f}%)')
print(f'─────────────────────────────')
print(f'Total    : {total:3d} sessions')
