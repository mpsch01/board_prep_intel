#!/usr/bin/env python3
"""
AAFP Targeted Downloader
========================
Downloads PDFs for a targeted list of AFP-source DB articles using a manually
authenticated Playwright browser session.

Workflow per article:
  1. AAFP site search by title -> find article landing page URL
  2. Navigate to landing page, read citation_pdf_url meta tag
  3. context.request.get(pdf_url) fetches PDF bytes via the authenticated session
  4. Save with codon filename to VC_fail/

Usage:
  python aafp_targeted_downloader.py                     # all 79 missing AFP
  python aafp_targeted_downloader.py --limit 10          # cap for testing
  python aafp_targeted_downloader.py --year 2024         # only one year

Browser opens, you log in, press ENTER, downloads run.
"""

import os
import re
import sys
import sqlite3
import argparse
import time
import json
from pathlib import Path
from urllib.parse import quote_plus

from difflib import SequenceMatcher

import requests
from playwright.sync_api import sync_playwright

SCRIPT_DIR    = Path(__file__).resolve().parent
PROJECT_ROOT  = SCRIPT_DIR.parent.parent.parent
DB_PATH       = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"
WAREHOUSE     = PROJECT_ROOT / "01_module.1_warehouse" / "citation_files" / "ITE"
DEST_DIR      = WAREHOUSE / "VC_fail"
LOG_PATH      = SCRIPT_DIR / "_aafp_targeted_log.json"
AUTH_PATH     = SCRIPT_DIR / "_aafp_auth.json"  # gitignored; persisted login state

CODON_RE = re.compile(r'#@#(ART-\d+)@#@')
DELAY    = 1.5
TITLE_MATCH_THRESHOLD = 0.55  # SequenceMatcher ratio between landing-page citation_title and DB title

# AAFP biweekly issue → MMDD mapping. Pre-2021 AFP published biweekly with TWO
# volumes per year (each spans 6 months). Volume parity determines which half:
#   ODD volume  (e.g. 87, 99, 101)  → Jan-Jun, issue 1 = Jan 1, issue 12 = Jun 15
#   EVEN volume (e.g. 100, 102, 108) → Jul-Dec, issue 1 = Jul 1, issue 12 = Dec 15
# Examples confirmed against live AAFP URLs:
#   Hainer 2013 vol 87 (odd) issue 10  → 05/15  ✓ /pubs/afp/issues/2013/0515/p682
#   Pyzocha 2020 vol 102 (even) issue 9 → 11/01 ✓ /pubs/afp/issues/2020/1101/p571
def issue_to_mmdd(issue_num, volume=None):
    if volume is not None and int(volume) % 2 == 0:
        month = 7 + (issue_num - 1) // 2  # even vol = Jul-Dec
    else:
        month = (issue_num + 1) // 2      # odd vol = Jan-Jun
    day = 1 if issue_num % 2 == 1 else 15
    return f"{month:02d}{day:02d}"

# Parse clean_ref like "Am Fam Physician. 2024;110(1):45-51." -> (year, volume, issue, page)
CITATION_RE = re.compile(
    r'Am\.?\s*Fam\.?\s*Physician\.?\s*(\d{4})\s*[;:]\s*(\d+)\s*\(\s*(\d+)\s*\)\s*:\s*(\d+)',
    re.IGNORECASE,
)
def parse_afp_citation(clean_ref):
    if not clean_ref:
        return (None, None, None, None)
    m = CITATION_RE.search(clean_ref)
    if not m:
        return (None, None, None, None)
    return (m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4)))


