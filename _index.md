# _index.md â€” Ground Truth Directory Map
**Scope:** `board_prep_intel/` (project root â€” Option B complete 2026-04-04)
**Last Updated:** 2026-04-08 (BATON 050 – practice Q year-over-year fixes; YOY section added; two-table layout in ite_report_builder_v2.js)
**Status:** Current – 1,004 total PDFs (637 VC_fail + 168 VC_pass + 117 local_lite + 58 right_click + 14 dupe_archive + 15 AAFP + 16 exams); M1 maintain = 26 scripts; M2 = 75py + 6js; M3 = 14py + 2js + report_config.json; DB stable (1,985 articles); skills_abilities/ includes ite-score-analyzer-v2/ plugin + session-housekeeping agents/.

> This file maps the `board_prep_intel/` project root. `00_#PROJECT_OVERHAUL` nesting has been removed (Option B, 2026-04-04).
> Stale counts are worse than no index. Verify before trusting.

---

## Top-Level Structure

```
board_prep_intel/
â”œâ”€â”€ BATON_active_050_20260408_practice_q_yoy_fixes.md  â† active BATON
â”œâ”€â”€ CLAUDE.md                              â† project memory + conventions
â”œâ”€â”€ REPO_MAP.md                            â† current-state architectural overview (NEW â€” BATON 039)
â”œâ”€â”€ README.md                              â† project overview (human-readable)
â”œâ”€â”€ README_PROJECT.md                      â† extended project documentation
â”œâ”€â”€ _index.md                              â† this file
â”œâ”€â”€ .gitattributes / .gitignore
â”‚
â”œâ”€â”€ 00_database/                           â† source of truth (DB + supporting data)
â”œâ”€â”€ 01_module.1_warehouse/                 â† M1 3-domain: citation_files/ (966 ITE PDFs across 4 tiers + 15 AAFP PDFs) + practice_questions/ (42 Q&A deliverables) + ite_exams/ (16 raw PDFs) + scripts/
â”œâ”€â”€ 02_module.2_processor/                 â† M2 pipeline scripts + source inputs
â”œâ”€â”€ 03_module.3_analyst/                   â† M3 score analysis + ICD-10 + pathways
â”œâ”€â”€ 04_module.4_sandbox/                   â† M4 experiments and agent prototypes
â”‚
â”œâ”€â”€ _archive_/                             â† curated deliverables + retired artifacts (renamed from archive_canonical 2026-04-03; includes docx_guideline_library/)
â”œâ”€â”€ auto-memory-copies/                    â† git-tracked mirror of .auto-memory/ (durable backup)
â”œâ”€â”€ baton_archive/                         â† all archived BATONs (40+)
â”œâ”€â”€ extracted_json/                        â† extracted article JSONs (middle-man layer; not git-tracked)
â”œâ”€â”€ key_data_files/                        â† critical reference + architecture data files
â””â”€â”€ skills_abilities/                      â† SDK docs, agent toolbox, skill files (includes apify-actors/)
```

**Removed/relocated (2026-03-27):** `sectional_READMEs/`, `tagging_bundle/`, `re-org_guidance/`, `master_map.JSON`, `MASTER_MAP_V.1.html`, `TEMP_MIGRATION_MANIFEST.md`
**Swept (2026-04-03, BATON 034):** `docx_guideline_library/` â†’ `_archive_/`; `archive_canonical/` â†’ renamed `_archive_/`; `apify-actors/` â†’ `skills_abilities/`; `apify_smart_article_extractor` â†’ deleted; BATON 032/033 duplicates â†’ deleted from root
**Swept (2026-04-04, BATON 035):** 5 legacy scripts deprecated (headers applied) + staged in `_legacy/` â†’ moved to offsite archive by user; originals pending Windows delete; `build_faculty_pptx.js` verified clean (no path deps)
**Swept (2026-04-04, BATON 036/037):** M1 restructured to 3-domain layout (citation_files/ + practice_questions/ + ite_exams/); all 11 M1 maintain scripts path-updated; build_ite_qa_deliverables.py + build_aafp_qa_deliverables.py built + 42 deliverables generated; ite_exams/ archive confirmed (2018â€“2025)

**Fixed (2026-04-08, BATON 049):** Three ITE score analysis bugs fixed — BUG-047-01: ite_parser.py exam_year now extracted from PDF text (not hardcoded 2025); BUG-047-02: ite_analyzer_v3.py added BODYSYSTEM_PDF_NORM alias map + _normalize_body_system() function for body system name normalization; BUG-047-03: ite_analyze_v2.py imports normalize function, applies it to body_system_scaled dict, uses official score when available. Test reports validated: Scholl_2022/23/24, Sarkar_2025, Hopkins_2025. New finding: practice question 0-question warnings detected in qid_art_xref tagging (deferred flag: DEFERRED-PRACTICE-Q-COVERAGE).

