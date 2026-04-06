# _index.md — Ground Truth Directory Map
**Scope:** `board_prep_intel/` (project root — Option B complete 2026-04-04)
**Last Updated:** 2026-04-06 (BATON 045 — ite_analyzer_v3.py AAFP quota fix; ite_report_builder_v2.js overhaul; question_icd10 cleanup)
**Status:** Current — 966 ITE + 15 AAFP PDFs; M1 maintain = 25 scripts; M2 updated (75py + 6js); DB cleaned (no_match rows removed).

> This file maps the `board_prep_intel/` project root. `00_#PROJECT_OVERHAUL` nesting has been removed (Option B, 2026-04-04).
> Stale counts are worse than no index. Verify before trusting.

---

## Top-Level Structure

```
board_prep_intel/
├── BATON_active_045_20260406_analyzer_report_builder_cleanup.md  ← active BATON
├── CLAUDE.md                              ← project memory + conventions
├── REPO_MAP.md                            ← current-state architectural overview (NEW — BATON 039)
├── README.md                              ← project overview (human-readable)
├── README_PROJECT.md                      ← extended project documentation
├── _index.md                              ← this file
├── .gitattributes / .gitignore
│
├── 00_database/                           ← source of truth (DB + supporting data)
├── 01_module.1_warehouse/                 ← M1 3-domain: citation_files/ (966 ITE PDFs across 4 tiers + 15 AAFP PDFs) + practice_questions/ (42 Q&A deliverables) + ite_exams/ (16 raw PDFs) + scripts/
├── 02_module.2_processor/                 ← M2 pipeline scripts + source inputs
├── 03_module.3_analyst/                   ← M3 score analysis + ICD-10 + pathways
├── 04_module.4_sandbox/                   ← M4 experiments and agent prototypes
│
├── _archive_/                             ← curated deliverables + retired artifacts (renamed from archive_canonical 2026-04-03; includes docx_guideline_library/)
├── auto-memory-copies/                    ← git-tracked mirror of .auto-memory/ (durable backup)
├── baton_archive/                         ← all archived BATONs (40+)
├── extracted_json/                        ← extracted article JSONs (middle-man layer; not git-tracked)
├── key_data_files/                        ← critical reference + architecture data files
└── skills_abilities/                      ← SDK docs, agent toolbox, skill files (includes apify-actors/)
```

**Removed/relocated (2026-03-27):** `sectional_READMEs/`, `tagging_bundle/`, `re-org_guidance/`, `master_map.JSON`, `MASTER_MAP_V.1.html`, `TEMP_MIGRATION_MANIFEST.md`
**Swept (2026-04-03, BATON 034):** `docx_guideline_library/` → `_archive_/`; `archive_canonical/` → renamed `_archive_/`; `apify-actors/` → `skills_abilities/`; `apify_smart_article_extractor` → deleted; BATON 032/033 duplicates → deleted from root
**Swept (2026-04-04, BATON 035):** 5 legacy scripts deprecated (headers applied) + staged in `_legacy/` → moved to offsite archive by user; originals pending Windows delete; `build_faculty_pptx.js` verified clean (no path deps)
**Swept (2026-04-04, BATON 036/037):** M1 restructured to 3-domain layout (citation_files/ + practice_questions/ + ite_exams/); all 11 M1 maintain scripts path-updated; build_ite_qa_deliverables.py + build_aafp_qa_deliverables.py built + 42 deliverables generated; ite_exams/ archive confirmed (2018–2025)
**Cleaned (2026-04-04, BATON 039):** Windows cleanup complete — 5 deprecated M1 scripts deleted; Option B artifacts deleted (SEVERANCE_PLAN.md, option_b_patch.py, repo_pre_severance.md); schema docs refreshed (articles.md: row count, tier column, source_type dist; questions.md: subcategory removed); script counts corrected (M1 build 6, maintain 18, M2 75py, M3 13py); REPO_MAP.md added to root
**Fixed (2026-04-04, BATON 038):** 14 code review defects resolved — hop count bugs (preprocess_concept_tags, batch_db_extract, db_guided_extractor), SCHEMAS_DIR/OUTPUT_DIR (build_icd10_tags), filename pattern (extract_ite_year), exists() guard (audit_engine_type_changes), crosswalk output paths + multi-tier scan (build_crosswalk_index), XGBoost param (classify_ite_year), JSON_DIR/LOG_DIR/OUTPUT_DIR path fixes (4 scripts), VC gate cross-check (backfill), docstring escapes (2 scripts)

---

## Module Folders

