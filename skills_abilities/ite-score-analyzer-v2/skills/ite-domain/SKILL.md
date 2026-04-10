---
description: >
  ITE Score Analysis domain knowledge for the Family Medicine In-Training Examination.
  Use when the user asks about "ITE scores", "ABFM results", "blueprint categories",
  "body system performance", "scaled scores", "pass probability", "practice questions",
  "exam analysis", "PGY level", "cohort comparison", or any related score interpretation task.
  Also triggers when working with ite_intelligence.db, ABFM score report PDFs, or any
  file in the ITE score analysis pipeline in 03_module.3_analyst/.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent, AskUserQuestion, TodoWrite
---

# ITE Score Analysis — Domain Knowledge

## What This System Does

Processes ABFM In-Training Examination score report PDFs for Family Medicine residents and produces:
1. A **10-section analysis DOCX** with performance breakdown + targeted practice questions
2. An **exam DOCX** (questions only, no answers) + answer key
3. An **analysis_v2.json** (machine-readable full output)

The pipeline is deterministic and locked. What changes over time is the *analytics content* — which sections appear, what thresholds define weakness, how many questions to generate. All of that is controlled by `report_config.json` (see references/report_config_spec.md).

---

## Pipeline Architecture

```
ABFM PDFs (blueprint + body system)
         │
         ▼
  ite_analyze_v2.py      ← orchestrator, locked steps
         │
         ├─→ ite_analyzer_v3.py     ← 9 analysis layers (Python)
         │         │
         │         └─→ ite_intelligence.db  ← question bank + article library
         │
         └─→ ite_report_builder_v2.js  ← DOCX output (Node.js)
```

**The pipeline steps are locked.** Do not modify the sequence. What you can tune is `report_config.json`.

---

## Path Constants (Windows)

```
PYTHON      = C:\Users\mpsch\AppData\Local\Programs\Python\Python312\python.exe
PROJECT_ROOT= C:\Users\mpsch\Desktop\board_prep_intel
SCRIPTS_DIR = C:\Users\mpsch\Desktop\board_prep_intel\03_module.3_analyst\scripts
REPORTS_DIR = C:\Users\mpsch\Desktop\board_prep_intel\03_module.3_analyst\reports
RAW_PDFS    = C:\Users\mpsch\Desktop\board_prep_intel\03_module.3_analyst\resident_data
DB_PATH     = C:\Users\mpsch\Desktop\board_prep_intel\00_database\db\ite_intelligence.db
CONFIG      = C:\Users\mpsch\Desktop\board_prep_intel\03_module.3_analyst\scripts\ite_parser_config.json
REPORT_CFG  = C:\Users\mpsch\Desktop\board_prep_intel\03_module.3_analyst\scripts\report_config.json
```

---

## Input PDFs

The ABFM provides two separate score reports per resident:

| PDF | Header Text | What It Contains |
|-----|-------------|-----------------|
| Blueprint Performance | "Item Performance Report By Blueprint Category" | Performance by FM blueprint domain |
| Body System Performance | "Item Performance Report By Body System Category" | Performance by organ system |

Both are required for a full analysis run.

**Source folder:** `resident_data/` — drop PDFs here before running.
**Naming convention (for tracking):** `{LastName}_{Year}_blueprint.pdf` / `{LastName}_{Year}_bodysystem.pdf`

---

## CLI Command (Single Resident)

```cmd
"C:\Users\mpsch\AppData\Local\Programs\Python\Python312\python.exe" ^
  "C:\Users\mpsch\Desktop\board_prep_intel\03_module.3_analyst\scripts\ite_analyze_v2.py" ^
  --blueprint "{blueprint_pdf_path}" ^
  --bodysystem "{bodysystem_pdf_path}" ^
  --db "C:\Users\mpsch\Desktop\board_prep_intel\00_database\db\ite_intelligence.db" ^
  --config "C:\Users\mpsch\Desktop\board_prep_intel\03_module.3_analyst\scripts\ite_parser_config.json" ^
  --output-dir "C:\Users\mpsch\Desktop\board_prep_intel\03_module.3_analyst\reports\{LastName}_{Year}" ^
  --pgy-level {1-4} ^
  --plugins "concept,icd10"
```

