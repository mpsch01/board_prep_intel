"""
layer_a_text.py
===============
Layer A — Text Fidelity Audit (detect-only V1).

Scans the ITE `questions` table for evidence of parsing artifacts, format drift,
and truncation. All checks are pure-DB: no PDF I/O, no API calls.

Checks implemented:
  A1. ENCODING_ARTIFACT   — known-bad sequences (Symbol-font, double-encoded
                            Latin, mojibake) in question_text / choices /
                            explanation / reference.
  A2. TRUNCATION_CANDIDATE — explanation field ends without terminal punctuation
                             AND length is in the bottom decile (p10) for its
                             exam_year (catches dangling-reference-number cuts).
                             Reference field: dangling/empty pipe segments.
                             (question_text truncation is NOT checked — ITE has
                             legitimate fill-in-the-blank stems that end mid-
                             sentence; that check is deferred to A4 PDF diff.)
  A3. FORMAT_DRIFT        — correct_letter outside {A..E}; choices NULL / parse
                            failure / empty list; correct_letter not present in
                            choices' letter set; blueprint / body_system /
                            body_system_merged null. (ITE allows both 4-choice
                            and 5-choice questions, so the rigid "must be 5"
                            check is intentionally NOT applied.)

Deferred to V1.1:
  A4. PDF_DIFF (spot re-extract) — per-field diff against re-extracted PDF text
                                   for QIDs already flagged by A1/A2/A3.
                                   Requires hooking into M2 critique extractor;
                                   tracked under DEFERRED-CORPUS-QC-LAYERS-AB-D.

Usage:
  python layer_a_text.py --output-dir <OUTPUT_DIR> \\
                         [--db-path <DB>] \\
                         [--truncation-floor-percentile 10]

Output:
  findings_layer_a.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from utils import (  # noqa: E402
    ENCODING_FIXES,
    connect_db_readonly,
    find_encoding_artifacts,
    resolve_db_path,
)


EXPECTED_LETTERS = {"A", "B", "C", "D", "E"}  # valid letter alphabet (4-choice
                                              # questions use A-D, 5-choice use
                                              # A-E; both are legitimate)

# Terminal punctuation that legitimately ends a question / explanation.
QUESTION_TERMINALS = ("?", ".", ")", "?)", ").")
EXPLANATION_TERMINALS = (".", "?", "!", ")", '"', "”", "’")
REFERENCE_TERMINALS = (".", ")", "]", "”", '"')


def _default_project_root() -> Path:
    return SCRIPT_DIR.parent.parent.parent.parent.parent.resolve()


# ══════════════════════════════════════════════════════════════════════════════
# A1 — ENCODING_ARTIFACT
# ══════════════════════════════════════════════════════════════════════════════

QUESTION_TEXT_FIELDS: tuple[str, ...] = (
    "question_text",
    "choices",
    "correct_text",
    "explanation",
    "reference",
)


def _collect_choice_strings(choices_raw: str | None) -> list[str]:
    """Parse choices JSON and return the list of choice-text strings.
    If parse fails, fall back to scanning the raw string."""
    if not choices_raw:
        return []
    try:
        parsed = json.loads(choices_raw)
    except (json.JSONDecodeError, TypeError):
        return [choices_raw]
    if not isinstance(parsed, list):
        return [choices_raw]
    out: list[str] = []
    for item in parsed:
        if isinstance(item, dict) and "text" in item:
            out.append(str(item["text"]))
        else:
            out.append(str(item))
    return out


def check_encoding_artifacts(questions: list[dict]) -> list[dict]:
    findings: list[dict] = []
    for q in questions:
        for field in QUESTION_TEXT_FIELDS:
            raw = q.get(field)
            if raw is None:
                continue

            if field == "choices":
                texts = _collect_choice_strings(raw)
                for idx, t in enumerate(texts):
                    arts = find_encoding_artifacts(t)
                    for bad, good in arts:
                        findings.append({
                            "check": "ENCODING_ARTIFACT",
                            "severity": "MEDIUM",
                            "qid": q["qid"],
                            "exam_year": q.get("exam_year"),
                            "field": f"choices[{idx}]",
                            "bad_sequence": bad,
                            "corrected": good,
                            "count": t.count(bad),
                            "detail": (
                                f"Bad sequence {bad!r} found in choices[{idx}] "
                                f"({t.count(bad)}×) — corrected = {good!r}."
                            ),
                        })
                continue

            if not isinstance(raw, str):
                continue
            arts = find_encoding_artifacts(raw)
            for bad, good in arts:
                findings.append({
                    "check": "ENCODING_ARTIFACT",
                    "severity": "MEDIUM",
                    "qid": q["qid"],
                    "exam_year": q.get("exam_year"),
                    "field": field,
                    "bad_sequence": bad,
                    "corrected": good,
                    "count": raw.count(bad),
                    "detail": (
                        f"Bad sequence {bad!r} found in {field} "
                        f"({raw.count(bad)}×) — corrected = {good!r}."
                    ),
                })
    return findings


# ══════════════════════════════════════════════════════════════════════════════
# A2 — TRUNCATION_CANDIDATE
# ══════════════════════════════════════════════════════════════════════════════

def _percentile(sorted_vals: list[int], p: float) -> int:
    if not sorted_vals:
        return 0
    idx = max(0, min(len(sorted_vals) - 1, int(len(sorted_vals) * p)))
    return sorted_vals[idx]


def _endswith_terminal(text: str, terminals: tuple[str, ...]) -> bool:
    stripped = text.rstrip().rstrip('"\'')
    return any(stripped.endswith(t) for t in terminals)


def check_truncation(
    questions: list[dict],
    floor_percentile: float,
) -> list[dict]:
    findings: list[dict] = []

    # Build per-year length distribution for explanation only.
    # question_text truncation is intentionally NOT checked — fill-in-the-blank
    # stems legitimately end without terminal punctuation, and the bottom-decile
    # heuristic generates ~30 false positives. Deferred to A4 (PDF diff).
    by_year: dict[int, list[int]] = defaultdict(list)
    for q in questions:
        y = q.get("exam_year")
        if not isinstance(y, int):
            continue
        if q.get("explanation"):
            by_year[y].append(len(q["explanation"]))

    floors: dict[int, int] = {
        y: _percentile(sorted(lengths), floor_percentile)
        for y, lengths in by_year.items()
    }

    for q in questions:
        y = q.get("exam_year")
        etext = q.get("explanation")
        ref = q.get("reference")

        # A2b — explanation truncation
        if etext and isinstance(y, int):
            floor = floors.get(y, 0)
            if len(etext) < floor and not _endswith_terminal(etext, EXPLANATION_TERMINALS):
                findings.append({
                    "check": "TRUNCATION_CANDIDATE",
                    "subtype": "explanation",
                    "severity": "HIGH",
                    "qid": q["qid"],
                    "exam_year": y,
                    "length": len(etext),
                    "year_floor_p": floor_percentile,
                    "year_floor_chars": floor,
                    "tail": etext[-80:] if etext else "",
                    "detail": (
                        f"explanation is {len(etext)} chars (year p"
                        f"{int(floor_percentile*100)}={floor}) and lacks "
                        "terminal punctuation."
                    ),
                })

        # A2c — reference dangling pipe / empty segments
        if ref and isinstance(ref, str):
            stripped = ref.strip()
            problem = None
            if stripped.endswith("|"):
                problem = "ends with dangling pipe"
            elif stripped.startswith("|"):
                problem = "starts with pipe (empty leading segment)"
            elif re.search(r"\|\s*\|", stripped):
                problem = "contains empty segment between pipes"
            elif stripped.endswith(",") or stripped.endswith(";"):
                problem = "ends mid-citation (terminal , or ;)"
            if problem:
                findings.append({
                    "check": "TRUNCATION_CANDIDATE",
                    "subtype": "reference",
                    "severity": "MEDIUM",
                    "qid": q["qid"],
                    "exam_year": y,
                    "length": len(ref),
                    "tail": ref[-80:],
                    "detail": f"reference field {problem}.",
                })

    return findings


# ══════════════════════════════════════════════════════════════════════════════
# A3 — FORMAT_DRIFT
# ══════════════════════════════════════════════════════════════════════════════

def check_format_drift(questions: list[dict]) -> list[dict]:
    findings: list[dict] = []
    for q in questions:
        qid = q["qid"]
        y = q.get("exam_year")

        # A3a — correct_letter out of range
        cl = q.get("correct_letter")
        if cl is None or cl not in EXPECTED_LETTERS:
            findings.append({
                "check": "FORMAT_DRIFT",
                "subtype": "correct_letter",
                "severity": "HIGH",
                "qid": qid,
                "exam_year": y,
                "current_value": cl,
                "detail": (
                    f"correct_letter={cl!r} not in {{A,B,C,D,E}} — answer key "
                    "is malformed."
                ),
            })

        # A3b — choices parse + count + letter coverage
        choices_raw = q.get("choices")
        if choices_raw is None:
            findings.append({
                "check": "FORMAT_DRIFT",
                "subtype": "choices_null",
                "severity": "HIGH",
                "qid": qid,
                "exam_year": y,
                "detail": "choices field is NULL.",
            })
        else:
            try:
                parsed = json.loads(choices_raw)
            except (json.JSONDecodeError, TypeError):
                parsed = None
                findings.append({
                    "check": "FORMAT_DRIFT",
                    "subtype": "choices_parse_error",
                    "severity": "HIGH",
                    "qid": qid,
                    "exam_year": y,
                    "preview": choices_raw[:160] if isinstance(choices_raw, str) else None,
                    "detail": "choices field does not parse as JSON.",
                })
            if isinstance(parsed, list):
                if len(parsed) == 0:
                    findings.append({
                        "check": "FORMAT_DRIFT",
                        "subtype": "choices_empty",
                        "severity": "HIGH",
                        "qid": qid,
                        "exam_year": y,
                        "detail": "choices field parses as an empty list — answer key has no options.",
                    })
                else:
                    letters_seen = {
                        str(c.get("letter")).strip() if isinstance(c, dict) else None
                        for c in parsed
                    }
                    letters_seen.discard(None)
                    extra = letters_seen - EXPECTED_LETTERS
                    if extra:
                        findings.append({
                            "check": "FORMAT_DRIFT",
                            "subtype": "choices_letters_extra",
                            "severity": "HIGH",
                            "qid": qid,
                            "exam_year": y,
                            "letters_seen": sorted(letters_seen),
                            "extra": sorted(extra),
                            "detail": (
                                f"choices contains letters outside {{A..E}}: "
                                f"extra={sorted(extra)}."
                            ),
                        })
                    if cl is not None and cl in EXPECTED_LETTERS and cl not in letters_seen:
                        findings.append({
                            "check": "FORMAT_DRIFT",
                            "subtype": "correct_letter_not_in_choices",
                            "severity": "HIGH",
                            "qid": qid,
                            "exam_year": y,
                            "correct_letter": cl,
                            "letters_seen": sorted(letters_seen),
                            "detail": (
                                f"correct_letter={cl!r} does not appear in "
                                f"choices (letters_seen={sorted(letters_seen)})."
                            ),
                        })

        # A3c — blueprint / body_system / body_system_merged null/empty
        for col in ("blueprint", "body_system", "body_system_merged"):
            v = q.get(col)
            if v is None or (isinstance(v, str) and not v.strip()):
                findings.append({
                    "check": "FORMAT_DRIFT",
                    "subtype": f"{col}_empty",
                    "severity": "MEDIUM",
                    "qid": qid,
                    "exam_year": y,
                    "detail": (
                        f"{col} is NULL/empty — expected 100% coverage post-"
                        "BATON 060."
                    ),
                })

    return findings


# ══════════════════════════════════════════════════════════════════════════════
# Orchestration
# ══════════════════════════════════════════════════════════════════════════════

def run_layer_a(db_path: Path, floor_percentile: float) -> tuple[list[dict], dict]:
    conn = connect_db_readonly(db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT qid, exam_year, blueprint, body_system, body_system_merged, "
        "       question_text, choices, correct_letter, correct_text, "
        "       explanation, reference "
        "FROM questions"
    )
    questions = [dict(r) for r in cur.fetchall()]
    conn.close()

    findings: list[dict] = []
    findings.extend(check_encoding_artifacts(questions))
    findings.extend(check_truncation(questions, floor_percentile))
    findings.extend(check_format_drift(questions))

    meta = {
        "questions_scanned": len(questions),
        "truncation_floor_percentile": floor_percentile,
        "encoding_fixes_table_size": len(ENCODING_FIXES),
        "a4_pdf_diff_status": "DEFERRED-V1.1 (needs M2 critique re-extractor hook)",
    }
    return findings, meta


def build_summary(findings: list[dict], meta: dict) -> dict[str, Any]:
    by_check: Counter = Counter(f["check"] for f in findings)
    by_subtype: Counter = Counter(
        f"{f['check']}/{f.get('subtype', '-')}" for f in findings
    )
    by_severity: Counter = Counter(f["severity"] for f in findings)
    return {
        **meta,
        "total_findings": len(findings),
        "by_check": dict(by_check),
        "by_check_subtype": dict(by_subtype),
        "by_severity": dict(by_severity),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Layer A — text fidelity audit (detect-only)")
    parser.add_argument("--output-dir", required=True,
                        help="Where to write findings_layer_a.json")
    parser.add_argument("--db-path", help="Path to ite_intelligence.db (auto-detected if omitted)")
    parser.add_argument("--project-root",
                        help="Override PROJECT_ROOT (used for DB auto-detect)")
    parser.add_argument("--truncation-floor-percentile", type=float, default=0.10,
                        help="Percentile of year-length used as truncation floor (default 0.10)")
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.db_path:
        db_path = Path(args.db_path).resolve()
    elif args.project_root:
        db_path = resolve_db_path(Path(args.project_root).resolve())
    else:
        db_path = resolve_db_path(_default_project_root())

    print(f"DB:         {db_path}")
    print(f"Output dir: {output_dir}")
    print(f"Truncation floor: p{int(args.truncation_floor_percentile*100)}")

    if not db_path.exists():
        print(f"ERROR: DB not found at {db_path}", file=sys.stderr)
        return 1

    print("Running Layer A checks...")
    findings, meta = run_layer_a(db_path, args.truncation_floor_percentile)
    summary = build_summary(findings, meta)

    result = {
        "layer": "A",
        "name": "text_fidelity",
        "summary": summary,
        "findings": findings,
    }

    out_path = output_dir / "findings_layer_a.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)

    print()
    print("=== Layer A Summary ===")
    print(f"Questions scanned: {meta['questions_scanned']}")
    print(f"Total findings:    {summary['total_findings']}")
    for check, cnt in sorted(summary["by_check"].items()):
        print(f"  {check}: {cnt}")
    print()
    if summary["by_check_subtype"]:
        print("By subtype:")
        for k, v in sorted(summary["by_check_subtype"].items()):
            print(f"  {k}: {v}")
    print()
    print(f"Written to: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
