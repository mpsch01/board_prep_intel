"""
rematch_unmatched.py — Fuzzy Re-Matcher for Unmatched ITE Pairs
===============================================================
Phase 2 | ITE Intelligence Pipeline

The 2024/2025 question_ref_pairs rows have clean_ref = NULL because
RefMatched was blank in the source CSV. However, 470+ of those refs
DO exist in the articles table under slightly different citation formatting.

2025-specific artifact: refs contain " . " (space-dot-space) instead of "."
e.g. "Am Fam Physician . 2023;108(3):278-287" — normalizer strips this.

This script:
  1. Loads all unmatched pairs (clean_ref IS NULL) from the DB
  2. Builds a candidate list from the articles table
  3. Fuzzy-matches each unmatched ref_raw to the candidate list
  4. Updates clean_ref in question_ref_pairs where score >= THRESHOLD
  5. Writes a detailed log + rematch report

Run:
  python scripts/rematch_unmatched.py
  python scripts/rematch_unmatched.py --threshold 75     (stricter)
  python scripts/rematch_unmatched.py --dry-run          (preview only)

Default threshold: 72/100
"""

import sqlite3
import json
import re
import argparse
from pathlib import Path
from datetime import datetime

try:
    from rapidfuzz import fuzz, process
except ImportError:
    raise ImportError("Run: pip install rapidfuzz")

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).resolve().parent.parent
DB_PATH     = BASE_DIR / "00_database" / "db" / "ite_intelligence.db"
LOG_PATH    = BASE_DIR / "logs" / "rematch_log.json"
REPORT_PATH = BASE_DIR / "logs" / "rematch_report.txt"

DEFAULT_THRESHOLD = 72


# ── Citation Normalizer ────────────────────────────────────────────────────
def normalize_citation(text: str) -> str:
    """
    Normalize a citation string for fuzzy comparison.
    Handles known formatting artifacts across all exam years:
      - 2025 source artifact: "Am Fam Physician . 2023" (space before period)
      - En-dashes, soft hyphens in page ranges
      - Inconsistent semicolon/colon spacing
      - Trailing whitespace in truncated refs
    """
    if not text:
        return ""
    t = text.strip()

    # ── 2025 artifact: space before period (e.g. "Physician . 2023") ──────
    # Must do BEFORE lowercasing to avoid mis-matching ". " sentence ends
    t = re.sub(r'\s+\.\s+', '. ', t)       # " . " → ". "
    t = re.sub(r'\s+\.$', '.', t)           # trailing " ." → "."
    t = re.sub(r'\s+\.\s*$', '', t)         # trailing " . " → strip

    t = t.lower()

    # Standardize author list separators
    t = re.sub(r'\s*;\s*', ', ', t)

    # Collapse all whitespace
    t = re.sub(r'\s+', ' ', t)

    # Remove trailing periods
    t = t.rstrip('.')

    # Normalize volume/page punctuation
    t = re.sub(r'\s*:\s*', ':', t)
    t = re.sub(r'\s*;\s*', ';', t)

    # Unicode normalization — hyphens and dashes
    t = t.replace('\u00ad', '-')   # soft hyphen
    t = t.replace('\u2013', '-')   # en-dash
    t = t.replace('\u2014', '-')   # em-dash

    # Remove page range hyphens with spaces (e.g. "341- 349" → "341-349")
    t = re.sub(r'(\d+)-\s+(\d+)', r'\1-\2', t)

    return t.strip()


