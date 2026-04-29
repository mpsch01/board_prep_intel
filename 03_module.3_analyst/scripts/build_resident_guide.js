#!/usr/bin/env node

// ITE Report Guide — Resident's Reading Guide
// Generates an interactive guide to help residents interpret their ITE Score Analysis report
// Usage: node build_resident_guide.js
// Output: ../docs/ITE_Report_Guide_Resident.docx

const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, HeadingLevel, BorderStyle, WidthType,
  ShadingType, VerticalAlign, PageNumber, PageBreak, LevelFormat
} = require("docx");

// ── Style constants ─────────────────────────────────────────────────
const NAVY   = "1F3864";
const BLUE   = "2E75B6";
const DGRAY  = "333333";
const MGRAY  = "595959";
const WHITE  = "FFFFFF";
const LTBLUE = "D6E4F7";
const GREEN  = "276749";
const AMBER  = "975A16";
const RED    = "9B2C2C";
const GOLD   = "C8922A";
const FONT   = "Aptos";

// ── Margin constants (1 inch = 1440 DXA) ───────────────────────────
const MARGIN_IN = 1440;
const PAGE_WIDTH = 12240;
const PAGE_HEIGHT = 15840;
const CONTENT_WIDTH = PAGE_WIDTH - (2 * MARGIN_IN);  // 9360 DXA

// ── Helper functions ────────────────────────────────────────────────
function noBorders() {
  const n = { style: BorderStyle.NONE, size: 0, color: WHITE };
  return { top: n, bottom: n, left: n, right: n };
}

const thinBorder = { style: BorderStyle.SINGLE, size: 1, color: "D0D0D0" };
const cellBorders = { top: thinBorder, bottom: thinBorder, left: thinBorder, right: thinBorder };

function sectionBar(text) {
  const W = CONTENT_WIDTH;
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
            children: [new TextRun({ text, font: FONT, size: 22, bold: true, color: WHITE })]
          })]
        })
      ]
    })]
  });
}

function subBar(text, fill = NAVY) {
  const W = CONTENT_WIDTH;
  return new Table({
    width: { size: W, type: WidthType.DXA },
    columnWidths: [W],
    rows: [new TableRow({
      cantSplit: true,
      children: [
        new TableCell({
          width: { size: W, type: WidthType.DXA },
          shading: { fill, type: ShadingType.CLEAR },
          borders: noBorders(),
          margins: { top: 50, bottom: 50, left: 140, right: 140 },
          children: [new Paragraph({
            keepNext: true,
            children: [new TextRun({ text, font: FONT, size: 20, bold: true, color: WHITE })]
          })]
        })
      ]
    })]
  });
}

function actionCallout(text) {
  return new Paragraph({
    spacing: { before: 120, after: 200 },
    border: { left: { style: BorderStyle.SINGLE, size: 12, color: GOLD, space: 8 } },
    indent: { left: 200 },
    children: [
      new TextRun({ text: "✎ ACTION  ", font: FONT, size: 20, bold: true, color: NAVY }),
      new TextRun({ text, font: FONT, size: 20, color: NAVY })
    ]
  });
}

function spacer(pts = 100, keepNext = false) {
  return new Paragraph({ spacing: { before: pts, after: 0 }, keepNext, children: [] });
}

function bodyText(text) {
  return new Paragraph({
    spacing: { before: 80, after: 80 },
    children: [new TextRun({ text, font: FONT, size: 18, color: DGRAY })]
  });
}

function bulletList(items) {
  return items.map((item, idx) => {
    return new Paragraph({
      spacing: { before: 60, after: 60 },
      indent: { left: 360, hanging: 360 },
      children: [
        new TextRun({ text: `• ${item}`, font: FONT, size: 18, color: DGRAY })
      ]
    });
  });
}

// ═══════════════════════════════════════════════════════════════════
// BUILD DOCUMENT SECTIONS
// ═══════════════════════════════════════════════════════════════════

const sections = [];

// ────────────────────────────────────────────────────────────────────
// COVER PAGE & INTRO
// ────────────────────────────────────────────────────────────────────
sections.push(new Paragraph({
  spacing: { before: 600, after: 0 },
  alignment: AlignmentType.CENTER,
  children: [new TextRun({
    text: "ITE Score Analysis",
    font: FONT,
    size: 44,
    bold: true,
    color: NAVY
  })]
}));

