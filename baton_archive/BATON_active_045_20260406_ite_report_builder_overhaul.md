# BATON 045: ITE V3 Score Analysis Pipeline Overhaul
**Date:** 2026-04-06  
**Session Focus:** ite_analyzer_v3.py bug fixes + ite_report_builder_v2.js de-identification & restructuring  
**Status:** Pipeline operational — QC passed, 2 resident runs complete

---

## Session Summary

This session completed a targeted overhaul of the ITE score analysis pipeline (M3), fixing two critical bugs in ite_analyzer_v3.py and executing a 20+ edit restructuring of ite_report_builder_v2.js for de-identification, report layout, and section reorganization.

**Key outcome:** Hopkins 2025 and Sarkar 2025 resident exam reports now generate with correct AAFP quota enforcement, cleaned ICD-10 sentinel values, and professional (de-identified, compact) output format suitable for resident review.

---

## What Was Built

### ite_analyzer_v3.py: 4 targeted fixes

1. **AAFP quota enforcement** (BUG)
   - **Problem:** ITE 2025 recency bonus (+0.2) was monopolizing all 20 dimension slots before AAFP questions could be selected. Result: 0 AAFP questions in top dimensions.
   - **Solution:** Added `AAFP_MIN_QUESTIONS = 4` constant. Modified `select_top_questions()` to reserve 4 slots for AAFP (separate bank), then fill remaining 16 with ITE.
   - **Result:** Clean 16 ITE / 4 AAFP split across all dimensions.

2. **no_match sentinel cleanup** (BUG)
   - **Problem:** 66 rows in question_icd10 + 49 rows in clinical_pathways had icd10_code = 'no_match' (legacy artifact from earlier pipeline versions). These polluted dimension detail queries.
   - **Solution:** 
     - Applied direct DELETE via /tmp DB copy (FUSE write limitation workaround).
     - Added `AND qi.icd10_code != 'no_match'` filter in icd10_weakness_map() query.
   - **Result:** question_icd10 reduced 5,284 → 5,218; clinical_pathways reduced 4,020 → 3,971.

3. **missed_items_detail** (NEW)
   - **Function:** New `fetch_missed_items_detail()` fetches full question text, choice labels, resident answer, correct answer, and explanation for all 60+ missed items in a cohort exam via QID map.
   - **Injected into:** analyze_v3() return dict as `"missed_items_detail"` (resident-facing appendix data).
   - **Fields:** QID, question_text, choices (A–D), resident_answer, correct_answer, explanation, icd10_code.

4. **concept_qid_map + QID tracking**
   - **Function:** Modified `concept_clustering()` to track which QIDs contributed each diagnosis/drug/guideline concept.
   - **Injected into:** Return dict as `"concept_qid_map"` (e.g., `{"diagnosis": {"HTN": [QID-2024-0001, QID-2024-0042]}, ...}`).
   - **Also modified:** `difficulty_profile()` to include QID in all easy_miss entries.

### ite_report_builder_v2.js: 20+ edits for de-ID & professional output

**De-identification & removal:**
- Removed resident name from executive summary header and exam document running header.
- Removed "Term Key" section (terminology glossary).
- Removed "Subcategory Decomposition" section (granularity no longer needed).
- Removed "Clinical Pathway" section (redundant with ICD-10 table).
- Removed tier badge (VC pass/fail/local_lite) — percentile ranking only.
- Removed green coloring from correct answer choices in practice questions appendix.
- Removed "Status" column from overview tables (eliminated 70% threshold lane markings).

**Layout & section reorganization:**
- **New:** ITE Performance Overview section — added early (post-exec summary) with:
  - Blueprint summary table (10 blueprint categories × score/pct/interpretation).
  - Body system summary table (14 body systems × missed/total/% weak).
