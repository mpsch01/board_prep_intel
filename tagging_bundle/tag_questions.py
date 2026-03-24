"""
ABFM ITE Question Tagger
========================
Uses the Anthropic API to tag all questions with:
  - BlueprintCategory
  - Subcategory (human-readable label)
  - QuestionType
  - ClinicalFocus
  - Confidence (model's self-assessed confidence)

Usage:
    pip install anthropic
    export ANTHROPIC_API_KEY="your-key-here"
    python tag_questions.py

Output:
    ABFM_ITE_AI_Tagged.csv  — full dataset with new tag columns
    tagging_log.txt         — per-question log for auditing
"""

import anthropic
import pandas as pd
import json
import time
import os
import re
from datetime import datetime

# ── Config ──────────────────────────────────────────────────────────────────
INPUT_CSV  = "ABFM_ITE_6_Year_Master.csv"   # original file
OUTPUT_CSV = "ABFM_ITE_AI_Tagged.csv"
LOG_FILE   = "tagging_log.txt"
MODEL      = "claude-haiku-4-5-20251001"     # fast + cheap, ideal for bulk tagging
RATE_LIMIT_DELAY = 0.5                        # seconds between calls (adjust if you hit rate limits)
RETRY_ATTEMPTS   = 3
RETRY_DELAY      = 10                         # seconds to wait on rate limit error

# ── Tag definitions (sent in the prompt so model stays consistent) ──────────
BLUEPRINT_CATEGORIES = [
    "Acute Care and Diagnosis",
    "Chronic Care Management",
    "Emergent and Urgent Care",
    "Preventive Care",
    "Foundations of Care",
]

QUESTION_TYPES = [
    "Diagnosis",        # What is the diagnosis?
    "Management",       # What is the next best step / treatment?
    "Screening",        # Who/when to screen?
    "Pharmacology",     # Drug choice, dosing, side effects
    "Counseling",       # Patient education, lifestyle
    "Interpretation",   # Interpret lab/imaging result
    "Pathophysiology",  # Mechanism of disease
]

# ── Prompt ───────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are an expert Family Medicine physician and medical educator with deep knowledge of the ABFM ITE (In-Training Examination) and board exam content.

Your job is to analyze Family Medicine ITE questions and assign structured tags. Be precise and consistent.

Respond ONLY with a valid JSON object — no explanation, no markdown, no extra text."""

def build_user_prompt(question_stem: str, correct_answer: str, primary_category: str) -> str:
    return f"""Analyze this Family Medicine ITE question and assign the following tags.

QUESTION:
{question_stem}

CORRECT ANSWER:
{correct_answer}

PRIMARY CATEGORY (already assigned): {primary_category}

Assign these tags:

1. BlueprintCategory — choose exactly one:
{json.dumps(BLUEPRINT_CATEGORIES, indent=2)}

2. Subcategory — a specific, human-readable clinical subcategory (e.g., "Type 2 Diabetes Management", "Atrial Fibrillation", "Major Depressive Disorder", "Pneumonia Diagnosis"). Be specific — 2-5 words.

3. QuestionType — choose exactly one:
{json.dumps(QUESTION_TYPES, indent=2)}

4. ClinicalFocus — one concise phrase (3-6 words) describing the core clinical concept being tested (e.g., "first-line HTN treatment in CKD", "DVT prophylaxis post-surgery", "depression screening in primary care")

5. Confidence — your confidence in these tags: "High", "Medium", or "Low"

