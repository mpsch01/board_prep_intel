#!/usr/bin/env python3
"""
⚠️  ALREADY RUN — DO NOT RE-RUN (2026-04-04)
    Status: 2018-2019 data is in ite_intelligence.db. This script has served its purpose.
    Bug: PROJECT_ROOT uses 2 hops (wrong — M1/build/ requires 3). Moot since it won't be run again.
    Retained for historical reference only. Flag for deletion on next Windows housekeeping pass.
    Gathered in: 01_module.1_warehouse/scripts/_legacy/
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

integrate_2018_2019.py — Full pipeline to integrate 2018-2019 ITE data into the DB.

Steps:
  1. Merge enriched 2018-2019 JSON into ite_questions_clean.json (1200 → 1640)
  2. Parse references from 2018-2019 explanations
  3. Fuzzy-match references against existing articles in the DB
  4. Create new article records for unmatched references
  5. Insert new questions into the DB
  6. Create question_ref_pairs entries
  7. Route enrichment ICD-10 codes into article_icd10 table
  8. Update article aggregation fields (citation_count, exam_years, qid_list)
  9. Verify final DB counts

Usage:
  python integrate_2018_2019.py --dry-run     # Preview, no DB writes
  python integrate_2018_2019.py               # Full integration
  python integrate_2018_2019.py --skip-merge  # Skip JSON merge (already done)

Requires: ite_2018_2019_enriched.json (from enrich_ite_questions.py)
"""

import sqlite3
import json
import re
import os
import sys
import shutil
import argparse
from pathlib import Path
from datetime import datetime, timezone
from difflib import SequenceMatcher
from collections import defaultdict

# ── Config ──────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent  # 00_#PROJECT_OVERHAUL/

ENRICHED_JSON = PROJECT_ROOT / "02_module.2_processor" / "ite_2018_2019_enriched.json"
MASTER_JSON = PROJECT_ROOT / "key_data_files" / "ite_questions_clean.json"
MASTER_JSON_BACKUP = PROJECT_ROOT / "key_data_files" / f"ite_questions_clean_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

DB_PATH = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"
DB_BACKUP = PROJECT_ROOT / "00_database" / "db" / f"ite_intelligence_pre2018_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"

LOG_DIR = PROJECT_ROOT / "00_database" / "logs"
LOG_PATH = LOG_DIR / f"integrate_2018_2019_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

FUZZY_MATCH_THRESHOLD = 0.75  # Minimum similarity for reference matching

LOG = {"started": str(datetime.now(timezone.utc)), "steps": [], "counts": {}, "errors": [], "warnings": []}


def log(msg, key=None, val=None):
    print(msg)
    LOG["steps"].append(msg)
    if key:
        LOG["counts"][key] = val


def warn(msg):
    print(f"  WARNING: {msg}")
    LOG["warnings"].append(msg)


def err(msg):
    print(f"  ERROR: {msg}")
    LOG["errors"].append(msg)


# ── Reference Parsing ───────────────────────────────────────────────────────

def parse_references_from_explanation(reference_text):
    """Split a reference string into individual citation entries.

    Handles formats like:
      'Ref: Author1 AB: Title1. Journal 2017;1:1-5. 2) Author2 CD: Title2. Journal 2018;2:6-10.'
      'Author1 AB: Title1. Journal 2017. Author2 CD: Title2. Journal 2018.'
    """
    if not reference_text:
        return []

    # Clean up
    text = reference_text.strip()
    text = re.sub(r'^Ref:\s*', '', text)

    # Split on numbered references: "2) " or "3) " etc
    # Also try splitting on patterns that look like new citations after a period
    parts = re.split(r'\s*\d+\)\s+', text)
    parts = [p.strip() for p in parts if p.strip()]

    if len(parts) == 1:
        # Try splitting on period followed by capital letter pattern for new author
        # e.g., "...2017;1:1-5. Smith AB, Jones CD:"
        # This is tricky because periods appear within citations
        # Only split if we see a clear author pattern after a period
        alt_parts = re.split(r'\.\s+(?=[A-Z][a-z]+ [A-Z]{1,2}[,;])', text)
        if len(alt_parts) > 1:
            # Re-add the period that was consumed by the split
            parts = [p.strip().rstrip('.') + '.' for p in alt_parts if p.strip()]

    return parts


