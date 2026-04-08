/**
 * POST /api/question-sets — Save a faculty NL search result as a named question set.
 *
 * Request body:
 *   { name: string, query?: string, qids: string[], article_ids?: string[] }
 *
 * Authentication: faculty or admin only.
 */
import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

export async function POST(request: NextRequest) {
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

  let body: { name?: string; query?: string; qids?: string[]; article_ids?: string[] };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  const { name, query, qids, article_ids } = body;

  if (!name || typeof name !== "string" || name.trim().length === 0) {
    return NextResponse.json({ error: "name is required" }, { status: 400 });
  }

  if (!Array.isArray(qids) || qids.length === 0) {
    return NextResponse.json({ error: "qids must be a non-empty array" }, { status: 400 });
  }

  const { data, error } = await supabase
    .from("question_sets")
    .insert({
      faculty_id: user.id,
      name: name.trim(),
      query: query ?? null,
      qids,
      article_ids: article_ids ?? null,
    })
    .select("id, name, created_at")
    .single();

  if (error) {
    console.error("/api/question-sets insert error:", error);
    return NextResponse.json({ error: "Database error" }, { status: 500 });
  }

  return NextResponse.json(data, { status: 201 });
}

/**
 * GET /api/question-sets — List faculty's saved question sets.
 */
export async function GET(request: NextRequest) {
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

  const { data, error } = await supabase
    .from("question_sets")
    .select("id, name, query, qids, article_ids, created_at, updated_at")
    .eq("faculty_id", user.id)
    .order("created_at", { ascending: false });

  if (error) {
    return NextResponse.json({ error: "Database error" }, { status: 500 });
  }

  return NextResponse.json(data);
}
