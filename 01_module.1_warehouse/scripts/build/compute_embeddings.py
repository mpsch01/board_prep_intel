"""
compute_embeddings.py — Upgrade #1: sqlite-vec + OpenAI Embeddings
==================================================================
Computes vector embeddings for all articles and questions in ite_intelligence.db.
Creates two virtual tables (article_vec, question_vec) for semantic similarity search.

Usage:
    python compute_embeddings.py                 # embed everything
    python compute_embeddings.py --new-only      # incremental: only items not yet embedded
    python compute_embeddings.py --articles-only # just articles
    python compute_embeddings.py --questions-only # just questions
    python compute_embeddings.py --dry-run       # show what would be embedded, no API calls

Requires:
    pip install sqlite-vec openai
    Environment variable: OPENAI_API_KEY

Cost estimate: ~$0.015 for full corpus (1,936 articles + 1,629 questions)
             ~$0.006 for gap-fill pass (--new-only: ~979 items)
Runtime: ~60 seconds full, ~20 seconds gap-fill
"""

import sqlite3
import json
import sys
import os
import time
import argparse
from pathlib import Path

# ---------------------------------------------------------------------------
# CONFIG — tune these knobs
# ---------------------------------------------------------------------------
SCRIPT_DIR    = Path(__file__).resolve().parent
PROJECT_ROOT  = SCRIPT_DIR.parent.parent.parent          # build/ -> scripts/ -> M1/ -> PROJECT_ROOT
DB_PATH       = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"
EMBED_MODEL   = "text-embedding-3-small"   # 1536 dimensions, $0.02/M tokens
EMBED_DIM     = 1536
BATCH_SIZE    = 100                        # OpenAI supports up to 2048 per call
MAX_TOKENS    = 8191                       # model context limit per input

# ---------------------------------------------------------------------------
# Text builders — deterministic representations for embedding
# ---------------------------------------------------------------------------

def build_article_text(row: dict) -> str:
    """
    Build a text representation of an article for embedding.
    Combines title, citation, categories, and tier into a single string.
    """
    parts = []

    # Title (parsed from clean_ref)
    title = (row.get("title") or "").strip()
    if title:
        parts.append(title)

    # Full citation reference
    clean_ref = (row.get("clean_ref") or "").strip()
    if clean_ref and clean_ref != title:
        parts.append(clean_ref)

    # Categories (body systems)
    categories = (row.get("categories") or "").strip()
    if categories:
        parts.append(f"Categories: {categories}")

    # Blueprint categories
    blueprint = (row.get("blueprint_cats") or "").strip()
    if blueprint:
        parts.append(f"Blueprint: {blueprint}")

    # Tier
    tier = (row.get("tier") or "").strip()
    if tier:
        parts.append(f"Tier: {tier}")

    text = " | ".join(parts)

    # Truncate to stay within token limits (~4 chars per token)
    max_chars = MAX_TOKENS * 3  # conservative estimate
    if len(text) > max_chars:
        text = text[:max_chars]

    return text


def build_question_text(row: dict) -> str:
    """
    Build a text representation of a question for embedding.
    Combines stem, correct answer, body system, and concept tags.
    """
    parts = []

    # Question stem
    stem = (row.get("question_text") or "").strip()
    if stem:
        parts.append(stem[:600])  # cap stem length

    # Correct answer text
    correct = (row.get("correct_text") or "").strip()
    if correct:
        parts.append(f"Answer: {correct}")

    # Body system + subcategory
    body = (row.get("body_system") or "").strip()
    subcat = (row.get("subcategory") or "").strip()
    if body or subcat:
        parts.append(f"System: {body} / {subcat}")

    # Concept tags (structured clinical concepts)
    tags_raw = (row.get("concept_tags") or "").strip()
    if tags_raw:
        try:
            tags = json.loads(tags_raw)
            # Include concept summary (most valuable for embedding)
            summary = tags.get("concept_summary", "")
            if summary:
                parts.append(f"Concept: {summary}")
            # Include diagnoses
            diagnoses = tags.get("diagnoses", [])
            if diagnoses:
                parts.append(f"Diagnoses: {', '.join(diagnoses)}")
            # Include drugs
            drugs = tags.get("drugs", [])
            if drugs:
                parts.append(f"Drugs: {', '.join(drugs)}")
        except json.JSONDecodeError:
            pass

    text = " | ".join(parts)

    max_chars = MAX_TOKENS * 3
    if len(text) > max_chars:
        text = text[:max_chars]

    return text


