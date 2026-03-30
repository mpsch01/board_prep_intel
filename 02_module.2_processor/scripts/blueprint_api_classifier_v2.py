#!/usr/bin/env python3
"""
blueprint_api_classifier_v2.py
Classifies ITE exam questions into ABFM blueprint categories.

Improvements over v1:
  - Full rubric from official 2025 gold-standard methodology
  - 19 real gold-standard few-shot examples (incl. 9 diagnostic edge cases)
  - Priority ordering resolves Foundations > Emergent > Chronic > Preventive > Acute
  - Classify by clinical JOB, not organ system or topic
  - Honest variance — no forced distribution

Usage:
    python blueprint_api_classifier_v2.py --input <xlsx> --output <xlsx>
    python blueprint_api_classifier_v2.py  # uses defaults

Requires: ANTHROPIC_API_KEY in environment
"""

import os
import sys
import json
import re
import time
import sqlite3
import argparse
import pandas as pd
from pathlib import Path

# ── Script location / project root ────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"

# ── Defaults ───────────────────────────────────────────────────────────────────
DEFAULT_INPUT  = PROJECT_ROOT / "02_module.2_processor" / "source" / "2020-2023_no_blueprint.xlsx"
DEFAULT_OUTPUT = PROJECT_ROOT / "02_module.2_processor" / "source" / "blueprint_classifications_v2.xlsx"
MODEL          = "claude-sonnet-4-6"
BATCH_SIZE     = 10          # questions per API call
SLEEP_SECONDS  = 1.0         # between batches (rate-limit courtesy)
MAX_RETRIES    = 3

# ── Category labels ────────────────────────────────────────────────────────────
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
  Example: a cervical cancer question about leading a QI project = Foundations (not Preventive).
  Example: a cardiology question asking to calculate NNT = Foundations (not Acute).

Step 2 → EMERGENT second
  If management cannot safely wait — ED transfer, admission, stabilization,
  same-day safety decision, hemodynamic instability, time-sensitive postexposure care
  → Emergent and Urgent Care.
  This wins over Preventive when prevention is postexposure and time-sensitive.
  Example: post-sexual assault HIV PEP + emergency contraception = Emergent (not Preventive).
  Example: positive suicidality screen requiring immediate risk evaluation = Emergent (not Chronic).

Step 3 → CHRONIC third
  If the patient already has an ESTABLISHED disease or KNOWN abnormality, AND the
  question is about long-term follow-up, surveillance, medication adjustment, monitoring
  complications, or secondary prevention → Chronic Care Management.
  This wins over Preventive when "screening" is really surveillance within existing disease.
  Example: annual monitoring in HIV on HAART = Chronic (not Preventive).
  Example: colonoscopy interval after prior adenomas = Chronic (not Preventive) — the known
           lesion makes it surveillance, not average-risk screening.

Step 4 → PREVENTIVE fourth
  If the main task is screening, vaccination, counseling, prophylaxis, anticipatory guidance,
  sports clearance, or risk reduction in a STABLE patient WITHOUT an established disease
  driving the question → Preventive Care.

Step 5 → ACUTE (default)
  Otherwise: initial diagnosis, first workup, first-line treatment of a current complaint
  → Acute Care and Diagnosis.
  CRITICAL NUANCE: Long symptom duration does NOT make a question Chronic.
  If the question asks for the first proper evaluation of a complaint — even if that complaint
  has been present for months or years — the official label is still Acute Care and Diagnosis.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
KEY TIE-BREAKERS (from official gold-standard labels):
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
Question: A new lipid-lowering drug yields an ARR of 0.04 for acute MI (event rate 0.085 vs 0.045). Which one of the following is the number needed to treat (NNT)?
Correct answer: B (25)
Category: Foundations of Care
Why: Cardiology topic but the task is a pure statistics calculation (NNT = 1/ARR) — evidence reasoning wins over the clinical backdrop.

EXAMPLE — Item 139
Question: How long after intranasal administration does naloxone reach peak plasma concentrations?
Correct answer: D (15–30 minutes)
Category: Foundations of Care
Why: No clinical scenario, no diagnosis or management — pure pharmacokinetic knowledge question.