### `00_database/` — Source of Truth
```
00_database/
├── DATABASE_GUIDE.md                  ← DB contents, linkages, current uses, future applications (NEW — BATON 045)
├── db/
│   ├── ite_intelligence.db                ← PRODUCTION (1,985 articles, 1,629 questions)
│   ├── ite_intelligence.db-wal            ← write-ahead log
│   ├── ite_intelligence_pre2018_backup_20260324_001256.db
│   ├── ite_intelligence_pre_flag15_backup.db
│   └── ite_intelligence_v1_backup_20260310_095728.db
├── crosswalk/
│   ├── crosswalk_index.json
│   └── crosswalk_report.txt
├── logs/                                  ← 139+ pipeline run logs + archive/
├── readable_db_files/                     ← Intelligence 2.0 CSV/JSON exports
│   ├── 4a_body_system_subcategory_trends.csv
│   ├── 4a_body_system_trends.csv
│   ├── 4a_concept_tag_trends.csv
│   ├── batch_icd10_requests.jsonl / batch_icd10_results.jsonl
│   ├── layer1_icd10_*.csv (3 files)
│   ├── layer3_pathways_*.csv (4 files)
│   ├── null_clean_ref_missing_articles_20260326.csv  ← 212 missing article refs (88 AFP + others)
│   ├── sample_pathway_E11_type2dm.json
│   ├── aafp_ite_semantic_similarity.csv              ← NEW (BATON 031) — 34 AAFP near-duplicates (dist < 0.30)
│   ├── aafp_ite_question_level_citation_overlap_detail.csv  ← NEW (BATON 031) — 1,555 rows; research layer
│   ├── aafp_ite_question_level_citation_overlap_summary.csv ← NEW (BATON 031) — 595 rows; distributable overlap list
│   └── aafp_ite_semantic_and_citation_intersection.csv      ← NEW (BATON 031) — 0 rows; redundant (File 1 IS the intersection)
└── schemas/
    ├── clinical_synonym_map.json          ← 151 clinical term → ICD-10 translations
    ├── icd10_mcp_lookup.json              ← 1,406 MCP-verified ICD-10 codes
    └── ite-data-context-skill/
```

**DB Counts (verified live 2026-04-03, BATON 034):**
| Table | Rows | Notes |
|-------|------|-------|
| articles | 1,985 | +49 AAFP acquisition (ART-1938–ART-1986); PDFs pending download |
| questions (ITE) | 1,629 | 2018–2025; blueprint 100% filled; subcategory + topic_label DROPPED |
| aafp_questions | 1,221 | blueprint 100% filled; subcategory + aafp_explanations DROPPED; correct_letter/correct_text/explanation merged in |
| question_ref_pairs | 2,722 | 222 NULL clean_ref |
| qid_art_xref | 2,470 | All 8 years (2018–2025) |
| aafp_qid_art_xref | 864 | 643 unique questions linked (52.7%) |
| article_icd10 | 4,020 | +282 AAFP backfill (revised from live DB) (2026-03-31) |
| question_icd10 | 5,218 | 1,512/1,629 ITE questions (92.8%) — cleaned -66 no_match rows (2026-04-06) |
| aafp_question_icd10 | 4,753 | relevance normalized; related cap applied |
| clinical_pathways | 3,971 | REBUILT 2026-03-31 — blueprint-based, both banks; cleaned -49 no_match rows (2026-04-06) |
| article_citation_trend | 1,740 | longitudinal citation tracking + watch_list flag |
| pubmed_pmid_cache | 344 | Layer 2 seed (citation_id → PMID) |
| icd10_rollup | 614 | |
| icd10_code_xref | 1,006 | |
| icd10_vec | 2,219 | BLOB — OpenAI text-embedding-3-small (1536d) |
| article_icd10_vec | 1,757 | BLOB — rebuilt 2026-04-01 (updated 2026-04-05) |
| question_icd10_vec | 2,747 | BLOB — rebuilt 2026-04-01 (updated 2026-04-05) |
| article_vec | 1,985 | sqlite-vec virtual table |
| question_vec | 1,629 | sqlite-vec virtual table |
| aafp_question_vec | 1,221 | sqlite-vec virtual table |
| aafp_citations | 1,600 | one parsed citation per row |
| aafp_citation_raw | 1,600 | full text archive + coordinates |

---