Respond with ONLY this JSON structure:
{{
  "BlueprintCategory": "...",
  "Subcategory": "...",
  "QuestionType": "...",
  "ClinicalFocus": "...",
  "Confidence": "..."
}}"""


# ── Tagging function ──────────────────────────────────────────────────────────
def tag_question(client, row, log_file):
    prompt = build_user_prompt(
        question_stem=str(row.get('QuestionStem', '')),
        correct_answer=str(row.get('CorrectAnswer', '')),
        primary_category=str(row.get('PrimaryCategory', ''))
    )

    for attempt in range(RETRY_ATTEMPTS):
        try:
            message = client.messages.create(
                model=MODEL,
                max_tokens=300,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            )
            
            raw = message.content[0].text.strip()
            
            # Strip markdown fences if present
            raw = re.sub(r'^```(?:json)?\s*', '', raw)
            raw = re.sub(r'\s*```$', '', raw)
            
            result = json.loads(raw)
            
            # Validate required keys
            required = ['BlueprintCategory', 'Subcategory', 'QuestionType', 'ClinicalFocus', 'Confidence']
            for key in required:
                if key not in result:
                    result[key] = 'Unknown'
            
            log_file.write(f"[OK] {row['Question ID']} | {result['BlueprintCategory']} | {result['Subcategory']} | {result['QuestionType']} | conf={result['Confidence']}\n")
            return result

        except json.JSONDecodeError as e:
            log_file.write(f"[JSON_ERR] {row['Question ID']} attempt {attempt+1}: {str(e)} | raw={raw[:100]}\n")
            if attempt < RETRY_ATTEMPTS - 1:
                time.sleep(2)
        except anthropic.RateLimitError:
            log_file.write(f"[RATE_LIMIT] {row['Question ID']} attempt {attempt+1} — waiting {RETRY_DELAY}s\n")
            time.sleep(RETRY_DELAY)
        except Exception as e:
            log_file.write(f"[ERROR] {row['Question ID']} attempt {attempt+1}: {str(e)}\n")
            if attempt < RETRY_ATTEMPTS - 1:
                time.sleep(2)

    # All attempts failed
    return {
        'BlueprintCategory': 'ERROR',
        'Subcategory': 'ERROR',
        'QuestionType': 'ERROR',
        'ClinicalFocus': 'ERROR',
        'Confidence': 'Low'
    }


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set.\nRun: export ANTHROPIC_API_KEY='your-key-here'")

    print(f"Loading {INPUT_CSV}...")
    df = pd.read_csv(INPUT_CSV)
    print(f"Loaded {len(df)} questions")

    # Initialize new columns
    for col in ['AI_BlueprintCategory', 'AI_Subcategory', 'AI_QuestionType', 'AI_ClinicalFocus', 'AI_Confidence', 'AI_Source']:
        if col not in df.columns:
            df[col] = ''

    # Check for already-tagged rows (allows resuming interrupted runs)
    already_tagged = df[df['AI_Source'] == 'Claude-AI'].shape[0]
    if already_tagged > 0:
        print(f"Resuming — {already_tagged} questions already tagged, skipping those")

    client = anthropic.Anthropic(api_key=api_key)

    start_time = datetime.now()
    tagged_count = 0
    error_count = 0

    with open(LOG_FILE, 'a') as log:
        log.write(f"\n=== Run started {start_time} ===\n")
        
        for idx, row in df.iterrows():
            # Skip already tagged
            if df.at[idx, 'AI_Source'] == 'Claude-AI':
                continue

            result = tag_question(client, row, log)
            
            df.at[idx, 'AI_BlueprintCategory'] = result['BlueprintCategory']
            df.at[idx, 'AI_Subcategory']        = result['Subcategory']
            df.at[idx, 'AI_QuestionType']        = result['QuestionType']
            df.at[idx, 'AI_ClinicalFocus']       = result['ClinicalFocus']
            df.at[idx, 'AI_Confidence']          = result['Confidence']
            df.at[idx, 'AI_Source']              = 'Claude-AI'

            if result['BlueprintCategory'] == 'ERROR':
                error_count += 1
            else:
                tagged_count += 1

            # Progress update every 50 questions
            if (tagged_count + error_count) % 50 == 0:
                elapsed = (datetime.now() - start_time).seconds
                total_done = tagged_count + error_count
                rate = total_done / elapsed if elapsed > 0 else 0
                remaining = len(df) - already_tagged - total_done
                eta_min = (remaining / rate / 60) if rate > 0 else 0
                print(f"  Progress: {total_done}/{len(df) - already_tagged} | "
                      f"errors: {error_count} | "
                      f"~{eta_min:.1f} min remaining")
                
                # Save checkpoint every 50 questions
                df.to_csv(OUTPUT_CSV, index=False)

            time.sleep(RATE_LIMIT_DELAY)

        log.write(f"=== Run finished {datetime.now()} | tagged={tagged_count} | errors={error_count} ===\n")

    # Final save
    df.to_csv(OUTPUT_CSV, index=False)
    
    elapsed_total = (datetime.now() - start_time).seconds / 60
    print(f"\n✓ Done! {tagged_count} questions tagged, {error_count} errors")
    print(f"  Time: {elapsed_total:.1f} minutes")
    print(f"  Output: {OUTPUT_CSV}")
    print(f"  Log:    {LOG_FILE}")

    # Quick summary
    print("\n=== Tag Distribution Summary ===")
    print("\nBlueprintCategory:")
    print(df['AI_BlueprintCategory'].value_counts().to_string())
    print("\nQuestionType:")
    print(df['AI_QuestionType'].value_counts().to_string())
    print("\nConfidence:")
    print(df['AI_Confidence'].value_counts().to_string())


if __name__ == "__main__":
    main()