EXAMPLE — Item 196
Question: An 84-year-old male with mild cognitive impairment is admitted for a hip fracture and is clearly unable to articulate understanding of his situation. Which one of the following is the most appropriate decision-maker?
Correct answer: C (Durable power of attorney for health care)
Category: Foundations of Care
Why: The task is identifying the correct surrogate decision-maker — medical ethics and legal framework.

EXAMPLE — Item 89
Question: A 5-year-old is brought to the ED after falling from a kitchen table, landing on his right head, with one episode of vomiting. On exam he is tearful but consolable. Which one of the following is the most appropriate management?
Correct answer: A (Reassurance and outpatient observation)
Category: Emergent and Urgent Care
Why: Active safety assessment and disposition decision (admit vs. observe) in the ED — time-sensitive, urgent setting.

EXAMPLE — Item 28
Question: A 46-year-old presents for acute low back pain. During triage, PHQ-2 is positive; PHQ-9 is administered and the patient screens positive for thoughts of being better off dead. Which one of the following is the most appropriate next step?
Correct answer: A (Evaluate suicidal ideation including plan, means, and risk)
Category: Emergent and Urgent Care
Why: This looks like a depression visit but the real task is same-day safety assessment — urgent risk evaluation with possible inpatient disposition.

EXAMPLE — Item 68
Question: A 23-year-old female presents after a sexual assault the prior evening. She is up to date on vaccinations. Which one of the following is the most appropriate management?
Correct answer: D (Empiric STI treatment, HIV PEP, emergency contraception)
Category: Emergent and Urgent Care
Why: HIV PEP, emergency contraception, and empiric STI treatment are all postexposure and time-sensitive — urgency wins over the preventive framing.

EXAMPLE — Item 10
Question: A 45-year-old male living with HIV, on HAART for 10 years, presents for routine follow-up. Which one of the following would be part of an appropriate screening strategy for long-term HAART complications?
Correct answer: E (Annual urinalysis + twice-yearly GFR)
Category: Chronic Care Management
Why: Established HIV on long-term antiretroviral therapy — the question asks about surveillance for drug toxicity within ongoing disease management; known disease beats screening language.

EXAMPLE — Item 29
Question: A 58-year-old had a screening colonoscopy 3 years ago with 2 tubular adenomas (6 mm and 8 mm) removed. When should the next colonoscopy be performed?
Correct answer: E (7–10 years)
Category: Chronic Care Management
Why: Surveillance interval after prior adenomas — the known lesion makes this follow-up within a known abnormality, not average-risk screening.

EXAMPLE — Item 53
Question: A 14-year-old with asthma uses albuterol as needed and has symptoms 3–4 days per week with mildly reduced lung function. Based on GINA guidelines, which one of the following is the most appropriate management?
Correct answer: C (Add daily inhaled corticosteroid)
Category: Chronic Care Management
Why: Established asthma requiring step-up in controller therapy — ongoing management of a known chronic condition.

EXAMPLE — Item 60
Question: You are seeing a patient at 12 weeks' gestation with a family history of neural tube defects, taking 4 mg high-dose folic acid. Which one of the following should you recommend regarding her folic acid supplementation?
Correct answer: C (Continue 4 mg through 12 weeks, then reduce to 0.4–0.8 mg for the remainder)
Category: Chronic Care Management
Why: Ongoing prenatal management decision within an established pregnancy — longitudinal care, not initial evaluation.

EXAMPLE — Item 39
Question: A 17-year-old with well-controlled diabetes presents for sports preparticipation evaluation before soccer. Which one of the following, if present, would be the most important reason to restrict participation?
Correct answer: B (Enlarged spleen)
Category: Preventive Care
Why: Sports clearance exam — ambulatory risk assessment to determine safe participation; preventive function even in a patient with a known diagnosis.

EXAMPLE — Item 27
Question: A 67-year-old female has not had a Pap test in 15 years and has no history of abnormal cytology. According to USPSTF guidelines, which one of the following is the most appropriate recommendation?
Correct answer: E (Cervical cancer screening should be performed)
Category: Preventive Care
Why: Standard preventive screening in a healthy ambulatory patient with no prior adequate screening.

