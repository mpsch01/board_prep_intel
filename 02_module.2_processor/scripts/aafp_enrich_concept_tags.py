#!/usr/bin/env python3
"""
aafp_enrich_concept_tags.py — API Enrichment for AAFP Questions
================================================================
Adds concept_tags, subcategory, and ICD-10 codes to aafp_questions.

Mirrors the ITE enrichment schema so AAFP and ITE question sets are
comparable for trend analysis.

OUTPUT COLUMNS (added to aafp_questions):
  concept_tags  TEXT  JSON: {diagnoses, drugs, guidelines, thresholds, concept_summary}
  subcategory   TEXT  e.g., Diagnosis, Management, Pharmacology, Screening, Workup

ICD-10 codes: inserted into aafp_question_icd10 for questions not yet covered.

MODES:
  --mode linked    643 questions with article xref (uses article title + categories as context)
  --mode unlinked  578 questions without article xref (uses ITE neighbor stem as context)
  --mode all       All 1,221 questions [default]

FLAGS:
  --dry-run        Print first 3 prompts without calling the API
  --rerun          Re-process questions that already have concept_tags
  --rerun-icd10    Re-insert ICD-10 even for already-covered questions
  --limit N        Process only N questions (for testing)
  --sleep SECS     Seconds to sleep between API calls (default: 0.5)
  --model NAME     Claude model to use (default: claude-sonnet-4-5)

RESUME SAFETY:
  By default, skips rows where concept_tags IS NOT NULL.
  Use --rerun to reprocess everything.

USAGE:
  python aafp_enrich_concept_tags.py --mode linked --dry-run
  python aafp_enrich_concept_tags.py --mode linked --limit 10
  python aafp_enrich_concept_tags.py --mode all
  python aafp_enrich_concept_tags.py --mode unlinked --rerun
"""

import argparse
import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"

# ── Config ────────────────────────────────────────────────────────────────────
DEFAULT_MODEL   = "claude-haiku-4-5-20251001"
DEFAULT_SLEEP   = 0.5   # seconds between API calls
MAX_TOKENS      = 1024  # response budget per question
VALID_MODES     = {"linked", "unlinked", "all"}

VALID_SUBCATEGORIES = {
    "Diagnosis", "Management", "Pharmacology", "Screening",
    "Workup", "Prevention", "Counseling", "Prognosis/Risk",
    "Treatment", "Interpretation", "Pathophysiology"
}

# ── Prompt templates ──────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a clinical knowledge extraction system for a Family Medicine board exam question bank.
Your job is to extract structured clinical metadata from board review questions.
Always return valid JSON. Never include explanatory text outside the JSON."""


def build_linked_prompt(stem: str, explanation: str | None,
                        article_titles: str, categories: str) -> str:
    explanation_block = (
        f"\nEXPLANATION:\n{explanation.strip()[:800]}\n"
        if explanation else ""
    )
    return f"""Analyze this AAFP Board Review Question and extract structured clinical metadata.

QUESTION STEM:
{stem.strip()[:600]}
{explanation_block}
LINKED CLINICAL GUIDELINE(S):
{article_titles[:400]}
Categories: {categories[:200]}

Extract the following as a single valid JSON object:
{{
  "concept_tags": {{
    "diagnoses": ["list of primary and differential diagnoses being tested"],
    "drugs": ["medications or drug classes referenced"],
    "guidelines": ["specific guidelines, societies, or organizations cited"],
    "thresholds": ["numeric cutoffs, criteria, or clinical thresholds"],
    "concept_summary": "1-2 sentence summary of what clinical concept or decision point is tested"
  }},
  "subcategory": "One of: Diagnosis, Management, Pharmacology, Screening, Workup, Prevention, Counseling, Prognosis/Risk, Treatment, Interpretation, Pathophysiology",
  "icd10_codes": [
    {{"code": "X00.0", "desc": "Description", "relevance": "primary"}}
  ]
}}

Return ONLY the JSON object. No markdown, no explanation, no code fences."""


def build_unlinked_prompt(stem: str, explanation: str | None,
                          ite_neighbor_stem: str | None,
                          ite_neighbor_dist: float | None,
                          ite_body_system: str | None) -> str:
    explanation_block = (
        f"\nEXPLANATION:\n{explanation.strip()[:800]}\n"
        if explanation else ""
    )
    neighbor_block = ""
    if ite_neighbor_stem and ite_neighbor_dist is not None and ite_neighbor_dist < 0.50:
        neighbor_block = f"""
