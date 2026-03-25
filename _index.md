# _index.md — Ground Truth Directory Map
**Scope:** `00_#PROJECT_OVERHAUL/` only
**Last Updated:** 2026-03-24 (BATON 005 → 006)
**Status:** Current — updated post TEMP_05 migration (crosswalk pipeline, extracted_json/ root)

> This file maps only the `00_#PROJECT_OVERHAUL` workspace. It does not map the broader `claude_knowledge` tree.
> Stale counts are worse than no index. Verify before trusting.

---

## Top-Level Structure

```
00_#PROJECT_OVERHAUL/
├── BATON_active_006_20260324_temp05.md    ← active session handoff (BATON 006)
├── README.json                            ← STALE (March 17) — needs rebuild
├── README_PROJECT.md                      ← STALE (March 17) — needs rebuild
├── master_map.JSON                        ← STALE — reflects old 7-module structure
├── MASTER_MAP_V.1.html                    ← STALE — reflects old 7-module structure
├── _index.md                              ← this file
│
├── 00_database/                           ← source of truth (DB + supporting data)
├── 01_module.1_warehouse/                 ← M1 PDF library (4 tiers, 404 PDFs)
├── 02_module.2_processor/                 ← M2 pipeline scripts + 2018-2019 JSONs
├── 03_module.3_analyst/                   ← M3 analysis scripts
├── 04_module.4_sandbox/                   ← M4 experiments (empty placeholder)
│
├── archive_canonical/                     ← curated deliverables archive
├── baton_archive/                         ← all archived BATONs (28+)
├── key_data_files/                        ← critical reference data files
├── re-org_guidance/                       ← architecture docs, auto-memory, protocol
├── sectional_READMEs/                     ← legacy JSON/MD READMEs consolidated
├── extracted_json/                        ← 242 extracted JSONs (middle-man layer; not git-tracked)
├── skills_abilities/                      ← SDK docs, agent toolbox, skill files
├── tagging_bundle/                        ← working scripts + data for question tagging
└── (no loose scripts at root)
```

---

## Module Folders

### `00_database/` — Source of Truth
```
00_database/
├── db/
│   ├── ite_intelligence.db                ← PRODUCTION (1,936 articles, 1,629 questions)
│   ├── ite_intelligence.db-shm            ← shared memory (normal SQLite artifact)
│   ├── ite_intelligence.db-wal            ← write-ahead log
│   ├── ite_intelligence_pre2018_backup_20260324_001256.db  ← pre-integration rollback point
│   ├── ite_intelligence_pre_flag15_backup.db
│   └── ite_intelligence_v1_backup_20260310_095728.db
├── crosswalk/
│   ├── crosswalk_index.json
│   └── crosswalk_report.txt
├── logs/                                  ← 139+ pipeline run logs
│   ├── backfill_keywords_20260324_074416.json  ← keyword backfill (440 rows, 2018-2019)
│   ├── add_keywords_log.json
│   ├── batch_enricher_state.json
│   ├── [enricher_live_*, enricher_batch_*, db_guided_extraction_* logs]
│   └── archive/
├── readable_db_files/                     ← Intelligence 2.0 CSV/JSON exports
│   ├── 4a_body_system_subcategory_trends.csv
│   ├── 4a_body_system_trends.csv
│   ├── 4a_concept_tag_trends.csv
│   ├── batch_icd10_requests.jsonl / batch_icd10_results.jsonl
│   ├── layer1_icd10_*.csv (3 files)
│   ├── layer3_pathways_*.csv (4 files)
│   └── sample_pathway_E11_type2dm.json
└── schemas/
    ├── clinical_synonym_map.json          ← 151 clinical term → ICD-10 translations
    ├── icd10_mcp_lookup.json              ← 1,406 MCP-verified ICD-10 codes
    └── ite-data-context-skill/            ← skill files copy (canonical in skills_abilities/)
```

**DB Counts (as of 2026-03-24, post 2018-2019 integration):**
| Table | Rows |
|-------|------|
| articles | 1,936 |
| questions | 1,629 (2018–2025) |
| question_ref_pairs | 2,722 |
| qid_art_xref | 1,818 |
| article_icd10 | 3,855 |
| clinical_pathways | 4,528 |
| icd10_rollup | 736 |
| icd10_code_xref | 1,668 |

