/**
 * build_summary.js — Generates a standalone clinical guideline summary DOCX
 * from a unified_v1.0 extraction JSON (optionally augmented by synthesize.js).
 *
 * Usage:  node build_summary.js <input.json> <output.docx>
 *
 * Requires NODE_PATH set to the node_modules directory containing 'docx'.
 *
 * Sections:
 *   1  Title Banner
 *   2  Classification Badge
 *   3  Clinical Summary
 *   4  Practice Pearls
 *   5  Target Population
 *   6  Definitions & Thresholds
 *   7  Recommendations
 *   8  Medications
 *   9  Red Flags
 *   10 Follow-Up
 *   11 Escalation Path
 *   12 ITE Exam Intelligence  ← NEW (renders ite_intelligence{} block)
 */

// Suppress Node.js experimental localStorage warning (v25+)
process.removeAllListeners('warning');

const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
        HeadingLevel, AlignmentType, BorderStyle, WidthType, ShadingType,
        LevelFormat, PageBreak } = require('docx');
const fs   = require('fs');
const path = require('path');

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
const NO_BORDER = { style: BorderStyle.NONE, size: 0, color: WHITE };
const NO_BORDERS = { top: NO_BORDER, bottom: NO_BORDER, left: NO_BORDER, right: NO_BORDER };

// ── Safety: coerce any value to a display string ────────────────
function toStr(v) {
  if (v == null) return "";
  if (typeof v === "string") return v;
  if (typeof v === "number" || typeof v === "boolean") return String(v);
  if (Array.isArray(v)) return v.map(toStr).join(", ");
  if (typeof v === "object") return Object.entries(v).map(([k, val]) => `${k}: ${toStr(val)}`).join("; ");
  return String(v);
}

// ── Helpers ─────────────────────────────────────────────────────
function hdr(text, level = 1) {
  return new Paragraph({
    heading: level === 1 ? HeadingLevel.HEADING_1
           : level === 2 ? HeadingLevel.HEADING_2
           : HeadingLevel.HEADING_3,
    spacing: { before: level === 1 ? 360 : 240, after: 120 },
    children: [new TextRun({ text, bold: true,
      color: level === 1 ? NAVY : level === 2 ? BLUE : DGRAY,
      size:  level === 1 ? 28  : level === 2 ? 24  : 22 })]
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

function recFill(strength, evidence) {
  const s = (strength || "").toLowerCase();
  const e = (evidence || "").toLowerCase();
  if (s.includes("strong") || s.includes("class i") || e === "a"
      || e.includes("high-quality")) return TEAL;
  if (s.includes("conditional") || s.includes("moderate") || s.includes("iia")
      || e === "b" || e.includes("limited-quality")) return AMBER;
  return WHITE;
}

// ══════════════════════════════════════════════════════════════════
//  SECTION BUILDERS (1–11 unchanged)
// ══════════════════════════════════════════════════════════════════

function buildTitleBlock(source) {
  const parts = [];

  // ── Navy banner ──
  parts.push(new Paragraph({
    alignment: AlignmentType.CENTER, spacing: { before: 240, after: 60 },
    shading: { fill: NAVY, type: ShadingType.CLEAR },
    children: [new TextRun({ text: "GUIDELINE SUMMARY", bold: true, color: LBLUE, size: 20, font: "Arial" })]
  }));
  parts.push(new Paragraph({
    alignment: AlignmentType.CENTER, spacing: { before: 0, after: 60 },
    shading: { fill: NAVY, type: ShadingType.CLEAR },
    children: [new TextRun({ text: source.title || "Untitled Guideline", bold: true, color: WHITE, size: 32, font: "Arial" })]
  }));

  // ── Meta line: org | year | doi (inside banner) ──
  const metaParts = [];
  if (source.organization) metaParts.push(source.organization);
  if (source.publication_year) metaParts.push(String(source.publication_year));
  if (source.doi) metaParts.push(source.doi);
  const metaLine = metaParts.length > 0 ? metaParts.join("  |  ") : source.file_name || "";
  parts.push(new Paragraph({
    alignment: AlignmentType.CENTER, spacing: { before: 0, after: 240 },
    shading: { fill: NAVY, type: ShadingType.CLEAR },
    children: [new TextRun({ text: metaLine, italic: true, color: LBLUE, size: 20, font: "Arial" })]
  }));

  // ── Citation line (below banner, outside navy fill) ──
  // Prefer source.citation_display (set by enricher from DB).
  // Fallback: build best-effort citation from available source fields.
  const citation = source.citation_display || (() => {
    const parts = [];
    if (source.organization) parts.push(source.organization);
    if (source.title) parts.push(source.title);
    if (source.publication_year) parts.push(String(source.publication_year));
    if (source.doi) parts.push(`DOI: ${source.doi}`);
    return parts.join(". ");
  })();

  if (citation) {
    parts.push(new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 80, after: 120 },
      children: [new TextRun({ text: citation, italic: true, color: DGRAY, size: 18, font: "Arial" })]
    }));
  }

  return parts;
}

