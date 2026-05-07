# _index.md — Ground Truth Directory Map
**Scope:** `board_prep_intel/` (project root — Option B complete 2026-04-04)
**Last Updated:** 2026-05-07 (BATON 066 — JAMA + NEJM PDF harvest complete; 127 new PDFs (in worktree pending merge); DevTools-console pattern established for browser-auth journals)
**Status:** Current — 1,396 total PDFs post-merge (990 VC_fail + 216 VC_pass + 117 local_lite + 58 right_click + 14 dupe_archive + 15 AAFP + 16 exams; 127 new this session, in worktree pending merge); M1 build = 8 + maintain = 36 (post-merge); M2 = 75py + 6js; M3 = 55py + 4js + 1 json config + abfm_reference_2024.json; M5 scaffold = 3py + 35ts/tsx + 5sql; DB enriched (2,206 articles, 1,639 ITE questions, article_icd10 4,959, question_icd10 5,774, clinical_pathways 4,959, intersection_centroid_vec 158); skills_abilities/ includes ite-score-analyzer-v2/ plugin + session-housekeeping agents/.

> This file maps the `board_prep_intel/` project root. `00_#PROJECT_OVERHAUL` nesting has been removed (Option B, 2026-04-04).
> Stale counts are worse than no index. Verify before trusting.

---

## Top-Level Structure

```
board_prep_intel/
├── BATON_active_066_20260507_jama_nejm_pdf_harvest_complete.md  — active BATON
├── CLAUDE.md                              — project memory + conventions
├── REPO_MAP.md                            — current-state architectural overview (NEW — BATON 039)
├── README.md                              — project overview (human-readable)
├── README_PROJECT.md                      — extended project documentation
├── _index.md                              — this file
├── .gitattributes / .gitignore
│
├── 00_database/                           — source of truth (DB + supporting data)
├── 01_module.1_warehouse/                 — M1 3-domain: citation_files/ (1,381 PDFs across 4 tiers + 15 AAFP, post-merge) + practice_questions/ (42 Q&A deliverables) + ite_exams/ (16 raw PDFs) + scripts/
├── 02_module.2_processor/                 — M2 pipeline scripts + source inputs
├── 03_module.3_analyst/                   — M3 score analysis + ICD-10 + pathways
├── 04_module.4_sandbox/                   — M4 experiments and agent prototypes
└── 05_module.5_web/                       — M5 web platform (Next.js + Supabase + Sanity + Railway)
│
├── _archive_/                             — curated deliverables + retired artifacts (renamed from archive_canonical 2026-04-03; includes docx_guideline_library/)
├── auto-memory-copies/                    — git-tracked mirror of .auto-memory/ (durable backup)
├── baton_archive/                         — all archived BATONs (40+)
├── extracted_json/                        — extracted article JSONs (middle-man layer; not git-tracked)
├── key_data_files/                        — critical reference + architecture data files
└── skills_abilities/                      — SDK docs, agent toolbox, skill files (includes apify-actors/)
```

**Removed/relocated (2026-03-27):** `sectional_READMEs/`, `tagging_bundle/`, `re-org_guidance/`, `master_map.JSON`, `MASTER_MAP_V.1.html`, `TEMP_MIGRATION_MANIFEST.md`
**Swept (2026-04-03, BATON 034):** `docx_guideline_library/` → `_archive_/`; `archive_canonical/` → renamed `_archive_/`; `apify-actors/` → `skills_abilities/`; `apify_smart_article_extractor` → deleted; BATON 032/033 duplicates → deleted from root
**Swept (2026-04-04, BATON 035):** 5 legacy scripts deprecated (headers applied) + staged in `_legacy/` → moved to offsite archive by user; originals pending Windows delete; `build_faculty_pptx.js` verified clean (no path deps)
**Swept (2026-04-04, BATON 036/037):** M1 restructured to 3-domain layout (citation_files/ + practice_questions/ + ite_exams/); all 11 M1 maintain scripts path-updated; build_ite_qa_deliverables.py + build_aafp_qa_deliverables.py built + 42 deliverables generated; ite_exams/ archive confirmed (2018–2025)