---

### `01_module.1_warehouse/` — PDF Library (404 total) + Scripts
```
01_module.1_warehouse/
├── 00_non-codon/     ← 147 PDFs (codon-named but not yet pipeline-processed)
├── 01_local_lite/    ← 117 PDFs (ITE-linked, not VC-cited)
├── 02_codon/         ← ~90 PDFs (codon-named, ITE-linked, VC-cited)
├── 03_right_click/   ← ~70 PDFs (VC-cited — $right_click$ tier, enriched)
├── scripts/
│   ├── build/                             ← structural/one-time (assume DB doesn't exist)
│   │   ├── README.md
│   │   ├── rebuild_ite_db_v2.py           ← primary DB constructor
│   │   ├── build_clean_question_bank.py   ← Excel → ite_questions_clean.json
│   │   ├── integrate_2018_2019.py         ← 2018-2019 integration (already run 2026-03-24)
│   │   ├── validate_db_v2.py              ← post-build QC
│   │   ├── compute_embeddings.py          ← vector embeddings (deferred — FLAG 33)
│   │   └── validate_vector_search.py      ← post-embedding QC (deferred — FLAG 33)
│   └── maintain/                          ← operational/recurring (assume DB exists)
│       ├── README.md
│       ├── aafp_cleanup_filenames.py      ← fix ALL-CAPS author names
│       ├── aafp_fill_gaps.py              ← download missing AAFP PDFs
│       ├── aafp_retry_playwright.py       ← paywalled PDF fallback
│       ├── aafp_retry_selenium.py         ← Selenium fallback
│       ├── aafp_top20_downloader.py       ← top-20 article downloader
│       ├── aafp_vc_batch_download.py      ← batch VC article downloader
│       ├── build_crosswalk_index.py       ← scans codons → crosswalk_index.json
│       ├── build_match_staging.py         ← proposes ART-ID matches for unmatched PDFs
│       ├── rename_to_codon.py             ← executes approved codon renames
│       ├── build_clinical_pathways.py     ← Layer 3: clinical_pathways table builder
│       ├── build_topic_trends.py          ← Layer 4a: trend CSVs
│       ├── match_tiers_to_library.py      ← scans warehouse PDFs vs ReferenceTiers CSV → match_summary.csv
│       └── rebuild_acquisition_list.py    ← match_summary → confirmed_present.csv + ranked XLSX
├── has_extraction_audit.txt
├── MOVE_STUCK_FILES.ps1
└── README.json
```
*M1 scripts migration complete (BATON 004+006 sessions). build/ = 6 scripts, maintain/ = 13 scripts.*
*M3 duplicates (`build_clinical_pathways.py`, `build_topic_trends.py`) pending manual delete by user — VM cannot rm mounted files.*

---

