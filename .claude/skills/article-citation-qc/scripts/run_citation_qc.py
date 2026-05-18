"""
run_citation_qc.py
==================
Article Citation QC — reads all available staging JSONs + ite_intelligence.db,
runs six QC checks, writes qc_results.json to --output-dir.

Usage:
    cd PROJECT_ROOT/03_module.3_analyst/scripts/
    python <skill>/scripts/run_citation_qc.py \
        --staging-dir ../../02_module.2_processor/outputs/ \
        --output-dir ../../03_module.3_analyst/outputs/article_qc/

Checks:
    TRUNC_TITLE     - title field is a fragment of the full title in clean_ref
    AUTHOR_ARTIFACT - author1 is a parsing stop-word fragment
    UMBRELLA        - high citation_count + high topic diversity
    QID_MISMATCH    - critique says QID→ART-X, but DB has QID→ART-Y (or nothing)
    UNMATCHED_REF   - critique citation has no corresponding DB article
    NULL_CLEAN_REF  - article exists but clean_ref is null (for cited articles)

Outputs qc_results.json with structure:
{
  "summary": { "total_articles": N, "by_check": {...}, "by_severity": {...} },
  "findings": [
    {
      "check": "TRUNC_TITLE",
      "severity": "MEDIUM",
      "article_id": "ART-0230",
      "current_value": "discovering the underlying cause",
      "corrected_value": "Secondary hypertension: discovering the underlying cause",
      "clean_ref": "Charles L, Triscott J, Dobbs B. Secondary hypertension: ...",
      "citation_count": 9,
      "detail": "..."
    },
    ...
  ],
  "years_processed": [2018, 2019, ...],
  "years_missing": [...]
}
"""

import re
import json
import argparse
import sqlite3
from pathlib import Path
from collections import defaultdict

# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent
# When called from 03_module.3_analyst/scripts/, PROJECT_ROOT is 2 hops up
# When called from anywhere else, use the STAGING_DIR anchor
ITE_YEARS    = list(range(2018, 2026))  # 2018–2025

# ── Stop-words for AUTHOR_ARTIFACT check ──────────────────────────────────────
AUTHOR_STOP_WORDS = {
    "final", "us", "updated", "recommendation", "recommendations",
    "task", "force", "services", "preventive", "statement", "committee",
    "working", "group", "panel", "board", "american", "national",
    "centers", "center", "department", "who", "cdc", "nih", "fda",
    "uptodate", "clinical"
}

# ── Title extraction from clean_ref ────────────────────────────────────────────
def extract_title_from_clean_ref(clean_ref: str) -> str | None:
    """
    Extract the article title from a standard medical citation.

    Two main formats:
    1. Author citation: "Smith J, Jones A. Article title: subtitle. Journal. Year;Vol:Pages."
       → Title is the second ". "-delimited segment.
    2. Org-byline citation: "AAP releases guideline on X. Am Fam Physician 2015;91(8):578."
       "American Academy of Dermatology: Don't prescribe..."
       → Title is the FIRST segment (org abbreviation + title merged).

    Detection: if first segment contains NO comma (no co-author list) AND is longer than
    40 chars, treat it as an org-byline citation where seg[0] IS the title.
    """
    if not clean_ref:
        return None

    ref = clean_ref.strip()
    segments = re.split(r'\.\s+', ref)

    if len(segments) < 1:
        return None

    first_seg = segments[0].strip()

    # Detect org-byline citations:
    # 1. No comma in first segment → not a "Last, First" author format
    # 2. First segment is substantively long (not just "AAP" or "CDC")
    # 3. First segment doesn't look like a bare author (< 4 words with commas)
    is_org_byline = (
        ',' not in first_seg and
        len(first_seg) > 40 and
        len(first_seg.split()) >= 4
    )

    if is_org_byline:
        # The title is the first segment; strip trailing colon-content if present
        # (handles "Org Name: Don't prescribe..." → "Org Name")
        # But we want the full title, not just the org name
        return first_seg

    # Standard author citation: title is second segment
    for seg in segments[1:]:
        seg = seg.strip()
        if not seg:
            continue
        if re.match(r'^\d{4}', seg):  # starts with year
            continue
        if re.match(r'^\d+[\(\d]', seg):  # volume/page ref
            continue
        if seg.startswith('http') or seg.startswith('www'):
            continue
        if len(seg) < 15:  # too short (journal abbrev)
            continue
        # Skip if it looks like a journal+year combo: "Am Fam Physician 2015;..."
        if re.match(r'^[A-Za-z ]+\d{4}', seg):
            continue
        return seg

    return None


