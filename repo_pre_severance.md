# repo_pre_severance.md
**Purpose:** Full script inventory and dependency map of `00_#PROJECT_OVERHAUL/` taken immediately after Sweep 1 (2026-04-03, BATON 034 session) and before Option B (flatten to `claude_knowledge/` root). Use this as ground truth for Option B planning.

**Snapshot date:** 2026-04-04 (BATON 034)
**Post-sweep state:** `archive_canonical/` → `_archive_/`; `apify-actors/` → `skills_abilities/`; 11 scripts fixed for the rename; legacy/dead scripts identified below.
**Path note:** All paths below are relative to `00_#PROJECT_OVERHAUL/`. After Option B (flatten), hop counts stay the SAME — only the `claude_knowledge/` prefix changes, not the internal relative distances.

---

## Path Convention Reference

| Location | SCRIPT_DIR hops to PROJECT_ROOT | Example |
|----------|---------------------------------|---------|
| M1 `scripts/build/` | 3 hops (`../../..`) | `SCRIPT_DIR.parent.parent.parent` |
| M1 `scripts/maintain/` | 3 hops (`../../..`) | `SCRIPT_DIR.parent.parent.parent` |
| M2 `scripts/` | 2 hops (`../..`) | `SCRIPT_DIR.parent.parent` |
| M3 `scripts/` | 2 hops (`../..`) | `SCRIPT_DIR.parent.parent` |
| `skills_abilities/agents/scripts/` | 3 hops (`../../..`) | `SCRIPT_DIR.parent.parent.parent` |
| JS (`__dirname` in `scripts/`) | 2 hops `path.resolve(__dirname, "../../")` | resolves to PROJECT_ROOT ✅ |

**DB path from any script:** `PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"`

---

## M1 — `01_module.1_warehouse/scripts/build/` (9 scripts)

One-time build sequence. Run in order. Assumes clean slate.

| Script | Step | What It Does | PROJECT_ROOT hops | Key Reads | Key Writes |
|--------|------|-------------|-------------------|-----------|------------|
| `build_clean_question_bank.py` | 1 | Excel → ite_questions_clean.json | 3 | `ABFM_ITE_Master_v2.xlsx` | `key_data_files/ite_questions_clean.json` |
| `rebuild_ite_db_v2.py` | 2 | Core DB from JSON (2020–2025) | 3 | `ite_questions_clean.json` | `ite_intelligence.db` (create) |
| `extract_ite_2018_2019.py` | 3 | Extract 2018-2019 from split PDFs | 3 | `/sessions/fervent-hopeful-thompson/...` (**DEAD PATH**) | staging JSON |
| `enrich_ite_questions.py` | 4 | Claude API enrichment for 2018-2019 | 3 | staging JSON | enriched JSON |
| `integrate_2018_2019.py` | 5 | Merge 2018-2019 into DB | 3 (**WRONG — uses 2**) | enriched JSON | `ite_intelligence.db` |
| `backfill_keywords_2018_2019.py` | 6 | Keyword backfill for 2018-2019 | 3 (**WRONG — uses 2, DEPRECATED**) | DB | DB |
| `validate_db_v2.py` | 7 | Post-build QC | 3 | DB | console |
| `compute_embeddings.py` | 8 | Vector embeddings (`--new-only` for incremental) | 3 | DB | DB (article_vec, question_vec, aafp_question_vec) |
| `validate_vector_search.py` | 9 | Post-embedding QC | 3 | DB | console |

**⚠ Irregularities:**
- `extract_ite_2018_2019.py` — references `/sessions/fervent-hopeful-thompson/` (dead session path). Already run; historical only.
- `integrate_2018_2019.py` — wrong hop count (uses 2, needs 3 for M1/build/). Already run; DB is current.
- `backfill_keywords_2018_2019.py` — wrong hop count + DEPRECATED (keyword pipeline superseded by E_v4). Already run.

---

## M1 — `01_module.1_warehouse/scripts/maintain/` (17 scripts)

Operational/recurring. Assume DB exists with data.

### PDF Acquisition & Management (6 scripts)

