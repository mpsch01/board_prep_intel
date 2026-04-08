/**
 * /resident/scores/upload — PDF score report upload page.
 */
"use client";

import { useState, FormEvent, ChangeEvent } from "react";

const EXAM_YEARS = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025];

export default function ScoreUploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [examYear, setExamYear] = useState<number>(2025);
  const [status, setStatus] = useState<"idle" | "uploading" | "success" | "error">("idle");
  const [message, setMessage] = useState<string | null>(null);

  function handleFileChange(e: ChangeEvent<HTMLInputElement>) {
    const selected = e.target.files?.[0] ?? null;
    if (selected && selected.type !== "application/pdf") {
      setMessage("Please select a PDF file.");
      setFile(null);
      return;
    }
    setFile(selected);
    setMessage(null);
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!file) return;

    setStatus("uploading");
    setMessage(null);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("examYear", String(examYear));

    try {
      const res = await fetch("/api/scores/upload", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();

      if (!res.ok) {
        setStatus("error");
        setMessage(data.error ?? "Upload failed.");
        return;
      }

      setStatus("success");
      setMessage(data.message ?? "Upload successful. Results will appear in your analytics shortly.");
    } catch {
      setStatus("error");
      setMessage("Network error. Please try again.");
    }
  }

  return (
    <main style={{ maxWidth: "600px", margin: "0 auto", padding: "2rem 1rem" }}>
      <h1 style={{ fontSize: "1.5rem", marginBottom: "0.5rem" }}>Upload ITE Score Report</h1>
      <p style={{ color: "var(--color-text-muted)", marginBottom: "2rem" }}>
        Upload your ABFM ITE score report PDF. We will parse your item-level performance and
        generate personalized analytics and reading recommendations.
      </p>

      {status === "success" ? (
        <div style={{ background: "#dcfce7", color: "var(--color-success)", padding: "1rem", borderRadius: "6px" }}>
          ✓ {message}
          <div style={{ marginTop: "1rem" }}>
            <a href="/resident/analytics" style={{ color: "var(--color-primary)" }}>
              View your analytics →
            </a>
          </div>
        </div>
      ) : (
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          <div>
            <label style={{ display: "block", marginBottom: "0.25rem", fontWeight: 500 }}>
              Exam Year
            </label>
            <select
              value={examYear}
              onChange={(e) => setExamYear(Number(e.target.value))}
              style={{ width: "100%", padding: "0.5rem", border: "1px solid var(--color-border)", borderRadius: "4px" }}
            >
              {EXAM_YEARS.map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
          </div>

          <div>
            <label style={{ display: "block", marginBottom: "0.25rem", fontWeight: 500 }}>
              Score Report PDF
            </label>
            <input
              type="file"
              accept="application/pdf"
              onChange={handleFileChange}
              required
              style={{ width: "100%" }}
            />
            <p style={{ fontSize: "0.75rem", color: "var(--color-text-muted)", marginTop: "0.25rem" }}>
              Upload the Blueprint Performance or Body System Performance PDF from ABFM.
            </p>
          </div>

          {message && (
            <div style={{ color: status === "error" ? "var(--color-danger)" : "var(--color-text-muted)", fontSize: "0.875rem" }}>
              {message}
            </div>
          )}

          <button
            type="submit"
            disabled={!file || status === "uploading"}
            style={{ padding: "0.75rem", background: "var(--color-primary)", color: "white", border: "none", borderRadius: "4px", cursor: !file || status === "uploading" ? "not-allowed" : "pointer", opacity: !file || status === "uploading" ? 0.7 : 1, fontWeight: 600 }}
          >
            {status === "uploading" ? "Uploading…" : "Upload Score Report"}
          </button>
        </form>
      )}
    </main>
  );
}
