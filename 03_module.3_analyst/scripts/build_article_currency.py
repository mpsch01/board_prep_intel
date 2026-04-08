#!/usr/bin/env python3
"""
build_article_currency.py
03_module.3_analyst/scripts/

Intelligence 2.0 — Layer 2: Article Currency via PubMed

Creates and populates the article_currency table by:

  Phase A — PMID Resolution
    A1. Seed from pubmed_pmid_cache (344 PMIDs already resolved via AAFP citation path)
    A2. esearch remaining articles: first-author + year → PMID

  Phase B — Currency Check
    For each article with a pubmed_id:
      1. efetch → verify metadata (title, pub_date, first_author)
      2. esearch for newer publications by same first author post-publication year
      3. Set currency_status: current | updated | check_needed | not_indexed

Run:
    python scripts/build_article_currency.py                       # full run (A then B)
    python scripts/build_article_currency.py --phase-a             # PMID resolution only
    python scripts/build_article_currency.py --phase-b             # currency check only (A must run first)
    python scripts/build_article_currency.py --phase-b --recheck   # re-check 'updated' rows with new logic
    python scripts/build_article_currency.py --dry-run             # report without DB writes
    python scripts/build_article_currency.py --limit 20            # process first N articles (testing)

Env:
    NCBI_API_KEY  — optional; unlocks 10 req/s vs 3 req/s without key
                    Free registration: https://www.ncbi.nlm.nih.gov/account/

currency_status values:
    pending       — PMID resolved, currency check not yet run
    current       — checked, no newer publication found
    updated       — checked, single newer publication found (details in newer_version_* cols)
    check_needed  — checked, multiple newer articles found OR ambiguous PMID match
    not_indexed   — article not found in PubMed (no PMID could be resolved)
"""

import os
import sys
import re
import time
import sqlite3
import argparse
import logging
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import date

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH      = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"
LOG_DIR      = PROJECT_ROOT / "00_database" / "logs"

# ── NCBI Config ───────────────────────────────────────────────────────────────
NCBI_API_KEY  = os.environ.get("NCBI_API_KEY", "")
RATE_DELAY    = 0.11 if NCBI_API_KEY else 0.36   # 10/s with key, ~3/s without
BASE_URL      = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
TODAY         = date.today().isoformat()
CURRENT_YEAR  = date.today().year

# ── Schema ────────────────────────────────────────────────────────────────────
CREATE_ARTICLE_CURRENCY = """
CREATE TABLE IF NOT EXISTS article_currency (
    article_id          TEXT PRIMARY KEY,
    pubmed_id           TEXT,
    pub_date            TEXT,
    pub_title           TEXT,
    last_checked        TEXT,
    newer_version_pmid  TEXT,
    newer_version_date  TEXT,
    newer_version_title TEXT,
    currency_status     TEXT,
    title_signals       TEXT    -- JSON array of clinical category words (diagnosis, treatment, etc.)
                                -- filtered from overlap check; forward-use: blueprint cross-reference
);
"""

def ensure_title_signals_column(conn: sqlite3.Connection) -> bool:
    """
    Idempotent migration: adds title_signals TEXT column to article_currency
    if it doesn't already exist. Returns True if column was added, False if
    it was already present. Safe to call on every run.
    """
    cur  = conn.cursor()
    cols = [row[1] for row in cur.execute("PRAGMA table_info(article_currency)").fetchall()]
    if 'title_signals' not in cols:
        cur.execute("ALTER TABLE article_currency ADD COLUMN title_signals TEXT")
        conn.commit()
        log.info("Migration: added title_signals column to article_currency")
        return True
    return False


def backfill_title_signals(conn: sqlite3.Connection) -> int:
    """
    Populate title_signals for existing rows that have a pub_title but no
    title_signals yet. Pure text operation — no API calls.
    Run once after column is added; safe to re-run (skips already-populated rows).
    """
    import json
    cur  = conn.cursor()
    rows = cur.execute("""
        SELECT article_id, pub_title
        FROM   article_currency
        WHERE  pub_title IS NOT NULL
          AND  (title_signals IS NULL OR title_signals = '')
    """).fetchall()

    updated = 0
    for article_id, pub_title in rows:
        _, signals = extract_title_parts(pub_title)
        cur.execute(
            "UPDATE article_currency SET title_signals = ? WHERE article_id = ?",
            (json.dumps(signals) if signals else '[]', article_id),
        )
        updated += 1

    conn.commit()
    log.info(f"Backfill: populated title_signals for {updated} existing rows")
    return updated


# ═══════════════════════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════════════════════

