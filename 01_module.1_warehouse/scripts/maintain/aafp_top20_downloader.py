#!/usr/bin/env python3
"""
AAFP Top 20 Articles PDF Downloader
====================================
Downloads all AFP Top 20 Articles (2017–2025) = 180 PDFs.
Names each file using the codon system:
  - DB match found  →  Author_Year#@#ART-XXXX@#@.pdf
  - No DB match     →  Author_Year.pdf

Requirements (run once):
  pip install requests beautifulsoup4 browser-cookie3

Usage:
  python aafp_top20_downloader.py
"""

import os
import re
import json
import time
import sqlite3
from pathlib import Path
from difflib import SequenceMatcher

import requests
from bs4 import BeautifulSoup
import browser_cookie3

# ─── CONFIG ───────────────────────────────────────────────────────────────────
SCRIPT_DIR      = Path(__file__).resolve().parent
PROJECT_ROOT    = SCRIPT_DIR.parent.parent.parent   # maintain/ → scripts/ → 01_module.1_warehouse/ → root
DB_PATH         = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"
DEST_FOLDER     = PROJECT_ROOT / "01_module.1_warehouse" / "VC_fail"
TOP_URL         = "https://www.aafp.org/pubs/afp/content/top-articles.html"
DELAY_SECONDS   = 1.5    # polite delay between requests
MATCH_THRESHOLD = 0.72   # title similarity score to accept a DB match

# ─── SETUP ────────────────────────────────────────────────────────────────────
os.makedirs(DEST_FOLDER, exist_ok=True)

print("Loading Chrome cookies for aafp.org...")
try:
    cookies = browser_cookie3.chrome(domain_name='.aafp.org')
except Exception as e:
    print(f"  WARNING: Could not load Chrome cookies: {e}")
    cookies = {}

session = requests.Session()
session.cookies.update(cookies)
session.headers.update({
    'User-Agent':      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept':          'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer':         'https://www.aafp.org/',
})

# ─── DB SETUP ─────────────────────────────────────────────────────────────────
print(f"Connecting to DB: {DB_PATH}")
conn   = sqlite3.connect(DB_PATH)
cur    = conn.cursor()

# Cache AFP articles from DB: {year -> [(article_id, title, author1, codon_filename)]}
db_cache = {}
cur.execute("""
    SELECT article_id, title, author1, year, codon_filename
    FROM articles
    WHERE source_type = 'AFP' AND year IS NOT NULL AND title IS NOT NULL
""")
for art_id, title, author1, year, codon in cur.fetchall():
    db_cache.setdefault(str(year), []).append((art_id, title or '', author1 or '', codon or ''))

total_afp_cached = sum(len(v) for v in db_cache.values())
print(f"  Cached {total_afp_cached} AFP articles from DB across {len(db_cache)} years")

# ─── HELPER: DB MATCH ─────────────────────────────────────────────────────────
def find_art_id(scraped_title, author_last, year):
    """
    Returns (art_id, art_codon) if a match is found, else (None, None).
    Strategy 1: fuzzy title match within same year
    Strategy 2: author last name + year (broader)
    """
    candidates = db_cache.get(str(year), [])
    title_clean = scraped_title.lower().strip()

    # Strategy 1: fuzzy title similarity
    best_score = 0
    best = (None, None)
    for art_id, db_title, db_author, codon in candidates:
        score = SequenceMatcher(None, title_clean, db_title.lower().strip()).ratio()
        if score > best_score:
            best_score = score
            best = (art_id, codon)

    if best_score >= MATCH_THRESHOLD:
        return best

    # Strategy 2: author last name match in any year (±1 year)
    for yr in [str(year), str(int(year)-1), str(int(year)+1)]:
        for art_id, db_title, db_author, codon in db_cache.get(yr, []):
            if db_author.lower().startswith(author_last.lower()):
                score = SequenceMatcher(None, title_clean, db_title.lower().strip()).ratio()
                if score >= 0.55:
                    return (art_id, codon)

    return (None, None)

# ─── HELPER: FILENAME BUILDER ─────────────────────────────────────────────────
def build_filename(author_last, year, art_id=None, used=set()):
    """Build codon filename with duplicate protection."""
    base = f"{author_last}_{year}"

    if art_id:
        return f"{base}#@#{art_id}@#@.pdf"

    # No DB match — base format with dedup suffix if needed
    candidate = f"{base}.pdf"
    if candidate not in used:
        used.add(candidate)
        return candidate
    for suffix in 'bcdefghijklmnop':
        candidate = f"{base}{suffix}.pdf"
        if candidate not in used:
            used.add(candidate)
            return candidate
    return f"{base}_x.pdf"

# ─── STEP 1: SCRAPE ARTICLE LIST ─────────────────────────────────────────────
print(f"\nFetching top articles page...")
resp = session.get(TOP_URL, timeout=30)
soup = BeautifulSoup(resp.text, 'html.parser')

