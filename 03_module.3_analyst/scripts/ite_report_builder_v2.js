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
  tone: "clinical precision with actionable clarity — every finding leads to a recommendation, every weakness maps to a recovery path",
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
        children: [new Paragraph({ spacing: { before: 0, after: 0 }, children: [
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
        children: [new Paragraph({ children: [
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
function spacer(pts = 100) {
  return new Paragraph({ spacing: { before: pts, after: 0 }, children: [] });
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

// ── Build output filenames ──────────────────────────────────────────
const ver = analysisVer.startsWith("3") ? "v3" : "v2";
const analysisFileName = `ITE_${data.exam_year}_${ver}_Analysis_${safeName}.docx`;
const examFileName = `ITE_${data.exam_year}_${ver}_Exam_${safeName}.docx`;
const analysisPath = path.join(outputDir, analysisFileName);
const examPath = path.join(outputDir, examFileName);

// ── Identify weak areas ─────────────────────────────────────────────
const weakBlueprints = [];
for (const [cat, cls] of Object.entries(t2.classifications || {})) {
  if (cls.classification === "relative_weakness") weakBlueprints.push(cat);
}
for (const [cat, vals] of Object.entries(perf.blueprint)) {
  if (vals.rate < 0.70 && !weakBlueprints.includes(cat)) weakBlueprints.push(cat);
}

// ── Group questions by targeting (weak area) ────────────────────────
const qByTarget = {};
for (const q of allQuestions) {
  const target = q.targeting || "General";
  if (!qByTarget[target]) qByTarget[target] = [];
  qByTarget[target].push(q);
}

// Collect warnings for 5+ per weak area
const warnings = [];
for (const wb of weakBlueprints) {
  const count = (qByTarget[wb] || []).length;
  if (count < 5) {
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
children.push(new Paragraph({ spacing: { before: 80, after: 0 }, alignment: AlignmentType.CENTER, children: [
  new TextRun({ text: res.name, font: FONT, size: 26, color: BLUE }),
]}));
children.push(new Paragraph({ spacing: { before: 40, after: 0 }, alignment: AlignmentType.CENTER, children: [
  new TextRun({ text: `ABFM ID: ${res.abfm_id}  |  ${res.program}`, font: FONT, size: 18, color: MGRAY }),
]}));
children.push(spacer(300));

// Score display
children.push(makeTable([3120, 3120, 3120], [row([
  new TableCell({ borders: noBorders(), width: { size: 3120, type: WidthType.DXA }, verticalAlign: VerticalAlign.CENTER, children: [
    new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: `${perf.overall.pct}%`, font: FONT, size: 56, bold: true, color: NAVY })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: `${perf.overall.correct}/${perf.overall.total} correct`, font: FONT, size: 18, color: MGRAY })] }),
  ]}),
  new TableCell({ borders: noBorders(), width: { size: 3120, type: WidthType.DXA }, verticalAlign: VerticalAlign.CENTER, children: [
    new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: `${t1.scaled_score}`, font: FONT, size: 56, bold: true, color: BLUE })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Scaled Score", font: FONT, size: 18, color: MGRAY })] }),
  ]}),
  new TableCell({ borders: noBorders(), width: { size: 3120, type: WidthType.DXA }, verticalAlign: VerticalAlign.CENTER,
    shading: { fill: NAVY, type: ShadingType.CLEAR }, margins: { top: 100, bottom: 100, left: 100, right: 100 }, children: [
    new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: tierBadge(t1.pass_tier.tier), font: FONT, size: 28, bold: true, color: WHITE })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: `${t1.percentile_estimate}th percentile`, font: FONT, size: 18, color: WHITE })] }),
  ]}),
])]));
children.push(spacer(100));
children.push(new Paragraph({ spacing: { before: 80, after: 0 }, alignment: AlignmentType.CENTER, children: [
  new TextRun({ text: `vs MPS (380): +${t1.vs_mps}  |  vs PGY2 National Mean (${t1.national_mean}): +${t1.scaled_score - t1.national_mean}  |  N = 15,382`, font: FONT, size: 18, color: MGRAY }),
]}));