### `01_module.1_warehouse/` — 3-Domain PDF Warehouse + Scripts
```
01_module.1_warehouse/
├── citation_files/                        ← PDF guideline library (966 PDFs across 4 tiers + _dupe_archive/)
│   ├── ITE/
│   │   ├── VC_fail/      ← bulk PDFs (exa downloads landed here; 37 AAFP articles still awaiting manual download)
│   │   ├── local_lite/   ← 117 PDFs (VC_fail + fully enriched)
│   │   ├── VC_pass/      ← 94 PDFs (VC gate passed — destined for right_click)
│   │   └── right_click/  ← 71 PDFs (VC_pass + fully enriched; highest-value tier)
│   │   [Total: 868 PDFs across 4 tiers — exa_pdf_downloader + pmc_oa_downloader complete 2026-04-05]
│   └── AAFP/             ← AAFP citation PDFs
├── practice_questions/                    ← Q&A study deliverables (gitignored; regenerable from DB)
│   ├── word_docs/        ← 8 ITE_YYYY_QA.docx + 13 AAFP_quiz_NNN-NNN.docx = 21 DOCX
│   └── excel/            ← 8 ITE_YYYY_QA.xlsx + 13 AAFP_quiz_NNN-NNN.xlsx = 21 XLSX
├── ite_exams/                             ← Raw ABFM ITE exam PDFs (YYYY_MC.pdf + YYYY_critique.pdf)
│   ├── 2018_MC.pdf … 2025_MC.pdf         ← 8 question PDFs
│   ├── 2018_critique.pdf … 2025_critique.pdf  ← 8 critique PDFs
│   └── README.txt
├── scripts/
│   ├── aafp_brq_scraper.py                ← v3 scraper (moved from aafp_brq/scraper/); OUTPUT_DIR=scripts/_aafp_staging/
│   ├── build/                             ← full DB build sequence (run in order)
│   │   ├── README.md
│   │   ├── build_clean_question_bank.py   ← Step 1: Excel → ite_questions_clean.json
│   │   ├── rebuild_ite_db_v2.py           ← Step 2: core DB from JSON (2020–2025)
│   │   ├── enrich_ite_questions.py        ← Step 3: Claude API enrichment (2018-2019 historical; already run)
│   │   ├── validate_db_v2.py              ← Step 4: post-build QC
│   │   ├── compute_embeddings.py          ← Step 5: vector embeddings (--new-only for incremental)
│   │   └── validate_vector_search.py      ← Step 6: post-embedding QC
│   └── maintain/                          ← operational/recurring (assume DB exists)
│       ├── README.md
│       ├── aafp_cleanup_filenames.py
│       ├── aafp_fill_gaps.py
│       ├── aafp_retry_playwright.py
│       ├── aafp_retry_selenium.py
│       ├── aafp_top20_downloader.py
│       ├── aafp_vc_batch_download.py
│       ├── audit_engine_type_changes.py
│       ├── backfill_new_article_metadata.py
│       ├── build_clinical_pathways.py     ← Layer 3
│       ├── build_crosswalk_index.py
│       ├── build_topic_trends.py          ← Layer 4a
│       ├── match_tiers_to_library.py
│       ├── preprocess_concept_tags.py     ← concept_tags via API (moved from M2 2026-03-27)
│       ├── rebuild_acquisition_list.py
│       ├── rename_tier_labels_in_db.py
│       ├── download_aafp_acquisitions.py  ← AAFP acquisition PDF downloader (OA API + E-Fetch fallback)
│       ├── download_pmc_actor_batch.py    ← one-off PMC batch downloader (actor-discovered URLs)
│       ├── exa_pdf_finder.py              ← NEW (BATON 040) — EXA semantic search; classifies 1,572 missing articles; outputs exa_pdf_queue.csv
│       ├── exa_pdf_downloader.py          ← NEW (BATON 040) — downloads direct_pdf + AAFP open_access + pmc_fulltext; 397/558 downloaded
│       └── pmc_oa_downloader.py           ← NEW (BATON 040) — NCBI OA API; direct PDF + tgz extraction; 47/95 downloaded (33 tgz)
├── has_extraction_audit.txt
├── MOVE_STUCK_FILES.ps1
└── README.json
```
*M1 scripts: build/ = 6 scripts, maintain/ = 23 scripts (recovered_unpaywall.py + pmc_oa_downloader.py added) (exa_pdf_finder, exa_pdf_downloader, pmc_oa_downloader)*

---

