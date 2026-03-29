"""
aafp_assign_body_system.py  v2
================================
Assigns body_system to all 1,221 AAFP BRQ questions using a three-tier strategy:

  Tier 1 — ALREADY ASSIGNED (594 Q)
      Questions with body_system populated by aafp_context_propagator (article xref).
      These are authoritative. Kept as-is. method = 'propagated'

  Tier 2 — ITE NEIGHBOR (questions with ite_nearest_dist < 0.45)
      Close ITE neighbor carries reliable body_system label.
      method = 'neighbor'

  Tier 3 — KEYWORD FREQUENCY CLASSIFIER (remaining questions)
      Builds a term→body_system frequency table from 1,629 ITE questions
      (the ground-truth corpus). Scores each AAFP question's all_keywords +
      correct_text against the table. Picks highest-scoring body_system.
      method = 'keyword_freq'

Schema change:
  ALTER TABLE aafp_questions ADD COLUMN body_system_method TEXT
  (tracks how each assignment was made — auditable)

Run:
    python aafp_assign_body_system.py             # full run
    python aafp_assign_body_system.py --dry-run   # report only, no writes
    python aafp_assign_body_system.py --report    # coverage report after run

Path: SCRIPT_DIR = this file; PROJECT_ROOT = SCRIPT_DIR.parent.parent
"""

import sqlite3
import argparse
from pathlib import Path
from collections import defaultdict, Counter

SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH      = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"

NEIGHBOR_DIST_THRESHOLD  = 0.45   # below this → trust ITE neighbor body_system
CONFIDENCE_THRESHOLD     = 1.10   # below this → classifier too uncertain, fall back to ITE neighbor

