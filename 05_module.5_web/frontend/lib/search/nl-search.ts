/**
 * nl-search.ts — Natural Language search for questions and articles.
 *
 * Flow:
 *  1. Send user query to OpenAI → get 1536-dim embedding
 *  2. Call Supabase RPC search_questions_by_embedding → ranked QIDs
 *  3. Fetch full question rows for those QIDs
 *  4. Collect linked article_ids via qid_art_xref
 *  5. Return questions + articles together
 *
 * This module is server-side only (uses OPENAI_API_KEY).
 * Called from the /api/search Route Handler.
 */

import OpenAI from "openai";
import { createClient } from "@/lib/supabase/server";
import type { Article, Question, AafpQuestion } from "@/lib/supabase/types";

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

export type SearchResult = {
  questions: (Question | AafpQuestion)[];
  articles: Article[];
  queryEmbeddingMs: number;
  searchMs: number;
};

export type SearchOptions = {
  count?: number;           // default 15
  sourceBank?: "ITE" | "AAFP";  // default: both
};

/**
 * Embed a query string using OpenAI text-embedding-3-small.
 * Same model used to build question_icd10_vec and article_icd10_vec.
 */
async function embedQuery(query: string): Promise<number[]> {
  const response = await openai.embeddings.create({
    model: "text-embedding-3-small",
    input: query,
  });
  return response.data[0].embedding;
}

/**
 * Main NL search function.
 */
export async function nlSearch(
  query: string,
  options: SearchOptions = {}
): Promise<SearchResult> {
  const { count = 15, sourceBank } = options;

  // ── Step 1: Embed the query ──────────────────────────────────────────────
  const embedStart = Date.now();
  const embedding = await embedQuery(query);
  const queryEmbeddingMs = Date.now() - embedStart;

  // ── Step 2: Vector search ────────────────────────────────────────────────
  const searchStart = Date.now();
  const supabase = await createClient();

  const { data: vectorMatches, error: vecError } = await supabase.rpc(
    "search_questions_by_embedding",
    {
      query_embedding: embedding,
      source_bank_filter: sourceBank ?? null,
      match_count: count,
    }
  );

  if (vecError) throw new Error(`Vector search failed: ${vecError.message}`);

  const matchedQids = (vectorMatches ?? []).map(
    (m: { qid: string }) => m.qid
  );

  if (matchedQids.length === 0) {
    return { questions: [], articles: [], queryEmbeddingMs, searchMs: Date.now() - searchStart };
  }

  // ── Step 3: Partition QIDs by bank and fetch question rows ───────────────
  const iteQids = matchedQids.filter((q: string) => q.startsWith("QID-"));
  const aafpQids = matchedQids.filter((q: string) => q.startsWith("AAFP-"));

  const [iteResult, aafpResult] = await Promise.all([
    iteQids.length > 0
      ? supabase
          .from("questions")
          .select(
            "qid, exam_year, question_text, choices, correct_answer, explanation, body_system_merged, blueprint, concept_tags"
          )
          .in("qid", iteQids)
      : Promise.resolve({ data: [] }),
    aafpQids.length > 0
      ? supabase
          .from("aafp_questions")
          .select(
            "aafp_qid, stem, choices, correct_letter, correct_text, explanation, body_system, blueprint, concept_tags"
          )
          .in("aafp_qid", aafpQids)
      : Promise.resolve({ data: [] }),
  ]);

  const iteQuestions: Question[] = iteResult.data ?? [];
  const aafpQuestions: AafpQuestion[] = aafpResult.data ?? [];

  // Preserve the vector-ranked order
  const questionMap = new Map<string, Question | AafpQuestion>();
  iteQuestions.forEach((q) => questionMap.set(q.qid, q));
  aafpQuestions.forEach((q) => questionMap.set(q.aafp_qid, q));
  const rankedQuestions = matchedQids
    .map((qid: string) => questionMap.get(qid))
    .filter((q: Question | AafpQuestion | undefined): q is Question | AafpQuestion => q !== undefined);

  // ── Step 4: Collect linked article IDs ───────────────────────────────────
  const allArticleIds = new Set<string>();

  if (iteQids.length > 0) {
    const { data: xref } = await supabase
      .from("qid_art_xref")
      .select("article_id")
      .in("qid", iteQids);
    (xref ?? []).forEach((r: { article_id: string }) => allArticleIds.add(r.article_id));
  }

  if (aafpQids.length > 0) {
    const { data: xref } = await supabase
      .from("aafp_qid_art_xref")
      .select("article_id")
      .in("aafp_qid", aafpQids);
    (xref ?? []).forEach((r: { article_id: string }) => allArticleIds.add(r.article_id));
  }

  // ── Step 5: Fetch article rows ────────────────────────────────────────────
  let articles: Article[] = [];
  if (allArticleIds.size > 0) {
    const { data: artData } = await supabase
      .from("articles")
      .select(
        "article_id, clean_ref, canonical_filename, author1, author2, year, tier, source_type, blueprint, body_system, citation_count, concept_tags"
      )
      .in("article_id", [...allArticleIds])
      .gt("citation_count", 0)          // exclude orphans
      .neq("source_type", "stub");      // exclude stubs
    // ART-0001 is the canonical "placeholder/unknown" article record in the DB
    // and is excluded from all search results by convention.

    articles = artData ?? [];
  }

  const searchMs = Date.now() - searchStart;

  return { questions: rankedQuestions, articles, queryEmbeddingMs, searchMs };
}