### `02_module.2_processor/` — Extraction + Enrichment Pipeline
```
02_module.2_processor/
├── main.py                                ← CLI entry point for extraction pipeline
├── requirements.txt
├── guideline_extractor.json               ← pipeline config/manifest (v2.3)
├── PIPELINE_README.md
├── INTEGRATION_PROMPT.md
├── core/                                  ← pipeline orchestration package
│   ├── ingestion.py, routing.py, screening.py
├── engines/                               ← 6 clinical extraction engines
│   ├── base_engine.py, acute_engine.py, chronic_engine.py
│   ├── diagnostic_engine.py, preventive_engine.py, rct_engine.py
├── utils/
│   ├── logger.py, preprocess.py, prompt_builder.py
│   ├── qid_filename_parser.py, validator.py
├── prompts/candidates/                    ← 4 extraction prompt candidates
├── source/
│   ├── 00_EX_content_outline_w_q.docx
│   ├── aafp_transcripts/                 ← 50 cleaned .txt files
│   └── ite_source/                       ← 2025_ITE_Questions.docx + 2025_ITE_Critique.docx
└── scripts/                               ← 75 Python + 6 JS + 1 JSON + 4 Windows files
    │
    │── MODULE F — VC OUTLINE PIPELINE (run order: 01→02b→03→04→07→08→09→build_v6)
    ├── 01_build_crosswalk.py
    ├── 02b_generate_hy_inserts_v2.py
    ├── 03_inject_into_outline_v3.py
    ├── 04_inject_poll_questions.py
    ├── 07_inject_supplements_v2.py
    ├── 08_build_supplement_doc.py
    ├── 09_build_pearl_callouts.py
    ├── build_v6_resident.py
    ├── build_poll_inserts.py
    │
    │── KEYWORD LIBRARY PIPELINE (run order: A→B→C→D→E_v4→F→G)
    ├── A_build_outline_terms.py
    ├── B_build_tfidf_keywords.py
    ├── C_build_vtt_time_weights.py
    ├── D_build_keyword_library.py
    ├── E_v4_question_driven.py
    ├── F_extract_question_refs.py         ← DOCX-based ref extractor (2020-2025 legacy path)
    ├── G_backfill_references.py
    │
    │── REFERENCE DATA HYGIENE
    ├── hygiene_audit.py
    ├── hygiene_fix.py
    ├── sg_reweight_v3.py
    ├── split_by_year.py
    ├── validate_v4.py
    │
    │── EXTRACTION + ENRICHMENT PIPELINE
    ├── backfill_extraction_status.py
    ├── batch_db_extract.py
    ├── calibration.py
    ├── clear_and_reenrich.py
    ├── classify_null_refs.py
    ├── convert_pdfs_to_json.py
    ├── db_guided_extractor.py
    ├── ite_intelligence_enricher.py       ← primary v4 enricher (Strategy 0 first)
    ├── ite_intelligence_enricher_batch.py
    ├── pre_scan.py
    ├── reextract_gold_list.py
    ├── rematch_unmatched.py
    ├── run_test_batch.py
    │
    │── LINKED REFS CROSSWALK PIPELINE
    ├── build_crosswalk_v2.py
    ├── apply_overrides.py
    ├── crosswalk_overrides.json           ← config
    │
    │── DOCX BUILDERS (JS)
    ├── build_db_docx.js
    ├── build_exemplar_v2.js
    ├── build_merged_docx.js
    ├── build_summary.js
    ├── synthesize.js
    ├── gen_linked_refs_v2.js
    │
    │── ITE QUESTION PIPELINE (run order: 01→02→03→ite_tag_questions)
    ├── 00_body_system_extractor.py
    ├── 01_ite_extractor.py                ← generalizable, --year flag
    ├── 02_ite_categorizer.py
    ├── 03_ite_merger.py
    ├── ite_tag_questions.py
    ├── ite_build_from_text.py
    ├── ite_merge_csv.py
    ├── ite_diff_banks.py
    ├── ite_check_columns.py
    ├── build_qbank_exam_version.py
    │
    │── AAFP BRQ PIPELINE (8 scripts — run in order after import)
    ├── aafp_brq_import.py                 ← v3: 5-table schema, citation splitting, vol/page dupe finder (864 xref rows)
    ├── aafp_keyword_extractor.py          ← TF-IDF stem+explanation keywords; --top N; 100% coverage
    ├── aafp_merge_keywords.py             ← merges stem+explanation keywords → all_keywords (1221/1221) (BATON 021)
    ├── aafp_context_propagator.py         ← body_system, source_type, aafp_question_icd10 from xref JOIN
    ├── aafp_assign_body_system.py         ← 3-tier classifier: propagated→neighbor→keyword_freq; body_system_method audit trail (BATON 021)
    ├── aafp_vector_explorer.py            ← AAFP-ITE cross-corpus KNN + --save; ite_nearest_qid+dist persisted
    ├── aafp_enrich_concept_tags.py        ← API enrichment: concept_tags + subcategory + ICD-10; --mode linked|unlinked|all; Haiku 4.5 (BATON 022)
    ├── aafp_model_comparison.py           ← Haiku vs Sonnet 10-Q side-by-side comparison; writes aafp_comparison_results.json (BATON 022)
    ├── aafp_ref_match_v2.py              ← second-pass matcher: S2 space-tolerant vol/page, S3 AFP title, S4 Cochrane CD#, S5 guideline/society keyword (BATON 017)
    └── batch_insert_aafp_articles.py     ← AAFP acquisition inserter: reads pubmed_acquisition_queue CSV, assigns ART-IDs, links xref (BATON 019)
    │
    │── WINDOWS SYSTEM FILES
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
│   ├── ite_analyze_v2.py                  ← entry point; routes to v3 by default; --v2-only flag
│   ├── ite_analyzer_v3.py                 ← PRIMARY — 9 analysis layers, dual bank, 3-tier Q cascade (BATON 030)
│   ├── ite_analyzer_v2.py                 ← DEPRECATED — subcategory dropped; header added (BATON 030)
│   ├── ite_parser.py
│   ├── ite_report_builder_v2.js           ← patched: subcatAnalysis, TIER_LABELS, pathway sections (BATON 030)
│   ├── build_icd10_tags.py
│   ├── aafp_question_reuse_investigation.py  ← AAFP-ITE shared vignette finder; 38 pairs found (BATON 020)
│   ├── export_aafp_ite_relationships.py   ← NEW (BATON 031) — 4-CSV AAFP↔ITE relationship export
│   ├── word_doc_defaults.py               ← NEW (BATON 031) — St. Luke's style template; import in ALL python-docx scripts
│   ├── build_aafp_qa.py                   ← NEW (BATON 031) — File 3 Q&A builder (595 AAFP citation-overlap questions)
│   ├── build_aafp_qa_file1.py             ← NEW (BATON 031) — File 1 Q&A builder (34 near-duplicate questions + ITE companion)
│   ├── build_aafp_qa_deliverables.py      ← NEW (BATON 036) — 26 AAFP Q&A deliverables (13 DOCX + 13 XLSX); answer fix BATON 037
│   ├── build_ite_qa_deliverables.py       ← NEW (BATON 037) — 16 ITE Q&A deliverables (8 DOCX + 8 XLSX); uniform MC choices
│   ├── abfm_reference_2025.json
│   └── ite_parser_config.json
├── docs/
│   ├── ITE_SCORE_ANALYSIS_PIPELINE.md
│   └── README_ite_score_analysis.json
├── reports/                               ← gitignored (derived)
│   ├── test_v3/ (ITE_2025_v3_Analysis_Oceana_Hopkins.docx, ITE_2025_v3_Exam_Oceana_Hopkins.docx, analysis_v2.json)
│   ├── AAFP_BRQ_ITE_Overlap_QA_v2.docx   ← NEW (BATON 031) — 595 AAFP questions, sorted by ITE overlap
│   └── AAFP_BRQ_NearDuplicate_QA.docx    ← NEW (BATON 031) — 34 near-duplicate questions with ITE companion
├── outputs/                               ← gitignored (derived)
│   ├── hopkins_2025/ (analysis_v2.json, score_analysis.json)
│   └── sarkar_2025/  (analysis_v2.json, score_analysis.json)
└── resident_data/                         ← gitignored (binary PHI-adjacent)
    ├── hopkins_2025_blueprint.pdf / bodysystem.pdf
    ├── sarkar_2025_blueprint.pdf / bodysystem.pdf
    └── scholl_2025_ENCRYPTED_22/23/24.pdf ← FLAG 30 (needs password)
```
*13 Python + 2 JS + 2 JSON configs*