SEMANTICALLY SIMILAR ITE EXAM QUESTION (distance={ite_neighbor_dist:.3f}):
{ite_neighbor_stem.strip()[:400]}
Body system: {ite_body_system or 'Unknown'}
"""
    return f"""Analyze this AAFP Board Review Question and extract structured clinical metadata.

QUESTION STEM:
{stem.strip()[:600]}
{explanation_block}{neighbor_block}
Extract the following as a single valid JSON object:
{{
  "concept_tags": {{
    "diagnoses": ["list of primary and differential diagnoses being tested"],
    "drugs": ["medications or drug classes referenced"],
    "guidelines": ["specific guidelines, societies, or organizations cited"],
    "thresholds": ["numeric cutoffs, criteria, or clinical thresholds"],
    "concept_summary": "1-2 sentence summary of what clinical concept or decision point is tested"
  }},
  "subcategory": "One of: Diagnosis, Management, Pharmacology, Screening, Workup, Prevention, Counseling, Prognosis/Risk, Treatment, Interpretation, Pathophysiology",
  "icd10_codes": [
    {{"code": "X00.0", "desc": "Description", "relevance": "primary"}}
  ]
}}

Return ONLY the JSON object. No markdown, no explanation, no code fences."""


# ── Context builders ───────────────────────────────────────────────────────────

def get_linked_context(conn: sqlite3.Connection, aafp_qid: str) -> dict:
    """Pull article titles + categories for a linked question."""
    rows = conn.execute("""
        SELECT a.title, a.categories
        FROM aafp_qid_art_xref x
        JOIN articles a ON x.article_id = a.article_id
        WHERE x.aafp_qid = ?
    """, (aafp_qid,)).fetchall()
    titles = " | ".join(r[0] or "" for r in rows if r[0])
    cats   = ", ".join(set(r[1] or "" for r in rows if r[1]))
    return {"article_titles": titles or "N/A", "categories": cats or ""}


def get_explanation(conn: sqlite3.Connection, aafp_qid: str) -> str | None:
    """Pull explanation text from aafp_explanations."""
    row = conn.execute(
        "SELECT explanation FROM aafp_explanations WHERE aafp_qid = ?",
        (aafp_qid,)
    ).fetchone()
    return row[0] if row else None


def get_ite_neighbor(conn: sqlite3.Connection,
                     ite_qid: str | None) -> tuple[str | None, str | None]:
    """Pull ITE neighbor's question_text and body_system."""
    if not ite_qid:
        return None, None
    row = conn.execute(
        "SELECT question_text, body_system FROM questions WHERE qid = ?",
        (ite_qid,)
    ).fetchone()
    if row:
        return row[0], row[1]
    return None, None


# ── JSON parsing ───────────────────────────────────────────────────────────────

def extract_json(text: str) -> dict | None:
    """Strip markdown fences and parse JSON from API response."""
    text = text.strip()
    # Remove ```json ... ``` or ``` ... ```
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to extract JSON object
        m = re.search(r'\{[\s\S]*\}', text)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                pass
    return None


def normalize_subcategory(raw: str | None) -> str | None:
    """Snap raw subcategory to nearest valid value, or return as-is."""
    if not raw:
        return None
    if raw in VALID_SUBCATEGORIES:
        return raw
    # Case-insensitive match
    lower = raw.lower()
    for valid in VALID_SUBCATEGORIES:
        if lower == valid.lower():
            return valid
    # Partial match fallback
    for valid in VALID_SUBCATEGORIES:
        if lower in valid.lower() or valid.lower() in lower:
            return valid
    return raw  # keep as-is if no match


# ── Schema migration ───────────────────────────────────────────────────────────

def ensure_columns(conn: sqlite3.Connection) -> None:
    """Add concept_tags and subcategory columns to aafp_questions if missing."""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(aafp_questions)")}
    if "concept_tags" not in cols:
        conn.execute("ALTER TABLE aafp_questions ADD COLUMN concept_tags TEXT")
        print("  → Added concept_tags column to aafp_questions")
    if "subcategory" not in cols:
        conn.execute("ALTER TABLE aafp_questions ADD COLUMN subcategory TEXT")
        print("  → Added subcategory column to aafp_questions")
    conn.commit()


# ── Question selection ─────────────────────────────────────────────────────────