# Stopwords: demographic descriptors and generic clinical filler that appear
# across all body systems equally — not discriminating signals.
# "male"/"female" are the primary culprits (drive false Reproductive: Male/Female hits).
# "year old", "patient", "presents" etc. are noise for the same reason.
CLASSIFIER_STOPWORDS = {
    # Demographics — the main offenders
    "male", "female", "woman", "women", "man", "men", "boy", "girl",
    "patient", "patients", "person", "individual",
    # Age descriptors
    "year", "old", "year old", "years", "aged", "age", "young",
    "elderly", "adult", "adults", "child", "children", "adolescent",
    "infant", "newborn", "pediatric",
    # Generic presentation words
    "presents", "presentation", "history", "physical", "examination",
    "following", "appropriate", "management", "treatment", "diagnosis",
    "evaluation", "symptoms", "signs", "office", "clinic", "visit",
    "care", "physician", "sees", "comes",
    # Generic modifiers
    "normal", "abnormal", "recent", "current", "new", "initial",
    "further", "additional", "next", "first", "second", "primary",
    # Ultra-common tokens
    "level", "levels", "result", "results", "test", "testing",
    "finding", "findings", "report", "value", "true", "one",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_keywords(kw_str: str | None) -> list[str]:
    if not kw_str:
        return []
    return [t.strip().lower() for t in kw_str.split(",") if t.strip()]


def ensure_column(conn: sqlite3.Connection) -> None:
    existing = {row[1] for row in conn.execute("PRAGMA table_info(aafp_questions)")}
    for col in ["body_system_method"]:
        if col not in existing:
            conn.execute(f"ALTER TABLE aafp_questions ADD COLUMN {col} TEXT")
            print(f"  [schema] Added column: {col}")
    conn.commit()


# ---------------------------------------------------------------------------
# Step 1: Build term→body_system frequency table from ITE questions
# ---------------------------------------------------------------------------

def build_frequency_table(conn: sqlite3.Connection) -> dict[str, Counter]:
    """
    Returns: term_freq[term] = Counter({body_system: count, ...})
    Built from ITE questions.all_keywords where body_system_merged IS NOT NULL.
    correct_text is also included as high-weight signal (counted 3x).
    """
    rows = conn.execute("""
        SELECT body_system_merged, all_keywords, correct_text
        FROM questions
        WHERE body_system_merged IS NOT NULL
          AND all_keywords IS NOT NULL
    """).fetchall()

    term_freq: dict[str, Counter] = defaultdict(Counter)
    body_system_counts: Counter = Counter()

    for bs, all_kw, correct_text in rows:
        body_system_counts[bs] += 1
        terms = parse_keywords(all_kw)
        # correct_text counted at 3x weight — it names the answer directly
        if correct_text:
            correct_terms = [t.strip().lower() for t in correct_text.split() if len(t.strip()) > 3]
            terms = correct_terms * 3 + terms
        for term in terms:
            term_freq[term][bs] += 1

    print(f"  [freq table] Built from {len(rows)} ITE questions, "
          f"{len(term_freq)} unique terms, {len(body_system_counts)} body systems")
    return term_freq, body_system_counts


def score_body_system(terms: list[str], term_freq: dict[str, Counter],
                      body_system_counts: Counter) -> tuple[str | None, float]:
    """
    Score each body_system using term frequencies (Naive Bayes-style).
    Demographic stopwords are filtered before scoring.
    Returns (best_body_system, confidence_ratio) or (None, 0) if no signal.
    confidence_ratio = top_score / second_score (higher = more confident).
    """
    scores: Counter = Counter()
    for term in terms:
        if term in CLASSIFIER_STOPWORDS:
            continue
        if term in term_freq:
            for bs, count in term_freq[term].items():
                # Normalize by how common the body_system is overall
                scores[bs] += count / body_system_counts[bs]

    if not scores:
        return None, 0.0

    top_two = scores.most_common(2)
    best_bs, best_score = top_two[0]
    confidence = best_score / top_two[1][1] if len(top_two) > 1 and top_two[1][1] > 0 else 99.0
    return best_bs, round(confidence, 3)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(dry_run: bool = False, report_only: bool = False, rerun_kwfreq: bool = False) -> None:
    print(f"DB: {DB_PATH}")
    if dry_run:
        print("  ** DRY RUN — no writes **\n")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    if not dry_run and not report_only:
        ensure_column(conn)

    # Build frequency table
    term_freq, body_system_counts = build_frequency_table(conn)

    # Load all AAFP questions — body_system_method may not exist yet
    existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(aafp_questions)")}
    method_col = "aq.body_system_method" if "body_system_method" in existing_cols else "NULL as body_system_method"

    rows = conn.execute(f"""
        SELECT aq.aafp_qid, aq.body_system, {method_col},
               aq.all_keywords, aq.ite_nearest_qid, aq.ite_nearest_dist,
               ae.correct_text
        FROM aafp_questions aq
        LEFT JOIN aafp_explanations ae ON aq.aafp_qid = ae.aafp_qid
    """).fetchall()

    # Load ITE nearest body_system in one shot
    ite_body = {}
    ite_rows = conn.execute(
        "SELECT qid, body_system_merged FROM questions WHERE body_system_merged IS NOT NULL"
    ).fetchall()
    for r in ite_rows:
        ite_body[r["qid"]] = r["body_system_merged"]

    updates = []
    stats = Counter()
    unresolved = []
    sample_kwfreq = []   # for dry-run preview

    for row in rows:
        qid        = row["aafp_qid"]
        cur_bs     = row["body_system"]
        cur_method = row["body_system_method"]
        dist       = row["ite_nearest_dist"]
        nearest    = row["ite_nearest_qid"]
        correct    = row["correct_text"] or ""
        all_kw     = row["all_keywords"] or ""

        # Tier 1: already assigned by propagator
        if cur_bs and cur_method == "propagated":
            stats["tier1_keep"] += 1
            continue

        if cur_bs and not cur_method:
            # Propagated but method not yet tagged — mark it
            updates.append(("propagated", cur_bs, qid))
            stats["tier1_tag"] += 1
            continue

        # When --rerun-kwfreq: skip neighbor assignments, only redo keyword_freq
        if rerun_kwfreq and cur_method in ("neighbor", "neighbor_fallback"):
            stats["tier2_keep"] += 1
            continue

        # Tier 2: close ITE neighbor
        if dist is not None and dist < NEIGHBOR_DIST_THRESHOLD and nearest in ite_body:
            neighbor_bs = ite_body[nearest]
            updates.append(("neighbor", neighbor_bs, qid))
            stats["tier2_neighbor"] += 1
            continue

        # Tier 3: keyword frequency classifier
        correct_terms = [t.strip().lower() for t in correct.split() if len(t.strip()) > 3]
        kw_terms = parse_keywords(all_kw)
        all_terms = correct_terms * 3 + kw_terms

        best_bs, confidence = score_body_system(all_terms, term_freq, body_system_counts)

        if best_bs and confidence >= CONFIDENCE_THRESHOLD:
            updates.append(("keyword_freq", best_bs, qid))
            stats["tier3_kwfreq"] += 1
            if len(sample_kwfreq) < 5:
                sample_kwfreq.append((qid, best_bs, confidence, correct[:60], all_kw[:80]))
        elif best_bs and confidence < CONFIDENCE_THRESHOLD:
            # Classifier uncertain — fall back to ITE neighbor regardless of distance
            fallback_bs = ite_body.get(nearest)
            if fallback_bs:
                updates.append(("neighbor_lowconf", fallback_bs, qid))
                stats["tier3_lowconf_fallback"] += 1
            else:
                # No ITE neighbor either — take the uncertain kwfreq result
                updates.append(("keyword_freq_lowconf", best_bs, qid))
                stats["tier3_kwfreq_lowconf"] += 1
        else:
            # Absolute fallback: use ITE neighbor regardless of distance
            if nearest in ite_body:
                updates.append(("neighbor_fallback", ite_body[nearest], qid))
                stats["tier3_fallback"] += 1
            else:
                updates.append(("unresolved", None, qid))
                stats["unresolved"] += 1
                unresolved.append(qid)

    # Summary
    total = len(rows)
    print(f"\n  === ASSIGNMENT SUMMARY ({total} questions) ===")
    print(f"  Tier 1 — already propagated (kept):    {stats['tier1_keep'] + stats['tier1_tag']:4d}")
    print(f"  Tier 2 — ITE neighbor (dist < {NEIGHBOR_DIST_THRESHOLD}):   {stats['tier2_neighbor']:4d}")
    print(f"  Tier 3 — keyword freq classifier:       {stats['tier3_kwfreq']:4d}")
    print(f"  Tier 3 — neighbor fallback (dist≥{NEIGHBOR_DIST_THRESHOLD}): {stats['tier3_fallback']:4d}")
    print(f"  Unresolved:                             {stats['unresolved']:4d}")
    print(f"  Total assignments to write:             {len(updates):4d}")

    if sample_kwfreq:
        print(f"\n  === SAMPLE Tier 3 keyword_freq assignments ===")
        for qid, bs, conf, correct, kw in sample_kwfreq:
            print(f"  [{qid}] → {bs} (conf ratio: {conf})")
            print(f"    correct: {correct}")
            print(f"    keywords: {kw}")

    if unresolved:
        print(f"\n  UNRESOLVED ({len(unresolved)}): {unresolved[:10]}")

    if dry_run or report_only:
        return

    # Write updates
    # Updates tuple: (method, body_system, qid)
    conn.executemany("""
        UPDATE aafp_questions
        SET body_system_method = ?,
            body_system = COALESCE(?, body_system)
        WHERE aafp_qid = ?
    """, updates)
    conn.commit()

    # Verify
    populated = conn.execute(
        "SELECT COUNT(*) FROM aafp_questions WHERE body_system IS NOT NULL"
    ).fetchone()[0]
    print(f"\n  ✓ body_system populated: {populated}/{total}")

    # Method breakdown
    print("\n  Method breakdown (post-write):")
    for row in conn.execute("""
        SELECT body_system_method, COUNT(*) as n
        FROM aafp_questions
        GROUP BY body_system_method
        ORDER BY n DESC
    """).fetchall():
        print(f"    {row[0] or 'NULL'}: {row[1]}")

    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Assign body_system to all AAFP BRQ questions")
    parser.add_argument("--dry-run",      action="store_true", help="Preview only, no DB writes")
    parser.add_argument("--report",       action="store_true", help="Show coverage report after run")
    parser.add_argument("--rerun-kwfreq", action="store_true", help="Re-score only keyword_freq rows (skip propagated + neighbor)")
    args = parser.parse_args()
    run(dry_run=args.dry_run, report_only=args.report, rerun_kwfreq=args.rerun_kwfreq)
