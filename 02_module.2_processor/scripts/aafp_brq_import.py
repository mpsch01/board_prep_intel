#!/usr/bin/env python3
"""
AAFP Board Review Questions — DB Import Script
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Reads:   02_module.2_processor/outputs/aafp_brq_staging.json
Writes:  00_database/db/ite_intelligence.db → aafp_questions table

Schema rationale:
  - Separate table from `questions` (different source, different fields)
  - aafp_qid  = "AAFP-{question_id}" (e.g. AAFP-49733) — server-stable PK
  - article_id + match_status for downstream xref linking
  - ref_text preserved raw for re-matching

Matching strategies (in order):
  Strategy 0: exact clean_ref match (case-insensitive)
  Strategy 1: author + year substring match
  Strategy 2: unmatched → left for manual review

Run:
  python aafp_brq_import.py [--dry-run]
  python aafp_brq_import.py --stats     ← QC summary only (no insert)
"""

import re
import json
import sqlite3
import sys
from pathlib import Path

# ══════════════════════════════════════════════════════════════════════
# PATHS
# ══════════════════════════════════════════════════════════════════════
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent

DB_PATH      = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"
STAGING_FILE = PROJECT_ROOT / "01_module.1_warehouse" / "aafp_brq" / "staging" / "aafp_brq_staging.json"
# ══════════════════════════════════════════════════════════════════════

DRY_RUN = "--dry-run" in sys.argv
STATS   = "--stats"   in sys.argv


# ─────────────────────────────────────────────────────────────────────
# SCHEMA
# ─────────────────────────────────────────────────────────────────────
CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS aafp_questions (
    aafp_qid        TEXT PRIMARY KEY,   -- "AAFP-49733"
    question_id     INTEGER UNIQUE,     -- server's internal question ID
    assessment_id   INTEGER,            -- quiz set ID (e.g. 13882)
    quiz_title      TEXT,               -- "Board Review Questions 01"
    question_number INTEGER,            -- 1-10 within quiz
    questions_total INTEGER,            -- 10
    stem            TEXT,               -- question text
    choices         TEXT,               -- JSON array [{value, text}]
    correct_value   TEXT,               -- radio button value of correct answer
    correct_text    TEXT,               -- human-readable correct answer
    explanation     TEXT,               -- explanation (Ref: stripped)
    explanation_html TEXT,              -- raw HTML from AnswerExplanation — preserved for re-extraction
    ref_text        TEXT,               -- raw citation from "Ref:" in explanation
    article_id      TEXT,               -- FK -> articles.article_id (null if unmatched)
    match_status    TEXT DEFAULT 'unmatched',  -- matched/fuzzy/unmatched/no_ref
    url             TEXT                -- source URL
)
"""


# ─────────────────────────────────────────────────────────────────────
# MATCHING
# ─────────────────────────────────────────────────────────────────────
def build_article_index(conn: sqlite3.Connection) -> tuple[dict, list]:
    """
    Returns:
      clean_ref_map: {clean_ref.lower(): article_id}
      author_year_list: [(author1.lower(), year, article_id)]
    """
    cur = conn.cursor()
    cur.execute("SELECT clean_ref, article_id, author1, year FROM articles WHERE article_id IS NOT NULL")
    rows = cur.fetchall()

    clean_ref_map  = {}
    author_year_list = []

    for clean_ref, article_id, author1, year in rows:
        if clean_ref:
            clean_ref_map[clean_ref.lower().strip()] = article_id
        if author1 and year:
            author_year_list.append((author1.lower().strip(), str(year).strip(), article_id))

    return clean_ref_map, author_year_list


def normalize(text: str) -> str:
    """Lowercase, collapse whitespace, strip punctuation for loose matching."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def match_ref(ref_text: str, clean_ref_map: dict, author_year_list: list) -> tuple[str | None, str]:
    """
    Returns (article_id, match_status).
    match_status: 'matched' | 'fuzzy' | 'unmatched'
    """
    if not ref_text or not ref_text.strip():
        return None, "no_ref"

    ref_lower = ref_text.lower().strip()

    # Strategy 0: exact clean_ref match
    if ref_lower in clean_ref_map:
        return clean_ref_map[ref_lower], "matched"

    # Strategy 1: author + year substring
    # Extract year from ref_text (4-digit number)
    year_match = re.search(r"\b(20\d{2}|19\d{2})\b", ref_text)
    if year_match:
        ref_year = year_match.group(1)
        # Extract first word (author surname) — first token before comma or space
        first_token = re.split(r"[,\s]", ref_text.strip())[0].lower()
        if first_token and len(first_token) >= 3:
            for (author1, year, article_id) in author_year_list:
                if year == ref_year and author1.startswith(first_token[:4]):
                    return article_id, "fuzzy"

    return None, "unmatched"


