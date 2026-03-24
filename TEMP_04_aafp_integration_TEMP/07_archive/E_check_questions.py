import csv
with open(r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\ite_exam\03_database\ABFM_ITE_Enriched.csv', encoding='utf-8') as f:
    rows = list(csv.DictReader(f))
print('Total questions:', len(rows))
# Show cluster and keyword fields for first 10
for r in rows[:10]:
    print(f"  Cluster={r.get('Subcategory_Cluster','')[:35]:35s} | Keywords={r.get('Cluster_Keywords','')[:50]}")
