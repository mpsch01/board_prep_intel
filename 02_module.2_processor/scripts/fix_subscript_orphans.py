#!/usr/bin/env python3
"""
fix_subscript_orphans.py

Two-phase cleanup of wandering-subscript orphans in questions.question_text
and questions.explanation (BATON 076 finding: 47 + 115 = 162 affected rows
with 205 total orphan instances).

Pattern: pdfplumber renders chemical/lab subscripts (A₁c, H₂, T₄, B₁₂, S₃,
HCO₃, FEV₁, etc.) on their own row between content lines. Result is text like:

    "...hemoglobin A  ≥6.5%,
    1c
    a fasting plasma glucose..."

Phase 1 — Orphan line removal:
    Detect lines that contain only a short digit/digit-letter token
    (e.g., "1c", "2", "12") sandwiched between non-empty content lines.
    Remove the orphan line and join the surrounding content with a single
    space (or no space if join would create a double-space).

Phase 2 — Subscript recovery (medical-knowledge regex sweep):
    After Phase 1, apply a curated set of context-aware substitutions to
    re-insert the subscript at its canonical host position. Patterns:
      - "hemoglobin A   " → "hemoglobin A1c " (when followed by lab value)
      - "vitamin B   " → "vitamin B12 " (when followed by level/deficien)
      - "H -blocker" → "H2-blocker"
      - "T  levels" / "Free T " → "T4 levels" / "Free T4 "
      - "S  heart sound" / "S  gallop" → "S3 heart sound" / "S3 gallop"
        (NOTE: S₃ vs S₄ is ambiguous from text alone — defaults to S3 as
        most common in ITE questions; flag for manual review)
      - "FEV " → "FEV1 "
      - "HCO " → "HCO3 "
      - "Lp-PLA " → "Lp-PLA2 "
      - "PaCO " → "PaCO2 "
      - "PaO " → "PaO2 "
      - "Free T " → "Free T4 "
    Page-footer leaks (multi-digit 2-99) are dropped in Phase 1 with no
    Phase 2 recovery (they were never subscripts).

Writes preview + SQL to:
  03_module.3_analyst/outputs/corpus_qc/<date>_subscript_cleanup/

Does NOT modify the DB — apply via inline fix-applier pattern after review.
"""

import io
import json
import re
import sqlite3
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path


def setup_utf8_stdout() -> None:
    for name in ("stdout", "stderr"):
        stream = getattr(sys, name)
        enc = (getattr(stream, "encoding", "") or "").lower()
        if enc == "utf-8":
            continue
        try:
            setattr(sys, name, io.TextIOWrapper(stream.buffer, encoding="utf-8", errors="replace"))
        except Exception:
            pass


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"
OUT_DIR = (
    PROJECT_ROOT
    / "03_module.3_analyst"
    / "outputs"
    / "corpus_qc"
    / f"{datetime.now():%Y-%m-%d}_subscript_cleanup"
)

# ─── Phase 1: orphan detection ─────────────────────────────────────────────
# Single short token: "1", "2", "1c", "12", "35", "49", etc.
ORPHAN_TOKEN_RE = re.compile(r"^\d{1,3}[a-z]{0,2}$")
# Multi-token orphan: "1 1", "2 2", "1 2" — two adjacent subscripts on one line.
# Max 4 tokens (rare) to limit risk on legitimate short numeric lines.
MULTI_TOKEN_ORPHAN_RE = re.compile(r"^(\d{1,3}[a-z]{0,2})(\s+\d{1,3}[a-z]{0,2}){1,3}$")


def is_orphan_line(stripped: str) -> bool:
    return bool(ORPHAN_TOKEN_RE.fullmatch(stripped) or MULTI_TOKEN_ORPHAN_RE.fullmatch(stripped))


def remove_orphan_lines(text: str) -> tuple[str, list[dict]]:
    """Remove digit-only (single or multi-token) lines sandwiched between content."""
    if not text:
        return text, []
    lines = text.split("\n")
    keep: list[str] = []
    removed = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if (
            is_orphan_line(stripped)
            and i > 0 and i < len(lines) - 1
            and lines[i - 1].strip()
            and lines[i + 1].strip()
        ):
            removed.append({"position": i, "token": stripped,
                            "prev_tail": lines[i - 1][-60:],
                            "next_head": lines[i + 1][:60]})
        else:
            keep.append(line)
    return "\n".join(keep), removed


