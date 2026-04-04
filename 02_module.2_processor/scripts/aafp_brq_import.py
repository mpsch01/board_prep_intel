#!/usr/bin/env python3
"""
AAFP Board Review Questions — DB Import (v3)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Reads:   _archive_/02_question_bank/aafp_initial_staging/aafp_brq_staging.json
Writes:  00_database/db/ite_intelligence.db → 4 tables + xref

Tables:
  aafp_questions      stem + MC choices only
  aafp_explanations   correct_letter + explanation (1:1 with aafp_questions)
  aafp_citations      one row per parsed citation — article linkage, match_status
  aafp_citation_raw   raw citation archive — full untruncated text, lookup coordinates
  aafp_qid_art_xref   parallel to qid_art_xref — populated from aafp_citations

Citation splitting:
  Multi-citation refs ("...2018. 2) NextAuthor...") are split before matching.
  Each individual citation gets its own citation_id (e.g. AAFP-49733-C1),
  its own matching pass, and its own rows in aafp_citations + aafp_citation_raw.

Matching strategies (per individual citation):
  Strategy 0: exact clean_ref match (case-insensitive)
  Strategy 1: vol/page dupe finder — year + vol + issue + start_page + author1
              All five must align. Catches formatting noise only.

Run:
  python aafp_brq_import.py              ← INSERT OR IGNORE (incremental)
  python aafp_brq_import.py --rebuild    ← DROP all + recreate + full re-import
  python aafp_brq_import.py --dry-run    ← preview stats, no writes
  python aafp_brq_import.py --stats      ← QC summary from existing DB
"""

import re
import json
import sqlite3
import sys
from pathlib import Path

# ══════════════════════════════════════════════════════════════════════
# PATHS
# ══════════════════════════════════════════════════════════════════════
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent

DB_PATH      = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"
STAGING_FILE = PROJECT_ROOT / "_archive_" / "02_question_bank" / "aafp_initial_staging" / "aafp_brq_staging.json"
# ══════════════════════════════════════════════════════════════════════

DRY_RUN = "--dry-run" in sys.argv
STATS   = "--stats"   in sys.argv
REBUILD = "--rebuild" in sys.argv

LETTERS = ['A', 'B', 'C', 'D', 'E']


# ─────────────────────────────────────────────────────────────────────
# SCHEMA
# ─────────────────────────────────────────────────────────────────────
CREATE_QUESTIONS = """
CREATE TABLE IF NOT EXISTS aafp_questions (
    aafp_qid        TEXT PRIMARY KEY,   -- "AAFP-49733"
    question_id     INTEGER UNIQUE,     -- server's internal question ID
    assessment_id   INTEGER,            -- quiz set ID (e.g. 13882)
    quiz_title      TEXT,               -- "Board Review Questions 01"
    question_number INTEGER,            -- 1-10 within quiz
    stem            TEXT,               -- question text
    choices         TEXT,               -- JSON [{letter, text}] position-based A/B/C/D(/E)
    url             TEXT,               -- source URL
    stem_keywords     TEXT,               -- comma-separated clinical terms (see aafp_keyword_extractor.py)
    body_system       TEXT,               -- propagated from articles.categories via xref
    source_type       TEXT,               -- propagated from articles.source_type via xref
    ite_nearest_qid   TEXT,               -- nearest ITE question by vector distance (see aafp_vector_explorer.py)
    ite_nearest_dist  REAL                -- cosine distance to ite_nearest_qid
)
"""

CREATE_EXPLANATIONS = """
CREATE TABLE IF NOT EXISTS aafp_explanations (
    aafp_qid             TEXT PRIMARY KEY,   -- FK → aafp_questions.aafp_qid (1:1)
    correct_letter       TEXT,               -- "A"/"B"/"C"/"D"/"E"
    correct_text         TEXT,               -- human-readable correct answer
    explanation          TEXT,               -- explanation text (Ref: line stripped)
    explanation_html     TEXT,               -- raw HTML preserved for re-extraction
    explanation_keywords TEXT                -- comma-separated clinical terms (see aafp_keyword_extractor.py)
)
"""

