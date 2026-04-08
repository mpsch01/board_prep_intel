/**
 * /faculty/search — Natural Language question + article search.
 *
 * The Dr. XYZ use case: "Give me 15 questions on abdominal pain —
 * acute, chronic, and subacute, adults and peds."
 *
 * This is a client-side page that POSTs to /api/search.
 * Results displayed in a side-by-side questions / articles layout.
 */
"use client";

import { useState, FormEvent } from "react";
import type { Question, AafpQuestion, Article } from "@/lib/supabase/types";

type SearchResult = {
  questions: (Question | AafpQuestion)[];
  articles: Article[];
  meta: {
    queryEmbeddingMs: number;
    searchMs: number;
    totalQuestions: number;
    totalArticles: number;
  };
};

function isIteQuestion(q: Question | AafpQuestion): q is Question {
  return "qid" in q;
}

const TIER_COLOR: Record<string, string> = {
  right_click: "var(--color-tier-right-click)",
  VC_pass: "var(--color-tier-vc-pass)",
  local_lite: "var(--color-tier-local-lite)",
  VC_fail: "var(--color-tier-vc-fail)",
};

export default function FacultySearchPage() {
  const [query, setQuery] = useState("");
  const [count, setCount] = useState(15);
  const [sourceBank, setSourceBank] = useState<"" | "ITE" | "AAFP">("");
  const [result, setResult] = useState<SearchResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedQid, setExpandedQid] = useState<string | null>(null);

  async function handleSearch(e: FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);
    setExpandedQid(null);

    try {
      const res = await fetch("/api/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: query.trim(),
          count,
          sourceBank: sourceBank || undefined,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        setError(data.error ?? "Search failed.");
        return;
      }
      setResult(data);
    } catch {
      setError("Network error. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  async function saveAsSet() {
    if (!result) return;
    const name = window.prompt("Name this question set:", query.slice(0, 60));
    if (!name) return;

    const qids = result.questions.map((q) => (isIteQuestion(q) ? q.qid : q.aafp_qid));
    const articleIds = result.articles.map((a) => a.article_id);

    await fetch("/api/question-sets", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, query, qids, article_ids: articleIds }),
    });
    alert("Question set saved.");
  }

  return (
    <main style={{ maxWidth: "1300px", margin: "0 auto", padding: "2rem 1rem" }}>
      <h1 style={{ fontSize: "1.5rem", marginBottom: "0.5rem" }}>Question + Article Search</h1>
      <p style={{ color: "var(--color-text-muted)", marginBottom: "1.5rem" }}>
        Describe what you need in plain English. Example: <em>"15 questions on abdominal pain — acute, chronic, and pediatric"</em>
      </p>

      {/* ── Search Form ─────────────────────────────────────── */}
      <form onSubmit={handleSearch} style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap", marginBottom: "1.5rem", alignItems: "flex-end" }}>
        <div style={{ flex: "1 1 400px" }}>
          <label style={{ display: "block", marginBottom: "0.25rem", fontSize: "0.875rem" }}>Search Query</label>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g. abdominal pain — acute and chronic, adults and peds"
            style={{ width: "100%", padding: "0.6rem 0.75rem", border: "1px solid var(--color-border)", borderRadius: "4px" }}
            required
          />
        </div>
        <div>
          <label style={{ display: "block", marginBottom: "0.25rem", fontSize: "0.875rem" }}># Questions</label>
          <input type="number" value={count} onChange={(e) => setCount(Number(e.target.value))} min={1} max={100} style={{ width: "80px", padding: "0.6rem", border: "1px solid var(--color-border)", borderRadius: "4px" }} />
        </div>
        <div>
          <label style={{ display: "block", marginBottom: "0.25rem", fontSize: "0.875rem" }}>Bank</label>
          <select value={sourceBank} onChange={(e) => setSourceBank(e.target.value as "" | "ITE" | "AAFP")} style={{ padding: "0.6rem", border: "1px solid var(--color-border)", borderRadius: "4px" }}>
            <option value="">Both</option>
            <option value="ITE">ITE only</option>
            <option value="AAFP">AAFP only</option>
          </select>
        </div>
        <button type="submit" disabled={loading} style={{ padding: "0.6rem 1.5rem", background: "var(--color-primary)", color: "white", border: "none", borderRadius: "4px", cursor: loading ? "not-allowed" : "pointer", opacity: loading ? 0.7 : 1, fontWeight: 600 }}>
          {loading ? "Searching…" : "Search"}
        </button>
      </form>

      {error && <div style={{ color: "var(--color-danger)", marginBottom: "1rem" }}>{error}</div>}

      {result && (
        <>
          {/* ── Meta ─────────────────────────────────────────── */}
          <div style={{ display: "flex", gap: "1rem", alignItems: "center", marginBottom: "1rem", fontSize: "0.875rem", color: "var(--color-text-muted)" }}>
            <span>{result.meta.totalQuestions} questions · {result.meta.totalArticles} articles</span>
            <span>Embed {result.meta.queryEmbeddingMs}ms · Search {result.meta.searchMs}ms</span>
            <button onClick={saveAsSet} style={{ marginLeft: "auto", padding: "0.375rem 1rem", background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: "4px", cursor: "pointer" }}>
              Save as Question Set
            </button>
          </div>

          {/* ── Side-by-side layout ──────────────────────────── */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>

            {/* Questions panel */}
            <div>
              <h2 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "0.75rem" }}>Questions ({result.meta.totalQuestions})</h2>
              {result.questions.map((q, i) => {
                const qid = isIteQuestion(q) ? q.qid : q.aafp_qid;
                const stem = isIteQuestion(q) ? q.question_text : q.stem;
                const year = isIteQuestion(q) ? q.exam_year : null;
                const expanded = expandedQid === qid;

                return (
                  <div key={qid} style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: "6px", padding: "0.875rem", marginBottom: "0.5rem" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "0.5rem" }}>
                      <div>
                        <span style={{ fontSize: "0.75rem", color: "var(--color-text-muted)" }}>
                          {i + 1}. {qid} {year ? `· ITE ${year}` : "· AAFP"}
                        </span>
                        <p style={{ marginTop: "0.25rem", fontSize: "0.9375rem" }}>{stem}</p>
                      </div>
                      <button onClick={() => setExpandedQid(expanded ? null : qid)} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--color-primary)", fontSize: "0.875rem", whiteSpace: "nowrap" }}>
                        {expanded ? "▲ Less" : "▼ More"}
                      </button>
                    </div>

                    {expanded && (
                      <div style={{ marginTop: "0.75rem", borderTop: "1px solid var(--color-border)", paddingTop: "0.75rem" }}>
                        <ol style={{ paddingLeft: "1.25rem", fontSize: "0.875rem" }}>
                          {((isIteQuestion(q) ? q.choices : q.choices) as { letter: string; text: string }[]).map((c) => (
                            <li key={c.letter} style={{ marginBottom: "0.25rem", color: c.letter === (isIteQuestion(q) ? q.correct_answer : q.correct_letter) ? "var(--color-success)" : "inherit", fontWeight: c.letter === (isIteQuestion(q) ? q.correct_answer : q.correct_letter) ? 600 : 400 }}>
                              {c.letter}. {c.text}
                            </li>
                          ))}
                        </ol>
                        <p style={{ marginTop: "0.75rem", fontSize: "0.875rem", background: "#f9fafb", padding: "0.625rem", borderRadius: "4px" }}>
                          {isIteQuestion(q) ? q.explanation : q.explanation}
                        </p>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Articles panel */}
            <div>
              <h2 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "0.75rem" }}>Matched Articles ({result.meta.totalArticles})</h2>
              {result.articles.map((a) => (
                <div key={a.article_id} style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: "6px", padding: "0.875rem", marginBottom: "0.5rem" }}>
                  <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", marginBottom: "0.25rem" }}>
                    <span style={{ fontSize: "0.75rem", color: a.tier ? TIER_COLOR[a.tier] : "var(--color-text-muted)", fontWeight: 600 }}>{a.tier ?? "—"}</span>
                    <span style={{ fontSize: "0.75rem", color: "var(--color-text-muted)" }}>{a.article_id}</span>
                    <span style={{ fontSize: "0.75rem", color: "var(--color-text-muted)", marginLeft: "auto" }}>{a.citation_count} citations</span>
                  </div>
                  <p style={{ fontWeight: 500, fontSize: "0.9375rem" }}>{a.canonical_filename}</p>
                  <p style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)", marginTop: "0.125rem" }}>
                    {a.blueprint} · {a.body_system}
                  </p>
                  <p style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)", marginTop: "0.125rem" }}>
                    {a.clean_ref}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </main>
  );
}
