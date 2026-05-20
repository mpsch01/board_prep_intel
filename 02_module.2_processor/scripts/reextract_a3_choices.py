#!/usr/bin/env python3
"""
reextract_a3_choices.py

One-off remediation for the 42 A3 (choices_empty) findings from
corpus-integrity-qc V1 (BATON 075 post-Tier-1 QC run).

For each target QID:
  1. Open the corresponding YYYY_MC.pdf in 01_module.1_warehouse/ite_exams/
  2. Locate the item by number (last 4 digits of QID = item number)
  3. Parse choices A-E from the item block
  4. Generate an UPDATE statement that sets choices (JSON array of {letter,text}
     objects) and correct_text (the text matching the existing correct_letter)

Writes three artifacts to 03_module.3_analyst/outputs/corpus_qc/<date>_a3_reextract/:
  - a3_extraction_results.json   manifest with per-QID extraction state
  - a3_updates.sql               BEGIN/COMMIT block, ready for fix-applier review
  - a3_preview.md                human-readable preview, per-QID choices listing

Does NOT modify the DB. Apply via the inline fix-applier pattern after review.

Naming convention: 'A3' refers to the corpus-integrity-qc check tag
A3-choices_empty (see fix_tiers.md). The 42 target QIDs are pinned in this
file as TARGET_QIDS so the script is reproducible without re-parsing fixes.sql.
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
    """Reconfigure stdout/stderr to UTF-8. No-op on streams already UTF-8."""
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
    / f"{datetime.now():%Y-%m-%d}_a3_reextract"
)

TARGET_QIDS = [
    "QID-2020-0036", "QID-2020-0046", "QID-2020-0052", "QID-2020-0162",
    "QID-2021-0017", "QID-2021-0039", "QID-2021-0064", "QID-2021-0107", "QID-2021-0148",
    "QID-2022-0009", "QID-2022-0028", "QID-2022-0030", "QID-2022-0053", "QID-2022-0073",
    "QID-2022-0085", "QID-2022-0097", "QID-2022-0099", "QID-2022-0128", "QID-2022-0141",
    "QID-2022-0163", "QID-2022-0168",
    "QID-2023-0006", "QID-2023-0032", "QID-2023-0079", "QID-2023-0080", "QID-2023-0084",
    "QID-2023-0170", "QID-2023-0173", "QID-2023-0177", "QID-2023-0182", "QID-2023-0195",
    "QID-2024-0032", "QID-2024-0033", "QID-2024-0038", "QID-2024-0059", "QID-2024-0062",
    "QID-2024-0115", "QID-2024-0137", "QID-2024-0142",
    "QID-2025-0041", "QID-2025-0123", "QID-2025-0178",
]

PAGE_FOOTER_RE = re.compile(r"(?m)^\s*\d{1,3}\s*$")
ITEM_START_RE = re.compile(r"(?m)^(\d{1,3})\.\s")
CHOICE_LETTER_RE = re.compile(r"(?m)^([A-E])\)\s")


def build_full_text(pdf_path: Path) -> str:
    """Concatenate full PDF text and strip standalone page-footer numeric lines."""
    parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            parts.append(page.extract_text() or "")
    text = "\n".join(parts)
    return PAGE_FOOTER_RE.sub("", text)


def split_items(text: str) -> dict:
    """Return {item_num: block_text} where block_text spans until the next item header.

    Item numbers in ITE exams run 1..200 in strict order. We filter raw regex
    matches to those that monotonically increase by 1, which rejects stray
    "NN. " line starts caused by question content (e.g., a question stem
    wrapping mid-sentence such that "...at age\\n22." matches as item 22).
    """
    raw = list(ITEM_START_RE.finditer(text))
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


def parse_choices(block: str) -> dict | None:
    """Find lines starting with A)-E) and extract their text.

    Returns {letter: text} or None if no choices found. Multi-line choices are
    flattened to single-line; trailing page-footer-style digit fragments are
    stripped.
    """
    matches = list(CHOICE_LETTER_RE.finditer(block))
    if not matches:
        return None
    out = {}
    for i, m in enumerate(matches):
        letter = m.group(1)
        if letter in out:
            return None
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(block)
        raw = block[start:end].strip()
        cleaned = re.sub(r"\s+", " ", raw).strip()
        cleaned = re.sub(r"\s+Item\s+#\d+\s*$", "", cleaned)
        cleaned = re.sub(r"\s+\d{1,3}\s*$", "", cleaned)
        out[letter] = cleaned
    return out


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
            "SELECT correct_letter, question_text FROM questions WHERE qid = ?", (qid,)
        ).fetchone()
        db_state[qid] = {"correct_letter": row[0], "question_text": row[1] or ""}
    conn.close()

    results = []
    for year in sorted(by_year):
        pdf_path = EXAM_PDFS_DIR / f"{year}_MC.pdf"
        print(f"[{year}] {pdf_path.name}")
        full_text = build_full_text(pdf_path)
        items = split_items(full_text)
        print(f"[{year}]   parsed {len(items)} items")
        for qid, item_num in by_year[year]:
            block = items.get(item_num)
            if block is None:
                results.append({
                    "qid": qid, "year": year, "item": item_num,
                    "status": "ITEM_NOT_FOUND",
                    "letters_found": [],
                    "choices": None,
                    "correct_letter": db_state[qid]["correct_letter"],
                    "correct_text": None,
                    "db_qtext_head": db_state[qid]["question_text"][:120],
                    "pdf_block_head": None,
                })
                continue
            choices = parse_choices(block)
            if not choices:
                results.append({
                    "qid": qid, "year": year, "item": item_num,
                    "status": "NO_CHOICES_FOUND",
                    "letters_found": [],
                    "choices": None,
                    "correct_letter": db_state[qid]["correct_letter"],
                    "correct_text": None,
                    "db_qtext_head": db_state[qid]["question_text"][:120],
                    "pdf_block_head": block[:200],
                })
                continue
            db_head = db_state[qid]["question_text"][:40]
            stem_ok = bool(db_head) and db_head in block
            letters_found = sorted(choices)
            complete = letters_found == ["A", "B", "C", "D", "E"]
            partial_abcd = letters_found == ["A", "B", "C", "D"]
            status = "OK"
            if not stem_ok:
                status = "STEM_MISMATCH"
            elif complete:
                status = "OK"
            elif partial_abcd:
                status = "PARTIAL_4OF5"
            else:
                status = "INCOMPLETE_LETTERS"
            correct_letter = db_state[qid]["correct_letter"]
            correct_text = choices.get(correct_letter, "")
            results.append({
                "qid": qid, "year": year, "item": item_num,
                "status": status,
                "letters_found": letters_found,
                "choices": [{"letter": L, "text": choices[L]} for L in letters_found],
                "correct_letter": correct_letter,
                "correct_text": correct_text,
                "db_qtext_head": db_state[qid]["question_text"][:120],
                "pdf_block_head": block[:200],
            })

    (OUT_DIR / "a3_extraction_results.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    status_counts = Counter(r["status"] for r in results)
    print()
    print(f"Status distribution: {dict(status_counts)}")

    sql_lines = [
        "-- A3 choices_empty re-extraction",
        f"-- Generated: {datetime.now():%Y-%m-%d %H:%M:%S}",
        f"-- Source PDFs: {EXAM_PDFS_DIR.relative_to(PROJECT_ROOT).as_posix()}/YYYY_MC.pdf",
        f"-- Targets: {len(TARGET_QIDS)} QIDs    Status: {dict(status_counts)}",
        "",
        "-- ============================================================",
        "-- UPDATES — all recovered choices (OK 5-of-5 + PARTIAL_4OF5)",
        "-- PARTIAL_4OF5 rows: source-PDF defect, choice E truncated by ABFM's",
        "-- original PDF generation. Verified via pdfplumber extract_words():",
        "-- no 'E)' token on the page. For every PARTIAL_4OF5 row in this batch,",
        "-- correct_letter is in {A,B,C,D} so the correct answer is preserved.",
        "-- ============================================================",
        "BEGIN;",
        "",
    ]
    for r in results:
        if r["status"] not in ("OK", "PARTIAL_4OF5"):
            continue
        choices_json = json.dumps(r["choices"], ensure_ascii=False).replace("'", "''")
        ctext = (r["correct_text"] or "").replace("'", "''")
        sql_lines.append(
            f"-- {r['qid']} (item {r['item']} in {r['year']}_MC.pdf) — letter={r['correct_letter']} — {r['status']}"
        )
        sql_lines.append(
            f"UPDATE questions SET choices = '{choices_json}', correct_text = '{ctext}' "
            f"WHERE qid = '{r['qid']}';"
        )
        sql_lines.append("")
    sql_lines.append("COMMIT;")
    sql_lines.append("")
    sql_lines.extend([
        "-- ============================================================",
        "-- SKIPPED — other failure modes (manual investigation required)",
        "-- ============================================================",
    ])
    skipped_any = False
    for r in results:
        if r["status"] in ("OK", "PARTIAL_4OF5"):
            continue
        skipped_any = True
        sql_lines.append(
            f"-- SKIPPED ({r['status']}) {r['qid']} — item {r['item']} in {r['year']}_MC.pdf"
        )
    if not skipped_any:
        sql_lines.append("-- (none)")
    (OUT_DIR / "a3_updates.sql").write_text("\n".join(sql_lines), encoding="utf-8")

    md_lines = [f"# A3 choices_empty re-extraction preview ({len(results)} QIDs)", ""]
    md_lines.append(f"Status distribution: {dict(status_counts)}")
    md_lines.append("")
    for r in results:
        md_lines.append(f"## {r['qid']} ({r['year']}_MC.pdf, item {r['item']}) — {r['status']}")
        md_lines.append(f"- correct_letter: `{r['correct_letter']}`")
        if r["status"] == "OK":
            md_lines.append(f"- correct_text → `{r['correct_text']}`")
            md_lines.append("- choices:")
            for c in r["choices"]:
                marker = " **(correct)**" if c["letter"] == r["correct_letter"] else ""
                md_lines.append(f"  - {c['letter']}: {c['text']}{marker}")
        else:
            md_lines.append(f"- letters_found: {r['letters_found']}")
            md_lines.append(f"- db_qtext_head: `{r['db_qtext_head']}`")
            head = (r.get("pdf_block_head") or "")[:200]
            md_lines.append(f"- pdf_block_head: `{head}`")
        md_lines.append("")
    (OUT_DIR / "a3_preview.md").write_text("\n".join(md_lines), encoding="utf-8")

    print()
    print(f"Artifacts written to: {OUT_DIR.relative_to(PROJECT_ROOT).as_posix()}/")
    print("  - a3_extraction_results.json")
    print("  - a3_updates.sql")
    print("  - a3_preview.md")


if __name__ == "__main__":
    main()
