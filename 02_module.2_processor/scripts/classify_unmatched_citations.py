#!/usr/bin/env python3
"""
AAFP Unmatched Citations — Classifier + Exporter
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Classifies all unmatched AAFP citations into 3 buckets:

  IRRECOVERABLE  — truncated scraper artifacts + books/textbooks
                   Cannot be matched regardless of strategy or acquisition
  JOURNAL_MISSING — proper journal citations pointing to articles not in DB
                   Acquisition targets (download → ingest → re-run aafp_ref_match_v2.py)
  REMAINING       — guideline statements, Cochrane, other — still workable

Actions:
  1. Adds `unmatched_class` column to aafp_citations (if not exists)
  2. Sets class on all currently-unmatched rows
  3. Exports 3 CSVs to 00_database/readable_db_files/

Run:
  python classify_unmatched_citations.py            <- classify + export
  python classify_unmatched_citations.py --dry-run  <- preview counts, no writes
  python classify_unmatched_citations.py --stats    <- show current classification counts
"""

import re
import csv
import sqlite3
import sys
from pathlib import Path
from datetime import date

SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH      = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"
OUT_DIR      = PROJECT_ROOT / "00_database" / "readable_db_files"

DRY_RUN = "--dry-run" in sys.argv
STATS   = "--stats"   in sys.argv

TODAY = date.today().strftime("%Y%m%d")

# ──────────────────────────────────────────────────────────────────────
# CLASSIFICATION PATTERNS
# ──────────────────────────────────────────────────────────────────────

# Strict journal vol/page pattern  YYYY;VOL(ISSUE):PAGE
VOL_STRICT_RE = re.compile(r'(\d{4});(\d+)\((\d+)\):(\d+)')

# Book/textbook markers
BOOK_RE = re.compile(
    r'\b(ed\s*\d+|pp?\s*\d+|chapter|edition|McGraw.?Hill|Elsevier|Saunders|'
    r'Lippincott|Springer|Williams\s*&?\s*Wilkins|Wolters|Kluwer|Oxford|'
    r'Mosby|Churchill|Livingstone|Thieme|Wiley|Blackwell|Humana)\b',
    re.I
)

# URL references
URL_RE = re.compile(r'https?://')

# Guideline / society / CDC / USPSTF
GUIDELINE_RE = re.compile(
    r'\b(task force|preventive services|uspstf|recommendation|practice guideline|'
    r'clinical practice|position statement|consensus|advisory committee|'
    r'centers for disease control|cdc|acip|acog|aha|acc|ats|idsa|acs|aafp|aap|'
    r'american academy|american college|american association|american society|'
    r'joint commission|world health|who)\b',
    re.I
)

# Cochrane reviews
COCHRANE_RE = re.compile(r'Cochrane', re.I)


def classify_citation(raw_text: str, vol_key_in_db: bool) -> str:
    """
    Classify a single unmatched citation into one of:
      IRRECOVERABLE   — truncated or book (cannot be matched)
      JOURNAL_MISSING — proper journal citation, article not in DB
      REMAINING       — guideline, Cochrane, URL, or other
    """
    ref = (raw_text or '').strip()

    # Truncated artifact: very short or just "Author, "
    if len(ref) < 25:
        return 'IRRECOVERABLE'

    # URL references — not matchable to articles
    if URL_RE.search(ref):
        return 'REMAINING'      # could theoretically scrape, keep as remaining

    # Book / textbook
    if BOOK_RE.search(ref):
        return 'IRRECOVERABLE'

    # Journal with strict vol/page AND key not in DB  -> acquisition target
    if VOL_STRICT_RE.search(ref) and not vol_key_in_db:
        return 'JOURNAL_MISSING'

    # Guideline / society / CDC
    if GUIDELINE_RE.search(ref):
        return 'REMAINING'

    # Cochrane
    if COCHRANE_RE.search(ref):
        return 'REMAINING'

    # Has a vol/page key that IS in DB (shouldn't happen post-pass, but safety net)
    if VOL_STRICT_RE.search(ref) and vol_key_in_db:
        return 'REMAINING'

    # Everything else
    return 'REMAINING'


def build_vol_key_set(conn) -> set:
    """Build set of (year, vol, issue, page) keys present in articles DB."""
    cur = conn.cursor()
    cur.execute("SELECT clean_ref FROM articles WHERE clean_ref IS NOT NULL")
    keys = set()
    for (ref,) in cur.fetchall():
        m = VOL_STRICT_RE.search(ref or '')
        if m:
            keys.add((m.group(1), m.group(2), m.group(3), m.group(4)))
    return keys