LOG_DIR.mkdir(parents=True, exist_ok=True)
log_file = LOG_DIR / f"article_currency_{TODAY.replace('-', '')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# NCBI API HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def ncbi_get(endpoint: str, params: dict) -> str | None:
    """GET request to NCBI eutils. Returns response text or None on error."""
    if NCBI_API_KEY:
        params["api_key"] = NCBI_API_KEY
    url = BASE_URL + endpoint + "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        log.warning(f"NCBI request failed ({endpoint}): {e}")
        return None


def esearch(query: str, retmax: int = 5) -> list:
    """Search PubMed. Returns list of PMIDs (strings), up to retmax."""
    resp = ncbi_get("esearch.fcgi", {
        "db": "pubmed", "term": query,
        "retmax": retmax, "retmode": "xml",
    })
    time.sleep(RATE_DELAY)
    if not resp:
        return []
    try:
        root = ET.fromstring(resp)
        return [el.text for el in root.findall(".//Id") if el.text]
    except ET.ParseError:
        return []


def efetch_article(pmid: str) -> dict | None:
    """
    Fetch article metadata for a PMID.
    Returns dict: title, pub_date, first_author, journal — or None on failure.
    """
    resp = ncbi_get("efetch.fcgi", {
        "db": "pubmed", "id": pmid,
        "rettype": "xml", "retmode": "xml",
    })
    time.sleep(RATE_DELAY)
    if not resp:
        return None
    try:
        root = ET.fromstring(resp)
        art = root.find(".//PubmedArticle")
        if art is None:
            return None

        # Title
        title_el = art.find(".//ArticleTitle")
        title = (title_el.text or "") if title_el is not None else ""

        # Publication year — prefer structured Year, fall back to MedlineDate
        year_el   = art.find(".//PubDate/Year")
        med_el    = art.find(".//PubDate/MedlineDate")
        if year_el is not None and year_el.text:
            pub_date = year_el.text
        elif med_el is not None and med_el.text:
            pub_date = med_el.text[:4]
        else:
            pub_date = ""

        # First author last name
        author_el    = art.find(".//AuthorList/Author/LastName")
        first_author = (author_el.text or "") if author_el is not None else ""

        # Journal abbreviation
        journal_el = art.find(".//Journal/ISOAbbreviation")
        if journal_el is None:
            journal_el = art.find(".//Journal/Title")
        journal = (journal_el.text or "") if journal_el is not None else ""

        return {
            "title":        title[:500],
            "pub_date":     pub_date,
            "first_author": first_author,
            "journal":      journal,
        }
    except ET.ParseError:
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE A — PMID RESOLUTION
# ═══════════════════════════════════════════════════════════════════════════════

# Textbook / non-journal signals — these won't appear in PubMed as citable articles
_TEXTBOOK_SIGNALS = re.compile(
    r'\(eds?\b|ed\s+\d+\b|McGraw.?Hill|Elsevier|Saunders|Lippincott|Springer|'
    r'Williams\s*&\s*Wilkins|Oxford\s+University|Cambridge\s+University|'
    r'UpToDate|Wolters\s+Kluwer',
    re.IGNORECASE,
)

# Org-author prefixes that are not personal surnames
_ORG_AUTHOR_PREFIXES = re.compile(
    r'^(US\s+Preventive|USPSTF|American\s+|Centers\s+for|World\s+Health|'
    r'National\s+|CDC\b|WHO\b|Final\s+Recommendation|Joint\s+Commission|'
    r'Agency\s+for)',
    re.IGNORECASE,
)

# Words that look like capitalized surnames but are actually document title words
_NON_SURNAME_WORDS = {
    'Final', 'Global', 'Lexapro', 'Plague', 'Advancing', 'Antibiotic', 'Aspirin',
    'Autism', 'Birth', 'Breastfeeding', 'Clinical', 'Screening', 'Prevention',
    'Diagnosis', 'Treatment', 'Management', 'Authors', 'Evidence', 'Updated',
    'Current', 'Using', 'Reducing', 'Understanding', 'Evaluating', 'Interpreting',
    'Improving', 'Care', 'New', 'Practice', 'Executive', 'Summary', 'Report',
    'Guideline', 'Guidelines', 'Recommendations', 'Statement', 'Update', 'Policy',
}

# Org abbreviations → PubMed Collective Name (None = unresolvable, skip)
_ORG_ABBREV_MAP = {
    'AAP':  'American Academy of Pediatrics',
    'ACC':  'American College of Cardiology',
    'ACOG': 'American College of Obstetricians and Gynecologists',
    'ACR':  'American College of Rheumatology',
    'ADA':  'American Diabetes Association',
    'AHA':  'American Heart Association',
    'AAFP': 'American Academy of Family Physicians',
    'AGS':  'American Geriatrics Society',
    'AAN':  'American Academy of Neurology',
    'AAOS': 'American Academy of Orthopaedic Surgeons',
    'AMDA': 'AMDA',                                  # short name works better in PubMed
    'ACP':  'American College of Physicians',
    'ASAM': 'American Society of Addiction Medicine',
    'IDSA': 'Infectious Diseases Society of America',
    'ATA':  'American Thyroid Association',
    'AASM': 'American Academy of Sleep Medicine',
    # Unresolvable — not standard PubMed collective authors
    'FDA':  None,
    'VA':   None,
    'VTE':  None,
    'EBM':  None,
    'AFP':  None,
}


