# BATON 050 — Practice Question Year Bias & Year-Over-Year Reporting
**Date:** 2026-04-08  
**Branch:** main  
**Git Hash:** 03334d0  
**Status:** Practice question recency bias FIXED; YoY longitudinal section implemented with deferred robustness work

---

## Session Summary

This session addressed **practice question year bias** (residents were seeing 2024/2025 questions 80%+ of the time) and added **year-over-year longitudinal progress reporting** to DOCX output. Root cause was two-layer: SQL `ORDER BY exam_year DESC` + Python recency bonus both clustering selections. Fixed by removing exam_year ordering, increasing tier limits 20→60, removing recency bonus, and adding current-year exclusion logic.

### What Was Built
1. **Year bias FIX — SQL tier functions**
   - Removed `ORDER BY exam_year DESC` from `_tier1_direct()`, `_tier1b_richseed()`, `_tier2_icd10_sibling()` → now `ORDER BY linked_articles DESC`
   - Increased SQL limits: 20→60 rows per tier (distributes selections across more years)
   - Removed recency_bonus entirely from `_compute_relevance()` in `ite_analyzer_v3.py`
   - Added current_exam_year exclusion: residents don't see their own exam year as practice (type-safe str→int cast)

2. **CLI flags for `ite_analyze_v2.py`**
   - `--skip-reading-list`: sets `SKIP_READING_LIST=1` env var → skips Section 10 in DOCX
   - `--question-count N`: controls practice question count (default 20)

3. **DOCX practice question layout — two-table design**
   - Replaced per-dimension loop with combined tables: single-category dims → 1 table, cross-category (×) dims → separate table
   - Column structure: `["#", "Targeting", "QID", "Blueprint", "Body System", "Source", "Match"]`
   - Helper: `buildPqTable(questions, startNum)` for table rendering
   - Part C exam section: `renderExamSection(questions, label, color)` for per-dimension styling

4. **DOCX Section 3b — Year-over-Year Progress table**
   - Inserted between Executive Summary and Performance Overview
   - Renders `data.longitudinal_delta` from analysis JSON
   - **5-column layout:** Metric | Prior | Current | Change | Weak Area Trajectory
   - **Trajectory coding:**
     - ✔ Closed (GREEN): gap remedied vs prior year
     - ⚠ Persistent (AMBER): gap remained open in both years
     - ▶ New gap (RED): gap appeared only in current year
   - Uses data from `ite_parser.py` `parse_score_report()` (merged into ite_score_analyzer plugin v1.0.0)

5. **DOCX reading list guard**
   - Section 10 gated by `SKIP_READING_LIST` env var
   - Used in Pjetergjoka run (no reading list requested)

6. **Test run: Adona Pjetergjoka 2024 + 2025**
   - Generated DOCXs with 35 practice questions, longitudinal delta, full YoY table
   - Files: `resident_data/ITE_adona_pjetergjoka/`
   - Verified: practice questions span 2018–2025 (no clustering to 2024/2025)
   - Verified: YoY table renders correctly with trajectory coding

7. **Git index corruption — FIXED**
   - NTFS/Linux mount caused 555 "D" staged deletions
   - Resolution: `del .git\index` → `git read-tree HEAD` (CMD)
   - Result: 3 modified files (ite_parser.py, ite_analyzer_v3.py, ite_analyze_v2.py)

---

## DB State

| Table | Rows | Notes |
|-------|------|-------|
| articles | 1,985 | +49 AAFP acquisition (ART-1938–1986) |
| questions | 1,629 | 2018–2025, blueprint 100% |
| aafp_questions | 1,221 | blueprint & concept_tags 100% |
| qid_art_xref | 2,470 | 8-year cross-reference |
| aafp_qid_art_xref | 864 | 52.7% AAFP coverage |
| article_icd10 | 4,020 | vec rebuilt 2026-04-05 |
| question_icd10 | 5,218 | 92.8% ITE coverage (1,512/1,629) |
| aafp_question_icd10 | 4,753 | relevance normalized |
| clinical_pathways | 3,971 | both banks, ART-0002–1985 |
| pubmed_pmid_cache | 344 | Layer 2 seed |
| icd10_vec | 2,219 | OpenAI text-embedding-3-small |
| article_icd10_vec | 1,757 | rebuilt 2026-04-05 |
| question_icd10_vec | 2,747 | rebuilt 2026-04-05 |
| article_currency | 1,985 | 2026-04-07: current:1100, updated:169, check_needed:106, not_indexed:610 |

**Next ART-ID:** ART-1987

---

## PDF Library State

