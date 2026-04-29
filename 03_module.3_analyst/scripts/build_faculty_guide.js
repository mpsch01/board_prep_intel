#!/usr/bin/env node

// Faculty Advisor Methodology Guide — DOCX Generator
// Purpose: Comprehensive methodology companion to ITE Score Analysis Report
// Usage: node build_faculty_guide.js
// Output: ../docs/ITE_Report_Guide_Faculty.docx

const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, HeadingLevel, BorderStyle, WidthType,
  ShadingType, VerticalAlign, PageNumber, PageBreak, LevelFormat, UnderlineType
} = require("docx");

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
    rows: [new TableRow({
      cantSplit: true,
      children: [
        new TableCell({
          width: { size: W, type: WidthType.DXA },
          shading: { fill: NAVY, type: ShadingType.CLEAR },
          borders: noBorders(),
          margins: { top: 60, bottom: 60, left: 140, right: 140 },
          verticalAlign: VerticalAlign.CENTER,
          children: [new Paragraph({
            spacing: { before: 0, after: 0 },
            keepNext: true,
            children: [
              new TextRun({ text, font: FONT, size: 22, bold: true, color: WHITE }),
            ]
          })],
        }),
      ]
    })]
  });
}

function subBar(text, fill = BLUE) {
  const W = 9360;
  return new Table({
    width: { size: W, type: WidthType.DXA },
    columnWidths: [W],
    rows: [new TableRow({
      children: [
        new TableCell({
          width: { size: W, type: WidthType.DXA },
          shading: { fill, type: ShadingType.CLEAR },
          borders: noBorders(),
          margins: { top: 50, bottom: 50, left: 140, right: 140 },
          children: [new Paragraph({
            keepNext: true,
            children: [
              new TextRun({ text, font: FONT, size: 20, bold: true, color: WHITE }),
            ]
          })],
        }),
      ]
    })]
  });
}

function dataSourceBox(content) {
  return new Paragraph({
    spacing: { before: 120, after: 200 },
    border: { left: { style: BorderStyle.SINGLE, size: 12, color: GREEN, space: 8 } },
    indent: { left: 200 },
    children: [
      new TextRun({ text: "📂 DATA SOURCE  ", font: FONT, size: 18, bold: true, color: GREEN }),
      new TextRun({ text: content, font: FONT, size: 18, color: DGRAY }),
    ],
  });
}

function limitationBox(content) {
  return new Paragraph({
    spacing: { before: 120, after: 200 },
    border: { left: { style: BorderStyle.SINGLE, size: 12, color: AMBER, space: 8 } },
    indent: { left: 200 },
    children: [
      new TextRun({ text: "⚠ LIMITATION  ", font: FONT, size: 18, bold: true, color: AMBER }),
      new TextRun({ text: content, font: FONT, size: 18, color: DGRAY }),
    ],
  });
}

function coachingUseBox(content) {
  return new Paragraph({
    spacing: { before: 120, after: 200 },
    border: { left: { style: BorderStyle.SINGLE, size: 12, color: NAVY, space: 8 } },
    indent: { left: 200 },
    children: [
      new TextRun({ text: "👤 COACHING USE  ", font: FONT, size: 18, bold: true, color: NAVY }),
      new TextRun({ text: content, font: FONT, size: 18, color: DGRAY }),
    ],
  });
}

function spacer(pts = 100, keepNext = false) {
  return new Paragraph({ spacing: { before: pts, after: 0 }, keepNext, children: [] });
}

function row(cells) {
  return new TableRow({ cantSplit: true, children: cells });
}

function headerCell(text, w) {
  return new TableCell({
    width: { size: w, type: WidthType.DXA },
    borders: cellBorders,
    shading: { fill: LTBLUE, type: ShadingType.CLEAR },
    margins: { top: 60, bottom: 60, left: 80, right: 80 },
    verticalAlign: VerticalAlign.CENTER,
    children: [new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [
        new TextRun({ text, font: FONT, size: 18, bold: true, color: NAVY }),
      ]
    })],
  });
}

function dataCell(text, w, color = DGRAY, bold = false, align = AlignmentType.CENTER) {
  return new TableCell({
    width: { size: w, type: WidthType.DXA },
    borders: cellBorders,
    margins: { top: 50, bottom: 50, left: 80, right: 80 },
    verticalAlign: VerticalAlign.CENTER,
    children: [new Paragraph({
      alignment: align,
      children: [
        new TextRun({ text: String(text), font: FONT, size: 18, color, bold }),
      ]
    })],
  });
}

function makeTable(colWidths, rows) {
  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: colWidths,
    rows
  });
}

function bodyTextParagraph(text, options = {}) {
  return new Paragraph({
    spacing: { before: options.before || 0, after: options.after || 80 },
    indent: options.indent || {},
    alignment: options.alignment || AlignmentType.LEFT,
    children: [
      new TextRun({
        text,
        font: FONT,
        size: options.size || 18,
        color: options.color || DGRAY,
        italics: options.italics || false,
        bold: options.bold || false,
      })
    ]
  });
}

// ── Resolve output path ─────────────────────────────────────────────
const SCRIPT_DIR = path.resolve(__dirname);
const PROJECT_ROOT = path.resolve(SCRIPT_DIR, "..", "..");
const docsDir = path.resolve(SCRIPT_DIR, "..", "docs");

// Create docs directory if it doesn't exist
if (!fs.existsSync(docsDir)) {
  try {
    fs.mkdirSync(docsDir, { recursive: true });
  } catch (err) {
    console.error(`ERROR: Cannot create docs directory: ${docsDir}`);
    process.exit(1);
  }
}

const outputPath = path.resolve(docsDir, "ITE_Report_Guide_Faculty.docx");

// ═══════════════════════════════════════════════════════════════════
// BUILD DOCUMENT
// ═══════════════════════════════════════════════════════════════════

const children = [];

// ────────────────────────────────────────────────────────────────────
// COVER / INTRO
// ────────────────────────────────────────────────────────────────────

children.push(new Paragraph({
  spacing: { before: 600, after: 0 },
  alignment: AlignmentType.CENTER,
  children: [
    new TextRun({ text: "ITE Score Analysis", font: FONT, size: 36, bold: true, color: NAVY }),
  ]
}));

children.push(new Paragraph({
  spacing: { before: 0, after: 0 },
  alignment: AlignmentType.CENTER,
  children: [
    new TextRun({ text: "Faculty Advisor's Methodology Guide", font: FONT, size: 32, bold: true, color: BLUE }),
  ]
}));

children.push(spacer(200));