**Fixed (2026-04-08, BATON 049):** Three ITE score analysis bugs fixed — BUG-047-01: ite_parser.py exam_year now extracted from PDF text (not hardcoded 2025); BUG-047-02: ite_analyzer_v3.py added BODYSYSTEM_PDF_NORM alias map + _normalize_body_system() function for body system name normalization; BUG-047-03: ite_analyze_v2.py imports normalize function, applies it to body_system_scaled dict, uses official score when available. Test reports validated: Scholl_2022/23/24, Sarkar_2025, Hopkins_2025. New finding: practice question 0-question warnings detected in qid_art_xref tagging (deferred flag: DEFERRED-PRACTICE-Q-COVERAGE).

**Improved (2026-04-08, BATON 050):** Practice Q year-over-year analysis refined — removed recency bonus from ite_analyzer_v3.py; updated SQL ORDER BY exam_year DESC queries; increased result limits from 20 to 60; added current_exam_year exclusion with int cast; ite_report_builder_v2.js implements two-table layout (single-dimension + cross-dimension); longitudinal year-over-year section 3b added with month-by-month trend data; --skip-reading-list and --question-count CLI flags added to ite_analyze_v2.py; SKIP_READING_LIST env var passed to Node. Ran Pjetergjoka 2024+2025 analysis with 35 questions.

**Swept (2026-04-08, BATON 048):** DATABASE_GUIDE.md relocated from 00_database/ to project root; session-housekeeping agent templates created in .claude/skills/session-housekeeping/agents/

**Added (2026-04-09, BATON 051):** 05_module.5_web/ scaffold (54 files — Next.js, Supabase, Sanity, Railway, OpenAI NL search) committed to GitHub by Copilot on 2026-04-08; nl_search_validation.py added to M4 sandbox; M3 script count corrected to 15py; housekeeping sweep complete.

**Refined (2026-04-12, BATON 054):** ite_report_builder_v2.js underwent 18-edit redesign for multi-year resident reporting; improved year-over-year section 3b rendering; added ABFM 2024 national benchmark comparison (PGY 1-4); abfm_reference_2024.json created in M3 scripts/; ite_analyze_v2.py and ite_analyzer_v3.py optimized for cohort-level aggregation.

**Added (2026-04-15, BATON 059):** Full body_system QC pipeline completed (ITE 2018-2021, 2024-2025 + AAFP); 19 new M3 scripts created; body-system-qc skill + methodology_scout/ directory established; 201 ITE + 129 AAFP questions in human_review queue; deferred flags: DEFERRED-BODY-SYSTEM-MERGED-UPDATE (NEW), DEFERRED-CENTROID-REBUILD (NEW), DEFERRED-HUMAN-REVIEW-BODY-SYSTEM (NEW); DEFERRED-AAFP-BODY-SYSTEM-AUDIT (CLOSED).

**Completed (2026-04-16, BATON 060):** Enrichment pipeline for 10 recovered ITE questions (Steps 1-6 completed); 22 holdout body_system corrections applied (2024-2025 deprecated labels); apply_body_system_normalization.py fixed Musculoskeletal (48 QIDs), QID-2021-0168, synced 376 body_system_merged records; DEFERRED-BODY-SYSTEM-MERGED-UPDATE (CLOSED); DEFERRED-CENTROID-REBUILD (CLOSED); M3 script count: 39 → 50 (+10 new session scripts: audit_blueprint_by_year.py through apply_recovered_questions.py).