sections.push(new Paragraph({
  spacing: { before: 80, after: 0 },
  alignment: AlignmentType.CENTER,
  children: [new TextRun({
    text: "Resident's Reading Guide",
    font: FONT,
    size: 32,
    bold: true,
    color: BLUE
  })]
}));

sections.push(spacer(240));

sections.push(new Paragraph({
  spacing: { before: 100, after: 100 },
  alignment: AlignmentType.CENTER,
  children: [new TextRun({
    text: "How to turn your report into a study plan",
    font: FONT,
    size: 20,
    italics: true,
    color: MGRAY
  })]
}));

sections.push(spacer(200));

sections.push(bodyText(
  "The ITE Score Analysis report is designed to show you exactly where your knowledge gaps are and which gaps are worth your study time. This guide walks through the report section by section. For each section, you'll learn what you're reading and what to do with it."
));

sections.push(new PageBreak());

// ────────────────────────────────────────────────────────────────────
// SECTION 0 — EXAM AT A GLANCE
// ────────────────────────────────────────────────────────────────────
sections.push(sectionBar("Section 0 — Exam at a Glance"));
sections.push(spacer(100));

sections.push(bodyText(
  "National statistics about the exam itself — how many items are scored, the passing score, and where the average resident in your PGY year scored."
));

sections.push(subBar("Key things to note"));
sections.push(spacer(60));

sections.push(...bulletList([
  "MPS is 380. Below 380 = your #1 goal is closing this gap before the FMCE.",
  "440 is the FMCE signal threshold. If you're comfortably above MPS but below 440, that's your target zone.",
  "SEM ±38 means there's natural measurement error. A score of 375 and 380 are not meaningfully different — they're within one measurement unit of each other.",
  "The experimental items (deleted items) don't count toward your score. Don't be confused by question numbers that don't appear in your score."
]));

sections.push(actionCallout(
  "Before reading further, note your score against these three marks: MPS (380), FMCE threshold (440), and the listed PGY Mean for your year. These three numbers anchor everything that follows."
));

sections.push(new PageBreak());

// ────────────────────────────────────────────────────────────────────
// SECTION 1 — YOUR SCORE
// ────────────────────────────────────────────────────────────────────
sections.push(sectionBar("Section 1 — Your Score"));
sections.push(spacer(100));

sections.push(bodyText(
  "Three versions of your score — raw %, scaled score, and percentile — plus comparison to the national average for your PGY level."
));

sections.push(subBar("The numbers explained"));
sections.push(spacer(60));

sections.push(...bulletList([
  "Raw %: The fraction of questions you answered correctly out of the total scored items.",
  "Scaled score: A standardized number (roughly 200–600) that accounts for year-to-year variation in difficulty. This is the number that matters for passing (MPS = 380) and the FMCE (440 signal).",
  "Percentile: Where you rank among all residents who took that year's exam."
]));

sections.push(spacer(120));
sections.push(bodyText(
  "The \"confidence range (68%)\" shows that your actual knowledge level falls somewhere within this band. A scored test always has measurement error — this range captures it."
));

sections.push(spacer(120));
sections.push(bodyText(
  "If you see a trajectory label like STRONG or AT RISK, treat it as a directional signal, not a verdict. It's an estimate based on your score relative to national benchmarks."
));

sections.push(actionCallout(
  "Look at \"vs MPS\" and \"vs PGY Mean.\" These two numbers tell you the whole story. If vs MPS is negative, getting to 380 is your priority. If you're above MPS, pushing toward 440 is the goal."
));

sections.push(new PageBreak());

// ────────────────────────────────────────────────────────────────────
// SECTION 2 — EXAM SUMMARY
// ────────────────────────────────────────────────────────────────────
sections.push(sectionBar("Section 2 — Exam Summary"));
sections.push(spacer(100));

sections.push(bodyText(
  "A quick-reference bullet list summarizing your most important findings."
));

sections.push(subBar("The bullets explained"));
sections.push(spacer(60));

sections.push(...bulletList([
  "Scaled score line: Same as Section 1 — confirms your baseline.",
  "\"X additional correct answers needed to reach MPS\": A rough estimate of how many more questions you'd need to answer correctly to hit 380. Use it for motivation, not precision.",
  "Weak areas: The content domains where your score is below your personal average OR below 70%. These are your study priorities for Part B (practice questions) and the reading list.",
  "Lowest blueprint category: The single domain where you struggled most. Start your content review here.",
  "Easy misses: The most important number in this section. These are questions most of your peers got right that you missed. See Section 6 for the full breakdown."
]));

