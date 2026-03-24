import csv, re

with open(r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\ite_exam\03_database\ABFM_ITE_Enriched.csv', encoding='utf-8') as f:
    rows = list(csv.DictReader(f))

# Patterns that suggest a citation is present
ref_patterns = [
    r'Ref(?:erence)?s?:',
    r'\b[A-Z][a-z]+ [A-Z]{1,2},',   # Author LastName Initials,
    r'Am Fam Physician',
    r'N Engl J Med',
    r'JAMA',
    r'Ann Intern Med',
    r'\d{4};\d+\(',                   # year;vol(issue)
]
combined = re.compile('|'.join(ref_patterns))

has_ref = []
no_ref = []
for r in rows:
    expl = r.get('Explanation', '')
    if combined.search(expl):
        has_ref.append(r)
    else:
        no_ref.append(r)

print(f'Questions WITH parseable ref in Explanation: {len(has_ref)} / {len(rows)}')
print(f'Questions WITHOUT:                           {len(no_ref)} / {len(rows)}')
print()

# Show variety of ref formats from 20 examples
print('=== SAMPLE REF SNIPPETS (last 300 chars of explanation) ===')
for r in has_ref[:20]:
    tail = r['Explanation'][-300:].strip()
    print(f"  {r['Question ID']} | {r['PrimaryCategory']}")
    print(f"  ...{tail}")
    print()
