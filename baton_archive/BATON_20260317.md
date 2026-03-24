# BATON — Layer 1 ICD-10 Rebuild (MCP Source of Truth)

**Date:** March 17, 2026
**Previous BATON:** `BATON_active_20260316_1330.md` (archived as `BATON_20260316_1330.md`)
**Status:** Layer 1 ICD-10 fully rebuilt from MCP-verified codes. FLAG 15 resolved. build_icd10_tags.py v2 rewritten. All housekeeping complete.

---

## What Was Done This Session

### 1. FLAG 15 — engine_type Fix (6 Articles)

**Problem:** 6 articles with enriched JSONs had NULL engine_type, blocking merged DOCX generation.

**Fix applied:**
- 6 UPDATEs to articles.engine_type (ART-0412, ART-0420, ART-0865, ART-1259, ART-1263, ART-1331)
- 30 stubs had citation_count recalculated from qid_art_xref links
- NULL engine_type went from 31 → 25

**Status:** RESOLVED.

### 2. ICD-10 MCP Validation → Full Layer 1 Rebuild

**Discovery:** During ICD-10 validation, found that the original Layer 1 (built via Claude Batch API) contained fabricated codes — Claude assigned codes from memory that don't exist in ICD-10-CM (e.g., C97, Q00-Q07, R95, A16.9, A56.9, B85.9, C78.9). Also found that Claude ranked overly specific codes above correct unspecified codes for general terms.

**Decision:** Replace the entire Claude-based approach with a fully deterministic MCP-first pipeline. Zero API cost.

**Pipeline:**
1. Extract diagnoses from `concept_tags.diagnoses` (already in DB, Claude-preprocessed per question)
2. Translate clinical shorthand via `clinical_synonym_map.json` (151 entries)
3. Look up translated terms in `icd10_mcp_lookup.json` (1,406 entries, all MCP-verified)
4. Insert into `article_icd10` with relevance assignment (first=primary, next 1-2=secondary, rest=related)

**Results (before → after):**
| Table | Old (Claude API) | New (MCP-first) |
|---|---|---|
| article_icd10 | 4,528 | 3,093 |
| icd10_code_xref | 1,668 | 1,006 |
| icd10_rollup | 736 | 614 |
| clinical_pathways | 4,528 | 3,093 |
| Fabricated codes | 7+ | 0 |
| Every code verified | No | Yes |

### 3. Clinical Synonym Translation Layer

Built `clinical_synonym_map.json` — 151 entries mapping clinical vocabulary to ICD-10 search terms. Three categories:
- Abbreviation expansions (51): `adhd` → `attention deficit hyperactivity`
- Drug/toxicity translations (20): `lithium toxicity` → `adverse effect of lithium`
- Clinical vocabulary translations (80): `aortic regurgitation` → `aortic valve insufficiency`

This is a **reusable asset** — will serve future pipeline runs and the clinical blending engine.

### 4. build_icd10_tags.py v2 Rewrite

Rewrote from Claude Batch API approach to MCP-first deterministic pipeline. Four phases:
- `build` — Extract diagnoses → translate → look up → insert into article_icd10
- `crosswalk` — Rebuild icd10_code_xref + icd10_rollup
- `pathways` — Rebuild clinical_pathways from ENGINE_ROLE_MAP
- `report` — Generate all 7 CSVs to readable_db_files/

Usage: `python build_icd10_tags.py all` (runs all phases, zero API cost)

### 5. Housekeeping

- Regenerated all 7 readable_db_files/ CSVs from rebuilt tables
- Persisted `clinical_synonym_map.json` and `icd10_mcp_lookup.json` to `schemas/`
- Updated `_index.md` with new Layer 1/3 numbers and housekeeping log entries
- Updated `README.json` and `README_PROJECT.md`
- Archived previous BATON

---

## Current State

### DB Tables (10 + 2 virtual)
| Table | Rows | Notes |
|---|---|---|
| articles | 1,397 | 1,372 classified (engine_type), 25 NULL (1 garbled, 24 true stubs) |
| questions | 1,189 | ITE exam questions (2020-2025) |
| question_ref_pairs | 2,069 | Canonical QID->ref pairs |
| qid_art_xref | 1,818 | Ergonomic QID->article_id join |
| article_icd10 | 3,093 | MCP-verified ICD-10 assignments (zero fabrication) |
| icd10_rollup | 614 | Parent category rollup |
| icd10_code_xref | 1,006 | Code->parent crosswalk |
| clinical_pathways | 3,093 | (article_id, icd10_code) -> pathway_role |
| article_vec | 1,397 | Vector embeddings (sqlite-vec) |
| question_vec | 1,189 | Vector embeddings (sqlite-vec) |

