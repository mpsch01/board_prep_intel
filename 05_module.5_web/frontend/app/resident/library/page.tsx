/**
 * /resident/library — Prescribed reading list for the resident.
 *
 * Loads prescribed readings from Sanity (for the resident's cohort)
 * and enriches each article_id with live data from Supabase.
 */
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { sanityClient } from "@/lib/sanity/client";
import type { Article, ArticleCurrency } from "@/lib/supabase/types";

interface SanityArticleEntry {
  articleId: string;
  canonicalFilename: string | null;
  priorityTier: "required" | "recommended" | "optional";
  readingNotes: string | null;
}

interface SanityReading {
  _id: string;
  dueDate: string | null;
  sessionTitle: string | null;
  articles: SanityArticleEntry[];
}

const TIER_BADGE: Record<string, string> = {
  required: "#dc2626",
  recommended: "#d97706",
  optional: "#6b7280",
};

const CURRENCY_LABEL: Record<string, string> = {
  current: "✓ Current",
  updated: "↑ Newer version available",
  check_needed: "⚠ Review needed",
  not_indexed: "—",
};

export default async function LibraryPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/login");

  const { data: profile } = await supabase
    .from("user_profiles")
    .select("cohort_year")
    .eq("id", user.id)
    .single();

  const cohortYear = profile?.cohort_year ?? 0;

  // Fetch all prescribed readings for this cohort from Sanity
  const readings: SanityReading[] = await sanityClient.fetch(
    `*[_type == "prescribedReading" && visibleToResidents == true && $year in session->cohorts[]->cohortYear] | order(dueDate asc) {
      _id,
      dueDate,
      "sessionTitle": session->title,
      articles[] { articleId, canonicalFilename, priorityTier, readingNotes }
    }`,
    { year: cohortYear }
  );

  // Collect all article IDs and fetch from Supabase
  const allArticleIds = [
    ...new Set(readings.flatMap((r) => (r.articles ?? []).map((a) => a.articleId))),
  ];

  let articleMap = new Map<string, Article & { currency?: ArticleCurrency }>();

  if (allArticleIds.length > 0) {
    const [{ data: artData }, { data: currencyData }] = await Promise.all([
      supabase.from("articles").select("article_id, canonical_filename, author1, author2, year, tier, blueprint, body_system, citation_count").in("article_id", allArticleIds),
      supabase.from("article_currency").select("article_id, currency_status, pub_date, newer_version_title").in("article_id", allArticleIds),
    ]);

    const currencyMap = new Map((currencyData ?? []).map((c: ArticleCurrency) => [c.article_id, c]));
    (artData ?? []).forEach((a: Article) => {
      articleMap.set(a.article_id, { ...a, currency: currencyMap.get(a.article_id) });
    });
  }

  // Fetch completed readings for progress display
  const { data: completed } = await supabase
    .from("reading_completions")
    .select("article_id")
    .eq("resident_id", user.id);
  const completedIds = new Set((completed ?? []).map((c: { article_id: string }) => c.article_id));

  return (
    <main style={{ maxWidth: "1000px", margin: "0 auto", padding: "2rem 1rem" }}>
      <h1 style={{ fontSize: "1.5rem", marginBottom: "0.5rem" }}>Reading Library</h1>
      <p style={{ color: "var(--color-text-muted)", marginBottom: "2rem" }}>
        {readings.length > 0
          ? `${completedIds.size} of ${allArticleIds.length} articles completed`
          : "No reading lists assigned yet."}
      </p>

      {readings.map((reading) => (
        <section key={reading._id} style={{ marginBottom: "2rem" }}>
          <h2 style={{ fontSize: "1.125rem", marginBottom: "0.25rem" }}>
            {reading.sessionTitle ?? "Unlinked List"}
          </h2>
          {reading.dueDate && (
            <p style={{ fontSize: "0.875rem", color: "var(--color-text-muted)", marginBottom: "0.75rem" }}>
              Due {reading.dueDate}
            </p>
          )}

          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            {(reading.articles ?? []).map((entry) => {
              const art = articleMap.get(entry.articleId);
              const isDone = completedIds.has(entry.articleId);

              return (
                <div key={entry.articleId} style={{ background: "var(--color-surface)", border: `1px solid ${isDone ? "var(--color-success)" : "var(--color-border)"}`, borderRadius: "6px", padding: "0.875rem 1rem", display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "1rem" }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", marginBottom: "0.25rem" }}>
                      <span style={{ fontSize: "0.75rem", background: TIER_BADGE[entry.priorityTier], color: "white", padding: "2px 6px", borderRadius: "3px" }}>
                        {entry.priorityTier}
                      </span>
                      <span style={{ fontWeight: 500 }}>
                        {art?.canonical_filename ?? entry.canonicalFilename ?? entry.articleId}
                      </span>
                    </div>
                    {art && (
                      <div style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)" }}>
                        {art.blueprint} · {art.body_system}
                        {art.currency?.currency_status && (
                          <span style={{ marginLeft: "0.5rem", color: art.currency.currency_status === "updated" ? "var(--color-warning)" : "inherit" }}>
                            · {CURRENCY_LABEL[art.currency.currency_status]}
                          </span>
                        )}
                      </div>
                    )}
                    {entry.readingNotes && (
                      <p style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)", marginTop: "0.25rem" }}>
                        {entry.readingNotes}
                      </p>
                    )}
                  </div>
                  {isDone && (
                    <span style={{ color: "var(--color-success)", fontWeight: 600, whiteSpace: "nowrap" }}>
                      ✓ Done
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </section>
      ))}
    </main>
  );
}