// ────────────────────────────────────────────────────────────────────
// 2. EXECUTIVE SUMMARY
// ────────────────────────────────────────────────────────────────────
children.push(spacer(200));
children.push(sectionBar("\u2605 EXECUTIVE SUMMARY"));
children.push(spacer(60));
// Dynamic executive summary
const personalMean = t2.thresholds?.personal_mean || 0;
const personalMeanPct = (personalMean * 100).toFixed(1);
const bpEntries = Object.entries(perf.blueprint).sort((a, b) => a[1].rate - b[1].rate);
const worstBp = bpEntries[0];
const bestBp = bpEntries[bpEntries.length - 1];
const worstSem = t3?.[worstBp[0]]?.sem ? ` (SEM \u00B1${t3[worstBp[0]].sem})` : "";
const topYield = yields?.[0];
const topYieldText = topYield
  ? `Highest-yield recovery: ${topYield.dimension} = ${topYield.recoverable_items?.toFixed(1) || "?"} recoverable items at ${topYield.exam_weight_pct || "?"}% exam weight.`
  : "";

children.push(studyNote(
  `Dr. ${safeName} scored ${t1.scaled_score} (${t1.percentile_estimate}th percentile), ` +
  `placing in the "${tierBadge(t1.pass_tier.tier)}" tier. ` +
  `Weak areas identified: ${weakList}. ` +
  `${worstBp[0]} is the lowest-performing category at ${(worstBp[1].rate * 100).toFixed(1)}% ` +
  `(vs personal mean ${personalMeanPct}%)${worstSem}, ` +
  `while ${bestBp[0]} is the strongest at ${(bestBp[1].rate * 100).toFixed(1)}%. ` +
  `${diff.easy_miss_count || 0} easy misses (\u2265700 difficulty) represent the most recoverable knowledge gaps. ` +
  `${topYieldText} ` +
  `This report provides targeted practice questions for each weak area (min. 5 per section), ranked by fit, ` +
  `plus a separate exam version for timed self-assessment.`
));

// ────────────────────────────────────────────────────────────────────
// 3. TERM KEY
// ────────────────────────────────────────────────────────────────────
children.push(spacer(200));
children.push(sectionBar("\uD83D\uDCD6 TERM KEY"));
children.push(spacer(80));

const termDefs = [
  // ITE Subcategories
  ["Management", "Clinical decision-making: what is the most appropriate next step? May include observation, referral, monitoring \u2014 not necessarily a prescription."],
  ["Pharmacology", "Drug-specific knowledge: which medication, dose, mechanism, contraindication, or side effect? Always a pharmacologic answer."],
  ["Diagnosis", "Pattern recognition: given the clinical data presented, what condition does this patient have? The evidence is already in front of you."],
  ["Workup", "Evaluation sequence: what test, lab, or imaging do you order next? The diagnosis is not yet established \u2014 you are gathering data."],
  ["Screening", "Population-level detection: which test do you perform in an asymptomatic patient based on age, sex, or risk factors?"],
  ["Prevention", "Risk reduction: what intervention prevents disease onset or progression? Includes vaccines, lifestyle counseling, chemoprophylaxis."],
  ["Counseling", "Patient communication: what do you tell the patient about their condition, prognosis, or treatment plan?"],
  ["Prognosis/Risk", "Outcome prediction: what is the expected clinical course, complication risk, or mortality for this condition?"],
  ["Pathophysiology", "Mechanism of disease: what biological process explains the patient\u2019s symptoms, lab findings, or imaging?"],
  // Scoring Terms
  ["Scaled Score", "Equated score (200\u2013800) derived from raw score via Rasch model. Allows comparison across exam years. MPS = 380."],
  ["MPS", "Minimum Passing Standard. Scaled score of 380 = threshold for FMCE pass probability. Set by ABFM annually."],
  ["SEM", "Standard Error of Measurement. Quantifies score precision per dimension. Large SEM (\u2265100) = interpret as hypothesis only."],
  ["Pass Probability Tier", "FMCE pass likelihood bucket: Critical Risk (<380), At Risk (380\u2013419), On Track (420\u2013479), Strong (480+)."],
  ["Relative Weakness", "Blueprint category performing >1 SD below the resident\u2019s personal mean. Statistically anchored, not an arbitrary cutoff."],
  ["Relative Strength", "Blueprint category performing >1 SD above the resident\u2019s personal mean."],
  ["Difficulty Score", "ABFM item difficulty (0\u20131000). Easy (\u2265700) = most examinees correct. Mid (300\u2013699) = discriminating. Hard (<300) = most miss."],
  ["Yield-Weighted Priority", "Weakness rank ordered by (recoverable items) \u00D7 (exam weight). Higher rank = more scaled score points per study hour."],
  ["ICD-10", "International Classification of Diseases, 10th Revision. Used here to map missed items to clinical disease categories."],
];

const tkColW = [2200, 7160];
const tkRows = [row([headerCell("Term", tkColW[0]), headerCell("Definition", tkColW[1])])];
termDefs.forEach(([term, def]) => {
  tkRows.push(row([
    dataCell(term, tkColW[0], NAVY, true, AlignmentType.LEFT),
    dataCell(def, tkColW[1], DGRAY, false, AlignmentType.LEFT),
  ]));
});
children.push(makeTable(tkColW, tkRows));

