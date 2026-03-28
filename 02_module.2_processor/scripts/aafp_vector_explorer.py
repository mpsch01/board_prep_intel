#!/usr/bin/env python3
"""
AAFP Vector Explorer
━━━━━━━━━━━━━━━━━━━
Cross-corpus semantic similarity analysis.
Queries aafp_question_vec ↔ question_vec to map AAFP questions
onto the ITE question space.

What this shows:
  1. Distance distribution (AAFP → nearest ITE match)
  2. Strongest matches: AAFP questions with ITE twins
  3. Unique AAFP territory: furthest from any ITE question
  4. Body-system breakdown of overlap
  5. Article-linked vs unlinked comparison

Persisting scores (--save):
  Writes ite_nearest_qid + ite_nearest_dist to aafp_questions.
  Adds columns if not present. Safe to re-run.

Run:
  python aafp_vector_explorer.py              ← analysis only (read-only)
  python aafp_vector_explorer.py --save       ← analysis + persist scores to DB
  python aafp_vector_explorer.py --save --new-only  ← only fill NULL rows (incremental)
  python aafp_vector_explorer.py --sample 50  ← quick look at first N questions
"""

import sys
import sqlite3
import statistics
from pathlib import Path
from collections import defaultdict, Counter

try:
    import sqlite_vec
except ImportError:
    print("ERROR: sqlite-vec not installed. Run: pip install sqlite-vec")
    sys.exit(1)

# ══════════════════════════════════════════════════════════════════════
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH      = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"
# ══════════════════════════════════════════════════════════════════════

SAVE     = "--save"     in sys.argv
NEW_ONLY = "--new-only" in sys.argv

SAMPLE_N = None
for i, arg in enumerate(sys.argv):
    if arg == "--sample" and i + 1 < len(sys.argv):
        try:
            SAMPLE_N = int(sys.argv[i + 1])
        except ValueError:
            pass

# Distance interpretation thresholds (calibrated to smoke test: 0.37 = strong match)
CLOSE   = 0.38   # strong semantic match — likely same clinical topic
RELATED = 0.50   # overlapping domain / related area
# > 0.50 = divergent — unique AAFP content


def bar(value: float, max_val: float, width: int = 30) -> str:
    filled = int(round(value / max_val * width))
    return "█" * filled + "░" * (width - filled)


def pct(n, total):
    return f"{n / total * 100:.1f}" if total else "0"


def add_column_if_missing(conn: sqlite3.Connection, table: str, column: str, col_type: str = "TEXT") -> None:
    cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        print(f"  ✓ Added column: {table}.{column}")


