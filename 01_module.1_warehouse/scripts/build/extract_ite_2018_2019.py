#!/usr/bin/env python3
"""
⚠️  ALREADY RUN — DO NOT RE-RUN (2026-04-04)
    Status: 2018-2019 data is in ite_intelligence.db. This script has served its purpose.
    Dead path: reads from /sessions/fervent-hopeful-thompson/ — a session that no longer exists.
    Retained for historical reference only. Flag for deletion on next Windows housekeeping pass.
    Gathered in: 01_module.1_warehouse/scripts/_legacy/
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Extract 2018 and 2019 ITE exam questions and answers from separate PDFs.
Merges Q+A by item number into structured JSON matching ite_questions_clean.json schema.

Output: ite_2018_2019_extracted.json
"""

import pdfplumber
import json
import re
import sys
from pathlib import Path

# ── CONFIG ──────────────────────────────────────────────────────────────────
YEARS = {
    2018: {
        "questions_pdf": "/sessions/fervent-hopeful-thompson/mnt/uploads/2018 ITE Questions.pdf",
        "answers_pdf":   "/sessions/fervent-hopeful-thompson/mnt/uploads/2018 ITE Answers.pdf",
        "expected_count": 240,
    },
    2019: {
        "questions_pdf": "/sessions/fervent-hopeful-thompson/mnt/uploads/2019 ITE Questions.pdf",
        "answers_pdf":   "/sessions/fervent-hopeful-thompson/mnt/uploads/2019 ITE Answers.pdf",
        "expected_count": 200,
    },
}

OUTPUT_FILE = "/sessions/fervent-hopeful-thompson/ite_2018_2019_extracted.json"

# Canonical 16 body system categories (for reference - enrichment script uses these)
BODY_SYSTEMS = [
    "Cardiovascular", "Dermatologic", "Endocrine", "Eyes, Ears, Nose & Throat",
    "Gastrointestinal", "Hematologic/Immune", "Maternity Care",
    "Musculoskeletal", "Nephrologic/Urologic", "Neurologic",
    "Nonspecific/Other", "Population-Based/Preventive", "Psychiatric/Behavioral",
    "Pulmonary/Critical Care", "Reproductive (Female)", "Reproductive (Male)"
]


# ── QUESTION PDF PARSER ─────────────────────────────────────────────────────
def extract_questions(pdf_path, year):
    """Parse Questions PDF into list of dicts keyed by item number."""
    print(f"  Extracting questions from: {Path(pdf_path).name}")

    full_text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"

    # Split on question numbers: "1." or "123." at start of line or after whitespace
    # Pattern: number followed by period and space, at line boundary
    # We need to handle the fact that some choice letters like "A)" could be confused

    questions = {}

    # Split text into blocks per question number
    # Match pattern: newline (or start) + number + period + space
    pattern = r'(?:^|\n)\s*(\d{1,3})\.\s+'
    splits = list(re.finditer(pattern, full_text))

    for i, match in enumerate(splits):
        q_num = int(match.group(1))
        start = match.end()
        end = splits[i + 1].start() if i + 1 < len(splits) else len(full_text)
        block = full_text[start:end].strip()

        # Skip if question number seems like a page number or non-question
        if q_num < 1 or q_num > 300:
            continue

        # Parse choices from the block
        # Choices pattern: A) text, B) text, etc.
        choice_pattern = r'\n\s*([A-E])\)\s+'
        choice_matches = list(re.finditer(choice_pattern, '\n' + block))

        if not choice_matches:
            # Some questions might not have standard choice format
            # Try without leading newline requirement
            choice_pattern2 = r'([A-E])\)\s+'
            choice_matches = list(re.finditer(choice_pattern2, block))

        if choice_matches:
            # Question text is everything before first choice
            first_choice_pos = choice_matches[0].start()
            # Adjust for the prepended newline if we used the first pattern
            if '\n' + block != block:
                q_text = block[:max(0, first_choice_pos - 1)].strip()
            else:
                q_text = block[:first_choice_pos].strip()

            choices = []
            for j, cm in enumerate(choice_matches):
                letter = cm.group(1)
                c_start = cm.end()
                c_end = choice_matches[j + 1].start() if j + 1 < len(choice_matches) else len(block) + 1
                # Adjust for prepended newline
                choice_text = ('\n' + block)[c_start:c_end].strip() if c_start < len('\n' + block) else block[cm.end():].strip()

                # Clean up: remove trailing page numbers, excessive whitespace
                choice_text = re.sub(r'\n\s*\d{1,2}\s*$', '', choice_text).strip()
                choice_text = ' '.join(choice_text.split())

                choices.append({"letter": letter, "text": choice_text})

            # Clean question text
            q_text = ' '.join(q_text.split())
            # Remove any "Which one of the following" that might be split across lines

            questions[q_num] = {
                "item_number": q_num,
                "question_text": q_text,
                "choices": choices,
            }
        else:
            # Fallback: store full block as question text with no choices parsed
            questions[q_num] = {
                "item_number": q_num,
                "question_text": ' '.join(block.split()),
                "choices": [],
            }

    print(f"    Parsed {len(questions)} questions")
    return questions


