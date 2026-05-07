"""
acquire_missing_citations.py
============================
Acquires article records + PDFs for citations in question_ref_pairs
where clean_ref IS NULL (no matching article in the library).

Phases:
  1. Load     — read unmatched citations from question_ref_pairs
  2. Dedup    — group by ref_raw; collect all affected QIDs per citation
  3. Parse    — extract author1, year, title, journal → source_type
  4. Classify — textbook_skip | textbook_fauci | searchable
  5. Search   — Exa search per searchable citation; URL → classification
  6. Insert   — new article records + qid_art_xref + question_ref_pairs update
  7. Download — PDFs for direct_pdf / pmc_fulltext / open_access URLs

Usage:
    python acquire_missing_citations.py --dry-run          # parse + classify, no DB writes, no downloads
    python acquire_missing_citations.py --skip-download    # insert DB records only, no PDFs
    python acquire_missing_citations.py                    # full run (Exa + DB + download)
    python acquire_missing_citations.py --limit 10         # cap for testing
    python acquire_missing_citations.py --resume           # skip refs already acquired
    python acquire_missing_citations.py --textbook-only    # Fauci/Harrison entries only

Classification rules:
    textbook_skip   — non-Fauci textbook chapters → skipped entirely, no record created
    textbook_fauci  — Harrison's / Fauci → citation_only=1, source_type='Textbook/Fauci', no PDF
    searchable      — all others → Exa search → classify URL → download

Output:
    scripts/maintain/acquire_results.csv   one row per citation processed
    scripts/maintain/acquire_run.log       timestamped progress log

Note: article_currency table is NOT updated by this script.
      Run build_article_currency.py after to fill new rows.
"""

import sqlite3, os, re, json, csv, time, argparse, sys
import requests

# Force UTF-8 output on Windows (cp1252 console can't handle box-drawing chars)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter

# ── Paths ──────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent   # maintain → scripts → M1 → root
DB_PATH      = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"
PDF_ROOT     = PROJECT_ROOT / "01_module.1_warehouse" / "citation_files" / "ITE"
VC_GATE_PATH = PROJECT_ROOT / "key_data_files" / "session_hy_inserts_v7.json"
RESULTS_CSV  = SCRIPT_DIR / "acquire_results.csv"
LOG_PATH     = SCRIPT_DIR / "acquire_run.log"

# ── EXA ────────────────────────────────────────────────────────────────────
EXA_API_KEY    = os.environ.get("EXA_API_KEY", "")
EXA_SEARCH_URL = "https://api.exa.ai/search"
RATE_LIMIT_SEC = 1.2
NUM_RESULTS    = 5

# ── Download settings ──────────────────────────────────────────────────────
RATE_DOWNLOAD_SEC = 2.0
MAX_PDF_MB        = 50
TIMEOUT_SEC       = 30
CHUNK_SIZE        = 8192

# ── Textbook detection ─────────────────────────────────────────────────────
# Any ref_raw matching these patterns → is_textbook = True
TEXTBOOK_SIGNALS = [
    r"\bIn:\s",           # chapter format "In: Smith J, ed."
    r"\bEds?\.\s",        # "Ed." or "Eds." preceding publisher
    r"McGraw.?Hill",
    r"Elsevier",
    r"Wolters\s+Kluwer",
    r"Lippincott",
    r"Saunders",
    r"Mosby",
    r"Springer",
    r"\d+(?:st|nd|rd|th)\s+ed",  # "21st ed", "7th ed"
    r"Clinical\s+Dermatology",   # Habif
]
TEXTBOOK_RE = re.compile("|".join(TEXTBOOK_SIGNALS), re.IGNORECASE)

# Harrison's / Fauci signals → keep as citation_only=1, source_type='Textbook/Fauci'
FAUCI_SIGNALS = [
    r"Harrison",
    r"\bFauci\b",
    r"Principles\s+of\s+Internal\s+Medicine",
]
FAUCI_RE = re.compile("|".join(FAUCI_SIGNALS), re.IGNORECASE)

