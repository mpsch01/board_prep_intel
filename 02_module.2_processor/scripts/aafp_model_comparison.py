#!/usr/bin/env python3
"""
aafp_model_comparison.py — Haiku 4.5 vs Sonnet 4.6 side-by-side quality check
===============================================================================
Runs 3 AAFP questions through both models and prints outputs for comparison.
Pick one linked (has article context) and one unlinked for a fair test.

USAGE:
    python aafp_model_comparison.py

OUTPUT: prints side-by-side JSON for each question, both models.
Eyeball concept_tags quality, subcategory accuracy, ICD-10 precision.
"""

import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH      = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"

MODELS = {
    "haiku":  "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-6",
}

SYSTEM_PROMPT = """You are a clinical knowledge extraction system for a Family Medicine board exam question bank.
Your job is to extract structured clinical metadata from board review questions.
Always return valid JSON. Never include explanatory text outside the JSON."""

# ── Pick test questions: 2 linked, 1 unlinked ─────────────────────────────────
TEST_QIDS = None  # None = auto-select from DB


def build_linked_prompt(stem, explanation, article_titles, categories):
    exp_block = f"\nEXPLANATION:\n{explanation.strip()[:800]}\n" if explanation else ""
    return f"""Analyze this AAFP Board Review Question and extract structured clinical metadata.

QUESTION STEM:
{stem.strip()[:600]}
{exp_block}
LINKED CLINICAL GUIDELINE(S):
{article_titles[:400]}
Categories: {categories[:200]}

Extract the following as a single valid JSON object:
{{
  "concept_tags": {{
    "diagnoses": ["primary and differential diagnoses being tested"],
    "drugs": ["medications or drug classes referenced"],
    "guidelines": ["specific guidelines or organizations cited"],
    "thresholds": ["numeric cutoffs or clinical thresholds"],
    "concept_summary": "1-2 sentence summary of what clinical concept is tested"
  }},
  "subcategory": "One of: Diagnosis, Management, Pharmacology, Screening, Workup, Prevention, Counseling, Prognosis/Risk, Treatment, Interpretation, Pathophysiology",
  "icd10_codes": [
    {{"code": "X00.0", "desc": "Description", "relevance": "primary"}}
  ]
}}

Return ONLY the JSON object. No markdown, no explanation."""


def build_unlinked_prompt(stem, explanation, ite_stem, ite_dist, ite_bs):
    exp_block = f"\nEXPLANATION:\n{explanation.strip()[:800]}\n" if explanation else ""
    neighbor_block = ""
    if ite_stem and ite_dist is not None and ite_dist < 0.50:
        neighbor_block = f"\nSEMANTICALLY SIMILAR ITE QUESTION (dist={ite_dist:.3f}):\n{ite_stem.strip()[:400]}\nBody system: {ite_bs or 'Unknown'}\n"
    return f"""Analyze this AAFP Board Review Question and extract structured clinical metadata.

QUESTION STEM:
{stem.strip()[:600]}
{exp_block}{neighbor_block}
Extract the following as a single valid JSON object:
{{
  "concept_tags": {{
    "diagnoses": ["primary and differential diagnoses being tested"],
    "drugs": ["medications or drug classes referenced"],
    "guidelines": ["specific guidelines or organizations cited"],
    "thresholds": ["numeric cutoffs or clinical thresholds"],
    "concept_summary": "1-2 sentence summary of what clinical concept is tested"
  }},
  "subcategory": "One of: Diagnosis, Management, Pharmacology, Screening, Workup, Prevention, Counseling, Prognosis/Risk, Treatment, Interpretation, Pathophysiology",
  "icd10_codes": [
    {{"code": "X00.0", "desc": "Description", "relevance": "primary"}}
  ]
}}

Return ONLY the JSON object. No markdown, no explanation."""


def extract_json(text):
    text = re.sub(r'^```(?:json)?\s*', '', text.strip())
    text = re.sub(r'\s*```$', '', text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r'\{[\s\S]*\}', text)
        if m:
            try:
                return json.loads(m.group())
            except:
                pass
    return None


def get_test_questions(conn):
    """Auto-select: 5 linked + 5 unlinked = 10 questions, varied body systems."""
    linked = conn.execute("""
        SELECT aq.aafp_qid, aq.stem, aq.body_system,
               aq.ite_nearest_qid, aq.ite_nearest_dist,
               COUNT(x.article_id) as n_art
        FROM aafp_questions aq
        JOIN aafp_qid_art_xref x ON aq.aafp_qid = x.aafp_qid
        GROUP BY aq.aafp_qid
        ORDER BY aq.body_system, aq.aafp_qid
        LIMIT 5
    """).fetchall()

    unlinked = conn.execute("""
        SELECT aq.aafp_qid, aq.stem, aq.body_system,
               aq.ite_nearest_qid, aq.ite_nearest_dist, 0 as n_art
        FROM aafp_questions aq
        LEFT JOIN aafp_qid_art_xref x ON aq.aafp_qid = x.aafp_qid
        WHERE x.aafp_qid IS NULL
        ORDER BY aq.body_system, aq.aafp_qid
        LIMIT 5
    """).fetchall()

    return [dict(zip(["aafp_qid","stem","body_system","ite_nearest_qid","ite_nearest_dist","n_art"], r))
            for r in (linked + unlinked)]


