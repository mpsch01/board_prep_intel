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
2. **SQL fix file** (`article_qc_fixes.sql`) — three sections: TRUNC_TITLE UPDATEs,
   AUTHOR_ARTIFACT UPDATEs, and QID_XREF_REBUILD (DELETE + re-INSERT per QID from
   critique ground truth). Never auto-applied — Mikey reviews and runs manually.
3. **PDF lookup patch** (`pdf_lookup_patch.sql`) — optional; for QIDs the extractor
   missed entirely; references manually read from the PDFs.
4. **Missing article INSERTs** (`add_missing_articles.sql`) — optional; for citations
   with no DB record; auto-parses and assigns next ART-ID.

---

## Project paths

```
PROJECT_ROOT  = board_prep_intel/
DB            = PROJECT_ROOT/00_database/db/ite_intelligence.db
CRITIQUE_DIR  = PROJECT_ROOT/01_module.1_warehouse/ite_exams/
STAGING_DIR   = PROJECT_ROOT/02_module.2_processor/outputs/
EXTRACTOR     = PROJECT_ROOT/02_module.2_processor/scripts/extract_ite_critique_refs.py
QC_SCRIPT     = <this_skill>/scripts/run_citation_qc.py
SQL_SCRIPT    = <this_skill>/scripts/generate_citation_sql.py   <- PRIMARY (supersedes generate_sql_fixes.py)
PATCH_SCRIPT  = <this_skill>/scripts/pdf_lookup_patch.py
INSERT_SCRIPT = <this_skill>/scripts/add_missing_articles.py
OUTPUT_DIR    = PROJECT_ROOT/03_module.3_analyst/outputs/article_qc/
```

All scripts use dynamic path resolution (SCRIPT_DIR / PROJECT_ROOT pattern).
`generate_sql_fixes.py` is kept for reference but **superseded** by `generate_citation_sql.py`.

---

## Workflow

### Phase 1 — Verify staging JSONs exist (run first, always)

All 8 years (2018–2025) should already have staging JSONs at:
`STAGING_DIR/YYYY_critique_refs_staging.json`

Check that all 8 files exist. If any are missing, re-extract the missing years:

> "I need you to run these extraction commands — one per missing year.
>  Run each from `PROJECT_ROOT/02_module.2_processor/scripts/`:"

```bash
python extract_ite_critique_refs.py --pdf ../../01_module.1_warehouse/ite_exams/YYYY_critique.pdf --year YYYY
```

**Do NOT use `--commit`.** Staging mode only — no DB writes during extraction.

Wait for the user to confirm before proceeding.

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
| QID_MISMATCH | HIGH | Yes — all match levels included; exact-match rows labeled |
| UNMATCHED_REF | MEDIUM | No — report only; route to acquisition queue (see Phase 7) |
| UMBRELLA | HIGH/MEDIUM | No — report only (needs human triage) |
| NULL_CLEAN_REF | LOW | No — report only |

### Phase 3 — Generate SQL fixes (generate_citation_sql.py)

```bash
python <skill>/scripts/generate_citation_sql.py \
  --qc-results ../../03_module.3_analyst/outputs/article_qc/qc_results.json \
  --staging-dir ../../02_module.2_processor/outputs/ \
  --output-dir ../../03_module.3_analyst/outputs/article_qc/
```

Writes `article_qc_fixes.sql` to OUTPUT_DIR. The SQL file has **three sections**:

**Section 1 — TRUNC_TITLE**: `UPDATE articles SET title = '...' WHERE article_id = '...'`
  for each article whose title field is a fragment of the full title in clean_ref.

**Section 2 — AUTHOR_ARTIFACT**: `UPDATE articles SET author1 = '...' WHERE article_id = '...'`
  for each article whose author1 is a parser stop-word (e.g. "Final", "US", "American").

**Section 3 — QID_XREF_REBUILD**: For every QID that appears in any staging JSON with at
  least one matched reference:
  - `DELETE FROM qid_art_xref WHERE qid = '...' AND exam_year = NNNN`
  - `INSERT OR IGNORE INTO qid_art_xref (...)` for every matched reference (exact AND fuzzy)

  QIDs with NO matched references in any staging JSON are left untouched — their existing
  DB link is preserved as a fallback (listed as comments in the "BACKUP" section).

  This is a **faithful transcript** rebuild: multi-reference per QID reflecting actual
  critique content, not single-article-per-QID consolidation.

