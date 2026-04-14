#!/usr/bin/env python3
"""
Build intersection centroid vectors (blueprint × body_system) from question embeddings.

Computes centroid embeddings for each blueprint × body_system cell that has >= MIN_QUESTIONS
questions. Uses local numpy computation only — no API calls.

Schema: intersection_centroid_vec
  - blueprint TEXT
  - body_system TEXT
  - embedding BLOB (np.float32 vector, 1536-dim)
  - q_count INTEGER
  - source_bank TEXT ('ite' or 'aafp')
  - model TEXT
  - built_at TEXT (timestamp)
  - PK: (blueprint, body_system, source_bank)

Usage:
  python build_intersection_centroids.py [--db PATH] [--ite-only|--aafp-only] [--min-questions N] [--rebuild]
"""

import argparse
import sqlite3
import struct
from pathlib import Path
from typing import Optional

import numpy as np


# Configuration
MIN_QUESTIONS = 3
EMBED_DIM = 1536


def blob_to_vec(blob: bytes) -> Optional[np.ndarray]:
    """Unpack BLOB bytes to numpy float32 vector."""
    if not blob:
        return None
    try:
        n = len(blob) // 4
        return np.array(struct.unpack(f"{n}f", blob), dtype=np.float32)
    except struct.error:
        return None


def vec_to_blob(vec: np.ndarray) -> bytes:
    """Pack numpy vector to BLOB bytes."""
    return struct.pack(f"{len(vec)}f", *vec.tolist())


def get_db_path() -> Path:
    """Resolve DB path using dynamic path logic."""
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent.parent.parent
    db_path = project_root / "00_database" / "db" / "ite_intelligence.db"
    return db_path


def check_embedding_tables(conn: sqlite3.Connection) -> tuple[bool, bool]:
    """
    Check that question_full_vec and aafp_question_full_vec tables exist and have rows.
    
    Returns: (ite_ready, aafp_ready)
    """
    cursor = conn.cursor()
    
    ite_ready = False
    aafp_ready = False
    
    try:
        cursor.execute("SELECT COUNT(*) FROM question_full_vec")
        ite_count = cursor.fetchone()[0]
        if ite_count > 0:
            ite_ready = True
        else:
            print("❌ ERROR: question_full_vec table exists but is empty.")
    except sqlite3.OperationalError:
        print("❌ ERROR: question_full_vec table does not exist.")
    
    try:
        cursor.execute("SELECT COUNT(*) FROM aafp_question_full_vec")
        aafp_count = cursor.fetchone()[0]
        if aafp_count > 0:
            aafp_ready = True
        else:
            print("❌ ERROR: aafp_question_full_vec table exists but is empty.")
    except sqlite3.OperationalError:
        print("❌ ERROR: aafp_question_full_vec table does not exist.")
    
    if not ite_ready and not aafp_ready:
        print("\n⚠️  Run compute_embeddings.py --rebuild first to populate question_full_vec.")
    
    return ite_ready, aafp_ready


