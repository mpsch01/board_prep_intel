"""
aafp_pmc_oa_downloader.py
=========================
Downloads PDFs for the 9 AAFP-only PMC articles using the NCBI OA API.

These articles failed in aafp_pdf_downloader.py because direct PMC PDF
URLs return HTTP 403 to requests scraping. The NCBI OA API (oa.fcgi)
returns authenticated FTP/HTTPS links for articles in the OA subset.

Usage:
    python aafp_pmc_oa_downloader.py
    python aafp_pmc_oa_downloader.py --dry-run

Output:
    citation_files/AAFP/  →  codon-named PDFs

Requires: NCBI_API_KEY in environment (optional but faster with it)
"""

import os, re, io, tarfile, time, argparse
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime

# ── Paths ──────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent   # maintain->scripts->M1->root
DEST         = PROJECT_ROOT / "01_module.1_warehouse" / "citation_files" / "AAFP"

# ── NCBI API ───────────────────────────────────────────────────────────────
NCBI_API_KEY = os.environ.get("NCBI_API_KEY", "").strip()
OA_API_URL   = "https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi"
RATE_LIMIT   = 0.5
TIMEOUT      = 20
CHUNK_SIZE   = 8192
MAX_PDF_MB   = 50

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/pdf,application/octet-stream,*/*",
}

# ── Target articles: (art_id, codon_filename, pmc_id) ─────────────────────
ARTICLES = [
    ("ART-1945", "Albalawi_2011#@#ART-1945@#@.pdf",       "PMC6492479"),
    ("ART-1949", "Keay_2012#@#ART-1949@#@.pdf",           "PMC4261928"),
    ("ART-1950", "Dennis_2008#@#ART-1950@#@.pdf",         "PMC6148705"),
    ("ART-0864", "Metlay_Waterer_2019#@#ART-0864@#@.pdf", "PMC6812437"),
    ("ART-1959", "Binic_2011#@#ART-1959@#@.pdf",          "PMC4996308"),
    ("ART-1972", "Byington_2012#@#ART-1972@#@.pdf",       "PMC4074609"),
    ("ART-1940", "Islam_2016#@#ART-1940@#@.pdf",          "PMC4748908"),
    ("ART-1967", "Verbalis_2007#@#ART-1967@#@.pdf",       "PMC2643091"),
    ("ART-1975", "Khan_2010#@#ART-1975@#@.pdf",           "PMC2943085"),
]


def get_oa_links(pmc_id):
    """Call NCBI OA API. Returns (pdf_url, tgz_url, status)."""
    params = {"id": pmc_id}
    if NCBI_API_KEY:
        params["api_key"] = NCBI_API_KEY
    try:
        resp = requests.get(OA_API_URL, params=params, timeout=TIMEOUT)
        resp.raise_for_status()
    except Exception as e:
        return None, None, f"api_error: {e}"
    try:
        root = ET.fromstring(resp.text)
    except ET.ParseError as e:
        return None, None, f"xml_error: {e}"
    error = root.find(".//error")
    if error is not None:
        return None, None, f"not_oa ({error.get('code', '?')})"
    pdf_url = tgz_url = None
    for link in root.findall(".//link"):
        fmt  = link.get("format", "")
        href = link.get("href", "").replace("ftp://", "https://", 1)
        if fmt == "pdf":
            pdf_url = href
        elif fmt == "tgz":
            tgz_url = href
    if pdf_url:
        return pdf_url, tgz_url, "found"
    if tgz_url:
        return None, tgz_url, "tgz_only"
    return None, None, "no_pdf"


def download_pdf(url, dest):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT,
                            stream=True, allow_redirects=True)
        if resp.status_code != 200:
            return False, f"http_{resp.status_code}", 0
        dest.parent.mkdir(parents=True, exist_ok=True)
        size = 0
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(CHUNK_SIZE):
                f.write(chunk)
                size += len(chunk)
                if size > MAX_PDF_MB * 1024 * 1024:
                    dest.unlink(missing_ok=True)
                    return False, "too_large", 0
        if size < 1024:
            dest.unlink(missing_ok=True)
            return False, "too_small", 0
        with open(dest, "rb") as f:
            if not f.read(4).startswith(b"%PDF"):
                dest.unlink(missing_ok=True)
                return False, "not_pdf", 0
        return True, "ok", size
    except Exception as e:
        dest.unlink(missing_ok=True) if dest.exists() else None
        return False, f"error: {e}", 0

def extract_pdf_from_tgz(tgz_url, dest):
    try:
        resp = requests.get(tgz_url, headers=HEADERS, timeout=60, stream=True)
        if resp.status_code != 200:
            return False, f"http_{resp.status_code}", 0
        buf = io.BytesIO()
        size = 0
        for chunk in resp.iter_content(CHUNK_SIZE):
            buf.write(chunk)
            size += len(chunk)
            if size > 200 * 1024 * 1024:
                return False, "tgz_too_large", 0
        buf.seek(0)
        with tarfile.open(fileobj=buf, mode="r:gz") as tar:
            pdfs = [m for m in tar.getmembers() if m.name.lower().endswith(".pdf")]
            if not pdfs:
                return False, "no_pdf_in_tgz", 0
            member = max(pdfs, key=lambda m: m.size)
            pdf_bytes = tar.extractfile(member).read()
        if not pdf_bytes[:4].startswith(b"%PDF") or len(pdf_bytes) < 1024:
            return False, "not_pdf", 0
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(pdf_bytes)
        return True, "ok", len(pdf_bytes)
    except Exception as e:
        return False, f"error: {e}", 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print(f"\naafp_pmc_oa_downloader.py  —  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Destination: {DEST}")
    print(f"NCBI key:    {'loaded' if NCBI_API_KEY else 'NOT SET (rate-limited to 3/sec)'}")
    print(f"Articles:    {len(ARTICLES)}\n")
    print("-" * 70)

    if args.dry_run:
        for art_id, fname, pmc_id in ARTICLES:
            on_disk = (DEST / fname).exists()
            status = "ON DISK" if on_disk else "PENDING"
            print(f"  {status:8}  {art_id}  {pmc_id}  {fname}")
        return

    ok_list, fail_list, skip_list = [], [], []

    for art_id, fname, pmc_id in ARTICLES:
        dest = DEST / fname

        if dest.exists():
            print(f"SKIP   {art_id}  {fname}  ({dest.stat().st_size // 1024} KB on disk)")
            skip_list.append(art_id)
            continue

        print(f"\nDL     {art_id}  [{pmc_id}]  {fname}")
        pdf_url, tgz_url, oa_status = get_oa_links(pmc_id)
        print(f"  OA   {oa_status}" + (f": {(pdf_url or tgz_url or '')[:70]}" if pdf_url or tgz_url else ""))

        if pdf_url:
            success, status, nbytes = download_pdf(pdf_url, dest)
        elif tgz_url:
            print("  -> extracting from tgz...")
            success, status, nbytes = extract_pdf_from_tgz(tgz_url, dest)
        else:
            print(f"  SKIP ({oa_status})")
            fail_list.append((art_id, oa_status))
            time.sleep(RATE_LIMIT)
            continue

        if success:
            print(f"  OK   {nbytes // 1024} KB saved")
            ok_list.append((art_id, fname, nbytes // 1024))
        else:
            print(f"  FAIL {status}")
            fail_list.append((art_id, status))

        time.sleep(RATE_LIMIT)

    print("\n" + "=" * 70)
    print(f"SUMMARY:  OK={len(ok_list)}  SKIP={len(skip_list)}  FAIL={len(fail_list)}")
    if ok_list:
        print("\nDownloaded:")
        for art_id, fn, kb in ok_list:
            print(f"  {art_id}  {fn}  ({kb} KB)")
    if fail_list:
        print("\nFailed:")
        for art_id, reason in fail_list:
            print(f"  {art_id}  {reason}")
    print(f"\nDestination: {DEST}")


if __name__ == "__main__":
    main()