function buildClassificationBadge(classification) {
  if (!classification) return [];
  const docType = (classification.document_type || "").replace(/_/g, " ").toUpperCase();
  const engine  = classification.engine_used || "";
  const conf    = classification.confidence != null ? Math.round(classification.confidence * 100) + "%" : "\u2014";
  const systems = (classification.body_systems || []).join(", ");
  return [
    gap(1),
    new Table({
      width: { size: 9360, type: WidthType.DXA },
      columnWidths: [2340, 2340, 1560, 3120],
      rows: [
        new TableRow({ children: [
          hCell("Document Type", 2340, BLUE), hCell("Engine", 2340, BLUE),
          hCell("Confidence", 1560, BLUE),    hCell("Body Systems", 3120, BLUE)
        ]}),
        new TableRow({ children: [
          dCell(docType, 2340, LBLUE, true, NAVY), dCell(engine, 2340),
          dCell(conf, 1560, WHITE, true),           dCell(systems, 3120)
        ]})
      ]
    }),
    gap(1)
  ];
}

function buildClinicalSummary(extraction, synthesis) {
  const parts = [];
  const hasSummary = !!extraction.summary;
  const hasBottomLine = synthesis && synthesis.clinical_bottom_line;
  if (!hasSummary && !hasBottomLine) return [];
  parts.push(hdr("Clinical Summary", 1));
  if (hasSummary) parts.push(para(extraction.summary, { size: 22, color: "333333" }));
  if (hasBottomLine) {
    if (hasSummary) parts.push(gap(1));
    synthesis.clinical_bottom_line.split(/\n\n+/).map(p => p.trim()).filter(p => p.length > 0)
      .forEach(p => parts.push(para(p, { size: 21, color: "333333", spaceBefore: 80, spaceAfter: 80 })));
  }
  parts.push(gap(1));
  return parts;
}

function buildPracticePearls(synthesis) {
  if (!synthesis || !synthesis.practice_pearls || synthesis.practice_pearls.length === 0) return [];
  return [
    new Paragraph({
      spacing: { before: 120, after: 80 }, shading: { fill: TEAL, type: ShadingType.CLEAR },
      children: [new TextRun({ text: "  KEY PRACTICE CHANGES", bold: true, color: DTEAL, size: 20, font: "Arial" })]
    }),
    ...synthesis.practice_pearls.map(p => bullet(p, 0, { color: "333333" })),
    gap(2)
  ];
}

function buildPopulationTable(population) {
  if (!population) return [];
  const fields = [
    ["Age Criteria",       population.age_criteria],
    ["Risk Criteria",      population.risk_criteria],
    ["Disease Definition", population.disease_definition],
    ["Exclusions",         population.exclusions],
    ["Severity Staging",   population.severity_staging]
  ];
  const hasData = fields.some(([, v]) => { const s = toStr(v); return s && !s.match(/^(not specified|none specified|n\/a)$/i); });
  if (!hasData) return [];
  const rows = [new TableRow({ children: [hCell("Field", 2400), hCell("Details", 6960)] })];
  fields.forEach(([label, value], i) => {
    const sv = toStr(value);
    if (sv && !sv.match(/^(not specified|none specified|n\/a)$/i)) {
      rows.push(new TableRow({ children: [
        dCell(label, 2400, i % 2 === 0 ? LGRAY : WHITE, true),
        dCell(sv, 6960, i % 2 === 0 ? LGRAY : WHITE)
      ]}));
    }
  });
  return [
    hdr("Target Population", 2),
    new Table({ width: { size: 9360, type: WidthType.DXA }, columnWidths: [2400, 6960], rows }),
    gap(1)
  ];
}

