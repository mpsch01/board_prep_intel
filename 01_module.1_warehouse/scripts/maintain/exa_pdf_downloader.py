"""
exa_pdf_downloader.py
=====================
Downloads PDFs discovered by exa_pdf_finder.py.

Handles four tiers of actionable results:
  direct_pdf    - fetches .pdf URL directly
  pmc_fulltext  - constructs PMC PDF URL from PMC article page
  open_access   - AAFP .html→.pdf swap (AFP articles)
  paywall       - authenticated download (JAMA Network, NEJM)

Usage:
    python exa_pdf_downloader.py                           # all actionable
    python exa_pdf_downloader.py --classification direct_pdf
    python exa_pdf_downloader.py --classification pmc_fulltext
    python exa_pdf_downloader.py --classification paywall
    python exa_pdf_downloader.py --tier VC_pass
    python exa_pdf_downloader.py --limit 10                # cap for testing
    python exa_pdf_downloader.py --dry-run                 # no downloads

Credentials (set as Windows environment variables once — persist across runs):
    AAFP_SESSION_COOKIE  - AAFP session cookie value (manual, browser DevTools)
    JAMA_EMAIL           - JAMA Network account email
    JAMA_PASSWORD        - JAMA Network account password
    NEJM_EMAIL           - NEJM account email
    NEJM_PASSWORD        - NEJM account password

JAMA/NEJM auth uses Playwright headless browser to log in with credentials on
each run — no manual cookie extraction required. Sessions are rebuilt automatically.

Output:
    PDFs saved to: 01_module.1_warehouse/citation_files/ITE/{tier}/
    Filename:      Author_Year#@#ART-XXXX@#@.pdf
    Log:           scripts/maintain/exa_download.log
    Results CSV:   scripts/maintain/exa_download_results.csv
"""

import os, re, csv, time, argparse, sys, json
import requests
try:
    import curl_cffi.requests as cffi_requests
    CURL_CFFI_AVAILABLE = True
except ImportError:
    CURL_CFFI_AVAILABLE = False
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
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/pdf,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "max-age=0",
    "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
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

# ── Credential-driven authentication (Playwright) ─────────────────────────

COOKIE_DIR = PROJECT_ROOT / "key_data_files" / "cookies"


def find_cookie_file(label_lower):
    """
    Find the most recently modified cookie file for a journal in COOKIE_DIR.
    Matches any .json or .txt file whose name contains the label (case-insensitive).
    Returns a Path or None.
    """
    if not COOKIE_DIR.exists():
        return None
    matches = [
        f for f in COOKIE_DIR.iterdir()
        if label_lower in f.name.lower() and f.suffix.lower() in (".json", ".txt")
    ]
    if not matches:
        return None
    return max(matches, key=lambda f: f.stat().st_mtime)


def load_session_from_cookie_file(label):
    """
    Load a requests.Session from a Cookie-Editor JSON export file.

    Looks in key_data_files/cookies/ for any .json/.txt file whose name
    contains the journal label (e.g. 'jama', 'nejm').  Picks the most
    recently modified match — so re-exporting cookies with a new date
    filename just works automatically.

    Returns an authenticated requests.Session, or None if no file found.
    """
    cookie_file = find_cookie_file(label.lower())
    if not cookie_file:
        log(f"  {label}: no cookie file found in key_data_files/cookies/")
        log(f"         Export cookies from Chrome (Cookie-Editor extension) and")
        log(f"         save the file with '{label.lower()}' in the filename.")
        return None

    try:
        with open(cookie_file, encoding="utf-8") as f:
            cookies = json.load(f)

        if not cookies:
            log(f"  ✗ {label}: cookie file is empty — re-export from Chrome")
            return None

        if CURL_CFFI_AVAILABLE:
            session = cffi_requests.Session(impersonate="chrome110")
            session.headers.update(HEADERS)
            log(f"  ✓ {label}: curl_cffi session (Chrome TLS impersonation active)")
        else:
            session = requests.Session()
            session.headers.update(HEADERS)
            log(f"  ⚠  {label}: curl_cffi not installed — Cloudflare bypass unavailable")
            log(f"         pip install curl-cffi")

        for c in cookies:
            session.cookies.set(
                c["name"], c["value"],
                domain=c.get("domain", ""),
                path=c.get("path", "/"),
            )

        log(f"  ✓ {label}: {len(cookies)} cookies loaded from {cookie_file.name}")
        return session

    except Exception as e:
        log(f"  ✗ {label} cookie load error: {e}")
        return None


