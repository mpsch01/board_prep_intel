"""
build_report.py
===============
Merge findings_layer_{a,b,c}.json into a single Markdown QC report (qc_report.md).

Report structure (matches SKILL.md Phase 3 spec):

  # Corpus Integrity QC Report
  ## Executive Summary           — by layer × check × severity
  ## Layer A — Text Fidelity     — encoding / truncation / format drift
  ## Layer B — Citation Linkage  — B1-B7 grouped
  ## Layer C — Structural        — qid_list / count / years / orphan
  ## Recommended Next Steps      — derived from per-tier counts

Per-finding excerpts are capped to keep the report readable; the full evidence
is preserved in the source findings JSONs.

Usage:
  python build_report.py --findings-dir <DIR_WITH_findings_layer_*.json>

Output:
  qc_report.md in --findings-dir
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from utils import setup_utf8_stdout  # noqa: E402

setup_utf8_stdout()


# Hard cap on listed examples per check to keep the report readable.
MAX_EXAMPLES_PER_CHECK = 10


# ══════════════════════════════════════════════════════════════════════════════
# Loaders
# ══════════════════════════════════════════════════════════════════════════════

def load_layer(findings_dir: Path, layer: str) -> dict:
    p = findings_dir / f"findings_layer_{layer}.json"
    if not p.exists():
        return {"layer": layer.upper(), "name": f"layer_{layer}_missing",
                "summary": {}, "findings": []}
    with open(p, encoding="utf-8") as f:
        return json.load(f)


# ══════════════════════════════════════════════════════════════════════════════
# Markdown rendering helpers
# ══════════════════════════════════════════════════════════════════════════════

def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return "_(no rows)_\n"
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join("---" for _ in headers) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out) + "\n"


def _short(text: str | None, n: int = 100) -> str:
    if not text:
        return "—"
    s = str(text).replace("\n", " ").replace("|", "\\|").strip()
    if len(s) <= n:
        return s
    return s[: n - 1] + "…"


def _example_block(findings: list[dict], fmt) -> str:
    if not findings:
        return ""
    out: list[str] = []
    for f in findings[:MAX_EXAMPLES_PER_CHECK]:
        out.append("- " + fmt(f))
    if len(findings) > MAX_EXAMPLES_PER_CHECK:
        out.append(f"- _… and {len(findings) - MAX_EXAMPLES_PER_CHECK} more._")
    return "\n".join(out) + "\n"


# ══════════════════════════════════════════════════════════════════════════════
# Layer A renderer
# ══════════════════════════════════════════════════════════════════════════════

def render_layer_a(layer: dict) -> str:
    findings = layer.get("findings", [])
    summary = layer.get("summary", {})
    by_subtype: dict[str, list[dict]] = defaultdict(list)
    for f in findings:
        key = f"{f['check']}/{f.get('subtype', '-')}"
        by_subtype[key].append(f)

    out: list[str] = ["## Layer A — Text Fidelity\n"]
    out.append(
        f"**Questions scanned:** {summary.get('questions_scanned', '?')}  \n"
        f"**Findings:** {summary.get('total_findings', 0)}  \n"
        f"**Truncation floor:** p{int(summary.get('truncation_floor_percentile', 0.10)*100)}  \n"
        f"**A4 PDF diff:** {summary.get('a4_pdf_diff_status', 'deferred')}\n"
    )

    if not findings:
        out.append("_No text-fidelity findings._\n")
        return "\n".join(out)

    # A1 — encoding artifacts (group by bad_sequence)
    enc = [f for f in findings if f["check"] == "ENCODING_ARTIFACT"]
    if enc:
        out.append(f"### A1. ENCODING_ARTIFACT ({len(enc)})\n")
        by_seq: Counter = Counter(f["bad_sequence"] for f in enc)
        rows = [[repr(seq),
                 next(f["corrected"] for f in enc if f["bad_sequence"] == seq),
                 cnt]
                for seq, cnt in by_seq.most_common()]
        out.append(_md_table(["Bad sequence", "Corrected", "Count"], rows))
        out.append(_example_block(
            enc,
            lambda f: f"`{f['qid']}` ({f.get('field')}): `{f['bad_sequence']}` → "
                      f"`{f['corrected']}` ({f.get('count', '?')}×)",
        ))

    # A2 — truncation
    trunc = [f for f in findings if f["check"] == "TRUNCATION_CANDIDATE"]
    if trunc:
        out.append(f"### A2. TRUNCATION_CANDIDATE ({len(trunc)})\n")
        by_st: Counter = Counter(f.get("subtype", "-") for f in trunc)
        out.append(_md_table(
            ["Subtype", "Count"],
            [[k, v] for k, v in by_st.most_common()],
        ))
        out.append(_example_block(
            trunc,
            lambda f: f"`{f['qid']}` ({f.get('exam_year')}): "
                      f"`{f.get('subtype')}` — len={f.get('length')} "
                      f"(floor={f.get('year_floor_chars', '-')}); tail: "
                      f"`{_short(f.get('tail'), 80)}`",
        ))

    # A3 — format drift
    fmt = [f for f in findings if f["check"] == "FORMAT_DRIFT"]
    if fmt:
        out.append(f"### A3. FORMAT_DRIFT ({len(fmt)})\n")
        by_st = Counter(f.get("subtype", "-") for f in fmt)
        out.append(_md_table(
            ["Subtype", "Count"],
            [[k, v] for k, v in by_st.most_common()],
        ))
        out.append(_example_block(
            fmt,
            lambda f: f"`{f['qid']}` ({f.get('exam_year')}): "
                      f"`{f.get('subtype')}` — {_short(f.get('detail'), 120)}",
        ))

    return "\n".join(out)


# ══════════════════════════════════════════════════════════════════════════════
# Layer B renderer
# ══════════════════════════════════════════════════════════════════════════════

def render_layer_b(layer: dict) -> str:
    findings = layer.get("findings", [])
    summary = layer.get("summary", {})
    out: list[str] = ["## Layer B — Citation Linkage\n"]
    out.append(
        f"**Articles scanned:** {summary.get('articles_scanned', '?')}  \n"
        f"**Staging records loaded:** {summary.get('staging_records_loaded', '?')}  \n"
        f"**DB xref rows:** {summary.get('db_xref_rows', '?')}  \n"
        f"**Years missing staging:** "
        f"{summary.get('years_missing_staging') or 'none'}  \n"
        f"**Findings:** {summary.get('total_findings', 0)}\n"
    )

    if not findings:
        out.append("_No citation-linkage findings._\n")
        return "\n".join(out)

    groups = [
        ("CRITIQUE_REF_MISSING_FROM_DB", "B1"),
        ("DB_REF_NOT_IN_CRITIQUE",        "B2"),
        ("UNMATCHED_CITATION",            "B3"),
        ("TRUNC_TITLE",                   "B4"),
        ("AUTHOR_ARTIFACT",               "B5"),
        ("UMBRELLA",                      "B6"),
        ("NULL_CLEAN_REF",                "B7"),
    ]
    for chk, code in groups:
        sub = [f for f in findings if f["check"] == chk]
        if not sub:
            continue
        out.append(f"### {code}. {chk} ({len(sub)})\n")
        if chk == "CRITIQUE_REF_MISSING_FROM_DB":
            exact = sum(1 for f in sub if (f.get("match_score") or 0) >= 1.0)
            fuzzy = len(sub) - exact
            out.append(f"- exact-match (score ≥ 1.0): {exact} → Tier 1\n"
                       f"- fuzzy (score < 1.0): {fuzzy} → Tier 2 (review)\n")
            out.append(_example_block(
                sub,
                lambda f: f"`{f['qid']}` → `{f['article_id']}` "
                          f"(score={f.get('match_score')}, "
                          f"year={f.get('exam_year')}): "
                          f"{_short(f.get('ref_raw'), 120)}",
            ))
        elif chk == "DB_REF_NOT_IN_CRITIQUE":
            out.append(_example_block(
                sub,
                lambda f: f"`{f['qid']}` → `{f['article_id']}` (informational)",
            ))
        elif chk == "UNMATCHED_CITATION":
            by_yr: Counter = Counter(f.get("exam_year") for f in sub)
            out.append(_md_table(
                ["Year", "Count"],
                [[y, c] for y, c in sorted(by_yr.items())],
            ))
            out.append(_example_block(
                sub,
                lambda f: f"`{f['qid']}` ({f.get('exam_year')}): "
                          f"{_short(f.get('ref_raw'), 120)}",
            ))
        elif chk == "TRUNC_TITLE":
            out.append(_example_block(
                sub,
                lambda f: f"`{f['article_id']}`: "
                          f"current `{_short(f.get('current_title'), 60)}` "
                          f"→ proposed `{_short(f.get('proposed_title'), 90)}`",
            ))
        elif chk == "AUTHOR_ARTIFACT":
            out.append(_example_block(
                sub,
                lambda f: f"`{f['article_id']}`: author1="
                          f"`{f.get('current_author1')}` (clean_ref: "
                          f"{_short(f.get('clean_ref'), 100)})",
            ))
        elif chk == "UMBRELLA":
            out.append(_example_block(
                sub,
                lambda f: f"`{f['article_id']}` (cited {f.get('citation_count')}× "
                          f"across {f.get('unique_years')} years, "
                          f"{len(f.get('distinct_blueprints', []))} BP × "
                          f"{len(f.get('distinct_body_systems', []))} BS): "
                          f"`{_short(f.get('current_title'), 80)}`",
            ))
        elif chk == "NULL_CLEAN_REF":
            out.append(_example_block(
                sub,
                lambda f: f"`{f['article_id']}` "
                          f"(citation_count={f.get('citation_count')}): "
                          f"title=`{_short(f.get('current_title'), 80)}`",
            ))
    return "\n".join(out)


# ══════════════════════════════════════════════════════════════════════════════
# Layer C renderer
# ══════════════════════════════════════════════════════════════════════════════

def render_layer_c(layer: dict) -> str:
    findings = layer.get("findings", [])
    summary = layer.get("summary", {})
    out: list[str] = ["## Layer C — Structural Integrity\n"]
    out.append(
        f"**Articles scanned:** {summary.get('total_articles', '?')}  \n"
        f"**Xref rows:** {summary.get('total_xref_rows', '?')}  \n"
        f"**Findings:** {summary.get('total_findings', 0)}\n"
    )

    if not findings:
        out.append("_No structural findings._\n")
        return "\n".join(out)

    by_check: Counter = Counter(f["check"] for f in findings)
    out.append(_md_table(
        ["Check", "Count"],
        [[c, v] for c, v in by_check.most_common()],
    ))

    # Show first ORPHAN_XREF rows inline (rare and important)
    orphans = [f for f in findings if f["check"] == "ORPHAN_XREF"]
    if orphans:
        out.append(f"\n### ORPHAN_XREF ({len(orphans)})\n")
        out.append(_example_block(
            orphans,
            lambda f: f"`{f.get('qid')}` ↔ `{f.get('article_id')}` "
                      f"(year={f.get('exam_year')}, {f.get('subtype')})",
        ))

    # UNLINKED_CITED_ARTICLE is medium severity — show samples
    unlinked = [f for f in findings if f["check"] == "UNLINKED_CITED_ARTICLE"]
    if unlinked:
        out.append(f"\n### UNLINKED_CITED_ARTICLE ({len(unlinked)})\n")
        out.append(_example_block(
            unlinked,
            lambda f: f"`{f['article_id']}` cached citation_count="
                      f"{f.get('cached_value')} but xref has 0 rows",
        ))
    return "\n".join(out)


# ══════════════════════════════════════════════════════════════════════════════
# Top-level
# ══════════════════════════════════════════════════════════════════════════════

def render_report(findings_by_layer: dict[str, dict]) -> str:
    a = findings_by_layer["A"]
    b = findings_by_layer["B"]
    c = findings_by_layer["C"]
    total = sum(len(layer.get("findings", [])) for layer in (a, b, c))

    out: list[str] = []
    out.append("# Corpus Integrity QC Report")
    out.append("")
    out.append(f"_Generated: {_dt.datetime.now().isoformat(timespec='seconds')}_")
    out.append(f"_Total findings: **{total}**_")
    out.append("")

    # ── Executive summary ──
    out.append("## Executive Summary\n")
    rows: list[list] = []
    for label, layer in [
        ("A — Text Fidelity", a),
        ("B — Citation Linkage", b),
        ("C — Structural Integrity", c),
    ]:
        s = layer.get("summary", {})
        by_check = s.get("by_check", {})
        by_sev = s.get("by_severity", {})
        rows.append([
            label,
            s.get("total_findings", 0),
            ", ".join(f"{k}={v}" for k, v in sorted(by_check.items())) or "—",
            ", ".join(f"{k}={v}" for k, v in sorted(by_sev.items())) or "—",
        ])
    out.append(_md_table(
        ["Layer", "Total", "By check", "By severity"], rows,
    ))

    # ── Per-layer sections ──
    out.append(render_layer_a(a))
    out.append("\n---\n")
    out.append(render_layer_b(b))
    out.append("\n---\n")
    out.append(render_layer_c(c))
    out.append("\n---\n")

    # ── Recommended next steps ──
    out.append("## Recommended Next Steps\n")
    out.append(
        "1. **Review `fixes.sql`** — Tier 1 statements are wrapped in "
        "`BEGIN`/`COMMIT`; pre-flight by reading the block, then apply.\n"
        "2. **Tier 2 review** — each statement is commented out by default; "
        "uncomment after eyeballing the evidence inline.\n"
        "3. **Tier 3 manual triage** — see the per-section examples above; "
        "no SQL is generated.\n"
        "4. **Re-run resident analyses** after any Tier 1 application that "
        "touches `articles` cache columns or `qid_art_xref`.\n"
        "5. **Spot re-extract from PDF** for any A2/A3 finding before "
        "uncommenting its Tier 2 statement (V1.1 will automate this via "
        "the deferred A4 PDF-diff hook).\n"
    )
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build qc_report.md from findings JSONs")
    parser.add_argument("--findings-dir", required=True,
                        help="Directory containing findings_layer_{a,b,c}.json")
    args = parser.parse_args()

    findings_dir = Path(args.findings_dir).resolve()
    if not findings_dir.exists():
        print(f"ERROR: findings dir not found at {findings_dir}", file=sys.stderr)
        return 1

    findings = {
        "A": load_layer(findings_dir, "a"),
        "B": load_layer(findings_dir, "b"),
        "C": load_layer(findings_dir, "c"),
    }

    text = render_report(findings)
    out_path = findings_dir / "qc_report.md"
    out_path.write_text(text, encoding="utf-8")

    print(f"Written: {out_path} ({len(text):,} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