**Improved (2026-04-08, BATON 050):** Practice Q year-over-year analysis refined — removed recency bonus from ite_analyzer_v3.py; updated SQL ORDER BY exam_year DESC queries; increased result limits from 20 to 60; added current_exam_year exclusion with int cast; ite_report_builder_v2.js implements two-table layout (single-dimension + cross-dimension); longitudinal year-over-year section 3b added with month-by-month trend data; --skip-reading-list and --question-count CLI flags added to ite_analyze_v2.py; SKIP_READING_LIST env var passed to Node. Ran Pjetergjoka 2024+2025 analysis with 35 questions.

**Swept (2026-04-08, BATON 048):** DATABASE_GUIDE.md relocated from 00_database/ to project root; session-housekeeping agent templates created in .claude/skills/session-housekeeping/agents/

**Cleaned (2026-04-04, BATON 039):** Windows cleanup complete â€” 5 deprecated M1 scripts deleted; Option B artifacts deleted (SEVERANCE_PLAN.md, option_b_patch.py, repo_pre_severance.md); schema docs refreshed (articles.md: row count, tier column, source_type dist; questions.md: subcategory removed); script counts corrected (M1 build 6, maintain 18, M2 75py, M3 13py); REPO_MAP.md added to root
**Fixed (2026-04-04, BATON 038):** 14 code review defects resolved â€” hop count bugs (preprocess_concept_tags, batch_db_extract, db_guided_extractor), SCHEMAS_DIR/OUTPUT_DIR (build_icd10_tags), filename pattern (extract_ite_year), exists() guard (audit_engine_type_changes), crosswalk output paths + multi-tier scan (build_crosswalk_index), XGBoost param (classify_ite_year), JSON_DIR/LOG_DIR/OUTPUT_DIR path fixes (4 scripts), VC gate cross-check (backfill), docstring escapes (2 scripts)

---

## Module Folders

### `00_database/` â€” Source of Truth
```
00_database/
â”œâ”€â”€ DATABASE_GUIDE.md                  â† DB contents, linkages, current uses, future applications (NEW â€” BATON 045)
â”œâ”€â”€ db/
â”‚   â”œâ”€â”€ ite_intelligence.db                â† PRODUCTION (1,985 articles, 1,629 questions)
â”‚   â”œâ”€â”€ ite_intelligence.db-wal            â† write-ahead log
â”‚   â”œâ”€â”€ ite_intelligence_pre2018_backup_20260324_001256.db
â”‚   â”œâ”€â”€ ite_intelligence_pre_flag15_backup.db
â”‚   â””â”€â”€ ite_intelligence_v1_backup_20260310_095728.db
â”œâ”€â”€ crosswalk/
â”‚   â”œâ”€â”€ crosswalk_index.json
â”‚   â””â”€â”€ crosswalk_report.txt
â”œâ”€â”€ logs/                                  â† 139+ pipeline run logs + archive/
â”œâ”€â”€ readable_db_files/                     â† Intelligence 2.0 CSV/JSON exports
â”‚   â”œâ”€â”€ 4a_body_system_subcategory_trends.csv
â”‚   â”œâ”€â”€ 4a_body_system_trends.csv
â”‚   â”œâ”€â”€ 4a_concept_tag_trends.csv
â”‚   â”œâ”€â”€ batch_icd10_requests.jsonl / batch_icd10_results.jsonl
â”‚   â”œâ”€â”€ layer1_icd10_*.csv (3 files)
â”‚   â”œâ”€â”€ layer3_pathways_*.csv (4 files)
â”‚   â”œâ”€â”€ null_clean_ref_missing_articles_20260326.csv  â† 212 missing article refs (88 AFP + others)
â”‚   â”œâ”€â”€ sample_pathway_E11_type2dm.json
â”‚   â”œâ”€â”€ aafp_ite_semantic_similarity.csv              â† NEW (BATON 031) â€” 34 AAFP near-duplicates (dist < 0.30)
â”‚   â”œâ”€â”€ aafp_ite_question_level_citation_overlap_detail.csv  â† NEW (BATON 031) â€” 1,555 rows; research layer
â”‚   â”œâ”€â”€ aafp_ite_question_level_citation_overlap_summary.csv â† NEW (BATON 031) â€” 595 rows; distributable overlap list
â”‚   â””â”€â”€ aafp_ite_semantic_and_citation_intersection.csv      â† NEW (BATON 031) â€” 0 rows; redundant (File 1 IS the intersection)
â””â”€â”€ schemas/
    â”œâ”€â”€ clinical_synonym_map.json          â† 151 clinical term â†’ ICD-10 translations
    â”œâ”€â”€ icd10_mcp_lookup.json              â† 1,406 MCP-verified ICD-10 codes
    â””â”€â”€ ite-data-context-skill/
```

