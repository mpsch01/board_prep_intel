/**
 * build_cookbook_protocol.js — Generates a self-contained cookbook-style protocol DOCX.
 *
 * This document describes EVERYTHING needed to rebuild the PDF-to-DOCX clinical
 * guideline extraction pipeline from scratch. No external references or prior knowledge
 * required — just follow the steps.
 *
 * Usage:  node build_cookbook_protocol.js
 * Output: ~/Desktop/Guideline_Extractor_Cookbook.docx
 */

const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
        HeadingLevel, AlignmentType, BorderStyle, WidthType, ShadingType,
        LevelFormat, PageBreak } = require('docx');
const fs   = require('fs');
const path = require('path');
const os   = require('os');

// ── Colors ──────────────────────────────────────────────────────
const NAVY   = "1F3864";
const BLUE   = "2E75B6";
const LBLUE  = "D6E4F7";
const WHITE  = "FFFFFF";
const LGRAY  = "F2F2F2";
const DGRAY  = "595959";
const AMBER  = "FFF2CC";
const TEAL   = "E2EFDA";
const DTEAL  = "2D572C";
const RED    = "C00000";
const LRED   = "FFDEDE";
const BORDER  = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const BORDERS = { top: BORDER, bottom: BORDER, left: BORDER, right: BORDER };
const NO_BORDER  = { style: BorderStyle.NONE, size: 0, color: WHITE };
const NO_BORDERS = { top: NO_BORDER, bottom: NO_BORDER, left: NO_BORDER, right: NO_BORDER };

const W = 9360;  // content width (US Letter, 0.75" margins)

// ── Helpers ─────────────────────────────────────────────────────
function hdr(text, level = 1) {
  return new Paragraph({
    heading: level === 1 ? HeadingLevel.HEADING_1
           : level === 2 ? HeadingLevel.HEADING_2
           : HeadingLevel.HEADING_3,
    spacing: { before: level === 1 ? 360 : 240, after: 120 },
    children: [new TextRun({ text, bold: true,
      color: level === 1 ? NAVY : level === 2 ? BLUE : DGRAY,
      size:  level === 1 ? 28  : level === 2 ? 24  : 22,
      font: "Arial" })]
  });
}

function para(text, opts = {}) {
  const { bold = false, italic = false, color = "000000", size = 22,
          indent = 0, spaceBefore = 60, spaceAfter = 60, center = false } = opts;
  return new Paragraph({
    alignment: center ? AlignmentType.CENTER : AlignmentType.LEFT,
    indent: indent ? { left: indent } : undefined,
    spacing: { before: spaceBefore, after: spaceAfter },
    children: [new TextRun({ text, bold, italic, color, size, font: "Arial" })]
  });
}

function richPara(runs, opts = {}) {
  const { indent = 0, spaceBefore = 60, spaceAfter = 60 } = opts;
  return new Paragraph({
    indent: indent ? { left: indent } : undefined,
    spacing: { before: spaceBefore, after: spaceAfter },
    children: runs.map(r => new TextRun({ font: "Arial", size: 20, ...r }))
  });
}

function bullet(text, level = 0, opts = {}) {
  const { bold = false, color = "000000" } = opts;
  return new Paragraph({
    numbering: { reference: "bullets", level },
    spacing: { before: 40, after: 40 },
    children: [new TextRun({ text, bold, color, size: 20, font: "Arial" })]
  });
}

function numbered(text, level = 0, opts = {}) {
  const { bold = false, color = "000000" } = opts;
  return new Paragraph({
    numbering: { reference: "numbers", level },
    spacing: { before: 40, after: 40 },
    children: [new TextRun({ text, bold, color, size: 20, font: "Arial" })]
  });
}

function gap(n = 1) {
  return new Paragraph({ spacing: { before: n * 60, after: n * 60 }, children: [] });
}

function hr() {
  return new Paragraph({
    spacing: { before: 120, after: 120 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: BLUE, space: 1 } },
    children: []
  });
}

function hCell(text, width, fill = NAVY) {
  return new TableCell({
    width: { size: width, type: WidthType.DXA },
    shading: { fill, type: ShadingType.CLEAR },
    margins: { top: 80, bottom: 80, left: 120, right: 120 },
    borders: BORDERS,
    children: [new Paragraph({
      alignment: AlignmentType.LEFT,
      children: [new TextRun({ text, bold: true, color: WHITE, size: 18, font: "Arial" })]
    })]
  });
}

function dCell(text, width, fill = WHITE, bold = false, color = "000000") {
  return new TableCell({
    width: { size: width, type: WidthType.DXA },
    shading: { fill, type: ShadingType.CLEAR },
    margins: { top: 80, bottom: 80, left: 120, right: 120 },
    borders: BORDERS,
    children: [new Paragraph({
      children: [new TextRun({ text: String(text || ""), bold, color, size: 18, font: "Arial" })]
    })]
  });
}

function codeBlock(lines) {
  return lines.map(line => new Paragraph({
    spacing: { before: 10, after: 10 },
    indent: { left: 360 },
    shading: { fill: "F5F5F5", type: ShadingType.CLEAR },
    children: [new TextRun({ text: line, font: "Consolas", size: 17, color: "333333" })]
  }));
}

function multiCellPara(runs) {
  return new Paragraph({
    children: runs.map(r => new TextRun({ font: "Arial", size: 18, ...r }))
  });
}

// Multi-line cell: array of text lines -> single cell with multiple paragraphs
function dCellMulti(lines, width, fill = WHITE) {
  return new TableCell({
    width: { size: width, type: WidthType.DXA },
    shading: { fill, type: ShadingType.CLEAR },
    margins: { top: 80, bottom: 80, left: 120, right: 120 },
    borders: BORDERS,
    children: lines.map(line => new Paragraph({
      children: [new TextRun({ text: line, size: 18, font: "Arial", color: "000000" })]
    }))
  });
}

function sectionBanner(text) {
  return new Paragraph({
    spacing: { before: 240, after: 120 },
    shading: { fill: NAVY, type: ShadingType.CLEAR },
    children: [new TextRun({ text: "  " + text, bold: true, color: WHITE, size: 24, font: "Arial" })]
  });
}

// ══════════════════════════════════════════════════════════════════
//  DOCUMENT CONTENT
// ══════════════════════════════════════════════════════════════════

const children = [];

// ── COVER ──────────────────────────────────────────────────────
children.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { before: 1200, after: 60 },
  children: [new TextRun({ text: "CLINICAL GUIDELINE EXTRACTOR", bold: true, color: NAVY, size: 40, font: "Arial" })]
}));
children.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { before: 0, after: 60 },
  children: [new TextRun({ text: "Complete Build Protocol", bold: true, color: BLUE, size: 32, font: "Arial" })]
}));
children.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { before: 0, after: 240 },
  children: [new TextRun({ text: "A self-contained cookbook for building the PDF-to-DOCX pipeline from scratch", italic: true, color: DGRAY, size: 22, font: "Arial" })]
}));
children.push(hr());
children.push(para("This document contains every ingredient, every step, and every configuration needed to build a working clinical guideline extraction pipeline. No prior knowledge of the system is assumed.", { size: 20, color: DGRAY }));
children.push(gap(1));

// Overview box
children.push(new Paragraph({
  spacing: { before: 120, after: 60 },
  shading: { fill: LBLUE, type: ShadingType.CLEAR },
  children: [new TextRun({ text: "  WHAT THIS PIPELINE DOES", bold: true, color: NAVY, size: 20, font: "Arial" })]
}));
children.push(para("Right-click any clinical guideline PDF anywhere on your computer. The pipeline automatically:", { size: 20, color: "333333", indent: 180 }));
children.push(numbered("Extracts the full text from the PDF", 0));
children.push(numbered("Classifies the document type (chronic, acute, preventive, diagnostic, or RCT)", 0));
children.push(numbered("Routes to a specialized extraction engine that pulls structured clinical data via LLM", 0));
children.push(numbered("Synthesizes a physician-focused narrative with practice pearls and critical alerts", 0));
children.push(numbered("Generates a professionally styled summary Word document next to the original PDF", 0));
children.push(gap(1));
children.push(para("The output is a DOCX with color-coded recommendation tables, grouped medications, red flags with clinical context, definitions, and a clinical bottom line \u2014 designed for rapid board review.", { size: 20, color: "333333" }));

children.push(new Paragraph({ children: [new PageBreak()] }));

// ══════════════════════════════════════════════════════════════════
//  SECTION 1: PREREQUISITES
// ══════════════════════════════════════════════════════════════════

children.push(sectionBanner("1. PREREQUISITES"));
children.push(gap(1));
children.push(hdr("Software Requirements", 2));

