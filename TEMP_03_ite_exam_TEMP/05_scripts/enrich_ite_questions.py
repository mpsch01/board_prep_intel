#!/usr/bin/env python3
"""
Enrichment script for 2018-2019 ITE questions.
Uses Claude API to classify each question with:
  - body_system (16 canonical categories)
  - subcategory (specific topic)
  - icd10_codes (list of relevant ICD-10-CM codes)

Reads:  ite_2018_2019_extracted.json
Writes: ite_2018_2019_enriched.json (incremental saves after each batch)

Usage:
  python enrich_ite_questions.py                   # Process all unenriched
  python enrich_ite_questions.py --resume           # Resume from last checkpoint
  python enrich_ite_questions.py --start 100        # Start from question index 100
  python enrich_ite_questions.py --test 5           # Test run on first 5 questions

Requires: ANTHROPIC_API_KEY in environment variables
Runtime estimate: ~440 questions × ~2 sec/question ≈ 15 minutes
Cost estimate: ~440 × ~1500 tokens ≈ 660K tokens ≈ $2-3 (Sonnet)
"""

import json
import os
import sys
import time
import argparse
from pathlib import Path

try:
    import anthropic
except ImportError:
    print("ERROR: anthropic package not found. Install with:")
    print("  pip install anthropic")
    sys.exit(1)

# ── CONFIG ──────────────────────────────────────────────────────────────────
INPUT_FILE = "ite_2018_2019_extracted.json"
OUTPUT_FILE = "ite_2018_2019_enriched.json"
CHECKPOINT_FILE = "ite_enrichment_checkpoint.json"

MODEL = "claude-sonnet-4-20250514"  # Fast + accurate for classification
BATCH_SIZE = 10                      # Save checkpoint every N questions
MAX_RETRIES = 3
RETRY_DELAY = 5                      # Seconds between retries

# Canonical 16 body system categories - MUST match existing DB exactly
BODY_SYSTEMS = [
    "Cardiovascular",
    "Dermatologic",
    "Endocrine",
    "Eyes, Ears, Nose & Throat",
    "Gastrointestinal",
    "Hematologic/Immune",
    "Maternity Care",
    "Musculoskeletal",
    "Nephrologic/Urologic",
    "Neurologic",
    "Nonspecific/Other",
    "Population-Based/Preventive",
    "Psychiatric/Behavioral",
    "Pulmonary/Critical Care",
    "Reproductive (Female)",
    "Reproductive (Male)",
]

SYSTEM_PROMPT = """You are a medical classification expert specializing in the ABFM In-Training Examination (ITE).

For each ITE question, you will provide THREE classifications:

1. **body_system**: Classify into exactly ONE of these 16 canonical categories:
   - Cardiovascular
   - Dermatologic
   - Endocrine
   - Eyes, Ears, Nose & Throat
   - Gastrointestinal
   - Hematologic/Immune
   - Maternity Care
   - Musculoskeletal
   - Nephrologic/Urologic
   - Neurologic
   - Nonspecific/Other
   - Population-Based/Preventive
   - Psychiatric/Behavioral
   - Pulmonary/Critical Care
   - Reproductive (Female)
   - Reproductive (Male)

2. **subcategory**: A specific clinical topic within that body system (e.g., "Heart Failure", "Type 2 Diabetes Management", "ACL Injury Diagnosis"). Keep it concise (2-5 words).

3. **icd10_codes**: A list of 1-3 most relevant ICD-10-CM codes for the PRIMARY clinical condition being tested. Use the most specific code applicable.

Respond ONLY with valid JSON in this exact format:
{
  "body_system": "Cardiovascular",
  "subcategory": "Heart Failure Management",
  "icd10_codes": [
    {"code": "I50.9", "desc": "Heart failure, unspecified"}
  ]
}

Rules:
- body_system MUST be one of the 16 categories listed above, spelled exactly as shown
- For preventive medicine, screening, or population health questions, use "Population-Based/Preventive"
- For behavioral health, substance abuse, or psychiatric questions, use "Psychiatric/Behavioral"
- For pregnancy-related questions, use "Maternity Care"
- ICD-10 codes should be valid ICD-10-CM codes (e.g., E11.9 for Type 2 DM, I10 for Essential HTN)
- Limit to 1-3 most relevant codes; do not over-code
- Always provide at least one ICD-10 code"""