### `02_module.2_processor/` — Extraction + Enrichment Pipeline
```
02_module.2_processor/
├── main.py                                ← CLI entry point for extraction pipeline
├── requirements.txt                       ← anthropic>=0.25.0, pdfplumber>=0.10.0
├── guideline_extractor.json               ← pipeline config/manifest (v2.3)
├── PIPELINE_README.md                     ← pipeline documentation
├── INTEGRATION_PROMPT.md                  ← prompt reference doc
├── ite_2018_2019_enriched.json            ← 440 enriched 2018-2019 questions (integrated)
├── ite_2018_2019_extracted.json           ← pre-enrichment upstream artifact
├── core/                                  ← pipeline orchestration package
│   ├── ingestion.py, routing.py, screening.py
├── engines/                               ← 6 clinical extraction engines
│   ├── base_engine.py, acute_engine.py, chronic_engine.py
│   ├── diagnostic_engine.py, preventive_engine.py, rct_engine.py
├── utils/                                 ← pipeline utilities package
│   ├── logger.py, preprocess.py, prompt_builder.py
│   ├── qid_filename_parser.py, validator.py
├── prompts/candidates/                    ← 4 extraction prompt candidates
├── source/                                ← pipeline source inputs (not code)
│   ├── 00_EX_content_outline_w_q.docx    ← VC content outline (6.1MB, Mar 6) — input to A, 01, 03, 04, 07, 09
│   └── aafp_transcripts/                 ← 50 cleaned .txt files — input to B_build_tfidf_keywords.py
└── scripts/                               ← 41 standalone pipeline scripts (all paths dynamic)
    │
    │── MODULE F — VC OUTLINE PIPELINE (run order: 01→02b→03→04→07→08→09→build_v6)
    ├── 01_build_crosswalk.py              ← outline sessions → session_cluster_crosswalk.csv
    ├── 02b_generate_hy_inserts_v2.py      ← cluster crosswalk → session_hy_inserts_v2.json
    ├── 03_inject_into_outline_v3.py       ← HY inserts → enriched outline DOCX (v4 out)
    ├── 04_inject_poll_questions.py        ← poll inserts → enriched outline (v6 out)
    ├── 07_inject_supplements_v2.py        ← supplement questions → enriched outline (v7 out)
    ├── 08_build_supplement_doc.py         ← builds standalone supplement DOCX
    ├── 09_build_pearl_callouts.py         ← pearl callouts into outline
    ├── build_v6_resident.py               ← resident-facing v6 outline builder
    ├── build_poll_inserts.py              ← poll_inserts.json generator
    │
    │── KEYWORD LIBRARY PIPELINE (run order: A→B→C→D→E_v4→F→G)
    ├── A_build_outline_terms.py           ← outline DOCX → outline_terms.json
    ├── B_build_tfidf_keywords.py          ← aafp_transcripts/ → tfidf_keywords.json
    ├── C_build_vtt_time_weights.py        ← VTTs → vtt_time_weights.json (VTTs not migrated — pre-computed output preserved)
    ├── D_build_keyword_library.py         ← A+B+C → session_keyword_library.json
    ├── E_v4_question_driven.py            ← keyword library → session_hy_inserts_v6.json
    ├── F_extract_question_refs.py         ← ITE Q docs → question_ref_pairs.csv
    ├── G_backfill_references.py           ← pairs → backfills ABFM_ITE_Enriched.csv
    │
    │── REFERENCE DATA HYGIENE
    ├── hygiene_audit.py                   ← fuzzy-dedup ITE_Reference_Tiers.csv
    ├── hygiene_fix.py                     ← 6-pass fix on ITE_Reference_Tiers_Clean.csv
    ├── sg_reweight_v3.py                  ← study guide yield score reweighter
    ├── split_by_year.py                   ← splits master CSV by exam year
    ├── validate_v4.py                     ← validates session_hy_inserts_v7.json structure
    │
    │── EXTRACTION + ENRICHMENT PIPELINE
    ├── backfill_extraction_status.py      ← sets extraction_status in DB
    ├── backfill_keywords_2018_2019.py     ← keyword backfill for 2018-2019
    ├── batch_db_extract.py                ← batch API DB-guided extractor (50% cheaper)
    ├── calibration.py                     ← extraction QC + candidate prompt generator
    ├── clear_and_reenrich.py              ← strip ite_intelligence block + re-enrich
    ├── convert_pdfs_to_json.py            ← PDF → extracted JSON (pre-enrichment step)
    ├── db_guided_extractor.py             ← DB intelligence as extraction flashlight
    ├── ite_intelligence_enricher.py       ← primary v4 enricher (codon-first, 2-strategy)
    ├── ite_intelligence_enricher_batch.py ← batch API enricher (50% cheaper)
    ├── pre_scan.py                        ← pre-flight PDF scanner (INGEST/SKIP/REVIEW)
    ├── preprocess_concept_tags.py         ← Claude API concept_tags generator
    ├── reextract_gold_list.py             ← re-extraction runner for gold list PDFs
    ├── rematch_unmatched.py               ← fuzzy re-matcher for orphaned question_ref_pairs
    ├── run_test_batch.py                  ← pipeline test runner (vs gold baseline 0.957)
    │
    │── LINKED REFS CROSSWALK PIPELINE (run order: build_crosswalk_v2 → apply_overrides → gen_linked_refs_v2)
    ├── build_crosswalk_v2.py              ← session_hy_inserts_v7 + extracted JSONs → linked_refs_crosswalk_v2.csv
    ├── apply_overrides.py                 ← crosswalk_v2.csv + overrides JSON → crosswalk_final.csv
    ├── gen_linked_refs_v2.js              ← crosswalk_final.csv → ABFM_BoardPrep_LinkedRefs_v2.docx
    ├── crosswalk_overrides.json           ← gold exclusions, null overrides, manual pins (config)
    │
    │── DOCX BUILDERS (JS)
    ├── build_db_docx.js                   ← DB-powered DOCX builder
    ├── build_exemplar_v2.js               ← Intelligence 2.0 DOCX w/ ICD-10 + pathways
    ├── build_merged_docx.js               ← merged clinical narrative + DB intelligence DOCX
    ├── build_summary.js                   ← summary DOCX builder
    ├── build_qbank_exam_version.py        ← exam-version question bank DOCX builder
    ├── synthesize.js                      ← JSON → DOCX pre-processor
    │
    │── WINDOWS SYSTEM FILES (paths deferred — not dynamically resolvable)
    ├── batch_reprocess.ps1                ← batch reprocessing runner
    ├── extract_guideline.bat              ← Windows one-click orchestrator
    ├── install_context_menu.reg           ← Windows right-click setup
    └── uninstall_context_menu.reg         ← Windows right-click removal
```
*45 Python + JS scripts + 1 config JSON. All Python/JS paths dynamic (BATON 005+006). .bat/.ps1/.reg paths deferred. Files with `# TODO: not yet migrated` in BATCH_DIRS point to `extracted_json/` subdirs — update annotation when JSONs are sorted into batch folders.*