def extract_first_author(clean_ref: str) -> str | None:
    """
    Extract first author surname from a clean_ref citation string.
    Returns None for org authors, textbooks, title-word false positives.
      "Gentry M, et al..." → "Gentry"
      "Tu P. Heel pain..."  → "Tu"   (2-char surnames supported)
      "USPSTF. Screening..." → None  (org author prefix)
      "Final Recommendation Statement..." → None  (title word)
      "Harrison's Principles (eds)..." → None  (textbook)
    """
    if not clean_ref:
        return None
    ref = clean_ref.strip()

    # Skip known org-author prefixes
    if _ORG_AUTHOR_PREFIXES.match(ref):
        return None

    # Skip textbooks and non-journal sources
    if _TEXTBOOK_SIGNALS.search(ref):
        return None

    # Match a capitalized surname (2+ chars) at the start
    match = re.match(r'^([A-Z][a-zA-Z\-\']+)', ref)
    if not match:
        return None

    candidate = match.group(1)

    # Reject known title-word false positives
    if candidate in _NON_SURNAME_WORDS:
        return None

    return candidate


def build_collective_name_query(clean_ref: str, year: int) -> str | None:
    """
    If clean_ref starts with a known org abbreviation (AAP, ACOG, etc.),
    build a PubMed [Collective Name] query instead of [Author].
    Returns None if not an org abbreviation or abbreviation is unresolvable.

    Example:
      "AAP. Breastfeeding policy. Pediatrics. 2015;91(5):578-585."
      → '"American Academy of Pediatrics"[Collective Name] AND 2015[dp] AND 91[vi] AND 578[pg]'
    """
    if not clean_ref or not year:
        return None

    # Extract first token (handles "ACOG." or "ACOG " or "ACOG:")
    first_token = re.match(r'^([A-Z]{2,6})\b', clean_ref.strip())
    if not first_token:
        return None

    abbrev = first_token.group(1)

    if abbrev not in _ORG_ABBREV_MAP:
        return None   # not a known org abbreviation

    full_name = _ORG_ABBREV_MAP[abbrev]
    if full_name is None:
        return None   # known abbreviation but not PubMed-resolvable (FDA, VA, etc.)

    query = f'"{full_name}"[Collective Name] AND {year}[dp]'

    # Add volume + first page for precision
    vol_match  = re.search(r';\s*(\d+)\s*[\(\[]', clean_ref)
    page_match = re.search(r':\s*(\d+)\s*[-–\.]', clean_ref)
    if vol_match:
        query += f" AND {vol_match.group(1)}[vi]"
    if page_match:
        query += f" AND {page_match.group(1)}[pg]"

    return query


def build_esearch_query(clean_ref: str, year: int) -> str | None:
    """
    Build a precise PubMed esearch query from a clean_ref citation string.
    Uses author + year as base, then adds volume + first page for precision.

    Examples:
      "Gentry S, Gentry B: COPD. Am Fam Physician 2017;95(7):433-441"
      → "Gentry[Author] AND 2017[dp] AND 95[vi] AND 433[pg]"   (single hit)

      "Tu P. Heel pain. Am Fam Physician. 2018;97(2):86-93."
      → "Tu[Author] AND 2018[dp] AND 97[vi] AND 86[pg]"

      "Harrison's Principles (eds)..." → None  (textbook, skip)
      "USPSTF. Screening for ..."      → None  (org author, skip)
    """
    author = extract_first_author(clean_ref or "")
    if not author or not year:
        return None

    query = f"{author}[Author] AND {year}[dp]"

    # Add journal volume: "2017;95(7):433" → [vi] 95
    vol_match = re.search(r';\s*(\d+)\s*[\(\[]', clean_ref)
    if vol_match:
        query += f" AND {vol_match.group(1)}[vi]"

    # Add first page: ":433-441" or ":86-93." → [pg] 433
    page_match = re.search(r':\s*(\d+)\s*[-–\.]', clean_ref)
    if page_match:
        query += f" AND {page_match.group(1)}[pg]"

    return query