# ---------------------------------------------------------------------------
# Embedding computation
# ---------------------------------------------------------------------------

def get_embeddings(client, texts: list[str]) -> list[list[float]]:
    """Call OpenAI embeddings API for a batch of texts."""
    resp = client.embeddings.create(model=EMBED_MODEL, input=texts)
    return [item.embedding for item in resp.data]


def create_vec_tables(conn):
    """Create virtual tables for vector search (idempotent)."""
    conn.execute(f"""
        CREATE VIRTUAL TABLE IF NOT EXISTS article_vec USING vec0(
            article_id TEXT PRIMARY KEY,
            embedding  float[{EMBED_DIM}]
        )
    """)
    conn.execute(f"""
        CREATE VIRTUAL TABLE IF NOT EXISTS question_vec USING vec0(
            qid        TEXT PRIMARY KEY,
            embedding  float[{EMBED_DIM}]
        )
    """)
    conn.commit()


def embed_articles(conn, client, dry_run=False, new_only=False):
    """Compute and store embeddings for all articles (or only new ones)."""
    if new_only:
        articles = conn.execute("""
            SELECT a.article_id, a.clean_ref, a.title, a.categories, a.blueprint_cats, a.tier
            FROM articles a
            LEFT JOIN article_vec v ON a.article_id = v.article_id
            WHERE v.article_id IS NULL
            ORDER BY a.article_id
        """).fetchall()
        print(f"  [new-only mode] {len(articles)} articles without embeddings")
    else:
        articles = conn.execute("""
            SELECT article_id, clean_ref, title, categories, blueprint_cats, tier
            FROM articles
            ORDER BY article_id
        """).fetchall()

    print(f"\n{'='*60}")
    print(f"ARTICLES: {len(articles)} to embed")
    print(f"{'='*60}")

    if dry_run:
        for a in articles[:3]:
            text = build_article_text(dict(a))
            print(f"  {a['article_id']}: {text[:120]}...")
        print(f"  ... and {len(articles)-3} more")
        return 0, 0

    total_tokens = 0
    embedded = 0

    for i in range(0, len(articles), BATCH_SIZE):
        batch = articles[i:i+BATCH_SIZE]
        texts = [build_article_text(dict(a)) for a in batch]
        ids   = [a["article_id"] for a in batch]

        embeddings = get_embeddings(client, texts)
        total_tokens += sum(len(t.split()) * 1.3 for t in texts)  # rough estimate

        for art_id, emb in zip(ids, embeddings):
            # sqlite-vec expects a list serialized as bytes
            import struct
            blob = struct.pack(f"{len(emb)}f", *emb)
            conn.execute(
                "INSERT OR REPLACE INTO article_vec(article_id, embedding) VALUES (?, ?)",
                (art_id, blob)
            )

        embedded += len(batch)
        print(f"  Batch {i//BATCH_SIZE + 1}: embedded {len(batch)} articles "
              f"({embedded}/{len(articles)})")

    conn.commit()
    return embedded, int(total_tokens)


