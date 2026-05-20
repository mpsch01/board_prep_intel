#!/usr/bin/env python3
"""
clean_question_text_contamination.py

Strips four categories of ingestion-time contamination from
questions.question_text:

  1. EMBEDDED_CHOICE_BLOCK — full choice block (inline `A) text\\nB) text\\n...`
     or empty slots `A) \\nB) \\nC) \\nD) \\nE)`) appended to the stem.
  2. TRAIL_ITEM_HDR — running header "Item #NN" leaking into stem
  3. TRAIL_DIGIT — trailing isolated digit (page footer leak)
  4. TRAIL_WHITESPACE — trailing whitespace/newlines

The cleanup is conservative: it only truncates AT or AFTER the first answer-
choice boundary (line-start `A) ` or post-`?` ` A) `). Body text never
contains a bare `A) ` outside the answer-choice context, so this is safe.

Writes preview + SQL to:
  03_module.3_analyst/outputs/corpus_qc/<date>_qtext_cleanup/

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
    / f"{datetime.now():%Y-%m-%d}_qtext_cleanup"
)

# Match the first answer-choice boundary. The 'lead' group captures the
# preceding whitespace (and an optional `?` so we know whether to preserve it).
# Cases:
#   "stem?\nA) ..."  → lead='?\n', preserve the '?'
#   "stem text\nA) ..."  → lead='\n', drop everything from the newline
#   "stem (NNT)? A) <1 ..."  → lead='? ', preserve the '?'
CHOICE_BOUNDARY_RE = re.compile(r"(?m)(?P<lead>(?:^|\n|\?)\s*)A\)\s")

# Trailing residue patterns to strip after stem truncation.
TRAIL_ITEM_HDR_RE = re.compile(r"\s*Item\s+#\d+\s*$", re.IGNORECASE)
TRAIL_DIGIT_RE = re.compile(r"\s+\d{1,3}\s*$")


def clean_qtext(qtext: str) -> tuple[str, list[str]]:
    """Return (cleaned, list-of-actions). Actions describe what was stripped."""
    if not qtext:
        return qtext, []

    actions = []
    out = qtext

    # 1. Truncate at first A) boundary, preserving a trailing `?` if present.
    m = CHOICE_BOUNDARY_RE.search(out)
    if m:
        cut = m.start("lead")
        # If 'lead' begins with '?', keep the '?' by advancing the cut past it.
        if cut < len(out) and out[cut] == "?":
            cut += 1
        dropped = len(out) - cut
        actions.append(f"truncated_choice_block (at pos {cut}, dropped {dropped} chars)")
        out = out[:cut]

    # 2. Strip trailing Item #NN residue iteratively.
    changed = True
    while changed:
        changed = False
        new = TRAIL_ITEM_HDR_RE.sub("", out)
        if new != out:
            actions.append("stripped_item_hdr")
            out = new
            changed = True
        new = TRAIL_DIGIT_RE.sub("", out)
        if new != out:
            actions.append("stripped_trail_digit")
            out = new
            changed = True

    # 3. Strip trailing whitespace.
    stripped = out.rstrip()
    if stripped != out:
        actions.append("stripped_trail_whitespace")
        out = stripped

    return out, actions


def main() -> None:
    setup_utf8_stdout()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT qid, exam_year, question_text FROM questions ORDER BY qid"
    ).fetchall()
    conn.close()

    results = []
    for qid, year, qtext in rows:
        original = qtext or ""
        cleaned, actions = clean_qtext(original)
        if cleaned != original:
            results.append({
                "qid": qid,
                "year": year,
                "actions": actions,
                "original_len": len(original),
                "cleaned_len": len(cleaned),
                "delta": len(cleaned) - len(original),
                "original_tail": original[-200:],
                "cleaned_tail": cleaned[-200:],
                "cleaned": cleaned,
            })

    print(f"Total questions scanned: {len(rows)}")
    print(f"Questions needing cleanup: {len(results)}")
    if results:
        action_counts = Counter()
        for r in results:
            for a in r["actions"]:
                action_counts[a.split(" ")[0]] += 1
        print()
        print("Action distribution:")
        for a, n in action_counts.most_common():
            print(f"  {a:<32s} {n}")

    (OUT_DIR / "qtext_cleanup_results.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    sql_lines = [
        "-- question_text contamination cleanup",
        f"-- Generated: {datetime.now():%Y-%m-%d %H:%M:%S}",
        f"-- Targets: {len(results)} QIDs",
        "",
        "BEGIN;",
        "",
    ]
    for r in results:
        cleaned_sql = r["cleaned"].replace("'", "''")
        sql_lines.append(
            f"-- {r['qid']} ({r['year']}) delta={r['delta']:+d} actions={r['actions']}"
        )
        sql_lines.append(
            f"UPDATE questions SET question_text = '{cleaned_sql}' WHERE qid = '{r['qid']}';"
        )
        sql_lines.append("")
    sql_lines.append("COMMIT;")
    sql_lines.append("")
    (OUT_DIR / "qtext_cleanup.sql").write_text("\n".join(sql_lines), encoding="utf-8")

    md_lines = [
        f"# question_text cleanup preview ({len(results)} QIDs)",
        "",
        f"Action distribution: {dict(action_counts) if results else {}}",
        "",
    ]
    for r in results[:30]:  # cap preview to first 30
        md_lines.append(f"## {r['qid']} ({r['year']}) — actions: {r['actions']}")
        md_lines.append(f"- length: {r['original_len']} → {r['cleaned_len']}  (delta {r['delta']:+d})")
        md_lines.append(f"- original tail:")
        md_lines.append("```")
        md_lines.append(r["original_tail"])
        md_lines.append("```")
        md_lines.append(f"- cleaned tail:")
        md_lines.append("```")
        md_lines.append(r["cleaned_tail"])
        md_lines.append("```")
        md_lines.append("")
    if len(results) > 30:
        md_lines.append(f"_(showing first 30 of {len(results)} — see qtext_cleanup_results.json for full set)_")
    (OUT_DIR / "qtext_cleanup_preview.md").write_text("\n".join(md_lines), encoding="utf-8")

    print()
    print(f"Artifacts: {OUT_DIR.relative_to(PROJECT_ROOT).as_posix()}/")
    print("  - qtext_cleanup_results.json")
    print("  - qtext_cleanup.sql")
    print("  - qtext_cleanup_preview.md")


if __name__ == "__main__":
    main()
