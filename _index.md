# _index.md — Ground Truth Directory Map
**Scope:** `00_#PROJECT_OVERHAUL/` only
**Last Updated:** 2026-03-28 (BATON 020)
**Status:** Current — updated post AAFP question reuse investigation (38 shared AAFP-ITE vignettes; 49 new articles ART-1938-1986 inserted)

> This file maps only the `00_#PROJECT_OVERHAUL` workspace. It does not map the broader `claude_knowledge` tree.
> Stale counts are worse than no index. Verify before trusting.

---

## Top-Level Structure

```
00_#PROJECT_OVERHAUL/
├── BATON_active_020_20260328_aafp_question_reuse_investigation_complete.md  ← active BATON
├── CLAUDE.md                              ← project memory + conventions
├── README.json                            ← machine-readable project metadata
├── README_PROJECT.md                      ← human-readable overview
├── _index.md                              ← this file
├── .gitattributes / .gitignore
│
├── 00_database/                           ← source of truth (DB + supporting data)
├── 01_module.1_warehouse/                 ← M1 PDF library (4 tiers, 404 PDFs) + AAFP BRQ warehouse + build/maintain scripts
├── 02_module.2_processor/                 ← M2 pipeline scripts + source inputs
├── 03_module.3_analyst/                   ← M3 score analysis + ICD-10 + pathways
├── 04_module.4_sandbox/                   ← M4 experiments (_DELETE_THESE_FROM_WINDOWS.txt — cleanup checklist)
│
├── archive_canonical/                     ← curated deliverables archive
├── auto-memory-copies/                    ← durable backup of all auto-memory files (moved from re-org_guidance 2026-03-27)
├── baton_archive/                         ← all archived BATONs (40+)
├── extracted_json/                        ← extracted article JSONs (middle-man layer; not git-tracked)
├── key_data_files/                        ← critical reference + architecture data files
└── skills_abilities/                      ← SDK docs, agent toolbox, skill files
```

**Removed this session (2026-03-27):** `sectional_READMEs/`, `tagging_bundle/`, `re-org_guidance/`, `master_map.JSON`, `MASTER_MAP_V.1.html`, `TEMP_MIGRATION_MANIFEST.md`

---

## Module Folders

### `00_database/` — Source of Truth
```
00_database/
├── db/
│   ├── ite_intelligence.db                ← PRODUCTION (1,936 articles, 1,629 questions)
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
│   └── sample_pathway_E11_type2dm.json
└── schemas/
    ├── clinical_synonym_map.json          ← 151 clinical term → ICD-10 translations
    ├── icd10_mcp_lookup.json              ← 1,406 MCP-verified ICD-10 codes
    └── ite-data-context-skill/
```

**DB Counts (verified live 2026-03-28, BATON 020):**
| Table | Rows | Notes |
|-------|------|-------|
| articles | 1,985 | +49 AAFP acquisition (ART-1938–ART-1986) |
| questions | 1,629 (2018–2025) | |
| question_ref_pairs | 2,722 | 222 NULL clean_ref |
| qid_art_xref | 2,470 | All 8 years (2018–2025) |
| article_icd10 | 3,855 | |
| clinical_pathways | 3,093 | |
| icd10_rollup | 614 | |
| icd10_code_xref | 1,006 | |
| article_vec | 1,936 | sqlite-vec — 100% coverage (49 new articles pending embeddings) |
| question_vec | 1,629 | sqlite-vec — 100% coverage |
| **aafp_questions** | **1,221** | 7 enrichment cols + ite_shared_vignette (designed, not yet added) |
| **aafp_explanations** | **1,221** | explanation_keywords populated |
| **aafp_citations** | **1,600** | one parsed citation per row |
| **aafp_citation_raw** | **1,600** | full text archive + coordinates |
| **aafp_qid_art_xref** | **864** | 643 unique questions linked (52.7%) |
| **aafp_question_vec** | **1,221** | sqlite-vec — 100% coverage |
| **aafp_question_icd10** | **1,915** | 589 questions covered |

**Planned tables (designed, not yet built):**
- `article_citation_trend` — companion to articles; tracks years_cited, consecutive_streak, is_watch_list per article

