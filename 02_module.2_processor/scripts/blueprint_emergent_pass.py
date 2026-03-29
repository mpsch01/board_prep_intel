"""
blueprint_emergent_pass.py
===========================
Targeted second-pass binary classifier: scans all pre-2024 (2018-2023) questions
currently labeled 'Acute Care and Diagnosis' and reclassifies any that are actually
'Emergent and Urgent Care'.

WHY THIS EXISTS:
  The first-pass classifier (blueprint_api_classifier.py) used a "default to Acute
  when uncertain" rule that systematically under-called Emergent. Production result:
  10.4% Emergent vs 20% ABFM target (~119 questions missing from Emergent bucket).
  This focused pass corrects that without re-running the full 1,234-question job.

DESIGN:
  - Binary question only: "Is this Emergent?" YES or NO
  - Few-shot pool: all 80 Emergent Gold Standard examples (2024+2025)
    + 20 Acute examples that look emergent but aren't (boundary anchors)
  - Batch mode (25 questions/call), same architecture as blueprint_api_classifier.py
  - Default model: Haiku (binary task, no need for Sonnet)
  - --dry-run: validates recall/precision on Gold Standard before writing
  - --write: flips qualifying Acute → Emergent in DB

Usage:
  python blueprint_emergent_pass.py --estimate-cost
  python blueprint_emergent_pass.py --dry-run          # check recall/precision
  python blueprint_emergent_pass.py --dry-run --verbose
  python blueprint_emergent_pass.py --write            # apply to 2018-2023 Acute bucket

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

SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH      = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"

GOLD_YEARS   = (2024, 2025)
TARGET_YEARS = (2018, 2019, 2020, 2021, 2022, 2023)

EMERGENT_CAT = "Emergent and Urgent Care"
ACUTE_CAT    = "Acute Care and Diagnosis"

DEFAULT_MODEL      = "claude-sonnet-4-6"
DEFAULT_BATCH_SIZE = 25
DEFAULT_WORKERS    = 4
RANDOM_SEED        = 42
N_EMERGENT_EXAMPLES = 20   # positive examples (Emergent)
N_ACUTE_EXAMPLES    = 10   # negative boundary anchors (Acute that looks emergent)

MODELS = {
    "haiku":  "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-6",
}

PRICING = {
    "claude-haiku-4-5-20251001": {"input": 0.80,  "output": 4.00},
    "claude-sonnet-4-6":         {"input": 3.00,  "output": 15.00},
}

# ─── SYSTEM PROMPT ────────────────────────────────────────────────────────────

SYSTEM_PROMPT_TEMPLATE = """\
You are classifying ABFM Family Medicine board exam questions with a single
binary decision: is this question "Emergent and Urgent Care" or not?

━━━ THE ONLY QUESTION YOU ARE ANSWERING ━━━

Is the UNDERLYING CONDITION time-critical — meaning the patient will be
HARMED (death, permanent injury, organ loss) if this is NOT addressed
within HOURS TO 1–2 DAYS?

  YES → output: EMERGENT
  NO  → output: NOT_EMERGENT

━━━ KEY RULES ━━━

★ The category = TIME-URGENCY of the UNDERLYING CONDITION, not the
  question format. Even a diagnostic/imaging question about appendicitis
  is EMERGENT because the condition itself is time-critical.

★ Hemodynamic instability requiring vasopressors (septic shock, MAP <65,
  cardiogenic shock) → EMERGENT.

★ Respiratory compromise with active treatment decision (pneumothorax,
  acute respiratory failure, airway emergency) → EMERGENT.

★ The following conditions are ALWAYS EMERGENT regardless of what the
  question asks: appendicitis, ectopic pregnancy, testicular/ovarian
  torsion, STEMI or STEMI-equivalent (new LBBB + chest pain), SAH
  ("worst headache of life"), aortic dissection, tension pneumothorax,
  orbital cellulitis, acute limb ischemia, epiglottitis, cauda equina,
  DKA/HHS, meningitis/encephalitis (with treatment question), anaphylaxis
  requiring epinephrine, major trauma, septic shock.

