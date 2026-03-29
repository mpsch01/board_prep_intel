"""
blueprint_api_classifier.py
============================
Batch API-based ABFM Blueprint Category classifier for ITE questions.
Uses Claude few-shot classification on 2024/2025 Gold Standard labels.

METHODOLOGY — Wang et al. 2025 (ABFM / Journal of Applied Testing Technology):
  ABFM achieved 81% accuracy using GPT-4 + 10 few-shot examples per domain.
  This script uses Claude API with 10 examples per domain from our Gold Standard.
  KEY INSIGHT (Table 2): Category = time-urgency of UNDERLYING CONDITION, not
  question format. Appendicitis imaging Q → Emergent because "needs to be
  addressed in next hours to 1-2 days or else harm will happen."

BATCH DESIGN:
  Sends 25 questions per API call (configurable). Single system prompt shared
  across each batch — amortizes the ~4,000-token few-shot payload across 25
  questions. ~9x cheaper than individual calls.

VALIDATION SPLIT:
  --dry-run uses 2024 as few-shot examples, validates on 2025 (no data leakage).
  --write uses all 395 Gold Standard examples as few-shot (maximum signal).

Usage:
  python blueprint_api_classifier.py --estimate-cost       # cost before running
  python blueprint_api_classifier.py --show-examples       # see few-shot pool
  python blueprint_api_classifier.py --dry-run             # validate vs 2025 Gold Standard
  python blueprint_api_classifier.py --dry-run --verbose   # + misclassification detail
  python blueprint_api_classifier.py --year 2022           # preview distribution
  python blueprint_api_classifier.py --write               # apply to 2018-2023 (nulls only)
  python blueprint_api_classifier.py --write --force       # overwrite existing values

Requires: ANTHROPIC_API_KEY environment variable
          pip install anthropic --break-system-packages
"""

import sqlite3
import re
import json
import argparse
import os
import time
import random
from pathlib import Path
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"

GOLD_YEARS     = (2024, 2025)
TARGET_YEARS   = (2018, 2019, 2020, 2021, 2022, 2023)

CATEGORIES = [
    "Acute Care and Diagnosis",
    "Chronic Care Management",
    "Emergent and Urgent Care",
    "Preventive Care",
    "Foundations of Care",
]

# ── Configuration ─────────────────────────────────────────────────────────────
EXAMPLES_PER_CATEGORY  = 10    # few-shot examples per category
DEFAULT_BATCH_SIZE     = 25    # questions per API call
DEFAULT_WORKERS        = 4     # concurrent batch threads
RANDOM_SEED            = 42    # reproducible example selection
DEFAULT_MODEL          = "claude-sonnet-4-6"

MODELS = {
    "haiku":  "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-6",
}

# Pricing per million tokens (2025)
PRICING = {
    "claude-haiku-4-5-20251001": {"input": 0.80,  "output": 4.00},
    "claude-sonnet-4-6":         {"input": 3.00,  "output": 15.00},
}

# ─── SYSTEM PROMPT TEMPLATE ──────────────────────────────────────────────────

