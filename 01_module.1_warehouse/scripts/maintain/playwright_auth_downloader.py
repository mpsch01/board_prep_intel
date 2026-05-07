"""
playwright_auth_downloader.py
==============================
Downloads JAMA and NEJM PDFs using a real Playwright Chromium browser
with session cookies injected. Bypasses Cloudflare because the browser
IS Chrome — no TLS impersonation needed.

Usage:
    python playwright_auth_downloader.py --journal nejm       # NEJM only
    python playwright_auth_downloader.py --journal jama       # JAMA only
    python playwright_auth_downloader.py                      # both
    python playwright_auth_downloader.py --dry-run            # preview only
    python playwright_auth_downloader.py --limit 5            # cap for testing
    python playwright_auth_downloader.py --headful            # show browser (debug)

Reads:
    key_data_files/cookies/  →  JAMA and NEJM cookie files (Cookie-Editor JSON)
    scripts/maintain/exa_pdf_queue.csv  →  article queue (classification + URLs)
    scripts/maintain/exa_download_results.csv  →  skips already-downloaded

Output:
    citation_files/ITE/{tier}/  →  codon-named PDFs
    scripts/maintain/playwright_download_results.csv
    scripts/maintain/playwright_download.log
"""

import os, re, csv, json, time, argparse, sys
from pathlib import Path
from datetime import datetime
from collections import Counter

# ── Paths ──────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
PDF_ROOT     = PROJECT_ROOT / "01_module.1_warehouse" / "citation_files" / "ITE"
QUEUE_CSV    = SCRIPT_DIR / "exa_pdf_queue.csv"
PREV_RESULTS = SCRIPT_DIR / "exa_download_results.csv"
RESULTS_CSV  = SCRIPT_DIR / "playwright_download_results.csv"
LOG_PATH     = SCRIPT_DIR / "playwright_download.log"
COOKIE_DIR   = PROJECT_ROOT / "key_data_files" / "cookies"

# ── Settings ───────────────────────────────────────────────────────────────
RATE_LIMIT_SEC = 2.5
TIMEOUT_MS     = 45_000     # 45s page/response timeout
MAX_PDF_MB     = 50
MIN_PDF_BYTES  = 1024

# ── Codon regex ────────────────────────────────────────────────────────────
CODON_RE = re.compile(r'#@#(ART-\d+)@#@')

# ── Logging ────────────────────────────────────────────────────────────────
_log_fh = None

def log(msg):
    print(msg, flush=True)
    if _log_fh:
        _log_fh.write(msg + "\n")
        _log_fh.flush()


# ── Cookie loader ──────────────────────────────────────────────────────────

def find_cookie_file(label_lower):
    if not COOKIE_DIR.exists():
        return None
    matches = [
        f for f in COOKIE_DIR.iterdir()
        if label_lower in f.name.lower() and f.suffix.lower() in (".json", ".txt")
    ]
    if not matches:
        return None
    return max(matches, key=lambda f: f.stat().st_mtime)


def load_cookies(label):
    """Load Cookie-Editor JSON export. Returns list of cookie dicts or []."""
    cookie_file = find_cookie_file(label.lower())
    if not cookie_file:
        log(f"  ✗ {label}: no cookie file found in {COOKIE_DIR}")
        return []
    with open(cookie_file, encoding="utf-8") as f:
        cookies = json.load(f)
    log(f"  ✓ {label}: {len(cookies)} cookies from {cookie_file.name}")
    return cookies


def cookies_to_playwright(cookies, default_domain):
    """
    Convert Cookie-Editor format to Playwright add_cookies() format.
    Playwright requires: name, value, domain, path.
    """
    pw_cookies = []
    for c in cookies:
        domain = c.get("domain", default_domain)
        # Playwright needs domain without leading dot for exact match,
        # or with leading dot for subdomain matching.
        # Cookie-Editor may export ".nejm.org" — keep as-is, Playwright handles it.
        pw_cookies.append({
            "name":   c["name"],
            "value":  c["value"],
            "domain": domain if domain else default_domain,
            "path":   c.get("path", "/"),
        })
    return pw_cookies


# ── URL handling ───────────────────────────────────────────────────────────

def nejm_to_pdf_url(url):
    """Convert NEJM article URL to direct PDF URL."""
    # Already a PDF URL — pass through (strip query params that cause issues)
    if "/doi/pdf/" in url:
        return url.split("?")[0]
    # /doi/full/ or /doi/abs/ → /doi/pdf/
    for seg in ["/doi/full/", "/doi/abs/"]:
        if seg in url:
            return url.replace(seg, "/doi/pdf/").split("?")[0]
    # Bare /doi/10.xxxx pattern — insert /pdf/
    m = re.search(r'(https?://(?:www\.)?nejm\.org)/doi/(10\.\d+/\S+)', url)
    if m:
        doi = m.group(2).split("?")[0].rstrip("/")
        return f"{m.group(1)}/doi/pdf/{doi}"
    return url