def seed_from_pmid_cache(conn: sqlite3.Connection, dry_run: bool) -> int:
    """
    A1: Attempt to seed article_currency from pubmed_pmid_cache via AAFP citation path.
    Join: pubmed_pmid_cache → aafp_citations → articles

    NOTE: All 344 cached PMIDs were sourced from 'unmatched' aafp_citations (no article_id).
    This step is retained for forward-compatibility if new PMIDs are ever cached against
    matched citations, but currently contributes 0 rows. Phase A2 covers all articles.
    """
    cur = conn.cursor()
    rows = cur.execute("""
        SELECT DISTINCT ac.article_id, pc.pmid
        FROM   pubmed_pmid_cache pc
        JOIN   aafp_citations ac ON pc.citation_id = ac.citation_id
        WHERE  ac.article_id IS NOT NULL
          AND  pc.pmid IS NOT NULL
    """).fetchall()

    seeded = 0
    for article_id, pmid in rows:
        if not dry_run:
            cur.execute("""
                INSERT OR IGNORE INTO article_currency
                    (article_id, pubmed_id, last_checked, currency_status)
                VALUES (?, ?, ?, 'pending')
            """, (article_id, pmid, TODAY))
            cur.execute("""
                UPDATE article_currency
                SET    pubmed_id = ?, last_checked = ?, currency_status = 'pending'
                WHERE  article_id = ? AND pubmed_id IS NULL
            """, (pmid, TODAY, article_id))
        seeded += 1

    if not dry_run:
        conn.commit()
    log.info(f"[A1] Seeded {seeded} PMIDs from pubmed_pmid_cache (expected 0 — see note in docstring)")
    return seeded


def resolve_pmids_via_esearch(
    conn: sqlite3.Connection,
    dry_run: bool,
    limit: int | None,
    retry_mode: bool = False,
) -> dict:
    """
    A2: Attempt PMID lookup for articles via esearch.

    Search priority:
      1. Collective Name query (org abbreviations: AAP, ACOG, ACC, etc.)
      2. Personal author query (first_author[Author] AND year + vol + page)
      3. Page-drop fallback (retry without [pg] if step 2 returns 0 hits)

    Result → status mapping:
      1 hit   → 'pending'       (high-confidence)
      2-3 hits → 'check_needed' (ambiguous; take first PMID)
      0 hits   → 'not_indexed'

    retry_mode=True: re-processes existing 'not_indexed' rows (UPDATE instead of INSERT).
    """
    cur = conn.cursor()

    # Check whether article_currency exists yet (it won't in dry-run mode)
    table_exists = cur.execute("""
        SELECT COUNT(*) FROM sqlite_master
        WHERE type='table' AND name='article_currency'
    """).fetchone()[0]

    if retry_mode and table_exists:
        # Retry: only re-process existing not_indexed rows
        sql = """
            SELECT  a.article_id, a.clean_ref, a.year
            FROM    articles a
            JOIN    article_currency ac ON a.article_id = ac.article_id
            WHERE   ac.currency_status = 'not_indexed'
            ORDER BY a.citation_count DESC
        """
    elif table_exists:
        # Normal: only fetch articles not yet in the table
        sql = """
            SELECT  a.article_id, a.clean_ref, a.year
            FROM    articles a
            LEFT JOIN article_currency ac ON a.article_id = ac.article_id
            WHERE   ac.article_id IS NULL
            ORDER BY a.citation_count DESC
        """
    else:
        # Dry-run (table not created yet): query all articles
        sql = """
            SELECT  article_id, clean_ref, year
            FROM    articles
            ORDER BY citation_count DESC
        """
    if limit:
        sql += f" LIMIT {limit}"
    articles = cur.execute(sql).fetchall()

    stats = {"total": len(articles), "resolved": 0, "ambiguous": 0, "not_found": 0}
    log.info(f"[A2] {len(articles)} articles queued {'(retry not_indexed)' if retry_mode else ''}")

    for i, (article_id, clean_ref, year) in enumerate(articles, 1):
        ref = clean_ref or ""

        # ── Strategy 1: Collective Name (org abbreviations) ───────────────────
        search_term = build_collective_name_query(ref, year)
        strategy    = "collective"

        # ── Strategy 2: Personal author + vol + page ──────────────────────────
        if not search_term:
            search_term = build_esearch_query(ref, year)
            strategy    = "author"

        # ── No viable query → skip ────────────────────────────────────────────
        if not search_term:
            if not dry_run:
                if retry_mode:
                    pass   # already 'not_indexed', no change needed
                else:
                    cur.execute("""
                        INSERT OR IGNORE INTO article_currency
                            (article_id, pubmed_id, last_checked, currency_status)
                        VALUES (?, NULL, ?, 'not_indexed')
                    """, (article_id, TODAY))
            log.info(f"  [{i}/{stats['total']}] SKIPPED   {article_id} (org/textbook/no-author)")
            stats["not_found"] += 1
            continue

        pmids = esearch(search_term, retmax=3)

        # ── Strategy 3: Page-drop fallback ────────────────────────────────────
        if len(pmids) == 0 and '[pg]' in search_term:
            fallback = re.sub(r' AND \d+\[pg\]', '', search_term)
            pmids    = esearch(fallback, retmax=3)
            if pmids:
                log.info(f"  [{i}/{stats['total']}] FALLBACK  {article_id} (dropped page → {len(pmids)} hits)")
                search_term = fallback

        # ── Classify result ───────────────────────────────────────────────────
        if len(pmids) == 1:
            status = "pending"
            pmid   = pmids[0]
            stats["resolved"] += 1
            log.info(f"  [{i}/{stats['total']}] RESOLVED  {article_id} → PMID {pmid} [{strategy}]")
        elif len(pmids) > 1:
            status = "check_needed"
            pmid   = pmids[0]
            stats["ambiguous"] += 1
            log.info(f"  [{i}/{stats['total']}] AMBIGUOUS {article_id} ({len(pmids)} hits) → {pmid} [{strategy}]")
        else:
            status = "not_indexed"
            pmid   = None
            stats["not_found"] += 1
            log.info(f"  [{i}/{stats['total']}] NOT FOUND {article_id} (query: {search_term})")

        if not dry_run:
            if retry_mode:
                # UPDATE existing row
                cur.execute("""
                    UPDATE article_currency
                    SET    pubmed_id = ?, last_checked = ?, currency_status = ?
                    WHERE  article_id = ?
                """, (pmid, TODAY, status, article_id))
            else:
                cur.execute("""
                    INSERT OR IGNORE INTO article_currency
                        (article_id, pubmed_id, last_checked, currency_status)
                    VALUES (?, ?, ?, ?)
                """, (article_id, pmid, TODAY, status))

        # Commit every 100 rows to preserve progress
        if not dry_run and i % 100 == 0:
            conn.commit()
            log.info(f"  Progress commit at {i}/{stats['total']}")

    if not dry_run:
        conn.commit()
    log.info(f"[A2] Done — {stats}")
    return stats


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE B — CURRENCY CHECK
# ═══════════════════════════════════════════════════════════════════════════════

