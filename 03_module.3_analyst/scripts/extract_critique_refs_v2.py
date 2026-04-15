"""
extract_critique_refs_v2.py
============================
Extracts per-question citations from ITE critique PDFs using Claude's native
PDF reading via the Anthropic Files API. Replaces the pdfplumber-based
extract_ite_critique_refs.py for future years.

Advantages over v1 (pdfplumber):
  - Format-agnostic: works regardless of how ABFM structures the PDF year to year
  - No bounding-box math or format-specific parsers
  - Handles multi-column, wrapped text, and non-standard layouts automatically
  - Upload once → reuse across multiple extraction tasks (Files API)

Output: same staging JSON format as extract_ite_critique_refs.py so downstream
pipeline (citation QC, article matching) works unchanged.

Usage:
    # Extract citations for a specific year (uploads PDF if not registered)
    python extract_critique_refs_v2.py --year 2025

    # Extract all years
    python extract_critique_refs_v2.py --all

    # Use already-uploaded file (skip upload check)
    python extract_critique_refs_v2.py --year 2025 --file-id file_01abc123

    # Dry run — show prompt without calling API
    python extract_critique_refs_v2.py --year 2025 --dry-run

Output files:
    02_module.2_processor/outputs/YYYY_critique_refs_staging.json

Environment:
    ANTHROPIC_API_KEY: required
"""

import os
import sys
import json
import re
import argparse
import sqlite3
from pathlib import Path
from datetime import datetime
from difflib import SequenceMatcher

# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH      = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"
STAGING_DIR  = PROJECT_ROOT / "02_module.2_processor" / "outputs"

MODEL        = "claude-opus-4-6"   # native PDF reading; Opus handles layout best
MAX_TOKENS   = 8192                # critique books are long; need headroom

ITE_YEARS    = list(range(2018, 2026))
FUZZY_THRESHOLD = 0.80

sys.path.insert(0, str(SCRIPT_DIR))
from critique_pdf_registry import get_file_id, upload_pdf

EXTRACTION_PROMPT = """\
This is an ABFM Family Medicine In-Training Examination Critique Book.

For EVERY question (labeled "Item N" or "Question N"), extract:
1. The item/question number (integer)
2. All bibliographic references listed for that item

References appear after the explanation text, usually under a heading like
"Reference", "References", or inline starting with "Ref:". Each reference
is a full citation (author, title, journal, year, volume, pages).

Return a JSON array — one object per reference (not per question):
[
  {
    "item_num": 1,
    "ref_index": 1,
    "citation": "Levy M, Prentice M, Wass J. Diabetes insipidus. BMJ. 2019;364:l321."
  },
  {
    "item_num": 1,
    "ref_index": 2,
    "citation": "..."
  },
  {
    "item_num": 5,
    "ref_index": 1,
    "citation": "..."
  },
  ...
]

Rules:
- Include ALL items that have references. Skip items with no references.
- If an item has multiple references, create one object per reference with
  ref_index incrementing from 1.
- Copy citations exactly as written — do not paraphrase or abbreviate.
- item_num must be an integer (e.g. 1, not "Item 1").
- Return ONLY the JSON array. No explanation, no markdown fences.
"""


# ── DB helpers ─────────────────────────────────────────────────────────────────

def load_article_index(db_path: Path) -> dict:
    """
    Load articles from DB for citation matching.
    Returns {prefix: article_id} where prefix = first 80 chars of clean_ref.
    """
    if not db_path.exists():
        print(f"  WARNING: DB not found at {db_path} — skipping article matching")
        return {}
    conn = sqlite3.connect(str(db_path))
    rows = conn.execute(
        "SELECT article_id, clean_ref FROM articles WHERE clean_ref IS NOT NULL"
    ).fetchall()
    conn.close()
    return {(r[1] or "")[:80].lower().strip(): r[0] for r in rows}


def match_citation(citation: str, article_index: dict, threshold: float = FUZZY_THRESHOLD):
    """
    Match a citation string against the article index.
    Returns (match_status, article_id, match_score).
    """
    if not article_index:
        return "unmatched", None, 0.0

    prefix = citation[:80].lower().strip()

    # Exact prefix match first
    if prefix in article_index:
        return "matched", article_index[prefix], 1.0

    # Fuzzy match
    best_score, best_id = 0.0, None
    for ref_prefix, art_id in article_index.items():
        score = SequenceMatcher(None, prefix, ref_prefix).ratio()
        if score > best_score:
            best_score, best_id = score, art_id

    if best_score >= threshold:
        return "fuzzy_matched", best_id, best_score

    return "unmatched", None, best_score


# ── Extraction ─────────────────────────────────────────────────────────────────