# ── Core Matching ──────────────────────────────────────────────────────────
def find_best_match(
    ref_raw: str,
    candidates: list,
    candidate_norms: list,
    threshold: int
) -> tuple:
    """
    Find best matching candidate for ref_raw.
    Uses token_set_ratio as primary scorer (most accurate for citations).
    Returns (matched_clean_ref, score) or (None, best_score_seen).
    """
    norm_raw = normalize_citation(ref_raw)
    if not norm_raw or len(norm_raw) < 15:
        return None, 0

    best_ref   = None
    best_score = 0

    # Stage 1: Fast pre-filter with token_sort_ratio
    pre_result = process.extractOne(
        norm_raw,
        candidate_norms,
        scorer=fuzz.token_sort_ratio,
        score_cutoff=max(threshold - 15, 50)
    )

    contenders = set()
    if pre_result:
        contenders.add(candidate_norms.index(pre_result[0]))

    # Stage 2: partial_ratio catches truncated refs
    partial_result = process.extractOne(
        norm_raw,
        candidate_norms,
        scorer=fuzz.partial_ratio,
        score_cutoff=max(threshold - 15, 50)
    )
    if partial_result:
        contenders.add(candidate_norms.index(partial_result[0]))

    # Stage 3: token_set_ratio on contenders (most accurate)
    for idx in contenders:
        score = fuzz.token_set_ratio(norm_raw, candidate_norms[idx])
        if score > best_score:
            best_score = score
            best_ref   = candidates[idx]

    if best_score >= threshold:
        return best_ref, best_score
    return None, best_score


