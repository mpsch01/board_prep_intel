#!/usr/bin/env python3
"""
download_aafp_acquisitions.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Downloads PDFs for the 49 AAFP acquisition articles.

Workflow:
  1. Reads aafp_pubmed_acquisition_queue_20260328.csv + the DB to get ART-IDs
  2. Queries NCBI ID converter to find PMC IDs (free full text)
  3. Downloads open-access PDFs from PMC → renames to codon format
  4. Prints a checklist of subscription articles for manual download

Run from Windows (NCBI is accessible there):
  python download_aafp_acquisitions.py --dry-run   ← preview only
  python download_aafp_acquisitions.py             ← download OA PDFs
  python download_aafp_acquisitions.py --checklist ← print manual list only

Requirements: requests (pip install requests)
Output folder: 01_module.1_warehouse/citation_files/ITE/VC_fail/   (all new articles are VC_fail tier)
"""

import csv
import json
import re
import sqlite3
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
DB_PATH      = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"
QUEUE_CSV    = PROJECT_ROOT / "00_database" / "readable_db_files" / \
               "aafp_pubmed_acquisition_queue_20260328.csv"
OUTPUT_DIR   = PROJECT_ROOT / "01_module.1_warehouse" / "citation_files" / "ITE" / "VC_fail"

DRY_RUN   = "--dry-run"   in sys.argv
CHECKLIST = "--checklist" in sys.argv

# ── NCBI endpoints ────────────────────────────────────────────────────────────
IDCONV_URL  = "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/"
PMC_OA_URL  = "https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi"   # returns FTP href

HEADERS = {
    "User-Agent": "ITE-Intelligence-Downloader/1.0 (educational research; mailto:scholl.michael.p@gmail.com)"
}

# ── Load queue + codon map from DB ───────────────────────────────────────────
def load_acquisition_map() -> list[dict]:
    """
    Returns list of dicts: {citation_id, aafp_qid, pmid, first_author, year,
                             title, journal, notes, article_id, codon_filename}
    Only includes rows with a PMID.
    """
    with open(QUEUE_CSV, newline='', encoding='utf-8') as f:
        queue = list(csv.DictReader(f))

    # Get ART-ID + codon_filename from DB for these articles
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Fetch by querying aafp_citations → articles join
    cit_ids = [r['citation_id'] for r in queue if r['pmid'].strip()]
    ph = ','.join('?' * len(cit_ids))
    cur.execute(f"""
        SELECT ac.citation_id, a.article_id, a.codon_filename
        FROM aafp_citations ac
        JOIN articles a ON ac.article_id = a.article_id
        WHERE ac.citation_id IN ({ph})
    """, cit_ids)
    art_map = {row[0]: (row[1], row[2]) for row in cur.fetchall()}
    conn.close()

    result = []
    for row in queue:
        pmid = row['pmid'].strip()
        if not pmid:
            continue  # skip 3 Cochrane without PMID
        cit_id = row['citation_id']
        if cit_id in art_map:
            art_id, codon = art_map[cit_id]
            row['article_id'] = art_id
            row['codon_filename'] = codon
        else:
            row['article_id'] = '???'
            row['codon_filename'] = f"{row['first_author']}_{row['year']}_UNKNOWN.pdf"
        result.append(row)
    return result