def get_questions(conn: sqlite3.Connection, mode: str,
                  rerun: bool, limit: int | None) -> list[dict]:
    """Fetch the target question set based on mode and rerun flag."""
    base_filter = "" if rerun else "AND aq.concept_tags IS NULL"

    if mode == "linked":
        join = "JOIN aafp_qid_art_xref x ON aq.aafp_qid = x.aafp_qid"
        group = "GROUP BY aq.aafp_qid"
    elif mode == "unlinked":
        join = "LEFT JOIN aafp_qid_art_xref x ON aq.aafp_qid = x.aafp_qid"
        group = "GROUP BY aq.aafp_qid HAVING COUNT(x.article_id) = 0"
    else:  # all
        join = "LEFT JOIN aafp_qid_art_xref x ON aq.aafp_qid = x.aafp_qid"
        group = "GROUP BY aq.aafp_qid"

    sql = f"""
        SELECT aq.aafp_qid, aq.stem, aq.ite_nearest_qid, aq.ite_nearest_dist,
               aq.body_system, aq.concept_tags,
               COUNT(x.article_id) as n_articles
        FROM aafp_questions aq
        {join}
        WHERE 1=1 {base_filter}
        {group}
        ORDER BY aq.aafp_qid
    """
    if limit:
        sql += f" LIMIT {limit}"

    rows = conn.execute(sql).fetchall()
    return [
        {
            "aafp_qid": r[0], "stem": r[1],
            "ite_nearest_qid": r[2], "ite_nearest_dist": r[3],
            "body_system": r[4], "concept_tags": r[5],
            "n_articles": r[6]
        }
        for r in rows
    ]


# ── ICD-10 insert ──────────────────────────────────────────────────────────────

