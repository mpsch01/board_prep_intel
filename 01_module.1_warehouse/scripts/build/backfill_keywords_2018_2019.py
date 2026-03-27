"""
backfill_keywords_2018_2019.py
==============================
Backfill stem_keywords, explanation_keywords, and all_keywords
for the 440 new 2018-2019 questions added during the March 24, 2026
integration session.

WHY THIS SCRIPT EXISTS:
  add_keywords.py reads from ABFM_ITE_Master_v3.csv as its source.
  The 2018-2019 questions were integrated from ite_2018_2019_enriched.json,
  not from a CSV — so add_keywords.py can't reach them. This script hits
  the DB directly, deriving keywords from the already-populated
  question_text and explanation columns.

WHAT IT DOES:
  - Queries: WHERE exam_year IN (2018, 2019) AND (all_keywords IS NULL OR all_keywords = '')
  - Extracts stem_keywords from question_text
  - Extracts explanation_keywords from explanation
  - Merges both into all_keywords
  - Writes back to questions table
  - Logs results to 00_database/logs/

COST:    $0 — purely deterministic, no API calls
RUNTIME: ~5 seconds for 440 questions

RUN:
  python scripts/backfill_keywords_2018_2019.py
  python scripts/backfill_keywords_2018_2019.py --dry-run
  python scripts/backfill_keywords_2018_2019.py --reset   # clears keywords and reruns
"""

import sqlite3
import json
import re
import argparse
from pathlib import Path
from datetime import datetime, timezone

# ── Paths (PROJECT_ROOT pattern — same as integrate_2018_2019.py) ──────────
SCRIPT_DIR   = Path(__file__).resolve().parent          # 02_module.2_processor/scripts/
PROJECT_ROOT = SCRIPT_DIR.parent.parent                  # 00_#PROJECT_OVERHAUL/
DB_PATH      = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"
LOG_DIR      = PROJECT_ROOT / "00_database" / "logs"
LOG_PATH     = LOG_DIR / f"backfill_keywords_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"

TARGET_YEARS = (2018, 2019)

# ── Clinical stopwords (identical to add_keywords.py) ──────────────────────
STOP_WORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "is", "for", "with",
    "that", "this", "was", "are", "be", "at", "by", "as", "it", "from",
    "patient", "patients", "following", "year", "years", "old", "history",
    "presents", "treatment", "diagnosis", "management", "associated",
    "increased", "decreased", "should", "would", "which", "most", "likely",
    "used", "use", "may", "also", "can", "been", "will", "not", "no",
    "have", "has", "had", "all", "more", "one", "two", "after",
    "based", "due", "other", "new", "than", "when", "who", "them"
}


# ── Keyword extraction (identical logic to add_keywords.py) ────────────────
def extract_keywords(text: str, top_n: int = 12) -> list:
    """
    Extract clinical keywords from a text block.
    Matches multi-word clinical phrases first, then fills with top-frequency words.
    """
    if not text:
        return []
    text_lower = text.lower()

    phrase_patterns = [
        r'\b[a-z]+-[a-z]+ (syndrome|disease|disorder|deficiency|failure|infection)\b',
        r'\b(first.line|second.line|first-line|second-line)\b',
        r'\b(type [12] diabetes|type [12] dm)\b',
        r'\b(blood pressure|heart rate|blood glucose|serum [a-z]+)\b',
        r'\b[a-z]+ (receptor|inhibitor|antagonist|agonist|blocker)\b',
        r'\b(risk factor|risk factors|adverse effect|side effect)\b',
    ]

    found_phrases = set()
    for pattern in phrase_patterns:
        for match in re.finditer(pattern, text_lower):
            found_phrases.add(match.group(0).strip())

    words = re.findall(r'\b[a-z]{4,}\b', text_lower)
    freq = {}
    for w in words:
        if w not in STOP_WORDS:
            freq[w] = freq.get(w, 0) + 1

    top_words = sorted(freq, key=lambda w: -freq[w])[:top_n]
    combined = list(found_phrases) + [w for w in top_words if w not in found_phrases]
    return combined[:top_n]


def merge_keywords(*keyword_lists) -> str:
    """Union of multiple keyword lists, deduplicated, stopwords removed."""
    seen, merged = set(), []
    for kw_list in keyword_lists:
        items = [k.strip() for k in kw_list.split(",")] if isinstance(kw_list, str) else kw_list
        for item in items:
            norm = item.lower().strip()
            if norm and norm not in seen and norm not in STOP_WORDS:
                seen.add(norm)
                merged.append(norm)
    return ", ".join(merged)


