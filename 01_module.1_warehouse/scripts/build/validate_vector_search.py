"""
validate_vector_search.py — Recall@K Validation for Vector Embeddings
======================================================================
Tests how well vector similarity search recovers known question-reference pairs.

For each of the 2,069 known pairs in question_ref_pairs, embeds the question
and finds the top-K nearest articles by vector similarity. Reports recall at
various K values and recommends a distance threshold.

Usage:
    python validate_vector_search.py              # full validation
    python validate_vector_search.py --k 20       # test up to recall@20
    python validate_vector_search.py --verbose     # show every miss

Requires:
    pip install sqlite-vec
    Must run compute_embeddings.py first.
"""

import sqlite3
import struct
import json
import sys
import argparse
from pathlib import Path
from collections import defaultdict

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
DB_PATH   = Path(__file__).parent.parent / "db" / "ite_intelligence.db"
EMBED_DIM = 1536

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate(conn, max_k=10, verbose=False):
    """
    For each known question-reference pair, check if vector search
    would have found the correct article in the top-K results.
    """
    # Load all known pairs
    pairs = conn.execute("""
        SELECT p.qid, p.clean_ref, q.question_text, q.body_system
        FROM question_ref_pairs p
        JOIN questions q ON p.qid = q.qid
        ORDER BY p.qid
    """).fetchall()

    print(f"Testing {len(pairs)} known question-reference pairs")
    print(f"Recall targets: @1, @3, @5, @10" + (f", @{max_k}" if max_k > 10 else ""))
    print(f"{'='*60}\n")

    # Build article_id → clean_ref lookup
    art_lookup = {}
    rows = conn.execute("SELECT article_id, clean_ref FROM articles").fetchall()
    for r in rows:
        art_lookup[r["article_id"]] = r["clean_ref"]

    # Reverse lookup: clean_ref → article_id
    ref_to_art = {v: k for k, v in art_lookup.items()}

    # Track recall
    k_values = sorted(set([1, 3, 5, 10, max_k]))
    recall_at = {k: 0 for k in k_values}
    distances_of_correct = []
    misses = []
    skipped = 0
    tested = 0

    # Deduplicate: some questions map to multiple articles
    # Test each unique QID once with all its correct articles
    qid_refs = defaultdict(set)
    for p in pairs:
        qid_refs[p["qid"]].add(p["clean_ref"])

    for qid, correct_refs in qid_refs.items():
        # Get question embedding
        q_emb = conn.execute(
            "SELECT embedding FROM question_vec WHERE qid=?", (qid,)
        ).fetchone()

        if not q_emb:
            skipped += 1
            continue

        # Find top-K nearest articles
        results = conn.execute(f"""
            SELECT article_id, distance
            FROM article_vec
            WHERE embedding MATCH ?
            AND k = {max_k}
            ORDER BY distance
        """, (q_emb["embedding"],)).fetchall()

        ranked_refs = []
        ranked_distances = []
        for r in results:
            ref = art_lookup.get(r["article_id"])
            if ref:
                ranked_refs.append(ref)
                ranked_distances.append(r["distance"])

        tested += 1

        # Check if ANY correct ref appears in top-K
        found = False
        found_at = None
        found_dist = None
        for idx, ref in enumerate(ranked_refs):
            if ref in correct_refs:
                found = True
                found_at = idx + 1  # 1-indexed rank
                found_dist = ranked_distances[idx]
                break

        if found:
            distances_of_correct.append(found_dist)
            for k in k_values:
                if found_at <= k:
                    recall_at[k] += 1
        else:
            # Track misses for analysis
            q_row = conn.execute(
                "SELECT body_system, subcategory FROM questions WHERE qid=?", (qid,)
            ).fetchone()
            misses.append({
                "qid": qid,
                "correct_refs": list(correct_refs),
                "body_system": q_row["body_system"] if q_row else "?",
                "top_3": ranked_refs[:3]
            })

    # --------------- RESULTS ---------------
    print(f"{'='*60}")
    print(f"RECALL RESULTS")
    print(f"{'='*60}")
    print(f"  Pairs tested:  {tested} unique questions")
    print(f"  Skipped:       {skipped} (no embedding)")
    print()

    for k in k_values:
        pct = recall_at[k] / tested * 100 if tested > 0 else 0
        bar = "█" * int(pct / 2) + "░" * (50 - int(pct / 2))
        print(f"  Recall@{k:<3d}  {recall_at[k]:>5d}/{tested}  = {pct:5.1f}%  {bar}")

    # Distance distribution
    if distances_of_correct:
        sorted_d = sorted(distances_of_correct)
        n = len(sorted_d)
        p10 = sorted_d[int(n * 0.10)]
        p25 = sorted_d[int(n * 0.25)]
        p50 = sorted_d[int(n * 0.50)]
        p75 = sorted_d[int(n * 0.75)]
        p90 = sorted_d[int(n * 0.90)]

        print(f"\n{'='*60}")
        print(f"DISTANCE DISTRIBUTION (correct matches)")
        print(f"{'='*60}")
        print(f"  10th percentile: {p10:.4f}")
        print(f"  25th percentile: {p25:.4f}")
        print(f"  Median:          {p50:.4f}")
        print(f"  75th percentile: {p75:.4f}")
        print(f"  90th percentile: {p90:.4f}")
        print(f"\n  Recommended VECTOR_THRESHOLD: {p75:.4f}")
        print(f"  (captures ~75% of known correct matches)")

    # Miss analysis
    if misses:
        print(f"\n{'='*60}")
        print(f"MISS ANALYSIS ({len(misses)} questions not found in top-{max_k})")
        print(f"{'='*60}")

        # By body system
        miss_by_system = defaultdict(int)
        for m in misses:
            miss_by_system[m["body_system"]] += 1

        print(f"\n  Misses by body system:")
        for sys_name, count in sorted(miss_by_system.items(), key=lambda x: -x[1])[:10]:
            print(f"    {sys_name}: {count}")

        if verbose:
            print(f"\n  Detailed misses (first 20):")
            for m in misses[:20]:
                print(f"    {m['qid']} ({m['body_system']})")
                for ref in m["correct_refs"]:
                    print(f"      Expected: {ref[:80]}...")
                for ref in m["top_3"]:
                    print(f"      Got:      {ref[:80]}...")
                print()

    return recall_at, tested


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Validate vector search recall on known pairs")
    parser.add_argument("--k", type=int, default=10, help="Max K for recall@K (default: 10)")
    parser.add_argument("--verbose", action="store_true", help="Show individual misses")
    parser.add_argument("--db", type=str, default=str(DB_PATH), help="Path to SQLite DB")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"ERROR: Database not found at {db_path}")
        sys.exit(1)

    print(f"ITE Intelligence — Vector Search Validation")
    print(f"{'='*60}")
    print(f"Database:  {db_path}")
    print(f"Max K:     {args.k}")
    print(f"{'='*60}")

    import sqlite_vec
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)

    # Check embeddings exist
    try:
        art_count = conn.execute("SELECT COUNT(*) FROM article_vec").fetchone()[0]
        q_count   = conn.execute("SELECT COUNT(*) FROM question_vec").fetchone()[0]
    except Exception:
        print("ERROR: Vector tables not found. Run compute_embeddings.py first.")
        sys.exit(1)

    print(f"Embeddings: {art_count} articles, {q_count} questions")

    if art_count == 0 or q_count == 0:
        print("ERROR: No embeddings found. Run compute_embeddings.py first.")
        sys.exit(1)

    recall_at, tested = validate(conn, max_k=args.k, verbose=args.verbose)

    conn.close()
    print(f"\nDone.")


if __name__ == "__main__":
    main()
