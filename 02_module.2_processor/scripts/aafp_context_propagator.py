#!/usr/bin/env python3
"""
AAFP Context Propagator
━━━━━━━━━━━━━━━━━━━━━━━
Propagates clinical context from the article library to AAFP questions
via aafp_qid_art_xref. Entirely local — no API calls.

What gets propagated (for the ~586 questions with linked articles):

  aafp_questions.body_system      ← articles.categories (majority vote)
  aafp_questions.source_type      ← articles.source_type (majority vote)
  aafp_question_icd10 table       ← article_icd10 (parallel to article_icd10)

Questions with no linked articles stay NULL until gap filling or API enrichment.

Tables created/modified:
  ALTER aafp_questions    ADD COLUMN body_system TEXT
  ALTER aafp_questions    ADD COLUMN source_type TEXT
  CREATE aafp_question_icd10 (aafp_qid, icd10_code, icd10_desc, relevance)

Run:
  python aafp_context_propagator.py              ← full propagation
  python aafp_context_propagator.py --dry-run    ← preview stats, no writes
  python aafp_context_propagator.py --stats      ← show coverage from existing DB
  python aafp_context_propagator.py --rebuild    ← drop aafp_question_icd10 + repopulate

Majority vote logic (body_system / source_type):
  A question may link to 2+ articles. Majority vote picks the most
  common non-null value. Ties broken alphabetically (deterministic).
"""

import sys
import sqlite3
from pathlib import Path
from collections import Counter

# ══════════════════════════════════════════════════════════════════════
# PATHS
# ══════════════════════════════════════════════════════════════════════
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH      = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"
# ══════════════════════════════════════════════════════════════════════

DRY_RUN = "--dry-run" in sys.argv
STATS   = "--stats"   in sys.argv
REBUILD = "--rebuild" in sys.argv

CREATE_ICD10_TABLE = """
CREATE TABLE IF NOT EXISTS aafp_question_icd10 (
    aafp_qid   TEXT NOT NULL,    -- FK → aafp_questions.aafp_qid
    icd10_code TEXT NOT NULL,    -- e.g. "I10"
    icd10_desc TEXT,             -- e.g. "Essential (primary) hypertension"
    relevance  TEXT,             -- "primary" / "secondary" (inherited from article)
    PRIMARY KEY (aafp_qid, icd10_code)
)
"""


# ─────────────────────────────────────────────────────────────────────
# SCHEMA HELPERS
# ─────────────────────────────────────────────────────────────────────
def add_column_if_missing(conn: sqlite3.Connection, table: str, column: str) -> None:
    cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} TEXT")
        print(f"  ✓ Added column: {table}.{column}")
    else:
        print(f"  · {table}.{column} already exists")


def pct(n: int, total: int) -> str:
    return f"{n / total * 100:.1f}" if total else "0"


# ─────────────────────────────────────────────────────────────────────
# STATS MODE
# ─────────────────────────────────────────────────────────────────────
def run_stats(conn: sqlite3.Connection) -> None:
    print("\n══ AAFP Context Coverage ══════════════════════════════════")
    total = conn.execute("SELECT COUNT(*) FROM aafp_questions").fetchone()[0]

    for col in ["body_system", "source_type"]:
        try:
            filled = conn.execute(
                f"SELECT COUNT(*) FROM aafp_questions WHERE {col} IS NOT NULL AND {col} != ''"
            ).fetchone()[0]
            print(f"  aafp_questions.{col:<20}  {filled}/{total}  ({pct(filled, total)}%)")
        except Exception:
            print(f"  aafp_questions.{col}  — column missing")

    try:
        icd_q = conn.execute(
            "SELECT COUNT(DISTINCT aafp_qid) FROM aafp_question_icd10"
        ).fetchone()[0]
        icd_rows = conn.execute("SELECT COUNT(*) FROM aafp_question_icd10").fetchone()[0]
        print(f"  aafp_question_icd10               {icd_q} questions  ({icd_rows} total rows)")
    except Exception:
        print(f"  aafp_question_icd10               — table missing")

    print()
    # xref coverage baseline
    xref_q = conn.execute(
        "SELECT COUNT(DISTINCT aafp_qid) FROM aafp_qid_art_xref"
    ).fetchone()[0]
    print(f"  Baseline: {xref_q} questions have linked articles in aafp_qid_art_xref")