children.push(new Table({
  width: { size: W, type: WidthType.DXA },
  columnWidths: [1800, 2400, 5160],
  rows: [
    new TableRow({ tableHeader: true, children: [
      hCell("Tool", 1800), hCell("Version", 2400), hCell("Purpose", 5160)
    ]}),
    new TableRow({ children: [
      dCell("Python", 1800, LGRAY, true), dCell("3.10+", 2400, LGRAY), dCell("PDF extraction engine, LLM API calls", 5160, LGRAY)
    ]}),
    new TableRow({ children: [
      dCell("Node.js", 1800, WHITE, true), dCell("18+", 2400), dCell("Synthesis layer and DOCX generation", 5160)
    ]}),
    new TableRow({ children: [
      dCell("npm", 1800, LGRAY, true), dCell("(bundled with Node)", 2400, LGRAY), dCell("Install the 'docx' package", 5160, LGRAY)
    ]}),
  ]
}));

children.push(gap(1));
children.push(hdr("Python Packages", 2));
children.push(para("Install from the project root:", { size: 20, color: DGRAY }));
children.push(...codeBlock(["pip install anthropic>=0.25.0 pdfplumber>=0.10.0"]));
children.push(gap(1));

children.push(new Table({
  width: { size: W, type: WidthType.DXA },
  columnWidths: [2400, 6960],
  rows: [
    new TableRow({ tableHeader: true, children: [
      hCell("Package", 2400), hCell("What It Does", 6960)
    ]}),
    new TableRow({ children: [
      dCell("anthropic", 2400, LGRAY, true), dCell("Official Anthropic Python SDK \u2014 sends text to Claude models for classification, extraction, and metadata parsing", 6960, LGRAY)
    ]}),
    new TableRow({ children: [
      dCell("pdfplumber", 2400, WHITE, true), dCell("Extracts text from PDF files page-by-page, handles multi-column layouts and embedded tables", 6960)
    ]}),
  ]
}));

children.push(gap(1));
children.push(hdr("Node.js Package", 2));
children.push(para("Install from a shared node_modules directory:", { size: 20, color: DGRAY }));
children.push(...codeBlock(["npm install docx"]));
children.push(para("The 'docx' package (docx-js) generates Word documents programmatically from JavaScript objects.", { size: 18, color: DGRAY, italic: true }));

children.push(gap(1));
children.push(hdr("Anthropic API Key", 2));
children.push(para("You need a valid Anthropic API key (starts with sk-ant-...). The system checks for it in this order:", { size: 20, color: "333333" }));
children.push(numbered("Environment variable: ANTHROPIC_API_KEY", 0));
children.push(numbered("Windows User registry: HKCU\\Environment\\ANTHROPIC_API_KEY (for right-click context menu launches where env vars may not be inherited)", 0));
children.push(numbered("config.json at project root: {\"ANTHROPIC_API_KEY\": \"sk-ant-...\"}", 0));
children.push(gap(1));
children.push(para("To set it permanently on Windows (survives reboots):", { size: 20, color: DGRAY }));
children.push(...codeBlock([
  "[System.Environment]::SetEnvironmentVariable(",
  "  \"ANTHROPIC_API_KEY\", \"sk-ant-YOUR-KEY-HERE\", \"User\"",
  ")"
]));

children.push(gap(1));
children.push(hdr("LLM Models Used", 2));
children.push(new Table({
  width: { size: W, type: WidthType.DXA },
  columnWidths: [2400, 3600, 3360],
  rows: [
    new TableRow({ tableHeader: true, children: [
      hCell("Stage", 2400), hCell("Model ID", 3600), hCell("Used For", 3360)
    ]}),
    new TableRow({ children: [
      dCell("Python Extraction", 2400, LGRAY, true), dCell("claude-sonnet-4-20250514", 3600, LGRAY), dCell("Classification, metadata, and clinical data extraction from PDF text", 3360, LGRAY)
    ]}),
    new TableRow({ children: [
      dCell("Node.js Synthesis", 2400, WHITE, true), dCell("claude-sonnet-4-6", 3600), dCell("Clinical narrative, practice pearls, medication grouping, critical alerts", 3360)
    ]}),
  ]
}));

children.push(new Paragraph({ children: [new PageBreak()] }));

// ══════════════════════════════════════════════════════════════════
//  SECTION 2: PROJECT STRUCTURE
// ══════════════════════════════════════════════════════════════════

children.push(sectionBanner("2. PROJECT STRUCTURE"));
children.push(gap(1));
children.push(para("Create this directory structure. Every file is described in detail in later sections.", { size: 20, color: "333333" }));
children.push(gap(1));

const treeLines = [
  "guideline_extractor_v2/",
  "\u251C\u2500\u2500 requirements.txt         # Python dependencies",
  "\u251C\u2500\u2500 config.json              # (optional) API key fallback",
  "\u251C\u2500\u2500 main.py                  # CLI entry point",
  "\u251C\u2500\u2500 core/",
  "\u2502   \u251C\u2500\u2500 __init__.py",
  "\u2502   \u251C\u2500\u2500 ingestion.py         # Pipeline orchestrator (entry point for extraction)",
  "\u2502   \u251C\u2500\u2500 routing.py           # Maps document_type \u2192 engine class",
  "\u2502   \u2514\u2500\u2500 screening.py         # LLM classifier + RCT heuristic pre-screen",
  "\u251C\u2500\u2500 engines/",
  "\u2502   \u251C\u2500\u2500 __init__.py",
  "\u2502   \u251C\u2500\u2500 base_engine.py       # Abstract base class, schema scaffold",
  "\u2502   \u251C\u2500\u2500 chronic_engine.py     # Chronic disease guidelines",
  "\u2502   \u251C\u2500\u2500 acute_engine.py       # Acute/emergency protocols",
  "\u2502   \u251C\u2500\u2500 preventive_engine.py  # Screening & prevention guidelines",
  "\u2502   \u251C\u2500\u2500 diagnostic_engine.py  # Diagnostic workup guidelines",
  "\u2502   \u2514\u2500\u2500 rct_engine.py         # Randomized controlled trials",
  "\u251C\u2500\u2500 utils/",
  "\u2502   \u251C\u2500\u2500 __init__.py",
  "\u2502   \u251C\u2500\u2500 preprocess.py        # PDF/ZIP/text extraction (auto-detect by magic bytes)",
  "\u2502   \u251C\u2500\u2500 prompt_builder.py    # Anthropic API client, prompts, chunking logic",
  "\u2502   \u251C\u2500\u2500 validator.py          # Schema validation, field_coverage_score",
  "\u2502   \u2514\u2500\u2500 logger.py            # Per-run JSON logging",
  "\u251C\u2500\u2500 oneclick/",
  "\u2502   \u251C\u2500\u2500 extract_guideline.bat # Windows batch orchestrator",
  "\u2502   \u251C\u2500\u2500 synthesize.js        # LLM synthesis layer (Node.js)",
  "\u2502   \u251C\u2500\u2500 build_summary.js     # DOCX generator (Node.js)",
  "\u2502   \u251C\u2500\u2500 install_context_menu.reg   # Add right-click menu entries",
  "\u2502   \u2514\u2500\u2500 uninstall_context_menu.reg # Remove right-click menu entries",
  "\u2514\u2500\u2500 logs/                    # Auto-created at runtime",
];
children.push(...codeBlock(treeLines));

children.push(new Paragraph({ children: [new PageBreak()] }));

// ══════════════════════════════════════════════════════════════════
//  SECTION 3: THE EXTRACTION ENGINE (Python)
// ══════════════════════════════════════════════════════════════════

children.push(sectionBanner("3. THE EXTRACTION ENGINE (Python)"));
children.push(gap(1));
children.push(para("This is the core of the pipeline. A single Python function, ingest_document(file_path), takes any PDF and returns a structured JSON dict with all extracted clinical data. Internally it chains 6 steps:", { size: 20, color: "333333" }));
children.push(gap(1));

// Pipeline flow diagram
children.push(new Table({
  width: { size: W, type: WidthType.DXA },
  columnWidths: [600, 2160, 6600],
  rows: [
    new TableRow({ tableHeader: true, children: [
      hCell("#", 600), hCell("Step", 2160), hCell("What Happens", 6600)
    ]}),
    new TableRow({ children: [
      dCell("1", 600, TEAL, true), dCell("Preprocess", 2160, TEAL, true),
      dCell("Detect file format by magic bytes (%PDF, PK/ZIP, or plaintext). Extract full text via pdfplumber. Clean whitespace and control characters.", 6600, TEAL)
    ]}),
    new TableRow({ children: [
      dCell("2", 600, WHITE, true), dCell("Extract Metadata", 2160, WHITE, true),
      dCell("Send the first 2,000 chars to Claude. Returns: title, organization, publication_year, version_number, doi.", 6600)
    ]}),
    new TableRow({ children: [
      dCell("3", 600, TEAL, true), dCell("Classify Document", 2160, TEAL, true),
      dCell("RCT heuristic pre-screen (checks for journal names + trial keywords). Then LLM classifier sends first 3,000 chars to Claude with strict type definitions. Returns document_type + confidence score.", 6600, TEAL)
    ]}),
    new TableRow({ children: [
      dCell("4", 600, WHITE, true), dCell("Route to Engine", 2160, WHITE, true),
      dCell("Map document_type to the correct extraction engine class (5 specialized engines + unknown fallback).", 6600)
    ]}),
    new TableRow({ children: [
      dCell("5", 600, TEAL, true), dCell("Extract Clinical Data", 2160, TEAL, true),
      dCell("Engine sends full text (or chunks for large docs) to Claude with a type-specific prompt. Returns structured JSON with summary, population, recommendations, medications, thresholds, red flags, follow-up, escalation.", 6600, TEAL)
    ]}),
    new TableRow({ children: [
      dCell("6", 600, WHITE, true), dCell("Validate & Log", 2160, WHITE, true),
      dCell("Check schema compliance, compute field_coverage_score (0.0\u20131.0), write per-run JSON log. Warnings are non-fatal.", 6600)
    ]}),
  ]
}));