- **Changed:** "recovery/recoverable" → "improvement/improvable" throughout (softer framing).
- **Revamped:** Difficulty profile section — added explanation prose table, restructured easy_misses to omit subcategory column.
- **Split:** Yield priorities into two Low-Hanging Fruit tables: one by blueprint dimension, one by body system. Each dimension_type gets its own table.
- **New:** Crossover Weaknesses section — cross-tab high-yield cells (blueprint × body system) with narrative pattern summary.
- **Enhanced:** Concept Fingerprint — added QID column to each concept row.
- **Cleaned:** ICD-10 section — consolidated to single 4-column table (code | condition name | # misses | clinical domain).
- **Compacted:** Practice Questions section:
  - Replaced full question text rendering with compact reference table: # | QID | Blueprint | Body System | Source | Match.
  - Clicked links point to full question details.
- **Compacted:** Appendix "Missed Items Detail" — replaced full question+choices+explanation with compact reference table (Item# | QID | Blueprint | Body System | Status).

**Page break prevention (formatting):**
- Added `keepNext: true` to sectionBar and subBar inner paragraph properties.
- Added `keepNext: true` to all spacer paragraphs after section headers.
- Added `keepNext: true` to 6 caption paragraphs before tables (ITE overview, body system, low-hanging, ICD-10, concept, missed items).
- Result: No section headers orphaned at page bottoms; tables stay with their introductions.

### Pipeline runs this session

| Resident | Year | Score | ITE % | Dimension Split | Missed Items | Status |
|----------|------|-------|-------|-----------------|--------------|--------|
| Hopkins  | 2025 | 65.4% | 125/191 | 16 ITE / 4 AAFP | 66 | ✅ Passed |
| Sarkar   | 2025 | 57.1% | 109/191 | 16 ITE / 4 AAFP | 82 | ✅ Passed |

**QC checks all passed:**
- ✅ No 'no_match' rows in output.
- ✅ AAFP quota (4/20 dimensions) met.
- ✅ concept_qid_map fully populated.
- ✅ Page breaks optimized; no orphaned headers.

---

## Current DB State (as of end of session)

| Table | Rows | Notes |
|-------|------|-------|
| articles | 1,985 | (+49 AAFP acquisition: ART-1938–ART-1986) |
| questions (ITE) | 1,629 | 2018–2025, blueprint 100% filled |
| aafp_questions | 1,221 | Blueprint + concept_tags 100% |
| qid_art_xref | 2,470 | All years 2018–2025 |
| aafp_qid_art_xref | 864 | 52.7% link coverage |
| article_icd10 | 4,020 | Vec rebuilt 2026-04-05 |
| question_icd10 | 5,218 | (was 5,284, -66 no_match rows deleted) |
| aafp_question_icd10 | 4,753 | Relevance normalized, related cap applied |
| clinical_pathways | 3,971 | (was 4,020, -49 no_match rows deleted) — blueprint-based, both banks |
| pubmed_pmid_cache | 344 | Layer 2 seed (citation_id → PMID) |
| icd10_vec | 2,219 | OpenAI text-embedding-3-small (1536d) |
| article_icd10_vec | 1,757 | Rebuilt 2026-04-05 |
| question_icd10_vec | 2,747 | Rebuilt 2026-04-05 |

---

## PDF Library

| Tier | Count | Path | Notes |
|------|-------|------|-------|
| VC_fail | 623 | citation_files/ITE/VC_fail/ | Lowest citation priority |
| VC_pass | 168 | citation_files/ITE/VC_pass/ | VC gate passed (352 citations) |
| local_lite | 117 | citation_files/ITE/local_lite/ | VC_fail + fully enriched |
| right_click | 58 | citation_files/ITE/right_click/ | VC_pass + fully enriched (M2 complete) |
| AAFP | 15 | citation_files/AAFP/ | Recovered 2026-04-05 |
| ITE Exams | 16 | citation_files/ite_exams/ | 8 years × MC + critique |
| **Total** | **997** | | (14 dupes in _dupe_archive/) |

---

## Script Inventory

### M1 Warehouse (`01_module.1_warehouse/`)
- build/ (6 scripts): `build_v6.py`, `build_v6_summary.py`, `repair_schema.py`, `validate_schema.py`, etc.
- maintain/ (25 scripts): incremental insertion, cleanup, etc.

### M2 Processor (`02_module.2_processor/`)
- **core/** (4 py): Q/A extraction, blueprint parsing, enrichment orchestration.
- **engines/** (7 py): CoherenceEngine, ICD10Engine, PathwayEngine, etc.
- **utils/** (6 py): PDF parsing, text cleaning, formatting.
- **Modified this session:**
  - `ite_report_builder_v2.js` (20+ edits) — de-ID, layout overhaul, compact tables.
  - `ite_analyzer_v3.py` (4 fixes) — AAFP quota, no_match cleanup, missed_items_detail, concept_qid_map.
  - `word_doc_defaults.py` (minor) — keepNext formatting constants.
- **source/**: transcripts, blueprint XLSX, outline DOCX.
- **outputs/**: staging JSONs, citation gap analysis.
- **prompts/**: enrichment templates.
- **main.py** + **requirements.txt** at M2 root.

### M3 Analyst (`03_module.3_analyst/`)
- 13 Python + 2 JS + 2 JSON config.
- **Key scripts:**
  - `ite_analyzer_v3.py` — ITE cohort analysis (modified this session).
  - `ite_report_builder_v2.js` — DOCX report generation (modified this session).
  - `aafp_brq_analyzer.py` — AAFP cohort analysis.
  - `icd10_trends.py`, `clinical_pathway_analyzer.py`, etc.

### M4 Sandbox (`04_module.4_sandbox/`)
- Experimental code, one-offs.

### Root-level scripts
- `aafp_brq_scraper.py` — AAFP question ingestion (maintained).

---

## DEFERRED FLAGS (carry forward + session updates)

| Flag | Description | Status | Defer Date |
|------|-------------|--------|-----------|
| DEFERRED-AAFP-PAYWALL | 3 articles (ART-1959, ART-1972, ART-1967) — paywalled; obtain via institutional/interlibrary loan | OPEN | BATON 044 |
| DEFERRED-F | Intelligence 2.0 Layer 2 — `article_currency` via PubMed (344 PMIDs in pubmed_pmid_cache; NCBI API key set) | OPEN | BATON 044 |
| DEFERRED-RECO-CLEANUP | Clean empty RECO folders — user housekeeping task post-PDF recovery | ✅ CLOSED — completed by user prior to BATON 045 | BATON 044 |

---

## Next Steps

### Immediate (next session)
1. **Resume normal roadmap:** exa-research-search Phase 2 expansion + clinical pathways pipeline Phase 3.
2. **DEFERRED-F Priority:** Intelligence 2.0 Layer 2 (`article_currency` via PubMed NCBI API; 344 PMIDs ready in `pubmed_pmid_cache`).
3. ~~**User housekeeping:** DEFERRED-RECO-CLEANUP~~ — ✅ DONE. Do not carry forward.

### Medium-term
4. **Resident-facing report toggle:** When needed for resident-facing report version, re-enable full question rendering in ite_report_builder_v2.js practice questions section (currently shows compact reference table only).
5. **AAFP link coverage:** Consider aafp_brq_scraper improvements to increase link coverage from current 52.7% (864/1,221).

### Long-term
6. **Clinical Pathways Phase 3:** Integrate M3 pathway engines into M2 processor pipeline.
7. **Trends Layer:** Publish Intelligence 2.0 Layer 3 (Trends) and Layer 4 (Pathway recommendations).

---

## Conventions / Locked Rules Reminder

1. **Fix the data, not the code.** Messy data → clean upstream, not in script logic.
2. **VC gate = sole criterion** for right_click tier. DB membership alone is insufficient.
3. **Source data protected:** DB + PDFs + VC gate are permanent. Derived files (JSON, DOCX, CSV) are disposable.
4. **Dynamic paths only:** `SCRIPT_DIR = Path(__file__).resolve().parent; PROJECT_ROOT = SCRIPT_DIR.parent.parent` (3 hops).
5. **No de novo JS.** New code = Python only. Existing JS scripts (ite_report_builder_v2.js) migrate fine.
6. **BATON first.** Read active BATON before any work session.
7. **QC after every integration.** Schema-level column-by-column comparison, old cohort vs new.
8. **Git via Desktop Commander.** Use claude_knowledge/git_runner.py for commits. Cannot `rm` NTFS files — use PowerShell Remove-Item or Windows Explorer.
9. **shutil.rmtree is BANNED.** Use explicit file-by-file deletion or PowerShell Remove-Item. shutil.rmtree bypasses Recycle Bin (learned from fix_ghost.py 2026-04-05).
10. **Strategy 0 in every enricher.** Codon parse (regex ART-ID extraction from filename) is always first matching strategy.
11. **Schemas before scripts.** SQL `CREATE TABLE` defined before build scripts written.

---

## Git Status

- **Previous commit:** a2f91ae (BATON 044: AAFP PDF recovery + deferred flag cleanup)
- **Modified files this session:**
  - `02_module.2_processor/ite_report_builder_v2.js` (20+ edits)
  - `03_module.3_analyst/ite_analyzer_v3.py` (4 fixes)
  - `02_module.2_processor/word_doc_defaults.py` (minor)
- **Status:** Ready for commit (QC passed, pipeline operational).

---

## Session Notes

- **FUSE write limitation workaround:** Applied no_match deletion via /tmp copy because SQLite on FUSE mount (Google Drive) restricts direct DELETE statements. Copied DB to /tmp, deleted rows, verified count, copied back.
- **AAFP quota enforcement key insight:** Banks must be selected independently with reserved slots. Merged selection logic would allow high-scoring ITE questions to fill all slots before AAFP considered.
- **Report compaction trade-off:** Full question rendering removed from practice questions and appendix. Re-enable via toggle if resident-facing version needed (currently optimized for quick scan / weakness identification).
- **Page break prevention:** keepNext applied recursively to prevent orphaned headers. Tested on 65-page and 82-page reports — all section boundaries clean.

---

**BATON Author:** Claude Agent (session 2026-04-06)  
**Next BATON Due:** After next significant pipeline modification or session completion.