// ────────────────────────────────────────────────────────────────────
// 4. BLUEPRINT PERFORMANCE
// ────────────────────────────────────────────────────────────────────
children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(sectionBar("\u2606 BLUEPRINT CATEGORY PERFORMANCE"));
children.push(spacer(80));

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
// Dynamic SEM commentary
const semNotes = Object.entries(t3 || {}).map(([cat, s]) => {
  const label = s.reliable ? "reliable" : "hypothesis only";
  return `${cat} (\u00B1${s.sem} SEM = ${label})`;
});
children.push(studyNote(
  `ABFM caution: sub-scores are NOT sufficiently precise to confirm knowledge deficiencies. ` +
  `${semNotes.join(". ")}. ` +
  `Weak areas (${weakList}) receive \u22655 targeted practice questions in Part B.`
));

// ────────────────────────────────────────────────────────────────────
// 5. SUBCATEGORY DECOMPOSITION
// ────────────────────────────────────────────────────────────────────
children.push(spacer(200));
children.push(sectionBar("\uD83D\uDD2C SUBCATEGORY DECOMPOSITION"));
children.push(spacer(80));

children.push(new Paragraph({ spacing: { before: 40, after: 100 }, children: [
  new TextRun({ text: "Performance by clinical skill type (Management, Pharmacology, Diagnosis, etc.) within each blueprint category. " +
    "Color coding: ",
    font: FONT, size: 18, color: MGRAY, italics: true }),
  new TextRun({ text: "red", font: FONT, size: 18, color: RED, italics: true, bold: true }),
  new TextRun({ text: " below 50%, ", font: FONT, size: 18, color: MGRAY, italics: true }),
  new TextRun({ text: "amber", font: FONT, size: 18, color: AMBER, italics: true, bold: true }),
  new TextRun({ text: " below 70%, ", font: FONT, size: 18, color: MGRAY, italics: true }),
  new TextRun({ text: "green", font: FONT, size: 18, color: GREEN, italics: true, bold: true }),
  new TextRun({ text: " at or above 70%.", font: FONT, size: 18, color: MGRAY, italics: true }),
]}));

// subcatAnalysis: v2-era plugin; undefined in v3 -- default to null so optional chaining is safe
const subcatAnalysis = data.plugins?.subcategory_decomposition || data.subcategory_analysis || null;
// Named subcategory data (from v2 analyzer with DB lookup)
const bpSubcat = subcatAnalysis?.by_blueprint_subcategory || subcatAnalysis?.by_blueprint_subcol || {};
if (Object.keys(bpSubcat).length > 0) {
  for (const [bp, subcats] of Object.entries(bpSubcat)) {
    const isWeak = weakBlueprints.includes(bp);
    children.push(spacer(80));
    children.push(new Paragraph({ spacing: { before: 60, after: 60 }, children: [
      new TextRun({ text: bp, font: FONT, size: 22, bold: true, color: isWeak ? RED : BLUE }),
    ]}));

    // Build table: Subcategory | Correct | Rate
    const scColW = [3200, 2080, 2080, 2000];
    const entries = Object.entries(subcats).sort((a, b) => b[1].total - a[1].total);
    const scRows = [row(["Subcategory", "Correct", "Total", "Rate"].map((h, i) => headerCell(h, scColW[i])))];

    for (const [subcat, vals] of entries) {
      const r = vals.rate;
      scRows.push(row([
        dataCell(subcat, scColW[0], DGRAY, false, AlignmentType.LEFT),
        dataCell(`${vals.correct}`, scColW[1]),
        dataCell(`${vals.total}`, scColW[2]),
        dataCell((r * 100).toFixed(0) + "%", scColW[3], rateColor(r), true),
      ]));
    }

    children.push(makeTable(scColW, scRows));
  }

  // Overall subcategory performance
  const overallSubcat = subcatAnalysis?.overall_subcategory || {};
  if (Object.keys(overallSubcat).length > 0) {
    children.push(spacer(100));
    children.push(new Paragraph({ spacing: { before: 60, after: 60 }, children: [
      new TextRun({ text: "Overall Subcategory Performance (All Blueprints)", font: FONT, size: 22, bold: true, color: NAVY }),
    ]}));

    const oColW = [3200, 2080, 2080, 2000];
    const oRows = [row(["Subcategory", "Correct", "Total", "Rate"].map((h, i) => headerCell(h, oColW[i])))];
    for (const [subcat, vals] of Object.entries(overallSubcat)) {
      const r = vals.rate;
      oRows.push(row([
        dataCell(subcat, oColW[0], DGRAY, false, AlignmentType.LEFT),
        dataCell(`${vals.correct}`, oColW[1]),
        dataCell(`${vals.total}`, oColW[2]),
        dataCell((r * 100).toFixed(0) + "%", oColW[3], rateColor(r), true),
      ]));
    }
    children.push(makeTable(oColW, oRows));
  }

  children.push(studyNote(
    `The subcategory breakdown reveals WHAT TYPE of clinical reasoning drives your misses within each blueprint. ` +
    `For example, low Pharmacology rates suggest medication knowledge gaps, while low Diagnosis rates point to ` +
    `pattern recognition deficits. Cross-reference with the Concept Fingerprint to identify specific clinical topics.`
  ));
}

