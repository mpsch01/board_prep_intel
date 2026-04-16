"""
recover_missing_questions.py
----------------------------
Recovers 10 missing ITE questions from MC exam PDFs + critique PDFs.

These questions exist in qid_art_xref (article linkages confirmed) but are
absent from the questions table — extraction gaps during the original build.
All 10 confirmed present in both MC exam AND critique with full explanations.

USAGE:
    python recover_missing_questions.py [--dry-run]

OUTPUT:
    - recovered_questions_review.json  (human-readable review before insert)
    - recovered_questions_insert.sql   (SQL INSERT statements — apply after review)

LOCKED CONVENTIONS:
    - choices stored as JSON array: [{"letter": "A", "text": "..."}]
    - body_system / blueprint / keywords / concept_tags left NULL
      (filled by body-system-qc, blueprint classifier, keyword pipeline post-insert)
    - Dynamic paths: SCRIPT_DIR / PROJECT_ROOT
"""

import json
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

import pdfplumber

# ── Paths ────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"
EXAMS_DIR = PROJECT_ROOT / "01_module.1_warehouse" / "ite_exams"
OUTPUT_DIR = SCRIPT_DIR  # write review files alongside script

# ── Target QIDs ──────────────────────────────────────────────────────────────
# Each tuple: (qid, year, question_number_int)
TARGETS = [
    ("QID-2020-0134", 2020, 134),
    ("QID-2020-0138", 2020, 138),
    ("QID-2021-0050", 2021, 50),
    ("QID-2021-0168", 2021, 168),
    ("QID-2022-0175", 2022, 175),
    ("QID-2023-0004", 2023, 4),
    ("QID-2024-0017", 2024, 17),
    ("QID-2024-0117", 2024, 117),
    ("QID-2024-0140", 2024, 140),
    ("QID-2024-0187", 2024, 187),
]


# ── PDF Utilities ─────────────────────────────────────────────────────────────

def extract_page_text_column_aware(page):
    """Reconstruct 2-column ABFM exam page by sorting words by (y, x)."""
    words = page.extract_words(x_tolerance=3, y_tolerance=3)
    if not words:
        return ""
    lines = defaultdict(list)
    for w in words:
        y_bucket = round(w["top"] / 8) * 8
        lines[y_bucket].append(w)
    result = []
    for y in sorted(lines.keys()):
        line_words = sorted(lines[y], key=lambda w: w["x0"])
        result.append(" ".join(w["text"] for w in line_words))
    return "\n".join(result)


def load_mc_pdf(year: int) -> str:
    """Load and return full column-aware text from MC exam PDF."""
    path = EXAMS_DIR / f"{year}_MC.pdf"
    if not path.exists():
        raise FileNotFoundError(f"MC PDF not found: {path}")
    pages = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            pages.append(extract_page_text_column_aware(page))
    return "\n".join(pages)


def load_critique_pdf(year: int) -> str:
    """Load and return raw text from critique PDF."""
    path = EXAMS_DIR / f"{year}_critique.pdf"
    if not path.exists():
        raise FileNotFoundError(f"Critique PDF not found: {path}")
    pages = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                pages.append(t)
    return "\n".join(pages)


# ── MC Extraction ─────────────────────────────────────────────────────────────

def extract_mc_question(mc_text: str, qnum: int) -> dict:
    """
    Extract question text and choices for question number qnum from MC text.
    Returns dict with keys: question_text, choices (list of {letter, text})
    """
    # Find the question start: line beginning with "{N}."
    # Use word boundary to avoid matching e.g. "1175."
    pattern = rf"(?m)^{qnum}[\.]\s+(.+)"
    m = re.search(pattern, mc_text)
    if not m:
        return {"question_text": None, "choices": None, "parse_error": f"Q{qnum} not found in MC text"}

    start = m.start()

    # Find the NEXT question start to bound our extraction
    # Next question is qnum+1 (or qnum+2, etc. — find the first one present)
    end = len(mc_text)
    for next_q in range(qnum + 1, qnum + 10):
        next_pat = rf"(?m)^{next_q}[\.]\s+[A-Z]"
        nm = re.search(next_pat, mc_text[start + 1:])
        if nm:
            end = start + 1 + nm.start()
            break

    block = mc_text[start:end].strip()

    # Parse choices — lines that start with A) B) C) D) E)
    choice_pattern = re.compile(r"^([A-E])\)\s+(.+?)(?=^[A-E]\)|$)", re.MULTILINE | re.DOTALL)
    choices_raw = list(re.finditer(r"^([A-E])\)\s+(.+)", block, re.MULTILINE))

    if not choices_raw:
        # Some exams use "A) " style; try alternate
        choices_raw = list(re.finditer(r"^([A-E])\s{1,3}(.+)", block, re.MULTILINE))

    choices = []
    for i, cm in enumerate(choices_raw):
        letter = cm.group(1)
        # Text is from this match to next match (or end of block)
        text_start = cm.end()
        text_end = choices_raw[i + 1].start() if i + 1 < len(choices_raw) else len(block)
        full_text = (cm.group(2) + "\n" + block[text_start:text_end]).strip()
        # Clean up line breaks within choice text
        full_text = re.sub(r"\s+", " ", full_text).strip()
        choices.append({"letter": letter, "text": full_text})

    # Question text is everything before the first choice
    q_text_end = choices_raw[0].start() if choices_raw else len(block)
    question_text = block[:q_text_end].strip()
    # Remove the leading "N. " prefix
    question_text = re.sub(rf"^{qnum}\.\s+", "", question_text).strip()
    # Normalize whitespace
    question_text = re.sub(r"\s+", " ", question_text).strip()

    return {
        "question_text": question_text,
        "choices": choices,
    }


