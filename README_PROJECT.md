# ABFM ITE Intelligence System — PROJECT_OVERHAUL

**Last updated:** 2026-03-27 (BATON 016)
**Status:** Active development
**Active BATON:** `BATON_active_016_20260327_aafp_enrichment_complete_ite_similarity_scored.md`

---

## Project Overview

A queryable Family Medicine board exam knowledge base: 1,629 ITE questions (2018–2025) and 1,221 AAFP BRQ questions linked to a clinical guideline library of 1,936 articles and 404 PDFs via a structured SQLite pipeline. Intelligence 2.0 layers (ICD-10 diagnostic linkage, clinical pathways, topic trends, vector embeddings, cross-corpus semantic similarity) provide structured clinical navigation across the full corpus. System extends beyond exam prep into clinical decision support.

---

## Directory Structure

### 00_database/
Source of truth. Never disposable.
- `db/ite_intelligence.db` — Production SQLite database (1,936 articles, 1,629 questions)
- `readable_db_files/` — CSV exports, human-readable snapshots
- `logs/` — Pipeline run logs

### 01_module.1_warehouse/
PDF library (4 tiers, 404 PDFs) + pipeline build and maintenance scripts + AAFP BRQ data.
- `VC_fail/` — 146 PDFs: codon-named, not VC-cited, awaiting full pipeline
- `local_lite/` — 117 PDFs: enriched, not VC-cited (pipeline complete)
- `VC_pass/` — 94 PDFs: codon-named, VC-cited, awaiting full pipeline
- `right_click/` — 71 PDFs: VC-cited, fully enriched (pipeline complete)
- `build/` — 9 scripts: self-contained full rebuild sequence
- `maintain/` — 16 scripts: recurring DB population and maintenance operations
- `aafp_brq/scraper/` — aafp_brq_scraper.py + cookies + quiz map (Windows-only)
- `aafp_brq/staging/` — aafp_brq_staging.json (1,221 records, 4MB)

### 02_module.2_processor/
Extraction, enrichment, and DOCX build pipeline.
- `scripts/` — 49 Python + 6 JS + 1 JSON config + 4 Windows utilities
- `source/` — Input data for pipeline scripts

### 03_module.3_analyst/
ICD-10 tagging, clinical pathways, trend analysis, score analysis.
- `scripts/` — 4 Python + 1 JS + 2 JSON config

### 04_module.4_sandbox/
Experiments and agent prototypes (placeholder).

### archive_canonical/
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
- `null_clean_ref_missing_articles_20260326.csv` — 212 missing articles list
- `FILE_NAMING_SPEC.md`, `ITE_Intelligence_2.0_Architecture.md`
- `project_overhaul_inventory.md`, `RENAMING_PROPOSAL.md`, `script_library.csv`

---

## Database State (as of 2026-03-27, BATON 016)

| Table | Rows | Notes |
|-------|------|-------|
| articles | 1,936 | |
| questions (ITE) | 1,629 | 2018–2025 |
| question_ref_pairs | 2,722 | |
| qid_art_xref | 2,470 | |
| article_icd10 | 3,855 | |
| clinical_pathways | 3,093 | |
| icd10_rollup | 614 | |
| icd10_code_xref | 1,006 | |
| article_vec | 1,936 | 100% coverage |
| question_vec | 1,629 | 100% coverage |
| aafp_questions | 1,221 | 7 enrichment cols (keywords, body_system, source_type, ite_nearest_qid/dist) |
| aafp_explanations | 1,221 | explanation_keywords populated |
| aafp_citations | 1,600 | one row per parsed citation |
| aafp_citation_raw | 1,600 | full text archive + coordinates |
| aafp_qid_art_xref | 797 | 586 unique questions linked (48%) |
| aafp_question_vec | 1,221 | 100% coverage |
| aafp_question_icd10 | 1,876 | 577 questions × ~3.25 ICD codes |

**Next ART-ID:** ART-1938

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
| Layer 1 — ICD-10 diagnostic linkage | ✅ Complete | article_icd10 (3,855 rows) |
| Layer 2 — PubMed currency | ⬜ Not started | article_currency (planned) |
| Layer 3 — Clinical pathways | ✅ Complete | clinical_pathways (3,093 rows) |
| Layer 4a — Topic trends | ✅ Complete | CSVs in M3 outputs |
| Layer 4b — Alerts | ⬜ Not started | pubmed_alerts (planned) |
| Citation trend tracking | ⬜ Designed | article_citation_trend (schema ready) |

---

## M1 Build Sequence (9 scripts, self-contained)

Full DB rebuild from scratch runs M1/build/ scripts in order. All build-time operations are in M1/build/. All recurring maintenance operations are in M1/maintain/.

---

## AAFP BRQ Pipeline (added BATON 015–016)

AAFP Board Review Questions (1,221 questions across 135 quizzes) scraped and fully enriched. Separate 7-table schema from ITE questions.

**Pipeline run order:**
```powershell
python aafp_brq_import.py           # 5-table schema, citation splitting
python compute_embeddings.py --aafp-only  # from M1/build/
python aafp_keyword_extractor.py    # TF-IDF stem + explanation keywords
python aafp_context_propagator.py   # body_system, source_type, ICD-10
python aafp_vector_explorer.py --save    # cross-corpus AAFP↔ITE similarity
```

**Key finding:** Near-identical question pairs at dist<0.27 confirm likely direct question reuse between AAFP BRQ and ABFM ITE. Linked vs unlinked mean distance gap: 0.4497 vs 0.6973 — strong validation that citation matching is doing real clinical work.

---

## Next Steps (BATON 016)

1. **Windows:** Archive BATONs 013+014+015 → `baton_archive/`; delete sandbox originals; git commit
2. **AAFP question reuse investigation** — query WHERE ite_nearest_dist < 0.30; confirm exact dupes vs paraphrased
3. **AAFP-ITE lag analysis** — xref + shared citations + timing delta + ite_nearest_dist signal
4. **AAFP ref matching second pass** — 784 unmatched citations → target 70-80%
5. **229 citation gap articles** — 88 AFP batch-downloadable from `null_clean_ref_missing_articles_20260326.csv`
6. **Build designed scripts** — `article_citation_trend` table + `update_citation_trends.py` + `extract_ite_critique_refs.py`

---

## Technology Stack

- **Python 3** — All new scripts. pdfplumber, sqlite3, anthropic SDK.
- **Node.js** — Existing JS scripts only (no new JS). synthesize.js, build_summary.js, etc.
- **SQLite** — Production DB with sqlite-vec extension for vector search.
- **Claude API** — Enrichment engine (Anthropic SDK). API key in env vars.

---

**Project Lead:** Michael Scholl, MD
**Last Reviewed:** 2026-03-27