sections.push(actionCallout(
  "Highlight the \"Lowest blueprint category\" and \"Easy misses\" count. Those two facts should anchor your study plan."
));

sections.push(new PageBreak());

// ────────────────────────────────────────────────────────────────────
// SECTION 3b — YEAR-OVER-YEAR PROGRESS
// ────────────────────────────────────────────────────────────────────
sections.push(sectionBar("Section 3b — Year-Over-Year Progress"));
sections.push(spacer(100));

sections.push(bodyText(
  "(Only appears if you have a prior year's report) A direct comparison of your score and weak areas versus last year and the year before."
));

sections.push(subBar("The trajectory categories"));
sections.push(spacer(60));

sections.push(...bulletList([
  "✔ Closed: A gap you had last year that you've resolved. Don't abandon these topics entirely — they can regress if you stop reviewing.",
  "⚠ Persistent: A gap that appeared last year and is still here. This is a signal that studying the same way isn't working for this topic. You need a different approach — not just more hours, but a different strategy.",
  "▶ New: A gap that wasn't here last year. This may be new exam content, a topic you de-prioritized, or a domain where your knowledge decayed."
]));

sections.push(actionCallout(
  "Focus your energy on Persistent gaps first. If you've reviewed the same material twice and it's not sticking, change the resource or method. New gaps are secondary — they're easier to fix."
));

sections.push(new PageBreak());

// ────────────────────────────────────────────────────────────────────
// SECTION 4 — BLUEPRINT & BODY SYSTEM PERFORMANCE
// ────────────────────────────────────────────────────────────────────
sections.push(sectionBar("Section 4 — Blueprint & Body System Performance"));
sections.push(spacer(100));

sections.push(bodyText(
  "Your performance broken down by ABFM content domain (Blueprint) and by organ system (Body System)."
));

sections.push(subBar("How to read the Blueprint table"));
sections.push(spacer(60));

sections.push(...bulletList([
  "Prior %: Your rate last year (dashes = first year or no prior data).",
  "Δ: Change from last year. Green = improved, Red = regressed.",
  "SEM: The measurement error for this sub-score. A large SEM (e.g., ±15%) means this sub-score is based on few questions and is less reliable. Treat large-SEM sub-scores as hypotheses to investigate, not confirmed deficits.",
  "Color coding: Green (≥70%) = passing territory. Amber (50–70%) = needs work. Red (<50%) = urgent."
]));

sections.push(spacer(120));
sections.push(bodyText(
  "The two Body System tables: ABFM-Reported (navy label) came directly from your official ABFM score report — these are the most reliable sub-scores. Database-Derived (blue label) is inferred from the content of your exam questions using the ITE Knowledge Base. These are supplementary signals — useful for pattern detection, not for precise scoring."
));

sections.push(actionCallout(
  "Any row below 50% (red) is urgent. Any row in amber (50–70%) needs focused review. Within the red rows, prioritize those with a smaller SEM value — those are more reliable signals of a genuine gap. Start with the highest-priority red row and don't move to the next until you've done a content review of that domain."
));

sections.push(new PageBreak());

// ────────────────────────────────────────────────────────────────────
// SECTION 6 — DIFFICULTY PROFILE
// ────────────────────────────────────────────────────────────────────
sections.push(sectionBar("Section 6 — Difficulty Profile"));
sections.push(spacer(100));

sections.push(bodyText(
  "Your missed questions broken down by how difficult they were nationally."
));

sections.push(subBar("The three tiers"));
sections.push(spacer(60));

sections.push(...bulletList([
  "Easy Miss (≥700): Nearly everyone else got these right. These are NOT unlucky hard questions — they are genuine knowledge gaps. This is where your study time will produce the most improvement.",
  "Mid-Range (300–699): Challenging questions that reward high-yield review. Each one you convert is meaningful.",
  "Hard Miss (<300): Most residents missed these too. Chasing them is low ROI unless you've already cleaned up the Easy and Mid-Range tiers."
]));

sections.push(spacer(120));
sections.push(bodyText(
  "The Easy Misses table lists each specific question (QID) that was an Easy Miss. These are your highest-priority review items. Look each one up in your exam materials and understand the concept it tested."
));

