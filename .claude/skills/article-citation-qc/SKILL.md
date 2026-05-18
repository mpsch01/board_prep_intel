---
name: article-citation-qc
description: >
  QC audit of the ITE Intelligence articles table against ground-truth ITE critique PDFs
  (2018–2025). Detects broken article titles, author parsing artifacts, USPSTF umbrella
  consolidation errors, and QID-article linkage mismatches. Produces a structured QC
  report AND ready-to-run SQL UPDATE statements for confirmed fixes. ALWAYS trigger this
  skill when the user mentions: article labeling issues, citation QC, USPSTF umbrella
  problem, article verification, DB article integrity, broken/truncated titles, wrong
  author, mislabeled articles, "articles are wrong", or any concern about the quality or
  accuracy of the articles table or QID-article linkages. Also trigger proactively before
  re-running resident analyses if article data integrity hasn't been verified recently.
---

# Article Citation QC Skill

## What this skill does

Runs a full quality audit of the `articles` table in `ite_intelligence.db` against the
ground-truth citations embedded in the ITE critique PDFs (8 years: 2018–2025). Outputs:

1. **QC report** (`article_qc_report.md`) — findings by issue type with severity ratings.
2. **SQL fix file** (`article_qc_fixes.sql`) — ready-to-review UPDATE statements for
   TRUNC_TITLE, AUTHOR_ARTIFACT, and high-confidence QID_MISMATCH (match_score=1.0).
   Never auto-applied — Mikey reviews and runs manually.

---

## Project paths

```
PROJECT_ROOT = board_prep_intel/
DB           = PROJECT_ROOT/00_database/db/ite_intelligence.db
CRITIQUE_DIR = PROJECT_ROOT/01_module.1_warehouse/ite_exams/
STAGING_DIR  = PROJECT_ROOT/02_module.2_processor/outputs/
EXTRACTOR    = PROJECT_ROOT/02_module.2_processor/scripts/extract_ite_critique_refs.py
QC_SCRIPT    = <this_skill>/scripts/run_citation_qc.py
SQL_SCRIPT   = <this_skill>/scripts/generate_sql_fixes.py
OUTPUT_DIR   = PROJECT_ROOT/03_module.3_analyst/outputs/article_qc/
```

Use `db_connect.py` in `03_module.3_analyst/scripts/` for all DB reads.
All scripts use dynamic path resolution (SCRIPT_DIR / PROJECT_ROOT pattern).

---

## Workflow

### Phase 1 — Extract missing critique refs (run first, always)

For each year 2018–2025, check if `STAGING_DIR/YYYY_critique_refs_staging.json` exists.
For any missing years, tell the user:

> "I need you to run these extraction commands — one per missing year.
>  Run each from `PROJECT_ROOT/02_module.2_processor/scripts/`:"

```bash
python extract_ite_critique_refs.py --pdf ../../01_module.1_warehouse/ite_exams/YYYY_critique.pdf --year YYYY
```

**Do NOT use `--commit`.** Staging mode only — no DB writes during extraction.

Wait for the user to confirm the extractions ran before proceeding.

2024 and 2025 are already extracted. Typical missing years: 2018–2023.

> If a critique PDF is missing, note it and proceed with available years. The QC
> report will show which years were included.

### Phase 2 — Run QC checks

From `PROJECT_ROOT/03_module.3_analyst/scripts/`:

```bash
python <skill>/scripts/run_citation_qc.py \
  --staging-dir ../../02_module.2_processor/outputs/ \
  --output-dir ../../03_module.3_analyst/outputs/article_qc/
```

This writes `qc_results.json` to OUTPUT_DIR.

See `references/qc_rules.md` for check definitions. Summary:

| Check | Severity | Auto-SQL? |
|-------|----------|-----------|
| TRUNC_TITLE | MEDIUM | Yes — both colon-split and page-range artifacts |
| AUTHOR_ARTIFACT | MEDIUM | Yes — parser stop-word fragments ("Final", "US", "American", etc.) |
| QID_MISMATCH | HIGH | Yes — match_score=1.0 only; fuzzy cases report-only |
| UNMATCHED_REF | MEDIUM | No — report only |
| UMBRELLA | HIGH/MEDIUM | No — report only (needs human triage) |
| NULL_CLEAN_REF | LOW | No — report only |

### Phase 3 — Generate SQL fixes

```bash
python <skill>/scripts/generate_sql_fixes.py \
  --qc-results ../../03_module.3_analyst/outputs/article_qc/qc_results.json \
  --output-dir ../../03_module.3_analyst/outputs/article_qc/
```

Writes `article_qc_fixes.sql` to OUTPUT_DIR.

### Phase 4 — Generate the QC report

Read `qc_results.json` and write `article_qc_report.md` to OUTPUT_DIR.

**Report structure:**

```markdown
# Article Citation QC Report
Generated: [date] | Years covered: [list] | Total findings: N

## Executive Summary
| Check | Count | Severity |
...

## TRUNC_TITLE Findings (N)
[table: article_id | current title | corrected title | citation_count]

## AUTHOR_ARTIFACT Findings (N)
[table: article_id | bad author | corrected author | source type]

## QID_MISMATCH Findings (N)
### Exact-match (SQL-eligible, N)
[table: qid | exam_year | DB article | critique says | citation excerpt]

### Fuzzy-match (manual review, N)
[same columns]

## UMBRELLA Findings (N)
[table: article_id | title | citation_count | unique_years | blueprint categories | body systems]

## UNMATCHED_REF Findings (N)
[table: qid | exam_year | critique citation]

## Years with Missing Staging JSONs
[list any years skipped]

## Recommended Next Steps
1. Run article_qc_fixes.sql after review
2. Manually triage UMBRELLA articles
3. Re-extract missing years (if any)
4. Re-run resident analyses after fixes applied
```

---

## After generating outputs

Present `article_qc_report.md` and `article_qc_fixes.sql` to Mikey with:
- Total HIGH severity finding count (QID_MISMATCH)
- Total SQL statements generated
- Any UMBRELLA articles that look most suspicious (highest citation_count spanning most diverse topics)

**Never apply SQL automatically.** Always present for review first.

---

## Locked rules that apply here

- Source data is protected. DB is never modified automatically.
- Fix the data, not the code. If extraction fails for one year, note it and continue.
- QC after integration: after any fixes are applied, remind Mikey to re-run
  `test_v3_changes.py` and spot-check a resident analysis.