SYSTEM_PROMPT_TEMPLATE = """\
You are an expert classifier for ABFM (American Board of Family Medicine) \
board exam questions. Your task is to assign each question to exactly one \
of the 5 ABFM Blueprint Categories.

━━━ CATEGORY DEFINITIONS ━━━

Acute Care and Diagnosis  (35% of exam)
  Setting: Ambulatory/office. Patient presents with a NEW concern.
  Task: Next step in diagnosis, correct diagnosis, or INITIAL treatment.
  Key: NOT time-critical within hours. The condition can safely wait for
  a same-day or next-day appointment. Focus is on RECOGNIZING or DIAGNOSING.
  ⚠ TRAP: Patients with known chronic diseases can still present with NEW
  acute problems. A diabetic with new flank pain → ACUTE, not Chronic.
  Any question centered on ordering a workup or diagnosing a new finding
  is ACUTE, even if the patient carries chronic diagnoses.
  Examples: URI workup, knee pain evaluation, new-onset rash, chest X-ray
  interpretation for an outpatient, new symptom in a patient with diabetes.

Chronic Care Management  (25% of exam)
  Setting: Ambulatory, clinic, or long-term care.
  Task: Ongoing MANAGEMENT of an ESTABLISHED chronic disease — medication
  adjustments, monitoring, titration, complication prevention.
  Key: The diagnosis was established BEFORE this visit. The question is
  about managing it over time, not discovering or diagnosing anything new.
  ⚠ TRAP: Not every question mentioning a drug or chronic disease is Chronic.
  If the visit centers on a NEW symptom, NEW finding, or diagnostic workup —
  even in a patient with chronic disease — it is ACUTE, not Chronic.
  Examples: DM2 A1C management, COPD step-up therapy, follow-up of heart
  failure, osteoporosis treatment, lithium monitoring in known bipolar.

Emergent and Urgent Care  (20% of exam)
  Setting: ED, urgent care, hospital, OR ANY setting when the clinical
  situation demands action within HOURS TO 1–2 DAYS or the patient will
  be harmed.
  Task: Management, stabilization, or referral for time-critical conditions.
  ★ CRITICAL RULE: Category = TIME-URGENCY of the UNDERLYING CONDITION,
  NOT the question format. A diagnostic question about appendicitis IS
  Emergent because appendicitis must be resolved within hours regardless
  of what the question asks about (imaging choice, lab selection, etc.).
  Ask: "Will the patient be HARMED if this isn't addressed within hours
  to 1–2 days?" → YES = Emergent.
  Examples: Appendicitis (any question), STEMI, testicular torsion,
  SAH (worst headache), ectopic pregnancy, orbital cellulitis, DKA management,
  acute cervical spine trauma, sexual assault protocol.

Preventive Care  (15% of exam)
  Setting: Ambulatory, wellness/health maintenance visit.
  Task: Vaccinations, cancer screening recommendations, chemoprophylaxis,
  primary prevention of disease, USPSTF guidelines.
  Key: Patient is ASYMPTOMATIC or presents for preventive services. The
  focus is PREVENTING disease, not treating it.
  Examples: Vaccine schedule, colonoscopy age recommendation, PrEP, DEXA
  screening timing, sports pre-participation physical.

Foundations of Care  (5% of exam)
  Setting: Any. Not disease-specific.
  Task: Biostatistics (NNT, sensitivity/specificity, p-values, RRR),
  health policy (Medicare/Medicaid), medical ethics (informed consent,
  confidentiality, advance directives), health equity, motivational
  interviewing, shared decision-making.
  Key: These are foundational knowledge questions — not tied to managing
  a specific disease or clinical scenario.

━━━ CRITICAL DISTINGUISHING RULES ━━━

ACUTE vs. CHRONIC — The TASK is the discriminator, not the patient background:
  ┌──────────────────────────────────────────────────────────────────┐
  │ CHRONIC: Diagnosis known before visit. Visit = managing it.      │
  │ ACUTE:   The TASK is to DIAGNOSE or WORK UP something new.       │
  └──────────────────────────────────────────────────────────────────┘
  CHRONIC ✓  Known DM2 patient → A1C management, medication adjustment
  CHRONIC ✓  Known COPD → step-up inhaler therapy question
  CHRONIC ✓  Established bipolar disorder → lithium level monitoring
  CHRONIC ✓  Question asks about side-effect or fall-risk profile of a
             patient's EXISTING medication list → the meds are the known
             context; evaluating their risk = chronic management.
  CHRONIC ✓  Post-surgical complication (e.g., dumping syndrome after
             gastric bypass) that will require ongoing management →
             CHRONIC even if patient "presents with" new symptoms.
  ACUTE ✓    New fatigue + weight gain → hypothyroidism workup
  ACUTE ✓    Patient with known HTN → presents with NEW chest pain
  ACUTE ✓    Diabetic patient → new flank pain evaluation
  ACUTE ✓    Critically abnormal lab value (e.g., calcium 12.1 mg/dL,
             potassium 2.5) found incidentally → workup = ACUTE
             regardless of visit type or patient's chronic conditions.
  ACUTE ✓    Question asks to RULE OUT an acute process or select a
             diagnostic test to evaluate a new concern → ACUTE.
  ACUTE ✓    Young patient, ambulatory setting, asking for a diagnostic
             step → ACUTE (age and ambulatory context tip the balance).
  ⚠ KEY: A patient with chronic disease can have an acute problem.
    Focus on what the question is ASKING you to DO — if the task is
    diagnosing or working up something new, classify as ACUTE regardless
    of how many chronic conditions appear in the patient's history.

EMERGENT vs. ACUTE — The 24-hour harm test:
  ┌──────────────────────────────────────────────────────────────────┐
  │ Ask: Would a 24–48 hour delay cause irreversible harm or death?  │
  │ YES → Emergent.  NO → Acute.                                     │
  │ When uncertain: default to ACUTE over Emergent.                  │
  └──────────────────────────────────────────────────────────────────┘
  EMERGENT ✓  Appendicitis (surgical emergency — hours matter)
  EMERGENT ✓  "Worst headache of life" → SAH (even if asking about CT)
  EMERGENT ✓  New LBBB + chest pain → STEMI equivalent
  EMERGENT ✓  Ectopic pregnancy, testicular torsion, orbital cellulitis
  EMERGENT ✓  Hemodynamic instability requiring vasopressors (MAP <65,
             septic shock) — vasopressor selection question = EMERGENT.
  EMERGENT ✓  Respiratory compromise with O2 sat <94% + active treatment
             decision (e.g., pneumothorax management) = EMERGENT.
  ACUTE ✓     New knee pain after a fall (urgent, but hours don't matter)
  ACUTE ✓     Antibiotic choice for otitis media (same-day is fine)
  ⚠ KEY: ED setting does NOT automatically mean Emergent. The
    UNDERLYING CONDITION must be time-critical, not just the setting.
    A question about post-STEMI management (stable, days later) = Chronic.

PREVENTIVE vs. ACUTE — Is the patient ASYMPTOMATIC?
  • Annual physical, vaccine schedule, cancer screening → PREVENTIVE
  • Symptomatic patient + incidental screening question → likely ACUTE

FOUNDATIONS vs. CLINICAL — Is this about a CONCEPT or a DISEASE?
  • "What is the NNT for X?" → FOUNDATIONS
  • "A patient on warfarin, what is the target INR?" → CHRONIC (disease mgmt)

━━━ FEW-SHOT EXAMPLES ━━━

{examples}

━━━ RESPONSE FORMAT ━━━

You will receive a batch of questions, each identified by a number.
Respond with a JSON array containing EXACTLY the category name for each
question, in order. Use ONLY the exact category names listed above.

Example response for a 3-question batch:
["Emergent and Urgent Care", "Chronic Care Management", "Preventive Care"]

No explanation. No extra text. Only the JSON array.
"""