---

### `03_module.3_analyst/` — Analysis Scripts (5 scripts + 2 pending deletion)
```
03_module.3_analyst/
└── scripts/
    ├── build_icd10_tags.py                ← Layer 1: article_icd10 table builder
    ├── ite_analyze_v2.py
    ├── ite_analyzer_v2.py
    ├── ite_parser.py
    ├── ite_report_builder_v2.js
    ├── build_clinical_pathways.py         ← PENDING DELETE (canonical now in M1/maintain/)
    └── build_topic_trends.py              ← PENDING DELETE (canonical now in M1/maintain/)
```
*Two duplicates pending manual delete by user (VM cannot rm mounted files).*

### `04_module.4_sandbox/` — Empty placeholder

---

## Supporting Folders

### `archive_canonical/` — Curated Deliverables Archive
```
archive_canonical/
├── 01_curriculum/     ← enriched VC outline, board prep supplement, linked refs DOCX
├── 02_question_bank/  ← formatted question bank exports (CSV, DOCX vQA + vExam)
├── 03_analysis/       ← ITE analysis workbook, QC report, reference analysis
├── 04_reference_data/ ← reference tier CSVs, QRP pairs, crosswalk CSVs (v2 + final)
├── 05_acquisition/    ← ranked acquisition list, BATON templates, chrome prompt
└── README_canonical.json
```

### `extracted_json/` — Extracted Article JSONs (middle-man layer; not git-tracked)
```
extracted_json/
├── [242 article JSONs — flat, not yet sorted into batch subdirs]
├── raw_txt/           ← 21 raw text files (pre-JSON)
├── manifest.json      ← extraction manifest
├── pre_calibration_archive/    ← placeholder (empty — for gold list 21 JSONs)
├── afp_peds_uspstf_batch/      ← placeholder (empty)
├── id_renal_gi_hep_batch/      ← placeholder (empty)
├── jacc_pulm_batch/            ← placeholder (empty)
└── neuro_tox_rheum_psych_batch/ ← placeholder (empty)
```
*Flat layout is temporary. build_crosswalk_v2.py expects JSONs in the named subdirs (BATCH_DIRS). The TODO annotations in that script mark when sorting is needed. Sorting the 242 flat JSONs into batch subdirs is a deferred task.*

### `baton_archive/` — Session Handoff History
- 28+ archived BATONs (pre-001 naming debt — batch rename pending)
- `templates+guides/` — BATON protocol v2.0, JSON spec, pipeline templates

### `key_data_files/` — Critical Reference Data
```
key_data_files/
├── 00_DB_qbank_master_20-25.csv
├── ABFM_ITE_Master_v2.xlsx
├── ABFM_ITE_QuestionRefPairs_2020-2025.csv
├── clinical_synonym_map.json
├── session_hy_inserts_v7.json             ← VC GATE — 352 citations (production)
├── session_keyword_library.json           ← final output of keyword pipeline (A→D)
├── poll_inserts.json                      ← input to build_v6_resident.py
├── vtt_time_weights.json                  ← pre-computed step C output (VTTs not migrated)
├── README_AAFP_course_integration.json    ← AAFP course integration context doc
└── data_exams/
    ├── ITE_2020_raw.csv  ├── ITE_2021_raw.csv  ├── ITE_2022_raw.csv
    ├── ITE_2023_raw.csv  ├── ITE_2024_raw.csv  └── ITE_2025_raw.csv
```