CREATE_CITATIONS = """
CREATE TABLE IF NOT EXISTS aafp_citations (
    citation_id     TEXT PRIMARY KEY,   -- "AAFP-49733-C1", "AAFP-49733-C2"
    aafp_qid        TEXT NOT NULL,      -- FK → aafp_questions.aafp_qid
    citation_seq    INTEGER NOT NULL,   -- 1, 2, 3... order within question
    article_id      TEXT,               -- FK → articles.article_id (null if unmatched)
    match_status    TEXT                -- matched / fuzzy / unmatched / no_ref
)
"""

CREATE_CITATION_RAW = """
CREATE TABLE IF NOT EXISTS aafp_citation_raw (
    citation_id     TEXT PRIMARY KEY,   -- FK → aafp_citations.citation_id
    aafp_qid        TEXT NOT NULL,      -- coordinate → aafp_questions + aafp_explanations
    raw_text        TEXT                -- full untruncated citation string
)
"""

CREATE_XREF = """
CREATE TABLE IF NOT EXISTS aafp_qid_art_xref (
    aafp_qid     TEXT NOT NULL,         -- FK → aafp_questions.aafp_qid
    article_id   TEXT NOT NULL,         -- FK → articles.article_id
    match_status TEXT,                  -- matched / fuzzy
    PRIMARY KEY (aafp_qid, article_id)
)
"""

ALL_TABLES = [
    "aafp_questions",
    "aafp_explanations",
    "aafp_citations",
    "aafp_citation_raw",
    "aafp_qid_art_xref",
]


# ─────────────────────────────────────────────────────────────────────
# CHOICE CONVERSION
# ─────────────────────────────────────────────────────────────────────
def convert_choices(raw_choices: list, correct_value: str) -> tuple[list, str | None]:
    """
    Convert [{value, text}] → [{letter, text}] using position order (A/B/C/D/E).
    Returns (converted_choices, correct_letter).
    """
    converted      = []
    correct_letter = None
    for i, choice in enumerate(raw_choices):
        letter = LETTERS[i] if i < len(LETTERS) else f"X{i}"
        converted.append({"letter": letter, "text": choice["text"]})
        if choice.get("value") == correct_value:
            correct_letter = letter
    return converted, correct_letter


# ─────────────────────────────────────────────────────────────────────
# CITATION SPLITTING
# ─────────────────────────────────────────────────────────────────────
MULTI_CIT_RE = re.compile(r'\s+\d+\)\s+')

def split_citations(ref_text: str) -> list[str]:
    """
    Split a potentially multi-citation ref string into individual citations.
    Handles embedded '... 2) NextAuthor...' pattern.
    Strips any leading citation number (e.g. '1) Author...').
    Returns list of non-empty citation strings.
    """
    if not ref_text or not ref_text.strip():
        return []
    # Strip leading "1) " if present
    text = re.sub(r'^\s*\d+\)\s+', '', ref_text.strip())
    # Split on " 2) ", " 3) " etc.
    parts = MULTI_CIT_RE.split(text)
    return [p.strip() for p in parts if p.strip()]


# ─────────────────────────────────────────────────────────────────────
# ARTICLE MATCHING
# ─────────────────────────────────────────────────────────────────────
VOL_PAGE_RE = re.compile(r'(\d{4});(\d+)\((\d+)\):(\d+)')


def extract_vol_page(ref: str) -> tuple | None:
    """
    Extract (year, vol, issue, start_page) from a citation string.
    Matches pattern: YYYY;VOL(ISSUE):PAGE  e.g. '2015;92(6):487'
    Returns None if pattern not found.
    """
    m = VOL_PAGE_RE.search(ref)
    return (m.group(1), m.group(2), m.group(3), m.group(4)) if m else None


def norm_apostrophe(s: str) -> str:
    """Normalize Unicode apostrophes/quotes to plain ASCII apostrophe."""
    return re.sub(r'[\u2018\u2019\u201b\u2032\u2035\u02bc]', "'", s)


