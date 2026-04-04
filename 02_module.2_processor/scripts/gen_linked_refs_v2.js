const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  HeadingLevel, AlignmentType, BorderStyle, WidthType, ShadingType,
  LevelFormat, PageNumber, Footer, PageBreak
} = require("docx");
const fs   = require("fs");
const path = require("path");

// PATHS
const PROJECT_ROOT = path.resolve(__dirname, "../../");
const LOG      = path.join(PROJECT_ROOT, "gen_log.txt");
const CROSSWALK = path.join(PROJECT_ROOT, "_archive_", "04_reference_data", "linked_refs_crosswalk_final.csv");
const OUT_PATH  = path.join(PROJECT_ROOT, "_archive_", "01_curriculum", "00_RPT_linked_refs_20-25.docx");

// FILE LOGGER — PowerShell cannot capture Node stdout
fs.writeFileSync(LOG, "=== LinkedRefs v2 Generator ===\n" + new Date().toISOString() + "\n\n");
function log(msg) { fs.appendFileSync(LOG, msg + "\n"); }
function warn(msg) { fs.appendFileSync(LOG, "[WARN] " + msg + "\n"); }

log("Script started");

// COLORS
const C = {
  mustRead: "1F3864", core: "1F4E79", supp: "2E4057", unmatched: "595959",
  sessionHdr: "2E75B6", threshBg: "EBF3FB", recBg: "F0F7EE",
  medBg: "FFF8EC", redFlagBg: "FDE8E8", summBg: "E8F0F7", popBg: "EEF4FB",
  followBg: "F5F0FA", labelText: "1F3864"
};
const TIER_COLOR = { "Must-Read": C.mustRead, "Core": C.core, "Supplementary": C.supp, "Unmatched": C.unmatched };

function safe(v, fb) {
  fb = fb || "";
  if (!v) return fb;
  if (typeof v === "string") return v;
  if (Array.isArray(v)) return v.join("; ");
  return String(v);
}

function parseCSV(fp) {
  const lines = fs.readFileSync(fp, "utf8").replace(/\r/g, "").split("\n");
  const headers = lines[0].split(",").map(h => h.replace(/^"|"$/g, "").trim());
  return lines.slice(1).filter(l => l.trim()).map(line => {
    const fields = []; let cur = "", inQ = false;
    for (let i = 0; i < line.length; i++) {
      if (line[i] === '"') { inQ = !inQ; }
      else if (line[i] === "," && !inQ) { fields.push(cur); cur = ""; }
      else { cur += line[i]; }
    }
    fields.push(cur);
    const obj = {};
    headers.forEach((h, i) => { obj[h] = (fields[i] || "").trim(); });
    return obj;
  });
}

function loadJSON(fp) {
  try { return JSON.parse(fs.readFileSync(fp, "utf8")); }
  catch (e) { warn("JSON load failed: " + fp + " — " + e.message); return null; }
}

function brd(color, size) {
  return { style: BorderStyle.SINGLE, size: size || 1, color: color || "CCCCCC" };
}
function cellBorders(color) { const b = brd(color); return { top: b, bottom: b, left: b, right: b }; }

// PARAGRAPH BUILDERS
function sessionHeading(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    children: [new TextRun({ text, bold: true, size: 32, font: "Arial", color: C.sessionHdr })],
    spacing: { before: 360, after: 120 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: C.sessionHdr, space: 1 } }
  });
}

function sectionLabel(text, bg) {
  return new Paragraph({
    children: [new TextRun({ text: "  " + text + "  ", bold: true, size: 18, font: "Arial", color: C.labelText })],
    spacing: { before: 160, after: 40 },
    shading: { fill: bg || "E8F0F7", type: ShadingType.CLEAR }
  });
}

function bodyPara(text) {
  return new Paragraph({
    children: [new TextRun({ text: safe(text), size: 20, font: "Arial" })],
    spacing: { before: 40, after: 40 }
  });
}

function bulletItem(text) {
  return new Paragraph({
    numbering: { reference: "bullets", level: 0 },
    children: [new TextRun({ text: safe(text), size: 20, font: "Arial" })],
    spacing: { before: 20, after: 20 }
  });
}

function citationBlock(citation, tier) {
  const color = TIER_COLOR[tier] || C.unmatched;
  return new Paragraph({
    children: [
      new TextRun({ text: "[" + tier + "]  ", bold: true, size: 18, font: "Arial", color }),
      new TextRun({ text: citation, size: 18, font: "Arial", italics: true, color: "444444" })
    ],
    spacing: { before: 60, after: 80 },
    border: { left: { style: BorderStyle.SINGLE, size: 12, color, space: 6 } },
    indent: { left: 240 }
  });
}

function metaLine(text) {
  return new Paragraph({
    children: [new TextRun({ text: safe(text), size: 18, font: "Arial", color: "666666", italics: true })],
    spacing: { before: 20, after: 60 },
    indent: { left: 240 }
  });
}