# ─── HELPERS ─────────────────────────────────────────────────────────────────

def extract_concept_summary(concept_tags_json: str) -> str:
    if not concept_tags_json:
        return ""
    try:
        ct = json.loads(concept_tags_json)
        return ct.get("concept_summary", "") or ""
    except Exception:
        return ""


def format_question(question_text: str, concept_summary: str) -> str:
    """Format question + concept summary into a single string for the model."""
    text    = re.sub(r'\s+', ' ', (question_text    or "").strip())
    summary = re.sub(r'\s+', ' ', (concept_summary  or "").strip())
    parts = []
    if text:
        parts.append(f"Question: {text}")
    if summary:
        parts.append(f"Concept summary: {summary}")
    return "\n".join(parts)


# ─── FEW-SHOT EXAMPLE SELECTION ──────────────────────────────────────────────

def select_examples(conn, example_years=GOLD_YEARS,
                    n_per_category=EXAMPLES_PER_CATEGORY, seed=RANDOM_SEED):
    """
    Select n_per_category representative examples per category from Gold Standard.

    Strategy:
    - Prefer concise questions (shorter = cleaner few-shot signal)
    - Fixed random seed for reproducibility
    - Exclude any question whose text is NULL or very short
    """
    rng = random.Random(seed)
    year_clause = ",".join("?" * len(example_years))
    rows = conn.execute(f"""
        SELECT qid, exam_year, question_text, concept_tags, blueprint
        FROM questions
        WHERE exam_year IN ({year_clause})
          AND blueprint IS NOT NULL AND blueprint != ''
          AND question_text IS NOT NULL AND LENGTH(question_text) > 50
        ORDER BY qid
    """, example_years).fetchall()

    by_cat = defaultdict(list)
    for qid, year, text, ct_json, cat in rows:
        cs = extract_concept_summary(ct_json)
        by_cat[cat].append({
            "qid": qid, "year": year,
            "text": text, "summary": cs,
            "formatted": format_question(text, cs),
            "len": len(text),
        })

    selected = {}
    for cat in CATEGORIES:
        pool = sorted(by_cat.get(cat, []), key=lambda x: x["len"])
        # draw from the shorter 60% of examples for conciseness
        cutoff = max(n_per_category, int(len(pool) * 0.6))
        pool = pool[:cutoff]
        chosen = rng.sample(pool, min(n_per_category, len(pool)))
        selected[cat] = sorted(chosen, key=lambda x: x["qid"])

    return selected