**Completed (2026-04-29, BATON 063):** Two ITE interpretation guides written — build_resident_guide.py → ITE_Report_Guide_Resident_v2.docx (action-oriented, gold ACTION callouts, resident audience) and build_faculty_guide.py → ITE_Report_Guide_Faculty_v2.docx (methodology-focused, DATA SOURCE + LIMITATION callouts, faculty audience); word_doc_defaults.py updated with level 1/2 header differentiation (conditional spacing + shading); Rule 14 locked (all Python .docx scripts must use word_doc_defaults.py); DEFERRED-REPORT-GUIDE CLOSED; M3 count 50py+2js → 52py+4js; DB counts stable.

**Completed (2026-04-29, BATON 062):** Report builder improvements (5 issues: scoring note, body_system provenance split, consolidated tables, concept fingerprint drugs-only, two-tier reading list); M3 script enhancements (ite_analyze_v2.py body_system_sources tracking, ite_analyzer_v3.py match_top_articles() two-tier, ite_report_builder_v2.js 5-issue suite); platform migration from Windows PC to Mac via external HD (DB + PDFs intact); pre-existing Windows PC ICD-10/pathways enrichment discovered and integrated (article_icd10 3,952→4,959, question_icd10 ~5,003→5,774, clinical_pathways 3,971→4,959, intersection_centroid_vec 123→158); Git commit 47d6e8e staged, push pending; new deferred flag DEFERRED-REPORT-GUIDE.

**Completed (2026-04-16, BATON 061):** Legacy body_system analyses complete; all 7 resident analyses re-run with Stage 1.75 DB body_system backfill (Scholl 2022/2023/2024, Hopkins 2025, Sarkar 2025, Pjetergjoka 2024/2025); article_currency updated to 1,998 rows (100% complete); ite_analyze_v2.py: Stage 1.75 new pipeline stage added for DB body system backfill; ite_analyzer_v3.py: pathway_gap_map() LEFT JOIN fixed (icd10_desc column); intersection_centroid_vec verified (123 rows, 71 ITE + 52 AAFP blueprintxbody_system centroids).

**Cleaned (2026-04-04, BATON 039):** Windows cleanup complete — 5 deprecated M1 scripts deleted; Option B artifacts deleted (SEVERANCE_PLAN.md, option_b_patch.py, repo_pre_severance.md); schema docs refreshed (articles.md: row count, tier column, source_type dist; questions.md: subcategory removed); script counts corrected (M1 build 6, maintain 18, M2 75py, M3 13py); REPO_MAP.md added to root
**Fixed (2026-04-04, BATON 038):** 14 code review defects resolved — hop count bugs (preprocess_concept_tags, batch_db_extract, db_guided_extractor), SCHEMAS_DIR/OUTPUT_DIR (build_icd10_tags), filename pattern (extract_ite_year), exists() guard (audit_engine_type_changes), crosswalk output paths + multi-tier scan (build_crosswalk_index), XGBoost param (classify_ite_year), JSON_DIR/LOG_DIR/OUTPUT_DIR path fixes (4 scripts), VC gate cross-check (backfill), docstring escapes (2 scripts)

**Acquired (2026-05-06, BATON 065):** Phase 2 PDF acquisition — 281 new PDFs via exa_pdf_downloader + unpaywall batch integration (VC_fail 630→879, VC_pass 168→200); 208 new articles (ART-1999–ART-2206) added via acquire_missing_citations.py; M1 maintain script count 26→30 (acquire_missing_citations.py, playwright_auth_downloader.py, browser_pdf_harvester.py, setup_journal_auth.py); JAMA/NEJM IP-blocked (jama_pending.json output for handoff).