def is_truncated_title(db_title: str, extracted_title: str) -> bool:
    """
    Returns True if db_title appears to be a truncated or fragmented
    version of extracted_title from clean_ref.

    Cases:
    - db_title is a suffix of extracted_title (colon-split artifact)
    - db_title is significantly shorter and contained within extracted_title
    - db_title is a page range ("123-154") instead of a real title
    """
    if not db_title or not extracted_title:
        return False

    db = db_title.strip().lower()
    ext = extracted_title.strip().lower()

    # Page range pattern
    if re.match(r'^\d+[\-–]\d+$', db_title.strip()):
        return True

    # db_title is the after-colon fragment of extracted_title
    if ':' in ext:
        after_colon = ext.split(':', 1)[1].strip()
        if db == after_colon:
            return True

    # db_title is substantially shorter and is a suffix of extracted_title
    if len(db) < len(ext) * 0.7 and ext.endswith(db):
        return True

    # db_title is fully contained within extracted_title and is much shorter
    if db in ext and len(db) < len(ext) * 0.6:
        return True

    return False


def load_db(db_path: Path):
    """Open DB with immutable URI mode (avoids NTFS lock issues)."""
    uri = f"file:{db_path}?immutable=1"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def load_staging_jsons(staging_dir: Path) -> tuple[list[dict], list[int], list[int]]:
    """Load all available YYYY_critique_refs_staging.json files."""
    all_records = []
    years_found = []
    years_missing = []

    for year in ITE_YEARS:
        path = staging_dir / f"{year}_critique_refs_staging.json"
        if path.exists():
            with open(path) as f:
                records = json.load(f)
            for rec in records:
                rec['exam_year'] = year
            all_records.extend(records)
            years_found.append(year)
        else:
            years_missing.append(year)

    return all_records, years_found, years_missing


