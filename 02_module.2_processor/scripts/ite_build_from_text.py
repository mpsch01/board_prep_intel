#!/usr/bin/env python3
"""
ite_build_from_text.py

Parses ITE questions from plain text files (as opposed to PDF extraction).
Useful when working from .docx-exported or manually cleaned text.

Usage:
    python ite_build_from_text.py --questions q.txt --answers a.txt --year 2025 --out out.csv

Migrated from TEMP_06_ite_pipeline_TEMP (BATON 007)
"""

import argparse
import re
import csv
from pathlib import Path
from typing import Dict, List

SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent

QHEADER            = re.compile(r'(?m)^\s*(\d{1,4})\s*[\.\)\-:]\s*')
CHOICE_LABEL       = re.compile(r'(?m)^[ \t]*([A-F])[.)][ \t]+(.*)')
EXPLANATION_HEAD   = re.compile(r'(?im)^\s*Explanation\s*[:\-]\s*(.*)$')
CHOICE_INLINE_SPLIT = re.compile(r'\s(?=[A-F][\.\)])')


def normalize(s: str) -> str:
    return re.sub(r'\s+', ' ', s).strip()


def parse_questions(raw: str) -> List[Dict[str, str]]:
    matches = list(QHEADER.finditer(raw))
    questions: List[Dict[str, str]] = []
    for i, m in enumerate(matches):
        qid   = int(m.group(1))
        start = m.end()
        end   = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
        chunk = raw[start:end]

        choice_m = re.search(r'(?m)^[ \t]*[A-F][\.\)]\s+', chunk)
        if choice_m:
            stem         = normalize(chunk[:choice_m.start()])
            choice_region = chunk[choice_m.start():]
        else:
            stem         = normalize(chunk)
            choice_region = ""

        choices     = {k: "" for k in "ABCDEF"}
        explanation = ""

        if choice_region:
            current = None
            buf     = []
            for line in choice_region.splitlines():
                mexp = EXPLANATION_HEAD.match(line)
                if mexp:
                    if current:
                        choices[current] = normalize(" ".join(buf))
                        current = None
                        buf     = []
                    explanation = normalize(mexp.group(1))
                    continue
                mm = CHOICE_LABEL.match(line)
                if mm:
                    if current:
                        choices[current] = normalize(" ".join(buf))
                    current = mm.group(1).upper()
                    buf     = [mm.group(2)]
                else:
                    if current is not None:
                        buf.append(line)
                    else:
                        parts = CHOICE_INLINE_SPLIT.split(line.strip())
                        if len(parts) > 1:
                            for part in parts:
                                mmm = re.match(r'^\s*([A-F])[.)]\s*(.*)$', part)
                                if mmm:
                                    if current:
                                        choices[current] = normalize(" ".join(buf))
                                    current = mmm.group(1).upper()
                                    buf     = [mmm.group(2)]
                        else:
                            if explanation:
                                explanation += " " + line.strip()
                            else:
                                stem += " " + line.strip()
            if current:
                choices[current] = normalize(" ".join(buf))

        q = {"id": str(qid), "stem": stem, "explanation": explanation}
        for L in "ABCDEF":
            q[L] = choices.get(L, "")
        questions.append(q)

    uniq = {}
    for q in questions:
        uniq[int(q["id"])] = q
    return [uniq[k] for k in sorted(uniq.keys())]


def parse_answers(raw: str) -> Dict[int, str]:
    ans      = {}
    token_re = re.compile(r'Item\s+(\d{1,4})|ANSWER:\s*([A-F])', re.IGNORECASE)
    current_item = 1
    for m in token_re.finditer(raw):
        item, letter = m.groups()
        if item:
            current_item = int(item)
        elif letter:
            ans[current_item] = letter.upper()
            current_item += 1
    for m in re.finditer(r'(?m)^\s*(\d{1,4})\s*[\.\)\-:]\s*([A-F])\b', raw):
        ans[int(m.group(1))] = m.group(2).upper()
    return ans


def write_csv(questions, answers, out, year):
    header = ["id", "year", "stem", "A", "B", "C", "D", "E", "F",
              "correct", "explanation", "tags", "confidence"]
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        for q in questions:
            qid = int(q["id"])
            row = {k: q.get(k, "") for k in header}
            row["year"]    = str(year)
            row["correct"] = answers.get(qid, "")
            w.writerow(row)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", required=True)
    ap.add_argument("--answers",   required=True)
    ap.add_argument("--year",      type=int, required=True)
    ap.add_argument("--out",       required=True)
    a  = ap.parse_args()
    qtxt = Path(a.questions).read_text(encoding="utf-8", errors="ignore")
    atxt = Path(a.answers).read_text(encoding="utf-8", errors="ignore")
    qs   = parse_questions(qtxt)
    ans  = parse_answers(atxt)
    write_csv(qs, ans, a.out, a.year)
    print(f"Wrote {len(qs)} rows -> {a.out} (answers parsed: {len(ans)})")


if __name__ == "__main__":
    main()