// ────────────────────────────────────────────────────────────────────
// 6. DIFFICULTY PROFILE
// ────────────────────────────────────────────────────────────────────
children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(sectionBar("\u26A1 DIFFICULTY PROFILE"));
children.push(spacer(80));

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
children.push(studyNote(
  `${diff.easy_miss_count || 23} easy misses = genuine knowledge gaps on items most examinees answer correctly. ` +
  `These are the highest-yield recovery targets. ` +
  `${diff.mid_range_count || 34} mid-range misses = the volume play for score improvement. ` +
  `${diff.hard_miss_count || 9} hard misses = low-yield to chase.`
));

// Easy misses detail table
const easyMisses = diff.easy_misses || [];
if (easyMisses.length > 0) {
  children.push(spacer(120));
  children.push(new Paragraph({ spacing: { before: 60, after: 60 }, children: [
    new TextRun({ text: `Easy Misses \u2014 ${easyMisses.length} Items (Score \u2265 700)`, font: FONT, size: 22, bold: true, color: RED }),
  ]}));
  children.push(new Paragraph({ spacing: { before: 0, after: 80 }, children: [
    new TextRun({ text: "Most examinees answered these correctly. Each one is a recoverable point.",
      font: FONT, size: 18, color: MGRAY, italics: true }),
  ]}));

  const emColW = [1600, 900, 2200, 2200, 2460];
  const emRows = [row(["QID", "Score", "Body System", "Blueprint", "Subcategory"].map((h, i) => headerCell(h, emColW[i])))];
  for (const m of easyMisses) {
    emRows.push(row([
      dataCell(m.qid || `Item ${m.item}`, emColW[0], DGRAY, false, AlignmentType.LEFT),
      dataCell(m.score, emColW[1], m.score >= 900 ? RED : AMBER, true),
      dataCell(m.body_system_merged || m.body_system || "\u2014", emColW[2], DGRAY, false, AlignmentType.LEFT),
      dataCell(m.blueprint || "\u2014", emColW[3], DGRAY, false, AlignmentType.LEFT),
      dataCell(m.subcategory || "\u2014", emColW[4], DGRAY, false, AlignmentType.LEFT),
    ]));
  }
  children.push(makeTable(emColW, emRows));
}

// ────────────────────────────────────────────────────────────────────
// 7. YIELD-WEIGHTED PRIORITIES
// ────────────────────────────────────────────────────────────────────
children.push(spacer(200));
children.push(sectionBar("\u2B06 YIELD-WEIGHTED PRIORITIES"));
children.push(spacer(80));

if (yields && yields.length > 0) {
  const yColW = [900, 2800, 1900, 1900, 1860];
  const yRows = [row(["Priority", "Category", "Recoverable Items", "Exam Weight", "Scaled Pts"].map((h, i) => headerCell(h, yColW[i])))];
  yields.forEach((y, i) => {
    const name = y.dimension || y.category || y.blueprint || "";
    const recov = y.recoverable_items != null ? y.recoverable_items.toFixed(1) : "\u2014";
    const weightPct = y.exam_weight_pct != null ? `${y.exam_weight_pct}%` : (y.exam_weight ? (y.exam_weight * 100).toFixed(0) + "%" : "\u2014");
    const scaledPts = y.priority_score != null ? `~${y.priority_score.toFixed(1)}` : (y.scaled_point_value ? `~${y.scaled_point_value.toFixed(0)}` : "\u2014");
    yRows.push(row([
      dataCell(`#${i + 1}`, yColW[0], NAVY, true),
      dataCell(name, yColW[1], DGRAY, true, AlignmentType.LEFT),
      dataCell(recov, yColW[2]),
      dataCell(weightPct, yColW[3]),
      dataCell(scaledPts, yColW[4], BLUE, true),
    ]));
  });
  children.push(makeTable(yColW, yRows));
  children.push(studyNote(
    `Priorities ranked by (recoverable items) \u00D7 (exam weight). ` +
    `The #1 priority yields the most scaled score improvement per study hour. ` +
    `Allocate study time proportionally to this ranking.`
  ));
} else {
  children.push(new Paragraph({ children: [
    new TextRun({ text: "Yield priorities not computed for this analysis run.", font: FONT, size: 20, color: MGRAY }),
  ]}));
}