children.push(new Paragraph({
  spacing: { before: 0, after: 100 },
  alignment: AlignmentType.CENTER,
  children: [
    new TextRun({
      text: "Data sources, derivation logic, and interpretation framework for program directors and faculty advisors",
      font: FONT,
      size: 20,
      color: MGRAY,
      italics: true
    })
  ]
}));

children.push(spacer(400));

children.push(bodyTextParagraph(
  "This guide accompanies the ITE Score Analysis report. It explains how each section of the report was generated, what data sources underlie it, and what the analytical limitations are. Faculty advisors using this report to guide resident advising should understand which findings are reliable and which require clinical judgment to interpret.",
  { after: 120 }
));

// ────────────────────────────────────────────────────────────────────
// SECTION: System Overview
// ────────────────────────────────────────────────────────────────────

children.push(spacer(200));
children.push(sectionBar("SYSTEM OVERVIEW — HOW THE PIPELINE WORKS"));
children.push(spacer(100, true));

children.push(bodyTextParagraph("The ITE Intelligence pipeline processes each resident's exam in four consecutive stages:", { after: 100 }));

// Pipeline table
const pipelineColW = [2400, 6960];
const pipelineRows = [
  row([
    headerCell("Stage", pipelineColW[0]),
    headerCell("What happens", pipelineColW[1])
  ]),
  row([
    dataCell("Stage 1: PDF Extraction", pipelineColW[0], NAVY, true, AlignmentType.LEFT),
    dataCell(
      "ABFM Score Report PDF → ite_parser.py extracts scaled score, blueprint rates, body system rates, item numbers, and difficulty scores from the PDF text using pdfplumber",
      pipelineColW[1],
      DGRAY,
      false,
      AlignmentType.LEFT
    )
  ]),
  row([
    dataCell("Stage 2: Analysis (v2)", pipelineColW[0], NAVY, true, AlignmentType.LEFT),
    dataCell(
      "ite_analyze_v2.py processes extracted data; runs 9 analysis layers including tier analysis, difficulty profiling, yield priorities, concept fingerprint, longitudinal delta computation, and ICD-10 integration; outputs analysis_v2.json",
      pipelineColW[1],
      DGRAY,
      false,
      AlignmentType.LEFT
    )
  ]),
  row([
    dataCell("Stage 3: Enhancement (v3)", pipelineColW[0], NAVY, true, AlignmentType.LEFT),
    dataCell(
      "ite_analyzer_v3.py adds practice question selection (3-tier cascade), reading list matching (two-tier article selection), concept QID mapping, and linked_qids attachment; final JSON output",
      pipelineColW[1],
      DGRAY,
      false,
      AlignmentType.LEFT
    )
  ]),
  row([
    dataCell("Stage 4: Report Generation", pipelineColW[0], NAVY, true, AlignmentType.LEFT),
    dataCell(
      "ite_report_builder_v2.js reads final JSON, generates two DOCX files: Analysis Report (Parts A+B) and Exam Version (Part C, answers at end)",
      pipelineColW[1],
      DGRAY,
      false,
      AlignmentType.LEFT
    )
  ])
];
children.push(makeTable(pipelineColW, pipelineRows));

children.push(spacer(120));

children.push(bodyTextParagraph("Key infrastructure:", { before: 60, bold: true, color: NAVY }));
children.push(new Paragraph({
  spacing: { before: 40, after: 40 },
  indent: { left: 360, hanging: 260 },
  children: [
    new TextRun({ text: "• ", font: FONT, size: 18, bold: true, color: NAVY }),
    new TextRun({
      text: "Source database: ite_intelligence.db (SQLite) — 1,639 ITE questions (2018–2025), 1,221 AAFP BRQ questions, 1,998 clinical guideline articles",
      font: FONT,
      size: 18,
      color: DGRAY
    })
  ]
}));
children.push(new Paragraph({
  spacing: { before: 40, after: 40 },
  indent: { left: 360, hanging: 260 },
  children: [
    new TextRun({ text: "• ", font: FONT, size: 18, bold: true, color: NAVY }),
    new TextRun({
      text: "The DB is the single source of truth — questions, articles, ICD-10 tags, embeddings, and article currency all live here",
      font: FONT,
      size: 18,
      color: DGRAY
    })
  ]
}));
children.push(new Paragraph({
  spacing: { before: 40, after: 40 },
  indent: { left: 360, hanging: 260 },
  children: [
    new TextRun({ text: "• ", font: FONT, size: 18, bold: true, color: NAVY }),
    new TextRun({
      text: "The pipeline runs per-resident: each resident's score report PDF is run through the pipeline independently",
      font: FONT,
      size: 18,
      color: DGRAY
    })
  ]
}));
children.push(new Paragraph({
  spacing: { before: 40, after: 80 },
  indent: { left: 360, hanging: 260 },
  children: [
    new TextRun({ text: "• ", font: FONT, size: 18, bold: true, color: NAVY }),
    new TextRun({
      text: "Longitudinal comparison requires prior year's analysis_v2.json to be passed via --prior-year flag",
      font: FONT,
      size: 18,
      color: DGRAY
    })
  ]
}));

// ────────────────────────────────────────────────────────────────────
// SECTION 0: Exam at a Glance
// ────────────────────────────────────────────────────────────────────

children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(sectionBar("SECTION 0 — EXAM AT A GLANCE: DATA SOURCE AND ACCURACY"));
children.push(spacer(100, true));

children.push(dataSourceBox(
  "abfm_reference_{year}.json — a manually curated JSON file containing exam specifications (total items, scored items, deletion count, MPS, SEM, administration count), and national benchmarks by PGY level (mean scaled score, SD, n) sourced from ABFM's published ITE technical report for that exam year. Also includes FMCE signal threshold (440)."
));

children.push(bodyTextParagraph("Update requirement: This file must be updated annually after ABFM releases the year's score report. The file is stored at 03_module.3_analyst/scripts/abfm_reference_{year}.json. If the current year's file is missing, the pipeline falls back to the most recent available year — a warning is printed but execution continues.", { before: 60, after: 100 }));

children.push(limitationBox(
  "National benchmarks are published at the program aggregate level. Individual-resident PGY comparisons (shown in the score display section) require official score report input — if no score report PDF was parsed, the comparison falls back to the national all-PGY mean."
));

children.push(coachingUseBox(
  "The national benchmark table is most useful for contextualizing a resident's scaled score relative to their PGY year. A PGY-1 at the PGY-1 mean is performing as expected; a PGY-3 below the PGY-1 mean warrants serious advising attention."
));

// ────────────────────────────────────────────────────────────────────
// SECTION 1: Score Display
// ────────────────────────────────────────────────────────────────────