**DB Counts (verified live 2026-04-08, BATON 046):**
| Table | Rows | Notes |
|-------|------|-------|
| articles | 1,985 | +49 AAFP acquisition (ART-1938â€“ART-1986); PDFs pending download |
| questions (ITE) | 1,629 | 2018â€“2025; blueprint 100% filled; subcategory + topic_label DROPPED |
| aafp_questions | 1,221 | blueprint 100% filled; subcategory + aafp_explanations DROPPED; correct_letter/correct_text/explanation merged in |
| question_ref_pairs | 2,722 | 222 NULL clean_ref |
| qid_art_xref | 2,470 | All 8 years (2018â€“2025) |
| aafp_qid_art_xref | 864 | 643 unique questions linked (52.7%) |
| article_icd10 | 4,020 | +282 AAFP backfill (revised from live DB) (2026-03-31) |
| question_icd10 | 5,218 | 1,512/1,629 ITE questions (92.8%) â€” cleaned -66 no_match rows (2026-04-06) |
| aafp_question_icd10 | 4,753 | relevance normalized; related cap applied |
| clinical_pathways | 3,971 | REBUILT 2026-03-31 â€” blueprint-based, both banks; cleaned -49 no_match rows (2026-04-06) |
| article_citation_trend | 1,740 | longitudinal citation tracking + watch_list flag |
| article_currency | 1,985 | âœ… NEW â€” Layer 2 complete; current:1100, updated:169, check_needed:106, not_indexed:610; title_signals column (JSON array) |
| pubmed_pmid_cache | 344 | Layer 2 seed (citation_id â†’ PMID) |
| icd10_rollup | 614 | |
| icd10_code_xref | 1,006 | |
| icd10_vec | 2,219 | BLOB â€” OpenAI text-embedding-3-small (1536d) |
| article_icd10_vec | 1,757 | BLOB â€” rebuilt 2026-04-01 (updated 2026-04-05) |
| question_icd10_vec | 2,747 | BLOB â€” rebuilt 2026-04-01 (updated 2026-04-05) |
| article_vec | 1,985 | sqlite-vec virtual table |
| question_vec | 1,629 | sqlite-vec virtual table |
| aafp_question_vec | 1,221 | sqlite-vec virtual table |
| aafp_citations | 1,600 | one parsed citation per row |
| aafp_citation_raw | 1,600 | full text archive + coordinates |

---

### `01_module.1_warehouse/` â€” 3-Domain PDF Warehouse + Scripts
```
01_module.1_warehouse/
â”œâ”€â”€ citation_files/                        â† PDF guideline library (966 PDFs across 4 tiers + _dupe_archive/)
â”‚   â”œâ”€â”€ ITE/
â”‚   â”‚   â”œâ”€â”€ VC_fail/      â† bulk PDFs (exa downloads landed here; 37 AAFP articles still awaiting manual download)
â”‚   â”‚   â”œâ”€â”€ local_lite/   â† 117 PDFs (VC_fail + fully enriched)
â”‚   â”‚   â”œâ”€â”€ VC_pass/      â† 94 PDFs (VC gate passed â€” destined for right_click)
â”‚   â”‚   â””â”€â”€ right_click/  â† 71 PDFs (VC_pass + fully enriched; highest-value tier)
â”‚   â”‚   [Total: 868 PDFs across 4 tiers â€” exa_pdf_downloader + pmc_oa_downloader complete 2026-04-05]
â”‚   â””â”€â”€ AAFP/             â† AAFP citation PDFs
â”œâ”€â”€ practice_questions/                    â† Q&A study deliverables (gitignored; regenerable from DB)
â”‚   â”œâ”€â”€ word_docs/        â† 8 ITE_YYYY_QA.docx + 13 AAFP_quiz_NNN-NNN.docx = 21 DOCX
â”‚   â””â”€â”€ excel/            â† 8 ITE_YYYY_QA.xlsx + 13 AAFP_quiz_NNN-NNN.xlsx = 21 XLSX
â”œâ”€â”€ ite_exams/                             â† Raw ABFM ITE exam PDFs (YYYY_MC.pdf + YYYY_critique.pdf)
â”‚   â”œâ”€â”€ 2018_MC.pdf â€¦ 2025_MC.pdf         â† 8 question PDFs
â”‚   â”œâ”€â”€ 2018_critique.pdf â€¦ 2025_critique.pdf  â† 8 critique PDFs
â”‚   â””â”€â”€ README.txt
â”œâ”€â”€ scripts/
â”‚   â”œâ”€â”€ aafp_brq_scraper.py                â† v3 scraper (moved from aafp_brq/scraper/); OUTPUT_DIR=scripts/_aafp_staging/
â”‚   â”œâ”€â”€ build/                             â† full DB build sequence (run in order)
â”‚   â”‚   â”œâ”€â”€ README.md
â”‚   â”‚   â”œâ”€â”€ build_clean_question_bank.py   â† Step 1: Excel â†’ ite_questions_clean.json
â”‚   â”‚   â”œâ”€â”€ rebuild_ite_db_v2.py           â† Step 2: core DB from JSON (2020â€“2025)
â”‚   â”‚   â”œâ”€â”€ enrich_ite_questions.py        â† Step 3: Claude API enrichment (2018-2019 historical; already run)
â”‚   â”‚   â”œâ”€â”€ validate_db_v2.py              â† Step 4: post-build QC
â”‚   â”‚   â”œâ”€â”€ compute_embeddings.py          â† Step 5: vector embeddings (--new-only for incremental)
â”‚   â”‚   â””â”€â”€ validate_vector_search.py      â† Step 6: post-embedding QC
â”‚   â””â”€â”€ maintain/                          â† operational/recurring (assume DB exists)
â”‚       â”œâ”€â”€ README.md
â”‚       â”œâ”€â”€ aafp_cleanup_filenames.py
â”‚       â”œâ”€â”€ aafp_fill_gaps.py
â”‚       â”œâ”€â”€ aafp_retry_playwright.py
â”‚       â”œâ”€â”€ aafp_retry_selenium.py
â”‚       â”œâ”€â”€ aafp_top20_downloader.py
â”‚       â”œâ”€â”€ aafp_vc_batch_download.py
â”‚       â”œâ”€â”€ audit_engine_type_changes.py
â”‚       â”œâ”€â”€ backfill_new_article_metadata.py
â”‚       â”œâ”€â”€ build_clinical_pathways.py     â† Layer 3
â”‚       â”œâ”€â”€ build_crosswalk_index.py
â”‚       â”œâ”€â”€ build_topic_trends.py          â† Layer 4a
â”‚       â”œâ”€â”€ match_tiers_to_library.py
â”‚       â”œâ”€â”€ preprocess_concept_tags.py     â† concept_tags via API (moved from M2 2026-03-27)
â”‚       â”œâ”€â”€ rebuild_acquisition_list.py
â”‚       â”œâ”€â”€ rename_tier_labels_in_db.py
â”‚       â”œâ”€â”€ download_aafp_acquisitions.py  â† AAFP acquisition PDF downloader (OA API + E-Fetch fallback)
â”‚       â”œâ”€â”€ download_pmc_actor_batch.py    â† one-off PMC batch downloader (actor-discovered URLs)
â”‚       â”œâ”€â”€ exa_pdf_finder.py              â† NEW (BATON 040) â€” EXA semantic search; classifies 1,572 missing articles; outputs exa_pdf_queue.csv
â”‚       â”œâ”€â”€ exa_pdf_downloader.py          â† NEW (BATON 040) â€” downloads direct_pdf + AAFP open_access + pmc_fulltext; 397/558 downloaded
â”‚       â”œâ”€â”€ pmc_oa_downloader.py           â† NEW (BATON 040) â€” NCBI OA API; direct PDF + tgz extraction; 47/95 downloaded (33 tgz)
â”‚       â””â”€â”€ download_targeted.py           â† NEW (BATON 047) â€” targeted PDF downloader for specific article list
â”œâ”€â”€ has_extraction_audit.txt
â”œâ”€â”€ MOVE_STUCK_FILES.ps1
â””â”€â”€ README.json
```
*M1 scripts: build/ = 6 scripts, maintain/ = 26 scripts (recovered_unpaywall.py + pmc_oa_downloader.py + download_targeted.py added) (exa_pdf_finder, exa_pdf_downloader, pmc_oa_downloader)*

