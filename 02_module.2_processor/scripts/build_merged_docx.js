/**
 * build_merged_docx.js — Merged DOCX generator (Clinical Narrative + DB Intelligence)
 *
 * For articles with enriched JSONs (146 codon PDFs), merges API-synthesized
 * clinical content with DB intelligence into a single comprehensive DOCX.
 * For all other articles, falls back to DB-only output (identical to build_db_docx.js).
 *
 * Usage:
 *   node build_merged_docx.js [--limit N] [--article ART-XXXX] [--merged-only]
 *
 * Flags:
 *   --limit N        Process only N articles
 *   --article ART-X  Process a single article
 *   --merged-only    Only generate DOCXs for articles that have enriched JSONs
 *
 * Output: clinical_guidelines/02_docx_guideline_library/<canonical>_<ART-ID>_db_intel.docx
 */

const fs = require("fs");
const path = require("path");
const initSqlJs = require("sql.js");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  HeadingLevel, AlignmentType, BorderStyle, WidthType, ShadingType,
  LevelFormat
} = require("docx");

// ── Config ──────────────────────────────────────────────────
// __dirname = .../02_module.2_processor/scripts
// PROJECT_ROOT = two levels up
const PROJECT_ROOT    = path.resolve(__dirname, "../../");
const DB_PATH         = path.join(PROJECT_ROOT, "00_database/db/ite_intelligence.db");
const OUTPUT_DIR      = path.join(PROJECT_ROOT, "02_module.2_processor/outputs/docx_guideline_library");
const TREND_DIR       = path.join(PROJECT_ROOT, "03_module.3_analyst/outputs");
const JSON_DIR        = path.join(PROJECT_ROOT, "key_data_files/ingested/json");   // TODO: not yet migrated
const JSON_INDEX_PATH = path.join(__dirname, "json_artid_index.json");

// ── Colors ──────────────────────────────────────────────────
const NAVY   = "1F3864";
const BLUE   = "2E75B6";
const LBLUE  = "D6E4F7";
const WHITE  = "FFFFFF";
const LGRAY  = "F2F2F2";
const DGRAY  = "595959";
const AMBER  = "FFF2CC";
const TEAL   = "E2EFDA";
const DTEAL  = "2D572C";
const CONCEPT_BG = "1A1A2E";
const RED_BG = "FDE8E8";
const CHIP = { green: "00B050", yellow: "FFD700", red: "FF6B6B", white: "CCCCCC" };

const BORDER  = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const BORDERS = { top: BORDER, bottom: BORDER, left: BORDER, right: BORDER };

// ── Helpers ─────────────────────────────────────────────────
function hdr(text, level = 1) {
  return new Paragraph({
    heading: level === 1 ? HeadingLevel.HEADING_1 : level === 2 ? HeadingLevel.HEADING_2 : HeadingLevel.HEADING_3,
    spacing: { before: level === 1 ? 360 : 240, after: 120 },
    children: [new TextRun({ text, bold: true, color: level === 1 ? NAVY : level === 2 ? BLUE : DGRAY, size: level === 1 ? 28 : level === 2 ? 24 : 22, font: "Aptos" })]
  });
}

function para(text, opts = {}) {
  const { bold = false, italic = false, color = "000000", size = 22, indent = 0, spaceBefore = 60, spaceAfter = 60, center = false } = opts;
  return new Paragraph({
    alignment: center ? AlignmentType.CENTER : AlignmentType.LEFT,
    indent: indent ? { left: indent } : undefined,
    spacing: { before: spaceBefore, after: spaceAfter },
    children: [new TextRun({ text, bold, italic, color, size, font: "Aptos" })]
  });
}

function bullet(text, level = 0, opts = {}) {
  const { bold = false, color = "000000" } = opts;
  return new Paragraph({ numbering: { reference: "bullets", level }, spacing: { before: 40, after: 40 }, children: [new TextRun({ text, bold, color, size: 20, font: "Aptos" })] });
}

function gap(n = 1) { return new Paragraph({ spacing: { before: n * 60, after: n * 60 }, children: [] }); }
function hr() { return new Paragraph({ spacing: { before: 120, after: 120 }, border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: BLUE, space: 1 } }, children: [] }); }

function hCell(text, width, fill = NAVY, align = AlignmentType.LEFT) {
  return new TableCell({
    width: { size: width, type: WidthType.DXA }, shading: { fill, type: ShadingType.CLEAR },
    margins: { top: 80, bottom: 80, left: 120, right: 120 }, borders: BORDERS, verticalAlign: "center",
    children: [new Paragraph({ alignment: align, children: [new TextRun({ text, bold: true, color: WHITE, size: 18, font: "Aptos" })] })]
  });
}

function dCell(text, width, fill = WHITE, bold = false, color = "000000", align = AlignmentType.LEFT) {
  return new TableCell({
    width: { size: width, type: WidthType.DXA }, shading: { fill, type: ShadingType.CLEAR },
    margins: { top: 80, bottom: 80, left: 120, right: 120 }, borders: BORDERS, verticalAlign: "center",
    children: [new Paragraph({ alignment: align, children: [new TextRun({ text: String(text || ""), bold, color, size: 18, font: "Aptos" })] })]
  });
}