def norm_author(ref: str) -> str:
    """Extract and normalize the first author token from a citation string."""
    token = re.split(r'[,\s]', norm_apostrophe(ref.strip()))[0]
    return token.lower()


def build_article_index(conn: sqlite3.Connection) -> tuple[dict, dict]:
    """
    Returns:
      clean_ref_map:  {clean_ref.lower(): article_id}
      vol_page_map:   {(year, vol, issue, start_page): (article_id, author1_normalized)}
    """
    cur = conn.cursor()
    cur.execute("SELECT clean_ref, article_id FROM articles WHERE article_id IS NOT NULL")
    rows = cur.fetchall()

    clean_ref_map = {}
    vol_page_map  = {}

    for clean_ref, article_id in rows:
        if not clean_ref:
            continue
        clean_ref_map[clean_ref.lower().strip()] = article_id
        key = extract_vol_page(clean_ref)
        if key:
            author = norm_author(clean_ref)
            vol_page_map[key] = (article_id, author)

    return clean_ref_map, vol_page_map


def match_citation(citation: str, clean_ref_map: dict, vol_page_map: dict) -> tuple[str | None, str]:
    """
    Match a single parsed citation string against the article index.
    Returns (article_id, match_status).

    Strategy 0: exact clean_ref match (case-insensitive)
    Strategy 1: vol/page dupe finder — year + vol + issue + start_page + author1
                All five must align. Formatting noise only — not a guesser.
    """
    if not citation or not citation.strip():
        return None, "no_ref"

    ref_lower = citation.lower().strip()

    # Strategy 0: exact match
    if ref_lower in clean_ref_map:
        return clean_ref_map[ref_lower], "matched"

    # Strategy 1: vol/page + author1 dupe finder
    key = extract_vol_page(citation)
    if key and key in vol_page_map:
        article_id, db_author = vol_page_map[key]
        aafp_author = norm_author(citation)
        if aafp_author and aafp_author == db_author:
            return article_id, "fuzzy"

    return None, "unmatched"


# ─────────────────────────────────────────────────────────────────────
# STATS
# ─────────────────────────────────────────────────────────────────────
def pct(n: int, total: int) -> str:
    return f"{n / total * 100:.1f}" if total else "0"


def print_import_stats(stats: dict, sample_unmatched: list):
    total        = stats["questions"]
    cit_total    = stats["citations_total"]
    matched      = stats.get("matched",   0)
    fuzzy        = stats.get("fuzzy",     0)
    unmatched    = stats.get("unmatched", 0)
    no_ref       = stats.get("no_ref",    0)
    multi        = stats.get("multi_cit_questions", 0)
    no_letter    = stats.get("no_correct_letter", 0)

    print(f"\n══ IMPORT QC ═══════════════════════════════════════════════")
    print(f"  Questions:                {total}")
    print(f"  correct_letter resolved:  {total - no_letter}/{total}  ({pct(total - no_letter, total)}%)")
    print(f"  Multi-citation questions: {multi}")
    print(f"")
    print(f"  Citations total:          {cit_total}")
    print(f"    matched  (exact):       {matched}  ({pct(matched, cit_total)}%)")
    print(f"    fuzzy    (vol/pg+auth): {fuzzy}  ({pct(fuzzy, cit_total)}%)")
    print(f"    unmatched:              {unmatched}  ({pct(unmatched, cit_total)}%)")
    print(f"    no_ref:                 {no_ref}  ({pct(no_ref, cit_total)}%)")
    print(f"  Total citations linked:   {matched + fuzzy}  ({pct(matched + fuzzy, cit_total)}%)")

    if sample_unmatched:
        print(f"\n  Sample unmatched citations (first 10):")
        for ref in sample_unmatched[:10]:
            print(f"    · {ref[:100]}")


def print_db_counts(conn: sqlite3.Connection):
    cur = conn.cursor()
    print(f"\n  DB row counts (post-write):")
    for table in ALL_TABLES:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            print(f"    {table:<28} {cur.fetchone()[0]}")
        except Exception:
            print(f"    {table:<28} (not found)")
    # xref breakdown
    cur.execute("SELECT match_status, COUNT(*) FROM aafp_qid_art_xref GROUP BY match_status")
    for status, count in cur.fetchall():
        print(f"      xref → {status}: {count}")


