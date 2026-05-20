#!/usr/bin/env python3
"""
render_partial_4of5_docx.py

One-off — renders the 15 PARTIAL_4OF5 QIDs (the BATON 076 A3-source-PDF-missing-E
set) into both Exam and Study Guide DOCX form, using the existing
build_exam_docx / build_study_guide_docx helpers from
03_module.3_analyst/scripts/build_custom_question_set.py.

Purpose: visual verification that the second-level renderer produces no
orphan letters, dangling text, empty A/B/C/D/E slots, or other artifacts
for the 15 partial questions.

Output:
  03_module.3_analyst/custom_question_sets/<date>/
    QSet_15Q_PARTIAL_4of5_Exam.docx
    QSet_15Q_PARTIAL_4of5_StudyGuide.docx
"""

import io
import sys
import sqlite3
from datetime import date
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"
M3_SCRIPTS_DIR = PROJECT_ROOT / "03_module.3_analyst" / "scripts"
OUT_DIR = PROJECT_ROOT / "03_module.3_analyst" / "custom_question_sets" / date.today().isoformat()


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


PARTIAL_QIDS = [
    "QID-2020-0162",
    "QID-2021-0017", "QID-2021-0064", "QID-2021-0107",
    "QID-2022-0009", "QID-2022-0053", "QID-2022-0097",
    "QID-2023-0006", "QID-2023-0182",
    "QID-2024-0033", "QID-2024-0038", "QID-2024-0137", "QID-2024-0142",
    "QID-2025-0041", "QID-2025-0123",
]


def main() -> None:
    setup_utf8_stdout()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Import builders from build_custom_question_set
    sys.path.insert(0, str(M3_SCRIPTS_DIR))
    from build_custom_question_set import (
        clean_text,
        clean_choices,
        build_exam_docx,
        build_study_guide_docx,
    )

    placeholders = ",".join("?" * len(PARTIAL_QIDS))
    sql = (
        "SELECT qid, question_text, choices, correct_letter, correct_text, "
        "       explanation, blueprint, body_system, exam_year, 'ITE' AS source_bank "
        f"FROM questions WHERE qid IN ({placeholders}) "
        "ORDER BY exam_year, qid"
    )
    con = sqlite3.connect(str(DB_PATH))
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute(sql, PARTIAL_QIDS)
    questions = []
    for row in cur.fetchall():
        d = dict(row)
        d["question_text"] = clean_text(d.get("question_text"))
        d["explanation"] = clean_text(d.get("explanation"))
        d["choices"] = clean_choices(d.get("choices"))
        questions.append(d)
    con.close()

    print(f"Fetched {len(questions)} questions")
    for q in questions:
        n = len(q["choices"]) if isinstance(q["choices"], dict) else 0
        print(f"  {q['qid']}: {n} choices  correct={q['correct_letter']}")

    label = "PARTIAL_4of5_audit"
    filter_summary = "BATON 076 A3 PARTIAL_4OF5 visual-render audit (15 QIDs)"
    exam_path = OUT_DIR / f"QSet_{len(questions)}Q_{label}_Exam.docx"
    guide_path = OUT_DIR / f"QSet_{len(questions)}Q_{label}_StudyGuide.docx"

    print()
    print("Building Exam DOCX...")
    build_exam_docx(questions, exam_path, label, filter_summary)
    print(f"  -> {exam_path}")
    print("Building Study Guide DOCX...")
    build_study_guide_docx(questions, guide_path, label, filter_summary)
    print(f"  -> {guide_path}")
    print()
    print(f"Output dir: {OUT_DIR.relative_to(PROJECT_ROOT).as_posix()}")


if __name__ == "__main__":
    main()
