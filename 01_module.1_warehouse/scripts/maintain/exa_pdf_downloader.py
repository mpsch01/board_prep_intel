"""
exa_pdf_downloader.py
=====================
Downloads PDFs discovered by exa_pdf_finder.py.

Handles three tiers of actionable results:
  direct_pdf    - fetches .pdf URL directly (259 articles)
  pmc_fulltext  - constructs PMC PDF URL from PMC article page (109 articles)
  open_access   - AAFP .html→.pdf swap (up to ~199 AFP articles)

Usage:
    python exa_pdf_downloader.py                           # all actionable
    python exa_pdf_downloader.py --classification direct_pdf
    python exa_pdf_downloader.py --classification pmc_fulltext
    python exa_pdf_downloader.py --tier VC_pass
    python exa_pdf_downloader.py --limit 10                # cap for testing
    python exa_pdf_downloader.py --dry-run                 # no downloads

AAFP credentials:
    Set env var AAFP_SESSION_COOKIE with the value of your 'AAFPSESSION'
    cookie from a logged-in browser session. This unlocks AFP articles
    that aren't yet freely available.

Output:
    PDFs saved to: 01_module.1_warehouse/citation_files/ITE/{tier}/
    Filename:      Author_Year#@#ART-XXXX@#@.pdf
    Log:           scripts/maintain/exa_download.log
    Results CSV:   scripts/maintain/exa_download_results.csv
"""

import os, re, csv, time, argparse, sys, json
import requests
from pathlib import Path
from datetime import datetime
from collections import Counter

# ── Paths ──────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent   # maintain→scripts→M1→root
PDF_ROOT     = PROJECT_ROOT / "01_module.1_warehouse" / "citation_files" / "ITE"
QUEUE_CSV    = SCRIPT_DIR / "exa_pdf_queue.csv"
RESULTS_CSV  = SCRIPT_DIR / "exa_download_results.csv"
LOG_PATH     = SCRIPT_DIR / "exa_download.log"

# ── Download settings ──────────────────────────────────────────────────────
RATE_LIMIT_SEC  = 2.0          # seconds between requests
MAX_PDF_MB      = 50           # skip files larger than this
TIMEOUT_SEC     = 30
CHUNK_SIZE      = 8192

# ── Codon regex (for scanning on-disk files) ───────────────────────────────
CODON_RE = re.compile(r'#@#(ART-\d+)@#@')

# ── PMC URL patterns ───────────────────────────────────────────────────────
PMC_ID_RE = re.compile(r'PMC(\d+)', re.IGNORECASE)