# ── Critique Extraction ───────────────────────────────────────────────────────

def extract_critique_item(critique_text: str, qnum: int) -> dict:
    """
    Extract answer letter, explanation, and reference for Item N from critique.
    Critique format: Item N\\nANSWER: {letter}\\n{explanation}\\nReference\\n{citation}
    """
    # Find Item N
    item_pattern = rf"Item\s+{qnum}\b"
    m = re.search(item_pattern, critique_text)
    if not m:
        return {"correct_letter": None, "explanation": None, "reference": None,
                "parse_error": f"Item {qnum} not found in critique"}

    # Find end: next Item or end of text
    next_item = re.search(r"Item\s+\d+\b", critique_text[m.end():])
    block_end = m.end() + next_item.start() if next_item else len(critique_text)
    block = critique_text[m.start():block_end].strip()

    # Extract ANSWER letter
    answer_m = re.search(r"ANSWER:\s*([A-E])", block)
    correct_letter = answer_m.group(1) if answer_m else None

    # Extract Reference section
    ref_m = re.search(r"\bReference\b", block, re.IGNORECASE)
    if not ref_m:
        # Try "Ref:" pattern
        ref_m = re.search(r"\bRef:", block)

    if ref_m:
        explanation_raw = block[answer_m.end() if answer_m else 0:ref_m.start()].strip()
        reference_raw = block[ref_m.end():].strip()
    else:
        explanation_raw = block[answer_m.end() if answer_m else 0:].strip()
        reference_raw = None

    # Clean up explanation (remove leading "ANSWER: X" leftover)
    explanation = re.sub(r"^ANSWER:\s*[A-E]\s*", "", explanation_raw).strip()
    explanation = re.sub(r"\s+", " ", explanation).strip()

    reference = re.sub(r"\s+", " ", reference_raw).strip() if reference_raw else None

    return {
        "correct_letter": correct_letter,
        "explanation": explanation,
        "reference": reference,
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    dry_run = "--dry-run" in sys.argv

    print("=" * 65)
    print("ITE Missing Question Recovery")
    print(f"Targets: {len(TARGETS)} questions across years 2020-2024")
    print("=" * 65)

    # Load PDFs by year (cache to avoid re-opening)
    mc_cache = {}
    critique_cache = {}

    results = []
    errors = []

    for qid, year, qnum in TARGETS:
        print(f"\n  Extracting {qid} (Q{qnum} / {year})...")

        # Load PDFs
        if year not in mc_cache:
            print(f"    Loading {year}_MC.pdf...")
            mc_cache[year] = load_mc_pdf(year)
        if year not in critique_cache:
            print(f"    Loading {year}_critique.pdf...")
            critique_cache[year] = load_critique_pdf(year)

        mc_data = extract_mc_question(mc_cache[year], qnum)
        crit_data = extract_critique_item(critique_cache[year], qnum)

        if "parse_error" in mc_data:
            print(f"    ⚠ MC parse error: {mc_data['parse_error']}")
            errors.append({"qid": qid, "error": mc_data["parse_error"]})
            continue
        if "parse_error" in crit_data:
            print(f"    ⚠ Critique parse error: {crit_data['parse_error']}")
            errors.append({"qid": qid, "error": crit_data["parse_error"]})
            continue

        # Resolve correct_text from choices
        correct_letter = crit_data.get("correct_letter")
        correct_text = None
        if correct_letter and mc_data.get("choices"):
            for c in mc_data["choices"]:
                if c["letter"] == correct_letter:
                    correct_text = c["text"]
                    break

        record = {
            "qid": qid,
            "exam_year": year,
            "question_text": mc_data.get("question_text"),
            "choices": mc_data.get("choices"),
            "choices_json": json.dumps(mc_data.get("choices")) if mc_data.get("choices") else None,
            "correct_letter": correct_letter,
            "correct_text": correct_text,
            "explanation": crit_data.get("explanation"),
            "reference": crit_data.get("reference"),
            # Intentionally NULL — filled by downstream pipelines
            "body_system": None,
            "blueprint": None,
            "stem_keywords": None,
            "explanation_keywords": None,
            "all_keywords": None,
            "concept_tags": None,
            "body_system_merged": None,
        }

        results.append(record)
        status = "✓" if correct_text else "⚠ correct_text unresolved"
        print(f"    {status}  answer={correct_letter} | choices={len(mc_data.get('choices', []))} | explanation={len(crit_data.get('explanation',''))} chars")
        print(f"    Q: {record['question_text'][:80]}...")

    # ── Write review JSON ────────────────────────────────────────────────────
    review_path = OUTPUT_DIR / "recovered_questions_review.json"
    with open(review_path, "w") as f:
        json.dump({"recovered": results, "errors": errors}, f, indent=2)
    print(f"\n\nReview JSON written → {review_path}")

    # ── Write INSERT SQL ─────────────────────────────────────────────────────
    sql_path = OUTPUT_DIR / "recovered_questions_insert.sql"
    sql_lines = [
        "-- recovered_questions_insert.sql",
        "-- Generated by recover_missing_questions.py",
        "-- REVIEW recovered_questions_review.json before applying",
        "-- Apply: sqlite3 ite_intelligence.db < recovered_questions_insert.sql",
        "",
        "BEGIN TRANSACTION;",
        "",
    ]

    for r in results:
        def q(val):
            if val is None:
                return "NULL"
            return "'" + str(val).replace("'", "''") + "'"

        sql_lines.append(f"-- {r['qid']} | {r['exam_year']} | Q: {str(r['question_text'])[:60]}...")
        sql_lines.append(
            f"INSERT INTO questions (qid, exam_year, question_text, choices, correct_letter, correct_text, "
            f"explanation, reference, body_system, blueprint, stem_keywords, explanation_keywords, "
            f"all_keywords, concept_tags, body_system_merged) VALUES ("
            f"{q(r['qid'])}, {r['exam_year']}, {q(r['question_text'])}, {q(r['choices_json'])}, "
            f"{q(r['correct_letter'])}, {q(r['correct_text'])}, {q(r['explanation'])}, {q(r['reference'])}, "
            f"NULL, NULL, NULL, NULL, NULL, NULL, NULL);"
        )
        sql_lines.append("")

    sql_lines.append("COMMIT;")
    sql_lines.append("")
    sql_lines.append("-- Post-insert verification")
    sql_lines.append("SELECT qid, exam_year, correct_letter, SUBSTR(question_text, 1, 60) as q_preview")
    sql_lines.append("FROM questions")
    sql_lines.append("WHERE qid IN ('" + "','".join(r['qid'] for r in results) + "')")
    sql_lines.append("ORDER BY qid;")

    with open(sql_path, "w") as f:
        f.write("\n".join(sql_lines))
    print(f"INSERT SQL written    → {sql_path}")

    # ── Summary ──────────────────────────────────────────────────────────────
    print(f"\n{'='*65}")
    print(f"SUMMARY: {len(results)} questions extracted, {len(errors)} errors")
    if errors:
        print("ERRORS:")
        for e in errors:
            print(f"  {e['qid']}: {e['error']}")
    print()
    print("NEXT STEPS:")
    print(f"  1. Review: {review_path.name}")
    print(f"  2. Verify question text + choices look correct")
    print(f"  3. Apply: sqlite3 00_database/db/ite_intelligence.db < {sql_path.name}")
    print(f"  4. Run body-system-qc + blueprint classifier on new QIDs")
    print(f"  5. Run keyword pipeline on new QIDs")
    print(f"  6. Run concept_tags enrichment on new QIDs")
    print(f"  7. Rebuild question_full_vec (new rows + stale body_system rows)")


if __name__ == "__main__":
    main()
