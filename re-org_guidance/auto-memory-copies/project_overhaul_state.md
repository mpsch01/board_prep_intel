---
name: project_overhaul_state
description: PROJECT_OVERHAUL current state - BATON 007 session 3, FLAG 33 closed, vec tables at 100%, articles standardized, M3 fully structured
type: project
---

**Project:** ABFM ITE Intelligence System (Family Medicine board exam knowledge base)
**Root (Windows):** `C:\Users\mpsch\Desktop\claude_knowledge\00_#PROJECT_OVERHAUL\`
**Active BATON:** `BATON_active_007_20260325_m3_pipeline.md`
**Git:** `main`, latest commit `cedab1c`

---

## Current Phase: Post-TEMP-Migration / Intelligence Enrichment

The 4-module rebuild and TEMP migration campaign are complete. Articles table fully standardized (100% on source_type/tier/engine_type). Vec tables at 100% coverage (FLAG 33 closed). Next phase: Intelligence 2.0 Layer 2 (PubMed article_currency) and ITE question pipeline end-to-end test.

---

## Module State

| Module | Location | Scripts | Status |
|--------|----------|---------|--------|
| M1 Warehouse | `01_module.1_warehouse/` | 6 build + 13 maintain | Complete |
| M2 Processor | `02_module.2_processor/scripts/` | 47 Python + 6 JS + 1 config JSON | Complete |
| M3 Analyst | `03_module.3_analyst/` | 4 Python + 1 JS + 2 JSON config | Fully structured (BATON 007) |
| M4 Sandbox | `04_module.4_sandbox/` | Empty placeholder | N/A |
| DB | `00_database/db/ite_intelligence.db` | Source of truth | 1,936 articles, 1,629 questions |

---

## Key Numbers (as of BATON 007 session 3, 2026-03-25)

- **DB articles:** 1,936 (ART-0001 → ART-1937; next = ART-1938)
- **DB questions:** 1,629 (2018–2025, all years complete)
- **PDFs:** 404 across 4 tiers (non-codon 145 / local_lite 117 / codon ~90 / right_click ~58)
- **M2 scripts:** 47 Python + 6 JS + 1 config JSON (all paths dynamic)
- **M3 scripts:** 4 Python + 1 JS + 2 JSON config
- **extracted_json/:** 249 flat article JSONs (gitignored, not yet batch-sorted)
- **VC gate:** `key_data_files/session_hy_inserts_v7.json` — 352 citations
- **article_vec:** 1,936/1,936 embeddings (100%) — OpenAI text-embedding-3-small, 1536-dim
- **question_vec:** 1,629/1,629 embeddings (100%)

---

## Active Deferred Flags

| Flag | Description |
|------|-------------|
| ~~FLAG 33~~ | **CLOSED 2026-03-25** — vec tables at 100%, path bug fixed, new_only support added |
| BATCH_DIRS | 249 flat JSONs in extracted_json/ need sorting into 5 batch subdirs |
| Scholl PDFs | scholl_2025_ENCRYPTED_22/23/24.pdf in M3/resident_data/ — need password |

---

## Next Steps

1. **Intelligence 2.0 Layer 2** — `article_currency` table via PubMed MCP (freshness checks, superseded_by)
2. **ITE question pipeline end-to-end test** — `01_ite_extractor.py` → `02_ite_categorizer.py` → `03_ite_merger.py` → `ite_tag_questions.py` on 2025 source docs
3. **2018–2019 qid_art_xref crosswalk pass** — 0 entries for these years; expected pipeline gap

**Why:** The DB is the source of truth. Derived files (JSONs, DOCXs, CSVs) are disposable. Architecture extends toward clinical decision support, not just exam prep.

**How to apply:** Always read the active BATON first. TEMP_MIGRATION_MANIFEST.md is the root reference for all TEMP folder history and Windows delete checklist.
