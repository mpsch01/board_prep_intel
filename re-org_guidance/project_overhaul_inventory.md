# PROJECT INVENTORY — Complete Building Block Catalog
 
**Purpose:** Total examination of every component in the current system. For each item: what it is, what it does, whether it's needed for the rebuild, and which new module it maps to.
 
**Modules in the new architecture:**
- **M1 — Warehouse** (store)
- **M2 — Processor** (transform)
- **M3 — Analyst** (analyze)
- **M4 — Sandbox** (experiment)
- **EXT — External Sources** (not ours to control)
- **ARCHIVE** — safe to cold-store or delete
- **INFRA** — project infrastructure (docs, configs, housekeeping)
 
---
 
## SECTION A: SOURCE DATA (The Irreplaceable Stuff)
 
These are the items that cannot be regenerated. If you lose them, you lose real data.
 
| Item | Current Location | Size | What It Is | Verdict | New Module |
|------|-----------------|------|-----------|---------|------------|
| **ite_intelligence.db** | `02_ite_intelligence/db/` | ~25MB | SQLite DB: 1,547 articles, 1,189 questions, 2,069+ QRP, ICD-10 tables, vector embeddings, concept_tags | **KEEP — Source of Truth** | M1 |
| **ite_questions_clean.json** | `03_ite_exam/03_database/` | ~2MB | 1,189 structured questions (2020–2025) | **KEEP** | M1 |
| **ite_2018_2019_extracted.json** | `03_ite_exam/02_working/` | ~1MB | 440 questions extracted from 2018-2019 PDFs | **KEEP** | M1 |
| **ite_2018_2019_enriched.json** | `03_ite_exam/02_working/` (on local machine) | ~1.5MB | 440 questions with body_system, subcategory, ICD-10 | **KEEP — needs integration** | M1 |
| **ABFM_ITE_Master_v2.xlsx** | `03_ite_exam/03_database/` | ~1MB | Human-curated Excel master: all ITE questions with metadata | **KEEP — original source** | M1 |
| **session_hy_inserts_v7.json** | `04_aafp_integration/02_working/` | ~200KB | The VC gate: 48 sessions, 229 QIDs, 352 unique citations | **KEEP — Critical** | M1 |
| **PDF Library (codon)** | `clinical_guidelines/01_pdf_guideline_library/02_codon/` | 70 files | Codon-renamed PDFs with ART-IDs | **KEEP** | M1 |
| **PDF Library (right_click)** | `clinical_guidelines/01_pdf_guideline_library/03_right_click/` | 71 files | VC-tier PDFs ready for extraction | **KEEP** | M1 |
| **PDF Library (local_lite)** | `clinical_guidelines/01_pdf_guideline_library/01_local_lite/` | 117 files | Non-VC tier PDFs | **KEEP** | M1 |
| **PDF Library (non-codon)** | `clinical_guidelines/01_pdf_guideline_library/00_non-codon/` | 174 files (146 + 28 staged) | Unmatched/staging PDFs | **KEEP** | M1 |
| **Enriched JSONs** | `clinical_guidelines/03_enriched_JSON/` | 217 JSON + 217 TXT | Structured article extractions | **KEEP — derived but expensive to regenerate** | M1 |
| **DOCX Library** | `clinical_guidelines/02_docx_guideline_library/` | 1,518 files | Clinical summary documents | **KEEP — terminal deliverables** | M1 |
| **clinical_synonym_map.json** | `02_ite_intelligence/schemas/` | ~15KB | 151 clinical term → ICD-10 translations | **KEEP** | M1 |
| **icd10_mcp_lookup.json** | `02_ite_intelligence/schemas/` | ~100KB | 1,406 MCP-verified ICD-10 codes | **KEEP** | M1 |
| **crosswalk_index.json** | `02_ite_intelligence/` | ~50KB | Maps codon filenames → ART-IDs → DB metadata | **KEEP** | M1 |
| **Raw ITE Exam PDFs** | `03_ite_exam/01_source/` | ~50MB | Original ABFM exam PDFs (2018–2025) | **KEEP — External source** | EXT |
| **ABFM Score Report PDFs** | `08_ite_score_analysis/raw_pdfs/` | 3.1MB | 7 PDFs (Hopkins, Sarkar, Scholl encrypted) | **KEEP** | EXT |
| **ABFM Reference Handbooks** | `08_ite_score_analysis/raw_pdfs/reference/` | 3.7MB | 2024 + 2025 ITE Score Result Handbooks | **KEEP** | EXT |
| **Alt Refs (clinical)** | `clinical_guidelines/alt_refs/` | 78 files | Inpatient refs, ACLS/PALS, vaccine sheets | **KEEP** | M1 |
| **AAFP Video Transcripts** | `04_aafp_integration/` | 102 files (VTT + TXT) | 51 session transcripts + companion PDFs | **KEEP — External source** | EXT |
| **ITE Reference Tiers** | `05_ite_refs/03_database/` | ~500KB | ITE_Reference_Tiers_Final.csv, Expanded.csv | **KEEP** | M1 |
| **Score Analysis Outputs** | `08_ite_score_analysis/reports/` | ~700KB | Hopkins + Sarkar analysis JSONs and DOCXs | **KEEP** | M3 |
 
