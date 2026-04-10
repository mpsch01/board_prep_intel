# BATON 052 — 2026-04-10 — Psychogenic Retirement

**Active Session Handoff Document for board_prep_intel**

---

## Session Overview

| Item | Value |
|------|-------|
| **Date** | 2026-04-10 |
| **Previous BATON** | BATON_active_051_20260409_module5_housekeeping.md |
| **Git Hash (pre-commit)** | 8fb7549 |
| **Branch** | main |
| **Primary Goal** | Close DEFERRED-PRACTICE-Q-COVERAGE; retire "Psychogenic" canonical value |
| **Status** | ✅ Complete |

---

## What This BATON Tracks

This handoff document records the state of the ABFM ITE Intelligence System as of end-of-session 2026-04-10. It captures:
- **Active database state** — table row counts, schema status
- **Deferred flags** — work in progress, blockers, dependencies
- **Code changes** — what was modified and why
- **Next steps** — immediate, short-term, future work

**RULE: Read this BATON first before any work in the next session.**

---

## DATABASE STATE (inherited from BATON 051 — no structural changes)

| Table | Rows | Notes |
|-------|------|-------|
| articles | 1,985 | +49 from AAFP acquisition (ART-1938–ART-1986) |
| questions | 1,629 | ITE 2018–2025; body_system_merged updated this session |
| aafp_questions | 1,221 | aafp body_system updated this session |
| qid_art_xref | 2,470 | All 8 years |
| aafp_qid_art_xref | 864 | 643 unique questions linked (52.7%) |
| article_icd10 | 4,020 | Rebuilt with vec 2026-04-05 |
| question_icd10 | 5,218 | 1,512/1,629 ITE (92.8%); 66 no_match deleted |
| aafp_question_icd10 | 4,753 | Relevance normalized, related cap applied |
| clinical_pathways | 3,971 | Rebuilt 2026-03-31; ART-0002–ART-1985 |
| pubmed_pmid_cache | 344 | Layer 2 seed |
| article_icd10_vec | 1,757 | Rebuilt 2026-04-05 |
| question_icd10_vec | 2,747 | Rebuilt 2026-04-05 |
| icd10_vec | 2,219 | OpenAI text-embedding-3-small (1536d) |
| article_currency | 1,985 | Built 2026-04-07 |
| article_citation_trend | 1,740 | Citation trend tracking |

### Body System Migration (THIS SESSION)
**Key Update:** "Psychogenic" canonical value retired. All derived columns now use "Psychiatric/Behavioral".

- **questions.body_system_merged:** 120 rows updated (Psychogenic → Psychiatric/Behavioral) ✅
- **aafp_questions.body_system:** 82 rows updated (Psychogenic → Psychiatric/Behavioral) ✅
- **questions.body_system (source column):** UNTOUCHED — preserves ABFM original data ✅
- **Verification:** 0 "Psychogenic" remaining in either derived column

---

## PDF LIBRARY (unchanged from BATON 051)

| Tier | Count | Notes |
|------|-------|-------|
| VC_fail | 630 | Failed VC gate; awaiting enrichment |
| VC_pass | 168 | Passed VC gate; awaiting enrichment |
| local_lite | 117 | Fully enriched, failed VC gate |
| right_click | 58 | Fully enriched, passed VC gate |
| **ITE Total** | **973** | — |
| AAFP | 15 | Recovered 2026-04-05 |
| ITE exams | 16 | All 8 years (2018–2025) × MC + critique |
| Dupes archive | 14 | Recovered PDFs |

---

## SESSION SUMMARY: WHAT HAPPENED

### Task 1: DEFERRED-PRACTICE-Q-COVERAGE — ✅ CLOSED

Investigated why the practice question engine returned warnings for 7 dimensions with 0 questions.

#### Root Cause 1 — JS Threshold Mismatch (5 dimensions)
**Affected dims:** Foundations, Preventive, Cardiovascular, Respiratory, Sexual and Reproductive

JS `weakBlueprints` collection uses a **relative personal threshold:** `rate < personal_mean − personal_sd`. For high-performing residents, this threshold can exceed 0.70. Python's `yield_weighted_priorities()` uses a **hard 0.70 threshold** — questions only generated when `rate < 0.70`. Result: dims marked "weak" in JS but skipped by Python → false 0-question warnings.

