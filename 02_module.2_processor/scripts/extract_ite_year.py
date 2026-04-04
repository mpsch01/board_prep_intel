#!/usr/bin/env python3
"""
extract_ite_year.py
===================
Extracts ITE exam questions from ABFM-provided PDFs and inserts directly
into ite_intelligence.db. QID is assigned at the moment of extraction —
everything downstream uses QID-YYYY-NNNN from the first write.

Replaces the CSV-intermediate pipeline (01_ite_extractor → 02_ite_categorizer →
03_ite_merger). CSVs are now generated on demand as derived exports.

Source PDFs expected in:
    01_module.1_warehouse/ite_source/
        {YEAR}_ITE_Questions.pdf
        {YEAR}_ITE_Critique.pdf

    PDFs land in M1 (warehouse) first — always. M2 reads from M1.

Usage:
    python extract_ite_year.py --year 2026
    python extract_ite_year.py --year 2026 --dry-run

Pass 1 — Questions PDF:
    Extracts: question stems, A-E answer choices
    Assigns: QID-YYYY-NNNN immediately on parse
    Writes:   questions table (qid, exam_year, question_text, choices)

Pass 2 — Critique PDF:
    Extracts: correct letter, correct text, explanation, citation strings
    Writes:   questions table (correct_letter, correct_text, explanation, reference)
              question_ref_pairs (one row per citation, match_status='pending')

Downstream (run after this script):
    classify_ite_year.py --year YYYY   → body_system (SBERT + XGBoost)
    blueprint_api_classifier_v2.py     → blueprint (API, NULL rows only)
    unified_keyword_extractor.py       → stem/explanation keywords
    build_ite_question_icd10.py        → ICD-10 linkage
    compute_embeddings.py --new-only   → question_vec
"""

import re
import json
import sqlite3
import argparse
import pdfplumber
from pathlib import Path
from datetime import datetime, timezone

# ── Paths ────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
ITE_SOURCE   = PROJECT_ROOT / "01_module.1_warehouse" / "ite_source"
DB_PATH      = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"
LOG_DIR      = PROJECT_ROOT / "00_database" / "logs"

# ── Regex patterns ───────────────────────────────────────────────────────────
Q_HEADER_RE  = re.compile(r'^(\d{1,3})\.\s+(.*)')        # "1. Question stem..."
CHOICE_RE    = re.compile(r'^([A-E])[)\.]\s+(.*)')        # "A) Choice text"
ITEM_RE      = re.compile(r'^Item\s+(\d+)\s*$')           # "Item 1"
ANSWER_RE    = re.compile(r'^ANSWER:\s*([A-E])')          # "ANSWER: C"
REF_NUM_RE   = re.compile(r'^\d+\.\s+.{10,}')             # "1. Author et al..."
FOOTER_RE    = re.compile(r'^\d{4}\s+ITE\s+RATIONALE', re.IGNORECASE)


def make_qid(year: str, item_num: int) -> str:
    """Canonical QID format: QID-2026-0001"""
    return f"QID-{year}-{item_num:04d}"


# ── Pass 1: Questions PDF ────────────────────────────────────────────────────

def parse_questions_pdf(pdf_path: Path, year: str) -> dict:
    """
    Returns dict keyed by item_number (int):
        {stem: str, choices: [{letter, text}, ...]}
    QID is not assigned here — assigned at INSERT time to keep this pure.
    """
    questions = {}   # item_num (int) -> {stem, choices}
    current_num  = None
    current_stem = []
    current_choices = []
    in_choices = False

    print(f"  [Pass 1] Reading: {pdf_path.name}")
    if not pdf_path.exists():
        print(f"  ERROR: Not found: {pdf_path}")
        return {}

    lines = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                lines.extend(text.splitlines())

    def save_current():
        if current_num is not None:
            questions[current_num] = {
                "stem":    " ".join(current_stem).strip(),
                "choices": list(current_choices),
            }

    for line in lines:
        text = line.strip()
        if not text:
            continue

        # New question header
        m = Q_HEADER_RE.match(text)
        if m:
            save_current()
            current_num    = int(m.group(1))
            current_stem   = [m.group(2).strip()]
            current_choices = []
            in_choices      = False
            continue

        if current_num is None:
            continue

        # Answer choice line
        c = CHOICE_RE.match(text)
        if c:
            in_choices = True
            current_choices.append({"letter": c.group(1), "text": c.group(2).strip()})
            continue

        # Continuation line — stem or last-choice overflow
        if in_choices and current_choices:
            # Append to last choice
            current_choices[-1]["text"] += " " + text
        else:
            current_stem.append(text)

    save_current()
    print(f"  [Pass 1] Extracted {len(questions)} questions")
    return questions


