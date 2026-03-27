"""
classify_null_refs.py — Bucket Classifier for Unresolvable NULL clean_ref Rows
===============================================================================
Phase 2 | ITE Intelligence Pipeline

After rematch_unmatched.py has run, some question_ref_pairs rows will still
have clean_ref = NULL. This script classifies those remaining rows into four
buckets to separate "genuinely fixable" from "permanently unresolvable."

BUCKETS
-------
  1 = well_formed    : Full author + title + journal citation. Potentially
                       linkable to articles table with more work.
  2 = journal_stub   : Journal name + volume/page only, no author/title.
                       Cannot be matched — not enough info.
  3 = web_resource   : Government/agency web pages, USPSTF recommendations,
                       CDC pages, AAP guidelines (non-journal). No DB article.
  4 = data_corrupt   : Question stem text bleeding into the ref field.
                       Data ingestion artifact. Should be NULL'd or deleted.

OUTPUT
------
  - Console: bucket counts + year breakdown + sample rows per bucket
  - Report:  00_database/logs/classify_null_refs_report.txt
  - JSON:    00_database/logs/classify_null_refs.json

Run:
  python scripts/classify_null_refs.py
"""

import sqlite3
import json
import re
from pathlib import Path
from datetime import datetime

# ── Paths ──────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH      = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"
LOG_DIR      = PROJECT_ROOT / "00_database" / "logs"
REPORT_PATH  = LOG_DIR / "classify_null_refs_report.txt"
JSON_PATH    = LOG_DIR / "classify_null_refs.json"


# ── Bucket Detection Patterns ──────────────────────────────────────────────

# Journals that appear as stubs (ref starts directly with journal name)
JOURNAL_STUB_PREFIXES = re.compile(
    r'^(JAMA|Lancet|BMJ|N Engl J Med|Circulation|Stroke|Pediatrics|'
    r'Orthop J|Clin Infect Dis|Hepatology|J Am Coll|Am J Kidney|'
    r'Ann Intern Med|Arch Intern Med|Chest|Heart|Gut|Blood|'
    r'J Hematol|J Am Acad Orthop|Wilderness Environ)',
    re.IGNORECASE
)

# Web/agency resource signals
WEB_AGENCY_PATTERNS = re.compile(
    r'^(Centers for Disease Control|US Preventive Services|'
    r'American Diabetes Association|Final recommendation statement|'
    r'American College of Obstetricians|American Academy of Pediatrics|'
    r'Reviewed (January|February|March|April|May|June|July|August|September|'
    r'October|November|December)|Updated (January|February|March|April|May|'
    r'June|July|August|September|October|November|December)|'
    r'Differentiated and simplified|Diagnosis, evaluation, and management of ascites|'
    r'Environmental interventions for preventing falls|'
    r'Physical activity guidelines|Centre for Evidence)',
    re.IGNORECASE
)

# Data corruption: question stem text bleeding into ref field
# These look like narrative sentences, not citations
CORRUPT_SIGNALS = re.compile(
    r'^(He |She |A |An |The (patient|2018|2019|2020|hallmark|following|'
    r'diagnosis|management|physician|study|trial|question|answer)|'
    r'Falls are|In (patients|addition|this)|You are|Your patient)',
    re.IGNORECASE
)

# A well-formed citation starts with an author: "Lastname X," or "Lastname XY,"
# or "Lastname XX, Lastname" etc.
AUTHOR_START = re.compile(
    r'^[A-Z][a-zA-Z\-\']+\s+[A-Z]{1,4}[,\.]'   # Smith AB, or Smith AB.
    r'|^[A-Z][a-zA-Z\-\']+\s+[A-Z][a-z]+\s+[A-Z]'  # Smith Jones A
    r'|^American (Diabetes|College|Board|Heart|Gastroenterological)'  # org authors
    r'|^Committee on'
    r'|^[A-Z][a-zA-Z\-\']+ [A-Z][a-zA-Z\-\']+,'   # Two-word last name
,
    re.IGNORECASE
)


def classify_ref(ref_raw: str) -> str:
    """Classify a single ref_raw string into a bucket label."""
    if not ref_raw:
        return "data_corrupt"

    r = ref_raw.strip()

    # Bucket 4: Corruption check — question stem text bleeding into ref field.
    # The CORRUPT_SIGNALS regex catches narrative sentence starts; that's sufficient.
    # Do NOT use word-presence heuristics (e.g. "diagnosis", "treatment") because
    # AFP article titles routinely contain these words and would be misflagged.
    if CORRUPT_SIGNALS.match(r):
        return "data_corrupt"

    # Bucket 2: Journal stub (starts directly with journal name, no author)
    if JOURNAL_STUB_PREFIXES.match(r):
        return "journal_stub"

    # Bucket 3: Web/agency resource
    if WEB_AGENCY_PATTERNS.match(r):
        return "web_resource"

    # Bucket 1: Well-formed citation (default for anything with author structure)
    return "well_formed"


