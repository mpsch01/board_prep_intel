# _index.md Ã¢â‚¬â€ Ground Truth Directory Map
**Scope:** `board_prep_intel/` (project root Ã¢â‚¬â€ Option B complete 2026-04-04)
**Last Updated:** 2026-04-15 (BATON 059 â€“ body_system QC pipeline, 19 new M3 scripts, body-system-qc skill)
**Status:** Current â€“ 1,020 total PDFs (630 VC_fail + 168 VC_pass + 117 local_lite + 58 right_click + 14 dupe_archive + 15 AAFP + 16 exams); M1 build = 8 + maintain = 26; M2 = 75py + 6js; M3 = 39py + 2js + 1 json config + abfm_reference_2024.json; M5 scaffold = 3py + 35ts/tsx + 5sql; DB stable (1,998 articles); skills_abilities/ includes ite-score-analyzer-v2/ plugin + session-housekeeping agents/.

> This file maps the `board_prep_intel/` project root. `00_#PROJECT_OVERHAUL` nesting has been removed (Option B, 2026-04-04).
> Stale counts are worse than no index. Verify before trusting.

---

## Top-Level Structure

```
board_prep_intel/
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ BATON_active_059_20260415_body_system_qc_ite_aafp_complete.md  Ã¢â€ Â active BATON
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ CLAUDE.md                              Ã¢â€ Â project memory + conventions
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ REPO_MAP.md                            Ã¢â€ Â current-state architectural overview (NEW Ã¢â‚¬â€ BATON 039)
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ README.md                              Ã¢â€ Â project overview (human-readable)
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ README_PROJECT.md                      Ã¢â€ Â extended project documentation
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ _index.md                              Ã¢â€ Â this file
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ .gitattributes / .gitignore
Ã¢â€â€š
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ 00_database/                           Ã¢â€ Â source of truth (DB + supporting data)
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ 01_module.1_warehouse/                 Ã¢â€ Â M1 3-domain: citation_files/ (966 ITE PDFs across 4 tiers + 15 AAFP PDFs) + practice_questions/ (42 Q&A deliverables) + ite_exams/ (16 raw PDFs) + scripts/
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ 02_module.2_processor/                 Ã¢â€ Â M2 pipeline scripts + source inputs
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ 03_module.3_analyst/                   Ã¢â€ Â M3 score analysis + ICD-10 + pathways
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ 04_module.4_sandbox/                   Ã¢â€ Â M4 experiments and agent prototypes
â”œâ”€â”€ 05_module.5_web/                       â€  M5 web platform (Next.js + Supabase + Sanity + Railway)
Ã¢â€â€š
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ _archive_/                             Ã¢â€ Â curated deliverables + retired artifacts (renamed from archive_canonical 2026-04-03; includes docx_guideline_library/)
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ auto-memory-copies/                    Ã¢â€ Â git-tracked mirror of .auto-memory/ (durable backup)
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ baton_archive/                         Ã¢â€ Â all archived BATONs (40+)
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ extracted_json/                        Ã¢â€ Â extracted article JSONs (middle-man layer; not git-tracked)
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ key_data_files/                        Ã¢â€ Â critical reference + architecture data files
Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ skills_abilities/                      Ã¢â€ Â SDK docs, agent toolbox, skill files (includes apify-actors/)
```

**Removed/relocated (2026-03-27):** `sectional_READMEs/`, `tagging_bundle/`, `re-org_guidance/`, `master_map.JSON`, `MASTER_MAP_V.1.html`, `TEMP_MIGRATION_MANIFEST.md`
**Swept (2026-04-03, BATON 034):** `docx_guideline_library/` Ã¢â€ â€™ `_archive_/`; `archive_canonical/` Ã¢â€ â€™ renamed `_archive_/`; `apify-actors/` Ã¢â€ â€™ `skills_abilities/`; `apify_smart_article_extractor` Ã¢â€ â€™ deleted; BATON 032/033 duplicates Ã¢â€ â€™ deleted from root
**Swept (2026-04-04, BATON 035):** 5 legacy scripts deprecated (headers applied) + staged in `_legacy/` Ã¢â€ â€™ moved to offsite archive by user; originals pending Windows delete; `build_faculty_pptx.js` verified clean (no path deps)
**Swept (2026-04-04, BATON 036/037):** M1 restructured to 3-domain layout (citation_files/ + practice_questions/ + ite_exams/); all 11 M1 maintain scripts path-updated; build_ite_qa_deliverables.py + build_aafp_qa_deliverables.py built + 42 deliverables generated; ite_exams/ archive confirmed (2018Ã¢â‚¬â€œ2025)