children.push(gap(1));
children.push(hdr("3.1 Preprocessing (utils/preprocess.py)", 2));
children.push(para("Accepts any file path. Auto-detects format by reading the first 4 bytes (magic bytes):", { size: 20, color: "333333" }));
children.push(new Table({
  width: { size: W, type: WidthType.DXA },
  columnWidths: [2400, 2400, 4560],
  rows: [
    new TableRow({ tableHeader: true, children: [
      hCell("Magic Bytes", 2400), hCell("Format", 2400), hCell("Handler", 4560)
    ]}),
    new TableRow({ children: [
      dCell("%PDF", 2400, LGRAY, true), dCell("PDF", 2400, LGRAY),
      dCell("pdfplumber extracts text page-by-page, joins all pages", 4560, LGRAY)
    ]}),
    new TableRow({ children: [
      dCell("PK (0x504B)", 2400, WHITE, true), dCell("ZIP archive", 2400),
      dCell("Unzips, finds .txt/.pdf inside, extracts text from each", 4560)
    ]}),
    new TableRow({ children: [
      dCell("(anything else)", 2400, LGRAY, true), dCell("Plain text", 2400, LGRAY),
      dCell("Reads file directly as UTF-8 text", 4560, LGRAY)
    ]}),
  ]
}));
children.push(para("After extraction, _clean_text() normalizes whitespace and strips control characters.", { size: 18, italic: true, color: DGRAY }));

children.push(gap(1));
children.push(hdr("3.2 Document Classification (core/screening.py)", 2));
children.push(para("Two-stage classification: a fast heuristic pre-screen for RCTs, then an LLM classifier for everything else.", { size: 20, color: "333333" }));
children.push(gap(1));
children.push(hdr("RCT Pre-Screen Heuristic", 3));
children.push(para("Checks for journal name patterns (NEJM, Lancet, JAMA, BMJ, Annals of Internal Medicine) AND content patterns (randomized, hazard ratio, intention-to-treat, confidence interval, Kaplan-Meier). If both match, immediately classifies as RCT with confidence 0.90 without spending an API call.", { size: 20, color: "333333" }));

children.push(gap(1));
children.push(hdr("LLM Classifier", 3));
children.push(para("Sends the first 3,000 characters of document text to Claude with strict type definitions. Returns:", { size: 20, color: "333333" }));
children.push(bullet("document_type: one of 6 types (see routing table below)", 0));
children.push(bullet("confidence: float 0.0\u20131.0", 0));
children.push(bullet("signals: up to 5 text phrases that drove the classification", 0));
children.push(bullet("body_systems: list of body systems involved (e.g., [\"respiratory\", \"cardiovascular\"])", 0));
children.push(bullet("numeric_threshold_present: boolean", 0));

children.push(gap(1));
children.push(hdr("Document Type Definitions", 3));
children.push(new Table({
  width: { size: W, type: WidthType.DXA },
  columnWidths: [2200, 7160],
  rows: [
    new TableRow({ tableHeader: true, children: [
      hCell("Type", 2200), hCell("Definition & Signals", 7160)
    ]}),
    new TableRow({ children: [
      dCell("chronic_guideline", 2200, LGRAY, true),
      dCell("Long-term management of chronic conditions. Signals: stepwise therapy, medication titration, lifestyle modification, risk stratification over time. Examples: COPD, HTN, DM, HF.", 7160, LGRAY)
    ]}),
    new TableRow({ children: [
      dCell("acute_protocol", 2200, WHITE, true),
      dCell("Acute, time-sensitive, or emergency condition management. Signals: treatment windows, emergency medications, severity triage, disposition decisions. Examples: sepsis, croup, diverticulitis.", 7160)
    ]}),
    new TableRow({ children: [
      dCell("preventive_guideline", 2200, LGRAY, true),
      dCell("Screening, prevention, or health maintenance in asymptomatic populations. Signals: screening intervals, USPSTF grades, age/risk eligibility, chemoprophylaxis. Examples: lung cancer screening, statin prevention.", 7160, LGRAY)
    ]}),
    new TableRow({ children: [
      dCell("diagnostic_guideline", 2200, WHITE, true),
      dCell("Diagnostic workup, test interpretation, imaging decision trees. Signals: diagnostic criteria, test thresholds, biopsy indications, classification systems. Examples: thyroid nodule workup, spirometry interpretation.", 7160)
    ]}),
    new TableRow({ children: [
      dCell("rct", 2200, LGRAY, true),
      dCell("Primary research article from a randomized controlled trial. Signals: METHODS section, randomization, trial arms, hazard ratios, p-values. Examples: COMPASS trial, VOYAGER PAD.", 7160, LGRAY)
    ]}),
    new TableRow({ children: [
      dCell("unknown", 2200, WHITE, true),
      dCell("Cannot confidently classify. Falls back to chronic_guideline engine.", 7160)
    ]}),
  ]
}));

children.push(gap(1));
children.push(hdr("3.3 Engine Routing (core/routing.py)", 2));
children.push(para("A simple mapping from document_type to engine class:", { size: 20, color: "333333" }));
children.push(new Table({
  width: { size: W, type: WidthType.DXA },
  columnWidths: [2800, 3280, 3280],
  rows: [
    new TableRow({ tableHeader: true, children: [
      hCell("document_type", 2800), hCell("Engine Class", 3280), hCell("Specialized Modules", 3280)
    ]}),
    new TableRow({ children: [
      dCell("chronic_guideline", 2800, LGRAY, true), dCell("ChronicRiskEngine", 3280, LGRAY),
      dCell("disease_definition, diagnostic_thresholds, risk_stratification, escalation_ladder, medication_management, monitoring_schedule", 3280, LGRAY)
    ]}),
    new TableRow({ children: [
      dCell("acute_protocol", 2800, WHITE, true), dCell("AcuteProtocolEngine", 3280),
      dCell("urgency_triage, stabilization_steps, critical_thresholds, emergency_medications, escalation_triggers, disposition", 3280)
    ]}),
    new TableRow({ children: [
      dCell("preventive_guideline", 2800, LGRAY, true), dCell("PreventiveEngine", 3280, LGRAY),
      dCell("screening_population, screening_intervals, risk_stratification, preventive_medications, counseling_interventions, positive_screen_pathway", 3280, LGRAY)
    ]}),
    new TableRow({ children: [
      dCell("diagnostic_guideline", 2800, WHITE, true), dCell("DiagnosticEngine", 3280),
      dCell("diagnostic_criteria, test_thresholds, workup_algorithm, result_interpretation, referral_indications, follow_up_imaging", 3280)
    ]}),
    new TableRow({ children: [
      dCell("rct", 2800, LGRAY, true), dCell("RCTEngine", 3280, LGRAY),
      dCell("trial_design, population_eligibility, intervention_comparator, primary_endpoints, statistical_results, safety_adverse_events, clinical_implications", 3280, LGRAY)
    ]}),
    new TableRow({ children: [
      dCell("unknown", 2800, WHITE, true), dCell("ChronicRiskEngine", 3280),
      dCell("(falls back to chronic engine)", 3280)
    ]}),
  ]
}));

children.push(new Paragraph({ children: [new PageBreak()] }));

children.push(hdr("3.4 LLM Extraction (utils/prompt_builder.py)", 2));
children.push(para("Each engine type has its own system prompt and user prompt. The system prompt establishes the extraction role and calibration rules (evidence levels, units). The user prompt defines the exact JSON fields to return.", { size: 20, color: "333333" }));