# ── Pass 2: Critique PDF ─────────────────────────────────────────────────────

def parse_critique_pdf(pdf_path: Path, year: str) -> dict:
    """
    Returns dict keyed by item_number (int):
        {correct_letter, explanation, citations: [str, ...]}
    """
    critiques    = {}   # item_num -> {correct_letter, explanation, citations}
    current_num  = None
    in_refs      = False
    expl_lines   = []
    ref_lines    = []

    print(f"  [Pass 2] Reading: {pdf_path.name}")
    if not pdf_path.exists():
        print(f"  ERROR: Not found: {pdf_path}")
        return {}

    lines = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                lines.extend(text.splitlines())

    def save_current():
        if current_num is not None:
            critiques[current_num] = {
                "correct_letter": critiques.get(current_num, {}).get("correct_letter", ""),
                "explanation":    " ".join(expl_lines).strip(),
                "citations":      [r.strip() for r in ref_lines if r.strip()],
            }

    for line in lines:
        text = line.strip()
        if not text:
            continue
        if FOOTER_RE.match(text):
            continue

        # New item block
        m = ITEM_RE.match(text)
        if m:
            save_current()
            current_num = int(m.group(1))
            critiques[current_num] = {"correct_letter": "", "explanation": "", "citations": []}
            in_refs    = False
            expl_lines = []
            ref_lines  = []
            continue

        if current_num is None:
            continue

        # Answer line
        a = ANSWER_RE.match(text)
        if a:
            critiques[current_num]["correct_letter"] = a.group(1)
            continue

        # References section marker
        if text.lower() == "references":
            in_refs = True
            continue

        if in_refs:
            # Accumulate reference lines — could span multiple lines
            if REF_NUM_RE.match(text):
                ref_lines.append(text)
            elif ref_lines:
                # Continuation of previous ref
                ref_lines[-1] += " " + text
        else:
            expl_lines.append(text)

    save_current()
    print(f"  [Pass 2] Extracted critiques for {len(critiques)} items")
    return critiques


# ── DB Insert ────────────────────────────────────────────────────────────────

def check_existing(conn: sqlite3.Connection, year: str) -> int:
    """Returns count of existing questions for this year."""
    cur = conn.execute(
        "SELECT COUNT(*) FROM questions WHERE exam_year = ?", (int(year),)
    )
    return cur.fetchone()[0]


