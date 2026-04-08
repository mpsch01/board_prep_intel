/**
 * AnalyticsDashboard — Client component for resident performance analytics.
 *
 * Charts:
 *   - RadarChart: % correct per body system
 *   - BarChart: % correct per blueprint category
 *   - Watch-list articles table (highest priority missed references)
 */
"use client";

import {
  Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";

interface BodySystemRow {
  body_system: string;
  total_items: number;
  correct_items: number;
  pct_correct: number;
}

interface BlueprintRow {
  blueprint: string;
  total_items: number;
  correct_items: number;
  pct_correct: number;
}

interface WatchlistArticle {
  article_id: string;
  canonical_filename: string;
  tier: string;
  consecutive_streak: number;
  clean_ref: string;
}

interface Props {
  bodySystemData: BodySystemRow[];
  blueprintData: BlueprintRow[];
  watchlistArticles: WatchlistArticle[];
  availableYears: number[];
  selectedYear: number;
}

const TIER_COLOR: Record<string, string> = {
  right_click: "#7c3aed",
  VC_pass: "#1d4ed8",
  local_lite: "#0369a1",
  VC_fail: "#374151",
};

export default function AnalyticsDashboard({
  bodySystemData,
  blueprintData,
  watchlistArticles,
  availableYears,
  selectedYear,
}: Props) {
  const radarData = bodySystemData.map((r) => ({
    subject: r.body_system?.replace("Ear, Nose & Throat", "ENT") ?? "",
    score: r.pct_correct,
  }));

  const barData = blueprintData.map((r) => ({
    name: r.blueprint?.replace("Foundations of Medicine", "Foundations") ?? "",
    score: r.pct_correct,
    total: r.total_items,
  }));

  return (
    <div>
      {/* Year selector */}
      {availableYears.length > 1 && (
        <div style={{ marginBottom: "1.5rem", display: "flex", gap: "0.5rem" }}>
          {availableYears.map((y) => (
            <a
              key={y}
              href={`?year=${y}`}
              style={{ padding: "0.375rem 0.875rem", border: "1px solid var(--color-border)", borderRadius: "4px", background: y === selectedYear ? "var(--color-primary)" : "var(--color-surface)", color: y === selectedYear ? "white" : "inherit" }}
            >
              ITE {y}
            </a>
          ))}
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem", marginBottom: "2rem" }}>
        {/* Body System Radar */}
        <div style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: "8px", padding: "1.25rem" }}>
          <h2 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "1rem" }}>Body System Performance</h2>
          {radarData.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <RadarChart data={radarData}>
                <PolarGrid />
                <PolarAngleAxis dataKey="subject" tick={{ fontSize: 11 }} />
                <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fontSize: 10 }} />
                <Radar
                  name="% Correct"
                  dataKey="score"
                  stroke="var(--color-primary)"
                  fill="var(--color-primary)"
                  fillOpacity={0.25}
                />
                <Tooltip formatter={(v: number) => [`${v}%`, "% Correct"]} />
              </RadarChart>
            </ResponsiveContainer>
          ) : (
            <p style={{ color: "var(--color-text-muted)", textAlign: "center", padding: "2rem" }}>No data.</p>
          )}
        </div>

        {/* Blueprint Bar Chart */}
        <div style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: "8px", padding: "1.25rem" }}>
          <h2 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "1rem" }}>Blueprint Performance</h2>
          {barData.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={barData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" domain={[0, 100]} tickFormatter={(v: number) => `${v}%`} tick={{ fontSize: 11 }} />
                <YAxis type="category" dataKey="name" width={90} tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v: number) => [`${v}%`, "% Correct"]} />
                <Bar
                  dataKey="score"
                  fill="var(--color-primary)"
                  radius={[0, 4, 4, 0]}
                  label={{ position: "right", fontSize: 11, formatter: (v: number) => `${v}%` }}
                />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p style={{ color: "var(--color-text-muted)", textAlign: "center", padding: "2rem" }}>No data.</p>
          )}
        </div>
      </div>

      {/* Watch-list articles */}
      <section>
        <h2 style={{ fontSize: "1.125rem", fontWeight: 600, marginBottom: "0.5rem" }}>
          🔥 Priority Reading — Watch-List Articles
        </h2>
        <p style={{ fontSize: "0.875rem", color: "var(--color-text-muted)", marginBottom: "1rem" }}>
          These articles underlie questions you missed AND have appeared on the ABFM exam for{" "}
          {watchlistArticles.length > 0 ? "2+" : "—"} consecutive years — highest review priority.
        </p>
        {watchlistArticles.length === 0 ? (
          <p style={{ color: "var(--color-text-muted)" }}>
            No watch-list articles found for missed questions. Great work!
          </p>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            {watchlistArticles.map((a) => (
              <div key={a.article_id} style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: "6px", padding: "0.875rem 1rem", display: "flex", justifyContent: "space-between", alignItems: "center", gap: "1rem" }}>
                <div>
                  <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", marginBottom: "0.25rem" }}>
                    <span style={{ fontSize: "0.75rem", color: TIER_COLOR[a.tier] ?? "var(--color-text-muted)", fontWeight: 600 }}>{a.tier}</span>
                    <span style={{ fontWeight: 500 }}>{a.canonical_filename}</span>
                  </div>
                  <p style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)" }}>{a.clean_ref}</p>
                </div>
                <div style={{ textAlign: "right", whiteSpace: "nowrap" }}>
                  <span style={{ fontSize: "0.875rem", color: "var(--color-warning)", fontWeight: 600 }}>
                    {a.consecutive_streak} yr streak
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
