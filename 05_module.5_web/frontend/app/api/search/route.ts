/**
 * POST /api/search — NL question + article search.
 *
 * Request body:
 *   { query: string, count?: number, sourceBank?: "ITE" | "AAFP" }
 *
 * Response:
 *   { questions: [...], articles: [...], meta: { queryEmbeddingMs, searchMs } }
 *
 * Authentication: requires a valid Supabase session (checked via server client).
 * Roles: faculty and admin only.
 */
import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { nlSearch } from "@/lib/search/nl-search";

export async function POST(request: NextRequest) {
  // Auth check
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { data: profile } = await supabase
    .from("user_profiles")
    .select("role")
    .eq("id", user.id)
    .single();

  if (!profile || !["faculty", "admin"].includes(profile.role)) {
    return NextResponse.json({ error: "Forbidden" }, { status: 403 });
  }

  // Parse request body
  let body: { query?: string; count?: number; sourceBank?: "ITE" | "AAFP" };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  const { query, count = 15, sourceBank } = body;

  if (!query || typeof query !== "string" || query.trim().length === 0) {
    return NextResponse.json({ error: "query is required" }, { status: 400 });
  }

  if (count < 1 || count > 100) {
    return NextResponse.json(
      { error: "count must be between 1 and 100" },
      { status: 400 }
    );
  }

  try {
    const result = await nlSearch(query.trim(), { count, sourceBank });
    return NextResponse.json({
      questions: result.questions,
      articles: result.articles,
      meta: {
        queryEmbeddingMs: result.queryEmbeddingMs,
        searchMs: result.searchMs,
        totalQuestions: result.questions.length,
        totalArticles: result.articles.length,
      },
    });
  } catch (err) {
    console.error("/api/search error:", err);
    return NextResponse.json(
      { error: "Search failed. Check server logs." },
      { status: 500 }
    );
  }
}