function divider() {
  return new Paragraph({
    children: [],
    spacing: { before: 100, after: 100 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 2, color: "DDDDDD", space: 1 } }
  });
}

// TABLE BUILDERS
function hdrCell(text, w) {
  return new TableCell({
    width: { size: w, type: WidthType.DXA },
    borders: cellBorders("999999"),
    shading: { fill: "1F3864", type: ShadingType.CLEAR },
    margins: { top: 80, bottom: 80, left: 120, right: 120 },
    children: [new Paragraph({
      children: [new TextRun({ text: safe(text), bold: true, size: 18, font: "Arial", color: "FFFFFF" })]
    })]
  });
}

function dataCell(text, w, bg) {
  return new TableCell({
    width: { size: w, type: WidthType.DXA },
    borders: cellBorders("CCCCCC"),
    shading: { fill: bg || "FFFFFF", type: ShadingType.CLEAR },
    margins: { top: 60, bottom: 60, left: 120, right: 120 },
    children: [new Paragraph({
      children: [new TextRun({ text: safe(text, "\u2014"), size: 18, font: "Arial" })]
    })]
  });
}

function thresholdsTable(items) {
  if (!items || !items.length) return null;
  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: [3120, 2160, 4080],
    rows: [
      new TableRow({ tableHeader: true, children: [hdrCell("Parameter", 3120), hdrCell("Value / Unit", 2160), hdrCell("Clinical Context", 4080)] }),
      ...items.map(item => new TableRow({ children: [
        dataCell(item.parameter, 3120, C.threshBg),
        dataCell((safe(item.value) + " " + safe(item.unit)).trim(), 2160),
        dataCell(item.context, 4080)
      ]}))
    ]
  });
}

function recommendationsTable(items) {
  if (!items || !items.length) return null;
  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: [6000, 1680, 1680],
    rows: [
      new TableRow({ tableHeader: true, children: [hdrCell("Recommendation", 6000), hdrCell("Strength", 1680), hdrCell("Evidence", 1680)] }),
      ...items.map(item => new TableRow({ children: [
        dataCell(item.recommendation, 6000, C.recBg),
        dataCell(item.strength, 1680),
        dataCell(item.evidence_level, 1680)
      ]}))
    ]
  });
}

function medicationsTable(items) {
  if (!items || !items.length) return null;
  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: [2520, 2160, 2880, 1800],
    rows: [
      new TableRow({ tableHeader: true, children: [hdrCell("Drug", 2520), hdrCell("Dose", 2160), hdrCell("Indication", 2880), hdrCell("Class", 1800)] }),
      ...items.map(item => new TableRow({ children: [
        dataCell(item.drug, 2520, C.medBg),
        dataCell(item.dose, 2160),
        dataCell(item.indication, 2880),
        dataCell(item.class || item.drug_class || "", 1800)
      ]}))
    ]
  });
}

// REFERENCE BLOCK
function buildRefBlock(row, jdata) {
  const elems = [];
  const ext = jdata.extraction || {};
  const src = jdata.source || {};

  elems.push(citationBlock(row.citation, row.tier));

  const orgYear = [safe(src.organization), safe(src.publication_year)].filter(Boolean).join(" \u00B7 ");
  if (orgYear) elems.push(metaLine(orgYear));

  if (ext.summary) {
    elems.push(sectionLabel("SUMMARY", C.summBg));
    elems.push(bodyPara(ext.summary));
  }

  if (ext.population) {
    const pop = ext.population;
    const lines = [
      pop.disease_definition && "Definition: " + pop.disease_definition,
      pop.age_criteria && "Population: " + pop.age_criteria,
      pop.risk_criteria && "Risk Factors: " + pop.risk_criteria,
      pop.exclusions && "Exclusions: " + pop.exclusions,
      pop.severity_staging && "Staging: " + pop.severity_staging
    ].filter(Boolean);
    if (lines.length) {
      elems.push(sectionLabel("POPULATION", C.popBg));
      lines.forEach(l => elems.push(bulletItem(l)));
    }
  }

  if (ext.key_thresholds && ext.key_thresholds.length) {
    elems.push(sectionLabel("KEY THRESHOLDS", C.threshBg));
    const tbl = thresholdsTable(ext.key_thresholds);
    if (tbl) elems.push(tbl);
  }

  if (ext.recommendations && ext.recommendations.length) {
    elems.push(sectionLabel("RECOMMENDATIONS", C.recBg));
    const tbl = recommendationsTable(ext.recommendations);
    if (tbl) elems.push(tbl);
  }

  if (ext.medications && ext.medications.length) {
    elems.push(sectionLabel("MEDICATIONS", C.medBg));
    const tbl = medicationsTable(ext.medications);
    if (tbl) elems.push(tbl);
  }

  if (ext.red_flags && ext.red_flags.length) {
    elems.push(sectionLabel("RED FLAGS", C.redFlagBg));
    ext.red_flags.forEach(rf => elems.push(bulletItem(rf)));
  }

  const followUp = safe(ext.follow_up);
  const escalation = safe(ext.escalation_path);
  if (followUp || escalation) {
    elems.push(sectionLabel("FOLLOW-UP & ESCALATION", C.followBg));
    if (followUp) elems.push(bodyPara("Follow-up: " + followUp));
    if (escalation) elems.push(bodyPara("Escalation: " + escalation));
  }

  elems.push(divider());
  return elems;
}

