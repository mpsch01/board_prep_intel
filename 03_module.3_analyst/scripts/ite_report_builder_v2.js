#!/usr/bin/env node

// ITE Report Builder v2 — Restyled DOCX Generator
// Usage: node ite_report_builder_v2.js <analysis_v2.json> [output-dir]
// Produces two files:
//   - ITE_{year}_v2_Analysis_{name}.docx (Parts A+B: analysis + practice questions)
//   - ITE_{year}_v2_Exam_{name}.docx (Part C: exam version, answer key at end)

const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, HeadingLevel, BorderStyle, WidthType,
  ShadingType, VerticalAlign, PageNumber, PageBreak, LevelFormat
} = require("docx");

// ── Parse CLI arguments ──────────────────────────────────────────────
const args = process.argv.slice(2);
let inputPath = args[0];
let outputDir = args[1];

if (!inputPath) {
  console.error("ERROR: Input file path required.");
  console.error("Usage: node ite_report_builder_v2.js <analysis_v2.json> [output-dir]");
  process.exit(1);
}

// Resolve absolute path for input
inputPath = path.resolve(inputPath);

// Validate input file exists
if (!fs.existsSync(inputPath)) {
  console.error(`ERROR: Input file not found: ${inputPath}`);
  process.exit(1);
}

// Determine output directory (default: same as input file)
if (!outputDir) {
  outputDir = path.dirname(inputPath);
} else {
  outputDir = path.resolve(outputDir);
}

// Create output directory if it doesn't exist
if (!fs.existsSync(outputDir)) {
  try {
    fs.mkdirSync(outputDir, { recursive: true });
  } catch (err) {
    console.error(`ERROR: Cannot create output directory: ${outputDir}`);
    process.exit(1);
  }
}

// ── Load analysis data ───────────────────────────────────────────────
let data;
try {
  data = JSON.parse(fs.readFileSync(inputPath, "utf-8"));
} catch (err) {
  console.error(`ERROR: Failed to parse input file: ${err.message}`);
  process.exit(1);
}

// ═══════════════════════════════════════════════════════════════════
// REPORT PHILOSOPHY — shapes every narrative block
// ═══════════════════════════════════════════════════════════════════
const REPORT_VOICE = {
  role: "master standardized test analyzer and report builder",
  exam: "Family Medicine In-Training Examination (ITE)",
  objectives: [
    "A) Create a highly detailed, professional and sharp-looking report",
    "B) Provide at least 5 additional practice questions from the ITE database for each section marked 'weak', ranked by fit to weak areas",
    "C) Provide the same practice questions without answers/explanations as an 'exam' version with correct QID tags"
  ],
  tone: "clinical precision with actionable clarity — every finding leads to a recommendation, every weakness maps to an improvement path",
};

// ── Style constants ─────────────────────────────────────────────────
const NAVY   = "1F3864";
const BLUE   = "2E75B6";
const DGRAY  = "333333";
const MGRAY  = "595959";
const LGRAY  = "A0A0A0";
const WHITE  = "FFFFFF";
const LTBLUE = "D6E4F7";
const GREEN  = "276749";
const AMBER  = "975A16";
const RED    = "9B2C2C";
const FONT   = "Aptos";

// ── Helper functions ────────────────────────────────────────────────
function noBorders() {
  const n = { style: BorderStyle.NONE, size: 0, color: WHITE };
  return { top: n, bottom: n, left: n, right: n };
}
const thinBorder = { style: BorderStyle.SINGLE, size: 1, color: "D0D0D0" };
const cellBorders = { top: thinBorder, bottom: thinBorder, left: thinBorder, right: thinBorder };

function sectionBar(text) {
  const W = 9360;
  return new Table({
    width: { size: W, type: WidthType.DXA },
    columnWidths: [W],
    rows: [row([
      new TableCell({
        width: { size: W, type: WidthType.DXA },
        shading: { fill: NAVY, type: ShadingType.CLEAR },
        borders: noBorders(),
        margins: { top: 60, bottom: 60, left: 140, right: 140 },
        verticalAlign: VerticalAlign.CENTER,
        children: [new Paragraph({ spacing: { before: 0, after: 0 }, keepNext: true, children: [
          new TextRun({ text, font: FONT, size: 22, bold: true, color: WHITE }),
        ]})],
      }),
    ])],
  });
}

function subBar(text, fill = BLUE) {
  const W = 9360;
  return new Table({
    width: { size: W, type: WidthType.DXA },
    columnWidths: [W],
    rows: [row([
      new TableCell({
        width: { size: W, type: WidthType.DXA },
        shading: { fill, type: ShadingType.CLEAR },
        borders: noBorders(),
        margins: { top: 50, bottom: 50, left: 140, right: 140 },
        children: [new Paragraph({ keepNext: true, children: [
          new TextRun({ text, font: FONT, size: 20, bold: true, color: WHITE }),
        ]})],
      }),
    ])],
  });
}

function studyNote(text) {
  return new Paragraph({
    spacing: { before: 120, after: 200 },
    border: { left: { style: BorderStyle.SINGLE, size: 12, color: BLUE, space: 8 } },
    indent: { left: 200 },
    children: [
      new TextRun({ text: "\u270E STUDY NOTE  ", font: FONT, size: 20, bold: true, color: NAVY }),
      new TextRun({ text, font: FONT, size: 20, color: NAVY }),
    ],
  });
}

function rateColor(rate) {
  if (rate >= 0.70) return GREEN;
  if (rate >= 0.50) return AMBER;
  return RED;
}
function tierBadge(tier) {
  const map = { strong: "STRONG", on_track: "ON TRACK", at_risk: "AT RISK", critical_risk: "CRITICAL RISK" };
  return map[tier] || tier.toUpperCase();
}
function classIcon(cls) {
  if (cls === "relative_weakness") return "\u26A0";
  if (cls === "relative_strength") return "\u2605";
  return "\u2014";
}
function spacer(pts = 100, keepNext = false) {
  return new Paragraph({ spacing: { before: pts, after: 0 }, keepNext, children: [] });
}
function row(cells) {
  return new TableRow({ cantSplit: true, children: cells });
}
function headerCell(text, w) {
  return new TableCell({
    width: { size: w, type: WidthType.DXA }, borders: cellBorders,
    shading: { fill: LTBLUE, type: ShadingType.CLEAR },
    margins: { top: 60, bottom: 60, left: 80, right: 80 },
    verticalAlign: VerticalAlign.CENTER,
    children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [
      new TextRun({ text, font: FONT, size: 18, bold: true, color: NAVY }),
    ]})],
  });
}
function dataCell(text, w, color = DGRAY, bold = false, align = AlignmentType.CENTER) {
  return new TableCell({
    width: { size: w, type: WidthType.DXA }, borders: cellBorders,
    margins: { top: 50, bottom: 50, left: 80, right: 80 },
    verticalAlign: VerticalAlign.CENTER,
    children: [new Paragraph({ alignment: align, children: [
      new TextRun({ text: String(text), font: FONT, size: 18, color, bold }),
    ]})],
  });
}
function multiLineCell(lines, w) {
  return new TableCell({
    width: { size: w, type: WidthType.DXA }, borders: cellBorders,
    margins: { top: 50, bottom: 50, left: 80, right: 80 },
    verticalAlign: VerticalAlign.CENTER,
    children: lines.map(l => new Paragraph({ children: [
      new TextRun({ text: l.text, font: FONT, size: l.size || 18, color: l.color || DGRAY, bold: l.bold || false, italics: l.italics || false }),
    ]})),
  });
}
function makeTable(colWidths, rows) {
  return new Table({ width: { size: 9360, type: WidthType.DXA }, columnWidths: colWidths, rows });
}

