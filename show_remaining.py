import json, re

YEAR_RE = re.compile(r'\b(19|20)\d{2}\b')
VOL_SPACE_RE = re.compile(r'(\d{4});\s*(\d+)\s*[\(\[]?(\d*)\]?\)?\s*:\s*([A-Z0-9-]+)')

d = json.load(open('remaining_parsed.json', encoding='utf-8'))

print("=== COCHRANE (9) ===")
for r in d['cochrane']:
    y = YEAR_RE.search(r['raw_text'])
    m = VOL_SPACE_RE.search(r['raw_text'])
    year = y.group(0) if y else '?'
    vol = m.group(2) if m else '?'
    page = m.group(4) if m else '?'
    author = r['raw_text'].split(',')[0].strip()
    print(f"  [{r['citation_id']}] {author} | {year} | vol={vol} pg={page}")
    print(f"    {r['raw_text'][:120]}")

print("\n=== GUIDELINE/OTHER — named authors with parseable data ===")
skippable = re.compile(r'^(US |American|National|Centers|Division|Authors|Statement|Final|ACC|AHA|AAN|AAP|ACOG|AAFP|Joint|Task|WHO|CDC|HPV|Screening|ACR|Cardiovasc|Committee)', re.I)
parseable = []
for r in d['guideline_other']:
    ref = r['raw_text'].strip()
    first_token = ref.split(',')[0].strip()
    if skippable.match(first_token) or len(ref) < 25:
        continue
    y = YEAR_RE.search(ref)
    year = y.group(0) if y else None
    # Try to get vol/page including non-numeric pages (ITC, S, suppl)
    m = VOL_SPACE_RE.search(ref)
    author = first_token.split()[0]
    parseable.append({
        'citation_id': r['citation_id'],
        'aafp_qid': r['aafp_qid'],
        'raw_text': ref,
        'author': author,
        'year': int(year) if year else None,
        'volume': m.group(2) if m else None,
        'first_page': m.group(4) if m else None,
    })

print(f"Named-author guideline/other with data: {len(parseable)}")
for r in parseable[:20]:
    print(f"  [{r['citation_id']}] {r['author']} | {r['year']} | vol={r['volume']} pg={r['first_page']}")
    print(f"    {r['raw_text'][:110]}")

# Save enriched parseable list
out2 = {'parseable_named': parseable, 'cochrane': d['cochrane']}
json.dump(out2, open('remaining_named.json','w',encoding='utf-8'), indent=2, ensure_ascii=False)
print(f"\nTotal named-author parseable: {len(parseable)}")