# ── Journal → source_type map ──────────────────────────────────────────────
# Checked in order; first match wins. Keys are case-insensitive substrings.
# Guideline/Org entries come FIRST so they don't get overridden by journal names
# (e.g. USPSTF recs sometimes published in JAMA — we prefer the org classification).
JOURNAL_SOURCE_MAP = [
    # ── Guideline / Org sources (highest priority) ──
    ("Final recommendation statement",          "Guideline/Org"),
    ("US Preventive Services Task Force",        "Guideline/Org"),
    ("U.S. Preventive Services Task Force",      "Guideline/Org"),
    ("USPSTF",                                   "Guideline/Org"),
    ("Centers for Disease Control",              "Guideline/Org"),
    ("MMWR",                                     "Guideline/Org"),
    ("uspreventiveservicestaskforce",            "Guideline/Org"),
    ("National Cancer Institute",                "Guideline/Org"),
    ("Sexually transmitted infections treatment guidelines", "Guideline/Org"),
    ("Differentiated and simplified",            "Guideline/Org"),
    # ── Journals ──
    ("Am Fam Physician",       "AFP"),
    ("JAMA",                   "JAMA"),
    ("N Engl J Med",           "NEJM"),
    ("Lancet",                 "Other Journal"),
    ("BMJ",                    "Other Journal"),
    ("Ann Intern Med",         "Other Journal"),
    ("Diabetes Care",          "Other Journal"),
    ("Circulation",            "Other Journal"),
    ("J Am Coll Cardiol",      "Other Journal"),
    ("Pediatrics",             "Other Journal"),
    ("Obstet Gynecol",         "Other Journal"),
    ("J Athl Train",           "Other Journal"),
    ("J Hematol Oncol",        "Other Journal"),
    ("Clin Infect Dis",        "Other Journal"),
    ("Am J Kidney",            "Other Journal"),
    ("Kidney Int",             "Other Journal"),
    ("Hepatology",             "Other Journal"),
    ("J Hepatol",              "Other Journal"),
    ("Chest",                  "Other Journal"),
    ("Am J Respir",            "Other Journal"),
    ("Arthritis",              "Other Journal"),
    ("J Rheumatol",            "Other Journal"),
    ("Neurology",              "Other Journal"),
    ("Stroke",                 "Other Journal"),
    ("J Clin Oncol",           "Other Journal"),
    ("Gastroenterology",       "Other Journal"),
    ("Am J Gastroenterol",     "Other Journal"),
    ("J Am Acad Dermatol",     "Other Journal"),
    ("J Clin Psychiatry",      "Other Journal"),
    ("Arch Intern Med",        "Other Journal"),
    ("Mayo Clin Proc",         "Other Journal"),
    ("Eur Heart J",            "Other Journal"),
    ("Blood",                  "Other Journal"),
    ("MMWR",                   "Guideline/Org"),
    ("uspreventiveservices",   "Guideline/Org"),
    ("uspstf",                 "Guideline/Org"),
    ("cdc.gov",                "Guideline/Org"),
]

# ── URL classifiers (mirrors exa_pdf_finder.py) ────────────────────────────
PMC_PATTERNS = [
    "pmc.ncbi.nlm.nih.gov/articles/PMC",
    "ncbi.nlm.nih.gov/pmc/articles",
    "europepmc.org/articles/PMC",
]
OA_PATTERNS = [
    "biomedcentral.com/articles", "frontiersin.org", "mdpi.com",
    "plos", "elifesciences.org", "bmj.com/content",
    "academic.oup.com", "onlinelibrary.wiley.com/doi/full",
    "ginasthma.org", "uspreventiveservicestaskforce.org",
    "aafp.org/pubs/afp", "cdc.gov", "who.int", "cochranelibrary.com",
]
PAYWALL_PATTERNS = [
    "jamanetwork.com", "nejm.org", "ahajournals.org",
    "publications.aap.org", "pediatrics.aappublications.org",
    "acc.org", "sciencedirect.com", "link.springer.com/article",
    "journals.lww.com", "annals.org", "thelancet.com",
    "diabetesjournals.org", "acpjournals.org",
]

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/pdf,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "max-age=0",
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


