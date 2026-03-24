const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
        HeadingLevel, AlignmentType, BorderStyle, WidthType, ShadingType,
        LevelFormat, PageNumber, PageBreak } = require('docx');
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

// ── Helpers ──────────────────────────────────────────────────
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

function numbered(text, level=0, opts={}) {
  const { bold=false } = opts;
  return new Paragraph({
    numbering: { reference: "numbers", level },
    spacing: { before: 40, after: 40 },
    children: [new TextRun({ text, bold, size: 20, font: "Arial" })]
  });
}

function hr() {
  return new Paragraph({
    spacing: { before: 120, after: 120 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: BLUE, space: 1 } },
    children: []
  });
}

function gap(n=1) {
  return new Paragraph({ spacing: { before: n*60, after: n*60 }, children: [] });
}

function hCell(text, width, fill=NAVY) {
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

function stageBox(num, label, description, fill=LBLUE, textColor=NAVY) {
  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: [720, 2200, 6440],
    rows: [new TableRow({ children: [
      new TableCell({
        width: { size: 720, type: WidthType.DXA },
        shading: { fill: BLUE, type: ShadingType.CLEAR },
        margins: { top: 80, bottom: 80, left: 120, right: 120 },
        borders: BORDERS,
        verticalAlign: "center",
        children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [new TextRun({ text: num, bold: true, color: WHITE, size: 28, font: "Arial" })]
        })]
      }),
      new TableCell({
        width: { size: 2200, type: WidthType.DXA },
        shading: { fill: NAVY, type: ShadingType.CLEAR },
        margins: { top: 80, bottom: 80, left: 120, right: 120 },
        borders: BORDERS,
        children: [new Paragraph({
          children: [new TextRun({ text: label, bold: true, color: WHITE, size: 20, font: "Arial" })]
        })]
      }),
      new TableCell({
        width: { size: 6440, type: WidthType.DXA },
        shading: { fill, type: ShadingType.CLEAR },
        margins: { top: 80, bottom: 80, left: 180, right: 120 },
        borders: BORDERS,
        children: [new Paragraph({
          children: [new TextRun({ text: description, size: 18, color: textColor, font: "Arial" })]
        })]
      })
    ]})]
  });
}