function buildRecommendationsTable(recs) {
  if (!recs || recs.length === 0) return [];
  const rows = [new TableRow({ tableHeader: true, children: [
    hCell("#", 420), hCell("Recommendation", 5760), hCell("Strength", 1440), hCell("Evidence", 1740)
  ]})];
  recs.forEach((r, i) => {
    const fill = recFill(r.strength, r.evidence_level);
    rows.push(new TableRow({ cantSplit: false, children: [
      dCell(String(i + 1), 420, fill, true),
      dCell(r.recommendation || "", 5760, fill),
      dCell(r.strength || "\u2014", 1440, fill, true),
      dCell(r.evidence_level || "\u2014", 1740, fill)
    ]}));
  });
  return [
    new Paragraph({ children: [new PageBreak()] }),
    hdr("Clinical Recommendations", 1),
    para(`${recs.length} recommendation${recs.length !== 1 ? "s" : ""} extracted`, { color: DGRAY, size: 18, italic: true }),
    richPara([
      { text: "  \u25A0 ", color: DTEAL, size: 18, bold: true }, { text: "Strong/High  ", color: DGRAY, size: 16 },
      { text: "  \u25A0 ", color: "B8860B", size: 18, bold: true }, { text: "Conditional/Moderate  ", color: DGRAY, size: 16 },
      { text: "  \u25A0 ", color: "999999", size: 18, bold: true }, { text: "Other", color: DGRAY, size: 16 },
    ], { spaceBefore: 0, spaceAfter: 80 }),
    new Table({ width: { size: 9360, type: WidthType.DXA }, columnWidths: [420, 5760, 1440, 1740], rows }),
    gap(1)
  ];
}

function buildDefinitionsSection(synthesis, rawMeds) {
  if (!synthesis || !synthesis.definitions_and_thresholds || synthesis.definitions_and_thresholds.length === 0) return [];
  const medNames = new Set((rawMeds || []).map(m => (m.drug || "").toLowerCase()));
  const items = synthesis.definitions_and_thresholds.filter(d => !medNames.has((d.term || "").toLowerCase()));
  if (items.length === 0) return [];
  const rows = [new TableRow({ tableHeader: true, children: [hCell("Term", 2800), hCell("Definition / Threshold", 6560)] })];
  items.forEach((d, i) => {
    const fill = i % 2 === 0 ? LGRAY : WHITE;
    rows.push(new TableRow({ cantSplit: false, children: [
      dCell(d.term || "", 2800, fill, true, NAVY), dCell(d.definition || "", 6560, fill)
    ]}));
  });
  return [
    hdr("Definitions & Diagnostic Thresholds", 1),
    para("High-yield definitions and thresholds that change management.", { color: DGRAY, size: 18, italic: true }),
    new Table({ width: { size: 9360, type: WidthType.DXA }, columnWidths: [2800, 6560], rows }),
    gap(1)
  ];
}

function buildMedicationsSection(synthesis, rawMeds) {
  if (synthesis && synthesis.medication_groups && synthesis.medication_groups.length > 0)
    return buildMedicationsGrouped(synthesis.medication_groups, rawMeds || []);
  return buildMedicationsFlat(rawMeds);
}

function buildMedicationsGrouped(groups, rawMeds) {
  const parts = [hdr("Medications", 1), para("Medications organized by clinical indication.", { color: DGRAY, size: 18, italic: true })];
  groups.forEach(group => {
    parts.push(hdr(group.group_name || "Other", 3));
    if (group.narrative) parts.push(para(group.narrative, { size: 20, color: "333333", indent: 180, italic: true }));
    (group.drugs || []).forEach(drugName => {
      const match = rawMeds.find(m =>
        (m.drug || "").toLowerCase().includes(drugName.toLowerCase()) ||
        drugName.toLowerCase().includes((m.drug || "").toLowerCase())
      );
      let detail = drugName;
      if (match) {
        const dosePart = match.dose && !/not specified/i.test(match.dose) ? ` \u2014 ${match.dose}` : "";
        const classPart = match.class ? ` (${match.class})` : "";
        detail = `${match.drug || drugName}${dosePart}${classPart}`;
      }
      parts.push(bullet(detail, 0));
    });
    parts.push(gap(1));
  });
  return parts;
}