EXAMPLE — Item 124
Question: A 3-day-old infant presents for a routine check-up. Parents report fewer wet diapers than expected. On exam the infant appears slightly lethargic with dry skin. Which one of the following is the most reliable clinical sign for assessing dehydration?
Correct answer: A (Capillary refill time)
Category: Preventive Care
Why: Well-child check at a scheduled visit — routine newborn assessment, preventive care setting.

EXAMPLE — Item 8
Question: A 60-year-old female presents because she is concerned about urinary leakage that started a couple of years ago and has worsened. Leakage occurs when she coughs or laughs but also if she waits too long. Which one of the following is the most appropriate next step in evaluation?
Correct answer: B (Urinalysis)
Category: Acute Care and Diagnosis
Why: Even though symptoms have been present for years, the question asks for the INITIAL evaluation step — first workup beats symptom duration.

EXAMPLE — Item 30
Question: A 27-year-old G1P0 at 38 weeks presents for prenatal care. You discuss the risks and benefits of induction at 39 weeks (ARRIVE trial: induction had lower cesarean rate without increased neonatal morbidity). Which one of the following is the most appropriate recommendation?
Correct answer: D (Offer induction at 39 weeks)
Category: Acute Care and Diagnosis
Why: Trial data is used to answer a concrete current management question — clinical decision, not a statistics task; Acute beats Foundations here.

EXAMPLE — Item 6
Question: According to AGA guidelines, which one of the following is recommended as the best pharmacologic treatment of typical symptoms in diarrhea-predominant irritable bowel syndrome?
Correct answer: E (Rifaximin)
Category: Acute Care and Diagnosis
Why: Initial treatment selection for a current complaint based on current guidelines — no prior established management plan.

EXAMPLE — Item 69
Question: A 29-year-old female with a long-standing history of depressed mood, headaches, and irritability in the 1–2 weeks before menses presents for evaluation. Which one of the following is the most appropriate initial treatment?
Correct answer: B (Calcium carbonate 1000–1200 mg daily)
Category: Acute Care and Diagnosis
Why: Initial treatment decision for a current complaint (premenstrual syndrome) — new evaluation and management, not ongoing monitoring.

EXAMPLE — Item 107
Question: A 28-year-old male who uses cannabis daily has a 2-week history of persistent nausea and vomiting with relief during hot showers. While tapering cannabis, which one of the following would be most likely to resolve symptoms?
Correct answer: B (Haloperidol)
Category: Acute Care and Diagnosis
Why: Initial treatment decision for cannabinoid hyperemesis syndrome — first-line treatment of a current episodic complaint.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT — respond with valid JSON only, no extra text:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{
  "results": [
    {
      "question_id": "Q2020-001",
      "blueprint_category": "<one of the five exact category names>",
      "confidence": "<High|Medium|Low>",
      "justification": "<one sentence explaining the key signal that determined the category>"
    }
  ]
}