**Fixed (2026-04-08, BATON 049):** Three ITE score analysis bugs fixed â€” BUG-047-01: ite_parser.py exam_year now extracted from PDF text (not hardcoded 2025); BUG-047-02: ite_analyzer_v3.py added BODYSYSTEM_PDF_NORM alias map + _normalize_body_system() function for body system name normalization; BUG-047-03: ite_analyze_v2.py imports normalize function, applies it to body_system_scaled dict, uses official score when available. Test reports validated: Scholl_2022/23/24, Sarkar_2025, Hopkins_2025. New finding: practice question 0-question warnings detected in qid_art_xref tagging (deferred flag: DEFERRED-PRACTICE-Q-COVERAGE).

**Improved (2026-04-08, BATON 050):** Practice Q year-over-year analysis refined â€” removed recency bonus from ite_analyzer_v3.py; updated SQL ORDER BY exam_year DESC queries; increased result limits from 20 to 60; added current_exam_year exclusion with int cast; ite_report_builder_v2.js implements two-table layout (single-dimension + cross-dimension); longitudinal year-over-year section 3b added with month-by-month trend data; --skip-reading-list and --question-count CLI flags added to ite_analyze_v2.py; SKIP_READING_LIST env var passed to Node. Ran Pjetergjoka 2024+2025 analysis with 35 questions.

**Swept (2026-04-08, BATON 048):** DATABASE_GUIDE.md relocated from 00_database/ to project root; session-housekeeping agent templates created in .claude/skills/session-housekeeping/agents/

**Added (2026-04-09, BATON 051):** 05_module.5_web/ scaffold (54 files â€” Next.js, Supabase, Sanity, Railway, OpenAI NL search) committed to GitHub by Copilot on 2026-04-08; nl_search_validation.py added to M4 sandbox; M3 script count corrected to 15py; housekeeping sweep complete.

**Refined (2026-04-12, BATON 054):** ite_report_builder_v2.js underwent 18-edit redesign for multi-year resident reporting; improved year-over-year section 3b rendering; added ABFM 2024 national benchmark comparison (PGY 1-4); abfm_reference_2024.json created in M3 scripts/; ite_analyze_v2.py and ite_analyzer_v3.py optimized for cohort-level aggregation.

**Refined (2026-04-12, BATON 054):** ite_report_builder_v2.js underwent 18-edit redesign for multi-year resident reporting; improved year-over-year section 3b rendering; added ABFM 2024 national benchmark comparison (PGY 1-4); abfm_reference_2024.json created in M3 scripts/; ite_analyze_v2.py and ite_analyzer_v3.py optimized for cohort-level aggregation.

**Added (2026-04-15, BATON 059):** Full body_system QC pipeline completed (ITE 2018-2021, 2024-2025 + AAFP); 19 new M3 scripts created (extract_score_report_labels.py through extract_critique_refs_v2.py); body-system-qc skill + methodology_scout/ directory established; 201 ITE + 129 AAFP questions in human_review queue; deferred flags: DEFERRED-BODY-SYSTEM-MERGED-UPDATE (NEW), DEFERRED-CENTROID-REBUILD (NEW), DEFERRED-HUMAN-REVIEW-BODY-SYSTEM (NEW); DEFERRED-AAFP-BODY-SYSTEM-AUDIT (CLOSED).


**Cleaned (2026-04-04, BATON 039):** Windows cleanup complete Ã¢â‚¬â€ 5 deprecated M1 scripts deleted; Option B artifacts deleted (SEVERANCE_PLAN.md, option_b_patch.py, repo_pre_severance.md); schema docs refreshed (articles.md: row count, tier column, source_type dist; questions.md: subcategory removed); script counts corrected (M1 build 6, maintain 18, M2 75py, M3 13py); REPO_MAP.md added to root
**Fixed (2026-04-04, BATON 038):** 14 code review defects resolved Ã¢â‚¬â€ hop count bugs (preprocess_concept_tags, batch_db_extract, db_guided_extractor), SCHEMAS_DIR/OUTPUT_DIR (build_icd10_tags), filename pattern (extract_ite_year), exists() guard (audit_engine_type_changes), crosswalk output paths + multi-tier scan (build_crosswalk_index), XGBoost param (classify_ite_year), JSON_DIR/LOG_DIR/OUTPUT_DIR path fixes (4 scripts), VC gate cross-check (backfill), docstring escapes (2 scripts)

