"""
generate_citation_sql.py
=========================
Generates article_qc_fixes.sql from staging JSONs + qc_results.json.

Philosophy: the ITE critique PDFs are the source of truth.
qid_art_xref should be a faithful transcript of what each critique listed —
no consolidation, no deduplication, no single-reference-per-question assumption.

Fix strategy:
  TRUNC_TITLE      → UPDATE articles SET title = '...' WHERE article_id = '...'
  AUTHOR_ARTIFACT  → UPDATE articles SET author1 = '...' WHERE article_id = '...'
  QID_XREF_REBUILD → For each QID found in staging JSONs with ≥1 matched reference:
                       DELETE FROM qid_art_xref WHERE qid = '...' AND exam_year = NNNN
                       INSERT OR IGNORE for every matched reference (exact AND fuzzy)
                     QIDs with NO matched references in staging are left untouched
                     (existing DB link preserved as fallback).

Usage:
    cd PROJECT_ROOT/03_module.3_analyst/scripts/
    python generate_citation_sql.py \
        --qc-results ../../03_module.3_analyst/outputs/article_qc/qc_results.json \
        --staging-dir ../../02_module.2_processor/outputs/ \
        --output-dir ../../03_module.3_analyst/outputs/article_qc/
"""

import json
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict

SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH      = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"
ITE_YEARS    = list(range(2018, 2026))


def escape_sql(value) -> str:
    if value is None:
        return "NULL"
    return str(value).replace("'", "''")


def load_db(db_path: Path):
    uri = f"file:{db_path}?immutable=1"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def load_article_meta(db_path: Path) -> dict:
    """Load tier, author1, year from articles table for INSERT statements."""
    conn = load_db(db_path)
    rows = conn.execute("SELECT article_id, tier, author1, year FROM articles").fetchall()
    conn.close()
    return {row["article_id"]: dict(row) for row in rows}


def load_existing_xref(db_path: Path) -> set:
    """Load all (qid, exam_year) pairs currently in qid_art_xref."""
    conn = load_db(db_path)
    rows = conn.execute("SELECT DISTINCT qid, exam_year FROM qid_art_xref").fetchall()
    conn.close()
    return {(row["qid"], row["exam_year"]) for row in rows}


def load_existing_xref_full(db_path: Path) -> dict:
    """Load qid_art_xref grouped as (qid, exam_year) → set[article_id].
    Used to detect identity-rebuild QIDs (DELETE + same INSERTs = no-op churn)."""
    conn = load_db(db_path)
    rows = conn.execute("SELECT qid, article_id, exam_year FROM qid_art_xref").fetchall()
    conn.close()
    grouped: dict[tuple[str, int], set[str]] = defaultdict(set)
    for row in rows:
        grouped[(row["qid"], row["exam_year"])].add(row["article_id"])
    return grouped


def load_staging_jsons(staging_dir: Path) -> tuple[dict, list[int]]:
    """
    Load all staging JSONs. Group matched records by (qid, exam_year).
    Only includes records with match_status in (matched, fuzzy_matched) AND a valid article_id.
    Returns: (grouped_refs dict, years_loaded list)
    """
    grouped = defaultdict(list)
    years_loaded = []

    for year in ITE_YEARS:
        path = staging_dir / f"{year}_critique_refs_staging.json"
        if not path.exists():
            continue
        records = json.load(open(path, encoding='utf-8'))
        years_loaded.append(year)
        for rec in records:
            status = rec.get("match_status", "")
            art_id = rec.get("_article_id") or rec.get("article_id")
            if status in ("matched", "fuzzy_matched") and art_id:
                key = (rec.get("qid"), year)
                grouped[key].append({
                    "article_id": art_id,
                    "match_score": rec.get("match_score", 0.0),
                    "match_status": status,
                    "clean_ref": (rec.get("clean_ref") or "")[:80],
                    "ref_index": rec.get("ref_index", 1),
                })

    return grouped, years_loaded