// Multi-paragraph cell (for clinical bottom line, etc.)
function multiParaCell(textArray, width, fill = WHITE) {
  const children = textArray.map(t =>
    new Paragraph({ spacing: { before: 60, after: 60 }, children: [new TextRun({ text: t, color: "333333", size: 20, font: "Aptos" })] })
  );
  return new TableCell({
    width: { size: width, type: WidthType.DXA }, shading: { fill, type: ShadingType.CLEAR },
    margins: { top: 100, bottom: 100, left: 160, right: 160 }, borders: BORDERS,
    children
  });
}

// ── Colorize concept text ───────────────────────────────────
function colorizeConceptText(conceptSummary, conceptTags) {
  if (!conceptSummary) return [new TextRun({ text: "\u2014", color: CHIP.white, size: 16, font: "Aptos" })];
  let drugTerms = [], diagTerms = [], threshTerms = [];
  if (conceptTags) {
    try {
      const tags = typeof conceptTags === "string" ? JSON.parse(conceptTags) : conceptTags;
      drugTerms = (tags.drugs || []).filter(d => d.length > 2);
      diagTerms = (tags.diagnoses || []).filter(d => d.length > 2);
      threshTerms = (tags.thresholds || []).filter(t => t.length > 1);
    } catch (e) {}
  }
  const text = conceptSummary;
  const allTerms = [
    ...drugTerms.map(t => ({ term: t, color: CHIP.yellow })),
    ...diagTerms.map(t => ({ term: t, color: CHIP.green })),
    ...threshTerms.map(t => ({ term: t, color: CHIP.red }))
  ].sort((a, b) => b.term.length - a.term.length);

  if (allTerms.length === 0) return [new TextRun({ text, color: CHIP.white, size: 16, font: "Aptos" })];

  const segments = [];
  let pos = 0;
  while (pos < text.length) {
    let found = null, foundAt = text.length;
    for (const { term, color } of allTerms) {
      const idx = text.toLowerCase().indexOf(term.toLowerCase(), pos);
      if (idx !== -1 && idx < foundAt) { foundAt = idx; found = { term: text.substring(idx, idx + term.length), color, idx }; }
    }
    if (found && found.idx < text.length) {
      if (found.idx > pos) segments.push({ text: text.substring(pos, found.idx), color: CHIP.white });
      segments.push({ text: found.term, color: found.color, bold: true });
      pos = found.idx + found.term.length;
    } else {
      segments.push({ text: text.substring(pos), color: CHIP.white });
      break;
    }
  }
  return segments.map(seg => new TextRun({ text: seg.text, color: seg.color, bold: seg.bold || false, size: 16, font: "Aptos" }));
}

// ── Load trend data from CSVs ───────────────────────────────
function loadTrends() {
  const trends = {};
  const trendFile = path.join(TREND_DIR, "4a_body_system_trends.csv");
  if (!fs.existsSync(trendFile)) return trends;
  const lines = fs.readFileSync(trendFile, "utf-8").replace(/^\uFEFF/, "").split("\n").filter(l => l.trim());
  const header = lines[0].split(",");
  for (let i = 1; i < lines.length; i++) {
    const cols = lines[i].split(",");
    const bs = cols[0];
    trends[bs] = {
      counts: { 2020: +cols[1], 2021: +cols[2], 2022: +cols[3], 2023: +cols[4], 2024: +cols[5], 2025: +cols[6] },
      total: +cols[7], slope: +cols[8]
    };
  }
  return trends;
}

// ── Load enriched JSON index ────────────────────────────────
function loadJsonIndex() {
  if (!fs.existsSync(JSON_INDEX_PATH)) {
    console.warn("  [WARN] json_artid_index.json not found — all DOCXs will be DB-only.");
    return {};
  }
  return JSON.parse(fs.readFileSync(JSON_INDEX_PATH, "utf-8"));
}

function loadEnrichedJson(jsonFilename) {
  const fp = path.join(JSON_DIR, jsonFilename);
  if (!fs.existsSync(fp)) return null;
  let data = JSON.parse(fs.readFileSync(fp, "utf-8"));
  if (Array.isArray(data)) data = data[0] || {};
  return data;
}