---

## Module Folders

### `00_database/` Ã¢â‚¬â€ Source of Truth
```
00_database/
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ DATABASE_GUIDE.md                  Ã¢â€ Â DB contents, linkages, current uses, future applications (NEW Ã¢â‚¬â€ BATON 045)
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ db/
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ ite_intelligence.db                Ã¢â€ Â PRODUCTION (1,998 articles, 1,629 questions)
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ ite_intelligence.db-wal            Ã¢â€ Â write-ahead log
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ ite_intelligence_pre2018_backup_20260324_001256.db
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ ite_intelligence_pre_flag15_backup.db
Ã¢â€â€š   Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ ite_intelligence_v1_backup_20260310_095728.db
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ crosswalk/
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ crosswalk_index.json
Ã¢â€â€š   Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ crosswalk_report.txt
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ logs/                                  Ã¢â€ Â 139+ pipeline run logs + archive/
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ readable_db_files/                     Ã¢â€ Â Intelligence 2.0 CSV/JSON exports
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ 4a_body_system_subcategory_trends.csv
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ 4a_body_system_trends.csv
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ 4a_concept_tag_trends.csv
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ batch_icd10_requests.jsonl / batch_icd10_results.jsonl
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ layer1_icd10_*.csv (3 files)
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ layer3_pathways_*.csv (4 files)
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ null_clean_ref_missing_articles_20260326.csv  Ã¢â€ Â 212 missing article refs (88 AFP + others)
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ sample_pathway_E11_type2dm.json
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ aafp_ite_semantic_similarity.csv              Ã¢â€ Â NEW (BATON 031) Ã¢â‚¬â€ 34 AAFP near-duplicates (dist < 0.30)
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ aafp_ite_question_level_citation_overlap_detail.csv  Ã¢â€ Â NEW (BATON 031) Ã¢â‚¬â€ 1,555 rows; research layer
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ aafp_ite_question_level_citation_overlap_summary.csv Ã¢â€ Â NEW (BATON 031) Ã¢â‚¬â€ 595 rows; distributable overlap list
Ã¢â€â€š   Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ aafp_ite_semantic_and_citation_intersection.csv      Ã¢â€ Â NEW (BATON 031) Ã¢â‚¬â€ 0 rows; redundant (File 1 IS the intersection)
Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ schemas/
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ clinical_synonym_map.json          Ã¢â€ Â 151 clinical term Ã¢â€ â€™ ICD-10 translations
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ icd10_mcp_lookup.json              Ã¢â€ Â 1,406 MCP-verified ICD-10 codes
    Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ ite-data-context-skill/
```