# ── Main ────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Fuzzy re-matcher for unmatched ITE pairs")
    parser.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD)
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview without writing to DB")
    args = parser.parse_args()

    if not DB_PATH.exists():
        print(f"❌ DB not found: {DB_PATH}")
        return

    print("=" * 60)
    print("ITE Pair Fuzzy Re-Matcher  v2")
    print(f"  Threshold: {args.threshold}/100")
    print(f"  Mode:      {'DRY RUN' if args.dry_run else 'LIVE'}")
    print("=" * 60)

    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    # Load unmatched pairs
    cur.execute("""
        SELECT p.id, p.qid, p.ref_raw, q.exam_year
        FROM question_ref_pairs p
        JOIN questions q ON p.qid = q.qid
        WHERE p.clean_ref IS NULL
          AND p.ref_raw IS NOT NULL
          AND TRIM(p.ref_raw) != ''
        ORDER BY q.exam_year, p.qid
    """)
    unmatched = cur.fetchall()
    print(f"\n  Unmatched pairs: {len(unmatched)}")

    # Count by year for reporting
    year_input = {}
    for _, _, _, yr in unmatched:
        year_input[yr] = year_input.get(yr, 0) + 1
    for yr in sorted(year_input):
        print(f"    {yr}: {year_input[yr]} unmatched pairs")

    # Load candidates
    cur.execute("""
        SELECT clean_ref FROM articles
        WHERE source_type != 'stub'
        ORDER BY citation_count DESC
    """)
    candidates     = [r[0] for r in cur.fetchall()]
    candidate_norms = [normalize_citation(c) for c in candidates]
    print(f"\n  Candidate articles: {len(candidates)}")
    print(f"  Matching...\n")

    results = []
    matched_count   = 0
    unmatched_count = 0
    year_matched    = {}

    for pair_id, qid, ref_raw, exam_year in unmatched:
        matched_ref, score = find_best_match(
            ref_raw, candidates, candidate_norms, args.threshold
        )

        status = "matched" if matched_ref else "no_match"
        if matched_ref:
            matched_count += 1
            year_matched[exam_year] = year_matched.get(exam_year, 0) + 1
            if not args.dry_run:
                conn.execute("""
                    UPDATE question_ref_pairs
                    SET clean_ref = ?, match_score = ?, match_status = 'fuzzy_matched'
                    WHERE id = ?
                """, (matched_ref, score / 100.0, pair_id))
        else:
            unmatched_count += 1

        results.append({
            "id":          pair_id,
            "qid":         qid,
            "exam_year":   exam_year,
            "ref_raw":     ref_raw[:120],
            "matched_ref": matched_ref[:120] if matched_ref else None,
            "score":       score,
            "status":      status
        })

    if not args.dry_run:
        conn.commit()

    # Post-rematch year stats
    cur.execute("""
        SELECT q.exam_year,
               COUNT(*) as total,
               SUM(CASE WHEN p.clean_ref IS NOT NULL THEN 1 ELSE 0 END) as linked,
               ROUND(100.0 * SUM(CASE WHEN p.clean_ref IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 1) as pct
        FROM question_ref_pairs p
        JOIN questions q ON p.qid = q.qid
        GROUP BY q.exam_year ORDER BY q.exam_year
    """)
    year_stats = cur.fetchall()
    conn.close()

    # Summary
    low_conf = [r for r in results if r["status"] == "matched" and r["score"] < 80]

    print("── Results ───────────────────────────────────────────")
    print(f"  Newly matched:   {matched_count}")
    print(f"  Still unmatched: {unmatched_count}")
    print(f"  Low-conf (72-79): {len(low_conf)}")
    if args.dry_run:
        print("  ⚠️  DRY RUN — no DB changes made")
        print("\n── Projected match rates (if run live) ──────────────")
        for yr in sorted(year_input):
            newly = year_matched.get(yr, 0)
            cur_linked = next((r[2] for r in year_stats if r[0] == yr), 0)
            total      = next((r[1] for r in year_stats if r[0] == yr), 0)
            projected  = cur_linked + newly
            pct        = round(100.0 * projected / total, 1) if total else 0
            print(f"  {yr}: {projected}/{total} ({pct}%)  [+{newly} new]")
    else:
        print("\n── Match rates after rematch ─────────────────────────")
        for r in year_stats:
            print(f"  {r[0]}: {r[2]}/{r[1]} ({r[3]}%)")

    # Sample matches
    matched_sample = [r for r in results if r["status"] == "matched"][:8]
    print("\n── Sample Matches ────────────────────────────────────")
    for r in matched_sample:
        print(f"  [{r['score']:.0f}] {r['qid']}")
        print(f"    RAW: {r['ref_raw'][:90]}")
        print(f"    →    {r['matched_ref'][:90]}")

    # Write outputs
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    log = {
        "run_at":        datetime.now().isoformat(),
        "threshold":     args.threshold,
        "dry_run":       args.dry_run,
        "input_count":   len(unmatched),
        "matched":       matched_count,
        "unmatched":     unmatched_count,
        "match_rate":    round(matched_count / len(unmatched) * 100, 1) if unmatched else 0,
        "year_matched_new": {str(k): v for k, v in year_matched.items()},
        "year_stats_post": {str(r[0]): {"total": r[1], "linked": r[2], "pct": r[3]} for r in year_stats},
        "low_confidence_count": len(low_conf),
    }
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2)

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(f"ITE Pair Rematch Report v2\n")
        f.write(f"Run: {datetime.now().isoformat()}  |  Threshold: {args.threshold}  |  Dry: {args.dry_run}\n")
        f.write(f"Matched: {matched_count}/{len(unmatched)}\n\n")
        f.write("=== MATCHED ===\n\n")
        for r in results:
            if r["status"] == "matched":
                flag = " ⚠️LOW" if r["score"] < 80 else ""
                f.write(f"[{r['score']:.1f}{flag}] {r['qid']} ({r['exam_year']})\n")
                f.write(f"  RAW: {r['ref_raw']}\n")
                f.write(f"  →    {r['matched_ref']}\n\n")
        f.write("\n=== STILL UNMATCHED ===\n\n")
        for r in results:
            if r["status"] == "no_match":
                f.write(f"[best={r['score']:.1f}] {r['qid']} ({r['exam_year']})\n")
                f.write(f"  {r['ref_raw']}\n\n")

    status_word = "DRY RUN complete" if args.dry_run else "✅ Done"
    print(f"\n{status_word}")
    print(f"   Log:    {LOG_PATH}")
    print(f"   Report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