---

### `02_module.2_processor/` â€” Extraction + Enrichment Pipeline
```
02_module.2_processor/
â”œâ”€â”€ main.py                                â† CLI entry point for extraction pipeline
â”œâ”€â”€ requirements.txt
â”œâ”€â”€ guideline_extractor.json               â† pipeline config/manifest (v2.3)
â”œâ”€â”€ PIPELINE_README.md
â”œâ”€â”€ INTEGRATION_PROMPT.md
â”œâ”€â”€ core/                                  â† pipeline orchestration package
â”‚   â”œâ”€â”€ ingestion.py, routing.py, screening.py
â”œâ”€â”€ engines/                               â† 6 clinical extraction engines
â”‚   â”œâ”€â”€ base_engine.py, acute_engine.py, chronic_engine.py
â”‚   â”œâ”€â”€ diagnostic_engine.py, preventive_engine.py, rct_engine.py
â”œâ”€â”€ utils/
â”‚   â”œâ”€â”€ logger.py, preprocess.py, prompt_builder.py
â”‚   â”œâ”€â”€ qid_filename_parser.py, validator.py
â”œâ”€â”€ prompts/candidates/                    â† 4 extraction prompt candidates
â”œâ”€â”€ source/
â”‚   â”œâ”€â”€ 00_EX_content_outline_w_q.docx
â”‚   â”œâ”€â”€ aafp_transcripts/                 â† 50 cleaned .txt files
â”‚   â””â”€â”€ ite_source/                       â† 2025_ITE_Questions.docx + 2025_ITE_Critique.docx
â””â”€â”€ scripts/                               â† 75 Python + 6 JS + 1 JSON + 4 Windows files
    â”‚
    â”‚â”€â”€ MODULE F â€” VC OUTLINE PIPELINE (run order: 01â†’02bâ†’03â†’04â†’07â†’08â†’09â†’build_v6)
    â”œâ”€â”€ 01_build_crosswalk.py
    â”œâ”€â”€ 02b_generate_hy_inserts_v2.py
    â”œâ”€â”€ 03_inject_into_outline_v3.py
    â”œâ”€â”€ 04_inject_poll_questions.py
    â”œâ”€â”€ 07_inject_supplements_v2.py
    â”œâ”€â”€ 08_build_supplement_doc.py
    â”œâ”€â”€ 09_build_pearl_callouts.py
    â”œâ”€â”€ build_v6_resident.py
    â”œâ”€â”€ build_poll_inserts.py
    â”‚
    â”‚â”€â”€ KEYWORD LIBRARY PIPELINE (run order: Aâ†’Bâ†’Câ†’Dâ†’E_v4â†’Fâ†’G)
    â”œâ”€â”€ A_build_outline_terms.py
    â”œâ”€â”€ B_build_tfidf_keywords.py
    â”œâ”€â”€ C_build_vtt_time_weights.py
    â”œâ”€â”€ D_build_keyword_library.py
    â”œâ”€â”€ E_v4_question_driven.py
    â”œâ”€â”€ F_extract_question_refs.py         â† DOCX-based ref extractor (2020-2025 legacy path)
    â”œâ”€â”€ G_backfill_references.py
    â”‚
    â”‚â”€â”€ REFERENCE DATA HYGIENE
    â”œâ”€â”€ hygiene_audit.py
    â”œâ”€â”€ hygiene_fix.py
    â”œâ”€â”€ sg_reweight_v3.py
    â”œâ”€â”€ split_by_year.py
    â”œâ”€â”€ validate_v4.py
    â”‚
    â”‚â”€â”€ EXTRACTION + ENRICHMENT PIPELINE
    â”œâ”€â”€ backfill_extraction_status.py
    â”œâ”€â”€ batch_db_extract.py
    â”œâ”€â”€ calibration.py
    â”œâ”€â”€ clear_and_reenrich.py
    â”œâ”€â”€ classify_null_refs.py
    â”œâ”€â”€ convert_pdfs_to_json.py
    â”œâ”€â”€ db_guided_extractor.py
    â”œâ”€â”€ ite_intelligence_enricher.py       â† primary v4 enricher (Strategy 0 first)
    â”œâ”€â”€ ite_intelligence_enricher_batch.py
    â”œâ”€â”€ pre_scan.py
    â”œâ”€â”€ reextract_gold_list.py
    â”œâ”€â”€ rematch_unmatched.py
    â”œâ”€â”€ run_test_batch.py
    â”‚
    â”‚â”€â”€ LINKED REFS CROSSWALK PIPELINE
    â”œâ”€â”€ build_crosswalk_v2.py
    â”œâ”€â”€ apply_overrides.py
    â”œâ”€â”€ crosswalk_overrides.json           â† config
    â”‚
    â”‚â”€â”€ DOCX BUILDERS (JS)
    â”œâ”€â”€ build_db_docx.js
    â”œâ”€â”€ build_exemplar_v2.js
    â”œâ”€â”€ build_merged_docx.js
    â”œâ”€â”€ build_summary.js
    â”œâ”€â”€ synthesize.js
    â”œâ”€â”€ gen_linked_refs_v2.js
    â”‚
    â”‚â”€â”€ ITE QUESTION PIPELINE (run order: 01â†’02â†’03â†’ite_tag_questions)
    â”œâ”€â”€ 00_body_system_extractor.py
    â”œâ”€â”€ 01_ite_extractor.py                â† generalizable, --year flag
    â”œâ”€â”€ 02_ite_categorizer.py
    â”œâ”€â”€ 03_ite_merger.py
    â”œâ”€â”€ ite_tag_questions.py
    â”œâ”€â”€ ite_build_from_text.py
    â”œâ”€â”€ ite_merge_csv.py
    â”œâ”€â”€ ite_diff_banks.py
    â”œâ”€â”€ ite_check_columns.py
    â”œâ”€â”€ build_qbank_exam_version.py
    â”‚
    â”‚â”€â”€ AAFP BRQ PIPELINE (8 scripts â€” run in order after import)
    â”œâ”€â”€ aafp_brq_import.py                 â† v3: 5-table schema, citation splitting, vol/page dupe finder (864 xref rows)
    â”œâ”€â”€ aafp_keyword_extractor.py          â† TF-IDF stem+explanation keywords; --top N; 100% coverage
    â”œâ”€â”€ aafp_merge_keywords.py             â† merges stem+explanation keywords â†’ all_keywords (1221/1221) (BATON 021)
    â”œâ”€â”€ aafp_context_propagator.py         â† body_system, source_type, aafp_question_icd10 from xref JOIN
    â”œâ”€â”€ aafp_assign_body_system.py         â† 3-tier classifier: propagatedâ†’neighborâ†’keyword_freq; body_system_method audit trail (BATON 021)
    â”œâ”€â”€ aafp_vector_explorer.py            â† AAFP-ITE cross-corpus KNN + --save; ite_nearest_qid+dist persisted
    â”œâ”€â”€ aafp_enrich_concept_tags.py        â† API enrichment: concept_tags + subcategory + ICD-10; --mode linked|unlinked|all; Haiku 4.5 (BATON 022)
    â”œâ”€â”€ aafp_model_comparison.py           â† Haiku vs Sonnet 10-Q side-by-side comparison; writes aafp_comparison_results.json (BATON 022)
    â”œâ”€â”€ aafp_ref_match_v2.py              â† second-pass matcher: S2 space-tolerant vol/page, S3 AFP title, S4 Cochrane CD#, S5 guideline/society keyword (BATON 017)
    â””â”€â”€ batch_insert_aafp_articles.py     â† AAFP acquisition inserter: reads pubmed_acquisition_queue CSV, assigns ART-IDs, links xref (BATON 019)
    â”‚
    â”‚â”€â”€ WINDOWS SYSTEM FILES
    â”œâ”€â”€ batch_reprocess.ps1
    â”œâ”€â”€ extract_guideline.bat
    â”œâ”€â”€ install_context_menu.reg
    â””â”€â”€ uninstall_context_menu.reg
```

