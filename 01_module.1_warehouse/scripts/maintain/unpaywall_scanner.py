"""
unpaywall_scanner.py — M1 Maintain
Unpaywall OA discovery + PDF download for landing_page and PMC-skipped articles.

Inputs:
  - exa_pdf_queue.csv       -> 872 landing_page rows (3-tier DOI resolution)
  - pmc_oa_results.csv      -> 162 skip rows (PMC ID -> EUtils -> DOI)

DOI Resolution (landing_page):
  Tier 1: Extract DOI from top_url regex
  Tier 2: Extract PMID from PubMed URL -> NCBI EUtils -> DOI
  Tier 3: CrossRef API by title/author/year (uses FULL titles from DB, not truncated CSV)

DOI Resolution (PMC skips):
  PMC ID -> NCBI EUtils elink (pmc->pubmed) -> PMID -> esummary -> DOI

Then: Unpaywall API -> OA PDF URL (url_for_pdf only) -> download -> codon filename -> save

Flags:
  --dry-run       resolve DOIs + call Unpaywall but don't download
  --limit N       process only first N articles
  --resume        skip ALL articles already in unpaywall_results.csv
  --retry-failed  re-process no_doi + download_failed; skip only downloaded/not_oa
  --source        'exa' | 'pmc' | 'both' (default: both)
"""

import argparse
import csv
import json
import os
import re
import sqlite3
import time
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from datetime import datetime

# --- Paths ---
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent  # maintain->scripts->M1->root

EXA_CSV      = SCRIPT_DIR / 'exa_pdf_queue.csv'
PMC_CSV      = SCRIPT_DIR / 'pmc_oa_results.csv'
RESULTS_CSV  = SCRIPT_DIR / 'unpaywall_results.csv'
PDF_BASE     = PROJECT_ROOT / '01_module.1_warehouse' / 'citation_files' / 'ITE'
LOG_FILE     = SCRIPT_DIR / 'unpaywall_scan.log'
DB_PATH      = PROJECT_ROOT / '00_database' / 'db' / 'ite_intelligence.db'

# --- Config ---
NCBI_API_KEY       = os.environ.get('NCBI_API_KEY', '')
UNPAYWALL_EMAIL    = 'scholl.michael.p@gmail.com'
CROSSREF_EMAIL     = 'scholl.michael.p@gmail.com'

NCBI_RATE          = 0.11   # seconds between NCBI calls (10/sec with key)
CROSSREF_RATE      = 0.15   # seconds between CrossRef calls
UNPAYWALL_RATE     = 0.15   # seconds between Unpaywall calls
DOWNLOAD_RATE      = 0.5    # seconds between PDF downloads
SAVE_EVERY         = 10     # flush results CSV every N articles

CROSSREF_MIN_SCORE = 30.0   # lowered from 50 - year filter handles false positives
YEAR_TOLERANCE     = 1      # accept DOI if year is within +/-1 of target

# --- Regex patterns ---
DOI_PATTERN     = re.compile(r'10\.\d{4,}/[^\s"<>]+')
PMID_PATTERN    = re.compile(r'pubmed\.ncbi\.nlm\.nih\.gov/(\d+)')
PMC_NUM_PATTERN = re.compile(r'PMC(\d+)')

# --- Logging ---
def log(msg):
    ts = datetime.now().strftime('%H:%M:%S')
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(line + '\n')

# --- HTTP helper ---
def http_get(url, timeout=15):
    """Simple GET returning parsed JSON or None on error."""
    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': f'ITE-Intelligence/1.0 (mailto:{UNPAYWALL_EMAIL})'}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode('utf-8', errors='replace'))
    except Exception:
        return None