# ── NCBI ID converter: PMID → PMCID ──────────────────────────────────────────
def get_pmcids(pmids: list[str]) -> dict[str, str]:
    """
    Calls NCBI ID converter in batches of 20.
    Returns {pmid: pmcid} for articles with free full text on PMC.
    PMIDs without PMCIDs are not included in the result.
    """
    pmcid_map = {}
    batch_size = 20

    for i in range(0, len(pmids), batch_size):
        batch = pmids[i:i + batch_size]
        params = {
            "tool":   "ITE-Intelligence",
            "email":  "scholl.michael.p@gmail.com",
            "ids":    ",".join(batch),
            "idtype": "pmid",
            "format": "json",
        }
        try:
            resp = requests.get(IDCONV_URL, params=params, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            for record in data.get("records", []):
                pmid = str(record.get("pmid", ""))
                pmcid = record.get("pmcid", "")
                if pmid and pmcid:
                    pmcid_map[pmid] = pmcid
        except Exception as e:
            print(f"  WARN: NCBI ID converter error (batch {i//batch_size + 1}): {e}")
        time.sleep(0.4)  # be polite to NCBI

    return pmcid_map


# ── Get direct PDF download URL via PMC OA API ───────────────────────────────
def get_pmc_pdf_url(pmcid: str) -> str | None:
    """
    Queries the PMC Open Access API to get the FTP/HTTPS URL for the PDF.
    PMC OA API returns XML: <link format="pdf" href="ftp://..." />
    We convert ftp:// → https:// for direct HTTP download.
    Returns download URL string, or None if not available.
    """
    try:
        resp = requests.get(
            PMC_OA_URL,
            params={"id": pmcid, "format": "pdf"},
            headers=HEADERS,
            timeout=15,
        )
        if resp.status_code != 200:
            return None
        # Parse the XML for the pdf href
        import xml.etree.ElementTree as ET
        root = ET.fromstring(resp.text)
        for link in root.iter("link"):
            fmt  = link.get("format", "")
            href = link.get("href", "")
            if fmt == "pdf" and href:
                # Convert ftp:// to https:// — NCBI FTP is also served over HTTPS
                https_url = href.replace("ftp://ftp.ncbi.nlm.nih.gov", "https://ftp.ncbi.nlm.nih.gov")
                return https_url
    except Exception as e:
        print(f"    WARN: OA API error for {pmcid}: {e}")
    return None


# ── Fallback: NCBI E-Fetch PDF endpoint ───────────────────────────────────────
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

def get_pmc_viewer_pdf_url(pmcid: str) -> str:
    """
    Fallback strategy when the OA API returns no PDF URL.
    Constructs the NCBI E-Fetch PDF endpoint URL directly — no pre-flight
    network call needed.  Whether the endpoint actually serves a PDF depends
    on the article's access status; the %PDF sanity check in download_pmc_pdf
    handles validation cleanly.
    Covers articles in PMC that are readable but outside the strict OA FTP subset.
    """
    return (
        f"{EFETCH_URL}?db=pmc&id={pmcid}&rettype=pdf"
        f"&tool=ITE-Intelligence&email=scholl.michael.p%40gmail.com"
    )


# ── Download PDF from PMC ─────────────────────────────────────────────────────
def download_pmc_pdf(pmcid: str, dest_path: Path) -> bool:
    """
    Downloads the PDF for a PMC article.
    Strategy 1: PMC OA API  → FTP/HTTPS URL (strict OA subset)
    Strategy 2: PMC viewer scrape → direct PDF link (broader coverage)
    Returns True on success.
    """
    # Strategy 1: OA API
    pdf_url = get_pmc_pdf_url(pmcid)

    # Strategy 2: viewer page scrape
    if not pdf_url:
        pdf_url = get_pmc_viewer_pdf_url(pmcid)
        if pdf_url:
            print(f"    → PDF URL via viewer scrape")
        else:
            print(f"    ✗ No PDF URL found for {pmcid} (may require subscription)")
            return False
    try:
        resp = requests.get(pdf_url, headers=HEADERS, timeout=60, allow_redirects=True)
        if resp.status_code == 200 and len(resp.content) > 10_000:
            # Sanity check: real PDFs start with %PDF
            if resp.content[:4] == b'%PDF':
                dest_path.write_bytes(resp.content)
                size_kb = len(resp.content) // 1024
                print(f"    ✓ {dest_path.name} ({size_kb} KB)")
                return True
            else:
                print(f"    ✗ Downloaded file is not a valid PDF for {pmcid}")
                return False
        else:
            print(f"    ✗ Download failed for {pmcid}: HTTP {resp.status_code}, {len(resp.content)} bytes")
            return False
    except Exception as e:
        print(f"    ✗ Download error for {pmcid}: {e}")
        return False


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print(f"DB:       {DB_PATH}")
    print(f"Queue:    {QUEUE_CSV}")
    print(f"Output:   {OUTPUT_DIR}")
    print(f"Dry run:  {DRY_RUN}")
    print()

    # Load acquisition map
    articles = load_acquisition_map()
    print(f"Articles with PMID: {len(articles)}")

    if CHECKLIST:
        # Just print the manual download list
        print()
        print("═══ MANUAL DOWNLOAD CHECKLIST ═══════════════════════════════")
        print("For each article: download PDF from institutional access,")
        print(f"rename to the codon filename, and place in: {OUTPUT_DIR}")
        print()
        for a in articles:
            print(f"  PMID {a['pmid']:>10}  {a['codon_filename']}")
            print(f"    {a['pubmed_url']}")
        return

    # Query NCBI for PMC IDs
    pmids = [a['pmid'] for a in articles]
    print("Querying NCBI for PMC IDs (free full-text availability)...")
    pmcid_map = get_pmcids(pmids)
    print(f"  PMC IDs found: {len(pmcid_map)} of {len(pmids)} articles")
    print()

    # Split into open-access and manual groups
    oa_articles      = [a for a in articles if a['pmid'] in pmcid_map]
    manual_articles  = [a for a in articles if a['pmid'] not in pmcid_map]

    # Also include the 3 Cochrane-only rows (no PMID) in manual list
    with open(QUEUE_CSV, newline='', encoding='utf-8') as f:
        all_rows = list(csv.DictReader(f))
    cochrane_no_pmid = [r for r in all_rows if not r['pmid'].strip()]

    print(f"Open-access (PMC):  {len(oa_articles)} articles → auto-download")
    print(f"Subscription:       {len(manual_articles)} articles → manual")
    print(f"Cochrane (no PMID): {len(cochrane_no_pmid)} articles → manual")
    print()

    # ── Download open-access ──
    downloaded = 0
    failed_oa  = []

    if oa_articles:
        print("═══ DOWNLOADING OPEN-ACCESS PDFs ════════════════════════════")
        if not DRY_RUN:
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        for a in oa_articles:
            pmcid = pmcid_map[a['pmid']]
            dest  = OUTPUT_DIR / a['codon_filename']
            print(f"  {a['article_id']}  {a['first_author']} {a['year']}  (PMCID: {pmcid})")
            print(f"    → {a['codon_filename']}")

            if DRY_RUN:
                print(f"    [DRY RUN — would download from PMC]")
                continue

            if dest.exists():
                print(f"    ↓ already exists, skipping")
                downloaded += 1
                continue

            success = download_pmc_pdf(pmcid, dest)
            if success:
                downloaded += 1
            else:
                failed_oa.append(a)
            time.sleep(0.5)

    # ── Manual download list ──
    print()
    print("═══ MANUAL DOWNLOAD REQUIRED ════════════════════════════════")
    print(f"Download from institutional access → rename → place in:")
    print(f"  {OUTPUT_DIR}")
    print()
    for a in manual_articles:
        print(f"  {a['article_id']}  PMID {a['pmid']:>10}  {a['codon_filename']}")
        print(f"    {a['pubmed_url']}")
    for r in cochrane_no_pmid:
        print(f"  (no ART-ID yet)  Cochrane  {r['first_author']} {r['year']}")
        print(f"    {r['notes']}")

    if failed_oa:
        print()
        print("═══ OA ARTICLES: DOWNLOAD FROM BROWSER (free, no subscription) ══")
        print("These are open-access but auto-download failed. Go to each URL,")
        print("download the PDF, rename to the codon filename, place in VC_fail/")
        print()
        for a in failed_oa:
            pmcid = pmcid_map[a['pmid']]
            print(f"  {a['article_id']}  {a['codon_filename']}")
            print(f"    https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/")

    # ── Summary ──
    print()
    print("═══ SUMMARY ══════════════════════════════════════════════════")
    if not DRY_RUN:
        print(f"  Downloaded (OA):   {downloaded}")
        print(f"  OA failures:       {len(failed_oa)}")
    print(f"  Manual needed:     {len(manual_articles) + len(cochrane_no_pmid)}")
    print()
    print("After all PDFs are in VC_fail/, run:")
    print("  python 01_module.1_warehouse/scripts/maintain/backfill_new_article_metadata.py --art-id-min 1938")


if __name__ == "__main__":
    if "--help" in sys.argv:
        print(__doc__)
        sys.exit(0)
    if not DB_PATH.exists():
        print(f"ERROR: DB not found: {DB_PATH}")
        sys.exit(1)
    if not QUEUE_CSV.exists():
        print(f"ERROR: Queue CSV not found: {QUEUE_CSV}")
        sys.exit(1)
    main()
