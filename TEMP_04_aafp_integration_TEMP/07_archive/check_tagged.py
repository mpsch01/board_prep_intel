import openpyxl, re

wb = openpyxl.load_workbook(
    r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\ite_exam\03_database\ABFM_ITE_AI_Tagged_excel.xlsx',
    read_only=True
)
ws = wb.active
rows = list(ws.iter_rows(values_only=True))

for target_year in (2024, 2025):
    found = 0
    for row in rows[1:]:
        if row[1] == target_year:
            print(f'=== Year {target_year} | QID: {row[0]} ===')
            expl = str(row[6] or '')
            print(f'Expl tail (last 500 chars):')
            print(repr(expl[-500:]))
            print()
            found += 1
            if found == 2:
                break

# Also count how many rows per year have non-empty explanation
from collections import defaultdict
year_counts = defaultdict(lambda: {'total':0,'has_expl':0,'has_ref':0})
for row in rows[1:]:
    yr = row[1]
    if yr:
        year_counts[yr]['total'] += 1
        expl = str(row[6] or '')
        if len(expl) > 10:
            year_counts[yr]['has_expl'] += 1
        if 'Ref:' in expl or 'Reference' in expl:
            year_counts[yr]['has_ref'] += 1

print('Year | Total | Has Expl | Has Ref text')
for yr in sorted(year_counts):
    d = year_counts[yr]
    print(f'{yr}  | {d["total"]:5d} | {d["has_expl"]:8d} | {d["has_ref"]:12d}')
