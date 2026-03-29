#!/usr/bin/env python3
"""
AAFP Citations — Second-Pass Matcher (v1)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Attempts to link remaining unmatched AAFP citations to articles using
strategies that go beyond what aafp_brq_import.py can do.

Background:
  After v3 import: 797 xref rows (586 Q linked, 48%)
  Unmatched pool: 784 citations — most are articles not yet in DB,
  but ~200+ AFP citations are in DB with non-standard clean_ref format
  (no vol/page), causing vol/page lookup to miss them.

Strategies (applied in order, first match wins per citation):
  S2: Space-tolerant vol/page + author  — catches minor formatting noise
  S3: AFP title keyword + year          — AFP articles w/ summary-style clean_ref
  S4: Cochrane CD number                — CD-number in citation -> DB clean_ref
  S5: Guideline/society keyword + year  — USPSTF/Task Force/CDC statements

Run modes:
  python aafp_ref_match_v2.py            ← run all strategies, write results
  python aafp_ref_match_v2.py --dry-run  ← preview matches, no DB writes
  python aafp_ref_match_v2.py --stats    ← current match counts only, no processing
  python aafp_ref_match_v2.py --verbose  ← show every match found

Design rule: precision over recall. If multiple articles match a citation,
skip it (ambiguous). One unambiguous match only.
"""

import re
import sqlite3
import sys
from pathlib import Path

# ══════════════════════════════════════════════════════════════════════
# PATHS
# ══════════════════════════════════════════════════════════════════════
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH      = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"
# ══════════════════════════════════════════════════════════════════════

DRY_RUN = "--dry-run" in sys.argv
STATS   = "--stats"   in sys.argv
VERBOSE = "--verbose" in sys.argv


# ─────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────

# Journals to strip when extracting title from citation
JOURNAL_STRIP_RE = re.compile(
    r'(?:\.\s*|\s+)(?:Am Fam Physician|JAMA|N Engl J Med|Lancet|BMJ|Ann Intern Med|'
    r'Cochrane Database Syst Rev|Cochrane|Circulation|Pediatrics|Chest|'
    r'Am J Gastroenterol|Am J Cardiol|Am J Obstet|Obstet Gynecol|'
    r'J Clin Sleep Med|J Clin Endocrinol|Mayo Clin Proc|Crit Care Med|'
    r'Emerg Med Clin|Clin Infect Dis|Neurology|Gastroenterology|'
    r'Arch Intern Med|Arch Pediatr|CMAJ|Spine|Stroke|Diabetes Care|'
    r'Am J Psychiatry|J Am Coll Cardiol|Hypertension)[\s\d.,;(]',
    re.I
)

# Vol/page pattern with optional spaces (S2)
VOL_SPACE_RE = re.compile(r'(\d{4});\s*(\d+)\s*\((\d+)\)\s*:\s*(\d+)')

# Strict vol/page (used to build DB index)
VOL_STRICT_RE = re.compile(r'(\d{4});(\d+)\((\d+)\):(\d+)')

# Cochrane CD number
CD_RE = re.compile(r'\bCD\d{6,7}\b', re.I)

# Year extraction
YEAR_RE = re.compile(r'\b(19|20)\d{2}\b')

# Stopwords for keyword matching
STOPWORDS = {
    'the', 'and', 'for', 'with', 'from', 'that', 'this', 'are', 'was', 'were',
    'has', 'have', 'been', 'their', 'after', 'before', 'during', 'about', 'more',
    'also', 'some', 'than', 'when', 'into', 'between', 'among', 'within', 'across',
    'using', 'based', 'evidence', 'review', 'update', 'updated', 'clinical', 'practice',
    'management', 'treatment', 'diagnosis', 'screening', 'prevention', 'evaluation',
    'patients', 'patient', 'adults', 'adult', 'children', 'child', 'care', 'health',
    'disease', 'disorders', 'disorder', 'syndrome', 'therapy', 'approach', 'strategies',
    'associated', 'related', 'primary', 'common', 'chronic', 'acute', 'versus', 'effect',
    'effects', 'risk', 'factors', 'outcomes', 'american', 'national', 'society', 'guideline',
    'guidelines', 'statement', 'recommendations', 'recommendation', 'report', 'systematic',
}