### `04_module.4_sandbox/` — Experiments
```
04_module.4_sandbox/
└── _DELETE_THESE_FROM_WINDOWS.txt  ← cleanup checklist (sandbox AAFP files → moved to M1; delete originals from Windows)
```

---

## Supporting Folders

### `auto-memory-copies/` — Auto-Memory Backup (moved to root 2026-03-27)
Durable backup of all `.auto-memory/` files. Updated each housekeeping sweep.

### `_archive_/` — Curated Deliverables + Retired Artifacts
Renamed from `archive_canonical/` on 2026-04-03. Also houses retired artifacts relocated during Sweep 1.
```
_archive_/
├── 01_curriculum/          ← enriched VC outline, supplement, linked refs DOCX
├── 02_question_bank/       ← formatted question bank exports (CSV, DOCX)
├── 03_analysis/            ← ITE analysis workbook, QC report
├── 04_reference_data/      ← reference tier CSVs, QRP pairs, crosswalk CSVs
├── 05_acquisition/         ← ranked acquisition list, BATON templates
├── docx_guideline_library/ ← 1,518 legacy DOCXs (derived data; moved from root 2026-04-03)
└── README_canonical.json
```

**Note on DOCX library:** 1,518 DOCXs moved from root to `_archive_/docx_guideline_library/` on 2026-04-03. Derived data — all ART-tagged DOCXs regenerable from pipeline (`build_summary.js` + existing PDFs + DB).