**DB Counts (verified live 2026-04-15, BATON 059):**
| Table | Rows | Notes |
|-------|------|-------|
| articles | 1,998 | +13 new from critique rebuild; +49 AAFP acquisition (ART-1938Ã¢â‚¬â€œART-1986); PDFs pending download |
| questions (ITE) | 1,629 | 2018Ã¢â‚¬â€œ2025; blueprint 100% filled; subcategory + topic_label DROPPED |
| aafp_questions | 1,221 | blueprint 100% filled; subcategory + aafp_explanations DROPPED; correct_letter/correct_text/explanation merged in |
| question_ref_pairs | 2,722 | 222 NULL clean_ref |
| qid_art_xref | 2,485 | All 8 years (2018Ã¢â‚¬â€œ2025) |
| aafp_qid_art_xref | 864 | 643 unique questions linked (52.7%) |
| article_icd10 | 4,020 | +282 AAFP backfill (revised from live DB) (2026-03-31) |
| question_icd10 | 5,218 | 1,512/1,629 ITE questions (92.8%) Ã¢â‚¬â€ cleaned -66 no_match rows (2026-04-06) |
| aafp_question_icd10 | 4,753 | relevance normalized; related cap applied |
| clinical_pathways | 3,971 | REBUILT 2026-03-31 Ã¢â‚¬â€ blueprint-based, both banks; cleaned -49 no_match rows (2026-04-06) |
| article_citation_trend | 1,740 | longitudinal citation tracking + watch_list flag |
| article_currency | 1,998 | Ã¢Å“â€¦ NEW Ã¢â‚¬â€ Layer 2 complete; current:1100, updated:169, check_needed:106, not_indexed:610; title_signals column (JSON array) |
| pubmed_pmid_cache | 344 | Layer 2 seed (citation_id Ã¢â€ â€™ PMID) |
| icd10_rollup | 614 | |
| icd10_code_xref | 1,006 | |
| icd10_vec | 2,219 | BLOB Ã¢â‚¬â€ OpenAI text-embedding-3-small (1536d) |
| article_icd10_vec | 1,757 | BLOB Ã¢â‚¬â€ rebuilt 2026-04-01 (updated 2026-04-05) |
| question_icd10_vec | 2,747 | BLOB Ã¢â‚¬â€ rebuilt 2026-04-01 (updated 2026-04-05) |
| article_vec | 1,998 | sqlite-vec virtual table |
| question_vec | 1,629 | sqlite-vec virtual table |
| aafp_question_vec | 1,221 | sqlite-vec virtual table |
| aafp_citations | 1,600 | one parsed citation per row |
| aafp_citation_raw | 1,600 | full text archive + coordinates |
| question_full_vec | 1,629 | BLOB â€“ full question embedding with blueprint (NEW â€“ BATON 056) |
| aafp_question_full_vec | 1,221 | BLOB â€“ full AAFP embedding with blueprint+body_system+concept_tags (NEW â€“ BATON 056) |
| blueprint_label_vec | 5 | BLOB â€“ 5 canonical blueprint category label embeddings (NEW â€“ BATON 056) |
| bodysystem_label_vec | 5 | BLOB â€“ 5 canonical body system label embeddings (NEW â€“ BATON 056) |
| question_concepttag_vec | 2,850 | BLOB â€“ concept_tags embedding per question (NEW â€“ BATON 056) |
| intersection_centroid_vec | 135 | BLOB â€“ 71 ITE + 64 AAFP blueprintÃ—body_system centroids (NEW â€“ BATON 056) |

---