AFP_MARKER  = 'Am Fam Physician'
COCHRANE_MARKER = 'Cochrane'


# ─────────────────────────────────────────────────────────────────────
# UTILITY: AUTHOR NORMALIZATION
# ─────────────────────────────────────────────────────────────────────
def norm_author(ref: str) -> str:
    """Extract and normalize first author token."""
    token = re.split(r'[,\s]', ref.strip())[0]
    return token.lower()


# ─────────────────────────────────────────────────────────────────────
# UTILITY: YEAR EXTRACTION
# ─────────────────────────────────────────────────────────────────────
def extract_year(ref: str) -> str | None:
    """Extract first 4-digit year from citation."""
    m = YEAR_RE.search(ref)
    return m.group(0) if m else None


# ─────────────────────────────────────────────────────────────────────
# UTILITY: TITLE EXTRACTION
# ─────────────────────────────────────────────────────────────────────
def extract_title_portion(ref: str) -> str:
    """
    Extract the title-like segment from a citation string.

    Handles two main formats:
      1. "Author, Author2: Title of article. Journal YYYY;..."
      2. "Author. Title of article. Journal. YYYY;..."

    Returns the portion between the author block and the journal abbreviation.
    """
    # Strip trailing punctuation noise
    ref = ref.strip().rstrip('.')

    # Find the title start: after first ': ' (colon format) or first '. ' (period format)
    colon_pos = ref.find(': ')
    period_pos = ref.find('. ')

    if colon_pos > 0 and (period_pos < 0 or colon_pos <= period_pos + 30):
        title_start = colon_pos + 2
    elif period_pos > 0:
        title_start = period_pos + 2
    else:
        title_start = 0

    title_portion = ref[title_start:]

    # Strip journal + vol/page from the end
    m = JOURNAL_STRIP_RE.search(title_portion)
    if m:
        title_portion = title_portion[:m.start()]
    else:
        # Fallback: strip trailing year and everything after
        title_portion = YEAR_RE.split(title_portion)[0]

    return title_portion.strip().rstrip(':.,; ')


# ─────────────────────────────────────────────────────────────────────
# UTILITY: KEYWORD TOKENIZATION
# ─────────────────────────────────────────────────────────────────────
def significant_words(text: str) -> list[str]:
    """
    Extract significant lowercase words: 4+ chars, not in STOPWORDS.
    Returns list (order preserved, no dedup — caller uses set() if needed).
    """
    words = re.findall(r'\b[a-z]{4,}\b', text.lower())
    return [w for w in words if w not in STOPWORDS]


# ─────────────────────────────────────────────────────────────────────
# BUILD INDEXES
# ─────────────────────────────────────────────────────────────────────
def build_indexes(conn: sqlite3.Connection) -> tuple[dict, dict, list, list]:
    """
    Returns four indexes built from articles table:
      vol_space_map: {(year, vol, issue, page): (article_id, author1_norm)}  — S2
      title_index:   [(article_id, year_str, word_set, title, clean_ref)]     — S3/S5
      cd_list:       [(cd_num_upper, article_id)]                             — S4
      guideline_idx: [(article_id, year_str, word_set, clean_ref)]           — S5
    """
    cur = conn.cursor()
    cur.execute("SELECT article_id, clean_ref, year, title FROM articles WHERE clean_ref IS NOT NULL")
    rows = cur.fetchall()

    vol_space_map = {}
    title_index   = []
    cd_list       = []

    for article_id, clean_ref, year, title in rows:
        year_str = str(year).strip() if year else None

        # S2 index: space-tolerant vol/page
        m = VOL_SPACE_RE.search(clean_ref)
        if m:
            key = (m.group(1), m.group(2).strip(), m.group(3).strip(), m.group(4).strip())
            author = norm_author(clean_ref)
            vol_space_map[key] = (article_id, author)

        # S3/S5 title index: need meaningful title
        title_text = title or ''
        words = set(significant_words(title_text))
        if len(words) >= 3:
            title_index.append((article_id, year_str, words, title_text, clean_ref or ''))

        # S4 CD number index
        m_cd = CD_RE.search(clean_ref)
        if m_cd:
            cd_list.append((m_cd.group(0).upper(), article_id))

    print(f"  vol_space index: {len(vol_space_map)} keys")
    print(f"  title index:     {len(title_index)} articles")
    print(f"  cochrane index:  {len(cd_list)} CD entries")

    return vol_space_map, title_index, cd_list