sections.push(actionCallout(
  "Print (or note) the Easy Misses table. Each QID listed is a question where you and most of your peers diverged — meaning it's a learnable, reviewable gap. Work through every one before your next exam."
));

sections.push(new PageBreak());

// ────────────────────────────────────────────────────────────────────
// SECTION 7 — LOW-HANGING FRUIT
// ────────────────────────────────────────────────────────────────────
sections.push(sectionBar("Section 7 — Low-Hanging Fruit"));
sections.push(spacer(100));

sections.push(bodyText(
  "A ranked list of content domains by study ROI — where each hour of review converts to the most scaled score improvement."
));

sections.push(subBar("The two metrics explained"));
sections.push(spacer(60));

sections.push(...bulletList([
  "Improvable Items: The number of questions in this category that (1) you got wrong AND (2) most of your peers got right. These are the questions you could realistically convert on a re-test with targeted review.",
  "Priority Score: Improvable Items × how much this domain counts on the exam. A domain worth 35% of the exam with 3 improvable items ranks higher than a domain worth 5% of the exam with 5 improvable items."
]));

sections.push(spacer(120));
sections.push(bodyText(
  "The Blueprint table includes a Priority Score (tied to official exam weighting). The Body System table shows only Improvable Items (body systems don't have published ABFM weightings)."
));

sections.push(actionCallout(
  "Start with Rank #1 on the Blueprint table. Spend concentrated study time there before moving to Rank #2. This section is your study sequence generator — follow it."
));

sections.push(new PageBreak());

// ────────────────────────────────────────────────────────────────────
// SECTION 7b — CATEGORY CROSSOVER WEAKNESSES
// ────────────────────────────────────────────────────────────────────
sections.push(sectionBar("Section 7b — Category Crossover Weaknesses"));
sections.push(spacer(100));

sections.push(bodyText(
  "Weak spots at the intersection of TWO dimensions — for example, \"Cardiovascular × Acute Care\" means acute presentations of cardiovascular disease specifically (not cardiovascular disease broadly, not acute care broadly — the overlap)."
));

sections.push(subBar("Why this matters"));
sections.push(spacer(60));

sections.push(bodyText(
  "A pure Cardiovascular weakness might mean you need to review all cardiac medicine. A Cardiovascular × Acute Care crossover means you specifically need to focus on acute cardiac presentations (chest pain, ACS, arrhythmia emergencies) — a much tighter study target."
));

sections.push(actionCallout(
  "If any crossover weakness aligns with one of your red/amber Blueprint rows from Section 4, that intersection is your most specific study target. Narrow your review to clinical scenarios at exactly that overlap."
));

sections.push(new PageBreak());

// ────────────────────────────────────────────────────────────────────
// SECTION 8 — CONCEPT FINGERPRINT
// ────────────────────────────────────────────────────────────────────
sections.push(sectionBar("Section 8 — Concept Fingerprint"));
sections.push(spacer(100));

sections.push(bodyText(
  "Drugs that appeared repeatedly across your missed questions — a \"fingerprint\" of recurring pharmacology knowledge gaps."
));

sections.push(subBar("How to read the frequency column"));
sections.push(spacer(60));

sections.push(...bulletList([
  "3×+ (red): This drug appeared in 3 or more of your missed questions. This is a consistent pharmacology gap — not a coincidence.",
  "2× (amber): Two missed questions shared this drug. Worth targeted review.",
  "The QID column: Lists the specific question IDs where this drug appeared. Use them to pull those questions from your exam materials."
]));

sections.push(spacer(120));
sections.push(bodyText(
  "Badges (appear only on multi-year reports): A 🔁 badge means this drug cluster was in your missed questions last year too. A 🆕 badge means it's new this year."
));

sections.push(actionCallout(
  "For any drug appearing 2+ times, review: mechanism of action, indications, contraindications, key drug interactions, and monitoring parameters. Use the QID column to find those specific questions and understand why you missed them."
));

sections.push(new PageBreak());

// ────────────────────────────────────────────────────────────────────
// SECTION 9 — ICD-10 WEAKNESS MAP
// ────────────────────────────────────────────────────────────────────
sections.push(sectionBar("Section 9 — ICD-10 Weakness Map"));
sections.push(spacer(100));

