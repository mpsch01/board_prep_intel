"""
preprocess_concept_tags.py
==========================
Claude API batch processor — populates concept_tags for all questions
where the column is currently NULL (resume-safe, targets any year).

CURRENT TARGET: 440 new 2018-2019 questions added March 24, 2026.
  After this run, concept_tags will be 1,629/1,629 (100%).

WHAT IT GENERATES per question:
  {
    "diagnoses":       ["clinical conditions being tested"],
    "drugs":           ["medications or drug classes"],
    "guidelines":      ["org + year, e.g. ACC/AHA 2017"],
    "thresholds":      ["numeric values, e.g. BP >130/80, A1C >7%"],
    "concept_summary": "1-2 sentence exam-focused summary"
  }

COST ESTIMATE (440 questions):
  440 / 25 per batch = ~18 API calls
  ~$0.03-0.05 per call = ~$0.55-0.90 total (one-time)

RESUME BEHAVIOR:
  Safe to interrupt and rerun. Already-processed questions are skipped.
  Use --reset to clear concept_tags for a specific year and reprocess.

PATH NOTE:
  This script uses the PROJECT_ROOT pattern (3 hops — M1/scripts/maintain/):
    SCRIPT_DIR   = 01_module.1_warehouse/scripts/maintain/
    PROJECT_ROOT = 00_#PROJECT_OVERHAUL/
    DB_PATH      = 00_database/db/ite_intelligence.db

RUN:
  python scripts/preprocess_concept_tags.py
  python scripts/preprocess_concept_tags.py --dry-run
  python scripts/preprocess_concept_tags.py --limit 50
  python scripts/preprocess_concept_tags.py --year 2018
  python scripts/preprocess_concept_tags.py --year 2019
  python scripts/preprocess_concept_tags.py --reset --year 2018
"""

import sqlite3
import json
import re
import os
import argparse
import time
from pathlib import Path
from datetime import datetime, timezone

try:
    import anthropic
except ImportError:
    raise ImportError("Run: pip install anthropic")

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── Paths (PROJECT_ROOT pattern) ────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent              # 01_module.1_warehouse/scripts/maintain/
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent            # board_prep_intel/ (3 hops: maintain/ → scripts/ → M1 → root)
DB_PATH      = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"
LOG_DIR      = PROJECT_ROOT / "00_database" / "logs"

# ── Config ──────────────────────────────────────────────────────────────────
MODEL      = "claude-sonnet-4-20250514"   # current production model
BATCH_SIZE = 20          # reduced from 25 — keeps output comfortably under token ceiling
MAX_TOKENS = 8192        # 4000 was too tight for 25 questions; 8192 gives ample headroom
RETRY_MAX  = 3
RETRY_WAIT = 5   # seconds between retries

# ── System prompt (identical to preprocess_keywords_v2.py) ─────────────────
SYSTEM_PROMPT = """You are a medical education expert specializing in ABFM board exam preparation.

Your task: analyze ITE (In-Training Examination) questions and extract structured clinical concept tags.

Each question is labeled with an ABFM blueprint content area. Use the definitions below to orient
your tag extraction — they define the clinical frame the question is operating in.

ABFM ITE CONTENT AREAS (official definitions):
- Acute Care and Diagnosis (35%): Questions from scenarios encountered in normal ambulatory clinic
  practice where you are asked to provide next steps in diagnosis, provide the correct diagnosis,
  or provide the initial treatment.
- Chronic Care Management (25%): Questions from scenarios encountered in normal ambulatory clinic
  practice or other long-term care settings where you are asked to provide ongoing management of
  a chronic disease.
- Emergent and Urgent Care (20%): Questions from hospital, emergency department, urgent care, or
  ambulatory settings where you are asked patient management decisions needed in a matter of hours.
- Preventive Care (15%): Questions from any issue encountered in the ambulatory clinic setting
  where preventive care services are being provided.
- Foundations of Care (5%): Questions regarding other topics important in the provision of care,
  including statistics, health policy, legal issues, health equity, and other topics.

For each question you receive, return ONLY a JSON object — no preamble, no explanation, no markdown fences.

The JSON must have this exact structure:
{
  "QID-YYYY-NNNN": {
    "diagnoses": ["list of clinical conditions, diseases, or syndromes being tested"],
    "drugs": ["medications or drug classes mentioned or relevant to the answer"],
    "guidelines": ["guideline name + year if referenced, e.g. ACC/AHA 2017, JNC 8, CDC 2019"],
    "thresholds": ["specific numeric values that are clinically important, e.g. BP >130/80, A1C >7%, ANC <500"],
    "concept_summary": "1-2 sentence summary of exactly what clinical concept this question tests and what a resident must know to answer it correctly"
  },
  "QID-YYYY-NNNN": { ... }
}

Rules:
- Be specific and clinical — not vague. "hypertension" not "blood pressure problem"
- For concept_summary: focus on the DECISION POINT, not just the topic
- If a field has nothing relevant, use an empty array []
- Never include explanatory text outside the JSON object
- Return ALL questions provided in a single JSON object"""