**Dependencies (one-time install, Windows):**
```cmd
pip install pymupdf
cd "C:\Users\mpsch\Desktop\board_prep_intel\03_module.3_analyst\scripts" && npm install docx
```

---

## Key Parameters

| Arg | Values | Default | Effect |
|-----|--------|---------|--------|
| `--pgy-level` | 1, 2, 3, 4 | 3 | Adjusts expected performance benchmarks |
| `--plugins` | `concept`, `icd10`, or both | `concept,icd10` | Enrichment layers to run |

---

## Output Files

All outputs land in `reports/{LastName}_{Year}/`:

| File | Description |
|------|-------------|
| `analysis_v2.json` | Full analysis data — machine-readable, used for cohort comparison |
| `ITE_{year}_v2_Analysis_{name}.docx` | 10-section report with practice questions |
| `ITE_{year}_v2_Exam_{name}.docx` | Exam version (questions only) + answer key |

---

## The 9 Analysis Layers

1. **Score Overview** — overall %, scaled score, percentile, pass tier
2. **Blueprint Analysis** — performance by ABFM blueprint category
3. **Body System Analysis** — performance by organ system
4. **Weak Area Identification** — items below weakness threshold (see report_config.json)
5. **Priority Matrix** — weak areas ranked by exam blueprint weight × deficit magnitude
6. **Easy Miss Detection** — high-difficulty items the resident got wrong (yield opportunities)
7. **Practice Question Generation** — linked questions from ite_intelligence.db by weak area
8. **ICD-10 Crosswalk** — maps weak areas to ICD-10 codes → links to relevant articles (if icd10 plugin active)
9. **Concept Tag Enrichment** — surfaces related clinical concepts (if concept plugin active)

---

## Cohort Analysis

When multiple residents have been analyzed (each has `analysis_v2.json`), the cohort comparison identifies:
- **Program-level gaps** — weak areas shared by >50% of residents (curriculum issue)
- **Individual gaps** — weak in only 1 resident (individual study target)
- **Universal strengths** — all residents strong (curriculum working)

All `analysis_v2.json` files live under `reports/`. List them with:
```cmd
dir "C:\Users\mpsch\Desktop\board_prep_intel\03_module.3_analyst\reports\*\analysis_v2.json" /S /B
```

---

## Modifying Analytics Output

**The pipeline steps are locked.** If you want to change *what the report shows* — thresholds, section visibility, question counts — edit `report_config.json`.

See `references/report_config_spec.md` for the full spec and example edits.

---

## Category String Validation

**Read `references/blueprint_categories.md` before diagnosing any parsing issue.**

Key facts:
- Blueprint categories: 5 strings, perfectly stable 2018–2025 (ITE + AAFP both)
- Body system categories: stable 2018–2023 and 2025; **2024 had 3 renamed categories** (Injuries/Musculoskeletal, Psychiatric/Behavioral, Sexual and Reproductive) that are valid only for 2024 score reports
- If a parsed category string doesn't match the canonical list → parsing failure, diagnose before running analysis

---

## Troubleshooting

**If the pipeline fails**, check `references/troubleshooting.md` before asking the user to re-run.

10 documented failure modes covering:
- Missing Python/npm dependencies
- `python` command not found (always use full path)
- Empty weak areas (parse mismatch vs. genuinely strong performance)
- Unicode errors in resident names
- Wrong PDF type provided
- Missing `report_config.json`
- Old v1 analysis files skipped by cohort compare

---

## DB Schema (Quick Reference)

See `references/db_schema.md` for full table definitions.

Key tables used by the analyzer:
- `ite_questions` — 1,629 questions (2018–2025), with blueprint, body_system, difficulty, correct_rate
- `aafp_questions` — 1,221 AAFP BRQ questions
- `articles` — 1,985 articles with tier, category, citation_count
- `qid_art_xref` — 2,470 question→article links
- `article_icd10` — 4,020 article→ICD-10 mappings
- `question_icd10` — 5,218 question→ICD-10 mappings
- `clinical_pathways` — 3,971 diagnosis→article pathway rows
