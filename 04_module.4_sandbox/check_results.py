import csv
from collections import Counter
from urllib.parse import urlparse

EXA = r'C:\Users\mpsch\Desktop\board_prep_intel\01_module.1_warehouse\scripts\maintain\exa_pdf_queue.csv'
RES = r'C:\Users\mpsch\Desktop\board_prep_intel\01_module.1_warehouse\scripts\maintain\unpaywall_results.csv'
DB  = r'C:\Users\mpsch\Desktop\board_prep_intel\00_database\db\ite_intelligence.db'

# Load no_doi article IDs
with open(RES, newline='', encoding='utf-8') as f:
    no_doi_ids = {r['article_id'] for r in csv.DictReader(f) if r['download_status'] == 'no_doi'}

# Join with exa_pdf_queue to get domains
domain_counts = Counter()
source_type_counts = Counter()
with open(EXA, newline='', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        if row['article_id'] in no_doi_ids:
            url = row.get('top_url', '')
            domain = urlparse(url).netloc.replace('www.', '')
            domain_counts[domain] += 1
            source_type_counts[row.get('source_type', 'unknown')] += 1

print(f"=== No-DOI articles: top domains ===")
for domain, count in domain_counts.most_common(20):
    print(f"  {count:4d}  {domain}")

print(f"\n=== No-DOI articles: source_type breakdown ===")
for st, count in source_type_counts.most_common():
    print(f"  {count:4d}  {st}")

# Check how many no_doi articles have full titles in DB vs truncated
import sqlite3
conn = sqlite3.connect(DB)
cur = conn.cursor()
cur.execute("SELECT citation_id, title FROM articles WHERE citation_id IN ({})".format(
    ','.join('?' * len(no_doi_ids))), list(no_doi_ids))
db_rows = {r[0]: r[1] for r in cur.fetchall()}
conn.close()

exa_titles = {}
with open(EXA, newline='', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        if row['article_id'] in no_doi_ids:
            exa_titles[row['article_id']] = row.get('title', '')

truncated = sum(1 for aid in no_doi_ids
                if aid in db_rows and aid in exa_titles
                and len(exa_titles[aid]) >= 78
                and db_rows.get(aid, '') != exa_titles.get(aid, ''))
print(f"\n=== Title truncation analysis ===")
print(f"No-doi articles found in DB: {len(db_rows)}")
print(f"Articles with truncated titles in CSV (>=78 chars): {truncated}")
