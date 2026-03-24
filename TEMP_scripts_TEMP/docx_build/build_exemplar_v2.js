/**
 * build_exemplar_v2.js — DB-powered DOCX using v1 visual style from build_summary.js
 *
 * Sections:
 *   1  Title Banner (navy)
 *   2  Classification Badge (blue table)
 *   3  Clinical Pathway Map (new — ICD-10 + pathway roles)
 *   4  ITE Exam Intelligence (v1 style — navy/blue banners, concept ranking)
 *   5  High-Yield Concepts (teal banner + bullet list + mini table)
 *   6  Exam Trend Context (new)
 *   7  Study Note (hybrid tone)
 *   8  Footer
 */

const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  HeadingLevel, AlignmentType, BorderStyle, WidthType, ShadingType,
  LevelFormat, PageBreak
} = require("docx");

// ── Colors (matched from build_summary.js) ─────────────────
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
const CONCEPT_BG = "1A1A2E";
const CHIP = { green: "00B050", yellow: "FFD700", red: "FF6B6B", white: "CCCCCC" };

const BORDER  = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const BORDERS = { top: BORDER, bottom: BORDER, left: BORDER, right: BORDER };

// ── Helpers (matched from build_summary.js) ─────────────────
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
    children: [new TextRun({ text, bold, italic, color, size, font: "Aptos" })]
  });
}