def efetch_batch(pmids: list) -> dict:
    """
    Batch-fetch metadata for multiple PMIDs in a single NCBI request.
    Returns {pmid_str: {"title": ..., "pub_date": ..., "first_author": ...}}.
    Silently returns empty dict on failure.
    """
    if not pmids:
        return {}
    resp = ncbi_get("efetch.fcgi", {
        "db":      "pubmed",
        "id":      ",".join(pmids),
        "rettype": "xml",
        "retmode": "xml",
    })
    time.sleep(RATE_DELAY)
    if not resp:
        return {}
    results = {}
    try:
        root = ET.fromstring(resp)
        for art in root.findall(".//PubmedArticle"):
            pmid_el = art.find(".//PMID")
            if pmid_el is None or not pmid_el.text:
                continue
            pmid_val = pmid_el.text.strip()

            title_el = art.find(".//ArticleTitle")
            title    = (title_el.text or "") if title_el is not None else ""

            year_el  = art.find(".//PubDate/Year")
            med_el   = art.find(".//PubDate/MedlineDate")
            if year_el is not None and year_el.text:
                pub_date = year_el.text
            elif med_el is not None and med_el.text:
                pub_date = med_el.text[:4]
            else:
                pub_date = ""

            author_el    = art.find(".//AuthorList/Author/LastName")
            first_author = (author_el.text or "") if author_el is not None else ""

            results[pmid_val] = {
                "title":        title[:500],
                "pub_date":     pub_date,
                "first_author": first_author,
            }
    except ET.ParseError:
        pass
    return results


# ─── Title-relevance helpers ──────────────────────────────────────────────────

# Words stripped before computing overlap between original and newer titles.
# Anything that appears in nearly every medical paper title is excluded.
_STOPWORDS = {
    'a', 'an', 'the', 'of', 'in', 'for', 'with', 'to', 'and', 'or', 'by',
    'on', 'at', 'is', 'are', 'was', 'were', 'from', 'as', 'its', 'it',
    'this', 'that', 'be', 'has', 'have', 'had', 'use', 'used', 'using',
    'due', 'after', 'before', 'during', 'between', 'among', 'through',
    'within', 'without', 'including', 'following', 'compared', 'versus',
    'vs', 'per', 'not', 'no', 'than', 'their', 'other', 'each', 'more',
    # Ubiquitous clinical/research meta-words
    'patients', 'patient', 'adults', 'adult', 'children', 'child',
    'women', 'men', 'risk', 'based', 'associated', 'effect', 'effects',
    'impact', 'role', 'review', 'systematic', 'meta', 'analysis',
    'randomized', 'controlled', 'trial', 'study', 'cohort', 'clinical',
    'practice', 'guideline', 'guidelines', 'recommendation',
    'recommendations', 'statement', 'update', 'updated', 'care', 'new',
    'report', 'summary', 'executive', 'policy', 'american', 'national',
    'evidence', 'outcomes', 'outcome', 'results', 'data', 'case',
}

