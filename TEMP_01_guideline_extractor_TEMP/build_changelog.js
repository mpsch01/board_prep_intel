const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
        HeadingLevel, AlignmentType, BorderStyle, WidthType, ShadingType,
        LevelFormat, PageBreak } = require('docx');
const fs = require('fs');

const NAVY   = "1F3864";
const BLUE   = "2E75B6";
const LBLUE  = "D6E4F7";
const WHITE  = "FFFFFF";
const LGRAY  = "F2F2F2";
const DGRAY  = "595959";
const AMBER  = "FFF2CC";
const TEAL   = "E2EFDA";
const BORDER = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const BORDERS = { top: BORDER, bottom: BORDER, left: BORDER, right: BORDER };

function hdr(text, level=1) {
  return new Paragraph({
    heading: level === 1 ? HeadingLevel.HEADING_1 : level === 2 ? HeadingLevel.HEADING_2 : HeadingLevel.HEADING_3,
    spacing: { before: level === 1 ? 360 : 240, after: 120 },
    children: [new TextRun({ text, bold: true,
      color: level === 1 ? NAVY : level === 2 ? BLUE : DGRAY,
      size: level === 1 ? 28 : level === 2 ? 24 : 22 })]
  });
}

function para(text, opts={}) {
  const { bold=false, italic=false, color="000000", size=22, indent=0,
          spaceBefore=60, spaceAfter=60, center=false } = opts;
  return new Paragraph({
    alignment: center ? AlignmentType.CENTER : AlignmentType.LEFT,
    indent: indent ? { left: indent } : undefined,
    spacing: { before: spaceBefore, after: spaceAfter },
    children: [new TextRun({ text, bold, italic, color, size, font: "Arial" })]
  });
}

function bullet(text, level=0, opts={}) {
  const { bold=false, color="000000" } = opts;
  return new Paragraph({
    numbering: { reference: "bullets", level },
    spacing: { before: 40, after: 40 },
    children: [new TextRun({ text, bold, color, size: 20, font: "Arial" })]
  });
}

function gap(n=1) {
  return new Paragraph({ spacing: { before: n*60, after: n*60 }, children: [] });
}

function hr() {
  return new Paragraph({
    spacing: { before: 120, after: 120 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: BLUE, space: 1 } },
    children: []
  });
}

function hCell(text, width, fill=NAVY) {
  return new TableCell({
    width: { size: width, type: WidthType.DXA },
    shading: { fill, type: ShadingType.CLEAR },
    margins: { top: 80, bottom: 80, left: 120, right: 120 },
    borders: BORDERS,
    children: [new Paragraph({
      children: [new TextRun({ text, bold: true, color: WHITE, size: 18, font: "Arial" })]
    })]
  });
}