def build_examples_block(selected: dict) -> str:
    """Format selected examples into the template {examples} block."""
    lines = []
    for cat in CATEGORIES:
        examples = selected.get(cat, [])
        lines.append(f"─── {cat} ───")
        for ex in examples:
            # Truncate very long examples to keep prompt token cost reasonable
            text_part = ex["formatted"]
            if len(text_part) > 600:
                # Keep question start + full concept summary
                q_lines = text_part.split("\nConcept summary:")
                truncated_q = (q_lines[0][:400] + "...") if len(q_lines[0]) > 400 else q_lines[0]
                text_part = truncated_q + ("\nConcept summary:" + q_lines[1] if len(q_lines) > 1 else "")
            lines.append(text_part)
            lines.append(f"→ {cat}\n")
    return "\n".join(lines)


def build_system_prompt(selected: dict) -> str:
    examples_block = build_examples_block(selected)
    return SYSTEM_PROMPT_TEMPLATE.format(examples=examples_block)


# ─── BATCH CONSTRUCTION & PARSING ────────────────────────────────────────────

def build_batch_message(batch: list[tuple]) -> str:
    """
    Build user message for a batch of (qid, question_text, concept_summary) tuples.
    Each question is numbered 1..N for matching in the response.
    """
    parts = [f"Classify the following {len(batch)} questions.\n"]
    for i, (qid, text, cs) in enumerate(batch, 1):
        formatted = format_question(text, cs)
        parts.append(f"[{i}]\n{formatted}")
    return "\n\n".join(parts)


VALID_LOWER = {c.lower(): c for c in CATEGORIES}

def parse_category(raw: str) -> str:
    """Parse a single category string. Falls back to Acute if unrecognized."""
    s = (raw or "").strip().strip(".,")
    if s in CATEGORIES:
        return s
    lo = s.lower()
    if lo in VALID_LOWER:
        return VALID_LOWER[lo]
    for cat in CATEGORIES:
        if cat.lower() in lo or lo in cat.lower():
            return cat
    if "emergent" in lo or "urgent" in lo:
        return "Emergent and Urgent Care"
    if "chronic" in lo:
        return "Chronic Care Management"
    if "preventive" in lo or "prevention" in lo:
        return "Preventive Care"
    if "foundation" in lo or "statistic" in lo:
        return "Foundations of Care"
    return "Acute Care and Diagnosis"


def parse_batch_response(response_text: str, batch_size: int) -> list[str]:
    """
    Parse the model's JSON array response for a batch.
    Falls back to line-by-line parsing if JSON fails.
    Returns a list of category strings, padded to batch_size with 'Acute'.
    """
    text = (response_text or "").strip()

    # Try JSON array
    try:
        # Extract JSON array from response (model might include preamble)
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            raw_list = json.loads(match.group())
            parsed = [parse_category(str(item)) for item in raw_list]
            if len(parsed) == batch_size:
                return parsed
            # Pad or trim if wrong length
            while len(parsed) < batch_size:
                parsed.append("Acute Care and Diagnosis")
            return parsed[:batch_size]
    except (json.JSONDecodeError, TypeError):
        pass

    # Fallback: extract lines that look like category names
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    # Remove numbered prefixes like "1." or "[1]"
    cleaned = []
    for line in lines:
        line = re.sub(r'^[\[\(]?\d+[\]\)\.:]?\s*', '', line).strip()
        if any(cat_word in line for cat_word in
               ["Acute", "Chronic", "Emergent", "Preventive", "Foundations",
                "Care", "Diagnosis", "Management", "Urgent"]):
            cleaned.append(parse_category(line))
    if len(cleaned) == batch_size:
        return cleaned
    if cleaned:
        # Best effort: pad or trim
        while len(cleaned) < batch_size:
            cleaned.append("Acute Care and Diagnosis")
        return cleaned[:batch_size]

    # Last resort: default everything in this batch to Acute
    print(f"  ⚠  Could not parse batch response (len={batch_size}). Defaulting to Acute.")
    return ["Acute Care and Diagnosis"] * batch_size