# Extract the actual article title from clean_ref. DB title is unreliable for
# many older AFP entries (junk values like "Online", "402", "what you should know").
TITLE_FROM_REF_RE = re.compile(r'(.+?)\s*Am\.?\s*Fam\.?\s*Physician', re.IGNORECASE)
def extract_title_from_ref(clean_ref):
    if not clean_ref:
        return None
    m = TITLE_FROM_REF_RE.search(clean_ref)
    if not m:
        return None
    pre = m.group(1).strip().rstrip('.').rstrip(',').strip()
    # Strip author list — split on first ". " or ": " separating authors from title.
    # Common patterns:
    #   "Lastname I, Lastname I. Title."  -> split at ". "
    #   "Lastname I: Title."              -> split at ": "
    parts = re.split(r'(?:\.\s+|\:\s+)', pre, maxsplit=1)
    if len(parts) > 1:
        candidate = parts[1].strip().rstrip('.').rstrip(',').strip()
        # Only use the split if the result is reasonably long
        if len(candidate) >= 10:
            return candidate
    return pre if len(pre) >= 10 else None


def load_targets(args):
    on_disk = set()
    for tier in ['VC_fail','VC_pass','local_lite','right_click']:
        for p in (WAREHOUSE/tier).glob('*.pdf'):
            m = CODON_RE.search(p.name)
            if m: on_disk.add(m.group(1))

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT article_id, author1, year, title, codon_filename, clean_ref
        FROM articles
        WHERE source_type='AFP' AND (citation_only=0 OR citation_only IS NULL)
        ORDER BY year DESC, article_id
    """)
    rows = cur.fetchall()
    conn.close()

    missing = []
    for aid, a1, yr, title, codon, ref in rows:
        if aid in on_disk:
            continue
        if args.year and str(yr) != str(args.year):
            continue
        if not codon:
            codon = f"{(a1 or 'Unknown').replace(' ', '')}_{yr}#@#{aid}@#@.pdf"
        ref_year, ref_volume, ref_issue, ref_page = parse_afp_citation(ref or '')
        ref_title = extract_title_from_ref(ref or '')
        missing.append({
            'article_id': aid,
            'author1': a1,
            'year': str(yr),
            'title': title or '',
            'ref_title': ref_title or '',
            'codon': codon,
            'clean_ref': ref or '',
            'ref_year': ref_year,
            'ref_volume': ref_volume,
            'ref_issue': ref_issue,
            'ref_page': ref_page,
        })

    if args.limit:
        missing = missing[:args.limit]
    return missing


_TOC_CACHE = {}  # (year, month) -> list of {title, url} dicts

def fetch_toc(page, year, month, log):
    """Fetch one issue TOC page; return list of {title, url} dicts."""
    key = (year, month)
    if key in _TOC_CACHE:
        return _TOC_CACHE[key]

    # Try new format first (2018+); fall back to legacy if needed
    url_new = f"https://www.aafp.org/pubs/afp/issues/{year}/{month:02d}00.html"
    url_old = f"https://www.aafp.org/afp/{year}/{month:02d}00.html"

    articles = []
    for toc_url in (url_new, url_old):
        try:
            page.goto(toc_url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(0.5)
            # Grab article links from "Articles" / TOC region
            entries = page.evaluate("""
                () => {
                    const out = [];
                    document.querySelectorAll('a[href]').forEach(a => {
                        const href = a.href;
                        // Match issue article URLs (any slug)
                        if (/aafp\\.org\\/(pubs\\/afp\\/issues|afp)\\/\\d{4}\\/\\d{4}\\/[a-z0-9-]+\\.html/i.test(href)) {
                            const txt = (a.innerText || a.textContent || '').trim();
                            if (txt && txt.length > 3) {
                                out.push({title: txt, url: href});
                            }
                        }
                    });
                    return out;
                }
            """)
            if entries:
                # Dedupe by URL, prefer the longest title for that URL
                by_url = {}
                for e in entries:
                    if e['url'] not in by_url or len(e['title']) > len(by_url[e['url']]['title']):
                        by_url[e['url']] = e
                articles = list(by_url.values())
                break
        except Exception as e:
            log(f"      TOC fetch failed for {toc_url}: {str(e)[:80]}")

    _TOC_CACHE[key] = articles
    return articles


def try_direct_legacy_url(page, item, log):
    """Multi-pattern URL guess: /pubs/afp/issues/{YYYY}/{MMDD-or-MM00}/p{page}.html
    Tries several MMDD candidates per article (biweekly + monthly) — AAFP's
    publishing schedule changed between 2013 (biweekly) and 2021+ (monthly),
    and we don't know exactly when. Validation gate filters to the right one.
    Returns the article URL if any candidate passes validation, else None.
    """
    yr = item.get('ref_year') or item['year']
    issue = item.get('ref_issue')
    pg = item.get('ref_page')
    if not (yr and issue and pg):
        return None

    # Build candidate MMDD strings to try (deduped, ordered by likelihood):
    candidates = []
    vol = item.get('ref_volume')

    # Primary: biweekly with correct volume parity (pre-2021 articles)
    if vol:
        candidates.append(issue_to_mmdd(issue, vol))
    # Also try without volume parity in case our parity guess is wrong
    candidates.append(issue_to_mmdd(issue))           # odd-volume default
    candidates.append(issue_to_mmdd(issue, 2))        # force even-volume mapping

    # Monthly fallback (2021+ articles that retained p{page} slug)
    if 1 <= issue <= 12:
        candidates.append(f"{issue:02d}00")
    if 1 <= issue <= 6:
        candidates.append(f"{(issue + 6):02d}00")
    if 7 <= issue <= 12:
        candidates.append(f"{(issue - 6):02d}00")

    seen = set()
    deduped = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            deduped.append(c)

    for mmdd in deduped:
        cand_url = f"https://www.aafp.org/pubs/afp/issues/{yr}/{mmdd}/p{pg}.html"
        log(f"      legacy direct: {cand_url}")
        meta = fetch_article_metadata(page, cand_url, log)
        if validate_via_meta(meta, item):
            log(f"      VALIDATED via meta (vol={meta.get('volume')} iss={meta.get('issue')} pg={meta.get('firstpage')})")
            return cand_url
        landing_title = meta.get('title')
        if landing_title and title_matches(landing_title, item['title'], item.get('ref_title')):
            log(f"      VALIDATED via title: '{landing_title[:60]}'")
            return cand_url
        # Diagnostic: log only on first attempt to avoid log spam
        if mmdd == deduped[0]:
            if landing_title:
                log(f"        first attempt meta: title='{landing_title[:60]}' vol={meta.get('volume')!r} iss={meta.get('issue')!r} pg={meta.get('firstpage')!r}")
            elif any(meta.values()):
                log(f"        first attempt: partial meta (no title)")
            else:
                log(f"        first attempt: no meta (404 or empty)")
    return None


def find_via_crossref(page, item, log):
    """Tier-3 fallback: query CrossRef API for the article's DOI, then navigate
    to the doi.org URL (which redirects to the publisher's canonical URL).
    Useful when clean_ref is malformed (e.g., 'Online' / 'On' page placeholders)
    or when AAFP retired the URL we'd otherwise construct."""
    title = item.get('ref_title') or item.get('title') or ''
    title = title.strip()
    if not title or len(title) < 8:
        return None
    author = (item.get('author1') or '').strip()
    yr = item.get('ref_year') or item['year']

    params = {
        'query.bibliographic': f'{title} {author}'.strip(),
        'query.container-title': 'American Family Physician',
        'rows': 5,
    }
    if yr:
        params['filter'] = f'from-pub-date:{yr}-01-01,until-pub-date:{yr}-12-31'

    try:
        r = requests.get(
            'https://api.crossref.org/works',
            params=params,
            timeout=15,
            headers={'User-Agent': 'board_prep_intel AFP article finder (mailto:noreply@local)'},
        )
        if r.status_code != 200:
            log(f"      crossref HTTP {r.status_code}")
            return None
        items = r.json().get('message', {}).get('items', [])
    except Exception as e:
        log(f"      crossref lookup error: {str(e)[:80]}")
        return None

    if not items:
        log(f"      crossref: no results")
        return None

    # Pick the best title match
    best = None
    best_score = 0.0
    for crf in items:
        crf_titles = crf.get('title', []) or []
        crf_title = ' '.join(crf_titles)
        ratio = SequenceMatcher(None, crf_title.lower(), title.lower()).ratio()
        if ratio > best_score:
            best_score = ratio
            best = crf
    if not best or best_score < 0.50:
        log(f"      crossref: no good title match (best ratio={best_score:.2f})")
        return None

    doi = best.get('DOI')
    pub_url = best.get('URL') or (f"https://doi.org/{doi}" if doi else None)
    if not pub_url:
        log(f"      crossref: hit but no resolvable URL")
        return None
    log(f"      crossref hit: DOI={doi}  ratio={best_score:.2f}")

    # Navigate to the publisher URL via Playwright (auth context; redirects followed)
    try:
        page.goto(pub_url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(1.0)
        final_url = page.url
        if 'aafp.org' not in final_url:
            log(f"      crossref redirect did not land on aafp.org (got {final_url[:80]})")
            return None
        return final_url
    except Exception as e:
        log(f"      crossref redirect failed: {str(e)[:80]}")
        return None


def find_article_in_year(page, item, log):
    """Search all months of the article's year via TOC scrape; return URL or None."""
    yr = int(item.get('ref_year') or item['year'])
    title = item['title']
    ref_title = item.get('ref_title') or ''
    if not title and not ref_title:
        return None
    # Page numbers in AFP run sequentially through the year — use page to bias month order
    # but try all months as fallback
    months = list(range(1, 13))
    best_url = None
    best_title = None
    best_month = None
    best_score = 0.0
    for mo in months:
        toc = fetch_toc(page, yr, mo, log)
        for entry in toc:
            entry_lc = entry['title'].lower()
            r1 = SequenceMatcher(None, entry_lc, (title or '').lower()).ratio() if title else 0.0
            r2 = SequenceMatcher(None, entry_lc, ref_title.lower()).ratio() if ref_title else 0.0
            ratio = max(r1, r2)
            if ratio > best_score:
                best_score = ratio
                best_url = entry['url']
                best_title = entry['title']
                best_month = mo
        # Early-exit on strong match
        if best_score >= 0.85:
            log(f"      strong match in {yr}/{best_month:02d}: '{best_title[:60]}' (ratio={best_score:.2f})")
            return best_url
    if best_score >= 0.55:
        log(f"      best match in {yr}/{best_month:02d} (ratio={best_score:.2f}): '{best_title[:60]}'")
        return best_url
    return None


def fetch_article_metadata(page, article_url, log):
    """Navigate to article page; return dict with title/pdf_url/volume/issue/firstpage/doi.
    Empty dict on error."""
    try:
        page.goto(article_url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(0.5)
        meta = page.evaluate("""
            () => {
                const get = (n) => document.querySelector(`meta[name="${n}"]`)?.content || '';
                return {
                    title:     get('citation_title'),
                    pdf_url:   get('citation_pdf_url'),
                    volume:    get('citation_volume'),
                    issue:     get('citation_issue'),
                    firstpage: get('citation_firstpage'),
                    doi:       get('citation_doi'),
                };
            }
        """)
        return meta or {}
    except Exception as e:
        log(f"      fetch_article_metadata failed: {e}")
        return {}


def validate_via_meta(meta, item):
    """Structured validation: compare volume+issue+firstpage from page meta to clean_ref.
    Returns True only if all three match exactly. Most reliable signal — bypasses
    fuzzy title matching entirely when AAFP exposes the citation meta tags."""
    if not meta:
        return False
    rv = item.get('ref_volume')
    ri = item.get('ref_issue')
    rp = item.get('ref_page')
    if not (rv and ri and rp):
        return False
    try:
        mv = int(str(meta.get('volume','') or '').strip()) if meta.get('volume') else None
        mi = int(str(meta.get('issue','') or '').strip()) if meta.get('issue') else None
        mp = int(str(meta.get('firstpage','') or '').strip()) if meta.get('firstpage') else None
    except (ValueError, TypeError):
        return False
    if mv is None or mi is None or mp is None:
        return False
    return mv == int(rv) and mi == int(ri) and mp == int(rp)


def title_matches(landing_title, db_title, ref_title=None):
    """Validate the landing page is the article we expected.
    Accept if EITHER the DB title OR the clean_ref-extracted title matches.
    Falls back gracefully when DB title is unreliable (junk values like 'Online', '402')."""
    if not landing_title:
        return False
    a = landing_title.lower().strip()[:120]
    candidates = [t for t in (db_title, ref_title) if t and len(t) >= 5]
    for cand in candidates:
        b = cand.lower().strip()[:120]
        if SequenceMatcher(None, a, b).ratio() >= TITLE_MATCH_THRESHOLD:
            return True
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--year",  type=str, default=None)
    parser.add_argument("--dry-run", action="store_true",
                        help="Show plan without opening browser")
    parser.add_argument("--clear-auth", action="store_true",
                        help="Delete saved auth state, force fresh login")
    args = parser.parse_args()

    if args.clear_auth and AUTH_PATH.exists():
        AUTH_PATH.unlink()
        print(f"Deleted {AUTH_PATH.name}")

    targets = load_targets(args)
    print(f"\n=== {len(targets)} missing AFP articles to attempt ===")
    if args.dry_run:
        for t in targets:
            print(f"  {t['article_id']}  {t['author1']} {t['year']}  {t['title'][:60]}")
        return

    if not targets:
        print("Nothing to do.")
        return

    DEST_DIR.mkdir(parents=True, exist_ok=True)
    results = {'ok': [], 'no_search_hit': [], 'no_pdf_url': [], 'http_error': [],
               'not_pdf': [], 'title_mismatch': [], 'exception': []}

    log_lines = []
    def log(msg):
        print(msg)
        log_lines.append(msg)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        ctx_kwargs = dict(
            accept_downloads=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        # Reuse saved auth if present
        used_saved_auth = False
        if AUTH_PATH.exists():
            try:
                ctx_kwargs["storage_state"] = str(AUTH_PATH)
                used_saved_auth = True
            except Exception as e:
                print(f"Saved auth load failed ({e}); will prompt manual login.")

        context = browser.new_context(**ctx_kwargs)
        page = context.new_page()

        if used_saved_auth:
            # Verify the session is still valid by hitting a known authenticated page
            page.goto("https://www.aafp.org/pubs/afp.html",
                      wait_until="domcontentloaded", timeout=30000)
            time.sleep(1.0)
            current_url = page.url
            if "login" in current_url.lower():
                print("\nSaved auth appears to be expired. Falling back to manual login.")
                used_saved_auth = False

        if not used_saved_auth:
            page.goto("https://www.aafp.org/",
                      wait_until="domcontentloaded", timeout=30000)
            print("\n" + "="*65)
            print("  LOG IN to AAFP in the browser window that opened.")
            print("  (Click 'Sign In' on the homepage.)")
            print("  Once fully logged in, come back and press ENTER.")
            print("="*65)
            input("\n  Press ENTER when logged in >>> ")
            time.sleep(2)
            try:
                context.storage_state(path=str(AUTH_PATH))
                print(f"Saved auth state -> {AUTH_PATH.name} (skip login next run)")
            except Exception as e:
                print(f"Could not save auth state: {e}")
        else:
            print(f"\nUsing saved auth ({AUTH_PATH.name}); skipping login prompt.")

        for i, item in enumerate(targets, 1):
            aid = item['article_id']
            codon = item['codon']
            dest_path = DEST_DIR / codon
            log(f"\n[{i:3d}/{len(targets)}] {aid}  {item['author1']} {item['year']}")
            log(f"      title: {item['title'][:80]}")

            if dest_path.exists():
                log(f"      SKIP (already on disk: {codon})")
                results['ok'].append({'article_id': aid, 'codon': codon, 'note': 'already_on_disk'})
                continue

            try:
                article_url = None
                # Tier 1: deterministic legacy URL (cheap, ~1-4 fetches).
                # Works for pre-2021 biweekly articles when clean_ref is parseable.
                article_url = try_direct_legacy_url(page, item, log)
                # Tier 2: TOC scrape (works for 2020+ with title slugs)
                if not article_url:
                    article_url = find_article_in_year(page, item, log)
                # Tier 3: CrossRef DOI lookup (handles malformed clean_refs and URL retirements)
                if not article_url:
                    article_url = find_via_crossref(page, item, log)
                if not article_url:
                    log(f"      no match found (legacy + TOC + CrossRef) for year {item.get('ref_year') or item['year']}")
                    results['no_search_hit'].append(item)
                    continue

                # Final validation: read meta tags from landing page
                meta = fetch_article_metadata(page, article_url, log)

                # Either trust the meta tag's pdf_url, or derive .pdf from .html
                pdf_url = meta.get('pdf_url') or re.sub(r'\.html$', '.pdf', article_url)
                landing_title = meta.get('title')

                # Validation cascade: structured meta (vol/issue/page) is rock-solid;
                # title fuzzy match is fallback when meta tags missing.
                meta_ok  = validate_via_meta(meta, item)
                title_ok = title_matches(landing_title, item['title'], item.get('ref_title'))

                if not (meta_ok or title_ok):
                    log(f"      VALIDATION FAILED — landing: '{(landing_title or '')[:60]}'")
                    log(f"                       expected (db): '{item['title'][:60]}'")
                    log(f"                       expected (ref): '{(item.get('ref_title') or '')[:60]}'")
                    results['title_mismatch'].append({**item,
                                                      'article_url': article_url,
                                                      'landing_title': landing_title})
                    continue

                if meta_ok:
                    log(f"      VALIDATED via meta (vol={meta.get('volume')} iss={meta.get('issue')} pg={meta.get('firstpage')})")
                else:
                    log(f"      VALIDATED via title")
                log(f"      pdf_url: {pdf_url}")
                response = context.request.get(pdf_url, timeout=60000)
                if not response.ok:
                    log(f"      HTTP {response.status}")
                    results['http_error'].append({**item, 'pdf_url': pdf_url, 'status': response.status})
                    continue

                body = response.body()
                if not body.startswith(b'%PDF'):
                    log(f"      not a PDF ({len(body)} bytes)")
                    results['not_pdf'].append({**item, 'pdf_url': pdf_url, 'bytes': len(body)})
                    continue

                with open(dest_path, 'wb') as f:
                    f.write(body)
                size_kb = dest_path.stat().st_size // 1024
                log(f"      OK  {size_kb} KB")
                results['ok'].append({'article_id': aid, 'codon': codon, 'size_kb': size_kb,
                                      'pdf_url': pdf_url})

            except Exception as e:
                log(f"      EXCEPTION: {e}")
                results['exception'].append({**item, 'error': str(e)})

            time.sleep(DELAY)

        browser.close()

    print("\n" + "="*65)
    print("SUMMARY")
    print(f"  Downloaded:      {len([r for r in results['ok'] if r.get('size_kb')])}")
    print(f"  Already on disk: {len([r for r in results['ok'] if r.get('note')=='already_on_disk'])}")
    print(f"  No search hit:   {len(results['no_search_hit'])}")
    print(f"  No pdf_url:      {len(results['no_pdf_url'])}")
    print(f"  Title mismatch:  {len(results['title_mismatch'])}  (search returned wrong article — gate blocked save)")
    print(f"  HTTP error:      {len(results['http_error'])}")
    print(f"  Not a PDF:       {len(results['not_pdf'])}")
    print(f"  Exception:       {len(results['exception'])}")

    with open(LOG_PATH, 'w', encoding='utf-8') as f:
        json.dump({'log': log_lines, 'results': results}, f, indent=2, default=str)
    print(f"\nFull log: {LOG_PATH}")


if __name__ == "__main__":
    main()