# ─────────────────────────────────────────────────────────────────────
# PROPAGATION LOGIC
# ─────────────────────────────────────────────────────────────────────
def majority_vote(values: list[str | None]) -> str | None:
    """
    Pick most common non-null value from a list.
    Ties broken alphabetically (deterministic).
    Returns None if all values are null.
    """
    non_null = [v.strip() for v in values if v and v.strip()]
    if not non_null:
        return None
    counts = Counter(non_null)
    max_count = max(counts.values())
    candidates = sorted(k for k, v in counts.items() if v == max_count)
    return candidates[0]


def build_article_lookup(conn: sqlite3.Connection) -> dict[str, dict]:
    """
    Returns {article_id: {categories, source_type}} from articles table.
    """
    rows = conn.execute(
        "SELECT article_id, categories, source_type FROM articles WHERE article_id IS NOT NULL"
    ).fetchall()
    return {
        r[0]: {"categories": r[1], "source_type": r[2]}
        for r in rows
    }


def build_icd10_lookup(conn: sqlite3.Connection) -> dict[str, list[tuple]]:
    """
    Returns {article_id: [(icd10_code, icd10_desc, relevance), ...]} from article_icd10.
    """
    rows = conn.execute(
        "SELECT article_id, icd10_code, icd10_desc, relevance FROM article_icd10"
    ).fetchall()
    lookup: dict[str, list] = {}
    for art_id, code, desc, rel in rows:
        lookup.setdefault(art_id, []).append((code, desc, rel))
    return lookup


def load_xref(conn: sqlite3.Connection) -> dict[str, list[str]]:
    """
    Returns {aafp_qid: [article_id, ...]} from aafp_qid_art_xref.
    """
    rows = conn.execute(
        "SELECT aafp_qid, article_id FROM aafp_qid_art_xref"
    ).fetchall()
    xref: dict[str, list[str]] = {}
    for qid, art_id in rows:
        xref.setdefault(qid, []).append(art_id)
    return xref