# ── Main ────────────────────────────────────────────────────────────────────
def run(dry_run=False, reset=False):
    if not DB_PATH.exists():
        print(f"❌  DB not found: {DB_PATH}")
        return

    print("=" * 60)
    print(f"backfill_keywords_2018_2019.py")
    print(f"  DB:      {DB_PATH}")
    print(f"  Mode:    {'DRY RUN' if dry_run else 'LIVE'}")
    print(f"  Years:   {TARGET_YEARS}")
    print("=" * 60)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Ensure columns exist (idempotent)
    c.execute("PRAGMA table_info(questions)")
    existing_cols = {r[1] for r in c.fetchall()}
    for col in ("stem_keywords", "explanation_keywords", "all_keywords"):
        if col not in existing_cols:
            conn.execute(f"ALTER TABLE questions ADD COLUMN {col} TEXT")
            print(f"  + Added column: {col}")
    conn.commit()

    # Optionally reset target records
    if reset and not dry_run:
        c.execute(
            "UPDATE questions SET stem_keywords=NULL, explanation_keywords=NULL, all_keywords=NULL "
            "WHERE exam_year IN (?,?)",
            TARGET_YEARS
        )
        conn.commit()
        print(f"  Reset keyword columns for {c.rowcount} rows")

    # Load target records
    placeholders = ",".join("?" * len(TARGET_YEARS))
    c.execute(f"""
        SELECT qid, exam_year, question_text, explanation
        FROM questions
        WHERE exam_year IN ({placeholders})
          AND (all_keywords IS NULL OR all_keywords = '')
        ORDER BY exam_year, qid
    """, TARGET_YEARS)

    pending = [dict(r) for r in c.fetchall()]
    print(f"\n  Pending (missing keywords): {len(pending)}")

    if not pending:
        print("  ✅ All 2018-2019 records already have keywords. Use --reset to rerun.")
        conn.close()
        return

    # Build updates
    updates = []
    for row in pending:
        stem_kws  = extract_keywords(row["question_text"] or "")
        expl_kws  = extract_keywords(row["explanation"] or "")
        all_kws   = merge_keywords(stem_kws, expl_kws)

        updates.append({
            "qid":                  row["qid"],
            "exam_year":            row["exam_year"],
            "stem_keywords":        ", ".join(stem_kws),
            "explanation_keywords": ", ".join(expl_kws),
            "all_keywords":         all_kws,
        })

    if dry_run:
        print("\n  ── DRY RUN — first 5 updates ──────────────────────")
        for u in updates[:5]:
            print(f"\n  QID: {u['qid']} ({u['exam_year']})")
            print(f"    stem_keywords:        {u['stem_keywords'][:80]}")
            print(f"    explanation_keywords: {u['explanation_keywords'][:80]}")
            print(f"    all_keywords:         {u['all_keywords'][:100]}")
        print(f"\n  ⚠️  DRY RUN — {len(updates)} updates prepared, nothing written")
        conn.close()
        return

    # Write to DB
    written = 0
    for u in updates:
        r = conn.execute("""
            UPDATE questions
            SET stem_keywords = ?, explanation_keywords = ?, all_keywords = ?
            WHERE qid = ?
        """, (u["stem_keywords"], u["explanation_keywords"], u["all_keywords"], u["qid"]))
        if r.rowcount:
            written += 1

    conn.commit()

    # QC counts
    c.execute(
        f"SELECT COUNT(*) FROM questions WHERE exam_year IN ({placeholders}) AND all_keywords IS NOT NULL AND all_keywords != ''",
        TARGET_YEARS
    )
    filled_2018_2019 = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM questions WHERE all_keywords IS NOT NULL AND all_keywords != ''")
    filled_total = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM questions")
    total = c.fetchone()[0]

    conn.close()

    print(f"\n  Written:          {written}")
    print(f"  2018-2019 filled: {filled_2018_2019}/440")
    print(f"  All years filled: {filled_total}/{total} ({round(filled_total/total*100, 1)}%)")

    # Log
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_data = {
        "script":             "backfill_keywords_2018_2019.py",
        "run_at":             datetime.now(timezone.utc).isoformat(),
        "target_years":       list(TARGET_YEARS),
        "rows_processed":     len(updates),
        "rows_written":       written,
        "filled_2018_2019":   filled_2018_2019,
        "filled_total":       f"{filled_total}/{total}",
    }
    with open(LOG_PATH, "w") as f:
        json.dump(log_data, f, indent=2)

    print(f"\n✅  Done. Log: {LOG_PATH.name}")


# ── Entry ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill keyword columns for 2018-2019 ITE questions")
    parser.add_argument("--dry-run", action="store_true", help="Show first 5 results, write nothing")
    parser.add_argument("--reset",   action="store_true", help="Clear existing keywords before rerun")
    args = parser.parse_args()
    run(dry_run=args.dry_run, reset=args.reset)