**Acquired (2026-05-07, BATON 066):** JAMA + NEJM PDF harvest complete — 127 new PDFs harvested via DevTools-console pattern (jama_chrome_harvester.py: 50/50 JAMA articles; nejm_doi_lookup.py + nejm_console_script.py: 76/89 NEJM articles); 8 new M1 maintain scripts in worktree pending merge; DEFERRED-NEJM-PHASE-2 + DEFERRED-JAMA-PHASE-2 CLOSED; new deferred flags DEFERRED-MERGE-WORKTREE-TO-MAIN (127 PDFs + 8 scripts physically in worktree), DEFERRED-UNPAYWALL-CLOUDFLARE (144 OA URLs blocked), DEFERRED-DESHMUKH-2021 (ART-0302 paywalled at tandfonline), DEFERRED-PENDING-LIST-QC (jama_pending.json had wrong URL bug).

---

## Module Folders

### `00_database/` — Source of Truth
```
00_database/
├── DATABASE_GUIDE.md                  — DB contents, linkages, current uses, future applications (NEW — BATON 045)
├── db/
│   ├── ite_intelligence.db                — PRODUCTION (2,206 articles, 1,639 ITE questions)
│   ├── ite_intelligence.db-wal            — write-ahead log
│   ├── ite_intelligence_pre2018_backup_20260324_001256.db
│   ├── ite_intelligence_pre_flag15_backup.db
│   └── ite_intelligence_v1_backup_20260310_095728.db
├── crosswalk/
│   ├── crosswalk_index.json
│   └── crosswalk_report.txt
├── logs/                                  — 139+ pipeline run logs + archive/
├── readable_db_files/                     — Intelligence 2.0 CSV/JSON exports
│   ├── 4a_body_system_subcategory_trends.csv
│   ├── 4a_body_system_trends.csv
│   ├── 4a_concept_tag_trends.csv
│   ├── batch_icd10_requests.jsonl / batch_icd10_results.jsonl
│   ├── layer1_icd10_*.csv (3 files)
│   ├── layer3_pathways_*.csv (4 files)
│   ├── null_clean_ref_missing_articles_20260326.csv  — 212 missing article refs (88 AFP + others)
│   ├── sample_pathway_E11_type2dm.json
│   ├── aafp_ite_semantic_similarity.csv              — NEW (BATON 031) — 34 AAFP near-duplicates (dist < 0.30)
│   ├── aafp_ite_question_level_citation_overlap_detail.csv  — NEW (BATON 031) — 1,555 rows; research layer
│   ├── aafp_ite_question_level_citation_overlap_summary.csv — NEW (BATON 031) — 595 rows; distributable overlap list
│   └── aafp_ite_semantic_and_citation_intersection.csv      — NEW (BATON 031) — 0 rows; redundant (File 1 IS the intersection)
└── schemas/
    ├── clinical_synonym_map.json          — 151 clinical term → ICD-10 translations
    ├── icd10_mcp_lookup.json              — 1,406 MCP-verified ICD-10 codes
    └── ite-data-context-skill/
```