function bullet(text, level = 0, opts = {}) {
  const { bold = false, color = "000000" } = opts;
  return new Paragraph({
    numbering: { reference: "bullets", level },
    spacing: { before: 40, after: 40 },
    children: [new TextRun({ text, bold, color, size: 20, font: "Aptos" })]
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

function hCell(text, width, fill = NAVY, align = AlignmentType.LEFT) {
  return new TableCell({
    width: { size: width, type: WidthType.DXA },
    shading: { fill, type: ShadingType.CLEAR },
    margins: { top: 80, bottom: 80, left: 120, right: 120 },
    borders: BORDERS,
    verticalAlign: "center",
    children: [new Paragraph({
      alignment: align,
      children: [new TextRun({ text, bold: true, color: WHITE, size: 18, font: "Aptos" })]
    })]
  });
}

function dCell(text, width, fill = WHITE, bold = false, color = "000000", align = AlignmentType.LEFT) {
  return new TableCell({
    width: { size: width, type: WidthType.DXA },
    shading: { fill, type: ShadingType.CLEAR },
    margins: { top: 80, bottom: 80, left: 120, right: 120 },
    borders: BORDERS,
    verticalAlign: "center",
    children: [new Paragraph({
      alignment: align,
      children: [new TextRun({ text: String(text || ""), bold, color, size: 18, font: "Aptos" })]
    })]
  });
}

// ============================================================
// DATA — ART-0370
// ============================================================

const article = {
  article_id: "ART-0370",
  title: "Pharmacologic Approaches to Glycemic Treatment: Standards of Care in Diabetes \u2014 2023",
  author1: "ElSayed",
  author2: "Aleppo",
  year: "2023",
  journal: "Diabetes Care",
  tier: "Core",
  engine_type: "chronic_guideline",
  citation_count: 3,
  categories: "Endocrine, Nephrologic",
  citation_display: "ElSayed NA, Aleppo G, Aroda VR, et al. 9. Pharmacologic approaches to glycemic treatment: standards of care in diabetes\u20142023. Diabetes Care. 2023;46(Suppl 1):S140-S157.",
  codon_filename: "ElSayed_Aleppo_2023#@#ART-0370@#@.pdf"
};

const icd10_map = [
  { code: "E11.9", desc: "Type 2 diabetes mellitus without complications", relevance: "primary", role: "first_line" },
  { code: "N18.3", desc: "Chronic kidney disease, stage 3", relevance: "secondary", role: "monitoring" },
  { code: "E10.10", desc: "Type 1 DM with ketoacidosis without coma", relevance: "secondary", role: "monitoring" },
  { code: "K85.9", desc: "Acute pancreatitis, unspecified", relevance: "related", role: "special_pops" },
  { code: "R73.9", desc: "Hyperglycemia, unspecified", relevance: "related", role: "special_pops" }
];

const questions = [
  {
    qid: "QID-2023-0037", exam_year: 2023,
    body_system: "Nephrologic", subcategory: "Pharmacology",
    stem: "In patients with type 2 diabetes, medications from which one of the following classes have been shown to reduce the progression of chronic kidney disease?",
    correct: "C) SGLT2 inhibitors",
    concept_summary: "SGLT2 inhibitors are specifically recommended for patients with type 2 diabetes and stage 3+ CKD to slow progression independent of glucose control."
  },
  {
    qid: "QID-2023-0145", exam_year: 2023,
    body_system: "Endocrine", subcategory: "Pharmacology",
    stem: "A 56-year-old female with type 2 diabetes is hospitalized with acute epigastric pain, nausea, and vomiting. She reports that several of her diabetes medications were recently changed. Which class of medications is most likely responsible?",
    correct: "B) GLP-1 receptor agonists",
    concept_summary: "GLP-1 receptor agonists are associated with pancreatitis risk and should be discontinued in patients with suspected pancreatitis."
  },
  {
    qid: "QID-2023-0163", exam_year: 2023,
    body_system: "Endocrine", subcategory: "Pharmacology",
    stem: "A 56-year-old female comes to your office for an acute visit because she has had increased urinary frequency, thirst, and fatigue over the past month. Her hemoglobin A1C is 10.2%. What is the most appropriate initial pharmacologic treatment?",
    correct: "A) Basal insulin",
    concept_summary: "Symptomatic hyperglycemia with A1C \u226510% requires immediate insulin therapy per ADA guidelines, before considering other antidiabetic agents once glucose toxicity resolves."
  }
];

const highYield = {
  drugs: ["SGLT2 inhibitors", "GLP-1 receptor agonists", "Basal insulin", "Metformin", "DPP-4 inhibitors", "Thiazolidinediones"],
  diagnoses: ["Type 2 diabetes", "Chronic kidney disease", "Acute pancreatitis", "Diabetic ketoacidosis", "Hyperglycemia", "Microalbuminuria"],
  thresholds: ["A1C \u226510% (insulin initiation)", "Stage 3 CKD (SGLT2i indication)"],
  guidelines: ["ADA Standards of Care"]
};

const ktcData = [
  { concept: "SGLT2i for CKD progression in T2DM", tested: "Drug class \u2192 renal protection", qid: "QID-2023-0037" },
  { concept: "GLP-1 RA and pancreatitis risk", tested: "Drug complication recognition", qid: "QID-2023-0145" },
  { concept: "Insulin initiation at A1C \u226510%", tested: "Treatment escalation threshold", qid: "QID-2023-0163" }
];

const trendContext = {
  body_system: "Endocrine",
  slope: -1.31,
  direction: "declining",
  counts: { 2020: 16, 2021: 20, 2022: 17, 2023: 16, 2024: 10, 2025: 13 },
  subcategory_note: "Pharmacology is the dominant subcategory for this article's linked questions (3/3)."
};

// ============================================================
// BUILD SECTIONS
// ============================================================

const children = [];

// ── SECTION 1: TITLE BANNER (navy, centered) ──
children.push(new Paragraph({
  alignment: AlignmentType.CENTER, spacing: { before: 240, after: 60 },
  shading: { fill: NAVY, type: ShadingType.CLEAR },
  children: [new TextRun({ text: article.title, bold: true, color: WHITE, size: 32, font: "Aptos" })]
}));
children.push(new Paragraph({
  alignment: AlignmentType.CENTER, spacing: { before: 0, after: 240 },
  shading: { fill: NAVY, type: ShadingType.CLEAR },
  children: [new TextRun({ text: `${article.author1} & ${article.author2}  |  ${article.year}  |  ${article.journal}`, italic: true, color: LBLUE, size: 20, font: "Aptos" })]
}));

// Citation line below banner
children.push(new Paragraph({
  alignment: AlignmentType.CENTER, spacing: { before: 80, after: 120 },
  children: [new TextRun({ text: article.citation_display, italic: true, color: DGRAY, size: 18, font: "Aptos" })]
}));

// ── SECTION 2: CLASSIFICATION BADGE (ITE Citations + Body Systems only) ──
children.push(gap(1));
children.push(new Table({
  width: { size: 9360, type: WidthType.DXA },
  columnWidths: [3120, 6240],
  rows: [
    new TableRow({ cantSplit: true, children: [
      hCell("ITE Citations", 3120, BLUE), hCell("Body Systems", 6240, BLUE)
    ]}),
    new TableRow({ cantSplit: true, children: [
      dCell(String(article.citation_count), 3120, WHITE, true, "000000", AlignmentType.CENTER),
      dCell(article.categories, 6240)
    ]})
  ]
}));
children.push(gap(1));

// ── SECTION 3: CLINICAL PATHWAY MAP ──
children.push(hdr("Clinical Pathway Map", 1));
children.push(para("ICD-10 assignments and clinical pathway roles \u2014 where this article fits in clinical practice.", { color: DGRAY, size: 18, italic: true }));

const pathRows = [
  new TableRow({ cantSplit: true, tableHeader: true, children: [
    hCell("ICD-10", 1200, NAVY), hCell("Description", 3600, NAVY),
    hCell("Relevance", 1380, NAVY), hCell("Pathway Role", 3180, NAVY)
  ]})
];
icd10_map.forEach((item, i) => {
  const fill = i % 2 === 0 ? LGRAY : WHITE;
  // Color-code relevance
  const relFill = item.relevance === "primary" ? TEAL
                : item.relevance === "secondary" ? AMBER
                : LGRAY;
  pathRows.push(new TableRow({ cantSplit: true, children: [
    dCell(item.code, 1200, fill, true, NAVY),
    dCell(item.desc, 3600, fill),
    dCell(item.relevance, 1380, relFill, true, item.relevance === "primary" ? DTEAL : DGRAY),
    dCell(item.role.replace(/_/g, " "), 3180, fill)
  ]}));
});

children.push(new Table({
  width: { size: 9360, type: WidthType.DXA },
  columnWidths: [1200, 3600, 1380, 3180],
  rows: pathRows
}));
children.push(gap(2));

// ── SECTION 4: ITE EXAM INTELLIGENCE (v1 style) ──
const examYears = [...new Set(questions.map(q => q.exam_year))].sort();
const examYrs = examYears.join(", ");

children.push(new Paragraph({
  spacing: { before: 0, after: 0 },
  shading: { fill: NAVY, type: ShadingType.CLEAR },
  children: [new TextRun({ text: "  \u2605 ITE EXAM INTELLIGENCE", bold: true, color: WHITE, size: 24, font: "Aptos" })]
}));

children.push(new Paragraph({
  spacing: { before: 0, after: 120 },
  shading: { fill: BLUE, type: ShadingType.CLEAR },
  children: [new TextRun({ text: `  ${questions.length} question${questions.length !== 1 ? "s" : ""} across ${examYears.length} exam year${examYears.length !== 1 ? "s" : ""}  |  Years tested: ${examYrs}`, italic: true, color: LBLUE, size: 18, font: "Aptos" })]
}));

// Color key
children.push(new Paragraph({
  spacing: { before: 0, after: 0 },
  shading: { fill: CONCEPT_BG, type: ShadingType.CLEAR },
  children: [
    new TextRun({ text: "  Concept colors: ", color: "999999", size: 16, font: "Aptos", italic: true }),
    new TextRun({ text: "\u25A0 Diagnoses", color: CHIP.green, bold: true, size: 16, font: "Aptos" }),
    new TextRun({ text: "   \u25A0 Drugs/Treatments", color: CHIP.yellow, bold: true, size: 16, font: "Aptos" }),
    new TextRun({ text: "   \u25A0 Thresholds", color: CHIP.red, bold: true, size: 16, font: "Aptos" }),
  ]
}));

// Per-question rows
const qHeaderRow = new TableRow({ cantSplit: true, tableHeader: true, children: [
  hCell("Year", 900, NAVY, AlignmentType.CENTER), hCell("QID", 1440, NAVY, AlignmentType.CENTER),
  hCell("Question Stem", 3960, NAVY), hCell("Concept Tested", 3060, NAVY)
]});

// Parse concept_summary into colored segments: drugs=yellow, diagnoses=green, thresholds=red
function colorizeConceptText(q) {
  // Extract known entities from the question's concept tags
  const drugTerms = ["SGLT2 inhibitors", "GLP-1 receptor agonists", "basal insulin", "metformin",
    "DPP-4 inhibitors", "thiazolidinediones", "insulin"];
  const diagTerms = ["type 2 diabetes", "chronic kidney disease", "CKD", "pancreatitis",
    "hyperglycemia", "ketoacidosis"];
  const threshTerms = ["A1C", "stage 3", "\u226510%", "10%"];

  const runs = [];
  // Split into sentences for cleaner coloring
  const text = q.concept_summary;

  // Simple approach: color the whole summary, highlighting key terms inline
  let remaining = text;
  const allTerms = [
    ...drugTerms.map(t => ({ term: t, color: CHIP.yellow })),
    ...diagTerms.map(t => ({ term: t, color: CHIP.green })),
    ...threshTerms.map(t => ({ term: t, color: CHIP.red }))
  ].sort((a, b) => b.term.length - a.term.length); // longest first to avoid partial matches

  // Build segments by finding terms in order of appearance
  const segments = [];
  let pos = 0;
  while (pos < text.length) {
    let found = null;
    let foundAt = text.length;
    for (const { term, color } of allTerms) {
      const idx = text.toLowerCase().indexOf(term.toLowerCase(), pos);
      if (idx !== -1 && idx < foundAt) {
        foundAt = idx;
        found = { term: text.substring(idx, idx + term.length), color, idx };
      }
    }
    if (found && found.idx < text.length) {
      if (found.idx > pos) {
        segments.push({ text: text.substring(pos, found.idx), color: CHIP.white });
      }
      segments.push({ text: found.term, color: found.color, bold: true });
      pos = found.idx + found.term.length;
    } else {
      segments.push({ text: text.substring(pos), color: CHIP.white });
      break;
    }
  }

  return segments.map(seg => new TextRun({
    text: seg.text,
    color: seg.color,
    bold: seg.bold || false,
    size: 16,
    font: "Aptos"
  }));
}

const qDataRows = questions.map((q, i) => {
  const fill = i % 2 === 0 ? LGRAY : WHITE;
  const stemShort = q.stem.length > 160 ? q.stem.substring(0, 157) + "\u2026" : q.stem;
  return new TableRow({ cantSplit: true, children: [
    dCell(String(q.exam_year), 900, fill, true, NAVY, AlignmentType.CENTER),
    dCell(q.qid, 1440, fill, false, BLUE, AlignmentType.CENTER),
    dCell(stemShort, 3960, fill),
    new TableCell({
      width: { size: 3060, type: WidthType.DXA },
      shading: { fill: CONCEPT_BG, type: ShadingType.CLEAR },
      margins: { top: 80, bottom: 80, left: 120, right: 120 },
      borders: BORDERS,
      verticalAlign: "center",
      children: [new Paragraph({ spacing: { before: 40, after: 40 }, children: colorizeConceptText(q) })]
    })
  ]});
});

children.push(new Table({
  width: { size: 9360, type: WidthType.DXA },
  columnWidths: [900, 1440, 3960, 3060],
  rows: [qHeaderRow, ...qDataRows]
}));
children.push(gap(1));

// Correct answers
children.push(new Paragraph({
  spacing: { before: 80, after: 60 },
  shading: { fill: BLUE, type: ShadingType.CLEAR },
  children: [new TextRun({ text: "  CORRECT ANSWERS", bold: true, color: WHITE, size: 18, font: "Aptos" })]
}));
questions.forEach(q => {
  children.push(new Paragraph({
    spacing: { before: 40, after: 40 },
    indent: { left: 360 },
    children: [
      new TextRun({ text: `${q.qid}: `, bold: true, color: BLUE, size: 18, font: "Aptos" }),
      new TextRun({ text: q.correct, color: "333333", size: 18, font: "Aptos" }),
      new TextRun({ text: `  (${q.body_system} / ${q.subcategory})`, color: DGRAY, size: 16, font: "Aptos", italic: true })
    ]
  }));
});
children.push(gap(1));

// ── SECTION 5: KEY TESTABLE CONCEPTS (grouped with ITE block) ──
children.push(hdr("Key Testable Concepts", 2));
const ktcRows = [
  new TableRow({ cantSplit: true, tableHeader: true, children: [
    hCell("Concept", 3600, NAVY), hCell("What Was Tested", 3060, NAVY), hCell("Question", 2700, NAVY)
  ]})
];
ktcData.forEach((item, i) => {
  const fill = i % 2 === 0 ? LGRAY : WHITE;
  ktcRows.push(new TableRow({ cantSplit: true, children: [
    dCell(item.concept, 3600, fill, true, NAVY),
    dCell(item.tested, 3060, fill),
    dCell(item.qid, 2700, fill, false, BLUE)
  ]}));
});
children.push(new Table({
  width: { size: 9360, type: WidthType.DXA },
  columnWidths: [3600, 3060, 2700],
  rows: ktcRows
}));
children.push(gap(1));

// ── SECTION 6: EXAM TREND CONTEXT (grouped with ITE block) ──
children.push(hdr("Exam Trend Context", 2));

const tc = trendContext;
const trendLine = Object.entries(tc.counts).map(([yr, ct]) => `${yr}: ${ct}`).join("  \u2192  ");
const trendIcon = tc.slope > 0 ? "\u2191" : tc.slope < 0 ? "\u2193" : "\u2192";

children.push(new Table({
  width: { size: 9360, type: WidthType.DXA },
  columnWidths: [2340, 2340, 4680],
  rows: [
    new TableRow({ cantSplit: true, children: [
      hCell("Body System", 2340, BLUE), hCell("Trend", 2340, BLUE), hCell("Question Count by Year", 4680, BLUE)
    ]}),
    new TableRow({ cantSplit: true, children: [
      dCell(tc.body_system, 2340, LBLUE, true, NAVY),
      dCell(`${trendIcon} ${tc.slope}/yr (${tc.direction})`, 2340, tc.slope < 0 ? AMBER : TEAL, true),
      dCell(trendLine, 4680)
    ]})
  ]
}));
children.push(gap(1));

children.push(para(tc.subcategory_note, { size: 20, color: "333333" }));
children.push(para(
  `Although Endocrine questions are trending downward overall, Pharmacology \u2014 the subcategory driving all three linked questions \u2014 remains a high-frequency testing target. Expect drug-specific mechanism and complication questions to persist.`,
  { size: 19, color: DGRAY, italic: true, indent: 180 }
));
children.push(gap(1));

// ── SECTION 7: STUDY NOTE (grouped with ITE block) ──
children.push(new Paragraph({
  spacing: { before: 0, after: 0 },
  shading: { fill: NAVY, type: ShadingType.CLEAR },
  children: [new TextRun({ text: "  \u270E STUDY NOTE", bold: true, color: WHITE, size: 22, font: "Aptos" })]
}));

children.push(new Paragraph({
  spacing: { before: 0, after: 60 },
  shading: { fill: LBLUE, type: ShadingType.CLEAR },
  children: [new TextRun({
    text: "  This chronic guideline serves as a first-line treatment reference for Type 2 diabetes (E11.9), with secondary relevance to CKD monitoring and special population considerations for pancreatitis and hyperglycemia. It was tested 3 times on the 2023 ITE, all in Pharmacology.",
    color: NAVY, size: 20, font: "Aptos"
  })]
}));

children.push(new Paragraph({
  spacing: { before: 0, after: 120 },
  shading: { fill: LBLUE, type: ShadingType.CLEAR },
  children: [new TextRun({
    text: "  Know your SGLT2 inhibitors for renal protection, your GLP-1 agonist contraindications, and the A1C \u226510% insulin-first rule. The board loves testing drug-specific complications and escalation thresholds from this guideline.",
    bold: true, color: NAVY, size: 20, font: "Aptos"
  })]
}));
children.push(gap(2));

// ── SECTION 8: HIGH-YIELD CONCEPTS (at the end) ──
children.push(new Paragraph({
  spacing: { before: 80, after: 60 },
  shading: { fill: TEAL, type: ShadingType.CLEAR },
  children: [new TextRun({ text: "  HIGH-YIELD CONCEPTS FROM THIS ARTICLE", bold: true, color: DTEAL, size: 18, font: "Aptos" })]
}));

const conceptTypes = [
  { label: "Drugs", items: highYield.drugs },
  { label: "Diagnoses", items: highYield.diagnoses },
  { label: "Thresholds", items: highYield.thresholds },
  { label: "Guidelines", items: highYield.guidelines }
];

conceptTypes.forEach(ct => {
  children.push(new Paragraph({
    spacing: { before: 100, after: 20 },
    children: [new TextRun({ text: ct.label, bold: true, color: BLUE, size: 20, font: "Aptos" })]
  }));
  ct.items.forEach(item => {
    children.push(bullet(item, 0, { color: "333333" }));
  });
});
children.push(gap(2));

// ── SECTION 8: FOOTER ──
children.push(hr());
children.push(para(`${article.article_id}  |  ${article.codon_filename}`, { color: DGRAY, size: 16, center: true }));
children.push(para("Generated from ite_intelligence.db \u2014 ABFM Board Prep Project \u2014 DB Intelligence v1.0", { color: DGRAY, size: 16, center: true }));

// ============================================================
// ASSEMBLE & WRITE
// ============================================================

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
    default: { document: { run: { font: "Aptos", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, color: NAVY, font: "Aptos" },
        paragraph: { spacing: { before: 360, after: 120 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, color: BLUE, font: "Aptos" },
        paragraph: { spacing: { before: 240, after: 100 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 22, bold: true, color: DGRAY, font: "Aptos" },

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

const OUTPUT = "/sessions/confident-cool-carson/mnt/claude_knowledge/ART-0370_DB_Intelligence_v2.docx";

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync(OUTPUT, buf);
  console.log(`Written to ${OUTPUT}`);
  console.log(`Size: ${(buf.length / 1024).toFixed(1)} KB`);
});