def build_prompt(conn, q):
    aafp_qid = q["aafp_qid"]
    stem = q["stem"] or ""
    exp_row = conn.execute(
        "SELECT explanation FROM aafp_explanations WHERE aafp_qid=?", (aafp_qid,)
    ).fetchone()
    explanation = exp_row[0] if exp_row else None

    if q["n_art"] > 0:
        arts = conn.execute("""
            SELECT a.title, a.categories
            FROM aafp_qid_art_xref x JOIN articles a ON x.article_id = a.article_id
            WHERE x.aafp_qid=?
        """, (aafp_qid,)).fetchall()
        titles = " | ".join(r[0] or "" for r in arts)
        cats = ", ".join(set(r[1] or "" for r in arts))
        return build_linked_prompt(stem, explanation, titles, cats), "linked"
    else:
        ite_row = None
        if q["ite_nearest_qid"]:
            ite_row = conn.execute(
                "SELECT question_text, body_system FROM questions WHERE qid=?",
                (q["ite_nearest_qid"],)
            ).fetchone()
        ite_stem = ite_row[0] if ite_row else None
        ite_bs   = ite_row[1] if ite_row else None
        return build_unlinked_prompt(stem, explanation, ite_stem, q["ite_nearest_dist"], ite_bs), "unlinked"


def call_model(client, model_name, prompt, max_tokens=1024):
    response = client.messages.create(
        model=model_name,
        max_tokens=max_tokens,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = response.content[0].text
    usage = response.usage
    return raw, usage


def print_comparison(qid, body_system, mode, prompt, results):
    print(f"\n{'═'*70}")
    print(f"  {qid} | {body_system} | {mode.upper()}")
    print(f"{'═'*70}")

    # Print stem preview
    stem_preview = prompt.split("QUESTION STEM:\n")[-1][:200].split("\n")[0]
    print(f"  Stem: {stem_preview}...")
    print()

    for model_key, (parsed, usage, elapsed) in results.items():
        model_name = MODELS[model_key]
        print(f"  ── {model_key.upper()} ({model_name}) ──")
        print(f"     Tokens: {usage.input_tokens} in / {usage.output_tokens} out | {elapsed:.1f}s")
        if parsed:
            ct = parsed.get("concept_tags", {})
            print(f"     subcategory:    {parsed.get('subcategory','?')}")
            print(f"     diagnoses:      {ct.get('diagnoses', [])}")
            print(f"     drugs:          {ct.get('drugs', [])}")
            print(f"     guidelines:     {ct.get('guidelines', [])}")
            print(f"     thresholds:     {ct.get('thresholds', [])}")
            print(f"     concept_summary:{ct.get('concept_summary','')[:120]}")
            icd = parsed.get("icd10_codes", [])
            icd_summary = [str(c.get("code")) + " (" + str(c.get("relevance")) + ")" for c in icd[:3]]
            print(f"     icd10_codes:    {icd_summary}")
        else:
            print(f"     ⚠ PARSE FAILED")
        print()


OUTPUT_FILE = Path(__file__).resolve().parent.parent.parent / "aafp_comparison_results.json"


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set.")
        print("  PowerShell: $env:ANTHROPIC_API_KEY = 'sk-ant-...'")
        sys.exit(1)

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
    except ImportError:
        print("ERROR: pip install anthropic")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    questions = get_test_questions(conn)

    print(f"\nRunning {len(questions)} questions × {len(MODELS)} models = {len(questions)*len(MODELS)} API calls")
    print(f"Models: {list(MODELS.values())}\n")

    total_cost = {"haiku": 0.0, "sonnet": 0.0}
    all_results = []

    for q in questions:
        prompt, mode = build_prompt(conn, q)
        results = {}

        for model_key, model_name in MODELS.items():
            t0 = time.time()
            try:
                raw, usage = call_model(client, model_name, prompt)
                elapsed = time.time() - t0
                parsed = extract_json(raw)

                # Rough cost estimate (per-call)
                if model_key == "haiku":
                    cost = (usage.input_tokens / 1e6 * 1.0) + (usage.output_tokens / 1e6 * 5.0)
                else:
                    cost = (usage.input_tokens / 1e6 * 3.0) + (usage.output_tokens / 1e6 * 15.0)
                total_cost[model_key] += cost

                results[model_key] = (parsed, usage, elapsed)
            except Exception as e:
                print(f"  ERROR [{model_key}] {q['aafp_qid']}: {e}")
                results[model_key] = (None, type('U', (), {'input_tokens':0,'output_tokens':0})(), 0)

            time.sleep(0.3)

        print_comparison(q["aafp_qid"], q["body_system"], mode, prompt, results)

        # Collect for JSON output
        qr = {"aafp_qid": q["aafp_qid"], "body_system": q["body_system"], "mode": mode,
              "stem_preview": q["stem"][:200] if q["stem"] else ""}
        for model_key, (parsed, usage, elapsed) in results.items():
            qr[model_key] = {
                "parsed": parsed,
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "elapsed_s": round(elapsed, 2)
            }
        all_results.append(qr)

    conn.close()

    # Cost summary
    print(f"\n{'─'*70}")
    print(f"COST SUMMARY (standard pricing, {len(questions)} questions):")
    for k, c in total_cost.items():
        per_q = c / len(questions)
        projected_1221 = per_q * 1221
        projected_batch = projected_1221 * 0.5
        print(f"  {k:8s}: ${c:.4f} ({len(questions)} Q) | projected 1,221 Q: ${projected_1221:.2f} standard / ${projected_batch:.2f} batch")
    print()

    # Write JSON results file
    output = {
        "questions": all_results,
        "cost_summary": {k: {"sample_cost": round(c, 4),
                             "projected_1221_standard": round(c / len(questions) * 1221, 2),
                             "projected_1221_batch": round(c / len(questions) * 1221 * 0.5, 2)}
                         for k, c in total_cost.items()}
    }
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)
    print(f"Results written to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