def main():
    if not DB_PATH.exists():
        print(f"ERROR: DB not found:\n  {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)

    # ── Ensure score columns exist (safe no-op if already present) ────
    if SAVE:
        add_column_if_missing(conn, "aafp_questions", "ite_nearest_qid", "TEXT")
        add_column_if_missing(conn, "aafp_questions", "ite_nearest_dist", "REAL")
        conn.commit()

    # ── Load AAFP questions + embeddings ──────────────────────────────
    print("Loading AAFP question vectors...")
    new_only_filter = "AND q.ite_nearest_dist IS NULL" if NEW_ONLY else ""
    limit_clause    = f"LIMIT {SAMPLE_N}" if SAMPLE_N else ""
    aafp_rows = conn.execute(f"""
        SELECT v.aafp_qid, v.embedding, q.stem, q.body_system
        FROM aafp_question_vec v
        JOIN aafp_questions q ON v.aafp_qid = q.aafp_qid
        WHERE 1=1 {new_only_filter}
        ORDER BY v.aafp_qid
        {limit_clause}
    """).fetchall()
    print(f"  {len(aafp_rows)} AAFP questions loaded")

    # ── xref membership (linked vs unlinked) ─────────────────────────
    xref_qids = set(
        r[0] for r in conn.execute("SELECT DISTINCT aafp_qid FROM aafp_qid_art_xref").fetchall()
    )

    # ── For each AAFP question: find nearest ITE question ─────────────
    print("Computing nearest ITE match for each AAFP question...")
    results = []  # list of dicts

    for idx, (aafp_qid, embedding, stem, body_system) in enumerate(aafp_rows):
        if (idx + 1) % 200 == 0:
            print(f"  ...{idx + 1}/{len(aafp_rows)}")

        # KNN: nearest 3 ITE questions
        matches = conn.execute("""
            SELECT qid, distance
            FROM question_vec
            WHERE embedding MATCH ?
            AND k = 3
            ORDER BY distance
        """, (embedding,)).fetchall()

        if not matches:
            continue

        nearest_qid, nearest_dist = matches[0]

        # Get ITE question details
        ite_row = conn.execute(
            "SELECT question_text, body_system, exam_year FROM questions WHERE qid = ?",
            (nearest_qid,)
        ).fetchone()

        results.append({
            "aafp_qid":       aafp_qid,
            "aafp_stem":      (stem or "")[:120],
            "aafp_body":      body_system or "—",
            "ite_qid":        nearest_qid,
            "ite_dist":       nearest_dist,
            "ite_stem":       (ite_row[0] or "")[:120] if ite_row else "?",
            "ite_body":       ite_row[1] if ite_row else "?",
            "ite_year":       ite_row[2] if ite_row else "?",
            "has_xref":       aafp_qid in xref_qids,
            "tier":           "close" if nearest_dist < CLOSE else
                              "related" if nearest_dist < RELATED else "unique",
        })

    total = len(results)
    if total == 0:
        print("No results — check that aafp_question_vec and question_vec are populated.")
        conn.close()
        return

    distances = [r["ite_dist"] for r in results]

    # ═══════════════════════════════════════════════════════════════════
    print(f"\n{'═'*64}")
    print(f"  AAFP → ITE VECTOR SIMILARITY ANALYSIS")
    print(f"  {total} AAFP questions  |  nearest ITE match per question")
    print(f"{'═'*64}")

    # ── 1. Distance Distribution ───────────────────────────────────────
    close_n   = sum(1 for r in results if r["tier"] == "close")
    related_n = sum(1 for r in results if r["tier"] == "related")
    unique_n  = sum(1 for r in results if r["tier"] == "unique")

    print(f"\n── Distance Distribution ─────────────────────────────────")
    print(f"  Mean distance:    {statistics.mean(distances):.4f}")
    print(f"  Median distance:  {statistics.median(distances):.4f}")
    print(f"  Min distance:     {min(distances):.4f}  (most similar)")
    print(f"  Max distance:     {max(distances):.4f}  (most unique)")
    print(f"  Stdev:            {statistics.stdev(distances):.4f}")

    print(f"\n  Tier breakdown (dist thresholds: close <{CLOSE}, related <{RELATED})")
    print(f"  Close   (strong ITE match): {close_n:4d}  ({pct(close_n, total)}%)  {bar(close_n, total)}")
    print(f"  Related (overlapping area): {related_n:4d}  ({pct(related_n, total)}%)  {bar(related_n, total)}")
    print(f"  Unique  (AAFP-only terr.):  {unique_n:4d}  ({pct(unique_n, total)}%)  {bar(unique_n, total)}")

    # Histogram buckets
    buckets = [0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.70, 1.0]
    bucket_labels = ["<0.25","0.25-0.30","0.30-0.35","0.35-0.40","0.40-0.45",
                     "0.45-0.50","0.50-0.55","0.55-0.60","0.60-0.70",">0.70"]
    counts = [0] * len(buckets)
    for d in distances:
        for i, b in enumerate(buckets):
            if d < b:
                counts[i] += 1
                break
    print(f"\n  Distance histogram:")
    max_c = max(counts) if counts else 1
    for label, count in zip(bucket_labels, counts):
        print(f"  {label:<12}  {count:4d}  {bar(count, max_c, 25)}")

    # ── 2. Strongest matches ───────────────────────────────────────────
    by_dist = sorted(results, key=lambda r: r["ite_dist"])
    print(f"\n── Top 8 Strongest AAFP ↔ ITE Matches ───────────────────")
    for r in by_dist[:8]:
        print(f"\n  {r['aafp_qid']}  →  {r['ite_qid']}  (dist={r['ite_dist']:.4f})")
        print(f"  AAFP: {r['aafp_stem'][:100]}...")
        print(f"  ITE:  {r['ite_stem'][:100]}...")
        print(f"  Body: AAFP={r['aafp_body']}  ITE={r['ite_body']} ({r['ite_year']})")

    # ── 3. Most Unique AAFP territory ─────────────────────────────────
    print(f"\n── Top 6 AAFP Questions Furthest from ITE ────────────────")
    print(f"  (potential AAFP-specific content not in ITE)")
    for r in by_dist[-6:][::-1]:
        print(f"\n  {r['aafp_qid']}  →  nearest ITE: {r['ite_qid']}  (dist={r['ite_dist']:.4f})")
        print(f"  AAFP: {r['aafp_stem'][:100]}...")
        print(f"  Body: {r['aafp_body']}")

    # ── 4. Body System Breakdown ───────────────────────────────────────
    print(f"\n── Overlap by Body System ────────────────────────────────")
    body_data: dict[str, list[float]] = defaultdict(list)
    for r in results:
        bs = r["aafp_body"].split(",")[0].strip() if r["aafp_body"] != "—" else "Untagged"
        body_data[bs].append(r["ite_dist"])

    print(f"  {'Body System':<28}  {'N':>4}  {'MeanDist':>8}  {'Close%':>7}  Signal")
    print(f"  {'─'*28}  {'─'*4}  {'─'*8}  {'─'*7}  {'─'*20}")
    body_rows = []
    for bs, dists in body_data.items():
        n = len(dists)
        mean_d = statistics.mean(dists)
        close_pct = sum(1 for d in dists if d < CLOSE) / n * 100
        body_rows.append((bs, n, mean_d, close_pct))
    body_rows.sort(key=lambda x: x[2])  # sort by mean distance (closest first)
    for bs, n, mean_d, close_pct in body_rows:
        signal = bar(1 - mean_d, 1.0, 20)  # invert: lower dist = stronger signal
        print(f"  {bs:<28}  {n:>4}  {mean_d:>8.4f}  {close_pct:>6.1f}%  {signal}")

    # ── 5. Linked vs Unlinked articles ────────────────────────────────
    linked   = [r for r in results if r["has_xref"]]
    unlinked = [r for r in results if not r["has_xref"]]
    if linked and unlinked:
        print(f"\n── Article-Linked vs Unlinked Questions ─────────────────")
        print(f"  Linked   ({len(linked):4d} q): mean dist = {statistics.mean(d['ite_dist'] for d in linked):.4f}")
        print(f"  Unlinked ({len(unlinked):4d} q): mean dist = {statistics.mean(d['ite_dist'] for d in unlinked):.4f}")
        print(f"  (Linked questions should score lower — they share article citations with ITE)")

    # ── 6. ITE year distribution of nearest matches ───────────────────
    year_counts = Counter(r["ite_year"] for r in results if r["ite_year"] != "?")
    if year_counts:
        print(f"\n── ITE Year of Nearest Matches ───────────────────────────")
        max_yc = max(year_counts.values())
        for yr in sorted(year_counts):
            c = year_counts[yr]
            print(f"  {yr}  {c:4d}  {bar(c, max_yc, 30)}")

    # ── 7. Persist scores (--save) ────────────────────────────────────
    if SAVE:
        print(f"\n── Saving scores to aafp_questions ──────────────────────")
        write_rows = [(r["ite_qid"], r["ite_dist"], r["aafp_qid"]) for r in results]
        conn.executemany(
            "UPDATE aafp_questions SET ite_nearest_qid = ?, ite_nearest_dist = ? WHERE aafp_qid = ?",
            write_rows
        )
        conn.commit()
        # Coverage check
        total_q  = conn.execute("SELECT COUNT(*) FROM aafp_questions").fetchone()[0]
        filled   = conn.execute(
            "SELECT COUNT(*) FROM aafp_questions WHERE ite_nearest_dist IS NOT NULL"
        ).fetchone()[0]
        print(f"  ite_nearest_dist populated: {filled}/{total_q} ({pct(filled, total_q)}%)")
        print(f"  DB → {DB_PATH}")

    print(f"\n{'═'*64}")
    print(f"  Done. {total} AAFP questions analyzed.")
    conn.close()


if __name__ == "__main__":
    if "--help" in sys.argv:
        print(__doc__)
        sys.exit(0)
    main()
