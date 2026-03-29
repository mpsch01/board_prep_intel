"""Parse REMAINING unmatched citations into structured fields for PubMed lookup."""
import sqlite3, re, json

DB = r"C:\Users\mpsch\Desktop\claude_knowledge\00_#PROJECT_OVERHAUL\00_database\db\ite_intelligence.db"
conn = sqlite3.connect(DB)
cur = conn.cursor()

cur.execute("""
    SELECT ac.citation_id, ac.aafp_qid, cr.raw_text
    FROM aafp_citations ac
    JOIN aafp_citation_raw cr ON ac.citation_id = cr.citation_id
    WHERE ac.match_status = 'unmatched'
    AND ac.unmatched_class = 'REMAINING'
    ORDER BY ac.citation_id
""")
rows = cur.fetchall()
conn.close()

VOL_RE   = re.compile(r'(\d{4});\s*(\d+)\s*\((\d+)\)\s*:\s*(\d+)')  # YYYY;VOL(ISS):PAGE
YEAR_RE  = re.compile(r'\b(19|20)\d{2}\b')
CD_RE    = re.compile(r'\bCD\d{6,7}\b', re.I)
URL_RE   = re.compile(r'https?://')

JOURNAL_MAP = {
    'Am Fam Physician': 'American Family Physician',
    'N Engl J Med': 'New England Journal of Medicine',
    'JAMA': 'JAMA',
    'Lancet': 'Lancet',
    'BMJ': 'BMJ',
    'Ann Intern Med': 'Annals of Internal Medicine',
    'Cochrane Database Syst Rev': 'Cochrane Database of Systematic Reviews',
    'Cochrane': 'Cochrane Database of Systematic Reviews',
    'Am J Gastroenterol': 'American Journal of Gastroenterology',
    'Am J Cardiol': 'American Journal of Cardiology',
    'Obstet Gynecol': 'Obstetrics and Gynecology',
    'Chest': 'Chest',
    'Circulation': 'Circulation',
    'Pediatrics': 'Pediatrics',
    'Crit Care Med': 'Critical Care Medicine',
    'J Clin Sleep Med': 'Journal of Clinical Sleep Medicine',
    'Medicine (Baltimore)': 'Medicine',
    'CMAJ': 'CMAJ',
    'Emerg Med Clin North Am': 'Emergency Medicine Clinics of North America',
    'Clin Infect Dis': 'Clinical Infectious Diseases',
    'Spine': 'Spine',
}

def extract_author(ref):
    first = re.split(r'[,;]', ref.strip())[0].strip()
    surname = first.split()[0] if first else ''
    # Skip org-name starts
    if re.match(r'^(US|American|National|Centers|Division|Authors|Statement|Final|ACC|AHA|AAN|AAP|ACOG|AAFP|Joint|Task|WHO|CDC|HPV|Screening|ACR)', surname, re.I):
        return ''
    return surname

def extract_journal(ref):
    for abbrev, full in JOURNAL_MAP.items():
        if abbrev in ref:
            return abbrev
    return ''

parsed = []
skipped_url = []
skipped_guideline = []
skipped_cochrane_nosearch = []

for cid, qid, raw in rows:
    ref = (raw or '').strip()

    if URL_RE.search(ref):
        skipped_url.append({'citation_id': cid, 'aafp_qid': qid, 'raw_text': ref, 'type': 'url'})
        continue

    m = VOL_RE.search(ref)
    if m:
        year_str, vol, issue, page = m.group(1), m.group(2), m.group(3), m.group(4)
        journal = extract_journal(ref)
        author  = extract_author(ref)
        parsed.append({
            'citation_id': cid,
            'aafp_qid': qid,
            'raw_text': ref,
            'type': 'journal_volpage',
            'author': author,
            'year': int(year_str),
            'journal': journal,
            'volume': vol,
            'first_page': page,
        })
        continue

    cd = CD_RE.search(ref)
    if cd:
        skipped_cochrane_nosearch.append({'citation_id': cid, 'aafp_qid': qid, 'raw_text': ref, 'type': 'cochrane_no_match'})
        continue

    # Guideline / society / other with no vol/page
    year_m = YEAR_RE.search(ref)
    year = int(year_m.group(0)) if year_m else None
    skipped_guideline.append({
        'citation_id': cid,
        'aafp_qid': qid,
        'raw_text': ref,
        'type': 'guideline_or_other',
        'year': year,
    })

print(f"REMAINING citations: {len(rows)}")
print(f"  With vol/page (PubMed lookup): {len(parsed)}")
print(f"  URL references (skip):         {len(skipped_url)}")
print(f"  Cochrane no CD match (search): {len(skipped_cochrane_nosearch)}")
print(f"  Guideline/other (search):      {len(skipped_guideline)}")

print(f"\n=== VOL/PAGE PARSEABLE (first 15) ===")
for r in parsed[:15]:
    print(f"  [{r['citation_id']}] author={r['author']} year={r['year']} journal={r['journal']} vol={r['volume']} pg={r['first_page']}")
    print(f"    {r['raw_text'][:90]}")

print(f"\n=== GUIDELINE/OTHER (first 10) ===")
for r in skipped_guideline[:10]:
    print(f"  [{r['citation_id']}] {r['raw_text'][:110]}")

print(f"\n=== COCHRANE NO CD MATCH ===")
for r in skipped_cochrane_nosearch:
    print(f"  [{r['citation_id']}] {r['raw_text'][:110]}")

# Save parsed to JSON for next step
out = {
    'vol_page': parsed,
    'guideline_other': skipped_guideline,
    'cochrane': skipped_cochrane_nosearch,
    'url': skipped_url,
}
with open(r'C:\Users\mpsch\Desktop\claude_knowledge\00_#PROJECT_OVERHAUL\remaining_parsed.json', 'w', encoding='utf-8') as f:
    json.dump(out, f, indent=2, ensure_ascii=False)
print(f"\nSaved -> remaining_parsed.json")
