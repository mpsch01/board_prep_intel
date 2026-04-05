"""
pmc_oa_downloader.py
====================
Downloads PDFs for PMC articles using the NCBI Open Access API.

Targets the 109 PMC articles that failed in exa_pdf_downloader.py
(blocked by 403 on direct PMC PDF URL endpoints).

The NCBI OA API (oa.fcgi) returns authenticated FTP/HTTPS download
links for articles in the PMC Open Access Subset. Articles NOT in OA
are flagged as "not_oa" — those are truly paywalled even in PMC.

Typical yield: ~60-75% of PMC articles are in the OA subset.

Usage:
    python pmc_oa_downloader.py              # all failed PMC articles
    python pmc_oa_downloader.py --dry-run    # preview only, no downloads
    python pmc_oa_downloader.py --limit 10   # cap for testing
    python pmc_oa_downloader.py --all-pmc    # re-run ALL pmc entries
                                             # (ignores prior fail/ok)
Reads:
    exa_download_results.csv  → finds failed pmc strategy entries
    exa_pdf_queue.csv         → article metadata + tier info

Output:
    citation_files/ITE/{tier}/  →  codon-named PDFs
    scripts/maintain/pmc_oa_results.csv
    scripts/maintain/pmc_oa.log

Requires: NCBI_API_KEY in environment (set via system env vars)
"""

import os, re, csv, time, argparse, sys, io, tarfile
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime
from collections import Counter

# ── Paths ──────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
PDF_ROOT     = PROJECT_ROOT / "01_module.1_warehouse" / "citation_files" / "ITE"
QUEUE_CSV    = SCRIPT_DIR / "exa_pdf_queue.csv"
PREV_RESULTS = SCRIPT_DIR / "exa_download_results.csv"
RESULTS_CSV  = SCRIPT_DIR / "pmc_oa_results.csv"
LOG_PATH     = SCRIPT_DIR / "pmc_oa.log"

# ── NCBI API ───────────────────────────────────────────────────────────────
NCBI_API_KEY  = os.environ.get("NCBI_API_KEY", "").strip()
OA_API_URL    = "https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi"
RATE_LIMIT    = 0.5    # seconds between requests (10/sec allowed with API key)
TIMEOUT       = 20
CHUNK_SIZE    = 8192
MAX_PDF_MB    = 50

# ── Regex ──────────────────────────────────────────────────────────────────
CODON_RE  = re.compile(r'#@#(ART-\d+)@#@')
PMC_ID_RE = re.compile(r'PMC(\d+)', re.IGNORECASE)

