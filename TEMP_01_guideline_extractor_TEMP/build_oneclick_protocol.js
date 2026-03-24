const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
        HeadingLevel, AlignmentType, BorderStyle, WidthType, ShadingType,
        LevelFormat, PageBreak } = require('docx');
const fs = require('fs');

// ── Colors ──────────────────────────────────────────────────
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

function codeBlock(lines) {
  return lines.map(line =>
    new Paragraph({
      spacing: { before: 20, after: 20 },
      shading: { fill: "F5F5F5", type: ShadingType.CLEAR },
      indent: { left: 360 },
      border: { left: { style: BorderStyle.SINGLE, size: 8, color: BLUE, space: 4 } },
      children: [new TextRun({ text: line, font: "Courier New", size: 18, color: "1E1E1E" })]
    })
  );
}

// ── Document ──────────────────────────────────────────────────
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

      // ══════════════════════════════════════════════════════════
      //  TITLE PAGE
      // ══════════════════════════════════════════════════════════
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 720, after: 120 },
        shading: { fill: NAVY, type: ShadingType.CLEAR },
        children: [new TextRun({ text: "ABFM Board Prep", bold: true, color: WHITE, size: 40, font: "Arial" })]
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 0, after: 120 },
        shading: { fill: NAVY, type: ShadingType.CLEAR },
        children: [new TextRun({ text: "One-Click Summary Pipeline", bold: true, color: AMBER, size: 32, font: "Arial" })]
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 0, after: 600 },
        shading: { fill: NAVY, type: ShadingType.CLEAR },
        children: [new TextRun({ text: "Right-Click Any PDF \u2192 Styled Clinical Summary DOCX", italic: true, color: LBLUE, size: 24, font: "Arial" })]
      }),

      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [3120, 3120, 3120],
        rows: [new TableRow({ children: [
          new TableCell({
            width: { size: 3120, type: WidthType.DXA },
            shading: { fill: LBLUE, type: ShadingType.CLEAR },
            margins: { top: 80, bottom: 80, left: 120, right: 120 },
            borders: BORDERS,
            children: [
              new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Engine", bold: true, color: NAVY, size: 18, font: "Arial" })] }),
              new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "guideline_extractor_v2.3", color: DGRAY, size: 18, font: "Arial" })] })
            ]
          }),
          new TableCell({
            width: { size: 3120, type: WidthType.DXA },
            shading: { fill: LBLUE, type: ShadingType.CLEAR },
            margins: { top: 80, bottom: 80, left: 120, right: 120 },
            borders: BORDERS,
            children: [
              new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Synthesis Model", bold: true, color: NAVY, size: 18, font: "Arial" })] }),
              new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "claude-sonnet-4-6", color: DGRAY, size: 18, font: "Arial" })] })
            ]
          }),
          new TableCell({
            width: { size: 3120, type: WidthType.DXA },
            shading: { fill: LBLUE, type: ShadingType.CLEAR },
            margins: { top: 80, bottom: 80, left: 120, right: 120 },
            borders: BORDERS,
            children: [
              new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Last Updated", bold: true, color: NAVY, size: 18, font: "Arial" })] }),
              new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "2026-03-09", color: DGRAY, size: 18, font: "Arial" })] })
            ]
          })
        ]})]
      }),

      gap(2),
      para("This document covers the standalone one-click pipeline: right-click any clinical guideline PDF anywhere on the system, and a styled clinical summary DOCX appears next to it. The PDF never moves. The output always lands beside the input and is copied to the Desktop.", { color: DGRAY, size: 20 }),
      gap(1),
      new Paragraph({ children: [new PageBreak()] }),

      // ══════════════════════════════════════════════════════════
      //  1. HOW IT WORKS
      // ══════════════════════════════════════════════════════════
      hdr("1. How It Works", 1),
      para("The pipeline chains three stages: Python extraction (reuses the existing Phase 1 engine), Node.js LLM synthesis, and Node.js DOCX generation. A single batch file orchestrates all three."),
      gap(1),

      ...codeBlock([
        "  Right-click any PDF  \u2192  extract_guideline.bat \"%1\"",
        "       |",
        "       v",
        "  [1] Python ingestion     ingest_document(absolute_pdf_path)",
        "       |                   Classifies doc type, runs extraction engine",
        "       |                   Writes _extracted.json to %TEMP%",
        "       v",
        "  [2] synthesize.js        Calls Claude Sonnet (claude-sonnet-4-6, 4k tokens)",
        "       |                   Produces 5-field clinical narrative",
        "       |                   Augments JSON in-place with extraction.synthesis{}",
        "       v",
        "  [3] build_summary.js     Reads augmented JSON",
        "       |                   Generates styled DOCX via docx-js",
        "       v",
        "  _summary.docx            Placed next to original PDF",
        "                           + copied to Desktop",
      ]),

      gap(1),
      para("Single file: extract_guideline.bat processes one PDF and outputs one DOCX.", { color: DGRAY }),
      para("Batch folder: extract_guideline.bat accepts a folder path, loops over all *.pdf files, and reports a success/failure count at the end.", { color: DGRAY }),

      gap(1),
      new Paragraph({ children: [new PageBreak()] }),

      // ══════════════════════════════════════════════════════════
      //  2. PREREQUISITES
      // ══════════════════════════════════════════════════════════
      hdr("2. Prerequisites", 1),

      hdr("API Key", 2),
      para("The pipeline requires an Anthropic API key for both extraction (Python) and synthesis (Node.js). The batch file resolves the key in this order:"),
      bullet("Environment variable: ANTHROPIC_API_KEY (set in current shell)", 0, { bold: true }),
      bullet("Windows User registry: HKCU\\Environment\\ANTHROPIC_API_KEY (persists across sessions, used by context menu)", 0, { bold: true }),
      gap(1),
      para("To set the key permanently (recommended for context menu use):"),
      ...codeBlock([
        "# PowerShell (one-time setup)",
        "[System.Environment]::SetEnvironmentVariable(\"ANTHROPIC_API_KEY\", \"sk-ant-...\", \"User\")",
      ]),

      gap(1),
      hdr("Dependencies", 2),
      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [2200, 3400, 3760],
        rows: [
          new TableRow({ children: [hCell("Dependency", 2200), hCell("Purpose", 3400), hCell("Check", 3760)] }),
          new TableRow({ children: [dCell("Python 3.10+", 2200, LGRAY, true), dCell("PDF extraction engine (Phase 1 core)", 3400), dCell("python --version", 3760)] }),
          new TableRow({ children: [dCell("Node.js 18+", 2200, WHITE, true), dCell("Synthesis + DOCX generation", 3400), dCell("node --version", 3760)] }),
          new TableRow({ children: [dCell("pdfplumber", 2200, LGRAY, true), dCell("PDF text extraction (Python pip)", 3400), dCell("pip show pdfplumber", 3760)] }),
          new TableRow({ children: [dCell("anthropic", 2200, WHITE, true), dCell("Claude API client (Python pip)", 3400), dCell("pip show anthropic", 3760)] }),
          new TableRow({ children: [dCell("docx (npm)", 2200, LGRAY, true), dCell("Word document generation (Node.js)", 3400), dCell("node -e \"require('docx')\"", 3760)] }),
        ]
      }),
      gap(1),
      para("Node modules location: C:\\Users\\mpsch\\Desktop\\claude_knowledge\\node_modules (set via NODE_PATH in the batch file).", { color: DGRAY, size: 18 }),

      gap(1),
      new Paragraph({ children: [new PageBreak()] }),

      // ══════════════════════════════════════════════════════════
      //  3. PIPELINE STEPS IN DETAIL
      // ══════════════════════════════════════════════════════════
      hdr("3. Pipeline Steps", 1),

      // Step 1
      hdr("Step 1 \u2014 Extraction (Python)", 2),
      para("The batch file cd's to the project root internally and calls core.ingestion.ingest_document() with the absolute PDF path. This runs the full Phase 1 pipeline:"),
      bullet("Preprocessing: pdfplumber text extraction (or ZIP/plaintext fallback)"),
      bullet("Classification: LLM classifier determines document type (chronic, acute, preventive, diagnostic, RCT)"),
      bullet("Routing: Selects the appropriate extraction engine for the document type"),
      bullet("Extraction: LLM-driven structured extraction (auto-chunks documents >15k chars)"),
      bullet("Metadata: Title, organization, year, DOI from first 2,000 chars"),
      bullet("Validation: field_coverage_score computed"),
      gap(1),
      para("Output: _extracted.json written to %TEMP% directory (cleaned up after DOCX generation)."),

      gap(1),

      // Step 2
      hdr("Step 2 \u2014 Synthesis (synthesize.js)", 2),
      para("Calls Claude Sonnet to transform the raw extraction data into clinician-focused narrative. Augments the JSON in-place by adding an extraction.synthesis{} block. If synthesis fails (API error, timeout), the pipeline continues with raw data only \u2014 non-fatal."),
      gap(1),
      para("Model: claude-sonnet-4-6  |  Max tokens: 4,000", { bold: true, color: DGRAY }),
      gap(1),

      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [2800, 6560],
        rows: [
          new TableRow({ children: [hCell("Synthesis Field", 2800), hCell("Description", 6560)] }),
          new TableRow({ children: [dCell("clinical_bottom_line", 2800, LGRAY, true), dCell("2-3 paragraph narrative: what's NEW, DIFFERENT, or commonly missed in daily practice", 6560)] }),
          new TableRow({ children: [dCell("practice_pearls", 2800, WHITE, true), dCell("3-5 concise, actionable takeaways starting with action verbs", 6560)] }),
          new TableRow({ children: [dCell("medication_groups", 2800, LGRAY, true), dCell("Medications grouped by clinical indication with narrative context and drug lists", 6560)] }),
          new TableRow({ children: [dCell("critical_alerts", 2800, WHITE, true), dCell("5-8 red flags with 'why it matters' and immediate actions needed", 6560)] }),
          new TableRow({ children: [dCell("definitions_and_thresholds", 2800, LGRAY, true), dCell("High-yield definitions and diagnostic thresholds that change management (deduped against medications)", 6560)] }),
        ]
      }),

      gap(1),

      // Step 3
      hdr("Step 3 \u2014 DOCX Generation (build_summary.js)", 2),
      para("Reads the augmented JSON and generates a styled Word document using the docx-js library. Each section is only rendered if the data exists. The document uses the same color palette as the main extraction protocol."),
      gap(1),

      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [600, 2800, 5960],
        rows: [
          new TableRow({ children: [hCell("#", 600), hCell("Section", 2800), hCell("Content", 5960)] }),
          new TableRow({ children: [dCell("1", 600, LGRAY, true), dCell("Title Banner", 2800, LGRAY, true), dCell("Navy fill, white text: guideline title, org | year | DOI", 5960)] }),
          new TableRow({ children: [dCell("2", 600, WHITE, true), dCell("Classification Badge", 2800, WHITE, true), dCell("Document type, engine used, confidence %, body systems", 5960)] }),
          new TableRow({ children: [dCell("3", 600, LGRAY, true), dCell("Clinical Summary", 2800, LGRAY, true), dCell("Extraction summary + synthesis bottom-line narrative (merged view)", 5960)] }),
          new TableRow({ children: [dCell("4", 600, WHITE, true), dCell("Key Practice Changes", 2800, WHITE, true), dCell("Teal banner + bullet list from practice_pearls", 5960)] }),
          new TableRow({ children: [dCell("5", 600, LGRAY, true), dCell("Target Population", 2800, LGRAY, true), dCell("2-col table: age, risk, disease definition, exclusions, severity", 5960)] }),
          new TableRow({ children: [dCell("6", 600, WHITE, true), dCell("Definitions & Thresholds", 2800, WHITE, true), dCell("2-col table: term + definition (deduped against medication list)", 5960)] }),
          new TableRow({ children: [dCell("7", 600, LGRAY, true), dCell("Clinical Recommendations", 2800, LGRAY, true), dCell("4-col table, color-coded by strength: Strong/High = teal, Conditional = amber", 5960)] }),
          new TableRow({ children: [dCell("8", 600, WHITE, true), dCell("Medications", 2800, WHITE, true), dCell("Grouped by indication with narrative (synthesis) or flat 4-col table (fallback)", 5960)] }),
          new TableRow({ children: [dCell("9", 600, LGRAY, true), dCell("Red Flags & Critical Alerts", 2800, LGRAY, true), dCell("Red banner + alert/why-it-matters pairs, or flat bullet list without synthesis", 5960)] }),
          new TableRow({ children: [dCell("10", 600, WHITE, true), dCell("Follow-Up & Monitoring", 2800, WHITE, true), dCell("Paragraph text from extraction", 5960)] }),
          new TableRow({ children: [dCell("11", 600, LGRAY, true), dCell("Footer", 2800, LGRAY, true), dCell("Extraction timestamp, engine version, validation status, coverage score", 5960)] }),
        ]
      }),
      gap(1),
      para("Color palette: Navy (#1F3864), Blue (#2E75B6), Light Blue (#D6E4F7), Teal (#E2EFDA), Amber (#FFF2CC), Red (#C00000). Recommendations and definitions tables use tableHeader: true for repeating headers across pages and cantSplit: false for proper page-break handling.", { color: DGRAY, size: 18 }),

      gap(1),

      // Step 4
      hdr("Step 4 \u2014 Output", 2),
      para("The finished _summary.docx is written next to the original PDF, then copied to the Desktop for easy access. The temp JSON in %TEMP% is deleted."),
      gap(1),
      ...codeBlock([
        "# Example: input is C:\\Users\\mpsch\\Downloads\\sepsis_2024.pdf",
        "#",
        "# Output 1:  C:\\Users\\mpsch\\Downloads\\sepsis_2024_summary.docx  (next to PDF)",
        "# Output 2:  C:\\Users\\mpsch\\Desktop\\sepsis_2024_summary.docx    (Desktop copy)",
      ]),

      gap(1),
      new Paragraph({ children: [new PageBreak()] }),

      // ══════════════════════════════════════════════════════════
      //  4. INSTALLATION & USAGE
      // ══════════════════════════════════════════════════════════
      hdr("4. Installation & Usage", 1),

      hdr("Install Context Menu", 2),
      para("Run the registry file to add right-click entries (HKCU \u2014 no admin rights required). On Windows 11, entries appear under 'Show more options'."),
      gap(1),
      ...codeBlock([
        "# Install (double-click or run from cmd)",
        "regedit /s oneclick\\install_context_menu.reg",
        "",
        "# This adds two entries:",
        "#   - Right-click any .pdf  \u2192  \"Extract Guideline\"",
        "#   - Right-click any folder \u2192  \"Extract All Guidelines\"",
      ]),
      gap(1),
      para("To remove:"),
      ...codeBlock([
        "regedit /s oneclick\\uninstall_context_menu.reg",
      ]),

      gap(2),

      hdr("Usage \u2014 Single PDF", 2),
      para("Right-click any PDF file \u2192 Show more options \u2192 'Extract Guideline'. A console window will show progress through all 4 steps. The summary DOCX appears on your Desktop when done."),
      gap(1),
      para("Or from the command line:"),
      ...codeBlock([
        "oneclick\\extract_guideline.bat \"C:\\Users\\mpsch\\Downloads\\some_guideline.pdf\"",
      ]),

      gap(1),

      hdr("Usage \u2014 Batch Folder", 2),
      para("Right-click any folder \u2192 Show more options \u2192 'Extract All Guidelines'. Processes every *.pdf in the folder. Reports success/failure count at the end."),
      gap(1),
      ...codeBlock([
        "oneclick\\extract_guideline.bat \"C:\\Users\\mpsch\\Downloads\\guidelines_folder\"",
      ]),

      gap(1),

      hdr("Manual Test (No API Call)", 2),
      para("To test the DOCX generator without running extraction or synthesis, use an existing JSON:"),
      ...codeBlock([
        "# Test DOCX builder only (uses pre-existing extraction JSON)",
        "set NODE_PATH=C:\\Users\\mpsch\\Desktop\\claude_knowledge\\node_modules",
        "node oneclick\\build_summary.js outputs\\gold_list_v23_baseline\\1_extracted.json C:\\Users\\mpsch\\Desktop\\test.docx",
      ]),

      gap(1),
      new Paragraph({ children: [new PageBreak()] }),

      // ══════════════════════════════════════════════════════════
      //  5. FILE REFERENCE
      // ══════════════════════════════════════════════════════════
      hdr("5. File Reference", 1),
      para("All files live in guideline_extractor_v2/oneclick/:"),
      gap(1),

      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [2800, 6560],
        rows: [
          new TableRow({ children: [hCell("File", 2800), hCell("Purpose", 6560)] }),
          new TableRow({ children: [
            dCell("extract_guideline.bat", 2800, LGRAY, true),
            dCell("Orchestrator: accepts any PDF path or folder, cd's to project root internally, chains Python extraction \u2192 Node.js synthesis \u2192 Node.js DOCX generation. Handles API key resolution from env var or HKCU registry.", 6560)
          ]}),
          new TableRow({ children: [
            dCell("synthesize.js", 2800, WHITE, true),
            dCell("LLM synthesis layer: calls Claude Sonnet (claude-sonnet-4-6, 4k max tokens) to produce 5-field clinical narrative. Augments extraction JSON in-place. Non-fatal on failure.", 6560)
          ]}),
          new TableRow({ children: [
            dCell("build_summary.js", 2800, LGRAY, true),
            dCell("DOCX generator: reads augmented JSON, produces styled 11-section summary via docx-js library. Uses synthesis data when available, falls back to raw extraction data.", 6560)
          ]}),
          new TableRow({ children: [
            dCell("install_context_menu.reg", 2800, WHITE, true),
            dCell("Windows registry entries (HKCU): adds 'Extract Guideline' to PDF right-click and 'Extract All Guidelines' to folder right-click. No admin required.", 6560)
          ]}),
          new TableRow({ children: [
            dCell("uninstall_context_menu.reg", 2800, LGRAY, true),
            dCell("Removes both context menu entries from the registry.", 6560)
          ]}),
        ]
      }),

      gap(2),

      hdr("Key Configuration", 2),
      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [2800, 3000, 3560],
        rows: [
          new TableRow({ children: [hCell("Setting", 2800), hCell("Value", 3000), hCell("Where", 3560)] }),
          new TableRow({ children: [dCell("PROJECT_ROOT", 2800, LGRAY, true), dCell("..\\  (parent of oneclick/)", 3000), dCell("extract_guideline.bat line 13", 3560)] }),
          new TableRow({ children: [dCell("NODE_PATH", 2800, WHITE, true), dCell("C:\\...\\claude_knowledge\\node_modules", 3000), dCell("extract_guideline.bat line 14", 3560)] }),
          new TableRow({ children: [dCell("NODE_OPTIONS", 2800, LGRAY, true), dCell("--no-warnings", 3000), dCell("extract_guideline.bat line 16", 3560)] }),
          new TableRow({ children: [dCell("MODEL", 2800, WHITE, true), dCell("claude-sonnet-4-6", 3000), dCell("synthesize.js line 21", 3560)] }),
          new TableRow({ children: [dCell("MAX_TOKENS", 2800, LGRAY, true), dCell("4000", 3000), dCell("synthesize.js line 22", 3560)] }),
        ]
      }),

      gap(3),
      hr(),
      para("ABFM Board Prep Project \u2014 Internal Use Only \u2014 Do Not Distribute", { color: DGRAY, size: 16, center: true }),
      para("Updated 2026-03-09 | guideline_extractor_v2.3 | oneclick v1.0", { color: DGRAY, size: 16, center: true }),

    ]
  }]
});

const outPath = process.argv[2] || 'OneClick_Summary_Protocol.docx';
Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync(outPath, buf);
  console.log('Written: ' + outPath);
});
