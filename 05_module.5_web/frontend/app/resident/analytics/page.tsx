/**
 * /resident/analytics — Personal performance analytics dashboard.
 *
 * Displays:
 *   - Body system gap chart (radar)
 *   - Blueprint gap bar chart
 *   - Watch-list articles (high-priority missed references)
 *   - Year-over-year trend (if multiple years uploaded)
 */
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import AnalyticsDashboard from "@/components/resident/AnalyticsDashboard";

export default async function AnalyticsPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/login");

  // Fetch available exam years for this resident
  const { data: scoreYears } = await supabase
    .from("resident_scores")
    .select("exam_year")
    .eq("resident_id", user.id)
    .order("exam_year", { ascending: false });

  const availableYears = [
    ...new Set((scoreYears ?? []).map((r: { exam_year: number }) => r.exam_year)),
  ] as number[];

  if (availableYears.length === 0) {
    return (
      <main style={{ maxWidth: "900px", margin: "0 auto", padding: "2rem 1rem" }}>
        <h1 style={{ fontSize: "1.5rem", marginBottom: "1rem" }}>Analytics</h1>
        <div style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: "6px", padding: "2rem", textAlign: "center" }}>
          <p style={{ color: "var(--color-text-muted)", marginBottom: "1rem" }}>
            No score data found. Upload your ITE score report to see personalized analytics.
          </p>
          <a href="/resident/scores/upload" style={{ color: "var(--color-primary)" }}>
            Upload your score report →
          </a>
        </div>
      </main>
    );
  }

  const latestYear = availableYears[0];

  // Fetch body system summary from Postgres function
  const { data: bodySystemData } = await supabase.rpc("resident_body_system_summary", {
    p_resident_id: user.id,
    p_exam_year: latestYear,
  });

  // Fetch blueprint summary
  const { data: blueprintData } = await supabase.rpc("resident_blueprint_summary", {
    p_resident_id: user.id,
    p_exam_year: latestYear,
  });

  // Fetch watch-list articles
  const { data: watchlistData } = await supabase.rpc("resident_watchlist_articles", {
    p_resident_id: user.id,
    p_exam_year: latestYear,
  });

  return (
    <main style={{ maxWidth: "1100px", margin: "0 auto", padding: "2rem 1rem" }}>
      <h1 style={{ fontSize: "1.5rem", marginBottom: "0.25rem" }}>Analytics</h1>
      <p style={{ color: "var(--color-text-muted)", marginBottom: "2rem" }}>
        ITE {latestYear} · Item-level performance breakdown
      </p>

      <AnalyticsDashboard
        bodySystemData={bodySystemData ?? []}
        blueprintData={blueprintData ?? []}
        watchlistArticles={watchlistData ?? []}
        availableYears={availableYears}
        selectedYear={latestYear}
      />
    </main>
  );
}