# ─── Phase 2: subscript recovery (medical regex sweep) ─────────────────────
# Each tuple is (description, pattern, replacement). Applied in order.
# Patterns use `\s{2,}` or specific 2+ space gap as the signal that a subscript
# was removed, OR an alternate signal (e.g., "H -blocker" with single-space gap
# next to a recognizable medical idiom).
SUBSCRIPT_RULES: list[tuple[str, re.Pattern[str], str]] = [
    # hemoglobin A1c — "hemoglobin A  <value>" or "hemoglobin A , ..."
    # Replacement uses \g<1>1c (NOT \1c, which Python parses as group 1 + literal c).
    ("hemoglobin A1c",
     re.compile(r"\b(hemoglobin\s+A|Hb\s*A|HbA|HgbA)\s{1,4}(?=[≥<>=,.;]|\d|≤|\bis\b|\bnow\b|\bof\b|\blevel\b)"),
     r"\g<1>1c "),
    # A1c standalone (preceded by hemoglobin context loss-tolerant)
    ("A1c trailing percent",
     re.compile(r"\b(hemoglobin\s+A|Hb\s*A|A)\s{2,}(?=\d+\.\d+\s*%)"),
     r"\g<1>1c "),
    # vitamin B12
    ("vitamin B12",
     re.compile(r"\b(vitamin\s+B|cobalamin\s+B|B)\s{1,4}(?=level|deficien|status|\bor\b|\band\b|\bbut\b|malabsorp|\bin\b|\bis\b|,|\n|\.|\b—|\b–)"),
     r"\g<1>12 "),
    # H2-blocker / H2-antagonist / H2-receptor
    ("H2-blocker",
     re.compile(r"\bH\s+(?=-?(blocker|antagonist|receptor))"),
     "H2"),
    # H2O (water) — distinct from H2-blocker
    ("H2O",
     re.compile(r"\bH\s+O\b"),
     "H2O"),
    # CO2 (carbon dioxide)
    ("CO2",
     re.compile(r"\bCO\s+(?=level|saturation|content|retention|tension|\.|,)"),
     "CO2 "),
    # O2 saturation
    ("O2 saturation",
     re.compile(r"\b(\sO|^O)\s+(?=saturation)"),
     r"\g<1>2 "),
    # HCO3 (bicarbonate)
    ("HCO3",
     re.compile(r"\bHCO\s+(?=level|<|>|\d|—|-)"),
     "HCO3 "),
    # PaCO2 / PaO2
    ("PaCO2",
     re.compile(r"\bPaCO\s+"),
     "PaCO2 "),
    ("PaO2",
     re.compile(r"\bPaO\s+"),
     "PaO2 "),
    # Free T4 / T4 levels / TSH and T  levels
    ("Free T4",
     re.compile(r"\b(Free|free)\s+T\s+(?=level|\d|of\s|is\s)"),
     r"\g<1> T4 "),
    ("T4 levels",
     re.compile(r"\b(TSH\s+and|and)\s+T\s+(?=level)"),
     r"\g<1> T4 "),
    # S3 heart sound / S3 gallop (S₃ is more common in ITE — S₄ less common)
    ("S3 gallop",
     re.compile(r"\bS\s+(?=gallop|heart\s+sound)"),
     "S3 "),
    # FEV1
    ("FEV1",
     re.compile(r"\bFEV\s+(?=/|\bof|<|>|=|\bratio|\bvolume|\bvalue|\bpredicted|\bafter|\bnormal|reversibility|\bimproved|\bdecreased|\bincreased|\bthat\b)"),
     "FEV1 "),
    # Lp-PLA2
    ("Lp-PLA2",
     re.compile(r"\bLp-PLA\s+"),
     "Lp-PLA2 "),
    # phospholipase A2 (when no Lp- prefix)
    ("phospholipase A2",
     re.compile(r"\bphospholipase\s+A\s+(?=[(]|\d|level|in\b|or\b|and\b)"),
     "phospholipase A2 "),
    # alpha1-antitrypsin (α₁-antitrypsin) — handle the missing α + missing 1
    ("alpha1-antitrypsin",
     re.compile(r"(?<!\w)\s*-(?=Antitrypsin|antitrypsin)"),
     " α1-"),
]


def recover_subscripts(text: str) -> tuple[str, list[dict]]:
    """Apply subscript recovery rules. Return (new_text, applied_rules)."""
    if not text:
        return text, []
    applied = []
    out = text
    for name, pat, repl in SUBSCRIPT_RULES:
        new = pat.sub(repl, out)
        if new != out:
            applied.append({"rule": name, "delta": len(new) - len(out)})
            out = new
    return out, applied