def run_classifier(conn):
    cur = conn.cursor()

    # Ensure column exists
    try:
        cur.execute("ALTER TABLE aafp_citations ADD COLUMN unmatched_class TEXT")
        conn.commit()
        print("Added column: aafp_citations.unmatched_class")
    except Exception:
        pass  # Column already exists

    # Load all unmatched citations
    cur.execute("""
        SELECT ac.citation_id, ac.aafp_qid, cr.raw_text
        FROM aafp_citations ac
        JOIN aafp_citation_raw cr ON ac.citation_id = cr.citation_id
        WHERE ac.match_status = 'unmatched'
    """)
    rows = cur.fetchall()
    print(f"Unmatched citations to classify: {len(rows)}")

    # Build vol/page key set from DB for lookup
    db_vol_keys = build_vol_key_set(conn)

    # Classify
    classified = []  # (citation_id, aafp_qid, raw_text, class)
    counts = {'IRRECOVERABLE': 0, 'JOURNAL_MISSING': 0, 'REMAINING': 0}

    for citation_id, aafp_qid, raw_text in rows:
        ref = raw_text or ''
        m = VOL_STRICT_RE.search(ref)
        vol_key_in_db = False
        if m:
            key = (m.group(1), m.group(2), m.group(3), m.group(4))
            vol_key_in_db = key in db_vol_keys

        cls = classify_citation(ref, vol_key_in_db)
        counts[cls] += 1
        classified.append((citation_id, aafp_qid, raw_text, cls))

    # Print summary
    total = len(classified)
    print(f"\n== CLASSIFICATION RESULTS ==")
    print(f"  IRRECOVERABLE  (books + truncated):  {counts['IRRECOVERABLE']:>4}  ({counts['IRRECOVERABLE']/total*100:.1f}%)")
    print(f"  JOURNAL_MISSING (acquisition targets): {counts['JOURNAL_MISSING']:>4}  ({counts['JOURNAL_MISSING']/total*100:.1f}%)")
    print(f"  REMAINING       (still workable):      {counts['REMAINING']:>4}  ({counts['REMAINING']/total*100:.1f}%)")

    if DRY_RUN:
        print("\n[DRY RUN - no writes]")
        # Still show sample of each class
        for cls in ('IRRECOVERABLE', 'JOURNAL_MISSING', 'REMAINING'):
            samples = [(cid, aq, rt) for cid, aq, rt, c in classified if c == cls][:3]
            print(f"\n  Sample {cls}:")
            for cid, aq, rt in samples:
                print(f"    [{cid}] {(rt or '')[:100]}")
        return

    # ── Write unmatched_class to DB ──
    for citation_id, aafp_qid, raw_text, cls in classified:
        cur.execute(
            "UPDATE aafp_citations SET unmatched_class = ? WHERE citation_id = ?",
            (cls, citation_id)
        )
    conn.commit()
    print(f"\nDB updated: {len(classified)} rows tagged with unmatched_class")

    # ── Export CSVs ──
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    buckets = {
        'IRRECOVERABLE':  f'aafp_unmatched_irrecoverable_{TODAY}.csv',
        'JOURNAL_MISSING': f'aafp_unmatched_journal_missing_{TODAY}.csv',
        'REMAINING':       f'aafp_unmatched_remaining_{TODAY}.csv',
    }

    for cls, filename in buckets.items():
        out_path = OUT_DIR / filename
        rows_for_cls = [
            (cid, aq, rt) for cid, aq, rt, c in classified if c == cls
        ]
        with open(out_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['citation_id', 'aafp_qid', 'raw_text'])
            for cid, aq, rt in rows_for_cls:
                writer.writerow([cid, aq, rt or ''])
        print(f"  Exported {len(rows_for_cls):>4} rows -> {filename}")

    print(f"\nAll CSVs saved to: {OUT_DIR}")


def run_stats(conn):
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT unmatched_class, COUNT(*)
            FROM aafp_citations
            WHERE match_status = 'unmatched'
            GROUP BY unmatched_class
            ORDER BY COUNT(*) DESC
        """)
        print("aafp_citations.unmatched_class (unmatched rows only):")
        for cls, count in cur.fetchall():
            print(f"  {(cls or 'NULL'):<25} {count}")
    except Exception as e:
        print(f"Error (column may not exist yet): {e}")


if __name__ == "__main__":
    if "--help" in sys.argv:
        print(__doc__)
        sys.exit(0)

    if not DB_PATH.exists():
        print(f"ERROR: DB not found: {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    try:
        if STATS:
            run_stats(conn)
        else:
            run_classifier(conn)
    finally:
        conn.close()
        print(f"\nDB -> {DB_PATH}")