// ── Data references ─────────────────────────────────────────────────
const res    = data.resident;
const perf   = data.performance;
const t1     = data.thresholds.tier1_pass_probability;
const t2     = data.thresholds.tier2_relative;
const t3     = data.thresholds.tier3_sem;
const diff   = data.difficulty_profile;
const yields = data.yield_priorities;
// v3: concept_clustering + icd10_weakness_map + pathway_gap_map are top-level
// v2 fallback: plugins.concept_fingerprint + plugins.icd10_map
const concept  = data.concept_clustering || data.plugins?.concept_fingerprint;
const icd      = data.icd10_weakness_map  || data.plugins?.icd10_map;
const pathways = data.pathway_gap_map;
const analysisVer = data.analysis_version || "2.0";
const allQuestions = data.practice_questions || [];
const articles  = data.top_articles || [];

// Extract safe name: last name, spaces→underscores, remove periods
function extractSafeName(fullName) {
  const parts = fullName.split(",");
  if (parts.length > 0) {
    const lastName = parts[0].trim();
    return lastName
      .replace(/\s+/g, "_")
      .replace(/\./g, "");
  }
  return "Report";
}

const safeName = extractSafeName(res.name);

// ── Prefer official score report values over analyzer estimates ──────
// When a --score-report PDF was parsed, scaled_score_source === "official"
// and performance.overall carries the actual ABFM values (scaled_score_actual,
// vs_mps, pgy_level, pgy_mean_scaled, vs_pgy_mean). Fall back to thresholds
// estimates when no score report was provided.
const hasOfficialScore = perf.overall.scaled_score_source === "official";
const displayScaled    = hasOfficialScore ? perf.overall.scaled_score_actual : t1.scaled_score;
const displayVsMps     = hasOfficialScore ? perf.overall.vs_mps              : t1.vs_mps;
const displayPgyLevel  = (hasOfficialScore && perf.overall.pgy_level)
                           ? `PGY${perf.overall.pgy_level}` : "National";
const displayPgyMean   = hasOfficialScore ? perf.overall.pgy_mean_scaled     : t1.national_mean;
const displayVsPgy     = hasOfficialScore ? perf.overall.vs_pgy_mean
                           : (t1.scaled_score - t1.national_mean);

// ── Build output filenames ──────────────────────────────────────────
const ver = analysisVer.startsWith("3") ? "v3" : "v2";
const analysisFileName = `ITE_${data.exam_year}_${ver}_Analysis_${safeName}.docx`;
const examFileName = `ITE_${data.exam_year}_${ver}_Exam_${safeName}.docx`;
const analysisPath = path.join(outputDir, analysisFileName);
const examPath = path.join(outputDir, examFileName);

// ── Identify weak areas (blueprint + body system) ───────────────────
const weakBlueprints = [];
for (const [cat, cls] of Object.entries(t2.classifications || {})) {
  if (cls.classification === "relative_weakness") weakBlueprints.push(cat);
}
for (const [cat, vals] of Object.entries(perf.blueprint)) {
  if (vals.rate < 0.70 && !weakBlueprints.includes(cat)) weakBlueprints.push(cat);
}
// Include body systems below 70% so their targeted questions get ⚠ WEAK AREA treatment
for (const [sys, vals] of Object.entries(perf.body_system || {})) {
  if (vals.rate < 0.70 && !weakBlueprints.includes(sys)) weakBlueprints.push(sys);
}

// ── Group questions by targeting (weak area) ────────────────────────
const qByTarget = {};
for (const q of allQuestions) {
  const target = q.targeting || "General";
  if (!qByTarget[target]) qByTarget[target] = [];
  qByTarget[target].push(q);
}

// Collect warnings for weak areas with zero practice question coverage
const warnings = [];
for (const wb of weakBlueprints) {
  const count = (qByTarget[wb] || []).length;
  if (count === 0) {
    warnings.push(`"${wb}" (${count} questions)`);
  }
}

// ═══════════════════════════════════════════════════════════════════
// BUILD PART A: ANALYSIS REPORT
// ═══════════════════════════════════════════════════════════════════
const children = [];
const weakList = weakBlueprints.length > 0 ? weakBlueprints.join(", ") : "none identified";

// ────────────────────────────────────────────────────────────────────
// 1. TITLE BLOCK
// ────────────────────────────────────────────────────────────────────
children.push(new Paragraph({ spacing: { before: 600, after: 0 }, alignment: AlignmentType.CENTER, children: [
  new TextRun({ text: `ITE ${data.exam_year} SCORE ANALYSIS`, font: FONT, size: 36, bold: true, color: NAVY }),
]}));
children.push(spacer(300));

// Score display — de-identified: no name, no ABFM ID, no tier badge (percentile only)
children.push(makeTable([3120, 3120, 3120], [row([
  new TableCell({ borders: noBorders(), width: { size: 3120, type: WidthType.DXA }, verticalAlign: VerticalAlign.CENTER, children: [
    new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: `${perf.overall.pct}%`, font: FONT, size: 56, bold: true, color: NAVY })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: `${perf.overall.correct}/${perf.overall.total} correct`, font: FONT, size: 18, color: MGRAY })] }),
  ]}),
  new TableCell({ borders: noBorders(), width: { size: 3120, type: WidthType.DXA }, verticalAlign: VerticalAlign.CENTER, children: [
    new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: `${displayScaled}`, font: FONT, size: 56, bold: true, color: BLUE })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Scaled Score", font: FONT, size: 18, color: MGRAY })] }),
  ]}),
  new TableCell({ borders: noBorders(), width: { size: 3120, type: WidthType.DXA }, verticalAlign: VerticalAlign.CENTER,
    shading: { fill: NAVY, type: ShadingType.CLEAR }, margins: { top: 100, bottom: 100, left: 100, right: 100 }, children: [
    new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: `${t1.percentile_estimate}th`, font: FONT, size: 44, bold: true, color: WHITE })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Percentile", font: FONT, size: 18, color: WHITE })] }),
  ]}),
])]));
children.push(spacer(100));
children.push(new Paragraph({ spacing: { before: 80, after: 0 }, alignment: AlignmentType.CENTER, children: [
  new TextRun({ text: `vs MPS (380): +${displayVsMps}  |  vs ${displayPgyLevel} Mean (${displayPgyMean}): +${displayVsPgy}  |  N = 15,382`, font: FONT, size: 18, color: MGRAY }),
]}));