def run_checks(conn, staging_records: list[dict]) -> list[dict]:
    """Run all QC checks and return list of finding dicts."""
    findings = []
    cursor = conn.cursor()

    # ── Load articles table ───────────────────────────────────────────────────
    cursor.execute("""
        SELECT article_id, title, author1, clean_ref, citation_display,
               citation_count, unique_years, qid_list, source_type
        FROM articles
    """)
    articles = {row['article_id']: dict(row) for row in cursor.fetchall()}

    # ── Load qid_art_xref ─────────────────────────────────────────────────────
    cursor.execute("SELECT qid, article_id, exam_year FROM qid_art_xref")
    db_qid_to_art = {}
    for row in cursor.fetchall():
        db_qid_to_art[row['qid']] = row['article_id']

    # ── Load blueprint categories for UMBRELLA check ──────────────────────────
    try:
        cursor.execute("SELECT question_id, blueprint_category, body_system FROM questions")
        q_meta = {row['question_id']: dict(row) for row in cursor.fetchall()}
    except Exception:
        q_meta = {}

    # ── CHECK: TRUNC_TITLE + AUTHOR_ARTIFACT ─────────────────────────────────
    for art_id, art in articles.items():
        clean_ref = art.get('clean_ref') or ''
        db_title  = art.get('title') or ''
        author1   = art.get('author1') or ''

        # TRUNC_TITLE
        ext_title = extract_title_from_clean_ref(clean_ref)
        if ext_title and is_truncated_title(db_title, ext_title):
            findings.append({
                "check": "TRUNC_TITLE",
                "severity": "MEDIUM",
                "article_id": art_id,
                "current_value": db_title,
                "corrected_value": ext_title,
                "clean_ref": clean_ref[:150],
                "citation_count": art.get('citation_count', 0),
                "detail": f"Title appears truncated. DB: '{db_title}' | From clean_ref: '{ext_title}'"
            })

        # AUTHOR_ARTIFACT
        if author1 and author1.strip().lower().rstrip('.') in AUTHOR_STOP_WORDS:
            # Try to extract the real author/org name from clean_ref
            corrected_author = None
            if clean_ref:
                first_seg = re.split(r'\.\s+', clean_ref)[0].strip()
                if ',' in first_seg:
                    # Standard "Last, First, ..." → take first token before comma
                    corrected_author = first_seg.split(',')[0].strip()
                else:
                    # Org-byline: "American Academy of Dermatology: Don't..."
                    # Take everything before the first colon or period
                    org_name = re.split(r'[:\.]', first_seg)[0].strip()
                    # Cap at 80 chars — avoid capturing the full sentence
                    corrected_author = org_name[:80] if len(org_name) > 2 else None

            findings.append({
                "check": "AUTHOR_ARTIFACT",
                "severity": "MEDIUM",
                "article_id": art_id,
                "current_value": author1,
                "corrected_value": corrected_author,
                "clean_ref": clean_ref[:150],
                "citation_count": art.get('citation_count', 0),
                "detail": f"author1='{author1}' looks like a parsing artifact, not a real author name."
            })

        # NULL_CLEAN_REF (only flag if this article is actually cited)
        if not clean_ref and (art.get('citation_count') or 0) > 0:
            findings.append({
                "check": "NULL_CLEAN_REF",
                "severity": "LOW",
                "article_id": art_id,
                "current_value": None,
                "corrected_value": None,
                "clean_ref": None,
                "citation_count": art.get('citation_count', 0),
                "detail": f"article cited {art.get('citation_count')} time(s) but has no clean_ref"
            })

    # ── CHECK: UMBRELLA ───────────────────────────────────────────────────────
    for art_id, art in articles.items():
        citation_count = art.get('citation_count') or 0
        unique_years   = art.get('unique_years') or 0

        # Threshold: cited 5+ times across 3+ exam years
        if citation_count < 5 or unique_years < 3:
            continue

        # Get blueprint diversity across linked QIDs
        qid_list_raw = art.get('qid_list') or '[]'
        try:
            qid_list = json.loads(qid_list_raw) if isinstance(qid_list_raw, str) else qid_list_raw
        except Exception:
            qid_list = []

        blueprints = set()
        body_systems = set()
        for qid in qid_list:
            if qid in q_meta:
                bp = q_meta[qid].get('blueprint_category')
                bs = q_meta[qid].get('body_system')
                if bp:
                    blueprints.add(bp)
                if bs:
                    body_systems.add(bs)

        topic_diversity = len(blueprints) + len(body_systems)

        # Flag if spans 4+ unique blueprint categories OR 3+ body systems
        if len(blueprints) >= 4 or len(body_systems) >= 3:
            findings.append({
                "check": "UMBRELLA",
                "severity": "HIGH" if citation_count >= 8 else "MEDIUM",
                "article_id": art_id,
                "current_value": art.get('title', ''),
                "corrected_value": None,
                "clean_ref": (art.get('clean_ref') or '')[:150],
                "citation_count": citation_count,
                "detail": (
                    f"Possible umbrella article: cited {citation_count}x across {unique_years} years, "
                    f"spans {len(blueprints)} blueprint categories and {len(body_systems)} body systems. "
                    f"Blueprint cats: {sorted(blueprints)}. Body systems: {sorted(body_systems)}."
                )
            })

    # ── CHECK: QID_MISMATCH + UNMATCHED_REF (from staging JSONs) ─────────────
    for rec in staging_records:
        qid = rec.get('qid')
        critique_art_id = rec.get('_article_id') or rec.get('article_id')
        match_status = rec.get('match_status', 'unknown')
        clean_ref_from_critique = rec.get('clean_ref') or ''
        year = rec.get('exam_year')

        if not qid:
            continue

        # UNMATCHED_REF: critique has a citation that couldn't be matched to any DB article
        if match_status == 'unmatched' or not critique_art_id:
            findings.append({
                "check": "UNMATCHED_REF",
                "severity": "MEDIUM",
                "article_id": None,
                "current_value": None,
                "corrected_value": None,
                "clean_ref": clean_ref_from_critique[:150],
                "citation_count": None,
                "detail": (
                    f"QID {qid} (exam {year}): critique citation has no matching DB article. "
                    f"Citation: '{clean_ref_from_critique[:100]}'"
                )
            })
            continue

        # QID_MISMATCH: DB has a different article linked to this QID
        db_art_id = db_qid_to_art.get(qid)
        match_score = rec.get('match_score', 0.0)
        if db_art_id and critique_art_id and db_art_id != critique_art_id:
            findings.append({
                "check": "QID_MISMATCH",
                "severity": "HIGH",
                "article_id": critique_art_id,
                "current_value": db_art_id,
                "corrected_value": critique_art_id,
                "clean_ref": clean_ref_from_critique[:150],
                "citation_count": None,
                "match_score": match_score,  # 1.0 = exact match → SQL-eligible
                "qid": qid,
                "exam_year": year,
                "detail": (
                    f"QID {qid} (exam {year}): critique says → {critique_art_id}, "
                    f"but DB has → {db_art_id}. "
                    f"match_score={match_score:.2f}. "
                    f"Critique citation: '{clean_ref_from_critique[:80]}'"
                )
            })

    return findings