function buildMedicationsFlat(meds) {
  if (!meds || meds.length === 0) return [];
  const seen = new Set();
  const unique = meds.filter(m => { const k = (m.drug||"").toLowerCase(); if(seen.has(k)) return false; seen.add(k); return true; });
  const rows = [new TableRow({ children: [hCell("Drug",2200), hCell("Dose",1800), hCell("Class",2160), hCell("Indication",3200)] })];
  unique.forEach((m, i) => {
    const fill = i % 2 === 0 ? LGRAY : WHITE;
    rows.push(new TableRow({ children: [
      dCell(m.drug||"",2200,fill,true), dCell(m.dose||"",1800,fill),
      dCell(m.class||"",2160,fill,false,DGRAY), dCell(m.indication||"",3200,fill)
    ]}));
  });
  return [
    hdr("Medications", 1),
    para(`${unique.length} medication${unique.length !== 1 ? "s" : ""} referenced`, { color: DGRAY, size: 18, italic: true }),
    new Table({ width: { size: 9360, type: WidthType.DXA }, columnWidths: [2200,1800,2160,3200], rows }),
    gap(1)
  ];
}

function buildRedFlagsSection(synthesis, rawFlags) {
  if (synthesis && synthesis.critical_alerts && synthesis.critical_alerts.length > 0)
    return buildCriticalAlerts(synthesis.critical_alerts);
  return buildRedFlagsFlat(rawFlags);
}

function buildCriticalAlerts(alerts) {
  const parts = [
    hdr("Red Flags & Critical Alerts", 1),
    new Paragraph({ spacing: { before: 60, after: 80 }, shading: { fill: RED, type: ShadingType.CLEAR },
      children: [new TextRun({ text: `  ${alerts.length} CRITICAL ALERT${alerts.length !== 1 ? "S" : ""} \u2014 Know These`, bold: true, color: WHITE, size: 20, font: "Arial" })] }),
  ];
  alerts.forEach(a => {
    parts.push(richPara([
      { text: "\u26A0 ", color: RED, size: 20, bold: true },
      { text: a.alert || "", color: "333333", size: 20, bold: true },
    ], { spaceBefore: 80, spaceAfter: 20 }));
    if (a.why_it_matters)
      parts.push(para(a.why_it_matters, { size: 18, color: DGRAY, italic: true, indent: 360, spaceBefore: 0, spaceAfter: 60 }));
  });
  parts.push(gap(1));
  return parts;
}

function buildRedFlagsFlat(flags) {
  if (!flags || flags.length === 0) return [];
  const seen = new Set();
  const unique = flags.filter(f => { const k=toStr(f).substring(0,60).toLowerCase(); if(seen.has(k)) return false; seen.add(k); return true; });
  return [
    hdr("Red Flags", 1),
    new Paragraph({ spacing: { before: 60, after: 60 }, shading: { fill: RED, type: ShadingType.CLEAR },
      children: [new TextRun({ text: `  ${unique.length} WARNING SIGN${unique.length !== 1 ? "S" : ""}`, bold: true, color: WHITE, size: 20, font: "Arial" })] }),
    ...unique.map(f => bullet(toStr(f), 0, { color: "333333" })),
    gap(1)
  ];
}

function buildFollowUpSection(text) {
  const s = toStr(text);
  if (!s || s.match(/^not specified/i)) return [];
  return [ hdr("Follow-Up & Monitoring", 1), para(s, { size: 20, color: "333333" }) ];
}

function buildEscalationSection(text) {
  const s = toStr(text);
  if (!s || s.match(/^not specified/i)) return [];
  return [ hdr("Escalation Path", 1), para(s, { size: 20, color: "333333" }) ];
}

// ══════════════════════════════════════════════════════════════════
//  SECTION 12 — ITE EXAM INTELLIGENCE
// ══════════════════════════════════════════════════════════════════