★ ED setting alone does NOT make something Emergent. Many ED questions
  are about conditions that are urgent but not hours-critical.

★ Post-STEMI management (patient already stabilized) → NOT_EMERGENT
  (the acute phase has passed).

★ A patient with a chronic disease presenting with a new symptom that
  requires urgent workup but not hours-critical intervention → NOT_EMERGENT.

━━━ EXAMPLES ━━━

{examples}

━━━ RESPONSE FORMAT ━━━

Respond with a JSON array of EXACTLY one token per question: either
"EMERGENT" or "NOT_EMERGENT", in order.

Example for a 3-question batch:
["NOT_EMERGENT", "EMERGENT", "NOT_EMERGENT"]

No explanation. No extra text. Only the JSON array.
"""


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def extract_concept_summary(concept_tags_json: str) -> str:
    if not concept_tags_json:
        return ""
    try:
        ct = json.loads(concept_tags_json)
        return ct.get("concept_summary", "") or ""
    except Exception:
        return ""


def format_question(text: str, summary: str) -> str:
    text    = re.sub(r'\s+', ' ', (text    or "").strip())
    summary = re.sub(r'\s+', ' ', (summary or "").strip())
    parts = []
    if text:
        parts.append(f"Question: {text}")
    if summary:
        parts.append(f"Concept summary: {summary}")
    return "\n".join(parts)


# ─── EXAMPLE SELECTION ────────────────────────────────────────────────────────

def select_examples(conn, seed=RANDOM_SEED):
    """
    Build few-shot pool:
      - N_EMERGENT_EXAMPLES Emergent Gold Standard examples (positive)
      - N_ACUTE_EXAMPLES    Acute Gold Standard examples that are short/clear (negative anchors)
    """
    rng = random.Random(seed)

    rows = conn.execute("""
        SELECT qid, exam_year, question_text, concept_tags, blueprint
        FROM questions
        WHERE exam_year IN (2024, 2025)
          AND blueprint IS NOT NULL AND blueprint != ''
          AND question_text IS NOT NULL AND LENGTH(question_text) > 50
        ORDER BY qid
    """).fetchall()

    emergent_pool = []
    acute_pool    = []
    for qid, year, text, ct_json, cat in rows:
        cs = extract_concept_summary(ct_json)
        entry = {
            "qid": qid, "year": year,
            "text": text, "summary": cs,
            "formatted": format_question(text, cs),
            "len": len(text),
        }
        if cat == EMERGENT_CAT:
            emergent_pool.append(entry)
        elif cat == ACUTE_CAT:
            acute_pool.append(entry)

    # Prefer concise examples for token efficiency
    emergent_pool.sort(key=lambda x: x["len"])
    acute_pool.sort(key=lambda x: x["len"])

    cutoff_e = max(N_EMERGENT_EXAMPLES, int(len(emergent_pool) * 0.7))
    cutoff_a = max(N_ACUTE_EXAMPLES,    int(len(acute_pool)    * 0.4))

    emergent_chosen = rng.sample(emergent_pool[:cutoff_e], min(N_EMERGENT_EXAMPLES, len(emergent_pool)))
    acute_chosen    = rng.sample(acute_pool[:cutoff_a],    min(N_ACUTE_EXAMPLES,    len(acute_pool)))

    return {
        EMERGENT_CAT: sorted(emergent_chosen, key=lambda x: x["qid"]),
        ACUTE_CAT:    sorted(acute_chosen,    key=lambda x: x["qid"]),
    }


def build_examples_block(selected: dict) -> str:
    lines = []
    lines.append("─── EMERGENT examples (answer = EMERGENT) ───")
    for ex in selected.get(EMERGENT_CAT, []):
        text_part = ex["formatted"]
        if len(text_part) > 500:
            q_lines = text_part.split("\nConcept summary:")
            text_part = (q_lines[0][:350] + "...") + ("\nConcept summary:" + q_lines[1] if len(q_lines) > 1 else "")
        lines.append(text_part)
        lines.append("→ EMERGENT\n")

    lines.append("─── NOT_EMERGENT examples (answer = NOT_EMERGENT) ───")
    for ex in selected.get(ACUTE_CAT, []):
        text_part = ex["formatted"]
        if len(text_part) > 500:
            q_lines = text_part.split("\nConcept summary:")
            text_part = (q_lines[0][:350] + "...") + ("\nConcept summary:" + q_lines[1] if len(q_lines) > 1 else "")
        lines.append(text_part)
        lines.append("→ NOT_EMERGENT\n")

    return "\n".join(lines)


def build_system_prompt(selected: dict) -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(examples=build_examples_block(selected))


# ─── BATCH CONSTRUCTION & PARSING ────────────────────────────────────────────

def build_batch_message(batch: list) -> str:
    parts = [f"Classify the following {len(batch)} questions as EMERGENT or NOT_EMERGENT.\n"]
    for i, (qid, text, cs) in enumerate(batch, 1):
        parts.append(f"[{i}]\n{format_question(text, cs)}")
    return "\n\n".join(parts)


def parse_batch_response(response_text: str, batch_size: int) -> list:
    text = (response_text or "").strip()
    try:
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            raw_list = json.loads(match.group())
            parsed = []
            for item in raw_list:
                s = str(item).strip().upper()
                parsed.append("EMERGENT" if "EMERGENT" in s and "NOT" not in s else "NOT_EMERGENT")
            if len(parsed) == batch_size:
                return parsed
            while len(parsed) < batch_size:
                parsed.append("NOT_EMERGENT")
            return parsed[:batch_size]
    except (json.JSONDecodeError, TypeError):
        pass

    # Line fallback
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    cleaned = []
    for line in lines:
        line = re.sub(r'^[\[\(]?\d+[\]\)\.:]?\s*', '', line).strip().upper()
        if "EMERGENT" in line:
            cleaned.append("EMERGENT" if "NOT" not in line else "NOT_EMERGENT")
        elif "NOT_EMERGENT" in line or "NOT EMERGENT" in line:
            cleaned.append("NOT_EMERGENT")
    if len(cleaned) == batch_size:
        return cleaned

    print(f"  ⚠  Could not parse batch response (size={batch_size}). Defaulting to NOT_EMERGENT.")
    return ["NOT_EMERGENT"] * batch_size


# ─── API CALL ─────────────────────────────────────────────────────────────────

def call_api_batch(client, system_prompt: str, batch: list,
                   model: str, max_retries: int = 3) -> list:
    user_content = build_batch_message(batch)
    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=len(batch) * 15 + 20,
                system=system_prompt,
                messages=[{"role": "user", "content": user_content}],
            )
            return parse_batch_response(response.content[0].text, len(batch))
        except Exception as e:
            err_str = str(e)
            if "rate_limit" in err_str.lower() or "overloaded" in err_str.lower():
                wait = (2 ** attempt) * 5
                print(f"  Rate limit (attempt {attempt + 1}). Waiting {wait}s...")
                time.sleep(wait)
            elif attempt < max_retries - 1:
                wait = 2 ** attempt
                print(f"  API error (attempt {attempt + 1}): {err_str[:80]}. Retry in {wait}s...")
                time.sleep(wait)
            else:
                print(f"  API error after {max_retries} attempts. Defaulting batch to NOT_EMERGENT.")
                return ["NOT_EMERGENT"] * len(batch)
    return ["NOT_EMERGENT"] * len(batch)


# ─── CLASSIFY ROWS ────────────────────────────────────────────────────────────

def classify_rows(rows: list, client, system_prompt: str, model: str,
                  batch_size: int, workers: int, label: str = "") -> dict:
    batches = []
    for i in range(0, len(rows), batch_size):
        chunk = rows[i:i + batch_size]
        batch_input = []
        for qid, text, ct_json in chunk:
            cs = extract_concept_summary(ct_json)
            batch_input.append((qid, text, cs))
        batches.append(batch_input)

    total_q  = len(rows)
    results  = {}
    completed_q = 0
    lock_print = __import__('threading').Lock()

    def process_batch(batch_data):
        batch_qids = [item[0] for item in batch_data]
        preds = call_api_batch(client, system_prompt, batch_data, model)
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


# ─── COST ESTIMATE ────────────────────────────────────────────────────────────

def estimate_cost(conn, system_prompt: str, model: str, batch_size: int):
    n = conn.execute(
        "SELECT COUNT(*) FROM questions WHERE exam_year IN (?,?,?,?,?,?) AND blueprint = ?",
        (*TARGET_YEARS, ACUTE_CAT)
    ).fetchone()[0]
    n_batches = (n + batch_size - 1) // batch_size
    sys_tok      = len(system_prompt) // 4
    q_tok_each   = 300
    batch_in_tok = sys_tok + (q_tok_each * batch_size)
    batch_out_tok = batch_size * 5
    total_in  = batch_in_tok  * n_batches
    total_out = batch_out_tok * n_batches
    price = PRICING.get(model, {"input": 1.0, "output": 5.0})
    in_cost  = total_in  / 1_000_000 * price["input"]
    out_cost = total_out / 1_000_000 * price["output"]
    print(f"\n{'─'*55}")
    print(f" COST ESTIMATE  ({n} Acute-labeled questions  •  {model})")
    print(f"{'─'*55}")
    print(f"  Batch size:    {batch_size} questions/call → {n_batches} batches")
    print(f"  System prompt: ~{sys_tok:,} tokens/batch")
    print(f"  Total input:   ~{total_in:,} tokens  (${in_cost:.2f})")
    print(f"  Total output:  ~{total_out:,} tokens  (${out_cost:.2f})")
    print(f"  ─────────────────────────────────────────")
    print(f"  TOTAL COST:    ~${in_cost + out_cost:.2f}")
    print(f"{'─'*55}\n")


# ─── DRY RUN VALIDATION ───────────────────────────────────────────────────────

def validate(conn, client, system_prompt: str, model: str,
             batch_size: int, workers: int, verbose: bool = False):
    """
    Validate on Gold Standard (2024+2025):
      Recall:    how many true Emergent questions does the pass catch?
      Precision: of the ones it calls Emergent, how many are actually Emergent?
      False positive rate on Acute questions (ones it wrongly flips).
    """
    rows = conn.execute("""
        SELECT qid, exam_year, question_text, concept_tags, blueprint
        FROM questions
        WHERE exam_year IN (2024, 2025)
          AND blueprint IN (?, ?)
    """, (EMERGENT_CAT, ACUTE_CAT)).fetchall()

    total_emergent = sum(1 for r in rows if r[4] == EMERGENT_CAT)
    total_acute    = sum(1 for r in rows if r[4] == ACUTE_CAT)

    input_rows = [(qid, text, ct_json) for qid, year, text, ct_json, cat in rows]
    gold_map   = {qid: cat  for qid, year, text, ct_json, cat in rows}
    year_map   = {qid: year for qid, year, text, ct_json, cat in rows}
    text_map   = {qid: text for qid, year, text, ct_json, cat in rows}

    print(f"\nRunning validation  (n={len(rows)}: {total_emergent} Emergent + {total_acute} Acute  •  {model})...")
    results = classify_rows(input_rows, client, system_prompt, model,
                            batch_size, workers, label="[validation]")

    tp = fp = fn = tn = 0
    fp_list = []
    fn_list = []

    for qid, pred in results.items():
        gold = gold_map[qid]
        is_emergent_pred = (pred == "EMERGENT")
        is_emergent_gold = (gold == EMERGENT_CAT)
        if is_emergent_pred and is_emergent_gold:
            tp += 1
        elif is_emergent_pred and not is_emergent_gold:
            fp += 1
            fp_list.append((qid, year_map[qid], (text_map.get(qid) or "")[:120]))
        elif not is_emergent_pred and is_emergent_gold:
            fn += 1
            fn_list.append((qid, year_map[qid], (text_map.get(qid) or "")[:120]))
        else:
            tn += 1

    recall    = tp / (tp + fn) * 100 if (tp + fn) else 0
    precision = tp / (tp + fp) * 100 if (tp + fp) else 0
    fpr       = fp / total_acute    * 100 if total_acute else 0

    print(f"\n{'═'*65}")
    print(f" EMERGENT PASS VALIDATION   n={len(rows)}   model={model}")
    print(f"{'═'*65}")
    print(f"  True Emergent questions:  {total_emergent}")
    print(f"  True Acute questions:     {total_acute}")
    print(f"")
    print(f"  TP (Emergent → EMERGENT): {tp}")
    print(f"  FN (Emergent → missed):   {fn}")
    print(f"  FP (Acute → flipped):     {fp}")
    print(f"  TN (Acute → kept):        {tn}")
    print(f"")
    print(f"  Recall:    {recall:.1f}%   (of true Emergent, how many caught)")
    print(f"  Precision: {precision:.1f}%   (of predicted Emergent, how many correct)")
    print(f"  False +ve: {fpr:.1f}%   (of true Acute, how many wrongly flipped)")

    if verbose:
        if fn_list:
            print(f"\n  ── Missed Emergent (FN: {len(fn_list)}) ──")
            for qid, yr, stem in fn_list[:10]:
                print(f"     [{qid} {yr}]  {stem.strip()}")
        if fp_list:
            print(f"\n  ── False Positives (FP: {len(fp_list)}) ──")
            for qid, yr, stem in fp_list[:10]:
                print(f"     [{qid} {yr}]  {stem.strip()}")

    return recall, precision, fpr


# ─── WRITE PASS ───────────────────────────────────────────────────────────────

def write_emergent_pass(conn, client, system_prompt: str, model: str,
                        batch_size: int, workers: int):
    rows = conn.execute(
        f"SELECT qid, question_text, concept_tags FROM questions"
        f" WHERE exam_year IN (?,?,?,?,?,?) AND blueprint = ?",
        (*TARGET_YEARS, ACUTE_CAT)
    ).fetchall()

    total = len(rows)
    if total == 0:
        print("No Acute-labeled pre-2024 questions found.")
        return

    print(f"\nScanning {total} Acute-labeled questions from 2018-2023...")
    input_rows = [(qid, text, ct_json) for qid, text, ct_json in rows]
    results = classify_rows(input_rows, client, system_prompt, model,
                            batch_size, workers, label="[emergent-pass]")

    flips = [(qid,) for qid, pred in results.items() if pred == "EMERGENT"]
    total_flipped = len(flips)

    if total_flipped == 0:
        print("No questions reclassified as Emergent.")
        return

    # Checkpoint writes
    for chunk_start in range(0, len(flips), 200):
        chunk = flips[chunk_start:chunk_start + 200]
        conn.executemany(
            "UPDATE questions SET blueprint = ? WHERE qid = ?",
            [(EMERGENT_CAT, qid) for (qid,) in chunk]
        )
        conn.commit()
        print(f"  Checkpoint committed: {min(chunk_start + 200, total_flipped)}/{total_flipped} flips")

    print(f"\nFlipped {total_flipped}/{total} questions → '{EMERGENT_CAT}'")

    # Post-write distribution
    dist_rows = conn.execute(
        f"SELECT blueprint, COUNT(*) FROM questions"
        f" WHERE exam_year IN (?,?,?,?,?,?) GROUP BY blueprint",
        TARGET_YEARS
    ).fetchall()
    dist = {cat: cnt for cat, cnt in dist_rows}
    total_q = sum(dist.values())
    target = {
        "Acute Care and Diagnosis": 0.35,
        "Chronic Care Management":  0.25,
        "Emergent and Urgent Care": 0.20,
        "Preventive Care":          0.15,
        "Foundations of Care":      0.05,
    }
    print("\nUpdated 2018-2023 distribution vs ABFM targets:")
    for cat in ["Acute Care and Diagnosis", "Chronic Care Management",
                "Emergent and Urgent Care", "Preventive Care", "Foundations of Care"]:
        cnt = dist.get(cat, 0)
        pct = cnt / total_q * 100 if total_q else 0
        tgt = target[cat] * 100
        bar = "█" * int(pct / 2)
        print(f"  {cat:<35} {cnt:>4}  ({pct:.1f}%  target={tgt:.0f}%  Δ={pct-tgt:+.1f})  {bar}")


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Targeted Emergent second-pass classifier for pre-2024 ITE questions"
    )
    parser.add_argument("--dry-run",       action="store_true",
                        help="Validate recall/precision on Gold Standard; no writes")
    parser.add_argument("--verbose",       action="store_true",
                        help="Show misclassified questions in --dry-run")
    parser.add_argument("--write",         action="store_true",
                        help="Flip qualifying Acute → Emergent in DB for 2018-2023")
    parser.add_argument("--estimate-cost", action="store_true",
                        help="Show cost estimate without calling API")
    parser.add_argument("--show-examples", action="store_true",
                        help="Print few-shot examples")
    parser.add_argument("--model",         default=DEFAULT_MODEL,
                        help="Model alias: haiku (default) or sonnet")
    parser.add_argument("--batch-size",    type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--workers",       type=int, default=DEFAULT_WORKERS)
    args = parser.parse_args()

    model = MODELS.get(args.model, args.model)
    conn  = sqlite3.connect(DB_PATH)

    selected      = select_examples(conn)
    system_prompt = build_system_prompt(selected)
    n_e = len(selected.get(EMERGENT_CAT, []))
    n_a = len(selected.get(ACUTE_CAT, []))
    print(f"Few-shot pool: {n_e} Emergent + {n_a} Acute boundary examples")
    print(f"System prompt: ~{len(system_prompt)//4:,} tokens")

    if args.show_examples:
        for label, cat in [("EMERGENT", EMERGENT_CAT), ("NOT_EMERGENT", ACUTE_CAT)]:
            print(f"\n{'═'*65}")
            print(f"  {label}  ({len(selected.get(cat,[]))} examples)")
            print(f"{'═'*65}")
            for ex in selected.get(cat, []):
                print(f"  [{ex['qid']} {ex['year']}]")
                print(f"  {ex['text'][:120].strip()}...")
        conn.close()
        return

    if args.estimate_cost:
        estimate_cost(conn, system_prompt, model, args.batch_size)
        conn.close()
        return

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set.")
        conn.close()
        return
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
    except ImportError:
        print("ERROR: anthropic not installed. Run: pip install anthropic --break-system-packages")
        conn.close()
        return

    if args.dry_run:
        validate(conn, client, system_prompt, model,
                 batch_size=args.batch_size, workers=args.workers,
                 verbose=args.verbose)

    if args.write:
        print("\nRunning validation before writing...")
        recall, precision, fpr = validate(conn, client, system_prompt, model,
                                          batch_size=args.batch_size, workers=args.workers)
        print(f"\nRecall: {recall:.1f}%  |  Precision: {precision:.1f}%  |  False +ve rate: {fpr:.1f}%")
        confirm = input("Proceed with Emergent pass write? (yes/no): ").strip().lower()
        if confirm not in ("yes", "y"):
            print("Aborted.")
            conn.close()
            return
        write_emergent_pass(conn, client, system_prompt, model,
                            batch_size=args.batch_size, workers=args.workers)

    conn.close()


if __name__ == "__main__":
    main()