# ── ANSWER/CRITIQUE PDF PARSER ──────────────────────────────────────────────
def extract_answers(pdf_path, year):
    """Parse Answers/Critique PDF into list of dicts keyed by item number."""
    print(f"  Extracting answers from: {Path(pdf_path).name}")

    full_text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"

    answers = {}

    # Split on "Item N" pattern
    pattern = r'(?:^|\n)\s*Item\s+(\d{1,3})\s*\n'
    splits = list(re.finditer(pattern, full_text))

    for i, match in enumerate(splits):
        item_num = int(match.group(1))
        start = match.end()
        end = splits[i + 1].start() if i + 1 < len(splits) else len(full_text)
        block = full_text[start:end].strip()

        # Extract answer letter
        answer_match = re.match(r'ANSWER:\s+([A-E])', block)
        correct_letter = answer_match.group(1) if answer_match else ""

        # Everything after "ANSWER: X\n" is the explanation
        if answer_match:
            explanation_start = answer_match.end()
            remainder = block[explanation_start:].strip()
        else:
            remainder = block

        # Split explanation from references
        # References start with "Ref:" at the beginning of a line
        ref_match = re.search(r'\nRef:\s+', remainder)
        if ref_match:
            explanation = remainder[:ref_match.start()].strip()
            ref_text = remainder[ref_match.start():].strip()
            # Clean "Ref:" prefix
            ref_text = re.sub(r'^Ref:\s+', '', ref_text).strip()
        else:
            explanation = remainder.strip()
            ref_text = ""

        # Clean up text
        explanation = ' '.join(explanation.split())
        ref_text = ' '.join(ref_text.split())

        # Remove trailing page numbers
        explanation = re.sub(r'\s+\d{1,2}\s*$', '', explanation).strip()
        ref_text = re.sub(r'\s+\d{1,2}\s*$', '', ref_text).strip()

        answers[item_num] = {
            "item_number": item_num,
            "correct_letter": correct_letter,
            "explanation": explanation,
            "reference": ref_text,
        }

    print(f"    Parsed {len(answers)} answer items")
    return answers


# ── MERGE AND FORMAT ────────────────────────────────────────────────────────
def merge_and_format(questions, answers, year, expected_count):
    """Merge Q+A and format to match ite_questions_clean.json schema."""
    merged = []
    missing_q = []
    missing_a = []

    for item_num in range(1, expected_count + 1):
        q = questions.get(item_num)
        a = answers.get(item_num)

        if not q:
            missing_q.append(item_num)
        if not a:
            missing_a.append(item_num)

        # Build question_id: matches existing convention Q{year}-{NNN}
        question_id = f"Q{year}-{item_num:03d}"

        # Build QID for DB: QID-{year}-{NNNN}
        qid = f"QID-{year}-{item_num:04d}"

        correct_letter = a["correct_letter"] if a else ""
        choices = q["choices"] if q else []

        # Find correct answer text
        correct_text = ""
        if correct_letter and choices:
            for c in choices:
                if c["letter"] == correct_letter:
                    correct_text = c["text"]
                    break

        record = {
            "question_id": question_id,
            "qid": qid,
            "exam_year": year,
            "body_system": "",           # To be filled by enrichment script
            "subcategory": "",           # To be filled by enrichment script
            "icd10_codes": [],           # To be filled by enrichment script
            "blueprint": "",
            "format": "newline",
            "question_text": q["question_text"] if q else "",
            "choices": choices,
            "correct_letter": correct_letter,
            "correct_text": correct_text,
            "explanation": a["explanation"] if a else "",
            "reference": a["reference"] if a else "",
            "needs_review": not (q and a),  # Flag if missing either Q or A
        }

        merged.append(record)

    if missing_q:
        print(f"    WARNING: Missing questions for items: {missing_q[:10]}{'...' if len(missing_q) > 10 else ''}")
    if missing_a:
        print(f"    WARNING: Missing answers for items: {missing_a[:10]}{'...' if len(missing_a) > 10 else ''}")

    return merged


# ── MAIN ────────────────────────────────────────────────────────────────────
def main():
    all_records = []

    for year, config in YEARS.items():
        print(f"\n{'='*60}")
        print(f"Processing {year} ITE Exam")
        print(f"{'='*60}")

        questions = extract_questions(config["questions_pdf"], year)
        answers = extract_answers(config["answers_pdf"], year)

        merged = merge_and_format(questions, answers, year, config["expected_count"])
        all_records.extend(merged)

        # Summary stats
        total = len(merged)
        has_q = sum(1 for r in merged if r["question_text"])
        has_a = sum(1 for r in merged if r["correct_letter"])
        has_both = sum(1 for r in merged if r["question_text"] and r["correct_letter"])
        flagged = sum(1 for r in merged if r["needs_review"])

        print(f"\n  Summary for {year}:")
        print(f"    Total items:     {total}")
        print(f"    Have question:   {has_q}")
        print(f"    Have answer:     {has_a}")
        print(f"    Have both:       {has_both}")
        print(f"    Flagged review:  {flagged}")

    # Write output
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(all_records, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*60}")
    print(f"TOTAL: {len(all_records)} questions extracted")
    print(f"Output: {OUTPUT_FILE}")
    print(f"{'='*60}")

    # Quick quality check: show a sample
    print(f"\nSample record (item 1, 2018):")
    sample = all_records[0]
    print(f"  question_id: {sample['question_id']}")
    print(f"  exam_year:   {sample['exam_year']}")
    print(f"  correct:     {sample['correct_letter']}")
    print(f"  choices:     {len(sample['choices'])} options")
    print(f"  q_text:      {sample['question_text'][:100]}...")
    print(f"  explain:     {sample['explanation'][:100]}...")
    print(f"  reference:   {sample['reference'][:100]}...")


if __name__ == "__main__":
    main()
