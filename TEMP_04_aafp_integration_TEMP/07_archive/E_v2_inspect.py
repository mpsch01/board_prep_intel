import json, csv

CW = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\02_working\session_cluster_crosswalk.csv'
TIER = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\ite_refs\02_working\ITE_Reference_Tiers_Clean.csv'
V4 = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\02_working\session_hy_inserts_v4.json'

with open(CW, encoding='utf-8') as f:
    cw = list(csv.DictReader(f))
print('=== CROSSWALK ===')
print('Cols:', list(cw[0].keys()))
print('Row 0:', cw[0])
print('Row 1:', cw[1])
print()

with open(TIER, encoding='utf-8') as f:
    tier = list(csv.DictReader(f))
print('=== TIER DB ===')
print('Cols:', list(tier[0].keys()))
print('Row 0:', tier[0])
print('Total:', len(tier))
print()

with open(V4, encoding='utf-8') as f:
    v4 = json.load(f)
print('=== V4 JSON ===')
print('Type:', type(v4))
if isinstance(v4, dict):
    print('Keys:', list(v4.keys())[:5])
    first_key = list(v4.keys())[0]
    print('First entry:', json.dumps(v4[first_key], indent=2)[:600])
elif isinstance(v4, list):
    print('Length:', len(v4))
    print('First:', json.dumps(v4[0], indent=2)[:600])