// MAIN
log("Parsing crosswalk CSV...");
const rows = parseCSV(CROSSWALK);
const matched = rows.filter(r => r.match_status === "MATCHED");
log("Matched refs: " + matched.length);

// Group by session
const sessionMap = {};
for (const row of matched) {
  const ids = row.session_ids.split("|");
  const titles = row.session_titles.split("|");
  ids.forEach((sid, i) => {
    if (!sessionMap[sid]) sessionMap[sid] = { title: titles[i] || sid, refs: [] };
    sessionMap[sid].refs.push(row);
  });
}
const sortedSessions = Object.keys(sessionMap).sort((a, b) => parseInt(a) - parseInt(b));
log("Sessions with matched refs: " + sortedSessions.length);

// BUILD DOCUMENT
const children = [];

// Cover
children.push(new Paragraph({
  children: [new TextRun({ text: "ABFM Board Prep", bold: true, size: 56, font: "Arial", color: C.sessionHdr })],
  alignment: AlignmentType.CENTER,
  spacing: { before: 1440, after: 240 }
}));
children.push(new Paragraph({
  children: [new TextRun({ text: "Linked References \u2014 Version 2", bold: true, size: 36, font: "Arial", color: "444444" })],
  alignment: AlignmentType.CENTER,
  spacing: { before: 0, after: 240 }
}));
children.push(new Paragraph({
  children: [new TextRun({ text: matched.length + " verified reference\u2013article pairs | " + sortedSessions.length + " AAFP sessions", size: 22, font: "Arial", color: "666666" })],
  alignment: AlignmentType.CENTER,
  spacing: { before: 0, after: 120 }
}));
children.push(new Paragraph({
  children: [new TextRun({ text: "For internal residency use only \u2014 do not distribute", size: 18, font: "Arial", color: "999999", italics: true })],
  alignment: AlignmentType.CENTER,
  spacing: { before: 0, after: 480 }
}));
children.push(new Paragraph({ children: [new PageBreak()] }));

// Sessions
let refCount = 0, failCount = 0;
const tierOrder = { "Must-Read": 0, "Core": 1, "Supplementary": 2, "Unmatched": 3 };

for (const sid of sortedSessions) {
  const sess = sessionMap[sid];
  children.push(sessionHeading("Session " + sid + ": " + sess.title));
  children.push(new Paragraph({
    children: [new TextRun({ text: sess.refs.length + " reference" + (sess.refs.length > 1 ? "s" : "") + " with extracted content", size: 18, font: "Arial", color: "888888", italics: true })],
    spacing: { before: 0, after: 200 }
  }));

  const sortedRefs = [...sess.refs].sort((a, b) => (tierOrder[a.tier] || 9) - (tierOrder[b.tier] || 9));

  for (const row of sortedRefs) {
    const jdata = loadJSON(row.matched_json_path);
    if (!jdata) { failCount++; continue; }
    children.push(...buildRefBlock(row, jdata));
    refCount++;
    log("  [" + row.tier + "] Session " + sid + ": " + row.citation.substring(0, 55));
  }

  if (sid !== sortedSessions[sortedSessions.length - 1]) {
    children.push(new Paragraph({ children: [new PageBreak()] }));
  }
}

log("Building document object...");

const doc = new Document({
  numbering: {
    config: [{
      reference: "bullets",
      levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 600, hanging: 300 } } } }]
    }]
  },
  styles: {
    default: { document: { run: { font: "Arial", size: 20 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: "Arial", color: C.sessionHdr },
        paragraph: { spacing: { before: 360, after: 120 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, font: "Arial", color: "1F3864" },
        paragraph: { spacing: { before: 240, after: 80 }, outlineLevel: 1 } }
    ]
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1080, right: 1080, bottom: 1080, left: 1080 }
      }
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [
            new TextRun({ children: [PageNumber.CURRENT], size: 16, font: "Arial", color: "888888" })
          ]
        })]
      })
    },
    children
  }]
});

log("Packing document...");

Packer.toBuffer(doc).then(function(buf) {
  fs.writeFileSync(OUT_PATH, buf);
  log("DONE — " + refCount + " refs written, " + failCount + " failed");
  log("Output: " + OUT_PATH);
}).catch(function(err) {
  log("PACKER ERROR: " + err.message + "\n" + err.stack);
});