def generate_sql(findings: list[dict], staging_dir: Path, db_path: Path) -> tuple[str, dict]:
    articles      = load_article_meta(db_path)
    existing_xref = load_existing_xref(db_path)
    db_xref_full  = load_existing_xref_full(db_path)
    grouped_refs, years_loaded = load_staging_jsons(staging_dir)

    lines = [
        f"-- article_qc_fixes.sql",
        f"-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"-- Staging years: {', '.join(str(y) for y in sorted(years_loaded))}",
        f"--",
        f"-- Sections:",
        f"--   1. TRUNC_TITLE      — fix truncated article title fields",
        f"--   2. AUTHOR_ARTIFACT  — fix parser stop-word author1 fields",
        f"--   3. QID_XREF_REBUILD — rebuild qid_art_xref from critique ground truth",
        f"--",
        f"-- BACKUP RULE: QIDs with no matched references in any staging JSON",
        f"-- are left untouched. Existing DB link preserved as fallback.",
        f"-- These appear in the 'No-reference QIDs' section at the bottom.",
        f"--",
        f"-- REVIEW BEFORE RUNNING. Run in DB Browser. Use SAVEPOINT per section.",
        f"",
        f"BEGIN TRANSACTION;",
        f"",
    ]

    stats = {
        "TRUNC_TITLE": 0, "AUTHOR_ARTIFACT": 0,
        "QID_rebuilt": 0, "QID_inserted": 0,
        "QID_exact": 0, "QID_fuzzy": 0,
        "QID_no_ref_preserved": 0,
        "QID_skipped_identity": 0,
        "QID_extra_db_links": 0,
    }

    # ── SECTION 1: TRUNC_TITLE ────────────────────────────────────────────────
    trunc = [f for f in findings if f["check"] == "TRUNC_TITLE" and f.get("corrected_value")]
    lines += [
        f"-- ═══════════════════════════════════════════════════════",
        f"-- SECTION 1: TRUNC_TITLE ({len(trunc)} articles)",
        f"-- ═══════════════════════════════════════════════════════",
        f"",
    ]
    for f in sorted(trunc, key=lambda x: x["article_id"]):
        cur = (f.get("current_value") or "")[:75]
        fix = (f.get("corrected_value") or "")[:75]
        lines += [
            f"-- {f['article_id']} | cited {f.get('citation_count', 0)}x",
            f"-- Before: '{cur}'",
            f"-- After:  '{fix}'",
            f"UPDATE articles SET title = '{escape_sql(f['corrected_value'])}' "
            f"WHERE article_id = '{f['article_id']}';",
            f"",
        ]
        stats["TRUNC_TITLE"] += 1

    # ── SECTION 2: AUTHOR_ARTIFACT ────────────────────────────────────────────
    author = [f for f in findings if f["check"] == "AUTHOR_ARTIFACT" and f.get("corrected_value")]
    lines += [
        f"-- ═══════════════════════════════════════════════════════",
        f"-- SECTION 2: AUTHOR_ARTIFACT ({len(author)} articles)",
        f"-- ═══════════════════════════════════════════════════════",
        f"",
    ]
    for f in sorted(author, key=lambda x: x["article_id"]):
        lines += [
            f"-- {f['article_id']} | cited {f.get('citation_count', 0)}x",
            f"-- Before: '{f.get('current_value', '')}'",
            f"-- After:  '{(f.get('corrected_value') or '')[:55]}'",
            f"UPDATE articles SET author1 = '{escape_sql(f['corrected_value'])}' "
            f"WHERE article_id = '{f['article_id']}';",
            f"",
        ]
        stats["AUTHOR_ARTIFACT"] += 1

    # ── SECTION 3: QID_XREF_REBUILD ──────────────────────────────────────────
    # Identity-rebuild skip: if the staging-prescribed article set for a QID is
    # exactly equal to the DB's current article set for that QID, the rebuild is
    # a no-op (DELETE + re-INSERT same rows). Skip these to keep the SQL focused
    # on actual changes.
    qids_all_with_refs = sorted(grouped_refs.keys())
    qids_to_rebuild = []      # (qid, year) where staging != DB → real change
    qids_identity_skip = []   # (qid, year) where staging == DB → no-op
    qids_with_extra_db = {}   # (qid, year) → set of extras (DB - staging)

    for key in qids_all_with_refs:
        staging_arts = {r["article_id"] for r in grouped_refs[key]}
        db_arts      = db_xref_full.get(key, set())
        if staging_arts == db_arts:
            qids_identity_skip.append(key)
        else:
            qids_to_rebuild.append(key)
            extras = db_arts - staging_arts
            if extras:
                qids_with_extra_db[key] = extras

    total_inserts = sum(len(grouped_refs[k]) for k in qids_to_rebuild)
    exact_count   = sum(1 for k in qids_to_rebuild for r in grouped_refs[k] if r["match_score"] == 1.0)
    fuzzy_count   = total_inserts - exact_count

    # QIDs in DB but not in any staging JSON → preserved (backup fallback)
    no_ref_qids = existing_xref - {(qid, yr) for (qid, yr) in qids_all_with_refs}

    lines += [
        f"-- ═══════════════════════════════════════════════════════",
        f"-- SECTION 3: QID_XREF_REBUILD",
        f"-- Rebuilds qid_art_xref to match critique ground truth exactly.",
        f"-- {len(qids_all_with_refs)} QIDs have staging matches; {len(qids_identity_skip)} are",
        f"-- identity-equal to DB (skipped — rebuild would be no-op).",
        f"-- {len(qids_to_rebuild)} QIDs require actual rebuild ({len(qids_with_extra_db)} of these",
        f"-- have extra DB linkages beyond critique — see Section 3b for triage).",
        f"-- {len(qids_to_rebuild)} DELETE + {total_inserts} INSERT statements.",
        f"-- {exact_count} exact refs | {fuzzy_count} fuzzy refs.",
        f"-- {len(no_ref_qids)} QIDs have no staging match → left untouched (backup rule).",
        f"-- ═══════════════════════════════════════════════════════",
        f"",
    ]

    stats["QID_skipped_identity"] = len(qids_identity_skip)
    stats["QID_extra_db_links"]   = len(qids_with_extra_db)

    by_year = defaultdict(list)
    for (qid, year) in qids_to_rebuild:
        by_year[year].append(qid)

    for year in sorted(by_year):
        qids_this_year = sorted(by_year[year])
        lines += [
            f"-- ── {year} ({len(qids_this_year)} QIDs) ─────────────────────────────",
            f"",
        ]
        for qid in qids_this_year:
            refs = sorted(grouped_refs[(qid, year)], key=lambda r: r["ref_index"])
            db_arts = db_xref_full.get((qid, year), set())
            staging_arts = {r["article_id"] for r in refs}
            removed = sorted(db_arts - staging_arts)
            added   = sorted(staging_arts - db_arts)

            change_note = []
            if removed:
                change_note.append(f"removes {removed}")
            if added:
                change_note.append(f"adds {added}")
            change_str = "; ".join(change_note) if change_note else "no change"

            lines += [
                f"-- {qid}: {len(refs)} critique reference(s) — {change_str}",
                f"DELETE FROM qid_art_xref WHERE qid = '{qid}' AND exam_year = {year};",
            ]
            for ref in refs:
                art_id = ref["article_id"]
                score  = ref["match_score"]
                cite   = ref.get("clean_ref", "").replace('\r\n', ' ').replace('\n', ' ').replace('\r', ' ')
                art    = articles.get(art_id, {})
                tier   = art.get("tier") or "unknown"
                a1     = art.get("author1") or ""
                yr_val = art.get("year") or ""
                label  = "exact" if score == 1.0 else f"fuzzy {score:.2f}"
                lines += [
                    f"-- ref {ref['ref_index']} [{label}]: {cite}",
                    f"INSERT OR IGNORE INTO qid_art_xref "
                    f"(qid, article_id, tier, exam_year, author1, year) VALUES "
                    f"('{qid}', '{art_id}', '{escape_sql(tier)}', {year}, "
                    f"'{escape_sql(a1)}', '{escape_sql(yr_val)}');",
                ]
                if score == 1.0:
                    stats["QID_exact"] += 1
                else:
                    stats["QID_fuzzy"] += 1
            lines.append(f"")
            stats["QID_rebuilt"] += 1
            stats["QID_inserted"] += len(refs)

    # ── SECTION 3b: EXTRA_DB_LINK triage stubs ────────────────────────────────
    # These QIDs got their xref shrunk by Section 3 above (DB had ≥1 article that
    # the critique extractor did not find). Surfaced for human review — no SQL to
    # apply by default; the rebuild already takes effect via Section 3's DELETE.
    if qids_with_extra_db:
        lines += [
            f"",
            f"-- ═══════════════════════════════════════════════════════",
            f"-- SECTION 3b: EXTRA_DB_LINK summary ({len(qids_with_extra_db)} QIDs)",
            f"-- These QIDs had article linkages in qid_art_xref that the critique",
            f"-- extractor did not produce. Possible causes:",
            f"--   (a) extractor false-negative — review the critique PDF entry",
            f"--   (b) acquisition-pipeline speculative linkage (e.g. BATON 065's",
            f"--       acquire_missing_citations.py adding ART-20XX articles)",
            f"-- Section 3 above WILL remove these by default. If any should be kept,",
            f"-- manually edit Section 3 to skip the DELETE for that QID.",
            f"-- ═══════════════════════════════════════════════════════",
            f"",
        ]
        for (qid, year) in sorted(qids_with_extra_db):
            extras = sorted(qids_with_extra_db[(qid, year)])
            kept = sorted({r["article_id"] for r in grouped_refs[(qid, year)]})
            lines.append(
                f"-- {qid} (yr {year}): keeping {kept}, "
                f"removing extras {extras}"
            )
        lines.append(f"")

    # ── BACKUP: list preserved no-ref QIDs as comments ────────────────────────
    if no_ref_qids:
        stats["QID_no_ref_preserved"] = len(no_ref_qids)
        lines += [
            f"-- ═══════════════════════════════════════════════════════",
            f"-- BACKUP: {len(no_ref_qids)} QIDs with no staging match — NOT MODIFIED",
            f"-- These QIDs are in qid_art_xref but appeared in no staging JSON.",
            f"-- Possible causes: question had no References section in the critique PDF,",
            f"-- or the parser missed it. Existing DB link preserved as fallback.",
            f"-- Review these manually if needed.",
            f"-- ═══════════════════════════════════════════════════════",
            f"",
        ]
        for (qid, yr) in sorted(no_ref_qids):
            lines.append(f"-- PRESERVED (no staging match): {qid} (exam {yr})")
        lines.append(f"")

    lines += [
        f"COMMIT;",
        f"",
        f"-- ═══════════════════════════════════════════════════════",
        f"-- Summary:",
        f"--   TRUNC_TITLE:           {stats['TRUNC_TITLE']} article title updates",
        f"--   AUTHOR_ARTIFACT:       {stats['AUTHOR_ARTIFACT']} author1 updates",
        f"--   QID_XREF_REBUILD:      {stats['QID_rebuilt']} QIDs rebuilt",
        f"--                          {stats['QID_inserted']} total INSERTs",
        f"--                          ({stats['QID_exact']} exact + {stats['QID_fuzzy']} fuzzy)",
        f"--   IDENTITY-SKIPPED:      {stats['QID_skipped_identity']} QIDs (staging == DB, no-op)",
        f"--   EXTRA_DB_LINK FLAGGED: {stats['QID_extra_db_links']} QIDs (DB had links not in critique)",
        f"--   PRESERVED:             {stats['QID_no_ref_preserved']} QIDs with no staging match",
        f"-- ═══════════════════════════════════════════════════════",
    ]

    return "\n".join(lines), stats


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--qc-results", required=True)
    parser.add_argument("--staging-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--db-path", default=None)
    args = parser.parse_args()

    staging_dir = Path(args.staging_dir).resolve()
    out_dir     = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    db_path = Path(args.db_path).resolve() if args.db_path else (
        (staging_dir.parent.parent / "00_database" / "db" / "ite_intelligence.db").resolve()
    )
    if not db_path.exists():
        print(f"ERROR: DB not found at {db_path}")
        return 1

    findings = json.load(open(args.qc_results, encoding='utf-8')).get("findings", [])
    sql_text, stats = generate_sql(findings, staging_dir, db_path)

    out_path = out_dir / "article_qc_fixes.sql"
    out_path.write_text(sql_text, encoding="utf-8")

    print(f"Written: {out_path}")
    print(f"TRUNC_TITLE:           {stats['TRUNC_TITLE']}")
    print(f"AUTHOR_ARTIFACT:       {stats['AUTHOR_ARTIFACT']}")
    print(f"QID_XREF_REBUILD:      {stats['QID_rebuilt']} QIDs needing real change -> "
          f"{stats['QID_inserted']} inserts "
          f"({stats['QID_exact']} exact + {stats['QID_fuzzy']} fuzzy)")
    print(f"IDENTITY-SKIPPED:      {stats['QID_skipped_identity']} QIDs (staging == DB, no-op)")
    print(f"EXTRA_DB_LINK FLAGGED: {stats['QID_extra_db_links']} QIDs (DB had extras)")
    print(f"PRESERVED:             {stats['QID_no_ref_preserved']} QIDs (no staging match)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