# ─── API CALL ─────────────────────────────────────────────────────────────────

def call_api_batch(client, system_prompt: str, batch: list[tuple],
                   model: str, max_retries: int = 3) -> list[str]:
    """
    Call API with one batch of questions.
    Returns a list of category strings, one per question in the batch.
    """
    user_content = build_batch_message(batch)

    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=len(batch) * 12 + 20,  # ~10 tokens per category + overhead
                system=system_prompt,
                messages=[{"role": "user", "content": user_content}],
            )
            return parse_batch_response(response.content[0].text, len(batch))
        except Exception as e:
            err_str = str(e)
            if "rate_limit" in err_str.lower() or "overloaded" in err_str.lower():
                wait = (2 ** attempt) * 5  # longer wait for rate limits
                print(f"  Rate limit (attempt {attempt + 1}). Waiting {wait}s...")
                time.sleep(wait)
            elif attempt < max_retries - 1:
                wait = 2 ** attempt
                print(f"  API error (attempt {attempt + 1}): {err_str[:80]}. Retry in {wait}s...")
                time.sleep(wait)
            else:
                print(f"  API error after {max_retries} attempts: {err_str[:80]}. Defaulting batch.")
                return ["Acute Care and Diagnosis"] * len(batch)

    return ["Acute Care and Diagnosis"] * len(batch)


# ─── COST ESTIMATION ─────────────────────────────────────────────────────────

def estimate_cost(conn, system_prompt: str, model: str,
                  years=TARGET_YEARS, batch_size=DEFAULT_BATCH_SIZE):
    n = conn.execute(
        f"SELECT COUNT(*) FROM questions WHERE exam_year IN ({','.join('?'*len(years))})",
        years
    ).fetchone()[0]
    n_batches = (n + batch_size - 1) // batch_size

    # Rough token counts (4 chars ≈ 1 token)
    sys_tok      = len(system_prompt) // 4
    q_tok_each   = 300                          # avg tokens per question
    batch_in_tok = sys_tok + (q_tok_each * batch_size)
    batch_out_tok = batch_size * 12             # ~10 tokens per category name
    total_in_tok  = batch_in_tok  * n_batches
    total_out_tok = batch_out_tok * n_batches

    price = PRICING.get(model, {"input": 1.0, "output": 5.0})
    in_cost  = total_in_tok  / 1_000_000 * price["input"]
    out_cost = total_out_tok / 1_000_000 * price["output"]

    print(f"\n{'─'*55}")
    print(f" COST ESTIMATE  ({n} questions  •  {model})")
    print(f"{'─'*55}")
    print(f"  Batch size:       {batch_size} questions/call → {n_batches} batches")
    print(f"  System prompt:    ~{sys_tok:,} tokens/batch")
    print(f"  Per-question:     ~{q_tok_each} tokens input + 12 tokens output")
    print(f"  Total input:      ~{total_in_tok:,} tokens   (${in_cost:.2f})")
    print(f"  Total output:     ~{total_out_tok:,} tokens   (${out_cost:.2f})")
    print(f"  ─────────────────────────────────────────")
    print(f"  TOTAL COST:       ~${in_cost + out_cost:.2f}")
    print(f"{'─'*55}\n")


# ─── CLASSIFY A SET OF ROWS ──────────────────────────────────────────────────

def classify_rows(rows: list, client, system_prompt: str, model: str,
                  batch_size: int, workers: int, label: str = "") -> dict:
    """
    Classify a list of (qid, text, ct_json) rows.
    Returns dict {qid: predicted_category}.
    Processes batches concurrently using ThreadPoolExecutor.
    """
    # Build batches
    batches = []
    for i in range(0, len(rows), batch_size):
        chunk = rows[i:i + batch_size]
        batch_input = []
        for qid, text, ct_json in chunk:
            cs = extract_concept_summary(ct_json)
            batch_input.append((qid, text, cs))
        batches.append(batch_input)

    total_q  = len(rows)
    n_batches = len(batches)
    results  = {}
    completed_q = 0
    lock_print = __import__('threading').Lock()

    def process_batch(batch_data):
        batch_qids  = [item[0] for item in batch_data]
        batch_input = [(qid, text, cs) for qid, text, cs in batch_data]
        preds = call_api_batch(client, system_prompt, batch_input, model)
        return list(zip(batch_qids, preds))

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(process_batch, b): b for b in batches}
        for future in as_completed(futures):
            batch_results = future.result()
            for qid, pred in batch_results:
                results[qid] = pred
            completed_q += len(batch_results)
            with lock_print:
                pct = completed_q / total_q * 100
                suffix = f" {label}" if label else ""
                print(f"  Progress{suffix}: {completed_q}/{total_q}  ({pct:.0f}%)")

    return results


