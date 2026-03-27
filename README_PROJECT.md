# ABFM ITE Intelligence System — PROJECT_OVERHAUL

**Last updated:** 2026-03-27 (BATON 014)
**Status:** Active development
**Active BATON:** `BATON_active_014_20260327_m1_complete_m2_clean_critique_extractor_designed.md`

---

## Project Overview

A queryable Family Medicine board exam knowledge base: 1,629 ITE questions (2018–2025) linked to a clinical guideline library of 1,936 articles and 404 PDFs via a structured SQLite pipeline. Intelligence 2.0 layers (ICD-10 diagnostic linkage, clinical pathways, topic trends, vector embeddings) provide structured clinical navigation across the full corpus. System extends beyond exam prep into clinical decision support.

---

## Directory Structure

### 00_database/
Source of truth. Never disposable.
- `db/ite_intelligence.db` — Production SQLite database (1,936 articles, 1,629 questions)
- `readable_db_files/` — CSV exports, human-readable snapshots
- `logs/` — Pipeline run logs

### 01_module.1_warehouse/
PDF library (4 tiers, 404 PDFs) + pipeline build and maintenance scripts.
- `VC_fail/` — 146 PDFs: codon-named, not VC-cited, awaiting full pipeline
- `local_lite/` — 117 PDFs: enriched, not VC-cited (pipeline complete)
- `VC_pass/` — 94 PDFs: codon-named, VC-cited, awaiting full pipeline
- `right_click/` — 71 PDFs: VC-cited, fully enriched (pipeline complete)
- `build/` — 9 scripts: self-contained full rebuild sequence
- `maintain/` — 16 scripts: recurring DB population and maintenance operations

### 02_module.2_processor/
Extraction, enrichment, and DOCX build pipeline.
- `scripts/` — 44 Python + 6 JS + 1 JSON config + 4 Windows utilities
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

## Database State (as of 2026-03-27)

| Table | Rows |
|-------|------|
| articles | 1,936 |
| questions | 1,629 |
| question_ref_pairs | 2,722 |
| qid_art_xref | 2,470 |
| article_icd10 | 3,855 |
| clinical_pathways | 3,093 |
| icd10_rollup | 614 |
| icd10_code_xref | 1,006 |
| article_vec | 1,936 |
| question_vec | 1,629 |

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

## Next Steps (BATON 014)

1. Build `article_citation_trend` table + `update_citation_trends.py` + `extract_ite_critique_refs.py`
2. 88 AFP missing articles — batch download → codon rename → ingest → enrich
3. Intelligence 2.0 Layer 2 — `article_currency` via PubMed MCP
4. E2E module tests — M1 `build_crosswalk_index.py`, M3 `build_icd10_tags.py`
5. Pre-codon VC_fail no_match — `acute-low-back-imaging...` PDF

---

## Technology Stack

- **Python 3** — All new scripts. pdfplumber, sqlite3, anthropic SDK.
- **Node.js** — Existing JS scripts only (no new JS). synthesize.js, build_summary.js, etc.
- **SQLite** — Production DB with sqlite-vec extension for vector search.
- **Claude API** — Enrichment engine (Anthropic SDK). API key in env vars.

---

**Project Lead:** Michael Scholl, MD
**Last Reviewed:** 2026-03-27