// ────────────────────────────────────────────────────────────────────
// 8. CONCEPT FINGERPRINT
// ────────────────────────────────────────────────────────────────────
children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(sectionBar("\uD83D\uDCA1 CONCEPT FINGERPRINT"));
children.push(spacer(80));

if (concept) {
  // Build concept tables from diagnoses, drugs, guidelines dicts
  // v3: top_diagnoses/top_drugs/top_guidelines; v2 fallback: diagnoses/drugs/guidelines
  const conceptSections = [
    { label: "Top Diagnoses in Missed Items", data: concept.top_diagnoses || concept.diagnoses || {} },
    { label: "Top Drugs in Missed Items",     data: concept.top_drugs     || concept.drugs     || {} },
    { label: "Top Guidelines in Missed Items",data: concept.top_guidelines|| concept.guidelines|| {} },
  ];

  for (const sec of conceptSections) {
    const entries = Object.entries(sec.data).sort((a, b) => b[1] - a[1]);
    if (entries.length === 0) continue;
    children.push(new Paragraph({ spacing: { before: 80, after: 80 }, children: [
      new TextRun({ text: sec.label, font: FONT, size: 22, bold: true, color: BLUE }),
    ]}));
    const cColW = [6500, 2860];
    const cRows = [row(["Concept", "Frequency"].map((h, i) => headerCell(h, cColW[i])))];
    entries.slice(0, 10).forEach(([name, count]) => {
      cRows.push(row([
        dataCell(name, cColW[0], DGRAY, false, AlignmentType.LEFT),
        dataCell(`${count}\u00D7`, cColW[1], count >= 3 ? RED : count >= 2 ? AMBER : NAVY, count >= 3),
      ]));
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
children.push(spacer(80));

children.push(new Paragraph({ spacing: { before: 40, after: 100 }, children: [
  new TextRun({ text: "Missed items mapped to ICD-10 codes via linked articles in the ITE Intelligence database. " +
    "Chapter rollup shows which clinical domains concentrate the most misses. " +
    "Individual codes identify specific conditions to review.",
    font: FONT, size: 18, color: MGRAY, italics: true }),
]}));

if (icd) {
  // Chapter summary table
  const chapterSummary = icd.chapter_summary || {};
  if (Object.keys(chapterSummary).length > 0) {
    children.push(new Paragraph({ spacing: { before: 80, after: 80 }, children: [
      new TextRun({ text: "ICD-10 Chapter Rollup", font: FONT, size: 22, bold: true, color: BLUE }),
    ]}));

    const chColW = [1200, 5800, 1180, 1180];
    const chRows = [row(["Chapter", "Description", "Codes", "% of Total"].map((h, i) => headerCell(h, chColW[i])))];

    const chapterDescs = {
      "I": "Infectious/Parasitic", "II": "Neoplasms", "III": "Blood/Immune",
      "IV": "Endocrine/Metabolic", "V": "Mental/Behavioral", "VI": "Nervous System",
      "VII-VIII": "Eye and Ear", "IX": "Circulatory", "X": "Respiratory",
      "XI": "Digestive", "XII": "Skin/Subcutaneous", "XIII": "Musculoskeletal",
      "XIV": "Genitourinary", "XV": "Pregnancy/Childbirth", "XVI": "Perinatal",
      "XVII": "Congenital", "XVIII": "Symptoms/Signs", "XIX": "Injury/Poisoning",
      "XX": "External Causes", "XXI": "Factors/Health Status",
    };

    const totalCodes = icd.total_codes_found || Object.values(chapterSummary).reduce((a, b) => a + b, 0);
    const sorted = Object.entries(chapterSummary).sort((a, b) => b[1] - a[1]);
    sorted.forEach(([ch, count]) => {
      const pct = ((count / totalCodes) * 100).toFixed(1) + "%";
      chRows.push(row([
        dataCell(ch, chColW[0], NAVY, true),
        dataCell(chapterDescs[ch] || ch, chColW[1], DGRAY, false, AlignmentType.LEFT),
        dataCell(count, chColW[2], count >= 7 ? RED : count >= 4 ? AMBER : DGRAY, count >= 7),
        dataCell(pct, chColW[3]),
      ]));
    });
    children.push(makeTable(chColW, chRows));
  }

  // Top individual codes
  // v3: miss_count; v2: count
  const topCodes = (icd.icd10_clusters || []).filter(c => (c.miss_count || c.count || 0) >= 2);
  if (topCodes.length > 0) {
    children.push(spacer(120));
    children.push(new Paragraph({ spacing: { before: 80, after: 80 }, children: [
      new TextRun({ text: "High-Frequency ICD-10 Codes (appearing 2+ times)", font: FONT, size: 22, bold: true, color: BLUE }),
    ]}));

    const icColW = [1200, 5200, 1480, 1480];
    const icRows = [row(["Code", "Description", "Count", "Chapter"].map((h, i) => headerCell(h, icColW[i])))];
    topCodes.forEach(c => {
      icRows.push(row([
        dataCell(c.code, icColW[0], NAVY, true, AlignmentType.LEFT),
        dataCell(c.description, icColW[1], DGRAY, false, AlignmentType.LEFT),
        dataCell(`${c.miss_count || c.count}\u00D7`, icColW[2], RED, true),
        dataCell(c.chapter, icColW[3]),
      ]));
    });
    children.push(makeTable(icColW, icRows));
  }

  // Dynamic ICD-10 study note from chapter summary
  const chapterDescsNote = {
    "I": "Infectious/Parasitic", "II": "Neoplasms", "III": "Blood/Immune",
    "IV": "Endocrine/Metabolic", "V": "Mental/Behavioral", "VI": "Nervous System",
    "VII-VIII": "Eye and Ear", "IX": "Circulatory", "X": "Respiratory",
    "XI": "Digestive", "XII": "Skin/Subcutaneous", "XIII": "Musculoskeletal",
    "XIV": "Genitourinary", "XV": "Pregnancy/Childbirth", "XVI": "Perinatal",
    "XVII": "Congenital", "XVIII": "Symptoms/Signs", "XIX": "Injury/Poisoning",
    "XX": "External Causes", "XXI": "Factors/Health Status",
  };
  const sortedChapters = Object.entries(chapterSummary).sort((a, b) => b[1] - a[1]);
  const top3 = sortedChapters.slice(0, 3).map(([ch, cnt]) => `${chapterDescsNote[ch] || ch} (Ch ${ch}: ${cnt} codes)`);
  const topCodesNote = topCodes.slice(0, 3).map(c => `${c.code} (${c.description})`).join(", ");
  children.push(studyNote(
    (top3.length >= 2 ? `${top3[0]} and ${top3[1]} dominate the ICD-10 map` + (top3[2] ? `. ${top3[2]} rounds out the top 3.` : ".") : "") +
    (topCodesNote ? ` Top recurring codes: ${topCodesNote}.` : "") +
    ` Cross-reference these codes with the High-Yield Reading List for targeted review.`
  ));
}


// ════════════════════════════════════════════════════════════════════
// 10. CLINICAL PATHWAY GAP MAP (v3 only)
// ════════════════════════════════════════════════════════════════════
if (pathways && pathways.status === "complete" && (pathways.pathway_gaps || []).length > 0) {
  children.push(spacer(200));
  children.push(sectionBar("🧬 CLINICAL PATHWAY GAP MAP"));
  children.push(spacer(80));

  children.push(new Paragraph({ spacing: { before: 40, after: 100 }, children: [
    new TextRun({
      text: "Missed questions mapped to clinical pathway roles via ICD-10. " +
        "Shows not just WHERE you struggled but WHAT KIND of gap — " +
        "treatment selection, monitoring, screening, or escalation.",
      font: FONT, size: 18, color: MGRAY, italics: true }),
  ]}));

  const ROLE_COLORS = {
    "first_line":           "1F3864",
    "second_line":          "2E75B6",
    "monitoring":           "276749",
    "screening_prevention": "975A16",
    "referral":             "595959",
    "special_pops":         "553C9A",
    "diagnosis":            "9B2C2C",
  };

  for (const gap of pathways.pathway_gaps) {
    children.push(new Paragraph({ spacing: { before: 140, after: 20 }, children: [
      new TextRun({ text: `${gap.icd10_code}`, font: FONT, size: 22, bold: true, color: NAVY }),
      new TextRun({ text: `  ${gap.description || ""}`, font: FONT, size: 22, color: DGRAY }),
      new TextRun({ text: `  •  ${gap.miss_count} missed question${gap.miss_count !== 1 ? "s" : ""}`, font: FONT, size: 18, color: RED, italics: true }),
    ]}));

    const roles = Object.entries(gap.pathway_roles || {});
    if (roles.length > 0) {
      const pColW = [2400, 1600, 4360];
      const pRows = [row(["Pathway Role", "Guidelines", "Gap Type"].map((h, i) => headerCell(h, pColW[i])))];
      roles.forEach(([role, count]) => {
        const isDominant = role === gap.dominant_role;
        const roleColor = ROLE_COLORS[role] || MGRAY;
        const interp = isDominant ? `▶ ${gap.interpretation}` : "";
        pRows.push(row([
          dataCell(role.replace(/_/g, " "), pColW[0], roleColor, isDominant, AlignmentType.LEFT),
          dataCell(`${count} articles`, pColW[1], isDominant ? RED : MGRAY, isDominant),
          dataCell(interp, pColW[2], isDominant ? NAVY : LGRAY, false, AlignmentType.LEFT),
        ]));
      });
      children.push(makeTable(pColW, pRows));
    }
  }

  const topGap = pathways.pathway_gaps[0];
  if (topGap) {
    children.push(studyNote(
      `Your most concentrated gap: ${topGap.icd10_code} (${topGap.description || ""}) — ` +
      `${topGap.miss_count} missed questions pointing to a ${topGap.interpretation}. ` +
      `Focus on ${(topGap.dominant_role || "").replace(/_/g, " ")} guidelines for this condition first.`
    ));
  }
}

// ────────────────────────────────────────────────────────────────────
// 10. HIGH-YIELD READING LIST
// ────────────────────────────────────────────────────────────────────
children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(sectionBar("\uD83D\uDCDA HIGH-YIELD READING LIST"));
children.push(spacer(80));

children.push(new Paragraph({ spacing: { before: 40, after: 120 }, children: [
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

// ────────────────────────────────────────────────────────────────────
// PART B: PRACTICE QUESTIONS (with answers, grouped by weak area)
// ────────────────────────────────────────────────────────────────────
children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(sectionBar("\u270F TARGETED PRACTICE QUESTIONS \u2014 BY WEAK AREA"));
children.push(spacer(60));

children.push(new Paragraph({ spacing: { before: 40, after: 120 }, children: [
  new TextRun({ text: "Questions drawn from the ITE Intelligence database (ITE + AAFP BRQ), globally ranked by relevance to each weak area. " +
    "Minimum 5 per weak section. Correct answers highlighted with full explanations. " +
    "A separate exam version (no answers) is provided as a companion document.",
    font: FONT, size: 18, color: MGRAY, italics: true }),
]}));

// Match tier labels for question provenance
const TIER_LABELS = { 1: "Direct Match", 2: "ICD-10 Sibling", 3: "Vector Match" };
const TIER_COLORS = { 1: GREEN, 2: BLUE, 3: MGRAY };

let qNum = 0;
const targetOrder = [...weakBlueprints];
for (const t of Object.keys(qByTarget)) {
  if (!targetOrder.includes(t)) targetOrder.push(t);
}

for (const target of targetOrder) {
  const tQuestions = qByTarget[target] || [];
  if (tQuestions.length === 0) continue;
  const isWeak = weakBlueprints.includes(target);

  children.push(spacer(120));
  children.push(subBar(
    isWeak ? `\u26A0 WEAK AREA: ${target.toUpperCase()}  (${tQuestions.length} questions)` : `${target.toUpperCase()}  (${tQuestions.length} questions)`,
    isWeak ? BLUE : "4A5568"
  ));

  for (const q of tQuestions) {
    qNum++;
    children.push(new Paragraph({ spacing: { before: 180, after: 40 }, children: [
      new TextRun({ text: `Question ${qNum}`, font: FONT, size: 22, bold: true, color: NAVY }),
      new TextRun({ text: `  ${q.qid}`, font: FONT, size: 18, color: MGRAY }),
    ]}));

    const meta = [q.body_system_merged, q.blueprint].filter(Boolean).join("  |  ");
    const sourceLabel = q.source_label || (q.source_bank === "AAFP" ? "AAFP BRQ" : `ITE ${q.exam_year || ""}`.trim());
    const tierLabel = TIER_LABELS[q.match_tier] || "";
    const tierColor = TIER_COLORS[q.match_tier] || MGRAY;
    children.push(new Paragraph({ spacing: { before: 0, after: 60 },
      border: { bottom: { style: BorderStyle.SINGLE, size: 1, color: "D6E4F7", space: 4 } },
      children: [
        new TextRun({ text: meta, font: FONT, size: 16, color: BLUE }),
        ...(sourceLabel ? [new TextRun({ text: `  \u2022  ${sourceLabel}`, font: FONT, size: 16, color: BLUE, bold: true })] : []),
        ...(tierLabel ? [new TextRun({ text: `  \u2022  ${tierLabel}`, font: FONT, size: 16, color: tierColor, italics: true })] : []),
      ],
    }));

    children.push(new Paragraph({ spacing: { before: 80, after: 80 }, children: [
      new TextRun({ text: q.question_text || "", font: FONT, size: 20, color: DGRAY }),
    ]}));

    let choices = q.choices || [];
    if (typeof choices === "string") { try { choices = JSON.parse(choices); } catch { choices = []; } }
    choices.forEach(c => {
      const isCorrect = c.letter === q.correct_letter;
      children.push(new Paragraph({ spacing: { before: 30, after: 30 }, indent: { left: 360 }, children: [
        new TextRun({ text: `${c.letter}. ${c.text}`, font: FONT, size: 20, color: isCorrect ? GREEN : DGRAY, bold: isCorrect }),
        ...(isCorrect ? [new TextRun({ text: "  \u2713", font: FONT, size: 20, color: GREEN, bold: true })] : []),
      ]}));
    });

    children.push(new Paragraph({ spacing: { before: 80, after: 40 }, children: [
      new TextRun({ text: `Answer: ${q.correct_letter}`, font: FONT, size: 20, bold: true, color: GREEN }),
      new TextRun({ text: q.correct_text ? ` \u2014 ${q.correct_text}` : "", font: FONT, size: 20, color: GREEN }),
    ]}));

    if (q.explanation) {
      children.push(new Paragraph({ spacing: { before: 40, after: 100 }, indent: { left: 200 }, children: [
        new TextRun({ text: q.explanation, font: FONT, size: 18, color: MGRAY, italics: true }),
      ]}));
    }
  }
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
          border: { top: { style: BorderStyle.SINGLE, size: 1, color: "D0D0D0", space: 4 } },
          spacing: { before: 100 },
          children: [
            new TextRun({ text: `${footerText}  |  `, font: FONT, size: 14, color: LGRAY }),
            new TextRun({ text: "Page ", font: FONT, size: 14, color: LGRAY }),
            new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 14, color: LGRAY }),
          ],
        }),
      ]}) },
      children: docChildren,
    }],
  });
}

