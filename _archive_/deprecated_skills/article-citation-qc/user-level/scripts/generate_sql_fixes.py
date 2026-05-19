"""
generate_sql_fixes.py
======================
Reads qc_results.json and generates article_qc_fixes.sql with ready-to-run
SQL UPDATE statements for auto-fixable findings.

Auto-fixable:
  TRUNC_TITLE     → UPDATE articles SET title = '...' WHERE article_id = '...'
  AUTHOR_ARTIFACT → UPDATE articles SET author1 = '...' WHERE article_id = '...'
  QID_MISMATCH    → UPDATE qid_art_xref SET article_id = '...' WHERE qid = '...'
                    (ONLY for match_score = 1.0 exact matches)

Non-auto-fixable (report only):
  UMBRELLA, UNMATCHED_REF, NULL_CLEAN_REF

Usage:
    python generate_sql_fixes.py \
        --qc-results ../../03_module.3_analyst/outputs/article_qc/qc_results.json \
        --output-dir ../../03_module.3_analyst/outputs/article_qc/
"""

import json
import argparse
from pathlib import Path
from datetime import datetime


def escape_sql(value: str) -> str:
    if value is None:
        return "NULL"
    return value.replace("'", "''")


def generate_sql(findings: list[dict]) -> tuple[str, dict]:
    lines = [
        f"-- article_qc_fixes.sql",
        f"-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"-- REVIEW BEFORE RUNNING. Each statement is preceded by a comment",
        f"-- explaining the change. Run in SQLite3 or DB Browser.",
        f"--",
        f"-- Source: run_citation_qc.py findings",
        f"",
        f"BEGIN TRANSACTION;",
        f"",
    ]

    stats = {"TRUNC_TITLE": 0, "AUTHOR_ARTIFACT": 0, "QID_MISMATCH_exact": 0,
             "QID_MISMATCH_skipped": 0}

    trunc_findings = [f for f in findings if f['check'] == 'TRUNC_TITLE'
                      and f.get('corrected_value')]
    if trunc_findings:
        lines.append(f"-- ══════════════════════════════════════════════════════")
        lines.append(f"-- TRUNC_TITLE fixes ({len(trunc_findings)} articles)")
        lines.append(f"-- These articles have truncated/fragmented titles in the DB.")
        lines.append(f"-- Corrected titles are extracted from the clean_ref field.")
        lines.append(f"-- ══════════════════════════════════════════════════════")
        lines.append(f"")

        for f in sorted(trunc_findings, key=lambda x: x['article_id']):
            art_id = f['article_id']
            current = f['current_value'] or ''
            corrected = f['corrected_value'] or ''
            cited = f.get('citation_count', 0)

            lines.append(f"-- {art_id} | cited {cited}x")
            lines.append(f"-- Before: '{current[:80]}'")
            lines.append(f"-- After:  '{corrected[:80]}'")
            lines.append(
                f"UPDATE articles SET title = '{escape_sql(corrected)}' "
                f"WHERE article_id = '{art_id}';"
            )
            lines.append(f"")
            stats["TRUNC_TITLE"] += 1

    author_findings = [f for f in findings if f['check'] == 'AUTHOR_ARTIFACT'
                       and f.get('corrected_value')]
    if author_findings:
        lines.append(f"-- ══════════════════════════════════════════════════════")
        lines.append(f"-- AUTHOR_ARTIFACT fixes ({len(author_findings)} articles)")
        lines.append(f"-- These articles have a parsing stop-word as author1.")
        lines.append(f"-- ══════════════════════════════════════════════════════")
        lines.append(f"")

        for f in sorted(author_findings, key=lambda x: x['article_id']):
            art_id = f['article_id']
            current = f['current_value'] or ''
            corrected = f['corrected_value'] or ''

            lines.append(f"-- {art_id}")
            lines.append(f"-- Before: '{current}'")
            lines.append(f"-- After:  '{corrected[:60]}'")
            lines.append(
                f"UPDATE articles SET author1 = '{escape_sql(corrected)}' "
                f"WHERE article_id = '{art_id}';"
            )
            lines.append(f"")
            stats["AUTHOR_ARTIFACT"] += 1

    qid_findings_exact = [
        f for f in findings
        if f['check'] == 'QID_MISMATCH' and f.get('match_score', 0) == 1.0
    ]
    qid_findings_fuzzy = [
        f for f in findings
        if f['check'] == 'QID_MISMATCH' and f.get('match_score', 0) < 1.0
    ]

    if qid_findings_exact:
        lines.append(f"-- ══════════════════════════════════════════════════════")
        lines.append(f"-- QID_MISMATCH fixes — EXACT MATCH ONLY ({len(qid_findings_exact)} rows)")
        lines.append(f"-- Critique citation matched DB article with match_score = 1.0.")
        lines.append(f"-- These update qid_art_xref to point to the correct article.")
        lines.append(f"-- {len(qid_findings_fuzzy)} fuzzy-matched mismatches are in the report only (manual review).")
        lines.append(f"-- ══════════════════════════════════════════════════════")
        lines.append(f"")

        for f in qid_findings_exact:
            qid = f.get('qid', '')
            year = f.get('exam_year', '')
            current = f.get('current_value', '')
            corrected = f.get('corrected_value', '')

            lines.append(f"-- {qid} (exam {year})")
            lines.append(f"-- DB had: {current} | Critique says: {corrected}")
            lines.append(f"-- Citation: '{(f.get('clean_ref') or '')[:80]}'")
            lines.append(
                f"UPDATE qid_art_xref SET article_id = '{escape_sql(corrected)}' "
                f"WHERE qid = '{qid}' AND exam_year = {year};"
            )
            lines.append(f"")
            stats["QID_MISMATCH_exact"] += 1

    stats["QID_MISMATCH_skipped"] = len(qid_findings_fuzzy)

    lines.append(f"COMMIT;")
    lines.append(f"")
    lines.append(f"-- ══════════════════════════════════════════════════════")
    lines.append(f"-- Fix summary:")
    lines.append(f"--   TRUNC_TITLE:     {stats['TRUNC_TITLE']} articles")
    lines.append(f"--   AUTHOR_ARTIFACT: {stats['AUTHOR_ARTIFACT']} articles")
    lines.append(f"--   QID_MISMATCH:    {stats['QID_MISMATCH_exact']} exact (+ {stats['QID_MISMATCH_skipped']} fuzzy skipped)")
    lines.append(f"-- ══════════════════════════════════════════════════════")

    return "\n".join(lines), stats


def main():
    parser = argparse.ArgumentParser(description="Generate SQL fixes from QC results")
    parser.add_argument("--qc-results", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    qc_path = Path(args.qc_results).resolve()
    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(qc_path) as f:
        qc_data = json.load(f)

    findings = qc_data.get('findings', [])
    sql_text, stats = generate_sql(findings)

    out_path = out_dir / "article_qc_fixes.sql"
    with open(out_path, "w") as f:
        f.write(sql_text)

    print(f"SQL fixes written to: {out_path}")
    print(f"TRUNC_TITLE:     {stats['TRUNC_TITLE']}")
    print(f"AUTHOR_ARTIFACT: {stats['AUTHOR_ARTIFACT']}")
    print(f"QID_MISMATCH:    {stats['QID_MISMATCH_exact']} exact + {stats['QID_MISMATCH_skipped']} fuzzy (skipped)")


if __name__ == "__main__":
    raise SystemExit(main())