# ── Headers ────────────────────────────────────────────────────────────────
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/pdf,application/octet-stream,*/*",
}

# ── Logging ────────────────────────────────────────────────────────────────
_log_fh = None

def log(msg):
    print(msg, flush=True)
    if _log_fh:
        _log_fh.write(msg + "\n")
        _log_fh.flush()

# ── Filename / folder helpers ──────────────────────────────────────────────
def make_codon_filename(row):
    author = (row.get("author1") or "Unknown").strip()
    author_first = re.split(r'[\s,;/]', author)[0]
    author_safe  = re.sub(r'[^\w\-]', '', author_first) or "Unknown"
    year   = str(row.get("year") or "0000").strip()
    art_id = row.get("article_id", "ART-0000")
    return f"{author_safe}_{year}#@#{art_id}@#@.pdf"

def dest_folder(row):
    return PDF_ROOT / (row.get("tier") or "VC_fail")

def get_art_ids_on_disk():
    found = set()
    for pdf in PDF_ROOT.rglob("*.pdf"):
        m = CODON_RE.search(pdf.name)
        if m:
            found.add(m.group(1))
    return found

# ── NCBI OA API ────────────────────────────────────────────────────────────
def get_oa_links(pmc_id_str):
    """
    Call the NCBI OA API for a PMC ID (e.g. 'PMC3278056').
    Returns (pdf_url, tgz_url, status) where status is one of:
      'found'      – direct PDF link available
      'tgz_only'   – OA record exists but only tgz package (no PDF link)
      'not_oa'     – article not in OA subset
      'api_error'  – network or parse failure
    """
    params = {"id": pmc_id_str}
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
        return None, None, f"api_error: xml parse: {e}"

    # Check for error element (article not in OA subset)
    error = root.find(".//error")
    if error is not None:
        code = error.get("code", "unknown")
        return None, None, f"not_oa ({code})"

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

# ── PDF downloader ─────────────────────────────────────────────────────────
def download_pdf(url, dest_path):
    """Download PDF from url → dest_path. Returns (success, status, bytes)."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT,
                            stream=True, allow_redirects=True)
        if resp.status_code != 200:
            return False, f"http_{resp.status_code}", 0

        content_type = resp.headers.get("Content-Type", "").lower()
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        size = 0
        with open(dest_path, "wb") as f:
            for chunk in resp.iter_content(CHUNK_SIZE):
                f.write(chunk)
                size += len(chunk)
                if size > MAX_PDF_MB * 1024 * 1024:
                    dest_path.unlink(missing_ok=True)
                    return False, "too_large", 0

        if size < 1024:
            dest_path.unlink(missing_ok=True)
            return False, "too_small", 0

        # Quick PDF magic check
        with open(dest_path, "rb") as f:
            if not f.read(4).startswith(b"%PDF"):
                dest_path.unlink(missing_ok=True)
                return False, "not_pdf", 0

        return True, "ok", size

    except Exception as e:
        if dest_path.exists():
            dest_path.unlink(missing_ok=True)
        return False, f"error: {e}", 0

# ── TGZ extractor ─────────────────────────────────────────────────────────
def extract_pdf_from_tgz(tgz_url, dest_path):
    """
    Download a PMC tgz package, extract the PDF from inside it.
    Returns (success, status, bytes_written).
    The tgz typically contains: article.nxml, figures, and sometimes a PDF.
    """
    try:
        resp = requests.get(tgz_url, headers=HEADERS, timeout=60, stream=True)
        if resp.status_code != 200:
            return False, f"http_{resp.status_code}", 0

        # Stream tgz into memory (cap at 200 MB)
        buf = io.BytesIO()
        size = 0
        for chunk in resp.iter_content(CHUNK_SIZE):
            buf.write(chunk)
            size += len(chunk)
            if size > 200 * 1024 * 1024:
                return False, "tgz_too_large", 0
        buf.seek(0)

        # Open tarball and find PDF member
        with tarfile.open(fileobj=buf, mode="r:gz") as tar:
            pdf_members = [m for m in tar.getmembers()
                           if m.name.lower().endswith(".pdf")]
            if not pdf_members:
                return False, "no_pdf_in_tgz", 0

            # Take the largest PDF (usually the main article)
            pdf_member = max(pdf_members, key=lambda m: m.size)
            f = tar.extractfile(pdf_member)
            if not f:
                return False, "extract_failed", 0

            pdf_bytes = f.read()

        # Validate it's a real PDF
        if not pdf_bytes[:4].startswith(b"%PDF"):
            return False, "not_pdf", 0
        if len(pdf_bytes) < 1024:
            return False, "too_small", 0

        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_bytes(pdf_bytes)
        return True, "ok", len(pdf_bytes)

    except tarfile.TarError as e:
        return False, f"tar_error: {e}", 0
    except Exception as e:
        return False, f"error: {e}", 0


# ── Data loaders ───────────────────────────────────────────────────────────
def load_pmc_targets(all_pmc=False):
    """
    Build target list from exa_pdf_queue.csv (metadata) joined with
    exa_download_results.csv (to find the ones that failed or if all_pmc).
    Returns list of dicts with article metadata + top_url.
    """
    # Load queue metadata (all pmc_fulltext rows)
    queue = {}
    if QUEUE_CSV.exists():
        with open(QUEUE_CSV, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("classification") == "pmc_fulltext":
                    queue[row["article_id"]] = row

    if all_pmc:
        return list(queue.values())

    # Filter to only those that previously failed
    failed_ids = set()
    if PREV_RESULTS.exists():
        with open(PREV_RESULTS, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("strategy") == "pmc" and row.get("status") != "ok":
                    failed_ids.add(row["article_id"])

    return [queue[aid] for aid in failed_ids if aid in queue]

def append_result(row_data):
    fields = ["article_id", "tier", "pmc_id", "oa_status",
              "download_status", "bytes", "dest_filename",
              "pdf_url", "title", "author1", "year", "source_type"]
    write_header = not RESULTS_CSV.exists()
    with open(RESULTS_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        if write_header:
            w.writeheader()
        w.writerow(row_data)

# ── Main ───────────────────────────────────────────────────────────────────
def main():
    global _log_fh

    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run",  action="store_true")
    parser.add_argument("--limit",    type=int, default=0)
    parser.add_argument("--all-pmc",  action="store_true",
                        help="Re-run all pmc_fulltext entries, not just failed ones")
    args = parser.parse_args()

    _log_fh = open(LOG_PATH, "w", encoding="utf-8")
    log(f"=== pmc_oa_downloader.py - {datetime.now().isoformat()} ===")

    if not NCBI_API_KEY:
        log("WARNING: NCBI_API_KEY not set — rate limit is 3 req/sec (slower)")
    else:
        log(f"NCBI API key: loaded ({NCBI_API_KEY[:8]}...)")

    # Load targets
    targets = load_pmc_targets(all_pmc=args.all_pmc)
    log(f"\nPMC targets loaded: {len(targets)}")

    # Skip already on disk
    on_disk = get_art_ids_on_disk()
    before  = len(targets)
    targets = [t for t in targets if t["article_id"] not in on_disk]
    if before != len(targets):
        log(f"Skipped {before - len(targets)} already on disk")

    if args.limit:
        targets = targets[:args.limit]
        log(f"Capped at {args.limit} (--limit)")

    if not targets:
        log("Nothing to do.")
        _log_fh.close()
        return

    # Dry run
    if args.dry_run:
        log(f"\n🔍 Dry run — {len(targets)} PMC articles would be checked\n")
        log("  First 15:")
        for t in targets[:15]:
            m = PMC_ID_RE.search(t.get("top_url", ""))
            pmc_id = f"PMC{m.group(1)}" if m else "PMC?"
            log(f"  {t['article_id']} [{t.get('tier')}] {pmc_id}  "
                f"{(t.get('title') or '')[:55]}")
        if len(targets) > 15:
            log(f"  ... and {len(targets)-15} more")
        _log_fh.close()
        return

    # ── Download loop ─────────────────────────────────────────────────────
    log(f"\nProcessing {len(targets)} PMC articles...\n")
    counters = Counter()

    for i, row in enumerate(targets, 1):
        art_id  = row["article_id"]
        top_url = row.get("top_url", "")
        m       = PMC_ID_RE.search(top_url)
        if not m:
            log(f"[{i}/{len(targets)}] {art_id} — no PMC ID in URL: {top_url}")
            counters["no_pmc_id"] += 1
            append_result({**row, "pmc_id": "", "oa_status": "no_pmc_id",
                           "download_status": "skip", "bytes": 0,
                           "dest_filename": "", "pdf_url": ""})
            continue

        pmc_id = f"PMC{m.group(1)}"
        log(f"[{i}/{len(targets)}] {art_id} [{pmc_id}] "
            f"{(row.get('title') or '')[:50]}")

        # Query OA API
        pdf_url, tgz_url, oa_status = get_oa_links(pmc_id)
        url_preview = (pdf_url or tgz_url or "")[:70]
        log(f"  OA API  {oa_status}" + (f": {url_preview}" if url_preview else ""))

        fname  = make_codon_filename(row)
        folder = dest_folder(row)
        dest   = folder / fname

        if pdf_url:
            # Direct PDF download
            success, dl_status, nbytes = download_pdf(pdf_url, dest)
            used_url = pdf_url
        elif tgz_url:
            # Extract PDF from tgz package
            log(f"  → extracting PDF from tgz package...")
            success, dl_status, nbytes = extract_pdf_from_tgz(tgz_url, dest)
            used_url = tgz_url
        else:
            # not_oa or no links at all — skip
            counters[oa_status.split("(")[0].strip()] += 1
            append_result({**row, "pmc_id": pmc_id, "oa_status": oa_status,
                           "download_status": "skip", "bytes": 0,
                           "dest_filename": "", "pdf_url": ""})
            time.sleep(RATE_LIMIT)
            continue

        if success:
            kb = nbytes // 1024
            log(f"  ✓ saved ({kb} KB) → {fname}")
            counters["downloaded"] += 1
        else:
            log(f"  ✗ {dl_status}")
            counters[f"dl_{dl_status}"] += 1

        append_result({**row, "pmc_id": pmc_id, "oa_status": oa_status,
                       "download_status": "ok" if success else dl_status,
                       "bytes": nbytes,
                       "dest_filename": fname if success else "",
                       "pdf_url": used_url})
        time.sleep(RATE_LIMIT)

    # ── Summary ───────────────────────────────────────────────────────────
    log("\n" + "═" * 50)
    log("📦 PMC OA Download Summary")
    log("═" * 50)
    log(f"  ✓ downloaded:  {counters['downloaded']:4}  / {len(targets)}")
    log(f"  ✗ not_oa:      {counters.get('not_oa', 0):4}  (paywalled even in PMC)")
    log(f"  ✗ no_pdf:      {counters.get('no_pdf', 0):4}  (OA but no PDF or tgz)")
    log(f"  ✗ tgz_fail:    {sum(v for k,v in counters.items() if k.startswith('dl_')):4}  (tgz found but PDF not inside)")
    log(f"  ✗ api_error:   {counters.get('api_error', 0):4}")
    log(f"  ✗ other:       {sum(v for k,v in counters.items() if k not in ('downloaded','not_oa','no_pdf','api_error')):4}")
    log(f"\n  PDFs on disk now: {len(get_art_ids_on_disk())}")
    log(f"  Results: {RESULTS_CSV}")
    _log_fh.close()


if __name__ == "__main__":
    main()