# Clinical category words — too generic for topic overlap, but signal blueprint
# categories (diagnosis, treatment, management, etc.) that map to ABFM domains.
# These are FILTERED OUT of overlap comparison but CAPTURED in title_signals.
# Forward use: cross-reference article_currency.title_signals against blueprint
# to verify or enrich category assignments at the article level.
_CLINICAL_SIGNALS = {
    # Diagnostic axis
    'diagnosis', 'diagnoses', 'diagnostic', 'diagnostics', 'diagnose',
    'evaluation', 'evaluating', 'evaluate', 'workup',
    'assessment', 'assessments', 'assess',
    'screening', 'screen',
    # Treatment / management axis
    'treatment', 'treatments', 'treating', 'treat',
    'management', 'managing', 'manage',
    'therapy', 'therapies', 'therapeutic',
    'intervention', 'interventions',
    # Prevention axis
    'prevention', 'preventing', 'preventive', 'preventative',
    # Disease-type words (generic, not topic-specific)
    'disorder', 'disorders',
    'disease', 'diseases',
    'infection', 'infections', 'infectious',
    'syndrome', 'syndromes',
    'condition', 'conditions',
    'complications', 'complication',
}


def extract_title_parts(title: str) -> tuple:
    """
    Split a title into two buckets:

    content_kw  — meaningful topic words used for overlap comparison
                  (e.g. 'diabetes', 'copd', 'hypertension')
    signals     — clinical category words filtered out of overlap but
                  captured for blueprint tracking
                  (e.g. 'diagnosis', 'management', 'screening')

    Returns (content_kw: set, signals: list)

    "Chronic Obstructive Pulmonary Disease: Diagnosis and Management"
      → content_kw = {'chronic', 'obstructive', 'pulmonary'}
      → signals    = ['disease', 'diagnosis', 'management']
    """
    if not title:
        return set(), []
    words    = re.findall(r'[a-zA-Z]+', title.lower())
    content  = set()
    signals  = []
    for w in words:
        if len(w) < 4:
            continue
        if w in _STOPWORDS:
            continue
        if w in _CLINICAL_SIGNALS:
            if w not in signals:        # deduplicate
                signals.append(w)
        else:
            content.add(w)
    return content, signals


def title_keywords(title: str) -> set:
    """
    Extract content-only keywords from a title (overlap comparison use).
    Wraps extract_title_parts() — discards signals, returns content set only.

    Use extract_title_parts() directly when you also need the signal list.
    """
    content, _ = extract_title_parts(title)
    return content


def check_single_article(article_id: str, pmid: str, year) -> dict:
    """
    Currency check for one article:
      1. efetch → confirm metadata, store pub_date + pub_title
      2. esearch for newer pubs by same first author after publication year
      3. Batch efetch all newer candidates → title-relevance filter
         (≥1 meaningful content word must overlap between original + newer title)
      4. Classify: current | updated (1 relevant) | check_needed (2+ relevant)

    The relevance filter prevents false positives from prolific authors who
    publish unrelated papers. Only newer articles that share topic vocabulary
    with the original are counted as potential updates.
    """
    import json as _json

    result = {
        "article_id":           article_id,
        "pub_title":            None,
        "pub_date":             None,
        "newer_version_pmid":   None,
        "newer_version_date":   None,
        "newer_version_title":  None,
        "currency_status":      "current",
        "title_signals":        "[]",
    }

    # Step 1: efetch original article metadata
    meta = efetch_article(pmid)
    if not meta:
        result["currency_status"] = "not_indexed"
        return result

    result["pub_title"] = meta["title"]
    result["pub_date"]  = meta["pub_date"]
    first_author        = meta["first_author"]

    # Extract content keywords + clinical signals from original title
    orig_kw, signals        = extract_title_parts(meta["title"])
    result["title_signals"] = _json.dumps(signals) if signals else "[]"

    if not first_author or not year:
        result["currency_status"] = "current"
        return result

    # Step 2: esearch for newer publications by same first author
    search_start = int(year) + 1
    if search_start > CURRENT_YEAR:
        result["currency_status"] = "current"
        return result

    newer_query = f"{first_author}[Author] AND {search_start}:{CURRENT_YEAR}[dp]"
    newer_pmids = [p for p in esearch(newer_query, retmax=5) if p != pmid]

    if not newer_pmids:
        result["currency_status"] = "current"
        return result

    # Step 3: Batch efetch all newer candidates (one API call)
    newer_meta_map = efetch_batch(newer_pmids)

    # Step 4: Title-relevance filter — require ≥1 content-word overlap
    # Uses orig_kw (content only — clinical signals already stripped)
    relevant = []
    for np in newer_pmids:
        nm = newer_meta_map.get(np)
        if not nm:
            continue
        newer_kw, _ = extract_title_parts(nm["title"])
        overlap     = orig_kw & newer_kw
        if overlap:
            relevant.append((np, nm, overlap))
            log.debug(f"    RELEVANT {np}: overlap={overlap} — {nm['title'][:70]}")
        else:
            log.debug(f"    FILTERED {np}: no overlap — {nm['title'][:70]}")

    if not relevant:
        result["currency_status"] = "current"
        log.info(
            f"  → FILTERED to current "
            f"(0/{len(newer_pmids)} newer passed relevance; "
            f"orig_kw={orig_kw}, signals={signals})"
        )
        return result

    # Store top relevant result
    top_pmid, top_meta, top_overlap = relevant[0]
    result["newer_version_pmid"]  = top_pmid
    result["newer_version_date"]  = top_meta["pub_date"]
    result["newer_version_title"] = top_meta["title"]
    result["currency_status"]     = "updated" if len(relevant) == 1 else "check_needed"
    log.info(
        f"  → {result['currency_status'].upper()}: "
        f"{len(relevant)}/{len(newer_pmids)} newer passed relevance "
        f"(overlap: {top_overlap}, signals: {signals})"
    )
    return result