---
 
## SECTION B: PRODUCTION SCRIPTS (The Active Pipeline)
 
Scripts currently in use or needed for the rebuild.
 
### B1: Module ⓪ → M1 (Warehouse Building)
 
| Script | Location | What It Does | Verdict | New Module |
|--------|----------|-------------|---------|------------|
| `build_clean_question_bank.py` | `03_ite_exam/03_database/` | Parses Excel → clean JSON | **KEEP** | M1 |
| `rebuild_ite_db_v2.py` | `02_ite_intelligence/scripts/` | Builds all core DB tables from JSON | **KEEP** | M1 |
| `preprocess_keywords_v2.py` | `02_ite_intelligence/scripts/` | Claude API → concept_tags (25/call) | **KEEP** | M1 |
| `validate_db_v2.py` | `02_ite_intelligence/scripts/` | QC checkpoint for DB | **KEEP** | M1 |
| `build_icd10_tags.py` | `02_ite_intelligence/scripts/` | Layer 1: ICD-10 crosswalk (zero API cost) | **KEEP** | M1 |
| `compute_embeddings.py` | `02_ite_intelligence/scripts/` | Layer 2: Vector embeddings (OpenAI API) | **KEEP** | M1 |
| `validate_vector_search.py` | `02_ite_intelligence/scripts/` | Validates vector search tables | **KEEP** | M1 |
| `build_crosswalk_index.py` | `02_ite_intelligence/scripts/` | Scans codons → builds crosswalk JSON | **KEEP** | M1 |
| `build_clinical_pathways.py` | `02_ite_intelligence/scripts/` | Layer 3: Clinical pathway mapping | **KEEP** | M1 |
| `build_topic_trends.py` | `02_ite_intelligence/scripts/` | Layer 4: Topic trend analysis | **KEEP** | M1 |
| `build_match_staging.py` | `02_ite_intelligence/scripts/` | Proposes ART-ID matches for unmatched PDFs | **KEEP** | M1 |
| `rename_to_codon.py` | `02_ite_intelligence/scripts/` | Executes approved codon renames | **KEEP — overhaul pending** | M1 |
| `extract_ite_2018_2019.py` | `03_ite_exam/05_scripts/` | Extracts 2018-2019 from split PDFs | **KEEP** | M1 |
| `enrich_ite_questions.py` | `03_ite_exam/05_scripts/` | Claude API enrichment (body_system + ICD-10) | **KEEP** | M1 |
| `integrate_2018_2019.py` | `03_ite_exam/05_scripts/` | Integration pipeline for 2018-2019 | **KEEP — not yet run** | M1 |
 
### B2: Module Ⓕ → INFRA/M1 (VC Outline Generation)
 
| Script | Location | What It Does | Verdict | New Module |
|--------|----------|-------------|---------|------------|
| `01_build_crosswalk.py` | `04_aafp_integration/05_scripts/` | Session → ITE cluster mapping | **KEEP** | M1 |
| `02b_generate_hy_inserts_v2.py` | `04_aafp_integration/05_scripts/` | Generates the VC gate JSON | **KEEP — Critical** | M1 |
| `03_inject_into_outline_v3.py` | `04_aafp_integration/05_scripts/` | Injects ITE callouts into outline | **KEEP** | M2 |
| `04_inject_poll_questions.py` | `04_aafp_integration/05_scripts/` | Injects poll questions | **KEEP** | M2 |
| `07_inject_supplements_v2.py` | `04_aafp_integration/05_scripts/` | Injects supplements | **KEEP** | M2 |
| `08_build_supplement_doc.py` | `04_aafp_integration/05_scripts/` | Builds supplement question booklet | **KEEP** | M2 |
| `09_build_pearl_callouts.py` | `04_aafp_integration/05_scripts/` | Injects pearl callouts | **KEEP** | M2 |
| `A-F pipeline scripts` | `04_aafp_integration/05_scripts/` | VTT processing, TF-IDF, keyword lib | **KEEP — historical but may re-run** | M2 |
 