# ── VC gate loader ─────────────────────────────────────────────────────────
def load_vc_gate():
    """
    Load citation strings from VC gate JSON. Returns a set.

    Format: dict keyed by session_id ('02', '03', ...).
    Each session has a 'refs' list of dicts with a 'citation' key.
    """
    if not VC_GATE_PATH.exists():
        log(f"  WARNING: VC gate not found at {VC_GATE_PATH}")
        return set()
    with open(VC_GATE_PATH, encoding="utf-8") as f:
        data = json.load(f)
    refs = set()
    if isinstance(data, dict):
        # session_hy_inserts_v7 format: {session_id: {refs: [{citation: ...}]}}
        for session in data.values():
            for ref in session.get("refs", []):
                r = ref.get("citation", "").strip()
                if r:
                    refs.add(r)
    elif isinstance(data, list):
        # fallback: flat list of dicts with clean_ref or citation key
        for item in data:
            if isinstance(item, dict):
                r = (item.get("clean_ref") or item.get("citation") or "").strip()
                if r:
                    refs.add(r)
    log(f"  VC gate loaded: {len(refs)} citations")
    return refs


# ── Citation parser ────────────────────────────────────────────────────────
YEAR_RE   = re.compile(r'\b((?:19|20)\d{2})\b')
PMC_ID_RE = re.compile(r'PMC(\d+)', re.IGNORECASE)


def parse_citation(ref_raw):
    """
    Parse a raw citation string into structured fields.

    Returns dict:
        author1     — first author surname
        year        — publication year string
        title       — article title (heuristic extraction)
        source_type — AFP / JAMA / NEJM / Guideline/Org / Textbook/Fauci / Textbook / Other Journal
        is_textbook — bool
        is_fauci    — bool
    """
    raw = ref_raw.strip()

    # Textbook / Fauci detection (before any other parsing)
    is_fauci    = bool(FAUCI_RE.search(raw))
    is_textbook = is_fauci or bool(TEXTBOOK_RE.search(raw))

    # Year — first 4-digit year found
    year_matches = YEAR_RE.findall(raw)
    year = year_matches[0] if year_matches else None

    # Author1 — first alphabetic token before a comma, period, or space
    # Handles "Smith J," → "Smith"
    # Handles org names "American Diabetes Association" → "American"
    author_match = re.match(r'^([A-Za-z][A-Za-z\'\-]*)', raw)
    author1 = author_match.group(1) if author_match else "Unknown"

    # Title — heuristic: second sentence segment (after authors, before journal)
    # Standard format: "Authors. Title. Journal. Year;Vol(Issue):Pages."
    # Split on ". " to get segments; authors are segment[0], title is segment[1]
    segments = re.split(r'\.\s+', raw)
    title = segments[1].strip() if len(segments) > 1 else raw[:100]
    title = title[:200]  # cap

    # Source type from journal substring matching
    source_type = "Other Journal"
    raw_lower = raw.lower()
    for journal_substr, stype in JOURNAL_SOURCE_MAP:
        if journal_substr.lower() in raw_lower:
            source_type = stype
            break

    # Override for textbooks
    if is_fauci:
        source_type = "Textbook/Fauci"
    elif is_textbook:
        source_type = "Textbook"

    return {
        "author1":     author1,
        "year":        year,
        "title":       title,
        "source_type": source_type,
        "is_textbook": is_textbook,
        "is_fauci":    is_fauci,
    }


def classify_citation(parsed):
    """
    Returns one of:
        'textbook_skip'   — non-Fauci textbook, omit entirely
        'textbook_fauci'  — Harrison's/Fauci, insert as citation_only
        'searchable'      — search Exa for URL + attempt PDF download
    """
    if parsed["is_fauci"]:
        return "textbook_fauci"
    if parsed["is_textbook"]:
        return "textbook_skip"
    return "searchable"