function buildITEIntelligenceSection(iteIntelligence) {
  if (!iteIntelligence) return [];

  const qids      = iteIntelligence.linked_qids || iteIntelligence.question_ids || [];
  const concepts  = iteIntelligence.high_yield_concepts || [];
  const summary   = iteIntelligence.concept_summary || "";
  const artId     = iteIntelligence.article_id || iteIntelligence._match_method || "";
  const citCount  = iteIntelligence.citation_count || qids.length;
  const examYears = (iteIntelligence.exam_years || iteIntelligence.exam_years_cited || []).sort();
  const examYrs   = examYears.join(", ");

  if (qids.length === 0 && concepts.length === 0) return [];

  const parts = [];

  // ── Spacing before ITE section ──
  parts.push(gap(2));

  // ── Navy banner ──
  parts.push(new Paragraph({
    spacing: { before: 0, after: 0 },
    shading: { fill: NAVY, type: ShadingType.CLEAR },
    children: [new TextRun({ text: "  \u2605 ITE EXAM INTELLIGENCE", bold: true, color: WHITE, size: 24, font: "Arial" })]
  }));

  // ── Blue sub-banner: stats ──
  const statParts = [];
  if (citCount) statParts.push(`${citCount} question${citCount !== 1 ? "s" : ""} across ${examYears.length} exam year${examYears.length !== 1 ? "s" : ""}`);
  if (examYrs)  statParts.push(`Years tested: ${examYrs}`);
  parts.push(new Paragraph({
    spacing: { before: 0, after: 120 },
    shading: { fill: BLUE, type: ShadingType.CLEAR },
    children: [new TextRun({ text: "  " + (statParts.join("  |  ") || "ITE exam data"), italic: true, color: LBLUE, size: 18, font: "Arial" })]
  }));

  // ── Color key ──
  const COLOR_KEY_BG = "1A1A2E";
  parts.push(new Paragraph({
    spacing: { before: 0, after: 0 },
    shading: { fill: COLOR_KEY_BG, type: ShadingType.CLEAR },
    children: [
      new TextRun({ text: "  Concept rank: ", color: "999999", size: 16, font: "Arial", italic: true }),
      new TextRun({ text: "\u25A0 Highly specific to this article", color: "00B050", bold: true, size: 16, font: "Arial" }),
      new TextRun({ text: "   \u25A0 Moderately specific", color: "FFD700", bold: true, size: 16, font: "Arial" }),
      new TextRun({ text: "   \u25A0 Common across question bank", color: "FF6B6B", bold: true, size: 16, font: "Arial" }),
    ]
  }));

  // ── Per-QID table ──
  if (qids.length > 0) {
    const headerRow = new TableRow({ tableHeader: true, children: [
      hCell("Year",           900,  NAVY),
      hCell("QID",            1440, NAVY),
      hCell("Question Stem",  3960, NAVY),
      hCell("Concept Tested", 3060, NAVY)
    ]});

    // Color map for TF-IDF buckets — dark background needs bright chip colors
    const CHIP_COLORS = { green: "00B050", yellow: "FFD700", red: "FF6B6B", white: "CCCCCC" };
    const CONCEPT_BG  = "1A1A2E";  // near-black navy for concept column only

    const dataRows = qids.map((q, i) => {
      const fill = i % 2 === 0 ? LGRAY : WHITE;
      const stem = q.question_stem || q.question_text || "";
      const stemShort = stem.length > 160 ? stem.substring(0, 157) + "\u2026" : stem;

      // Build concept cell: colored chips if concept_colors present, fallback to plain text
      let conceptCell;
      const segments = q.concept_colors;
      if (segments && segments.length > 0) {
        const runs = segments.map(seg => new TextRun({
          text: seg.text,
          color: CHIP_COLORS[seg.color] || CHIP_COLORS.white,
          bold: seg.color !== "white",
          size: 16,
          font: "Arial"
        }));
        conceptCell = new TableCell({
          width: { size: 3060, type: WidthType.DXA },
          shading: { fill: CONCEPT_BG, type: ShadingType.CLEAR },
          children: [new Paragraph({ spacing: { before: 40, after: 40 }, children: runs })]
        });
      } else {
        const concept = q.concept_tested || q.interpretation || "\u2014";
        conceptCell = new TableCell({
          width: { size: 3060, type: WidthType.DXA },
          shading: { fill: CONCEPT_BG, type: ShadingType.CLEAR },
          children: [new Paragraph({ spacing: { before: 40, after: 40 }, children: [
            new TextRun({ text: concept, color: "CCCCCC", size: 16, font: "Arial" })
          ]})]
        });
      }

      return new TableRow({ cantSplit: false, children: [
        dCell(String(q.exam_year || "\u2014"), 900,  fill, true, NAVY),
        dCell(q.qid || "\u2014",              1440, fill, false, BLUE),
        dCell(stemShort,                       3960, fill),
        conceptCell
      ]});
    });
    parts.push(new Table({
      width: { size: 9360, type: WidthType.DXA },
      columnWidths: [900, 1440, 3960, 3060],
      rows: [headerRow, ...dataRows]
    }));
    parts.push(gap(1));
  }

  // ── High-yield concepts ──
  if (concepts.length > 0) {
    parts.push(new Paragraph({
      spacing: { before: 80, after: 60 }, shading: { fill: TEAL, type: ShadingType.CLEAR },
      children: [new TextRun({ text: "  HIGH-YIELD CONCEPTS FROM THIS ARTICLE", bold: true, color: DTEAL, size: 18, font: "Arial" })]
    }));
    concepts.forEach(c => parts.push(bullet(c, 0, { color: "333333" })));
    parts.push(gap(1));
  }

  // ── Concept summary ──
  if (summary) {
    parts.push(para(summary, { size: 20, color: "333333", italic: true, indent: 180 }));
    parts.push(gap(1));
  }

  return parts;
}