# ─────────────────────────────────────────────────────────────────────
# STRATEGY 2: SPACE-TOLERANT VOL/PAGE + AUTHOR
# ─────────────────────────────────────────────────────────────────────
def match_s2_space_volpage(ref: str, vol_space_map: dict) -> tuple[str | None, str]:
    """
    Space-tolerant vol/page + author1 match.
    Identical to Strategy 1 in import but with spaces allowed in vol/page pattern.
    """
    m = VOL_SPACE_RE.search(ref)
    if not m:
        return None, 'unmatched'
    key = (m.group(1), m.group(2).strip(), m.group(3).strip(), m.group(4).strip())
    if key in vol_space_map:
        article_id, db_author = vol_space_map[key]
        if norm_author(ref) == db_author:
            return article_id, 's2_space_volpage'
    return None, 'unmatched'


# ─────────────────────────────────────────────────────────────────────
# STRATEGY 3: AFP TITLE KEYWORD + YEAR
# ─────────────────────────────────────────────────────────────────────
def match_s3_afp_title(ref: str, year: str | None, title_index: list,
                        min_keywords: int = 3) -> tuple[str | None, str]:
    """
    Match AFP citation by title keywords + year.
    Only considers DB articles whose clean_ref contains 'Am Fam Physician'.
    Requires: year match (if available) + ≥min_keywords words in common.
    Ambiguous matches (2+ candidates) are skipped for safety.
    """
    title_portion = extract_title_portion(ref)
    if not title_portion:
        return None, 'unmatched'

    citation_words = set(significant_words(title_portion))
    if len(citation_words) < min_keywords:
        return None, 'unmatched'

    matches = []
    for article_id, art_year, art_words, art_title, clean_ref in title_index:
        # Must be AFP article
        if AFP_MARKER not in clean_ref:
            continue
        # Year: if both are known, they must match
        if year and art_year and year != art_year:
            continue
        # Keyword overlap
        overlap = citation_words & art_words
        if len(overlap) >= min_keywords:
            matches.append((article_id, len(overlap), art_title))

    if len(matches) == 1:
        return matches[0][0], 's3_afp_title'
    elif len(matches) > 1:
        # Tie-break: if one candidate has strictly more overlap, use it
        matches.sort(key=lambda x: x[1], reverse=True)
        if matches[0][1] > matches[1][1] + 1:  # clear winner (+2 extra words)
            return matches[0][0], 's3_afp_title'
    return None, 'unmatched'


# ─────────────────────────────────────────────────────────────────────
# STRATEGY 4: COCHRANE CD NUMBER
# ─────────────────────────────────────────────────────────────────────
def match_s4_cochrane_cd(ref: str, cd_list: list) -> tuple[str | None, str]:
    """
    Match Cochrane CD number from citation against DB articles.
    """
    m = CD_RE.search(ref)
    if not m:
        return None, 'unmatched'
    cd_num = m.group(0).upper()
    matches = [art_id for cd, art_id in cd_list if cd == cd_num]
    if len(matches) == 1:
        return matches[0], 's4_cochrane_cd'
    return None, 'unmatched'


# ─────────────────────────────────────────────────────────────────────
# STRATEGY 5: GUIDELINE/SOCIETY KEYWORD + YEAR
# ─────────────────────────────────────────────────────────────────────
GUIDELINE_MARKERS = re.compile(
    r'\b(task force|preventive services|uspstf|recommendation|practice guideline|'
    r'clinical practice|position statement|consensus|advisory committee|'
    r'centers for disease control|cdc|acip|acog|aha|acc|ats|idsa|acs|aafp|aap|'
    r'american academy|american college|american association|american society)\b',
    re.I
)