### Library Numbers
| Component | Count |
|---|---|
| PDFs (codon) | 146 |
| PDFs (non-codon) | 70 |
| Enriched JSONs (full extraction + ITE) | 146 |
| Enriched JSONs (scaffold only) | 71 |
| DOCXs (merged: clinical + DB intel) | 139 (6 more possible after FLAG 15 fix — user needs to re-run `build_merged_docx.js --merged-only`) |
| DOCXs (DB-only) | 1,227 |
| DOCXs total | 1,366 |

### Readable DB Files (`readable_db_files/`)
| File | Rows | Content |
|---|---|---|
| `4a_body_system_trends.csv` | 16 | Layer 4a Tier A |
| `4a_body_system_subcategory_trends.csv` | 144 | Layer 4a Tier B |
| `4a_concept_tag_trends.csv` | 166 | Layer 4a Tier C |
| `layer1_icd10_by_article.csv` | 1,366 | ICD-10 codes per article |
| `layer1_icd10_by_code.csv` | 1,430 | Articles per ICD-10 code |
| `layer1_icd10_rollup.csv` | 614 | Condensation crosswalk |
| `layer3_pathways_full_detail.csv` | 3,093 | Every clinical_pathways row |
| `layer3_pathways_by_article.csv` | 1,269 | Engine type + role per article |
| `layer3_pathways_by_code_role.csv` | 1,669 | Grouped by (code, role) |
| `layer3_pathways_by_parent_code.csv` | 1,341 | Rolled up to 3-char parents |
| `icd10_no_match_terms.txt` | 13 | Diagnosis terms without ICD-10 match |

### Schema Assets (`schemas/`)
| File | Entries | Purpose |
|---|---|---|
| `clinical_synonym_map.json` | 151 | Clinical shorthand → ICD-10 vocabulary translator |
| `icd10_mcp_lookup.json` | 1,406 | MCP-verified ICD-10 lookup cache |

---

## Open Flags

### FLAG 1 -- ITE Enrichment Quality Dimension
**Status:** OPEN (deferred)
Add ite_intelligence scoring as 6th dimension to calibrate.py.

### FLAG 13 -- Intelligence 2.0 Layers
**Status:** Layers 4a + 1 + 3 COMPLETE. Layer 2 next.

| Layer | Status | Description |
|---|---|---|
| Layer 1 (ICD-10) | COMPLETE | 3,093 MCP-verified assignments, 614 parent rollups, zero fabrication |
| Layer 2 (PubMed currency) | NOT STARTED | Article freshness checks, superseded_by tracking |
| Layer 3 (Clinical Pathways) | COMPLETE | 3,093 pathway rows, 7 roles, zero API cost |
| Layer 4a (Topic Trends) | COMPLETE | 3 CSVs, linear slopes, body_system_merged |
| Layer 4b (PubMed Trends) | NOT STARTED | External trend signals + alerts |

### FLAG 15 -- 6 Articles engine_type Fix
**Status:** RESOLVED (2026-03-17). DB fix applied. User still needs to re-run `node build_merged_docx.js --merged-only` to generate the 6 additional merged DOCXs (139 → 145).

### Pending Improvements
- **13 no-match ICD-10 terms:** Edge cases (pseudogout, sundowning, etc.) — could expand synonym map
- **220 original no-match terms (15.7%):** From MCP search. Some genuinely unmappable.
- **Blueprint backfill:** 66.8% of questions have empty blueprint field

---

## Next Steps

1. **Re-run merged DOCX builder** — User should run `node build_merged_docx.js --merged-only` to pick up the 6 FLAG 15 articles (139 → 145).
2. **FLAG 13 Layer 2 — PubMed Currency** — Article freshness checks via PubMed API. `superseded_by` tracking, publication date validation.
3. **Synonym map expansion** — Reduce the 13 no-match terms; potentially address more of the 220 original no-match terms.
5. **v2.3 re-extraction** — Re-extract all 216 PDFs through `main.py` for content-rich DOCXs. ~$6.50 batch cost.
6. FLAG 1 remains deferred.