// ────────────────────────────────────────────────────────────────────
// 2. EXECUTIVE SUMMARY
// ────────────────────────────────────────────────────────────────────
children.push(spacer(200));
children.push(sectionBar("\u2605 EXECUTIVE SUMMARY"));
children.push(spacer(60, true));
// Dynamic executive summary
const personalMean = t2.thresholds?.personal_mean || 0;
const personalMeanPct = (personalMean * 100).toFixed(1);
const bpEntries = Object.entries(perf.blueprint).sort((a, b) => a[1].rate - b[1].rate);
const worstBp = bpEntries[0];
const bestBp = bpEntries[bpEntries.length - 1];
const worstSem = t3?.[worstBp[0]]?.sem ? ` (SEM \u00B1${t3[worstBp[0]].sem})` : "";
const topYield = yields?.[0];
const topYieldText = topYield
  ? `Highest-yield improvement: ${topYield.dimension} = ${topYield.recoverable_items?.toFixed(1) || "?"} improvable items at ${topYield.exam_weight_pct || "?"}% exam weight.`
  : "";

children.push(studyNote(
  `Scaled score ${displayScaled}${hasOfficialScore ? " (official)" : " (est.)"}` +
  ` (${t1.percentile_estimate}th percentile est.), ` +
  `placing in the "${tierBadge(t1.pass_tier.tier)}" tier. ` +
  `Weak areas identified: ${weakList}. ` +
  `${worstBp[0]} is the lowest-performing category at ${(worstBp[1].rate * 100).toFixed(1)}% ` +
  `(vs personal mean ${personalMeanPct}%)${worstSem}, ` +
  `while ${bestBp[0]} is the strongest at ${(bestBp[1].rate * 100).toFixed(1)}%. ` +
  `${diff.easy_miss_count || 0} easy misses (\u2265700 difficulty) represent the most improvable knowledge gaps. ` +
  `${topYieldText} ` +
  `This report provides targeted practice questions for each weak area (min. 5 per section), ranked by fit, ` +
  `plus a separate exam version for timed self-assessment.`
));

// ────────────────────────────────────────────────────────────────────
// 3b. LONGITUDINAL DELTA (only rendered when prior-year data exists)
// ────────────────────────────────────────────────────────────────────
const lng = data.longitudinal_delta || {};
if (lng.n1 || lng.n2) {
  children.push(new Paragraph({ children: [new PageBreak()] }));
  children.push(sectionBar("\uD83D\uDCC8 YEAR-OVER-YEAR PROGRESS"));
  children.push(spacer(80, true));

  const lngColW = [1400, 1400, 1400, 1400, 3760];  // 9360 twips total

  for (const [key, delta] of [["n1", lng.n1], ["n2", lng.n2]]) {
    if (!delta) continue;
    const label = key === "n1" ? "vs Last Year" : "vs Two Years Ago";
    children.push(new Paragraph({ keepNext: true, spacing: { before: 120, after: 60 }, children: [
      new TextRun({ text: `${label} (${delta.prior_year} \u2192 ${data.exam_year})`, font: FONT, size: 22, bold: true, color: NAVY }),
    ]}));

    // Score row
    const scoreDelta = delta.scaled_delta != null ? delta.scaled_delta : delta.overall_delta_pct;
    const scorePrior = delta.scaled_delta != null ? delta.prior_scaled   : delta.prior_overall_pct + "%";
    const scoreCurr  = delta.scaled_delta != null ? delta.current_scaled : delta.current_overall_pct + "%";
    const scoreType  = delta.scaled_delta != null
      ? (delta.scaled_source === "official" ? "Scaled score (official)" : "Scaled score (est.)")
      : "Raw score %";
    const sign = scoreDelta >= 0 ? "+" : "";
    const deltaColor = scoreDelta > 0 ? GREEN : scoreDelta < 0 ? RED : DGRAY;

    const lngRows = [
      row(["Metric", "Prior", "Current", "Change", "Weak Area Trajectory"].map((h, i) => headerCell(h, lngColW[i]))),
      row([
        dataCell(scoreType,          lngColW[0], DGRAY, false, AlignmentType.LEFT),
        dataCell(String(scorePrior), lngColW[1], MGRAY, false),
        dataCell(String(scoreCurr),  lngColW[2], NAVY,  true),
        dataCell(`${sign}${scoreDelta}`, lngColW[3], deltaColor, true),
        (() => {
          const traj = delta.weak_area_trajectory || {};
          const lines = [];
          if (traj.closed?.length)      lines.push({ text: `\u2714 Closed: ${traj.closed.join(", ")}`,       bold: false, color: GREEN, size: 16 });
          if (traj.persistent?.length)  lines.push({ text: `\u26A0 Persistent: ${traj.persistent.join(", ")}`, bold: false, color: AMBER, size: 16 });
          if (traj.new?.length)         lines.push({ text: `\u25B6 New gap: ${traj.new.join(", ")}`,          bold: false, color: RED,   size: 16 });
          return lines.length ? multiLineCell(lines, lngColW[4]) : dataCell("\u2014", lngColW[4], MGRAY, false);
        })(),
      ]),
    ];
    children.push(makeTable(lngColW, lngRows));
    children.push(spacer(60));
  }
}

// ────────────────────────────────────────────────────────────────────
// 4a. ITE OVERVIEW TABLE (blueprint + body system at a glance)
// ────────────────────────────────────────────────────────────────────
children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(sectionBar("📊 ITE PERFORMANCE OVERVIEW"));
children.push(spacer(80, true));

children.push(new Paragraph({ keepNext: true, spacing: { before: 0, after: 80 }, children: [
  new TextRun({ text: "Summary of performance across all blueprint categories and body systems. " +
    "Color-coded by performance: green (strong), amber (developing), red (priority focus).",
    font: FONT, size: 18, color: MGRAY, italics: true }),
]}));

// Blueprint summary
children.push(new Paragraph({ spacing: { before: 80, after: 60 }, children: [
  new TextRun({ text: "Blueprint Categories", font: FONT, size: 22, bold: true, color: NAVY }),
]}));
{
  const ovColW = [4200, 1800, 1800, 1560];
  const ovRows = [row(["Category", "Correct", "Total", "Rate"].map((h, i) => headerCell(h, ovColW[i])))];
  for (const [cat, vals] of Object.entries(perf.blueprint)) {
    const rate = vals.rate;
    const pct  = (rate * 100).toFixed(1) + "%";
    ovRows.push(row([
      dataCell(cat, ovColW[0], DGRAY, true, AlignmentType.LEFT),
      dataCell(vals.correct, ovColW[1]),
      dataCell(vals.total,   ovColW[2]),
      dataCell(pct, ovColW[3], rateColor(rate), true),
    ]));
  }
  children.push(makeTable(ovColW, ovRows));
}

// Body system summary
children.push(spacer(120));
children.push(new Paragraph({ spacing: { before: 80, after: 60 }, children: [
  new TextRun({ text: "Body Systems", font: FONT, size: 22, bold: true, color: NAVY }),
]}));
{
  const bsColW = [4200, 1800, 1800, 1560];
  const bsRows = [row(["Body System", "Correct", "Total", "Rate"].map((h, i) => headerCell(h, bsColW[i])))];
  const bsSorted = Object.entries(perf.body_system || {}).sort((a, b) => a[1].rate - b[1].rate);
  for (const [cat, vals] of bsSorted) {
    const rate = vals.rate;
    const pct  = (rate * 100).toFixed(1) + "%";
    bsRows.push(row([
      dataCell(cat, bsColW[0], DGRAY, true, AlignmentType.LEFT),
      dataCell(vals.correct, bsColW[1]),
      dataCell(vals.total,   bsColW[2]),
      dataCell(pct, bsColW[3], rateColor(rate), true),
    ]));
  }
  children.push(makeTable(bsColW, bsRows));
}

