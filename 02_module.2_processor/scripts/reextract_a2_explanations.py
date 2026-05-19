#!/usr/bin/env python3
"""
reextract_a2_explanations.py

One-off remediation for the 23 A2 (TRUNCATION_CANDIDATE/explanation) findings
from corpus-integrity-qc V1 (BATON 075 post-Tier-1 QC run).

The A2 check is a heuristic — it flags questions whose explanation length is
below the year-median floor. Some flagged QIDs are genuinely truncated; others
just happen to have short explanations on simple topics. This script:

  1. Opens the matching YYYY_critique.pdf for each affected year
  2. Splits into Item NN blocks
  3. Extracts the explanation body for each target QID (between the "ANSWER: X"
     line and the next "Item NN" header)
  4. Compares PDF-extracted length against current DB explanation length
  5. Generates UPDATE statements ONLY where the PDF version is meaningfully
     longer than the DB version (cutoff: PDF >= DB + 50 chars)
  6. Reports per-QID classification: UPDATE_NEEDED, ALREADY_FULL, EXTRACTION_FAIL

Writes:
  - 03_module.3_analyst/outputs/corpus_qc/<date>_a2_reextract/a2_extraction_results.json
  - 03_module.3_analyst/outputs/corpus_qc/<date>_a2_reextract/a2_updates.sql
  - 03_module.3_analyst/outputs/corpus_qc/<date>_a2_reextract/a2_preview.md
"""

import io
import json
import re
import sqlite3
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

import pdfplumber


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
EXAM_PDFS_DIR = PROJECT_ROOT / "01_module.1_warehouse" / "ite_exams"
OUT_DIR = (
    PROJECT_ROOT
    / "03_module.3_analyst"
    / "outputs"
    / "corpus_qc"
    / f"{datetime.now():%Y-%m-%d}_a2_reextract"
)

TARGET_QIDS = [
    "QID-2020-0006", "QID-2020-0069", "QID-2020-0116", "QID-2020-0122",
    "QID-2020-0158", "QID-2020-0180", "QID-2020-0191",
    "QID-2021-0021", "QID-2021-0076", "QID-2021-0079", "QID-2021-0106", "QID-2021-0191",
    "QID-2022-0010", "QID-2022-0023", "QID-2022-0080", "QID-2022-0142", "QID-2022-0165",
    "QID-2022-0196",
    "QID-2023-0005", "QID-2023-0018", "QID-2023-0059", "QID-2023-0113", "QID-2023-0198",
]

MIN_GROWTH_CHARS = 50  # PDF must be >= DB + 50 chars to count as "needs update"

ITEM_RE = re.compile(r"(?m)^Item (\d{1,3})\b")
ANSWER_LINE_RE = re.compile(r"(?m)^ANSWER:\s*([A-E])\b")


def build_full_text(pdf_path: Path) -> str:
    """Concatenate full critique PDF text."""
    parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            parts.append(page.extract_text() or "")
    return "\n".join(parts)


def split_items(text: str) -> dict:
    """Split critique into {item_num: block_text} using monotonic constraint."""
    raw = list(ITEM_RE.finditer(text))
    valid = []
    expected = 1
    for m in raw:
        if int(m.group(1)) == expected:
            valid.append(m)
            expected += 1
    items = {}
    for i, m in enumerate(valid):
        num = int(m.group(1))
        start = m.end()
        end = valid[i + 1].start() if i + 1 < len(valid) else len(text)
        items[num] = text[start:end].strip()
    return items


def extract_explanation(block: str) -> tuple[str | None, str | None]:
    """From an Item block, locate the ANSWER line and return (answer_letter, explanation_body).

    The explanation body is everything after the ANSWER: X line through the
    end of the block (which is the next Item header or EOF).
    """
    m = ANSWER_LINE_RE.search(block)
    if not m:
        return None, None
    answer = m.group(1)
    body = block[m.end():].lstrip("\n").rstrip()
    return answer, body


