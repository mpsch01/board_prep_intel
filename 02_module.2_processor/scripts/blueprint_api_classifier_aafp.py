#!/usr/bin/env python3
"""
blueprint_api_classifier_aafp.py
=================================
Classifies AAFP Board Review Questions into ABFM blueprint categories
using the Anthropic Batch API (async, 50% cost vs real-time).

Same rubric and 19 gold-standard few-shot examples as blueprint_api_classifier_v2.py.
Source: aafp_questions (stem + choices + correct_letter + explanation) — all from DB.
Output: 02_module.2_processor/source/blueprint_classifications_aafp.xlsx

Usage:
    python blueprint_api_classifier_aafp.py --wait      # submit + poll + retrieve in one shot (recommended)

    python blueprint_api_classifier_aafp.py --submit    # build + submit batch → saves batch_id
    python blueprint_api_classifier_aafp.py --poll      # check processing status
    python blueprint_api_classifier_aafp.py --retrieve  # download results → writes xlsx

Then write to DB:
    python write_blueprint_aafp_to_db.py --live

Requires: ANTHROPIC_API_KEY in environment
"""

import os
import sys
import json
import re
import sqlite3
import argparse
import time
import pandas as pd
from pathlib import Path
from datetime import datetime

# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR    = Path(__file__).resolve().parent
PROJECT_ROOT  = SCRIPT_DIR.parent.parent
DB_PATH       = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"
OUTPUT_XLSX   = PROJECT_ROOT / "02_module.2_processor" / "source" / "blueprint_classifications_aafp.xlsx"
STATE_FILE    = PROJECT_ROOT / "02_module.2_processor" / "source" / "blueprint_aafp_batch_state.json"

MODEL      = "claude-sonnet-4-6"
BATCH_SIZE = 10   # questions per API request within the batch

CATEGORIES = [
    "Acute Care and Diagnosis",
    "Chronic Care Management",
    "Emergent and Urgent Care",
    "Preventive Care",
    "Foundations of Care",
]

# ── System prompt ──────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are an expert classifier for the American Board of Family Medicine (ABFM) In-Training Examination (ITE). Your task is to assign each question to its correct ABFM blueprint category.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CORE PRINCIPLE: Classify by the CLINICAL JOB, not the organ system or topic.
A cardiology question can be Acute, Chronic, Emergent, Preventive, or Foundations
depending on what the clinician is actually being asked to DO.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CATEGORY DEFINITIONS (official ABFM language):

1. Acute Care and Diagnosis
   Questions from scenarios in normal ambulatory clinic practice where you provide
   next steps in diagnosis, the correct diagnosis, or the initial treatment.

2. Chronic Care Management
   Questions from ambulatory or long-term care settings about ongoing management
   of a chronic disease (surveillance, medication adjustment, monitoring complications,
   secondary prevention, long-term follow-up).

3. Emergent and Urgent Care
   Questions from hospital, ED, urgent care, or ambulatory settings where you make
   patient management decisions needed within hours — stabilization, transfer,
   admission, immediate safety assessment, time-sensitive postexposure care.

4. Preventive Care
   Questions about prevention in the ambulatory setting — screening, immunization,
   prophylaxis, counseling, anticipatory guidance, sports/participation clearance,
   risk reduction in a stable patient without an established disease driving the question.

5. Foundations of Care
   Questions about quality improvement, evidence-based medicine (statistics, NNT,
   ARR, bias), ethics, legal issues, health policy, health equity, or health systems.
   The clinical topic is secondary — the task is reasoning about systems or evidence.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DECISION RUBRIC — apply in this priority order:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step 1 → FOUNDATIONS first
  If the stem is primarily about QI, statistics, ethics, legal issues, bias,
  health systems, or evidence interpretation → Foundations of Care.
  This wins even when the clinical topic sounds like something else.

Step 2 → EMERGENT second
  If management cannot safely wait — ED transfer, admission, stabilization,
  same-day safety decision, hemodynamic instability, time-sensitive postexposure care
  → Emergent and Urgent Care.

Step 3 → CHRONIC third
  If the patient already has an ESTABLISHED disease or KNOWN abnormality, AND the
  question is about long-term follow-up, surveillance, medication adjustment, monitoring
  complications, or secondary prevention → Chronic Care Management.

Step 4 → PREVENTIVE fourth
  If the main task is screening, vaccination, counseling, prophylaxis, anticipatory guidance,
  sports clearance, or risk reduction in a STABLE patient WITHOUT an established disease
  driving the question → Preventive Care.