// ────────────────────────────────────────────────────────────────────
// 4b. BLUEPRINT PERFORMANCE (detailed with SEM/classification)
// ────────────────────────────────────────────────────────────────────
children.push(spacer(200));
children.push(sectionBar("\u2606 BLUEPRINT CATEGORY PERFORMANCE"));
children.push(spacer(80, true));

const bpColW = [2200, 900, 900, 900, 1400, 900, 2160];
const bpRows = [row(["Category", "Correct", "Total", "Rate", "Relative", "SEM", "Confidence"].map((h, i) => headerCell(h, bpColW[i])))];

for (const [cat, vals] of Object.entries(perf.blueprint)) {
  const rate = vals.rate;
  const pct = (rate * 100).toFixed(1) + "%";
  const cls = t2.classifications?.[cat];
  const sem = t3?.[cat];
  const relLabel = cls ? `${classIcon(cls.classification)} ${cls.classification.replace(/_/g, " ")}` : "\u2014";
  const semLabel = sem ? (sem.reliable ? "\u2705 Reliable" : "\u26A0 Hypothesis") : "\u2014";
  bpRows.push(row([
    dataCell(cat, bpColW[0], DGRAY, true, AlignmentType.LEFT),
    dataCell(vals.correct, bpColW[1]), dataCell(vals.total, bpColW[2]),
    dataCell(pct, bpColW[3], rateColor(rate), true),
    dataCell(relLabel, bpColW[4]),
    dataCell(sem ? `\u00B1${sem.sem}` : "\u2014", bpColW[5], MGRAY),
    dataCell(semLabel, bpColW[6]),
  ]));
}
children.push(makeTable(bpColW, bpRows));

// ────────────────────────────────────────────────────────────────────
// 6. DIFFICULTY PROFILE
// ────────────────────────────────────────────────────────────────────
children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(sectionBar("\u26A1 DIFFICULTY PROFILE"));
children.push(spacer(80, true));

const diffColW = [2400, 2320, 2320, 2320];
const diffRows = [
  row(["Category", "Easy Miss (\u2265700)", "Mid-Range (300\u2013699)", "Hard Miss (<300)"].map((h, i) => headerCell(h, diffColW[i]))),
  row([
    dataCell("OVERALL", diffColW[0], NAVY, true, AlignmentType.LEFT),
    dataCell(diff.overall.easy_miss || 0, diffColW[1], RED, true),
    dataCell(diff.overall.mid_range || 0, diffColW[2], AMBER, true),
    dataCell(diff.overall.hard_miss || 0, diffColW[3], MGRAY),
  ]),
];
for (const [cat, vals] of Object.entries(diff.by_blueprint)) {
  diffRows.push(row([
    dataCell(cat, diffColW[0], DGRAY, false, AlignmentType.LEFT),
    dataCell(vals.easy_miss || 0, diffColW[1], RED),
    dataCell(vals.mid_range || 0, diffColW[2], AMBER),
    dataCell(vals.hard_miss || 0, diffColW[3], MGRAY),
  ]));
}
children.push(makeTable(diffColW, diffRows));

// Explanation of the difficulty score and tiers
children.push(new Paragraph({ spacing: { before: 120, after: 60 }, children: [
  new TextRun({ text: "How to read this table: ", font: FONT, size: 20, bold: true, color: NAVY }),
]}));
children.push(new Paragraph({ spacing: { before: 0, after: 60 }, children: [
  new TextRun({ text: "Each ITE question has an ABFM-assigned item difficulty ", font: FONT, size: 18, color: DGRAY }),
  new TextRun({ text: "score (0–999)", font: FONT, size: 18, bold: true, color: NAVY }),
  new TextRun({ text: " based on how often examinees nationally answered it correctly. " +
    "A score of 999 means nearly everyone got it right; a score near 0 means almost no one did.",
    font: FONT, size: 18, color: DGRAY }),
]}));
children.push(makeTable([3120, 6240], [
  row([headerCell("Tier", 3120), headerCell("What it means for your study plan", 6240)]),
  row([dataCell("Easy Miss (≥700)", 3120, RED, true, AlignmentType.LEFT),
       dataCell("Most examinees answered these correctly — genuine knowledge gap. Highest-priority improvement targets.", 6240, DGRAY, false, AlignmentType.LEFT)]),
  row([dataCell("Mid-Range (300–699)", 3120, AMBER, true, AlignmentType.LEFT),
       dataCell("High-yield study targets — meaningful score improvement per hour of review.", 6240, DGRAY, false, AlignmentType.LEFT)]),
  row([dataCell("Hard Miss (<300)", 3120, MGRAY, true, AlignmentType.LEFT),
       dataCell("Most examinees miss these too — low-yield to chase. Focus elsewhere unless time permits.", 6240, DGRAY, false, AlignmentType.LEFT)]),
]));

// Easy misses detail table — no Subcategory column
const easyMisses = diff.easy_misses || [];
if (easyMisses.length > 0) {
  children.push(spacer(120));
  children.push(new Paragraph({ spacing: { before: 60, after: 60 }, children: [
    new TextRun({ text: `Easy Misses \u2014 ${easyMisses.length} Items (Score \u2265 700)`, font: FONT, size: 22, bold: true, color: RED }),
  ]}));
  children.push(new Paragraph({ spacing: { before: 0, after: 80 }, children: [
    new TextRun({ text: "Most examinees answered these correctly. Each one is a directly improvable point.",
      font: FONT, size: 18, color: MGRAY, italics: true }),
  ]}));

  const emColW = [2000, 900, 2800, 3660];
  const emRows = [row(["QID", "Score", "Body System", "Blueprint"].map((h, i) => headerCell(h, emColW[i])))];
  for (const m of easyMisses) {
    emRows.push(row([
      dataCell(m.qid || `Item ${m.item}`, emColW[0], DGRAY, false, AlignmentType.LEFT),
      dataCell(m.score, emColW[1], m.score >= 900 ? RED : AMBER, true),
      dataCell(m.body_system_merged || m.body_system || "\u2014", emColW[2], DGRAY, false, AlignmentType.LEFT),
      dataCell(m.blueprint || "\u2014", emColW[3], DGRAY, false, AlignmentType.LEFT),
    ]));
  }
  children.push(makeTable(emColW, emRows));
}

// ────────────────────────────────────────────────────────────────────
// 7. LOW-HANGING FRUIT (yield-weighted priorities split by type)
// ────────────────────────────────────────────────────────────────────
children.push(spacer(200));
children.push(sectionBar("🍎 LOW-HANGING FRUIT — HIGHEST-YIELD IMPROVEMENT AREAS"));
children.push(spacer(80, true));

