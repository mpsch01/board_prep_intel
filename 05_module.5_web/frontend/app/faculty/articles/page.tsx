/**
 * /faculty/articles — Browse and filter the article knowledge base.
 */
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import type { Article } from "@/lib/supabase/types";

interface SearchParams {
  tier?: string;
  blueprint?: string;
  body_system?: string;
  page?: string;
}

const PAGE_SIZE = 50;

const TIER_OPTIONS = ["right_click", "VC_pass", "local_lite", "VC_fail"];
const BLUEPRINT_OPTIONS = ["Acute Care", "Chronic Care", "Emergent/Urgent", "Preventive", "Foundations of Medicine"];

export default async function ArticlesPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const params = await searchParams;
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/login");

  const currentPage = Number(params.page ?? 1);
  const offset = (currentPage - 1) * PAGE_SIZE;

  let query = supabase
    .from("articles")
    .select("article_id, canonical_filename, author1, year, tier, blueprint, body_system, citation_count, unique_years", { count: "exact" })
    .gt("citation_count", 0)
    .neq("source_type", "stub")
    .neq("article_id", "ART-0001");

  if (params.tier) query = query.eq("tier", params.tier);
  if (params.blueprint) query = query.eq("blueprint", params.blueprint);
  if (params.body_system) query = query.eq("body_system", params.body_system);

  const { data: articles, count } = await query
    .order("citation_count", { ascending: false })
    .range(offset, offset + PAGE_SIZE - 1);

  const totalPages = Math.ceil((count ?? 0) / PAGE_SIZE);

  return (
    <main style={{ maxWidth: "1100px", margin: "0 auto", padding: "2rem 1rem" }}>
      <h1 style={{ fontSize: "1.5rem", marginBottom: "1rem" }}>
        Article Library
        <span style={{ fontSize: "1rem", fontWeight: 400, color: "var(--color-text-muted)", marginLeft: "0.5rem" }}>
          {count ?? 0} articles
        </span>
      </h1>

      {/* ── Filters ─────────────────────────────────────────── */}
      <form method="GET" style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap", marginBottom: "1.5rem" }}>
        <select name="tier" defaultValue={params.tier ?? ""} style={{ padding: "0.5rem", border: "1px solid var(--color-border)", borderRadius: "4px" }}>
          <option value="">All Tiers</option>
          {TIER_OPTIONS.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
        <select name="blueprint" defaultValue={params.blueprint ?? ""} style={{ padding: "0.5rem", border: "1px solid var(--color-border)", borderRadius: "4px" }}>
          <option value="">All Blueprint</option>
          {BLUEPRINT_OPTIONS.map((b) => <option key={b} value={b}>{b}</option>)}
        </select>
        <button type="submit" style={{ padding: "0.5rem 1rem", background: "var(--color-primary)", color: "white", border: "none", borderRadius: "4px", cursor: "pointer" }}>
          Filter
        </button>
        <a href="/faculty/articles" style={{ padding: "0.5rem 1rem", border: "1px solid var(--color-border)", borderRadius: "4px", color: "inherit" }}>
          Clear
        </a>
      </form>

      {/* ── Table ───────────────────────────────────────────── */}
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.875rem" }}>
          <thead>
            <tr style={{ background: "var(--color-background)", borderBottom: "2px solid var(--color-border)" }}>
              <th style={{ padding: "0.625rem 0.75rem", textAlign: "left" }}>Article ID</th>
              <th style={{ padding: "0.625rem 0.75rem", textAlign: "left" }}>Reference</th>
              <th style={{ padding: "0.625rem 0.75rem", textAlign: "left" }}>Tier</th>
              <th style={{ padding: "0.625rem 0.75rem", textAlign: "left" }}>Blueprint</th>
              <th style={{ padding: "0.625rem 0.75rem", textAlign: "left" }}>Body System</th>
              <th style={{ padding: "0.625rem 0.75rem", textAlign: "right" }}>Citations</th>
              <th style={{ padding: "0.625rem 0.75rem", textAlign: "right" }}>Years</th>
            </tr>
          </thead>
          <tbody>
            {(articles as Article[] ?? []).map((a, i) => (
              <tr key={a.article_id} style={{ borderBottom: "1px solid var(--color-border)", background: i % 2 === 0 ? "var(--color-surface)" : "transparent" }}>
                <td style={{ padding: "0.5rem 0.75rem", fontFamily: "monospace", fontSize: "0.8125rem", color: "var(--color-text-muted)" }}>{a.article_id}</td>
                <td style={{ padding: "0.5rem 0.75rem", maxWidth: "320px" }}>{a.canonical_filename}</td>
                <td style={{ padding: "0.5rem 0.75rem", fontSize: "0.8125rem" }}>{a.tier}</td>
                <td style={{ padding: "0.5rem 0.75rem", fontSize: "0.8125rem" }}>{a.blueprint}</td>
                <td style={{ padding: "0.5rem 0.75rem", fontSize: "0.8125rem" }}>{a.body_system}</td>
                <td style={{ padding: "0.5rem 0.75rem", textAlign: "right" }}>{a.citation_count}</td>
                <td style={{ padding: "0.5rem 0.75rem", textAlign: "right" }}>{a.unique_years}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* ── Pagination ──────────────────────────────────────── */}
      {totalPages > 1 && (
        <div style={{ display: "flex", gap: "0.5rem", justifyContent: "center", marginTop: "1.5rem" }}>
          {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
            <a
              key={p}
              href={`?${new URLSearchParams({ ...params, page: String(p) })}`}
              style={{ padding: "0.375rem 0.75rem", border: "1px solid var(--color-border)", borderRadius: "4px", background: p === currentPage ? "var(--color-primary)" : "var(--color-surface)", color: p === currentPage ? "white" : "inherit" }}
            >
              {p}
            </a>
          ))}
        </div>
      )}
    </main>
  );
}
