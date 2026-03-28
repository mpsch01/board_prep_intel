#!/usr/bin/env python3
"""
AAFP BRQ Keyword Extractor
━━━━━━━━━━━━━━━━━━━━━━━━━━
Extracts clinical keywords from AAFP question stems and explanations
using TF-IDF across the AAFP corpus. Entirely local — no API calls.

Adds columns if not present:
  aafp_questions.stem_keywords          TEXT   comma-separated clinical terms from stem
  aafp_explanations.explanation_keywords TEXT   comma-separated clinical terms from explanation

Output feeds the downstream API concept_tags enrichment pass (Big Claude).

Run:
  python aafp_keyword_extractor.py              ← extract + write (default top 15 each)
  python aafp_keyword_extractor.py --top 20     ← override top-N
  python aafp_keyword_extractor.py --dry-run    ← preview sample output, no writes
  python aafp_keyword_extractor.py --stats      ← show column coverage from existing DB

TF-IDF approach:
  Each question stem is treated as a document in the stem corpus (1,221 docs).
  Each explanation is treated as a document in the explanation corpus (1,221 docs).
  TF-IDF surfaces terms that are frequent within ONE question AND distinctive
  vs. the overall corpus — exactly what a clinical keyword should be.
  Unigrams + bigrams, 3+ character minimum.
"""

import re
import math
import sys
import sqlite3
from pathlib import Path
from collections import Counter, defaultdict

# ══════════════════════════════════════════════════════════════════════
# PATHS
# ══════════════════════════════════════════════════════════════════════
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH      = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"
# ══════════════════════════════════════════════════════════════════════

DRY_RUN = "--dry-run" in sys.argv
STATS   = "--stats"   in sys.argv

TOP_N = 15
for i, arg in enumerate(sys.argv):
    if arg == "--top" and i + 1 < len(sys.argv):
        try:
            TOP_N = int(sys.argv[i + 1])
        except ValueError:
            pass


# ─────────────────────────────────────────────────────────────────────
# STOPWORDS
# Extended medical stopword list: general English + clinical noise
# that appears in virtually every question (adds no signal).
# ─────────────────────────────────────────────────────────────────────
STOPWORDS = {
    # General English
    "a", "an", "the", "and", "or", "but", "not", "nor", "so", "yet",
    "in", "on", "at", "to", "for", "of", "with", "from", "by", "as",
    "is", "are", "was", "were", "be", "been", "being", "have", "has",
    "had", "do", "does", "did", "will", "would", "could", "should",
    "may", "might", "can", "shall", "must",
    "this", "that", "these", "those", "it", "its", "itself",
    "he", "she", "they", "their", "them", "we", "our", "you", "your",
    "who", "which", "what", "when", "where", "how", "why",
    "one", "two", "three", "four", "five", "six", "seven", "eight",
    "also", "both", "each", "few", "more", "most", "other", "some",
    "such", "than", "then", "very", "just", "now", "only", "same",
    "about", "above", "after", "all", "any", "because", "before",
    "between", "during", "even", "every", "following", "given", "if",
    "into", "like", "much", "per", "since", "still", "through", "too",
    "under", "up", "upon", "without", "within", "while", "already",
    "often", "never", "always", "usually", "typically", "generally",
    # Clinical filler — in nearly every AAFP question/explanation
    "patient", "patients", "year", "years", "old", "male", "female",
    "man", "woman", "child", "girl", "boy", "infant", "adult",
    "history", "presents", "presentation", "exam", "examination",
    "physical", "initial", "given", "known", "seen", "new", "well",
    "age", "first", "test", "use", "used", "using", "associated",
    "include", "includes", "including", "based", "findings", "finding",
    "result", "results", "recent", "further", "taking", "report",
    "reports", "status", "level", "levels", "current", "evaluation",
    "assessment", "show", "shows", "shown", "noted", "note", "notes",
    "appropriate", "indicate", "indicates", "indicated", "recommended",
    "consistent", "significant", "likely", "concerning", "additional",
    "increase", "increased", "decreased", "elevated", "normal",
    "abnormal", "best", "next", "management", "treatment", "therapy",
    "diagnosis", "clinical", "recommend", "concern", "prior",
    "develop", "developed", "develops", "negative", "positive",
    "mild", "moderate", "severe", "acute", "chronic", "recent",
    "cause", "causes", "caused", "due", "related", "present",
    "common", "commonly", "important", "most", "least", "high",
    "low", "well", "poorly", "typically", "recently", "start",
    "started", "begins", "began", "following", "undergo", "undergoes",
    "underwent", "undergo", "review", "reviewed", "performed",
    "obtained", "ordered", "started", "placed", "admitted", "seen",
    "referred", "consulted", "returned", "brought",
    # Units / abbreviations that appear as tokens
    "due", "via", "per", "the", "ref", "doi", "and", "etal",
    "mg", "ml", "mcg", "mmhg", "ium", "ibid", "vol", "fig",
}


# ─────────────────────────────────────────────────────────────────────
# TOKENIZER
# ─────────────────────────────────────────────────────────────────────
def tokenize(text: str) -> list[str]:
    """
    Tokenize text into unigrams + bigrams.
    - Lowercase
    - 3+ character alpha tokens only
    - Filter STOPWORDS
    - Bigrams from consecutive non-stopword tokens
    """
    raw = re.findall(r"[a-zA-Z]{3,}", (text or "").lower())
    filtered = [t for t in raw if t not in STOPWORDS]
    unigrams = filtered
    bigrams  = [f"{filtered[i]} {filtered[i+1]}" for i in range(len(filtered) - 1)]
    return unigrams + bigrams


