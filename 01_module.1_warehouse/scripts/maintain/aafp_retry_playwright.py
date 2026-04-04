#!/usr/bin/env python3
"""
AAFP Top 20 – Playwright Retry (Browser-Native Download)
=========================================================
Uses Playwright as a real browser to download auth-gated PDFs.
You log in manually in the browser window — no cookie injection needed.

BEFORE RUNNING (one-time install):
  C:\\Users\\mpsch\\AppData\\Local\\Programs\\Python\\Python312\\python.exe -m pip install playwright
  C:\\Users\\mpsch\\AppData\\Local\\Programs\\Python\\Python312\\python.exe -m playwright install chromium

Usage:
  C:\\Users\\mpsch\\AppData\\Local\\Programs\\Python\\Python312\\python.exe aafp_retry_playwright.py

  A browser window will open → log in → press ENTER in the terminal → downloads run.
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

from playwright.sync_api import sync_playwright

# ─── CONFIG ───────────────────────────────────────────────────────────────────
SCRIPT_DIR      = Path(__file__).resolve().parent
PROJECT_ROOT    = SCRIPT_DIR.parent.parent.parent   # maintain/ → scripts/ → 01_module.1_warehouse/ → root
DB_PATH         = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"
DEST_FOLDER     = PROJECT_ROOT / "01_module.1_warehouse" / "citation_files" / "ITE" / "VC_fail"
LOG_PATH        = DEST_FOLDER / "_download_log.json"
DELAY           = 1.5
MATCH_THRESHOLD = 0.72

# ─── LOAD FAILED LIST ─────────────────────────────────────────────────────────
with open(LOG_PATH) as f:
    log = json.load(f)

failed_entries = log.get('failed', [])
failed_urls    = [e['url'] for e in failed_entries if isinstance(e, dict) and 'url' in e]
print(f"Found {len(failed_urls)} articles to retry")

if not failed_urls:
    print("Nothing to retry — exiting.")
    exit(0)

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
    # Author fallback across adjacent years
    for yr in [str(year), str(int(year)-1), str(int(year)+1)]:
        for art_id, db_title, db_author, codon in db_cache.get(yr, []):
            if db_author.lower().startswith(author_last.lower()):
                score = SequenceMatcher(None, title_clean, db_title.lower().strip()).ratio()
                if score >= 0.55:
                    return (art_id, codon)
    return (None, None)

used_filenames = set(f for f in os.listdir(DEST_FOLDER) if f.endswith('.pdf'))

def build_filename(author_last, year, art_id=None):
    base = f"{author_last}_{year}"
    if art_id:
        return f"{base}#@#{art_id}@#@.pdf"
    candidate = f"{base}.pdf"
    if candidate not in used_filenames:
        return candidate
    for suffix in 'bcdefghijklmnop':
        candidate = f"{base}{suffix}.pdf"
        if candidate not in used_filenames:
            return candidate
    return f"{base}_x.pdf"

# ─── PLAYWRIGHT ───────────────────────────────────────────────────────────────
results = {'downloaded': [], 'skipped': [], 'failed': []}

# Use a temp dir for downloads — we rename files ourselves
tmp_dl_dir = tempfile.mkdtemp(prefix="aafp_dl_")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(
        accept_downloads=True,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
    page = context.new_page()

    # ── Manual login ──────────────────────────────────────────────────────────
    print("\nOpening AAFP login page...")
    page.goto("https://www.aafp.org/home/login.html", wait_until="domcontentloaded", timeout=30000)
    print("\n" + "="*65)
    print("  LOG IN to AAFP in the browser window that just opened.")
    print("  Once you are fully logged in and can see member content,")
    print("  come back here and press ENTER to start the downloads.")
    print("="*65)
    input("\n  Press ENTER when logged in >>> ")

    # Give any post-login redirects time to settle before proceeding
    time.sleep(2)
    print(f"\nSession active — starting {len(failed_urls)} downloads...\n")

    # ── Download loop ─────────────────────────────────────────────────────────
    for i, article_url in enumerate(failed_urls, 1):
        slug = article_url.split('aafp.org')[1]
        print(f"[{i:2d}/{len(failed_urls)}] {slug}")

        try:
            time.sleep(DELAY)

            # Navigate to article page and scrape metadata
            page.goto(article_url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(1)

            pdf_url = page.evaluate(
                "document.querySelector('meta[name=\"citation_pdf_url\"]')?.content || ''"
            )
            title = page.evaluate(
                "document.querySelector('meta[name=\"citation_title\"]')?.content || ''"
            )
            author = page.evaluate(
                "document.querySelector('meta[name=\"citation_author\"]')?.content || ''"
            )

            if not pdf_url:
                print(f"       ✗  No PDF URL found on page")
                results['failed'].append({'url': article_url, 'reason': 'no pdf meta'})
                continue

            # Parse author / year
            author_last = author.split(',')[0].strip().split()[-1] if author else 'Unknown'
            author_last = author_last.title()
            yr_match    = re.search(r'/(20\d\d)/', article_url)
            year        = yr_match.group(1) if yr_match else '0000'

            # DB match
            art_id, _ = find_art_id(title, author_last, year)

            # Filename
            filename  = build_filename(author_last, year, art_id)
            dest_path = os.path.join(DEST_FOLDER, filename)

            if os.path.exists(dest_path):
                print(f"       SKIP (exists): {filename}")
                results['skipped'].append(filename)
                continue

            # Navigate to PDF URL — Playwright downloads it natively
            time.sleep(DELAY)
            # Open PDF URL in a new tab to avoid navigating away from article context
            page2 = context.new_page()
            with page2.expect_download(timeout=60000) as dl_info:
                page2.goto(pdf_url, wait_until="commit", timeout=60000)

            download = dl_info.value

            # Check if it actually got a PDF (not an HTML redirect)
            tmp_path = os.path.join(tmp_dl_dir, download.suggested_filename or 'file.bin')
            download.save_as(tmp_path)
            page2.close()

            # Verify it's a PDF by checking magic bytes
            with open(tmp_path, 'rb') as f:
                header = f.read(4)

            if header != b'%PDF':
                print(f"       ✗  Download was not a PDF (got {header[:20]})")
                os.remove(tmp_path)
                results['failed'].append({'url': article_url, 'pdf_url': pdf_url,
                                          'reason': 'not a PDF'})
                continue

            shutil.move(tmp_path, dest_path)
            used_filenames.add(filename)

            size_kb    = os.path.getsize(dest_path) // 1024
            match_note = f"[{art_id}]" if art_id else "[no DB match]"
            print(f"       ✓  {filename}  {size_kb}KB  {match_note}")
            results['downloaded'].append({'filename': filename, 'art_id': art_id, 'title': title})

        except Exception as e:
            print(f"       ✗  ERROR: {e}")
            results['failed'].append({'url': article_url, 'reason': str(e)})
            try:
                page2.close()
            except Exception:
                pass

    browser.close()

# Cleanup temp dir
try:
    shutil.rmtree(tmp_dl_dir, ignore_errors=True)
except Exception:
    pass

# ─── UPDATE LOG ───────────────────────────────────────────────────────────────
log['downloaded'].extend(results['downloaded'])
log.setdefault('skipped', []).extend(results['skipped'])
log['failed'] = results['failed']

with open(LOG_PATH, 'w') as f:
    json.dump(log, f, indent=2)

# ─── SUMMARY ──────────────────────────────────────────────────────────────────
print("\n" + "="*65)
print("RETRY COMPLETE")
print(f"  Downloaded:   {len(results['downloaded'])}")
print(f"  Skipped:      {len(results['skipped'])}")
print(f"  Still failed: {len(results['failed'])}")

if results['failed']:
    print("\nStill failing (may need manual download):")
    for f in results['failed']:
        print(f"    {f}")

print(f"\nLog updated → {LOG_PATH}")