### `re-org_guidance/` — Architecture & Memory
```
re-org_guidance/
├── auto-memory-copies/                    ← durable backup of all auto-memory files
│   ├── MEMORY.md
│   ├── project_architecture_tiered_system.md
│   ├── project_current_db_state.md
│   ├── project_new_architecture.md
│   ├── project_overhaul_state.md
│   ├── rebuild_structuring_guidelines.md
│   ├── reference_baton_protocol.md        ← v2.0
│   ├── reference_sdk_docs.md
│   ├── reference_vc_gate.md
│   └── user_profile.md
├── FILE_NAMING_SPEC.md
├── ITE_Intelligence_2.0_Architecture.md
├── project_overhaul_inventory.md
├── RENAMING_PROPOSAL.md
└── script_library.csv
```

### `sectional_READMEs/` — Legacy READMEs (11 files)
Consolidated JSON/MD READMEs from old module structure. Reference only — not maintained.

### `skills_abilities/` — SDK Docs + Agent Toolbox + Skills
```
skills_abilities/
├── 01–17 SDK reference text files + notebooks (17+ files)
├── agents/
│   ├── scripts/              ← 7 files: pdf_sourcer_agent.py + 6 helpers
│   └── docs+logs/            ← cookies, manifests, run logs
├── ite-data-context-skill/   ← domain skill for ITE DB queries
│   ├── SKILL.md
│   ├── ite_data_context_skill.md
│   └── references/           ← entities.md, gotchas.md, metrics.md, pipeline.md
│       └── tables/           ← per-table reference docs
├── API_primer.md
└── [notebooks: crop_tool, prompting_aesthetics, session_memory, etc.]
```

### `tagging_bundle/` — Question Tagging Scripts & Reference Data
Working folder containing scripts and reference files assembled for the keyword/concept-tag generation task. Not part of the active pipeline — reference + archival.
```
tagging_bundle/
├── add_keywords.py               ← keyword population (CSV-source, 2020-2025)
├── backfill_keywords_2018_2019.py← (copy — production script now in M2/scripts/)
├── B_build_tfidf_keywords.py     ← TF-IDF on AAFP transcripts (AAFP pipeline, not ITE)
├── build_glossary.py             ← gold tier reference glossary builder
├── classify_body_system.py       ← TF-IDF + LinearSVC body system classifier
├── clinical_synonym_map.json     ← 151-entry synonym map
├── D_build_keyword_library.py    ← AAFP keyword library builder (not ITE)
├── extraction_schema.json        ← JSON schema for extracted guideline documents
├── fingerprint_archetypes.json   ← cluster archetype definitions (9 clusters)
├── fingerprint_cluster_summary.csv
├── fingerprint_clustering.py     ← K-means clustering of exam questions
├── generate_subcategory.py       ← rule-based subcategory classifier (11 categories)
├── icd10_mcp_lookup.json
├── integrate_2018_2019.py        ← (copy — production script now in M2/scripts/)
├── ITE_ExamFingerprint_Clustered.xlsx
├── ITE_Fingerprint_cluster_summary.json
├── ite_fingerprint_cluster.py    ← fingerprint + cluster pipeline
├── preprocess_keywords_v2.py     ← (predecessor to production preprocess_concept_tags.py)
├── subcategory_labels.csv
├── tag_bank.py                   ← rule-based tagger (requires tagger_rules module)
├── tag_questions.py              ← per-question Claude API tagger (CSV-based)
├── ABFM_ITE_AI_Tagged.csv        ← output of tag_questions.py
└── unified_schema.json           ← unified extraction + governance JSON schema
```

---