// ── Study note generator (template-driven) ──────────────────
function generateStudyNote(article, icd10Map, questions) {
  const engineLabel = (article.engine_type || "").replace(/_/g, " ");
  const primaryCodes = icd10Map.filter(c => c.relevance === "primary");
  const primaryDesc = primaryCodes.map(c => `${c.desc} (${c.code})`).join(", ") || "multiple conditions";
  const roles = [...new Set(icd10Map.map(c => c.role.replace(/_/g, " ")))];
  const rolesStr = roles.join(", ");
  const qCount = questions.length;
  const examYears = [...new Set(questions.map(q => q.exam_year))].sort();
  const subcats = [...new Set(questions.map(q => q.subcategory))];
  const subcatStr = subcats.length <= 2 ? subcats.join(" and ") : `${subcats.length} subcategories`;

  let line1 = `  This ${engineLabel} serves as a ${rolesStr} reference for ${primaryDesc}.`;
  if (qCount > 0) {
    line1 += ` It was tested ${qCount} time${qCount !== 1 ? "s" : ""} on the ITE (${examYears.join(", ")}), in ${subcatStr}.`;
  } else {
    line1 += ` It has not been directly tested on the ITE yet.`;
  }

  let line2 = "";
  if (qCount > 0) {
    const allDrugs = new Set(), allDiags = new Set(), allThresh = new Set();
    for (const q of questions) {
      if (q.concept_tags) {
        try {
          const tags = typeof q.concept_tags === "string" ? JSON.parse(q.concept_tags) : q.concept_tags;
          (tags.drugs || []).forEach(d => allDrugs.add(d));
          (tags.diagnoses || []).forEach(d => allDiags.add(d));
          (tags.thresholds || []).forEach(t => allThresh.add(t));
        } catch (e) {}
      }
    }
    const topDrugs = [...allDrugs].slice(0, 3);
    const topThresh = [...allThresh].slice(0, 2);
    if (topDrugs.length > 0 || topThresh.length > 0) {
      const parts = [];
      if (topDrugs.length > 0) parts.push(`Know your ${topDrugs.join(", ")}`);
      if (topThresh.length > 0) parts.push(`key thresholds: ${topThresh.join(", ")}`);
      line2 = `  ${parts.join(". ")}. The board has tested these concepts across ${examYears.length} exam year${examYears.length !== 1 ? "s" : ""}.`;
    }
  }
  return { line1, line2 };
}

// ══════════════════════════════════════════════════════════════
//  CLINICAL NARRATIVE SECTIONS (from enriched JSON)
// ══════════════════════════════════════════════════════════════

function buildClinicalSections(jsonData) {
  const children = [];
  const ext = jsonData.extraction || {};
  const synth = ext.synthesis || {};

  // ── CLINICAL BOTTOM LINE ──────────────────────────────────
  if (synth.clinical_bottom_line) {
    children.push(new Paragraph({
      spacing: { before: 0, after: 0 }, shading: { fill: NAVY, type: ShadingType.CLEAR },
      children: [new TextRun({ text: "  \u2302 CLINICAL BOTTOM LINE", bold: true, color: WHITE, size: 24, font: "Aptos" })]
    }));

    const paragraphs = synth.clinical_bottom_line.split(/\n\n+/).filter(p => p.trim());
    paragraphs.forEach(p => {
      children.push(new Paragraph({
        spacing: { before: 80, after: 80 }, indent: { left: 180 },
        children: [new TextRun({ text: p.trim(), color: "333333", size: 20, font: "Aptos" })]
      }));
    });
    children.push(gap(1));
  }

  // ── PRACTICE PEARLS ───────────────────────────────────────
  if (synth.practice_pearls && synth.practice_pearls.length > 0) {
    children.push(new Paragraph({
      spacing: { before: 120, after: 60 }, shading: { fill: TEAL, type: ShadingType.CLEAR },
      children: [new TextRun({ text: "  \u2736 PRACTICE PEARLS", bold: true, color: DTEAL, size: 22, font: "Aptos" })]
    }));
    synth.practice_pearls.forEach(pearl => {
      children.push(bullet(pearl, 0, { color: "333333" }));
    });
    children.push(gap(1));
  }

  // ── DEFINITIONS & THRESHOLDS ──────────────────────────────
  if (synth.definitions_and_thresholds && synth.definitions_and_thresholds.length > 0) {
    children.push(hdr("Definitions & Thresholds", 2));
    const dtRows = [
      new TableRow({ cantSplit: true, tableHeader: true, children: [
        hCell("Term", 3120, NAVY), hCell("Definition / Threshold", 6240, NAVY)
      ] })
    ];
    synth.definitions_and_thresholds.forEach((item, i) => {
      const fill = i % 2 === 0 ? LGRAY : WHITE;
      dtRows.push(new TableRow({ cantSplit: true, children: [
        dCell(item.term || "", 3120, fill, true, NAVY),
        dCell(item.definition || "", 6240, fill)
      ] }));
    });
    children.push(new Table({ width: { size: 9360, type: WidthType.DXA }, columnWidths: [3120, 6240], rows: dtRows }));
    children.push(gap(2));
  }

  // ── RECOMMENDATIONS ───────────────────────────────────────
  const recs = ext.recommendations || [];
  if (recs.length > 0) {
    children.push(hdr("Recommendations", 2));
    recs.forEach((rec, i) => {
      const text = typeof rec === "string" ? rec : (rec.text || rec.recommendation || JSON.stringify(rec));
      const grade = typeof rec === "object" ? (rec.grade || rec.strength || "") : "";
      const gradeTag = grade ? `[${grade}] ` : "";

      children.push(new Paragraph({
        numbering: { reference: "bullets", level: 0 },
        spacing: { before: 40, after: 40 },
        children: [
          ...(gradeTag ? [new TextRun({ text: gradeTag, bold: true, color: BLUE, size: 20, font: "Aptos" })] : []),
          new TextRun({ text, color: "333333", size: 20, font: "Aptos" })
        ]
      }));
    });
    children.push(gap(1));
  }

  // ── MEDICATION GROUPS ─────────────────────────────────────
  if (synth.medication_groups && synth.medication_groups.length > 0) {
    children.push(hdr("Medications", 2));
    synth.medication_groups.forEach(group => {
      children.push(new Paragraph({
        spacing: { before: 120, after: 40 },
        children: [new TextRun({ text: group.group_name || "Medications", bold: true, color: BLUE, size: 22, font: "Aptos" })]
      }));
      if (group.narrative) {
        children.push(para(group.narrative, { italic: true, color: DGRAY, size: 20, spaceBefore: 20, spaceAfter: 40 }));
      }
      (group.drugs || []).forEach(drug => {
        children.push(bullet(drug, 1, { color: "333333" }));
      });
    });
    children.push(gap(1));
  }

  // ── CRITICAL ALERTS ───────────────────────────────────────
  if (synth.critical_alerts && synth.critical_alerts.length > 0) {
    children.push(new Paragraph({
      spacing: { before: 120, after: 60 }, shading: { fill: RED_BG, type: ShadingType.CLEAR },
      children: [new TextRun({ text: "  \u26A0 CRITICAL ALERTS", bold: true, color: "C00000", size: 22, font: "Aptos" })]
    }));
    const alertRows = [
      new TableRow({ cantSplit: true, tableHeader: true, children: [
        hCell("Alert", 3600, "C00000"), hCell("Why It Matters", 5760, "C00000")
      ] })
    ];
    synth.critical_alerts.forEach((alert, i) => {
      const fill = i % 2 === 0 ? RED_BG : WHITE;
      alertRows.push(new TableRow({ cantSplit: true, children: [
        dCell(alert.alert || "", 3600, fill, true, "C00000"),
        dCell(alert.why_it_matters || "", 5760, fill)
      ] }));
    });
    children.push(new Table({ width: { size: 9360, type: WidthType.DXA }, columnWidths: [3600, 5760], rows: alertRows }));
    children.push(gap(2));
  }

  // ── RED FLAGS (from extraction, if not covered by critical_alerts) ──
  const redFlags = ext.red_flags || [];
  if (redFlags.length > 0 && (!synth.critical_alerts || synth.critical_alerts.length === 0)) {
    children.push(hdr("Red Flags", 2));
    redFlags.forEach(flag => {
      const text = typeof flag === "string" ? flag : (flag.text || flag.finding || JSON.stringify(flag));
      children.push(bullet(text, 0, { color: "C00000" }));
    });
    children.push(gap(1));
  }

  return children;
}