| Script | What It Does | PROJECT_ROOT hops | Key Reads | Key Writes |
|--------|-------------|-------------------|-----------|------------|
| `aafp_fill_gaps.py` | Scrapes AAFP top-20; downloads missing PDFs | 3 | AAFP website | `VC_fail/` or `VC_pass/` |
| `aafp_vc_batch_download.py` | Batch download for VC-cited articles | 3 | VC gate JSON | warehouse PDFs |
| `aafp_top20_downloader.py` | Top-20 article downloader (AAFP) | 3 | AAFP website | warehouse PDFs |
| `aafp_retry_playwright.py` | Browser-auth fallback for paywalled PDFs | 3 | URL list | warehouse PDFs |
| `aafp_retry_selenium.py` | Selenium fallback for paywalled PDFs | 3 | URL list | warehouse PDFs |
| `aafp_cleanup_filenames.py` | Fixes ALL-CAPS author names in PDF filenames | 3 | warehouse PDFs | warehouse PDFs (rename) |

### Codon & Crosswalk (3 scripts)

| Script | What It Does | PROJECT_ROOT hops | Key Reads | Key Writes |
|--------|-------------|-------------------|-----------|------------|
| `build_crosswalk_index.py` | Scans warehouse for codon filenames → crosswalk_index.json | 3 | warehouse PDFs | `00_database/crosswalk/crosswalk_index.json` |
| `build_match_staging.py` | Proposes ART-ID matches for unmatched PDFs | 3 (**⚠ pre-overhaul — dead warehouse paths**) | warehouse PDFs | staging JSON |
| `rename_to_codon.py` | Executes approved codon renames on warehouse PDFs | 4 (**⚠ pre-overhaul — 4-hop PROJ_ROOT, dead source paths**) | staging JSON | warehouse PDFs (rename) |