def embed_questions(conn, client, dry_run=False, new_only=False):
    """Compute and store embeddings for all questions (or only new ones)."""
    if new_only:
        questions = conn.execute("""
            SELECT q.qid, q.question_text, q.correct_text, q.body_system, q.subcategory, q.concept_tags
            FROM questions q
            LEFT JOIN question_vec v ON q.qid = v.qid
            WHERE v.qid IS NULL
            ORDER BY q.qid
        """).fetchall()
        print(f"  [new-only mode] {len(questions)} questions without embeddings")
    else:
        questions = conn.execute("""
            SELECT qid, question_text, correct_text, body_system, subcategory, concept_tags
            FROM questions
            ORDER BY qid
        """).fetchall()

    print(f"\n{'='*60}")
    print(f"QUESTIONS: {len(questions)} to embed")
    print(f"{'='*60}")

    if dry_run:
        for q in questions[:3]:
            text = build_question_text(dict(q))
            print(f"  {q['qid']}: {text[:120]}...")
        print(f"  ... and {len(questions)-3} more")
        return 0, 0

    total_tokens = 0
    embedded = 0

    for i in range(0, len(questions), BATCH_SIZE):
        batch = questions[i:i+BATCH_SIZE]
        texts = [build_question_text(dict(q)) for q in batch]
        qids  = [q["qid"] for q in batch]

        embeddings = get_embeddings(client, texts)
        total_tokens += sum(len(t.split()) * 1.3 for t in texts)

        for qid, emb in zip(qids, embeddings):
            import struct
            blob = struct.pack(f"{len(emb)}f", *emb)
            conn.execute(
                "INSERT OR REPLACE INTO question_vec(qid, embedding) VALUES (?, ?)",
                (qid, blob)
            )

        embedded += len(batch)
        print(f"  Batch {i//BATCH_SIZE + 1}: embedded {len(batch)} questions "
              f"({embedded}/{len(questions)})")

    conn.commit()
    return embedded, int(total_tokens)


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def verify(conn):
    """Quick sanity checks after embedding."""
    print(f"\n{'='*60}")
    print("VERIFICATION")
    print(f"{'='*60}")

    art_count = conn.execute("SELECT COUNT(*) FROM article_vec").fetchone()[0]
    q_count   = conn.execute("SELECT COUNT(*) FROM question_vec").fetchone()[0]

    art_total = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    q_total   = conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]

    print(f"  article_vec: {art_count}/{art_total} articles embedded")
    print(f"  question_vec: {q_count}/{q_total} questions embedded")

    # Quick similarity test: find the closest article to the first question
    first_q = conn.execute("SELECT qid, embedding FROM question_vec LIMIT 1").fetchone()
    if first_q:
        results = conn.execute("""
            SELECT article_id, distance
            FROM article_vec
            WHERE embedding MATCH ?
            AND k = 3
            ORDER BY distance
        """, (first_q[1],)).fetchall()

        if results:
            print(f"\n  Smoke test — nearest articles to {first_q[0]}:")
            for r in results:
                # Look up the article title
                art = conn.execute(
                    "SELECT title, tier FROM articles WHERE article_id=?",
                    (r[0],)
                ).fetchone()
                title = (art[0] or "")[:80] if art else "?"
                print(f"    {r[0]} (dist={r[1]:.4f}, tier={art[1] if art else '?'}): {title}")

    # Coverage check
    if art_count < art_total:
        print(f"\n  WARNING: {art_total - art_count} articles missing embeddings!")
    if q_count < q_total:
        print(f"\n  WARNING: {q_total - q_count} questions missing embeddings!")

    if art_count == art_total and q_count == q_total:
        print(f"\n  ALL CLEAR — 100% embedding coverage")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Compute vector embeddings for ITE Intelligence DB")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be embedded, no API calls")
    parser.add_argument("--new-only", action="store_true",
                        help="Only embed articles/questions not yet in vec tables (incremental update)")
    parser.add_argument("--articles-only", action="store_true", help="Only embed articles")
    parser.add_argument("--questions-only", action="store_true", help="Only embed questions")
    parser.add_argument("--db", type=str, default=str(DB_PATH), help="Path to SQLite DB")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"ERROR: Database not found at {db_path}")
        sys.exit(1)

    print(f"ITE Intelligence — Vector Embedding Pipeline")
    print(f"{'='*60}")
    print(f"Database:  {db_path}")
    print(f"Model:     {EMBED_MODEL} ({EMBED_DIM} dimensions)")
    print(f"Batch:     {BATCH_SIZE} items per API call")
    print(f"Dry run:   {args.dry_run}")
    print(f"New only:  {args.new_only}")
    print(f"{'='*60}")

    # Connect to DB with sqlite-vec
    import sqlite_vec
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)

    # Create virtual tables
    create_vec_tables(conn)

    # Initialize OpenAI client
    client = None
    if not args.dry_run:
        from openai import OpenAI
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            print("ERROR: OPENAI_API_KEY not set in environment.")
            sys.exit(1)
        client = OpenAI(api_key=api_key)
        print(f"OpenAI:    connected")

    start = time.time()
    total_embedded = 0
    total_tokens = 0

    # Embed articles
    if not args.questions_only:
        n, t = embed_articles(conn, client, dry_run=args.dry_run, new_only=args.new_only)
        total_embedded += n
        total_tokens += t

    # Embed questions
    if not args.articles_only:
        n, t = embed_questions(conn, client, dry_run=args.dry_run, new_only=args.new_only)
        total_embedded += n
        total_tokens += t

    elapsed = time.time() - start

    if not args.dry_run:
        verify(conn)

    # Summary
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"  Items embedded: {total_embedded}")
    print(f"  Est. tokens:    {total_tokens:,}")
    est_cost = total_tokens * 0.02 / 1_000_000
    print(f"  Est. cost:      ${est_cost:.4f}")
    print(f"  Elapsed:        {elapsed:.1f}s")

    conn.close()
    print(f"\nDone.")


if __name__ == "__main__":
    main()