# --- DB: full title lookup ---
def get_db_titles(article_ids):
    """Fetch full titles from articles DB table by article_id."""
    if not DB_PATH.exists() or not article_ids:
        return {}
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cur = conn.cursor()
        placeholders = ','.join('?' * len(article_ids))
        cur.execute(
            f"SELECT article_id, clean_ref FROM articles WHERE article_id IN ({placeholders})",
            list(article_ids)
        )
        titles = {row[0]: row[1] for row in cur.fetchall()}
        conn.close()
        return titles
    except Exception as e:
        log(f"  [WARN] DB title lookup failed: {e}")
        return {}

# --- Tier 1: DOI from URL ---
def doi_from_url(url):
    """Extract DOI directly from URL string."""
    m = DOI_PATTERN.search(url)
    if m:
        return m.group(0).rstrip('.,;)')
    return None

# --- Tier 2: PMID from PubMed URL -> EUtils -> DOI ---
def pmid_from_url(url):
    m = PMID_PATTERN.search(url)
    return m.group(1) if m else None

def doi_from_pmid(pmid):
    """NCBI EUtils esummary: PMID -> DOI."""
    key_param = f'&api_key={NCBI_API_KEY}' if NCBI_API_KEY else ''
    url = (f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi'
           f'?db=pubmed&id={pmid}&retmode=json{key_param}')
    time.sleep(NCBI_RATE)
    data = http_get(url)
    if not data:
        return None
    try:
        article_ids = data['result'][pmid]['articleids']
        for aid in article_ids:
            if aid.get('idtype') == 'doi':
                return aid['value']
    except (KeyError, TypeError):
        pass
    return None

# --- PMC ID -> PMID -> DOI ---
def doi_from_pmc(pmc_id):
    """PMC ID string (e.g. 'PMC6953397') -> DOI via EUtils elink + esummary."""
    m = PMC_NUM_PATTERN.search(pmc_id)
    if not m:
        return None
    pmc_num = m.group(1)
    key_param = f'&api_key={NCBI_API_KEY}' if NCBI_API_KEY else ''

    # Step 1: PMC -> PMID via elink
    elink_url = (f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi'
                 f'?dbfrom=pmc&db=pubmed&id={pmc_num}&retmode=json{key_param}')
    time.sleep(NCBI_RATE)
    data = http_get(elink_url)
    pmid = None
    try:
        links = data['linksets'][0]['linksetdbs']
        for ldb in links:
            if ldb.get('dbto') == 'pubmed':
                pmid = str(ldb['links'][0])
                break
    except (KeyError, TypeError, IndexError):
        pass

    if not pmid:
        return None
    return doi_from_pmid(pmid)

# --- Tier 3: CrossRef lookup ---
def doi_from_crossref(title, author, year):
    """CrossRef API: citation string -> DOI via query.bibliographic.
    'title' here is actually the full clean_ref citation string from the DB.
    query.bibliographic is designed for full citation lookups.
    """
    if not title:
        return None
    # Use full citation string if it looks like one (>80 chars or contains journal info)
    # Otherwise fall back to title + author
    citation_query = title if len(title) > 80 or any(c in title for c in [';', 'Am Fam', 'JAMA', 'NEJM', 'Lancet']) else f'{title} {author}'
    query = urllib.parse.quote(citation_query)
    url = (f'https://api.crossref.org/works'
           f'?query.bibliographic={query}'
           f'&filter=from-pub-date:{year},until-pub-date:{int(year)+1}'
           f'&rows=3'
           f'&select=DOI,title,author,published,score'
           f'&mailto={CROSSREF_EMAIL}')
    time.sleep(CROSSREF_RATE)
    data = http_get(url)
    if not data:
        return None
    try:
        items = data['message']['items']
        if not items:
            return None
        top = items[0]
        score = top.get('score', 0)
        if score < CROSSREF_MIN_SCORE:
            return None
        # Verify year is close
        pub_year = None
        if 'published' in top:
            parts = top['published'].get('date-parts', [[None]])
            pub_year = parts[0][0] if parts and parts[0] else None
        if pub_year and abs(int(pub_year) - int(year)) > YEAR_TOLERANCE:
            return None
        return top.get('DOI')
    except (KeyError, TypeError, ValueError):
        return None

