/**
 * /faculty/question-sets — Browse and manage saved question sets.
 */
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import type { QuestionSet } from "@/lib/supabase/types";

export default async function QuestionSetsPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/login");

  const { data: sets } = await supabase
    .from("question_sets")
    .select("id, name, query, qids, article_ids, created_at")
    .eq("faculty_id", user.id)
    .order("created_at", { ascending: false });

  return (
    <main style={{ maxWidth: "900px", margin: "0 auto", padding: "2rem 1rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
        <h1 style={{ fontSize: "1.5rem" }}>Saved Question Sets</h1>
        <a href="/faculty/search" style={{ color: "var(--color-primary)" }}>
          + New Search
        </a>
      </div>

      {(!sets || sets.length === 0) ? (
        <div style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: "6px", padding: "2rem", textAlign: "center" }}>
          <p style={{ color: "var(--color-text-muted)", marginBottom: "1rem" }}>
            No saved question sets yet.
          </p>
          <a href="/faculty/search" style={{ color: "var(--color-primary)" }}>
            Run an NL search to create your first set →
          </a>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          {(sets as QuestionSet[]).map((s) => (
            <div key={s.id} style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: "6px", padding: "1rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <div>
                  <strong style={{ fontSize: "1rem" }}>{s.name}</strong>
                  {s.query && (
                    <p style={{ fontSize: "0.875rem", color: "var(--color-text-muted)", marginTop: "0.125rem" }}>
                      Query: <em>"{s.query}"</em>
                    </p>
                  )}
                </div>
                <span style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)", whiteSpace: "nowrap" }}>
                  {new Date(s.created_at).toLocaleDateString()}
                </span>
              </div>
              <div style={{ marginTop: "0.5rem", fontSize: "0.8125rem", color: "var(--color-text-muted)" }}>
                {s.qids.length} question{s.qids.length !== 1 ? "s" : ""}
                {s.article_ids?.length ? ` · ${s.article_ids.length} article${s.article_ids.length !== 1 ? "s" : ""}` : ""}
              </div>
            </div>
          ))}
        </div>
      )}
    </main>
  );
}