def run_phase_b(
    conn: sqlite3.Connection,
    dry_run: bool,
    limit: int | None,
    recheck: bool = False,
) -> dict:
    """
    Phase B: Currency check for articles with a resolved pubmed_id.

    Normal mode (recheck=False):
      Processes articles with currency_status IN ('pending', 'check_needed').

    Recheck mode (recheck=True, --recheck flag):
      Also re-processes 'updated' rows — useful after logic changes (e.g., adding
      the title-relevance filter) to re-evaluate previously flagged articles.
      Does NOT re-check 'current' rows (no newer was found; logic is identical).
    """
    cur = conn.cursor()

    # article_currency won't exist in dry-run mode — return empty gracefully
    table_exists = cur.execute("""
        SELECT COUNT(*) FROM sqlite_master
        WHERE type='table' AND name='article_currency'
    """).fetchone()[0]

    if not table_exists:
        log.info("[B] article_currency table not found — skipping (dry-run or Phase A not yet run)")
        return {"total": 0, "current": 0, "updated": 0, "check_needed": 0, "not_indexed": 0}

    status_filter = "('pending', 'check_needed', 'updated')" if recheck else "('pending', 'check_needed')"
    if recheck:
        log.info("[B] RECHECK mode — also re-processing 'updated' rows with new relevance filter")

    query = f"""
        SELECT  ac.article_id, ac.pubmed_id, a.year
        FROM    article_currency ac
        JOIN    articles a ON ac.article_id = a.article_id
        WHERE   ac.pubmed_id IS NOT NULL
          AND   ac.currency_status IN {status_filter}
        ORDER BY a.citation_count DESC
    """
    if limit:
        query += f" LIMIT {limit}"
    rows = cur.execute(query).fetchall()

    stats   = {"total": len(rows), "current": 0, "updated": 0,
               "check_needed": 0, "not_indexed": 0}
    log.info(f"[B] {len(rows)} articles queued for currency check")

    for i, (article_id, pmid, year) in enumerate(rows, 1):
        log.info(f"  [{i}/{stats['total']}] {article_id}  PMID {pmid}")
        update = check_single_article(article_id, pmid, year)
        status = update["currency_status"]
        stats[status] = stats.get(status, 0) + 1

        if not dry_run:
            cur.execute("""
                UPDATE article_currency SET
                    pub_title           = ?,
                    pub_date            = ?,
                    last_checked        = ?,
                    newer_version_pmid  = ?,
                    newer_version_date  = ?,
                    newer_version_title = ?,
                    currency_status     = ?,
                    title_signals       = ?
                WHERE article_id = ?
            """, (
                update["pub_title"],
                update["pub_date"],
                TODAY,
                update["newer_version_pmid"],
                update["newer_version_date"],
                update["newer_version_title"],
                status,
                update.get("title_signals", "[]"),
                article_id,
            ))

        if not dry_run and i % 50 == 0:
            conn.commit()
            log.info(f"  Progress commit at {i}/{stats['total']} — {stats}")

    if not dry_run:
        conn.commit()
    log.info(f"[B] Done — {stats}")
    return stats


# ═══════════════════════════════════════════════════════════════════════════════
# SUMMARY REPORT
# ═══════════════════════════════════════════════════════════════════════════════