def match_s5_guideline_title(ref: str, year: str | None, title_index: list,
                              min_keywords: int = 4) -> tuple[str | None, str]:
    """
    Match guideline/society citations by title keyword + year.
    Higher keyword threshold (4) than AFP to reduce false positives.
    Does NOT restrict to AFP — covers all article types.

    Author check: if the citation has an identifiable first author surname
    (personal name, not an organization), that surname must appear in the
    matched article's clean_ref. Prevents cross-guideline false positives
    where two different articles from the same society share keyword sets.
    """
    if not GUIDELINE_MARKERS.search(ref):
        return None, 'unmatched'

    # Detect named first author (personal surname — starts with capital letter
    # before first comma or semicolon, not an org name keyword)
    first_token = re.split(r'[,;]', ref.strip())[0].strip()
    ORG_STARTS = re.compile(
        r'^(US |American |National |Centers |Division |Authors|Statement|Final|'
        r'ACC|AHA|AAN|AAP|ACOG|AAFP|Joint|Task|WHO|CDC|Moyer|HPV|Screening)',
        re.I
    )
    has_named_author = bool(first_token) and not ORG_STARTS.match(first_token)
    author_surname = first_token.split()[0].lower() if has_named_author else None

    # For guidelines, the whole citation IS the title (no author to strip)
    # Extract meaningful content — remove organization names and boilerplate
    title_portion = re.sub(
        r'\b(us preventive services task force|centers for disease control|'
        r'american academy of|american college of|american association of|'
        r'american society of|final recommendation|recommendation statement|'
        r'practice guideline|clinical practice)\b',
        ' ', ref, flags=re.I
    ).strip()

    citation_words = set(significant_words(title_portion))
    if len(citation_words) < min_keywords:
        return None, 'unmatched'

    matches = []
    for article_id, art_year, art_words, art_title, clean_ref in title_index:
        if year and art_year and year != art_year:
            continue
        # Author check: if named author, their surname must appear in clean_ref
        if author_surname and author_surname not in clean_ref.lower():
            continue
        overlap = citation_words & art_words
        if len(overlap) >= min_keywords:
            matches.append((article_id, len(overlap), art_title, clean_ref))

    if len(matches) == 1:
        return matches[0][0], 's5_guideline'
    elif len(matches) > 1:
        matches.sort(key=lambda x: x[1], reverse=True)
        if matches[0][1] > matches[1][1] + 1:
            return matches[0][0], 's5_guideline'
    return None, 'unmatched'