children.push(new Paragraph({ keepNext: true, spacing: { before: 0, after: 100 }, children: [
  new TextRun({
    text: "Ranked by (improvable items) × (exam weight). The top entry gives the most scaled score improvement per hour of study. " +
      "Blueprint and body system categories are listed separately so you can attack both dimensions.",
    font: FONT, size: 18, color: MGRAY, italics: true }),
]}));

if (yields && yields.length > 0) {
  const bpYields  = yields.filter(y => y.dimension_type === "blueprint");
  const bsYields  = yields.filter(y => y.dimension_type === "body_system");

  function yieldTable(rows_data, label) {
    if (rows_data.length === 0) return;
    children.push(new Paragraph({ spacing: { before: 80, after: 60 }, children: [
      new TextRun({ text: label, font: FONT, size: 22, bold: true, color: NAVY }),
    ]}));
    const yColW = [900, 3200, 1700, 1700, 1860];
    const yRows = [row(["Rank", "Category", "Improvable Items", "Exam Weight", "Priority Score"].map((h, i) => headerCell(h, yColW[i])))];
    rows_data.forEach((y, i) => {
      const name     = y.dimension || "";
      const recov    = y.recoverable_items != null ? y.recoverable_items.toFixed(1) : "\u2014";
      const weightPct = y.exam_weight_pct != null ? `${y.exam_weight_pct}%` : (y.exam_weight ? (y.exam_weight * 100).toFixed(0) + "%" : "\u2014");
      const score    = y.priority_score != null ? y.priority_score.toFixed(1) : "\u2014";
      const isTop    = i === 0;
      yRows.push(row([
        dataCell(`#${i + 1}`, yColW[0], NAVY, true),
        dataCell(name, yColW[1], isTop ? RED : DGRAY, true, AlignmentType.LEFT),
        dataCell(recov, yColW[2], isTop ? RED : DGRAY, isTop),
        dataCell(weightPct, yColW[3]),
        dataCell(score, yColW[4], BLUE, true),
      ]));
    });
    children.push(makeTable(yColW, yRows));
    children.push(spacer(80));
  }

  yieldTable(bpYields, "Blueprint Category — Improvement Priorities");
  yieldTable(bsYields, "Body System — Improvement Priorities");
} else {
  children.push(new Paragraph({ children: [
    new TextRun({ text: "Yield priorities not computed for this analysis run.", font: FONT, size: 20, color: MGRAY }),
  ]}));
}

// ────────────────────────────────────────────────────────────────────
// 7b. CATEGORY CROSSOVER WEAKNESSES
// ────────────────────────────────────────────────────────────────────
{
  const crossYields = (yields || []).filter(y => y.dimension_type === "cross_tab");
  const patterns    = data.cross_dimensional_patterns?.patterns || [];

  if (crossYields.length > 0 || patterns.length > 0) {
    children.push(spacer(180));
    children.push(sectionBar("⚡ CATEGORY CROSSOVER WEAKNESSES"));
    children.push(spacer(80, true));

    children.push(new Paragraph({ spacing: { before: 0, after: 100 }, children: [
      new TextRun({
        text: "Weaknesses that appear at the intersection of a blueprint category AND a body system. " +
          "These represent double-exposure gaps — areas where both the clinical domain and the exam competency are below threshold.",
        font: FONT, size: 18, color: MGRAY, italics: true }),
    ]}));

    // Cross-tab yield table
    if (crossYields.length > 0) {
      const cxColW = [900, 4200, 1500, 1400, 1360];
      const cxRows = [row(["Rank", "Intersection", "Improvable Items", "Exam Weight", "Priority"].map((h, i) => headerCell(h, cxColW[i])))];
      crossYields.slice(0, 8).forEach((y, i) => {
        const recov     = y.recoverable_items != null ? y.recoverable_items.toFixed(1) : "\u2014";
        const weightPct = y.exam_weight_pct != null ? `${y.exam_weight_pct}%` : "\u2014";
        const score     = y.priority_score != null ? y.priority_score.toFixed(1) : "\u2014";
        cxRows.push(row([
          dataCell(`#${i + 1}`, cxColW[0], NAVY, true),
          dataCell(y.dimension || "", cxColW[1], DGRAY, true, AlignmentType.LEFT),
          dataCell(recov, cxColW[2]),
          dataCell(weightPct, cxColW[3]),
          dataCell(score, cxColW[4], BLUE, true),
        ]));
      });
      children.push(makeTable(cxColW, cxRows));
      children.push(spacer(100));
    }

    // Narrative patterns
    if (patterns.length > 0) {
      children.push(new Paragraph({ spacing: { before: 60, after: 60 }, children: [
        new TextRun({ text: "Pattern Analysis", font: FONT, size: 22, bold: true, color: NAVY }),
      ]}));
      for (const p of patterns) {
        children.push(new Paragraph({ spacing: { before: 60, after: 60 }, indent: { left: 200 }, children: [
          new TextRun({ text: `\u2022  ${p.description || ""}`, font: FONT, size: 18, color: DGRAY }),
        ]}));
      }
    }
  }
}

// ────────────────────────────────────────────────────────────────────
// 8. CONCEPT FINGERPRINT
// ────────────────────────────────────────────────────────────────────
children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(sectionBar("\uD83D\uDCA1 CONCEPT FINGERPRINT"));
children.push(spacer(80, true));