## Data Flow Summary
```
External Sources (ITE exams 2018-2025, AAFP course, guidelines, score reports)
        ↓
M1 Warehouse — store
  00_database/        (DB: 1,936 articles, 1,629 questions)
  01_module.1_warehouse/  (PDF library: 404 PDFs, 4 tiers)
  key_data_files/     (VC gate: 352 citations, exam CSVs, question bank)
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
  04_module.4_sandbox/  (agents, new ideas, graduation path to M1-M3)
```

---

## Schema-Level Column Coverage (as of 2026-03-24)

### questions table (1,629 rows)
| Column | Coverage | Notes |
|--------|----------|-------|
| body_system_merged | 100% | Backfilled this session for 2018-2019 |
| stem_keywords | 100% | Backfilled this session for 2018-2019 |
| explanation_keywords | 100% | Backfilled this session for 2018-2019 |
| all_keywords | 100% | Backfilled this session for 2018-2019 |
| concept_tags | ~73% → 100% | In progress — 440 new records via preprocess_concept_tags.py |
| blueprint | ~33% | Pre-existing debt, cross-year gap |

### articles table (1,936 rows)
| Column | Coverage | Notes |
|--------|----------|-------|
| source_type | ~72% | New 389 articles: 0% — requires classification pipeline |
| categories | ~56% | New 389 articles: 0% |
| tier | ~72% | New 389 articles: 0% — requires VC gate check |
| auto_assigned | ~70% | Populated during tier assignment |
| engine_type | ~71% | Populated during PDF extraction |

---

## Housekeeping Log

| Date | Action |
|------|--------|
| 2026-03-24 | `_index.md` updated to BATON 005 → 006. TEMP_05 fully migrated: `build_crosswalk_v2.py` + `apply_overrides.py` + `crosswalk_overrides.json` → M2/scripts/. `gen_linked_refs_v2.js` → M2/scripts/ (de-hardcoded). `match_tiers_to_library.py` + `rebuild_acquisition_list.py` → M1/maintain/. `extracted_json/` root created (242 flat JSONs + 5 batch subdirs as placeholders). `linked_refs_crosswalk_final.csv` → archive_canonical/04_reference_data/. gen_gold_tier_v2.js excluded (does not migrate). M1/maintain count: 11 → 13. M2/scripts count: 41 → 45 (+1 config JSON). |
| 2026-03-24 | `_index.md` updated to BATON 004 → 005. TEMP_04 fully migrated: Module F (9 scripts) + keyword library (7 scripts A-G) + 5 hygiene/utility scripts → M2/scripts/. M2/source/ layer created with content outline DOCX + 50 AAFP transcripts. 4 key data files added to key_data_files/. All 30 Python/JS scripts de-hardcoded (commit `ed85b06`). M2 script count: 10 → 41. |
| 2026-03-24 | `_index.md` updated to BATON 003 → 004. M1 `scripts/build/` and `scripts/maintain/` created and populated (11 scripts total). 7 scripts relocated from M2/scripts to M1/maintain or M1/build. `aafp_vc_batch_download.py` relocated from agents/scripts to M1/maintain. M2/scripts count: 17 → 10. M3 script duplication flagged. |
| 2026-03-24 | `_index.md` updated to BATON 002. DB counts updated: 1,936 articles, 1,629 questions (added 2018-2019 integration). New scripts documented: `backfill_keywords_2018_2019.py`, `preprocess_concept_tags.py`. `tagging_bundle/` section added. Schema coverage table added. |
| 2026-03-24 | 2018-2019 integration complete: 440 questions, 389 new articles (ART-1549 → ART-1937), 653 question_ref_pairs, 762 article_icd10. Backup: `ite_intelligence_pre2018_backup_20260324_001256.db`. |
| 2026-03-24 | `body_system_merged` backfilled (440 rows). `stem_keywords`, `explanation_keywords`, `all_keywords` backfilled (440 rows, $0). `concept_tags` generation in progress via API (~$0.70, 440 records). |
| 2026-03-23 | `_index.md` rebuilt from scratch — scope narrowed to `00_#PROJECT_OVERHAUL` only. Old index (March 17, full claude_knowledge tree) superseded. |
| 2026-03-23 | 4-module folder structure fully populated. `01_database` renamed `00_database`. BATON protocol upgraded to v2.0. Sequential numbering introduced (starting BATON 001). |
| 2026-03-21 | PDF library migrated. DB expanded to 1,547 articles. Agent SDK integrated. PDF sourcer built. |
