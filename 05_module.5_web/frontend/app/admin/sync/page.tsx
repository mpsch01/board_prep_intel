/**
 * /admin/sync — Trigger SQLite → Supabase sync.
 *
 * In production, you run sqlite_to_supabase.py locally after a pipeline run.
 * This page provides a status overview and instructions.
 */
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";

export default async function AdminSyncPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/login");

  const { data: profile } = await supabase.from("user_profiles").select("role").eq("id", user.id).single();
  if (profile?.role !== "admin") redirect("/");

  // Fetch table row counts from Supabase for status display
  const tables = ["articles", "questions", "aafp_questions", "qid_art_xref", "article_icd10", "question_icd10", "clinical_pathways", "article_citation_trend", "article_currency"] as const;

  const counts = await Promise.all(
    tables.map(async (t) => {
      const { count } = await supabase.from(t).select("*", { count: "exact", head: true });
      return { table: t, count: count ?? 0 };
    })
  );

  return (
    <main style={{ maxWidth: "900px", margin: "0 auto", padding: "2rem 1rem" }}>
      <h1 style={{ fontSize: "1.5rem", marginBottom: "0.5rem" }}>Database Sync Status</h1>
      <p style={{ color: "var(--color-text-muted)", marginBottom: "2rem" }}>
        The SQLite database (local) → Supabase (production) sync is manual.
        Run the sync script from your machine after any M1/M2/M3 pipeline run.
      </p>

      {/* Row counts */}
      <section style={{ marginBottom: "2rem" }}>
        <h2 style={{ fontSize: "1.125rem", marginBottom: "0.75rem" }}>Supabase Table Counts</h2>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.875rem" }}>
            <thead>
              <tr style={{ background: "var(--color-background)", borderBottom: "2px solid var(--color-border)" }}>
                <th style={{ padding: "0.5rem 0.75rem", textAlign: "left" }}>Table</th>
                <th style={{ padding: "0.5rem 0.75rem", textAlign: "right" }}>Rows in Supabase</th>
              </tr>
            </thead>
            <tbody>
              {counts.map(({ table, count }, i) => (
                <tr key={table} style={{ borderBottom: "1px solid var(--color-border)", background: i % 2 === 0 ? "var(--color-surface)" : "transparent" }}>
                  <td style={{ padding: "0.5rem 0.75rem", fontFamily: "monospace" }}>{table}</td>
                  <td style={{ padding: "0.5rem 0.75rem", textAlign: "right" }}>{count.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Instructions */}
      <section style={{ background: "#f9fafb", border: "1px solid var(--color-border)", borderRadius: "6px", padding: "1.5rem" }}>
        <h2 style={{ fontSize: "1.125rem", marginBottom: "0.75rem" }}>How to Sync</h2>
        <ol style={{ paddingLeft: "1.25rem", lineHeight: "2" }}>
          <li>Run the M1/M2/M3 pipeline scripts as usual — they update <code>ite_intelligence.db</code> locally.</li>
          <li>
            Copy <code>.env</code> with <code>SUPABASE_URL</code> and <code>SUPABASE_SERVICE_KEY</code> into{" "}
            <code>05_module.5_web/supabase/sync/</code>
          </li>
          <li>
            Run content sync:<br />
            <code style={{ background: "#e5e7eb", padding: "2px 6px", borderRadius: "3px" }}>
              python 05_module.5_web/supabase/sync/sqlite_to_supabase.py
            </code>
          </li>
          <li>
            Run vector sync (after embedding rebuild):<br />
            <code style={{ background: "#e5e7eb", padding: "2px 6px", borderRadius: "3px" }}>
              python 05_module.5_web/supabase/sync/vector_sync.py
            </code>
          </li>
          <li>Refresh this page to verify row counts match your local DB.</li>
        </ol>
      </section>
    </main>
  );
}