### `extracted_json/` — Extracted Article JSONs (not git-tracked)
```
extracted_json/
├── manifest.json                          ← root manifest (only file at root)
├── synthesis_library/                     ← ~242 pre-pipeline guideline JSONs (all legacy flat JSONs consolidated 2026-03-27)
│   ├── README.md
│   └── move_files.ps1
├── VC_pass_batch/                         ← 95 enriched JSONs from VC_pass tier
├── VC_fail_batch/                         ← 147 enriched JSONs from VC_fail tier
├── raw_txt/                               ← 21 raw text files
├── pre_calibration_archive/
├── VC_pass_archive/                       ← (target) completed right_click JSONs
├── VC_fail_archive/                       ← (target) completed local_lite JSONs
└── [legacy empty batch placeholders]
```
*Root is clean — only manifest.json remains at top level.*

### `key_data_files/` — Critical Reference + Architecture Data
```
key_data_files/
├── session_hy_inserts_v7.json             ← VC GATE — 352 citations (PROTECTED)
├── ABFM_ITE_Master_v2.xlsx               ← original source
├── 00_DB_qbank_master_20-25.csv
├── ABFM_ITE_QuestionRefPairs_2020-2025.csv
├── body_system_full.csv
├── clinical_synonym_map.json
├── ite_questions_clean.json
├── poll_inserts.json
├── session_keyword_library.json
├── vtt_time_weights.json
├── README_AAFP_course_integration.json
├── FILE_NAMING_SPEC.md                    ← moved from re-org_guidance 2026-03-27
├── ITE_Intelligence_2.0_Architecture.md  ← moved from re-org_guidance 2026-03-27
├── project_overhaul_inventory.md         ← original inventory (March 21) — historical ref
├── script_library.csv                    ← moved from re-org_guidance 2026-03-27
└── data_exams/
    ├── ITE_2020_raw.csv through ITE_2025_raw.csv
```

### `baton_archive/` — Session Handoff History
- 40+ archived BATONs
- `templates+guides/` — BATON protocol v2.0, JSON spec

### `skills_abilities/` — SDK Docs + Agent Toolbox + Skills
- 17+ SDK reference files + notebooks
- `agents/` — pdf_sourcer_agent.py + 6 helpers
- `apify-actors/` — citation_crawler actor source (deployed: actor ID `rh50nQRP7BupbUF64`, build 0.3.1) — moved from root 2026-04-03
- `ite-data-context-skill/` — domain skill for ITE DB queries
- `API_primer.md`

---

## Data Flow Summary
```
External Sources (ITE exams 2018-2025, AAFP course, guidelines, score reports)
        ↓
M1 Warehouse — store
  00_database/        (DB: 1,985 articles, 1,629 ITE questions, 1,221 AAFP BRQ questions)
  01_module.1_warehouse/  (PDF library: 868 PDFs, 4 tiers)
  key_data_files/     (VC gate, exam CSVs, architecture docs)
        ↓
M2 Processor — transform
  02_module.2_processor/scripts/
  (extraction → enrichment → concept_tags → keywords → DOCX)
        ↓
M3 Analyst — analyze
  03_module.3_analyst/scripts/
  (score analysis, ICD-10 tagging, pathways, trends)
        ↓
M4 Sandbox — experiment
  04_module.4_sandbox/  (agents, new ideas)
```

---

## New Year Integration Pipeline (as of BATON 014)

**For new exam year (2026+) — full pipeline:**
1. `01_ite_extractor.py --year 2026` → CSV
2. `02_ite_categorizer.py` → body system labels
3. `03_ite_merger.py` → merged into master bank
4. *(planned)* `extract_ite_critique_refs.py --year 2026` → question_ref_pairs
5. *(planned)* generalized DB insert script → questions into DB
6. `ite_tag_questions.py` → BlueprintCategory, Subcategory, etc.
7. `preprocess_concept_tags.py` → concept_tags (M1/maintain/)
8. `compute_embeddings.py --new-only` → vectors
9. *(planned)* `update_citation_trends.py` → article_citation_trend refresh

