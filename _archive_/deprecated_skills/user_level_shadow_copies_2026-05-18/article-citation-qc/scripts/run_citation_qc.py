"""
run_citation_qc.py
==================
Article Citation QC — reads all available staging JSONs + ite_intelligence.db,
runs six QC checks, writes qc_results.json to --output-dir.

Usage:
    cd PROJECT_ROOT/03_module.3_analyst/scripts/
    python run_citation_qc.py \
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
    if not clean_ref:
        return None

    ref = clean_ref.strip()
    segments = re.split(r'\.\s+', ref)

    if len(segments) < 1:
        return None

    first_seg = segments[0].strip()

    is_org_byline = (
        ',' not in first_seg and
        len(first_seg) > 40 and
        len(first_seg.split()) >= 4
    )

    if is_org_byline:
        return first_seg

    for seg in segments[1:]:
        seg = seg.strip()
        if not seg:
            continue
        if re.match(r'^\d{4}', seg):
            continue
        if re.match(r'^\d+[\(\d]', seg):
            continue
        if seg.startswith('http') or seg.startswith('www'):
            continue
        if len(seg) < 15:
            continue
        if re.match(r'^[A-Za-z ]+\d{4}', seg):
            continue
        return seg

    return None


def is_truncated_title(db_title: str, extracted_title: str) -> bool:
    if not db_title or not extracted_title:
        return False

    db = db_title.strip().lower()
    ext = extracted_title.strip().lower()

    if re.match(r'^\d+[\-–]\d+$', db_title.strip()):
        return True

    if ':' in ext:
        after_colon = ext.split(':', 1)[1].strip()
        if db == after_colon:
            return True

    if len(db) < len(ext) * 0.7 and ext.endswith(db):
        return True

    if db in ext and len(db) < len(ext) * 0.6:
        return True

    return False


def load_db(db_path: Path):
    uri = f"file:{db_path}?immutable=1"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def load_staging_jsons(staging_dir: Path) -> tuple[list[dict], list[int], list[int]]:
    all_records = []
    years_found = []
    years_missing = []

    for year in ITE_YEARS:
        path = staging_dir / f"{year}_critique_refs_staging.json"
        if path.exists():
            with open(path, encoding="utf-8") as f:
                records = json.load(f)
            for rec in records:
                rec['exam_year'] = year
            all_records.extend(records)
            years_found.append(year)
        else:
            years_missing.append(year)

    return all_records, years_found, years_missing


def run_checks(conn, staging_records: list[dict]) -> list[dict]:
    findings = []
    cursor = conn.cursor()

    cursor.execute("""
        SELECT article_id, title, author1, clean_ref, citation_display,
               citation_count, unique_years, qid_list, source_type
        FROM articles
    """)
    articles = {row['article_id']: dict(row) for row in cursor.fetchall()}

    # qid_art_xref: build qid → set[article_id] (a QID can have multiple xref rows;
    # the prior dict assignment kept only the last article_id per QID and produced
    # phantom QID_MISMATCH findings equal to (n_refs - 1) per multi-ref QID).
    cursor.execute("SELECT qid, article_id, exam_year FROM qid_art_xref")
    db_qid_arts: dict[str, set[str]] = defaultdict(set)
    for row in cursor.fetchall():
        db_qid_arts[row['qid']].add(row['article_id'])

    try:
        cursor.execute("SELECT question_id, blueprint_category, body_system FROM questions")
        q_meta = {row['question_id']: dict(row) for row in cursor.fetchall()}
    except Exception:
        q_meta = {}

    # ── TRUNC_TITLE + AUTHOR_ARTIFACT + NULL_CLEAN_REF ────────────────────────
    for art_id, art in articles.items():
        clean_ref = art.get('clean_ref') or ''
        db_title  = art.get('title') or ''
        author1   = art.get('author1') or ''

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

        if author1 and author1.strip().lower().rstrip('.') in AUTHOR_STOP_WORDS:
            corrected_author = None
            if clean_ref:
                first_seg = re.split(r'\.\s+', clean_ref)[0].strip()
                if ',' in first_seg:
                    corrected_author = first_seg.split(',')[0].strip()
                else:
                    org_name = re.split(r'[:\.]', first_seg)[0].strip()
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

    # ── UMBRELLA ──────────────────────────────────────────────────────────────
    for art_id, art in articles.items():
        citation_count = art.get('citation_count') or 0
        unique_years   = art.get('unique_years') or 0

        if citation_count < 5 or unique_years < 3:
            continue

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

    # ── QID_MISMATCH + UNMATCHED_REF ─────────────────────────────────────────
    # Collect critique-side article_ids per QID for the inverse EXTRA_DB_LINK
    # check at the bottom.
    critique_qid_arts: dict[str, set[str]] = defaultdict(set)
    critique_qid_year: dict[str, int] = {}

    for rec in staging_records:
        qid = rec.get('qid')
        critique_art_id = rec.get('_article_id') or rec.get('article_id')
        match_status = rec.get('match_status', 'unknown')
        clean_ref_from_critique = rec.get('clean_ref') or ''
        year = rec.get('exam_year')

        if not qid:
            continue

        if match_status == 'unmatched' or not critique_art_id:
            findings.append({
                "check": "UNMATCHED_REF",
                "severity": "MEDIUM",
                "article_id": None,
                "current_value": None,
                "corrected_value": None,
                "clean_ref": clean_ref_from_critique[:150],
                "citation_count": None,
                "qid": qid,
                "exam_year": year,
                "detail": (
                    f"QID {qid} (exam {year}): critique citation has no matching DB article. "
                    f"Citation: '{clean_ref_from_critique[:100]}'"
                )
            })
            continue

        # Track this critique-side linkage for the EXTRA_DB_LINK pass below.
        critique_qid_arts[qid].add(critique_art_id)
        critique_qid_year[qid] = year

        # True QID_MISMATCH: critique-claimed article is NOT in the DB xref for
        # this QID (set membership, not single-value equality). The DB may carry
        # multiple linkages per QID — that is expected and not a mismatch by itself.
        db_arts_for_qid = db_qid_arts.get(qid, set())
        match_score = rec.get('match_score', 0.0)
        if db_arts_for_qid and critique_art_id not in db_arts_for_qid:
            findings.append({
                "check": "QID_MISMATCH",
                "severity": "HIGH",
                "article_id": critique_art_id,
                "current_value": ", ".join(sorted(db_arts_for_qid)),
                "corrected_value": critique_art_id,
                "clean_ref": clean_ref_from_critique[:150],
                "citation_count": None,
                "match_score": match_score,
                "qid": qid,
                "exam_year": year,
                "detail": (
                    f"QID {qid} (exam {year}): critique says → {critique_art_id}, "
                    f"DB xref has → {sorted(db_arts_for_qid)}. "
                    f"match_score={match_score:.2f}. "
                    f"Critique citation: '{clean_ref_from_critique[:80]}'"
                )
            })

    # ── EXTRA_DB_LINK ─────────────────────────────────────────────────────────
    # DB has linkages that the critique extractor did not produce. Two causes:
    # (a) extractor false-negative — critique listed it but parser missed it; OR
    # (b) speculative linkage from acquisition pipeline (e.g. acquire_missing_
    #     citations.py in BATON 065) that is not in the critique reference list.
    # Either way, surfaced for human triage. Severity MEDIUM — not auto-fixed.
    for qid, db_arts in db_qid_arts.items():
        if qid not in critique_qid_arts:
            # QID has DB linkages but no matched staging records at all.
            # This is the "preserved" set (treated by SQL generator's BACKUP rule).
            # Reported separately as PRESERVED_NO_CRITIQUE for visibility.
            findings.append({
                "check": "PRESERVED_NO_CRITIQUE",
                "severity": "LOW",
                "article_id": None,
                "current_value": ", ".join(sorted(db_arts)),
                "corrected_value": None,
                "clean_ref": None,
                "citation_count": None,
                "qid": qid,
                "exam_year": None,
                "detail": (
                    f"QID {qid}: DB xref has {sorted(db_arts)} but staging JSONs "
                    f"have no matched references for this QID. Likely critique-extraction "
                    f"miss for the QID block, or QID predates current extraction range."
                )
            })
            continue

        extras = db_arts - critique_qid_arts[qid]
        if extras:
            findings.append({
                "check": "EXTRA_DB_LINK",
                "severity": "MEDIUM",
                "article_id": None,
                "current_value": ", ".join(sorted(db_arts)),
                "corrected_value": ", ".join(sorted(critique_qid_arts[qid])),
                "clean_ref": None,
                "citation_count": None,
                "qid": qid,
                "exam_year": critique_qid_year.get(qid),
                "extra_articles": sorted(extras),
                "detail": (
                    f"QID {qid}: DB xref carries {sorted(db_arts)} but critique only "
                    f"references {sorted(critique_qid_arts[qid])}. "
                    f"Extra DB linkages: {sorted(extras)} — "
                    f"likely BATON 065 acquisition-pipeline additions or extraction misses. "
                    f"Triage before treating Section 3 rebuild as authoritative."
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
    parser.add_argument("--staging-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--db-path", help="Path to ite_intelligence.db (auto-detected if omitted)")
    args = parser.parse_args()

    staging_dir = Path(args.staging_dir).resolve()
    output_dir  = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.db_path:
        db_path = Path(args.db_path).resolve()
    else:
        db_path = (staging_dir.parent.parent / "00_database" / "db" / "ite_intelligence.db").resolve()

    print(f"DB:          {db_path}")
    print(f"Staging dir: {staging_dir}")
    print(f"Output dir:  {output_dir}")

    if not db_path.exists():
        print(f"ERROR: DB not found at {db_path}")
        return 1

    staging_records, years_found, years_missing = load_staging_jsons(staging_dir)
    print(f"Staging JSONs loaded: {sorted(years_found)} ({len(staging_records)} records total)")
    if years_missing:
        print(f"WARNING: Missing staging JSONs for years: {years_missing}")

    conn = load_db(db_path)
    print("Running QC checks...")
    findings = run_checks(conn, staging_records)
    conn.close()

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
    with open(out_path, "w", encoding="utf-8") as f:
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