// ── Document ──────────────────────────────────────────────────
const doc = new Document({
  numbering: {
    config: [
      { reference: "bullets",
        levels: [
          { level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 540, hanging: 270 } } } },
          { level: 1, format: LevelFormat.BULLET, text: "\u25E6", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 900, hanging: 270 } } } }
        ]
      },
      { reference: "numbers",
        levels: [
          { level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 540, hanging: 270 } } } }
        ]
      }
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

      // ── TITLE PAGE ───────────────────────────────────────────
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
        children: [new TextRun({ text: "Guideline Extraction Protocol", bold: true, color: AMBER, size: 32, font: "Arial" })]
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 0, after: 600 },
        shading: { fill: NAVY, type: ShadingType.CLEAR },
        children: [new TextRun({ text: "PDF \u2192 JSON \u2192 Synthesis \u2192 Summary DOCX Pipeline", italic: true, color: LBLUE, size: 24, font: "Arial" })]
      }),

      // Metadata row
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
              new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Calibration Quality", bold: true, color: NAVY, size: 18, font: "Arial" })] }),
              new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "0.958 overall score", color: DGRAY, size: 18, font: "Arial" })] })
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
      para("This document is the authoritative reference for the guideline extraction protocol used in the ABFM Board Prep project. It covers every step from raw PDF acquisition through structured JSON extraction, clinical narrative synthesis, and styled summary document generation. For library matching, see the separate matching protocol.", { color: DGRAY, size: 20 }),
      gap(1),
      new Paragraph({ children: [new PageBreak()] }),

      // ── SECTION 1: OVERVIEW ──────────────────────────────────
      hdr("1. Pipeline Overview", 1),
      para("The extraction pipeline converts clinical guideline PDFs into structured JSON and ultimately produces high-yield content for the resident curriculum. The pipeline has three major phases:"),
      gap(1),

      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [1800, 3780, 3780],
        rows: [
          new TableRow({ children: [
            hCell("Phase", 1800), hCell("Input \u2192 Output", 3780), hCell("Key Scripts", 3780)
          ]}),
          new TableRow({ children: [
            dCell("Phase 1", 1800, LBLUE, true, NAVY),
            dCell("PDF \u2192 Structured JSON", 3780, WHITE),
            dCell("main.py, calibration.py, migrate_to_unified.py", 3780, WHITE)
          ]}),
          new TableRow({ children: [
            dCell("Phase 2", 1800, TEAL, true, "1C5C1C"),
            dCell("JSON \u2192 Word Doc (via session inserts)", 3780, WHITE),
            dCell("E_v4_question_driven.py, 03_inject_into_outline_v3.py", 3780, WHITE)
          ]}),
          new TableRow({ children: [
            dCell("Phase 3", 1800, AMBER, true, NAVY),
            dCell("PDF \u2192 Standalone Summary DOCX (one-click)", 3780, WHITE),
            dCell("extract_guideline.bat, synthesize.js, build_summary.js", 3780, WHITE)
          ]})
        ]
      }),

      gap(2),
      para("The pipeline uses the Anthropic Claude API (claude-sonnet-4-6) for document classification, content extraction, and clinical narrative synthesis. API key is resolved from: (1) ANTHROPIC_API_KEY environment variable, (2) HKCU\\Environment registry, (3) config.json at the project root."),
      gap(1),

      // Architecture diagram as table
      hdr("Pipeline Architecture", 2),
      ...codeBlock([
        "  PDF FILE(S)",
        "      |",
        "      v",
        "  [1] preprocess.py        -- Extract text (pdfplumber / ZIP / plaintext auto-detect)",
        "      |",
        "      v",
        "  [2] screening.py         -- LLM classifier: RCT / chronic / acute / preventive / diagnostic",
        "      |",
        "      v",
        "  [3] routing.py           -- Select engine based on document_type",
        "      |",
        "      v",
        "  [4] <engine>.extract()   -- LLM extraction via prompt_builder.py (chunked if >15k chars)",
        "      |",
        "      v",
        "  [5] prompt_builder.py    -- extract_metadata() : title, org, year, DOI",
        "      |",
        "      v",
        "  [6] validator.py         -- validation_passed, field_coverage_score",
        "      |",
        "      v",
        "  [7] logger.py            -- Run log to logs/run_<timestamp>_<id>.json",
        "      |",
        "      v",
        "  _extracted.json          -- unified_v1.0 schema output",
        "      |",
        "      +--- Phase 2 --->  migrate_to_unified.py --> ite_refs/ingested/json/",
        "      |",
        "      +--- Phase 3 --->  synthesize.js --> build_summary.js --> _summary.docx",
      ]),

      gap(1),
      new Paragraph({ children: [new PageBreak()] }),

      // ── SECTION 2: PHASE 1 — PDF EXTRACTION ──────────────────
      hdr("2. Phase 1: PDF \u2192 JSON Extraction", 1),
      para("Phase 1 converts raw clinical guideline PDFs into structured JSON files conforming to the unified_v1.0 schema. All scripts run from the guideline_extractor_v2/ project root on Windows 11."),
      gap(1),

      // Step 1
      hdr("Step 1 \u2014 Preprocessing (preprocess.py)", 2),
      para("Handles all input formats via magic byte detection before attempting extension-based parsing:"),
      bullet("True PDF binary (%PDF header): pdfplumber page-by-page extraction, pages joined with double newlines"),
      bullet("ZIP bundle (PK header): Ordered .txt file extraction from JACC/NEJM project files"),
      bullet("Plain text fallback: UTF-8 read for .txt, .md, or text-disguised-as-.pdf files"),
      gap(1),
      para("Text cleaning removes control characters and normalizes whitespace. The first 5,000 chars are forwarded to the screening classifier.", { color: DGRAY }),

      // Step 2
      hdr("Step 2 \u2014 Screening Classifier (screening.py)", 2),
      para("Classifies the document into one of five types via an LLM call. A fast heuristic pre-screen catches RCTs from NEJM/Lancet/JAMA before invoking the LLM (avoids 'unknown' misclassification from column-fragmented PDF text)."),
      gap(1),

      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [2200, 4560, 2600],
        rows: [
          new TableRow({ children: [hCell("Document Type", 2200), hCell("Key Signals", 4560), hCell("Example Sources", 2600)] }),
          new TableRow({ children: [dCell("chronic_guideline", 2200, LGRAY, true), dCell("Stepwise therapy, medication titration, long-term monitoring, risk stratification", 4560), dCell("JACC HTN, COPD GOLD, ADA diabetes", 2600)] }),
          new TableRow({ children: [dCell("acute_protocol", 2200, WHITE, true), dCell("Treatment windows, inpatient stabilization, antibiotic selection, severity triage", 4560), dCell("IDSA CAP, sepsis bundles, croup", 2600)] }),
          new TableRow({ children: [dCell("preventive_guideline", 2200, LGRAY, true), dCell("Screening intervals, USPSTF grades, age/risk eligibility, chemoprophylaxis", 4560), dCell("USPSTF aspirin, statin primary prevention", 2600)] }),
          new TableRow({ children: [dCell("diagnostic_guideline", 2200, WHITE, true), dCell("Diagnostic criteria, test thresholds, workup algorithms, result interpretation", 4560), dCell("Thyroid nodule workup, chest pain algorithm", 2600)] }),
          new TableRow({ children: [dCell("rct", 2200, LGRAY, true), dCell("Methods/randomization, hazard ratios, p-values, Kaplan-Meier, ITT analysis", 4560), dCell("NEJMoa2000052, COMPASS trial", 2600)] }),
        ]
      }),

      gap(1),

      // Step 3
      hdr("Step 3 \u2014 Engine Routing (routing.py)", 2),
      para("Routes the classified document to the appropriate extraction engine. Each engine carries type-specific extraction prompts calibrated for that document class. The engine_map falls back to ChronicRiskEngine for 'unknown' classifications."),
      gap(1),

      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [2800, 3000, 3560],
        rows: [
          new TableRow({ children: [hCell("Engine Class", 2800), hCell("Handles", 3000), hCell("Prompt Focus", 3560)] }),
          new TableRow({ children: [dCell("ChronicRiskEngine", 2800, LGRAY), dCell("chronic_guideline, unknown", 3000), dCell("Stepwise therapy, medication titration, monitoring schedules", 3560)] }),
          new TableRow({ children: [dCell("AcuteProtocolEngine", 2800, WHITE), dCell("acute_protocol", 3000), dCell("Time-sensitive treatment, antibiotic regimens, disposition", 3560)] }),
          new TableRow({ children: [dCell("PreventiveEngine", 2800, LGRAY), dCell("preventive_guideline", 3000), dCell("Screening ages/intervals, USPSTF grades, eligibility criteria", 3560)] }),
          new TableRow({ children: [dCell("DiagnosticEngine", 2800, WHITE), dCell("diagnostic_guideline", 3000), dCell("Test thresholds, workup algorithms, referral indications", 3560)] }),
          new TableRow({ children: [dCell("RCTEngine", 2800, LGRAY), dCell("rct", 3000), dCell("Trial arms, primary endpoints, HR/CI/p-values, clinical implications", 3560)] }),
        ]
      }),

      gap(1),

      // Step 4
      hdr("Step 4 \u2014 LLM Extraction (prompt_builder.py)", 2),
      para("The extraction engine calls prompt_builder.llm_extract(), which automatically invokes chunked extraction for documents exceeding 15,000 characters."),
      gap(1),
      para("Chunking parameters (tuned for large society guidelines 500k\u2013800k chars):", { bold: true }),
      bullet("LARGE_DOC_THRESHOLD: 15,000 chars \u2014 triggers chunked mode"),
      bullet("CHUNK_SIZE: 25,000 chars per chunk (~6,250 tokens)"),
      bullet("CHUNK_OVERLAP: 2,500 chars between adjacent chunks"),
      bullet("MAX_CHUNKS: 12 (covers ~272k chars maximum)"),
      bullet("Parallelism: 2 concurrent workers, staggered by 5s to stay under 30k TPM rate limit"),
      bullet("Retry: Exponential backoff on 429s (2s, 4s, 8s, 16s) before failing chunk"),
      gap(1),
      para("Chunked results are merged with deduplication: scalar fields (summary, population, follow_up, escalation_path) take the first non-empty value; list fields (recommendations, key_thresholds, medications, red_flags) are unioned and deduplicated by first 60 characters of the primary text field."),

      gap(1),

      // Step 5
      hdr("Step 5 \u2014 Metadata Extraction (prompt_builder.extract_metadata)", 2),
      para("A separate LLM call on the first 2,000 chars extracts bibliographic fields: title, organization/journal, publication_year (integer), version_number, and DOI. These populate the source block of the output JSON."),

      gap(1),

      // Step 6
      hdr("Step 6 \u2014 Validation (validator.py)", 2),
      para("Validates the structured output and computes a field_coverage_score (0.0\u20131.0) representing the fraction of non-optional extraction fields that are populated. Eight fields are assessed: summary, population (5 subfields), key_thresholds, recommendations, medications, red_flags, follow_up, and escalation_path."),

      gap(1),

      // JSON Schema
      hdr("unified_v1.0 JSON Schema", 2),
      para("Every extracted JSON conforms to the unified_v1.0 schema with five top-level blocks:"),
      gap(1),

      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [1800, 2200, 5360],
        rows: [
          new TableRow({ children: [hCell("Block", 1800), hCell("Source", 2200), hCell("Key Fields", 5360)] }),
          new TableRow({ children: [dCell("source", 1800, LGRAY, true), dCell("LLM + manifest", 2200), dCell("title, organization, document_type, publication_year, doi, file_name, source_id, status", 5360)] }),
          new TableRow({ children: [dCell("classification", 1800, WHITE, true), dCell("screening.py", 2200), dCell("engine_used, document_type, confidence, signals, body_systems", 5360)] }),
          new TableRow({ children: [dCell("extraction", 1800, LGRAY, true), dCell("LLM engine + synthesis", 2200), dCell("summary, population, key_thresholds, recommendations, medications, red_flags, follow_up, escalation_path, synthesis{}", 5360)] }),
          new TableRow({ children: [dCell("governance", 1800, WHITE, true), dCell("Human-curated", 2200), dCell("badge (must_read/high_yield/supplemental), cross_guideline_impact, change_log, internal_qc", 5360)] }),
          new TableRow({ children: [dCell("metadata", 1800, LGRAY, true), dCell("Pipeline auto", 2200), dCell("schema_version, run_id, extracted_at, validation_passed, field_coverage_score, raw_text_chars", 5360)] }),
        ]
      }),

      gap(1),
      new Paragraph({ children: [new PageBreak()] }),

      // ── SECTION 3: RUNNING THE EXTRACTION ────────────────────
      hdr("3. Running the Extraction", 1),
      hdr("CLI \u2014 main.py", 2),
      para("Always run from the guideline_extractor_v2/ project root. Set the API key before running."),
      gap(1),
      ...codeBlock([
        "# Set API key (PowerShell)",
        "$env:ANTHROPIC_API_KEY = \"sk-ant-...\"",
        "",
        "# Navigate to project root",
        "cd C:\\Users\\mpsch\\Desktop\\claude_knowledge\\guideline_extractor_v2",
        "",
        "# Single file",
        "python main.py --file documents/gold_list/1.pdf --out outputs/my_batch/",
        "",
        "# Batch directory (all PDFs)",
        "python main.py --dir documents/gold_list/ --out outputs/gold_list_v23_baseline/",
        "",
        "# AFP/peds/USPSTF batch (100 docs -- the canonical completed batch)",
        "python main.py --dir <pdf_source_dir>/ --out outputs/afp_peds_uspstf_batch/",
      ]),
      gap(1),
      para("Output per document: <stem>_extracted.json. Output per batch: batch_summary.json with per_document stats including field_coverage_score, recs, thresholds, medications counts, and validation status."),

      gap(1),
      hdr("Test Run Protocol", 2),
      para("Before running a full batch, always run a 5-document test using run_test_batch.py. This catches API key issues, prompt errors, and schema mismatches without burning the full batch budget."),
      gap(1),
      ...codeBlock([
        "# 5-doc AFP test before full batch",
        "python run_test_batch.py",
        "",
        "# Check test output",
        "dir outputs\\afp_test_batch\\",
        "type outputs\\afp_test_batch\\batch_summary.json",
      ]),

      gap(1),
      hdr("Batch Monitoring", 2),
      para("For long-running batches (100+ docs), monitor completion via PowerShell rather than relying on stdout (buffers unreliably). Count JSON files written to the output directory:"),
      gap(1),
      ...codeBlock([
        "# Count completed files in output dir",
        "(Get-ChildItem outputs\\afp_peds_uspstf_batch\\ -Filter *.json | Measure-Object).Count",
        "",
        "# Show most recently written files",
        "Get-ChildItem outputs\\afp_peds_uspstf_batch\\ | Sort-Object LastWriteTime -Descending | Select -First 10",
      ]),

      gap(1),
      new Paragraph({ children: [new PageBreak()] }),

      // ── SECTION 4: CALIBRATION ───────────────────────────────
      hdr("4. Calibration (calibration.py)", 1),
      para("Calibration scores extraction quality across a batch of unified_v1.0 JSONs, identifies systematic gaps by engine type, and generates prompt improvement candidates. The current production calibration score is 0.958 across the AFP/peds/USPSTF batch (n=100)."),
      gap(1),

      hdr("Quality Dimensions Scored", 2),
      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [2200, 4560, 2600],
        rows: [
          new TableRow({ children: [hCell("Dimension", 2200), hCell("What Gets Scored", 4560), hCell("Weight", 2600)] }),
          new TableRow({ children: [dCell("recommendations", 2200, LGRAY), dCell("strength populated, evidence_level populated, average text length", 4560), dCell("30%", 2600)] }),
          new TableRow({ children: [dCell("key_thresholds", 2200, WHITE), dCell("unit populated, context populated, value is specific (not vague)", 4560), dCell("25%", 2600)] }),
          new TableRow({ children: [dCell("population", 2200, LGRAY), dCell("All 5 sub-fields populated and non-trivial: age_criteria, risk_criteria, disease_definition, exclusions, severity_staging", 4560), dCell("20%", 2600)] }),
          new TableRow({ children: [dCell("summary", 2200, WHITE), dCell("Length >= 80 chars, >= 2 sentences, not vague/placeholder", 4560), dCell("15%", 2600)] }),
          new TableRow({ children: [dCell("medications", 2200, LGRAY), dCell("dose populated, class populated (only scored for docs with medications)", 4560), dCell("10%*", 2600)] }),
        ]
      }),
      para("*Medications weight is conditionally activated and total weights renormalized when medication docs are present.", { color: DGRAY, size: 18 }),
      gap(1),

      hdr("Running Calibration", 2),
      ...codeBlock([
        "# Run from guideline_extractor_v2/ project root",
        "cd C:\\Users\\mpsch\\Desktop\\claude_knowledge\\guideline_extractor_v2",
        "",
        "# Default: calibrates against ite_refs/04_outputs/ingested/json/",
        "python calibration.py",
        "",
        "# Custom source directory",
        "python calibration.py --source outputs/afp_peds_uspstf_batch/",
        "",
        "# Output: outputs/calibration/calibration_report_<timestamp>.json",
      ]),
      gap(1),
      para("When gaps are found, calibration automatically writes prompt improvement candidates to prompts/candidates/. These are pre-formatted instruction blocks to paste into the affected engine's system prompt in prompt_builder.py."),

      gap(1),
      new Paragraph({ children: [new PageBreak()] }),

      // ── SECTION 5: MIGRATE TO UNIFIED ────────────────────────
      hdr("5. Migration to Canonical Destination (migrate_to_unified.py)", 1),
      para("After extraction, raw _extracted.json files must be migrated into the ite_refs unified JSON destination. This step wires in the source_id from the ITE manifest, adds an empty governance scaffold, computes field_coverage_score, and writes to the canonical path."),
      gap(1),

      ...codeBlock([
        "# Run from guideline_extractor_v2/ project root",
        "cd C:\\Users\\mpsch\\Desktop\\claude_knowledge\\guideline_extractor_v2",
        "",
        "# Dry run first (shows what would be written, no files changed)",
        "python migrate_to_unified.py --dry-run",
        "",
        "# Live migration (gold list baseline -> ingested/json/)",
        "python migrate_to_unified.py",
        "",
        "# Override paths for AFP batch migration",
        "python migrate_to_unified.py \\",
        "  --baseline outputs/afp_peds_uspstf_batch/ \\",
        "  --manifest C:\\...\\ite_refs\\04_outputs\\ingested\\manifest.json \\",
        "  --dest C:\\...\\ite_refs\\04_outputs\\ingested\\json\\",
      ]),
      gap(1),

      para("What migrate_to_unified.py does:", { bold: true }),
      bullet("Loads ITE manifest (maps PDF filename \u2192 source_id \u2192 destination JSON slug)"),
      bullet("For each _extracted.json in baseline dir: reads v2.3 output, transforms to unified_v1.0 schema"),
      bullet("Wires source_id from manifest into source.source_id (format: AFP-<hash> or ITE-<hash>)"),
      bullet("Adds empty governance scaffold (badge, cross_guideline_impact, change_log, internal_qc)"),
      bullet("Computes field_coverage_score via inline validator"),
      bullet("Writes to ite_refs/04_outputs/ingested/json/<slug>.json"),
      bullet("Writes migration_summary.json with per-document stats"),

      gap(1),

      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [2400, 6960],
        rows: [
          new TableRow({ children: [hCell("Canonical Destination", 2400), hCell("Path", 6960)] }),
          new TableRow({ children: [dCell("AFP batch JSONs", 2400, LGRAY), dCell("board_prep\\ite_refs\\04_outputs\\ingested\\json\\  (AFP- source IDs)", 6960)] }),
          new TableRow({ children: [dCell("Gold list JSONs", 2400, WHITE), dCell("board_prep\\ite_refs\\04_outputs\\ingested\\json\\  (ITE- source IDs)", 6960)] }),
          new TableRow({ children: [dCell("Manifest", 2400, LGRAY), dCell("board_prep\\ite_refs\\04_outputs\\ingested\\manifest.json", 6960)] }),
        ]
      }),

      gap(1),
      new Paragraph({ children: [new PageBreak()] }),

      // ── SECTION 6: PHASE 2 WORD INJECTION ────────────────────
      hdr("6. Phase 2: JSON \u2192 Word Document Injection", 1),
      para("Phase 2 reads the migrated JSON extractions, matches them to AAFP board prep sessions via keyword-driven question matching, and injects styled callout blocks into the curriculum Word document."),
      gap(1),

      hdr("Step 1 \u2014 Question-Driven Session Matching (E_v4_question_driven.py)", 2),
      para("Matches ITE exam questions to the 48 board prep sessions by scoring keyword overlap between question stems + AI clinical focus tags and the session keyword library. For each matched question, refs are parsed inline from the Explanation column and fuzzy-matched against the tier database."),
      gap(1),

      ...codeBlock([
        "# Run from board_prep/aafp_integration/05_scripts/",
        "cd C:\\Users\\mpsch\\Desktop\\claude_knowledge\\board_prep\\aafp_integration\\05_scripts",
        "",
        "python E_v4_question_driven.py",
        "",
        "# Output: board_prep/aafp_integration/02_working/session_hy_inserts_v6.json",
        "# Schema: {session_id, session_title, question_count,",
        "#   questions: [{qid, year, focus, stem_preview, kw_score, kw_hits}],",
        "#   refs:      [{citation, tier, match_score, cited_by}],",
        "#   must_read_count, core_count, supplementary_count}",
      ]),
      gap(1),
      para("Key design decisions in the matching engine:", { bold: true }),
      bullet("Question-driven (not reference-driven): refs are earned bottom-up by matched questions, not forced top-down from the tier list. A session only gets a Must-Read ref if a matched question actually cites it."),
      bullet("Matching uses QuestionStem + AI_ClinicalFocus + AI_Subcategory for tokenization (not the full Explanation text, which is too noisy)"),
      bullet("2020\u20132023 refs use 'Ref:' prefix format in Explanation; 2024 uses 'Reference' heading format"),
      bullet("Fuzzy matching against tier DB uses difflib.SequenceMatcher; threshold tuned to avoid false positives from superficial keyword overlap"),

      gap(1),
      hdr("Step 2 \u2014 Word Injection (03_inject_into_outline_v3.py)", 2),
      para("Injects styled callout blocks into the AAFP Board Prep content outline Word document. Reads session_hy_inserts_v6.json and injects after each Heading1 'Session N:' paragraph using raw XML surgery via Python zipfile."),
      gap(1),

      ...codeBlock([
        "# Run from board_prep/aafp_integration/05_scripts/",
        "cd C:\\Users\\mpsch\\Desktop\\claude_knowledge\\board_prep\\aafp_integration\\05_scripts",
        "",
        "python 03_inject_into_outline_v3.py",
        "",
        "# Source:  board_prep/aafp_integration/04_outputs/BoardPrep-ContentOutline_HY-ENRICHED-v3.docx",
        "# Output:  board_prep/aafp_integration/04_outputs/BoardPrep-ContentOutline_HY-ENRICHED-v4.docx",
      ]),
      gap(1),

      para("What the injection script does:", { bold: true }),
      bullet("Loads source DOCX as ZIP, reads word/document.xml into memory"),
      bullet("Strips existing callout blocks from prior runs (identified by fill color palette: 1F3864, 2E75B6, D6E4F7, FFF2CC, EBF3FB)"),
      bullet("Pre-builds all 48 callout XML blocks from v6 JSON"),
      bullet("Injects each callout after its matching Heading1 'Session N:' paragraph via regex substitution"),
      bullet("Repacks all ZIP entries to new DOCX \u2014 zero repair warnings required"),

      gap(1),
      hdr("Callout Block Visual Design", 2),

      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [2800, 6560],
        rows: [
          new TableRow({ children: [hCell("Row Type", 2800), hCell("Style", 6560)] }),
          new TableRow({ children: [dCell("Header bar", 2800, LGRAY), dCell("Fill: 1F3864 (dark navy), white bold text, session name + question/ref counts", 6560)] }),
          new TableRow({ children: [dCell("Section sub-headers", 2800, WHITE), dCell("Fill: 2E75B6 (mid blue), white bold text, 'ITE EXAM QUESTIONS' / 'KEY REFERENCES'", 6560)] }),
          new TableRow({ children: [dCell("Question rows", 2800, LGRAY), dCell("Fill: D6E4F7 (light blue), QID + year + match score bold; focus text italic below", 6560)] }),
          new TableRow({ children: [dCell("Must-Read refs", 2800, WHITE), dCell("Fill: FFF2CC (amber), [MUST-READ] label + citation + cited-by", 6560)] }),
          new TableRow({ children: [dCell("Core refs", 2800, LGRAY), dCell("Fill: EBF3FB (pale blue), [CORE] label + citation + cited-by", 6560)] }),
          new TableRow({ children: [dCell("Footer rule", 2800, WHITE), dCell("Fill: 1F3864, 4pt bottom border, closes the block", 6560)] }),
        ]
      }),

      gap(1),
      new Paragraph({ children: [new PageBreak()] }),

      // ── SECTION 7: PHASE 3 — ONE-CLICK SUMMARY ──────────────
      hdr("7. Phase 3: One-Click Summary Pipeline", 1),
      para("Phase 3 adds a standalone summary workflow: right-click any PDF anywhere on the system, and a styled summary DOCX appears next to it. No CLI, no project root navigation, no manual steps. The PDF never moves; the output always lands beside the input and is also copied to the Desktop."),
      gap(1),

      hdr("Architecture", 2),
      ...codeBlock([
        "  Right-click any PDF  -->  extract_guideline.bat",
        "       |",
        "       v",
        "  [1] Python ingestion   (cd to project root internally)",
        "       |                  ingest_document(absolute_pdf_path)",
        "       |                  Writes temp JSON to %TEMP%",
        "       v",
        "  [2] synthesize.js      Calls Claude Sonnet (claude-sonnet-4-6)",
        "       |                  Augments JSON with extraction.synthesis{}",
        "       v",
        "  [3] build_summary.js   Reads augmented JSON",
        "       |                  Generates styled DOCX via docx-js",
        "       v",
        "  _summary.docx          Placed next to original PDF + copied to Desktop",
      ]),
      gap(1),

      hdr("Synthesis Layer (synthesize.js)", 2),
      para("The synthesis layer calls Claude Sonnet to transform raw extraction data into clinician-focused narrative. It augments the extraction JSON in-place, adding an extraction.synthesis{} block. If synthesis fails, the pipeline continues with raw data only (non-fatal)."),
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
          new TableRow({ children: [dCell("critical_alerts", 2800, WHITE, true), dCell("5-8 red flags with 'why it matters' explanations and immediate actions", 6560)] }),
          new TableRow({ children: [dCell("definitions_and_thresholds", 2800, LGRAY, true), dCell("High-yield clinical definitions and diagnostic thresholds that change management", 6560)] }),
        ]
      }),

      gap(1),

      hdr("Summary DOCX Layout (build_summary.js)", 2),
      para("The summary DOCX is generated by build_summary.js using the docx-js library. Sections are only rendered if the data exists. The document uses the same color palette as this protocol document."),
      gap(1),

      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [600, 2400, 6360],
        rows: [
          new TableRow({ children: [hCell("#", 600), hCell("Section", 2400), hCell("Content", 6360)] }),
          new TableRow({ children: [dCell("1", 600, LGRAY, true), dCell("Title Banner", 2400, LGRAY, true), dCell("Navy fill, white text: title, org | year | DOI", 6360)] }),
          new TableRow({ children: [dCell("2", 600, WHITE, true), dCell("Classification Badge", 2400, WHITE, true), dCell("Doc type, engine, confidence %, body systems", 6360)] }),
          new TableRow({ children: [dCell("3", 600, LGRAY, true), dCell("Clinical Summary", 2400, LGRAY, true), dCell("Extraction summary + synthesis bottom line (merged view)", 6360)] }),
          new TableRow({ children: [dCell("4", 600, WHITE, true), dCell("Key Practice Changes", 2400, WHITE, true), dCell("Teal banner + bullet list from practice_pearls", 6360)] }),
          new TableRow({ children: [dCell("5", 600, LGRAY, true), dCell("Target Population", 2400, LGRAY, true), dCell("2-col table: age, risk, disease def, exclusions, severity", 6360)] }),
          new TableRow({ children: [dCell("6", 600, WHITE, true), dCell("Definitions & Thresholds", 2400, WHITE, true), dCell("2-col table: term + definition (deduped against medications)", 6360)] }),
          new TableRow({ children: [dCell("7", 600, LGRAY, true), dCell("Clinical Recommendations", 2400, LGRAY, true), dCell("4-col table, color-coded: Strong=teal, Conditional=amber", 6360)] }),
          new TableRow({ children: [dCell("8", 600, WHITE, true), dCell("Medications", 2400, WHITE, true), dCell("Grouped by indication (synthesis) or flat 4-col table (fallback)", 6360)] }),
          new TableRow({ children: [dCell("9", 600, LGRAY, true), dCell("Red Flags & Critical Alerts", 2400, LGRAY, true), dCell("Red banner + alert/why-it-matters pairs (synthesis) or bullet list", 6360)] }),
          new TableRow({ children: [dCell("10", 600, WHITE, true), dCell("Follow-Up & Monitoring", 2400, WHITE, true), dCell("Paragraph text from extraction", 6360)] }),
          new TableRow({ children: [dCell("11", 600, LGRAY, true), dCell("Footer", 2400, LGRAY, true), dCell("Extraction timestamp, engine version, coverage score", 6360)] }),
        ]
      }),

      gap(1),

      hdr("Context Menu Installation", 2),
      para("The context menu entries are installed via Windows registry (HKCU \u2014 no admin rights required). On Windows 11, entries appear under 'Show more options' in the right-click menu."),
      gap(1),
      ...codeBlock([
        "# Install right-click menu entries",
        "regedit /s oneclick\\install_context_menu.reg",
        "",
        "# Uninstall",
        "regedit /s oneclick\\uninstall_context_menu.reg",
        "",
        "# Manual test (single file)",
        "oneclick\\extract_guideline.bat \"C:\\Users\\mpsch\\Downloads\\some_guideline.pdf\"",
        "",
        "# Manual test (batch folder)",
        "oneclick\\extract_guideline.bat \"C:\\Users\\mpsch\\Downloads\\guidelines_folder\"",
      ]),
      gap(1),
      para("API key resolution: The bat file resolves ANTHROPIC_API_KEY from (1) current environment, then (2) HKCU\\Environment registry. Context menu launches a fresh cmd.exe that may not inherit User env vars, so the registry fallback is critical."),

      gap(1),

      hdr("One-Click File Reference", 2),
      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [3000, 6360],
        rows: [
          new TableRow({ children: [hCell("File", 3000), hCell("Purpose", 6360)] }),
          new TableRow({ children: [dCell("extract_guideline.bat", 3000, LGRAY, true), dCell("Orchestrator: accepts any PDF path or folder, handles cd to project root, chains Python + Node.js steps", 6360)] }),
          new TableRow({ children: [dCell("synthesize.js", 3000, WHITE, true), dCell("LLM synthesis: calls Claude Sonnet to produce 5-field clinical narrative, augments JSON in-place", 6360)] }),
          new TableRow({ children: [dCell("build_summary.js", 3000, LGRAY, true), dCell("DOCX generator: reads augmented JSON, produces styled 11-section summary via docx-js", 6360)] }),
          new TableRow({ children: [dCell("install_context_menu.reg", 3000, WHITE, true), dCell("Adds 'Extract Guideline' (PDF) and 'Extract All Guidelines' (folder) to right-click menu", 6360)] }),
          new TableRow({ children: [dCell("uninstall_context_menu.reg", 3000, LGRAY, true), dCell("Removes both context menu entries", 6360)] }),
        ]
      }),

      gap(1),
      new Paragraph({ children: [new PageBreak()] }),

      // ── SECTION 8: IMPORTANT RULES ────────────────────────────
      hdr("8. Critical Rules & Common Pitfalls", 1),
      gap(1),

      hdr("DOCX Editing \u2014 Never Use Pandoc", 2),
      para("CRITICAL: Never use pandoc round-trip for DOCX editing. Pandoc destroys Word styles, relationships, and media. Always use the unpack/XML-edit/pack workflow:", { bold: true, color: "C00000" }),
      gap(1),
      ...codeBlock([
        "# ALWAYS this workflow:",
        "python scripts/office/unpack.py document.docx unpacked/",
        "# ... edit unpacked/word/document.xml ...",
        "python scripts/office/pack.py unpacked/ output.docx --original document.docx",
        "",
        "# The --original flag is REQUIRED to inherit relationships and media",
        "# Zero repair warnings required (files shared with non-technical users)",
      ]),
      gap(1),

      hdr("API Key", 2),
      para("Resolution order: (1) ANTHROPIC_API_KEY environment variable, (2) HKCU\\Environment registry (used by context menu launcher), (3) config.json at guideline_extractor_v2/ root. Never hardcode the key in scripts."),
      gap(1),

      hdr("Script Execution Pattern", 2),
      ...codeBlock([
        "# Write script to disk via Desktop Commander write_file, then execute:",
        "Desktop Commander:start_process(",
        "  command='cd guideline_extractor_v2 && python main.py --dir ...',",
        "  timeout_ms=120000  # 2 min for small batches; scale up for large",
        ")",
        "",
        "# Monitor with polling, NOT stdout capture (buffers unreliably):",
        "(Get-ChildItem outputs\\batch\\ -Filter *.json | Measure-Object).Count",
      ]),
      gap(1),

      hdr("Source ID Naming Convention", 2),
      bullet("AFP batch: AFP-<hash> (100 JSONs with AFP- source IDs, migration confirmed complete)"),
      bullet("Gold list: ITE-<hash> (21 docs, 7 pending migration as of 2026-03-06)"),
      bullet("Each source_id is unique and links the ingested JSON back to the ITE refs manifest"),

      gap(1),
      hdr("Previous Versions Policy", 2),
      para("Superseded scripts or documents that would produce unwanted outputs are removed or moved to previous_versions/ subfolders \u2014 never left in place as passive warnings. Stale files are a liability."),

      gap(1),
      new Paragraph({ children: [new PageBreak()] }),

      // ── SECTION 9: QUICK REFERENCE ────────────────────────────
      hdr("9. Quick Reference \u2014 All Key Scripts", 1),
      gap(1),

      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [2800, 3600, 2960],
        rows: [
          new TableRow({ children: [hCell("Script", 2800), hCell("Purpose", 3600), hCell("Location", 2960)] }),
          new TableRow({ children: [dCell("main.py", 2800, LGRAY, true), dCell("CLI entry point: single file or batch directory", 3600), dCell("guideline_extractor_v2/", 2960)] }),
          new TableRow({ children: [dCell("preprocess.py", 2800, WHITE, true), dCell("PDF/ZIP/text extraction + cleaning", 3600), dCell(".../utils/", 2960)] }),
          new TableRow({ children: [dCell("screening.py", 2800, LGRAY, true), dCell("LLM document classifier (5 types + RCT heuristic)", 3600), dCell(".../core/", 2960)] }),
          new TableRow({ children: [dCell("routing.py", 2800, WHITE, true), dCell("Engine selection based on document_type", 3600), dCell(".../core/", 2960)] }),
          new TableRow({ children: [dCell("ingestion.py", 2800, LGRAY, true), dCell("Full pipeline orchestrator: preprocess \u2192 screen \u2192 route \u2192 extract \u2192 validate \u2192 log", 3600), dCell(".../core/", 2960)] }),
          new TableRow({ children: [dCell("prompt_builder.py", 2800, WHITE, true), dCell("Anthropic API client: llm_screen, llm_extract, extract_metadata, chunked extraction", 3600), dCell(".../utils/", 2960)] }),
          new TableRow({ children: [dCell("[engine].py", 2800, LGRAY, true), dCell("5 extraction engines: chronic, acute, preventive, diagnostic, rct", 3600), dCell(".../engines/", 2960)] }),
          new TableRow({ children: [dCell("validator.py", 2800, WHITE, true), dCell("Validation + field_coverage_score computation", 3600), dCell(".../utils/", 2960)] }),
          new TableRow({ children: [dCell("logger.py", 2800, LGRAY, true), dCell("Run logging to logs/run_<ts>_<id>.json", 3600), dCell(".../utils/", 2960)] }),
          new TableRow({ children: [dCell("calibration.py", 2800, WHITE, true), dCell("Quality scoring, gap analysis, prompt candidate generation", 3600), dCell("guideline_extractor_v2/", 2960)] }),
          new TableRow({ children: [dCell("run_test_batch.py", 2800, LGRAY, true), dCell("5-doc AFP test run before full batches", 3600), dCell("guideline_extractor_v2/", 2960)] }),
          new TableRow({ children: [dCell("migrate_to_unified.py", 2800, WHITE, true), dCell("Transform v2.3 outputs to unified_v1.0 and write to canonical ite_refs destination", 3600), dCell("guideline_extractor_v2/", 2960)] }),
          new TableRow({ children: [dCell("E_v4_question_driven.py", 2800, LGRAY, true), dCell("Question-driven session matching + ref extraction \u2192 session_hy_inserts_v6.json", 3600), dCell("board_prep/.../05_scripts/", 2960)] }),
          new TableRow({ children: [dCell("03_inject_into_outline_v3.py", 2800, WHITE, true), dCell("Inject v6 JSON callout blocks into HY-ENRICHED Word doc", 3600), dCell("board_prep/.../05_scripts/", 2960)] }),
          // Phase 3 one-click scripts
          new TableRow({ children: [dCell("extract_guideline.bat", 2800, AMBER, true, NAVY), dCell("One-click orchestrator: right-click any PDF \u2192 summary DOCX", 3600, AMBER), dCell("oneclick/", 2960, AMBER)] }),
          new TableRow({ children: [dCell("synthesize.js", 2800, AMBER, true, NAVY), dCell("LLM synthesis: 5-field clinical narrative via Claude Sonnet", 3600, AMBER), dCell("oneclick/", 2960, AMBER)] }),
          new TableRow({ children: [dCell("build_summary.js", 2800, AMBER, true, NAVY), dCell("DOCX generator: styled 11-section summary from augmented JSON", 3600, AMBER), dCell("oneclick/", 2960, AMBER)] }),
        ]
      }),

      gap(2),

      hdr("Completed Batches (as of 2026-03-09)", 2),
      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [2600, 1200, 1800, 3760],
        rows: [
          new TableRow({ children: [hCell("Batch", 2600), hCell("Docs", 1200), hCell("Avg Quality", 1800), hCell("Status", 3760)] }),
          new TableRow({ children: [dCell("afp_peds_uspstf_batch", 2600, TEAL), dCell("100", 1200, TEAL), dCell("0.958", 1800, TEAL), dCell("Complete \u2014 migrated to ingested/json/ with AFP- source IDs", 3760, TEAL)] }),
          new TableRow({ children: [dCell("gold_list_v23_baseline", 2600, LGRAY), dCell("14 / 21", 1200, LGRAY), dCell("0.93+", 1800, LGRAY), dCell("14 migrated with ITE- source IDs; 7 pending migration", 3760, LGRAY)] }),
          new TableRow({ children: [dCell("jacc_pulm_batch", 2600, WHITE), dCell("22", 1200, WHITE), dCell("\u2014", 1800, WHITE), dCell("Extracted; pending migration", 3760, WHITE)] }),
          new TableRow({ children: [dCell("id_renal_gi_hep_batch", 2600, LGRAY), dCell("70", 1200, LGRAY), dCell("\u2014", 1800, LGRAY), dCell("Extracted; pending migration", 3760, LGRAY)] }),
          new TableRow({ children: [dCell("neuro_tox_rheum_psych_batch", 2600, WHITE), dCell("35", 1200, WHITE), dCell("\u2014", 1800, WHITE), dCell("Extracted; pending migration", 3760, WHITE)] }),
        ]
      }),

      gap(3),
      hr(),
      para("ABFM Board Prep Project \u2014 Internal Use Only \u2014 Do Not Distribute", { color: DGRAY, size: 16, center: true }),
      para("Updated 2026-03-09 | guideline_extractor_v2.3 | unified_v1.0 schema | oneclick v1.0", { color: DGRAY, size: 16, center: true }),

    ]
  }]
});

const outPath = process.argv[2] || 'ABFM_GuidanceExtraction_Protocol_v3.docx';
Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync(outPath, buf);
  console.log('Written: ' + outPath);
});