function dCell(text, width, fill=WHITE, bold=false, color="000000") {
  return new TableCell({
    width: { size: width, type: WidthType.DXA },
    shading: { fill, type: ShadingType.CLEAR },
    margins: { top: 80, bottom: 80, left: 120, right: 120 },
    borders: BORDERS,
    children: [new Paragraph({
      children: [new TextRun({ text, bold, color, size: 18, font: "Arial" })]
    })]
  });
}

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
        paragraph: { spacing: { before: 180, after: 80 }, outlineLevel: 2 } },
    ]
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1080, right: 1080, bottom: 1080, left: 1080 }
      }
    },
    children: [

      // ── TITLE ──
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 480, after: 120 },
        shading: { fill: NAVY, type: ShadingType.CLEAR },
        children: [new TextRun({ text: "Guideline Extraction Protocol", bold: true, color: WHITE, size: 36, font: "Arial" })]
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 0, after: 360 },
        shading: { fill: NAVY, type: ShadingType.CLEAR },
        children: [new TextRun({ text: "Change Log: v2 \u2192 v3", bold: true, color: AMBER, size: 28, font: "Arial" })]
      }),

      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [4680, 4680],
        rows: [new TableRow({ children: [
          new TableCell({
            width: { size: 4680, type: WidthType.DXA },
            shading: { fill: LBLUE, type: ShadingType.CLEAR },
            margins: { top: 80, bottom: 80, left: 120, right: 120 },
            borders: BORDERS,
            children: [
              new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Date", bold: true, color: NAVY, size: 18, font: "Arial" })] }),
              new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "2026-03-09", color: DGRAY, size: 18, font: "Arial" })] })
            ]
          }),
          new TableCell({
            width: { size: 4680, type: WidthType.DXA },
            shading: { fill: LBLUE, type: ShadingType.CLEAR },
            margins: { top: 80, bottom: 80, left: 120, right: 120 },
            borders: BORDERS,
            children: [
              new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Files", bold: true, color: NAVY, size: 18, font: "Arial" })] }),
              new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "build_protocol_v3.js  |  Protocol_v3.docx", color: DGRAY, size: 18, font: "Arial" })] })
            ]
          })
        ]})]
      }),

      gap(2),
      para("This document summarizes all changes between v2 and v3 of the ABFM Guideline Extraction Protocol. The primary addition is Phase 3: the one-click summary pipeline that generates standalone clinical summary DOCX files from any PDF via right-click context menu.", { color: DGRAY, size: 20 }),

      gap(1),
      hr(),

      // ── SUMMARY OF CHANGES ──
      hdr("Summary of Changes", 1),
      gap(1),

      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [2400, 3600, 3360],
        rows: [
          new TableRow({ children: [hCell("Area", 2400), hCell("Change", 3600), hCell("Impact", 3360)] }),
          new TableRow({ children: [
            dCell("New Section 7", 2400, AMBER, true, NAVY),
            dCell("Phase 3: One-Click Summary Pipeline", 3600, AMBER),
            dCell("Entire new section documenting the standalone summary workflow", 3360, AMBER)
          ]}),
          new TableRow({ children: [
            dCell("Section 1", 2400, LGRAY, true),
            dCell("Phase table expanded from 2 to 3 phases", 3600),
            dCell("Phase 3 row added (amber)", 3360)
          ]}),
          new TableRow({ children: [
            dCell("Section 1", 2400, WHITE, true),
            dCell("Architecture diagram updated", 3600),
            dCell("Phase 2 + Phase 3 branch paths shown", 3360)
          ]}),
          new TableRow({ children: [
            dCell("Section 1", 2400, LGRAY, true),
            dCell("API key resolution updated", 3600),
            dCell("Added HKCU\\Environment registry as resolution step", 3360)
          ]}),
          new TableRow({ children: [
            dCell("Section 1", 2400, WHITE, true),
            dCell("Model reference updated", 3600),
            dCell("claude-sonnet-4-6 (was claude-sonnet-4-20250514)", 3360)
          ]}),
          new TableRow({ children: [
            dCell("Section 2", 2400, LGRAY, true),
            dCell("JSON Schema table updated", 3600),
            dCell("extraction block now includes synthesis{} sub-object", 3360)
          ]}),
          new TableRow({ children: [
            dCell("Sections 7-8", 2400, WHITE, true),
            dCell("Renumbered to 8-9", 3600),
            dCell("Shifted to accommodate new Section 7", 3360)
          ]}),
          new TableRow({ children: [
            dCell("Section 8 (was 7)", 2400, LGRAY, true),
            dCell("API Key resolution expanded", 3600),
            dCell("HKCU registry step documented for context menu use", 3360)
          ]}),
          new TableRow({ children: [
            dCell("Section 9 (was 8)", 2400, WHITE, true),
            dCell("Quick Reference table expanded", 3600),
            dCell("3 new oneclick scripts added (amber-highlighted rows)", 3360)
          ]}),
          new TableRow({ children: [
            dCell("Title page", 2400, LGRAY, true),
            dCell("Subtitle updated", 3600),
            dCell("Now includes 'Synthesis' and 'Summary DOCX' in pipeline description", 3360)
          ]}),
          new TableRow({ children: [
            dCell("Footer", 2400, WHITE, true),
            dCell("Version tag added", 3600),
            dCell("'oneclick v1.0' appended to footer line", 3360)
          ]}),
          new TableRow({ children: [
            dCell("Dates", 2400, LGRAY, true),
            dCell("Updated to 2026-03-09", 3600),
            dCell("Title page and Completed Batches header", 3360)
          ]}),
        ]
      }),

      gap(1),
      new Paragraph({ children: [new PageBreak()] }),

      // ── DETAILED CHANGES ──
      hdr("Detailed Changes", 1),

      hdr("NEW: Section 7 \u2014 Phase 3: One-Click Summary Pipeline", 2),
      para("This is the largest addition. Section 7 documents the complete standalone summary workflow:"),
      gap(1),

      bullet("Architecture: Flow diagram showing right-click \u2192 bat file \u2192 Python ingestion \u2192 Node.js synthesis \u2192 DOCX generation"),
      bullet("Synthesis Layer: Table documenting all 5 synthesis fields (clinical_bottom_line, practice_pearls, medication_groups, critical_alerts, definitions_and_thresholds)"),
      bullet("Summary DOCX Layout: 11-section table showing the complete document structure from Title Banner through Footer"),
      bullet("Context Menu Installation: Registry-based installation instructions (HKCU, no admin required)"),
      bullet("File Reference: Table of all 5 files in the oneclick/ directory with their purposes"),
      gap(1),

      hdr("New Files (oneclick/ directory)", 2),
      para("Five new files were created to support the one-click workflow:"),
      gap(1),

      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [3000, 3360, 3000],
        rows: [
          new TableRow({ children: [hCell("File", 3000), hCell("Purpose", 3360), hCell("Size", 3000)] }),
          new TableRow({ children: [dCell("extract_guideline.bat", 3000, LGRAY, true), dCell("Orchestrator batch script", 3360), dCell("145 lines", 3000)] }),
          new TableRow({ children: [dCell("synthesize.js", 3000, WHITE, true), dCell("Claude Sonnet narrative synthesis", 3360), dCell("161 lines", 3000)] }),
          new TableRow({ children: [dCell("build_summary.js", 3000, LGRAY, true), dCell("DOCX generation via docx-js", 3360), dCell("596 lines", 3000)] }),
          new TableRow({ children: [dCell("install_context_menu.reg", 3000, WHITE, true), dCell("Windows registry entries for right-click", 3360), dCell("18 lines", 3000)] }),
          new TableRow({ children: [dCell("uninstall_context_menu.reg", 3000, LGRAY, true), dCell("Registry cleanup", 3360), dCell("6 lines", 3000)] }),
        ]
      }),

      gap(1),

      hdr("Modified Sections", 2),

      hdr("Section 1: Pipeline Overview", 3),
      bullet("Phase table: Added Phase 3 row (amber background): 'PDF \u2192 Standalone Summary DOCX (one-click)' with scripts extract_guideline.bat, synthesize.js, build_summary.js"),
      bullet("Pipeline description: Changed from 'two major phases' to 'three major phases'"),
      bullet("Architecture diagram: Added two branch paths at bottom showing Phase 2 (migrate_to_unified.py) and Phase 3 (synthesize.js \u2192 build_summary.js) as parallel outputs from _extracted.json"),
      bullet("API key text: Added 'HKCU\\Environment registry' as resolution step (2) between env var and config.json"),
      bullet("Model reference: Updated to 'claude-sonnet-4-6' (was 'claude-sonnet-4-20250514')"),
      gap(1),

      hdr("Section 2: JSON Schema Table", 3),
      bullet("extraction block 'Source' column: Changed from 'LLM engine' to 'LLM engine + synthesis'"),
      bullet("extraction block 'Key Fields' column: Added 'synthesis{}' to the field list"),
      gap(1),

      hdr("Sections 7-8 \u2192 8-9 (Renumbered)", 3),
      bullet("'7. Critical Rules & Common Pitfalls' became '8. Critical Rules & Common Pitfalls'"),
      bullet("'8. Quick Reference \u2014 All Key Scripts' became '9. Quick Reference \u2014 All Key Scripts'"),
      bullet("No content changes to these sections other than renumbering and the additions noted below"),
      gap(1),

      hdr("Section 8 (was 7): API Key", 3),
      bullet("Added '(2) HKCU\\Environment registry (used by context menu launcher)' to resolution order"),
      gap(1),

      hdr("Section 9 (was 8): Quick Reference", 3),
      bullet("Added 3 new rows at bottom of script table (amber-highlighted):"),
      bullet("extract_guideline.bat \u2014 'One-click orchestrator: right-click any PDF \u2192 summary DOCX' \u2014 oneclick/", 1),
      bullet("synthesize.js \u2014 'LLM synthesis: 5-field clinical narrative via Claude Sonnet' \u2014 oneclick/", 1),
      bullet("build_summary.js \u2014 'DOCX generator: styled 11-section summary from augmented JSON' \u2014 oneclick/", 1),
      bullet("Completed Batches header date: Updated to '2026-03-09' (was '2026-03-08')"),
      gap(1),

      hdr("Cosmetic Updates", 3),
      bullet("Title page subtitle: 'PDF \u2192 JSON \u2192 Word Document Pipeline' became 'PDF \u2192 JSON \u2192 Synthesis \u2192 Summary DOCX Pipeline'"),
      bullet("Title page description: Added 'clinical narrative synthesis, and styled summary document generation'"),
      bullet("Footer: Appended 'oneclick v1.0' to version line"),
      bullet("All dates: Updated to 2026-03-09"),

      gap(2),
      hr(),

      // ── UNCHANGED ──
      hdr("Sections Unchanged", 1),
      para("The following sections carry over from v2 with no modifications:"),
      gap(1),
      bullet("Section 2: Phase 1 extraction steps 1-6 (preprocess through validation)"),
      bullet("Section 3: Running the Extraction (CLI usage, test run protocol, batch monitoring)"),
      bullet("Section 4: Calibration (quality dimensions, running calibration)"),
      bullet("Section 5: Migration to Canonical Destination"),
      bullet("Section 6: Phase 2 Word Document Injection (question matching, Word injection, callout design)"),
      bullet("Completed Batches table: Data unchanged, only header date updated"),

      gap(3),
      hr(),
      para("ABFM Board Prep Project \u2014 Internal Use Only \u2014 Do Not Distribute", { color: DGRAY, size: 16, center: true }),

    ]
  }]
});

const outPath = process.argv[2] || 'Protocol_ChangeLog_v2_to_v3.docx';
Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync(outPath, buf);
  console.log('Written: ' + outPath);
});