Step 5 → ACUTE (default)
  Otherwise: initial diagnosis, first workup, first-line treatment of a current complaint
  → Acute Care and Diagnosis.
  CRITICAL NUANCE: Long symptom duration does NOT make a question Chronic.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
KEY TIE-BREAKERS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Statistics/QI task beats clinical topic → Foundations
• Time sensitivity beats prevention framing → Emergent
• Known disease beats screening language → Chronic
• First workup beats symptom duration → Acute

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GOLD-STANDARD EXAMPLES (from official 2025 ABFM ITE with verified labels):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EXAMPLE — Item 1
Question: Your practice management team has reviewed clinic-wide cancer screening rates and found that cervical cancer screening has fallen behind. You are asked to lead a quality improvement project to increase rates of cervical cancer screening for appropriate patients. Which one of the following would be the most appropriate first step?
Correct answer: B (Evaluating barriers to cervical cancer screening and reporting)
Category: Foundations of Care
Why: The topic is cervical cancer screening, but the actual task is leading a QI project — systems reasoning wins over the preventive topic.

EXAMPLE — Item 41
Question: A new lipid-lowering drug yields an ARR of 0.04 for acute MI. Which one of the following is the number needed to treat (NNT)?
Correct answer: B (25)
Category: Foundations of Care
Why: Pure statistics calculation — evidence reasoning wins over the clinical backdrop.

EXAMPLE — Item 139
Question: How long after intranasal administration does naloxone reach peak plasma concentrations?
Correct answer: D (15–30 minutes)
Category: Foundations of Care
Why: No clinical scenario — pure pharmacokinetic knowledge question.

EXAMPLE — Item 196
Question: An 84-year-old male with mild cognitive impairment is admitted for a hip fracture and is clearly unable to articulate understanding of his situation. Which one of the following is the most appropriate decision-maker?
Correct answer: C (Durable power of attorney for health care)
Category: Foundations of Care
Why: Medical ethics and legal framework — surrogate decision-maker identification.

EXAMPLE — Item 89
Question: A 5-year-old is brought to the ED after falling from a kitchen table, landing on his right head, with one episode of vomiting. On exam he is tearful but consolable. Which one of the following is the most appropriate management?
Correct answer: A (Reassurance and outpatient observation)
Category: Emergent and Urgent Care
Why: Safety assessment and disposition decision in the ED — time-sensitive, urgent setting.

EXAMPLE — Item 28
Question: A 46-year-old presents for acute low back pain. PHQ-9 screens positive for thoughts of being better off dead. Which one of the following is the most appropriate next step?
Correct answer: A (Evaluate suicidal ideation including plan, means, and risk)
Category: Emergent and Urgent Care
Why: Same-day safety assessment — urgent risk evaluation with possible inpatient disposition.

EXAMPLE — Item 68
Question: A 23-year-old female presents after a sexual assault the prior evening. Which one of the following is the most appropriate management?
Correct answer: D (Empiric STI treatment, HIV PEP, emergency contraception)
Category: Emergent and Urgent Care
Why: Time-sensitive postexposure care — urgency wins over preventive framing.

EXAMPLE — Item 10
Question: A 45-year-old male living with HIV, on HAART for 10 years, presents for routine follow-up. Which one of the following would be part of an appropriate screening strategy for long-term HAART complications?
Correct answer: E (Annual urinalysis + twice-yearly GFR)
Category: Chronic Care Management
Why: Established HIV on long-term therapy — surveillance for drug toxicity within ongoing disease management.

EXAMPLE — Item 29
Question: A 58-year-old had a screening colonoscopy 3 years ago with 2 tubular adenomas removed. When should the next colonoscopy be performed?
Correct answer: E (7–10 years)
Category: Chronic Care Management
Why: Known lesion makes this surveillance within existing disease, not average-risk screening.

EXAMPLE — Item 53
Question: A 14-year-old with asthma has symptoms 3–4 days per week with mildly reduced lung function. Which one of the following is the most appropriate management?
Correct answer: C (Add daily inhaled corticosteroid)
Category: Chronic Care Management
Why: Established asthma requiring step-up — ongoing management of a known chronic condition.

EXAMPLE — Item 60
Question: You are seeing a patient at 12 weeks' gestation with a family history of neural tube defects, taking 4 mg high-dose folic acid. Which one of the following should you recommend?
Correct answer: C (Continue 4 mg through 12 weeks, then reduce to 0.4–0.8 mg)
Category: Chronic Care Management
Why: Ongoing prenatal management within an established pregnancy — longitudinal care.