children.push(spacer(200));
children.push(sectionBar("SECTION 1 — SCORE DISPLAY: DERIVATION LOGIC"));
children.push(spacer(100, true));

children.push(bodyTextParagraph("Three numbers are displayed on the score report cover:", { before: 60, after: 80, bold: true, color: NAVY }));

children.push(new Paragraph({
  spacing: { before: 40, after: 40 },
  indent: { left: 360, hanging: 260 },
  children: [
    new TextRun({ text: "1. ", font: FONT, size: 18, bold: true, color: NAVY }),
    new TextRun({
      text: "Raw %: correct / total_scored — direct calculation from parsed exam data.",
      font: FONT,
      size: 18,
      color: DGRAY
    })
  ]
}));

children.push(new Paragraph({
  spacing: { before: 40, after: 40 },
  indent: { left: 360, hanging: 260 },
  children: [
    new TextRun({ text: "2. ", font: FONT, size: 18, bold: true, color: NAVY }),
    new TextRun({
      text: "Scaled score: Two sources. Official (labeled 'official'): extracted directly from the ABFM score report PDF by ite_parser.py. Estimated (labeled 'est.'): if no score report PDF is provided, a linear approximation is used: scaled ≈ 380 × (raw_pct / national_mean_pct). Accurate to ±10–15 points in the 330–480 range; less reliable at extremes.",
      font: FONT,
      size: 18,
      color: DGRAY
    })
  ]
}));

children.push(new Paragraph({
  spacing: { before: 40, after: 80 },
  indent: { left: 360, hanging: 260 },
  children: [
    new TextRun({ text: "3. ", font: FONT, size: 18, bold: true, color: NAVY }),
    new TextRun({
      text: "Percentile: Estimated from a normal distribution approximation using the published national mean and SD for that PGY level (or overall if PGY unknown). Not derived from ABFM's percentile ranking directly.",
      font: FONT,
      size: 18,
      color: DGRAY
    })
  ]
}));

children.push(bodyTextParagraph("Confidence range (68%): ±1 exam-level SEM (±38) around the displayed scaled score. This is the band within which the resident's true ability lies with 68% probability.", { before: 60, after: 80 }));

children.push(bodyTextParagraph("Score band labels (STRONG / ON TRACK / AT RISK / CRITICAL RISK) are derived from pass probability estimates using the resident's scaled score position relative to MPS (380) and the national SD. These are probabilistic labels, not categorical determinations.", { before: 60, after: 80 }));

children.push(bodyTextParagraph("FMCE probability: Estimated from the scaled score relative to the FMCE signal threshold (440), using the same normal approximation. This is a training-exam proxy — it does not reflect the FMCE's actual scoring model.", { before: 60, after: 80 }));

children.push(limitationBox(
  "Estimated scaled scores have ±10–15 point error. The percentile and FMCE probability estimates inherit this error. When official score report PDFs are provided, all displayed values are authoritative ABFM outputs."
));

children.push(coachingUseBox(
  "Use the confidence range to temper over-interpretation of single-point score differences. A resident who 'fell just short' of a threshold may be statistically indistinguishable from one who cleared it. Focus coaching on the direction and magnitude of change over years, not single-exam point values."
));

// ────────────────────────────────────────────────────────────────────
// SECTION 2: Exam Summary
// ────────────────────────────────────────────────────────────────────

children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(sectionBar("SECTION 2 — EXAM SUMMARY: COMPUTATION DETAILS"));
children.push(spacer(100, true));

children.push(bodyTextParagraph("Personal mean: The mean of the resident's per-category rates across all blueprint dimensions. Used as the relative baseline for the Tier 2 relative weakness analysis. A category below the personal mean is flagged as 'relatively weak' even if above 70%.", { before: 60, after: 80 }));

children.push(bodyTextParagraph("Weak areas list: Union of two criteria — (1) categories classified as relative_weakness by Tier 2 analysis (below personal mean by a statistically meaningful margin), AND (2) categories with absolute rate < 70%. Either criterion qualifies. This list drives practice question targeting and reading list selection.", { before: 60, after: 80 }));

children.push(bodyTextParagraph("Easy miss count: Questions where the item difficulty score ≥ 700 AND the resident answered incorrectly. Item difficulty scores are ABFM-published statistics from the annual ITE critique PDF, representing the national percentage of examinees who answered correctly × 10 (0–999 scale). A score of 700 means 70% of national examinees answered this item correctly.", { before: 60, after: 80 }));

children.push(bodyTextParagraph("MPS gap estimate: ceil((380/scaled_score - 1) × correct_count). This is a linear approximation of the raw→scaled relationship. Accurate for scores in the 330–480 range; less accurate at extremes.", { before: 60, after: 80 }));

children.push(limitationBox(
  "The MPS gap estimate assumes a linear raw-to-scaled conversion, which is an approximation. The actual ABFM conversion uses item response theory and is non-linear. Treat this number as a directional estimate, not a precise target."
));

// ────────────────────────────────────────────────────────────────────
// SECTION 3b: Year-Over-Year Progress
// ────────────────────────────────────────────────────────────────────

children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(sectionBar("SECTION 3B — YEAR-OVER-YEAR PROGRESS: COMPUTATION"));
children.push(spacer(100, true));

children.push(bodyTextParagraph("Triggered only when a prior-year analysis_v2.json is supplied via the --prior-year CLI flag in ite_analyze_v2.py. The file must be from the same resident and a prior exam year.", { before: 60, after: 80, italics: true, color: MGRAY }));

children.push(bodyTextParagraph("Scaled delta: current_scaled - prior_scaled (when both are official). Falls back to raw percentage delta if either year used an estimated scaled score.", { before: 60, after: 80 }));

children.push(bodyTextParagraph("Trajectory categories (computed per weak-area dimension):", { before: 60, bold: true, color: NAVY }));

children.push(new Paragraph({
  spacing: { before: 40, after: 40 },
  indent: { left: 360, hanging: 260 },
  children: [
    new TextRun({ text: "• ", font: FONT, size: 18, bold: true, color: NAVY }),
    new TextRun({
      text: "Closed: dimension was in the prior-year weak list but is not in the current-year weak list",
      font: FONT,
      size: 18,
      color: DGRAY
    })
  ]
}));

children.push(new Paragraph({
  spacing: { before: 40, after: 40 },
  indent: { left: 360, hanging: 260 },
  children: [
    new TextRun({ text: "• ", font: FONT, size: 18, bold: true, color: NAVY }),
    new TextRun({
      text: "Persistent: dimension is in the weak list in both years",
      font: FONT,
      size: 18,
      color: DGRAY
    })
  ]
}));

