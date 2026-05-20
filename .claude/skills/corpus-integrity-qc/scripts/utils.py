"""
utils.py
========
Shared utilities for the corpus-integrity-qc skill.

Three groups of helpers, salvaged + extended from the original
article-citation-qc skill and from build_custom_question_set.py:

1. ENCODING_FIXES table + detection helpers (Layer A1)
2. Article-text parsers — title extraction, truncation detection,
   author stop-word set (Layer B4/B5)
3. DB connect helper (immutable URI mode for safe read-only audit)

All scripts in scripts/ should import from here rather than duplicating.
"""

from __future__ import annotations

import re
import sqlite3
import sys
from pathlib import Path


def setup_utf8_stdout() -> None:
    """Reconfigure stdout/stderr to UTF-8 so scripts can print ✓/✗/⚠/→ on
    Windows consoles (which default to cp1252). No-op on Python <3.7 or if
    streams don't support reconfigure (e.g., already wrapped)."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


# ════════════════════════════════════════════════════════════════════════════
# 1. ENCODING_FIXES table — used by Layer A1 (text fidelity)
# ════════════════════════════════════════════════════════════════════════════
# Canonical home of the bad-sequence → corrected-character map.
# Symbol-font artifacts: extracting from PDFs with the Symbol font produces
# Win-1252-mapped characters; if the resulting byte sequence then gets
# Latin-1-interpreted, you get the 3-char `ï‚X` strings below.
# Double-encoded UTF-8: Latin char encoded once as UTF-8, then the bytes
# interpreted again as Win-1252, producing 2-char `ÃY` strings.

ENCODING_FIXES: list[tuple[str, str]] = [
    # Symbol-font artifacts (most common in ITE explanations)
    ("ï‚£", "≤"),   # Symbol 0xA3 (less-than-or-equal)
    ("ï‚³", "≥"),   # Symbol 0xB3 (greater-than-or-equal)
    ("ï‚±", "±"),   # Symbol 0xB1 (plus-minus)
    ("ï‚®", "→"),   # Symbol 0xAE (arrow right)
    ("ï‚¬", "←"),   # Symbol 0xAC (arrow left)
    ("ï‚´", "×"),   # Symbol 0xB4 (multiply)
    ("ï‚¸", "÷"),   # Symbol 0xB8 (divide)
    # Double-encoded Latin
    ("Ã©", "é"),
    ("Ã¨", "è"),
    ("Ã¼", "ü"),
    ("Ã¶", "ö"),
    # Double-encoded U+00D7 multiply + accented Latin (verified present in DB 2026-05-19)
    ("Ã—", "×"),
    ("Ã¤", "ä"),
    ("Ã³", "ó"),
    ("Ã§", "ç"),
    ("Ã­", "í"),
    ("Ã¡", "á"),
    ("Ã¯", "ï"),
    ("Ã¸", "ø"),
    ("Â²", "²"),
    ("Â³", "³"),
    ("Â°", "°"),
    # Smart-quote / dash mojibake
    ("â€œ", '"'),
    ("â€", '"'),
    ("â€™", "'"),
    ("â€˜", "'"),
    ("â€“", "–"),
    ("â€”", "—"),
]


# Symbol-font dot-leader runs (table column-aligners). DB stores the
# triple-mojibake form 'ï€®'; raw private-use codepoints kept as defensive
# fallback. Collapsed to ": " so lab tables read as "Platelets: 112,000".
DOTLEADER_RE = re.compile(
    r"(?<!:)\s*(?:ï€®|[" + chr(0xF02E) + chr(0xF02D) + chr(0xF02C) + r"])+\s*"
)


def find_encoding_artifacts(text: str | None) -> list[tuple[str, str]]:
    """
    Return list of (bad_seq, good_char) tuples for every artifact found in `text`.
    Each artifact is reported once even if it appears multiple times — count is
    encoded by separately calling text.count(bad_seq) if needed.

    Empty list = clean text.
    """
    if not text:
        return []
    found: list[tuple[str, str]] = []
    for bad, good in ENCODING_FIXES:
        if bad in text:
            found.append((bad, good))
    if DOTLEADER_RE.search(text):
        found.append(("ï€® dot-leader run", ": "))
    return found


def apply_encoding_fixes(text: str | None) -> str:
    """Return text with all encoding fixes applied. Idempotent."""
    if not text:
        return text or ""
    for bad, good in ENCODING_FIXES:
        if bad in text:
            text = text.replace(bad, good)
    # Collapse Symbol-font dot-leader runs + surrounding whitespace → ": "
    text = DOTLEADER_RE.sub(": ", text)
    # Smart quotes (the proper UTF-8 versions, not mojibake)
    text = text.replace("“", '"').replace("”", '"')
    text = text.replace("‘", "'").replace("’", "'")
    return text


# ════════════════════════════════════════════════════════════════════════════
# 2. Article-text parsers (Layer B4/B5)
# ════════════════════════════════════════════════════════════════════════════

AUTHOR_STOP_WORDS: set[str] = {
    "final", "us", "updated", "recommendation", "recommendations",
    "task", "force", "services", "preventive", "statement", "committee",
    "working", "group", "panel", "board", "american", "national",
    "centers", "center", "department", "who", "cdc", "nih", "fda",
    "uptodate", "clinical",
}


def extract_title_from_clean_ref(clean_ref: str | None) -> str | None:
    """
    Extract the article title from a standard medical citation.

    Two main formats:
    1. Author citation: "Smith J, Jones A. Article title: subtitle. Journal. Year;Vol:Pages."
       → Title is the second ". "-delimited segment.
    2. Org-byline citation: "American Academy of Dermatology: Don't prescribe..."
       → Title is the FIRST segment (no co-author list, substantively long).

    Returns None if extraction fails.
    """
    if not clean_ref:
        return None

    ref = clean_ref.strip()
    segments = re.split(r"\.\s+", ref)
    if not segments:
        return None

    first_seg = segments[0].strip()

    is_org_byline = (
        "," not in first_seg
        and len(first_seg) > 40
        and len(first_seg.split()) >= 4
    )
    if is_org_byline:
        return first_seg

    # Author citation: title is in segments[1:]; skip year/vol-page/URL/journal-abbrev
    for seg in segments[1:]:
        seg = seg.strip()
        if not seg:
            continue
        if re.match(r"^\d{4}", seg):           # starts with year
            continue
        if re.match(r"^\d+[\(\d]", seg):       # volume/page ref
            continue
        if seg.startswith(("http", "www")):
            continue
        if len(seg) < 15:                       # journal abbrev
            continue
        if re.match(r"^[A-Za-z ]+\d{4}", seg):  # "Am Fam Physician 2015"
            continue
        return seg

    return None


def is_truncated_title(db_title: str | None, extracted_title: str | None) -> bool:
    """
    True if db_title appears to be a truncated/fragmented version of
    extracted_title from clean_ref.

    Cases caught:
    - db_title is a page range ("123–154")
    - db_title is the after-colon fragment of extracted_title
    - db_title is significantly shorter and is a suffix of extracted_title
    - db_title is fully contained within extracted_title and is much shorter
    """
    if not db_title or not extracted_title:
        return False

    db = db_title.strip().lower()
    ext = extracted_title.strip().lower()

    if re.match(r"^\d+[\-–]\d+$", db_title.strip()):
        return True

    if ":" in ext:
        after_colon = ext.split(":", 1)[1].strip()
        if db == after_colon:
            return True

    if len(db) < len(ext) * 0.7 and ext.endswith(db):
        return True

    if db in ext and len(db) < len(ext) * 0.6:
        return True

    return False


def correct_author_from_clean_ref(clean_ref: str | None) -> str | None:
    """
    Given a clean_ref that triggered AUTHOR_ARTIFACT, derive the corrected author1.

    Standard: "Last, First, ..." → first token before first comma.
    Org-byline: "American Academy of Dermatology: ..." → text before first ':' or '.'.

    Returns None if unparseable.
    """
    if not clean_ref:
        return None
    first_seg = re.split(r"\.\s+", clean_ref)[0].strip()
    if "," in first_seg:
        return first_seg.split(",")[0].strip()
    org_name = re.split(r"[:\.]", first_seg)[0].strip()
    return org_name[:80] if len(org_name) > 2 else None


# ════════════════════════════════════════════════════════════════════════════
# 3. DB helper
# ════════════════════════════════════════════════════════════════════════════

def connect_db_readonly(db_path: Path) -> sqlite3.Connection:
    """
    Open DB in immutable URI mode. Audit scripts must never lock the DB.
    `immutable=1` tells SQLite the file won't change during the connection,
    which disables WAL writes and avoids any chance of corrupting the DB.
    """
    uri = f"file:{db_path}?immutable=1"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def resolve_project_root_from_staging(staging_dir: Path) -> Path:
    """
    Project root is two hops up from M2/outputs/.
    staging_dir = PROJECT_ROOT/02_module.2_processor/outputs/
    """
    return staging_dir.resolve().parent.parent


def resolve_db_path(project_root: Path) -> Path:
    return project_root / "00_database" / "db" / "ite_intelligence.db"
