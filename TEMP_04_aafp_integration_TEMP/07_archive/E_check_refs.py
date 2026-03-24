import csv
with open(r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\ite_refs\03_database\ITE_Reference_Tiers_Final.csv', encoding='utf-8') as f:
    rows = list(csv.DictReader(f))
print('Total refs:', len(rows))
print('Columns:', list(rows[0].keys()))
print()
print('Sample Categories values (first 25 refs):')
for r in rows[:25]:
    print(f"  Tier={r['Tier']:10s} | Cat={r['Categories']:40s} | {r['CleanRef'][:60]}")
print()
# Show unique category values
cats = set(r['Categories'] for r in rows)
print(f'Unique category values ({len(cats)}):')
for c in sorted(cats):
    print(f'  "{c}"')