---

### `01_module.1_warehouse/` — PDF Library (404 total) + AAFP BRQ Data + Scripts
```
01_module.1_warehouse/
├── VC_fail/          ← 146 PDFs (VC gate failed — destined for local_lite)
├── 01_local_lite/    ← 117 PDFs (VC_fail + fully enriched)
├── VC_pass/          ← 94 PDFs (VC gate passed — destined for right_click)
├── 03_right_click/   ← 71 PDFs (VC_pass + fully enriched)
├── aafp_brq/                              ← AAFP Board Review Questions (scraper + staging)
│   ├── scraper/
│   │   ├── aafp_brq_scraper.py            ← v3 + resume/salvage logic (Windows-only: VM proxy blocks HTTPS)
│   │   ├── aafp_cookies.json              ← 38 auth cookies (refresh before each scrape run)
│   │   ├── aafp_quiz_map.json             ← 135 quiz sets (assessment_id → quiz_title)
│   │   └── aafp_explore_dump.txt          ← Q49733 reference (explore mode output)
│   └── staging/
│       └── aafp_brq_staging.json          ← 1,221 scraped questions (4MB); import script in M2
├── scripts/
│   ├── build/                             ← full DB build sequence (run in order)
│   │   ├── README.md
│   │   ├── build_clean_question_bank.py   ← Step 1: Excel → ite_questions_clean.json
│   │   ├── rebuild_ite_db_v2.py           ← Step 2: core DB from JSON (2020–2025)
│   │   ├── extract_ite_2018_2019.py       ← Step 3: extract 2018-2019 from split PDFs
│   │   ├── enrich_ite_questions.py        ← Step 4: Claude API enrichment for 2018-2019
│   │   ├── integrate_2018_2019.py         ← Step 5: merge 2018-2019 into DB
│   │   ├── backfill_keywords_2018_2019.py ← Step 6: keyword backfill for 2018-2019 (moved from M2 2026-03-27)
│   │   ├── validate_db_v2.py              ← Step 7: post-build QC
│   │   ├── compute_embeddings.py          ← Step 8: vector embeddings (--new-only for incremental)
│   │   └── validate_vector_search.py      ← Step 9: post-embedding QC
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
│       ├── build_match_staging.py
│       ├── build_topic_trends.py          ← Layer 4a
│       ├── match_tiers_to_library.py
│       ├── preprocess_concept_tags.py     ← concept_tags via API (moved from M2 2026-03-27)
│       ├── rebuild_acquisition_list.py
│       ├── rename_tier_labels_in_db.py
│       └── rename_to_codon.py
├── has_extraction_audit.txt
├── MOVE_STUCK_FILES.ps1
└── README.json
```
*M1 scripts: build/ = 9 scripts, maintain/ = 16 scripts*

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
└── scripts/                               ← 45 Python + 6 JS + 1 JSON + 4 Windows files
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
    │── AAFP BRQ PIPELINE (4 scripts — run in order after import)
    ├── aafp_brq_import.py                 ← v3: 5-table schema, citation splitting, vol/page dupe finder (864 xref rows)
    ├── aafp_keyword_extractor.py          ← TF-IDF stem+explanation keywords; --top N; 100% coverage
    ├── aafp_context_propagator.py         ← body_system, source_type, aafp_question_icd10 from xref JOIN
    ├── aafp_vector_explorer.py            ← AAFP-ITE cross-corpus KNN + --save; ite_nearest_qid+dist persisted
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
- `update_citation_trends.py` — populates/refreshes article_citation_trend table from qid_art_xref (pure SQL) [BATON 014]

**Ref extraction architecture (two paths):**
- **Path A — DOCX (2020-2025):** `F_extract_question_refs.py` — legacy, already processed
- **Path B — PDF/API (2018-2019):** `enrich_ite_questions.py` — API extracts refs inline
- **Path C — PDF local (future):** `extract_ite_critique_refs.py` — planned, zero API cost

---