| Tier | Count | Notes |
|------|-------|-------|
| VC_fail | 637 | +7 from 2026-04-08 recovery (exa_pdf_downloader + pmc_oa_downloader) |
| VC_pass | 168 | Passed VC gate (VC_pass/ folder) |
| local_lite | 117 | VC_fail + enriched → local_lite tier |
| right_click | 58 | VC_pass + enriched → right_click tier (SOLE criterion: VC gate + DOCX exists) |
| **Total** | **980** | 14 dupes in _dupe_archive/ |
| AAFP | 15 | citation_files/AAFP/ |
| ITE exams | 16 | 8 years (2018–2025) × MC + critique |

---

## Script Counts

| Module | Category | Count |
|--------|----------|-------|
| M1 | Build scripts (6py) | `build/`: schemas, ingest, PDF tier ops |
| M1 | Maintain scripts (26py) | `maintain/`: reconciliation, gap detection, archival |
| M2 | Python (75py) | core/, engines/, utils/ packages + main.py |
| M2 | JavaScript (6js) | DOCX builder, report templates |
| M3 | Python (14py) | ICD-10 tagging, pathways, trends, score analysis |
| M3 | JavaScript (2js) | Report generation |
| M3 | Config (1 JSON) | report_config.json |

**Key files modified this session:**
- `ite_parser.py` — added parse_score_report() for longitudinal delta parsing
- `ite_analyzer_v3.py` — removed recency_bonus, fixed exam_year exclusion logic
- `ite_analyze_v2.py` — added `--skip-reading-list` and `--question-count` flags
- `ite_report_builder_v2.js` — added YoY table, two-table practice question layout, reading list guard

---

## Deferred Flags

### DEFERRED-YOY-ROBUSTNESS
**Description:** Year-over-year longitudinal section in `ite_report_builder_v2.js` needs more robust implementation.  
**Why deferred:** Current implementation works for the nominal case (2-year resident with scaled scores in both years) but needs edge-case handling.  
**What needs fixing:**
- Missing scaled scores (resident has raw scores only in one year)
- Partial year data (resident took exam late in year, data cut before full exam cycle)
- Multi-year gaps between exams (resident > 2 years out)
- N > 2 year comparisons (3+ years of data)

**Next session action:** Expand `longitudinal_delta` computation in `ite_analyzer_v3.py` to detect these conditions; add null checks and fallback messaging in `renderYoYSection()` in JS.

---

### DEFERRED-PRACTICE-Q-COVERAGE
**Description:** Practice question engine returns 0-question warnings for specific blueprint dimensions.  
**Affected dims:** Foundations, Preventive, Cardiovascular, Respiratory, Sexual and Reproductive, Psychiatric, Behavioral  
**Root cause TBD:** Either insufficient ICD-10 linkage in qid_art_xref or question tagging gaps in blueprint schema.  
**Why deferred:** Needs investigation to determine whether to fix in SQL (add missing questions), Python (improve matching logic), or data (re-tag questions).  
**Next session action:** Query qid_art_xref for these dims; check question_icd10 coverage; compare to overall blueprint population.

---

### DEFERRED-PGY-BENCHMARKS
**Description:** Add PGY 1–4 expected % ranges for performance contextualization.  
**Why deferred:** Awaiting Mikey's input on institutional baseline ranges.  
**Artifact:** Will create `pgy_benchmarks.md` in `key_data_files/` with Mikey's data.  
**Next session action:** Receive data from Mikey → integrate into DOCX rendering logic (Executive Summary).

---

### DEFERRED-AAFP-PDF-RETRY
**Description:** Re-run exa_pdf_downloader against AAFP site when it stabilizes.  
**Status:** AAFP site had intermittent availability during 2026-04-05 recovery run.  
**Action:** Monitor AAFP access; re-run `download_targeted.py` for AAFP articles not yet acquired.

---

### DATABASE_GUIDE.md relocation (CARRY FROM 049)
**Description:** Finalize git add/rm to register DATABASE_GUIDE.md as a rename.  
**Current state:** File moved but git index shows as [D] deletion + [A] addition instead of [R] rename.  
**Action:** `git rm` old path, `git add` new path, verify as [R]ename in git status.

---

## Next Steps

### Immediate (BLOCKING)
1. **Git commit** — Stage and commit modified files:
   - `ite_parser.py` (parse_score_report added)
   - `ite_analyzer_v3.py` (recency_bonus removed, year bias fix)
   - `ite_analyze_v2.py` (CLI flags added)
   - `ite_report_builder_v2.js` (YoY table + practice Q layout)
   - Commit message: `fix: remove practice question year bias; add YoY longitudinal reporting [BUG-048-01/02/03]`