Confidence guidelines:
- High: The dominant category is clearly correct; rubric steps 1-4 give a clear winner.
- Medium: Two categories are plausible but one is more consistent with the gold-standard labeling behavior.
- Low: Genuine ambiguity — two categories have a real claim; flag for human review.
"""

def derive_db_qid(workbook_qid: str, year: int) -> str:
    """Map workbook-local IDs to the durable DB qid convention."""
    seq_num = int(str(workbook_qid).split("-")[-1])
    offset = (year - 2020) * 200
    db_qnum = seq_num - offset
    return f"QID-{year}-{db_qnum:04d}"


def normalize_text(text: str) -> str:
    """Normalize text for lightweight workbook/DB consistency checks."""
    collapsed = re.sub(r"\s+", " ", (text or "").strip()).lower()
    return re.sub(r"[^a-z0-9]+", "", collapsed)


def text_matches_db(workbook_text: str, db_text: str) -> bool:
    """Return True when the workbook row clearly corresponds to the DB row."""
    workbook_norm = normalize_text(workbook_text)
    db_norm = normalize_text(db_text)
    if not workbook_norm or not db_norm:
        return False
    probe_len = min(120, len(workbook_norm), len(db_norm))
    if probe_len < 40:
        return False
    return (
        workbook_norm.startswith(db_norm[:probe_len]) or
        db_norm.startswith(workbook_norm[:probe_len]) or
        workbook_norm[:probe_len] in db_norm or
        db_norm[:probe_len] in workbook_norm
    )


def attach_db_qids(df: pd.DataFrame) -> pd.DataFrame:
    """Attach durable DB qids to workbook rows and flag unmatched rows."""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("""
        SELECT qid, exam_year, question_text
        FROM questions
        WHERE exam_year BETWEEN 2020 AND 2023
    """).fetchall()
    conn.close()

    db_rows = {qid: {"year": year, "question_text": question_text or ""} for qid, year, question_text in rows}
    out = df.copy()
    db_qids = []
    statuses = []

    for _, row in out.iterrows():
        year = int(row["year"])
        db_qid = derive_db_qid(row["question_id"], year)
        db_row = db_rows.get(db_qid)
        if not db_row:
            db_qids.append("")
            statuses.append("missing_in_db")
            continue

        db_qids.append(db_qid)
        status = "matched" if text_matches_db(row["question_text"], db_row["question_text"]) else "text_mismatch"
        statuses.append(status)

    out["db_qid"] = db_qids
    out["db_match_status"] = statuses
    return out


def parse_xlsx(path: Path) -> pd.DataFrame:
    """Parse the input xlsx into a clean DataFrame."""
    raw = pd.read_excel(path, header=None)
    # Columns: 0=QID, 1=Year, 2=QuestionText+Choices, 3=CorrectAnswer, 4-5=blank, 6=Rationale
    df = pd.DataFrame({
        "question_id":  raw.iloc[:, 0].astype(str),
        "year":         raw.iloc[:, 1].astype(int),
        "question_text": raw.iloc[:, 2].astype(str),
        "correct_answer": raw.iloc[:, 3].astype(str),
        "rationale":    raw.iloc[:, 6].fillna("").astype(str),
    })
    # Infer question number from QID (e.g. Q2020-001 → 1)
    df["question_number"] = df["question_id"].str.extract(r'-(\d+)$').astype(int, errors='ignore')
    return attach_db_qids(df)


def build_user_message(batch: pd.DataFrame) -> str:
    """Build the user message for a batch of questions."""
    lines = [f"Classify the following {len(batch)} ITE exam question(s) into their ABFM blueprint categories.\n"]
    for _, row in batch.iterrows():
        q_text = str(row["question_text"]).replace('\n', ' ').strip()
        rationale = str(row["rationale"]).replace('\n', ' ').strip()
        lines.append(
            f"--- QUESTION ID: {row['question_id']} ---\n"
            f"STEM + CHOICES: {q_text[:1200]}\n"
            f"CORRECT ANSWER: {row['correct_answer']}\n"
            f"CRITIQUE/RATIONALE: {rationale[:600]}\n"
        )
    lines.append('\nRespond with valid JSON only.')
    return '\n'.join(lines)


def call_api(client, user_message: str, attempt: int = 0) -> list[dict]:
    """Call the Claude API and parse the JSON response."""
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}]
        )
        content = response.content[0].text.strip()
        # Strip markdown code fences if present
        content = re.sub(r'^```(?:json)?\s*', '', content)
        content = re.sub(r'\s*```$', '', content)
        parsed = json.loads(content)
        return parsed.get("results", [])
    except json.JSONDecodeError as e:
        if attempt < MAX_RETRIES:
            print(f"  JSON parse error (attempt {attempt+1}/{MAX_RETRIES}): {e}")
            time.sleep(2)
            return call_api(client, user_message, attempt + 1)
        raise
    except Exception as e:
        if attempt < MAX_RETRIES and "rate" in str(e).lower():
            wait = 60 * (attempt + 1)
            print(f"  Rate limit hit - waiting {wait}s...")
            time.sleep(wait)
            return call_api(client, user_message, attempt + 1)
        raise


def validate_category(cat: str) -> str:
    """Snap to exact category name; return 'REVIEW' if unrecognized."""
    exact = {c.lower(): c for c in CATEGORIES}
    return exact.get(cat.strip().lower(), f"REVIEW: {cat}")


def main():
    parser = argparse.ArgumentParser(description="ABFM ITE Blueprint Classifier v2")
    parser.add_argument("--input",  type=Path, default=DEFAULT_INPUT,  help="Input xlsx path")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output xlsx path")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE,  help="Questions per API call")
    parser.add_argument("--start-row",  type=int, default=0,           help="Resume from row N (0-indexed)")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set in environment.")
        sys.exit(1)

    import anthropic
    client = anthropic.Anthropic(api_key=api_key)

    # ── Load input ────────────────────────────────────────────────────────────
    if not args.input.exists():
        # Try uploads folder as fallback
        fallback = Path(__file__).resolve().parent.parent.parent / "uploads" / "2020-2023_no_blueprint.xlsx"
        if fallback.exists():
            args.input = fallback
        else:
            print(f"ERROR: Input file not found: {args.input}")
            sys.exit(1)

    print(f"Loading: {args.input}")
    df = parse_xlsx(args.input)
    print(f"  {len(df)} questions loaded ({df['year'].value_counts().to_dict()})")
    match_counts = df["db_match_status"].value_counts().to_dict()
    print(f"  DB mapping status: {match_counts}")
    unmatched = df[df["db_match_status"] != "matched"]
    if len(unmatched):
        print("  WARNING: some workbook rows do not map cleanly to live DB qids.")
        for _, row in unmatched.head(10).iterrows():
            label = row["db_qid"] or "NO DB QID"
            print(f"    {row['question_id']} -> {label} [{row['db_match_status']}]")

    # ── Resume support ────────────────────────────────────────────────────────
    results = []
    start = args.start_row
    if args.output.exists() and start == 0:
        existing = pd.read_excel(args.output)
        if {"db_qid", "db_match_status"}.issubset(existing.columns):
            start = len(existing)
            results = existing.to_dict('records')
            print(f"  Resuming from row {start} (found existing output with {start} rows)")
        else:
            print("  Existing output uses legacy schema without db_qid; rebuilding from row 0.")

    # ── Process in batches ────────────────────────────────────────────────────
    todo = df.iloc[start:]
    total_batches = (len(todo) + args.batch_size - 1) // args.batch_size
    print(f"\nClassifying {len(todo)} questions in {total_batches} batches of {args.batch_size}...")
    print(f"Model: {MODEL}\n")

    for batch_idx in range(total_batches):
        row_start = batch_idx * args.batch_size
        batch = todo.iloc[row_start: row_start + args.batch_size]
        global_start = start + row_start
        print(f"Batch {batch_idx+1}/{total_batches} - rows {global_start+1}-{global_start+len(batch)} "
              f"({batch.iloc[0]['question_id']} -> {batch.iloc[-1]['question_id']})")

        user_msg = build_user_message(batch)
        api_results = call_api(client, user_msg)

        # Map by question_id in case order shifts
        api_by_id = {r.get("question_id", ""): r for r in api_results}

        for _, row in batch.iterrows():
            api_r = api_by_id.get(row["question_id"], {})
            cat = validate_category(api_r.get("blueprint_category", "REVIEW: missing"))
            results.append({
                "question_id":       row["question_id"],
                "db_qid":            row["db_qid"],
                "db_match_status":   row["db_match_status"],
                "year":              row["year"],
                "question_number":   row["question_number"],
                "blueprint_category": cat,
                "confidence":        api_r.get("confidence", "Low"),
                "justification":     api_r.get("justification", ""),
                "question_stem":     str(row["question_text"])[:300],
            })

        # Save checkpoint after every batch
        out_df = pd.DataFrame(results)
        out_df.to_excel(args.output, index=False)
        print(f"  Saved checkpoint ({len(results)} total rows)")

        if batch_idx < total_batches - 1:
            time.sleep(SLEEP_SECONDS)

    # ── Final summary ─────────────────────────────────────────────────────────
    out_df = pd.DataFrame(results)
    print(f"\n{'='*60}")
    print(f"DONE - {len(out_df)} questions classified")
    print(f"\nDistribution:")
    dist = out_df["blueprint_category"].value_counts()
    total = len(out_df)
    for cat, n in dist.items():
        print(f"  {cat}: {n} ({n/total*100:.1f}%)")
    print(f"\nConfidence:")
    conf = out_df["confidence"].value_counts()
    for c, n in conf.items():
        print(f"  {c}: {n}")
    print(f"\nOutput saved: {args.output}")


if __name__ == "__main__":
    main()