children.push(new Paragraph({
  spacing: { before: 40, after: 80 },
  indent: { left: 360, hanging: 260 },
  children: [
    new TextRun({ text: "• ", font: FONT, size: 18, bold: true, color: NAVY }),
    new TextRun({
      text: "New: dimension is in the current-year weak list but was not in prior year",
      font: FONT,
      size: 18,
      color: DGRAY
    })
  ]
}));

children.push(bodyTextParagraph("Blueprint delta and body_system_delta: stored as percentage-point differences (current_rate - prior_rate) per dimension. These populate the Δ column in Section 4's tables.", { before: 60, after: 80 }));

children.push(bodyTextParagraph("Concept delta: Prior-year top drugs, diagnoses, and guidelines are stored in the longitudinal_delta.n1.concept_delta field. Used for the 🔁 / 🆕 badge display in Section 8.", { before: 60, after: 80 }));

children.push(limitationBox(
  "Year-over-year comparison is confounded by exam content variation — the ITE is not the same exam each year. A persistent gap may reflect consistent knowledge deficit OR consistent exam exposure to topics the resident hasn't mastered. Interpret trajectory with clinical context."
));

children.push(coachingUseBox(
  "Persistent gaps are the most important advising signal in this section. If the same category is weak two years running, the study strategy needs to change — not just the volume. Ask the resident directly what resource they've been using for that domain and whether it's been effective. New gaps may reflect content rotation in the exam, knowledge decay, or recent clinical rotations in areas not covered by their study plan."
));

// ────────────────────────────────────────────────────────────────────
// SECTION 4: Blueprint & Body System Performance
// ────────────────────────────────────────────────────────────────────

children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(sectionBar("SECTION 4 — BLUEPRINT & BODY SYSTEM PERFORMANCE: DATA SOURCES"));
children.push(spacer(100, true));

children.push(bodyTextParagraph("Blueprint data source: The official ABFM score report PDF includes a 'Performance by Blueprint Category' table. ite_parser.py extracts these values: category name, number correct, number of items, and rate. This is authoritative ABFM data.", { before: 60, after: 80 }));

children.push(subBar("Body System — ABFM-Reported (NAVY label)", NAVY));
children.push(spacer(60));

children.push(dataSourceBox(
  "A separate section of the ABFM score report PDF titled 'Performance by Body System' or equivalent. Parsed by ite_parser.py using the same extraction logic as Blueprint. These are the most reliable body system sub-scores — directly from ABFM. Stored in body_system_sources.abfm array in the JSON."
));

children.push(spacer(60));
children.push(subBar("Body System — Database-Derived (BLUE label, Stage 1.75 backfill)", BLUE));
children.push(spacer(60));

children.push(dataSourceBox(
  "ite_intelligence.db questions table, body_system_merged column. When ABFM body system data is absent or sparse, Stage 1.75 runs in ite_analyze_v2.py: for each missed question QID, the DB is queried for that question's body_system_merged value; rates are aggregated across all missed questions in each body system. body_system_merged was validated and QC'd against ABFM's published score distributions using a custom two-stage classifier (SVM + Claude API CoT) in 2026-04-16 pipeline run. 376 body system assignments were corrected in that run. Stored in body_system_sources.db array in the JSON."
));

children.push(spacer(60));

children.push(bodyTextParagraph("Provenance tracking: body_system_sources field records which systems came from ABFM vs DB backfill. The report renders them in separate sub-tables. Graceful fallback: old JSON files without this field render a single flat table.", { before: 60, after: 80 }));

children.push(bodyTextParagraph("SEM values: Per-category SEM from abfm_reference_{year}.json — these are ABFM-published measurement error values for blueprint sub-scores. Sub-scores with large SEM values (often >15%) are based on few items and should generate hypotheses, not confirm deficits.", { before: 60, after: 80 }));

children.push(limitationBox(
  "Database-Derived body systems inherit any errors in the DB's body_system_merged column. While the 2026-04-16 QC pass corrected the majority of known errors, some mis-assignments may remain, particularly for questions at domain boundaries (e.g., a mental health question about a physical complaint). Flag discrepancies to the system administrator for correction."
));

children.push(coachingUseBox(
  "When advising on body systems, weight ABFM-Reported scores more heavily than Database-Derived scores. If the two sources diverge (e.g., ABFM shows Cardiovascular as strong but DB shows it as weak), acknowledge the discrepancy rather than treating one as definitive. ABFM-Reported covers only the body systems ABFM chose to report; DB-Derived covers all body systems in the question database."
));

// ────────────────────────────────────────────────────────────────────
// SECTION 6: Difficulty Profile
// ────────────────────────────────────────────────────────────────────

children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(sectionBar("SECTION 6 — DIFFICULTY PROFILE: ITEM DIFFICULTY DATA"));
children.push(spacer(100, true));

children.push(bodyTextParagraph("Item difficulty scores:", { before: 60, bold: true, color: NAVY }));

children.push(new Paragraph({
  spacing: { before: 40, after: 40 },
  indent: { left: 360, hanging: 260 },
  children: [
    new TextRun({ text: "• ", font: FONT, size: 18, bold: true, color: NAVY }),
    new TextRun({
      text: "Source: ABFM publishes item-level difficulty statistics in the annual ITE critique PDF (e.g., 2025_critique.pdf)",
      font: FONT,
      size: 18,
      color: DGRAY
    })
  ]
}));

children.push(new Paragraph({
  spacing: { before: 40, after: 40 },
  indent: { left: 360, hanging: 260 },
  children: [
    new TextRun({ text: "• ", font: FONT, size: 18, bold: true, color: NAVY }),
    new TextRun({
      text: "The difficulty statistic is the P-value × 1000 (proportion of examinees who answered correctly, on a 0–999 scale). A difficulty of 700 = 70% of national examinees answered correctly.",
      font: FONT,
      size: 18,
      color: DGRAY
    })
  ]
}));

children.push(new Paragraph({
  spacing: { before: 40, after: 80 },
  indent: { left: 360, hanging: 260 },
  children: [
    new TextRun({ text: "• ", font: FONT, size: 18, bold: true, color: NAVY }),
    new TextRun({
      text: "Extraction: Difficulty scores are stored in the questions table of ite_intelligence.db. They were extracted from critique PDFs using pdfplumber and matched to QIDs. For questions without critique data (primarily 2018–2019), difficulty is NULL.",
      font: FONT,
      size: 18,
      color: DGRAY
    })
  ]
}));

children.push(bodyTextParagraph("Tier thresholds:", { before: 60, bold: true, color: NAVY }));

