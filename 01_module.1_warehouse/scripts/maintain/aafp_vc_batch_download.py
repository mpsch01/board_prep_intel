#!/usr/bin/env python3
"""
AAFP VC Batch Download — FLAG 32 Sourcing (76 articles)
========================================================
Downloads the 76 AAFP articles from the FLAG 32 missing-PDF list
using pre-resolved PubMed URLs in aafp_download_manifest.json.

Workflow:
  1. Reads the manifest (already has article URLs from PubMed resolution)
  2. Opens browser → you log in to AAFP manually
  3. For each article: navigates to article page → extracts PDF URL → downloads
  4. Names files as Author_Year#@#ART-XXXX@#@.pdf (codon convention)
  5. Saves to pdf_codon/ and copies to 04_need_extraction/
  6. Updates _download_log.json

Prerequisites:
  pip install playwright
  python -m playwright install chromium

Usage:
  python aafp_vc_batch_download.py
  python aafp_vc_batch_download.py --dry-run      # shows what would download
  python aafp_vc_batch_download.py --start-at 20   # resume from item 20

Author: Claude + Mikey, March 2026
"""

import os
import re
import json
import time
import shutil
import subprocess
import tempfile
import argparse
from pathlib import Path

# ─── CONFIG ───────────────────────────────────────────────────────────────────
SCRIPT_DIR    = Path(__file__).resolve().parent
PROJECT_ROOT  = SCRIPT_DIR.parent.parent.parent   # maintain/ → scripts/ → 01_module.1_warehouse/ → root
WAREHOUSE     = PROJECT_ROOT / "01_module.1_warehouse"
CITATION_ITE  = WAREHOUSE / "citation_files" / "ITE"
CODON_DIR     = CITATION_ITE / "VC_pass"
EXTRACT_DIR   = CITATION_ITE / "VC_fail"
MANIFEST_PATH = SCRIPT_DIR / "aafp_download_manifest.json"
LOG_PATH      = SCRIPT_DIR / "_download_log.json"
DELAY         = 2.0   # seconds between downloads (be polite to AAFP servers)

# ─── PARSE ARGS ───────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="AAFP VC Batch Download (FLAG 32)")
parser.add_argument("--dry-run", action="store_true", help="Show what would download without downloading")
parser.add_argument("--start-at", type=int, default=1, help="Resume from item N (1-based)")
args = parser.parse_args()

# ─── LOAD MANIFEST ────────────────────────────────────────────────────────────
with open(MANIFEST_PATH, encoding="utf-8") as f:
    manifest = json.load(f)

# Filter to only resolved articles with URLs
downloadable = [m for m in manifest if m.get("resolution_status") == "resolved" and m.get("aafp_article_url")]

print(f"Manifest loaded: {len(manifest)} total, {len(downloadable)} downloadable")

# ─── CHECK EXISTING ───────────────────────────────────────────────────────────
existing = set()
for d in [CODON_DIR, EXTRACT_DIR]:
    if d.is_dir():
        existing.update(f.name for f in d.iterdir() if f.suffix.lower() == ".pdf")

# Also check by ART-ID in existing filenames (in case filename format differs slightly)
existing_art_ids = set()
codon_re = re.compile(r"#@#(ART-\d+)@#@")
for fname in existing:
    m = codon_re.search(fname)
    if m:
        existing_art_ids.add(m.group(1))

print(f"Existing PDFs in library: {len(existing)}")
print(f"Existing ART-IDs: {len(existing_art_ids)}")

# Filter out already-downloaded
to_download = []
skipped = []
for item in downloadable:
    art_id = item["article_id"]
    codon_fn = item.get("codon_filename", "")
    if art_id in existing_art_ids or codon_fn in existing:
        skipped.append(item)
    else:
        to_download.append(item)

print(f"Already have: {len(skipped)}")
print(f"Need to download: {len(to_download)}")

if args.dry_run:
    print("\n=== DRY RUN — Would download: ===")
    for i, item in enumerate(to_download, 1):
        print(f"  [{i:2d}] {item['codon_filename']}")
        print(f"       URL: {item['aafp_article_url']}")
    print(f"\nTotal: {len(to_download)} articles")
    exit(0)

if not to_download:
    print("\nNothing to download — all articles already in library!")
    exit(0)

# Apply --start-at
if args.start_at > 1:
    to_download = to_download[args.start_at - 1:]
    print(f"Resuming from item {args.start_at}, {len(to_download)} remaining")

# ─── PLAYWRIGHT DOWNLOAD ─────────────────────────────────────────────────────
from playwright.sync_api import sync_playwright

results = {"downloaded": [], "skipped": [], "failed": []}
tmp_dl_dir = tempfile.mkdtemp(prefix="aafp_vc_")