**DB Counts (verified live 2026-05-07, BATON 066):**
| Table | Rows | Notes |
|-------|------|-------|
| articles | 2,206 | Stable from BATON 065 |
| questions (ITE) | 1,639 | 2018–2025 (+10 recovered); blueprint 100% filled; subcategory + topic_label DROPPED |
| aafp_questions | 1,221 | blueprint 100% filled; subcategory + aafp_explanations DROPPED; correct_letter/correct_text/explanation merged in |
| question_ref_pairs | 2,722 | 222 NULL clean_ref |
| qid_art_xref | 2,710 | All 8 years (2018–2025); stable from BATON 065 |
| aafp_qid_art_xref | 864 | 643 unique questions linked (52.7%) |
| article_icd10 | 4,959 | Stable; pre-existing Windows PC enrichment (BATON 062) |
| question_icd10 | 5,774 | ~89.9%+ ITE coverage; stable (BATON 062) |
| aafp_question_icd10 | 4,753 | relevance normalized; related cap applied |
| clinical_pathways | 4,959 | Stable (BATON 062) |
| article_citation_trend | 1,740 | longitudinal citation tracking + watch_list flag |
| article_currency | 2,206 | ✅ COMPLETE 2026-05-06 — Layer 2 complete; status enum + title_signals JSON column |
| pubmed_pmid_cache | 344 | Layer 2 seed (citation_id → PMID) |
| icd10_rollup | 614 | |
| icd10_code_xref | 1,006 | |
| icd10_vec | 2,219 | BLOB — OpenAI text-embedding-3-small (1536d) |
| article_icd10_vec | 1,757 | BLOB — rebuilt 2026-04-01 (updated 2026-04-05) |
| question_icd10_vec | 2,747 | BLOB — rebuilt 2026-04-01 (updated 2026-04-05) |
| article_vec | 1,998 | sqlite-vec virtual table (rebuilt 2026-04-16) |
| question_vec | 1,639 | sqlite-vec virtual table (rebuilt 2026-04-16) |
| aafp_question_vec | 1,221 | sqlite-vec virtual table |
| aafp_citations | 1,600 | one parsed citation per row |
| aafp_citation_raw | 1,600 | full text archive + coordinates |
| question_full_vec | 1,639 | BLOB — full question embedding with blueprint (NEW — BATON 056) |
| aafp_question_full_vec | 1,221 | BLOB — full AAFP embedding with blueprint+body_system+concept_tags (NEW — BATON 056) |
| blueprint_label_vec | 5 | BLOB — 5 canonical blueprint category label embeddings (NEW — BATON 056) |
| bodysystem_label_vec | 5 | BLOB — 5 canonical body system label embeddings (NEW — BATON 056) |
| question_concepttag_vec | 2,850 | BLOB — concept_tags embedding per question (NEW — BATON 056) |
| intersection_centroid_vec | 158 | BLOB — Stable (BATON 062) |

---