const analysisDoc = makeDocShell(children, `ITE ${data.exam_year} Score Analysis  |  ${res.name}`, "Generated by ITE Score Analysis Pipeline v2");

// ═══════════════════════════════════════════════════════════════════
// PART C: EXAM VERSION
// ═══════════════════════════════════════════════════════════════════
const examChildren = [];
const answerKey = [];

examChildren.push(new Paragraph({ spacing: { before: 600, after: 0 }, alignment: AlignmentType.CENTER, children: [
  new TextRun({ text: `ITE ${data.exam_year} PRACTICE EXAM`, font: FONT, size: 36, bold: true, color: NAVY }),
]}));
examChildren.push(new Paragraph({ spacing: { before: 80, after: 0 }, alignment: AlignmentType.CENTER, children: [
  new TextRun({ text: `Personalized for ${res.name}`, font: FONT, size: 22, color: BLUE }),
]}));
examChildren.push(new Paragraph({ spacing: { before: 60, after: 0 }, alignment: AlignmentType.CENTER, children: [
  new TextRun({ text: `${allQuestions.length} questions targeted to weak areas  |  Answer key at end`, font: FONT, size: 18, color: MGRAY }),
]}));
examChildren.push(spacer(200));

let examNum = 0;
for (const target of targetOrder) {
  const tQuestions = qByTarget[target] || [];
  if (tQuestions.length === 0) continue;
  const isWeak = weakBlueprints.includes(target);

  examChildren.push(spacer(100));
  examChildren.push(subBar(
    isWeak ? `\u26A0 ${target.toUpperCase()}` : target.toUpperCase(),
    isWeak ? BLUE : "4A5568"
  ));

  for (const q of tQuestions) {
    examNum++;
    answerKey.push({ num: examNum, qid: q.qid, letter: q.correct_letter, text: q.correct_text || "", target, body: q.body_system_merged || "" });

    examChildren.push(new Paragraph({ spacing: { before: 180, after: 40 }, children: [
      new TextRun({ text: `Question ${examNum}`, font: FONT, size: 22, bold: true, color: NAVY }),
      new TextRun({ text: `  ${q.qid}`, font: FONT, size: 18, color: MGRAY }),
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

const examDoc = makeDocShell(examChildren, `ITE ${data.exam_year} Practice Exam  |  ${res.name}`, "ITE Practice Exam");

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