**For pre-2020 years (2016-2017) — template path:**
Uses M1/build/ scripts 3-6 as template, adapted for year-specific PDF format.

---

## Schema-Level Column Coverage

### questions table — ITE (1,629 rows)
| Column | Coverage |
|--------|----------|
| body_system_merged | 100% |
| stem_keywords | 100% |
| explanation_keywords | 100% |
| all_keywords | 100% |
| concept_tags | 100% |
| blueprint | **100%** — 2024/2025 Gold Standard; 2018-2023 API pseudo-label (Sonnet, 70.4% accuracy vs Gold Standard) |

### aafp_questions table (1,221 rows)
| Column | Coverage | Notes |
|--------|----------|-------|
| body_system | 100% | 3-tier classifier (propagated → neighbor → keyword_freq) |
| body_system_method | 100% | audit trail |
| all_keywords | 100% | stem + explanation merged |
| source_type | 100% | propagated from article xref |
| ite_nearest_qid / dist | 100% | KNN match to ITE corpus |
| concept_tags | **100%** | Haiku 4.5 API — complete 2026-03-29 |

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
| Latest commit | `6fb312c` (2026-04-04, BATON 039 — REPO_MAP.md added) |
| .gitignore strategy | **Code + docs on GitHub. Binaries on local disk / Google Drive.** |

**What IS tracked:** all Python, JS, JSON, Markdown, `.md`, `.bat`, `.ps1`, `.reg`, `.txt` files. Basically: anything readable and diffable.

**What is NOT tracked (gitignored):** `*.db`, `*.pdf`, `extracted_json/`, `resident_data/`, `__pycache__/`, `*.pyc`, `*.log`, `node_modules/`, `outputs/` (derived). The DB and PDFs are source data — too large for GitHub; kept on local disk and mirrored to Google Drive.

**Why this split:** DB is ~50MB+ and changes with every session — wrong tool for binary tracking. PDFs are immutable source files. GitHub tracks intent and logic; Google Drive / local disk tracks the data.

---

## Housekeeping Log

