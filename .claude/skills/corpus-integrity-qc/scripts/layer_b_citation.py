"""
layer_b_citation.py
===================
Layer B — Citation Linkage Audit (multi-reference-aware).

Compares two bags per QID:
  DB bag       — { article_id : SELECT article_id FROM qid_art_xref WHERE qid = ? }
  Critique bag — { _article_id : record in YYYY_critique_refs_staging.json
                                 where qid matches AND match_status in
                                 {matched, fuzzy_matched} AND _article_id IS NOT NULL }

Set-containment semantics: a QID with [A, B, C] in the critique and [A, B] in the DB
flags only C as missing. This is the bug-fix layer — the original article-citation-qc
collapsed multi-ref QIDs to a single article via dict overwrite (BATON 058), which
generated ~900 false-positive missing-citation findings.

Checks implemented:
  B1. CRITIQUE_REF_MISSING_FROM_DB   — per QID×article  (HIGH)
  B2. DB_REF_NOT_IN_CRITIQUE         — per QID×article  (LOW, informational)
  B3. UNMATCHED_CITATION             — per critique row (MEDIUM, acquisition queue)
  B4. TRUNC_TITLE                    — per article      (MEDIUM, Tier 1 fix)
  B5. AUTHOR_ARTIFACT                — per article      (MEDIUM, Tier 1 fix)
  B6. UMBRELLA                       — per article      (HIGH/MEDIUM, Tier 3 manual)
  B7. NULL_CLEAN_REF                 — per article      (LOW, Tier 3 manual)

Usage:
  python layer_b_citation.py --output-dir <OUTPUT_DIR> \\
                             [--staging-dir <STAGING_DIR>] \\
                             [--db-path <DB>] \\
                             [--years 2018 2019 2020 ...]

Output:
  findings_layer_b.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from utils import (  # noqa: E402
    AUTHOR_STOP_WORDS,
    connect_db_readonly,
    extract_title_from_clean_ref,
    is_truncated_title,
    resolve_db_path,
    setup_utf8_stdout,
)

setup_utf8_stdout()


# Skill scaffold lives at PROJECT_ROOT/.claude/skills/corpus-integrity-qc/scripts/
def _default_project_root() -> Path:
    # scripts/ -> corpus-integrity-qc/ -> skills/ -> .claude/ -> PROJECT_ROOT/
    return SCRIPT_DIR.parent.parent.parent.parent.resolve()


def resolve_staging_dir(project_root: Path) -> Path:
    return project_root / "02_module.2_processor" / "outputs"


# ══════════════════════════════════════════════════════════════════════════════
# Staging loaders
# ══════════════════════════════════════════════════════════════════════════════

def load_staging_year(staging_dir: Path, year: int) -> list[dict]:
    """Return the list of critique-ref records for one year, or [] if file missing."""
    path = staging_dir / f"{year}_critique_refs_staging.json"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"{path} did not contain a JSON list")
    return data


def load_all_staging(staging_dir: Path, years: list[int]) -> tuple[list[dict], list[int]]:
    """Load every available year; return (all_records, missing_years)."""
    all_records: list[dict] = []
    missing: list[int] = []
    for year in years:
        path = staging_dir / f"{year}_critique_refs_staging.json"
        if not path.exists():
            missing.append(year)
            continue
        all_records.extend(load_staging_year(staging_dir, year))
    return all_records, missing


# ══════════════════════════════════════════════════════════════════════════════
# B1 / B2 / B3 — bag comparison + unmatched
# ══════════════════════════════════════════════════════════════════════════════

def check_bag_per_qid(
    staging_records: list[dict],
    db_xref: list[dict],
) -> list[dict]:
    """
    For each QID present in either source, compare bags and emit per-pair findings.

    B1 (CRITIQUE_REF_MISSING_FROM_DB):  critique - db
    B2 (DB_REF_NOT_IN_CRITIQUE):        db - critique
    B3 (UNMATCHED_CITATION):            critique record where match_status == unmatched
    """
    # critique_bag[qid] = { article_id : best_match_score_seen }
    critique_bag: dict[str, dict[str, float]] = defaultdict(dict)
    # Track exam_year per (qid, article_id) so B1 inserts have the right year
    critique_year: dict[tuple[str, str], int] = {}
    # Keep the critique ref text alongside for evidence in findings
    critique_evidence: dict[tuple[str, str], dict] = {}

    findings: list[dict] = []

    # ── Pass 1: walk staging ──
    for rec in staging_records:
        qid = rec.get("qid")
        status = rec.get("match_status")
        art_id = rec.get("_article_id")
        score = rec.get("match_score") or 0.0
        year = rec.get("exam_year")
        if not qid:
            continue

        if status == "unmatched":
            # B3: critique cites a paper not in the articles table at all.
            findings.append({
                "check": "UNMATCHED_CITATION",
                "severity": "MEDIUM",
                "qid": qid,
                "exam_year": year,
                "ref_index": rec.get("ref_index"),
                "match_score": score,
                "ref_raw": rec.get("ref_raw"),
                "clean_ref": rec.get("clean_ref"),
                "detail": (
                    "Critique cites a paper with no row in articles table — "
                    "feeds acquisition queue."
                ),
            })
            continue

        if status not in ("matched", "fuzzy_matched") or not art_id:
            continue

        # Keep the best (highest match_score) for B1 tier decisions
        prev = critique_bag[qid].get(art_id)
        if prev is None or score > prev:
            critique_bag[qid][art_id] = score
            critique_year[(qid, art_id)] = year
            critique_evidence[(qid, art_id)] = {
                "match_status": status,
                "match_score": score,
                "ref_raw": rec.get("ref_raw"),
                "clean_ref": rec.get("clean_ref"),
                "ref_index": rec.get("ref_index"),
            }

    # ── Pass 2: build DB bag ──
    db_bag: dict[str, set[str]] = defaultdict(set)
    for r in db_xref:
        db_bag[r["qid"]].add(r["article_id"])

    # ── Pass 3: per-QID set diffs ──
    all_qids = set(critique_bag) | set(db_bag)
    for qid in sorted(all_qids):
        crit_ids = set(critique_bag.get(qid, {}).keys())
        db_ids = db_bag.get(qid, set())

        # B1: in critique but not in DB
        for art_id in sorted(crit_ids - db_ids):
            ev = critique_evidence[(qid, art_id)]
            findings.append({
                "check": "CRITIQUE_REF_MISSING_FROM_DB",
                "severity": "HIGH",
                "qid": qid,
                "article_id": art_id,
                "exam_year": critique_year.get((qid, art_id)),
                "match_status": ev["match_status"],
                "match_score": ev["match_score"],
                "ref_index": ev["ref_index"],
                "ref_raw": ev["ref_raw"],
                "clean_ref": ev["clean_ref"],
                "detail": (
                    f"Critique cites {art_id} for {qid} "
                    f"({ev['match_status']}, score={ev['match_score']}) "
                    "but qid_art_xref has no row linking them."
                ),
            })

        # B2: in DB but not in critique (informational)
        for art_id in sorted(db_ids - crit_ids):
            findings.append({
                "check": "DB_REF_NOT_IN_CRITIQUE",
                "severity": "LOW",
                "qid": qid,
                "article_id": art_id,
                "detail": (
                    f"qid_art_xref links {qid} → {art_id} but the critique "
                    "staging does not list this article for that QID. May be a "
                    "legitimate enrichment-pipeline link (pathway-derived, etc.); "
                    "informational only."
                ),
            })

    return findings


# ══════════════════════════════════════════════════════════════════════════════
# B4 / B5 / B7 — per-article scalar checks
# ══════════════════════════════════════════════════════════════════════════════

def check_truncated_titles(articles: list[dict]) -> list[dict]:
    """B4. TRUNC_TITLE — db title is a fragment of the title parsed from clean_ref."""
    findings: list[dict] = []
    for a in articles:
        db_title = a.get("title")
        clean_ref = a.get("clean_ref")
        if not db_title or not clean_ref:
            continue
        extracted = extract_title_from_clean_ref(clean_ref)
        if not extracted:
            continue
        if is_truncated_title(db_title, extracted):
            findings.append({
                "check": "TRUNC_TITLE",
                "severity": "MEDIUM",
                "article_id": a["article_id"],
                "current_title": db_title,
                "proposed_title": extracted,
                "clean_ref": clean_ref,
                "detail": (
                    "articles.title appears to be a truncated/fragmented version "
                    "of the title parsed from clean_ref."
                ),
            })
    return findings


def check_author_artifacts(articles: list[dict]) -> list[dict]:
    """B5. AUTHOR_ARTIFACT — author1 is a stop-word like 'Final', 'US', 'Updated'."""
    findings: list[dict] = []
    for a in articles:
        author1 = a.get("author1")
        if not author1:
            continue
        token = author1.strip().lower()
        if token in AUTHOR_STOP_WORDS:
            findings.append({
                "check": "AUTHOR_ARTIFACT",
                "severity": "MEDIUM",
                "article_id": a["article_id"],
                "current_author1": author1,
                "clean_ref": a.get("clean_ref"),
                "detail": (
                    f"articles.author1={author1!r} is a parsing stop-word; "
                    "real author/org-byline should be re-derived from clean_ref."
                ),
            })
    return findings


def check_null_clean_ref(articles: list[dict]) -> list[dict]:
    """B7. NULL_CLEAN_REF — citation_count > 0 but clean_ref IS NULL/empty."""
    findings: list[dict] = []
    for a in articles:
        cnt = a.get("citation_count") or 0
        ref = a.get("clean_ref")
        if cnt > 0 and (ref is None or (isinstance(ref, str) and not ref.strip())):
            findings.append({
                "check": "NULL_CLEAN_REF",
                "severity": "LOW",
                "article_id": a["article_id"],
                "citation_count": cnt,
                "current_title": a.get("title"),
                "detail": (
                    f"article cited {cnt} time(s) but clean_ref is NULL/empty — "
                    "populate from critique PDF for the cited years."
                ),
            })
    return findings


# ══════════════════════════════════════════════════════════════════════════════
# B6 — UMBRELLA
# ══════════════════════════════════════════════════════════════════════════════

def check_umbrella(
    articles: list[dict],
    db_xref: list[dict],
    questions: list[dict],
) -> list[dict]:
    """
    B6. UMBRELLA — single article used as catch-all across diverse topics.

    Heuristic (from qc_rules.md B6):
      citation_count >= 5
      AND unique_years >= 3
      AND (distinct blueprint linked >= 4 OR distinct body_system linked >= 3)

    Severity: HIGH if citation_count >= 8 else MEDIUM. Tier 3 (manual) regardless —
    resolution requires splitting the umbrella into topic-specific records.
    """
    # qid → (blueprint, body_system)
    qid_meta: dict[str, tuple[str | None, str | None]] = {
        q["qid"]: (q.get("blueprint"), q.get("body_system")) for q in questions
    }

    # article_id → list of qids linked
    art_to_qids: dict[str, list[str]] = defaultdict(list)
    for r in db_xref:
        art_to_qids[r["article_id"]].append(r["qid"])

    findings: list[dict] = []
    for a in articles:
        cnt = a.get("citation_count") or 0
        uy = a.get("unique_years") or 0
        if cnt < 5 or uy < 3:
            continue

        linked_qids = art_to_qids.get(a["article_id"], [])
        blueprints = {qid_meta.get(q, (None, None))[0] for q in linked_qids}
        body_systems = {qid_meta.get(q, (None, None))[1] for q in linked_qids}
        blueprints.discard(None)
        body_systems.discard(None)

        if len(blueprints) >= 4 or len(body_systems) >= 3:
            sev = "HIGH" if cnt >= 8 else "MEDIUM"
            findings.append({
                "check": "UMBRELLA",
                "severity": sev,
                "article_id": a["article_id"],
                "citation_count": cnt,
                "unique_years": uy,
                "distinct_blueprints": sorted(blueprints),
                "distinct_body_systems": sorted(body_systems),
                "current_title": a.get("title"),
                "current_author1": a.get("author1"),
                "linked_qids": sorted(linked_qids),
                "detail": (
                    f"Article cited {cnt}x across {uy} years; spans "
                    f"{len(blueprints)} blueprint categor(ies) and "
                    f"{len(body_systems)} body system(s) — likely catch-all "
                    "umbrella. Resolution requires splitting into topic-specific "
                    "records."
                ),
            })
    return findings


# ══════════════════════════════════════════════════════════════════════════════
# Orchestration
# ══════════════════════════════════════════════════════════════════════════════

def run_layer_b(
    db_path: Path,
    staging_dir: Path,
    years: list[int],
) -> tuple[list[dict], dict]:
    conn = connect_db_readonly(db_path)
    cur = conn.cursor()

    cur.execute("SELECT qid, article_id, exam_year FROM qid_art_xref")
    db_xref = [dict(r) for r in cur.fetchall()]

    cur.execute(
        "SELECT article_id, title, author1, clean_ref, citation_count, unique_years "
        "FROM articles"
    )
    articles = [dict(r) for r in cur.fetchall()]

    cur.execute("SELECT qid, blueprint, body_system FROM questions")
    questions = [dict(r) for r in cur.fetchall()]

    conn.close()

    staging_records, missing_years = load_all_staging(staging_dir, years)

    findings: list[dict] = []
    findings.extend(check_bag_per_qid(staging_records, db_xref))
    findings.extend(check_truncated_titles(articles))
    findings.extend(check_author_artifacts(articles))
    findings.extend(check_null_clean_ref(articles))
    findings.extend(check_umbrella(articles, db_xref, questions))

    meta = {
        "years_requested": years,
        "years_missing_staging": missing_years,
        "staging_records_loaded": len(staging_records),
        "db_xref_rows": len(db_xref),
        "articles_scanned": len(articles),
        "questions_scanned": len(questions),
    }
    return findings, meta


def build_summary(findings: list[dict], meta: dict) -> dict:
    by_check: Counter = Counter(f["check"] for f in findings)
    by_severity: Counter = Counter(f["severity"] for f in findings)
    return {
        **meta,
        "total_findings": len(findings),
        "by_check": dict(by_check),
        "by_severity": dict(by_severity),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Layer B — citation linkage audit")
    parser.add_argument("--output-dir", required=True,
                        help="Where to write findings_layer_b.json")
    parser.add_argument("--db-path", help="Path to ite_intelligence.db (auto-detected if omitted)")
    parser.add_argument("--staging-dir",
                        help="M2 outputs/ dir containing YYYY_critique_refs_staging.json")
    parser.add_argument("--project-root",
                        help="Override PROJECT_ROOT (used for DB + staging auto-detect)")
    parser.add_argument("--years", nargs="+", type=int,
                        default=list(range(2018, 2026)),
                        help="Years to audit (default 2018–2025)")
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    project_root = (
        Path(args.project_root).resolve() if args.project_root
        else _default_project_root()
    )
    db_path = (
        Path(args.db_path).resolve() if args.db_path
        else resolve_db_path(project_root)
    )
    staging_dir = (
        Path(args.staging_dir).resolve() if args.staging_dir
        else resolve_staging_dir(project_root)
    )

    print(f"Project root: {project_root}")
    print(f"DB:           {db_path}")
    print(f"Staging dir:  {staging_dir}")
    print(f"Output dir:   {output_dir}")
    print(f"Years:        {args.years}")

    if not db_path.exists():
        print(f"ERROR: DB not found at {db_path}", file=sys.stderr)
        return 1
    if not staging_dir.exists():
        print(f"ERROR: staging dir not found at {staging_dir}", file=sys.stderr)
        return 1

    print("Running Layer B checks...")
    findings, meta = run_layer_b(db_path, staging_dir, args.years)
    summary = build_summary(findings, meta)

    result = {
        "layer": "B",
        "name": "citation_linkage",
        "summary": summary,
        "findings": findings,
    }

    out_path = output_dir / "findings_layer_b.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print()
    print("=== Layer B Summary ===")
    print(f"Years scanned:           {meta['years_requested']}")
    if meta["years_missing_staging"]:
        print(f"  ⚠  Missing staging:    {meta['years_missing_staging']}")
    print(f"Staging records loaded:  {meta['staging_records_loaded']}")
    print(f"DB xref rows:            {meta['db_xref_rows']}")
    print(f"Articles scanned:        {meta['articles_scanned']}")
    print(f"Total findings:          {summary['total_findings']}")
    for check, cnt in sorted(summary["by_check"].items()):
        print(f"  {check}: {cnt}")
    print()
    print(f"Written to: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