### B3: Module Ⓐ → M1 (PDF Acquisition)
 
| Script | Location | What It Does | Verdict | New Module |
|--------|----------|-------------|---------|------------|
| `aafp_fill_gaps.py` | `clinical_guidelines/05_scripts/` | Scrapes top-20, downloads missing | **KEEP** | M1 |
| `aafp_retry_playwright.py` | `clinical_guidelines/05_scripts/` | Browser-auth fallback for paywalled PDFs | **KEEP** | M1 |
| `aafp_cleanup_filenames.py` | `clinical_guidelines/05_scripts/` | Fixes ALL-CAPS author names | **KEEP** | M1 |
| `aafp_vc_batch_download.py` | `clinical_guidelines/05_scripts/` | Batch download for VC articles | **KEEP** | M1 |
| `aafp_top20_downloader.py` | `clinical_guidelines/05_scripts/` | Top 20 article downloader | **KEEP** | M1 |
| `_download_log.json` | `clinical_guidelines/05_scripts/` | 174-entry download audit trail | **KEEP** | M1 |
 
### B4: Module Ⓒ → M2 (Extraction/Enrichment/DOCX)
 
| Script | Location | What It Does | Verdict | New Module |
|--------|----------|-------------|---------|------------|
| `main.py` | `01_guideline_extractor/` | Single-file extraction CLI | **KEEP** | M2 |
| `core/ingestion.py` | `01_guideline_extractor/core/` | Pipeline orchestrator | **KEEP** | M2 |
| `core/screening.py` | `01_guideline_extractor/core/` | Document classification | **KEEP** | M2 |
| `core/routing.py` | `01_guideline_extractor/core/` | Engine routing | **KEEP** | M2 |
| `engines/*.py` (5 files) | `01_guideline_extractor/engines/` | 5 extraction engines | **KEEP** | M2 |
| `extract_guideline.bat` | `01_guideline_extractor/oneclick/` | Windows right-click orchestrator | **KEEP** | M2 |
| `synthesize.js` | `01_guideline_extractor/oneclick/` | Claude API clinical narrative | **KEEP** | M2 |
| `build_summary.js` | `01_guideline_extractor/oneclick/` | JSON → DOCX renderer | **KEEP** | M2 |
| `ite_intelligence_enricher.py` | `02_ite_intelligence/scripts/` | Adds ITE intelligence block to JSON | **KEEP** | M2 |
| `batch_db_extract.py` | `02_ite_intelligence/scripts/` | Batch API extraction (50% savings) | **KEEP** | M2 |
| `db_guided_extractor.py` | `02_ite_intelligence/scripts/` | "Flashlight" DB-guided extraction | **KEEP** | M2 |
| `build_merged_docx.js` | `02_ite_intelligence/scripts/docx_build/` | Merged clinical+DB DOCX | **KEEP** | M2 |
| `build_db_docx.js` | `02_ite_intelligence/scripts/docx_build/` | DB-only DOCX fallback | **KEEP** | M2 |
| `extraction_schema.json` | `01_guideline_extractor/schemas/` | Output format spec | **KEEP** | M2 |
| `unified_schema.json` | `01_guideline_extractor/schemas/` | Unified multi-domain schema | **KEEP** | M2 |
 
### B5: Module Ⓔ → M3 (Score Analysis)
 
| Script | Location | What It Does | Verdict | New Module |
|--------|----------|-------------|---------|------------|
| `ite_analyze_v2.py` | `08_ite_score_analysis/pipeline/` | v2 CLI entry point | **KEEP** | M3 |
| `ite_parser.py` | `08_ite_score_analysis/pipeline/` | RGB color extraction from PDFs | **KEEP** | M3 |
| `ite_analyzer_v2.py` | `08_ite_score_analysis/pipeline/` | 5-layer analysis engine + plugins | **KEEP** | M3 |
| `ite_report_builder_v2.js` | `08_ite_score_analysis/pipeline/` | Dual DOCX generator | **KEEP** | M3 |
| `ite_parser_config.json` | `08_ite_score_analysis/pipeline/` | Parser calibration constants | **KEEP** | M3 |
| `abfm_reference_2025.json` | `08_ite_score_analysis/pipeline/` | Exam specs + national benchmarks | **KEEP** | M3 |
 