// ══════════════════════════════════════════════════════════════
//  BUILD DOCX (merged: clinical narrative + DB intelligence)
// ══════════════════════════════════════════════════════════════

function buildDocx(article, icd10Map, questions, trendData, jsonData) {
  const children = [];
  const hasClinical = !!jsonData;

  // ═══════════════════════════════════════════════════════════
  //  SECTION 1: TITLE BANNER
  // ═══════════════════════════════════════════════════════════
  const titleText = article.title ? article.title.charAt(0).toUpperCase() + article.title.slice(1) : "Untitled";
  const authorLine = [article.author1, article.author2].filter(Boolean).join(" & ");
  const metaLine = [authorLine, article.year, article.source_type].filter(Boolean).join("  |  ");

  children.push(new Paragraph({
    alignment: AlignmentType.CENTER, spacing: { before: 240, after: 60 },
    shading: { fill: NAVY, type: ShadingType.CLEAR },
    children: [new TextRun({ text: titleText, bold: true, color: WHITE, size: 32, font: "Aptos" })]
  }));
  children.push(new Paragraph({
    alignment: AlignmentType.CENTER, spacing: { before: 0, after: 240 },
    shading: { fill: NAVY, type: ShadingType.CLEAR },
    children: [new TextRun({ text: metaLine, italic: true, color: LBLUE, size: 20, font: "Aptos" })]
  }));
  if (article.citation_display) {
    children.push(new Paragraph({
      alignment: AlignmentType.CENTER, spacing: { before: 80, after: 120 },
      children: [new TextRun({ text: article.citation_display, italic: true, color: DGRAY, size: 18, font: "Aptos" })]
    }));
  }

  // ═══════════════════════════════════════════════════════════
  //  SECTION 2: CLASSIFICATION BADGE
  // ═══════════════════════════════════════════════════════════
  children.push(gap(1));
  const badgeLabel = hasClinical ? "Full Extraction + DB Intelligence" : "DB Intelligence Only";
  children.push(new Table({
    width: { size: 9360, type: WidthType.DXA }, columnWidths: [2340, 2340, 4680],
    rows: [
      new TableRow({ cantSplit: true, children: [hCell("ITE Citations", 2340, BLUE), hCell("Body Systems", 4680, BLUE), hCell("Source", 2340, BLUE)] }),
      new TableRow({ cantSplit: true, children: [
        dCell(String(article.citation_count || 0), 2340, WHITE, true, "000000", AlignmentType.CENTER),
        dCell(article.categories || "\u2014", 4680),
        dCell(badgeLabel, 2340, hasClinical ? TEAL : AMBER, true, hasClinical ? DTEAL : DGRAY, AlignmentType.CENTER)
      ] })
    ]
  }));
  children.push(gap(1));

  // ═══════════════════════════════════════════════════════════
  //  SECTIONS 3-8: CLINICAL NARRATIVE (only if JSON exists)
  // ═══════════════════════════════════════════════════════════
  if (hasClinical) {
    const clinicalChildren = buildClinicalSections(jsonData);
    children.push(...clinicalChildren);

    // Divider between clinical and intelligence sections
    children.push(hr());
  }

  // ═══════════════════════════════════════════════════════════
  //  SECTION 9: CLINICAL PATHWAY MAP
  // ═══════════════════════════════════════════════════════════
  if (icd10Map.length > 0) {
    children.push(hdr("Clinical Pathway Map", 1));
    children.push(para("ICD-10 assignments and clinical pathway roles \u2014 where this article fits in clinical practice.", { color: DGRAY, size: 18, italic: true }));

    const pathRows = [
      new TableRow({ cantSplit: true, tableHeader: true, children: [
        hCell("ICD-10", 1200, NAVY), hCell("Description", 3600, NAVY),
        hCell("Relevance", 1380, NAVY), hCell("Pathway Role", 3180, NAVY)
      ] })
    ];
    icd10Map.forEach((item, i) => {
      const fill = i % 2 === 0 ? LGRAY : WHITE;
      const relFill = item.relevance === "primary" ? TEAL : item.relevance === "secondary" ? AMBER : LGRAY;
      pathRows.push(new TableRow({ cantSplit: true, children: [
        dCell(item.code, 1200, fill, true, NAVY),
        dCell(item.desc || "", 3600, fill),
        dCell(item.relevance, 1380, relFill, true, item.relevance === "primary" ? DTEAL : DGRAY),
        dCell((item.role || "").replace(/_/g, " "), 3180, fill)
      ] }));
    });
    children.push(new Table({ width: { size: 9360, type: WidthType.DXA }, columnWidths: [1200, 3600, 1380, 3180], rows: pathRows }));
    children.push(gap(2));
  }

  // ═══════════════════════════════════════════════════════════
  //  SECTION 10: ITE EXAM INTELLIGENCE
  // ═══════════════════════════════════════════════════════════
  if (questions.length > 0) {
    const examYears = [...new Set(questions.map(q => q.exam_year))].sort();
    const examYrs = examYears.join(", ");

    children.push(new Paragraph({
      spacing: { before: 0, after: 0 }, shading: { fill: NAVY, type: ShadingType.CLEAR },
      children: [new TextRun({ text: "  \u2605 ITE EXAM INTELLIGENCE", bold: true, color: WHITE, size: 24, font: "Aptos" })]
    }));
    children.push(new Paragraph({
      spacing: { before: 0, after: 120 }, shading: { fill: BLUE, type: ShadingType.CLEAR },
      children: [new TextRun({ text: `  ${questions.length} question${questions.length !== 1 ? "s" : ""} across ${examYears.length} exam year${examYears.length !== 1 ? "s" : ""}  |  Years tested: ${examYrs}`, italic: true, color: LBLUE, size: 18, font: "Aptos" })]
    }));

    // Color key
    children.push(new Paragraph({
      spacing: { before: 0, after: 0 }, shading: { fill: CONCEPT_BG, type: ShadingType.CLEAR },
      children: [
        new TextRun({ text: "  Concept colors: ", color: "999999", size: 16, font: "Aptos", italic: true }),
        new TextRun({ text: "\u25A0 Diagnoses", color: CHIP.green, bold: true, size: 16, font: "Aptos" }),
        new TextRun({ text: "   \u25A0 Drugs/Treatments", color: CHIP.yellow, bold: true, size: 16, font: "Aptos" }),
        new TextRun({ text: "   \u25A0 Thresholds", color: CHIP.red, bold: true, size: 16, font: "Aptos" }),
      ]
    }));

    // Question table
    const qRows = [
      new TableRow({ cantSplit: true, tableHeader: true, children: [
        hCell("Year", 900, NAVY, AlignmentType.CENTER), hCell("QID", 1440, NAVY, AlignmentType.CENTER),
        hCell("Question Stem", 3960, NAVY), hCell("Concept Tested", 3060, NAVY)
      ] })
    ];
    questions.forEach((q, i) => {
      const fill = i % 2 === 0 ? LGRAY : WHITE;
      const stem = q.question_text || "";
      const stemShort = stem.length > 160 ? stem.substring(0, 157) + "\u2026" : stem;
      const conceptSummary = q.concept_tags ? (() => {
        try { const t = JSON.parse(q.concept_tags); return t.concept_summary || ""; } catch(e) { return ""; }
      })() : "";

      qRows.push(new TableRow({ cantSplit: true, children: [
        dCell(String(q.exam_year || ""), 900, fill, true, NAVY, AlignmentType.CENTER),
        dCell(q.qid || "", 1440, fill, false, BLUE, AlignmentType.CENTER),
        dCell(stemShort, 3960, fill),
        new TableCell({
          width: { size: 3060, type: WidthType.DXA }, shading: { fill: CONCEPT_BG, type: ShadingType.CLEAR },
          margins: { top: 80, bottom: 80, left: 120, right: 120 }, borders: BORDERS, verticalAlign: "center",
          children: [new Paragraph({ spacing: { before: 40, after: 40 }, children: colorizeConceptText(conceptSummary, q.concept_tags) })]
        })
      ] }));
    });
    children.push(new Table({ width: { size: 9360, type: WidthType.DXA }, columnWidths: [900, 1440, 3960, 3060], rows: qRows }));
    children.push(gap(1));

    // Correct answers
    children.push(new Paragraph({
      spacing: { before: 80, after: 60 }, shading: { fill: BLUE, type: ShadingType.CLEAR },
      children: [new TextRun({ text: "  CORRECT ANSWERS", bold: true, color: WHITE, size: 18, font: "Aptos" })]
    }));
    questions.forEach(q => {
      const correctStr = q.correct_letter && q.correct_text ? `${q.correct_letter}) ${q.correct_text}` : q.correct_letter || "\u2014";
      children.push(new Paragraph({
        spacing: { before: 40, after: 40 }, indent: { left: 360 },
        children: [
          new TextRun({ text: `${q.qid}: `, bold: true, color: BLUE, size: 18, font: "Aptos" }),
          new TextRun({ text: correctStr, color: "333333", size: 18, font: "Aptos" }),
          new TextRun({ text: `  (${q.body_system_merged || q.body_system || ""} / ${q.subcategory || ""})`, color: DGRAY, size: 16, font: "Aptos", italic: true })
        ]
      }));
    });
    children.push(gap(1));

    // KEY TESTABLE CONCEPTS
    const ktcData = [];
    questions.forEach(q => {
      if (q.concept_tags) {
        try {
          const tags = JSON.parse(q.concept_tags);
          if (tags.concept_summary) {
            const summary = tags.concept_summary;
            const shortConcept = summary.length > 60 ? summary.substring(0, 57) + "..." : summary;
            const testedAs = q.subcategory || "General";
            ktcData.push({ concept: shortConcept, tested: testedAs, qid: q.qid });
          }
        } catch (e) {}
      }
    });

    if (ktcData.length > 0) {
      children.push(hdr("Key Testable Concepts", 2));
      const ktcRows = [
        new TableRow({ cantSplit: true, tableHeader: true, children: [
          hCell("Concept", 3600, NAVY), hCell("Subcategory", 3060, NAVY), hCell("Question", 2700, NAVY)
        ] })
      ];
      ktcData.forEach((item, i) => {
        const fill = i % 2 === 0 ? LGRAY : WHITE;
        ktcRows.push(new TableRow({ cantSplit: true, children: [
          dCell(item.concept, 3600, fill, true, NAVY),
          dCell(item.tested, 3060, fill),
          dCell(item.qid, 2700, fill, false, BLUE)
        ] }));
      });
      children.push(new Table({ width: { size: 9360, type: WidthType.DXA }, columnWidths: [3600, 3060, 2700], rows: ktcRows }));
      children.push(gap(1));
    }

    // EXAM TREND CONTEXT
    const bodySystems = [...new Set(questions.map(q => q.body_system_merged || q.body_system).filter(Boolean))];
    if (bodySystems.length > 0 && trendData) {
      const primaryBS = bodySystems[0];
      const trend = trendData[primaryBS];
      if (trend) {
        children.push(hdr("Exam Trend Context", 2));
        const trendLine = Object.entries(trend.counts).map(([yr, ct]) => `${yr}: ${ct}`).join("  \u2192  ");
        const trendIcon = trend.slope > 0 ? "\u2191" : trend.slope < 0 ? "\u2193" : "\u2192";
        const direction = trend.slope > 0.5 ? "rising" : trend.slope < -0.5 ? "declining" : "stable";

        children.push(new Table({
          width: { size: 9360, type: WidthType.DXA }, columnWidths: [2340, 2340, 4680],
          rows: [
            new TableRow({ cantSplit: true, children: [
              hCell("Body System", 2340, BLUE), hCell("Trend", 2340, BLUE), hCell("Question Count by Year", 4680, BLUE)
            ] }),
            new TableRow({ cantSplit: true, children: [
              dCell(primaryBS, 2340, LBLUE, true, NAVY),
              dCell(`${trendIcon} ${trend.slope}/yr (${direction})`, 2340, trend.slope < -0.5 ? AMBER : trend.slope > 0.5 ? TEAL : WHITE, true),
              dCell(trendLine, 4680)
            ] })
          ]
        }));

        const subcats = questions.map(q => q.subcategory).filter(Boolean);
        const subcatCounts = {};
        subcats.forEach(s => { subcatCounts[s] = (subcatCounts[s] || 0) + 1; });
        const topSubcat = Object.entries(subcatCounts).sort((a, b) => b[1] - a[1])[0];
        if (topSubcat) {
          children.push(gap(1));
          children.push(para(`${topSubcat[0]} is the dominant subcategory for this article's linked questions (${topSubcat[1]}/${questions.length}).`, { size: 20, color: "333333" }));
        }
        children.push(gap(1));
      }
    }

    // STUDY NOTE
    const studyNote = generateStudyNote(article, icd10Map, questions);
    children.push(new Paragraph({
      spacing: { before: 0, after: 0 }, shading: { fill: NAVY, type: ShadingType.CLEAR },
      children: [new TextRun({ text: "  \u270E STUDY NOTE", bold: true, color: WHITE, size: 22, font: "Aptos" })]
    }));
    children.push(new Paragraph({
      spacing: { before: 0, after: 60 }, shading: { fill: LBLUE, type: ShadingType.CLEAR },
      children: [new TextRun({ text: studyNote.line1, color: NAVY, size: 20, font: "Aptos" })]
    }));
    if (studyNote.line2) {
      children.push(new Paragraph({
        spacing: { before: 0, after: 120 }, shading: { fill: LBLUE, type: ShadingType.CLEAR },
        children: [new TextRun({ text: studyNote.line2, bold: true, color: NAVY, size: 20, font: "Aptos" })]
      }));
    }
    children.push(gap(2));
  }

  // HIGH-YIELD CONCEPTS
  if (questions.length > 0) {
    const allDrugs = new Set(), allDiags = new Set(), allThresh = new Set(), allGuidelines = new Set();
    for (const q of questions) {
      if (q.concept_tags) {
        try {
          const tags = JSON.parse(q.concept_tags);
          (tags.drugs || []).forEach(d => allDrugs.add(d));
          (tags.diagnoses || []).forEach(d => allDiags.add(d));
          (tags.thresholds || []).forEach(t => allThresh.add(t));
          (tags.guidelines || []).forEach(g => allGuidelines.add(g));
        } catch (e) {}
      }
    }
    const hasContent = allDrugs.size + allDiags.size + allThresh.size + allGuidelines.size > 0;
    if (hasContent) {
      children.push(new Paragraph({
        spacing: { before: 80, after: 60 }, shading: { fill: TEAL, type: ShadingType.CLEAR },
        children: [new TextRun({ text: "  HIGH-YIELD CONCEPTS FROM THIS ARTICLE", bold: true, color: DTEAL, size: 18, font: "Aptos" })]
      }));
      const conceptTypes = [
        { label: "Drugs", items: [...allDrugs] },
        { label: "Diagnoses", items: [...allDiags] },
        { label: "Thresholds", items: [...allThresh] },
        { label: "Guidelines", items: [...allGuidelines] }
      ];
      conceptTypes.forEach(ct => {
        if (ct.items.length === 0) return;
        children.push(new Paragraph({ spacing: { before: 100, after: 20 }, children: [new TextRun({ text: ct.label, bold: true, color: BLUE, size: 20, font: "Aptos" })] }));
        ct.items.forEach(item => children.push(bullet(item, 0, { color: "333333" })));
      });
      children.push(gap(2));
    }
  }

  // ═══════════════════════════════════════════════════════════
  //  FOOTER
  // ═══════════════════════════════════════════════════════════
  children.push(hr());
  const sourceTag = hasClinical ? "Full Extraction + DB Intelligence v1.0" : "DB Intelligence v1.0";
  children.push(para(`${article.article_id}  |  ${article.codon_filename || article.canonical_filename || ""}`, { color: DGRAY, size: 16, center: true }));
  children.push(para(`Generated from ite_intelligence.db \u2014 ABFM Board Prep Project \u2014 ${sourceTag}`, { color: DGRAY, size: 16, center: true }));

  return new Document({
    numbering: { config: [{ reference: "bullets", levels: [
      { level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } },
      { level: 1, format: LevelFormat.BULLET, text: "\u25E6", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 900, hanging: 270 } } } }
    ] }] },
    styles: {
      default: { document: { run: { font: "Aptos", size: 22 } } },
      paragraphStyles: [
        { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 28, bold: true, color: NAVY, font: "Aptos" }, paragraph: { spacing: { before: 360, after: 120 }, outlineLevel: 0 } },
        { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 24, bold: true, color: BLUE, font: "Aptos" }, paragraph: { spacing: { before: 240, after: 100 }, outlineLevel: 1 } },
        { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 22, bold: true, color: DGRAY, font: "Aptos" }, paragraph: { spacing: { before: 180, after: 80 }, outlineLevel: 2 } }
      ]
    },
    sections: [{ properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1080, right: 1080, bottom: 1080, left: 1080 } } }, children }]
  });
}