---

## Critical File Locations

| File | Path |
|---|---|
| Active baton | `house_keeping_hub/baton_archive/BATON_active_20260317.md` |
| Baton archive | `house_keeping_hub/baton_archive/` |
| _index.md | `claude_knowledge/_index.md` |
| ITE Intelligence DB | `abfm_prep/02_ite_intelligence/db/ite_intelligence.db` |
| **build_icd10_tags.py v2** | `abfm_prep/02_ite_intelligence/scripts/build_icd10_tags.py` |
| **clinical_synonym_map.json** | `abfm_prep/02_ite_intelligence/schemas/clinical_synonym_map.json` |
| **icd10_mcp_lookup.json** | `abfm_prep/02_ite_intelligence/schemas/icd10_mcp_lookup.json` |
| ite-data-context-skill | `abfm_prep/02_ite_intelligence/schemas/ite-data-context-skill/` |
| Merged DOCX builder | `abfm_prep/02_ite_intelligence/scripts/docx_build/build_merged_docx.js` |
| JSON-to-ART-ID index | `abfm_prep/02_ite_intelligence/scripts/docx_build/json_artid_index.json` |
| DB DOCX batch builder | `abfm_prep/02_ite_intelligence/scripts/docx_build/build_db_docx.js` |
| Clinical pathways script | `abfm_prep/02_ite_intelligence/scripts/build_clinical_pathways.py` |
| Topic trends script | `abfm_prep/02_ite_intelligence/scripts/build_topic_trends.py` |
| Readable CSVs | `abfm_prep/02_ite_intelligence/readable_db_files/` |
| Enricher (batch) | `abfm_prep/02_ite_intelligence/scripts/ite_intelligence_enricher_batch.py` |
| Right-click pipeline | `abfm_prep/01_guideline_extractor/oneclick/extract_guideline.bat` |

---

## Key Architecture Reminders

- **Codon format:** `Author_Year#@#ART-XXXX@#@.pdf` — `#@#` = start, `@#@` = stop
- **Layer 1 pipeline (v2):** concept_tags.diagnoses → synonym map → MCP lookup → article_icd10 (zero API cost)
- **build_icd10_tags.py v2:** `python build_icd10_tags.py all` rebuilds everything (build + crosswalk + pathways + report)
- **ENGINE_ROLE_MAP:** (engine_type × relevance) → pathway_role (5 engine types × 3 relevance levels = 15 mappings → 7 roles)
- **Merged DOCX builder:** `build_merged_docx.js` — reads `json_artid_index.json`, loads enriched JSON per article
- **DB DOCX dependencies:** `npm install docx sql.js` in the `docx_build/` directory
- **Pipeline order:** convert_pdfs_to_json.py → ite_intelligence_enricher_batch.py → build_crosswalk_index.py
- **v2.3 pipeline:** main.py → synthesize.js → ite_intelligence_enricher.py → build_summary.js (3 Claude API calls)
- **Baton lifecycle:** archive → sync docs → write new
- **Standard filters:** Exclude `citation_count = 0`, `source_type = 'stub'`, `article_id = 'ART-0001'`
- **Trend queries:** Always use `body_system_merged` (not `body_system`)
- **ICD-10 join chain:** `icd10_rollup` → `icd10_code_xref` → `article_icd10` → `articles` → `qid_art_xref` → `questions`

---

## Known Issues

- **ART-0072 (garbled title "123-154"):** Permanently unclassifiable. No engine_type.
- **24 true stub articles:** No linked questions, no engine_type. Expected.
- **13 ICD-10 no-match terms:** Edge cases where no ICD-10 code maps cleanly (e.g., pseudogout, sundowning, wooden splinter).
- **Old batch files in readable_db_files/:** `batch_icd10_requests.jsonl`, `batch_icd10_results.jsonl`, `icd10_ingest_errors.txt`, `layer1_icd10_analysis_report.md` are artifacts from the original Claude API approach. Can be deleted.
- **node_modules not persisted:** The `docx_build/` folder needs `npm install` before re-running DOCX builders.
- **70 non-codon PDFs:** No DB match. Produce extracted-only JSONs without ITE intelligence.
- **practice_guidelines/ folder:** Duplicate of clinical_guidelines with original download names — no unique PDFs to migrate.