def build_summary(findings: list[dict], total_articles: int) -> dict:
    by_check = defaultdict(int)
    by_severity = defaultdict(int)
    for f in findings:
        by_check[f['check']] += 1
        by_severity[f['severity']] += 1
    return {
        "total_articles": total_articles,
        "total_findings": len(findings),
        "by_check": dict(by_check),
        "by_severity": dict(by_severity)
    }


def main():
    parser = argparse.ArgumentParser(description="Article Citation QC")
    parser.add_argument("--staging-dir", required=True, help="Path to M2/outputs/ with staging JSONs")
    parser.add_argument("--output-dir", required=True, help="Where to write qc_results.json")
    parser.add_argument("--db-path", help="Path to ite_intelligence.db (auto-detected if omitted)")
    args = parser.parse_args()

    staging_dir = Path(args.staging_dir).resolve()
    output_dir  = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Auto-detect DB path relative to this script's location
    if args.db_path:
        db_path = Path(args.db_path).resolve()
    else:
        # Script lives in <skill>/scripts/; DB is at PROJECT_ROOT/00_database/db/
        # PROJECT_ROOT can be detected from staging_dir (which is M2/outputs/)
        # M2/outputs/../.. = PROJECT_ROOT
        db_path = (staging_dir.parent.parent / "00_database" / "db" / "ite_intelligence.db").resolve()

    print(f"DB:          {db_path}")
    print(f"Staging dir: {staging_dir}")
    print(f"Output dir:  {output_dir}")

    if not db_path.exists():
        print(f"ERROR: DB not found at {db_path}")
        return 1

    # Load staging JSONs
    staging_records, years_found, years_missing = load_staging_jsons(staging_dir)
    print(f"Staging JSONs loaded: {sorted(years_found)} ({len(staging_records)} records total)")
    if years_missing:
        print(f"WARNING: Missing staging JSONs for years: {years_missing}")
        print("  → Run extract_ite_critique_refs.py for missing years before re-running QC.")

    # Open DB and run checks
    conn = load_db(db_path)
    print("Running QC checks...")
    findings = run_checks(conn, staging_records)
    conn.close()

    # Count articles for summary
    conn2 = load_db(db_path)
    total_articles = conn2.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    conn2.close()

    summary = build_summary(findings, total_articles)

    result = {
        "summary": summary,
        "years_processed": sorted(years_found),
        "years_missing": years_missing,
        "findings": findings
    }

    out_path = output_dir / "qc_results.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\n=== QC SUMMARY ===")
    print(f"Total articles: {summary['total_articles']}")
    print(f"Total findings: {summary['total_findings']}")
    for check, cnt in sorted(summary['by_check'].items()):
        print(f"  {check}: {cnt}")
    print(f"\nResults written to: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
