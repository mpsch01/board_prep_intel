"""
build_ite_db.py — ITE Intelligence Database Builder
=====================================================
Phase 2 | ITE Intelligence Pipeline

Reads:
  - ABFM_ITE_QuestionRefPairs_2020-2025.csv
  - ABFM_ITE_ReferenceTiers_Expanded_v1369.csv

Normalizes QIDs: Q2020-001 → QID-2020-0001
Parses author1/author2/year from CleanRef
Joins pairs → tiers on RefMatched = CleanRef
Outputs: ite_intelligence.db (SQLite, 3 tables)

Schema:
  articles(clean_ref PK, author1, author2, year, source_type,
           categories, tier, citation_count, unique_years, filename)
  questions(qid PK, exam_year)
  question_ref_pairs(id PK, qid FK, clean_ref FK, tier, match_score, ref_index)

Run:
  python scripts/build_ite_db.py
"""

import sqlite3
import csv
import re
import os
import json
from datetime import datetime
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).resolve().parent.parent
DATA_DIR   = Path(r"C:\Users\mpsch\Desktop\claude_knowledge\00_canonical\04_reference_data")
DB_PATH    = BASE_DIR / "db" / "ite_intelligence.db"
LOG_PATH   = BASE_DIR / "logs" / "build_ite_db_log.json"

PAIRS_CSV  = DATA_DIR / "ABFM_ITE_QuestionRefPairs_2020-2025.csv"
TIERS_CSV  = DATA_DIR / "ABFM_ITE_ReferenceTiers_Expanded_v1369.csv"


# ── QID Normalizer ─────────────────────────────────────────────────────────
def normalize_qid(raw: str) -> str:
    """
    Q2020-001   → QID-2020-0001
    Q2020-1     → QID-2020-0001
    QID-2020-1  → QID-2020-0001  (already prefixed, still pad)
    """
    raw = raw.strip()
    # Strip leading Q or QID-
    raw = re.sub(r'^QID-', '', raw)
    raw = re.sub(r'^Q',    '', raw)
    # Expect YYYY-NNN[N]
    m = re.match(r'^(\d{4})-(\d+)$', raw)
    if not m:
        return f"QID-INVALID-{raw}"
    year, num = m.group(1), m.group(2)
    return f"QID-{year}-{int(num):04d}"


# ── Author / Year Parser ────────────────────────────────────────────────────
def parse_clean_ref(clean_ref: str) -> dict:
    """
    Extract author1, author2, year from a CleanRef string.
    Format examples:
      Smith DK, Lennon RP, Carlsgaard PB: Title. Journal Year;...
      USPSTF: Title. Year.
      Gaitonde DY, Moore FC, Morgan MK: Title. AFP 2019;...
    Returns dict with author1, author2, year (all str or None).
    """
    result = {"author1": None, "author2": None, "year": None}

    # Extract year (4-digit, 1990-2030)
    year_match = re.search(r'\b(199\d|20[0-2]\d)\b', clean_ref)
    if year_match:
        result["year"] = year_match.group(1)

    # Split before the colon to get author block
    colon_idx = clean_ref.find(":")
    if colon_idx == -1:
        # No colon — try first token as author
        parts = clean_ref.split()
        if parts:
            result["author1"] = parts[0].rstrip(",")
        return result

    author_block = clean_ref[:colon_idx].strip()

    # Handle org-style refs (USPSTF, CDC, AAFP, etc.)
    if re.match(r'^[A-Z]{2,}', author_block) and "," not in author_block:
        result["author1"] = author_block
        return result

    # Split by comma, take first two surnames
    parts = [p.strip() for p in author_block.split(",")]
    # Each part like "Smith DK" or "Smith DK et al"
    if parts:
        name_parts = parts[0].split()
        result["author1"] = name_parts[0] if name_parts else None
    if len(parts) >= 2:
        name_parts = parts[1].split()
        candidate = name_parts[0] if name_parts else None
        # Skip initials-only tokens and "et al"
        if candidate and len(candidate) > 2 and candidate.lower() not in ("et", "al"):
            result["author2"] = candidate

    return result


