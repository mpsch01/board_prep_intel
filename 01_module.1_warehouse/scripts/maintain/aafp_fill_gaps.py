#!/usr/bin/env python3
"""
AAFP Top 20 – Gap Filler
========================
Scrapes the top articles page fresh, checks both VC_pass and VC_fail
for existing files, and downloads only what's missing using Playwright.

Run this any time files are missing or after a fresh year is added to the page.

Usage:
  C:\\Users\\mpsch\\AppData\\Local\\Programs\\Python\\Python312\\python.exe aafp_fill_gaps.py
"""

import os
import re
import json
import time
import sqlite3
import shutil
import tempfile
from pathlib import Path
from difflib import SequenceMatcher

import requests
from bs4 import BeautifulSoup
import browser_cookie3
from playwright.sync_api import sync_playwright

# ─── CONFIG ───────────────────────────────────────────────────────────────────
SCRIPT_DIR    = Path(__file__).resolve().parent
PROJECT_ROOT  = SCRIPT_DIR.parent.parent.parent   # maintain/ → scripts/ → 01_module.1_warehouse/ → root
WAREHOUSE     = PROJECT_ROOT / "01_module.1_warehouse"
CITATION_ITE  = WAREHOUSE / "citation_files" / "ITE"
CODON_DIR     = str(CITATION_ITE / "VC_pass")
NONCODON_DIR  = str(CITATION_ITE / "VC_fail")
EXTRACT_DIR   = str(CITATION_ITE / "VC_fail")        # unified with VC_fail in new structure
LOG_PATH      = str(SCRIPT_DIR / "_download_log.json")
DB_PATH       = str(PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db")
TOP_URL       = "https://www.aafp.org/pubs/afp/content/top-articles.html"
DELAY         = 1.5
MATCH_THRESHOLD = 0.72

# ─── COLLECT ALL EXISTING FILENAMES ───────────────────────────────────────────
existing = set()
for d in [CODON_DIR, NONCODON_DIR, EXTRACT_DIR]:
    if os.path.isdir(d):
        existing.update(f for f in os.listdir(d) if f.endswith('.pdf'))

print(f"Existing PDFs in library: {len(existing)}")

# ─── SCRAPE TOP ARTICLES PAGE ─────────────────────────────────────────────────
print("Scraping top articles page...")
resp = requests.get(TOP_URL, timeout=30)
soup = BeautifulSoup(resp.text, 'html.parser')

NEW_FMT = re.compile(r'https://www\.aafp\.org/pubs/afp/issues/\d{4}/\d{4}/.+\.html')
OLD_FMT = re.compile(r'https://www\.aafp\.org/afp/\d{4}/\d{4}/.+\.html')

all_urls = []
for a in soup.find_all('a', href=True):
    href = a['href']
    if not href.startswith('http'):
        href = 'https://www.aafp.org' + href
    if NEW_FMT.match(href) or OLD_FMT.match(href):
        if href not in all_urls:
            all_urls.append(href)

print(f"Found {len(all_urls)} article URLs on page")

# ─── DB SETUP ─────────────────────────────────────────────────────────────────
conn = sqlite3.connect(DB_PATH)
cur  = conn.cursor()
db_cache = {}
cur.execute("""
    SELECT article_id, title, author1, year, codon_filename
    FROM articles
    WHERE source_type = 'AFP' AND year IS NOT NULL AND title IS NOT NULL
""")
for art_id, title, author1, year, codon in cur.fetchall():
    db_cache.setdefault(str(year), []).append(
        (art_id, title or '', author1 or '', codon or '')
    )
conn.close()

def find_art_id(scraped_title, author_last, year):
    candidates  = db_cache.get(str(year), [])
    title_clean = scraped_title.lower().strip()
    best_score, best = 0, (None, None)
    for art_id, db_title, db_author, codon in candidates:
        score = SequenceMatcher(None, title_clean, db_title.lower().strip()).ratio()
        if score > best_score:
            best_score = score
            best = (art_id, codon)
    if best_score >= MATCH_THRESHOLD:
        return best
    for yr in [str(year), str(int(year)-1), str(int(year)+1)]:
        for art_id, db_title, db_author, codon in db_cache.get(yr, []):
            if db_author.lower().startswith(author_last.lower()):
                score = SequenceMatcher(None, title_clean, db_title.lower().strip()).ratio()
                if score >= 0.55:
                    return (art_id, codon)
    return (None, None)

def build_filename(author_last, year, art_id=None):
    base = f"{author_last}_{year}"
    if art_id:
        return f"{base}#@#{art_id}@#@.pdf"
    candidate = f"{base}.pdf"
    if candidate not in existing:
        return candidate
    for suffix in 'bcdefghijklmnop':
        candidate = f"{base}{suffix}.pdf"
        if candidate not in existing:
            return candidate
    return f"{base}_x.pdf"

# ─── PLAYWRIGHT DOWNLOAD ──────────────────────────────────────────────────────
results = {'downloaded': [], 'skipped': [], 'failed': []}
tmp_dl_dir = tempfile.mkdtemp(prefix="aafp_gap_")

# Pre-scan: figure out which URLs we actually need to download
# (we'll confirm during scraping, but filter obvious existing ones by year)
print(f"\nWill check {len(all_urls)} articles against {len(existing)} existing files\n")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(
        accept_downloads=True,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
    page = context.new_page()

    # Manual login
    print("Opening AAFP login page...")
    page.goto("https://www.aafp.org/home/login.html", wait_until="domcontentloaded", timeout=30000)
    print("\n" + "="*65)
    print("  LOG IN to AAFP in the browser window that just opened.")
    print("  Once fully logged in, come back and press ENTER.")
    print("="*65)
    input("\n  Press ENTER when logged in >>> ")
    time.sleep(2)

    to_download = []
    skipped_existing = 0

    for i, article_url in enumerate(all_urls, 1):
        time.sleep(0.3)
        try:
            page.goto(article_url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(0.5)

            pdf_url = page.evaluate(
                "document.querySelector('meta[name=\"citation_pdf_url\"]')?.content || ''"
            )
            title = page.evaluate(
                "document.querySelector('meta[name=\"citation_title\"]')?.content || ''"
            )
            author = page.evaluate(
                "document.querySelector('meta[name=\"citation_author\"]')?.content || ''"
            )

            author_last = author.split(',')[0].strip().split()[-1].title() if author else 'Unknown'
            yr_match    = re.search(r'/(20\d\d)/', article_url)
            year        = yr_match.group(1) if yr_match else '0000'
            art_id, _   = find_art_id(title, author_last, year)
            filename    = build_filename(author_last, year, art_id)

            if filename in existing:
                skipped_existing += 1
                print(f"[{i:3d}/{len(all_urls)}] SKIP  {filename}")
                results['skipped'].append(filename)
                continue

            to_download.append({
                'url': article_url, 'pdf_url': pdf_url,
                'filename': filename, 'art_id': art_id, 'title': title
            })
            print(f"[{i:3d}/{len(all_urls)}] NEED  {filename}")

        except Exception as e:
            print(f"[{i:3d}/{len(all_urls)}] ERR   {article_url.split('aafp.org')[1]} — {e}")

    print(f"\nSkipped (already exist): {skipped_existing}")
    print(f"To download: {len(to_download)}\n")

    for j, item in enumerate(to_download, 1):
        print(f"[{j:2d}/{len(to_download)}] {item['filename']}")
        try:
            time.sleep(DELAY)
            if not item['pdf_url']:
                print(f"       ✗  No PDF URL")
                results['failed'].append({'url': item['url'], 'reason': 'no pdf url'})
                continue

            dest_dir  = CODON_DIR if '#@#' in item['filename'] else NONCODON_DIR
            dest_path = os.path.join(dest_dir, item['filename'])

            page2 = context.new_page()
            with page2.expect_download(timeout=60000) as dl_info:
                page2.goto(item['pdf_url'], wait_until="commit", timeout=60000)

            download = dl_info.value
            tmp_path = os.path.join(tmp_dl_dir, download.suggested_filename or 'file.bin')
            download.save_as(tmp_path)
            page2.close()

            with open(tmp_path, 'rb') as f:
                header = f.read(4)

            if header != b'%PDF':
                print(f"       ✗  Not a PDF")
                os.remove(tmp_path)
                results['failed'].append({'url': item['url'], 'reason': 'not a PDF'})
                continue

            shutil.move(tmp_path, dest_path)
            existing.add(item['filename'])

            # Also copy to 04_need_extraction
            shutil.copy2(dest_path, os.path.join(EXTRACT_DIR, item['filename']))

            size_kb    = os.path.getsize(dest_path) // 1024
            match_note = f"[{item['art_id']}]" if item['art_id'] else "[no DB match]"
            print(f"       ✓  {size_kb}KB  {match_note}")
            results['downloaded'].append({
                'filename': item['filename'], 'art_id': item['art_id'], 'title': item['title']
            })

        except Exception as e:
            print(f"       ✗  ERROR: {e}")
            results['failed'].append({'url': item['url'], 'reason': str(e)})
            try: page2.close()
            except: pass

    browser.close()

shutil.rmtree(tmp_dl_dir, ignore_errors=True)

# ─── UPDATE LOG ───────────────────────────────────────────────────────────────
try:
    with open(LOG_PATH) as f:
        log = json.load(f)
except Exception:
    log = {'downloaded': [], 'skipped': [], 'failed': []}

log['downloaded'].extend(results['downloaded'])
log.setdefault('skipped', []).extend(results['skipped'])
log['failed'] = results['failed']

with open(LOG_PATH, 'w') as f:
    json.dump(log, f, indent=2)

# ─── SUMMARY ──────────────────────────────────────────────────────────────────
print("\n" + "="*65)
print("COMPLETE")
print(f"  Downloaded + staged: {len(results['downloaded'])}")
print(f"  Skipped (exist):     {len(results['skipped'])}")
print(f"  Failed:              {len(results['failed'])}")
if results['failed']:
    for f in results['failed']:
        print(f"    {f}")