EXAMPLE — Item 39
Question: A 17-year-old with well-controlled diabetes presents for sports preparticipation evaluation. Which one of the following would be the most important reason to restrict participation?
Correct answer: B (Enlarged spleen)
Category: Preventive Care
Why: Sports clearance exam — ambulatory risk assessment for safe participation.

EXAMPLE — Item 27
Question: A 67-year-old female has not had a Pap test in 15 years and has no history of abnormal cytology. Which one of the following is the most appropriate recommendation?
Correct answer: E (Cervical cancer screening should be performed)
Category: Preventive Care
Why: Standard preventive screening in a healthy ambulatory patient.

EXAMPLE — Item 124
Question: A 3-day-old infant presents for a routine check-up. Parents report fewer wet diapers. On exam the infant appears slightly lethargic with dry skin. Which one of the following is the most reliable clinical sign for assessing dehydration?
Correct answer: A (Capillary refill time)
Category: Preventive Care
Why: Well-child check at a scheduled visit — preventive care setting.

EXAMPLE — Item 8
Question: A 60-year-old female presents because she is concerned about urinary leakage that started a couple of years ago. Which one of the following is the most appropriate next step in evaluation?
Correct answer: B (Urinalysis)
Category: Acute Care and Diagnosis
Why: Initial evaluation step — first workup beats symptom duration.

EXAMPLE — Item 30
Question: A 27-year-old G1P0 at 38 weeks presents for prenatal care. You discuss the risks and benefits of induction at 39 weeks (ARRIVE trial). Which one of the following is the most appropriate recommendation?
Correct answer: D (Offer induction at 39 weeks)
Category: Acute Care and Diagnosis
Why: Concrete current management decision — clinical judgment, not a statistics task.

EXAMPLE — Item 6
Question: According to AGA guidelines, which one of the following is recommended as the best pharmacologic treatment of diarrhea-predominant irritable bowel syndrome?
Correct answer: E (Rifaximin)
Category: Acute Care and Diagnosis
Why: Initial treatment selection for a current complaint.

EXAMPLE — Item 69
Question: A 29-year-old female with a long-standing history of depressed mood and irritability in the 1–2 weeks before menses presents for evaluation. Which one of the following is the most appropriate initial treatment?
Correct answer: B (Calcium carbonate 1000–1200 mg daily)
Category: Acute Care and Diagnosis
Why: Initial treatment decision for a current complaint — not ongoing monitoring.

