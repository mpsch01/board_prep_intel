# ABFM ITE Intelligence System — board_prep_intel

**Last updated:** 2026-04-07 (BATON 046)
**Status:** Active development
**Active BATON:** `BATON_active_046_20260407_layer2_article_currency.md`
**Next ART-ID:** ART-1987
**Git:** `main` → `https://github.com/mpsch01/board_prep_intel` (private)

---

## Project Overview

A queryable Family Medicine board exam knowledge base: 1,629 ITE questions (2018–2025) and 1,221 AAFP BRQ questions linked to a clinical guideline library of 1,985 articles and 981 PDFs via a structured SQLite pipeline. Both corpora are schema-parallel with full enrichment across body_system, blueprint, concept_tags, and ICD-10. Intelligence 2.0 layers (ICD-10 diagnostic linkage, clinical pathways, citation trend tracking, vector embeddings, cross-corpus semantic similarity) provide structured clinical navigation across the full corpus. System extends beyond exam prep into clinical decision support.

---

## Directory Structure

### 00_database/
Source of truth. Never disposable.
- `db/ite_intelligence.db` — Production SQLite database (1,985 articles, 1,629 ITE questions, 1,221 AAFP questions)
- `readable_db_files/` — CSV exports, human-readable snapshots
- `logs/` — Pipeline run logs

### 01_module.1_warehouse/
PDF library (4 tiers, 966 ITE + 15 AAFP PDFs) + pipeline build and maintenance scripts.
- `citation_files/ITE/VC_fail/` — 623 PDFs: bulk; lowest citation priority
- `citation_files/ITE/VC_pass/` — 168 PDFs: codon-named, VC-cited, awaiting full pipeline
- `citation_files/ITE/local_lite/` — 117 PDFs: VC_fail + fully enriched (pipeline complete)
- `citation_files/ITE/right_click/` — 58 PDFs: VC_pass + fully enriched (highest-value tier)
- `citation_files/AAFP/` — 15 AAFP citation PDFs (recovered 2026-04-05)
- `citation_files/_dupe_archive/` — 14 duplicate PDFs archived
- `practice_questions/` — 42 Q&A deliverables: 8 ITE DOCX + 8 ITE XLSX + 13 AAFP DOCX + 13 AAFP XLSX (gitignored; regenerable from DB)
- `ite_exams/` — 16 raw PDFs: YYYY_MC.pdf + YYYY_critique.pdf (2018–2025)
- `build/` — 6 scripts: self-contained full rebuild sequence
- `maintain/` — 25 scripts: recurring DB population and maintenance operations
- `scripts/aafp_brq_scraper.py` — scraper at scripts/ root (Windows-only)

### 02_module.2_processor/
Extraction, enrichment, and DOCX build pipeline.
- `scripts/` — 75 Python + 6 JS + 1 JSON config + 4 Windows utilities; includes `core/` (4py), `engines/` (7py), `utils/` (6py) packages + `source/` (transcripts, blueprint xlsx), `outputs/` (staging JSONs), `prompts/` (templates)

### 03_module.3_analyst/
ICD-10 tagging, clinical pathways, trend analysis, score analysis, AAFP-ITE reuse investigation.
- `scripts/` — 14 Python + 2 JS + 2 JSON config (ite_analyzer_v3.py, ite_parser.py, ite_report_builder_v2.js, build_article_currency.py, etc.)
- `reports/` — per-resident analysis output (analysis_v2.json + DOCX per resident)
- `resident_data/` — raw ABFM score report PDFs (not git-tracked)

### 04_module.4_sandbox/
Experiments and agent prototypes (placeholder).

### _archive_/
Curated deliverables (renamed from archive_canonical/ 2026-04-03): curriculum definitions, question bank, analysis outputs, reference data, acquisition lists. Also houses retired artifacts from Sweep 1 (docx_guideline_library/).

### baton_archive/
All archived BATON session handoff documents.

### extracted_json/
Middle-man layer (not git-tracked).
- `synthesis_library/` — 242 legacy pre-pipeline flat JSONs (inert, no ART-IDs)
- `VC_pass_batch/` — 95 enriched JSONs (VC_pass tier)
- `VC_fail_batch/` — 147 enriched JSONs (VC_fail tier)
- Root: `manifest.json` only

### key_data_files/
Critical reference data:
- `session_hy_inserts_v7.json` — VC gate (352 citations, sole right_click criterion)
- `null_clean_ref_missing_articles_20260326.csv` — 212 missing articles list (88 AFP batch-downloadable)
- `FILE_NAMING_SPEC.md`, `ITE_Intelligence_2.0_Architecture.md`

---

## Database State (as of 2026-04-07, BATON 046)