children.push(gap(1));
children.push(hdr("Extraction Output Fields (all engine types)", 3));
children.push(para("Every engine extracts the same 8 fields, but prompts are tuned per type:", { size: 20, color: "333333" }));
children.push(new Table({
  width: { size: W, type: WidthType.DXA },
  columnWidths: [2200, 3000, 4160],
  rows: [
    new TableRow({ tableHeader: true, children: [
      hCell("Field", 2200), hCell("Type", 3000), hCell("Content", 4160)
    ]}),
    new TableRow({ children: [
      dCell("summary", 2200, LGRAY, true), dCell("string", 3000, LGRAY),
      dCell("2\u20133 sentence clinical summary", 4160, LGRAY)
    ]}),
    new TableRow({ children: [
      dCell("population", 2200, WHITE, true), dCell("object", 3000),
      dCell("age_criteria, risk_criteria, disease_definition, exclusions, severity_staging", 4160)
    ]}),
    new TableRow({ children: [
      dCell("key_thresholds", 2200, LGRAY, true), dCell("array of objects", 3000, LGRAY),
      dCell("Each: parameter, value, unit, context", 4160, LGRAY)
    ]}),
    new TableRow({ children: [
      dCell("recommendations", 2200, WHITE, true), dCell("array of objects", 3000),
      dCell("Each: recommendation, strength, evidence_level, notes", 4160)
    ]}),
    new TableRow({ children: [
      dCell("medications", 2200, LGRAY, true), dCell("array of objects", 3000, LGRAY),
      dCell("Each: drug, dose, indication, class", 4160, LGRAY)
    ]}),
    new TableRow({ children: [
      dCell("red_flags", 2200, WHITE, true), dCell("array of strings", 3000),
      dCell("Clinical warning signs requiring escalation", 4160)
    ]}),
    new TableRow({ children: [
      dCell("follow_up", 2200, LGRAY, true), dCell("string", 3000, LGRAY),
      dCell("Recommended monitoring/follow-up schedule", 4160, LGRAY)
    ]}),
    new TableRow({ children: [
      dCell("escalation_path", 2200, WHITE, true), dCell("string", 3000),
      dCell("When/how to escalate care", 4160)
    ]}),
  ]
}));

children.push(gap(1));
children.push(hdr("Calibration Rules (baked into system prompts)", 3));
children.push(bullet("Evidence levels: Never leave empty. Expand single letters: A \u2192 \"Grade A (strong evidence, RCT-based)\", B \u2192 \"Grade B (moderate evidence, observational)\", C \u2192 \"Grade C (expert consensus)\". If guideline has no grading, infer from study design.", 0));
children.push(bullet("Strength: Never leave empty. Infer from language: \"should\"/\"recommend\" \u2192 Strong, \"may\"/\"consider\" \u2192 Conditional.", 0));
children.push(bullet("Units: Never leave blank for numeric thresholds. Use standard clinical notation: mmHg, mg/dL, years, points, %.", 0));

children.push(gap(1));
children.push(hdr("Chunked Extraction (large documents)", 3));
children.push(para("Documents exceeding 15,000 characters are automatically split into overlapping chunks and processed in parallel:", { size: 20, color: "333333" }));
children.push(new Table({
  width: { size: W, type: WidthType.DXA },
  columnWidths: [3600, 5760],
  rows: [
    new TableRow({ tableHeader: true, children: [
      hCell("Parameter", 3600), hCell("Value", 5760)
    ]}),
    new TableRow({ children: [
      dCell("LARGE_DOC_THRESHOLD", 3600, LGRAY, true), dCell("15,000 characters \u2014 documents above this get chunked", 5760, LGRAY)
    ]}),
    new TableRow({ children: [
      dCell("CHUNK_SIZE", 3600, WHITE, true), dCell("25,000 characters per chunk", 5760)
    ]}),
    new TableRow({ children: [
      dCell("CHUNK_OVERLAP", 3600, LGRAY, true), dCell("2,500 characters overlap between adjacent chunks", 5760, LGRAY)
    ]}),
    new TableRow({ children: [
      dCell("MAX_CHUNKS", 3600, WHITE, true), dCell("12 chunks maximum (\u2248272k characters total coverage)", 5760)
    ]}),
    new TableRow({ children: [
      dCell("Parallelism", 3600, LGRAY, true), dCell("2 concurrent workers, 5-second stagger between pairs (stays under 30k TPM free-tier limit)", 5760, LGRAY)
    ]}),
    new TableRow({ children: [
      dCell("Retry on rate limit", 3600, WHITE, true), dCell("Exponential backoff: 2s, 4s, 8s, 16s on HTTP 429", 5760)
    ]}),
    new TableRow({ children: [
      dCell("Merge strategy", 3600, LGRAY, true), dCell("Scalars: first non-empty wins. Lists: union, deduplicated by first 60 chars of primary text field.", 5760, LGRAY)
    ]}),
  ]
}));

children.push(gap(1));
children.push(hdr("3.5 Validation (utils/validator.py)", 2));
children.push(para("After extraction, validate_output() checks the full JSON dict against the schema:", { size: 20, color: "333333" }));
children.push(bullet("Verifies all 5 top-level keys exist: source, classification, extraction, governance, metadata", 0));
children.push(bullet("Checks required sub-fields in each block", 0));
children.push(bullet("Computes field_coverage_score (0.0\u20131.0) \u2014 fraction of 8 extraction fields populated, with population sub-fields contributing fractionally", 0));
children.push(bullet("Returns a list of warnings (non-fatal). Coverage below 0.50 triggers a warning.", 0));

children.push(gap(1));
children.push(hdr("3.6 Logging (utils/logger.py)", 2));
children.push(para("Each extraction run writes a JSON log file to logs/ with: timestamp, run_id, file_name, document_type, engine_used, confidence, body_systems, module list, text size, validation status, and counts of recommendations/thresholds/medications. Also appends to session_log.jsonl for batch summary.", { size: 20, color: "333333" }));

children.push(gap(1));
children.push(hdr("3.7 The Orchestrator (core/ingestion.py)", 2));
children.push(para("ingest_document(file_path) chains all of the above:", { size: 20, color: "333333" }));
children.push(...codeBlock([
  "def ingest_document(file_path, run_id=None):",
  "    text = preprocess(file_path)",
  "    meta = extract_metadata(text)",
  "    screening_result = screening_classifier(text)",
  "    engine = route_document(screening_result)",
  "    output = engine.extract(text)",
  "    output[\"source\"].update({",
  "        \"title\": meta[\"title\"],",
  "        \"organization\": meta[\"organization\"],",
  "        \"publication_year\": meta[\"publication_year\"],",
  "        \"version_number\": meta[\"version_number\"],",
  "        \"doi\": meta[\"doi\"],",
  "        \"file_name\": os.path.basename(file_path),",
  "    })",
  "    warnings = validate_output(output)",
  "    output[\"metadata\"][\"validation_passed\"] = len(warnings) == 0",
  "    output[\"metadata\"][\"validation_warnings\"] = warnings",
  "    output[\"metadata\"][\"raw_text_chars\"] = len(text)",
  "    log_run(output, run_id=run_id)",
  "    return output",
]));
children.push(para("Returns a single dict conforming to the unified_v1.0 schema (documented next).", { size: 18, color: DGRAY, italic: true }));

children.push(new Paragraph({ children: [new PageBreak()] }));

// ══════════════════════════════════════════════════════════════════
//  SECTION 4: THE JSON SCHEMA (unified_v1.0)
// ══════════════════════════════════════════════════════════════════

children.push(sectionBanner("4. THE JSON SCHEMA (unified_v1.0)"));
children.push(gap(1));
children.push(para("Every extraction produces a JSON object with exactly 5 top-level blocks. This is the contract between the Python extraction engine and the Node.js layers that consume it.", { size: 20, color: "333333" }));
children.push(gap(1));

children.push(hdr("Top-Level Structure", 2));
children.push(...codeBlock([
  "{",
  "  \"source\":         { ... },   // Document identity & bibliographic data",
  "  \"classification\": { ... },   // What type, which engine, confidence",
  "  \"extraction\":     { ... },   // All clinical content + synthesis{}",
  "  \"governance\":     { ... },   // Human QC scaffold (empty at extraction)",
  "  \"metadata\":       { ... }    // Run metadata, validation, coverage",
  "}",
]));

children.push(gap(1));
children.push(hdr("source", 2));
children.push(new Table({
  width: { size: W, type: WidthType.DXA },
  columnWidths: [2400, 1800, 5160],
  rows: [
    new TableRow({ tableHeader: true, children: [
      hCell("Field", 2400), hCell("Type", 1800), hCell("Description", 5160)
    ]}),
    ...[ ["title", "string", "Full document title"],
         ["organization", "string", "Publishing org or journal"],
         ["document_type", "string", "One of 6 types (from classification)"],
         ["publication_year", "int|null", "Year as integer"],
         ["version_number", "string", "Version/edition if stated"],
         ["doi", "string", "DOI if present"],
         ["file_name", "string", "Original PDF filename"],
    ].map(([f, t, d], i) => new TableRow({ children: [
      dCell(f, 2400, i % 2 === 0 ? LGRAY : WHITE, true),
      dCell(t, 1800, i % 2 === 0 ? LGRAY : WHITE),
      dCell(d, 5160, i % 2 === 0 ? LGRAY : WHITE)
    ]}))
  ]
}));