# ─────────────────────────────────────────────────────────────────────
# MAIN MATCHING PASS
# ─────────────────────────────────────────────────────────────────────
def run_second_pass(conn: sqlite3.Connection):
    cur = conn.cursor()

    # Load all unmatched citations with raw text
    cur.execute("""
        SELECT ac.citation_id, ac.aafp_qid, cr.raw_text
        FROM aafp_citations ac
        JOIN aafp_citation_raw cr ON ac.citation_id = cr.citation_id
        WHERE ac.match_status = 'unmatched'
    """)
    unmatched = cur.fetchall()
    print(f"\nUnmatched citations to process: {len(unmatched)}")

    print("Building article indexes...")
    vol_space_map, title_index, cd_list = build_indexes(conn)

    stats = {
        's2_space_volpage': 0,
        's3_afp_title':     0,
        's4_cochrane_cd':   0,
        's5_guideline':     0,
        'still_unmatched':  0,
        'skipped_empty':    0,
    }

    updates = []    # (article_id, match_status, citation_id)
    new_xref = []   # (aafp_qid, article_id, match_status)

    for citation_id, aafp_qid, raw_text in unmatched:
        ref = (raw_text or '').strip()

        if not ref or len(ref) < 15:
            stats['skipped_empty'] += 1
            continue

        year = extract_year(ref)

        # Try strategies in order
        article_id, status = None, 'unmatched'

        if article_id is None:
            article_id, status = match_s2_space_volpage(ref, vol_space_map)

        if article_id is None and AFP_MARKER in ref:
            article_id, status = match_s3_afp_title(ref, year, title_index)

        if article_id is None and COCHRANE_MARKER in ref:
            article_id, status = match_s4_cochrane_cd(ref, cd_list)

        if article_id is None:
            article_id, status = match_s5_guideline_title(ref, year, title_index)

        if article_id:
            stats[status] = stats.get(status, 0) + 1
            updates.append((article_id, status, citation_id))
            new_xref.append((aafp_qid, article_id, status))
            if VERBOSE:
                print(f"  [{status}] {citation_id}: {ref[:80]}")
                print(f"           -> {article_id}")
        else:
            stats['still_unmatched'] += 1

    # ── Print results ──
    total_new = sum(v for k, v in stats.items() if k not in ('still_unmatched', 'skipped_empty'))
    print(f"\n══ SECOND-PASS RESULTS ═══════════════════════════════════════")
    print(f"  Total processed:          {len(unmatched)}")
    print(f"  Skipped (empty/truncated): {stats['skipped_empty']}")
    print(f"")
    print(f"  NEW MATCHES:              {total_new}")
    print(f"    S2 space vol/page:      {stats['s2_space_volpage']}")
    print(f"    S3 AFP title keyword:   {stats['s3_afp_title']}")
    print(f"    S4 Cochrane CD#:        {stats['s4_cochrane_cd']}")
    print(f"    S5 guideline keyword:   {stats['s5_guideline']}")
    print(f"")
    print(f"  Still unmatched:          {stats['still_unmatched']}")

    if DRY_RUN:
        print(f"\n[DRY RUN — no changes written]")
        return

    # ── Write updates ──
    updated_citations = 0
    for article_id, match_status, citation_id in updates:
        cur.execute("""
            UPDATE aafp_citations
            SET article_id = ?, match_status = ?
            WHERE citation_id = ?
        """, (article_id, match_status, citation_id))
        updated_citations += cur.rowcount

    # ── Write xref (dedupe by aafp_qid + article_id) ──
    xref_seen = set()
    xref_inserted = 0
    for aafp_qid, article_id, match_status in new_xref:
        key = (aafp_qid, article_id)
        if key in xref_seen:
            continue
        xref_seen.add(key)
        cur.execute("""
            INSERT OR IGNORE INTO aafp_qid_art_xref (aafp_qid, article_id, match_status)
            VALUES (?, ?, ?)
        """, (aafp_qid, article_id, match_status))
        xref_inserted += cur.rowcount

    conn.commit()
    print(f"\n  DB writes:")
    print(f"    aafp_citations updated:   {updated_citations}")
    print(f"    aafp_qid_art_xref added:  {xref_inserted}")

    # ── Post-write summary ──
    cur.execute("SELECT match_status, COUNT(*) FROM aafp_citations GROUP BY match_status ORDER BY COUNT(*) DESC")
    print(f"\n  aafp_citations match_status breakdown:")
    total_cit = 0
    for status, count in cur.fetchall():
        print(f"    {status:<25} {count}")
        total_cit += count

    cur.execute("SELECT COUNT(*) FROM aafp_qid_art_xref")
    xref_total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT aafp_qid) FROM aafp_qid_art_xref")
    unique_q = cur.fetchone()[0]
    print(f"\n  aafp_qid_art_xref: {xref_total} rows ({unique_q} unique questions linked)")
    cur.execute("SELECT COUNT(*) FROM aafp_questions")
    total_q = cur.fetchone()[0]
    print(f"  Link rate: {unique_q}/{total_q} ({unique_q/total_q*100:.1f}%)")


# ─────────────────────────────────────────────────────────────────────
# STATS MODE
# ─────────────────────────────────────────────────────────────────────
def run_stats_only(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.execute("SELECT match_status, COUNT(*) FROM aafp_citations GROUP BY match_status ORDER BY COUNT(*) DESC")
    print("aafp_citations match_status:")
    for row in cur.fetchall():
        print(f"  {row[0]:<25} {row[1]}")
    cur.execute("SELECT COUNT(*) FROM aafp_qid_art_xref")
    print(f"\naafp_qid_art_xref rows: {cur.fetchone()[0]}")
    cur.execute("SELECT COUNT(DISTINCT aafp_qid) FROM aafp_qid_art_xref")
    print(f"Unique questions linked: {cur.fetchone()[0]}")


# ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if "--help" in sys.argv:
        print(__doc__)
        sys.exit(0)

    if not DB_PATH.exists():
        print(f"ERROR: DB not found:\n  {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        if STATS:
            run_stats_only(conn)
        else:
            run_second_pass(conn)
    finally:
        conn.close()
        print(f"\n  DB -> {DB_PATH}")