| Date | Action |
|------|--------|
| 2026-04-05 | BATON 040: EXA PDF pipeline built. 3 new M1 maintain scripts: exa_pdf_finder.py (1,572 articles searched; 259 direct_pdf + 332 open_access + 109 pmc_fulltext + 872 landing_page), exa_pdf_downloader.py (397/558 downloaded: 215 direct + 190 AAFP), pmc_oa_downloader.py (47/95 downloaded: 14 direct OA + 33 tgz extracted). PDFs 413→868. M1 maintain 18→21. DEFERRED-G: unpaywall_scanner.py (next round). |
| 2026-04-04 | BATON 035–039: Option B flatten complete (board_prep_intel/ is now flat project root). M1 restructured to 3-domain layout (citation_files/ + practice_questions/ + ite_exams/). 42 Q&A deliverables built (16 ITE + 26 AAFP). 14 code review defects fixed. 5 deprecated scripts deleted. Schema docs corrected (articles.md tier column rewritten — VC_fail/pass/local_lite/right_click; row count 1985; source_type refreshed). REPO_MAP.md added. Git: remote renamed board_prep_intel. M1 build 6py, maintain 18py, M2 75py, M3 13py. |
| 2026-04-01 | BATON 030–031: ite_analyzer_v3.py built + smoke tested (PASS). ICD-10 vec layers rebuilt. 5 bugs fixed (entry point imports, _not_in() col param, unicode, subcatAnalysis). QUESTION-DIST-001 flagged. export_aafp_ite_relationships.py run → 4 CSVs in readable_db_files/. word_doc_defaults.py committed to auto-memory. build_aafp_qa.py + build_aafp_qa_file1.py built → 2 AAFP Q&A docs delivered. M3: 5→9 Python. |
| 2026-03-29 | BATON 023–024: Blueprint labeling complete (1,629/1,629). blueprint_api_classifier.py (Sonnet, 70.4% Gold Standard accuracy) wrote 1,234 pseudo-labels for 2018-2023. blueprint_emergent_pass.py: 16 Acute→Emergent flips. Pre-2024 Emergent at 11.7% (vs 20% target) — accepted as known limitation (blueprint targets are 2024+ design spec). aafp_question_icd10.relevance normalized (74→3 values). unified_keyword_extractor.py: TF-IDF unigrams for all 1,629 ITE + 1,221 AAFP questions. aafp_vs_ite_comparison_dashboard.html built + patched. M2: 55→57 Python. |
| 2026-03-29 | BATON 021–022: AAFP full enrichment pipeline complete. aafp_merge_keywords.py: all_keywords 1221/1221. aafp_assign_body_system.py v2: 3-tier classifier, all 16 body systems 1221/1221, body_system_method audit trail. aafp_enrich_concept_tags.py: concept_tags + subcategory 1221/1221 (Haiku 4.5); aafp_question_icd10 ~4,065 rows (98.9% coverage). aafp_model_comparison.py: Haiku vs Sonnet 10-Q eval (Haiku selected, ~3× cost savings). M2: 51→55 Python. |
| 2026-03-28 | BATON 020: AAFP question reuse investigation complete. 38 shared AAFP-ITE vignettes found (verbatim identical stems, all dist 0.23–0.30). aafp_question_reuse_investigation.py built (M3/scripts/). 49 new articles inserted (ART-1938–ART-1986); aafp_qid_art_xref: 864 rows (643 unique Q linked, 52.7%). aafp_ref_match_v2.py (S2-S5 strategies, 12 new links). batch_insert_aafp_articles.py built. M2: 49→51 Python. M3: 4→5 Python. |
| 2026-03-27 | BATON 016: AAFP enrichment pipeline complete. aafp_brq_import.py v3: 5-table schema (aafp_questions, aafp_explanations, aafp_citations, aafp_citation_raw, aafp_qid_art_xref — 797 rows, 586Q linked). aafp_question_vec: 1221/1221 vectors. aafp_keyword_extractor.py: stem+explanation TF-IDF keywords 100%. aafp_context_propagator.py: body_system/source_type propagated + aafp_question_icd10 (1,876 rows). aafp_vector_explorer.py: AAFP-ITE KNN analysis + --save; ite_nearest_dist on all 1221 rows. Key finding: near-identical AAFP-ITE question pairs (dist<0.27); linked/unlinked dist gap = 0.25. M2 scripts: 45→49 Python. |
| 2026-03-27 | BATON 015: AAFP BRQ scraper built (v3 + resume/salvage). 1,221 Q scraped across 135 quizzes. aafp_questions table created + populated (1,221 rows, 51.1% article-linked). M1 reorganized: aafp_brq/ as proper warehouse source (scraper/ + staging/). aafp_brq_import.py added to M2/scripts/ (+1 → 45 Python). citation_gap_list_2024_2025.txt built (229 unmatched ITE Critique refs). FUSE oplock conflict documented. Option B+C confirmed. **Git: cd32816 — pushed to GitHub (github.com/mpsch01/project-overhaul, private). .gitignore strategy: code + docs on GitHub; binaries (*.db, *.pdf, extracted_json/) on local disk / Google Drive.** |
| 2026-03-27 | BATON 014: Full inventory sweep + M2 cleanup. Deleted: sectional_READMEs/, tagging_bundle/, re-org_guidance/, master_map.JSON, MASTER_MAP_V.1.html, TEMP_MIGRATION_MANIFEST.md, 3 one-time M2 scripts (backfill_merge_source_fields, build_xref_2018_2019, batch_retrieve_enrichment). Moved: backfill_keywords_2018_2019.py → M1/build/; preprocess_concept_tags.py → M1/maintain/; auto-memory-copies/ → root; re-org_guidance keep files → key_data_files/. M1 build sequence now self-contained (9 scripts). synthesis_library confirmed at 242 files (all legacy flat JSONs). qid_art_xref corrected to 2,470 (build_xref_2018_2019.py ran post-BATON 013). Designed: article_citation_trend table + extract_ite_critique_refs.py + update_citation_trends.py (not yet built). |
| 2026-03-26 | BATON 012: Nomenclature sweep complete — VC_pass/VC_fail naming. VC_fail 146 PDFs enriched. rematch_unmatched.py (8 new links). classify_null_refs.py added. rename_tier_labels_in_db.py added. Git: 609ef99, 10d8208. |
| 2026-03-25 | FLAG 33 closed — vec tables at 100%. Articles table fully standardized. TEMP migrations complete. |
| 2026-03-24 | 2018-2019 integration: 440 questions, 389 articles, 653 QRP. Module structure fully populated. All scripts de-hardcoded. |
| 2026-03-23 | _index.md rebuilt. 4-module structure created. BATON protocol v2.0. |