# ─────────────────────────────────────────────────────────────────────
# IMPORT
# ─────────────────────────────────────────────────────────────────────
def run_import():
    if not STAGING_FILE.exists():
        print(f"ERROR: Staging file not found:\n  {STAGING_FILE}")
        print("Run aafp_brq_scraper.py --scrape first.")
        sys.exit(1)

    if not DB_PATH.exists():
        print(f"ERROR: DB not found:\n  {DB_PATH}")
        sys.exit(1)

    print(f"Loading staging file...")
    with open(STAGING_FILE, encoding="utf-8") as f:
        records = json.load(f)
    print(f"  {len(records)} records loaded")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Create table
    conn.execute(CREATE_TABLE)
    conn.commit()

    # Build article index for matching
    print(f"Building article index for ref matching...")
    clean_ref_map, author_year_list = build_article_index(conn)
    print(f"  {len(clean_ref_map)} articles indexed")

    # Stats counters
    stats = {
        "total":     len(records),
        "inserted":  0,
        "skipped":   0,    # already exists
        "matched":   0,
        "fuzzy":     0,
        "unmatched": 0,
        "no_ref":    0,
    }

    rows_to_insert = []

    for rec in records:
        qid      = rec.get("question_id")
        aafp_qid = f"AAFP-{qid}"

        ref_text = rec.get("ref_text", "") or ""
        article_id, match_status = match_ref(ref_text, clean_ref_map, author_year_list)

        stats[match_status] = stats.get(match_status, 0) + 1

        rows_to_insert.append({
            "aafp_qid":        aafp_qid,
            "question_id":     qid,
            "assessment_id":   rec.get("assessment_id"),
            "quiz_title":      rec.get("quiz_title", ""),
            "question_number": rec.get("question_number"),
            "questions_total": rec.get("questions_total"),
            "stem":            rec.get("stem", ""),
            "choices":         json.dumps(rec.get("choices", []), ensure_ascii=False),
            "correct_value":   rec.get("correct_value", ""),
            "correct_text":    rec.get("correct_text", ""),
            "explanation":      rec.get("explanation", ""),
            "explanation_html": rec.get("explanation_html", ""),
            "ref_text":         ref_text,
            "article_id":      article_id,
            "match_status":    match_status,
            "url":             rec.get("url", ""),
        })

    if STATS or DRY_RUN:
        print_stats(stats, records)
        if DRY_RUN:
            print("\n[DRY RUN — no changes written]")
        return

    # Insert with OR IGNORE (skip existing rows)
    inserted = 0
    skipped  = 0

    for row in rows_to_insert:
        cur = conn.execute(
            """INSERT OR IGNORE INTO aafp_questions
               (aafp_qid, question_id, assessment_id, quiz_title,
                question_number, questions_total, stem, choices,
                correct_value, correct_text, explanation, explanation_html,
                ref_text, article_id, match_status, url)
               VALUES (:aafp_qid, :question_id, :assessment_id, :quiz_title,
                       :question_number, :questions_total, :stem, :choices,
                       :correct_value, :correct_text, :explanation, :explanation_html,
                       :ref_text, :article_id, :match_status, :url)""",
            row
        )
        if cur.rowcount:
            inserted += 1
        else:
            skipped += 1

    conn.commit()
    conn.close()

    stats["inserted"] = inserted
    stats["skipped"]  = skipped

    print_stats(stats, records)
    print(f"\n  Inserted: {inserted}  |  Already existed (skipped): {skipped}")
    print(f"  DB → {DB_PATH}")


def print_stats(stats: dict, records: list):
    total       = stats["total"]
    matched     = stats.get("matched",   0)
    fuzzy       = stats.get("fuzzy",     0)
    unmatched   = stats.get("unmatched", 0)
    no_ref      = stats.get("no_ref",    0)
    no_correct  = sum(1 for r in records if not r.get("correct_value"))

    print(f"\n══ IMPORT QC ═══════════════════════════════════════════════")
    print(f"  Questions total:       {total}")
    print(f"  Quizzes (10 per):      {total // 10}")
    print(f"")
    print(f"  correct_value found:   {total - no_correct}/{total}  ({pct(total-no_correct, total)}%)")
    print(f"  ref_text present:      {total - no_ref}/{total}  ({pct(total-no_ref, total)}%)")
    print(f"")
    print(f"  — matched (exact):     {matched}  ({pct(matched, total)}%)")
    print(f"  — fuzzy (author+yr):   {fuzzy}  ({pct(fuzzy, total)}%)")
    print(f"  — unmatched:           {unmatched}  ({pct(unmatched, total)}%)")
    print(f"  — no_ref:              {no_ref}  ({pct(no_ref, total)}%)")

    # Show sample unmatched refs for inspection
    unmatched_refs = [r["ref_text"] for r in records
                      if r.get("ref_text") and not r.get("article_id")]
    if unmatched_refs:
        print(f"\n  Sample unmatched refs (first 10):")
        for ref in unmatched_refs[:10]:
            print(f"    · {ref[:100]}")


def pct(n: int, total: int) -> str:
    if total == 0:
        return "0"
    return f"{n/total*100:.1f}"


# ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if "--help" in sys.argv:
        print(__doc__)
        sys.exit(0)
    run_import()
