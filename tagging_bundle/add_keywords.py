"""
add_keywords.py — Populate questions table with stem/explanation text and keywords
===================================================================================
Phase 2 | ITE Intelligence Pipeline

Reads ABFM_ITE_Master_v3.csv and writes to questions table:
  - stem_text, answer_text, explanation_text
  - stem_keywords, explanation_keywords, all_keywords

QID normalization: ABFM_ITE_Master_v3.csv uses SEQUENTIAL numbering across years:
  2020: Q2020-001 to Q2020-200  (offset 0)   -> QID-2020-0001
  2021: Q2021-201 to Q2021-400  (offset 200) -> QID-2021-0001
  2022: Q2022-401 to Q2022-600  (offset 400) -> QID-2022-0001
  2023: Q2023-601 to Q2023-800  (offset 600) -> QID-2023-0001
  2024: Q2024-801 to Q2024-1000 (offset 800) -> QID-2024-0001
  2025: Q2025-001 to Q2025-200  (offset 0)   -> QID-2025-0001  (resets)
The DB uses per-year numbering (each year restarts at 0001).

Run:
  python scripts/add_keywords.py
  python scripts/add_keywords.py --source path/to/file.csv
  python scripts/add_keywords.py --dry-run
"""

import sqlite3
import csv
import json
import re
import argparse
from pathlib import Path
from datetime import datetime

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).resolve().parent.parent
DB_PATH     = BASE_DIR / "00_database" / "db" / "ite_intelligence.db"
LOG_PATH    = BASE_DIR / "logs" / "add_keywords_log.json"

DEFAULT_SOURCE = Path(
    r"C:\Users\mpsch\Desktop\claude_knowledge"
    r"\board_prep\ite_exam\03_database\raw_files\ABFM_ITE_Master_v3.csv"
)

# Clinical stopwords
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

# ── QID Normalizer ─────────────────────────────────────────────────────────
# v3 CSV uses sequential numbering; DB uses per-year numbering.
YEAR_OFFSETS = {"2020": 0, "2021": 200, "2022": 400, "2023": 600, "2024": 800, "2025": 0}

def normalize_qid(raw: str, exam_year: str = None) -> str:
    raw = raw.strip()
    m = re.match(r'^Q?(\d{4})-(\d+)$', raw, re.IGNORECASE)
    if not m:
        return None
    year   = m.group(1)
    number = int(m.group(2))
    offset = YEAR_OFFSETS.get(str(exam_year) if exam_year else year, 0)
    number -= offset
    if number < 1:
        return None
    return f"QID-{year}-{number:04d}"


# ── Keyword Extractor ──────────────────────────────────────────────────────
def extract_explanation_keywords(text: str, top_n: int = 12) -> list:
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
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=str, default=str(DEFAULT_SOURCE))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    source_path = Path(args.source)
    if not source_path.exists():
        print(f"❌ Source not found: {source_path}"); return
    if not DB_PATH.exists():
        print(f"❌ DB not found: {DB_PATH}"); return

    print("=" * 60)
    print(f"add_keywords.py  |  Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print(f"  Source: {source_path.name}")
    print("=" * 60)

    # Load CSV
    with open(source_path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    print(f"\n  Loaded {len(rows)} rows")

    # Auto-detect columns
    sample = rows[0]
    col_map = {}
    for col in sample.keys():
        cl = col.lower().strip()
        if "questionid" in cl: col_map["qid"] = col
        elif "stem" in cl:     col_map.setdefault("stem", col)
        elif "correctanswer" in cl or ("answer" in cl and "id" not in cl):
            col_map.setdefault("answer", col)
        elif "explanation" in cl: col_map.setdefault("explanation", col)
        elif "cluster_keywords" in cl or "keywords" in cl:
            col_map.setdefault("cluster_keywords", col)
    print(f"  Column map: {col_map}")

    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    # Add columns if missing
    cur.execute("PRAGMA table_info(questions)")
    existing = {r[1] for r in cur.fetchall()}
    for col, dtype in [("stem_text","TEXT"),("answer_text","TEXT"),
                       ("explanation_text","TEXT"),("stem_keywords","TEXT"),
                       ("explanation_keywords","TEXT"),("all_keywords","TEXT")]:
        if col not in existing:
            conn.execute(f"ALTER TABLE questions ADD COLUMN {col} {dtype}")
            print(f"  + Added column: {col}")
    conn.commit()


    # Build + apply updates
    updates, skipped, no_match = [], 0, 0

    for row in rows:
        raw_qid = row.get(col_map.get("qid",""), "").strip()
        exam_yr = row.get("ExamYear", "").strip()
        qid     = normalize_qid(raw_qid, exam_yr)
        if not qid:
            skipped += 1; continue

        stem        = row.get(col_map.get("stem",""), "").strip()
        answer      = row.get(col_map.get("answer",""), "").strip()
        explanation = row.get(col_map.get("explanation",""), "").strip()
        cluster_kws = row.get(col_map.get("cluster_keywords",""), "").strip()
        expl_kws    = extract_explanation_keywords(explanation)
        all_kws     = merge_keywords(cluster_kws, expl_kws)

        updates.append((stem, answer, explanation, cluster_kws,
                        ", ".join(expl_kws), all_kws, qid))

    print(f"\n  Updates prepared: {len(updates)}")

    if args.dry_run:
        print("\n  ── DRY RUN — first 3 updates ──────────────────────")
        for u in updates[:3]:
            print(f"\n  QID: {u[6]}")
            print(f"    Stem:     {u[0][:80]}...")
            print(f"    Answer:   {u[1]}")
            print(f"    Stem kws: {u[3][:60]}")
            print(f"    Expl kws: {u[4][:60]}")
            print(f"    All kws:  {u[5][:80]}")
        print("\n  ⚠️  DRY RUN — no changes written")
        conn.close(); return

    updated = 0
    for u in updates:
        r = conn.execute("""
            UPDATE questions
            SET stem_text=?, answer_text=?, explanation_text=?,
                stem_keywords=?, explanation_keywords=?, all_keywords=?
            WHERE qid=?
        """, u)
        if r.rowcount: updated += 1
        else:          no_match += 1
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM questions WHERE all_keywords IS NOT NULL AND all_keywords!=''")
    filled = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM questions")
    total  = cur.fetchone()[0]
    conn.close()

    print(f"\n  Rows updated:    {updated}")
    print(f"  No DB match:     {no_match}")
    print(f"  Keywords filled: {filled}/{total} ({round(filled/total*100,1)}%)")

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "w") as f:
        json.dump({"run_at": datetime.now().isoformat(), "source": str(source_path),
                   "dry_run": False, "rows_in": len(rows), "updated": updated,
                   "no_match": no_match, "keywords_filled": f"{filled}/{total}"}, f, indent=2)

    print(f"\n✅ Done\n   Log: {LOG_PATH}")


if __name__ == "__main__":
    main()