### `03_module.3_analyst/` — Score Analysis + ICD-10 + Pathways
```
03_module.3_analyst/
├── scripts/
│   ├── ite_analyze_v2.py
│   ├── ite_analyzer_v2.py
│   ├── ite_parser.py
│   ├── ite_report_builder_v2.js
│   ├── build_icd10_tags.py
│   ├── aafp_question_reuse_investigation.py  ← AAFP-ITE shared vignette finder; --full, --csv flags; 38 pairs found (BATON 020)
│   ├── abfm_reference_2025.json
│   └── ite_parser_config.json
├── docs/
│   ├── ITE_SCORE_ANALYSIS_PIPELINE.md
│   └── README_ite_score_analysis.json
├── outputs/                               ← gitignored (derived)
│   ├── hopkins_2025/ (analysis_v2.json, score_analysis.json)
│   └── sarkar_2025/  (analysis_v2.json, score_analysis.json)
└── resident_data/                         ← gitignored (binary PHI-adjacent)
    ├── hopkins_2025_blueprint.pdf / bodysystem.pdf
    ├── sarkar_2025_blueprint.pdf / bodysystem.pdf
    └── scholl_2025_ENCRYPTED_22/23/24.pdf ← FLAG 30 (needs password)
```
*4 Python + 1 JS + 2 JSON configs*

### `04_module.4_sandbox/` — Experiments
```
04_module.4_sandbox/
└── _DELETE_THESE_FROM_WINDOWS.txt  ← cleanup checklist (sandbox AAFP files → moved to M1; delete originals from Windows)
```

---

## Supporting Folders

### `auto-memory-copies/` — Auto-Memory Backup (moved to root 2026-03-27)
Durable backup of all `.auto-memory/` files. Updated each housekeeping sweep.

### `archive_canonical/` — Curated Deliverables Archive
```
archive_canonical/
├── 01_curriculum/     ← enriched VC outline, supplement, linked refs DOCX
├── 02_question_bank/  ← formatted question bank exports (CSV, DOCX)
├── 03_analysis/       ← ITE analysis workbook, QC report
├── 04_reference_data/ ← reference tier CSVs, QRP pairs, crosswalk CSVs
├── 05_acquisition/    ← ranked acquisition list, BATON templates
└── README_canonical.json
```

**Note on DOCX library:** Pre-overhaul had 1,518 DOCXs in `clinical_guidelines/02_docx_guideline_library/`. Not migrated — metadata-only DOCXs not worth recovering. Right_click DOCXs (71) are regenerable from pipeline (`build_summary.js` + existing PDFs + DB).

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
- `ite-data-context-skill/` — domain skill for ITE DB queries
- `API_primer.md`

---

## Data Flow Summary
```
External Sources (ITE exams 2018-2025, AAFP course, guidelines, score reports)
        ↓
M1 Warehouse — store
  00_database/        (DB: 1,936 articles, 1,629 ITE questions, 1,221 AAFP BRQ questions)
  01_module.1_warehouse/  (PDF library: 404 PDFs, 4 tiers)
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

### questions table (1,629 rows)
| Column | Coverage |
|--------|----------|
| body_system_merged | 100% |
| stem_keywords | 100% |
| explanation_keywords | 100% |
| all_keywords | 100% |
| concept_tags | 100% |
| blueprint | ~33% (pre-existing debt) |

### articles table (1,936 rows)
| Column | Coverage |
|--------|----------|
| source_type | 100% |
| categories | 90.2% (189 unresolvable) |
| tier | 100% |
| engine_type | 100% |
| auto_assigned | 100% |

---

## Version Control

| Item | Value |
|------|-------|
| Remote | `https://github.com/mpsch01/project-overhaul` (private) |
| Branch | `main` |
| Latest commit | `cd32816` (2026-03-27) |
| .gitignore strategy | **Code + docs on GitHub. Binaries on local disk / Google Drive.** |

**What IS tracked:** all Python, JS, JSON, Markdown, `.md`, `.bat`, `.ps1`, `.reg`, `.txt` files. Basically: anything readable and diffable.

**What is NOT tracked (gitignored):** `*.db`, `*.pdf`, `extracted_json/`, `resident_data/`, `__pycache__/`, `*.pyc`, `*.log`, `node_modules/`, `outputs/` (derived). The DB and PDFs are source data — too large for GitHub; kept on local disk and mirrored to Google Drive.