# ── Database Setup ─────────────────────────────────────────────────────────
def init_db(conn: sqlite3.Connection):
    conn.executescript("""
        PRAGMA journal_mode=WAL;
        PRAGMA foreign_keys=ON;

        CREATE TABLE IF NOT EXISTS articles (
            clean_ref       TEXT PRIMARY KEY,
            author1         TEXT,
            author2         TEXT,
            year            TEXT,
            source_type     TEXT,
            categories      TEXT,
            blueprint_cats  TEXT,
            tier            TEXT,
            citation_count  INTEGER DEFAULT 0,
            unique_years    INTEGER DEFAULT 0,
            auto_assigned   TEXT,
            filename        TEXT
        );

        CREATE TABLE IF NOT EXISTS questions (
            qid             TEXT PRIMARY KEY,
            exam_year       INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS question_ref_pairs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            qid             TEXT NOT NULL REFERENCES questions(qid),
            clean_ref       TEXT REFERENCES articles(clean_ref),
            ref_raw         TEXT,
            tier            TEXT,
            match_score     REAL,
            ref_index       INTEGER,
            match_status    TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_pairs_qid       ON question_ref_pairs(qid);
        CREATE INDEX IF NOT EXISTS idx_pairs_clean_ref ON question_ref_pairs(clean_ref);
        CREATE INDEX IF NOT EXISTS idx_articles_tier   ON articles(tier);
        CREATE INDEX IF NOT EXISTS idx_articles_year   ON articles(year);
    """)
    conn.commit()