if (concept) {
  // QID map per concept (added in v3.1 Python analyzer)
  const cqMap = concept.concept_qid_map || {};

  // Build concept tables from diagnoses, drugs, guidelines dicts
  const conceptSections = [
    { label: "Top Diagnoses in Missed Items", data: concept.top_diagnoses || concept.diagnoses || {}, qids: cqMap.diagnoses  || {} },
    { label: "Top Drugs in Missed Items",     data: concept.top_drugs     || concept.drugs     || {}, qids: cqMap.drugs      || {} },
    { label: "Top Guidelines in Missed Items",data: concept.top_guidelines|| concept.guidelines|| {}, qids: cqMap.guidelines || {} },
  ];

  for (const sec of conceptSections) {
    const entries = Object.entries(sec.data).sort((a, b) => b[1] - a[1]);
    if (entries.length === 0) continue;
    children.push(new Paragraph({ spacing: { before: 80, after: 80 }, children: [
      new TextRun({ text: sec.label, font: FONT, size: 22, bold: true, color: BLUE }),
    ]}));
    const hasQids = Object.keys(sec.qids).length > 0;
    const cColW = hasQids ? [3800, 1200, 4360] : [6500, 2860];
    const headers = hasQids ? ["Concept", "Frequency", "Question IDs"] : ["Concept", "Frequency"];
    const cRows = [row(headers.map((h, i) => headerCell(h, cColW[i])))];
    entries.slice(0, 10).forEach(([name, count]) => {
      const qidList = (sec.qids[name] || []).join(", ") || "\u2014";
      if (hasQids) {
        cRows.push(row([
          dataCell(name, cColW[0], DGRAY, false, AlignmentType.LEFT),
          dataCell(`${count}\u00D7`, cColW[1], count >= 3 ? RED : count >= 2 ? AMBER : NAVY, count >= 3),
          dataCell(qidList, cColW[2], MGRAY, false, AlignmentType.LEFT),
        ]));
      } else {
        cRows.push(row([
          dataCell(name, cColW[0], DGRAY, false, AlignmentType.LEFT),
          dataCell(`${count}\u00D7`, cColW[1], count >= 3 ? RED : count >= 2 ? AMBER : NAVY, count >= 3),
        ]));
      }
    });
    children.push(makeTable(cColW, cRows));
    children.push(spacer(80));
  }

  // Recurring themes (v3: recurring_diagnoses + recurring_drugs; v2: subcategory_distribution)
  const recurringDx    = concept.recurring_diagnoses || {};
  const recurringDrugs = concept.recurring_drugs     || {};
  const subcatDist     = concept.subcategory_distribution || {};  // v2 compat

  if (Object.keys(recurringDx).length > 0) {
    children.push(spacer(40));
    children.push(new Paragraph({ spacing: { before: 80, after: 80 }, children: [
      new TextRun({ text: "Recurring Diagnoses (2+ misses)", font: FONT, size: 22, bold: true, color: BLUE }),
    ]}));
    const rColW = [6500, 2860];
    const rRows = [row(["Diagnosis", "Miss Count"].map((h, i) => headerCell(h, rColW[i])))];
    Object.entries(recurringDx).forEach(([name, count]) => {
      rRows.push(row([
        dataCell(name, rColW[0], DGRAY, false, AlignmentType.LEFT),
        dataCell(`${count}\u00D7`, rColW[1], count >= 4 ? RED : count >= 2 ? AMBER : NAVY, count >= 4),
      ]));
    });
    children.push(makeTable(rColW, rRows));
  } else if (Object.keys(subcatDist).length > 0) {
    // v2 fallback
    children.push(spacer(40));
    children.push(new Paragraph({ spacing: { before: 80, after: 80 }, children: [
      new TextRun({ text: "Subcategory Distribution of Misses", font: FONT, size: 22, bold: true, color: BLUE }),
    ]}));
    const sColW = [6500, 2860];
    const sRows = [row(["Subcategory", "Misses"].map((h, i) => headerCell(h, sColW[i])))];
    Object.entries(subcatDist).sort((a, b) => b[1] - a[1]).forEach(([sub, count]) => {
      sRows.push(row([
        dataCell(sub, sColW[0], DGRAY, false, AlignmentType.LEFT),
        dataCell(count, sColW[1], count >= 15 ? RED : count >= 10 ? AMBER : DGRAY, count >= 10),
      ]));
    });
    children.push(makeTable(sColW, sRows));
  }

  // Dynamic study note
  const topDrugsAll = Object.entries(concept.top_drugs || concept.drugs || {}).sort((a, b) => b[1] - a[1]);
  const topDxAll    = Object.entries(concept.top_diagnoses || concept.diagnoses || {}).sort((a, b) => b[1] - a[1]);
  const dxNote = topDxAll.length >= 2
    ? `${topDxAll[0][0]} (${topDxAll[0][1]}\u00D7) and ${topDxAll[1][0]} (${topDxAll[1][1]}\u00D7) are the top recurring diagnoses in missed items.`
    : "";
  const drugNote = topDrugsAll.length >= 1 && topDrugsAll[0][1] >= 2
    ? ` Recurring drug cluster: ${topDrugsAll.slice(0, 3).map(d => `${d[0]} (${d[1]}\u00D7)`).join(", ")} — may represent a single reviewable pharmacology skill.`
    : "";
  if (dxNote) {
    children.push(studyNote(dxNote + drugNote));
  }
}

// ────────────────────────────────────────────────────────────────────
// 9. ICD-10 WEAKNESS MAP
// ────────────────────────────────────────────────────────────────────
children.push(spacer(200));
children.push(sectionBar("\uD83C\uDFE5 ICD-10 WEAKNESS MAP"));
children.push(spacer(80, true));

children.push(new Paragraph({ keepNext: true, spacing: { before: 40, after: 100 }, children: [
  new TextRun({ text: "Missed items mapped to ICD-10 codes via linked articles in the ITE Intelligence database. " +
    "Chapter rollup shows which clinical domains concentrate the most misses. " +
    "Individual codes identify specific conditions to review.",
    font: FONT, size: 18, color: MGRAY, italics: true }),
]}));

if (icd) {
  // All ICD-10 codes ranked by miss count — clean single table
  const allCodes = (icd.icd10_clusters || []).slice(0, 15);
  if (allCodes.length > 0) {
    const icColW = [1400, 5200, 900, 1860];
    const icRows = [row(["ICD-10 Code", "Condition", "Misses", "Clinical Domain"].map((h, i) => headerCell(h, icColW[i])))];
    const chDesc = {
      "I": "Infectious/Parasitic", "II": "Neoplasms", "III": "Blood/Immune",
      "IV": "Endocrine/Metabolic", "V": "Mental/Behavioral", "VI": "Nervous System",
      "IX": "Circulatory", "X": "Respiratory", "XI": "Digestive",
      "XII": "Skin", "XIII": "Musculoskeletal", "XIV": "Genitourinary",
      "XV": "OB/GYN", "XVIII": "Symptoms/Signs", "XIX": "Injury/Poisoning",
    };
    allCodes.forEach(c => {
      const domain = chDesc[c.chapter] || c.chapter_desc || c.chapter || "\u2014";
      const cnt = c.miss_count || c.count || 0;
      icRows.push(row([
        dataCell(c.code,        icColW[0], NAVY, true, AlignmentType.LEFT),
        dataCell(c.description, icColW[1], DGRAY, false, AlignmentType.LEFT),
        dataCell(`${cnt}\u00D7`, icColW[2], cnt >= 3 ? RED : cnt >= 2 ? AMBER : DGRAY, cnt >= 2),
        dataCell(domain,        icColW[3], MGRAY, false, AlignmentType.LEFT),
      ]));
    });
    children.push(makeTable(icColW, icRows));
  }
}