def authenticate_jama():
    """Load JAMA session from cookie file in key_data_files/cookies/. Returns requests.Session or None."""
    return load_session_from_cookie_file("JAMA")


def authenticate_nejm():
    """Load NEJM session from cookie file in key_data_files/cookies/. Returns requests.Session or None."""
    return load_session_from_cookie_file("NEJM")


# ── URL resolvers ──────────────────────────────────────────────────────────

def pmc_url_to_pdf_url(url):
    """Convert a PMC article page URL to a direct PDF download URL."""
    m = PMC_ID_RE.search(url)
    if not m:
        return None, None
    pmc_num  = m.group(1)
    pmc_id   = f"PMC{pmc_num}"
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


def nejm_url_to_pdf_url(url):
    """
    Convert NEJM article page URL to direct PDF URL.
    NEJM pattern: /doi/full/10.xxxx  →  /doi/pdf/10.xxxx
                  /doi/abs/10.xxxx   →  /doi/pdf/10.xxxx
    Returns (primary_url, fallback_url).
    """
    for seg in ["/doi/full/", "/doi/abs/"]:
        if seg in url:
            return url.replace(seg, "/doi/pdf/"), None
    if "/doi/pdf/" in url:
        return url, None
    # Exa may have found a direct PDF URL already
    return url, None


def jama_resolve_pdf_url(article_url, session):
    """
    Fetch the JAMA article page with an authenticated session and extract
    the direct PDF download link (href containing /article-pdf/).

    Returns resolved PDF URL, or the original article_url as fallback
    (letting download_pdf() attempt it and validate via %PDF magic bytes).
    """
    # If Exa already found a direct PDF URL, skip the page-fetch step
    u = article_url.lower()
    if u.endswith(".pdf") or "article-pdf" in u:
        return article_url

    try:
        resp = session.get(article_url, timeout=TIMEOUT_SEC, allow_redirects=True)
        if resp.status_code == 200:
            # Primary pattern: /journals/{journal}/article-pdf/{id}/{filename}.pdf
            m = re.search(
                r'href="(/journals/[^"]+/article-pdf/[^"]+\.pdf)"',
                resp.text, re.IGNORECASE
            )
            if m:
                return f"https://jamanetwork.com{m.group(1)}"

            # Secondary: any href ending in .pdf that looks like a download
            m2 = re.search(
                r'href="([^"]*\.pdf)"[^>]*>[^<]*(?:download|pdf|full.?text)[^<]*',
                resp.text, re.IGNORECASE
            )
            if m2:
                href = m2.group(1)
                return href if href.startswith("http") else f"https://jamanetwork.com{href}"
    except Exception as e:
        log(f"    [JAMA resolve] {e}")

    return article_url   # fall through to direct download attempt


def resolve_download_url(row, aafp_cookie=None, jama_session=None, nejm_session=None):
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
        return None, None, "skip"

    if classification == "paywall":
        u = top_url.lower()
        if "nejm.org" in u and nejm_session:
            primary, fallback = nejm_url_to_pdf_url(top_url)
            return primary, fallback, "nejm_auth"
        if "jamanetwork.com" in u and jama_session:
            # URL resolution (page fetch) happens at download time with auth session
            return top_url, None, "jama_auth"
        return None, None, "skip"

    if classification == "landing_page":
        # exa_pdf_finder.py bug (now fixed): PAYWALL_PATTERNS incorrectly returned
        # "landing_page" instead of "paywall", so all 715 landing_page rows include
        # JAMA/NEJM articles that need auth. Route known auth domains here too.
        # Everything else gets a direct attempt — many will be OA or accessible.
        u = top_url.lower()
        if "nejm.org" in u and nejm_session:
            primary, fallback = nejm_url_to_pdf_url(top_url)
            return primary, fallback, "nejm_auth"
        if "jamanetwork.com" in u and jama_session:
            return top_url, None, "jama_auth"
        # Skip known hard paywalls we have no credentials for
        hard_skip = ["sciencedirect.com", "link.springer.com/article",
                     "journals.lww.com", "acc.org"]
        if any(p in u for p in hard_skip):
            return None, None, "skip"
        # Attempt direct download on everything else — validate via %PDF magic bytes
        return top_url, None, "direct_attempt"

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