children.push(gap(1));
children.push(hdr("classification", 2));
children.push(new Table({
  width: { size: W, type: WidthType.DXA },
  columnWidths: [2400, 1800, 5160],
  rows: [
    new TableRow({ tableHeader: true, children: [
      hCell("Field", 2400), hCell("Type", 1800), hCell("Description", 5160)
    ]}),
    ...[ ["engine_used", "string", "Python class name (e.g. ChronicRiskEngine)"],
         ["document_type", "string", "Classified type"],
         ["confidence", "float", "0.0\u20131.0"],
         ["signals", "array", "Up to 5 classifier signal phrases"],
         ["body_systems", "array", "Body systems involved"],
    ].map(([f, t, d], i) => new TableRow({ children: [
      dCell(f, 2400, i % 2 === 0 ? LGRAY : WHITE, true),
      dCell(t, 1800, i % 2 === 0 ? LGRAY : WHITE),
      dCell(d, 5160, i % 2 === 0 ? LGRAY : WHITE)
    ]}))
  ]
}));

children.push(gap(1));
children.push(hdr("extraction", 2));
children.push(para("Contains the 8 clinical content fields (Section 3.4) plus an optional synthesis{} block added by the Node.js synthesis layer:", { size: 20, color: "333333" }));
children.push(new Table({
  width: { size: W, type: WidthType.DXA },
  columnWidths: [3200, 6160],
  rows: [
    new TableRow({ tableHeader: true, children: [
      hCell("synthesis.field", 3200), hCell("Description", 6160)
    ]}),
    new TableRow({ children: [
      dCell("clinical_bottom_line", 3200, LGRAY, true),
      dCell("2\u20133 paragraphs: what this guideline means for daily practice", 6160, LGRAY)
    ]}),
    new TableRow({ children: [
      dCell("practice_pearls", 3200, WHITE, true),
      dCell("Array of 3\u20135 concise, actionable takeaways", 6160)
    ]}),
    new TableRow({ children: [
      dCell("medication_groups", 3200, LGRAY, true),
      dCell("Array of {group_name, narrative, drugs[]} \u2014 medications grouped by clinical indication", 6160, LGRAY)
    ]}),
    new TableRow({ children: [
      dCell("critical_alerts", 3200, WHITE, true),
      dCell("Array of {alert, why_it_matters} \u2014 top red flags with clinical context", 6160)
    ]}),
    new TableRow({ children: [
      dCell("definitions_and_thresholds", 3200, LGRAY, true),
      dCell("Array of {term, definition} \u2014 high-yield clinical definitions and management-changing thresholds", 6160, LGRAY)
    ]}),
  ]
}));

children.push(gap(1));
children.push(hdr("metadata", 2));
children.push(new Table({
  width: { size: W, type: WidthType.DXA },
  columnWidths: [3000, 1400, 4960],
  rows: [
    new TableRow({ tableHeader: true, children: [
      hCell("Field", 3000), hCell("Type", 1400), hCell("Description", 4960)
    ]}),
    ...[ ["schema_version", "string", "\"unified_v1.0\""],
         ["run_id", "string", "8-char UUID"],
         ["extracted_at", "string", "ISO 8601 UTC timestamp"],
         ["engine_version", "string", "\"guideline_extractor_v2.3\""],
         ["modules_activated", "array", "Engine module names"],
         ["validation_passed", "bool", "true if zero warnings"],
         ["validation_warnings", "array", "List of warning strings"],
         ["field_coverage_score", "float", "0.0\u20131.0, fraction populated"],
         ["raw_text_chars", "int", "Character count of input text"],
    ].map(([f, t, d], i) => new TableRow({ children: [
      dCell(f, 3000, i % 2 === 0 ? LGRAY : WHITE, true),
      dCell(t, 1400, i % 2 === 0 ? LGRAY : WHITE),
      dCell(d, 4960, i % 2 === 0 ? LGRAY : WHITE)
    ]}))
  ]
}));

children.push(new Paragraph({ children: [new PageBreak()] }));

// ══════════════════════════════════════════════════════════════════
//  SECTION 5: SYNTHESIS LAYER (synthesize.js)
// ══════════════════════════════════════════════════════════════════

children.push(sectionBanner("5. THE SYNTHESIS LAYER (oneclick/synthesize.js)"));
children.push(gap(1));
children.push(para("After Python produces the raw extraction JSON, this Node.js script sends it to Claude Sonnet for clinical narrative synthesis. It reads the JSON file, builds a prompt from the raw data, calls the Anthropic API, and writes the synthesis{} block back into the JSON in-place.", { size: 20, color: "333333" }));

children.push(gap(1));
children.push(hdr("How It Works", 2));
children.push(numbered("Reads the extraction JSON (produced by Python in %TEMP%)", 0));
children.push(numbered("Builds a snapshot from: title, document_type, summary, population, recommendations (first 20), medications (first 25), red_flags (first 30), key_thresholds (first 15), follow_up, escalation_path", 0));
children.push(numbered("Sends snapshot to Claude Sonnet (claude-sonnet-4-6, max 4,000 tokens) with a detailed prompt", 0));
children.push(numbered("Parses the response as JSON (handles both raw JSON and markdown-fenced responses)", 0));
children.push(numbered("Validates required fields (clinical_bottom_line and practice_pearls must exist)", 0));
children.push(numbered("Writes extraction.synthesis = {...} back into the JSON file", 0));

children.push(gap(1));
children.push(hdr("Failure Handling", 2));
children.push(para("Synthesis is non-fatal. If the API call fails, if the response is unparseable, or if the API key is missing, the script logs a warning and exits cleanly (exit code 0). The pipeline continues and generates a DOCX from raw data only \u2014 without practice pearls, medication grouping, or critical alert context.", { size: 20, color: "333333" }));

children.push(gap(1));
children.push(hdr("Synthesis Prompt Details", 2));
children.push(para("The prompt instructs Claude to:", { size: 20, color: "333333" }));
children.push(bullet("clinical_bottom_line: Focus on what's NEW, DIFFERENT, or commonly missed. Be specific about which patients, what to do, when.", 0));
children.push(bullet("practice_pearls: Each starts with an action verb. Point-of-care level conciseness.", 0));
children.push(bullet("medication_groups: Group ALL medications by clinical scenario with a narrative explaining when/why.", 0));
children.push(bullet("critical_alerts: 5\u20138 most important red flags, each with a \"why it matters\" sentence.", 0));
children.push(bullet("definitions_and_thresholds: Only include thresholds where crossing the value changes what you DO. Include key clinical definitions (diagnostic criteria, staging). 5\u201312 entries.", 0));

children.push(gap(1));
children.push(hdr("Usage", 2));
children.push(...codeBlock([
  "node oneclick/synthesize.js <extraction.json>",
  "",
  "# Requires ANTHROPIC_API_KEY in environment",
  "# Modifies the JSON file in-place (adds extraction.synthesis)",
]));

children.push(new Paragraph({ children: [new PageBreak()] }));

// ══════════════════════════════════════════════════════════════════
//  SECTION 6: DOCX GENERATOR (build_summary.js)
// ══════════════════════════════════════════════════════════════════

children.push(sectionBanner("6. THE DOCX GENERATOR (oneclick/build_summary.js)"));
children.push(gap(1));
children.push(para("Reads the augmented extraction JSON and produces a professionally styled Word document. Uses the docx-js library (npm 'docx' package). Renders up to 11 sections, each conditional on data availability.", { size: 20, color: "333333" }));

children.push(gap(1));
children.push(hdr("Document Sections", 2));
children.push(new Table({
  width: { size: W, type: WidthType.DXA },
  columnWidths: [600, 2600, 6160],
  rows: [
    new TableRow({ tableHeader: true, children: [
      hCell("#", 600), hCell("Section", 2600), hCell("Content & Data Source", 6160)
    ]}),
    ...[ ["1", "Title Banner", "Navy fill, white text. Title, organization | year | DOI. Source: source{}"],
         ["2", "Classification Badge", "4-column table: doc type, engine, confidence %, body systems. Source: classification{}"],
         ["3", "Clinical Summary", "Extraction summary paragraph + synthesis clinical_bottom_line (2\u20133 paragraphs)"],
         ["4", "Practice Pearls", "Green banner + bullet list from synthesis.practice_pearls"],
         ["5", "Target Population", "2-column table: age, risk, disease def, exclusions, severity. Source: extraction.population"],
         ["6", "Definitions & Thresholds", "2-column table from synthesis.definitions_and_thresholds (deduped against medication names)"],
         ["7", "Recommendations", "4-column table, color-coded: Strong/High = teal, Conditional/Moderate = amber, Other = white"],
         ["8", "Medications", "Grouped by indication (synthesis.medication_groups with raw dose/class details) OR flat 4-col table fallback"],
         ["9", "Red Flags", "Critical alerts with context (synthesis) OR flat bullet list (raw). Red banner header."],
         ["10", "Follow-Up", "Paragraph from extraction.follow_up"],
         ["11", "Escalation Path", "Paragraph from extraction.escalation_path"],
    ].map(([n, s, d], i) => new TableRow({ children: [
      dCell(n, 600, i % 2 === 0 ? LGRAY : WHITE, true),
      dCell(s, 2600, i % 2 === 0 ? LGRAY : WHITE, true),
      dCell(d, 6160, i % 2 === 0 ? LGRAY : WHITE)
    ]}))
  ]
}));
children.push(para("+ Footer: extraction timestamp, engine version, validation status, coverage score.", { size: 18, italic: true, color: DGRAY }));