print(f"\nStarting Playwright for {len(to_download)} downloads...\n")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(
        accept_downloads=True,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
    page = context.new_page()

    # ── Manual login ──────────────────────────────────────────────────────
    print("Opening AAFP login page...")
    page.goto("https://www.aafp.org/home/login.html", wait_until="domcontentloaded", timeout=30000)
    print("\n" + "=" * 65)
    print("  LOG IN to AAFP in the browser window that just opened.")
    print("  Once fully logged in, come back and press ENTER.")
    print("=" * 65)
    input("\n  Press ENTER when logged in >>> ")
    time.sleep(2)
    print(f"\nSession active — starting {len(to_download)} downloads...\n")

    # ── Download loop ─────────────────────────────────────────────────────
    for i, item in enumerate(to_download, 1):
        art_id     = item["article_id"]
        article_url = item["aafp_article_url"]
        codon_fn   = item["codon_filename"]
        dest_path  = CODON_DIR / codon_fn

        print(f"[{i:2d}/{len(to_download)}] {codon_fn}")
        print(f"       → {article_url}")

        try:
            time.sleep(DELAY)

            # Navigate to article page
            page.goto(article_url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(1)

            # Extract PDF URL from meta tag
            pdf_url = page.evaluate(
                'document.querySelector(\'meta[name="citation_pdf_url"]\')?.content || ""'
            )

            if not pdf_url:
                # Fallback: try to find a PDF link on the page
                pdf_url = page.evaluate("""
                    (() => {
                        const a = document.querySelector('a[href*=".pdf"]');
                        return a ? a.href : '';
                    })()
                """)

            if not pdf_url:
                # Fallback 3: construct PDF URL from article URL (.html → .pdf)
                if article_url.endswith(".html"):
                    pdf_url = article_url.replace(".html", ".pdf")
                    print(f"       ⚡ No meta tag — trying constructed URL: ...{pdf_url[-40:]}")

            if not pdf_url:
                print(f"       ✗  No PDF URL found on page")
                results["failed"].append({
                    "article_id": art_id, "url": article_url,
                    "filename": codon_fn, "reason": "no pdf url on page"
                })
                continue

            # Download PDF via new tab
            page2 = context.new_page()
            try:
                with page2.expect_download(timeout=60000) as dl_info:
                    page2.goto(pdf_url, wait_until="commit", timeout=60000)

                download = dl_info.value
                tmp_path = os.path.join(tmp_dl_dir, download.suggested_filename or "file.bin")
                download.save_as(tmp_path)
            finally:
                page2.close()

            # Verify it's a PDF
            with open(tmp_path, "rb") as f:
                header = f.read(4)

            if header != b"%PDF":
                print(f"       ✗  Not a PDF (header: {header[:20]})")
                os.remove(tmp_path)
                results["failed"].append({
                    "article_id": art_id, "url": article_url,
                    "filename": codon_fn, "reason": "not a PDF"
                })
                continue

            # Move to codon directory
            shutil.move(tmp_path, str(dest_path))
            existing.add(codon_fn)
            existing_art_ids.add(art_id)

            # Copy to extraction queue
            if EXTRACT_DIR.is_dir():
                shutil.copy2(str(dest_path), str(EXTRACT_DIR / codon_fn))

            size_kb = dest_path.stat().st_size // 1024
            print(f"       ✓  {size_kb}KB  [{art_id}]")
            results["downloaded"].append({
                "filename": codon_fn, "art_id": art_id,
                "title": item.get("title", ""), "pmid": item.get("pmid", "")
            })

        except Exception as e:
            print(f"       ✗  ERROR: {e}")
            results["failed"].append({
                "article_id": art_id, "url": article_url,
                "filename": codon_fn, "reason": str(e)
            })

    browser.close()

# Cleanup temp dir — shutil.rmtree banned (NTFS); use PowerShell Remove-Item
subprocess.run(
    ["powershell", "-Command",
     f"Remove-Item -Recurse -Force '{tmp_dl_dir}' -ErrorAction SilentlyContinue"],
    capture_output=True
)

# ─── UPDATE LOG ───────────────────────────────────────────────────────────────
try:
    with open(LOG_PATH, encoding="utf-8") as f:
        log = json.load(f)
except Exception:
    log = {"downloaded": [], "skipped": [], "failed": []}

# Ensure log has proper structure
if isinstance(log, list):
    log = {"downloaded": log, "skipped": [], "failed": []}

log["downloaded"].extend(results["downloaded"])
log.setdefault("skipped", []).extend(results.get("skipped", []))
log["failed"] = results["failed"]  # overwrite failed with current run's failures

with open(LOG_PATH, "w", encoding="utf-8") as f:
    json.dump(log, f, indent=2)

# ─── SUMMARY ─────────────────────────────────────────────────────────────────
print("\n" + "=" * 65)
print("AAFP VC BATCH DOWNLOAD — COMPLETE")
print(f"  Downloaded:   {len(results['downloaded'])}")
print(f"  Skipped:      {len(skipped)} (already in library)")
print(f"  Failed:       {len(results['failed'])}")
print("=" * 65)

if results["failed"]:
    print("\nFailed articles (may need manual download):")
    for f in results["failed"]:
        print(f"  {f['article_id']}: {f['reason']}")
        print(f"    URL: {f['url']}")

if results["downloaded"]:
    print(f"\nNext step: re-run build_crosswalk_index.py to update the crosswalk")
    print(f"  cd C:\\Users\\mpsch\\Desktop\\claude_knowledge\\abfm_prep\\02_ite_intelligence\\scripts")
    print(f"  python build_crosswalk_index.py")

print(f"\nLog updated → {LOG_PATH}")
