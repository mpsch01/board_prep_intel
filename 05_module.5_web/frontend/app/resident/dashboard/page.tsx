import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { getAnnouncements, getAssignmentsForCohort, getSessionsForCohort } from "@/lib/sanity/client";

export default async function ResidentDashboard() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/login");

  const { data: profile } = await supabase
    .from("user_profiles")
    .select("display_name, cohort_year, abfm_id")
    .eq("id", user.id)
    .single();

  const cohortYear = profile?.cohort_year ?? 0;

  // Fetch Sanity content in parallel
  const [announcements, assignments, sessions] = await Promise.all([
    getAnnouncements(cohortYear),
    getAssignmentsForCohort(cohortYear),
    getSessionsForCohort(cohortYear),
  ]);

  // Fetch most recent score upload status
  const { data: latestUpload } = await supabase
    .from("score_uploads")
    .select("exam_year, parse_status, uploaded_at")
    .eq("resident_id", user.id)
    .order("uploaded_at", { ascending: false })
    .limit(1)
    .maybeSingle();

  return (
    <main style={{ maxWidth: "1100px", margin: "0 auto", padding: "2rem 1rem" }}>
      <h1 style={{ fontSize: "1.75rem", marginBottom: "0.25rem" }}>
        Welcome, {profile?.display_name ?? "Resident"}
      </h1>
      <p style={{ color: "var(--color-text-muted)", marginBottom: "2rem" }}>
        {cohortYear ? `Class of ${cohortYear}` : ""}
        {profile?.abfm_id ? ` · ABFM ID: ${profile.abfm_id}` : ""}
      </p>

      {/* ── Announcements ────────────────────────────────────────── */}
      {announcements.length > 0 && (
        <section style={{ marginBottom: "2rem" }}>
          <h2 style={{ fontSize: "1.125rem", marginBottom: "0.75rem" }}>📢 Announcements</h2>
          {announcements.map((a: { _id: string; title: string; pinned: boolean; publishedAt: string }) => (
            <div key={a._id} style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: "6px", padding: "1rem", marginBottom: "0.5rem" }}>
              <strong>{a.pinned ? "📌 " : ""}{a.title}</strong>
            </div>
          ))}
        </section>
      )}

      {/* ── Pending Assignments ──────────────────────────────────── */}
      <section style={{ marginBottom: "2rem" }}>
        <h2 style={{ fontSize: "1.125rem", marginBottom: "0.75rem" }}>📝 Assignments</h2>
        {assignments.length === 0 ? (
          <p style={{ color: "var(--color-text-muted)" }}>No active assignments.</p>
        ) : (
          <div style={{ display: "grid", gap: "0.75rem" }}>
            {assignments.map((a: { _id: string; title: string; dueDate?: string; sessionTitle?: string }) => (
              <a key={a._id} href={`/resident/assessment/${a._id}`} style={{ display: "block", background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: "6px", padding: "1rem", color: "inherit" }}>
                <div style={{ fontWeight: 600 }}>{a.title}</div>
                <div style={{ fontSize: "0.875rem", color: "var(--color-text-muted)" }}>
                  {a.sessionTitle && `${a.sessionTitle} · `}
                  {a.dueDate ? `Due ${a.dueDate}` : "No due date"}
                </div>
              </a>
            ))}
          </div>
        )}
      </section>

      {/* ── Upcoming Sessions ────────────────────────────────────── */}
      <section style={{ marginBottom: "2rem" }}>
        <h2 style={{ fontSize: "1.125rem", marginBottom: "0.75rem" }}>📅 Upcoming Sessions</h2>
        {sessions.length === 0 ? (
          <p style={{ color: "var(--color-text-muted)" }}>No sessions scheduled.</p>
        ) : (
          <div style={{ display: "grid", gap: "0.5rem" }}>
            {sessions.slice(0, 5).map((s: { _id: string; title: string; sessionDate?: string; bodySystem?: string }) => (
              <div key={s._id} style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: "6px", padding: "0.75rem 1rem" }}>
                <strong>{s.title}</strong>
                <span style={{ color: "var(--color-text-muted)", fontSize: "0.875rem", marginLeft: "0.5rem" }}>
                  {s.sessionDate} {s.bodySystem ? `· ${s.bodySystem}` : ""}
                </span>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* ── Score Report Status ──────────────────────────────────── */}
      <section style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
        <a href="/resident/scores/upload" style={{ flex: "1 1 200px", background: "var(--color-primary)", color: "white", padding: "1rem", borderRadius: "6px", textAlign: "center", fontWeight: 600 }}>
          Upload Score Report
        </a>
        <a href="/resident/analytics" style={{ flex: "1 1 200px", background: "var(--color-surface)", border: "1px solid var(--color-border)", color: "inherit", padding: "1rem", borderRadius: "6px", textAlign: "center", fontWeight: 600 }}>
          View Analytics
        </a>
        <a href="/resident/library" style={{ flex: "1 1 200px", background: "var(--color-surface)", border: "1px solid var(--color-border)", color: "inherit", padding: "1rem", borderRadius: "6px", textAlign: "center", fontWeight: 600 }}>
          Reading Library
        </a>
      </section>

      {latestUpload && (
        <p style={{ marginTop: "0.75rem", fontSize: "0.875rem", color: "var(--color-text-muted)" }}>
          Last upload: {latestUpload.exam_year} exam · Status:{" "}
          <strong style={{ color: latestUpload.parse_status === "complete" ? "var(--color-success)" : latestUpload.parse_status === "failed" ? "var(--color-danger)" : "var(--color-warning)" }}>
            {latestUpload.parse_status}
          </strong>
        </p>
      )}
    </main>
  );
}