sections.push(bodyText(
  "Your missed questions mapped to clinical conditions by ICD-10 code, showing which diseases/syndromes appear most frequently in your knowledge gaps."
));

sections.push(subBar("How to read it"));
sections.push(spacer(60));

sections.push(bodyText(
  "The \"Misses\" column shows how many of your missed questions involve each condition. Red (3+) means this condition appeared across multiple exam questions that you missed — it's a recurring exam theme."
));

sections.push(spacer(120));
sections.push(bodyText(
  "The \"Clinical Domain\" column groups codes by organ system (e.g., Circulatory, Endocrine/Metabolic) — useful for seeing whether gaps cluster in a single specialty area."
));

sections.push(actionCallout(
  "For any condition with 3+ misses, go to the matching article in your High-Yield Reading List (Section 10). If no article is listed for it, search your clinical guidelines or UpToDate for that specific condition."
));

sections.push(new PageBreak());

// ────────────────────────────────────────────────────────────────────
// SECTION 10 — HIGH-YIELD READING LIST
// ────────────────────────────────────────────────────────────────────
sections.push(sectionBar("Section 10 — High-Yield Reading List"));
sections.push(spacer(100));

sections.push(bodyText(
  "A curated reading list in two tiers, drawn from the ITE Knowledge Base of 1,998 clinical guidelines and review articles."
));

sections.push(subBar("The two tiers"));
sections.push(spacer(60));

sections.push(...bulletList([
  "\"Targeted to Your Exam\" (navy header): Articles specifically linked to questions you missed on this exam. These articles cover the clinical material behind your actual exam misses. Read these first.",
  "\"High-Yield for All Residents\" (blue header): The most frequently cited articles in the ABFM exam database — cornerstone references that appear repeatedly across all FM residents' exams. These are foundational reading regardless of your specific gaps."
]));

sections.push(spacer(120));
sections.push(subBar("The summary table columns", BLUE));
sections.push(spacer(60));

sections.push(...bulletList([
  "Citations: How many times this article has been cited across all ITE years. Higher = more likely to appear on future exams.",
  "Exam Yrs: How many different exam years referenced this article. Cited in 4+ years = very stable exam topic.",
  "Weak Links: How many of your specific missed questions this article covers.",
  "Status: Whether the guideline is current. ✓ Current = safe to use. ⚠ Updated = a newer guideline may exist — verify before relying on it."
]));

sections.push(spacer(120));
sections.push(bodyText(
  "The QID glossary under each article shows the exact questions from your exam that this article covers. If you read that article, you're directly addressing those question topics."
));

sections.push(actionCallout(
  "Read every article in the \"Targeted\" tier before your next exam. Use the QID glossary to connect each article back to your actual exam misses. For \"High-Yield\" articles, start with the highest citation count and work down."
));

sections.push(new PageBreak());

// ────────────────────────────────────────────────────────────────────
// PART B — PRACTICE QUESTIONS
// ────────────────────────────────────────────────────────────────────
sections.push(sectionBar("Part B — Practice Questions (with Answers)"));
sections.push(spacer(100));

sections.push(bodyText(
  "A curated set of practice questions from the ITE + AAFP BRQ database, selected specifically for your weak areas."
));

sections.push(subBar("How they were selected"));
sections.push(spacer(60));

sections.push(bodyText(
  "Questions were chosen by matching your weak areas (from Sections 4, 6, 7) to the ITE Knowledge Base. The \"Targeting\" column shows which weak area drove the selection:"
));

sections.push(spacer(80));

sections.push(...bulletList([
  "Blue text = Blueprint category match (e.g., \"Chronic Care\")",
  "Green text = Body system match (e.g., \"Cardiovascular\")",
  "Purple text = Crossover match (e.g., \"Cardiovascular × Acute Care\")",
  "Amber text = Concept fingerprint match"
]));

sections.push(spacer(120));
sections.push(bodyText(
  "The \"Match\" column shows how tightly matched the question is: Direct Match = the question is closely linked to one of your actual missed topics. ICD-10 Sibling = the question tests a clinically related condition within the same disease family. Vector Match = the question is semantically similar to your weak areas."
));

sections.push(spacer(120));
sections.push(bodyText(
  "Questions are ordered by relevance — #1 is the highest priority for your specific gaps."
));

sections.push(actionCallout(
  "Complete all practice questions BEFORE checking answers. Treat it like a mini-exam. Then review the explanation for every question you got wrong — not just to get the right answer, but to identify the underlying knowledge gap. The goal is to build a pattern, not memorize individual answers."
));