def insert_year(conn: sqlite3.Connection, year: str,
                questions: dict, critiques: dict,
                dry_run: bool = False) -> dict:
    """
    Assigns QID at insert time. Inserts into questions and question_ref_pairs.
    Returns summary counts.
    """
    counts = {"inserted": 0, "ref_pairs": 0, "skipped": 0, "warnings": []}
    cur    = conn.cursor()

    for item_num in sorted(questions.keys()):
        q    = questions[item_num]
        crit = critiques.get(item_num, {})

        stem = q.get("stem", "").strip()
        if not stem:
            counts["skipped"] += 1
            counts["warnings"].append(f"Item {item_num}: empty stem — skipped")
            continue

        # ── QID assigned here ────────────────────────────────────────────────
        qid = make_qid(year, item_num)

        choices_json  = json.dumps(q.get("choices", []))
        correct_letter = crit.get("correct_letter", "")
        explanation   = crit.get("explanation", "")
        citations     = crit.get("citations", [])

        # Derive correct_text from choices + correct_letter
        correct_text = ""
        for choice in q.get("choices", []):
            if choice["letter"] == correct_letter:
                correct_text = choice["text"]
                break

        # Primary reference (first citation) stored in questions.reference
        primary_ref = citations[0] if citations else ""

        if not dry_run:
            cur.execute("""
                INSERT OR IGNORE INTO questions
                    (qid, exam_year, question_text, choices,
                     correct_letter, correct_text, explanation, reference)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (qid, int(year), stem, choices_json,
                  correct_letter, correct_text, explanation, primary_ref))

        counts["inserted"] += 1

        # ── question_ref_pairs: one row per citation ─────────────────────────
        for ref_idx, raw_citation in enumerate(citations, start=1):
            if not raw_citation.strip():
                continue
            if not dry_run:
                cur.execute("""
                    INSERT INTO question_ref_pairs
                        (qid, ref_raw, ref_index, match_status, exam_year)
                    VALUES (?, ?, ?, 'pending', ?)
                """, (qid, raw_citation.strip(), ref_idx, int(year)))
            counts["ref_pairs"] += 1

        if not crit:
            counts["warnings"].append(f"{qid}: no critique data found")

    if not dry_run:
        conn.commit()

    return counts


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description="Extract ITE exam PDFs directly into ite_intelligence.db"
    )
    ap.add_argument("--year",    required=True, help="Exam year, e.g. 2026")
    ap.add_argument("--dry-run", action="store_true",
                    help="Parse PDFs and report counts — no DB writes")
    args = ap.parse_args()
    year = args.year

    q_pdf = ITE_SOURCE / f"{year}_ITE_Questions.pdf"
    c_pdf = ITE_SOURCE / f"{year}_ITE_Critique.pdf"

    print(f"\n{'='*60}")
    print(f"  extract_ite_year.py  |  Year: {year}  |  dry-run: {args.dry_run}")
    print(f"{'='*60}")
    print(f"  DB:       {DB_PATH}")
    print(f"  Q PDF:    {q_pdf}")
    print(f"  Critique: {c_pdf}\n")

    # ── Guard: check for existing data ───────────────────────────────────────
    conn = sqlite3.connect(DB_PATH)
    existing = check_existing(conn, year)
    if existing > 0 and not args.dry_run:
        print(f"  WARNING: {existing} questions for {year} already in DB.")
        print("  Use --dry-run to inspect, or manually clear before re-running.")
        conn.close()
        return

    # ── Parse ────────────────────────────────────────────────────────────────
    questions = parse_questions_pdf(q_pdf, year)
    critiques = parse_critique_pdf(c_pdf, year)

    if not questions:
        print("\n  ERROR: No questions extracted. Check PDF path and format.")
        conn.close()
        return

    # Coverage check
    q_set = set(questions.keys())
    c_set = set(critiques.keys())
    unmatched = q_set - c_set
    if unmatched:
        print(f"\n  WARNING: {len(unmatched)} questions have no critique match: "
              f"{sorted(unmatched)[:10]}{'...' if len(unmatched) > 10 else ''}")

    # ── Insert ───────────────────────────────────────────────────────────────
    print(f"\n  {'[DRY RUN] ' if args.dry_run else ''}Inserting into DB...")
    counts = insert_year(conn, year, questions, critiques, dry_run=args.dry_run)
    conn.close()

    # ── Log ──────────────────────────────────────────────────────────────────
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    log_path = LOG_DIR / f"extract_ite_year_{year}_{ts}.json"
    log_data = {
        "script":    "extract_ite_year.py",
        "year":      year,
        "dry_run":   args.dry_run,
        "timestamp": ts,
        "counts":    counts,
        "next_steps": [
            f"classify_ite_year.py --year {year}   → body_system",
            "blueprint_api_classifier_v2.py        → blueprint",
            "unified_keyword_extractor.py          → keywords",
            "build_ite_question_icd10.py           → ICD-10",
            "compute_embeddings.py --new-only      → question_vec",
        ]
    }
    if not args.dry_run:
        import json as _json
        log_path.write_text(_json.dumps(log_data, indent=2))
        print(f"\n  Log: {log_path.name}")

    # ── Summary ──────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  {'[DRY RUN] ' if args.dry_run else ''}Results for {year}:")
    print(f"    Questions inserted : {counts['inserted']}")
    print(f"    Ref pairs inserted : {counts['ref_pairs']}")
    print(f"    Skipped (no stem)  : {counts['skipped']}")
    if counts["warnings"]:
        print(f"    Warnings           : {len(counts['warnings'])}")
        for w in counts["warnings"][:5]:
            print(f"      - {w}")
        if len(counts["warnings"]) > 5:
            print(f"      ... ({len(counts['warnings']) - 5} more in log)")
    print(f"\n  QID range: QID-{year}-0001 → QID-{year}-{counts['inserted']:04d}")
    if not args.dry_run:
        print(f"\n  Next: python classify_ite_year.py --year {year}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