### B6: Agents → M4 (Sandbox / Future)
 
| Script | Location | What It Does | Verdict | New Module |
|--------|----------|-------------|---------|------------|
| **PDF Sourcer Agent** | `agents/` | Agent SDK-powered PDF finder | **KEEP** | M4 |
| **Agent SDK docs** | `skills_abilities/` (14 files) | SDK reference documentation | **KEEP** | INFRA |
 
---
 
## SECTION C: REFERENCE DATA & CONFIG FILES
 
| Item | Location | What It Does | Verdict | New Module |
|------|----------|-------------|---------|------------|
| `session_cluster_crosswalk.csv` | `04_aafp_integration/02_working/` | Session → cluster mapping | **KEEP** | M1 |
| `session_subcat_crosswalk.csv` | `04_aafp_integration/02_working/` | Session → subcategory weights | **KEEP** | M1 |
| `poll_questions_tagged.csv` | `04_aafp_integration/` | Tagged poll questions | **KEEP** | M1 |
| `session_keyword_library.json` | `04_aafp_integration/` | VTT-derived keyword index | **KEEP** | M1 |
| `vtt_time_weights.json` | `04_aafp_integration/` | Speaker dwell-time weights | **KEEP** | M1 |
| `manual_overrides.json` | `02_ite_intelligence/` | Manual match corrections | **KEEP** | M1 |
| `_download_log.json` | `clinical_guidelines/05_scripts/` | Download audit trail | **KEEP** | M1 |
| `FLAG32_vc_missing_pdfs.csv/json` | root + clinical_guidelines | 13 missing PDF tracker | **KEEP** | INFRA |
| `FLAG34_vc_unmatched_citations.csv` | root | Unmatched citation tracker | **KEEP** | INFRA |
| `requirements.txt` (various) | multiple modules | Python dependencies | **KEEP** | INFRA |
| `package.json / package-lock.json` | root + modules | Node.js dependencies | **KEEP** | INFRA |
 
---
 
## SECTION D: DOCUMENTATION & HOUSEKEEPING
 
| Item | Location | What It Does | Verdict | New Module |
|------|----------|-------------|---------|------------|
| `MASTER_MAP_V.1.html` | `house_keeping_hub/` | Visual pipeline map (all 7 modules) | **KEEP — update for new arch** | INFRA |
| `_index.md` | root | Ground-truth directory map | **REPLACE — rebuild for new structure** | INFRA |
| `README_PROJECT.md` | root | Human-readable overview | **REPLACE — rebuild for new structure** | INFRA |
| `README.json` | root | Machine-readable metadata | **REPLACE — rebuild for new structure** | INFRA |
| `ITE_Intelligence_2.0_Architecture.md` | root | Architecture spec | **KEEP — reference** | INFRA |
| `FILE_NAMING_SPEC.md` | `house_keeping_hub/` | Naming conventions | **KEEP — update** | INFRA |
| `BATON archive` (24 files) | `house_keeping_hub/baton_archive/` | Session handoff history | **KEEP — historical record** | INFRA |
| `BATON protocol docs` | `house_keeping_hub/re-org functionality/` | Protocol spec + JSON | **KEEP** | INFRA |
| `DEPENDENCY_MAP.md` | `house_keeping_hub/archive/` | Module dependency documentation | **KEEP — reference** | INFRA |
| `CONSOLIDATION_PROPOSAL.md` | `house_keeping_hub/re-org functionality/` | Previous reorg proposal | **KEEP — reference** | INFRA |
| `REORGANIZATION_LOG*.md` | `house_keeping_hub/re-org functionality/` | Historical reorg notes | **KEEP — reference** | INFRA |
| `sandbox_setup.ps1` | `house_keeping_hub/` | PowerShell sandbox setup | **KEEP** | M4 |
| `ite-score-analyzer.plugin` | root | Cowork plugin for ITE analysis | **KEEP** | M3 |
 
---
 
## SECTION E: CANONICAL DELIVERABLES
 