def normalize_ref(ref_text):
    """Normalize a reference for fuzzy matching.
    Lowercase, remove extra whitespace, strip punctuation."""
    if not ref_text:
        return ""
    s = ref_text.lower()
    s = re.sub(r'\s+', ' ', s)
    s = re.sub(r'[^\w\s]', '', s)
    return s.strip()


def extract_ref_key(ref_text):
    """Extract author-year key from reference for quick matching.
    Returns (first_author_surname, year) or None."""
    if not ref_text:
        return None

    # Extract year
    year_match = re.search(r'\b(19\d{2}|20[0-2]\d)\b', ref_text)
    year = year_match.group(1) if year_match else None

    # Extract first author surname
    # Patterns: "Smith AB," or "Smith AB:" or just "Smith,"
    author_match = re.match(r'^([A-Z][a-z]+(?:[-\'][A-Z][a-z]+)?)\s+', ref_text)
    if not author_match:
        # Try org-style: "CDC:" or "USPSTF:"
        author_match = re.match(r'^([A-Z]{2,})', ref_text)

    author = author_match.group(1) if author_match else None

    if author and year:
        return (author.lower(), year)
    return None


def fuzzy_match_ref(new_ref, existing_refs, threshold=FUZZY_MATCH_THRESHOLD):
    """Find the best matching existing reference for a new reference.
    Returns (clean_ref, score) or (None, 0)."""
    new_norm = normalize_ref(new_ref)
    new_key = extract_ref_key(new_ref)

    best_match = None
    best_score = 0

    for existing_ref in existing_refs:
        # Quick filter: if we have author-year keys, check those first
        existing_key = extract_ref_key(existing_ref)
        if new_key and existing_key:
            if new_key != existing_key:
                continue  # Different author/year, skip expensive comparison

        # Full fuzzy comparison
        existing_norm = normalize_ref(existing_ref)
        score = SequenceMatcher(None, new_norm, existing_norm).ratio()

        if score > best_score:
            best_score = score
            best_match = existing_ref

    if best_score >= threshold:
        return (best_match, best_score)
    return (None, best_score)


# ── Author/Year Parsing (same as rebuild_ite_db_v2.py) ──────────────────────

def parse_authors_year(clean_ref):
    result = {"author1": None, "author2": None, "year": None}
    year_m = re.search(r'\b(199\d|20[0-2]\d)\b', clean_ref)
    if year_m:
        result["year"] = year_m.group(1)
    colon = clean_ref.find(":")
    if colon == -1:
        parts = clean_ref.split()
        if parts:
            result["author1"] = parts[0].rstrip(",")
        return result
    author_block = clean_ref[:colon].strip()
    if re.match(r'^[A-Z]{2,}', author_block) and "," not in author_block:
        result["author1"] = author_block
        return result
    parts = [p.strip() for p in author_block.split(",")]
    if parts:
        result["author1"] = parts[0].split()[0] if parts[0].split() else None
    if len(parts) >= 2:
        result["author2"] = parts[1].split()[0] if parts[1].split() else None
    return result


def build_canonical_filename(author1, author2, year):
    def sanitize(s):
        if not s:
            return None
        s = re.sub(r"['\u2019\u2018]", "", s)
        s = re.sub(r"[^A-Za-z0-9]", "_", s)
        s = re.sub(r"_+", "_", s).strip("_")
        return s[:30] if s else None
    a1 = sanitize(author1) or "Unknown"
    a2 = sanitize(author2)
    yr = str(year) if year else "0000"
    if a2:
        return f"{a1}_{a2}_{yr}"
    return f"{a1}_{yr}"