# ─── VALIDATION (DRY RUN) ────────────────────────────────────────────────────

def validate_gold_standard(conn, client, system_prompt: str, model: str,
                            batch_size: int, workers: int, verbose: bool = False):
    """Validate classifier against Gold Standard. Uses 2025-only to avoid leakage."""
    rows = conn.execute("""
        SELECT qid, exam_year, question_text, concept_tags, blueprint
        FROM questions
        WHERE exam_year IN (2024, 2025)
          AND blueprint IS NOT NULL AND blueprint != ''
    """).fetchall()

    total = len(rows)
    input_rows = [(qid, text, ct_json) for qid, year, text, ct_json, gold in rows]
    gold_map   = {qid: gold for qid, year, text, ct_json, gold in rows}
    year_map   = {qid: year for qid, year, text, ct_json, gold in rows}
    text_map   = {qid: text for qid, year, text, ct_json, gold in rows}

    print(f"\nRunning Gold Standard validation  (n={total}  model={model})...")
    results = classify_rows(input_rows, client, system_prompt, model,
                            batch_size, workers, label="[validation]")

    correct = 0
    confusion = defaultdict(Counter)
    errors_by_cat = defaultdict(list)

    for qid, pred in results.items():
        gold = gold_map[qid]
        confusion[gold][pred] += 1
        if pred == gold:
            correct += 1
        else:
            errors_by_cat[gold].append(
                (qid, year_map[qid], pred, (text_map.get(qid) or "")[:130])
            )

    acc = correct / total * 100
    short = {
        "Acute Care and Diagnosis": "Acute",
        "Chronic Care Management":  "Chronic",
        "Emergent and Urgent Care": "Emergent",
        "Preventive Care":          "Preventive",
        "Foundations of Care":      "Foundations",
    }

    print(f"\n{'═'*65}")
    print(f" GOLD STANDARD VALIDATION   n={total}   model={model}")
    print(f"{'═'*65}")
    print(f" Overall accuracy: {correct}/{total}  ({acc:.1f}%)\n")
    print(f" {'Category':<28}  {'Gold':>5}  {'Corr':>5}  {'Acc%':>7}  Confusion")
    print(f" {'─'*70}")
    for cat in CATEGORIES:
        g = sum(confusion[cat].values())
        c = confusion[cat][cat]
        pct = c / g * 100 if g else 0
        others = {short[k]: v for k, v in confusion[cat].items() if k != cat and v > 0}
        others_str = "  ".join(
            f"{k}={v}" for k, v in sorted(others.items(), key=lambda x: -x[1])
        )
        print(f"   {cat:<28} {g:>5}  {c:>5}  {pct:>6.1f}%  {others_str}")

    if verbose:
        print("\n\n MISCLASSIFICATIONS BY CATEGORY:")
        for cat in CATEGORIES:
            errs = errors_by_cat[cat]
            if not errs:
                continue
            print(f"\n  ── {cat}  ({len(errs)} wrong) ──")
            for qid, yr, pred, stem in errs[:10]:
                print(f"     [{qid} {yr}] → {short[pred]}")
                print(f"     {stem.strip()}")

    return acc, confusion


# ─── PREVIEW YEAR ────────────────────────────────────────────────────────────