| Table | Rows | Notes |
|-------|------|-------|
| articles | 1,985 | +49 AAFP acquisition (ART-1938–ART-1986) |
| questions (ITE) | 1,629 | 2018–2025; blueprint 100% filled; subcategory + topic_label DROPPED |
| aafp_questions | 1,221 | blueprint + concept_tags 100%; correct_letter/correct_text/explanation merged in |
| question_ref_pairs | 2,722 | 222 NULL clean_ref |
| qid_art_xref | 2,470 | all 8 years (2018–2025) |
| aafp_qid_art_xref | 864 | 643 unique questions linked (52.7%) |
| article_icd10 | 4,020 | rebuilt with vec (2026-04-05) |
| question_icd10 | 5,218 | 1,512/1,629 ITE questions (92.8%) — -66 no_match rows deleted (2026-04-06) |
| aafp_question_icd10 | 4,753 | relevance normalized; related cap applied |
| clinical_pathways | 3,971 | blueprint-based, both banks — -49 no_match rows deleted (2026-04-06) |
| article_citation_trend | 1,740 | longitudinal citation tracking + watch_list flag |
| article_currency | 1,985 | ✅ Intelligence 2.0 Layer 2 complete (2026-04-07) — current:1100, updated:169, check_needed:106, not_indexed:610 |
| pubmed_pmid_cache | 344 | Layer 2 seed (citation_id → PMID) |
| icd10_vec | 2,219 | BLOB — OpenAI text-embedding-3-small (1536d) |
| article_icd10_vec | 1,757 | BLOB — rebuilt 2026-04-05 |
| question_icd10_vec | 2,747 | BLOB — rebuilt 2026-04-05 |
| article_vec | 1,985 | sqlite-vec virtual table (requires extension) |
| question_vec | 1,629 | sqlite-vec virtual table (requires extension) |
| aafp_question_vec | 1,221 | sqlite-vec virtual table (requires extension) |
| aafp_citations | 1,600 | one row per parsed citation |
| aafp_citation_raw | 1,600 | full text archive + coordinates |
| icd10_rollup | 614 | |
| icd10_code_xref | 1,006 | |

---

## Key Conventions

**Codon filename:** `Author_Year#@#ART-XXXX@#@.pdf`
The ART-ID embedded between `#@#` (start) and `@#@` (stop) codons is the durable DB link. Strategy 0 (regex parse of codon) is always the first matching strategy in every enricher.

**VC gate:** `key_data_files/session_hy_inserts_v7.json` (352 citations). Sole criterion for `right_click` vs `local_lite` tier. DB membership alone is not sufficient.

**Tier pipeline:**
```
PDF acquired → codon rename → VC gate check
                                  ↓ pass → VC_pass/ → pipeline → right_click/
                                  ↓ fail → VC_fail/ → pipeline → local_lite/
```

**Path convention (all Python scripts):**
```python
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH      = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"
```

**Locked rules:** Fix the data, not the code. Schema before script. Source data is protected. No de novo JS. QC after every integration. Git from Windows.

---

## Intelligence 2.0 Layers

| Layer | Status | Table |
|-------|--------|-------|
| Layer 1 — ICD-10 diagnostic linkage | ✅ Built | article_icd10 (4,020) + question_icd10 (5,218) + aafp_question_icd10 (4,753) |
| Layer 2 — PubMed currency | ✅ Built | article_currency (1,985 rows) — rebuilt 2026-04-07 |
| Layer 3 — Clinical pathways | ✅ Built | clinical_pathways (3,971 rows) — rebuilt 2026-03-31 |
| Layer 4 — Trends + alerts | ⬜ Partial | topic_trends built; pubmed_alerts planned |
| Citation trend tracking | ✅ Built | article_citation_trend (1,740 rows) |
| Vector embeddings (ICD-10 layer) | ✅ Built | icd10_vec (2,219) + article_icd10_vec (1,757) + question_icd10_vec (2,747) |

---

## AAFP BRQ Pipeline (complete as of BATON 022)

AAFP Board Review Questions (1,221 questions across 135 quizzes) scraped and fully enriched. Schema now parallel to ITE questions — both corpora have body_system, blueprint, concept_tags, and ICD-10. Note: subcategory was dropped; blueprint filled to 100% for both banks.

**Pipeline run order:**
```powershell
python aafp_brq_import.py                          # 5-table schema, citation splitting
python compute_embeddings.py --aafp-only           # from M1/build/
python aafp_keyword_extractor.py                   # TF-IDF stem + explanation keywords
python aafp_merge_keywords.py                      # unified all_keywords
python aafp_context_propagator.py                  # body_system, source_type, ICD-10
python aafp_assign_body_system.py                  # 3-tier classifier + audit trail
python aafp_vector_explorer.py --save              # cross-corpus AAFP↔ITE similarity
python aafp_enrich_concept_tags.py --mode linked   # API: concept_tags + subcategory + ICD-10
python aafp_enrich_concept_tags.py --mode unlinked
```

**Model selection:** Haiku 4.5 (`claude-haiku-4-5-20251001`) — ~3× cost savings vs Sonnet 4.6 at near-identical quality (validated by 10-question comparison study, BATON 022).

**Key finding:** 38 near-identical AAFP-ITE vignette pairs (dist 0.23–0.30) confirm likely direct question reuse between AAFP BRQ and ABFM ITE (BATON 020).

---

## Next Steps (BATON 046)

1. **exa-research-search Phase 2** — expansion of guideline library + clinical pathways pipeline
2. **Optional article_currency review** — 169 updated + 106 check_needed rows available for manual audit
3. **DEFERRED-AAFP-PAYWALL** — 3 articles (ART-1959, ART-1972, ART-1967) via institutional/interlibrary loan
4. **Resident-facing report toggle** — re-enable full question rendering in `ite_report_builder_v2.js` when needed (currently compact reference table mode)

---

## Technology Stack

- **Python 3** — All new scripts. pdfplumber, sqlite3, anthropic SDK.
- **Node.js** — Existing JS scripts only (no new JS). synthesize.js, build_summary.js, etc.
- **SQLite** — Production DB with sqlite-vec extension for vector search.
- **Claude API** — Enrichment engine (Anthropic SDK). API key in env vars. Haiku 4.5 for AAFP enrichment.

---

**Project Lead:** Michael Scholl, MD
**Last Reviewed:** 2026-04-07 (session housekeeping sweep — BATON 046, git 35f025d)
