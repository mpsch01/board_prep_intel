#!/usr/bin/env python3
"""
AAFP Top 20 – Selenium Retry for Failed PDFs
==============================================
Targets the 33 articles that failed in the first run (Apr 2024 – all 2025).
These newer articles require JS-initialized session tokens that browser_cookie3
can't capture. Selenium opens Chrome with your actual profile to get fresh tokens.

BEFORE RUNNING:
  1. Kill Chrome background processes (run in cmd/PowerShell):
       taskkill /F /IM chrome.exe /T
  2. Install deps if needed:
       pip install selenium webdriver-manager requests beautifulsoup4 browser-cookie3

Usage:
  python aafp_retry_selenium.py
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
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import browser_cookie3

# ─── CONFIG ───────────────────────────────────────────────────────────────────
SCRIPT_DIR      = Path(__file__).resolve().parent
PROJECT_ROOT    = SCRIPT_DIR.parent.parent.parent   # maintain/ → scripts/ → 01_module.1_warehouse/ → root
DB_PATH         = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"
DEST_FOLDER     = PROJECT_ROOT / "01_module.1_warehouse" / "citation_files" / "ITE" / "VC_fail"
LOG_PATH        = DEST_FOLDER / "_download_log.json"
DELAY           = 2.0
MATCH_THRESHOLD = 0.72

# ─── LOAD FAILED LIST ─────────────────────────────────────────────────────────
with open(LOG_PATH) as f:
    log = json.load(f)

failed_entries = log.get('failed', [])
failed_urls    = [e['url'] for e in failed_entries if isinstance(e, dict) and 'url' in e]
print(f"Found {len(failed_urls)} articles to retry")

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
    db_cache.setdefault(str(year), []).append((art_id, title or '', author1 or '', codon or ''))

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

def build_filename(author_last, year, art_id=None, used=set()):
    base = f"{author_last}_{year}"
    if art_id:
        return f"{base}#@#{art_id}@#@.pdf"
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

# ─── SELENIUM SETUP ───────────────────────────────────────────────────────────
# Strategy: fresh Chrome (no profile lock risk) + inject browser_cookie3 cookies
# → navigate to AAFP → JS runs → extract fully-initialized session cookies
print("\nLaunching fresh Chrome instance...")
print("(Run 'taskkill /F /IM chrome.exe /T' first if this fails)\n")

options = Options()
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--no-first-run")
options.add_argument("--disable-notifications")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)
# NOT headless — JS auth needs a real render

try:
    service = Service(ChromeDriverManager().install())
    driver  = webdriver.Chrome(service=service, options=options)
except Exception as e:
    print(f"\n✗ Chrome launch failed: {e}")
    print("\nFix: run  taskkill /F /IM chrome.exe /T  then try again")
    exit(1)

# Step 1: Navigate to AAFP domain so we can set cookies for it
print("Setting up AAFP session...")
driver.get("https://www.aafp.org")
time.sleep(2)

# Step 2: Inject persisted cookies from your Chrome profile
print("Injecting cookies from your Chrome profile...")
try:
    bc3_cookies = browser_cookie3.chrome(domain_name='.aafp.org')
    injected = 0
    for c in bc3_cookies:
        try:
            driver.add_cookie({
                'name':   c.name,
                'value':  c.value,
                'domain': c.domain if c.domain else '.aafp.org',
                'path':   c.path or '/',
            })
            injected += 1
        except Exception:
            pass
    print(f"  Injected {injected} cookies")
except Exception as e:
    print(f"  Warning: browser_cookie3 failed ({e}) — proceeding anyway")

# Step 3: Navigate to AAFP with cookies active — JS will generate fresh tokens
driver.get("https://www.aafp.org/pubs/afp/content/top-articles.html")
time.sleep(4)

# Step 4: Extract all cookies (persisted + JS-generated) into requests session
selenium_cookies = driver.get_cookies()
session = requests.Session()
for c in selenium_cookies:
    session.cookies.set(c['name'], c['value'], domain=c.get('domain', '.aafp.org'))

session.headers.update({
    'User-Agent':      driver.execute_script("return navigator.userAgent"),
    'Accept':          'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer':         'https://www.aafp.org/',
})
print(f"  Session ready — {len(selenium_cookies)} total cookies captured\n")

# ─── PROCESS FAILED ARTICLES ──────────────────────────────────────────────────
used_filenames = set(f for f in os.listdir(DEST_FOLDER) if f.endswith('.pdf'))

results = {'downloaded': [], 'skipped': [], 'failed': []}

for i, article_url in enumerate(failed_urls, 1):
    print(f"[{i:2d}/{len(failed_urls)}] {article_url.split('aafp.org')[1]}")

    try:
        time.sleep(DELAY)

        # Fetch article page to get citation meta tags
        art_resp = session.get(article_url, timeout=30, allow_redirects=True)
        art_soup = BeautifulSoup(art_resp.text, 'html.parser')

        def get_meta(name):
            tag = art_soup.find('meta', {'name': name})
            return tag['content'].strip() if tag and tag.get('content') else ''

        pdf_url = get_meta('citation_pdf_url')
        title   = get_meta('citation_title')
        author  = get_meta('citation_author')

        if not pdf_url:
            # Refresh cookies from Selenium and retry once
            print("  → No PDF meta, refreshing session...")
            driver.get(article_url)
            time.sleep(3)
            for c in driver.get_cookies():
                session.cookies.set(c['name'], c['value'], domain=c.get('domain', '.aafp.org'))
            art_resp = session.get(article_url, timeout=30, allow_redirects=True)
            art_soup = BeautifulSoup(art_resp.text, 'html.parser')
            pdf_url  = get_meta('citation_pdf_url')

        if not pdf_url:
            print(f"  ✗  No citation_pdf_url found")
            results['failed'].append({'url': article_url, 'reason': 'no pdf meta after retry'})
            continue

        # Parse author / year
        author_last = author.split(',')[0].strip().split()[-1] if author else 'Unknown'
        yr_match    = re.search(r'/(20\d\d)/', art_resp.url)
        year        = yr_match.group(1) if yr_match else re.search(r'/(20\d\d)/', article_url).group(1)

        # DB match
        art_id, _ = find_art_id(title, author_last, year)

        # Filename
        filename  = build_filename(author_last, year, art_id, used_filenames)
        dest_path = os.path.join(DEST_FOLDER, filename)

        if os.path.exists(dest_path):
            print(f"       SKIP (exists): {filename}")
            results['skipped'].append(filename)
            continue

        # Download PDF — use Selenium to navigate so we get the real token refresh
        time.sleep(DELAY)
        pdf_resp = session.get(pdf_url, timeout=60, allow_redirects=True, headers={
            'Accept':  'application/pdf,application/octet-stream,*/*',
            'Referer': art_resp.url,
        })

        content_type = pdf_resp.headers.get('Content-Type', '').lower()

        if 'html' in content_type:
            # Cookies may have expired mid-run — pull fresh ones from Selenium
            print(f"  → HTML response, refreshing cookies via browser...")
            driver.get(article_url)
            time.sleep(4)
            for c in driver.get_cookies():
                session.cookies.set(c['name'], c['value'], domain=c.get('domain', '.aafp.org'))

            pdf_resp = session.get(pdf_url, timeout=60, allow_redirects=True, headers={
                'Accept':  'application/pdf,application/octet-stream,*/*',
                'Referer': article_url,
            })
            content_type = pdf_resp.headers.get('Content-Type', '').lower()

        if 'html' in content_type or pdf_resp.status_code != 200:
            print(f"  ✗  Still gated: {pdf_resp.status_code} | {content_type[:50]}")
            results['failed'].append({'url': article_url, 'pdf_url': pdf_url, 'status': pdf_resp.status_code})
            continue

        with open(dest_path, 'wb') as f:
            f.write(pdf_resp.content)

        used_filenames.add(filename)
        size_kb    = len(pdf_resp.content) // 1024
        match_note = f"[{art_id}]" if art_id else "[no DB match]"
        print(f"  ✓  {filename}  {size_kb}KB  {match_note}")
        results['downloaded'].append({'filename': filename, 'art_id': art_id, 'title': title})

    except Exception as e:
        print(f"  ✗  ERROR: {e}")
        results['failed'].append({'url': article_url, 'reason': str(e)})

# ─── CLEANUP ──────────────────────────────────────────────────────────────────
driver.quit()
conn.close()

# ─── UPDATE LOG ───────────────────────────────────────────────────────────────
log['downloaded'].extend(results['downloaded'])
log['skipped'].extend(results['skipped'])
log['failed'] = results['failed']   # replace with only still-failing

with open(LOG_PATH, 'w') as f:
    json.dump(log, f, indent=2)

# ─── SUMMARY ──────────────────────────────────────────────────────────────────
print("\n" + "=" * 65)
print("RETRY COMPLETE")
print(f"  Downloaded:  {len(results['downloaded'])}")
print(f"  Skipped:     {len(results['skipped'])}")
print(f"  Still failed: {len(results['failed'])}")

if results['failed']:
    print("\nStill failing (may need manual download):")
    for f in results['failed']:
        print(f"    {f}")

print(f"\nLog updated → {LOG_PATH}")