**Planned scripts (designed, not yet built):**
- `extract_ite_critique_refs.py` â€” local PDF-native critique ref extractor (pdfplumber, no API, dispatcher architecture) [BATON 014]

**Built but not yet run:**
- `update_citation_trends.py` â€” populates/refreshes article_citation_trend table from qid_art_xref (pure SQL, 200 lines) [BATON 021 â€” confirmed built]
- `download_aafp_acquisitions.py` â€” downloads 49 PMC PDFs for ART-1938â€“1986; places in VC_fail/ with codon filenames (319 lines) [BATON 021 â€” confirmed built]

**Ref extraction architecture (two paths):**
- **Path A â€” DOCX (2020-2025):** `F_extract_question_refs.py` â€” legacy, already processed
- **Path B â€” PDF/API (2018-2019):** `enrich_ite_questions.py` â€” API extracts refs inline
- **Path C â€” PDF local (future):** `extract_ite_critique_refs.py` â€” planned, zero API cost

---

### `03_module.3_analyst/` â€” Score Analysis + ICD-10 + Pathways
```
03_module.3_analyst/
â”œâ”€â”€ scripts/
â”‚   â”œâ”€â”€ ite_analyze_v2.py                  â† entry point; routes to v3 by default; --v2-only flag
â”‚   â”œâ”€â”€ ite_analyzer_v3.py                 â† PRIMARY â€” 9 analysis layers, dual bank, 3-tier Q cascade (BATON 030)
â”‚   â”œâ”€â”€ ite_analyzer_v2.py                 â† DEPRECATED â€” subcategory dropped; header added (BATON 030)
â”‚   â”œâ”€â”€ ite_parser.py                      â† updated (BATON 047): parse_score_report() added; longitudinal delta support
â”‚   â”œâ”€â”€ ite_report_builder_v2.js           â† patched: subcatAnalysis, TIER_LABELS, pathway sections (BATON 030)
â”‚   â”œâ”€â”€ build_icd10_tags.py
â”‚   â”œâ”€â”€ build_article_currency.py             â† NEW (BATON 046) â€” Layer 2 complete; status enum (current/updated/check_needed/not_indexed); title_signals
â”‚   â”œâ”€â”€ report_config.json                  â† NEW (BATON 047) â€” analytics configuration
â”‚   â”œâ”€â”€ aafp_question_reuse_investigation.py  â† AAFP-ITE shared vignette finder; 38 pairs found (BATON 020)
â”‚   â”œâ”€â”€ export_aafp_ite_relationships.py   â† NEW (BATON 031) â€” 4-CSV AAFPâ†”ITE relationship export
â”‚   â”œâ”€â”€ word_doc_defaults.py               â† NEW (BATON 031) â€” St. Luke's style template; import in ALL python-docx scripts
â”‚   â”œâ”€â”€ build_aafp_qa.py                   â† NEW (BATON 031) â€” File 3 Q&A builder (595 AAFP citation-overlap questions)
â”‚   â”œâ”€â”€ build_aafp_qa_file1.py             â† NEW (BATON 031) â€” File 1 Q&A builder (34 near-duplicate questions + ITE companion)
â”‚   â”œâ”€â”€ build_aafp_qa_deliverables.py      â† NEW (BATON 036) â€” 26 AAFP Q&A deliverables (13 DOCX + 13 XLSX); answer fix BATON 037
â”‚   â”œâ”€â”€ build_ite_qa_deliverables.py       â† NEW (BATON 037) â€” 16 ITE Q&A deliverables (8 DOCX + 8 XLSX); uniform MC choices
â”‚   â”œâ”€â”€ abfm_reference_2025.json
â”‚   â””â”€â”€ ite_parser_config.json
â”œâ”€â”€ docs/
â”‚   â”œâ”€â”€ ITE_SCORE_ANALYSIS_PIPELINE.md
â”‚   â””â”€â”€ README_ite_score_analysis.json
â”œâ”€â”€ reports/                               â† gitignored (derived)
â”‚   â”œâ”€â”€ test_v3/ (ITE_2025_v3_Analysis_Oceana_Hopkins.docx, ITE_2025_v3_Exam_Oceana_Hopkins.docx, analysis_v2.json)
â”‚   â”œâ”€â”€ Scholl_2024/ (NEW â€” BATON 047 â€” resident analysis output)
â”‚   â”œâ”€â”€ AAFP_BRQ_ITE_Overlap_QA_v2.docx   â† NEW (BATON 031) â€” 595 AAFP questions, sorted by ITE overlap
â”‚   â””â”€â”€ AAFP_BRQ_NearDuplicate_QA.docx    â† NEW (BATON 031) â€” 34 near-duplicate questions with ITE companion
â”œâ”€â”€ outputs/                               â† gitignored (derived)
â”‚   â”œâ”€â”€ hopkins_2025/ (analysis_v2.json, score_analysis.json)
â”‚   â””â”€â”€ sarkar_2025/  (analysis_v2.json, score_analysis.json)
â””â”€â”€ resident_data/                         â† gitignored (binary PHI-adjacent)
    â”œâ”€â”€ hopkins_2025_blueprint.pdf / bodysystem.pdf
    â”œâ”€â”€ sarkar_2025_blueprint.pdf / bodysystem.pdf
    â””â”€â”€ scholl_2025_ENCRYPTED_22/23/24.pdf â† FLAG 30 (needs password)
```
*14 Python + 2 JS + 1 JSON config (report_config.json)*