// ────────────────────────────────────────────────────────────────────
// 10. HIGH-YIELD READING LIST
// ────────────────────────────────────────────────────────────────────
// Set SKIP_READING_LIST=1 in env to omit this section from the report.
const SKIP_READING_LIST = process.env.SKIP_READING_LIST === "1";
if (!SKIP_READING_LIST) {
children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(sectionBar("\uD83D\uDCDA HIGH-YIELD READING LIST"));
children.push(spacer(80, true));

children.push(new Paragraph({ keepNext: true, spacing: { before: 40, after: 120 }, children: [
  new TextRun({ text: "Articles selected from the ITE Intelligence database by citation frequency, exam year span, " +
    "and direct relevance to identified weak areas. Prioritize in order listed.",
    font: FONT, size: 18, color: MGRAY, italics: true }),
]}));

if (articles.length > 0) {
  const aColW = [400, 5360, 1100, 1200, 1300];
  const aRows = [row(["#", "Article", "Citations", "Exam Yrs", "Weak Links"].map((h, i) => headerCell(h, aColW[i])))];
  articles.forEach((a, i) => {
    aRows.push(row([
      dataCell(i + 1, aColW[0], NAVY, true),
      multiLineCell([
        { text: a.title, bold: true, color: BLUE },
        { text: a.clean_ref || `${a.author1} (${a.year})`, size: 16, color: MGRAY },
        { text: a.article_id, size: 14, color: LGRAY },
      ], aColW[1]),
      dataCell(`${a.citation_count}\u00D7`, aColW[2], NAVY, true),
      dataCell(a.unique_years, aColW[3]),
      dataCell(a.weak_area_links, aColW[4], a.weak_area_links >= 3 ? RED : a.weak_area_links >= 1 ? AMBER : DGRAY, a.weak_area_links >= 3),
    ]));
  });
  children.push(makeTable(aColW, aRows));

  children.push(spacer(120));
  articles.forEach((a, i) => {
    children.push(new Paragraph({ spacing: { before: 60, after: 40 }, children: [
      new TextRun({ text: `${i + 1}. ${a.title}`, font: FONT, size: 20, bold: true, color: NAVY }),
    ]}));
    children.push(new Paragraph({ spacing: { before: 0, after: 60 }, indent: { left: 300 }, children: [
      new TextRun({ text: `Why read this: cited ${a.citation_count}\u00D7 across ${a.unique_years} exam year(s)` +
        (a.weak_area_links > 0 ? `, links to ${a.weak_area_links} weak area(s)` : "") +
        `. High-frequency citation = high probability of appearing on future exams.`,
        font: FONT, size: 18, color: MGRAY }),
    ]}));
  });

  children.push(studyNote(
    `Articles with multiple weak area links address multiple knowledge gaps per hour of reading. ` +
    `Use citation count as a proxy for exam question likelihood \u2014 ` +
    `if the ABFM has cited it ${articles[0]?.citation_count || 5}\u00D7, it will appear again.`
  ));
}
} // end SKIP_READING_LIST guard

// ────────────────────────────────────────────────────────────────────
// PART B: PRACTICE QUESTIONS (with answers, grouped by weak area)
// ────────────────────────────────────────────────────────────────────
children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(sectionBar("\u270F TARGETED PRACTICE QUESTIONS \u2014 BY WEAK AREA"));
children.push(spacer(60, true));

children.push(new Paragraph({ keepNext: true, spacing: { before: 40, after: 120 }, children: [
  new TextRun({ text: "Questions selected from the ITE Intelligence database (ITE + AAFP BRQ), ranked by relevance to each weak area. " +
    "In the resident-facing report, full question text, answer choices, and explanations populate here. " +
    "This version displays the selection reference table only.",
    font: FONT, size: 18, color: MGRAY, italics: true }),
]}));

// Match tier labels for question provenance
const TIER_LABELS = { 1: "Direct Match", 2: "ICD-10 Sibling", 3: "Vector Match" };
const TIER_COLORS = { 1: GREEN, 2: BLUE, 3: MGRAY };

// Split into single-category and cross-category, sorted by targeting within each group
const singleQs = allQuestions
  .filter(q => !(q.targeting || "").includes(" \u00D7 "))
  .sort((a, b) => (a.targeting || "").localeCompare(b.targeting || ""));
const crossQs = allQuestions
  .filter(q => (q.targeting || "").includes(" \u00D7 "))
  .sort((a, b) => (a.targeting || "").localeCompare(b.targeting || ""));

// Shared column layout — adds "Targeting" column, replaces per-dim subBar headers
// Cols: #, Targeting, QID, Blueprint, Body System, Source, Match  → total 9360 twips
const pqColW = [500, 2000, 1300, 1800, 1800, 1000, 960];
const PQ_HEADERS = ["#", "Targeting", "QID", "Blueprint", "Body System", "Source", "Match"];

function buildPqTable(questions, startNum) {
  const pqRows = [row(PQ_HEADERS.map((h, i) => headerCell(h, pqColW[i])))];
  questions.forEach((q, idx) => {
    const num = startNum + idx;
    const sourceLabel = q.source_bank === "AAFP" ? "AAFP BRQ" : `ITE ${q.exam_year || ""}`.trim();
    const tierLabel   = TIER_LABELS[q.match_tier] || "\u2014";
    const tierColor   = TIER_COLORS[q.match_tier] || MGRAY;
    pqRows.push(row([
      dataCell(String(num),                      pqColW[0], NAVY, true),
      dataCell(q.targeting || "\u2014",           pqColW[1], BLUE, false, AlignmentType.LEFT),
      dataCell(q.qid || "\u2014",                 pqColW[2], DGRAY, false, AlignmentType.LEFT),
      dataCell(q.blueprint || "\u2014",           pqColW[3], DGRAY, false, AlignmentType.LEFT),
      dataCell(q.body_system_merged || "\u2014",  pqColW[4], DGRAY, false, AlignmentType.LEFT),
      dataCell(sourceLabel,                       pqColW[5], MGRAY, false, AlignmentType.LEFT),
      dataCell(tierLabel,                         pqColW[6], tierColor, false, AlignmentType.LEFT),
    ]));
  });
  return makeTable(pqColW, pqRows);
}

let globalQNum = 1;

// Table 1: Single weak-area questions
if (singleQs.length > 0) {
  children.push(spacer(120));
  children.push(subBar(`\u26A0 SINGLE WEAK AREA QUESTIONS  (${singleQs.length})`, BLUE));
  children.push(buildPqTable(singleQs, globalQNum));
  globalQNum += singleQs.length;
}

// Table 2: Cross-category questions
if (crossQs.length > 0) {
  children.push(spacer(120));
  children.push(subBar(`CROSS-CATEGORY INTERSECTIONS  (${crossQs.length})`, "4A5568"));
  children.push(buildPqTable(crossQs, globalQNum));
}

// ────────────────────────────────────────────────────────────────────
// APPENDIX: MISSED EXAM ITEMS (reference — full question text + answer)
// ────────────────────────────────────────────────────────────────────
const missedItems = data.missed_items_detail || [];
if (missedItems.length > 0) {
  children.push(new Paragraph({ children: [new PageBreak()] }));
  children.push(sectionBar("📋 APPENDIX — MISSED EXAM ITEMS"));
  children.push(spacer(60, true));

  children.push(new Paragraph({ keepNext: true, spacing: { before: 40, after: 120 }, children: [
    new TextRun({
      text: `${missedItems.length} items answered incorrectly. ` +
            "Reference table — use QIDs to locate questions in the practice section above.",
      font: FONT, size: 18, color: MGRAY, italics: true,
    }),
  ]}));

  const appColW = [900, 1900, 2800, 2800, 960];
  const appRows = [row(["Item #", "QID", "Blueprint", "Body System", "Status"].map((h, i) => headerCell(h, appColW[i])))];
  for (const m of missedItems) {
    const status = m.db_found ? "Linked" : "No record";
    appRows.push(row([
      dataCell(String(m.item_number), appColW[0], DGRAY, true),
      dataCell(m.qid || "\u2014", appColW[1], BLUE, false, AlignmentType.LEFT),
      dataCell(m.blueprint || "\u2014", appColW[2], DGRAY, false, AlignmentType.LEFT),
      dataCell(m.body_system || "\u2014", appColW[3], DGRAY, false, AlignmentType.LEFT),
      dataCell(status, appColW[4], m.db_found ? MGRAY : RED, false),
    ]));
  }
  children.push(makeTable(appColW, appRows));
}

