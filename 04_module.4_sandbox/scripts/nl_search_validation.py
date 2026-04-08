#!/usr/bin/env python3
"""
nl_search_validation.py — Validate the NL search pipeline before building the frontend.

"The One Thing to Do First" — per the architecture plan.

Tests the full stack locally:
    1. Embeds a query string using OpenAI text-embedding-3-small
    2. Runs a pgvector cosine similarity search against Supabase question_icd10_vec
    3. Fetches full question rows for the matched QIDs
    4. Surfaces linked articles via qid_art_xref
    5. Prints results and performance metrics

Usage:
    python nl_search_validation.py "abdominal pain acute and chronic adults and peds" --count 15
    python nl_search_validation.py "hypertension management" --count 10 --bank ITE

Environment variables (set in .env or shell):
    SUPABASE_URL
    SUPABASE_SERVICE_KEY     (or SUPABASE_ANON_KEY for read-only)
    OPENAI_API_KEY

Requirements:
    pip install openai supabase python-dotenv
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent

load_dotenv(PROJECT_ROOT / ".env")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "") or os.environ.get("SUPABASE_ANON_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY (or SUPABASE_ANON_KEY) must be set.")
    sys.exit(1)

if not OPENAI_API_KEY:
    print("ERROR: OPENAI_API_KEY must be set.")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Step 1: Embed the query
# ---------------------------------------------------------------------------
def embed_query(query: str) -> list[float]:
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)
    t0 = time.time()
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=query,
    )
    elapsed = (time.time() - t0) * 1000
    embedding = response.data[0].embedding
    print(f"  Embedding: {len(embedding)}d vector in {elapsed:.0f}ms")
    return embedding


# ---------------------------------------------------------------------------
# Step 2: Vector search via Supabase RPC
# ---------------------------------------------------------------------------
def vector_search(
    embedding: list[float],
    count: int,
    source_bank: str | None,
) -> list[dict]:
    from supabase import create_client
    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    t0 = time.time()
    result = client.rpc(
        "search_questions_by_embedding",
        {
            "query_embedding": embedding,
            "source_bank_filter": source_bank,
            "match_count": count,
        },
    ).execute()
    elapsed = (time.time() - t0) * 1000
    matches = result.data or []
    print(f"  Vector search: {len(matches)} matches in {elapsed:.0f}ms")
    return matches


# ---------------------------------------------------------------------------
# Step 3 + 4: Fetch questions and linked articles
# ---------------------------------------------------------------------------
def fetch_questions_and_articles(
    matches: list[dict],
) -> tuple[list[dict], list[dict]]:
    from supabase import create_client
    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    qids = [m["qid"] for m in matches]
    ite_qids = [q for q in qids if q.startswith("QID-")]
    aafp_qids = [q for q in qids if q.startswith("AAFP-")]

    questions = []

    if ite_qids:
        rows = client.table("questions").select(
            "qid, exam_year, question_text, correct_answer, blueprint, body_system_merged, concept_tags"
        ).in_("qid", ite_qids).execute().data or []
        questions.extend(rows)

    if aafp_qids:
        rows = client.table("aafp_questions").select(
            "aafp_qid, stem, correct_letter, blueprint, body_system, concept_tags"
        ).in_("aafp_qid", aafp_qids).execute().data or []
        for r in rows:
            r["qid"] = r.pop("aafp_qid")
            r["question_text"] = r.pop("stem", "")
            r["correct_answer"] = r.pop("correct_letter", "")
        questions.extend(rows)

    # Build ranked order
    qid_to_q = {q["qid"]: q for q in questions}
    ranked = [qid_to_q[m["qid"]] for m in matches if m["qid"] in qid_to_q]

    # Collect linked article IDs
    article_ids: set[str] = set()
    if ite_qids:
        xref = client.table("qid_art_xref").select("article_id").in_("qid", ite_qids).execute().data or []
        article_ids.update(r["article_id"] for r in xref)
    if aafp_qids:
        xref = client.table("aafp_qid_art_xref").select("article_id").in_("aafp_qid", aafp_qids).execute().data or []
        article_ids.update(r["article_id"] for r in xref)

    articles = []
    if article_ids:
        articles = client.table("articles").select(
            "article_id, canonical_filename, tier, blueprint, body_system, citation_count, clean_ref"
        ).in_("article_id", list(article_ids)).gt("citation_count", 0).neq("source_type", "stub").execute().data or []

    return ranked, articles


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
def print_results(
    query: str,
    matches: list[dict],
    questions: list[dict],
    articles: list[dict],
) -> None:
    print()
    print("=" * 70)
    print(f"Query: \"{query}\"")
    print("=" * 70)

    print(f"\n{'─'*70}")
    print(f"QUESTIONS ({len(questions)})")
    print(f"{'─'*70}")
    for i, q in enumerate(questions, 1):
        similarity = next((m["similarity"] for m in matches if m["qid"] == q["qid"]), 0)
        bank = "ITE" if q["qid"].startswith("QID-") else "AAFP"
        year = f" {q.get('exam_year', '')}" if bank == "ITE" else ""
        print(f"\n  {i:>2}. [{q['qid']}] {bank}{year}  sim={similarity:.4f}")
        print(f"      Blueprint: {q.get('blueprint', '—')}  |  Body System: {q.get('body_system_merged', q.get('body_system', '—'))}")
        stem = q.get("question_text", "")[:140]
        print(f"      {stem}{'…' if len(q.get('question_text','')) > 140 else ''}")

    print(f"\n{'─'*70}")
    print(f"ARTICLES ({len(articles)})")
    print(f"{'─'*70}")
    for a in sorted(articles, key=lambda x: -x.get("citation_count", 0)):
        print(f"  [{a['article_id']}] {a['tier']:<12}  {a['citation_count']} citations")
        print(f"      {a.get('canonical_filename', a.get('clean_ref', ''))[:80]}")

    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="NL search validation script")
    parser.add_argument("query", help="Natural language search query")
    parser.add_argument("--count", type=int, default=15, help="Number of questions to retrieve")
    parser.add_argument("--bank", choices=["ITE", "AAFP"], default=None, help="Restrict to one question bank")
    args = parser.parse_args()

    print(f"\nValidating NL search pipeline…")
    print(f"  Query:   \"{args.query}\"")
    print(f"  Count:   {args.count}")
    print(f"  Bank:    {args.bank or 'both'}")
    print()

    t_total = time.time()

    print("Step 1: Embed query")
    embedding = embed_query(args.query)

    print("Step 2: Vector search")
    matches = vector_search(embedding, args.count, args.bank)

    if not matches:
        print("\nNo matches found. The vector table may be empty — run vector_sync.py first.")
        sys.exit(0)

    print("Step 3+4: Fetch questions and articles")
    questions, articles = fetch_questions_and_articles(matches)

    total_ms = (time.time() - t_total) * 1000
    print(f"\nTotal pipeline: {total_ms:.0f}ms")

    print_results(args.query, matches, questions, articles)

    # Quality check
    if len(questions) < args.count * 0.8:
        print(f"⚠ WARNING: Only {len(questions)} of {args.count} requested questions returned.")
        print("  This may indicate QID-to-embedding coverage gaps in question_icd10_vec.")
    else:
        print(f"✓ Search pipeline validated.  {len(questions)} questions + {len(articles)} articles returned.")

    if total_ms > 3000:
        print(f"⚠ WARNING: Total latency {total_ms:.0f}ms is high — check pgvector index (ivfflat probes).")
    else:
        print(f"✓ Latency {total_ms:.0f}ms — within acceptable range for server-side API route.")


if __name__ == "__main__":
    main()