**Fix A — `ite_report_builder_v2.js`:**
- Added `allPerfRates` lookup to check actual performance rate
- 0-question warning now fires only when: `rate < 0.70 AND count === 0`
- Dims that are "weakly weak" (above 70%, below personal mean) no longer trigger false warnings

#### Root Cause 2 — PDF Text Split Creates Phantom Columns (2 dimensions)
**Affected dims:** "Psychiatric", "Behavioral"

`_detect_bodysystem_columns()` in `ite_parser.py` dynamically reads white text spans from ABFM PDF headers. "Psychiatric/Behavioral" renders as **two separate text spans** → phantom columns "Psychiatric" and "Behavioral" created. Neither key exists in `BODYSYSTEM_PDF_TO_DB` → 0 rows returned.

**Fix B — `ite_parser.py`:**
- Added `COMPOUND_HEADERS` dict mapping adjacent spans to canonical names
- Merge loop combines spans that form known compound headers before x-position boundary calculation
- Handles: Psychiatric/Behavioral, Injuries/Musculoskeletal, Sexual and Reproductive, Population-Based Care, Patient-Based Systems, Hematologic/Immune

#### Root Cause 3 — Stale Mapping Direction
`BODYSYSTEM_PDF_TO_DB` in `ite_analyzer_v3.py` mapped `"Psychiatric/Behavioral"` → `["Psychogenic"]`. Since no questions had `body_system_merged = 'Psychiatric/Behavioral'` pre-migration, this was a silent failure.

**Fix C — `ite_analyzer_v3.py` + `ite_analyzer_v2.py`:**
- Corrected: `"Psychiatric/Behavioral": ["Psychiatric/Behavioral"]`

---

### Task 2: Psychogenic Retirement — ✅ COMPLETE

"Psychogenic" is not a real clinical category. It was the legacy DB-side canonical value for psychiatric/behavioral questions (holdover from early categorization).

#### Files Modified (12 total)

**Module 3 (Analyst):**
1. `03_module.3_analyst/scripts/ite_analyzer_v3.py`
   - BODYSYSTEM_PDF_TO_DB: fixed mapping
   - BODYSYSTEM_PDF_NORM: kept legacy alias for runtime normalization

2. `03_module.3_analyst/scripts/ite_analyzer_v2.py`
   - BODYSYSTEM_PDF_TO_DB: same fix

3. `03_module.3_analyst/scripts/ite_parser.py`
   - BS_SYSTEMS list: "Psychogenic" kept as comment alias (pre-2024 PDF recognition)
   - Added COMPOUND_HEADERS dict (Fix B)

4. `03_module.3_analyst/scripts/ite_report_builder_v2.js`
   - Applied Fix A (threshold mismatch + allPerfRates lookup)

**Module 2 (Processor):**
5. `02_module.2_processor/scripts/00_body_system_extractor.py`
   - P2_CATS, REMAP_2024, ANCHOR: all Psychogenic refs → Psychiatric/Behavioral

6. `02_module.2_processor/scripts/01_build_crosswalk.py`
   - 6 Psychogenic occurrences replaced

7. `02_module.2_processor/scripts/02_ite_categorizer.py`
   - STANDARD_CATEGORIES + CATEGORY_MAP updated

8. `02_module.2_processor/scripts/classify_ite_year.py`
   - Same pattern as 02_ite_categorizer.py

9. `02_module.2_processor/scripts/batch_insert_aafp_articles.py`
   - Keyword map: Psychogenic → Psychiatric/Behavioral

10. `02_module.2_processor/scripts/build_clinical_pathways_v2.py`
    - CHRONIC_CATEGORIES updated

**Module 1 (Warehouse):**
11. `01_module.1_warehouse/scripts/maintain/backfill_new_article_metadata.py`
    - Keyword map updated

12. `01_module.1_warehouse/scripts/maintain/build_clinical_pathways.py`
    - CHRONIC_CATEGORIES updated