> REVIEW BEFORE RUNNING. Never auto-apply. Run in DB Browser using SAVEPOINT per section.

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
Note: These are acquisition queue entries — see Phase 7.

## Years with Missing Staging JSONs
[list any years skipped]

## Recommended Next Steps
1. Run article_qc_fixes.sql after review (Sections 1-3)
2. For parser-missed QIDs: run pdf_lookup_patch.py -> review pdf_lookup_patch.sql
3. For UNMATCHED_REF: route to exa_research_search acquisition pipeline (Phase 7)
4. Manually triage UMBRELLA articles
5. Re-run resident analyses after all fixes applied
```

### Phase 5 — Parser-missed QIDs: pdf_lookup_patch.py [OPTIONAL]

Use when the extractor failed to parse a specific QID's references entirely (not a match
failure — a parser gap). References are read directly from the critique PDFs and hardcoded
into the script's `ITEMS` dict.

```bash
cd PROJECT_ROOT/03_module.3_analyst/scripts/
python <skill>/scripts/pdf_lookup_patch.py
```

Output: `03_module.3_analyst/outputs/article_qc/pdf_lookup_patch.sql`

The script uses exact prefix match against `articles.clean_ref`. Refs found in DB get
linked via INSERT into qid_art_xref. Refs NOT found are flagged as `MISSING — not in DB`
(library gaps — route to Phase 6).

> To add new QIDs: open `pdf_lookup_patch.py` and add entries to the `ITEMS` dict.
> Key = (qid, year), value = list of raw citation strings read from the PDF.

### Phase 6 — Add missing articles: add_missing_articles.py [OPTIONAL]

Use when UNMATCHED_REF findings or pdf_lookup_patch MISSING items represent citations
that are genuinely not in the DB and need to be inserted as new article records.

```bash
cd PROJECT_ROOT/03_module.3_analyst/scripts/
python <skill>/scripts/add_missing_articles.py
```

Output: `03_module.3_analyst/outputs/article_qc/add_missing_articles.sql`

The script:
1. Normalizes punctuation and fuzzy-matches each citation against all existing articles
   (similarity >= 0.88 -> links to existing record, no INSERT needed)
2. For genuinely new citations -> generates `INSERT INTO articles (...)` with auto-assigned
   ART-ID (reads next available from DB at runtime)
3. Generates `DELETE FROM qid_art_xref` + `INSERT OR IGNORE INTO qid_art_xref` for every
   resolved article

> To add new missing refs: open `add_missing_articles.py` and add entries to `MISSING_REFS`.
> Key = (qid, year), value = list of full citation strings from the PDF.

> IMPORTANT: After running add_missing_articles.sql, update `Next ART-ID` in
> CLAUDE.md and README.json to reflect the new maximum.

### Phase 7 — UNMATCHED_REF Acquisition Queue [ARCHITECTURAL PRINCIPLE — BATON 058]

**Locked principle:** UNMATCHED_REF citations are NOT data errors — they are
**acquisition queue entries**. Each represents a guideline cited on the exam that
isn't in the library yet. Never discard; always acquire.

Workflow:
1. Collect all UNMATCHED_REF rows from the QC report (qid, exam_year, critique citation)
2. For each citation, run the `exa-research-search` skill to locate the paper/guideline
3. If found: add to DB via `add_missing_articles.py` (Phase 6 above)
4. If not found: log in BATON deferred flags as DEFERRED-QID-XREF-LIBRARY-GAPS

---

## After generating outputs

Present `article_qc_report.md` and `article_qc_fixes.sql` to Mikey with:
- Total HIGH severity finding count (QID_MISMATCH exact + fuzzy)
- Total SQL statements generated (TRUNC_TITLE + AUTHOR_ARTIFACT + QID_XREF_REBUILD inserts)
- Any UMBRELLA articles that look most suspicious (highest citation_count, most diverse topics)
- Count of UNMATCHED_REF entries (acquisition queue backlog)

**Never apply SQL automatically.** Always present for review first.

---

## Locked rules that apply here

- Source data is protected. DB is never modified automatically.
- Fix the data, not the code. If extraction fails for one year, note it and continue.
- QC after integration: after any fixes are applied, remind Mikey to re-run
  `test_v3_changes.py` and spot-check a resident analysis.
- UNMATCHED_REF is never a discard — always an acquisition signal.
- Next ART-ID must be updated in CLAUDE.md + README.json after any add_missing_articles run.