# ── Browser-like headers (avoids 403 on many servers) ─────────────────────
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/pdf,application/octet-stream,*/*",
    "Accept-Language": "en-US,en;q=0.9",
}

# ── Logging ────────────────────────────────────────────────────────────────
_log_fh = None

def log(msg):
    print(msg, flush=True)
    if _log_fh:
        _log_fh.write(msg + "\n")
        _log_fh.flush()

# ── Filename builder ───────────────────────────────────────────────────────
def make_codon_filename(row):
    """Build codon-format filename: Author_Year#@#ART-XXXX@#@.pdf"""
    author = (row.get("author1") or "Unknown").strip()
    # Take first token (handles 'Smith J' → 'Smith', 'ACOG Practice...' → 'ACOG')
    author_first = re.split(r'[\s,;/]', author)[0]
    author_safe  = re.sub(r'[^\w\-]', '', author_first) or "Unknown"
    year         = str(row.get("year") or "0000").strip()
    art_id       = row.get("article_id", "ART-0000")
    return f"{author_safe}_{year}#@#{art_id}@#@.pdf"

def dest_folder(row):
    """Return the correct tier subfolder Path."""
    tier = row.get("tier", "VC_fail")
    return PDF_ROOT / tier

# ── On-disk ART-ID scanner ─────────────────────────────────────────────────
def get_art_ids_on_disk():
    found = set()
    if not PDF_ROOT.exists():
        return found
    for pdf_file in PDF_ROOT.rglob("*.pdf"):
        m = CODON_RE.search(pdf_file.name)
        if m:
            found.add(m.group(1))
    return found

# ── URL resolvers ──────────────────────────────────────────────────────────
def pmc_url_to_pdf_url(url):
    """
    Convert a PMC article page URL to a direct PDF download URL.
    Tries the NCBI PMC endpoint first; EuroPMC is the fallback.
    """
    m = PMC_ID_RE.search(url)
    if not m:
        return None, None
    pmc_num = m.group(1)
    pmc_id  = f"PMC{pmc_num}"
    primary  = f"https://pmc.ncbi.nlm.nih.gov/articles/{pmc_id}/pdf/"
    fallback = f"https://europepmc.org/backend/ptpmcrender.fcgi?accid={pmc_id}&blobtype=pdf"
    return primary, fallback

def aafp_html_to_pdf_url(url):
    """Convert AAFP article HTML page URL to PDF URL (swap extension)."""
    u = url.lower()
    if "aafp.org/pubs/afp/issues" in u and url.endswith(".html"):
        return url[:-5] + ".pdf"
    if "aafp.org/pubs/afp/issues" in u and not url.endswith(".pdf"):
        return url + ".pdf"
    return None

def resolve_download_url(row, aafp_cookie=None):
    """
    Return (primary_url, fallback_url, strategy) for a queue row.
    Returns (None, None, 'skip') if the row is not downloadable.
    """
    classification = row.get("classification", "")
    top_url        = row.get("top_url", "")

    if classification == "direct_pdf":
        return top_url, None, "direct"

    if classification == "pmc_fulltext":
        primary, fallback = pmc_url_to_pdf_url(top_url)
        if primary:
            return primary, fallback, "pmc"
        return None, None, "skip"

    if classification == "open_access":
        pdf_url = aafp_html_to_pdf_url(top_url)
        if pdf_url:
            return pdf_url, None, "aafp"
        return None, None, "skip"   # non-AAFP open_access: skip for now

    return None, None, "skip"

# ── CSV loaders ────────────────────────────────────────────────────────────
def load_queue(tier_filter=None, class_filter=None):
    if not QUEUE_CSV.exists():
        log(f"ERROR: Queue file not found: {QUEUE_CSV}")
        return []
    rows = []
    with open(QUEUE_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if tier_filter  and row.get("tier") != tier_filter:
                continue
            if class_filter and row.get("classification") != class_filter:
                continue
            rows.append(row)
    return rows

def load_existing_results():
    """Returns set of article_ids already in the results CSV."""
    done = set()
    if not RESULTS_CSV.exists():
        return done
    with open(RESULTS_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            done.add(row.get("article_id", ""))
    return done

# ── Core downloader ────────────────────────────────────────────────────────
def download_pdf(url, dest_path, aafp_cookie=None, fallback_url=None):
    """
    Download a PDF from url to dest_path.
    Returns (success: bool, status: str, bytes_written: int)
    """
    session = requests.Session()
    session.headers.update(HEADERS)

    # Inject AAFP session cookie when provided
    if aafp_cookie and "aafp.org" in url:
        session.cookies.set("AAFPSESSION", aafp_cookie, domain=".aafp.org")

    urls_to_try = [u for u in [url, fallback_url] if u]

    for attempt_url in urls_to_try:
        try:
            resp = session.get(attempt_url, timeout=TIMEOUT_SEC, stream=True,
                               allow_redirects=True)
            if resp.status_code != 200:
                log(f"    HTTP {resp.status_code} → {attempt_url[:70]}")
                continue

            content_type = resp.headers.get("Content-Type", "").lower()
            if "pdf" not in content_type and "octet-stream" not in content_type:
                # Check first bytes for PDF magic number
                first_bytes = next(resp.iter_content(chunk_size=8), b"")
                if not first_bytes.startswith(b"%PDF"):
                    log(f"    Not a PDF (Content-Type: {content_type[:40]})")
                    continue
                # It IS a PDF — write that first chunk then continue
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                with open(dest_path, "wb") as f:
                    f.write(first_bytes)
                    size = len(first_bytes)
                    for chunk in resp.iter_content(chunk_size=CHUNK_SIZE):
                        f.write(chunk)
                        size += len(chunk)
                        if size > MAX_PDF_MB * 1024 * 1024:
                            log(f"    File exceeds {MAX_PDF_MB}MB limit — aborting")
                            dest_path.unlink(missing_ok=True)
                            return False, "too_large", 0
                return True, "ok", size

            # Normal PDF path (content-type confirmed)
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            size = 0
            with open(dest_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=CHUNK_SIZE):
                    f.write(chunk)
                    size += len(chunk)
                    if size > MAX_PDF_MB * 1024 * 1024:
                        log(f"    File exceeds {MAX_PDF_MB}MB limit — aborting")
                        dest_path.unlink(missing_ok=True)
                        return False, "too_large", 0
            if size < 1024:
                log(f"    Suspiciously small ({size} bytes) — discarding")
                dest_path.unlink(missing_ok=True)
                return False, "too_small", 0
            return True, "ok", size

        except requests.exceptions.Timeout:
            log(f"    Timeout: {attempt_url[:70]}")
        except requests.exceptions.ConnectionError as e:
            log(f"    Connection error: {e}")
        except Exception as e:
            log(f"    Error: {e}")

    return False, "failed", 0

# ── Results writer ─────────────────────────────────────────────────────────
def append_result(row_data):
    """Append a single result row to the results CSV."""
    fields = ["article_id", "tier", "classification", "strategy",
              "status", "bytes", "dest_filename", "url_used",
              "title", "author1", "year", "source_type"]
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
    parser.add_argument("--tier",           default=None,
                        choices=["VC_pass", "VC_fail", "local_lite", "right_click"])
    parser.add_argument("--classification", default=None,
                        choices=["direct_pdf", "pmc_fulltext", "open_access"])
    parser.add_argument("--limit",          type=int, default=0)
    parser.add_argument("--resume",         action="store_true",
                        help="Skip article_ids already in results CSV")
    parser.add_argument("--dry-run",        action="store_true")
    args = parser.parse_args()

    _log_fh = open(LOG_PATH, "w", encoding="utf-8")
    log(f"=== exa_pdf_downloader.py - {datetime.now().isoformat()} ===")
    log(f"tier={args.tier} class={args.classification} limit={args.limit} "
        f"resume={args.resume} dry_run={args.dry_run}")

    # AAFP session cookie from env
    aafp_cookie = os.environ.get("AAFP_SESSION_COOKIE", "").strip()
    if aafp_cookie:
        log("  AAFP session cookie: LOADED (AFP gated articles unlocked)")
    else:
        log("  AAFP session cookie: not set (open AFP articles only)")

    # Load queue
    all_rows = load_queue(args.tier, args.classification)
    log(f"\nQueue loaded: {len(all_rows)} rows")

    # Filter to actionable only (direct_pdf, pmc_fulltext, AAFP open_access)
    actionable = []
    skipped_class = 0
    for row in all_rows:
        url, fallback, strategy = resolve_download_url(row, aafp_cookie)
        if strategy == "skip":
            skipped_class += 1
            continue
        row["_url"]      = url
        row["_fallback"] = fallback
        row["_strategy"] = strategy
        actionable.append(row)

    log(f"Actionable: {len(actionable)}  |  Skipped (non-downloadable class): {skipped_class}")

    # Resume: skip already-on-disk ART-IDs
    on_disk = get_art_ids_on_disk()
    before  = len(actionable)
    actionable = [r for r in actionable if r["article_id"] not in on_disk]
    if before != len(actionable):
        log(f"Resume: skipped {before - len(actionable)} already on disk")

    # Resume: skip already in results CSV
    if args.resume:
        done_ids = load_existing_results()
        before   = len(actionable)
        actionable = [r for r in actionable if r["article_id"] not in done_ids]
        if before != len(actionable):
            log(f"Resume: skipped {before - len(actionable)} already in results CSV")

    # Cap
    if args.limit:
        actionable = actionable[:args.limit]
        log(f"Capped at {args.limit} (--limit)")

    # Dry run
    if args.dry_run:
        by_class    = Counter(r["classification"] for r in actionable)
        by_strategy = Counter(r["_strategy"] for r in actionable)
        log(f"\n🔍 Dry run — {len(actionable)} files would be downloaded\n")
        log("  By classification:")
        for k, v in by_class.most_common():
            log(f"    {k}: {v}")
        log("\n  By strategy:")
        for k, v in by_strategy.most_common():
            log(f"    {k}: {v}")
        log("\n  First 15 planned downloads:")
        for r in actionable[:15]:
            fname = make_codon_filename(r)
            log(f"    [{r['_strategy']:6}] {r['article_id']} → {fname}")
            log(f"             {r['_url'][:75]}")
        if len(actionable) > 15:
            log(f"  ... and {len(actionable)-15} more")
        _log_fh.close()
        return

    # ── Download loop ─────────────────────────────────────────────────────
    log(f"\nStarting downloads: {len(actionable)} files\n")
    counters = Counter()

    for i, row in enumerate(actionable, 1):
        art_id   = row["article_id"]
        strategy = row["_strategy"]
        url      = row["_url"]
        fallback = row["_fallback"]
        fname    = make_codon_filename(row)
        folder   = dest_folder(row)
        dest     = folder / fname

        log(f"[{i}/{len(actionable)}] {art_id} [{strategy}] {(row.get('title') or '')[:50]}")
        log(f"  → {fname}")
        log(f"    {url[:80]}")

        success, status, nbytes = download_pdf(
            url, dest, aafp_cookie=aafp_cookie, fallback_url=fallback
        )

        if success:
            kb = nbytes // 1024
            log(f"    ✓ saved ({kb} KB)")
            counters["downloaded"] += 1
        else:
            log(f"    ✗ {status}")
            counters[status] += 1
            # Clean up empty file if it was created
            if dest.exists() and dest.stat().st_size == 0:
                dest.unlink()

        append_result({
            "article_id":    art_id,
            "tier":          row.get("tier"),
            "classification":row.get("classification"),
            "strategy":      strategy,
            "status":        "ok" if success else status,
            "bytes":         nbytes,
            "dest_filename": fname if success else "",
            "url_used":      url,
            "title":         row.get("title", ""),
            "author1":       row.get("author1", ""),
            "year":          row.get("year", ""),
            "source_type":   row.get("source_type", ""),
        })

        time.sleep(RATE_LIMIT_SEC)

    # ── Final summary ─────────────────────────────────────────────────────
    total_tried = len(actionable)
    log("\n" + "═" * 50)
    log("📦 Download Summary")
    log("═" * 50)
    log(f"  ✓ downloaded:  {counters['downloaded']:4}  /  {total_tried}")
    log(f"  ✗ failed:      {counters['failed']:4}")
    log(f"  ✗ too_small:   {counters['too_small']:4}")
    log(f"  ✗ too_large:   {counters['too_large']:4}")
    log(f"  ✗ other:       {sum(v for k,v in counters.items() if k not in ('downloaded','failed','too_small','too_large')):4}")

    # Total PDFs now on disk
    final_on_disk = len(get_art_ids_on_disk())
    log(f"\n  PDFs on disk (total): {final_on_disk}")
    log(f"  Results log: {RESULTS_CSV}")
    log(f"  Download log: {LOG_PATH}")

    _log_fh.close()


if __name__ == "__main__":
    main()