# ─────────────────────────────────────────────────────────────────────
# STATS MODE
# ─────────────────────────────────────────────────────────────────────
def run_stats_only():
    if not DB_PATH.exists():
        print(f"ERROR: DB not found:\n  {DB_PATH}")
        sys.exit(1)
    conn = sqlite3.connect(DB_PATH)
    print_db_counts(conn)
    conn.close()


# ─────────────────────────────────────────────────────────────────────
# MAIN IMPORT
# ─────────────────────────────────────────────────────────────────────
def run_import():
    if not STAGING_FILE.exists():
        print(f"ERROR: Staging file not found:\n  {STAGING_FILE}")
        sys.exit(1)
    if not DB_PATH.exists():
        print(f"ERROR: DB not found:\n  {DB_PATH}")
        sys.exit(1)

    print(f"Loading staging file...")
    with open(STAGING_FILE, encoding="utf-8") as f:
        records = json.load(f)
    print(f"  {len(records)} records loaded")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    if REBUILD:
        print(f"\n⚠  --rebuild: dropping all AAFP tables...")
        for table in reversed(ALL_TABLES):   # reverse to respect FK order
            conn.execute(f"DROP TABLE IF EXISTS {table}")
        conn.commit()
        print(f"   Tables dropped.")

    # Create tables
    for ddl in [CREATE_QUESTIONS, CREATE_EXPLANATIONS,
                CREATE_CITATIONS, CREATE_CITATION_RAW, CREATE_XREF]:
        conn.execute(ddl)
    conn.commit()

    # Build article index
    print(f"Building article index...")
    clean_ref_map, vol_page_map = build_article_index(conn)
    print(f"  {len(clean_ref_map)} clean_refs  |  {len(vol_page_map)} vol/page keys")

    stats = {
        "questions":            len(records),
        "citations_total":      0,
        "matched":              0,
        "fuzzy":                0,
        "unmatched":            0,
        "no_ref":               0,
        "no_correct_letter":    0,
        "multi_cit_questions":  0,
    }
    sample_unmatched = []

    q_rows     = []
    exp_rows   = []
    cit_rows   = []
    raw_rows   = []
    xref_seen  = set()   # (aafp_qid, article_id) — dedupe xref

    for rec in records:
        qid      = rec.get("question_id")
        aafp_qid = f"AAFP-{qid}"

        # ── choices conversion ──
        raw_choices   = rec.get("choices", [])
        correct_value = rec.get("correct_value", "")
        converted_choices, correct_letter = convert_choices(raw_choices, correct_value)
        if correct_letter is None:
            stats["no_correct_letter"] += 1

        # ── aafp_questions row ──
        q_rows.append({
            "aafp_qid":        aafp_qid,
            "question_id":     qid,
            "assessment_id":   rec.get("assessment_id"),
            "quiz_title":      rec.get("quiz_title", ""),
            "question_number": rec.get("question_number"),
            "stem":            rec.get("stem", ""),
            "choices":         json.dumps(converted_choices, ensure_ascii=False),
            "url":             rec.get("url", ""),
        })

        # ── aafp_explanations row ──
        exp_rows.append({
            "aafp_qid":        aafp_qid,
            "correct_letter":  correct_letter,
            "correct_text":    rec.get("correct_text", ""),
            "explanation":     rec.get("explanation", ""),
            "explanation_html": rec.get("explanation_html", ""),
        })

        # ── citations: split, match, build rows ──
        raw_ref   = rec.get("ref_text", "") or ""
        citations = split_citations(raw_ref)

        if not citations:
            # no_ref case — one placeholder citation row
            citation_id = f"{aafp_qid}-C1"
            cit_rows.append({
                "citation_id":  citation_id,
                "aafp_qid":     aafp_qid,
                "citation_seq": 1,
                "article_id":   None,
                "match_status": "no_ref",
            })
            raw_rows.append({
                "citation_id": citation_id,
                "aafp_qid":    aafp_qid,
                "raw_text":    raw_ref,
            })
            stats["no_ref"] += 1
            stats["citations_total"] += 1
            continue

        if len(citations) > 1:
            stats["multi_cit_questions"] += 1

        for seq, cit_text in enumerate(citations, start=1):
            citation_id = f"{aafp_qid}-C{seq}"
            stats["citations_total"] += 1

            article_id, match_status = match_citation(cit_text, clean_ref_map, vol_page_map)
            stats[match_status] = stats.get(match_status, 0) + 1

            if match_status == "unmatched":
                sample_unmatched.append(cit_text)

            cit_rows.append({
                "citation_id":  citation_id,
                "aafp_qid":     aafp_qid,
                "citation_seq": seq,
                "article_id":   article_id,
                "match_status": match_status,
            })
            raw_rows.append({
                "citation_id": citation_id,
                "aafp_qid":    aafp_qid,
                "raw_text":    cit_text,
            })

            # xref: one row per unique (aafp_qid, article_id) pair where linked
            if article_id:
                xref_key = (aafp_qid, article_id)
                if xref_key not in xref_seen:
                    xref_seen.add(xref_key)

    print_import_stats(stats, sample_unmatched)

    if DRY_RUN:
        print("\n[DRY RUN — no changes written]")
        conn.close()
        return

    # ── writes ──
    def insert_many(sql, rows):
        inserted = skipped = 0
        for row in rows:
            cur = conn.execute(sql, row)
            if cur.rowcount:
                inserted += 1
            else:
                skipped += 1
        return inserted, skipped

    qi, qs = insert_many(
        """INSERT OR IGNORE INTO aafp_questions
           (aafp_qid, question_id, assessment_id, quiz_title, question_number, stem, choices, url)
           VALUES (:aafp_qid, :question_id, :assessment_id, :quiz_title,
                   :question_number, :stem, :choices, :url)""",
        q_rows
    )
    ei, es = insert_many(
        """INSERT OR IGNORE INTO aafp_explanations
           (aafp_qid, correct_letter, correct_text, explanation, explanation_html)
           VALUES (:aafp_qid, :correct_letter, :correct_text, :explanation, :explanation_html)""",
        exp_rows
    )
    ci, cs = insert_many(
        """INSERT OR IGNORE INTO aafp_citations
           (citation_id, aafp_qid, citation_seq, article_id, match_status)
           VALUES (:citation_id, :aafp_qid, :citation_seq, :article_id, :match_status)""",
        cit_rows
    )
    ri, rs = insert_many(
        """INSERT OR IGNORE INTO aafp_citation_raw
           (citation_id, aafp_qid, raw_text)
           VALUES (:citation_id, :aafp_qid, :raw_text)""",
        raw_rows
    )

    # xref: build from xref_seen
    xref_rows = []
    for aafp_qid, article_id in xref_seen:
        # get match_status from cit_rows (take highest confidence: matched > fuzzy)
        statuses = [r["match_status"] for r in cit_rows
                    if r["aafp_qid"] == aafp_qid and r["article_id"] == article_id]
        status = "matched" if "matched" in statuses else "fuzzy"
        xref_rows.append({"aafp_qid": aafp_qid, "article_id": article_id, "match_status": status})

    xi, xs = insert_many(
        """INSERT OR IGNORE INTO aafp_qid_art_xref
           (aafp_qid, article_id, match_status)
           VALUES (:aafp_qid, :article_id, :match_status)""",
        xref_rows
    )

    conn.commit()

    print(f"\n  Inserted / skipped:")
    print(f"    aafp_questions:     {qi} / {qs}")
    print(f"    aafp_explanations:  {ei} / {es}")
    print(f"    aafp_citations:     {ci} / {cs}")
    print(f"    aafp_citation_raw:  {ri} / {rs}")
    print(f"    aafp_qid_art_xref:  {xi} / {xs}")

    print_db_counts(conn)
    print(f"\n  DB → {DB_PATH}")
    conn.close()


# ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if "--help" in sys.argv:
        print(__doc__)
        sys.exit(0)
    if STATS:
        run_stats_only()
    else:
        run_import()