article_urls = []
seen = set()
for a in soup.find_all('a', href=True):
    href = a['href']
    full = href if href.startswith('http') else 'https://www.aafp.org' + href

    # Match both URL formats
    new_fmt = re.match(r'https://www\.aafp\.org/pubs/afp/issues/\d{4}/\d{4}/.+\.html$', full)
    old_fmt = re.match(r'https://www\.aafp\.org/afp/\d{4}/\d{4}/.+\.html$', full)

    if (new_fmt or old_fmt) and full not in seen:
        article_urls.append(full)
        seen.add(full)

print(f"  Found {len(article_urls)} article URLs")

# Count by year
by_year = {}
for url in article_urls:
    m = re.search(r'/(20\d\d)/', url)
    if m:
        yr = m.group(1)
        by_year[yr] = by_year.get(yr, 0) + 1
for yr in sorted(by_year):
    print(f"    {yr}: {by_year[yr]} articles")

# ─── STEP 2: PROCESS EACH ARTICLE ────────────────────────────────────────────
print("\nStarting downloads...\n")

results      = {'downloaded': [], 'skipped': [], 'failed': [], 'no_db_match': []}
used_filenames = set(f for f in os.listdir(DEST_FOLDER) if f.endswith('.pdf'))

for i, article_url in enumerate(article_urls, 1):
    print(f"[{i:3d}/{len(article_urls)}] {article_url.split('aafp.org')[1]}")

    try:
        # --- Fetch article page ---
        time.sleep(DELAY_SECONDS)
        art_resp = session.get(article_url, timeout=30, allow_redirects=True)
        art_soup = BeautifulSoup(art_resp.text, 'html.parser')

        # --- Extract citation metadata ---
        def get_meta(name):
            tag = art_soup.find('meta', {'name': name})
            return tag['content'].strip() if tag and tag.get('content') else ''

        pdf_url = get_meta('citation_pdf_url')
        title   = get_meta('citation_title')
        author  = get_meta('citation_author')

        if not pdf_url:
            print(f"  ✗  No citation_pdf_url meta — skipping")
            results['failed'].append({'url': article_url, 'reason': 'no pdf meta'})
            continue

        # --- Parse author last name ---
        # citation_author format: "First Last, MD" or "First M. Last, MD"
        author_last = author.split(',')[0].strip().split()[-1] if author else 'Unknown'

        # --- Parse year from URL ---
        yr_match = re.search(r'/(20\d\d)/', art_resp.url)
        year     = yr_match.group(1) if yr_match else re.search(r'/(20\d\d)/', article_url).group(1)

        # --- DB match ---
        art_id, _ = find_art_id(title, author_last, year)

        # --- Build filename ---
        filename  = build_filename(author_last, year, art_id, used_filenames)
        dest_path = os.path.join(DEST_FOLDER, filename)

        # --- Dedup check ---
        if os.path.exists(dest_path):
            print(f"       SKIP (exists): {filename}")
            results['skipped'].append(filename)
            continue

        # --- Download PDF ---
        time.sleep(DELAY_SECONDS)
        pdf_resp = session.get(pdf_url, timeout=60, allow_redirects=True, headers={
            'Accept':  'application/pdf,application/octet-stream,*/*',
            'Referer': art_resp.url,
        })

        content_type = pdf_resp.headers.get('Content-Type', '').lower()
        if pdf_resp.status_code != 200 or 'html' in content_type:
            print(f"  ✗  PDF gate hit — status {pdf_resp.status_code}, type: {content_type[:40]}")
            results['failed'].append({'url': article_url, 'pdf_url': pdf_url, 'status': pdf_resp.status_code})
            continue

        # Write file
        with open(dest_path, 'wb') as f:
            f.write(pdf_resp.content)

        used_filenames.add(filename)
        size_kb = len(pdf_resp.content) // 1024
        match_note = f"[{art_id}]" if art_id else "[no DB match]"
        print(f"  ✓  {filename}  {size_kb}KB  {match_note}")
        results['downloaded'].append({'filename': filename, 'art_id': art_id, 'title': title})

        if not art_id:
            results['no_db_match'].append({'url': article_url, 'title': title, 'filename': filename})

    except Exception as e:
        print(f"  ✗  ERROR: {e}")
        results['failed'].append({'url': article_url, 'reason': str(e)})

# ─── CLEANUP ──────────────────────────────────────────────────────────────────
conn.close()

# ─── SUMMARY ──────────────────────────────────────────────────────────────────
print("\n" + "=" * 65)
print("DOWNLOAD COMPLETE")
print(f"  Downloaded:    {len(results['downloaded'])}")
print(f"  Skipped:       {len(results['skipped'])}  (already existed)")
print(f"  Failed:        {len(results['failed'])}")
print(f"  No DB match:   {len(results['no_db_match'])}  (base filename used)")

if results['no_db_match']:
    print("\nArticles without DB match (base filename only):")
    for a in results['no_db_match']:
        print(f"    {a['title'][:65]}")

if results['failed']:
    print("\nFailed:")
    for f in results['failed']:
        print(f"    {f}")

# Save run log
log_path = os.path.join(DEST_FOLDER, '_download_log.json')
with open(log_path, 'w') as f:
    json.dump(results, f, indent=2)
print(f"\nLog saved → {log_path}")