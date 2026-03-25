"""
preprocess_keywords_v2.py — Claude Batch Keyword Preprocessor
==============================================================
Preprocessing-First Design | ITE Intelligence Pipeline

PURPOSE:
  Replace noisy regex-extracted keywords with clean, structured,
  clinically-meaningful concept_tags for every question in the DB.
  This is a ONE-TIME preprocessing run. Results stored permanently.

WHAT IT DOES:
  - Reads questions WHERE concept_tags IS NULL (resume-safe)
  - Batches 25 questions per Claude API call
  - Returns structured JSON per question:
      {
        "diagnoses":        [...],   // clinical conditions tested
        "drugs":            [...],   // medications, drug classes
        "guidelines":       [...],   // org + year (e.g. "ACC/AHA 2017")
        "thresholds":       [...],   // numeric values (BP, A1C, labs)
        "concept_summary":  "..."    // 1-2 sentence exam-focused summary
      }
  - Writes results back to questions.concept_tags (JSON string)
  - Logs every batch with timing and token usage

COST ESTIMATE:
  ~1189 questions / 25 per batch = ~48 API calls
  ~$0.03-0.05 per call = ~$1.50-2.50 total (one-time)

RESUME BEHAVIOR:
  Safe to interrupt and rerun. Already-processed questions are skipped.
  Use --reset to clear all concept_tags and start fresh.

RUN:
  python scripts/preprocess_keywords_v2.py
  python scripts/preprocess_keywords_v2.py --dry-run   # show first batch only
  python scripts/preprocess_keywords_v2.py --limit 50  # process N questions
  python scripts/preprocess_keywords_v2.py --reset      # clear + reprocess all
"""

import sqlite3, json, re, os, argparse, time
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


# ── Config ─────────────────────────────────────────────────────────────────
BASE_DIR  = Path(__file__).resolve().parent.parent
DB_PATH   = BASE_DIR / "00_database" / "db" / "ite_intelligence.db"
LOG_DIR   = BASE_DIR / "logs"
LOG_PATH  = LOG_DIR / f"preprocess_keywords_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"

MODEL      = "claude-sonnet-4-20250514"
BATCH_SIZE = 25
RETRY_MAX  = 3
RETRY_WAIT = 5   # seconds between retries

LOG = {
    "started":   str(datetime.now(timezone.utc)),
    "model":     MODEL,
    "batches":   [],
    "totals":    {"processed": 0, "failed": 0, "skipped": 0, "input_tokens": 0, "output_tokens": 0},
    "errors":    []
}

# ── System prompt ───────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a medical education expert specializing in ABFM board exam preparation.

Your task: analyze ITE (In-Training Examination) questions and extract structured clinical concept tags.

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
def format_question_for_prompt(q: dict) -> str:
    """Build a compact but complete question block for the API prompt."""
    lines = []
    lines.append(f"QID: {q['qid']} | {q['exam_year']} | {q.get('body_system','?')} / {q.get('subcategory','?')}")

    stem = (q.get('question_text') or '').strip().replace('\n', ' ')
    # Trim very long stems — first 400 chars is enough for concept extraction
    if len(stem) > 400:
        stem = stem[:400] + "..."
    lines.append(f"STEM: {stem}")

    # Choices
    try:
        choices = json.loads(q.get('choices') or '[]')
        for ch in choices[:5]:
            lines.append(f"  ({ch['letter']}) {ch['text'][:100]}")
    except Exception:
        pass

    correct = q.get('correct_text') or ''
    lines.append(f"CORRECT: ({q.get('correct_letter','?')}) {correct[:120]}")

    expl = (q.get('explanation') or '').strip().replace('\n', ' ')
    if len(expl) > 500:
        expl = expl[:500] + "..."
    lines.append(f"EXPLANATION: {expl}")

    return '\n'.join(lines)


# ── Call Claude for one batch ───────────────────────────────────────────────
def process_batch(client, questions: list, dry_run=False) -> dict:
    """
    Send a batch of questions to Claude.
    Returns dict: {qid: concept_tags_dict, ...}
    Raises on unrecoverable error.
    """
    prompt_parts = []
    for q in questions:
        prompt_parts.append(format_question_for_prompt(q))
        prompt_parts.append("---")

    user_message = (
        f"Please extract concept tags for the following {len(questions)} ITE questions.\n\n"
        + '\n'.join(prompt_parts)
    )

    if dry_run:
        print("\n[DRY RUN] Would send to Claude:")
        print(f"  Questions: {[q['qid'] for q in questions]}")
        print(f"  Prompt length: ~{len(user_message)} chars")
        print("  First question preview:")
        print("  " + format_question_for_prompt(questions[0])[:300])
        return {}

    for attempt in range(1, RETRY_MAX + 1):
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=4000,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}]
            )
            raw = response.content[0].text.strip()

            # Strip any accidental markdown fences
            raw = re.sub(r'^```json\s*', '', raw)
            raw = re.sub(r'^```\s*',     '', raw)
            raw = re.sub(r'\s*```$',     '', raw)

            result = json.loads(raw)
            return {
                "tags":          result,
                "input_tokens":  response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            }

        except json.JSONDecodeError as e:
            print(f"    JSON parse error attempt {attempt}: {e}")
            print(f"    Raw response[:200]: {raw[:200]}")
            if attempt == RETRY_MAX:
                raise
            time.sleep(RETRY_WAIT)

        except Exception as e:
            print(f"    API error attempt {attempt}: {e}")
            if attempt == RETRY_MAX:
                raise
            time.sleep(RETRY_WAIT * attempt)