// ── Footer ────────────────────────────────────────────────────
function buildFooter(metadata) {
  const cov  = metadata.field_coverage_score != null ? (metadata.field_coverage_score * 100).toFixed(0) + "%" : "";
  const valid = metadata.validation_passed ? "Passed" : "Warnings";
  const footerParts = [`Validation: ${valid}`];
  if (cov) footerParts.push(`Coverage: ${cov}`);
  return [
    hr(),
    para(footerParts.join("  |  "), { color: DGRAY, size: 16, center: true }),
    para("Generated by guideline_extractor_v2 \u2014 ABFM Board Prep Project", { color: DGRAY, size: 16, center: true })
  ];
}

// ══════════════════════════════════════════════════════════════════
//  MAIN
// ══════════════════════════════════════════════════════════════════

const jsonPath = process.argv[2];
const docxPath = process.argv[3];

if (!jsonPath || !docxPath) { console.error("Usage: node build_summary.js <input.json> <output.docx>"); process.exit(1); }
if (!fs.existsSync(jsonPath)) { console.error("Input JSON not found: " + jsonPath); process.exit(1); }

const data = JSON.parse(fs.readFileSync(jsonPath, "utf-8"));
const { source = {}, classification = {}, extraction = {}, metadata = {} } = data;
const synthesis       = extraction.synthesis || null;
const iteIntelligence = extraction.ite_intelligence || data.ite_intelligence || null;

// ── Assemble ──────────────────────────────────────────────────
const children = [];

// Page 1: Overview
children.push(...buildTitleBlock(source));
children.push(...buildClassificationBadge(classification));
children.push(...buildClinicalSummary(extraction, synthesis));
children.push(...buildPracticePearls(synthesis));
children.push(...buildPopulationTable(extraction.population));

// Page 2+: Clinical Details
children.push(...buildDefinitionsSection(synthesis, extraction.medications));
children.push(...buildRecommendationsTable(extraction.recommendations));
children.push(...buildMedicationsSection(synthesis, extraction.medications));
children.push(...buildRedFlagsSection(synthesis, extraction.red_flags));

// Management
children.push(...buildFollowUpSection(extraction.follow_up));
children.push(...buildEscalationSection(extraction.escalation_path));

// Section 12: ITE Intelligence (renders only if ite_intelligence block present)
children.push(...buildITEIntelligenceSection(iteIntelligence));

children.push(...buildFooter(metadata));

const doc = new Document({
  numbering: {
    config: [{
      reference: "bullets",
      levels: [
        { level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 540, hanging: 270 } } } },
        { level: 1, format: LevelFormat.BULLET, text: "\u25E6", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 900, hanging: 270 } } } }
      ]
    }]
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
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1080, right: 1080, bottom: 1080, left: 1080 } } },
    children
  }]
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync(docxPath, buf);
  console.log("  Summary DOCX written: " + docxPath);
}).catch(err => {
  console.error("DOCX generation error:", err.message);
  process.exit(1);
});
