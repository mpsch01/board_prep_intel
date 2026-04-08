/**
 * /admin/users — Manage residents and faculty accounts.
 */
import { redirect } from "next/navigation";
import { createClient, createAdminClient } from "@/lib/supabase/server";
import type { UserProfile } from "@/lib/supabase/types";

export default async function AdminUsersPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/login");

  const { data: profile } = await supabase.from("user_profiles").select("role").eq("id", user.id).single();
  if (profile?.role !== "admin") redirect("/");

  const adminClient = await createAdminClient();
  const { data: profiles } = await adminClient
    .from("user_profiles")
    .select("id, role, display_name, abfm_id, cohort_year, created_at")
    .order("role")
    .order("display_name");

  const byRole = {
    admin: (profiles ?? []).filter((p: UserProfile) => p.role === "admin"),
    faculty: (profiles ?? []).filter((p: UserProfile) => p.role === "faculty"),
    resident: (profiles ?? []).filter((p: UserProfile) => p.role === "resident"),
  };

  return (
    <main style={{ maxWidth: "1000px", margin: "0 auto", padding: "2rem 1rem" }}>
      <h1 style={{ fontSize: "1.5rem", marginBottom: "0.25rem" }}>User Management</h1>
      <p style={{ color: "var(--color-text-muted)", marginBottom: "2rem" }}>
        {profiles?.length ?? 0} total users
      </p>

      {(["resident", "faculty", "admin"] as const).map((role) => (
        <section key={role} style={{ marginBottom: "2rem" }}>
          <h2 style={{ fontSize: "1.125rem", textTransform: "capitalize", marginBottom: "0.75rem" }}>
            {role}s ({byRole[role].length})
          </h2>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.875rem" }}>
              <thead>
                <tr style={{ background: "var(--color-background)", borderBottom: "2px solid var(--color-border)" }}>
                  <th style={{ padding: "0.5rem 0.75rem", textAlign: "left" }}>Name</th>
                  <th style={{ padding: "0.5rem 0.75rem", textAlign: "left" }}>Supabase UUID</th>
                  {role === "resident" && <th style={{ padding: "0.5rem 0.75rem", textAlign: "left" }}>ABFM ID</th>}
                  {role === "resident" && <th style={{ padding: "0.5rem 0.75rem", textAlign: "left" }}>Cohort Year</th>}
                  <th style={{ padding: "0.5rem 0.75rem", textAlign: "left" }}>Joined</th>
                </tr>
              </thead>
              <tbody>
                {byRole[role].map((p: UserProfile, i: number) => (
                  <tr key={p.id} style={{ borderBottom: "1px solid var(--color-border)", background: i % 2 === 0 ? "var(--color-surface)" : "transparent" }}>
                    <td style={{ padding: "0.5rem 0.75rem" }}>{p.display_name ?? "—"}</td>
                    <td style={{ padding: "0.5rem 0.75rem", fontFamily: "monospace", fontSize: "0.75rem", color: "var(--color-text-muted)" }}>{p.id}</td>
                    {role === "resident" && <td style={{ padding: "0.5rem 0.75rem" }}>{p.abfm_id ?? "—"}</td>}
                    {role === "resident" && <td style={{ padding: "0.5rem 0.75rem" }}>{p.cohort_year ?? "—"}</td>}
                    <td style={{ padding: "0.5rem 0.75rem", color: "var(--color-text-muted)" }}>{new Date(p.created_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ))}

      <div style={{ background: "#eff6ff", border: "1px solid #bfdbfe", borderRadius: "6px", padding: "1rem", fontSize: "0.875rem" }}>
        <strong>Adding users:</strong> Create accounts in the{" "}
        <a href="https://supabase.com/dashboard" target="_blank" rel="noopener noreferrer">
          Supabase Dashboard → Authentication → Users
        </a>.
        Set <code>raw_user_meta_data.role</code> to <code>resident</code>, <code>faculty</code>, or <code>admin</code>
        before inviting — the auto-trigger will create their profile with the correct role.
      </div>
    </main>
  );
}