### `01_module.1_warehouse/` — 3-Domain PDF Warehouse + Scripts
```
01_module.1_warehouse/
├── citation_files/                        — PDF guideline library (1,381 PDFs across 4 tiers + _dupe_archive/, post-merge)
│   ├── ITE/
│   │   ├── VC_fail/      — bulk PDFs (exa + unpaywall + JAMA/NEJM downloads; 990 total post-merge, 127 new this session in worktree pending merge)
│   │   ├── local_lite/   — 117 PDFs (VC_fail + fully enriched)
│   │   ├── VC_pass/      — 216 PDFs (VC gate passed — destined for right_click; post-merge)
│   │   └── right_click/  — 58 PDFs (VC_pass + fully enriched; highest-value tier)
│   │   [Total: 1,381 PDFs across 4 tiers post-merge — JAMA + NEJM harvest complete 2026-05-07]
│   └── AAFP/             — AAFP citation PDFs (15 total)
├── practice_questions/                    — Q&A study deliverables (gitignored; regenerable from DB)
│   ├── word_docs/        — 8 ITE_YYYY_QA.docx + 13 AAFP_quiz_NNN-NNN.docx = 21 DOCX
│   └── excel/            — 8 ITE_YYYY_QA.xlsx + 13 AAFP_quiz_NNN-NNN.xlsx = 21 XLSX
├── ite_exams/                             — Raw ABFM ITE exam PDFs (YYYY_MC.pdf + YYYY_critique.pdf)
│   ├── 2018_MC.pdf … 2025_MC.pdf         — 8 question PDFs
│   ├── 2018_critique.pdf … 2025_critique.pdf  — 8 critique PDFs
│   └── README.txt
├── scripts/
│   ├── aafp_brq_scraper.py                — v3 scraper (moved from aafp_brq/scraper/); OUTPUT_DIR=scripts/_aafp_staging/
│   ├── build/                             — full DB build sequence (run in order)
│   │   ├── README.md
│   │   ├── build_clean_question_bank.py   — Step 1: Excel → ite_questions_clean.json
│   │   ├── rebuild_ite_db_v2.py           — Step 2: core DB from JSON (2020–2025)
│   │   ├── enrich_ite_questions.py        — Step 3: Claude API enrichment (2018-2019 historical; already run)
│   │   ├── validate_db_v2.py              — Step 4: post-build QC
│   │   ├── compute_embeddings.py          — Step 5: vector embeddings (--new-only for incremental)
│   │   ├── validate_vector_search.py      — Step 6: post-embedding QC
│   │   ├── build_modular_vectors.py        — Step 7: blueprint/body_system label embeddings + concept_tag embeddings (NEW — BATON 056)
│   │   └── build_intersection_centroids.py  — Step 8: local centroid computation for Tier 1 matching (NEW — BATON 056)
│   └── maintain/                          — operational/recurring (assume DB exists)
│       ├── README.md
│       ├── aafp_cleanup_filenames.py
│       ├── aafp_fill_gaps.py
│       ├── aafp_retry_playwright.py
│       ├── aafp_retry_selenium.py
│       ├── aafp_top20_downloader.py
│       ├── aafp_vc_batch_download.py
│       ├── audit_engine_type_changes.py
│       ├── backfill_new_article_metadata.py
│       ├── build_clinical_pathways.py     — Layer 3
│       ├── build_crosswalk_index.py
│       ├── build_topic_trends.py          — Layer 4a
│       ├── match_tiers_to_library.py
│       ├── preprocess_concept_tags.py     — concept_tags via API (moved from M2 2026-03-27)
│       ├── rebuild_acquisition_list.py
│       ├── rename_tier_labels_in_db.py
│       ├── download_aafp_acquisitions.py  — AAFP acquisition PDF downloader (OA API + E-Fetch fallback)
│       ├── download_pmc_actor_batch.py    — one-off PMC batch downloader (actor-discovered URLs)
│       ├── exa_pdf_finder.py              — NEW (BATON 040) — EXA semantic search; classifies 1,572 missing articles; outputs exa_pdf_queue.csv
│       ├── exa_pdf_downloader.py          — NEW (BATON 040) — downloads direct_pdf + AAFP open_access + pmc_fulltext; 397/558 downloaded
│       ├── pmc_oa_downloader.py           — NEW (BATON 040) — NCBI OA API; direct PDF + tgz extraction; 47/95 downloaded (33 tgz)
│       ├── download_targeted.py           — NEW (BATON 047) — targeted PDF downloader for specific article list
│       ├── acquire_missing_citations.py   — NEW (BATON 065) — batch article import + PDF linkage; 208 articles added
│       ├── playwright_auth_downloader.py  — NEW (BATON 065) — JAMA/NEJM auth + download (blocked by IP; jama_pending.json output)
│       ├── browser_pdf_harvester.py       — NEW (BATON 065) — browser-based PDF harvester for paywalled journals
│       ├── setup_journal_auth.py          — NEW (BATON 065) — journal authentication setup utility
│       ├── jama_chrome_harvester.py       — NEW (BATON 066, in worktree pending merge) — Chrome-driven JAMA fetcher (50/50 proven)
│       ├── jama_prep_articlepdf_urls.py   — NEW (BATON 066, in worktree pending merge) — articlepdf URL pre-builder
│       ├── nejm_doi_lookup.py             — NEW (BATON 066, in worktree pending merge) — Crossref DOI resolver (76/89)
│       ├── nejm_build_js_batch.py         — NEW (BATON 066, in worktree pending merge) — generate JS for batch downloads
│       ├── nejm_console_script.py         — NEW (BATON 066, in worktree pending merge) — DevTools-paste script generator
│       ├── nejm_move_downloads.py         — NEW (BATON 066, in worktree pending merge) — Downloads → tier mover
│       ├── nejm_save_server.py            — NEW (BATON 066, in worktree pending merge) — local CORS server (failed approach, kept for reference)
│       └── unpaywall_retry.py             — NEW (BATON 066, in worktree pending merge) — partial OA retry via curl-cffi
├── has_extraction_audit.txt
├── MOVE_STUCK_FILES.ps1
└── README.json
```
*M1 scripts: build/ = 8 scripts, maintain/ = 36 scripts (post-merge: +8 BATON 066 scripts in worktree)*

