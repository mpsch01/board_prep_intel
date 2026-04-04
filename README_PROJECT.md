# ABFM ITE Intelligence System — board_prep_intel

**Last updated:** 2026-04-04 (BATON 039)
**Status:** Active development
**Active BATON:** `BATON_active_039_20260404_schema_docs_cleanup.md`

---

## Project Overview

A queryable Family Medicine board exam knowledge base: 1,629 ITE questions (2018–2025) and 1,221 AAFP BRQ questions linked to a clinical guideline library of 1,985 articles and 404 PDFs via a structured SQLite pipeline. Both corpora are now schema-parallel with full enrichment across body_system, blueprint, concept_tags, and ICD-10. (Note: subcategory was dropped; blueprint filled to 100% for both banks.) Intelligence 2.0 layers (ICD-10 diagnostic linkage, clinical pathways, topic trends, vector embeddings, cross-corpus semantic similarity) provide structured clinical navigation across the full corpus. System extends beyond exam prep into clinical decision support.

---

## Directory Structure

### 00_database/
Source of truth. Never disposable.
- `db/ite_intelligence.db` — Production SQLite database (1,985 articles, 1,629 ITE questions, 1,221 AAFP questions)
- `readable_db_files/` — CSV exports, human-readable snapshots
- `logs/` — Pipeline run logs

### 01_module.1_warehouse/
PDF library (4 tiers, 404 PDFs) + pipeline build and maintenance scripts + AAFP BRQ data.
- `citation_files/ITE/VC_fail/` — ~156 PDFs: codon-named, not VC-cited, awaiting full pipeline (37 manual pending)
- `citation_files/ITE/local_lite/` — 117 PDFs: enriched, not VC-cited (pipeline complete)
- `citation_files/ITE/VC_pass/` — 94 PDFs: codon-named, VC-cited, awaiting full pipeline
- `citation_files/ITE/right_click/` — 71 PDFs: VC-cited, fully enriched (pipeline complete)
- `citation_files/AAFP/` — AAFP citation PDFs
- `practice_questions/` — 42 Q&A deliverables: 8 ITE DOCX + 8 ITE XLSX + 13 AAFP DOCX + 13 AAFP XLSX (gitignored)
- `ite_exams/` — 16 raw PDFs: YYYY_MC.pdf + YYYY_critique.pdf (2018–2025)
- `build/` — 6 scripts: self-contained full rebuild sequence (3 deprecated deleted ✓)
- `maintain/` — 18 scripts: recurring DB population and maintenance operations (2 deprecated deleted ✓)
- `scripts/aafp_brq_scraper.py` — scraper at scripts/ root (Windows-only)

### 02_module.2_processor/
Extraction, enrichment, and DOCX build pipeline.
- `scripts/` — 75 Python + 6 JS + 1 JSON config + 4 Windows utilities

### 03_module.3_analyst/
ICD-10 tagging, clinical pathways, trend analysis, score analysis, AAFP-ITE reuse investigation.
- `scripts/` — 13 Python + 2 JS + 2 JSON config

### 04_module.4_sandbox/
Experiments and agent prototypes (placeholder).

### _archive_/
Curated deliverables: curriculum definitions, question bank, analysis outputs, reference data, acquisition lists.

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

## Database State (as of 2026-04-04, BATON 039)

| Table | Rows | Notes |
|-------|------|-------|
| articles | 1,985 | ART-0001–ART-1986; next = ART-1987; +49 AAFP acquisition |
| questions (ITE) | 1,629 | 2018–2025; blueprint 100%; subcategory + topic_label DROPPED |
| aafp_questions | 1,221 | blueprint 100%; flattened; aafp_explanations DROPPED |
| question_ref_pairs | 2,722 | |
| qid_art_xref | 2,470 | all 8 years (2018–2025) |
| aafp_qid_art_xref | 864 | 643 unique questions linked (52.7%) |
| article_icd10 | 4,137 | +282 AAFP backfill 2026-03-31 |
| question_icd10 | 5,284 | 1,512/1,629 ITE questions (92.8%) |
| aafp_question_icd10 | 4,753 | 1,210/1,221 AAFP questions (99.1%) |
| clinical_pathways | 4,020 | REBUILT 2026-03-31 — blueprint-based, both banks |
| article_citation_trend | 1,740 | longitudinal citation tracking |
| pubmed_pmid_cache | 344 | Layer 2 seed (citation_id → PMID) |
| icd10_vec | 2,219 | OpenAI text-embedding-3-small (1536d) |
| article_icd10_vec | 1,674 | REBUILT 2026-04-01 |
| question_icd10_vec | 2,733 | REBUILT 2026-04-01 |
| article_vec | 1,985 | sqlite-vec virtual table; 100% coverage |
| question_vec | 1,629 | sqlite-vec virtual table; 100% coverage |
| aafp_question_vec | 1,221 | sqlite-vec virtual table; 100% coverage |
| aafp_citations | 1,600 | one row per parsed citation |
| aafp_citation_raw | 1,600 | full text archive + coordinates |
| icd10_rollup | 614 | |
| icd10_code_xref | 1,006 | |

**Next ART-ID:** ART-1987

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
| Layer 1 — ICD-10 diagnostic linkage | ✅ Built | article_icd10 (4,137) + question_icd10 (5,284) + aafp_question_icd10 (4,753) |
| Layer 2 — PubMed currency | 🟡 Deferred | pubmed_pmid_cache seeded (344 PMIDs); article_currency build pending |
| Layer 3 — Clinical pathways | ✅ Built | clinical_pathways (4,020 rows) — rebuilt 2026-03-31 |
| Layer 4 — Trends + alerts | ⬜ Planned | topic_trends + pubmed_alerts (schemas defined) |
| Citation trend tracking | ✅ Built | article_citation_trend (1,740 rows) |
| Vector embeddings (ICD-10 layer) | ✅ Built | icd10_vec (2,219) + article_icd10_vec (1,674) + question_icd10_vec (2,733) |

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

## Next Steps (BATON 039)

1. **DEFERRED-A** — 37 manual PDFs remaining (34 subscription + 3 Cochrane) → download → codon rename → `citation_files/ITE/VC_fail/`
2. **`backfill_new_article_metadata.py --art-id-min 1938`** — run once PDF batch assembled (VC gate cross-check active)
3. **DEFERRED-B** — `update_citation_trends.py` after backfill complete
4. **DEFERRED-F** — Intelligence 2.0 Layer 2: `article_currency` via PubMed (344 PMIDs in `pubmed_pmid_cache`)
5. **DEFERRED-D** — 229 citation gap articles (88 AFP batch-downloadable from `null_clean_ref_missing_articles_20260326.csv`)

---

## Technology Stack

- **Python 3** — All new scripts. pdfplumber, sqlite3, anthropic SDK.
- **Node.js** — Existing JS scripts only (no new JS). synthesize.js, build_summary.js, etc.
- **SQLite** — Production DB with sqlite-vec extension for vector search.
- **Claude API** — Enrichment engine (Anthropic SDK). API key in env vars. Haiku 4.5 for AAFP enrichment.

---

**Project Lead:** Michael Scholl, MD
**Last Reviewed:** 2026-04-04