def is_jama_url(url):
    return "jamanetwork.com" in url.lower()

def is_nejm_url(url):
    return "nejm.org" in url.lower()


# ── Filename helpers ───────────────────────────────────────────────────────

def make_codon_filename(row):
    author     = (row.get("author1") or "Unknown").strip()
    author_1st = re.split(r'[\s,;/]', author)[0]
    author_safe = re.sub(r'[^\w\-]', '', author_1st) or "Unknown"
    year   = str(row.get("year") or "0000").strip()
    art_id = row.get("article_id", "ART-0000")
    return f"{author_safe}_{year}#@#{art_id}@#@.pdf"

def dest_folder(row):
    return PDF_ROOT / row.get("tier", "VC_fail")


# ── On-disk scanner ────────────────────────────────────────────────────────

def get_art_ids_on_disk():
    found = set()
    if not PDF_ROOT.exists():
        return found
    for f in PDF_ROOT.rglob("*.pdf"):
        m = CODON_RE.search(f.name)
        if m:
            found.add(m.group(1))
    return found


def load_prev_downloaded():
    """ART-IDs already marked ok in exa_download_results.csv."""
    done = set()
    if not PREV_RESULTS.exists():
        return done
    with open(PREV_RESULTS, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("status") == "ok":
                done.add(row.get("article_id", ""))
    return done


# ── Queue loader ───────────────────────────────────────────────────────────

def load_targets(journal_filter):
    """
    Load rows from exa_pdf_queue.csv that belong to the requested journal(s).
    Returns list of dicts with resolved download URL attached as _url.
    """
    if not QUEUE_CSV.exists():
        log(f"ERROR: {QUEUE_CSV} not found")
        return []

    rows = []
    with open(QUEUE_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            url = row.get("top_url", "")
            if not url:
                continue
            want_nejm = (journal_filter in ("nejm", "both")) and is_nejm_url(url)
            want_jama = (journal_filter in ("jama", "both")) and is_jama_url(url)
            if not (want_nejm or want_jama):
                continue
            # Resolve to PDF URL
            if want_nejm:
                row["_url"]     = nejm_to_pdf_url(url)
                row["_journal"] = "nejm"
            else:
                row["_url"]     = url   # JAMA: fetch article page first in browser
                row["_journal"] = "jama"
            rows.append(row)
    return rows


# ── Results writer ─────────────────────────────────────────────────────────

def append_result(data):
    fields = ["article_id", "tier", "journal", "status", "bytes",
              "dest_filename", "url_used", "title", "author1", "year"]
    write_header = not RESULTS_CSV.exists()
    with open(RESULTS_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        if write_header:
            w.writeheader()
        w.writerow(data)


# ── Playwright download ────────────────────────────────────────────────────

def download_with_playwright(targets, nejm_cookies, jama_cookies, headful, dry_run):
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    except ImportError:
        log("ERROR: playwright not installed. Run: pip install playwright && playwright install chromium")
        return Counter()

    counters  = Counter()
    on_disk   = get_art_ids_on_disk()
    prev_done = load_prev_downloaded()

    # Filter already-done
    targets = [r for r in targets if r["article_id"] not in on_disk]
    targets = [r for r in targets if r["article_id"] not in prev_done]
    log(f"\n  After dedup filter: {len(targets)} targets remain\n")

    if dry_run:
        log(f"🔍 Dry run — {len(targets)} files would be downloaded:")
        by_journal = Counter(r["_journal"] for r in targets)
        for j, n in by_journal.items():
            log(f"  {j}: {n}")
        log("\n  First 15:")
        for r in targets[:15]:
            log(f"  [{r['_journal']:4}] {r['article_id']} {make_codon_filename(r)}")
            log(f"         {r['_url'][:80]}")
        return counters

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headful)

        # ── NEJM context ──────────────────────────────────────────────────
        nejm_context = None
        if nejm_cookies:
            nejm_context = browser.new_context(
                accept_downloads=True,
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
            )
            try:
                nejm_context.add_cookies(cookies_to_playwright(nejm_cookies, ".nejm.org"))
                log("  ✓ NEJM context: cookies injected")
            except Exception as e:
                log(f"  ⚠  NEJM cookie inject warning: {e}")

        # ── JAMA context ──────────────────────────────────────────────────
        jama_context = None
        if jama_cookies:
            jama_context = browser.new_context(
                accept_downloads=True,
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
            )
            try:
                jama_context.add_cookies(cookies_to_playwright(jama_cookies, ".jamanetwork.com"))
                log("  ✓ JAMA context: cookies injected")
            except Exception as e:
                log(f"  ⚠  JAMA cookie inject warning: {e}")

        log("")
        total = len(targets)

        for i, row in enumerate(targets, 1):
            art_id  = row["article_id"]
            journal = row["_journal"]
            url     = row["_url"]
            fname   = make_codon_filename(row)
            folder  = dest_folder(row)
            dest    = folder / fname

            log(f"[{i}/{total}] {art_id} [{journal}] {(row.get('title') or '')[:55]}")
            log(f"  → {fname}")
            log(f"    {url[:85]}")

            ctx = nejm_context if journal == "nejm" else jama_context
            if ctx is None:
                log(f"    ✗ no context for {journal} — skipped")
                counters["skipped"] += 1
                append_result({**row, "journal": journal, "status": "skipped",
                               "bytes": 0, "dest_filename": fname, "url_used": url})
                continue

            try:
                page = ctx.new_page()

                if journal == "jama":
                    # For JAMA: navigate to article page, find PDF link, then download
                    page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT_MS)
                    time.sleep(1)

                    # Try to find /article-pdf/ link in page
                    pdf_link = page.evaluate("""() => {
                        const links = Array.from(document.querySelectorAll('a[href]'));
                        const pdf = links.find(a =>
                            a.href.includes('/article-pdf/') ||
                            (a.href.toLowerCase().endsWith('.pdf') &&
                             a.href.includes('jamanetwork'))
                        );
                        return pdf ? pdf.href : null;
                    }""")

                    if pdf_link:
                        log(f"    Resolved PDF link: {pdf_link[:75]}")
                        url = pdf_link

                # Two-path download strategy:
                #   Path A: expect_download() — for URLs that trigger a browser download
                #   Path B: response interception — for URLs that serve PDF inline
                # Both run simultaneously; whichever delivers a valid PDF wins.

                folder.mkdir(parents=True, exist_ok=True)
                captured_pdf: list = []   # filled by response listener

                def _on_response(response):
                    if response.status == 200 and not captured_pdf:
                        ct = response.headers.get("content-type", "").lower()
                        if "pdf" in ct or "octet-stream" in ct:
                            try:
                                body = response.body()
                                if body[:4] == b"%PDF":
                                    captured_pdf.append(body)
                            except Exception:
                                pass

                page.on("response", _on_response)

                tmp_path  = dest.parent / (fname + ".tmp")
                pdf_bytes = None

                try:
                    with page.expect_download(timeout=15_000) as dl_info:
                        try:
                            page.goto(url, wait_until="domcontentloaded",
                                      timeout=TIMEOUT_MS)
                        except Exception as nav_err:
                            if "Download is starting" not in str(nav_err):
                                raise
                    # Path A: download event fired
                    dl_info.value.save_as(str(tmp_path))
                    if tmp_path.exists() and tmp_path.stat().st_size > MIN_PDF_BYTES:
                        pdf_bytes = tmp_path.read_bytes()
                        tmp_path.unlink(missing_ok=True)
                        log(f"    [download event]")

                except PWTimeout:
                    # Path B: no download — check response listener
                    if captured_pdf:
                        pdf_bytes = captured_pdf[0]
                        log(f"    [response intercept]")
                    else:
                        # Path C: navigate to article page and find PDF button
                        log(f"    [trying article page for PDF link]")
                        try:
                            page.goto(url.replace("/doi/pdf/", "/doi/full/"),
                                      wait_until="domcontentloaded", timeout=TIMEOUT_MS)
                            time.sleep(1)
                            pdf_link = page.evaluate("""() => {
                                const a = document.querySelector('a[href*="/doi/pdf/"]');
                                return a ? a.href : null;
                            }""")
                            if pdf_link:
                                log(f"    Found PDF link: {pdf_link[:70]}")
                                with page.expect_download(timeout=20_000) as dl2:
                                    try:
                                        page.goto(pdf_link, wait_until="domcontentloaded",
                                                  timeout=TIMEOUT_MS)
                                    except Exception as e2:
                                        if "Download is starting" not in str(e2):
                                            raise
                                dl2.value.save_as(str(tmp_path))
                                if tmp_path.exists() and tmp_path.stat().st_size > MIN_PDF_BYTES:
                                    pdf_bytes = tmp_path.read_bytes()
                                    tmp_path.unlink(missing_ok=True)
                                    log(f"    [article page fallback]")
                        except Exception as path_c_err:
                            log(f"    Path C failed: {path_c_err}")

                # ── Validate and save ─────────────────────────────────────
                if not pdf_bytes:
                    log(f"    ✗ No PDF captured")
                    page.close()
                    counters["failed"] += 1
                    append_result({**row, "journal": journal, "status": "no_pdf",
                                   "bytes": 0, "dest_filename": fname, "url_used": url})
                    time.sleep(RATE_LIMIT_SEC)
                    continue

                if pdf_bytes[:4] != b"%PDF":
                    log(f"    ✗ Not a PDF ({len(pdf_bytes)} bytes)")
                    page.close()
                    counters["failed"] += 1
                    append_result({**row, "journal": journal, "status": "not_pdf",
                                   "bytes": len(pdf_bytes), "dest_filename": fname, "url_used": url})
                    time.sleep(RATE_LIMIT_SEC)
                    continue

                if len(pdf_bytes) < MIN_PDF_BYTES:
                    log(f"    ✗ Too small: {len(pdf_bytes)} bytes")
                    page.close()
                    counters["failed"] += 1
                    append_result({**row, "journal": journal, "status": "too_small",
                                   "bytes": len(pdf_bytes), "dest_filename": fname, "url_used": url})
                    time.sleep(RATE_LIMIT_SEC)
                    continue

                if len(pdf_bytes) > MAX_PDF_MB * 1024 * 1024:
                    log(f"    ✗ Too large: {len(pdf_bytes) // 1024 // 1024} MB")
                    page.close()
                    counters["failed"] += 1
                    append_result({**row, "journal": journal, "status": "too_large",
                                   "bytes": len(pdf_bytes), "dest_filename": fname, "url_used": url})
                    time.sleep(RATE_LIMIT_SEC)
                    continue

                dest.write_bytes(pdf_bytes)
                kb = len(pdf_bytes) // 1024
                log(f"    ✓ {kb} KB saved")
                counters["downloaded"] += 1
                append_result({**row, "journal": journal, "status": "ok",
                               "bytes": len(pdf_bytes), "dest_filename": fname, "url_used": url})
                page.close()

            except PWTimeout:
                log(f"    ✗ Timeout")
                counters["failed"] += 1
                append_result({**row, "journal": journal, "status": "timeout",
                               "bytes": 0, "dest_filename": fname, "url_used": url})
                try:
                    page.close()
                except Exception:
                    pass

            except Exception as e:
                log(f"    ✗ Error: {e}")
                counters["failed"] += 1
                append_result({**row, "journal": journal, "status": "error",
                               "bytes": 0, "dest_filename": fname, "url_used": url})
                try:
                    page.close()
                except Exception:
                    pass

            time.sleep(RATE_LIMIT_SEC)

        if nejm_context:
            nejm_context.close()
        if jama_context:
            jama_context.close()
        browser.close()

    return counters


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    global _log_fh

    parser = argparse.ArgumentParser()
    parser.add_argument("--journal",  default="both",
                        choices=["nejm", "jama", "both"])
    parser.add_argument("--limit",   type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--headful", action="store_true",
                        help="Show the browser window (useful for debugging)")
    args = parser.parse_args()

    _log_fh = open(LOG_PATH, "w", encoding="utf-8")
    log(f"=== playwright_auth_downloader.py — {datetime.now().isoformat()} ===")
    log(f"journal={args.journal}  limit={args.limit}  dry_run={args.dry_run}  headful={args.headful}\n")

    # Load cookies
    nejm_cookies = load_cookies("nejm") if args.journal in ("nejm", "both") else []
    jama_cookies = load_cookies("jama") if args.journal in ("jama", "both") else []

    if not nejm_cookies and not jama_cookies:
        log("ERROR: No cookie files found. Export from Chrome using Cookie-Editor.")
        _log_fh.close()
        return

    # Load targets
    targets = load_targets(args.journal)
    log(f"\nTargets from queue: {len(targets)}")

    by_j = Counter(r["_journal"] for r in targets)
    for j, n in by_j.items():
        log(f"  {j}: {n}")

    if args.limit:
        targets = targets[:args.limit]
        log(f"Capped at {args.limit} (--limit)")

    # Run
    counters = download_with_playwright(targets, nejm_cookies, jama_cookies,
                                        args.headful, args.dry_run)

    if not args.dry_run:
        log(f"\n{'═'*50}")
        log(f"📦 Playwright Download Summary")
        log(f"{'═'*50}")
        log(f"  ✓ downloaded:  {counters['downloaded']:4}")
        log(f"  ✗ failed:      {counters['failed']:4}")
        log(f"  ✗ skipped:     {counters['skipped']:4}")
        log(f"  Results: {RESULTS_CSV}")

    _log_fh.close()


if __name__ == "__main__":
    main()