---

### `02_module.2_processor/` — Extraction + Enrichment Pipeline
```
02_module.2_processor/
├── main.py                                — CLI entry point for extraction pipeline
├── requirements.txt
├── guideline_extractor.json               — pipeline config/manifest (v2.3)
├── PIPELINE_README.md
├── INTEGRATION_PROMPT.md
├── core/                                  — pipeline orchestration package
│   ├── ingestion.py, routing.py, screening.py
├── engines/                               — 6 clinical extraction engines
│   ├── base_engine.py, acute_engine.py, chronic_engine.py
│   ├── diagnostic_engine.py, preventive_engine.py, rct_engine.py
├── utils/
│   ├── logger.py, preprocess.py, prompt_builder.py
│   ├── qid_filename_parser.py, validator.py
├── prompts/candidates/                    — 4 extraction prompt candidates
├── source/
│   ├── 00_EX_content_outline_w_q.docx
│   ├── aafp_transcripts/                 — 50 cleaned .txt files
│   └── ite_source/                       — 2025_ITE_Questions.docx + 2025_ITE_Critique.docx
└── scripts/                               — 75 Python + 6 JS + 1 JSON + 4 Windows files
    ├── MODULE F — VC OUTLINE PIPELINE (run order: 01→02b→03→04→07→08→09→build_v6)
    ├── [8 scripts...]
    ├── KEYWORD LIBRARY PIPELINE (run order: A→B→C→D→E_v4→F→G)
    ├── [7 scripts...]
    ├── REFERENCE DATA HYGIENE
    ├── [5 scripts...]
    ├── EXTRACTION + ENRICHMENT PIPELINE
    ├── [15 scripts...]
    ├── LINKED REFS CROSSWALK PIPELINE
    ├── [3 scripts...]
    ├── DOCX BUILDERS (JS)
    ├── [6 scripts...]
    ├── ITE QUESTION PIPELINE (run order: 01→02→03→ite_tag_questions)
    ├── [11 scripts...]
    ├── AAFP BRQ PIPELINE (8 scripts — run in order after import)
    ├── [8 scripts...]
    └── WINDOWS SYSTEM FILES
        ├── batch_reprocess.ps1
        ├── extract_guideline.bat
        ├── install_context_menu.reg
        └── uninstall_context_menu.reg
```

**Planned scripts (designed, not yet built):**
- `extract_ite_critique_refs.py` — local PDF-native critique ref extractor (pdfplumber, no API, dispatcher architecture) [BATON 014]

**Built but not yet run:**
- `update_citation_trends.py` — populates/refreshes article_citation_trend table from qid_art_xref (pure SQL, 200 lines) [BATON 021 — confirmed built]
- `download_aafp_acquisitions.py` — downloads 49 PMC PDFs for ART-1938–1986; places in VC_fail/ with codon filenames (319 lines) [BATON 021 — confirmed built]

**Ref extraction architecture (two paths):**
- **Path A — DOCX (2020-2025):** `F_extract_question_refs.py` — legacy, already processed
- **Path B — PDF/API (2018-2019):** `enrich_ite_questions.py` — API extracts refs inline
- **Path C — PDF local (future):** `extract_ite_critique_refs.py` — planned, zero API cost

---