# ── Main ────────────────────────────────────────────────────────────────────
def main():
    if not DB_PATH.exists():
        print(f"❌ DB not found: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    cur.execute("""
        SELECT p.id, p.qid, p.ref_raw, q.exam_year
        FROM question_ref_pairs p
        JOIN questions q ON p.qid = q.qid
        WHERE p.clean_ref IS NULL
          AND p.ref_raw IS NOT NULL
          AND TRIM(p.ref_raw) != ''
        ORDER BY q.exam_year, p.qid
    """)
    rows = cur.fetchall()
    conn.close()

    print("=" * 64)
    print("classify_null_refs.py — NULL clean_ref Bucket Classifier")
    print(f"  Total NULL rows to classify: {len(rows)}")
    print("=" * 64)

    # Classify all rows
    classified = []
    bucket_counts = {"well_formed": 0, "journal_stub": 0, "web_resource": 0, "data_corrupt": 0}
    year_buckets  = {}

    for row_id, qid, ref_raw, exam_year in rows:
        bucket = classify_ref(ref_raw or "")
        bucket_counts[bucket] += 1

        if exam_year not in year_buckets:
            year_buckets[exam_year] = {"well_formed": 0, "journal_stub": 0, "web_resource": 0, "data_corrupt": 0}
        year_buckets[exam_year][bucket] += 1

        classified.append({
            "id":        row_id,
            "qid":       qid,
            "exam_year": exam_year,
            "bucket":    bucket,
            "ref_raw":   (ref_raw or "").strip()
        })

    # ── Console Output ─────────────────────────────────────────────────────
    total = len(rows)
    print(f"\n{'BUCKET':<18} {'COUNT':>6}  {'PCT':>6}  DESCRIPTION")
    print("-" * 64)
    desc = {
        "well_formed":  "Full citation — potentially linkable",
        "journal_stub": "Journal/vol/pg only — unmatchable",
        "web_resource": "Gov/agency web resource — no DB article",
        "data_corrupt": "Question text corruption — should be NULL'd",
    }
    for bucket, count in bucket_counts.items():
        pct = round(100.0 * count / total, 1) if total else 0
        print(f"  {bucket:<16} {count:>6}  {pct:>5.1f}%  {desc[bucket]}")

    print(f"\n  {'TOTAL':<16} {total:>6}")

    print(f"\n{'YEAR BREAKDOWN':}")
    print("-" * 64)
    print(f"  {'Year':<6} {'well_formed':>12} {'journal_stub':>13} {'web_resource':>13} {'data_corrupt':>13}")
    for yr in sorted(year_buckets):
        yb = year_buckets[yr]
        yr_total = sum(yb.values())
        print(f"  {yr:<6} {yb['well_formed']:>12} {yb['journal_stub']:>13} {yb['web_resource']:>13} {yb['data_corrupt']:>13}  (n={yr_total})")

    # ── Sample rows per bucket ─────────────────────────────────────────────
    for bucket in ["data_corrupt", "journal_stub", "web_resource"]:
        sample = [c for c in classified if c["bucket"] == bucket][:4]
        if sample:
            print(f"\n── Sample: {bucket} ──")
            for s in sample:
                print(f"  [{s['exam_year']}] {s['qid']}: {s['ref_raw'][:90]}")

    # ── Write outputs ──────────────────────────────────────────────────────
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(f"classify_null_refs Report\n")
        f.write(f"Run: {datetime.now().isoformat()}\n")
        f.write(f"Total rows: {total}\n\n")
        for bucket, count in bucket_counts.items():
            pct = round(100.0 * count / total, 1) if total else 0
            f.write(f"  {bucket}: {count} ({pct}%)\n")
        f.write("\n")

        for bucket in ["data_corrupt", "journal_stub", "web_resource", "well_formed"]:
            f.write(f"\n{'='*60}\n{bucket.upper()}\n{'='*60}\n\n")
            for c in classified:
                if c["bucket"] == bucket:
                    f.write(f"[{c['exam_year']}] {c['qid']}\n  {c['ref_raw']}\n\n")

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump({
            "run_at":         datetime.now().isoformat(),
            "total_rows":     total,
            "bucket_counts":  bucket_counts,
            "year_buckets":   {str(k): v for k, v in year_buckets.items()},
            "rows":           classified
        }, f, indent=2)

    print(f"\n✅ Done")
    print(f"   Report: {REPORT_PATH}")
    print(f"   JSON:   {JSON_PATH}")


if __name__ == "__main__":
    main()