#### Legacy Aliases (Intentionally Kept)
1. **BODYSYSTEM_PDF_NORM in ite_analyzer_v3.py:** `"Psychogenic": "Psychiatric/Behavioral"` — normalizes old DB values at runtime for backward compatibility
2. **BS_SYSTEMS alias in ite_parser.py:** "Psychogenic" as comment for pre-2024 PDF recognition
3. **Comments in 00_body_system_extractor.py** — historical reference
4. **Docstring in 02b_generate_hy_inserts_v2.py** — historical note

#### Database Migration (Confirmed)
**Script:** `00_database/scripts/retire_psychogenic.py` (new file, one-time migration)

Execution verified:
- questions.body_system_merged: 120 rows updated to Psychiatric/Behavioral ✅
- aafp_questions.body_system: 82 rows updated to Psychiatric/Behavioral ✅
- questions.body_system (source): UNTOUCHED ✅
- Zero "Psychogenic" remaining in derived columns ✅

---

## SCRIPT INVENTORY (unchanged — modifications only, no new scripts except retire_psychogenic.py)

| Module | Category | Count | Notes |
|--------|----------|-------|-------|
| M1 | Build (Python) | 6 | — |
| M1 | Maintain (Python) | 26 | Updated 2 for Psychogenic retirement |
| M2 | Python | 75 | Updated 6 for Psychogenic retirement |
| M2 | JavaScript | 6 | — |
| M3 | Python | 15 | Updated 4 for Psychogenic retirement |
| M3 | JavaScript | 2 | Fixed ite_report_builder_v2.js (Fix A) |
| M3 | JSON config | 1 | — |
| M4 | Python | 1 | — |
| M5 | Python | 3 | — |
| M5 | TypeScript/TSX | 35 | — |
| M5 | SQL migrations | 5 | — |
| **DB Scripts** | Python | 1 | retire_psychogenic.py (one-time, gitignore candidate) |

---

## DEFERRED FLAGS (carry forward to next session)

### DEFERRED-PRACTICE-Q-COVERAGE
**Status: ✅ CLOSED**

Both root causes identified and fixed:
- **Fix A:** JS threshold mismatch resolved (allPerfRates lookup added)
- **Fix B:** PDF compound header split handled (COMPOUND_HEADERS merge logic)
- **Fix C:** BODYSYSTEM_PDF_TO_DB mapping corrected
- **DB Migration:** body_system_merged + aafp body_system fully migrated and verified

Do NOT carry this flag forward.

---

### DEFERRED-YOY-ROBUSTNESS
**Status: ACTIVE — carry forward**

Year-over-year section (Section 3b in executive summary) needs robustness work to handle edge cases:
- Missing scaled scores in historical data
- Partial year data (residents started mid-year)
- Multi-year gaps (residents with >1-year absences)
- N>2 year comparisons (residents with 3+ exams)

**Next action:** Expand `longitudinal_delta()` edge-case handling in `ite_analyzer_v3.py`; add null checks in `renderYoYSection()` JS.

---

### DEFERRED-PGY-BENCHMARKS
**Status: ACTIVE — awaiting Mikey's data**

Add PGY 1–4 expected score percentage ranges to Executive Summary for contextual framing.

**Blocker:** Awaiting PGY baseline ranges from Mikey (email pending)

**Next action:** Once received, create `key_data_files/pgy_benchmarks.md`, integrate into `report_config.json` and `ite_analyzer_v3.py`.

---

### DEFERRED-AAFP-PDF-RETRY
**Status: ACTIVE — awaiting site stability**

Re-run `exa_pdf_downloader` against AAFP site for stalled downloads.

**Blocker:** AAFP site reliability

**Next action:** Monitor AAFP site; re-run when stable.

---

### DATABASE_GUIDE.md Relocation
**Status: ACTIVE — carry forward**

Git index showing D+A instead of R (delete + add instead of rename). Affects commit cleanliness.

**Next action:** `git rm old + git add new`; verify R flag in git status; commit.

---

## CRITICAL REMINDERS FOR NEXT SESSION