### `01_module.1_warehouse/` Ã¢â‚¬â€ 3-Domain PDF Warehouse + Scripts
```
01_module.1_warehouse/
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ citation_files/                        Ã¢â€ Â PDF guideline library (966 PDFs across 4 tiers + _dupe_archive/)
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ ITE/
Ã¢â€â€š   Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ VC_fail/      Ã¢â€ Â bulk PDFs (exa downloads landed here; 37 AAFP articles still awaiting manual download)
Ã¢â€â€š   Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ local_lite/   Ã¢â€ Â 117 PDFs (VC_fail + fully enriched)
Ã¢â€â€š   Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ VC_pass/      Ã¢â€ Â 94 PDFs (VC gate passed Ã¢â‚¬â€ destined for right_click)
Ã¢â€â€š   Ã¢â€â€š   Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ right_click/  Ã¢â€ Â 71 PDFs (VC_pass + fully enriched; highest-value tier)
Ã¢â€â€š   Ã¢â€â€š   [Total: 868 PDFs across 4 tiers Ã¢â‚¬â€ exa_pdf_downloader + pmc_oa_downloader complete 2026-04-05]
Ã¢â€â€š   Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ AAFP/             Ã¢â€ Â AAFP citation PDFs
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ practice_questions/                    Ã¢â€ Â Q&A study deliverables (gitignored; regenerable from DB)
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ word_docs/        Ã¢â€ Â 8 ITE_YYYY_QA.docx + 13 AAFP_quiz_NNN-NNN.docx = 21 DOCX
Ã¢â€â€š   Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ excel/            Ã¢â€ Â 8 ITE_YYYY_QA.xlsx + 13 AAFP_quiz_NNN-NNN.xlsx = 21 XLSX
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ ite_exams/                             Ã¢â€ Â Raw ABFM ITE exam PDFs (YYYY_MC.pdf + YYYY_critique.pdf)
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ 2018_MC.pdf Ã¢â‚¬Â¦ 2025_MC.pdf         Ã¢â€ Â 8 question PDFs
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ 2018_critique.pdf Ã¢â‚¬Â¦ 2025_critique.pdf  Ã¢â€ Â 8 critique PDFs
Ã¢â€â€š   Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ README.txt
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ scripts/
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ aafp_brq_scraper.py                Ã¢â€ Â v3 scraper (moved from aafp_brq/scraper/); OUTPUT_DIR=scripts/_aafp_staging/
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ build/                             Ã¢â€ Â full DB build sequence (run in order)
Ã¢â€â€š   Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ README.md
Ã¢â€â€š   Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ build_clean_question_bank.py   Ã¢â€ Â Step 1: Excel Ã¢â€ â€™ ite_questions_clean.json
Ã¢â€â€š   Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ rebuild_ite_db_v2.py           Ã¢â€ Â Step 2: core DB from JSON (2020Ã¢â‚¬â€œ2025)
Ã¢â€â€š   Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ enrich_ite_questions.py        Ã¢â€ Â Step 3: Claude API enrichment (2018-2019 historical; already run)
Ã¢â€â€š   Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ validate_db_v2.py              Ã¢â€ Â Step 4: post-build QC
Ã¢â€â€š   Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ compute_embeddings.py          Ã¢â€ Â Step 5: vector embeddings (--new-only for incremental)
Ã¢â€â€š   Ã¢â€â€š   Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ validate_vector_search.py      Ã¢â€ Â Step 6: post-embedding QC
		â”‚   â”œâ”€â”€ build_modular_vectors.py        â€  Step 7: blueprint/body_system label embeddings + concept_tag embeddings (NEW â€“ BATON 056)
		â”‚   â””â”€â”€ build_intersection_centroids.py  â€  Step 8: local centroid computation for Tier 1 matching (NEW â€“ BATON 056)
Ã¢â€â€š   Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ maintain/                          Ã¢â€ Â operational/recurring (assume DB exists)
Ã¢â€â€š       Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ README.md
Ã¢â€â€š       Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ aafp_cleanup_filenames.py
Ã¢â€â€š       Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ aafp_fill_gaps.py
Ã¢â€â€š       Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ aafp_retry_playwright.py
Ã¢â€â€š       Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ aafp_retry_selenium.py
Ã¢â€â€š       Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ aafp_top20_downloader.py
Ã¢â€â€š       Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ aafp_vc_batch_download.py
Ã¢â€â€š       Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ audit_engine_type_changes.py
Ã¢â€â€š       Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ backfill_new_article_metadata.py
Ã¢â€â€š       Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ build_clinical_pathways.py     Ã¢â€ Â Layer 3
Ã¢â€â€š       Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ build_crosswalk_index.py
Ã¢â€â€š       Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ build_topic_trends.py          Ã¢â€ Â Layer 4a
Ã¢â€â€š       Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ match_tiers_to_library.py
Ã¢â€â€š       Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ preprocess_concept_tags.py     Ã¢â€ Â concept_tags via API (moved from M2 2026-03-27)
Ã¢â€â€š       Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ rebuild_acquisition_list.py
Ã¢â€â€š       Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ rename_tier_labels_in_db.py
Ã¢â€â€š       Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ download_aafp_acquisitions.py  Ã¢â€ Â AAFP acquisition PDF downloader (OA API + E-Fetch fallback)
Ã¢â€â€š       Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ download_pmc_actor_batch.py    Ã¢â€ Â one-off PMC batch downloader (actor-discovered URLs)
Ã¢â€â€š       Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ exa_pdf_finder.py              Ã¢â€ Â NEW (BATON 040) Ã¢â‚¬â€ EXA semantic search; classifies 1,572 missing articles; outputs exa_pdf_queue.csv
Ã¢â€â€š       Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ exa_pdf_downloader.py          Ã¢â€ Â NEW (BATON 040) Ã¢â‚¬â€ downloads direct_pdf + AAFP open_access + pmc_fulltext; 397/558 downloaded
Ã¢â€â€š       Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ pmc_oa_downloader.py           Ã¢â€ Â NEW (BATON 040) Ã¢â‚¬â€ NCBI OA API; direct PDF + tgz extraction; 47/95 downloaded (33 tgz)
Ã¢â€â€š       Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ download_targeted.py           Ã¢â€ Â NEW (BATON 047) Ã¢â‚¬â€ targeted PDF downloader for specific article list
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ has_extraction_audit.txt
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ MOVE_STUCK_FILES.ps1
Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ README.json
```
*M1 scripts: build/ = 6 scripts, maintain/ = 26 scripts (recovered_unpaywall.py + pmc_oa_downloader.py + download_targeted.py added) (exa_pdf_finder, exa_pdf_downloader, pmc_oa_downloader)*