# ── Load Tiers ─────────────────────────────────────────────────────────────
def load_tiers(conn: sqlite3.Connection, path: Path) -> dict:
    """Insert articles from ReferenceTiers CSV. Returns clean_ref → row map."""
    article_map = {}
    rows_inserted = 0

    with open(path, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            clean_ref = row.get("CleanRef", "").strip()
            if not clean_ref:
                continue

            parsed = parse_clean_ref(clean_ref)
            record = {
                "clean_ref":      clean_ref,
                "author1":        parsed["author1"],
                "author2":        parsed["author2"],
                "year":           parsed["year"],
                "source_type":    row.get("SourceType", "").strip(),
                "categories":     row.get("Categories", "").strip(),
                "blueprint_cats": row.get("BlueprintCategories", "").strip(),
                "tier":           row.get("Tier", "").strip(),
                "citation_count": int(row.get("CitationCount", 0) or 0),
                "unique_years":   int(row.get("UniqueYears", 0) or 0),
                "auto_assigned":  row.get("AutoAssigned", "").strip(),
                "filename":       None,
            }
            article_map[clean_ref] = record

            conn.execute("""
                INSERT OR REPLACE INTO articles
                (clean_ref, author1, author2, year, source_type, categories,
                 blueprint_cats, tier, citation_count, unique_years, auto_assigned, filename)
                VALUES (:clean_ref, :author1, :author2, :year, :source_type, :categories,
                        :blueprint_cats, :tier, :citation_count, :unique_years, :auto_assigned, :filename)
            """, record)
            rows_inserted += 1

    conn.commit()
    print(f"  [articles]  Inserted {rows_inserted} rows from tiers CSV")
    return article_map


# ── Load Pairs ─────────────────────────────────────────────────────────────
def load_pairs(conn: sqlite3.Connection, path: Path, article_map: dict) -> dict:
    """
    Insert questions + question_ref_pairs from QuestionRefPairs CSV.
    Returns stats dict.
    """
    questions_seen = set()
    pairs_inserted = 0
    matched = 0
    unmatched = 0
    stub_articles = 0

    with open(path, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_qid   = row.get("QuestionID_raw", row.get("QuestionID", "")).strip()
            qid       = normalize_qid(raw_qid)
            exam_year = int(row.get("ExamYear", 0) or 0)
            ref_raw   = row.get("RefRaw", "").strip()
            ref_match = row.get("RefMatched", "").strip()
            tier      = row.get("Tier", "").strip()
            match_score = float(row.get("MatchScore", 0) or 0)
            ref_index = int(row.get("RefIndex", 0) or 0)
            match_status = "matched" if match_score >= 1.0 else ("partial" if match_score > 0 else "unmatched")

            # Upsert question
            if qid not in questions_seen:
                conn.execute("""
                    INSERT OR IGNORE INTO questions (qid, exam_year)
                    VALUES (?, ?)
                """, (qid, exam_year))
                questions_seen.add(qid)

            # If RefMatched not in articles table, insert a stub so FK is satisfied
            clean_ref_key = ref_match if ref_match else None
            if clean_ref_key and clean_ref_key not in article_map:
                parsed = parse_clean_ref(clean_ref_key)
                conn.execute("""
                    INSERT OR IGNORE INTO articles
                    (clean_ref, author1, author2, year, source_type, tier)
                    VALUES (?, ?, ?, ?, 'stub', ?)
                """, (clean_ref_key, parsed["author1"], parsed["author2"],
                      parsed["year"], tier))
                article_map[clean_ref_key] = True
                stub_articles += 1

            conn.execute("""
                INSERT INTO question_ref_pairs
                (qid, clean_ref, ref_raw, tier, match_score, ref_index, match_status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (qid, clean_ref_key, ref_raw, tier, match_score, ref_index, match_status))

            pairs_inserted += 1
            if match_status == "matched":
                matched += 1
            elif match_status == "unmatched":
                unmatched += 1

    conn.commit()

    stats = {
        "questions_unique": len(questions_seen),
        "pairs_inserted":   pairs_inserted,
        "matched":          matched,
        "unmatched":        unmatched,
        "stub_articles":    stub_articles,
        "match_rate_pct":   round(matched / pairs_inserted * 100, 1) if pairs_inserted else 0,
    }
    print(f"  [questions] {stats['questions_unique']} unique QIDs inserted")
    print(f"  [pairs]     {pairs_inserted} pairs ({stats['match_rate_pct']}% matched, "
          f"{unmatched} unmatched, {stub_articles} stubs added)")
    return stats


# ── Verification Queries ────────────────────────────────────────────────────
def verify_db(conn: sqlite3.Connection) -> dict:
    """Run sanity checks and return summary."""
    cur = conn.cursor()

    checks = {}

    cur.execute("SELECT COUNT(*) FROM articles")
    checks["article_count"] = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM questions")
    checks["question_count"] = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM question_ref_pairs")
    checks["pair_count"] = cur.fetchone()[0]

    cur.execute("SELECT COUNT(DISTINCT exam_year) FROM questions")
    checks["exam_years"] = cur.fetchone()[0]

    cur.execute("SELECT exam_year, COUNT(*) as n FROM questions GROUP BY exam_year ORDER BY exam_year")
    checks["questions_by_year"] = {str(r[0]): r[1] for r in cur.fetchall()}

    cur.execute("SELECT tier, COUNT(*) as n FROM articles GROUP BY tier ORDER BY n DESC")
    checks["articles_by_tier"] = {r[0]: r[1] for r in cur.fetchall()}

    cur.execute("""
        SELECT a.clean_ref, COUNT(p.qid) as q_count
        FROM articles a JOIN question_ref_pairs p ON a.clean_ref = p.clean_ref
        GROUP BY a.clean_ref ORDER BY q_count DESC LIMIT 5
    """)
    checks["top_articles_by_question_count"] = [
        {"clean_ref": r[0][:80], "question_count": r[1]} for r in cur.fetchall()
    ]

    # Check for any orphaned pairs (no matching article)
    cur.execute("""
        SELECT COUNT(*) FROM question_ref_pairs
        WHERE clean_ref NOT IN (SELECT clean_ref FROM articles) AND clean_ref IS NOT NULL
    """)
    checks["orphaned_pairs"] = cur.fetchone()[0]

    return checks


# ── Main ────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("ITE Intelligence DB Builder")
    print(f"  DB path:    {DB_PATH}")
    print(f"  Pairs CSV:  {PAIRS_CSV}")
    print(f"  Tiers CSV:  {TIERS_CSV}")
    print("=" * 60)

    for p in [PAIRS_CSV, TIERS_CSV]:
        if not p.exists():
            raise FileNotFoundError(f"Required input not found: {p}")

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    try:
        print("\n[1] Initializing schema...")
        init_db(conn)

        print("\n[2] Loading reference tiers (articles)...")
        article_map = load_tiers(conn, TIERS_CSV)

        print("\n[3] Loading question-reference pairs...")
        pair_stats = load_pairs(conn, PAIRS_CSV, article_map)

        print("\n[4] Verifying database...")
        checks = verify_db(conn)

        print("\n── Verification Summary ──────────────────────────────")
        print(f"  Articles:         {checks['article_count']}")
        print(f"  Questions:        {checks['question_count']}")
        print(f"  Pairs:            {checks['pair_count']}")
        print(f"  Exam years:       {checks['exam_years']}")
        print(f"  Orphaned pairs:   {checks['orphaned_pairs']}")
        print(f"  Questions/year:   {checks['questions_by_year']}")
        print(f"  Articles/tier:    {checks['articles_by_tier']}")
        print("\n  Top 5 most-tested articles:")
        for a in checks["top_articles_by_question_count"]:
            print(f"    [{a['question_count']} Qs] {a['clean_ref']}")

        # Write log
        log = {
            "built_at": datetime.now().isoformat(),
            "db_path":  str(DB_PATH),
            "inputs": {
                "pairs_csv": str(PAIRS_CSV),
                "tiers_csv": str(TIERS_CSV),
            },
            "pair_stats": pair_stats,
            "verification": checks,
        }
        with open(LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(log, f, indent=2)

        print(f"\n✅ DB built: {DB_PATH}")
        print(f"   Log written: {LOG_PATH}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