**⚠ Irregularities:**
- `build_match_staging.py` — pre-overhaul, references `clinical_guidelines/01_pdf_guideline_library/pdf_non-codon/` (folder doesn't exist). Archive candidate.
- `rename_to_codon.py` — pre-overhaul, 4 hops to PROJECT_ROOT (`SCRIPT_DIR.parent.parent.parent.parent`) reaching `claude_knowledge/` — wrong. Also references dead source paths. Archive candidate.

### Reference Tier Matching & Acquisition (2 scripts)

| Script | What It Does | PROJECT_ROOT hops | Key Reads | Key Writes |
|--------|-------------|-------------------|-----------|------------|
| `match_tiers_to_library.py` | Scans warehouse PDFs vs reference tier CSV; MATCHED/NOT_FOUND | 3 | `_archive_/04_reference_data/ABFM_ITE_ReferenceTiers_Expanded_v1369.csv`; warehouse PDFs | `_archive_/05_acquisition/match_summary.csv`, `matched_high.csv`, `not_found.csv`, `match_report.json` |
| `rebuild_acquisition_list.py` | Reads match_summary → confirmed present + ranked acquisition XLSX | 3 | `_archive_/05_acquisition/match_summary.csv`; tier CSV | `confirmed_present.csv`, `ABFM_ITE_ReferenceAcquisitionList_Core_Ranked.xlsx` |

### Intelligence Layers & DB Enrichment (4 scripts)

| Script | What It Does | PROJECT_ROOT hops | Key Reads | Key Writes |
|--------|-------------|-------------------|-----------|------------|
| `build_clinical_pathways.py` | Layer 3: builds/rebuilds clinical_pathways table | 3 | DB (articles, questions, blueprint) | DB (`clinical_pathways`: 4,020 rows) |
| `build_topic_trends.py` | Layer 4a: builds topic trend CSVs | 3 | DB | `00_database/readable_db_files/4a_*.csv` |
| `backfill_new_article_metadata.py` | Backfills enrichment for new articles by ART-ID range (`--art-id-min`) | 3 | DB; PDFs in VC_fail | DB (articles metadata, article_icd10) |
| `update_citation_trends.py` | Populates/refreshes article_citation_trend from qid_art_xref (pure SQL) | 3 | DB | DB (`article_citation_trend`: 1,740 rows) — **built, not yet run** |

### Utility Scripts (2 scripts)

| Script | What It Does | PROJECT_ROOT hops | Key Reads | Key Writes |
|--------|-------------|-------------------|-----------|------------|
| `audit_engine_type_changes.py` | Audits changes to engine_type field across DB | 3 | DB | console/log |
| `rename_tier_labels_in_db.py` | One-time rename of tier labels in DB | 3 | DB | DB |

### New (BATON 034) — PMC Acquisition (2 scripts)

| Script | What It Does | PROJECT_ROOT hops | Key Reads | Key Writes |
|--------|-------------|-------------------|-----------|------------|
| `download_aafp_acquisitions.py` | Downloads 49 AAFP acquisition PDFs (OA API + E-Fetch fallback) | 3 | DB (ART-1938–1986); PMC OA API | `VC_fail/` codon-named PDFs |
| `download_pmc_actor_batch.py` | One-off: 9 hardcoded actor-discovered PMC PDF URLs | 3 | hardcoded URL list | `VC_fail/` PDFs |

### Concept Tag Scripts (1 script)

| Script | What It Does | PROJECT_ROOT hops | Key Reads | Key Writes |
|--------|-------------|-------------------|-----------|------------|
| `preprocess_concept_tags.py` | Concept tags via Claude API (moved from M2, 2026-03-27) | 3 | DB | DB (articles.concept_tags) |

---

## M2 — `02_module.2_processor/scripts/` (66 Python + 6 JS)

All scripts: 2 hops to PROJECT_ROOT.

### Module F — VC Outline Pipeline (run order: 01→02b→03→04→07→08→09→build_v6)

| Script | What It Does | Key Reads | Key Writes |
|--------|-------------|-----------|------------|
| `01_build_crosswalk.py` | Builds session-article crosswalk from keyword library | DB; `session_keyword_library.json` | crosswalk JSON |
| `02b_generate_hy_inserts_v2.py` | Generates HY inserts (enriched article content) | DB; enriched JSONs | `session_hy_inserts_v7.json` (VC gate) |
| `03_inject_into_outline_v3.py` | Injects HY inserts into VC outline DOCX | outline DOCX; HY inserts JSON | enhanced outline DOCX |
| `04_inject_poll_questions.py` | Injects poll questions into outline | `poll_inserts.json`; outline DOCX | outline DOCX |
| `07_inject_supplements_v2.py` | Injects supplement content | supplement data; outline | outline DOCX |
| `08_build_supplement_doc.py` | Builds standalone supplement document | supplement data | supplement DOCX |
| `09_build_pearl_callouts.py` | Builds clinical pearl callout blocks | DB | pearl DOCX |
| `build_v6_resident.py` | Builds final resident-facing v6 outline document | outline + inserts | `_archive_/01_curriculum/` DOCX |
| `build_poll_inserts.py` | Builds poll insert JSON from source | source DOCX | `poll_inserts.json` |

### Keyword Library Pipeline (run order: A→B→C→D→E_v4→F→G)

| Script | What It Does | Key Reads | Key Writes |
|--------|-------------|-----------|------------|
| `A_build_outline_terms.py` | Extracts terms from VC outline | source DOCX | outline_terms JSON |
| `B_build_tfidf_keywords.py` | TF-IDF keyword extraction from transcripts | `aafp_transcripts/` | tfidf JSON |
| `C_build_vtt_time_weights.py` | VTT transcript time weights | VTT files | `vtt_time_weights.json` |
| `D_build_keyword_library.py` | Assembles unified keyword library | A+B+C outputs | `session_keyword_library.json` |
| `E_v4_question_driven.py` | Question-driven enrichment (primary enricher v4) | DB; keyword library | enriched JSONs (`extracted_json/`) |
| `F_extract_question_refs.py` | DOCX-based ref extractor for 2020-2025 (legacy — already run) | ITE critique DOCXs | ref pairs JSON |
| `G_backfill_references.py` | Backfills ref pairs into DB | ref pairs JSON | DB (`question_ref_pairs`) |

### Reference Data Hygiene

| Script | What It Does | Key Reads | Key Writes |
|--------|-------------|-----------|------------|
| `hygiene_audit.py` | Audits ref data for inconsistencies | DB; CSVs | audit report |
| `hygiene_fix.py` | Applies hygiene fixes to ref data | DB | DB |
| `sg_reweight_v3.py` | Reweights scoring for subjective guideline refs | DB | DB |
| `split_by_year.py` | Splits question bank by year | DB | year-split JSONs/CSVs |
| `validate_v4.py` | Validates v4 enrichment output | enriched JSONs | console |

### Extraction + Enrichment Pipeline

| Script | What It Does | Key Reads | Key Writes |
|--------|-------------|-----------|------------|
| `ite_intelligence_enricher.py` | **PRIMARY v4 enricher** — Strategy 0 (codon) first, DB lookup | warehouse PDFs; DB | enriched JSONs (`extracted_json/`) |
| `ite_intelligence_enricher_batch.py` | Batch wrapper for primary enricher | warehouse PDFs; DB | enriched JSONs |
| `batch_db_extract.py` | Batch DB-guided extraction | DB; PDFs | JSONs |
| `db_guided_extractor.py` | DB-guided single-article extractor | DB; PDF | JSON |
| `convert_pdfs_to_json.py` | Converts PDFs to raw JSON (pdfplumber) | warehouse PDFs | raw JSONs |
| `calibration.py` | Enricher calibration runs | sample PDFs | calibration outputs |
| `clear_and_reenrich.py` | Clears enrichment fields + re-runs | DB | DB; JSONs |
| `pre_scan.py` | Pre-enrichment scan for codon matches | warehouse PDFs; DB | prescan report |
| `reextract_gold_list.py` | Re-extracts gold standard article set | gold list; PDFs | JSONs |
| `rematch_unmatched.py` | Second-pass matching for unmatched PDFs | warehouse PDFs; DB | match report |
| `run_test_batch.py` | Test batch run on small sample | sample PDFs | test outputs |
| `classify_null_refs.py` | Classifies NULL ref entries in DB | DB | DB update |
| `classify_unmatched_citations.py` | Classifies unmatched citation strings | DB | DB update |

### Linked Refs Crosswalk Pipeline

| Script | What It Does | Key Reads | Key Writes |
|--------|-------------|-----------|------------|
| `build_crosswalk_v2.py` | Builds article-ref crosswalk v2 | DB; ref data | `_archive_/04_reference_data/` CSVs |
| `apply_overrides.py` | Applies manual crosswalk overrides | `crosswalk_overrides.json`; DB | DB |
| `crosswalk_overrides.json` | Config: manual override rules | — | — |

### ITE Question Pipeline (run order: 01→02→03→ite_tag_questions)

| Script | What It Does | Key Reads | Key Writes |
|--------|-------------|-----------|------------|
| `00_body_system_extractor.py` | Extracts body system from question text | `_archive_/...` CSVs | staging JSON |
| `01_ite_extractor.py` | Extracts ITE question data (generalizable, `--year` flag) | source DOCXs | staging JSON |
| `02_ite_categorizer.py` | Categorizes questions by body system | staging JSON | categorized JSON |
| `03_ite_merger.py` | Merges categorized questions into DB | categorized JSON | DB |
| `ite_tag_questions.py` | Tags questions with keywords | DB; keyword library | DB |
| `ite_build_from_text.py` | Builds question bank from raw text | raw text files | staging JSON |
| `ite_merge_csv.py` | Merges year-split CSVs | year CSVs | merged CSV |
| `ite_diff_banks.py` | Diffs two question bank versions | two DB snapshots | diff report |
| `ite_check_columns.py` | Column population QC for questions table | `_archive_/...` CSVs | QC report |
| `build_qbank_exam_version.py` | Builds exam-ready question bank export | DB | `_archive_/02_question_bank/` DOCX/CSV |

### AAFP BRQ Pipeline (run in order after import)

| Script | What It Does | Key Reads | Key Writes |
|--------|-------------|-----------|------------|
| `aafp_brq_import.py` | Imports 1,221 AAFP questions into 5-table schema | `aafp_brq/staging/aafp_brq_staging.json` | DB (aafp_questions, aafp_citations, aafp_citation_raw, aafp_qid_art_xref, aafp_explanations) |
| `aafp_keyword_extractor.py` | TF-IDF stem + explanation keywords; `--top N` | DB | DB (aafp_questions.stem_keywords, explanation_keywords) |
| `aafp_merge_keywords.py` | Merges stem+explanation keywords → all_keywords | DB | DB (aafp_questions.all_keywords) |
| `aafp_context_propagator.py` | body_system, source_type, ICD-10 from xref JOIN | DB | DB (aafp_questions) |
| `aafp_assign_body_system.py` | 3-tier classifier: propagated→neighbor→keyword_freq | DB | DB (aafp_questions.body_system + body_system_method) |
| `aafp_vector_explorer.py` | AAFP-ITE cross-corpus KNN; `--save` persists | DB (aafp_question_vec + question_vec) | DB (aafp_questions.ite_nearest_qid, ite_nearest_dist) |
| `aafp_enrich_concept_tags.py` | API enrichment: concept_tags, subcategory, ICD-10; `--mode linked\|unlinked\|all`; Haiku 4.5 | DB | DB (aafp_questions.concept_tags; aafp_question_icd10) |
| `aafp_model_comparison.py` | Haiku vs Sonnet 10-Q comparison; writes comparison JSON | DB | `aafp_comparison_results.json` |
| `aafp_ref_match_v2.py` | Second-pass citation matcher: S2 vol/page, S3 AFP title, S4 Cochrane, S5 guideline/society | DB | DB (aafp_qid_art_xref) |
| `batch_insert_aafp_articles.py` | AAFP acquisition inserter: CSV → ART-IDs + xref links | pubmed_acquisition_queue CSV; DB | DB (articles ART-1938–1986) |

### AAFP Supplementary Scripts

| Script | What It Does | Key Reads | Key Writes |
|--------|-------------|-----------|------------|
| `aafp_context_propagator.py` | (see above) | — | — |
| `apply_aafp_related_cap.py` | Caps `related` ICD-10 links per AAFP question | DB | DB (aafp_question_icd10) |
| `backfill_aafp_article_icd10.py` | Backfills article_icd10 for AAFP-linked articles | DB | DB (article_icd10 +282 rows) |
| `flatten_aafp_questions.py` | Flattens aafp_questions schema (merged explanation/answer into main table) | DB | DB |
| `write_blueprint_aafp_to_db.py` | Writes AAFP blueprint scores to DB | blueprint CSV/JSON | DB |
| `write_blueprint_to_db.py` | Writes ITE blueprint scores to DB | blueprint CSV/JSON | DB |

### Blueprint Classification Scripts

| Script | What It Does | Key Reads | Key Writes |
|--------|-------------|-----------|------------|
| `blueprint_api_classifier.py` | Claude API blueprint classification v1 | DB | DB (questions.blueprint) |
| `blueprint_api_classifier_v2.py` | Blueprint classification v2 (current; ABFM rubric) | DB | DB (questions.blueprint) |
| `blueprint_api_classifier_aafp.py` | Blueprint classification for AAFP BRQ | DB | DB (aafp_questions.blueprint) |
| `blueprint_emergent_pass.py` | Emergent/fill-in-gap blueprint assignment | DB | DB (remaining NULL blueprint rows) |
| `blueprint_pseudo_classifier.py` | Rule-based fallback classifier | DB | DB |

### Intelligence Layer Scripts

| Script | What It Does | Key Reads | Key Writes |
|--------|-------------|-----------|------------|
| `build_ite_question_icd10.py` | Builds ITE question → ICD-10 linkage | DB | DB (question_icd10: 5,284 rows) |
| `build_icd10_embeddings.py` | OpenAI embeddings for ICD-10 codes | DB (icd10_code_xref) | DB (icd10_vec: 2,219 rows); DB (article_icd10_vec, question_icd10_vec) |
| `build_pubmed_citation_icd10.py` | ICD-10 linkage via PubMed citation text | DB (pubmed_pmid_cache) | DB |
| `build_clinical_pathways_v2.py` | Clinical pathways v2 (M2 copy — canonical is M1/maintain) | DB | DB (clinical_pathways) |

### DOCX Builders (JS — 6 scripts)

| Script | What It Does | Path convention | Key Reads | Key Writes |
|--------|-------------|-----------------|-----------|------------|
| `synthesize.js` | Synthesizes enriched JSON into article DOCX | CLI args (no PROJECT_ROOT needed) | enriched JSON | article DOCX |
| `build_summary.js` | Builds summary DOCX from article JSON | CLI args | enriched JSON | summary DOCX → `03_right_click/` or `01_local_lite/` |
| `build_db_docx.js` | Builds DOCX directly from DB query | 2-hop `__dirname` ✅ | DB | DOCX |
| `build_exemplar_v2.js` | Builds exemplar DOCX from DB | 2-hop `__dirname` ✅ | DB | exemplar DOCX |
| `build_merged_docx.js` | Merges multiple DOCXs into one | CLI args | DOCX list | merged DOCX |
| `gen_linked_refs_v2.js` | Generates linked-refs reference document | 2-hop `__dirname` ✅ | DB; `_archive_/04_reference_data/` | linked refs DOCX |

**Note:** Node.js dependencies (`officegen`, `docx`, etc.) require `NODE_PATH` env var set to the node_modules location. No `package.json` or `node_modules/` at project root — dependency resolution is environment-dependent.

### Utility / Other Scripts

| Script | What It Does |
|--------|-------------|
| `unified_keyword_extractor.py` | Unified keyword extraction (replaces A–G pipeline for new articles) |
| `build_xref_2018_2019.py` | Builds xref table entries for 2018-2019 questions |
| `extract_ite_critique_refs.py` | **PLANNED** — local PDF-native critique ref extractor (pdfplumber, no API) |

---

## M2 — `02_module.2_processor/` (core/ + engines/ + utils/ packages)

Not directly runnable as scripts. Supporting packages for `main.py`.

| Package/File | Role |
|-------------|------|
| `main.py` | CLI entry point — routes extraction jobs through engines |
| `core/ingestion.py` | PDF intake and pre-processing |
| `core/routing.py` | Routes article to correct extraction engine |
| `core/screening.py` | Pre-screen for article type |
| `engines/base_engine.py` | Abstract base class for all engines |
| `engines/acute_engine.py` | Acute condition extraction logic |
| `engines/chronic_engine.py` | Chronic disease extraction logic |
| `engines/diagnostic_engine.py` | Diagnostic study extraction logic |
| `engines/preventive_engine.py` | Preventive medicine extraction logic |
| `engines/rct_engine.py` | RCT/trial extraction logic |
| `utils/logger.py` | Shared logging utility |
| `utils/preprocess.py` | Text cleaning and normalization |
| `utils/prompt_builder.py` | Claude API prompt assembly |
| `utils/qid_filename_parser.py` | QID + codon filename parsing |
| `utils/validator.py` | Output validation |

---

## M3 — `03_module.3_analyst/scripts/` (9 Python + 1 JS)

All scripts: 2 hops to PROJECT_ROOT.

| Script | What It Does | Key Reads | Key Writes |
|--------|-------------|-----------|------------|
| `ite_analyze_v2.py` | Entry point; routes to v3 by default; `--v2-only` flag | DB; score PDFs | calls downstream scripts |
| `ite_analyzer_v3.py` | **PRIMARY** — 9 analysis layers, dual bank, 3-tier Q cascade | DB; parsed score JSON | analysis JSON |
| `ite_analyzer_v2.py` | DEPRECATED — subcategory dropped, header added | DB | analysis JSON |
| `ite_parser.py` | Parses ITE score PDF into structured JSON | score PDF | `outputs/<resident>/score_analysis.json` |
| `ite_report_builder_v2.js` | Builds resident score analysis DOCX from JSON | `analysis_v2.json`; `ite_parser_config.json` | `reports/<resident>/` DOCX |
| `build_icd10_tags.py` | ICD-10 tagging for articles (Layer 1 build) | DB | DB (article_icd10) |
| `aafp_question_reuse_investigation.py` | AAFP-ITE shared vignette finder; 38 pairs found | DB (aafp_question_vec + question_vec) | `readable_db_files/aafp_ite_semantic_*.csv` |
| `export_aafp_ite_relationships.py` | 4-CSV AAFP↔ITE relationship export | DB | `readable_db_files/` CSVs |
| `word_doc_defaults.py` | **IMPORT TARGET** — St. Luke's style template; import in ALL python-docx scripts | — | — (library module) |
| `build_aafp_qa.py` | File 3: Q&A DOCX builder (595 AAFP citation-overlap questions) | DB | `reports/AAFP_BRQ_ITE_Overlap_QA_v2.docx` |
| `build_aafp_qa_file1.py` | File 1: Q&A DOCX builder (34 near-duplicate pairs + ITE companion) | DB | `reports/AAFP_BRQ_NearDuplicate_QA.docx` |
| `export_aafp_ite.py` | AAFP↔ITE export helper | DB | CSVs |
| `build_faculty_pptx.js` | Faculty PPTX builder | ❓ (path convention not verified this session) | PPTX |
| `abfm_reference_2025.json` | Reference config for 2025 analysis | — | — |
| `ite_parser_config.json` | Parser config (section labels, score mappings) | — | — |

---

## `skills_abilities/agents/scripts/` (5 scripts)

3 hops to PROJECT_ROOT.

| Script | What It Does | Status |
|--------|-------------|--------|
| `pdf_sourcer_agent.py` | **PRIMARY** — SDK agent for PDF sourcing from PubMed/PMC | Built + validated (BATON 033) |
| `run_sourcer.py` | Runner/entry point for pdf_sourcer_agent | Built |
| `match_afp.py` | AFP article matcher helper | Built |
| `check_env.py` | Environment check utility | Built |
| `import_asyncio.py` | Asyncio import test | Utility |

---

## `skills_abilities/apify-actors/citation_crawler/` (Apify Actor)

Moved from root `apify-actors/` on 2026-04-03.

| File | What It Does |
|------|-------------|
| `src/main.js` | PlaywrightCrawler (Chromium) — PMC PDF URL crawler; 10/10 PMC articles in 42s |
| `.actor/actor.json` | Actor metadata (v0.3, 2048MB memory) |
| `.actor/Dockerfile` | `apify/actor-node-playwright-chrome:20` base image |
| `package.json` | playwright + cheerio + crawlee deps |

**Deployed:** Actor ID `rh50nQRP7BupbUF64` (`mpsch1~citation-crawler`), build 0.3.1 ✅

---

## Consolidated Irregularities

### ⚠ Dead / Broken Scripts (do not rely on)

| Script | Issue |
|--------|-------|
| `M1/build/extract_ite_2018_2019.py` | References `/sessions/fervent-hopeful-thompson/` — dead session path. Already run; historical only. |
| `M1/build/integrate_2018_2019.py` | Wrong hop count (2 instead of 3 for M1/build/). Already run. |
| `M1/build/backfill_keywords_2018_2019.py` | Wrong hop count + DEPRECATED. Already run. |

### ⚠ Pre-Overhaul Legacy (archive candidates)

| Script | Issue |
|--------|-------|
| `M1/maintain/rename_to_codon.py` | 4-hop PROJECT_ROOT (wrong); references `clinical_guidelines/01_pdf_guideline_library/pdf_non-codon/` (doesn't exist). Non-functional. |
| `M1/maintain/build_match_staging.py` | References same dead warehouse paths as `rename_to_codon.py`. Non-functional. |

### ⚠ Unresolved / Needs Verification

| Item | Issue |
|------|-------|
| `M3/build_faculty_pptx.js` | Path convention not verified. Needs `__dirname` check. |
| JS DOCX builders (all 6) | Require `NODE_PATH` env var for node_modules resolution. No `package.json` at project root. Dependency on Windows environment's NODE_PATH. |

### ✅ Fixed This Session (2026-04-03, archive_canonical → _archive_)

All 11 of these were broken by the `archive_canonical/` → `_archive_/` rename and fixed with `replace_all`:

`00_body_system_extractor.py`, `01_ite_extractor.py`, `02_ite_categorizer.py`, `03_ite_merger.py`, `ite_tag_questions.py`, `ite_check_columns.py`, `build_crosswalk_v2.py`, `apply_overrides.py`, `gen_linked_refs_v2.js` (M2); `match_tiers_to_library.py`, `rebuild_acquisition_list.py` (M1/maintain)

---

## Script Counts (as of 2026-04-04, BATON 034)

| Location | Python | JS | Total |
|----------|--------|----|-------|
| M1 build/ | 9 | 0 | 9 |
| M1 maintain/ | 17 | 0 | 17 |
| M1 aafp_brq/scraper/ | 1 | 0 | 1 |
| M2 scripts/ | ~60 | 6 | ~66 |
| M2 core/ + engines/ + utils/ | 12 | 0 | 12 |
| M3 scripts/ | 11 | 2 | 13 |
| skills_abilities/agents/scripts/ | 5 | 0 | 5 |
| **Total** | **~115** | **8** | **~123** |

---

## Option B Impact Assessment

**After Option B (flatten `00_#PROJECT_OVERHAUL/` → `claude_knowledge/` root):**
- All hop counts stay the same — internal relative distances don't change.
- `PROJECT_ROOT` resolves to `claude_knowledge/` instead of `00_#PROJECT_OVERHAUL/`.
- Zero script edits required for path convention.
- The 3 dead/wrong-hop scripts (extract_ite_2018_2019, integrate_2018_2019, backfill_keywords) and 2 legacy scripts (rename_to_codon, build_match_staging) remain broken regardless — they were broken before Option B.
- JS NODE_PATH dependency stays unresolved — Windows environment issue, not path structure.

**Verdict:** Option B is path-safe. No scripts break as a result of the flatten.