children.push(gap(1));
children.push(hdr("Color Palette", 2));
children.push(new Table({
  width: { size: W, type: WidthType.DXA },
  columnWidths: [1800, 1200, 6360],
  rows: [
    new TableRow({ tableHeader: true, children: [
      hCell("Name", 1800), hCell("Hex", 1200), hCell("Usage", 6360)
    ]}),
    ...[ ["NAVY", "1F3864", "Title banner, section headers, strong text"],
         ["BLUE", "2E75B6", "H2 headers, horizontal rules, classification badge header"],
         ["LBLUE", "D6E4F7", "Light blue fills, metadata text"],
         ["TEAL/E2EFDA", "E2EFDA", "Strong/High evidence row fill, practice pearls banner"],
         ["AMBER/FFF2CC", "FFF2CC", "Conditional/Moderate evidence row fill"],
         ["RED", "C00000", "Red flags banner, alert icons"],
         ["LGRAY", "F2F2F2", "Alternating table row fill"],
    ].map(([n, h, u], i) => new TableRow({ children: [
      dCell(n, 1800, i % 2 === 0 ? LGRAY : WHITE, true),
      dCell("#" + h, 1200, i % 2 === 0 ? LGRAY : WHITE),
      dCell(u, 6360, i % 2 === 0 ? LGRAY : WHITE)
    ]}))
  ]
}));

children.push(gap(1));
children.push(hdr("Table Pagination Settings", 2));
children.push(bullet("tableHeader: true on header rows \u2014 header repeats on every page when table spans pages", 0));
children.push(bullet("cantSplit: false on data rows \u2014 allows long rows to break across pages instead of pushing to next page", 0));
children.push(bullet("Page size: US Letter (12240 x 15840 DXA), 0.75\" margins (1080 DXA)", 0));

children.push(gap(1));
children.push(hdr("Usage", 2));
children.push(...codeBlock([
  "node oneclick/build_summary.js <input.json> <output.docx>",
  "",
  "# Requires NODE_PATH set to the directory containing 'docx' package",
]));

children.push(new Paragraph({ children: [new PageBreak()] }));

// ══════════════════════════════════════════════════════════════════
//  SECTION 7: BATCH ORCHESTRATOR (extract_guideline.bat)
// ══════════════════════════════════════════════════════════════════

children.push(sectionBanner("7. THE BATCH ORCHESTRATOR (oneclick/extract_guideline.bat)"));
children.push(gap(1));
children.push(para("A Windows batch script that ties everything together. Accepts a PDF path (or folder of PDFs) from anywhere on the system. The PDF never moves; the output DOCX appears right next to it.", { size: 20, color: "333333" }));

children.push(gap(1));
children.push(hdr("Single File Flow", 2));
children.push(new Table({
  width: { size: W, type: WidthType.DXA },
  columnWidths: [600, 2000, 6760],
  rows: [
    new TableRow({ tableHeader: true, children: [
      hCell("#", 600), hCell("Step", 2000), hCell("Detail", 6760)
    ]}),
    new TableRow({ children: [
      dCell("1", 600, TEAL, true), dCell("API Key", 2000, TEAL, true),
      dCell("Check %ANTHROPIC_API_KEY%. If empty, read from HKCU\\Environment registry. If still empty, show error.", 6760, TEAL)
    ]}),
    new TableRow({ children: [
      dCell("2", 600, WHITE, true), dCell("Python Extract", 2000, WHITE, true),
      dCell("cd to project root (needed for Python imports). Run: python -c \"from core.ingestion import ingest_document; ...\" Writes JSON to %TEMP%\\<name>_extracted.json", 6760)
    ]}),
    new TableRow({ children: [
      dCell("3", 600, TEAL, true), dCell("Node Synthesize", 2000, TEAL, true),
      dCell("node oneclick/synthesize.js \"%TEMP%\\<name>_extracted.json\" \u2014 Augments JSON with synthesis{} block", 6760, TEAL)
    ]}),
    new TableRow({ children: [
      dCell("4", 600, WHITE, true), dCell("Node Build DOCX", 2000, WHITE, true),
      dCell("node oneclick/build_summary.js \"%TEMP%\\...json\" \"<pdf_dir>\\<name>_summary.docx\"", 6760)
    ]}),
    new TableRow({ children: [
      dCell("5", 600, TEAL, true), dCell("Cleanup", 2000, TEAL, true),
      dCell("Delete temp JSON. Copy DOCX to Desktop as backup.", 6760, TEAL)
    ]}),
  ]
}));

children.push(gap(1));
children.push(hdr("Folder/Batch Mode", 2));
children.push(para("If the input is a directory, the script loops over all *.pdf files in that folder, processing each independently. Reports success/fail count at the end.", { size: 20, color: "333333" }));

children.push(gap(1));
children.push(hdr("Environment Variables Set by the Script", 2));
children.push(new Table({
  width: { size: W, type: WidthType.DXA },
  columnWidths: [2800, 6560],
  rows: [
    new TableRow({ tableHeader: true, children: [
      hCell("Variable", 2800), hCell("Value & Purpose", 6560)
    ]}),
    new TableRow({ children: [
      dCell("SCRIPT_DIR", 2800, LGRAY, true), dCell("Directory of the .bat file (oneclick/)", 6560, LGRAY)
    ]}),
    new TableRow({ children: [
      dCell("PROJECT_ROOT", 2800, WHITE, true), dCell("SCRIPT_DIR\\.. (project root, needed for Python imports)", 6560)
    ]}),
    new TableRow({ children: [
      dCell("NODE_MODULES", 2800, LGRAY, true), dCell("Path to shared node_modules (contains 'docx' package)", 6560, LGRAY)
    ]}),
    new TableRow({ children: [
      dCell("NODE_PATH", 2800, WHITE, true), dCell("Same as NODE_MODULES \u2014 tells Node.js where to find packages", 6560)
    ]}),
    new TableRow({ children: [
      dCell("NODE_OPTIONS", 2800, LGRAY, true), dCell("--no-warnings (suppress ExperimentalWarning noise)", 6560, LGRAY)
    ]}),
  ]
}));

children.push(gap(1));
children.push(hdr("Output Naming Convention", 2));
children.push(para("<original_name>.pdf \u2192 <original_name>_summary.docx (in the same directory as the PDF)", { size: 20, color: "333333", bold: true }));

children.push(new Paragraph({ children: [new PageBreak()] }));

// ══════════════════════════════════════════════════════════════════
//  SECTION 8: CONTEXT MENU INSTALLATION
// ══════════════════════════════════════════════════════════════════

children.push(sectionBanner("8. WINDOWS CONTEXT MENU INSTALLATION"));
children.push(gap(1));
children.push(para("Two registry files add right-click menu entries. No admin rights required \u2014 they write to HKCU (current user), not HKLM.", { size: 20, color: "333333" }));

children.push(gap(1));
children.push(hdr("install_context_menu.reg", 2));
children.push(para("Adds two entries:", { size: 20, color: "333333" }));
children.push(new Table({
  width: { size: W, type: WidthType.DXA },
  columnWidths: [2800, 3280, 3280],
  rows: [
    new TableRow({ tableHeader: true, children: [
      hCell("Menu Entry", 2800), hCell("Appears On", 3280), hCell("Registry Key", 3280)
    ]}),
    new TableRow({ children: [
      dCell("\"Extract Guideline\"", 2800, LGRAY, true),
      dCell("Any .pdf file", 3280, LGRAY),
      dCell("HKCU\\...\\SystemFileAssociations\\.pdf\\shell\\ExtractGuideline", 3280, LGRAY)
    ]}),
    new TableRow({ children: [
      dCell("\"Extract All Guidelines\"", 2800, WHITE, true),
      dCell("Any folder", 3280),
      dCell("HKCU\\...\\Directory\\shell\\ExtractAllGuidelines", 3280)
    ]}),
  ]
}));
children.push(para("Both invoke: extract_guideline.bat \"%1\" (passes the full path of the clicked item).", { size: 18, italic: true, color: DGRAY }));
children.push(gap(1));
children.push(para("On Windows 11: these entries appear under \"Show more options\" in the right-click menu (standard behavior for all third-party context menu entries).", { size: 20, color: "333333" }));

children.push(gap(1));
children.push(hdr("How to Install", 2));
children.push(numbered("Double-click install_context_menu.reg", 0));
children.push(numbered("Click \"Yes\" when Windows asks to confirm", 0));
children.push(numbered("Right-click any PDF \u2192 \"Show more options\" \u2192 \"Extract Guideline\"", 0));

