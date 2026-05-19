"""
generate_fixes.py
=================
Layer D — Tiered SQL Fix Generator.

Reads `findings_layer_{a,b,c}.json` and partitions findings into three tiers:

  Tier 1 — Auto-safe       (mechanical, reversible, no judgment)
  Tier 2 — Review required (correct value derivable but needs eyeballing;
                            statements emitted COMMENTED OUT by default)
  Tier 3 — Manual          (no SQL — see qc_report.md for evidence)

Tier assignment table:

  ┌──────────────────────────────────────┬──────────┬────────────────────────────┐
  │ check / subtype                      │ tier     │ sql verb                   │
  ├──────────────────────────────────────┼──────────┼────────────────────────────┤
  │ A1  ENCODING_ARTIFACT                │ 1        │ UPDATE questions REPLACE() │
  │ A2  TRUNCATION_CANDIDATE             │ 2        │ -- review                  │
  │ A3  FORMAT_DRIFT/*                   │ 2        │ -- review                  │
  │ B1  CRITIQUE_REF_MISSING_FROM_DB     │ 1 if    │ INSERT OR IGNORE xref      │
  │                                      │   score  │                            │
  │                                      │   ==1.0  │                            │
  │                                      │ else 2   │                            │
  │ B2  DB_REF_NOT_IN_CRITIQUE           │ 3        │ — (informational)          │
  │ B3  UNMATCHED_CITATION               │ 3        │ — (acquisition queue)      │
  │ B4  TRUNC_TITLE                      │ 1        │ UPDATE articles SET title  │
  │ B5  AUTHOR_ARTIFACT                  │ 1        │ UPDATE articles SET author1│
  │ B6  UMBRELLA                         │ 3        │ — (manual split)           │
  │ B7  NULL_CLEAN_REF                   │ 3        │ — (manual populate)        │
  │ C1  QID_LIST_CACHE_DRIFT             │ 1        │ UPDATE articles SET qid_list│
  │ C2  CITATION_COUNT_MISMATCH          │ 1        │ UPDATE articles SET cnt    │
  │ C3  EXAM_YEARS_DRIFT                 │ 1        │ UPDATE articles SET years  │
  │ C4  UNIQUE_YEARS_MISMATCH            │ 1        │ UPDATE articles SET uniq_yr│
  │ C5  ORPHAN_XREF                      │ 2        │ -- DELETE FROM xref        │
  │ C6  ZERO_CITATION_LINKED             │ 1        │ UPDATE articles SET cnt    │
  │ C7  UNLINKED_CITED_ARTICLE           │ 1        │ UPDATE articles SET cnt=0  │
  └──────────────────────────────────────┴──────────┴────────────────────────────┘

Usage:
  python generate_fixes.py --findings-dir <DIR_WITH_findings_layer_*.json> \\
                           [--db-path <DB>]   # used to look up clean_ref for B5

Output:
  fixes.sql in --findings-dir
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from utils import (  # noqa: E402
    connect_db_readonly,
    correct_author_from_clean_ref,
    resolve_db_path,
    setup_utf8_stdout,
)

setup_utf8_stdout()


def _default_project_root() -> Path:
    # scripts/ -> corpus-integrity-qc/ -> skills/ -> .claude/ -> PROJECT_ROOT/
    return SCRIPT_DIR.parent.parent.parent.parent.resolve()


# ══════════════════════════════════════════════════════════════════════════════
# SQL escaping
# ══════════════════════════════════════════════════════════════════════════════

def _sql_str(value: str | None) -> str:
    """Return a SQL-quoted single-quoted string literal, or 'NULL' for None."""
    if value is None:
        return "NULL"
    return "'" + str(value).replace("'", "''") + "'"


def _sql_int(value: int | None) -> str:
    if value is None:
        return "NULL"
    return str(int(value))


def _sql_json(value) -> str:
    """JSON-serialize a Python value, then SQL-quote the resulting string."""
    return _sql_str(json.dumps(value))


# ══════════════════════════════════════════════════════════════════════════════
# Tier 1 — Auto-safe generators (per check)
# ══════════════════════════════════════════════════════════════════════════════

# Map Layer A field names back to actual column names.
# (Layer A reports field="choices[0]" etc.; the underlying column is choices.)
def _field_to_column(field: str) -> str:
    if field.startswith("choices["):
        return "choices"
    return field


def _sql_json_escape_expr(s: str) -> str:
    """Build a SQL expression that produces the JSON-ensure_ascii=True escape
    form of `s` — i.e. ASCII chars verbatim, non-ASCII chars as the literal
    6-char ASCII escape `\\uXXXX`. SQLite interprets `\\u` in single-quoted
    string literals as the unicode codepoint (empirically tested — its own
    docs say string literals are literal, but they're not), so we must build
    the literal backslash with `char(92)` and concatenate.

    Examples:
      'Ã¶' (U+00C3 U+00B6) → "char(92) || 'u00c3' || char(92) || 'u00b6'"
      'ö'  (U+00F6)        → "char(92) || 'u00f6'"
      'abc'                → "'abc'"
    """
    parts: list[str] = []
    ascii_buf: list[str] = []
    for c in s:
        if ord(c) < 128:
            ascii_buf.append(c)
        else:
            if ascii_buf:
                parts.append("'" + "".join(ascii_buf).replace("'", "''") + "'")
                ascii_buf = []
            parts.append(f"char(92) || 'u{ord(c):04x}'")
    if ascii_buf:
        parts.append("'" + "".join(ascii_buf).replace("'", "''") + "'")
    if not parts:
        return "''"
    return " || ".join(parts)


def gen_encoding_fix(f: dict) -> str:
    """A1 — UPDATE questions SET <field> = REPLACE(<field>, bad, good) WHERE qid=?

    For text columns (question_text, explanation, correct_text, reference) the
    column stores the mojibake chars directly, so the literal bad/good chars
    in a SQL string literal work. (SQLite interprets `\\u` escapes, but those
    only collide with already-escaped JSON storage, not with raw text.)

    For the `choices` JSON column, the stored text is JSON-encoded with
    `ensure_ascii=True`, so non-ASCII chars live on disk as the literal 6-char
    ASCII escape `\\uXXXX`. We must REPLACE against that escape form, which
    requires building the literal backslash via `char(92)` so SQLite's own
    `\\u` interpretation doesn't undo us."""
    field = f["field"]
    col = _field_to_column(field)
    is_json_column = field.startswith("choices[")
    if is_json_column:
        bad = _sql_json_escape_expr(f["bad_sequence"])
        good = _sql_json_escape_expr(f["corrected"])
    else:
        bad = _sql_str(f["bad_sequence"])
        good = _sql_str(f["corrected"])
    qid = _sql_str(f["qid"])
    return (
        f"-- [A1] {f['qid']}: {f['field']} — replace {f['bad_sequence']!r} "
        f"with {f['corrected']!r} ({f['count']}×)\n"
        f"UPDATE questions SET {col} = REPLACE({col}, {bad}, {good}) "
        f"WHERE qid = {qid};"
    )


def gen_b1_exact_insert(f: dict) -> str:
    """B1 — exact-match (score==1.0): INSERT OR IGNORE INTO qid_art_xref."""
    qid = _sql_str(f["qid"])
    aid = _sql_str(f["article_id"])
    yr = _sql_int(f.get("exam_year"))
    return (
        f"-- [B1] {f['qid']} → {f['article_id']} (exact match, "
        f"score={f['match_score']})\n"
        f"INSERT OR IGNORE INTO qid_art_xref (qid, article_id, exam_year) "
        f"VALUES ({qid}, {aid}, {yr});"
    )


def gen_b4_title_fix(f: dict) -> str:
    """B4 — UPDATE articles SET title = proposed_title."""
    aid = _sql_str(f["article_id"])
    new_title = _sql_str(f["proposed_title"])
    return (
        f"-- [B4] {f['article_id']}: replace truncated title with full title "
        f"from clean_ref\n"
        f"--      old: {f['current_title']!r}\n"
        f"--      new: {f['proposed_title']!r}\n"
        f"UPDATE articles SET title = {new_title} WHERE article_id = {aid};"
    )


def gen_b5_author_fix(f: dict, derived_author: str | None) -> str | None:
    """B5 — UPDATE articles SET author1 = <derived from clean_ref>.
    Returns None if no valid author can be derived (skipped from Tier 1)."""
    if not derived_author:
        return None
    aid = _sql_str(f["article_id"])
    new_author = _sql_str(derived_author)
    return (
        f"-- [B5] {f['article_id']}: replace author1 stop-word "
        f"{f['current_author1']!r} with derived {derived_author!r}\n"
        f"UPDATE articles SET author1 = {new_author} WHERE article_id = {aid};"
    )


def gen_c_cache_rebuild(f: dict) -> str:
    """C1/C2/C3/C4/C6/C7 — rebuild the relevant articles.* cache column."""
    check = f["check"]
    aid = _sql_str(f["article_id"])
    if check == "QID_LIST_CACHE_DRIFT":
        new = _sql_json(sorted(f["computed_value"]))
        return (
            f"-- [C1] {f['article_id']}: qid_list cache rebuild "
            f"({len(f['computed_value'])} qids)\n"
            f"UPDATE articles SET qid_list = {new} WHERE article_id = {aid};"
        )
    if check in ("CITATION_COUNT_MISMATCH", "ZERO_CITATION_LINKED"):
        new = _sql_int(f["computed_value"])
        cached = f.get("cached_value")
        return (
            f"-- [C2/C6] {f['article_id']}: citation_count {cached} → "
            f"{f['computed_value']}\n"
            f"UPDATE articles SET citation_count = {new} WHERE article_id = {aid};"
        )
    if check == "EXAM_YEARS_DRIFT":
        new = _sql_json(sorted(f["computed_value"]))
        return (
            f"-- [C3] {f['article_id']}: exam_years cache rebuild\n"
            f"UPDATE articles SET exam_years = {new} WHERE article_id = {aid};"
        )
    if check == "UNIQUE_YEARS_MISMATCH":
        new = _sql_int(f["computed_value"])
        return (
            f"-- [C4] {f['article_id']}: unique_years "
            f"{f.get('cached_value')} → {f['computed_value']}\n"
            f"UPDATE articles SET unique_years = {new} WHERE article_id = {aid};"
        )
    if check == "UNLINKED_CITED_ARTICLE":
        return (
            f"-- [C7] {f['article_id']}: citation_count > 0 but no xref rows — "
            f"reset to 0\n"
            f"UPDATE articles SET citation_count = 0 WHERE article_id = {aid};"
        )
    return f"-- [C?] {f['article_id']}: unhandled C-check {check}"


# ══════════════════════════════════════════════════════════════════════════════
# Tier 2 — Review-required generators (commented out by default)
# ══════════════════════════════════════════════════════════════════════════════

def gen_b1_fuzzy_insert(f: dict) -> str:
    """B1 fuzzy — INSERT commented; user uncomments after eyeballing."""
    qid = _sql_str(f["qid"])
    aid = _sql_str(f["article_id"])
    yr = _sql_int(f.get("exam_year"))
    ref = (f.get("ref_raw") or "")[:140].replace("\n", " ")
    return (
        f"-- [B1-FUZZY] {f['qid']} → {f['article_id']} "
        f"(score={f['match_score']}) — REVIEW BEFORE UNCOMMENTING\n"
        f"--   critique ref: {ref}\n"
        f"-- INSERT OR IGNORE INTO qid_art_xref (qid, article_id, exam_year) "
        f"VALUES ({qid}, {aid}, {yr});"
    )


def gen_a2_review(f: dict) -> str:
    """A2 truncation — no auto-fix; show evidence inline."""
    tail = (f.get("tail") or "").replace("\n", " ")
    return (
        f"-- [A2-{f.get('subtype', '-')}] {f['qid']} ({f.get('exam_year')}): "
        f"len={f.get('length')} (year floor={f.get('year_floor_chars', 'n/a')})\n"
        f"--   tail: {tail!r}\n"
        f"--   REVIEW: re-extract from {f.get('exam_year')}_critique.pdf, "
        f"compose UPDATE manually."
    )


def gen_a3_review(f: dict) -> str:
    """A3 format drift — no auto-fix; describe the anomaly."""
    return (
        f"-- [A3-{f.get('subtype', '-')}] {f['qid']} ({f.get('exam_year')}): "
        f"{f.get('detail', 'format drift')}\n"
        f"--   REVIEW: re-extract from source PDF or correct by hand."
    )


def gen_c5_orphan(f: dict) -> str:
    qid = _sql_str(f["qid"])
    aid = _sql_str(f["article_id"])
    yr = _sql_int(f.get("exam_year"))
    return (
        f"-- [C5-{f.get('subtype', '-')}] orphan xref: "
        f"({f['qid']}, {f['article_id']}, year={f.get('exam_year')})\n"
        f"--   {f.get('detail', '')}\n"
        f"-- DELETE FROM qid_art_xref WHERE qid = {qid} AND article_id = {aid} "
        f"AND exam_year = {yr};"
    )


# ══════════════════════════════════════════════════════════════════════════════
# Main orchestration
# ══════════════════════════════════════════════════════════════════════════════

def load_findings(findings_dir: Path) -> dict[str, list[dict]]:
    """Load findings_layer_{a,b,c}.json from findings_dir, returning dict-by-layer."""
    out: dict[str, list[dict]] = {"A": [], "B": [], "C": []}
    for layer in ("a", "b", "c"):
        p = findings_dir / f"findings_layer_{layer}.json"
        if not p.exists():
            print(f"  ⚠  {p.name} not found — skipping layer {layer.upper()}",
                  file=sys.stderr)
            continue
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        out[layer.upper()] = data.get("findings", [])
    return out


def _load_article_clean_refs(
    db_path: Path,
    article_ids: list[str],
) -> dict[str, str | None]:
    """Bulk-fetch clean_ref for a set of article_ids (used by B5 author fix)."""
    if not article_ids:
        return {}
    conn = connect_db_readonly(db_path)
    placeholders = ",".join("?" * len(article_ids))
    rows = conn.execute(
        f"SELECT article_id, clean_ref FROM articles WHERE article_id IN ({placeholders})",
        article_ids,
    ).fetchall()
    conn.close()
    return {r["article_id"]: r["clean_ref"] for r in rows}


def partition_and_render(
    findings_by_layer: dict[str, list[dict]],
    db_path: Path | None,
) -> tuple[list[str], list[str], int, dict]:
    """Produce (tier1_lines, tier2_lines, tier3_count, per_tier_stats)."""
    tier1: list[str] = []
    tier2: list[str] = []
    tier3_count = 0
    stats = Counter()

    a_findings = findings_by_layer["A"]
    b_findings = findings_by_layer["B"]
    c_findings = findings_by_layer["C"]

    # ── Layer A ───
    for f in a_findings:
        chk = f["check"]
        if chk == "ENCODING_ARTIFACT":
            tier1.append(gen_encoding_fix(f))
            stats["T1/ENCODING_ARTIFACT"] += 1
        elif chk == "TRUNCATION_CANDIDATE":
            tier2.append(gen_a2_review(f))
            stats["T2/TRUNCATION_CANDIDATE"] += 1
        elif chk == "FORMAT_DRIFT":
            tier2.append(gen_a3_review(f))
            stats["T2/FORMAT_DRIFT"] += 1
        else:
            stats[f"T?/A:{chk}"] += 1

    # ── Layer B ───
    # Bulk-load clean_refs for AUTHOR_ARTIFACT fixes
    b5_article_ids = [
        f["article_id"] for f in b_findings if f["check"] == "AUTHOR_ARTIFACT"
    ]
    clean_refs = _load_article_clean_refs(db_path, b5_article_ids) if db_path else {}

    for f in b_findings:
        chk = f["check"]
        if chk == "CRITIQUE_REF_MISSING_FROM_DB":
            score = f.get("match_score") or 0.0
            if score >= 1.0:
                tier1.append(gen_b1_exact_insert(f))
                stats["T1/B1_exact"] += 1
            else:
                tier2.append(gen_b1_fuzzy_insert(f))
                stats["T2/B1_fuzzy"] += 1
        elif chk == "TRUNC_TITLE":
            tier1.append(gen_b4_title_fix(f))
            stats["T1/TRUNC_TITLE"] += 1
        elif chk == "AUTHOR_ARTIFACT":
            derived = correct_author_from_clean_ref(clean_refs.get(f["article_id"]))
            line = gen_b5_author_fix(f, derived)
            if line:
                tier1.append(line)
                stats["T1/AUTHOR_ARTIFACT"] += 1
            else:
                tier3_count += 1
                stats["T3/AUTHOR_ARTIFACT_unparseable"] += 1
        elif chk in ("DB_REF_NOT_IN_CRITIQUE", "UNMATCHED_CITATION", "UMBRELLA",
                     "NULL_CLEAN_REF"):
            tier3_count += 1
            stats[f"T3/{chk}"] += 1
        else:
            stats[f"T?/B:{chk}"] += 1

    # ── Layer C ───
    cache_checks = {
        "QID_LIST_CACHE_DRIFT": "T1/C1",
        "CITATION_COUNT_MISMATCH": "T1/C2",
        "EXAM_YEARS_DRIFT": "T1/C3",
        "UNIQUE_YEARS_MISMATCH": "T1/C4",
        "ZERO_CITATION_LINKED": "T1/C6",
        "UNLINKED_CITED_ARTICLE": "T1/C7",
    }
    for f in c_findings:
        chk = f["check"]
        if chk in cache_checks:
            tier1.append(gen_c_cache_rebuild(f))
            stats[cache_checks[chk]] += 1
        elif chk == "ORPHAN_XREF":
            tier2.append(gen_c5_orphan(f))
            stats["T2/ORPHAN_XREF"] += 1
        else:
            stats[f"T?/C:{chk}"] += 1

    return tier1, tier2, tier3_count, dict(stats)


def render_fixes_sql(
    tier1: list[str],
    tier2: list[str],
    tier3_count: int,
    stats: dict,
) -> str:
    """Render the full fixes.sql text."""
    lines: list[str] = []
    lines.append("-- ============================================================")
    lines.append("-- corpus-integrity-qc — fixes.sql")
    lines.append("-- Generated by generate_fixes.py")
    lines.append("-- ============================================================")
    lines.append("--")
    lines.append("-- Per-tier statement counts:")
    for k, v in sorted(stats.items()):
        lines.append(f"--   {k:40s} {v}")
    lines.append("--")
    lines.append("")
    lines.append("-- ============================================================")
    lines.append(f"-- TIER 1: AUTO-SAFE — review summary, apply whole block")
    lines.append(f"-- Total: {len(tier1)} statements")
    lines.append("-- ============================================================")
    if tier1:
        lines.append("BEGIN;")
        for stmt in tier1:
            lines.append(stmt)
        lines.append("COMMIT;")
    else:
        lines.append("-- (no Tier 1 findings)")
    lines.append("")
    lines.append("-- ============================================================")
    lines.append(f"-- TIER 2: REVIEW REQUIRED — uncomment after eyeballing each")
    lines.append(f"-- Total: {len(tier2)} statements (all commented by default)")
    lines.append("-- ============================================================")
    if tier2:
        for stmt in tier2:
            lines.append(stmt)
    else:
        lines.append("-- (no Tier 2 findings)")
    lines.append("")
    lines.append("-- ============================================================")
    lines.append(f"-- TIER 3: MANUAL — see qc_report.md for details, no SQL")
    lines.append(f"-- Total: {tier3_count} findings")
    lines.append("-- ============================================================")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Layer D — tiered SQL fix generator")
    parser.add_argument("--findings-dir", required=True,
                        help="Directory containing findings_layer_{a,b,c}.json")
    parser.add_argument("--db-path",
                        help="ite_intelligence.db (for B5 author derivation; auto-detected)")
    parser.add_argument("--project-root", help="Override PROJECT_ROOT")
    args = parser.parse_args()

    findings_dir = Path(args.findings_dir).resolve()
    if not findings_dir.exists():
        print(f"ERROR: findings dir not found at {findings_dir}", file=sys.stderr)
        return 1

    if args.db_path:
        db_path = Path(args.db_path).resolve()
    elif args.project_root:
        db_path = resolve_db_path(Path(args.project_root).resolve())
    else:
        db_path = resolve_db_path(_default_project_root())

    if not db_path.exists():
        print(f"WARN: DB not found at {db_path} — B5 author-derivation skipped",
              file=sys.stderr)
        db_path = None  # type: ignore

    print(f"Findings dir: {findings_dir}")
    print(f"DB:           {db_path}")

    findings_by_layer = load_findings(findings_dir)
    counts = {k: len(v) for k, v in findings_by_layer.items()}
    print(f"Loaded findings: {counts}")

    tier1, tier2, tier3_count, stats = partition_and_render(
        findings_by_layer, db_path
    )

    sql_text = render_fixes_sql(tier1, tier2, tier3_count, stats)
    out_path = findings_dir / "fixes.sql"
    out_path.write_text(sql_text, encoding="utf-8")

    print()
    print("=== Layer D Summary ===")
    print(f"Tier 1 statements: {len(tier1)}")
    print(f"Tier 2 statements: {len(tier2)} (commented out)")
    print(f"Tier 3 findings:   {tier3_count} (no SQL)")
    print()
    print("Per-bucket breakdown:")
    for k, v in sorted(stats.items()):
        print(f"  {k:40s} {v}")
    print()
    print(f"Written to: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