def preview_year(conn, client, system_prompt: str, year: int, model: str,
                 batch_size: int, workers: int):
    rows = conn.execute("""
        SELECT qid, question_text, concept_tags, blueprint
        FROM questions WHERE exam_year = ? ORDER BY qid
    """, (year,)).fetchall()

    input_rows = [(qid, text, ct_json) for qid, text, ct_json, _ in rows]
    print(f"\nPreviewing year {year}  (n={len(rows)}  model={model})...")
    results = classify_rows(input_rows, client, system_prompt, model,
                            batch_size, workers, label=f"[{year}]")

    dist = Counter(results.values())
    total = len(rows)
    target = {
        "Acute Care and Diagnosis": 0.35, "Chronic Care Management": 0.25,
        "Emergent and Urgent Care": 0.20, "Preventive Care": 0.15,
        "Foundations of Care": 0.05,
    }
    print(f"\n Year {year} predicted distribution (n={total}):")
    for cat in CATEGORIES:
        cnt = dist[cat]
        pct = cnt / total * 100
        tgt = target[cat] * 100
        bar = "█" * int(pct / 2)
        print(f"  {cat:<35} {cnt:>4}  ({pct:5.1f}%  target={tgt:.0f}%  Δ={pct-tgt:+.1f})  {bar}")


# ─── WRITE TO DB ─────────────────────────────────────────────────────────────

def write_classifications(conn, client, system_prompt: str, model: str,
                          batch_size: int, workers: int, force: bool = False):
    tc = ",".join("?" * len(TARGET_YEARS))
    if force:
        rows = conn.execute(
            f"SELECT qid, question_text, concept_tags FROM questions"
            f" WHERE exam_year IN ({tc})",
            TARGET_YEARS
        ).fetchall()
    else:
        rows = conn.execute(
            f"SELECT qid, question_text, concept_tags FROM questions"
            f" WHERE exam_year IN ({tc}) AND (blueprint IS NULL OR blueprint = '')",
            TARGET_YEARS
        ).fetchall()

    total = len(rows)
    if total == 0:
        print("No questions to classify. Use --force to overwrite existing values.")
        return

    input_rows = [(qid, text, ct_json) for qid, text, ct_json in rows]
    results = classify_rows(input_rows, client, system_prompt, model,
                            batch_size, workers, label="[2018-2023]")

    # Checkpoint-write to DB in chunks of 200 for safety
    items = list(results.items())
    for chunk_start in range(0, len(items), 200):
        chunk = items[chunk_start:chunk_start + 200]
        conn.executemany(
            "UPDATE questions SET blueprint = ? WHERE qid = ?",
            [(pred, qid) for qid, pred in chunk]
        )
        conn.commit()
        print(f"  Checkpoint committed: {min(chunk_start + 200, total)}/{total}")

    dist = Counter(results.values())
    target = {
        "Acute Care and Diagnosis": 0.35, "Chronic Care Management": 0.25,
        "Emergent and Urgent Care": 0.20, "Preventive Care": 0.15,
        "Foundations of Care": 0.05,
    }
    print(f"\nWrote {total} classifications  →  questions.blueprint")
    print("Distribution vs ABFM targets:")
    for cat in CATEGORIES:
        cnt = dist[cat]
        pct = cnt / total * 100
        tgt = target[cat] * 100
        bar = "█" * int(pct / 2)
        print(f"  {cat:<35} {cnt:>4}  ({pct:.1f}%  target={tgt:.0f}%  Δ={pct-tgt:+.1f})  {bar}")


# ─── POST-WRITE QC ────────────────────────────────────────────────────────────