def insert_icd10(conn: sqlite3.Connection, aafp_qid: str,
                 codes: list[dict], rerun_icd10: bool) -> int:
    """Insert ICD-10 codes into aafp_question_icd10. Returns count inserted."""
    if not codes:
        return 0

    already_covered = conn.execute(
        "SELECT COUNT(*) FROM aafp_question_icd10 WHERE aafp_qid = ?",
        (aafp_qid,)
    ).fetchone()[0]

    if already_covered and not rerun_icd10:
        return 0  # skip — already has ICD-10 entries

    if already_covered and rerun_icd10:
        conn.execute(
            "DELETE FROM aafp_question_icd10 WHERE aafp_qid = ?", (aafp_qid,)
        )

    count = 0
    for entry in codes:
        code = entry.get("code", "").strip()
        desc = entry.get("desc", "").strip()
        relevance = entry.get("relevance", "primary").strip()
        if not code or not re.match(r'^[A-Z]\d', code):
            continue  # skip malformed codes
        conn.execute("""
            INSERT OR IGNORE INTO aafp_question_icd10 (aafp_qid, icd10_code, icd10_desc, relevance)
            VALUES (?, ?, ?, ?)
        """, (aafp_qid, code, desc, relevance))
        count += 1

    return count


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="AAFP concept_tags + subcategory + ICD-10 enricher")
    parser.add_argument("--mode", choices=list(VALID_MODES), default="all",
                        help="Which question set to process (default: all)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print first 3 prompts, no API calls")
    parser.add_argument("--rerun", action="store_true",
                        help="Re-process questions already enriched")
    parser.add_argument("--rerun-icd10", action="store_true",
                        help="Re-insert ICD-10 for already-covered questions")
    parser.add_argument("--limit", type=int, default=None,
                        help="Process only N questions")
    parser.add_argument("--sleep", type=float, default=DEFAULT_SLEEP,
                        help=f"Sleep between API calls in seconds (default: {DEFAULT_SLEEP})")
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        help=f"Claude model (default: {DEFAULT_MODEL})")
    args = parser.parse_args()

    # ── Validate API key ───────────────────────────────────────────────────────
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key and not args.dry_run:
        print("ERROR: ANTHROPIC_API_KEY not found in environment.")
        print("  Set it with: $env:ANTHROPIC_API_KEY = 'sk-...'  (PowerShell)")
        sys.exit(1)

    # ── Import anthropic (only needed for real runs) ───────────────────────────
    client = None
    if not args.dry_run:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
        except ImportError:
            print("ERROR: anthropic package not installed.")
            print("  Run: pip install anthropic")
            sys.exit(1)

    # ── Connect to DB ──────────────────────────────────────────────────────────
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")

    print(f"\n{'='*60}")
    print(f"AAFP Concept Tag Enricher")
    print(f"  DB:    {DB_PATH}")
    print(f"  Mode:  {args.mode}")
    print(f"  Model: {args.model}")
    print(f"  Rerun: {args.rerun}")
    print(f"  Dry:   {args.dry_run}")
    print(f"{'='*60}\n")

    # ── Ensure schema ──────────────────────────────────────────────────────────
    ensure_columns(conn)

    # ── Load question queue ────────────────────────────────────────────────────
    questions = get_questions(conn, args.mode, args.rerun, args.limit)
    total = len(questions)
    print(f"Questions to process: {total}")
    if total == 0:
        print("Nothing to do. Use --rerun to re-process existing entries.")
        conn.close()
        return

    # ── Process ────────────────────────────────────────────────────────────────
    n_done = 0
    n_icd10 = 0
    n_errors = 0

    for i, q in enumerate(questions, 1):
        aafp_qid = q["aafp_qid"]
        stem     = q["stem"] or ""
        is_linked = q["n_articles"] > 0

        # Build prompt
        explanation = get_explanation(conn, aafp_qid)

        if is_linked:
            ctx = get_linked_context(conn, aafp_qid)
            prompt = build_linked_prompt(
                stem, explanation,
                ctx["article_titles"], ctx["categories"]
            )
        else:
            ite_stem, ite_bs = get_ite_neighbor(conn, q["ite_nearest_qid"])
            prompt = build_unlinked_prompt(
                stem, explanation,
                ite_stem, q["ite_nearest_dist"], ite_bs
            )

        # Dry run: print prompts and stop
        if args.dry_run:
            print(f"\n{'─'*50}")
            print(f"[{i}/{total}] {aafp_qid} | linked={is_linked}")
            print("PROMPT:")
            print(prompt[:1000])
            if i >= 3:
                print("\n[dry-run] Stopping after 3 prompts.")
                break
            continue

        # Call API
        try:
            response = client.messages.create(
                model=args.model,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            )
            raw_text = response.content[0].text
        except Exception as e:
            print(f"  [{i}/{total}] ERROR calling API for {aafp_qid}: {e}")
            n_errors += 1
            time.sleep(2)  # back off on error
            continue

        # Parse response
        parsed = extract_json(raw_text)
        if not parsed:
            print(f"  [{i}/{total}] PARSE ERROR for {aafp_qid}. Raw: {raw_text[:200]}")
            n_errors += 1
            continue

        # Extract fields
        concept_tags = parsed.get("concept_tags")
        subcategory  = normalize_subcategory(parsed.get("subcategory"))
        icd10_codes  = parsed.get("icd10_codes", [])

        concept_tags_str = json.dumps(concept_tags) if concept_tags else None

        # Write to DB
        conn.execute("""
            UPDATE aafp_questions
            SET concept_tags = ?, subcategory = ?
            WHERE aafp_qid = ?
        """, (concept_tags_str, subcategory, aafp_qid))

        icd_inserted = insert_icd10(conn, aafp_qid, icd10_codes, args.rerun_icd10)
        n_icd10 += icd_inserted
        conn.commit()
        n_done += 1

        # Progress
        pct = (i / total) * 100
        print(f"  [{i:4d}/{total}] {aafp_qid} | {subcategory or '?':20s} | "
              f"icd10+{icd_inserted} | {pct:.1f}%")

        if args.sleep > 0:
            time.sleep(args.sleep)

    # ── Summary ────────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"DONE")
    print(f"  Enriched:      {n_done}/{total} questions")
    print(f"  ICD-10 rows:   {n_icd10} inserted")
    print(f"  Errors:        {n_errors}")

    if not args.dry_run:
        # Final coverage check
        n_ct = conn.execute(
            "SELECT COUNT(*) FROM aafp_questions WHERE concept_tags IS NOT NULL"
        ).fetchone()[0]
        n_sc = conn.execute(
            "SELECT COUNT(*) FROM aafp_questions WHERE subcategory IS NOT NULL"
        ).fetchone()[0]
        n_total = conn.execute("SELECT COUNT(*) FROM aafp_questions").fetchone()[0]
        n_icd10_total = conn.execute(
            "SELECT COUNT(DISTINCT aafp_qid) FROM aafp_question_icd10"
        ).fetchone()[0]
        print(f"\n  Coverage after run:")
        print(f"    concept_tags:  {n_ct}/{n_total} ({n_ct/n_total*100:.1f}%)")
        print(f"    subcategory:   {n_sc}/{n_total} ({n_sc/n_total*100:.1f}%)")
        print(f"    icd10 (dist):  {n_icd10_total}/{n_total} ({n_icd10_total/n_total*100:.1f}%)")
        print(f"{'='*60}\n")

    conn.close()


if __name__ == "__main__":
    main()