// ═══════════════════════════════════════════════════════════════════
// ASSEMBLE ANALYSIS DOC
// ═══════════════════════════════════════════════════════════════════
function makeDocShell(docChildren, headerText, footerText) {
  return new Document({
    styles: {
      default: { document: { run: { font: FONT, size: 20 } } },
      paragraphStyles: [
        { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: { size: 28, bold: true, font: FONT, color: NAVY }, paragraph: { spacing: { before: 240, after: 120 }, outlineLevel: 0 } },
        { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: { size: 24, bold: true, font: FONT, color: BLUE }, paragraph: { spacing: { before: 180, after: 100 }, outlineLevel: 1 } },
      ],
    },
    sections: [{
      properties: {
        page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } },
      },
      headers: { default: new Header({ children: [
        new Paragraph({ alignment: AlignmentType.RIGHT, children: [
          new TextRun({ text: headerText, font: FONT, size: 16, color: LGRAY }),
        ]}),
      ]}) },
      footers: { default: new Footer({ children: [
        new Paragraph({
          alignment: AlignmentType.RIGHT,
          spacing: { before: 60 },
          children: [
            new TextRun({ text: "Page ", font: FONT, size: 14, color: LGRAY }),
            new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 14, color: LGRAY }),
          ],
        }),
      ]}) },
      children: docChildren,
    }],
  });
}

const analysisDoc = makeDocShell(children, `ITE ${data.exam_year} Score Analysis`, "");

// ═══════════════════════════════════════════════════════════════════
// PART C: EXAM VERSION
// ═══════════════════════════════════════════════════════════════════
const examChildren = [];
const answerKey = [];

examChildren.push(new Paragraph({ spacing: { before: 600, after: 0 }, alignment: AlignmentType.CENTER, children: [
  new TextRun({ text: `ITE ${data.exam_year} PRACTICE EXAM`, font: FONT, size: 36, bold: true, color: NAVY }),
]}));
examChildren.push(new Paragraph({ spacing: { before: 80, after: 0 }, alignment: AlignmentType.CENTER, children: [
  new TextRun({ text: `ITE ${data.exam_year} — Targeted Practice`, font: FONT, size: 22, color: BLUE }),
]}));
examChildren.push(new Paragraph({ spacing: { before: 60, after: 0 }, alignment: AlignmentType.CENTER, children: [
  new TextRun({ text: `${allQuestions.length} questions targeted to weak areas  |  Answer key at end`, font: FONT, size: 18, color: MGRAY }),
]}));
examChildren.push(spacer(200));

let examNum = 0;

function renderExamSection(questions, sectionLabel, sectionColor) {
  if (questions.length === 0) return;
  examChildren.push(spacer(100));
  examChildren.push(subBar(sectionLabel, sectionColor));
  for (const q of questions) {
    examNum++;
    answerKey.push({ num: examNum, qid: q.qid, letter: q.correct_letter, text: q.correct_text || "", target: q.targeting || "", body: q.body_system_merged || "" });

    examChildren.push(new Paragraph({ spacing: { before: 180, after: 40 }, children: [
      new TextRun({ text: `Question ${examNum}`, font: FONT, size: 22, bold: true, color: NAVY }),
      new TextRun({ text: `  ${q.qid}`, font: FONT, size: 18, color: MGRAY }),
      new TextRun({ text: `  \u2014  ${q.targeting || ""}`, font: FONT, size: 16, color: LGRAY, italics: true }),
    ]}));

    examChildren.push(new Paragraph({ spacing: { before: 80, after: 80 }, children: [
      new TextRun({ text: q.question_text || "", font: FONT, size: 20, color: DGRAY }),
    ]}));

    let choices = q.choices || [];
    if (typeof choices === "string") { try { choices = JSON.parse(choices); } catch { choices = []; } }
    choices.forEach(c => {
      examChildren.push(new Paragraph({ spacing: { before: 30, after: 30 }, indent: { left: 360 }, children: [
        new TextRun({ text: `${c.letter}. ${c.text}`, font: FONT, size: 20, color: DGRAY }),
      ]}));
    });
  }
}

renderExamSection(singleQs, `\u26A0 SINGLE WEAK AREA QUESTIONS  (${singleQs.length})`, BLUE);
renderExamSection(crossQs,  `CROSS-CATEGORY INTERSECTIONS  (${crossQs.length})`, "4A5568");

// Answer key
examChildren.push(new Paragraph({ children: [new PageBreak()] }));
examChildren.push(sectionBar("ANSWER KEY"));
examChildren.push(spacer(80));

const akColW = [500, 1800, 800, 2600, 3660];
const akRows = [row(["#", "QID", "Answer", "Target Area", "Body System"].map((h, i) => headerCell(h, akColW[i])))];
answerKey.forEach(a => {
  akRows.push(row([
    dataCell(a.num, akColW[0], NAVY, true),
    dataCell(a.qid, akColW[1], DGRAY, false, AlignmentType.LEFT),
    dataCell(a.letter, akColW[2], GREEN, true),
    dataCell(a.target, akColW[3], DGRAY, false, AlignmentType.LEFT),
    dataCell(a.body, akColW[4], MGRAY, false, AlignmentType.LEFT),
  ]));
});
examChildren.push(makeTable(akColW, akRows));

const examDoc = makeDocShell(examChildren, `ITE ${data.exam_year} Practice Exam`, "ITE Practice Exam");

// ═══════════════════════════════════════════════════════════════════
// WRITE BOTH FILES AND PRINT SUMMARY
// ═══════════════════════════════════════════════════════════════════

Promise.all([
  Packer.toBuffer(analysisDoc).then(buf => {
    fs.writeFileSync(analysisPath, buf);
  }),
  Packer.toBuffer(examDoc).then(buf => {
    fs.writeFileSync(examPath, buf);
  }),
]).then(() => {
  // Build warnings string
  const warningsStr = warnings.length > 0 ? warnings.join(", ") : "none";

  console.log("\nITE Report Builder v2");
  console.log(`  Input:    ${inputPath}`);
  console.log(`  Analysis: ${analysisPath}`);
  console.log(`  Exam:     ${examPath}`);
  console.log(`  Sections: 10 + Practice Questions + Exam`);
  console.log(`  Weak areas: ${weakList}`);
  const tierCounts = { 1: 0, 2: 0, 3: 0 };
  allQuestions.forEach(q => { if (q.match_tier) tierCounts[q.match_tier]++; });
  const tierStr = `T1:${tierCounts[1]} T2:${tierCounts[2]} T3:${tierCounts[3]}`;
  console.log(`  Questions: ${allQuestions.length} (${Math.round(allQuestions.length / weakBlueprints.length || 0)} per weak area)`);
  console.log(`  Match tiers: ${tierStr}`);
  console.log(`  Warnings: ${warningsStr}\n`);

  process.exit(0);
}).catch(err => {
  console.error("\nERROR: Failed to write output files");
  console.error(`  ${err.message}\n`);
  process.exit(1);
});