def main() -> None:
    setup_utf8_stdout()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    by_year: dict[int, list[tuple[str, int]]] = {}
    for qid in TARGET_QIDS:
        _, yr, item = qid.split("-")
        by_year.setdefault(int(yr), []).append((qid, int(item)))

    conn = sqlite3.connect(DB_PATH)
    db_state = {}
    for qid in TARGET_QIDS:
        row = conn.execute(
            "SELECT explanation, correct_letter FROM questions WHERE qid = ?", (qid,)
        ).fetchone()
        db_state[qid] = {
            "explanation": row[0] or "",
            "correct_letter": row[1],
        }
    conn.close()

    results = []
    for year in sorted(by_year):
        pdf_path = EXAM_PDFS_DIR / f"{year}_critique.pdf"
        print(f"[{year}] {pdf_path.name}")
        text = build_full_text(pdf_path)
        items = split_items(text)
        print(f"[{year}]   parsed {len(items)} items")
        for qid, item_num in by_year[year]:
            block = items.get(item_num)
            if block is None:
                results.append({
                    "qid": qid, "year": year, "item": item_num,
                    "status": "EXTRACTION_FAIL",
                    "reason": "item not found in critique PDF",
                    "db_len": len(db_state[qid]["explanation"]),
                    "pdf_len": None,
                    "db_correct_letter": db_state[qid]["correct_letter"],
                    "pdf_answer_letter": None,
                    "pdf_explanation": None,
                    "db_explanation_head": db_state[qid]["explanation"][:160],
                    "db_explanation_tail": db_state[qid]["explanation"][-160:],
                })
                continue
            answer, body = extract_explanation(block)
            if body is None:
                results.append({
                    "qid": qid, "year": year, "item": item_num,
                    "status": "EXTRACTION_FAIL",
                    "reason": "ANSWER: line not found in item block",
                    "db_len": len(db_state[qid]["explanation"]),
                    "pdf_len": None,
                    "db_correct_letter": db_state[qid]["correct_letter"],
                    "pdf_answer_letter": None,
                    "pdf_explanation": None,
                    "db_explanation_head": db_state[qid]["explanation"][:160],
                    "db_explanation_tail": db_state[qid]["explanation"][-160:],
                })
                continue
            db_exp = db_state[qid]["explanation"]
            db_len = len(db_exp)
            pdf_len = len(body)
            answer_mismatch = answer != db_state[qid]["correct_letter"]
            if pdf_len >= db_len + MIN_GROWTH_CHARS:
                status = "UPDATE_NEEDED"
            else:
                status = "ALREADY_FULL"
            results.append({
                "qid": qid, "year": year, "item": item_num,
                "status": status,
                "reason": None if not answer_mismatch else f"answer mismatch: DB={db_state[qid]['correct_letter']} PDF={answer}",
                "db_len": db_len,
                "pdf_len": pdf_len,
                "growth": pdf_len - db_len,
                "db_correct_letter": db_state[qid]["correct_letter"],
                "pdf_answer_letter": answer,
                "pdf_explanation": body,
                "db_explanation_head": db_exp[:160],
                "db_explanation_tail": db_exp[-160:],
            })

    (OUT_DIR / "a2_extraction_results.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    status_counts = Counter(r["status"] for r in results)
    print()
    print(f"Status distribution: {dict(status_counts)}")

    sql_lines = [
        "-- A2 explanation truncation re-extraction",
        f"-- Generated: {datetime.now():%Y-%m-%d %H:%M:%S}",
        f"-- Source PDFs: {EXAM_PDFS_DIR.relative_to(PROJECT_ROOT).as_posix()}/YYYY_critique.pdf",
        f"-- Targets: {len(TARGET_QIDS)} QIDs    Status: {dict(status_counts)}",
        f"-- Threshold: PDF length must be >= DB length + {MIN_GROWTH_CHARS} chars to update",
        "",
        "-- ============================================================",
        "-- UPDATES — only QIDs where critique-PDF explanation is meaningfully",
        "-- longer than DB explanation. ALREADY_FULL rows are skipped (the A2",
        "-- TRUNCATION_CANDIDATE heuristic flagged them as below year-median",
        "-- but the DB version already matches the critique PDF in full).",
        "-- ============================================================",
        "BEGIN;",
        "",
    ]
    for r in results:
        if r["status"] != "UPDATE_NEEDED":
            continue
        exp_sql = r["pdf_explanation"].replace("'", "''")
        sql_lines.append(
            f"-- {r['qid']} (item {r['item']} in {r['year']}_critique.pdf) "
            f"— db_len={r['db_len']}  pdf_len={r['pdf_len']}  growth=+{r['growth']}"
        )
        sql_lines.append(
            f"UPDATE questions SET explanation = '{exp_sql}' WHERE qid = '{r['qid']}';"
        )
        sql_lines.append("")
    sql_lines.append("COMMIT;")
    sql_lines.append("")
    sql_lines.extend([
        "-- ============================================================",
        "-- ALREADY_FULL — DB explanation matches critique PDF; no update needed",
        "-- ============================================================",
    ])
    skipped_full = [r for r in results if r["status"] == "ALREADY_FULL"]
    for r in skipped_full:
        sql_lines.append(
            f"-- ALREADY_FULL {r['qid']}: db_len={r['db_len']}  pdf_len={r['pdf_len']}  diff={r['growth']:+d}"
        )
    if not skipped_full:
        sql_lines.append("-- (none)")
    sql_lines.append("")
    sql_lines.extend([
        "-- ============================================================",
        "-- EXTRACTION_FAIL — could not extract from critique PDF",
        "-- ============================================================",
    ])
    failed = [r for r in results if r["status"] == "EXTRACTION_FAIL"]
    for r in failed:
        sql_lines.append(f"-- EXTRACTION_FAIL {r['qid']}: {r['reason']}")
    if not failed:
        sql_lines.append("-- (none)")
    (OUT_DIR / "a2_updates.sql").write_text("\n".join(sql_lines), encoding="utf-8")

    md_lines = [f"# A2 explanation truncation re-extraction ({len(results)} QIDs)", ""]
    md_lines.append(f"Status distribution: {dict(status_counts)}")
    md_lines.append("")
    for r in results:
        md_lines.append(
            f"## {r['qid']} ({r['year']}_critique.pdf, item {r['item']}) — {r['status']}"
        )
        if r.get("reason"):
            md_lines.append(f"- note: {r['reason']}")
        md_lines.append(f"- DB length: {r['db_len']}")
        if r["pdf_len"] is not None:
            md_lines.append(f"- PDF length: {r['pdf_len']}  (growth: {r['growth']:+d})")
            md_lines.append(f"- DB correct_letter: `{r['db_correct_letter']}`   PDF answer_letter: `{r['pdf_answer_letter']}`")
            if r["status"] == "UPDATE_NEEDED":
                md_lines.append("- **PDF explanation (full):**")
                md_lines.append("")
                md_lines.append("```")
                md_lines.append(r["pdf_explanation"])
                md_lines.append("```")
            else:
                md_lines.append(f"- DB head: `{r['db_explanation_head']}`")
                md_lines.append(f"- DB tail: `{r['db_explanation_tail']}`")
        else:
            md_lines.append(f"- DB head: `{r['db_explanation_head']}`")
            md_lines.append(f"- DB tail: `{r['db_explanation_tail']}`")
        md_lines.append("")
    (OUT_DIR / "a2_preview.md").write_text("\n".join(md_lines), encoding="utf-8")

    print()
    print(f"Artifacts written to: {OUT_DIR.relative_to(PROJECT_ROOT).as_posix()}/")
    print("  - a2_extraction_results.json")
    print("  - a2_updates.sql")
    print("  - a2_preview.md")


if __name__ == "__main__":
    main()
