/**
 * synthesize.js — Clinical narrative synthesis layer
 *
 * Takes a unified_v1.0 extraction JSON, calls Claude to produce
 * clinician-focused narrative, and augments the JSON in-place.
 *
 * Usage:  node synthesize.js <extraction.json>
 *
 * Adds extraction.synthesis with:
 *   - clinical_bottom_line: 2-3 paragraph narrative for practice
 *   - practice_pearls: 3-5 memorable bullet points
 *   - medication_groups: medications grouped by clinical indication
 *   - critical_alerts: top red flags with "why it matters"
 *
 * Non-destructive: if synthesis fails, the JSON is unchanged
 * and the pipeline continues with raw data only.
 */

// Suppress Node.js experimental localStorage warning (v25+)
process.removeAllListeners('warning');

const fs = require('fs');

const MODEL = "claude-sonnet-4-6";
const MAX_TOKENS = 4000;

// ── Build the prompt ─────────────────────────────────────────────

function buildPrompt(source, extraction) {
  // Cap arrays to control token budget
  const snapshot = {
    title: source.title || "Unknown",
    document_type: source.document_type || "guideline",
    summary: extraction.summary || "",
    population: extraction.population || {},
    recommendations: (extraction.recommendations || []).slice(0, 20),
    medications: (extraction.medications || []).slice(0, 25),
    red_flags: (extraction.red_flags || []).slice(0, 30),
    key_thresholds: (extraction.key_thresholds || []).slice(0, 15),
    follow_up: extraction.follow_up || "",
    escalation_path: extraction.escalation_path || ""
  };

  const system = `You are a clinical synthesis engine for family medicine board review. Given raw extraction data from a clinical guideline, produce a narrative that helps a busy physician understand WHY this guideline matters and HOW it changes practice.

Write in direct, clinical language. No fluff. Every sentence should be actionable or informative. Assume the reader is a board-certified family medicine physician who needs to quickly grasp what's new or important.`;

  const user = `Here is raw extraction data from "${snapshot.title}":

${JSON.stringify(snapshot, null, 2)}

Produce a JSON object with exactly these 5 fields:

1. "clinical_bottom_line" (string): 2-3 paragraphs explaining what this guideline means for daily practice. Focus on what's NEW, DIFFERENT, or commonly missed. Be specific about which patients, what to do, and when. Separate paragraphs with double newlines.

2. "practice_pearls" (array of 3-5 strings): Concise, memorable takeaways. Each should be a complete sentence starting with an action verb. These are the things a physician should remember at the point of care.

3. "medication_groups" (array of objects): Group ALL medications by clinical indication or scenario. Each object:
   - "group_name" (string): Clinical scenario name, e.g. "First-Line HFrEF Therapy"
   - "narrative" (string): 1-2 sentences: when to use, why these matter, what's the clinical rationale
   - "drugs" (array of strings): drug names in this group

4. "critical_alerts" (array of 5-8 objects): The most important red flags. Each:
   - "alert" (string): The sign, symptom, or finding
   - "why_it_matters" (string): One sentence — clinical significance and immediate action needed

5. "definitions_and_thresholds" (array of objects): High-yield clinical definitions AND diagnostic thresholds that CHANGE MANAGEMENT. Each:
   - "term" (string): The clinical term, condition, or diagnostic threshold
   - "definition" (string): Concise definition. For thresholds, include the value AND what action it triggers (e.g. "ANC <500 cells/mm³ → initiate empiric broad-spectrum antibiotics within 30 minutes")
   RULES:
   - ONLY include thresholds where crossing the value changes what you DO. Skip basic measurements (QRS duration, normal heart rate, etc.) that don't trigger a management decision.
   - Include key clinical definitions that a physician must know (e.g. diagnostic criteria, staging classifications, syndrome definitions).
   - Do NOT include medication names as terms — those belong in medication_groups.
   - Aim for 5-12 entries. Quality over quantity.

Return ONLY valid JSON. No markdown fencing. No commentary.`;

  return { system, user };
}

// ── Call Claude API ──────────────────────────────────────────────

async function callClaude(system, user, apiKey) {
  const resp = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-api-key": apiKey,
      "anthropic-version": "2023-06-01"
    },
    body: JSON.stringify({
      model: MODEL,
      max_tokens: MAX_TOKENS,
      system,
      messages: [{ role: "user", content: user }]
    })
  });

  if (!resp.ok) {
    const body = await resp.text();
    throw new Error(`API ${resp.status}: ${body.substring(0, 200)}`);
  }

  const result = await resp.json();
  return result.content[0].text;
}

// ── Parse response (handles raw JSON or markdown-fenced) ────────

function parseResponse(text) {
  try {
    return JSON.parse(text);
  } catch (_) {
    const match = text.match(/```(?:json)?\s*([\s\S]*?)```/);
    if (match) return JSON.parse(match[1]);
    throw new Error("Could not parse synthesis response as JSON");
  }
}

// ── Main ────────────────────────────────────────────────────────

async function main() {
  const jsonPath = process.argv[2];
  if (!jsonPath) {
    console.error("Usage: node synthesize.js <extraction.json>");
    process.exit(1);
  }

  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    console.error("    [SKIP] No ANTHROPIC_API_KEY — synthesis skipped");
    process.exit(0);
  }

  const data = JSON.parse(fs.readFileSync(jsonPath, 'utf-8'));
  const { source = {}, extraction = {} } = data;

  // Skip if no meaningful extraction data
  if (!extraction.summary && (!extraction.recommendations || extraction.recommendations.length === 0)) {
    console.error("    [SKIP] Insufficient extraction data for synthesis");
    process.exit(0);
  }

  const { system, user } = buildPrompt(source, extraction);
  const text = await callClaude(system, user, apiKey);
  const synthesis = parseResponse(text);

  // Validate minimum structure
  if (!synthesis.clinical_bottom_line || !synthesis.practice_pearls) {
    throw new Error("Synthesis response missing required fields");
  }

  // Augment extraction in-place
  data.extraction.synthesis = synthesis;
  fs.writeFileSync(jsonPath, JSON.stringify(data, null, 2), 'utf-8');
  console.log("    Synthesis OK");
}

main().catch(err => {
  // Non-fatal: log warning and exit cleanly so pipeline continues
  console.error("    [WARN] Synthesis failed:", err.message);
  process.exit(0);
});