### `03_module.3_analyst/` — Score Analysis + ICD-10 + Pathways
```
03_module.3_analyst/
├── scripts/
│   ├── ite_analyze_v2.py                  — entry point; routes to v3 by default; --v2-only flag
│   ├── ite_analyzer_v3.py                 — PRIMARY — 9 analysis layers, dual bank, 3-tier Q cascade (BATON 030)
│   ├── ite_analyzer_v2.py                 — DEPRECATED — subcategory dropped; header added (BATON 030)
│   ├── ite_parser.py                      — updated (BATON 047): parse_score_report() added; longitudinal delta support
│   ├── ite_report_builder_v2.js           — patched: subcatAnalysis, TIER_LABELS, pathway sections (BATON 030)
│   ├── build_icd10_tags.py
│   ├── build_article_currency.py             — NEW (BATON 046) — Layer 2 complete; status enum (current/updated/check_needed/not_indexed); title_signals
│   ├── report_config.json                  — NEW (BATON 047) — analytics configuration
│   ├── aafp_question_reuse_investigation.py  — AAFP-ITE shared vignette finder; 38 pairs found (BATON 020)
│   ├── export_aafp_ite_relationships.py   — NEW (BATON 031) — 4-CSV AAFP–ITE relationship export
│   ├── word_doc_defaults.py               — NEW (BATON 031) — St. Luke's style template; import in ALL python-docx scripts
│   ├── build_cole_exam_series.py          — NEW (BATON 064) — Cole-specific exam series generator
│   ├── build_exam_series.py               — NEW (BATON 064) — Generalized exam series generator
│   ├── build_custom_question_set.py       — NEW (BATON 064) — Content-addressable question set generator
│   ├── build_aafp_qa.py                   — NEW (BATON 031) — File 3 Q&A builder (595 AAFP citation-overlap questions)
│   ├── build_aafp_qa_file1.py             — NEW (BATON 031) — File 1 Q&A builder (34 near-duplicate questions + ITE companion)
│   ├── build_aafp_qa_deliverables.py      — NEW (BATON 036) — 26 AAFP Q&A deliverables (13 DOCX + 13 XLSX); answer fix BATON 037
│   ├── build_ite_qa_deliverables.py       — NEW (BATON 037) — 16 ITE Q&A deliverables (8 DOCX + 8 XLSX); uniform MC choices
│   ├── abfm_reference_2025.json
│   ├── [40 additional audit/analysis scripts from BATON 059-060]
│   └── ite_parser_config.json
├── docs/
│   ├── ITE_SCORE_ANALYSIS_PIPELINE.md
│   └── README_ite_score_analysis.json
├── reports/                               — gitignored (derived)
│   ├── test_v3/ (ITE_2025_v3_Analysis_Oceana_Hopkins.docx, ITE_2025_v3_Exam_Oceana_Hopkins.docx, analysis_v2.json)
│   ├── Scholl_2024/ (NEW — BATON 047 — resident analysis output)
│   ├── AAFP_BRQ_ITE_Overlap_QA_v2.docx   — NEW (BATON 031) — 595 AAFP questions, sorted by ITE overlap
│   └── AAFP_BRQ_NearDuplicate_QA.docx    — NEW (BATON 031) — 34 near-duplicate questions with ITE companion
├── outputs/                               — gitignored (derived)
│   ├── hopkins_2025/ (analysis_v2.json, score_analysis.json)
│   └── sarkar_2025/  (analysis_v2.json, score_analysis.json)
└── resident_data/                         — gitignored (binary PHI-adjacent)
    ├── hopkins_2025_blueprint.pdf / bodysystem.pdf
    ├── sarkar_2025_blueprint.pdf / bodysystem.pdf
    └── [resident score report PDFs]
```

*M3 scripts: 55 py + 4 js — Added BATON 064: build_cole_exam_series.py, build_exam_series.py, build_custom_question_set.py (3 new scripts); Modified: ite_analyzer_v3.py (Symbol-font encoding clean); Output dir: custom_question_sets/. Modified BATON 062: ite_analyze_v2.py (body_system_sources provenance tracking), ite_analyzer_v3.py (match_top_articles() two-tier personalized/general, linked_qids + selection_basis fields), ite_report_builder_v2.js (5 issues: scoring note, provenance split, consolidated tables, concept fingerprint drugs-only, two-tier reading list)*