---

### `02_module.2_processor/` Ã¢â‚¬â€ Extraction + Enrichment Pipeline
```
02_module.2_processor/
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ main.py                                Ã¢â€ Â CLI entry point for extraction pipeline
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ requirements.txt
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ guideline_extractor.json               Ã¢â€ Â pipeline config/manifest (v2.3)
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ PIPELINE_README.md
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ INTEGRATION_PROMPT.md
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ core/                                  Ã¢â€ Â pipeline orchestration package
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ ingestion.py, routing.py, screening.py
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ engines/                               Ã¢â€ Â 6 clinical extraction engines
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ base_engine.py, acute_engine.py, chronic_engine.py
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ diagnostic_engine.py, preventive_engine.py, rct_engine.py
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ utils/
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ logger.py, preprocess.py, prompt_builder.py
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ qid_filename_parser.py, validator.py
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ prompts/candidates/                    Ã¢â€ Â 4 extraction prompt candidates
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ source/
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ 00_EX_content_outline_w_q.docx
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ aafp_transcripts/                 Ã¢â€ Â 50 cleaned .txt files
Ã¢â€â€š   Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ ite_source/                       Ã¢â€ Â 2025_ITE_Questions.docx + 2025_ITE_Critique.docx
Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ scripts/                               Ã¢â€ Â 75 Python + 6 JS + 1 JSON + 4 Windows files
    Ã¢â€â€š
    Ã¢â€â€šÃ¢â€â‚¬Ã¢â€â‚¬ MODULE F Ã¢â‚¬â€ VC OUTLINE PIPELINE (run order: 01Ã¢â€ â€™02bÃ¢â€ â€™03Ã¢â€ â€™04Ã¢â€ â€™07Ã¢â€ â€™08Ã¢â€ â€™09Ã¢â€ â€™build_v6)
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ 01_build_crosswalk.py
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ 02b_generate_hy_inserts_v2.py
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ 03_inject_into_outline_v3.py
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ 04_inject_poll_questions.py
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ 07_inject_supplements_v2.py
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ 08_build_supplement_doc.py
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ 09_build_pearl_callouts.py
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ build_v6_resident.py
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ build_poll_inserts.py
    Ã¢â€â€š
    Ã¢â€â€šÃ¢â€â‚¬Ã¢â€â‚¬ KEYWORD LIBRARY PIPELINE (run order: AÃ¢â€ â€™BÃ¢â€ â€™CÃ¢â€ â€™DÃ¢â€ â€™E_v4Ã¢â€ â€™FÃ¢â€ â€™G)
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ A_build_outline_terms.py
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ B_build_tfidf_keywords.py
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ C_build_vtt_time_weights.py
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ D_build_keyword_library.py
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ E_v4_question_driven.py
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ F_extract_question_refs.py         Ã¢â€ Â DOCX-based ref extractor (2020-2025 legacy path)
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ G_backfill_references.py
    Ã¢â€â€š
    Ã¢â€â€šÃ¢â€â‚¬Ã¢â€â‚¬ REFERENCE DATA HYGIENE
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ hygiene_audit.py
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ hygiene_fix.py
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ sg_reweight_v3.py
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ split_by_year.py
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ validate_v4.py
    Ã¢â€â€š
    Ã¢â€â€šÃ¢â€â‚¬Ã¢â€â‚¬ EXTRACTION + ENRICHMENT PIPELINE
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ backfill_extraction_status.py
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ batch_db_extract.py
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ calibration.py
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ clear_and_reenrich.py
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ classify_null_refs.py
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ convert_pdfs_to_json.py
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ db_guided_extractor.py
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ ite_intelligence_enricher.py       Ã¢â€ Â primary v4 enricher (Strategy 0 first)
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ ite_intelligence_enricher_batch.py
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ pre_scan.py
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ reextract_gold_list.py
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ rematch_unmatched.py
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ run_test_batch.py
    Ã¢â€â€š
    Ã¢â€â€šÃ¢â€â‚¬Ã¢â€â‚¬ LINKED REFS CROSSWALK PIPELINE
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ build_crosswalk_v2.py
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ apply_overrides.py
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ crosswalk_overrides.json           Ã¢â€ Â config
    Ã¢â€â€š
    Ã¢â€â€šÃ¢â€â‚¬Ã¢â€â‚¬ DOCX BUILDERS (JS)
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ build_db_docx.js
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ build_exemplar_v2.js
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ build_merged_docx.js
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ build_summary.js
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ synthesize.js
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ gen_linked_refs_v2.js
    Ã¢â€â€š
    Ã¢â€â€šÃ¢â€â‚¬Ã¢â€â‚¬ ITE QUESTION PIPELINE (run order: 01Ã¢â€ â€™02Ã¢â€ â€™03Ã¢â€ â€™ite_tag_questions)
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ 00_body_system_extractor.py
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ 01_ite_extractor.py                Ã¢â€ Â generalizable, --year flag
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ 02_ite_categorizer.py
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ 03_ite_merger.py
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ ite_tag_questions.py
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ ite_build_from_text.py
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ ite_merge_csv.py
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ ite_diff_banks.py
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ ite_check_columns.py
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ build_qbank_exam_version.py
    Ã¢â€â€š
    Ã¢â€â€šÃ¢â€â‚¬Ã¢â€â‚¬ AAFP BRQ PIPELINE (8 scripts Ã¢â‚¬â€ run in order after import)
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ aafp_brq_import.py                 Ã¢â€ Â v3: 5-table schema, citation splitting, vol/page dupe finder (864 xref rows)
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ aafp_keyword_extractor.py          Ã¢â€ Â TF-IDF stem+explanation keywords; --top N; 100% coverage
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ aafp_merge_keywords.py             Ã¢â€ Â merges stem+explanation keywords Ã¢â€ â€™ all_keywords (1221/1221) (BATON 021)
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ aafp_context_propagator.py         Ã¢â€ Â body_system, source_type, aafp_question_icd10 from xref JOIN
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ aafp_assign_body_system.py         Ã¢â€ Â 3-tier classifier: propagatedÃ¢â€ â€™neighborÃ¢â€ â€™keyword_freq; body_system_method audit trail (BATON 021)
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ aafp_vector_explorer.py            Ã¢â€ Â AAFP-ITE cross-corpus KNN + --save; ite_nearest_qid+dist persisted
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ aafp_enrich_concept_tags.py        Ã¢â€ Â API enrichment: concept_tags + subcategory + ICD-10; --mode linked|unlinked|all; Haiku 4.5 (BATON 022)
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ aafp_model_comparison.py           Ã¢â€ Â Haiku vs Sonnet 10-Q side-by-side comparison; writes aafp_comparison_results.json (BATON 022)
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ aafp_ref_match_v2.py              Ã¢â€ Â second-pass matcher: S2 space-tolerant vol/page, S3 AFP title, S4 Cochrane CD#, S5 guideline/society keyword (BATON 017)
    Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ batch_insert_aafp_articles.py     Ã¢â€ Â AAFP acquisition inserter: reads pubmed_acquisition_queue CSV, assigns ART-IDs, links xref (BATON 019)
    Ã¢â€â€š
    Ã¢â€â€šÃ¢â€â‚¬Ã¢â€â‚¬ WINDOWS SYSTEM FILES
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ batch_reprocess.ps1
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ extract_guideline.bat
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ install_context_menu.reg
    Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ uninstall_context_menu.reg
```