# --- Unpaywall lookup ---
def unpaywall_lookup(doi):
    """Returns (is_oa, pdf_url, oa_location).
    ONLY returns pdf_url when url_for_pdf is explicitly present.
    Does NOT fall back to url (landing pages fail PDF magic bytes check).
    """
    encoded = urllib.parse.quote(doi, safe='')
    url = f'https://api.unpaywall.org/v2/{encoded}?email={UNPAYWALL_EMAIL}'
    time.sleep(UNPAYWALL_RATE)
    data = http_get(url)
    if not data:
        return False, None, None
    is_oa = data.get('is_oa', False)
    best = data.get('best_oa_location') or {}
    pdf_url = best.get('url_for_pdf')   # FIXED: no 'or best.get("url")' fallback
    oa_loc = best.get('host_type', '')
    return is_oa, pdf_url, oa_loc

# --- PDF download ---
def codon_filename(author1, year, article_id):
    author = re.sub(r'[^\w]', '', author1 or 'Unknown')
    return f'{author}_{year}#@#{article_id}@#@.pdf'

def download_pdf(pdf_url, dest_path):
    """Download PDF, verify magic bytes, save. Returns (success, bytes_written)."""
    try:
        req = urllib.request.Request(
            pdf_url,
            headers={
                'User-Agent': 'Mozilla/5.0 (compatible; ITE-Intelligence/1.0)',
                'Accept': 'application/pdf,*/*'
            }
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read()
        if not content.startswith(b'%PDF'):
            return False, 0
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_bytes(content)
        return True, len(content)
    except Exception:
        return False, 0

# --- Results CSV ---
RESULT_FIELDS = [
    'article_id', 'tier', 'source', 'author1', 'year',
    'doi_method', 'doi', 'is_oa', 'oa_host',
    'pdf_url', 'download_status', 'bytes', 'dest_filename'
]

def load_done(results_path, retry_failed=False):
    """Load set of article_ids that are already fully resolved.
    retry_failed=True: only skip 'downloaded' and 'not_oa' — re-process no_doi + download_failed.
    retry_failed=False (--resume): skip everything already in the CSV.
    """
    done = set()
    if not results_path.exists():
        return done
    with open(results_path, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if retry_failed:
                if row['download_status'] in ('downloaded', 'not_oa', 'dry_run'):
                    done.add(row['article_id'])
            else:
                done.add(row['article_id'])
    return done

def flush_results(rows, results_path, write_header):
    mode = 'w' if write_header else 'a'
    with open(results_path, mode, newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=RESULT_FIELDS)
        if write_header:
            w.writeheader()
        w.writerows(rows)

# --- Build article queue ---
def build_queue(source_filter):
    articles = {}  # article_id -> dict

    if source_filter in ('exa', 'both'):
        with open(EXA_CSV, newline='', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                if row['classification'] == 'landing_page':
                    articles[row['article_id']] = {
                        'article_id': row['article_id'],
                        'tier': row['tier'],
                        'source': 'exa',
                        'author1': row['author1'],
                        'year': row['year'],
                        'title': row['title'],    # may be truncated — enriched below
                        'top_url': row['top_url'],
                        'pmc_id': None,
                    }

    if source_filter in ('pmc', 'both'):
        with open(PMC_CSV, newline='', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                if row['download_status'] == 'skip' and row['pmc_id']:
                    aid = row['article_id']
                    if aid not in articles:
                        articles[aid] = {
                            'article_id': aid,
                            'tier': row['tier'],
                            'source': 'pmc',
                            'author1': row['author1'],
                            'year': row['year'],
                            'title': row['title'],
                            'top_url': '',
                            'pmc_id': row['pmc_id'],
                        }

    # Enrich with full titles from DB (CrossRef gets much better results)
    log(f"Fetching full titles from DB for {len(articles)} articles...")
    db_titles = get_db_titles(list(articles.keys()))
    enriched = 0
    for aid, art in articles.items():
        if aid in db_titles and db_titles[aid]:
            if art['title'] != db_titles[aid]:
                art['title'] = db_titles[aid]
                enriched += 1
    log(f"  Enriched {enriched} titles from DB (replacing truncated CSV titles)")

    return list(articles.values())

# --- Main ---
def main():
    parser = argparse.ArgumentParser(description='Unpaywall scanner + downloader')
    parser.add_argument('--dry-run',      action='store_true', help='Resolve + Unpaywall, no downloads')
    parser.add_argument('--limit',        type=int, default=0, help='Process only first N articles')
    parser.add_argument('--resume',       action='store_true', help='Skip all articles already in results CSV')
    parser.add_argument('--retry-failed', action='store_true', help='Re-process no_doi + download_failed (skip only downloaded/not_oa)')
    parser.add_argument('--source',       choices=['exa', 'pmc', 'both'], default='both')
    args = parser.parse_args()

    log(f'=== unpaywall_scanner.py START | source={args.source} dry-run={args.dry_run} '
        f'resume={args.resume} retry-failed={args.retry_failed} ===')

    retry_failed = args.retry_failed
    done = load_done(RESULTS_CSV, retry_failed=retry_failed) if (args.resume or retry_failed) else set()
    queue = build_queue(args.source)

    if args.resume or retry_failed:
        before = len(queue)
        queue = [a for a in queue if a['article_id'] not in done]
        log(f'Skipped {before - len(queue)} already-resolved; {len(queue)} to process')
    else:
        log(f'Queue: {len(queue)} articles')

    if args.limit:
        queue = queue[:args.limit]
        log(f'Limit applied: processing {len(queue)} articles')

    # When retrying failed, append to existing CSV (don't overwrite good rows)
    write_header = not ((args.resume or retry_failed) and RESULTS_CSV.exists())
    pending = []

    stats = {'doi_url': 0, 'doi_pmid': 0, 'doi_crossref': 0, 'doi_pmc': 0,
             'no_doi': 0, 'oa': 0, 'oa_no_pdf_url': 0, 'not_oa': 0,
             'downloaded': 0, 'failed': 0}

    for i, art in enumerate(queue, 1):
        aid   = art['article_id']
        tier  = art['tier']
        url   = art['top_url']
        title = art['title']
        auth  = art['author1']
        year  = art['year']
        pmc   = art['pmc_id']

        log(f'[{i}/{len(queue)}] {aid} -- {auth} {year}')

        # --- DOI resolution ---
        doi = None
        doi_method = 'none'

        if pmc and not url:
            doi = doi_from_pmc(pmc)
            if doi:
                doi_method = 'pmc_eutils'
                stats['doi_pmc'] += 1
        else:
            # Tier 1: DOI in URL
            doi = doi_from_url(url)
            if doi:
                doi_method = 'url'
                stats['doi_url'] += 1

            # Tier 2: PMID in URL
            if not doi:
                pmid = pmid_from_url(url)
                if pmid:
                    doi = doi_from_pmid(pmid)
                    if doi:
                        doi_method = 'pmid_eutils'
                        stats['doi_pmid'] += 1

            # Tier 3: CrossRef (using full DB title)
            if not doi and title and auth and year:
                doi = doi_from_crossref(title, auth, year)
                if doi:
                    doi_method = 'crossref'
                    stats['doi_crossref'] += 1

        if not doi:
            stats['no_doi'] += 1
            log(f'  [X] No DOI resolved')
            pending.append({
                'article_id': aid, 'tier': tier, 'source': art['source'],
                'author1': auth, 'year': year,
                'doi_method': 'none', 'doi': '', 'is_oa': 'false',
                'oa_host': '', 'pdf_url': '', 'download_status': 'no_doi',
                'bytes': '0', 'dest_filename': ''
            })
            if len(pending) >= SAVE_EVERY:
                flush_results(pending, RESULTS_CSV, write_header)
                write_header = False
                pending = []
            continue

        log(f'  DOI [{doi_method}]: {doi}')

        # --- Unpaywall ---
        is_oa, pdf_url, oa_host = unpaywall_lookup(doi)

        if not is_oa:
            stats['not_oa'] += 1
            log(f'  [X] Not OA')
            pending.append({
                'article_id': aid, 'tier': tier, 'source': art['source'],
                'author1': auth, 'year': year,
                'doi_method': doi_method, 'doi': doi,
                'is_oa': 'false', 'oa_host': oa_host or '',
                'pdf_url': '', 'download_status': 'not_oa',
                'bytes': '0', 'dest_filename': ''
            })
            if len(pending) >= SAVE_EVERY:
                flush_results(pending, RESULTS_CSV, write_header)
                write_header = False
                pending = []
            continue

        if not pdf_url:
            # OA exists but no direct PDF URL (url_for_pdf was None)
            stats['oa_no_pdf_url'] += 1
            log(f'  [~] OA found ({oa_host}) but no direct pdf_url — skipping')
            pending.append({
                'article_id': aid, 'tier': tier, 'source': art['source'],
                'author1': auth, 'year': year,
                'doi_method': doi_method, 'doi': doi,
                'is_oa': 'true', 'oa_host': oa_host or '',
                'pdf_url': '', 'download_status': 'oa_no_pdf_url',
                'bytes': '0', 'dest_filename': ''
            })
            if len(pending) >= SAVE_EVERY:
                flush_results(pending, RESULTS_CSV, write_header)
                write_header = False
                pending = []
            continue

        stats['oa'] += 1
        log(f'  [OK] OA + pdf_url ({oa_host}): {pdf_url[:80]}')

        # --- Download ---
        dl_status = 'dry_run'
        nbytes    = 0
        dest_fn   = ''

        if not args.dry_run:
            fname     = codon_filename(auth, year, aid)
            dest_path = PDF_BASE / tier / fname
            time.sleep(DOWNLOAD_RATE)
            ok, nbytes = download_pdf(pdf_url, dest_path)
            if ok:
                dl_status = 'downloaded'
                dest_fn   = fname
                stats['downloaded'] += 1
                log(f'  [OK] Downloaded: {fname} ({nbytes:,} bytes)')
            else:
                dl_status = 'download_failed'
                stats['failed'] += 1
                log(f'  [X] Download failed: {pdf_url[:80]}')
        else:
            log(f'  (dry-run: skipping download)')

        pending.append({
            'article_id': aid, 'tier': tier, 'source': art['source'],
            'author1': auth, 'year': year,
            'doi_method': doi_method, 'doi': doi,
            'is_oa': 'true', 'oa_host': oa_host or '',
            'pdf_url': pdf_url, 'download_status': dl_status,
            'bytes': str(nbytes), 'dest_filename': dest_fn
        })

        if len(pending) >= SAVE_EVERY:
            flush_results(pending, RESULTS_CSV, write_header)
            write_header = False
            pending = []

    # Final flush
    if pending:
        flush_results(pending, RESULTS_CSV, write_header)

    log('=== DONE ===')
    log(f'DOI from URL:      {stats["doi_url"]}')
    log(f'DOI from PMID:     {stats["doi_pmid"]}')
    log(f'DOI from CrossRef: {stats["doi_crossref"]}')
    log(f'DOI from PMC:      {stats["doi_pmc"]}')
    log(f'No DOI:            {stats["no_doi"]}')
    log(f'OA found + dl:     {stats["oa"]}')
    log(f'OA no pdf_url:     {stats["oa_no_pdf_url"]}')
    log(f'Not OA:            {stats["not_oa"]}')
    log(f'Downloaded:        {stats["downloaded"]}')
    log(f'Failed:            {stats["failed"]}')
    log(f'Results saved to:  {RESULTS_CSV}')

if __name__ == '__main__':
    main()