### `04_module.4_sandbox/` â€” Experiments
```
04_module.4_sandbox/
â””â”€â”€ _DELETE_THESE_FROM_WINDOWS.txt  â† cleanup checklist (sandbox AAFP files â†’ moved to M1; delete originals from Windows)
```

---

## Supporting Folders

### `auto-memory-copies/` â€” Auto-Memory Backup (moved to root 2026-03-27)
Durable backup of all `.auto-memory/` files. Updated each housekeeping sweep.

### `_archive_/` â€” Curated Deliverables + Retired Artifacts
Renamed from `archive_canonical/` on 2026-04-03. Also houses retired artifacts relocated during Sweep 1.
```
_archive_/
â”œâ”€â”€ 01_curriculum/          â† enriched VC outline, supplement, linked refs DOCX
â”œâ”€â”€ 02_question_bank/       â† formatted question bank exports (CSV, DOCX)
â”œâ”€â”€ 03_analysis/            â† ITE analysis workbook, QC report
â”œâ”€â”€ 04_reference_data/      â† reference tier CSVs, QRP pairs, crosswalk CSVs
â”œâ”€â”€ 05_acquisition/         â† ranked acquisition list, BATON templates
â”œâ”€â”€ docx_guideline_library/ â† 1,518 legacy DOCXs (derived data; moved from root 2026-04-03)
â””â”€â”€ README_canonical.json
```