def download_pdf(url, dest_path, aafp_cookie=None, fallback_url=None, auth_session=None):
    """
    Download a PDF from url to dest_path.

    auth_session: pre-authenticated requests.Session (JAMA, NEJM).
                  When provided it is used directly; no new session is created.

    Returns (success: bool, status: str, bytes_written: int)
    """
    if auth_session:
        session = auth_session
    else:
        session = requests.Session()
        session.headers.update(HEADERS)
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
                # Check PDF magic bytes before giving up
                first_bytes = next(resp.iter_content(chunk_size=8), b"")
                if not first_bytes.startswith(b"%PDF"):
                    log(f"    Not a PDF (Content-Type: {content_type[:40]})")
                    continue
                # It IS a PDF — write first chunk then stream the rest
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

            # Normal PDF path (Content-Type confirmed)
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
                        choices=["direct_pdf", "pmc_fulltext", "open_access", "paywall", "landing_page"])
    parser.add_argument("--strategy",       default=None,
                        choices=["direct", "pmc", "aafp", "nejm_auth", "jama_auth", "direct_attempt"],
                        help="Filter actionable items by resolved strategy (e.g. nejm_auth, jama_auth)")
    parser.add_argument("--limit",          type=int, default=0)
    parser.add_argument("--resume",         action="store_true",
                        help="Skip article_ids already in results CSV")
    parser.add_argument("--dry-run",        action="store_true")
    args = parser.parse_args()

    _log_fh = open(LOG_PATH, "w", encoding="utf-8")
    log(f"=== exa_pdf_downloader.py - {datetime.now().isoformat()} ===")
    log(f"tier={args.tier} class={args.classification} limit={args.limit} "
        f"resume={args.resume} dry_run={args.dry_run}")
    log("")

    # ── Credential setup ──────────────────────────────────────────────────

    # AAFP: manual session cookie (short-lived; set from browser DevTools when needed)
    aafp_cookie = os.environ.get("AAFP_SESSION_COOKIE", "").strip()
    if aafp_cookie:
        log("  AAFP:  session cookie loaded")
    else:
        log("  AAFP:  AAFP_SESSION_COOKIE not set (open AFP articles only)")

    # JAMA Network: loads from persistent profile saved by setup_journal_auth.py
    jama_session = authenticate_jama()
    if not jama_session:
        log("  JAMA:  no session — JAMA paywall articles will be skipped this run")
        log("         Run: python .../maintain/setup_journal_auth.py --jama")

    # NEJM: loads from persistent profile saved by setup_journal_auth.py
    nejm_session = authenticate_nejm()
    if not nejm_session:
        log("  NEJM:  no session — NEJM paywall articles will be skipped this run")
        log("         Run: python .../maintain/setup_journal_auth.py --nejm")

    log("")

    # ── Load queue ────────────────────────────────────────────────────────
    all_rows = load_queue(args.tier, args.classification)
    log(f"Queue loaded: {len(all_rows)} rows")

    # Filter to actionable rows
    actionable    = []
    skipped_class = 0
    for row in all_rows:
        url, fallback, strategy = resolve_download_url(
            row,
            aafp_cookie=aafp_cookie,
            jama_session=jama_session,
            nejm_session=nejm_session,
        )
        if strategy == "skip":
            skipped_class += 1
            continue
        row["_url"]      = url
        row["_fallback"] = fallback
        row["_strategy"] = strategy
        actionable.append(row)

    log(f"Actionable: {len(actionable)}  |  Skipped (no handler / no creds): {skipped_class}")

    if args.strategy:
        before = len(actionable)
        actionable = [r for r in actionable if r["_strategy"] == args.strategy]
        log(f"Strategy filter '{args.strategy}': {before} → {len(actionable)}")

    # Skip already-on-disk ART-IDs (always)
    on_disk = get_art_ids_on_disk()
    before  = len(actionable)
    actionable = [r for r in actionable if r["article_id"] not in on_disk]
    if before != len(actionable):
        log(f"Resume: skipped {before - len(actionable)} already on disk")

    # Optionally skip already-in-results-CSV
    if args.resume:
        done_ids = load_existing_results()
        before   = len(actionable)
        actionable = [r for r in actionable if r["article_id"] not in done_ids]
        if before != len(actionable):
            log(f"Resume: skipped {before - len(actionable)} already in results CSV")

    if args.limit:
        actionable = actionable[:args.limit]
        log(f"Capped at {args.limit} (--limit)")

    # ── Dry run ───────────────────────────────────────────────────────────
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
            log(f"    [{r['_strategy']:12}] {r['article_id']} → {fname}")
            log(f"                 {r['_url'][:75]}")
        if len(actionable) > 15:
            log(f"  ... and {len(actionable)-15} more")
        _log_fh.close()
        return

    # ── Download loop ─────────────────────────────────────────────────────
    log(f"\nStarting downloads: {len(actionable)} files\n")
    counters = Counter()

    # Deduplication: track url → dest_path for files already downloaded this run.
    # When a second ART-ID maps to the same URL, copy the file instead of
    # re-downloading (same bytes, different codon filename).
    url_to_dest: dict = {}

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

        # Select auth session and resolve final URL for gated domains
        auth_session = None

        if strategy == "nejm_auth":
            auth_session = nejm_session

        elif strategy == "jama_auth":
            auth_session = jama_session
            # JAMA: fetch article page to extract actual PDF download link
            resolved = jama_resolve_pdf_url(url, jama_session)
            if resolved != url:
                log(f"    Resolved PDF link: {resolved[:75]}")
                url = resolved

        # Dedup check: same URL already downloaded this run → copy instead of fetch
        if url in url_to_dest and url_to_dest[url].exists():
            existing = url_to_dest[url]
            try:
                dest.parent.mkdir(parents=True, exist_ok=True)
                import shutil as _shutil
                _shutil.copy2(existing, dest)
                nbytes = dest.stat().st_size
                kb = nbytes // 1024
                log(f"    ✓ copied from {existing.name} ({kb} KB) [dedup]")
                counters["downloaded"] += 1
                append_result({
                    "article_id":     art_id,
                    "tier":           row.get("tier"),
                    "classification": row.get("classification"),
                    "strategy":       strategy + "_dedup",
                    "status":         "ok",
                    "bytes":          nbytes,
                    "dest_filename":  fname,
                    "url_used":       url,
                    "title":          row.get("title", ""),
                    "author1":        row.get("author1", ""),
                    "year":           row.get("year", ""),
                    "source_type":    row.get("source_type", ""),
                })
                time.sleep(0.1)   # no rate limit needed for a copy
                continue
            except Exception as e:
                log(f"    [dedup copy failed: {e}] — falling through to download")

        success, status, nbytes = download_pdf(
            url, dest,
            aafp_cookie=aafp_cookie,
            fallback_url=fallback,
            auth_session=auth_session,
        )

        if success:
            kb = nbytes // 1024
            log(f"    ✓ saved ({kb} KB)")
            counters["downloaded"] += 1
            url_to_dest[url] = dest   # register for dedup on subsequent rows
        else:
            log(f"    ✗ {status}")
            counters[status] += 1
            if dest.exists() and dest.stat().st_size == 0:
                dest.unlink()

        append_result({
            "article_id":     art_id,
            "tier":           row.get("tier"),
            "classification": row.get("classification"),
            "strategy":       strategy,
            "status":         "ok" if success else status,
            "bytes":          nbytes,
            "dest_filename":  fname if success else "",
            "url_used":       url,
            "title":          row.get("title", ""),
            "author1":        row.get("author1", ""),
            "year":           row.get("year", ""),
            "source_type":    row.get("source_type", ""),
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

    final_on_disk = len(get_art_ids_on_disk())
    log(f"\n  PDFs on disk (total): {final_on_disk}")
    log(f"  Results log: {RESULTS_CSV}")
    log(f"  Download log: {LOG_PATH}")

    _log_fh.close()


if __name__ == "__main__":
    main()