children.push(new Paragraph({
  spacing: { before: 40, after: 40 },
  indent: { left: 360, hanging: 260 },
  children: [
    new TextRun({ text: "• ", font: FONT, size: 18, bold: true, color: NAVY }),
    new TextRun({
      text: "Easy Miss ≥ 700: ABFM convention — questions most examinees answer correctly",
      font: FONT,
      size: 18,
      color: DGRAY
    })
  ]
}));

children.push(new Paragraph({
  spacing: { before: 40, after: 40 },
  indent: { left: 360, hanging: 260 },
  children: [
    new TextRun({ text: "• ", font: FONT, size: 18, bold: true, color: NAVY }),
    new TextRun({
      text: "Mid-Range 300–699: Questions with meaningful variation across examinees",
      font: FONT,
      size: 18,
      color: DGRAY
    })
  ]
}));

children.push(new Paragraph({
  spacing: { before: 40, after: 80 },
  indent: { left: 360, hanging: 260 },
  children: [
    new TextRun({ text: "• ", font: FONT, size: 18, bold: true, color: NAVY }),
    new TextRun({
      text: "Hard Miss <300: Questions most examinees miss",
      font: FONT,
      size: 18,
      color: DGRAY
    })
  ]
}));

children.push(bodyTextParagraph("Easy Misses detail table: Lists each QID where the resident missed a ≥700 difficulty item. Columns include the actual difficulty score, body_system_merged, and blueprint — all from the DB questions table.", { before: 60, after: 80 }));

children.push(limitationBox(
  "Difficulty scores from one year do not transfer exactly to another year's exam. Item difficulty fluctuates with the examinee pool and question revision. The 2025 difficulty of a question from 2022 is an approximation — ABFM does not republish historical difficulties after re-scoring."
));

children.push(coachingUseBox(
  "Easy Misses are the highest-leverage advising lever. A resident with 8+ easy misses has a correctable performance gap — these are not questions they were outcompeted on by the exam; these are questions their peers answered correctly. The coaching question is: 'Were these random knowledge gaps, or do they cluster in a theme?' Refer to the body system and blueprint columns in the Easy Misses table to identify the pattern."
));

// ────────────────────────────────────────────────────────────────────
// SECTION 7: Low-Hanging Fruit
// ────────────────────────────────────────────────────────────────────

children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(sectionBar("SECTION 7 — LOW-HANGING FRUIT: PRIORITY SCORE FORMULA"));
children.push(spacer(100, true));

children.push(bodyTextParagraph("Improvable Items (per dimension): Count of missed items where item difficulty ≥ 500 AND dimension (blueprint or body system) matches. The difficulty threshold of 500 means 'more than half of national examinees answered this correctly' — a proxy for learnability. Items below 500 are excluded because they're unlikely to be improvable by standard study approaches.", { before: 60, after: 80 }));

children.push(bodyTextParagraph("Priority Score formula: improvable_items × exam_weight_pct. No normalization or log transformation is applied. This is a linear product — a category worth 35% of the exam with 3 improvable items scores 105; a category worth 5% with 5 items scores 25. The explicit intent is to weight toward high-exam-weight categories.", { before: 60, after: 80 }));

children.push(bodyTextParagraph("Exam weights: Published ABFM blueprint allocations (e.g., Chronic Care ≈ 35%, Acute Care ≈ 20%, Preventive Care ≈ 14%). Stored in abfm_reference_{year}.json.", { before: 60, after: 80 }));

children.push(bodyTextParagraph("Body system table: Improvable Items only — no Priority Score column because body systems do not have ABFM-published exam weight allocations. Their improvable item counts are directly comparable to each other but cannot be compared to Blueprint priority scores.", { before: 60, after: 80 }));

children.push(bodyTextParagraph("Section 7b — Cross-tab: Improvable items computed over blueprint × body system intersections. The intersection rate = resident's rate on questions where both the blueprint category AND the body system match the specified pair. Priority score = improvable_items × (combined_exam_weight of intersection). Top 8 intersections displayed.", { before: 60, after: 80 }));

children.push(limitationBox(
  "The priority score model is a deliberate simplification. It does not account for diminishing returns (studying 5 topics in a category may yield less than studying 3), the resident's prior familiarity level, or study resource availability. Use it as a starting sequence, not a precise optimization."
));

// ────────────────────────────────────────────────────────────────────
// SECTION 8: Concept Fingerprint
// ────────────────────────────────────────────────────────────────────

children.push(spacer(200));
children.push(sectionBar("SECTION 8 — CONCEPT FINGERPRINT: ENRICHMENT SOURCE"));
children.push(spacer(100, true));

children.push(dataSourceBox(
  "concept_tags column in the questions table of ite_intelligence.db. This column contains a JSON array of clinical concepts per question (e.g., ['metformin', 'type 2 diabetes', 'ADA guidelines']). Concept_tags were generated during the DB enrichment pipeline using Claude API batch processing. Each question was passed through a clinical concept extraction prompt that identified drug names, disease concepts, and clinical guideline references. Tags were normalized through a synonym map (151 entries in clinical_synonym_map.json) to collapse variants (e.g., 'T2DM' → 'type 2 diabetes')."
));

children.push(spacer(80));

children.push(bodyTextParagraph("Drug name normalization: Drug names normalize more cleanly than diagnosis names due to standardized pharmacology naming conventions. Diagnosis concepts at single-exam sample sizes (191 items) produce noisy frequency counts due to clinical variant labeling. This is why the report displays only drug concepts — diagnosis tags still run internally for ICD-10 scoring but are not shown.", { before: 60, after: 80 }));

children.push(bodyTextParagraph("Internal ICD-10 scoring: The concept fingerprint feeds into the ICD-10 weakness map and practice question selection through a hidden signal path (icd10_profile). This is a matching mechanism, not a clinical report — it never surfaces as a visible ICD-10 claim in the report.", { before: 60, after: 80 }));

children.push(bodyTextParagraph("Concept-QID map: ite_analyzer_v3.py builds a concept_qid_map during analysis: for each drug concept, the QIDs of missed questions containing that concept are recorded. Up to 10 QIDs stored, top 5 displayed.", { before: 60, after: 80 }));

children.push(bodyTextParagraph("YoY badges: Concept names are compared against prior-year top_drugs list from longitudinal_delta.n1.concept_delta. Matches = 🔁 Persistent; new entries = 🆕 New.", { before: 60, after: 80 }));