children.push(gap(1));
children.push(hdr("How to Uninstall", 2));
children.push(para("Double-click uninstall_context_menu.reg to remove both entries.", { size: 20, color: "333333" }));

children.push(gap(1));
children.push(new Paragraph({
  spacing: { before: 120, after: 60 },
  shading: { fill: AMBER, type: ShadingType.CLEAR },
  children: [new TextRun({ text: "  IMPORTANT: Update paths in both .reg files and extract_guideline.bat to match your actual install directory.", bold: true, color: "333333", size: 18, font: "Arial" })]
}));

children.push(new Paragraph({ children: [new PageBreak()] }));

// ══════════════════════════════════════════════════════════════════
//  SECTION 9: TESTING
// ══════════════════════════════════════════════════════════════════

children.push(sectionBanner("9. TESTING EACH COMPONENT"));
children.push(gap(1));
children.push(para("Test each layer independently before using the full pipeline.", { size: 20, color: "333333" }));

children.push(gap(1));
children.push(hdr("9.1 Test Python Extraction Only", 2));
children.push(para("From the project root directory:", { size: 20, color: DGRAY }));
children.push(...codeBlock([
  "cd guideline_extractor_v2",
  "python -c \"",
  "  import json",
  "  from core.ingestion import ingest_document",
  "  result = ingest_document(r'C:\\path\\to\\test.pdf')",
  "  print(json.dumps(result, indent=2)[:2000])",
  "  print('Type:', result['classification']['document_type'])",
  "  print('Conf:', result['classification']['confidence'])",
  "  print('Recs:', len(result['extraction']['recommendations']))",
  "\"",
]));
children.push(para("Expected: JSON output with all 5 top-level blocks. Check that document_type is correct and recommendations are populated.", { size: 18, italic: true, color: DGRAY }));

children.push(gap(1));
children.push(hdr("9.2 Test DOCX Generation Only (no API call)", 2));
children.push(para("If you already have an extraction JSON file:", { size: 20, color: DGRAY }));
children.push(...codeBlock([
  "set NODE_PATH=C:\\path\\to\\node_modules",
  "node oneclick\\build_summary.js path\\to\\extraction.json C:\\Users\\me\\Desktop\\test.docx",
]));
children.push(para("Expected: A styled DOCX appears on your Desktop. Open in Word to verify formatting.", { size: 18, italic: true, color: DGRAY }));

children.push(gap(1));
children.push(hdr("9.3 Test Synthesis Only", 2));
children.push(para("Requires ANTHROPIC_API_KEY set and an existing extraction JSON:", { size: 20, color: DGRAY }));
children.push(...codeBlock([
  "node oneclick\\synthesize.js path\\to\\extraction.json",
  "# Check: \"Synthesis OK\" message",
  "# Verify extraction.json now has extraction.synthesis{} block",
]));

children.push(gap(1));
children.push(hdr("9.4 Test Full Pipeline", 2));
children.push(...codeBlock([
  "oneclick\\extract_guideline.bat \"C:\\Users\\me\\Downloads\\some_guideline.pdf\"",
  "",
  "# Expected output:",
  "#   [1/4] Extracting clinical content...",
  "#     Extraction OK: type=chronic_guideline conf=0.92",
  "#   [2/4] Synthesizing clinical narrative...",
  "#     Synthesis OK",
  "#   [3/4] Generating summary DOCX...",
  "#     Summary DOCX written: ..._summary.docx",
  "#   [4/4] Done > Desktop\\some_guideline_summary.docx",
]));

children.push(gap(1));
children.push(hdr("9.5 Test Batch Mode", 2));
children.push(...codeBlock([
  "oneclick\\extract_guideline.bat \"C:\\Users\\me\\Downloads\\guidelines_folder\"",
  "",
  "# Expected: processes all *.pdf files in folder",
  "# Reports: \"Batch complete: X succeeded, Y failed\"",
]));

children.push(new Paragraph({ children: [new PageBreak()] }));

// ══════════════════════════════════════════════════════════════════
//  SECTION 10: QUALITY CALIBRATION & SELF-IMPROVEMENT
// ══════════════════════════════════════════════════════════════════

children.push(sectionBanner("10. QUALITY CALIBRATION & SELF-IMPROVEMENT"));
children.push(gap(1));

children.push(hdr("What Calibration Does", 2));
children.push(para("The calibration system scores extraction quality on 5 weighted dimensions, persists results across runs, detects recurring (chronic) gaps, and auto-generates targeted prompt supplements that improve future extractions. It is a self-improving feedback loop.", { size: 20, color: "333333" }));
children.push(gap(1));

children.push(para("Self-Improvement Loop:", { bold: true, size: 20 }));
children.push(...codeBlock([
  "Extract PDF \u2192 Score quality \u2192 Persist to history \u2192 Detect chronic gaps",
  "                                                           \u2193",
  "Future extractions \u2190 prompt_supplements.json \u2190 Auto-generate targeted fixes"
]));
children.push(gap(1));

children.push(hdr("Scoring Dimensions", 2));
children.push(new Table({
  width: { size: W, type: WidthType.DXA },
  columnWidths: [2000, 900, 4000, 2460],
  rows: [
    new TableRow({ tableHeader: true, children: [
      hCell("Dimension", 2000), hCell("Weight", 900), hCell("Formula", 4000), hCell("Sub-Metrics", 2460)
    ]}),
    ...[ ["Recommendations", "30%", "0.4\u00D7strength_rate + 0.4\u00D7evidence_rate + 0.2\u00D7min(avg_len/100, 1.0)", "strength_rate, evidence_rate"],
         ["Thresholds", "25%", "0.3\u00D7unit_rate + 0.4\u00D7context_rate + 0.3\u00D7specific_rate", "unit_rate, context_rate, specific_rate"],
         ["Population", "20%", "(populated_count \u2212 vague_count) / 5", "vague_fields"],
         ["Summary", "15%", "0.4\u00D7min(len/300,1) + 0.4\u00D7min(sentences/2,1) + 0.2\u00D7(!vague)", "length, sentences, vague"],
         ["Medications", "10%*", "0.5\u00D7dose_rate + 0.5\u00D7class_rate", "dose_rate, class_rate"],
    ].map(([d, w, f, s], i) => new TableRow({ children: [
      dCell(d, 2000, i % 2 === 0 ? LGRAY : WHITE, true),
      dCell(w, 900, i % 2 === 0 ? LGRAY : WHITE),
      dCell(f, 4000, i % 2 === 0 ? LGRAY : WHITE),
      dCell(s, 2460, i % 2 === 0 ? LGRAY : WHITE)
    ]}))
  ]
}));
children.push(para("* Medications weight is conditional \u2014 only applies when medications are present. All weights renormalize to sum to 1.0.", { size: 18, color: DGRAY, italic: true }));
children.push(gap(1));

children.push(hdr("Gap Detection", 2));
children.push(bullet("Field score < 0.70 \u2192 gap finding (HIGH priority if < 0.50, MEDIUM otherwise)"));
children.push(bullet("Sub-metric < 80% \u2192 sub-issue within a finding"));
children.push(bullet("Overall score \u2265 0.70 = PASS, < 0.70 = NEEDS TUNING"));
children.push(gap(1));

children.push(hdr("Vague Text Detection", 2));
children.push(para("12 vague phrases trigger scoring penalties: not specified, not stated, not provided, n/a, none mentioned, not applicable, unknown, not mentioned, not documented, not available, see document, varies", { size: 20, color: "333333" }));
children.push(gap(1));

children.push(hdr("How to Run", 2));
children.push(...codeBlock([
  "python calibrate.py <file.json>           # Score single extraction",
  "python calibrate.py <folder>              # Score all JSONs in folder",
  "python calibrate.py <file.json> --report  # Write calibration_report.txt"
]));
children.push(gap(1));

children.push(para("First-run behavior: On the very first extraction via extract_guideline.bat, calibration runs automatically. After that, it only runs when explicitly requested with the --calibrate flag. A .calibrated marker file in oneclick/ tracks this state.", { size: 20, color: "333333" }));
children.push(gap(1));

children.push(hdr("Persistence: calibration_history.json", 2));
children.push(para("Every calibration run appends an entry to oneclick/calibration_history.json. This file is the trend database \u2014 it stores per-run overall scores, dimension scores, gaps, and engine breakdowns. It grows over time and is never overwritten.", { size: 20, color: "333333" }));
children.push(gap(1));

children.push(hdr("Chronic Gap Detection", 2));
children.push(para("After each run, the system scans the last 5 runs for recurring patterns. If the same dimension + sub_metric gap appears in 3 or more of the last 5 runs, it is flagged as a chronic gap. Chronic gaps trigger automatic prompt supplement generation.", { size: 20, color: "333333" }));
children.push(gap(1));

