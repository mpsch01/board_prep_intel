---
description: >
  Analyze a resident's ITE score report PDFs and generate a targeted study report.
  Right-click a blueprint or body system PDF to trigger this command.
  Also triggers when the user says "analyze ITE", "run the score pipeline", "process score reports".
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent, AskUserQuestion, TodoWrite
argument-hint: [blueprint.pdf] [bodysystem.pdf]
---

# Analyze ITE Score Reports — Single Resident

Run the full ITE Score Analysis Pipeline on one resident's ABFM score report PDFs.

## Step 1: Locate Input PDFs

There are **3 PDFs per resident per year**:

| PDF | How to identify |
|-----|----------------|
| Score Report | 2-page ABFM PDF; page 2 has "Scaled Score:" in header and blueprint/body system tables |
| Blueprint Performance | 1-page item grid with columns: Acute Care, Chronic Care, Emergent/Urgent, Preventive, Foundations |
| Body System Performance | 1-page item grid with columns for organ systems |

If arguments provided via right-click or $ARGUMENTS, identify all three. If not, list available PDFs in the raw PDFs folder:
```
C:\Users\mpsch\Desktop\board_prep_intel\03_module.3_analyst\resident_data\
```

Ask the user to identify which is which if filenames are ambiguous. Suggested naming: `{LastName}_{Year}_score.pdf`, `{LastName}_{Year}_blueprint.pdf`, `{LastName}_{Year}_bodysystem.pdf`.

## Step 2: Read report_config.json

Read the config before proceeding:
```
C:\Users\mpsch\Desktop\board_prep_intel\03_module.3_analyst\scripts\report_config.json
```

Note the active settings — especially `weakness_threshold`, `question_count_per_area`, `pgy_default`, and which sections are enabled. You'll reference these when summarizing results.

## Step 3: Confirm Run Parameters

Extract resident last name and exam year from the PDF filename or ask the user:
- **Resident name** (for output folder naming)
- **PGY level** (1–4; default from `pgy_default` in report_config.json)
- **Plugins** (default from `plugins_default` in report_config.json)

Confirm in one message: "Running {name} ({year}), PGY-{level}, plugins: {plugins} — change anything?"

Wait for confirmation or corrections before proceeding.

## Step 4: Create Output Directory

Output folder:
```
C:\Users\mpsch\Desktop\board_prep_intel\03_module.3_analyst\reports\{LastName}_{Year}\
```

## Step 5: Run the Pipeline

**Provide this command for the user to copy-paste and run locally** (long runtime — user runs it):

```cmd
"C:\Users\mpsch\AppData\Local\Programs\Python\Python312\python.exe" "C:\Users\mpsch\Desktop\board_prep_intel\03_module.3_analyst\scripts\ite_analyze_v2.py" --blueprint "{blueprint_pdf_path}" --bodysystem "{bodysystem_pdf_path}" --score-report "{score_report_pdf_path}" --db "C:\Users\mpsch\Desktop\board_prep_intel\00_database\db\ite_intelligence.db" --config "C:\Users\mpsch\Desktop\board_prep_intel\03_module.3_analyst\scripts\ite_parser_config.json" --output-dir "C:\Users\mpsch\Desktop\board_prep_intel\03_module.3_analyst\reports\{LastName}_{Year}" --pgy-level {pgy_level} --plugins "{plugins}"
```

`--score-report` is optional but strongly recommended — it provides the actual ABFM scaled score, PGY class mean, and standard error, replacing estimated values in the analysis and enabling scaled-score-based longitudinal delta.

Tell the user: "Copy this command, paste it into your terminal, and run it. Come back with the output when it's done."

**One-time dependency install** (if running for the first time):
```cmd
pip install pymupdf
cd "C:\Users\mpsch\Desktop\board_prep_intel\03_module.3_analyst\scripts" && npm install docx
```

## Step 6: Validate Output

After the user pastes the run output, verify:
- `analysis_v2.json` was generated ✅
- `ITE_{year}_v2_Analysis_{name}.docx` was generated ✅
- `ITE_{year}_v2_Exam_{name}.docx` was generated ✅
- Practice question count > 0
- No warnings about empty weak areas

If any of the above fail, diagnose from the error output before asking the user to re-run.

## Step 7: Summarize Findings

Read `analysis_v2.json` from the output directory and summarize:

1. **Score**: Overall % · scaled score · percentile · pass tier
2. **Top 3 weak areas** (by priority matrix rank)
3. **Easy misses** count (if easy_misses section is enabled)
4. **Practice questions** generated (total count)
5. **Longitudinal delta** (if `longitudinal_delta` key is present in the JSON):
   - Report score trajectory vs. last year (n-1) and two years ago (n-2) if available
   - Call out closed gaps (wins), persistent gaps (priority), and new gaps (regressions)
   - If no prior years found — note this is the first-year baseline
6. **Highest-yield action** — the single most impactful study focus

Keep the summary to 5–7 bullet points. The DOCX has the full detail.

Present the output DOCX files as links so the user can open them directly.
