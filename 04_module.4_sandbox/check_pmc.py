import csv
from collections import Counter

CSV = r'C:\Users\mpsch\Desktop\board_prep_intel\01_module.1_warehouse\scripts\maintain\pmc_oa_results.csv'

with open(CSV, newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

print("COLS:", reader.fieldnames)
print("Total rows:", len(rows))

oa_status_counts = Counter(r['oa_status'] for r in rows)
dl_status_counts = Counter(r['download_status'] for r in rows)
print("\noa_status values:", dict(oa_status_counts))
print("download_status values:", dict(dl_status_counts))

# Show a not-downloaded row
not_dl = [r for r in rows if r['download_status'] != 'downloaded']
if not_dl:
    print("\nSample not-downloaded row:", dict(not_dl[0]))