2. **DOCX review — Mikey** — Open and verify:
   - Pjetergjoka_2024 and Pjetergjoka_2025 DOCXs
   - Section 3b YoY table: trajectory coding (✔/⚠/▶), correct metric/prior/current values
   - Practice question tables: mixed-year distribution (no 80%+ clustering to 2024/2025)
   - Reading list: correctly suppressed (--skip-reading-list flag)
   - If satisfied: sign off for deployment to production analysis runs

### Short-term (NEXT SESSION)
3. **DEFERRED-YOY-ROBUSTNESS** — Implement edge-case handling in longitudinal delta logic (priority: high, impacts all multi-year residents)

4. **DEFERRED-PRACTICE-Q-COVERAGE** — Investigate 0-question warnings for Foundations/Preventive/Cardiovascular/Respiratory/Sexual and Reproductive/Psychiatric/Behavioral (priority: high, impacts practice Q relevance for weak areas)

5. **DATABASE_GUIDE.md relocation** — Finalize git rename registration (priority: medium, housekeeping)

6. **Test Agents B & C** — Validate agent templates in next housekeeping run (priority: medium)

7. **DEFERRED-AAFP-PDF-RETRY** — Re-run PDF downloader when AAFP site stabilizes (priority: low, supplementary data)

---

## Locked Rules Reminder

No new rule additions this session. Active locked rules:

1. **Fix the data, not the code** — Clean upstream rather than complicating scripts
2. **VC gate = sole criterion** for right_click tier (DB membership insufficient)
3. **Source data protected** — DB + PDFs + VC gate survive everything; derived files disposable
4. **Dynamic paths only** — `SCRIPT_DIR = Path(__file__).resolve().parent; PROJECT_ROOT = SCRIPT_DIR.parent.parent`
5. **No de novo JS** (note: rule relaxed per feedback; use JS when needed, flag if multilingual clutter accumulates)
6. **BATON first** — Read active BATON before any work
7. **QC after every integration** — Schema-level column-by-column population comparison
8. **Git via Desktop Commander** — Python subprocess or direct CLI; cannot `rm` NTFS files
9. **`shutil.rmtree` is BANNED** — Use explicit file-by-file deletion or PowerShell Remove-Item
10. **Strategy 0 in every enricher** — Codon parse first matching strategy
11. **Schemas before scripts** — SQL `CREATE TABLE` defined before build scripts

---

## Git State

| Item | Value |
|------|-------|
| Current branch | main |
| Latest commit | 03334d0 |
| Staged changes | 3 files: ite_parser.py, ite_analyzer_v3.py, ite_analyze_v2.py, ite_report_builder_v2.js |
| Unstaged changes | None (git index recovered from NTFS/Linux corruption) |
| Remote | `https://github.com/mpsch01/board_prep_intel` (private) |
| Last commit message | BUG-047-01/02/03 fixes (from BATON 049) |
| .gitignore strategy | Code + docs on GitHub; binaries (*.db, *.pdf, extracted_json/, resident_data/) local/Drive |

**To-do before next session:** Commit staged files with BUG-048 tag.

---

## Session Metrics

- **Bugs fixed:** 3 (BUG-048-01: year bias in SQL order; BUG-048-02: recency bonus clustering; BUG-048-03: current-year exclusion)
- **Features added:** 2 (YoY longitudinal table; practice Q two-table layout)
- **CLI improvements:** 2 flags (--skip-reading-list, --question-count)
- **Residents analyzed:** 1 (Adona Pjetergjoka, 2 years)
- **Test run DOCXs:** 4 (2024 + 2025 pair, Hopkins + Sarkar from prior session)
- **Infrastructure fixes:** 1 (git index corruption recovery)

---

## For Next Claude Instance

**Start here:**
1. Read this BATON first (you're reading it)
2. Check git status: `git status` (should show 3 modified files, ready to commit)
3. Coordinate with Mikey on DOCX review feedback
4. Prioritize DEFERRED-PRACTICE-Q-COVERAGE investigation (impacts weak area targeting)
5. If Mikey approves, commit and deploy to production analysis pipeline

**Key files to touch next session:**
- `02_module.2_processor/ite_analyzer_v3.py` (longitudinal delta edge-case handling)
- `02_module.2_processor/ite_report_builder_v2.js` (YoY section robustness)
- `03_module.3_analyst/query_functions.py` (practice Q 0-question dim investigation)

**Context shortcuts:**
- Active plugin: `ite-score-analyzer-v2` (skills_abilities/) — parse_score_report() in ite_parser.py
- VC gate: `key_data_files/session_hy_inserts_v7.json` (352 citations)
- Database: `00_database/db/ite_intelligence.db` (source of truth, protected)