children.push(limitationBox(
  "Concept fingerprint reliability scales with the number of missed items. Residents with fewer than 30 misses will have sparse concept frequency tables. A drug appearing 2× in 20 misses carries more significance than 2× in 100 misses. Interpret low-miss-count fingerprints with proportional confidence."
));

children.push(coachingUseBox(
  "A persistent drug cluster (🔁) across two exam years is a reliable signal of a pharmacology knowledge gap — this is unlikely to be random when the same drugs appear across two independent exams. Use it as a direct advising probe: 'The report shows you've missed questions about metformin twice in a row — tell me what you know about its second-line indications and contraindications.'"
));

// ────────────────────────────────────────────────────────────────────
// SECTION 9: ICD-10 Weakness Map
// ────────────────────────────────────────────────────────────────────

children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(sectionBar("SECTION 9 — ICD-10 WEAKNESS MAP: DATA FLOW"));
children.push(spacer(100, true));

children.push(bodyTextParagraph("Full data flow chain:", { before: 60, bold: true, color: NAVY }));

children.push(new Paragraph({
  spacing: { before: 40, after: 40 },
  indent: { left: 360, hanging: 260 },
  children: [
    new TextRun({ text: "1. ", font: FONT, size: 18, bold: true, color: NAVY }),
    new TextRun({
      text: "Resident's missed question QIDs",
      font: FONT,
      size: 18,
      color: DGRAY
    })
  ]
}));

children.push(new Paragraph({
  spacing: { before: 40, after: 40 },
  indent: { left: 360, hanging: 260 },
  children: [
    new TextRun({ text: "2. ", font: FONT, size: 18, bold: true, color: NAVY }),
    new TextRun({
      text: "qid_art_xref table in DB (2,485 rows) → linked article_ids for each QID",
      font: FONT,
      size: 18,
      color: DGRAY
    })
  ]
}));

children.push(new Paragraph({
  spacing: { before: 40, after: 40 },
  indent: { left: 360, hanging: 260 },
  children: [
    new TextRun({ text: "3. ", font: FONT, size: 18, bold: true, color: NAVY }),
    new TextRun({
      text: "article_icd10 table in DB (4,959 rows) → ICD-10 codes and descriptions per article",
      font: FONT,
      size: 18,
      color: DGRAY
    })
  ]
}));

children.push(new Paragraph({
  spacing: { before: 40, after: 80 },
  indent: { left: 360, hanging: 260 },
  children: [
    new TextRun({ text: "4. ", font: FONT, size: 18, bold: true, color: NAVY }),
    new TextRun({
      text: "Aggregation: miss_count per ICD-10 code = number of distinct missed QIDs whose linked articles include that code",
      font: FONT,
      size: 18,
      color: DGRAY
    })
  ]
}));

children.push(dataSourceBox(
  "Each of the 1,998 articles in the DB was tagged with clinically relevant ICD-10 codes via Claude API batch processing. The enrichment prompt asked for condition-level ICD-10 codes that the article primarily addressed. Average 2–3 codes per article. Enrichment completed in batch API run (April 2026). Chapter mapping: ICD-10 chapter assignments are derived from code prefix (letter → chapter map hardcoded in ite_report_builder_v2.js). Chapter descriptions shown in the Clinical Domain column. Top 15 codes displayed; full icd10_weakness_map is available in the analysis_v2.json for programmatic use."
));

children.push(limitationBox(
  "This section reflects article-level ICD-10 tags, not question-level tags directly. If a question's linked article is about type 2 diabetes (E11), the question inherits the E11 code even if the specific question tested metformin dosing rather than diabetes diagnosis. This is an intentional approximation — it surfaces clinical domain patterns rather than precise question-level ICD-10 classification. For precise question-level coding, use the question_icd10 table in the DB directly. A second limitation: qid_art_xref coverage is 100% for ITE 2018–2023, 90% for 2024, and 83.5% for 2025. Questions without article linkages in 2024–2025 will not contribute to the ICD-10 map."
));

children.push(coachingUseBox(
  "This section is most useful for identifying specialty-area clustering. If a resident has 5+ misses clustering in ICD-10 Chapter IX (Circulatory) and Chapter IV (Endocrine/Metabolic), that's a cardiovascular-metabolic cluster — a coherent advising narrative you can use to recommend a specific clinical medicine review block."
));

// ────────────────────────────────────────────────────────────────────
// SECTION 10: High-Yield Reading List
// ────────────────────────────────────────────────────────────────────

children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(sectionBar("SECTION 10 — HIGH-YIELD READING LIST: TWO-TIER SELECTION LOGIC"));
children.push(spacer(100, true));

children.push(bodyTextParagraph("Data sources:", { before: 60, bold: true, color: NAVY }));

children.push(new Paragraph({
  spacing: { before: 40, after: 40 },
  indent: { left: 360, hanging: 260 },
  children: [
    new TextRun({ text: "• ", font: FONT, size: 18, bold: true, color: NAVY }),
    new TextRun({
      text: "articles table: 1,998 clinical guideline articles with title, author, year, citation_count, unique_years",
      font: FONT,
      size: 18,
      color: DGRAY
    })
  ]
}));

children.push(new Paragraph({
  spacing: { before: 40, after: 40 },
  indent: { left: 360, hanging: 260 },
  children: [
    new TextRun({ text: "• ", font: FONT, size: 18, bold: true, color: NAVY }),
    new TextRun({
      text: "qid_art_xref table: 2,485 rows linking question IDs to article IDs (the foundational linkage for personalization)",
      font: FONT,
      size: 18,
      color: DGRAY
    })
  ]
}));

children.push(new Paragraph({
  spacing: { before: 40, after: 80 },
  indent: { left: 360, hanging: 260 },
  children: [
    new TextRun({ text: "• ", font: FONT, size: 18, bold: true, color: NAVY }),
    new TextRun({
      text: "article_currency table: 1,998 rows with currency_status for each article (current / updated / check_needed / not_indexed), populated via PubMed API lookup in build_article_currency.py",
      font: FONT,
      size: 18,
      color: DGRAY
    })
  ]
}));

children.push(spacer(60));

children.push(subBar("Tier 1 — Personalized ('Targeted to Your Exam')", GREEN));
children.push(spacer(60));

children.push(new Paragraph({
  spacing: { before: 60, after: 40 },
  indent: { left: 360, hanging: 260 },
  children: [
    new TextRun({ text: "• ", font: FONT, size: 18, bold: true, color: NAVY }),
    new TextRun({
      text: "Selection pool: all articles with at least one linked QID that the resident answered incorrectly (weak_area_links ≥ 1)",
      font: FONT,
      size: 18,
      color: DGRAY
    })
  ]
}));