EXAMPLE — Item 107
Question: A 28-year-old male who uses cannabis daily has a 2-week history of persistent nausea and vomiting with relief during hot showers. Which one of the following would be most likely to resolve symptoms?
Correct answer: B (Haloperidol)
Category: Acute Care and Diagnosis
Why: Initial treatment of cannabinoid hyperemesis syndrome — first-line management of a current complaint.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT — respond with valid JSON only, no extra text:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{
  "results": [
    {
      "question_id": "AAFP-49733",
      "blueprint_category": "<one of the five exact category names>",
      "confidence": "<High|Medium|Low>",
      "justification": "<one sentence explaining the key signal that determined the category>"
    }
  ]
}
"""


# ── Helpers ────────────────────────────────────────────────────────────────────

def load_questions() -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT aafp_qid, stem, choices, correct_letter, correct_text, explanation "
        "FROM aafp_questions ORDER BY aafp_qid",
        conn
    )
    conn.close()
    return df


def format_choices(choices_json: str, correct_letter: str) -> str:
    try:
        choices = json.loads(choices_json or "[]")
        lines = []
        for c in choices:
            marker = " ← CORRECT" if c.get("letter") == correct_letter else ""
            lines.append(f"  {c['letter']}) {c['text']}{marker}")
        return "\n".join(lines) if lines else "(choices not available)"
    except Exception:
        return "(choices parse error)"


def build_user_message(batch_df: pd.DataFrame) -> str:
    lines = [f"Classify the following {len(batch_df)} AAFP Board Review Question(s) into their ABFM blueprint categories.\n"]
    for _, row in batch_df.iterrows():
        stem = str(row["stem"]).replace('\n', ' ').strip()
        choices_text = format_choices(row["choices"], row["correct_letter"])
        explanation  = str(row["explanation"] or "").replace('\n', ' ').strip()
        lines.append(
            f"--- QUESTION ID: {row['aafp_qid']} ---\n"
            f"STEM: {stem[:1000]}\n"
            f"CHOICES:\n{choices_text}\n"
            f"EXPLANATION: {explanation[:600]}\n"
        )
    lines.append('\nRespond with valid JSON only.')
    return '\n'.join(lines)


def validate_category(cat: str) -> str:
    exact = {c.lower(): c for c in CATEGORIES}
    return exact.get(cat.strip().lower(), f"REVIEW: {cat}")


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2))


# ── Mode: SUBMIT ───────────────────────────────────────────────────────────────

def do_submit(client):
    state = load_state()
    if state.get("batch_id"):
        print(f"Batch already submitted: {state['batch_id']}")
        print(f"Status at submission: {state.get('status', 'unknown')}")
        print("Run --poll to check progress, or delete the state file to resubmit.")
        return

    df = load_questions()
    print(f"Loaded {len(df)} questions from DB.")

    # Build one API request per group of BATCH_SIZE questions
    requests = []
    for i in range(0, len(df), BATCH_SIZE):
        chunk = df.iloc[i: i + BATCH_SIZE]
        custom_id = f"chunk_{i:04d}"   # e.g. chunk_0000, chunk_0010
        requests.append({
            "custom_id": custom_id,
            "params": {
                "model":      MODEL,
                "max_tokens": 4096,
                "system":     SYSTEM_PROMPT,
                "messages":   [{"role": "user", "content": build_user_message(chunk)}],
            }
        })

    print(f"Submitting {len(requests)} requests to Batch API ({len(df)} questions, {BATCH_SIZE}/request)...")

    batch = client.messages.batches.create(requests=requests)

    state = {
        "batch_id":       batch.id,
        "submitted_at":   datetime.utcnow().isoformat(),
        "total_questions": len(df),
        "total_requests":  len(requests),
        "status":         batch.processing_status,
    }
    save_state(state)

    print(f"\n✓ Batch submitted.")
    print(f"  batch_id:  {batch.id}")
    print(f"  requests:  {len(requests)}")
    print(f"  questions: {len(df)}")
    print(f"\nRun --poll to check status.")


# ── Mode: POLL ─────────────────────────────────────────────────────────────────

def do_poll(client):
    state = load_state()
    if not state.get("batch_id"):
        print("No batch found. Run --submit first.")
        return

    batch_id = state["batch_id"]
    batch = client.messages.batches.retrieve(batch_id)

    counts = batch.request_counts
    print(f"Batch ID:   {batch_id}")
    print(f"Status:     {batch.processing_status}")
    print(f"Processing: {counts.processing}")
    print(f"Succeeded:  {counts.succeeded}")
    print(f"Errored:    {counts.errored}")
    print(f"Canceled:   {counts.canceled}")
    print(f"Expired:    {counts.expired}")

    total = state.get("total_requests", "?")
    done  = counts.succeeded + counts.errored + counts.canceled + counts.expired
    print(f"\nProgress:   {done}/{total} requests complete")

    if batch.processing_status == "ended":
        print("\n✓ Batch complete. Run --retrieve to download results.")
    else:
        print("\nStill processing. Check back in a few minutes.")

    # Update state
    state["status"] = batch.processing_status
    save_state(state)


# ── Mode: RETRIEVE ─────────────────────────────────────────────────────────────

def do_retrieve(client):
    state = load_state()
    if not state.get("batch_id"):
        print("No batch found. Run --submit first.")
        return

    batch_id = state["batch_id"]
    batch = client.messages.batches.retrieve(batch_id)

    if batch.processing_status != "ended":
        print(f"Batch not yet complete (status: {batch.processing_status}). Run --poll to check.")
        return

    print(f"Downloading results for batch {batch_id}...")

    # Load original questions to get stem_preview and ID order
    df = load_questions()
    qid_to_row = {row["aafp_qid"]: row for _, row in df.iterrows()}

    # Parse all results
    all_classified = {}   # aafp_qid → result dict
    errors = []

    for result in client.messages.batches.results(batch_id):
        custom_id = result.custom_id
        # Derive chunk start index from custom_id (e.g. "chunk_0010" → 10)
        try:
            chunk_start = int(custom_id.split("_")[1])
        except (IndexError, ValueError):
            chunk_start = 0

        if result.result.type == "succeeded":
            content = result.result.message.content[0].text.strip()
            content = re.sub(r'^```(?:json)?\s*', '', content)
            content = re.sub(r'\s*```$', '', content)
            try:
                parsed = json.loads(content)
                api_results = parsed.get("results", [])
                api_by_id   = {r.get("question_id", ""): r for r in api_results}

                # Map back to the questions in this chunk
                chunk = df.iloc[chunk_start: chunk_start + BATCH_SIZE]
                for _, row in chunk.iterrows():
                    qid   = row["aafp_qid"]
                    api_r = api_by_id.get(qid, {})
                    all_classified[qid] = {
                        "aafp_qid":           qid,
                        "blueprint_category": validate_category(api_r.get("blueprint_category", "REVIEW: missing")),
                        "confidence":         api_r.get("confidence", "Low"),
                        "justification":      api_r.get("justification", ""),
                        "stem_preview":       str(row["stem"])[:200],
                    }
            except (json.JSONDecodeError, Exception) as e:
                errors.append(f"{custom_id}: JSON parse error — {e}")
        else:
            errors.append(f"{custom_id}: {result.result.type}")

    if errors:
        print(f"\nErrors ({len(errors)}):")
        for e in errors:
            print(f"  {e}")

    # Build output in original question order
    rows = [all_classified[qid] for qid in df["aafp_qid"] if qid in all_classified]
    out_df = pd.DataFrame(rows)
    out_df.to_excel(OUTPUT_XLSX, index=False)

    print(f"\n✓ Results retrieved: {len(rows)}/{len(df)} questions")
    print(f"\nDistribution:")
    for cat, n in out_df["blueprint_category"].value_counts().items():
        print(f"  {cat}: {n} ({n/len(out_df)*100:.1f}%)")
    print(f"\nConfidence:")
    for c, n in out_df["confidence"].value_counts().items():
        print(f"  {c}: {n}")
    review = out_df[out_df["blueprint_category"].str.startswith("REVIEW")]
    if len(review):
        print(f"\nREVIEW items ({len(review)}) — inspect before DB write:")
        for _, r in review.iterrows():
            print(f"  {r['aafp_qid']}: {r['blueprint_category']}")

    print(f"\nOutput: {OUTPUT_XLSX}")
    print("\nNext step: python write_blueprint_aafp_to_db.py --live")


# ── Mode: WAIT ─────────────────────────────────────────────────────────────────

def do_wait(client, poll_interval: int = 60):
    """Submit (if needed), poll until complete, then retrieve. One command, walk away."""
    state = load_state()

    # Submit if no batch_id yet
    if not state.get("batch_id"):
        do_submit(client)
        state = load_state()
    else:
        print(f"Existing batch found: {state['batch_id']} — skipping submit, resuming poll.")

    batch_id = state["batch_id"]
    print(f"\nPolling every {poll_interval}s until complete (Ctrl+C to stop and resume later)...\n")

    while True:
        batch = client.messages.batches.retrieve(batch_id)
        counts  = batch.request_counts
        total   = state.get("total_requests", "?")
        done    = counts.succeeded + counts.errored + counts.canceled + counts.expired
        ts      = datetime.utcnow().strftime("%H:%M:%S")

        print(f"  [{ts}] {batch.processing_status} — "
              f"{done}/{total} done  "
              f"(✓{counts.succeeded}  ✗{counts.errored}  ⊘{counts.canceled}  ⌛{counts.expired})")

        state["status"] = batch.processing_status
        save_state(state)

        if batch.processing_status == "ended":
            print("\nBatch complete — retrieving results...\n")
            do_retrieve(client)
            break

        time.sleep(poll_interval)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="AAFP Blueprint Classifier — Batch API")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--wait",     action="store_true", help="Submit + poll + retrieve in one shot (recommended)")
    group.add_argument("--submit",   action="store_true", help="Build and submit the batch")
    group.add_argument("--poll",     action="store_true", help="Check batch status")
    group.add_argument("--retrieve", action="store_true", help="Download results and write xlsx")
    parser.add_argument("--poll-interval", type=int, default=60, help="Seconds between polls in --wait mode (default: 60)")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set.")
        sys.exit(1)

    import anthropic
    client = anthropic.Anthropic(api_key=api_key)

    if args.wait:
        do_wait(client, poll_interval=args.poll_interval)
    elif args.submit:
        do_submit(client)
    elif args.poll:
        do_poll(client)
    elif args.retrieve:
        do_retrieve(client)


if __name__ == "__main__":
    main()