children.push(hdr("Prompt Supplements: prompt_supplements.json", 2));
children.push(para("When chronic gaps are detected, calibrate.py writes oneclick/prompt_supplements.json with targeted extraction instructions. Each supplement includes:", { size: 20, color: "333333" }));
children.push(bullet("target_engines \u2014 which engine types to apply the instruction to"));
children.push(bullet("instruction \u2014 the actual text appended to the LLM system prompt"));
children.push(bullet("dimension + sub_metric \u2014 the gap that triggered it"));
children.push(bullet("occurrences + avg_score + trend \u2014 tracking data"));
children.push(gap(1));

children.push(para("Integration: utils/prompt_builder.py reads prompt_supplements.json at extraction time and appends matching instructions to the system prompt. This is the mechanism by which the pipeline improves itself automatically.", { size: 20, color: "333333", bold: true }));
children.push(gap(1));

children.push(hdr("Prompt Improvement Templates", 2));
children.push(new Table({
  width: { size: W, type: WidthType.DXA },
  columnWidths: [3500, 5860],
  rows: [
    new TableRow({ tableHeader: true, children: [
      hCell("Gap Key", 3500), hCell("Supplement Instruction (summary)", 5860)
    ]}),
    ...[ ["recommendations.strength_rate", "Populate strength field using guideline grading or inferred language (should \u2192 Strong, may \u2192 Conditional)"],
         ["recommendations.evidence_rate", "Populate evidence_level using guideline coding (A/B/C) or inferred from study design"],
         ["thresholds.unit_rate", "Always include measurement unit (mmHg, mg/dL, %, etc.) for every threshold value"],
         ["thresholds.context_rate", "Write a clinical sentence fragment for context, not a single word"],
         ["medications.dose_rate", "Include dose amount + unit + frequency + route; write 'dose not specified' if absent"],
         ["medications.class_rate", "Use standard pharmacological classification (ACE inhibitor, ARB, SSRI, etc.)"],
         ["population.vague_fields", "Provide specific clinical values instead of 'adults' or 'not specified'"],
         ["summary.overall", "Write 2-3 clinically specific sentences; include condition, recommendation, and thresholds"],
    ].map(([k, d], i) => new TableRow({ children: [
      dCell(k, 3500, i % 2 === 0 ? LGRAY : WHITE, true),
      dCell(d, 5860, i % 2 === 0 ? LGRAY : WHITE)
    ]}))
  ]
}));
children.push(gap(1));

children.push(hdr("Tuning Workflow", 2));
children.push(numbered("Run calibrate.py on a batch of extraction JSONs"));
children.push(numbered("Review the quality report \u2014 check overall score and dimension breakdowns"));
children.push(numbered("If score < 0.70: examine the specific gaps identified"));
children.push(numbered("Run 3+ times to allow chronic gap detection to identify persistent patterns"));
children.push(numbered("Verify prompt_supplements.json was generated with targeted instructions"));
children.push(numbered("Re-extract documents and compare quality \u2014 supplements should improve scores"));
children.push(numbered("For manual tuning: edit system prompts in utils/prompt_builder.py directly"));

children.push(gap(2));
children.push(hr());

// ══════════════════════════════════════════════════════════════════
//  SECTION 11: QUICK REFERENCE
// ══════════════════════════════════════════════════════════════════

children.push(sectionBanner("11. QUICK REFERENCE"));
children.push(gap(1));

children.push(hdr("Key File Summary", 2));
children.push(new Table({
  width: { size: W, type: WidthType.DXA },
  columnWidths: [3600, 2400, 3360],
  rows: [
    new TableRow({ tableHeader: true, children: [
      hCell("File", 3600), hCell("Language", 2400), hCell("Role", 3360)
    ]}),
    ...[ ["core/ingestion.py", "Python", "Pipeline orchestrator"],
         ["core/screening.py", "Python", "Document classifier"],
         ["core/routing.py", "Python", "Engine router"],
         ["engines/base_engine.py", "Python", "Base class + schema"],
         ["engines/chronic_engine.py", "Python", "Chronic disease engine"],
         ["engines/acute_engine.py", "Python", "Acute/emergency engine"],
         ["engines/preventive_engine.py", "Python", "Preventive/screening engine"],
         ["engines/diagnostic_engine.py", "Python", "Diagnostic workup engine"],
         ["engines/rct_engine.py", "Python", "RCT article engine"],
         ["utils/preprocess.py", "Python", "PDF text extraction"],
         ["utils/prompt_builder.py", "Python", "LLM API + prompts"],
         ["utils/validator.py", "Python", "Schema validation"],
         ["utils/logger.py", "Python", "Run logging"],
         ["oneclick/synthesize.js", "Node.js", "Clinical narrative synthesis"],
         ["oneclick/build_summary.js", "Node.js", "DOCX generator"],
         ["oneclick/extract_guideline.bat", "Batch", "Batch orchestrator"],
         ["oneclick/calibrate.py", "Python", "Quality scorer + self-improvement"],
         ["oneclick/calibration_history.json", "JSON", "Auto-created: calibration trend database"],
         ["oneclick/prompt_supplements.json", "JSON", "Auto-created: LLM prompt improvements"],
    ].map(([f, l, r], i) => new TableRow({ children: [
      dCell(f, 3600, i % 2 === 0 ? LGRAY : WHITE, true),
      dCell(l, 2400, i % 2 === 0 ? LGRAY : WHITE),
      dCell(r, 3360, i % 2 === 0 ? LGRAY : WHITE)
    ]}))
  ]
}));

children.push(gap(1));
children.push(hdr("Key Parameters", 2));
children.push(new Table({
  width: { size: W, type: WidthType.DXA },
  columnWidths: [3600, 2400, 3360],
  rows: [
    new TableRow({ tableHeader: true, children: [
      hCell("Parameter", 3600), hCell("Value", 2400), hCell("Where", 3360)
    ]}),
    ...[ ["Python model", "claude-sonnet-4-20250514", "prompt_builder.py"],
         ["Synthesis model", "claude-sonnet-4-6", "synthesize.js"],
         ["Synthesis max tokens", "4,000", "synthesize.js"],
         ["Extraction max tokens", "3,000", "prompt_builder.py"],
         ["Chunk threshold", "15,000 chars", "prompt_builder.py"],
         ["Chunk size", "25,000 chars", "prompt_builder.py"],
         ["Chunk overlap", "2,500 chars", "prompt_builder.py"],
         ["Max chunks", "12", "prompt_builder.py"],
         ["Parallel workers", "2", "prompt_builder.py"],
         ["Schema version", "unified_v1.0", "base_engine.py"],
         ["Engine version", "v2.3", "base_engine.py"],
         ["Page size", "US Letter (12240\u00D715840)", "build_summary.js"],
         ["Margins", "0.75\" all sides (1080 DXA)", "build_summary.js"],
         ["Pass threshold", "\u22650.70 overall", "calibrate.py"],
         ["Gap threshold", "<0.70 per dimension", "calibrate.py"],
         ["Chronic detection", "3+ of last 5 runs", "calibrate.py"],
    ].map(([p, v, w], i) => new TableRow({ children: [
      dCell(p, 3600, i % 2 === 0 ? LGRAY : WHITE, true),
      dCell(v, 2400, i % 2 === 0 ? LGRAY : WHITE),
      dCell(w, 3360, i % 2 === 0 ? LGRAY : WHITE)
    ]}))
  ]
}));

children.push(gap(2));
children.push(hr());
children.push(para("Guideline Extractor Cookbook Protocol  |  March 2026  |  ABFM Board Prep Project", { color: DGRAY, size: 16, center: true }));

// ══════════════════════════════════════════════════════════════════
//  BUILD DOCUMENT
// ══════════════════════════════════════════════════════════════════

const doc = new Document({
  numbering: {
    config: [
      { reference: "bullets",
        levels: [
          { level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 540, hanging: 270 } } } },
          { level: 1, format: LevelFormat.BULLET, text: "\u25E6", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 900, hanging: 270 } } } }
        ] },
      { reference: "numbers",
        levels: [
          { level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 540, hanging: 270 } } } },
          { level: 1, format: LevelFormat.DECIMAL, text: "%2.", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 900, hanging: 270 } } } }
        ] }
    ]
  },
  styles: {
    default: { document: { run: { font: "Arial", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, color: NAVY, font: "Arial" },
        paragraph: { spacing: { before: 360, after: 120 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, color: BLUE, font: "Arial" },
        paragraph: { spacing: { before: 240, after: 100 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 22, bold: true, color: DGRAY, font: "Arial" },
        paragraph: { spacing: { before: 180, after: 80 }, outlineLevel: 2 } }
    ]
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1080, right: 1080, bottom: 1080, left: 1080 }
      }
    },
    children
  }]
});

const outPath = path.join(os.homedir(), "Desktop", "Guideline_Extractor_Cookbook.docx");

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync(outPath, buf);
  console.log("Cookbook protocol written: " + outPath);
}).catch(err => {
  console.error("Error:", err.message);
  process.exit(1);
});