children.push(new Paragraph({
  spacing: { before: 40, after: 40 },
  indent: { left: 360, hanging: 260 },
  children: [
    new TextRun({ text: "• ", font: FONT, size: 18, bold: true, color: NAVY }),
    new TextRun({
      text: "Strong Tier 1: weak_area_links ≥ 2 (article covers 2+ of the resident's actual missed questions)",
      font: FONT,
      size: 18,
      color: DGRAY
    })
  ]
}));

children.push(new Paragraph({
  spacing: { before: 40, after: 40 },
  indent: { left: 360, hanging: 260 },
  children: [
    new TextRun({ text: "• ", font: FONT, size: 18, bold: true, color: NAVY }),
    new TextRun({
      text: "Overflow Tier 1: weak_area_links ≥ 1 (article covers at least 1 missed question)",
      font: FONT,
      size: 18,
      color: DGRAY
    })
  ]
}));

children.push(new Paragraph({
  spacing: { before: 40, after: 40 },
  indent: { left: 360, hanging: 260 },
  children: [
    new TextRun({ text: "• ", font: FONT, size: 18, bold: true, color: NAVY }),
    new TextRun({
      text: "Fill order: strong first, then overflow; target 5, cap 7. Each article tagged: selection_basis = 'personalized'",
      font: FONT,
      size: 18,
      color: DGRAY
    })
  ]
}));

children.push(spacer(60));

children.push(subBar("Tier 2 — General ('High-Yield for All Residents')", BLUE));
children.push(spacer(60));

children.push(new Paragraph({
  spacing: { before: 60, after: 40 },
  indent: { left: 360, hanging: 260 },
  children: [
    new TextRun({ text: "• ", font: FONT, size: 18, bold: true, color: NAVY }),
    new TextRun({
      text: "Selection pool: articles NOT already selected in Tier 1",
      font: FONT,
      size: 18,
      color: DGRAY
    })
  ]
}));

children.push(new Paragraph({
  spacing: { before: 40, after: 40 },
  indent: { left: 360, hanging: 260 },
  children: [
    new TextRun({ text: "• ", font: FONT, size: 18, bold: true, color: NAVY }),
    new TextRun({
      text: "Strong Tier 2: citation_count ≥ 5 AND unique_years ≥ 4",
      font: FONT,
      size: 18,
      color: DGRAY
    })
  ]
}));

children.push(new Paragraph({
  spacing: { before: 40, after: 40 },
  indent: { left: 360, hanging: 260 },
  children: [
    new TextRun({ text: "• ", font: FONT, size: 18, bold: true, color: NAVY }),
    new TextRun({
      text: "Overflow Tier 2: citation_count ≥ 3 AND unique_years ≥ 3",
      font: FONT,
      size: 18,
      color: DGRAY
    })
  ]
}));

children.push(new Paragraph({
  spacing: { before: 40, after: 80 },
  indent: { left: 360, hanging: 260 },
  children: [
    new TextRun({ text: "• ", font: FONT, size: 18, bold: true, color: NAVY }),
    new TextRun({
      text: "Fill order: strong first by citation_count descending; then overflow; target 5, cap 8. Each article tagged: selection_basis = 'general'",
      font: FONT,
      size: 18,
      color: DGRAY
    })
  ]
}));

children.push(bodyTextParagraph("Currency status: article_currency table updated via PubMed API (April 2026). Statuses: 'current' = active guideline at time of last check; 'updated' = a newer version was detected; 'check_needed' = ambiguous currency signal; 'not_indexed' = not found in PubMed (often AFP articles or older guidelines). Currency status is checked against the article as indexed in our DB, not against real-time guidelines — it represents the last API check date, not live monitoring.", { before: 60, after: 80 }));

children.push(bodyTextParagraph("linked_qids: ite_analyzer_v3.py's _attach_qids() helper fetches the list of all missed QIDs linked to each article from qid_art_xref. Up to 10 stored, top 5 displayed in the '🔗 Your missed questions covered' line.", { before: 60, after: 80 }));

children.push(limitationBox(
  "Tier 1 personalization quality depends on qid_art_xref coverage. For 2024–2025 exams where coverage is 83–90%, some missed questions may not have linked articles, reducing the precision of personalized recommendations. A resident with few missed questions (strong performance) will have a smaller Tier 1 pool and more of the reading list will default to Tier 2 general articles. Currency status reflects a one-time API check, not live monitoring — advisors should verify guideline currency independently for any article marked 'updated' or 'check_needed.'"
));

children.push(coachingUseBox(
  "Tier 1 articles are the most direct advising tool — they represent the clinical literature that underlies the resident's actual exam misses. If a resident reads every Tier 1 article before the next ITE, they will have directly addressed the clinical reasoning behind their gaps. Tier 2 articles represent the foundational FM literature — useful for tracking whether a resident's reading is broadly comprehensive."
));

// ────────────────────────────────────────────────────────────────────
// PRACTICE QUESTIONS: Three-Tier Matching Cascade
// ────────────────────────────────────────────────────────────────────

children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(sectionBar("PRACTICE QUESTIONS: THREE-TIER MATCHING CASCADE"));
children.push(spacer(100, true));

children.push(bodyTextParagraph("Selection algorithm runs in ite_analyzer_v3.py. Three tiers are attempted in sequence; a question is assigned to the highest tier it qualifies for.", { before: 60, after: 100, italics: true, color: MGRAY }));

children.push(subBar("Tier 1 — Direct Match (GREEN)", GREEN));
children.push(spacer(60));

children.push(bodyTextParagraph("Questions where the QID is in qid_art_xref linked to an article that also links to one of the resident's weak-area QIDs. These questions share the same article foundation as the resident's actual exam misses.", { before: 60, after: 80 }));

children.push(spacer(60));

children.push(subBar("Tier 2 — ICD-10 Sibling (BLUE)", BLUE));
children.push(spacer(60));

children.push(bodyTextParagraph("Questions not matched in Tier 1 where the question's ICD-10 tags (from question_icd10 table, 5,774 rows) overlap with the resident's weak-area ICD-10 profile. The profile is built from the resident's missed QIDs' ICD-10 tags — questions with matching codes are clinical relatives of the missed items.", { before: 60, after: 80 }));

children.push(spacer(60));

children.push(subBar("Tier 3 — Vector Match (GRAY)", MGRAY));
children.push(spacer(60));

children.push(bodyTextParagraph("Questions not matched in Tier 1 or 2 where cosine similarity of the question's embedding vector to the weak-area centroid vector exceeds a threshold. Uses intersection_centroid_vec table (158 rows — blueprint × body system centroids at 1536d via OpenAI text-embedding-3-small).", { before: 60, after: 80 }));