def create_schema(conn: sqlite3.Connection) -> None:
    """Create intersection_centroid_vec table if it doesn't exist."""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS intersection_centroid_vec (
            blueprint   TEXT NOT NULL,
            body_system TEXT NOT NULL,
            embedding   BLOB NOT NULL,
            q_count     INTEGER NOT NULL,
            source_bank TEXT NOT NULL,
            model       TEXT,
            built_at    TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (blueprint, body_system, source_bank)
        )
    """)
    conn.commit()


def rebuild_table(conn: sqlite3.Connection) -> None:
    """Delete existing rows in intersection_centroid_vec."""
    cursor = conn.cursor()
    cursor.execute("DELETE FROM intersection_centroid_vec")
    conn.commit()
    print("✓ Cleared existing intersection_centroid_vec rows")


def compute_ite_centroids(
    conn: sqlite3.Connection, min_questions: int
) -> dict[str, int]:
    """
    Compute centroids for ITE questions grouped by (blueprint, body_system).
    
    Returns: {
        'computed': count of cells computed,
        'skipped': count of cells with < min_questions,
        'skipped_cells': list of (blueprint, body_system, q_count) tuples
    }
    """
    cursor = conn.cursor()
    
    # Get all unique (blueprint, body_system) pairs from ITE questions with embeddings
    cursor.execute("""
        SELECT
            q.blueprint,
            q.body_system,
            COUNT(v.qid) as q_count
        FROM question_full_vec v
        JOIN questions q ON q.qid = v.qid
        WHERE v.embedding IS NOT NULL
        GROUP BY q.blueprint, q.body_system
        ORDER BY q.blueprint, q.body_system
    """)
    
    cells = cursor.fetchall()
    computed = 0
    skipped = 0
    skipped_cells = []
    
    for blueprint, body_system, q_count in cells:
        if q_count < min_questions:
            skipped += 1
            skipped_cells.append((blueprint, body_system, q_count))
            continue
        
        # Fetch all embeddings for this cell
        cursor.execute("""
            SELECT v.embedding
            FROM question_full_vec v
            JOIN questions q ON q.qid = v.qid
            WHERE q.blueprint = ? AND q.body_system = ?
            AND v.embedding IS NOT NULL
        """, (blueprint, body_system))
        
        rows = cursor.fetchall()
        embeddings = []
        for (blob,) in rows:
            vec = blob_to_vec(blob)
            if vec is not None:
                embeddings.append(vec)
        
        if embeddings:
            centroid = np.mean(embeddings, axis=0)
            centroid_blob = vec_to_blob(centroid)
            
            # Insert into intersection_centroid_vec
            cursor.execute("""
                INSERT OR REPLACE INTO intersection_centroid_vec
                (blueprint, body_system, embedding, q_count, source_bank, model)
                VALUES (?, ?, ?, ?, 'ite', 'text-embedding-3-small')
            """, (blueprint, body_system, centroid_blob, q_count))
            
            computed += 1
            print(f"[ITE] {blueprint} × {body_system}: {q_count} Qs → centroid OK")
    
    conn.commit()
    
    return {
        'computed': computed,
        'skipped': skipped,
        'skipped_cells': skipped_cells,
    }


def compute_aafp_centroids(
    conn: sqlite3.Connection, min_questions: int
) -> dict[str, int]:
    """
    Compute centroids for AAFP questions grouped by (blueprint, body_system).
    
    Returns: {
        'computed': count of cells computed,
        'skipped': count of cells with < min_questions,
        'skipped_cells': list of (blueprint, body_system, q_count) tuples
    }
    """
    cursor = conn.cursor()
    
    # Get all unique (blueprint, body_system) pairs from AAFP questions with embeddings
    cursor.execute("""
        SELECT
            q.blueprint,
            q.body_system,
            COUNT(v.aafp_qid) as q_count
        FROM aafp_question_full_vec v
        JOIN aafp_questions q ON q.aafp_qid = v.aafp_qid
        WHERE v.embedding IS NOT NULL
        GROUP BY q.blueprint, q.body_system
        ORDER BY q.blueprint, q.body_system
    """)
    
    cells = cursor.fetchall()
    computed = 0
    skipped = 0
    skipped_cells = []
    
    for blueprint, body_system, q_count in cells:
        if q_count < min_questions:
            skipped += 1
            skipped_cells.append((blueprint, body_system, q_count))
            continue
        
        # Fetch all embeddings for this cell
        cursor.execute("""
            SELECT v.embedding
            FROM aafp_question_full_vec v
            JOIN aafp_questions q ON q.aafp_qid = v.aafp_qid
            WHERE q.blueprint = ? AND q.body_system = ?
            AND v.embedding IS NOT NULL
        """, (blueprint, body_system))
        
        rows = cursor.fetchall()
        embeddings = []
        for (blob,) in rows:
            vec = blob_to_vec(blob)
            if vec is not None:
                embeddings.append(vec)
        
        if embeddings:
            centroid = np.mean(embeddings, axis=0)
            centroid_blob = vec_to_blob(centroid)
            
            # Insert into intersection_centroid_vec
            cursor.execute("""
                INSERT OR REPLACE INTO intersection_centroid_vec
                (blueprint, body_system, embedding, q_count, source_bank, model)
                VALUES (?, ?, ?, ?, 'aafp', 'text-embedding-3-small')
            """, (blueprint, body_system, centroid_blob, q_count))
            
            computed += 1
            print(f"[AAFP] {blueprint} × {body_system}: {q_count} Qs → centroid OK")
    
    conn.commit()
    
    return {
        'computed': computed,
        'skipped': skipped,
        'skipped_cells': skipped_cells,
    }


def print_summary(
    ite_results: Optional[dict] = None,
    aafp_results: Optional[dict] = None,
) -> None:
    """Print summary of computation."""
    print("\n" + "=" * 70)
    print("INTERSECTION CENTROID COMPUTATION SUMMARY")
    print("=" * 70)
    
    if ite_results:
        print(f"\n[ITE]")
        print(f"  Cells computed: {ite_results['computed']}")
        print(f"  Cells skipped:  {ite_results['skipped']} (< MIN_QUESTIONS)")
        if ite_results['skipped_cells']:
            print(f"\n  Skipped cells:")
            for bp, bs, qc in ite_results['skipped_cells'][:10]:
                print(f"    - {bp} × {bs}: {qc} questions")
            if len(ite_results['skipped_cells']) > 10:
                print(f"    ... and {len(ite_results['skipped_cells']) - 10} more")
    
    if aafp_results:
        print(f"\n[AAFP]")
        print(f"  Cells computed: {aafp_results['computed']}")
        print(f"  Cells skipped:  {aafp_results['skipped']} (< MIN_QUESTIONS)")
        if aafp_results['skipped_cells']:
            print(f"\n  Skipped cells:")
            for bp, bs, qc in aafp_results['skipped_cells'][:10]:
                print(f"    - {bp} × {bs}: {qc} questions")
            if len(aafp_results['skipped_cells']) > 10:
                print(f"    ... and {len(aafp_results['skipped_cells']) - 10} more")
    
    print("\n" + "=" * 70)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Build intersection centroid vectors from question embeddings."
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=None,
        help="Path to ite_intelligence.db (default: auto-resolved from script location)",
    )
    parser.add_argument(
        "--ite-only",
        action="store_true",
        help="Compute ITE centroids only",
    )
    parser.add_argument(
        "--aafp-only",
        action="store_true",
        help="Compute AAFP centroids only",
    )
    parser.add_argument(
        "--min-questions",
        type=int,
        default=MIN_QUESTIONS,
        help=f"Minimum questions per cell to compute centroid (default: {MIN_QUESTIONS})",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Delete existing rows before recomputing",
    )
    
    args = parser.parse_args()
    
    # Resolve DB path
    db_path = args.db or get_db_path()
    if not db_path.exists():
        print(f"❌ ERROR: Database not found at {db_path}")
        return
    
    print(f"Database: {db_path}")
    print(f"MIN_QUESTIONS: {args.min_questions}")
    
    # Connect
    conn = sqlite3.connect(db_path)
    try:
        # Check embedding tables
        ite_ready, aafp_ready = check_embedding_tables(conn)
        if not ite_ready and not aafp_ready:
            print("\n⚠️  Cannot proceed without embeddings. Exiting.")
            return
        
        # Create schema
        create_schema(conn)
        
        # Rebuild if requested
        if args.rebuild:
            rebuild_table(conn)
        
        # Compute centroids
        ite_results = None
        aafp_results = None
        
        if not args.aafp_only and ite_ready:
            print("\n--- Computing ITE centroids ---")
            ite_results = compute_ite_centroids(conn, args.min_questions)
        
        if not args.ite_only and aafp_ready:
            print("\n--- Computing AAFP centroids ---")
            aafp_results = compute_aafp_centroids(conn, args.min_questions)
        
        # Print summary
        print_summary(ite_results, aafp_results)
        
    finally:
        conn.close()


if __name__ == "__main__":
    main()
