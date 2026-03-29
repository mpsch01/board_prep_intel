"""
aafp_merge_keywords.py  v1
===========================
Merges stem_keywords (aafp_questions) and explanation_keywords (aafp_explanations)
into a unified all_keywords column on aafp_questions.

Logic mirrors the ITE questions table:
  - Stem terms appear first (priority)
  - Explanation terms appended if not already present in stem set
  - Comparison is case-insensitive; stored as-is (original casing from stem)
  - Result is comma-separated string matching existing keyword format

Output:
  - all_keywords column added to aafp_questions (ALTER TABLE safe — skips if exists)
  - 1,221/1,221 rows populated on a clean run

Run:
    python aafp_merge_keywords.py             # full run
    python aafp_merge_keywords.py --dry-run   # preview first 10, no DB writes

Path pattern: SCRIPT_DIR = this file; PROJECT_ROOT = SCRIPT_DIR.parent.parent
"""

import sqlite3
import argparse
from pathlib import Path

SCRIPT_DIR  = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH     = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"


def merge_keywords(stem_kw: str | None, exp_kw: str | None) -> str:
    """
    Merge two comma-separated keyword strings.
    Stem terms first; explanation terms appended if not already present.
    Comparison is case-insensitive.
    """
    stem_terms = [t.strip() for t in stem_kw.split(",") if t.strip()] if stem_kw else []
    exp_terms  = [t.strip() for t in exp_kw.split(",")  if t.strip()] if exp_kw  else []

    seen = {t.lower() for t in stem_terms}
    merged = list(stem_terms)
    for term in exp_terms:
        if term.lower() not in seen:
            merged.append(term)
            seen.add(term.lower())

    return ", ".join(merged)


def ensure_column(conn: sqlite3.Connection) -> None:
    """Add all_keywords column to aafp_questions if it doesn't already exist."""
    existing = {row[1] for row in conn.execute("PRAGMA table_info(aafp_questions)")}
    if "all_keywords" not in existing:
        conn.execute("ALTER TABLE aafp_questions ADD COLUMN all_keywords TEXT")
        conn.commit()
        print("  [schema] all_keywords column added to aafp_questions")
    else:
        print("  [schema] all_keywords column already exists — skipping ALTER")


def run(dry_run: bool = False) -> None:
    print(f"DB: {DB_PATH}")
    if dry_run:
        print("  ** DRY RUN — no writes **")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    if not dry_run:
        ensure_column(conn)

    # Pull all questions with both keyword fields
    rows = conn.execute("""
        SELECT aq.aafp_qid, aq.stem_keywords, ae.explanation_keywords
        FROM aafp_questions aq
        LEFT JOIN aafp_explanations ae ON aq.aafp_qid = ae.aafp_qid
    """).fetchall()

    print(f"\n  Processing {len(rows)} questions...")

    updates = []
    stats = {"both": 0, "stem_only": 0, "exp_only": 0, "neither": 0}

    for row in rows:
        stem_kw = row["stem_keywords"]
        exp_kw  = row["explanation_keywords"]

        if stem_kw and exp_kw:
            stats["both"] += 1
        elif stem_kw:
            stats["stem_only"] += 1
        elif exp_kw:
            stats["exp_only"] += 1
        else:
            stats["neither"] += 1

        merged = merge_keywords(stem_kw, exp_kw)
        updates.append((merged, row["aafp_qid"]))

    # Preview in dry-run mode
    if dry_run:
        print("\n  === DRY RUN PREVIEW (first 10) ===")
        for i, (merged, qid) in enumerate(updates[:10]):
            orig_stem = rows[i]["stem_keywords"] or ""
            orig_exp  = rows[i]["explanation_keywords"] or ""
            print(f"\n  [{qid}]")
            print(f"    stem:    {orig_stem[:80]}")
            print(f"    exp:     {orig_exp[:80]}")
            print(f"    merged:  {merged[:120]}")
        print(f"\n  Would write {len(updates)} rows.")
    else:
        conn.executemany(
            "UPDATE aafp_questions SET all_keywords = ? WHERE aafp_qid = ?",
            updates
        )
        conn.commit()

        # Verify
        populated = conn.execute(
            "SELECT COUNT(*) FROM aafp_questions WHERE all_keywords IS NOT NULL AND all_keywords != ''"
        ).fetchone()[0]

        print(f"\n  ✓ all_keywords written: {populated}/{len(rows)}")

    # Coverage report
    print(f"\n  Keyword source breakdown:")
    print(f"    Both stem + explanation: {stats['both']}")
    print(f"    Stem only:               {stats['stem_only']}")
    print(f"    Explanation only:        {stats['exp_only']}")
    print(f"    Neither:                 {stats['neither']}")

    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge AAFP stem + explanation keywords into all_keywords")
    parser.add_argument("--dry-run", action="store_true", help="Preview merges without writing to DB")
    args = parser.parse_args()
    run(dry_run=args.dry_run)