# ── Main ────────────────────────────────────────────────────────────────────
def run(dry_run=False, limit=None, reset=False):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key and not dry_run:
        raise ValueError("ANTHROPIC_API_KEY not set. Add to .env or environment.")

    client = anthropic.Anthropic(api_key=api_key) if not dry_run else None

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Optionally reset all concept_tags
    if reset:
        print("Resetting all concept_tags to NULL...")
        c.execute("UPDATE questions SET concept_tags = NULL")
        conn.commit()
        print("  Done.")

    # Load questions that still need processing
    c.execute("""
        SELECT qid, exam_year, body_system, subcategory,
               question_text, choices, correct_letter, correct_text, explanation
        FROM questions
        WHERE concept_tags IS NULL
        ORDER BY exam_year, qid
    """)
    pending = [dict(r) for r in c.fetchall()]

    total_pending = len(pending)
    if limit:
        pending = pending[:limit]

    print("=" * 60)
    print("ITE Keyword Preprocessor v2")
    print(f"  Model:        {MODEL}")
    print(f"  Pending:      {total_pending} questions need concept_tags")
    print(f"  Processing:   {len(pending)} this run")
    print(f"  Batch size:   {BATCH_SIZE}")
    print(f"  Est. batches: {len(pending) // BATCH_SIZE + 1}")
    print(f"  dry_run:      {dry_run}")
    print("=" * 60)

    if total_pending == 0:
        print("All questions already have concept_tags. Use --reset to reprocess.")
        return

    # Process in batches
    processed = 0
    failed    = 0
    total_in  = 0
    total_out = 0

    for batch_num, i in enumerate(range(0, len(pending), BATCH_SIZE), start=1):
        batch = pending[i:i + BATCH_SIZE]
        qids  = [q['qid'] for q in batch]
        t0    = time.time()

        print(f"\n[Batch {batch_num}] {qids[0]} .. {qids[-1]}  ({len(batch)} questions)")

        batch_log = {
            "batch":     batch_num,
            "qids":      qids,
            "status":    None,
            "elapsed_s": None,
            "in_tokens": None,
            "out_tokens":None,
            "error":     None
        }

        try:
            result = process_batch(client, batch, dry_run=dry_run)

            if dry_run:
                batch_log["status"] = "dry_run_skipped"
                LOG["batches"].append(batch_log)
                break  # only show first batch in dry run

            tags      = result["tags"]
            in_tok    = result["input_tokens"]
            out_tok   = result["output_tokens"]
            elapsed   = round(time.time() - t0, 2)
            total_in  += in_tok
            total_out += out_tok

            # Write each QID's concept_tags back to DB
            batch_processed = 0
            for q in batch:
                qid     = q['qid']
                ct_dict = tags.get(qid)
                if ct_dict:
                    c.execute(
                        "UPDATE questions SET concept_tags = ? WHERE qid = ?",
                        (json.dumps(ct_dict), qid)
                    )
                    batch_processed += 1
                else:
                    print(f"    WARNING: No tags returned for {qid}")
                    LOG["errors"].append(f"No tags for {qid} in batch {batch_num}")
                    failed += 1

            conn.commit()
            processed    += batch_processed
            batch_log.update({
                "status":     "ok",
                "elapsed_s":  elapsed,
                "in_tokens":  in_tok,
                "out_tokens": out_tok,
                "wrote":      batch_processed
            })
            print(f"  OK  {batch_processed}/{len(batch)} written | "
                  f"{in_tok}+{out_tok} tokens | {elapsed}s")

        except Exception as e:
            elapsed = round(time.time() - t0, 2)
            print(f"  FAILED batch {batch_num}: {e}")
            LOG["errors"].append(f"Batch {batch_num} failed: {str(e)}")
            failed += len(batch)
            batch_log.update({"status": "failed", "error": str(e), "elapsed_s": elapsed})

        LOG["batches"].append(batch_log)

        # Polite pause between batches (avoid rate limits)
        if not dry_run and i + BATCH_SIZE < len(pending):
            time.sleep(1)

    conn.close()

    # Summary
    print("\n" + "=" * 60)
    print(f"COMPLETE  processed={processed}  failed={failed}")
    print(f"Tokens:   input={total_in}  output={total_out}")
    est_cost = (total_in / 1_000_000 * 3.0) + (total_out / 1_000_000 * 15.0)
    print(f"Est cost: ~${est_cost:.2f}")
    print("=" * 60)

    LOG["totals"].update({
        "processed": processed, "failed": failed,
        "input_tokens": total_in, "output_tokens": total_out,
        "est_cost_usd": round(est_cost, 3)
    })
    LOG["completed"] = str(datetime.now(timezone.utc))
    LOG["status"]    = "success" if not failed else "completed_with_errors"

    LOG_DIR.mkdir(exist_ok=True)
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(LOG, f, indent=2)
    print(f"Log: {LOG_PATH.name}")


# ── Entry ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Show first batch prompt, no API call")
    parser.add_argument("--limit",   type=int,            help="Process only N questions")
    parser.add_argument("--reset",   action="store_true", help="Clear all concept_tags first")
    args = parser.parse_args()
    run(dry_run=args.dry_run, limit=args.limit, reset=args.reset)