def build_exa_query(ref_raw, parsed):
    """Build a focused Exa search query from parsed citation fields."""
    title  = (parsed.get("title") or "").strip()
    author = (parsed.get("author1") or "").strip()
    year   = str(parsed.get("year") or "").strip()
    stype  = parsed.get("source_type", "")
    parts  = [p for p in [title, author, year] if p]
    if stype in ("AFP", "Other Journal", "Guideline/Org"):
        parts.append("PDF")
    return " ".join(parts)[:200]


# ── URL classifier ─────────────────────────────────────────────────────────
def classify_url(url):
    if not url:
        return "not_found"
    u = url.lower()
    if u.endswith(".pdf"):
        return "direct_pdf"
    for p in PMC_PATTERNS:
        if p.lower() in u:
            return "pmc_fulltext"
    for p in OA_PATTERNS:
        if p.lower() in u:
            return "open_access"
    for p in PAYWALL_PATTERNS:
        if p.lower() in u:
            return "landing_page"
    return "landing_page"


# ── Exa search ─────────────────────────────────────────────────────────────
def search_exa(query):
    resp = requests.post(
        EXA_SEARCH_URL,
        headers={"x-api-key": EXA_API_KEY, "Content-Type": "application/json"},
        json={
            "query":   query,
            "type":    "auto",
            "num_results": NUM_RESULTS,
            "contents": {"highlights": {"max_characters": 200}},
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("results", [])


# ── Filename builders ──────────────────────────────────────────────────────
def make_canonical_filename(parsed, art_id):
    author = re.sub(r"[^\w\-]", "", (parsed.get("author1") or "Unknown"))
    year   = str(parsed.get("year") or "0000")
    return f"{author}_{year}"


def make_codon_filename(parsed, art_id):
    return f"{make_canonical_filename(parsed, art_id)}#@#{art_id}@#@.pdf"


# ── PDF download helpers ───────────────────────────────────────────────────
def pmc_to_pdf_url(url):
    m = PMC_ID_RE.search(url)
    if not m:
        return None, None
    pmc_id = f"PMC{m.group(1)}"
    primary  = f"https://pmc.ncbi.nlm.nih.gov/articles/{pmc_id}/pdf/"
    fallback = f"https://europepmc.org/backend/ptpmcrender.fcgi?accid={pmc_id}&blobtype=pdf"
    return primary, fallback


def aafp_to_pdf_url(url):
    u = url.lower()
    if "aafp.org/pubs/afp" in u:
        if url.endswith(".html"):
            return url[:-5] + ".pdf"
        if not url.endswith(".pdf"):
            return url + ".pdf"
    return None


def resolve_pdf_url(url_class, top_url):
    if url_class == "direct_pdf":
        return top_url, None
    if url_class == "pmc_fulltext":
        return pmc_to_pdf_url(top_url)
    if url_class == "open_access":
        pdf_url = aafp_to_pdf_url(top_url)
        if pdf_url:
            return pdf_url, None
    return None, None


def download_pdf(url, dest_path, fallback=None, aafp_cookie=None):
    """
    Attempt to download a PDF. Returns (success, status_str, bytes_written).
    Tries primary URL first, then fallback if provided.
    """
    session = requests.Session()
    session.headers.update(BROWSER_HEADERS)
    if aafp_cookie and "aafp.org" in url:
        session.cookies.set("AAFPSESSION", aafp_cookie, domain=".aafp.org")

    for attempt_url in [u for u in [url, fallback] if u]:
        try:
            resp = session.get(attempt_url, timeout=TIMEOUT_SEC, stream=True,
                               allow_redirects=True)
            if resp.status_code != 200:
                log(f"    HTTP {resp.status_code} → {attempt_url[:70]}")
                continue

            ct = resp.headers.get("Content-Type", "").lower()
            # Peek at first bytes to verify PDF magic number
            first = next(resp.iter_content(chunk_size=8), b"")
            is_pdf = ("pdf" in ct or "octet-stream" in ct or first.startswith(b"%PDF"))
            if not is_pdf:
                log(f"    Not a PDF (Content-Type: {ct[:40]})")
                continue

            dest_path.parent.mkdir(parents=True, exist_ok=True)
            size = 0
            with open(dest_path, "wb") as f:
                f.write(first)
                size = len(first)
                for chunk in resp.iter_content(chunk_size=CHUNK_SIZE):
                    f.write(chunk)
                    size += len(chunk)
                    if size > MAX_PDF_MB * 1024 * 1024:
                        log(f"    Exceeds {MAX_PDF_MB}MB — aborting")
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


# ── DB helpers ─────────────────────────────────────────────────────────────
def get_next_art_num(conn):
    """Return the integer for the next available ART-XXXX id."""
    c = conn.cursor()
    c.execute("""
        SELECT MAX(CAST(SUBSTR(article_id, 5) AS INTEGER))
        FROM articles
        WHERE article_id LIKE 'ART-%'
    """)
    max_num = c.fetchone()[0] or 1999
    return max_num + 1


def get_already_acquired(conn):
    """Return set of ref_raw values already linked (clean_ref IS NOT NULL)."""
    c = conn.cursor()
    c.execute("SELECT ref_raw FROM question_ref_pairs WHERE clean_ref IS NOT NULL")
    return set(r[0] for r in c.fetchall())


def load_unmatched(conn):
    """
    Load all question_ref_pairs rows where clean_ref IS NULL.
    Returns list of dicts: {ref_raw, qids, exam_years}.
    Deduplicates by ref_raw — collects all QIDs per unique citation.
    """
    c = conn.cursor()
    c.execute("""
        SELECT qid, ref_raw, exam_year
        FROM question_ref_pairs
        WHERE clean_ref IS NULL
        ORDER BY ref_raw
    """)
    grouped = defaultdict(lambda: {"qids": [], "exam_years": set()})
    for qid, ref_raw, exam_year in c.fetchall():
        grouped[ref_raw]["qids"].append(qid)
        if exam_year:
            grouped[ref_raw]["exam_years"].add(str(exam_year))
    return [{"ref_raw": k, **v} for k, v in grouped.items()]


def insert_article(conn, art_id, ref_raw, parsed, citation_only, vc_gate_refs):
    """
    Insert a new row into articles.
    Returns (tier, effective_art_id).
    If clean_ref already exists (PK conflict), INSERT OR IGNORE silently
    skips — we fall back to the existing article_id so xrefs stay clean.
    Tier = VC_pass if ref_raw is in the VC gate, else VC_fail.
    citation_only rows get codon_filename=None (no PDF expected).
    """
    in_vc  = ref_raw in vc_gate_refs
    tier   = "VC_pass" if in_vc else "VC_fail"
    canonical = make_canonical_filename(parsed, art_id)
    codon     = make_codon_filename(parsed, art_id) if not citation_only else None

    c = conn.cursor()
    c.execute("""
        INSERT OR IGNORE INTO articles
            (clean_ref, article_id, author1, year, title, source_type,
             tier, citation_only, canonical_filename, codon_filename,
             citation_display, extraction_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        ref_raw,
        art_id,
        parsed.get("author1"),
        parsed.get("year"),
        parsed.get("title"),
        parsed.get("source_type"),
        tier,
        1 if citation_only else 0,
        canonical,
        codon,
        ref_raw[:300],    # citation_display = full raw ref, trimmed
        "pending",
    ))

    # If INSERT was ignored (PK conflict), use the existing article_id
    if c.rowcount == 0:
        c.execute("SELECT article_id, tier FROM articles WHERE clean_ref = ?", (ref_raw,))
        row = c.fetchone()
        if row:
            return row[1], row[0]   # (existing_tier, existing_art_id)

    return tier, art_id


def update_ref_pairs(conn, ref_raw):
    """Set clean_ref = ref_raw for all unmatched rows with this ref_raw."""
    c = conn.cursor()
    c.execute("""
        UPDATE question_ref_pairs
        SET clean_ref = ?
        WHERE ref_raw = ? AND clean_ref IS NULL
    """, (ref_raw, ref_raw))
    return c.rowcount


def insert_qid_xref(conn, qids, art_id, tier, parsed):
    """Insert qid_art_xref rows for each QID that cited this article."""
    c = conn.cursor()
    inserted = 0
    for qid in qids:
        m = re.match(r'QID-(\d{4})-', qid)
        exam_year = int(m.group(1)) if m else None
        try:
            c.execute("""
                INSERT OR IGNORE INTO qid_art_xref
                    (qid, article_id, tier, exam_year, author1, year)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (qid, art_id, tier, exam_year,
                  parsed.get("author1"), parsed.get("year")))
            inserted += c.rowcount
        except sqlite3.IntegrityError:
            pass
    return inserted


# ── Results CSV ────────────────────────────────────────────────────────────
RESULT_FIELDS = [
    "art_id", "classification", "url_class", "dl_status",
    "tier", "citation_only", "dl_bytes", "dest_filename",
    "author1", "year", "source_type", "qid_count", "url_used",
    "ref_raw",
]

def append_result(row):
    write_header = not RESULTS_CSV.exists()
    with open(RESULTS_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=RESULT_FIELDS, extrasaction="ignore")
        if write_header:
            w.writeheader()
        w.writerow(row)


def result_row(art_id, classification, url_class, dl_status, tier,
               citation_only, dl_bytes, dest_filename, parsed, qids, url_used, ref_raw):
    return {
        "art_id":        art_id,
        "classification": classification,
        "url_class":     url_class,
        "dl_status":     dl_status,
        "tier":          tier,
        "citation_only": citation_only,
        "dl_bytes":      dl_bytes,
        "dest_filename": dest_filename,
        "author1":       parsed.get("author1", ""),
        "year":          parsed.get("year", ""),
        "source_type":   parsed.get("source_type", ""),
        "qid_count":     len(qids),
        "url_used":      url_used,
        "ref_raw":       ref_raw[:200],
    }


# ── Main ───────────────────────────────────────────────────────────────────
def main():
    global _log_fh

    parser = argparse.ArgumentParser(
        description="Acquire missing citations: insert article records + download PDFs"
    )
    parser.add_argument("--dry-run",       action="store_true",
                        help="Parse + classify only; no DB writes, no Exa calls, no downloads")
    parser.add_argument("--skip-download", action="store_true",
                        help="Insert DB records + run Exa, but do not download PDFs")
    parser.add_argument("--textbook-only", action="store_true",
                        help="Process only Fauci/Harrison entries (citation_only inserts)")
    parser.add_argument("--limit",         type=int, default=0,
                        help="Cap total citations processed (for testing)")
    parser.add_argument("--resume",        action="store_true",
                        help="Skip citations whose ref_raw already has a clean_ref match")
    args = parser.parse_args()

    _log_fh = open(LOG_PATH, "w", encoding="utf-8")
    log(f"=== acquire_missing_citations.py — {datetime.now().isoformat()} ===")
    log(f"dry_run={args.dry_run}  skip_download={args.skip_download}  "
        f"textbook_only={args.textbook_only}  limit={args.limit}  resume={args.resume}")

    if not EXA_API_KEY and not args.dry_run and not args.textbook_only:
        log("ERROR: EXA_API_KEY not set.")
        log("  Use --dry-run to preview, --textbook-only to insert Fauci records only,")
        log("  or set the EXA_API_KEY environment variable before running.")
        _log_fh.close()
        return

    aafp_cookie = os.environ.get("AAFP_SESSION_COOKIE", "").strip()
    log(f"  AAFP cookie: {'LOADED' if aafp_cookie else 'not set (open AFP articles only)'}")

    # ── Phase 1+2: Load + dedup ────────────────────────────────────────────
    log("\n── Phase 1: Loading unmatched citations ──")
    conn = sqlite3.connect(DB_PATH)
    unmatched = load_unmatched(conn)
    total_rows = sum(len(u["qids"]) for u in unmatched)
    log(f"  {len(unmatched)} unique unmatched citations ({total_rows} question_ref_pairs rows)")

    if args.resume:
        already = get_already_acquired(conn)
        before  = len(unmatched)
        unmatched = [u for u in unmatched if u["ref_raw"] not in already]
        log(f"  --resume: skipped {before - len(unmatched)} already acquired")

    vc_gate_refs = load_vc_gate()

    # ── Phase 3+4: Parse + classify ───────────────────────────────────────
    log("\n── Phase 2: Parsing + classifying ──")
    for u in unmatched:
        u["parsed"]         = parse_citation(u["ref_raw"])
        u["classification"] = classify_citation(u["parsed"])

    counts = Counter(u["classification"] for u in unmatched)
    log(f"  searchable:      {counts['searchable']}")
    log(f"  textbook_fauci:  {counts['textbook_fauci']}")
    log(f"  textbook_skip:   {counts['textbook_skip']}")

    # Apply mode filters
    if args.textbook_only:
        unmatched = [u for u in unmatched if u["classification"] == "textbook_fauci"]
        log(f"  --textbook-only: {len(unmatched)} citations to process")

    if args.limit:
        unmatched = unmatched[:args.limit]
        log(f"  --limit {args.limit}: capped to {len(unmatched)}")

    # ── Dry run: show parse table + exit ─────────────────────────────────
    if args.dry_run:
        log("\n── DRY RUN PREVIEW (no DB writes, no Exa calls) ──")
        log(f"\n  {'Class':<18} {'Author':<14} {'Year':<6} {'Type':<20} {'QIDs':<5}  Preview")
        log("  " + "─" * 95)
        for u in unmatched:
            p = u["parsed"]
            preview = u["ref_raw"][:52].replace("\n", " ")
            log(f"  {u['classification']:<18} {(p['author1'] or ''):<14} "
                f"{(p['year'] or ''):<6} {p['source_type']:<20} "
                f"{len(u['qids']):<5}  {preview}")
        log(f"\n  Total: {len(unmatched)} citations")
        log(f"  textbook_skip entries → not inserted into DB")
        log(f"  textbook_fauci entries → citation_only=1, source_type='Textbook/Fauci'")
        log(f"  searchable entries → Exa search + classify + download (if not --skip-download)")
        log(f"\nRe-run without --dry-run to execute.")
        conn.close()
        _log_fh.close()
        return

    # ── Phase 5+6+7: Search + Insert + Download ───────────────────────────
    next_num       = get_next_art_num(conn)
    log(f"\n── Phase 3: Processing {len(unmatched)} citations (starting at ART-{next_num:04d}) ──")

    total_inserted = 0
    total_xref     = 0
    dl_counters    = Counter()

    for i, u in enumerate(unmatched, 1):
        ref_raw        = u["ref_raw"]
        parsed         = u["parsed"]
        classification = u["classification"]
        qids           = u["qids"]

        preview = ref_raw[:68].replace("\n", " ")
        log(f"\n[{i}/{len(unmatched)}] {classification.upper():18} "
            f"{parsed.get('author1','?'):12} {parsed.get('year','?'):6} | "
            f"QIDs:{len(qids)}")
        log(f"  {preview}")

        # ── textbook_skip: drop entirely ──────────────────────────────────
        if classification == "textbook_skip":
            log(f"  → SKIP (non-Fauci textbook)")
            append_result(result_row(
                "", classification, "skipped", "skipped", "", "",
                0, "", parsed, qids, "", ref_raw
            ))
            continue

        # ── Assign next ART-ID ────────────────────────────────────────────
        art_id    = f"ART-{next_num:04d}"
        next_num += 1

        # ── textbook_fauci: citation_only insert, no search ───────────────
        if classification == "textbook_fauci":
            log(f"  → {art_id} | citation_only=1 (Textbook/Fauci)")
            tier, eff_id = insert_article(conn, art_id, ref_raw, parsed, True, vc_gate_refs)
            pairs_upd    = update_ref_pairs(conn, ref_raw)
            xref_count   = insert_qid_xref(conn, qids, eff_id, tier, parsed)
            conn.commit()
            total_inserted += 1
            total_xref     += xref_count
            log(f"    tier={tier} | {pairs_upd} pairs updated | {xref_count} xrefs inserted")
            append_result(result_row(
                art_id, classification, "citation_only", "inserted", tier, 1,
                0, "", parsed, qids, "", ref_raw
            ))
            continue

        # ── searchable: Exa search ────────────────────────────────────────
        query     = build_exa_query(ref_raw, parsed)
        url_class = "not_found"
        top_url   = ""
        exa_title = ""
        log(f"  Exa: {query[:80]}")

        try:
            hits = search_exa(query)
            if hits:
                top       = hits[0]
                top_url   = top.get("url", "")
                exa_title = top.get("title", "")
                url_class = classify_url(top_url)
            log(f"  → {url_class}: {top_url[:75]}")
            time.sleep(RATE_LIMIT_SEC)
        except Exception as e:
            log(f"  Exa error: {e}")
            url_class = "error"
            time.sleep(RATE_LIMIT_SEC)

        # Insert article record (all searchable get a record regardless of URL class)
        tier, eff_id = insert_article(conn, art_id, ref_raw, parsed, False, vc_gate_refs)
        pairs_upd    = update_ref_pairs(conn, ref_raw)
        xref_count   = insert_qid_xref(conn, qids, eff_id, tier, parsed)
        conn.commit()
        total_inserted += 1
        total_xref     += xref_count
        log(f"  → {art_id} [{tier}] | {pairs_upd} pairs updated | {xref_count} xrefs inserted")

        # ── Download ──────────────────────────────────────────────────────
        dl_status  = "no_url"
        dl_bytes   = 0
        dest_fname = ""

        downloadable = ("direct_pdf", "pmc_fulltext", "open_access")
        if not args.skip_download and url_class in downloadable:
            pdf_url, fallback = resolve_pdf_url(url_class, top_url)
            if pdf_url:
                dest_fname = make_codon_filename(parsed, art_id)
                dest_path  = PDF_ROOT / tier / dest_fname
                log(f"  Downloading → {dest_fname}")
                success, dl_status, dl_bytes = download_pdf(
                    pdf_url, dest_path, fallback=fallback, aafp_cookie=aafp_cookie
                )
                if success:
                    log(f"    ✓ {dl_bytes // 1024} KB")
                    dl_counters["downloaded"] += 1
                else:
                    log(f"    ✗ {dl_status}")
                    dl_counters[dl_status] += 1
                time.sleep(RATE_DOWNLOAD_SEC)
            else:
                dl_status = "no_pdf_url"
                dl_counters["no_pdf_url"] += 1
        elif args.skip_download:
            dl_status = "skipped"
        else:
            dl_status = f"not_attempted_{url_class}"
            dl_counters[f"not_attempted_{url_class}"] += 1

        append_result(result_row(
            art_id, classification, url_class, dl_status, tier, 0,
            dl_bytes, dest_fname, parsed, qids, top_url, ref_raw
        ))

    conn.close()

    # ── Final summary ─────────────────────────────────────────────────────
    log("\n" + "═" * 58)
    log("  acquire_missing_citations.py — Summary")
    log("═" * 58)
    log(f"  Articles inserted:        {total_inserted}")
    log(f"  qid_art_xref rows added:  {total_xref}")
    log(f"  PDFs downloaded:          {dl_counters.get('downloaded', 0)}")
    log(f"  Download failed:          {dl_counters.get('failed', 0)}")
    log(f"  Too small / too large:    "
        f"{dl_counters.get('too_small', 0)} / {dl_counters.get('too_large', 0)}")
    log(f"  Landing page (paywall):   "
        f"{dl_counters.get('not_attempted_landing_page', 0)}")
    log(f"  Not found (Exa):          "
        f"{dl_counters.get('not_attempted_not_found', 0)}")
    log(f"\n  Results CSV: {RESULTS_CSV.name}")
    log(f"  Log:         {LOG_PATH.name}")
    log(f"\n  ⚠  article_currency not updated — run build_article_currency.py after to fill gaps.")
    _log_fh.close()


if __name__ == "__main__":
    main()