**Why this split:** DB is ~50MB+ and changes with every session — wrong tool for binary tracking. PDFs are immutable source files. GitHub tracks intent and logic; Google Drive / local disk tracks the data.

---

## Housekeeping Log

| Date | Action |
|------|--------|
| 2026-03-28 | BATON 020: AAFP question reuse investigation complete. 38 shared AAFP-ITE vignettes found (verbatim identical stems, all dist 0.23–0.30). aafp_question_reuse_investigation.py built (M3/scripts/). 49 new articles inserted (ART-1938–ART-1986); aafp_qid_art_xref: 864 rows (643 unique Q linked, 52.7%). aafp_ref_match_v2.py (S2-S5 strategies, 12 new links). batch_insert_aafp_articles.py built. M2: 49→51 Python. M3: 4→5 Python. |
| 2026-03-27 | BATON 016: AAFP enrichment pipeline complete. aafp_brq_import.py v3: 5-table schema (aafp_questions, aafp_explanations, aafp_citations, aafp_citation_raw, aafp_qid_art_xref — 797 rows, 586Q linked). aafp_question_vec: 1221/1221 vectors. aafp_keyword_extractor.py: stem+explanation TF-IDF keywords 100%. aafp_context_propagator.py: body_system/source_type propagated + aafp_question_icd10 (1,876 rows). aafp_vector_explorer.py: AAFP-ITE KNN analysis + --save; ite_nearest_dist on all 1221 rows. Key finding: near-identical AAFP-ITE question pairs (dist<0.27); linked/unlinked dist gap = 0.25. M2 scripts: 45→49 Python. |
| 2026-03-27 | BATON 015: AAFP BRQ scraper built (v3 + resume/salvage). 1,221 Q scraped across 135 quizzes. aafp_questions table created + populated (1,221 rows, 51.1% article-linked). M1 reorganized: aafp_brq/ as proper warehouse source (scraper/ + staging/). aafp_brq_import.py added to M2/scripts/ (+1 → 45 Python). citation_gap_list_2024_2025.txt built (229 unmatched ITE Critique refs). FUSE oplock conflict documented. Option B+C confirmed. **Git: cd32816 — pushed to GitHub (github.com/mpsch01/project-overhaul, private). .gitignore strategy: code + docs on GitHub; binaries (*.db, *.pdf, extracted_json/) on local disk / Google Drive.** |
| 2026-03-27 | BATON 014: Full inventory sweep + M2 cleanup. Deleted: sectional_READMEs/, tagging_bundle/, re-org_guidance/, master_map.JSON, MASTER_MAP_V.1.html, TEMP_MIGRATION_MANIFEST.md, 3 one-time M2 scripts (backfill_merge_source_fields, build_xref_2018_2019, batch_retrieve_enrichment). Moved: backfill_keywords_2018_2019.py → M1/build/; preprocess_concept_tags.py → M1/maintain/; auto-memory-copies/ → root; re-org_guidance keep files → key_data_files/. M1 build sequence now self-contained (9 scripts). synthesis_library confirmed at 242 files (all legacy flat JSONs). qid_art_xref corrected to 2,470 (build_xref_2018_2019.py ran post-BATON 013). Designed: article_citation_trend table + extract_ite_critique_refs.py + update_citation_trends.py (not yet built). |
| 2026-03-26 | BATON 012: Nomenclature sweep complete — VC_pass/VC_fail naming. VC_fail 146 PDFs enriched. rematch_unmatched.py (8 new links). classify_null_refs.py added. rename_tier_labels_in_db.py added. Git: 609ef99, 10d8208. |
| 2026-03-25 | FLAG 33 closed — vec tables at 100%. Articles table fully standardized. TEMP migrations complete. |
| 2026-03-24 | 2018-2019 integration: 440 questions, 389 articles, 653 QRP. Module structure fully populated. All scripts de-hardcoded. |
| 2026-03-23 | _index.md rebuilt. 4-module structure created. BATON protocol v2.0. |