// ══════════════════════════════════════════════════════════════
//  MAIN
// ══════════════════════════════════════════════════════════════
async function main() {
  const args = process.argv.slice(2);
  let limit = 0, singleArticle = null, mergedOnly = false;
  for (let i = 0; i < args.length; i++) {
    if (args[i] === "--limit" && args[i + 1]) limit = parseInt(args[i + 1]);
    if (args[i] === "--article" && args[i + 1]) singleArticle = args[i + 1];
    if (args[i] === "--merged-only") mergedOnly = true;
  }

  // Load DB
  const SQL = await initSqlJs();
  const dbBuffer = fs.readFileSync(DB_PATH);
  const db = new SQL.Database(dbBuffer);

  // Load trends + JSON index
  const trendData = loadTrends();
  const jsonIndex = loadJsonIndex();
  console.log(`JSON index: ${Object.keys(jsonIndex).length} enriched articles available`);

  // Get articles
  let articleQuery = "SELECT * FROM articles WHERE engine_type IS NOT NULL";
  if (singleArticle) articleQuery += ` AND article_id = '${singleArticle}'`;
  if (mergedOnly) {
    const artIds = Object.keys(jsonIndex).map(id => `'${id}'`).join(",");
    articleQuery += ` AND article_id IN (${artIds})`;
  }
  articleQuery += " ORDER BY citation_count DESC";
  if (limit > 0) articleQuery += ` LIMIT ${limit}`;

  const articleStmt = db.prepare(articleQuery);
  const articles = [];
  while (articleStmt.step()) articles.push(articleStmt.getAsObject());
  articleStmt.free();

  console.log(`Processing ${articles.length} articles${mergedOnly ? " (merged-only mode)" : ""}...`);

  if (!fs.existsSync(OUTPUT_DIR)) fs.mkdirSync(OUTPUT_DIR, { recursive: true });

  let generated = 0, merged = 0, dbOnly = 0, errors = 0;

  for (const article of articles) {
    try {
      // Get ICD-10 map + pathway roles
      const icdStmt = db.prepare(`
        SELECT ai.icd10_code AS code, ai.relevance, cp.pathway_role AS role,
               COALESCE(ai.icd10_desc, '') AS desc
        FROM article_icd10 ai
        LEFT JOIN clinical_pathways cp ON cp.article_id = ai.article_id AND cp.icd10_code = ai.icd10_code
        LEFT JOIN icd10_code_xref xr ON xr.icd10_code = ai.icd10_code
        WHERE ai.article_id = ?
        ORDER BY CASE ai.relevance WHEN 'primary' THEN 1 WHEN 'secondary' THEN 2 ELSE 3 END
      `);
      icdStmt.bind([article.article_id]);
      const icd10Map = [];
      while (icdStmt.step()) icd10Map.push(icdStmt.getAsObject());
      icdStmt.free();

      // Get linked questions
      const qStmt = db.prepare(`
        SELECT q.qid, q.exam_year, q.body_system, q.body_system_merged, q.subcategory,
               q.question_text, q.correct_letter, q.correct_text, q.concept_tags
        FROM qid_art_xref x
        JOIN questions q ON q.qid = x.qid
        WHERE x.article_id = ?
        ORDER BY q.exam_year, q.qid
      `);
      qStmt.bind([article.article_id]);
      const questions = [];
      while (qStmt.step()) questions.push(qStmt.getAsObject());
      qStmt.free();

      // Load enriched JSON if available
      let jsonData = null;
      const jsonFile = jsonIndex[article.article_id];
      if (jsonFile) {
        jsonData = loadEnrichedJson(jsonFile);
        if (jsonData) merged++;
        else dbOnly++;
      } else {
        dbOnly++;
      }

      // Build DOCX
      const doc = buildDocx(article, icd10Map, questions, trendData, jsonData);
      const buffer = await Packer.toBuffer(doc);

      // Write
      const baseName = article.canonical_filename || article.article_id;
      const filename = baseName + "_" + article.article_id + "_db_intel.docx";
      const outPath = path.join(OUTPUT_DIR, filename);
      fs.writeFileSync(outPath, buffer);
      generated++;

      if (generated % 50 === 0 || generated === articles.length) {
        console.log(`  ${generated}/${articles.length} generated (${merged} merged, ${dbOnly} DB-only)...`);
      }
    } catch (err) {
      errors++;
      console.error(`  ERROR on ${article.article_id}: ${err.message}`);
    }
  }

  db.close();
  console.log(`\nDone! Generated: ${generated} | Merged: ${merged} | DB-only: ${dbOnly} | Errors: ${errors}`);
}

main().catch(err => { console.error("Fatal:", err); process.exit(1); });