**Planned scripts (designed, not yet built):**
- `extract_ite_critique_refs.py` Ã¢â‚¬â€ local PDF-native critique ref extractor (pdfplumber, no API, dispatcher architecture) [BATON 014]

**Built but not yet run:**
- `update_citation_trends.py` Ã¢â‚¬â€ populates/refreshes article_citation_trend table from qid_art_xref (pure SQL, 200 lines) [BATON 021 Ã¢â‚¬â€ confirmed built]
- `download_aafp_acquisitions.py` Ã¢â‚¬â€ downloads 49 PMC PDFs for ART-1938Ã¢â‚¬â€œ1986; places in VC_fail/ with codon filenames (319 lines) [BATON 021 Ã¢â‚¬â€ confirmed built]

**Ref extraction architecture (two paths):**
- **Path A Ã¢â‚¬â€ DOCX (2020-2025):** `F_extract_question_refs.py` Ã¢â‚¬â€ legacy, already processed
- **Path B Ã¢â‚¬â€ PDF/API (2018-2019):** `enrich_ite_questions.py` Ã¢â‚¬â€ API extracts refs inline
- **Path C Ã¢â‚¬â€ PDF local (future):** `extract_ite_critique_refs.py` Ã¢â‚¬â€ planned, zero API cost

---