**Note on DOCX library:** 1,518 DOCXs moved from root to `_archive_/docx_guideline_library/` on 2026-04-03. Derived data â€” all ART-tagged DOCXs regenerable from pipeline (`build_summary.js` + existing PDFs + DB).

### `extracted_json/` â€” Extracted Article JSONs (not git-tracked)
```
extracted_json/
â”œâ”€â”€ manifest.json                          â† root manifest (only file at root)
â”œâ”€â”€ synthesis_library/                     â† ~242 pre-pipeline guideline JSONs (all legacy flat JSONs consolidated 2026-03-27)
â”‚   â”œâ”€â”€ README.md
â”‚   â””â”€â”€ move_files.ps1
â”œâ”€â”€ VC_pass_batch/                         â† 95 enriched JSONs from VC_pass tier
â”œâ”€â”€ VC_fail_batch/                         â† 147 enriched JSONs from VC_fail tier
â”œâ”€â”€ raw_txt/                               â† 21 raw text files
â”œâ”€â”€ pre_calibration_archive/
â”œâ”€â”€ VC_pass_archive/                       â† (target) completed right_click JSONs
â”œâ”€â”€ VC_fail_archive/                       â† (target) completed local_lite JSONs
â””â”€â”€ [legacy empty batch placeholders]
```
*Root is clean â€” only manifest.json remains at top level.*

### `key_data_files/` â€” Critical Reference + Architecture Data
```
key_data_files/
â”œâ”€â”€ session_hy_inserts_v7.json             â† VC GATE â€” 352 citations (PROTECTED)
â”œâ”€â”€ ABFM_ITE_Master_v2.xlsx               â† original source
â”œâ”€â”€ 00_DB_qbank_master_20-25.csv
â”œâ”€â”€ ABFM_ITE_QuestionRefPairs_2020-2025.csv
â”œâ”€â”€ body_system_full.csv
â”œâ”€â”€ clinical_synonym_map.json
â”œâ”€â”€ ite_questions_clean.json
â”œâ”€â”€ poll_inserts.json
â”œâ”€â”€ session_keyword_library.json
â”œâ”€â”€ vtt_time_weights.json
â”œâ”€â”€ README_AAFP_course_integration.json
â”œâ”€â”€ FILE_NAMING_SPEC.md                    â† moved from re-org_guidance 2026-03-27
â”œâ”€â”€ ITE_Intelligence_2.0_Architecture.md  â† moved from re-org_guidance 2026-03-27
â”œâ”€â”€ project_overhaul_inventory.md         â† original inventory (March 21) â€” historical ref
â”œâ”€â”€ script_library.csv                    â† moved from re-org_guidance 2026-03-27
â””â”€â”€ data_exams/
    â”œâ”€â”€ ITE_2020_raw.csv through ITE_2025_raw.csv
```