def extract_for_year(client, year: int, file_id: str, article_index: dict) -> list[dict]:
    """
    Call Claude with the critique PDF to extract per-question citations.
    Returns a list of staging records matching the v1 format.
    """
    print(f"  Calling Claude ({MODEL}) with file_id={file_id}...")

    response = client.beta.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "document",
                    "source": {
                        "type": "file",
                        "file_id": file_id,
                    },
                },
                {
                    "type": "text",
                    "text": EXTRACTION_PROMPT,
                },
            ],
        }],
        betas=["files-api-2025-04-14"],
    )

    raw_text = response.content[0].text.strip()

    # Strip markdown fences if present
    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
    raw_text = re.sub(r"\s*```$", "", raw_text)

    try:
        extracted = json.loads(raw_text)
    except json.JSONDecodeError as e:
        print(f"  ERROR: Could not parse Claude response as JSON: {e}")
        print(f"  Raw (first 500 chars): {raw_text[:500]}")
        return []

    print(f"  Extracted {len(extracted)} citation records from {year} critique")

    # Build staging records
    staging = []
    for rec in extracted:
        item_num  = rec.get("item_num")
        ref_index = rec.get("ref_index", 1)
        citation  = (rec.get("citation") or "").strip()

        if not item_num or not citation:
            continue

        # Format QID
        qid = f"QID-{year}-{int(item_num):04d}"

        # Match against article DB
        match_status, article_id, match_score = match_citation(citation, article_index)

        staging.append({
            "qid":          qid,
            "exam_year":    year,
            "item_num":     int(item_num),
            "ref_index":    ref_index,
            "clean_ref":    citation,
            "match_status": match_status,
            "_article_id":  article_id,
            "match_score":  round(match_score, 4),
            "source":       "files_api_v2",
        })

    return staging


def write_staging(year: int, records: list[dict]) -> Path:
    """Write staging JSON and return path."""
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    out_path = STAGING_DIR / f"{year}_critique_refs_staging.json"

    # Summary stats
    matched       = sum(1 for r in records if r["match_status"] == "matched")
    fuzzy_matched = sum(1 for r in records if r["match_status"] == "fuzzy_matched")
    unmatched     = sum(1 for r in records if r["match_status"] == "unmatched")
    questions     = len(set(r["qid"] for r in records))

    print(f"  Questions with refs: {questions}")
    print(f"  Total citations:     {len(records)}")
    print(f"  Matched:             {matched}")
    print(f"  Fuzzy matched:       {fuzzy_matched}")
    print(f"  Unmatched:           {unmatched}")

    out_path.write_text(json.dumps(records, indent=2), encoding="utf-8")
    print(f"  Written: {out_path}")
    return out_path


# ── Main ───────────────────────────────────────────────────────────────────────

def process_year(client, year: int, file_id: str | None, article_index: dict,
                 dry_run: bool = False) -> bool:
    """Process one year. Returns True on success."""
    print(f"\n=== {year} ===")

    # Resolve file_id
    if not file_id:
        file_id = get_file_id(year, "critique")

    if not file_id:
        print(f"  No file_id found — uploading {year}_critique.pdf...")
        file_id = upload_pdf(client, year, "critique")
        if not file_id:
            print(f"  FAILED: could not upload {year} critique PDF")
            return False

    print(f"  file_id: {file_id}")

    if dry_run:
        print("  [DRY RUN] Would call Claude with this file_id. Skipping.")
        return True

    records = extract_for_year(client, year, file_id, article_index)
    if not records:
        print(f"  WARNING: no records extracted for {year}")
        return False

    write_staging(year, records)
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Extract ITE critique citations via Claude Files API (v2)"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--year",  type=int, choices=ITE_YEARS,
                       help="Process a single exam year")
    group.add_argument("--all",   action="store_true",
                       help="Process all years 2018–2025")

    parser.add_argument("--file-id", type=str, default=None,
                        help="Use a specific Anthropic file_id (skips registry lookup)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would happen without calling the API")
    parser.add_argument("--force-upload", action="store_true",
                        help="Re-upload PDF even if already registered")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    from anthropic import Anthropic
    client = Anthropic(api_key=api_key)

    # Load article index for citation matching
    print("Loading article index from DB...")
    article_index = load_article_index(DB_PATH)
    print(f"  {len(article_index)} articles loaded for matching")

    years = ITE_YEARS if args.all else [args.year]
    results = {}

    for year in years:
        file_id = args.file_id if (args.year and args.file_id) else None
        if args.force_upload:
            from critique_pdf_registry import upload_pdf as do_upload
            file_id = do_upload(client, year, "critique", force=True)
        success = process_year(client, year, file_id, article_index, dry_run=args.dry_run)
        results[year] = "OK" if success else "FAILED"

    print(f"\n{'='*40}")
    print("Summary:")
    for year, status in sorted(results.items()):
        print(f"  {year}: {status}")


if __name__ == "__main__":
    main()