# ── Format a question for the prompt ───────────────────────────────────────
def format_question(q: dict) -> str:
    lines = []
    lines.append(
        f"QID: {q['qid']} | {q['exam_year']} | "
        f"{q.get('body_system_merged') or q.get('body_system') or '?'} | "
        f"blueprint: {q.get('blueprint') or '?'}"
    )

    stem = (q.get("question_text") or "").strip().replace("\n", " ")
    if len(stem) > 400:
        stem = stem[:400] + "..."
    lines.append(f"STEM: {stem}")

    try:
        choices = json.loads(q.get("choices") or "[]")
        for ch in choices[:5]:
            lines.append(f"  ({ch['letter']}) {ch['text'][:100]}")
    except Exception:
        pass

    correct = (q.get("correct_text") or "").strip()
    lines.append(f"CORRECT: ({q.get('correct_letter') or '?'}) {correct[:120]}")

    expl = (q.get("explanation") or "").strip().replace("\n", " ")
    if len(expl) > 500:
        expl = expl[:500] + "..."
    lines.append(f"EXPLANATION: {expl}")

    return "\n".join(lines)


# ── Call Claude for one batch ───────────────────────────────────────────────
def process_batch(client, questions: list, dry_run=False) -> dict:
    prompt_parts = []
    for q in questions:
        prompt_parts.append(format_question(q))
        prompt_parts.append("---")

    user_message = (
        f"Please extract concept tags for the following {len(questions)} ITE questions.\n\n"
        + "\n".join(prompt_parts)
    )

    if dry_run:
        print("\n[DRY RUN] Would send to Claude:")
        print(f"  QIDs:          {[q['qid'] for q in questions]}")
        print(f"  Prompt length: ~{len(user_message)} chars")
        print(f"  First question preview:")
        preview = format_question(questions[0])
        for line in preview.split("\n")[:6]:
            print(f"    {line}")
        return {}

    for attempt in range(1, RETRY_MAX + 1):
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}]
            )
            raw = response.content[0].text.strip()

            # Strip accidental markdown fences
            raw = re.sub(r"^```json\s*", "", raw)
            raw = re.sub(r"^```\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)

            result = json.loads(raw)
            return {
                "tags":          result,
                "input_tokens":  response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            }

        except json.JSONDecodeError as e:
            print(f"    JSON parse error (attempt {attempt}): {e}")
            print(f"    Raw[:200]: {raw[:200]}")
            if attempt == RETRY_MAX:
                raise
            time.sleep(RETRY_WAIT)

        except Exception as e:
            print(f"    API error (attempt {attempt}): {e}")
            if attempt == RETRY_MAX:
                raise
            time.sleep(RETRY_WAIT * attempt)


# ── Main ────────────────────────────────────────────────────────────────────
def run(dry_run=False, limit=None, reset=False, year=None):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key and not dry_run:
        raise ValueError(
            "ANTHROPIC_API_KEY not set.\n"
            "Set it in your environment or add to a .env file in the project root."
        )

    if not DB_PATH.exists():
        print(f"❌  DB not found: {DB_PATH}")
        return

    client = anthropic.Anthropic(api_key=api_key) if not dry_run else None

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    log_path = LOG_DIR / f"preprocess_concept_tags_{ts}.json"

    LOG = {
        "script":     "preprocess_concept_tags.py",
        "started":    datetime.now(timezone.utc).isoformat(),
        "model":      MODEL,
        "filter_year": year,
        "batches":    [],
        "totals":     {"processed": 0, "failed": 0, "input_tokens": 0, "output_tokens": 0},
        "errors":     []
    }

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Optional reset for a specific year
    if reset:
        if year:
            c.execute("UPDATE questions SET concept_tags = NULL WHERE exam_year = ?", (year,))
            print(f"  Reset concept_tags for exam_year={year} ({c.rowcount} rows)")
        else:
            c.execute("UPDATE questions SET concept_tags = NULL")
            print(f"  Reset concept_tags for ALL questions ({c.rowcount} rows)")
        conn.commit()

    # Load pending questions
    if year:
        c.execute("""
            SELECT qid, exam_year, body_system, body_system_merged, blueprint,
                   question_text, choices, correct_letter, correct_text, explanation
            FROM questions
            WHERE concept_tags IS NULL
              AND exam_year = ?
            ORDER BY exam_year, qid
        """, (year,))
    else:
        c.execute("""
            SELECT qid, exam_year, body_system, body_system_merged, blueprint,
                   question_text, choices, correct_letter, correct_text, explanation
            FROM questions
            WHERE concept_tags IS NULL
            ORDER BY exam_year, qid
        """)

    pending = [dict(r) for r in c.fetchall()]
    total_pending = len(pending)

    if limit:
        pending = pending[:limit]

    # Year distribution for display
    from collections import Counter
    year_dist = Counter(q["exam_year"] for q in pending)

    print("=" * 60)
    print("preprocess_concept_tags.py")
    print(f"  DB:           {DB_PATH.name}")
    print(f"  Model:        {MODEL}")
    print(f"  Pending:      {total_pending} questions need concept_tags")
    if year:
        print(f"  Year filter:  {year}")
    print(f"  Year dist:    {dict(sorted(year_dist.items()))}")
    print(f"  Processing:   {len(pending)} this run")
    print(f"  Batch size:   {BATCH_SIZE}")
    print(f"  Est. batches: {(len(pending) - 1) // BATCH_SIZE + 1 if pending else 0}")
    est_cost = ((len(pending) / 25) * 0.04)
    print(f"  Est. cost:    ~${est_cost:.2f}")
    print(f"  dry_run:      {dry_run}")
    print("=" * 60)

    if total_pending == 0:
        print("✅  All questions already have concept_tags.")
        if year:
            print(f"   Use --reset --year {year} to reprocess.")
        else:
            print("   Use --reset to reprocess all.")
        conn.close()
        return

    # Process in batches
    processed  = 0
    failed     = 0
    total_in   = 0
    total_out  = 0

    for batch_num, i in enumerate(range(0, len(pending), BATCH_SIZE), start=1):
        batch = pending[i:i + BATCH_SIZE]
        qids  = [q["qid"] for q in batch]
        t0    = time.time()

        print(f"\n[Batch {batch_num}] {qids[0]} .. {qids[-1]}  ({len(batch)} questions)")

        batch_log = {
            "batch": batch_num, "qids": qids,
            "status": None, "elapsed_s": None,
            "in_tokens": None, "out_tokens": None, "error": None
        }

        try:
            result = process_batch(client, batch, dry_run=dry_run)

            if dry_run:
                batch_log["status"] = "dry_run_skipped"
                LOG["batches"].append(batch_log)
                break

            tags     = result["tags"]
            in_tok   = result["input_tokens"]
            out_tok  = result["output_tokens"]
            elapsed  = round(time.time() - t0, 2)
            total_in  += in_tok
            total_out += out_tok

            batch_written = 0
            for q in batch:
                qid     = q["qid"]
                ct_dict = tags.get(qid)
                if ct_dict:
                    c.execute(
                        "UPDATE questions SET concept_tags = ? WHERE qid = ?",
                        (json.dumps(ct_dict), qid)
                    )
                    batch_written += 1
                else:
                    print(f"    WARNING: No tags returned for {qid}")
                    LOG["errors"].append(f"No tags for {qid} in batch {batch_num}")
                    failed += 1

            conn.commit()
            processed += batch_written
            batch_log.update({
                "status": "ok", "elapsed_s": elapsed,
                "in_tokens": in_tok, "out_tokens": out_tok,
                "wrote": batch_written
            })
            print(f"  OK  {batch_written}/{len(batch)} written | "
                  f"{in_tok}+{out_tok} tokens | {elapsed}s")

        except Exception as e:
            elapsed = round(time.time() - t0, 2)
            print(f"  FAILED batch {batch_num}: {e}")
            LOG["errors"].append(f"Batch {batch_num} failed: {str(e)}")
            failed += len(batch)
            batch_log.update({"status": "failed", "error": str(e), "elapsed_s": elapsed})

        LOG["batches"].append(batch_log)

        if not dry_run and i + BATCH_SIZE < len(pending):
            time.sleep(1)

    conn.close()

    # Summary
    print("\n" + "=" * 60)
    print(f"COMPLETE  processed={processed}  failed={failed}")
    print(f"Tokens:   input={total_in}  output={total_out}")
    est_actual = (total_in / 1_000_000 * 3.0) + (total_out / 1_000_000 * 15.0)
    print(f"Actual cost: ~${est_actual:.2f}")
    print("=" * 60)

    LOG["totals"].update({
        "processed": processed, "failed": failed,
        "input_tokens": total_in, "output_tokens": total_out,
        "est_cost_usd": round(est_actual, 3)
    })
    LOG["completed"] = datetime.now(timezone.utc).isoformat()
    LOG["status"]    = "success" if not failed else "completed_with_errors"

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(LOG, f, indent=2)
    print(f"Log: {log_path.name}")


# ── Entry ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Populate concept_tags for ITE questions via Claude API"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Show first batch prompt preview, no API call")
    parser.add_argument("--limit",   type=int,
                        help="Process only N questions (for testing)")
    parser.add_argument("--reset",   action="store_true",
                        help="Clear concept_tags before reprocessing (use with --year to scope)")
    parser.add_argument("--year",    type=int,
                        help="Filter to a single exam year (e.g. --year 2018)")
    args = parser.parse_args()
    run(dry_run=args.dry_run, limit=args.limit, reset=args.reset, year=args.year)