# ── API CALL ────────────────────────────────────────────────────────────────
def classify_question(client, question):
    """Call Claude API to classify a single question."""

    # Build the prompt with question context
    choices_text = "\n".join(f"  {c['letter']}) {c['text']}" for c in question["choices"])

    user_prompt = f"""Classify this ABFM ITE question:

QUESTION:
{question['question_text']}

CHOICES:
{choices_text}

CORRECT ANSWER: {question['correct_letter']}

EXPLANATION:
{question['explanation'][:500]}

Respond with JSON only."""

    for attempt in range(MAX_RETRIES):
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=300,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )

            # Parse response
            text = response.content[0].text.strip()

            # Handle markdown code blocks
            if text.startswith("```"):
                text = text.split("\n", 1)[1]  # Remove first line
                text = text.rsplit("```", 1)[0]  # Remove last ```
                text = text.strip()

            result = json.loads(text)

            # Validate body_system
            if result.get("body_system") not in BODY_SYSTEMS:
                print(f"    WARNING: Invalid body_system '{result.get('body_system')}' for {question['question_id']}")
                # Try fuzzy match
                bs = result.get("body_system", "")
                for valid_bs in BODY_SYSTEMS:
                    if bs.lower() in valid_bs.lower() or valid_bs.lower() in bs.lower():
                        result["body_system"] = valid_bs
                        break
                else:
                    result["body_system"] = "Nonspecific/Other"

            # Validate icd10_codes structure
            if not isinstance(result.get("icd10_codes"), list):
                result["icd10_codes"] = []

            return result

        except json.JSONDecodeError as e:
            print(f"    JSON parse error (attempt {attempt+1}): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
        except anthropic.RateLimitError:
            wait = RETRY_DELAY * (attempt + 2)
            print(f"    Rate limited, waiting {wait}s...")
            time.sleep(wait)
        except Exception as e:
            print(f"    API error (attempt {attempt+1}): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)

    # Fallback if all retries fail
    return {
        "body_system": "Nonspecific/Other",
        "subcategory": "NEEDS_REVIEW",
        "icd10_codes": [],
    }


# ── CHECKPOINT MANAGEMENT ───────────────────────────────────────────────────
def load_checkpoint():
    """Load last processed index from checkpoint file."""
    if Path(CHECKPOINT_FILE).exists():
        with open(CHECKPOINT_FILE) as f:
            return json.load(f)
    return {"last_index": -1}


def save_checkpoint(index):
    """Save current progress."""
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump({"last_index": index, "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")}, f)


# ── MAIN ────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Enrich ITE questions with body_system, subcategory, and ICD-10 codes")
    parser.add_argument("--resume", action="store_true", help="Resume from last checkpoint")
    parser.add_argument("--start", type=int, default=0, help="Start from question index N")
    parser.add_argument("--test", type=int, default=0, help="Test run on first N questions only")
    parser.add_argument("--input", default=INPUT_FILE, help="Input JSON file")
    parser.add_argument("--output", default=OUTPUT_FILE, help="Output JSON file")
    args = parser.parse_args()

    # Load data
    print(f"Loading questions from {args.input}...")
    with open(args.input, encoding="utf-8") as f:
        data = json.load(f)
    print(f"  Loaded {len(data)} questions")

    # Load existing output if resuming
    if args.resume and Path(args.output).exists():
        with open(args.output, encoding="utf-8") as f:
            data = json.load(f)
        checkpoint = load_checkpoint()
        start_idx = checkpoint["last_index"] + 1
        print(f"  Resuming from index {start_idx}")
    else:
        start_idx = args.start

    # Test mode
    end_idx = len(data)
    if args.test > 0:
        end_idx = min(start_idx + args.test, len(data))
        print(f"  TEST MODE: processing questions {start_idx} to {end_idx-1}")

    # Initialize API client
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set in environment variables")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    print(f"  API client initialized (model: {MODEL})")

    # Count already enriched
    already_done = sum(1 for r in data[start_idx:end_idx] if r.get("body_system"))
    to_process = end_idx - start_idx - already_done
    print(f"  Questions to process: {to_process}")
    print(f"  Estimated time: {to_process * 2 / 60:.1f} minutes")
    print(f"  Estimated cost: ~${to_process * 1500 * 3 / 1_000_000:.2f} (Sonnet)\n")

    # Process questions
    processed = 0
    errors = 0
    start_time = time.time()

    for i in range(start_idx, end_idx):
        q = data[i]

        # Skip if already enriched
        if q.get("body_system") and q["body_system"] != "":
            continue

        # Classify
        result = classify_question(client, q)

        # Apply results
        q["body_system"] = result["body_system"]
        q["subcategory"] = result.get("subcategory", "")
        q["icd10_codes"] = result.get("icd10_codes", [])

        if result.get("subcategory") == "NEEDS_REVIEW":
            errors += 1

        processed += 1

        # Progress
        elapsed = time.time() - start_time
        rate = processed / elapsed if elapsed > 0 else 0
        remaining = (to_process - processed) / rate if rate > 0 else 0

        print(f"  [{processed}/{to_process}] {q['question_id']}: {q['body_system']} / {q['subcategory']} "
              f"[{', '.join(c['code'] for c in q.get('icd10_codes', []))}] "
              f"({remaining:.0f}s remaining)")

        # Checkpoint save
        if processed % BATCH_SIZE == 0:
            with open(args.output, 'w', encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            save_checkpoint(i)

        # Small delay to be respectful of rate limits
        time.sleep(0.5)

    # Final save
    with open(args.output, 'w', encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    save_checkpoint(end_idx - 1)

    # Summary
    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"ENRICHMENT COMPLETE")
    print(f"{'='*60}")
    print(f"  Processed: {processed} questions in {elapsed:.0f}s ({elapsed/60:.1f} min)")
    print(f"  Errors:    {errors}")
    print(f"  Output:    {args.output}")

    # Distribution report
    print(f"\nBody System Distribution:")
    bs_counts = {}
    for r in data:
        bs = r.get("body_system", "EMPTY")
        bs_counts[bs] = bs_counts.get(bs, 0) + 1
    for bs, count in sorted(bs_counts.items(), key=lambda x: -x[1]):
        print(f"  {bs}: {count}")

    print(f"\nICD-10 Coverage:")
    with_icd = sum(1 for r in data if r.get("icd10_codes"))
    total_codes = sum(len(r.get("icd10_codes", [])) for r in data)
    print(f"  Questions with ICD-10: {with_icd}/{len(data)}")
    print(f"  Total ICD-10 codes: {total_codes}")
    print(f"  Avg codes/question: {total_codes/len(data):.1f}")

    # Cleanup checkpoint on success
    if errors == 0 and Path(CHECKPOINT_FILE).exists():
        os.remove(CHECKPOINT_FILE)
        print(f"\n  Checkpoint file cleaned up (no errors)")


if __name__ == "__main__":
    main()