# ─────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────
def main() -> None:
    if not DB_PATH.exists():
        print(f"ERROR: DB not found:\n  {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)

    if STATS:
        run_stats(conn)
        conn.close()
        return

    # ── Schema setup ─────────────────────────────────────────────────
    print("\nSchema check...")
    add_column_if_missing(conn, "aafp_questions", "body_system")
    add_column_if_missing(conn, "aafp_questions", "source_type")

    if REBUILD:
        print("\n⚠  --rebuild: dropping aafp_question_icd10...")
        conn.execute("DROP TABLE IF EXISTS aafp_question_icd10")
        conn.commit()

    conn.execute(CREATE_ICD10_TABLE)
    conn.commit()
    print("  · aafp_question_icd10 table ready")

    # ── Build lookups ─────────────────────────────────────────────────
    print("\nBuilding lookups...")
    art_lookup   = build_article_lookup(conn)
    icd10_lookup = build_icd10_lookup(conn)
    xref         = load_xref(conn)

    print(f"  {len(art_lookup)} articles indexed")
    print(f"  {len(icd10_lookup)} articles have ICD-10 codes")
    print(f"  {len(xref)} AAFP questions have linked articles")

    # ── Compute propagations ──────────────────────────────────────────
    body_system_updates: list[tuple[str, str]] = []   # (body_system, aafp_qid)
    source_type_updates: list[tuple[str, str]] = []   # (source_type, aafp_qid)
    icd10_rows: list[tuple[str, str, str, str]] = []  # (aafp_qid, code, desc, relevance)

    stats = {
        "body_system_set":   0,
        "source_type_set":   0,
        "icd10_questions":   0,
        "icd10_total_rows":  0,
        "no_linked_article": 0,
    }

    # Load all aafp_qids
    all_qids = [r[0] for r in conn.execute("SELECT aafp_qid FROM aafp_questions").fetchall()]

    for qid in all_qids:
        linked_articles = xref.get(qid, [])

        if not linked_articles:
            stats["no_linked_article"] += 1
            continue

        # body_system: majority vote across linked articles' categories
        cats = [art_lookup.get(a, {}).get("categories") for a in linked_articles]
        body_sys = majority_vote(cats)
        if body_sys:
            body_system_updates.append((body_sys, qid))
            stats["body_system_set"] += 1

        # source_type: majority vote across linked articles' source_type
        stypes = [art_lookup.get(a, {}).get("source_type") for a in linked_articles]
        stype = majority_vote(stypes)
        if stype:
            source_type_updates.append((stype, qid))
            stats["source_type_set"] += 1

        # ICD-10: union of all ICD-10 codes from all linked articles
        seen_codes: set[str] = set()
        has_icd10 = False
        for art_id in linked_articles:
            for code, desc, rel in icd10_lookup.get(art_id, []):
                if code not in seen_codes:
                    seen_codes.add(code)
                    icd10_rows.append((qid, code, desc or "", rel or ""))
                    has_icd10 = True
        if has_icd10:
            stats["icd10_questions"] += 1
        stats["icd10_total_rows"] += len(seen_codes)

    # ── Preview ───────────────────────────────────────────────────────
    print(f"\n══ Propagation preview ═══════════════════════════════════")
    total = len(all_qids)
    linked = len(xref)
    print(f"  Total AAFP questions:      {total}")
    print(f"  Questions with xref link:  {linked}  ({pct(linked, total)}%)")
    print(f"  body_system to set:        {stats['body_system_set']}")
    print(f"  source_type to set:        {stats['source_type_set']}")
    print(f"  ICD-10 questions covered:  {stats['icd10_questions']}")
    print(f"  ICD-10 rows to insert:     {stats['icd10_total_rows']}")

    # Sample body_system values
    if body_system_updates:
        sample_bs = body_system_updates[:5]
        print(f"\n  Sample body_system values:")
        for bs, qid in sample_bs:
            print(f"    {qid}  →  {bs}")

    # Sample ICD-10 rows
    if icd10_rows:
        print(f"\n  Sample ICD-10 rows:")
        for row in icd10_rows[:5]:
            print(f"    {row[0]}  →  {row[1]}  ({row[2][:50]})  [{row[3]}]")

    if DRY_RUN:
        print(f"\n[DRY RUN — no writes]")
        conn.close()
        return

    # ── Write ─────────────────────────────────────────────────────────
    print(f"\nWriting body_system...")
    conn.executemany(
        "UPDATE aafp_questions SET body_system = ? WHERE aafp_qid = ?",
        body_system_updates
    )
    conn.commit()

    print(f"Writing source_type...")
    conn.executemany(
        "UPDATE aafp_questions SET source_type = ? WHERE aafp_qid = ?",
        source_type_updates
    )
    conn.commit()

    print(f"Writing {len(icd10_rows)} ICD-10 rows...")
    conn.executemany(
        """INSERT OR IGNORE INTO aafp_question_icd10
           (aafp_qid, icd10_code, icd10_desc, relevance)
           VALUES (?, ?, ?, ?)""",
        icd10_rows
    )
    conn.commit()

    # ── Final stats ───────────────────────────────────────────────────
    run_stats(conn)
    print(f"\n  DB → {DB_PATH}")
    conn.close()
    print("Done.")


# ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if "--help" in sys.argv:
        print(__doc__)
        sys.exit(0)
    main()
