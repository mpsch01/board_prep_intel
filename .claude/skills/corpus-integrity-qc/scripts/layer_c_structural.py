"""
layer_c_structural.py
=====================
Layer C — Structural Integrity Audit.

Compares derived caches in the `articles` table against the source-of-truth
`qid_art_xref` bridge. Flags drift in:

  C1. qid_list cache               (JSON list cached on articles)
  C2. citation_count               (int cached on articles)
  C3. exam_years cache             (JSON list of distinct exam_years)
  C4. unique_years cache           (int — len of distinct-years set)
  C5. orphan xref rows             (point to non-existent qid or article_id)
  C6. zero_citation_linked         (citation_count==0 but xref rows exist)
  C7. unlinked_cited_article       (citation_count>0 but no xref rows)

All checks are SQL-only — no PDF I/O. Read-only access via immutable URI.

Usage:
  python layer_c_structural.py --output-dir <OUTPUT_DIR>

Output:
  findings_layer_c.json  — structured findings list + summary

Ground truth: qid_art_xref. The cached columns on articles are reconstructible
from this bridge; any drift is a finding.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

# Allow running this script standalone OR as `python -m scripts.layer_c_structural`
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from utils import (  # noqa: E402
    connect_db_readonly,
    resolve_db_path,
    setup_utf8_stdout,
)

setup_utf8_stdout()


def _parse_json_list(raw: str | None) -> list:
    """Tolerant parse of a JSON-list-or-NULL column."""
    if raw is None:
        return []
    if isinstance(raw, list):
        return raw
    if not isinstance(raw, str):
        return []
    raw = raw.strip()
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return parsed
        return []
    except json.JSONDecodeError:
        return []


def _set_equal(a: list | set, b: list | set) -> bool:
    return set(a) == set(b)


def run_layer_c(db_path: Path) -> list[dict]:
    findings: list[dict] = []
    conn = connect_db_readonly(db_path)
    cur = conn.cursor()

    # ── Build the source-of-truth view from qid_art_xref ──────────────────────
    cur.execute("SELECT qid, article_id, exam_year FROM qid_art_xref")
    xref_rows = cur.fetchall()

    # article_id → list of (qid, exam_year)
    article_to_refs: dict[str, list[tuple[str, int | None]]] = defaultdict(list)
    qid_set: set[str] = set()
    article_set_from_xref: set[str] = set()
    for r in xref_rows:
        article_to_refs[r["article_id"]].append((r["qid"], r["exam_year"]))
        qid_set.add(r["qid"])
        article_set_from_xref.add(r["article_id"])

    # ── Load articles table (cache columns) ───────────────────────────────────
    cur.execute(
        "SELECT article_id, qid_list, citation_count, exam_years, unique_years "
        "FROM articles"
    )
    articles_rows = cur.fetchall()
    articles_by_id: dict[str, dict] = {r["article_id"]: dict(r) for r in articles_rows}
    article_set_from_table = set(articles_by_id.keys())

    # ── Load questions table (qid set) ────────────────────────────────────────
    cur.execute("SELECT qid FROM questions")
    questions_qid_set: set[str] = {r["qid"] for r in cur.fetchall()}

    conn.close()

    # ── C5: ORPHAN_XREF — xref rows pointing to non-existent qid or article ──
    for r in xref_rows:
        if r["article_id"] not in article_set_from_table:
            findings.append({
                "check": "ORPHAN_XREF",
                "subtype": "missing_article",
                "severity": "HIGH",
                "qid": r["qid"],
                "article_id": r["article_id"],
                "exam_year": r["exam_year"],
                "detail": f"qid_art_xref row references article_id={r['article_id']} which does not exist in articles table",
            })
        if r["qid"] not in questions_qid_set:
            findings.append({
                "check": "ORPHAN_XREF",
                "subtype": "missing_question",
                "severity": "HIGH",
                "qid": r["qid"],
                "article_id": r["article_id"],
                "exam_year": r["exam_year"],
                "detail": f"qid_art_xref row references qid={r['qid']} which does not exist in questions table",
            })

    # ── C1–C4 + C6/C7 per article ─────────────────────────────────────────────
    for art_id, art in articles_by_id.items():
        refs = article_to_refs.get(art_id, [])
        computed_qids = sorted({q for q, _ in refs})
        computed_count = len(refs)
        computed_years = sorted({y for _, y in refs if y is not None})
        computed_unique_years = len(computed_years)

        cached_qids = sorted(_parse_json_list(art.get("qid_list")))
        cached_count = art.get("citation_count")
        cached_years = sorted(_parse_json_list(art.get("exam_years")))
        cached_unique_years = art.get("unique_years")

        # C1: qid_list cache drift
        if not _set_equal(cached_qids, computed_qids):
            findings.append({
                "check": "QID_LIST_CACHE_DRIFT",
                "severity": "LOW",
                "article_id": art_id,
                "cached_value": cached_qids,
                "computed_value": computed_qids,
                "added_in_bridge": sorted(set(computed_qids) - set(cached_qids)),
                "missing_in_bridge": sorted(set(cached_qids) - set(computed_qids)),
                "detail": "articles.qid_list disagrees with reverse-query of qid_art_xref",
            })

        # C2: citation_count mismatch
        if (cached_count or 0) != computed_count:
            findings.append({
                "check": "CITATION_COUNT_MISMATCH",
                "severity": "LOW",
                "article_id": art_id,
                "cached_value": cached_count,
                "computed_value": computed_count,
                "detail": f"articles.citation_count={cached_count} but xref has {computed_count} rows pointing to this article",
            })

        # C3: exam_years drift
        if not _set_equal(cached_years, computed_years):
            findings.append({
                "check": "EXAM_YEARS_DRIFT",
                "severity": "LOW",
                "article_id": art_id,
                "cached_value": cached_years,
                "computed_value": computed_years,
                "detail": "articles.exam_years disagrees with DISTINCT exam_year from qid_art_xref",
            })

        # C4: unique_years mismatch
        if (cached_unique_years or 0) != computed_unique_years:
            findings.append({
                "check": "UNIQUE_YEARS_MISMATCH",
                "severity": "LOW",
                "article_id": art_id,
                "cached_value": cached_unique_years,
                "computed_value": computed_unique_years,
                "detail": f"articles.unique_years={cached_unique_years} but xref has {computed_unique_years} distinct years",
            })

        # C6: zero_citation but linked
        if (cached_count or 0) == 0 and computed_count > 0:
            findings.append({
                "check": "ZERO_CITATION_LINKED",
                "severity": "LOW",
                "article_id": art_id,
                "cached_value": cached_count,
                "computed_value": computed_count,
                "detail": f"citation_count=0 but {computed_count} xref rows link this article",
            })

        # C7: cited but unlinked
        if (cached_count or 0) > 0 and computed_count == 0:
            findings.append({
                "check": "UNLINKED_CITED_ARTICLE",
                "severity": "MEDIUM",
                "article_id": art_id,
                "cached_value": cached_count,
                "computed_value": 0,
                "detail": f"citation_count={cached_count} but no xref rows link this article",
            })

    return findings


def build_summary(findings: list[dict], total_articles: int, total_xref_rows: int) -> dict:
    by_check: dict[str, int] = defaultdict(int)
    by_severity: dict[str, int] = defaultdict(int)
    for f in findings:
        by_check[f["check"]] += 1
        by_severity[f["severity"]] += 1
    return {
        "total_articles": total_articles,
        "total_xref_rows": total_xref_rows,
        "total_findings": len(findings),
        "by_check": dict(by_check),
        "by_severity": dict(by_severity),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Layer C — structural integrity audit")
    parser.add_argument("--output-dir", required=True, help="Where to write findings_layer_c.json")
    parser.add_argument("--db-path", help="Path to ite_intelligence.db (auto-detected if omitted)")
    parser.add_argument("--project-root", help="Override PROJECT_ROOT (used for DB auto-detect)")
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.db_path:
        db_path = Path(args.db_path).resolve()
    elif args.project_root:
        db_path = resolve_db_path(Path(args.project_root).resolve())
    else:
        # Skill lives at PROJECT_ROOT/.claude/skills/corpus-integrity-qc/scripts/
        # scripts/ -> corpus-integrity-qc/ -> skills/ -> .claude/ -> PROJECT_ROOT/
        project_root = SCRIPT_DIR.parent.parent.parent.parent
        db_path = resolve_db_path(project_root.resolve())

    print(f"DB:         {db_path}")
    print(f"Output dir: {output_dir}")

    if not db_path.exists():
        print(f"ERROR: DB not found at {db_path}", file=sys.stderr)
        return 1

    # Pre-count for summary
    conn = connect_db_readonly(db_path)
    total_articles = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    total_xref_rows = conn.execute("SELECT COUNT(*) FROM qid_art_xref").fetchone()[0]
    conn.close()

    print(f"Articles:   {total_articles}")
    print(f"Xref rows:  {total_xref_rows}")
    print("Running Layer C checks...")
    findings = run_layer_c(db_path)

    summary = build_summary(findings, total_articles, total_xref_rows)

    result = {
        "layer": "C",
        "name": "structural_integrity",
        "summary": summary,
        "findings": findings,
    }

    out_path = output_dir / "findings_layer_c.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print()
    print("=== Layer C Summary ===")
    print(f"Total findings: {summary['total_findings']}")
    for check, cnt in sorted(summary["by_check"].items()):
        print(f"  {check}: {cnt}")
    print()
    print(f"Written to: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