children.push(spacer(80));

children.push(bodyTextParagraph("Relevance score: Composite signal combining tier membership + concept tag overlap + ICD-10 overlap + vector similarity. Questions are sorted descending by relevance_score — higher-ranked questions are more precisely matched to the resident's gaps.", { before: 60, after: 80 }));

children.push(bodyTextParagraph("Source pool: All ITE questions from exam years excluding the current exam year (2018–2024 for a 2025 analysis), plus all AAFP BRQ questions. A question is never drawn from the same exam being analyzed.", { before: 60, after: 80 }));

children.push(bodyTextParagraph("Targeting dimension: Each practice question is assigned a targeting dimension based on what drove its selection — a Blueprint category, a Body System, a Blueprint×Body System crossover, or a concept fingerprint concept.", { before: 60, after: 80 }));

children.push(limitationBox(
  "Tier 3 vector matching can surface questions that are semantically similar but not topically identical — they may test adjacent knowledge rather than the same knowledge gap. Tier 1 and Tier 2 questions are more precisely targeted. If the practice set feels 'off-topic' to a resident, the likely culprit is the Tier 3 (Vector Match) questions."
));

children.push(coachingUseBox(
  "The 'Match' column tells advisors how tightly each practice question aligns with the resident's actual gaps. A set dominated by 'Direct Match' questions means the practice set is highly specific to the resident's exam experience. A set with many 'Vector Match' questions means the system had to cast a wider net — often because the resident has few missed questions to anchor on (strong performance) or because the weak-area ICD-10 coverage is sparse."
));

// ────────────────────────────────────────────────────────────────────
// CLOSING: Advising Framework
// ────────────────────────────────────────────────────────────────────

children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(sectionBar("ADVISING FRAMEWORK — PRACTICAL GUIDANCE"));
children.push(spacer(100, true));

children.push(bodyTextParagraph("When to act urgently:", { before: 60, bold: true, color: RED }));

children.push(bodyTextParagraph("Scaled score below MPS (380) + persistent gaps + easy miss count >8 → advising intervention before next exam cycle. These residents need structured support: a targeted study plan, weekly check-ins, and explicit review of exam-day test-taking strategy.", { before: 60, after: 80, indent: { left: 360, hanging: 260 } }));

children.push(bodyTextParagraph("When to reframe study strategy:", { before: 60, bold: true, color: AMBER }));

children.push(bodyTextParagraph("Same weak category across 2+ exam years → the issue is method, not time investment. Ask the resident directly: 'You've been weak in Cardiology for two straight years. What have you been doing to study it, and why hasn't it worked?' The answer often reveals either insufficient depth (too many breadth-focused resources), format mismatch (visual learner reading textbooks), or avoidance (resident skipping their weaker areas).", { before: 60, after: 80, indent: { left: 360, hanging: 260 } }));

children.push(bodyTextParagraph("Calibrated confidence:", { before: 60, bold: true, color: NAVY }));

children.push(bodyTextParagraph("Never advise based on a single sub-score with SEM >12% without corroboration from another section of the report. A blueprint category with only 4–5 items has high measurement error — treat it as a hypothesis generator ('Preventive Care might be weak'), not a confirmed deficit.", { before: 60, after: 80, indent: { left: 360, hanging: 260 } }));

children.push(bodyTextParagraph("Longitudinal tracking — the most valuable use:", { before: 60, bold: true, color: GREEN }));

children.push(bodyTextParagraph("The report's most valuable use is not a single exam — it's the year-over-year trajectory. A resident moving from 355 → 390 → 420 over three years is on a better trajectory than one stuck at 400 despite additional studying. This directional trend is more reliable than any single sub-score.", { before: 60, after: 80, indent: { left: 360, hanging: 260 } }));

children.push(bodyTextParagraph("What the report cannot tell you:", { before: 60, bold: true, color: MGRAY }));

children.push(new Paragraph({
  spacing: { before: 60, after: 40 },
  indent: { left: 360, hanging: 260 },
  children: [
    new TextRun({ text: "• ", font: FONT, size: 18, bold: true, color: NAVY }),
    new TextRun({
      text: "Clinical performance in continuity clinic",
      font: FONT,
      size: 18,
      color: DGRAY
    })
  ]
}));

children.push(new Paragraph({
  spacing: { before: 40, after: 40 },
  indent: { left: 360, hanging: 260 },
  children: [
    new TextRun({ text: "• ", font: FONT, size: 18, bold: true, color: NAVY }),
    new TextRun({
      text: "Patient care skills",
      font: FONT,
      size: 18,
      color: DGRAY
    })
  ]
}));

children.push(new Paragraph({
  spacing: { before: 40, after: 40 },
  indent: { left: 360, hanging: 260 },
  children: [
    new TextRun({ text: "• ", font: FONT, size: 18, bold: true, color: NAVY }),
    new TextRun({
      text: "Procedural competence",
      font: FONT,
      size: 18,
      color: DGRAY
    })
  ]
}));

children.push(new Paragraph({
  spacing: { before: 40, after: 80 },
  indent: { left: 360, hanging: 260 },
  children: [
    new TextRun({ text: "• ", font: FONT, size: 18, bold: true, color: NAVY }),
    new TextRun({
      text: "Professional development",
      font: FONT,
      size: 18,
      color: DGRAY
    })
  ]
}));

children.push(bodyTextParagraph("The ITE measures knowledge only. Advise holistically — use this report as one input into a comprehensive resident assessment that includes clinical performance, communication, and professionalism.", { before: 60, after: 100 }));

// ────────────────────────────────────────────────────────────────────
// DOCUMENT BUILD & SAVE
// ────────────────────────────────────────────────────────────────────

const doc = new Document({
  sections: [{
    properties: {
      page: {
        margins: {
          top: 1440,    // 1 inch
          bottom: 1440,
          left: 1440,
          right: 1440
        }
      }
    },
    footers: {
      default: new Footer({
        children: [
          new Paragraph({
            alignment: AlignmentType.CENTER,
            children: [
              new TextRun({
                text: "Page ",
                font: FONT,
                size: 18,
                color: MGRAY
              }),
              new TextRun({
                children: [PageNumber],
                font: FONT,
                size: 18,
                color: MGRAY
              })
            ]
          })
        ]
      })
    },
    children
  }]
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync(outputPath, buffer);
  console.log(`✓ Faculty guide generated successfully`);
  console.log(`  Output: ${outputPath}`);
}).catch(err => {
  console.error(`ERROR: Failed to write DOCX: ${err.message}`);
  process.exit(1);
});