# ─────────────────────────────────────────────────────────────────────
# TF-IDF ENGINE
# ─────────────────────────────────────────────────────────────────────
def build_tfidf(docs: list[str], top_n: int) -> list[list[str]]:
    """
    Compute TF-IDF for each document in docs.

    TF  = count(term in doc) / total_tokens_in_doc
    IDF = log((N+1) / (df+1)) + 1.0   [smoothed to avoid zero-division]

    Returns list of top_n term lists (strings only, score dropped).
    One list per document, same order as input.
    """
    N = len(docs)

    # Pass 1: tokenize all docs, build document-frequency map
    doc_token_lists: list[Counter] = []
    df: dict[str, int] = defaultdict(int)

    for doc in docs:
        tokens = tokenize(doc)
        counts = Counter(tokens)
        doc_token_lists.append(counts)
        for term in counts:
            df[term] += 1

    # Pass 2: score each doc
    results: list[list[str]] = []
    for counts in doc_token_lists:
        if not counts:
            results.append([])
            continue
        total = sum(counts.values())
        scored = []
        for term, count in counts.items():
            tf  = count / total
            idf = math.log((N + 1) / (df[term] + 1)) + 1.0
            scored.append((term, tf * idf))
        scored.sort(key=lambda x: x[1], reverse=True)
        results.append([term for term, _ in scored[:top_n]])

    return results


# ─────────────────────────────────────────────────────────────────────
# SCHEMA HELPERS
# ─────────────────────────────────────────────────────────────────────
def add_column_if_missing(conn: sqlite3.Connection, table: str, column: str) -> None:
    """ALTER TABLE to add column if it doesn't already exist."""
    cols = [row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]
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
    print("\n══ AAFP Keyword Coverage ══════════════════════════════════")
    checks = [
        ("aafp_questions",    "stem_keywords"),
        ("aafp_explanations", "explanation_keywords"),
    ]
    for table, col in checks:
        try:
            total  = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            filled = conn.execute(
                f"SELECT COUNT(*) FROM {table} WHERE {col} IS NOT NULL AND {col} != ''"
            ).fetchone()[0]
            print(f"  {table}.{col:<28}  {filled}/{total}  ({pct(filled, total)}%)")
        except Exception as e:
            print(f"  {table}.{col}  — column missing or error: {e}")


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

    # ── Ensure columns exist ──────────────────────────────────────────
    print("\nSchema check...")
    add_column_if_missing(conn, "aafp_questions",    "stem_keywords")
    add_column_if_missing(conn, "aafp_explanations", "explanation_keywords")
    conn.commit()

    # ── Load stems ────────────────────────────────────────────────────
    print("\nLoading stems...")
    q_rows = conn.execute(
        "SELECT aafp_qid, stem FROM aafp_questions ORDER BY aafp_qid"
    ).fetchall()
    q_qids  = [r[0] for r in q_rows]
    stems   = [r[1] or "" for r in q_rows]
    print(f"  {len(stems)} stems loaded")

    # ── Load explanations ─────────────────────────────────────────────
    print("Loading explanations...")
    e_rows = conn.execute(
        "SELECT aafp_qid, explanation FROM aafp_explanations ORDER BY aafp_qid"
    ).fetchall()
    e_qids = [r[0] for r in e_rows]
    exps   = [r[1] or "" for r in e_rows]
    print(f"  {len(exps)} explanations loaded")

    # ── TF-IDF ────────────────────────────────────────────────────────
    print(f"\nComputing stem TF-IDF (top {TOP_N})...")
    stem_kw_lists = build_tfidf(stems, TOP_N)

    print(f"Computing explanation TF-IDF (top {TOP_N})...")
    exp_kw_lists  = build_tfidf(exps, TOP_N)

    # ── Preview sample ────────────────────────────────────────────────
    print(f"\n══ Sample output (first 3 questions) ═════════════════════")
    for i in range(min(3, len(q_qids))):
        print(f"\n  {q_qids[i]}")
        stem_preview = (stems[i] or "")[:120].replace("\n", " ")
        print(f"  Stem:        {stem_preview}...")
        print(f"  stem_kw:     {', '.join(stem_kw_lists[i][:8])}")
        exp_preview  = (exps[i] or "")[:120].replace("\n", " ")
        print(f"  Explanation: {exp_preview}...")
        print(f"  expl_kw:     {', '.join(exp_kw_lists[i][:8])}")

    if DRY_RUN:
        print(f"\n[DRY RUN — {len(stems)} stems / {len(exps)} explanations processed, no writes]")
        conn.close()
        return

    # ── Write stem_keywords ───────────────────────────────────────────
    print(f"\nWriting {len(stem_kw_lists)} stem_keywords rows...")
    for qid, kw_list in zip(q_qids, stem_kw_lists):
        conn.execute(
            "UPDATE aafp_questions SET stem_keywords = ? WHERE aafp_qid = ?",
            (", ".join(kw_list), qid)
        )
    conn.commit()

    # ── Write explanation_keywords ────────────────────────────────────
    print(f"Writing {len(exp_kw_lists)} explanation_keywords rows...")
    for qid, kw_list in zip(e_qids, exp_kw_lists):
        conn.execute(
            "UPDATE aafp_explanations SET explanation_keywords = ? WHERE aafp_qid = ?",
            (", ".join(kw_list), qid)
        )
    conn.commit()

    # ── Coverage check ────────────────────────────────────────────────
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