1. **Psychogenic is retired.** Body system is now consistently "Psychiatric/Behavioral" across all code and derived DB columns.
   - `questions.body_system` (source ABFM data) **still has "Psychogenic"** — intentional, do not touch
   - `questions.body_system_merged` and `aafp_questions.body_system` now use "Psychiatric/Behavioral"

2. **Practice question engine is fixed.** 0-question warnings were false positives from:
   - Threshold mismatch between JS (relative) and Python (hard 0.70)
   - PDF text spans splitting compound column headers
   Both resolved.

3. **Key changed files this session:**
   - ite_analyzer_v3.py, ite_analyzer_v2.py, ite_parser.py, ite_report_builder_v2.js
   - 00_body_system_extractor.py, 01_build_crosswalk.py, 02_ite_categorizer.py, classify_ite_year.py
   - batch_insert_aafp_articles.py, build_clinical_pathways_v2.py
   - backfill_new_article_metadata.py, build_clinical_pathways.py (M1)
   - Plus new: 00_database/scripts/retire_psychogenic.py

4. **DB state is stable.** Row counts unchanged from BATON 051; only body_system_merged + aafp body_system updated.

5. **Next Claude instance should:**
   - Read this BATON first
   - Verify Psychogenic absence from derived columns (QC step)
   - Pick up on DEFERRED-YOY-ROBUSTNESS
   - Follow Mikey's guidance on DEFERRED-PGY-BENCHMARKS

---

## NEXT STEPS (Immediate → Short-term)

### Immediate (next session)
1. **DEFERRED-YOY-ROBUSTNESS** — Expand `longitudinal_delta()` edge-case handling; add null checks in `renderYoYSection()`
2. **DOCX Review** — Mikey to verify Pjetergjoka_2024/2025 DOCX output (YoY table render, practice Q dimension coverage now that fixes are in place)

### Short-term
3. **Module 5 Setup** — Provision Supabase project, run migrations, sync SQLite → Supabase, deploy Railway FastAPI, deploy Netlify frontend
4. **DEFERRED-PGY-BENCHMARKS** — Receive PGY 1–4 baseline ranges from Mikey; create pgy_benchmarks.md in key_data_files/; integrate into report_config.json and ite_analyzer_v3.py
5. **DATABASE_GUIDE.md Relocation** — git rm old + git add new; verify R flag; commit
6. **DEFERRED-AAFP-PDF-RETRY** — Monitor AAFP site; re-run exa_pdf_downloader when stable

---

## LOCKED RULES (Never Override Without Mikey Confirming)

1. **Fix the data, not the code.** Messy data → clean upstream, don't patch downstream.
2. **VC gate = sole criterion** for right_click tier. DB membership alone insufficient.
3. **Source data protected.** DB + PDFs + VC gate survive everything. Derived files (JSONs, DOCXs, CSVs) are disposable.
4. **Dynamic paths only.** Python: `SCRIPT_DIR = Path(__file__).resolve().parent; PROJECT_ROOT = SCRIPT_DIR.parent.parent`. JS: `path.resolve(__dirname, "../../")`.
5. **No de novo JS** (relaxed to "use when needed, flag if clutter accumulates").
6. **BATON first.** Read the active BATON before any work.
7. **QC after every integration.** Schema-level column-by-column population comparison.
8. **Git via Desktop Commander.** Claude can run `git commit` via Python subprocess helper.
9. **shutil.rmtree BANNED.** Use explicit file deletion or PowerShell Remove-Item (Recycle Bin safe).
10. **Strategy 0 in every enricher.** Codon parse always first.
11. **Schemas before scripts.** SQL CREATE TABLE defined before build scripts written.

---

## FOR THE REPO (Git Notes)

- **Branch:** main
- **Latest commit hash (pre-commit):** 8fb7549
- **Unpushed changes:** Psychogenic retirement across 12 files + new retire_psychogenic.py script
- **Next commit message:** Should reference "Retire Psychogenic canonical value; fix practice-q-coverage threshold mismatch and PDF compound header split"
- **.gitignore note:** `00_database/scripts/retire_psychogenic.py` is a one-time migration script. Consider adding to .gitignore after verification if it's not needed for future recovery.

---

**End BATON 052**  
*Handoff ready for next Claude instance. Read this first before any work.*