sections.push(new PageBreak());

// ────────────────────────────────────────────────────────────────────
// APPENDIX — MISSED EXAM ITEMS
// ────────────────────────────────────────────────────────────────────
sections.push(sectionBar("Appendix — Missed Exam Items"));
sections.push(spacer(100));

sections.push(bodyText(
  "A reference list of every question you missed on the actual exam, with QID and blueprint/body system labels. This lets you look up any specific question in your exam materials."
));

sections.push(actionCallout(
  "Use the QIDs here to cross-reference with your actual exam document (provided separately). If a missed item was also listed as an Easy Miss in Section 6, prioritize it for review."
));

sections.push(new PageBreak());

// ────────────────────────────────────────────────────────────────────
// CLOSING SECTION — YOUR STUDY PLAN SUMMARY
// ────────────────────────────────────────────────────────────────────
sections.push(sectionBar("Building Your Study Plan"));
sections.push(spacer(100));

sections.push(bodyText(
  "Synthesize the report into a prioritized action sequence:"
));

sections.push(spacer(120));

const studySteps = [
  "Address Easy Misses (Section 6 — QIDs listed)",
  "Work Rank #1 from Low-Hanging Fruit (Section 7)",
  "Read all Targeted articles (Section 10)",
  "Complete practice questions in order (Part B)",
  "Re-examine Persistent gaps (Section 3b) with a different study approach",
  "Read High-Yield articles in citation-count order (Section 10)",
  "Review concept fingerprint drugs (Section 8)"
];

const stepParagraphs = studySteps.map((step, idx) => {
  return new Paragraph({
    spacing: { before: 80, after: 80 },
    indent: { left: 360, hanging: 360 },
    children: [
      new TextRun({ text: `${idx + 1}. ${step}`, font: FONT, size: 18, color: DGRAY })
    ]
  });
});

sections.push(...stepParagraphs);

sections.push(spacer(200));

sections.push(new Paragraph({
  spacing: { before: 200, after: 0 },
  border: { top: { style: BorderStyle.SINGLE, size: 6, color: NAVY } },
  children: []
}));

sections.push(spacer(120));

sections.push(new Paragraph({
  spacing: { before: 80, after: 80 },
  alignment: AlignmentType.CENTER,
  children: [new TextRun({
    text: "Remember: This guide is a companion to your ITE Score Analysis report. Use them together to build a focused study plan that addresses your specific knowledge gaps.",
    font: FONT,
    size: 18,
    italics: true,
    color: MGRAY
  })]
}));

// ═══════════════════════════════════════════════════════════════════
// CREATE OUTPUT DIRECTORY
// ═══════════════════════════════════════════════════════════════════

const scriptDir = path.resolve(__dirname);
const outputDir = path.join(scriptDir, "..", "docs");

if (!fs.existsSync(outputDir)) {
  try {
    fs.mkdirSync(outputDir, { recursive: true });
  } catch (err) {
    console.error(`ERROR: Cannot create output directory: ${outputDir}`);
    process.exit(1);
  }
}

const outputPath = path.join(outputDir, "ITE_Report_Guide_Resident.docx");

// ═══════════════════════════════════════════════════════════════════
// CREATE DOCUMENT WITH FOOTER
// ═══════════════════════════════════════════════════════════════════

const doc = new Document({
  sections: [{
    properties: {
      margins: {
        top: MARGIN_IN,
        bottom: MARGIN_IN,
        left: MARGIN_IN,
        right: MARGIN_IN
      }
    },
    children: sections,
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
              new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 18, color: MGRAY })
            ]
          })
        ]
      })
    }
  }]
});

// ═══════════════════════════════════════════════════════════════════
// WRITE DOCUMENT
// ═══════════════════════════════════════════════════════════════════

Packer.toBuffer(doc).then(buffer => {
  try {
    fs.writeFileSync(outputPath, buffer);
    console.log(`\n✓ Resident Guide generated successfully`);
    console.log(`  Output: ${outputPath}`);
  } catch (err) {
    console.error(`ERROR: Failed to write output file: ${err.message}`);
    process.exit(1);
  }
}).catch(err => {
  console.error(`ERROR: Failed to generate DOCX: ${err.message}`);
  process.exit(1);
});