### `baton_archive/` â€” Session Handoff History
- 40+ archived BATONs
- `templates+guides/` â€” BATON protocol v2.0, JSON spec

### `skills_abilities/` â€” SDK Docs + Agent Toolbox + Skills
- 17+ SDK reference files + notebooks
- `agents/` â€” pdf_sourcer_agent.py + 6 helpers
- `apify-actors/` â€” citation_crawler actor source (deployed: actor ID `rh50nQRP7BupbUF64`, build 0.3.1) â€” moved from root 2026-04-03
- `ite-data-context-skill/` â€” domain skill for ITE DB queries
- `ite-score-analyzer-v2/` â€” NEW (BATON 047) â€” ITE score analysis plugin v1.0.0 (score report analysis, cohort comparison, study plan generation)
- `API_primer.md`

---

## Data Flow Summary
```
External Sources (ITE exams 2018-2025, AAFP course, guidelines, score reports)
        â†“
M1 Warehouse â€” store
  00_database/        (DB: 1,985 articles, 1,629 ITE questions, 1,221 AAFP BRQ questions)
  01_module.1_warehouse/  (PDF library: 868 PDFs, 4 tiers)
  key_data_files/     (VC gate, exam CSVs, architecture docs)
        â†“
M2 Processor â€” transform
  02_module.2_processor/scripts/
  (extraction â†’ enrichment â†’ concept_tags â†’ keywords â†’ DOCX)
        â†“
M3 Analyst â€” analyze
  03_module.3_analyst/scripts/
  (score analysis, ICD-10 tagging, pathways, trends)
        â†“
M4 Sandbox â€” experiment
  04_module.4_sandbox/  (agents, new ideas)
```

---

## New Year Integration Pipeline (as of BATON 014)

**For new exam year (2026+) â€” full pipeline:**
1. `01_ite_extractor.py --year 2026` â†’ CSV
2. `02_ite_categorizer.py` â†’ body system labels
3. `03_ite_merger.py` â†’ merged into master bank
4. *(planned)* `extract_ite_critique_refs.py --year 2026` â†’ question_ref_pairs
5. *(planned)* generalized DB insert script â†’ questions into DB
6. `ite_tag_questions.py` â†’ BlueprintCategory, Subcategory, etc.
7. `preprocess_concept_tags.py` â†’ concept_tags (M1/maintain/)
8. `compute_embeddings.py --new-only` â†’ vectors
9. *(planned)* `update_citation_trends.py` â†’ article_citation_trend refresh

**For pre-2020 years (2016-2017) â€” template path:**
Uses M1/build/ scripts 3-6 as template, adapted for year-specific PDF format.

---

## Schema-Level Column Coverage

### questions table â€” ITE (1,629 rows)
| Column | Coverage |
|--------|----------|
| body_system_merged | 100% |
| stem_keywords | 100% |
| explanation_keywords | 100% |
| all_keywords | 100% |
| concept_tags | 100% |
| blueprint | **100%** â€” 2024/2025 Gold Standard; 2018-2023 API pseudo-label (Sonnet, 70.4% accuracy vs Gold Standard) |

### aafp_questions table (1,221 rows)
| Column | Coverage | Notes |
|--------|----------|-------|
| body_system | 100% | 3-tier classifier (propagated â†’ neighbor â†’ keyword_freq) |
| body_system_method | 100% | audit trail |
| all_keywords | 100% | stem + explanation merged |
| source_type | 100% | propagated from article xref |
| ite_nearest_qid / dist | 100% | KNN match to ITE corpus |
| concept_tags | **100%** | Haiku 4.5 API â€” complete 2026-03-29 |

### articles table (1,985 rows)
| Column | Coverage |
|--------|----------|
| source_type | 100% |
| categories | 90.2% (189 unresolvable; 49 new articles pending backfill) |
| tier | 100% |
| engine_type | 100% |
| auto_assigned | 100% |

---

## Version Control

| Item | Value |
|------|-------|
| Remote | `https://github.com/mpsch01/board_prep_intel` (private) |
| Branch | `main` |
| Latest commit | `6fb312c` (2026-04-04, BATON 039 â€” REPO_MAP.md added) |
| .gitignore strategy | **Code + docs on GitHub. Binaries on local disk / Google Drive.** |

**What IS tracked:** all Python, JS, JSON, Markdown, `.md`, `.bat`, `.ps1`, `.reg`, `.txt` files. Basically: anything readable and diffable.

**What is NOT tracked (gitignored):** `*.db`, `*.pdf`, `extracted_json/`, `resident_data/`, `__pycache__/`, `*.pyc`, `*.log`, `node_modules/`, `outputs/` (derived). The DB and PDFs are source data â€” too large for GitHub; kept on local disk and mirrored to Google Drive.

**Why this split:** DB is ~50MB+ and changes with every session