def post_write_qc(conn):
    print("\nPost-write QC — blueprint population by year:")
    rows = conn.execute("""
        SELECT exam_year,
               COUNT(*) total,
               SUM(CASE WHEN blueprint IS NOT NULL AND blueprint != '' THEN 1 ELSE 0 END) filled
        FROM questions
        GROUP BY exam_year ORDER BY exam_year
    """).fetchall()
    for yr, total, filled in rows:
        label = "Gold Standard" if yr in GOLD_YEARS else "API pseudo-label"
        pct = filled / total * 100 if total else 0
        print(f"  {yr}:  {filled}/{total}  ({pct:.0f}% filled)  [{label}]")


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Batch API-based ABFM Blueprint classifier for ITE questions"
    )
    parser.add_argument("--dry-run",       action="store_true",
                        help="Validate against Gold Standard; no writes")
    parser.add_argument("--verbose",       action="store_true",
                        help="Show misclassification detail in --dry-run")
    parser.add_argument("--year",          type=int,
                        help="Preview predicted distribution for one year")
    parser.add_argument("--write",         action="store_true",
                        help="Write classifications to DB for 2018-2023")
    parser.add_argument("--force",         action="store_true",
                        help="With --write: overwrite existing values too")
    parser.add_argument("--estimate-cost", action="store_true",
                        help="Show cost estimate without calling API")
    parser.add_argument("--show-examples", action="store_true",
                        help="Print the few-shot examples that will be used")
    parser.add_argument("--model",         default=DEFAULT_MODEL,
                        help=f"Model: haiku (default) or sonnet")
    parser.add_argument("--batch-size",    type=int, default=DEFAULT_BATCH_SIZE,
                        help=f"Questions per API call (default: {DEFAULT_BATCH_SIZE})")
    parser.add_argument("--workers",       type=int, default=DEFAULT_WORKERS,
                        help=f"Concurrent batch workers (default: {DEFAULT_WORKERS})")
    parser.add_argument("--examples-per-cat", type=int, default=EXAMPLES_PER_CATEGORY,
                        help=f"Few-shot examples per category (default: {EXAMPLES_PER_CATEGORY})")
    args = parser.parse_args()

    # Resolve model alias
    model = MODELS.get(args.model, args.model)

    conn = sqlite3.connect(DB_PATH)

    # ── Select few-shot examples ───────────────────────────────────────────
    # For --dry-run: use 2024 as few-shot pool, validate on both 2024+2025
    # For --write:   use all 395 Gold Standard examples (max signal)
    # For --estimate-cost / --show-examples: use all by default
    if args.dry_run:
        example_years = (2024,)
        print(f"Validation mode: few-shot pool = 2024 only  (no leakage into 2025 test set)")
    else:
        example_years = GOLD_YEARS

    selected = select_examples(conn, example_years=example_years,
                               n_per_category=args.examples_per_cat)
    n_examples = sum(len(v) for v in selected.values())
    system_prompt = build_system_prompt(selected)

    print(f"Few-shot pool: {n_examples} examples "
          f"({args.examples_per_cat}/category from years {example_years})")
    print(f"System prompt: ~{len(system_prompt)//4:,} tokens")

    # ── --show-examples ───────────────────────────────────────────────────
    if args.show_examples:
        for cat in CATEGORIES:
            examples = selected.get(cat, [])
            print(f"\n{'═'*65}")
            print(f"  {cat}  ({len(examples)} examples)")
            print(f"{'═'*65}")
            for ex in examples:
                print(f"  [{ex['qid']} {ex['year']}]")
                print(f"  {ex['text'][:120].strip()}...")
                if ex["summary"]:
                    print(f"  CS: {ex['summary'][:100]}...")
        conn.close()
        return

    # ── --estimate-cost ──────────────────────────────────────────────────
    if args.estimate_cost:
        print("\n── Validation (Gold Standard, n≈395) ──")
        estimate_cost(conn, system_prompt, model,
                      years=GOLD_YEARS, batch_size=args.batch_size)
        print("\n── Production (2018-2023, n≈1234) ──")
        estimate_cost(conn, system_prompt, model,
                      years=TARGET_YEARS, batch_size=args.batch_size)
        conn.close()
        return

    # ── Initialize API client ─────────────────────────────────────────────
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY environment variable not set.")
        conn.close()
        return
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
    except ImportError:
        print("ERROR: anthropic package not installed.")
        print("  Run: pip install anthropic --break-system-packages")
        conn.close()
        return

    # ── Run requested mode ────────────────────────────────────────────────
    if args.dry_run or (not args.write and not args.year):
        validate_gold_standard(
            conn, client, system_prompt, model,
            batch_size=args.batch_size, workers=args.workers,
            verbose=args.verbose,
        )

    if args.year:
        preview_year(conn, client, system_prompt, args.year, model,
                     batch_size=args.batch_size, workers=args.workers)

    if args.write:
        print("Running Gold Standard validation before writing...")
        acc, _ = validate_gold_standard(
            conn, client, system_prompt, model,
            batch_size=args.batch_size, workers=args.workers,
        )
        print(f"\nValidation accuracy: {acc:.1f}%")
        confirm = input("Proceed with writing to 2018-2023? (yes/no): ").strip().lower()
        if confirm not in ("yes", "y"):
            print("Aborted.")
            conn.close()
            return
        write_classifications(
            conn, client, system_prompt, model,
            batch_size=args.batch_size, workers=args.workers,
            force=args.force,
        )
        post_write_qc(conn)

    conn.close()


if __name__ == "__main__":
    main()