def main() -> None:
    setup_utf8_stdout()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT qid, question_text, explanation FROM questions"
    ).fetchall()
    conn.close()

    results = []
    for qid, qtext, exp in rows:
        # Process each column independently.
        updates = {}
        notes = {}
        for col, value in (("question_text", qtext), ("explanation", exp)):
            value = value or ""
            phase1, removed = remove_orphan_lines(value)
            phase2, recoveries = recover_subscripts(phase1)
            if phase2 != value:
                updates[col] = phase2
                notes[col] = {
                    "removed_orphans": removed,
                    "recoveries": recoveries,
                    "before_len": len(value),
                    "after_len": len(phase2),
                }
        if updates:
            results.append({"qid": qid, "updates": updates, "notes": notes})

    print(f"Total questions scanned: {len(rows)}")
    print(f"Questions needing cleanup: {len(results)}")

    # Aggregate stats
    total_orphans_removed = sum(
        len(r["notes"][col]["removed_orphans"])
        for r in results
        for col in r["notes"]
    )
    total_recoveries = sum(
        len(r["notes"][col]["recoveries"])
        for r in results
        for col in r["notes"]
    )
    rule_counts: Counter = Counter()
    for r in results:
        for col, n in r["notes"].items():
            for rec in n["recoveries"]:
                rule_counts[rec["rule"]] += 1
    print(f"Total orphan lines removed: {total_orphans_removed}")
    print(f"Total subscript recoveries applied: {total_recoveries}")
    print()
    print("Rule application counts:")
    for k, n in rule_counts.most_common():
        print(f"  {k:<30s} {n}")

    (OUT_DIR / "subscript_cleanup_results.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Build SQL
    sql_lines = [
        "-- subscript orphan cleanup",
        f"-- Generated: {datetime.now():%Y-%m-%d %H:%M:%S}",
        f"-- Affects: {len(results)} questions",
        f"-- Orphan lines removed: {total_orphans_removed}",
        f"-- Subscript recoveries: {total_recoveries}",
        "",
        "BEGIN;",
        "",
    ]
    for r in results:
        sql_lines.append(f"-- {r['qid']}")
        for col, val in r["updates"].items():
            val_sql = val.replace("'", "''")
            sql_lines.append(f"UPDATE questions SET {col} = '{val_sql}' WHERE qid = '{r['qid']}';")
        sql_lines.append("")
    sql_lines.append("COMMIT;")
    sql_lines.append("")
    (OUT_DIR / "subscript_cleanup.sql").write_text("\n".join(sql_lines), encoding="utf-8")

    # Preview (first 25)
    md_lines = [
        f"# Subscript orphan cleanup preview ({len(results)} questions)",
        "",
        f"- orphan lines removed: {total_orphans_removed}",
        f"- subscript recoveries: {total_recoveries}",
        f"- recovery rule counts: {dict(rule_counts)}",
        "",
    ]
    for r in results[:25]:
        md_lines.append(f"## {r['qid']}")
        for col, n in r["notes"].items():
            md_lines.append(f"### {col} (len {n['before_len']} → {n['after_len']})")
            if n["removed_orphans"]:
                md_lines.append(f"  - orphan tokens removed: {[o['token'] for o in n['removed_orphans']]}")
            if n["recoveries"]:
                md_lines.append(f"  - recoveries: {[rec['rule'] for rec in n['recoveries']]}")
            md_lines.append("  - before tail:")
            md_lines.append("```")
            md_lines.append((qtext_or_exp_lookup(rows, r["qid"], col) or "")[-300:])
            md_lines.append("```")
            md_lines.append("  - after tail:")
            md_lines.append("```")
            md_lines.append(r["updates"][col][-300:])
            md_lines.append("```")
        md_lines.append("")
    if len(results) > 25:
        md_lines.append(f"_(showing first 25 of {len(results)})_")
    (OUT_DIR / "subscript_cleanup_preview.md").write_text("\n".join(md_lines), encoding="utf-8")

    print()
    print(f"Artifacts: {OUT_DIR.relative_to(PROJECT_ROOT).as_posix()}/")


def qtext_or_exp_lookup(rows, qid, col):
    for q, qt, exp in rows:
        if q == qid:
            return qt if col == "question_text" else exp
    return None


if __name__ == "__main__":
    main()