### `03_module.3_analyst/` Ã¢â‚¬â€ Score Analysis + ICD-10 + Pathways
```
03_module.3_analyst/
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ scripts/
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ ite_analyze_v2.py                  Ã¢â€ Â entry point; routes to v3 by default; --v2-only flag
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ ite_analyzer_v3.py                 Ã¢â€ Â PRIMARY Ã¢â‚¬â€ 9 analysis layers, dual bank, 3-tier Q cascade (BATON 030)
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ ite_analyzer_v2.py                 Ã¢â€ Â DEPRECATED Ã¢â‚¬â€ subcategory dropped; header added (BATON 030)
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ ite_parser.py                      Ã¢â€ Â updated (BATON 047): parse_score_report() added; longitudinal delta support
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ ite_report_builder_v2.js           Ã¢â€ Â patched: subcatAnalysis, TIER_LABELS, pathway sections (BATON 030)
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ build_icd10_tags.py
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ build_article_currency.py             Ã¢â€ Â NEW (BATON 046) Ã¢â‚¬â€ Layer 2 complete; status enum (current/updated/check_needed/not_indexed); title_signals
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ report_config.json                  Ã¢â€ Â NEW (BATON 047) Ã¢â‚¬â€ analytics configuration
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ aafp_question_reuse_investigation.py  Ã¢â€ Â AAFP-ITE shared vignette finder; 38 pairs found (BATON 020)
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ export_aafp_ite_relationships.py   Ã¢â€ Â NEW (BATON 031) Ã¢â‚¬â€ 4-CSV AAFPÃ¢â€ â€ITE relationship export
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ word_doc_defaults.py               Ã¢â€ Â NEW (BATON 031) Ã¢â‚¬â€ St. Luke's style template; import in ALL python-docx scripts
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ build_aafp_qa.py                   Ã¢â€ Â NEW (BATON 031) Ã¢â‚¬â€ File 3 Q&A builder (595 AAFP citation-overlap questions)
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ build_aafp_qa_file1.py             Ã¢â€ Â NEW (BATON 031) Ã¢â‚¬â€ File 1 Q&A builder (34 near-duplicate questions + ITE companion)
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ build_aafp_qa_deliverables.py      Ã¢â€ Â NEW (BATON 036) Ã¢â‚¬â€ 26 AAFP Q&A deliverables (13 DOCX + 13 XLSX); answer fix BATON 037
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ build_ite_qa_deliverables.py       Ã¢â€ Â NEW (BATON 037) Ã¢â‚¬â€ 16 ITE Q&A deliverables (8 DOCX + 8 XLSX); uniform MC choices
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ abfm_reference_2025.json
Ã¢â€â€š   Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ ite_parser_config.json
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ docs/
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ ITE_SCORE_ANALYSIS_PIPELINE.md
Ã¢â€â€š   Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ README_ite_score_analysis.json
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ reports/                               Ã¢â€ Â gitignored (derived)
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_v3/ (ITE_2025_v3_Analysis_Oceana_Hopkins.docx, ITE_2025_v3_Exam_Oceana_Hopkins.docx, analysis_v2.json)
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ Scholl_2024/ (NEW Ã¢â‚¬â€ BATON 047 Ã¢â‚¬â€ resident analysis output)
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ AAFP_BRQ_ITE_Overlap_QA_v2.docx   Ã¢â€ Â NEW (BATON 031) Ã¢â‚¬â€ 595 AAFP questions, sorted by ITE overlap
Ã¢â€â€š   Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ AAFP_BRQ_NearDuplicate_QA.docx    Ã¢â€ Â NEW (BATON 031) Ã¢â‚¬â€ 34 near-duplicate questions with ITE companion
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ outputs/                               Ã¢â€ Â gitignored (derived)
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ hopkins_2025/ (analysis_v2.json, score_analysis.json)
Ã¢â€â€š   Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ sarkar_2025/  (analysis_v2.json, score_analysis.json)
Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ resident_data/                         Ã¢â€ Â gitignored (binary PHI-adjacent)
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ hopkins_2025_blueprint.pdf / bodysystem.pdf
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ sarkar_2025_blueprint.pdf / bodysystem.pdf
    Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ scholl_20