def print_summary(conn: sqlite3.Connection):
    """Print a status breakdown of the article_currency table."""
    cur = conn.cursor()
    rows = cur.execute("""
        SELECT  currency_status, COUNT(*) as n
        FROM    article_currency
        GROUP BY currency_status
        ORDER BY n DESC
    """).fetchall()

    total_in_table = sum(n for _, n in rows)
    total_articles = cur.execute("SELECT COUNT(*) FROM articles").fetchone()[0]

    log.info("")
    log.info("══════════════════════════════════════════")
    log.info("  article_currency — Final State")
    log.info("══════════════════════════════════════════")
    for status, n in rows:
        bar = "█" * min(int(n / 20), 40)
        log.info(f"  {(status or 'NULL'):15s}  {n:5d}  {bar}")
    log.info(f"  {'─'*40}")
    log.info(f"  {'IN TABLE':15s}  {total_in_table:5d}  / {total_articles} total articles")
    log.info("══════════════════════════════════════════")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Layer 2: Article Currency via PubMed"
    )
    parser.add_argument("--phase-a",  action="store_true",
                        help="PMID resolution only (skip Phase B)")
    parser.add_argument("--phase-b",  action="store_true",
                        help="Currency check only (Phase A must have run first)")
    parser.add_argument("--dry-run",  action="store_true",
                        help="Print plan without writing to DB")
    parser.add_argument("--limit",    type=int, default=None,
                        help="Process only first N articles (useful for testing)")
    parser.add_argument("--retry-not-indexed", action="store_true",
                        help="Re-run Phase A on existing not_indexed rows only (UPDATE, not INSERT)")
    parser.add_argument("--recheck", action="store_true",
                        help="Phase B: also re-process 'updated' rows (use after logic changes)")
    args = parser.parse_args()

    run_a   = not args.phase_b   # run A unless --phase-b explicitly set
    run_b   = not args.phase_a   # run B unless --phase-a explicitly set
    retry   = args.retry_not_indexed
    recheck = args.recheck

    log.info("══════════════════════════════════════════")
    log.info(f"  build_article_currency.py  {'[DRY RUN]' if args.dry_run else ''}")
    log.info(f"  DB:       {DB_PATH}")
    log.info(f"  NCBI key: {'SET (10 req/s)' if NCBI_API_KEY else 'NOT SET (3 req/s)'}")
    log.info(
        f"  Phases:   {'A ' if run_a else ''}{'B' if run_b else ''}"
        f"{' [RETRY not_indexed]' if retry else ''}"
        f"{' [RECHECK updated]' if recheck else ''}"
    )
    if args.limit:
        log.info(f"  Limit:    {args.limit} articles")
    log.info("══════════════════════════════════════════")

    conn = sqlite3.connect(DB_PATH)

    # Ensure table exists
    if not args.dry_run:
        conn.execute(CREATE_ARTICLE_CURRENCY)
        conn.commit()
        log.info("article_currency table ensured")
        # Idempotent column migration + backfill (no-ops if already done)
        added = ensure_title_signals_column(conn)
        if added:
            backfill_title_signals(conn)
        else:
            # Column exists — backfill any rows that still have NULL signals
            backfill_title_signals(conn)
    else:
        log.info("[DRY RUN] Would create article_currency table")
        log.info(f"[DRY RUN] Schema:\n{CREATE_ARTICLE_CURRENCY}")

    # ── Phase A ────────────────────────────────────────────────────────────────
    if run_a:
        log.info("")
        log.info("── Phase A: PMID Resolution ──────────────")
        seeded   = seed_from_pmid_cache(conn, args.dry_run)
        a2_stats = resolve_pmids_via_esearch(conn, args.dry_run, args.limit, retry_mode=retry)
        log.info(
            f"Phase A complete: {seeded} seeded from cache + "
            f"{a2_stats['resolved']} resolved + "
            f"{a2_stats['ambiguous']} ambiguous + "
            f"{a2_stats['not_found']} not found"
        )

    # ── Phase B ────────────────────────────────────────────────────────────────
    if run_b:
        log.info("")
        log.info("── Phase B: Currency Check ───────────────")
        b_stats = run_phase_b(conn, args.dry_run, args.limit, recheck=recheck)
        log.info(
            f"Phase B complete: {b_stats.get('current', 0)} current, "
            f"{b_stats.get('updated', 0)} updated, "
            f"{b_stats.get('check_needed', 0)} check_needed, "
            f"{b_stats.get('not_indexed', 0)} not_indexed"
        )

    # ── Summary ────────────────────────────────────────────────────────────────
    if not args.dry_run:
        print_summary(conn)

    conn.close()
    log.info("Done.")


if __name__ == "__main__":
    main()