def parse_title(clean_ref):
    colon = clean_ref.find(":")
    if colon == -1:
        return clean_ref[:80].strip()
    after_colon = clean_ref[colon + 1:].strip()
    dot = after_colon.find(".")
    if dot == -1:
        return after_colon[:120].strip()
    return after_colon[:dot].strip()


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Integrate 2018-2019 ITE data into the DB")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--skip-merge", action="store_true", help="Skip JSON merge step")
    parser.add_argument("--enriched", default=str(ENRICHED_JSON), help="Path to enriched JSON")
    args = parser.parse_args()

    log("=" * 60)
    log("ITE 2018-2019 Integration Pipeline")
    log(f"  dry_run: {args.dry_run}")
    log(f"  enriched: {args.enriched}")
    log("=" * 60)

    # ── Load enriched data ──────────────────────────────────────────────────
    log("\n[STEP 1] Loading enriched 2018-2019 data...")
    with open(args.enriched, encoding="utf-8") as f:
        enriched = json.load(f)
    log(f"  Loaded {len(enriched)} enriched questions")

    # Validate enrichment completeness
    unenriched = [r for r in enriched if not r.get("body_system")]
    if unenriched:
        err(f"  {len(unenriched)} questions still unenriched! Run enrich_ite_questions.py first.")
        sys.exit(1)
    log(f"  All {len(enriched)} questions have body_system classifications")

    # ── Step 2: Merge into ite_questions_clean.json ─────────────────────────
    if not args.skip_merge:
        log(f"\n[STEP 2] Merging into {MASTER_JSON.name}...")

        with open(MASTER_JSON, encoding="utf-8") as f:
            master = json.load(f)
        log(f"  Existing master: {len(master)} questions")

        # Check for duplicate years
        existing_years = set(r["exam_year"] for r in master)
        new_years = set(r["exam_year"] for r in enriched)
        overlap = existing_years & new_years
        if overlap:
            err(f"  Year overlap detected: {overlap}. Aborting to prevent duplicates.")
            sys.exit(1)

        # Convert enriched records to master JSON format (strip extra fields)
        master_format_fields = [
            "question_id", "exam_year", "body_system", "subcategory",
            "blueprint", "format", "question_text", "choices",
            "correct_letter", "correct_text", "explanation", "reference",
            "needs_review"
        ]

        new_records = []
        for r in enriched:
            record = {k: r.get(k, "") for k in master_format_fields}
            # Also include icd10_codes as a bonus field (won't break existing scripts)
            record["icd10_codes"] = r.get("icd10_codes", [])
            new_records.append(record)

        # Sort all records: 2018, 2019, then existing 2020-2025
        combined = new_records + master
        combined.sort(key=lambda r: (r["exam_year"], r.get("question_id", "")))

        if not args.dry_run:
            # Backup existing
            shutil.copy2(MASTER_JSON, MASTER_JSON_BACKUP)
            log(f"  Backed up master to {MASTER_JSON_BACKUP.name}")

            with open(MASTER_JSON, 'w', encoding="utf-8") as f:
                json.dump(combined, f, indent=2, ensure_ascii=False)
            log(f"  Merged master: {len(combined)} questions ({len(new_records)} new)")
        else:
            log(f"  [DRY RUN] Would merge {len(new_records)} records → {len(combined)} total")

        log(f"  Year distribution:")
        for yr in sorted(set(r["exam_year"] for r in combined)):
            count = sum(1 for r in combined if r["exam_year"] == yr)
            log(f"    {yr}: {count} questions")
    else:
        log("\n[STEP 2] Skipped (--skip-merge)")

    # ── Step 3: Connect to DB and load existing articles ────────────────────
    log(f"\n[STEP 3] Connecting to DB: {DB_PATH.name}...")
    if not DB_PATH.exists():
        err(f"  DB not found: {DB_PATH}")
        sys.exit(1)

    if not args.dry_run:
        shutil.copy2(DB_PATH, DB_BACKUP)
        log(f"  Backed up DB to {DB_BACKUP.name}")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Load existing articles for reference matching
    c.execute("SELECT clean_ref, article_id FROM articles ORDER BY clean_ref")
    existing_articles = {row["clean_ref"]: row["article_id"] for row in c.fetchall()}
    log(f"  Loaded {len(existing_articles)} existing articles")

    # Find next article_id
    c.execute("SELECT article_id FROM articles ORDER BY article_id DESC LIMIT 1")
    last_art = c.fetchone()
    if last_art:
        last_num = int(re.search(r'(\d+)', last_art["article_id"]).group(1))
    else:
        last_num = 0
    next_art_num = last_num + 1
    log(f"  Next article_id: ART-{next_art_num:04d}")

    # ── Step 4: Parse references and match/create articles ──────────────────
    log(f"\n[STEP 4] Parsing references from 2018-2019 questions...")
    existing_refs = list(existing_articles.keys())

    new_articles = []       # New article records to insert
    new_pairs = []          # New question_ref_pairs to insert
    new_icd10_entries = []  # New article_icd10 entries

    match_stats = {"exact": 0, "fuzzy": 0, "new": 0, "no_ref": 0}
    ref_to_article_id = dict(existing_articles)  # clean_ref → article_id (will grow)

    for q in enriched:
        qid = q["qid"]
        exam_year = q["exam_year"]
        ref_text = q.get("reference", "")

        if not ref_text:
            match_stats["no_ref"] += 1
            continue

        # Parse individual references from the reference field
        individual_refs = parse_references_from_explanation(ref_text)

        for ref_idx, single_ref in enumerate(individual_refs):
            single_ref = single_ref.strip()
            if len(single_ref) < 10:
                continue  # Too short to be a real reference

            # Try exact match first
            if single_ref in ref_to_article_id:
                match_stats["exact"] += 1
                art_id = ref_to_article_id[single_ref]
                new_pairs.append({
                    "qid": qid,
                    "clean_ref": single_ref,
                    "ref_raw": single_ref,
                    "tier": None,
                    "match_score": 1.0,
                    "ref_index": ref_idx + 1,
                    "match_status": "matched",
                    "exam_year": exam_year,
                })
                continue

            # Try fuzzy match
            best_ref, score = fuzzy_match_ref(single_ref, existing_refs)
            if best_ref:
                match_stats["fuzzy"] += 1
                art_id = ref_to_article_id[best_ref]
                new_pairs.append({
                    "qid": qid,
                    "clean_ref": best_ref,
                    "ref_raw": single_ref,
                    "tier": None,
                    "match_score": round(score, 3),
                    "ref_index": ref_idx + 1,
                    "match_status": "fuzzy",
                    "exam_year": exam_year,
                })
                continue

            # New article — create it
            match_stats["new"] += 1
            art_id = f"ART-{next_art_num:04d}"
            next_art_num += 1

            prs = parse_authors_year(single_ref)
            a1, a2, yr = prs["author1"], prs["author2"], prs["year"]
            canon = build_canonical_filename(a1, a2, yr)

            new_articles.append({
                "clean_ref": single_ref,
                "article_id": art_id,
                "author1": a1,
                "author2": a2,
                "year": yr,
                "title": parse_title(single_ref),
                "source_type": None,
                "categories": None,
                "blueprint_cats": None,
                "tier": None,
                "auto_assigned": None,
                "citation_count": 1,
                "unique_years": 1,
                "exam_years": json.dumps([exam_year]),
                "qid_list": json.dumps([qid]),
                "canonical_filename": canon,
                "codon_filename": f"{canon}#@#{art_id}@#@.pdf",
                "citation_display": single_ref[:180] + ("..." if len(single_ref) > 180 else ""),
                "extraction_status": "pending",
            })

            # Add to lookup so subsequent questions can match this ref
            ref_to_article_id[single_ref] = art_id
            existing_refs.append(single_ref)

            new_pairs.append({
                "qid": qid,
                "clean_ref": single_ref,
                "ref_raw": single_ref,
                "tier": None,
                "match_score": 1.0,
                "ref_index": ref_idx + 1,
                "match_status": "new",
                "exam_year": exam_year,
            })

    log(f"  Reference matching results:")
    log(f"    Exact matches:   {match_stats['exact']}")
    log(f"    Fuzzy matches:   {match_stats['fuzzy']}")
    log(f"    New articles:    {match_stats['new']}")
    log(f"    No reference:    {match_stats['no_ref']}")
    log(f"  New articles to create: {len(new_articles)}")
    log(f"  New pairs to create:    {len(new_pairs)}")

    # ── Step 5: Build ICD-10 entries from enrichment ────────────────────────
    log(f"\n[STEP 5] Building ICD-10 entries from enrichment data...")

    # Map: for each question's ICD-10 codes, link them to the articles cited by that question
    # This creates article_icd10 entries (article-level, not question-level)
    qid_to_article_ids = defaultdict(set)
    for pair in new_pairs:
        art_id = ref_to_article_id.get(pair["clean_ref"])
        if art_id:
            qid_to_article_ids[pair["qid"]].add(art_id)

    seen_icd10_pairs = set()  # (article_id, icd10_code) to avoid duplicates
    # Load existing article_icd10 to avoid duplicates
    try:
        c.execute("SELECT article_id, icd10_code FROM article_icd10")
        for row in c.fetchall():
            seen_icd10_pairs.add((row["article_id"], row["icd10_code"]))
    except sqlite3.OperationalError:
        pass  # Table might not exist yet

    for q in enriched:
        icd10_codes = q.get("icd10_codes", [])
        if not icd10_codes:
            continue

        # Get all articles linked to this question
        article_ids = qid_to_article_ids.get(q["qid"], set())

        for code_entry in icd10_codes:
            code = code_entry.get("code", "")
            desc = code_entry.get("desc", "")
            if not code:
                continue

            for art_id in article_ids:
                key = (art_id, code)
                if key not in seen_icd10_pairs:
                    seen_icd10_pairs.add(key)
                    new_icd10_entries.append({
                        "article_id": art_id,
                        "icd10_code": code,
                        "icd10_desc": desc,
                        "relevance": "primary",
                    })

    log(f"  New article_icd10 entries: {len(new_icd10_entries)}")

    # ── Step 6: Insert new questions into DB ────────────────────────────────
    log(f"\n[STEP 6] Inserting new questions into DB...")

    new_question_rows = []
    for q in enriched:
        new_question_rows.append({
            "qid": q["qid"],
            "exam_year": q["exam_year"],
            "body_system": q.get("body_system"),
            "subcategory": q.get("subcategory"),
            "blueprint": q.get("blueprint", ""),
            "question_text": q.get("question_text"),
            "choices": json.dumps(q.get("choices", [])),
            "correct_letter": q.get("correct_letter"),
            "correct_text": q.get("correct_text"),
            "explanation": q.get("explanation"),
            "reference": q.get("reference"),
            "stem_keywords": None,
            "explanation_keywords": None,
            "all_keywords": None,
            "concept_tags": None,
        })

    if not args.dry_run:
        # Insert new articles
        if new_articles:
            c.executemany("""
                INSERT OR IGNORE INTO articles (clean_ref, article_id, author1, author2, year, title,
                    source_type, categories, blueprint_cats, tier, auto_assigned,
                    citation_count, unique_years, exam_years, qid_list,
                    canonical_filename, codon_filename, citation_display, extraction_status)
                VALUES (:clean_ref, :article_id, :author1, :author2, :year, :title,
                    :source_type, :categories, :blueprint_cats, :tier, :auto_assigned,
                    :citation_count, :unique_years, :exam_years, :qid_list,
                    :canonical_filename, :codon_filename, :citation_display, :extraction_status)
            """, new_articles)
            conn.commit()
            log(f"  Inserted {len(new_articles)} new articles")

        # Insert new questions
        c.executemany("""
            INSERT OR IGNORE INTO questions (qid, exam_year, body_system, subcategory, blueprint,
                question_text, choices, correct_letter, correct_text, explanation,
                reference, stem_keywords, explanation_keywords, all_keywords, concept_tags)
            VALUES (:qid, :exam_year, :body_system, :subcategory, :blueprint,
                :question_text, :choices, :correct_letter, :correct_text, :explanation,
                :reference, :stem_keywords, :explanation_keywords, :all_keywords, :concept_tags)
        """, new_question_rows)
        conn.commit()
        log(f"  Inserted {len(new_question_rows)} new questions")

        # Insert new pairs
        if new_pairs:
            c.executemany("""
                INSERT INTO question_ref_pairs (qid, clean_ref, ref_raw, tier,
                    match_score, ref_index, match_status, exam_year)
                VALUES (:qid, :clean_ref, :ref_raw, :tier,
                    :match_score, :ref_index, :match_status, :exam_year)
            """, new_pairs)
            conn.commit()
            log(f"  Inserted {len(new_pairs)} new question_ref_pairs")

        # Insert ICD-10 entries
        if new_icd10_entries:
            c.executemany("""
                INSERT OR IGNORE INTO article_icd10 (article_id, icd10_code, icd10_desc, relevance)
                VALUES (:article_id, :icd10_code, :icd10_desc, :relevance)
            """, new_icd10_entries)
            conn.commit()
            log(f"  Inserted {len(new_icd10_entries)} new article_icd10 entries")
    else:
        log(f"  [DRY RUN] Would insert:")
        log(f"    {len(new_articles)} articles")
        log(f"    {len(new_question_rows)} questions")
        log(f"    {len(new_pairs)} question_ref_pairs")
        log(f"    {len(new_icd10_entries)} article_icd10 entries")

    # ── Step 7: Update article aggregation fields ───────────────────────────
    log(f"\n[STEP 7] Updating article aggregations (citation_count, exam_years, qid_list)...")

    if not args.dry_run:
        # Rebuild aggregations for all articles that gained new pairs
        affected_refs = set(p["clean_ref"] for p in new_pairs)
        updated = 0
        for ref in affected_refs:
            c.execute("""
                SELECT qid, exam_year FROM question_ref_pairs WHERE clean_ref = ?
            """, (ref,))
            rows = c.fetchall()
            qids = sorted(set(r["qid"] for r in rows))
            years = sorted(set(int(r["exam_year"]) for r in rows if r["exam_year"]))

            c.execute("""
                UPDATE articles
                SET citation_count = ?, unique_years = ?, exam_years = ?, qid_list = ?
                WHERE clean_ref = ?
            """, (len(qids), len(years), json.dumps(years), json.dumps(qids), ref))
            updated += 1

        conn.commit()
        log(f"  Updated aggregations for {updated} articles")
    else:
        log(f"  [DRY RUN] Would update aggregations for {len(set(p['clean_ref'] for p in new_pairs))} articles")

    # ── Step 8: Verification ────────────────────────────────────────────────
    log(f"\n[STEP 8] Verification...")

    c.execute("SELECT COUNT(*) FROM articles")
    n_art = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM questions")
    n_q = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM question_ref_pairs")
    n_p = c.fetchone()[0]

    try:
        c.execute("SELECT COUNT(*) FROM article_icd10")
        n_icd = c.fetchone()[0]
    except:
        n_icd = "N/A"

    c.execute("SELECT exam_year, COUNT(*) as cnt FROM questions GROUP BY exam_year ORDER BY exam_year")
    year_dist = {row["exam_year"]: row["cnt"] for row in c.fetchall()}

    log(f"\n  Final DB counts:")
    log(f"    Articles:           {n_art}", "articles_final", n_art)
    log(f"    Questions:          {n_q}", "questions_final", n_q)
    log(f"    Question-Ref Pairs: {n_p}", "pairs_final", n_p)
    log(f"    Article-ICD10:      {n_icd}", "icd10_final", n_icd)
    log(f"\n  Questions by year:")
    for yr, cnt in sorted(year_dist.items()):
        log(f"    {yr}: {cnt}")

    # Spot check new questions
    log(f"\n  Sample new questions:")
    c.execute("SELECT qid, body_system, subcategory, correct_letter FROM questions WHERE exam_year IN (2018, 2019) LIMIT 5")
    for row in c.fetchall():
        log(f"    {row['qid']} | {row['body_system']} / {row['subcategory']} | correct={row['correct_letter']}")

    conn.close()

    # ── Write log ───────────────────────────────────────────────────────────
    LOG["completed"] = str(datetime.now(timezone.utc))
    LOG["status"] = "success" if not LOG["errors"] else "completed_with_errors"
    LOG_DIR.mkdir(exist_ok=True)
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(LOG, f, indent=2, ensure_ascii=False)
    log(f"\nDone. Log: {LOG_PATH.name}")

    if LOG["errors"]:
        log(f"WARNING: {len(LOG['errors'])} errors — see log for details")
    if LOG["warnings"]:
        log(f"INFO: {len(LOG['warnings'])} warnings — see log for details")


if __name__ == "__main__":
    main()