| Item | Location | What It Does | Verdict | New Module |
|------|----------|-------------|---------|------------|
| `ABFM_BoardPrep_ContentOutline_HY-Enriched_v5-pearls.docx` | `00_canonical/01_curriculum/` | Final enriched VC outline | **KEEP — terminal deliverable** | M1 |
| `ABFM_BoardPrep_Supplement_ITE-Questions_v1.docx` | `00_canonical/01_curriculum/` | Supplement question booklet | **KEEP** | M1 |
| Previous outline versions (v4, v5, v6) | `00_canonical/01_curriculum/previous_versions/` | Historical iterations | **ARCHIVE** | ARCHIVE |
| Question bank exports (CSV, DOCX) | `00_canonical/02_question_bank/` | Formatted question banks | **KEEP** | M1 |
| Analysis reports | `00_canonical/03_analysis/` | ITE analysis, QC reports | **KEEP** | M3 |
| Reference tier data | `00_canonical/04_reference_data/` | Reference tiers + QRP pairs | **KEEP** | M1 |
| Acquisition list + templates | `00_canonical/05_acquisition/` | Ranked acquisition + BATON templates | **KEEP** | INFRA |
 
---
 
## SECTION F: SAFE TO ARCHIVE OR DELETE
 
| Item | Current Location | Why |
|------|-----------------|-----|
| `08_ite_score_analysis/archive/` (65 files) | Score analysis archive | v1 outputs + test iterations, all superseded |
| `08_ite_score_analysis/pipeline/v1/` | v1 legacy pipeline | Superseded by v2, backward compat only |
| `01_guideline_extractor/logs/` (40+ files) | Extraction run logs | Historical audit, not needed for rebuild |
| `01_guideline_extractor/outputs/` | Migration reports, prescan results | One-time artifacts |
| `02_ite_intelligence/logs/` (160+ files) | Enricher run logs | Historical audit |
| `scratch_scripts/` (11 files) | Diagnostic throwaway scripts | One-time debugging |
| `05_ite_refs/` ingested refs (500+ files) | Individual reference JSON+TXT | Likely superseded by enriched JSON library |
| `05_ite_refs/` matching scripts (50+) | Reference matching pipeline | Functionality absorbed into Module B scripts |
| `06_ite_pipeline/` (15 files) | Legacy extraction + categorization | Functionality absorbed into Module ⓪ and B |
| Previous DOCX versions | `00_canonical/01_curriculum/previous_versions/` | Superseded deliverables |
| `node_modules/` | Root | Reinstallable from package.json |
| `__pycache__/` (various) | Multiple locations | Python bytecode, auto-regenerates |
| `.tmp.drivedownload/`, `.tmp.driveupload/` | Root | Temp sync directories |
| `$Temp/` | Root | Temp directory |
| `import_asyncio.py` | `clinical_guidelines/` root | Appears to be a test/scratch file |
| Various `_diagnose*.py`, `_inspect*.py`, `_spot_check*.py` | Scattered | One-time diagnostic scripts |
 
---
 
## SECTION G: BY-THE-NUMBERS SUMMARY
 
### Current State
| Category | Count |
|----------|-------|
| **Total files** | ~4,400+ |
| **Python scripts** | ~201 |
| **JavaScript files** | ~15 |
| **SQLite databases** | 4 (1 production + 3 backups) |
| **PDFs** | ~510 (guideline library) + ~60 (ITE/AAFP/score) |
| **DOCXs** | ~1,600 (1,518 guideline + ~83 other) |
| **JSONs** | ~1,100+ (217 enriched + logs + configs + outputs) |
| **CSVs** | ~450+ |
| **BATON files** | 24 |
 
### After Cleanup (Estimated)
| Category | Estimated |
|----------|-----------|
| **Production scripts** | ~80 (vs 201 — remove duplicates, diagnostics, one-off scripts) |
| **Data files (keep)** | ~2,500 (DB + PDFs + DOCXs + enriched JSONs) |
| **Archive (cold storage)** | ~1,000 (logs, test outputs, v1 artifacts, previous versions) |
| **Delete** | ~900 (node_modules, __pycache__, temp dirs, scratch scripts) |
 
### Module Mapping
| New Module | Script Count | Data Files | Primary Purpose |
|------------|-------------|------------|-----------------|
| **M1 — Warehouse** | ~30 | ~2,400 | DB, PDFs, JSONs, crosswalks, ICD-10, embeddings |
| **M2 — Processor** | ~25 | ~20 (schemas, configs) | Extraction engines, enricher, DOCX builders |
| **M3 — Analyst** | ~8 | ~15 (configs, reports) | Score analysis, practice tests, trend mining |
| **M4 — Sandbox** | ~5 | ~15 | Agent SDK experiments, PDF sourcer |
| **INFRA** | ~12 | ~50 | Docs, BATONs, configs, SDK refs, plugin |
 
---
 
*Compiled March 21, 2026 · Based on parallel filesystem scans of all project directories*