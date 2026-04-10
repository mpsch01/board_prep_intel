#!/usr/bin/env python3
"""
download_pmc_actor_batch.py
────────────────────────────
Downloads the 9 PMC articles whose PDF URLs were discovered by the
citation_crawler Apify actor (run PW1zeM9Sr6VmgHVYV, 2026-04-03).

These articles are in PMC but outside the strict OA FTP subset, so the
standard OA API and E-Fetch endpoints return nothing.  The Playwright actor
found the direct PDF URLs by rendering the PMC viewer page.

Run:
    python download_pmc_actor_batch.py

Output: PDFs saved to 01_module.1_warehouse/citation_files/ITE/VC_fail/ with codon filenames.
"""

import os
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: 'requests' not installed. Run: pip install requests")
    sys.exit(1)

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
OUTPUT_DIR   = PROJECT_ROOT / "01_module.1_warehouse" / "citation_files" / "ITE" / "VC_fail"

CONTACT_EMAIL = os.environ.get("ITE_CONTACT_EMAIL", "")
HEADERS = {
    "User-Agent": f"ITE-Intelligence-Downloader/1.0 (educational research; mailto:{CONTACT_EMAIL})" if CONTACT_EMAIL else "ITE-Intelligence-Downloader/1.0 (educational research)"
}

# ── Actor-discovered PDF URLs (run PW1zeM9Sr6VmgHVYV, 2026-04-03) ────────────
# Format: (codon_filename, pdf_url)
BATCH = [
    (
        "Islam_2016#@#ART-1940@#@.pdf",
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC4748908/pdf/medi-95-e2658.pdf",
    ),
    (
        "Bernard-Bonnin_2006#@#ART-1941@#@.pdf",
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC1783606/pdf/jCFP_v052_pg1247.pdf",
    ),
    (
        "Walitt_2015#@#ART-1942@#@.pdf",
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC4755337/pdf/CD011735.pdf",
    ),
    (
        "Venekamp_2016#@#ART-1944@#@.pdf",
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC6465056/pdf/CD011684.pdf",
    ),
    (
        "Keay_2012#@#ART-1949@#@.pdf",
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC4261928/pdf/nihms644925.pdf",
    ),
    (
        "Bocchetta_2006#@#ART-1954@#@.pdf",
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC1584230/pdf/1745-0179-2-23.pdf",
    ),
    (
        "Nahid_2016#@#ART-1965@#@.pdf",
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC6590850/pdf/ciw376.pdf",
    ),
    (
        "Byington_2012#@#ART-1972@#@.pdf",
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC4074609/pdf/peds.2012-0127.pdf",
    ),
    (
        "Khan_2010#@#ART-1975@#@.pdf",
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC2943085/pdf/JO2010-654348.pdf",
    ),
    # ART-1976 (Reddy_2010 / PMC2974597) — no article PDF found by actor, manual only
]


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Output: {OUTPUT_DIR}")
    print(f"Batch:  {len(BATCH)} articles\n")

    downloaded = 0
    failed = []

    for filename, url in BATCH:
        dest = OUTPUT_DIR / filename
        print(f"  {filename}")

        if dest.exists():
            print(f"    ↓ already exists, skipping\n")
            downloaded += 1
            continue

        try:
            resp = requests.get(url, headers=HEADERS, timeout=60, allow_redirects=True)
            if resp.status_code == 200 and resp.content[:4] == b'%PDF' and len(resp.content) > 10_000:
                dest.write_bytes(resp.content)
                size_kb = len(resp.content) // 1024
                print(f"    ✓ {size_kb} KB\n")
                downloaded += 1
            else:
                print(f"    ✗ HTTP {resp.status_code} | {len(resp.content)} bytes | not a valid PDF")
                print(f"    → Add to manual list\n")
                failed.append(filename)
        except Exception as e:
            print(f"    ✗ Error: {e}\n")
            failed.append(filename)

        time.sleep(0.5)

    print("═══ SUMMARY ══════════════════════════════════════════════════")
    print(f"  Downloaded: {downloaded}")
    print(f"  Failed:     {len(failed)}")
    if failed:
        print("\n  Manual download still needed:")
        for f in failed:
            print(f"    {f}")
    print()
    print("Next: run backfill_new_article_metadata.py --art-id-min 1938")


if __name__ == "__main__":
    main()
