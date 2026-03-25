---
name: project_overhaul_state
description: PROJECT_OVERHAUL current state - BATON 009, Windows sync complete, all 15 scripts fixed, 129/134 JSONs enriched, pipeline ready for E2E testing
type: project
---

**Project:** ABFM ITE Intelligence System (Family Medicine board exam knowledge base)
**Root (Windows):** `C:\Users\mpsch\Desktop\claude_knowledge\00_#PROJECT_OVERHAUL\`
**Active BATON:** `BATON_active_009_20260325_windows_sync_complete.md`
**Git:** `main`, latest commit `e28618a`

---

## Current Phase: Post-QC Sweep / Enrichment Pipeline Active

Mac QC sweep (BATON 008) complete. All 13 broken DB paths fixed across M2, M1/build, M1/maintain, and M3/scripts. Batch API enrichment job retrieved — 129/134 JSONs now have `ite_intelligence{}` blocks. backfill_merge_source_fields.py written to inject source provenance fields. Full pipeline end-to-end test is next.

---

## Module State

| Module | Location | Scripts | Status |
|--------|----------|---------|--------|
| M1 Warehouse | `01_module.1_warehouse/` | 6 build + 13 maintain | All DB paths fixed |
| M2 Processor | `02_module.2_processor/scripts/` | 50 Python + 6 JS + 1 config JSON | All DB paths fixed |
| M3 Analyst | `03_module.3_analyst/` | 4 Python + 1 JS + 2 JSON config | DB path fixed |
| M4 Sandbox | `04_module.4_sandbox/` | Empty placeholder | N/A |
| DB | `00_database/db/ite_intelligence.db` | Source of truth | 1,936 articles, 1,629 questions |

---

## Key Numbers (as of BATON 008, 2026-03-25)

- **DB articles:** 1,936 (ART-0001 → ART-1937; next = ART-1938)
- **DB questions:** 1,629 (2018–2025, all years complete)
- **PDFs:** 404 across 4 tiers (non-codon 145 / local_lite 117 / codon ~90 / right_click ~58)
- **M2 scripts:** 50 Python + 6 JS + 1 config JSON (all paths dynamic)
- **M3 scripts:** 4 Python + 1 JS + 2 JSON config
- **extracted_json/:** 243 JSONs — 129 with `ite_intelligence{}` (batch_api), 188 with `source.art_id` (backfill), 0 with both yet (merge pending)
- **VC gate:** `key_data_files/session_hy_inserts_v7.json` — 352 citations
- **article_vec:** 1,936/1,936 embeddings (100%) — FLAG 33 closed

---

## JSON Linkage State

| Category | Count |
|----------|-------|
| Total extracted JSONs | 243 |
| With `source.art_id` (backfill) | 188 |
| With `ite_intelligence{}` (batch_api) | 129 |
| 5 NO_FILE (truncation collision — acceptable) | 5 |
| Unlinked (no DB match found) | 54 |

---

## Active Deferred Flags

| Flag | Description |
|------|-------------|
| ~~FLAG 33~~ | **CLOSED** — vec tables at 100% |
| BATCH_DIRS | 243 flat JSONs need sorting into 5 batch subdirs |
| Scholl PDFs | scholl_2025_ENCRYPTED_22/23/24.pdf — need password |
| Supabase eval | Connected 2026-03-25 — defer until pipeline stable |
| Pattern B Windows paths | 5 AAFP scripts with hardcoded `C:\` — defer until Mac primary |
| Rename `#` folder | Defer until after QC + test runs complete |
| Dashboard replication | Replicate data lifecycle dashboard for M1, M3, Module F, ITE question pipeline |
| Orphan batch logs | Delete _141856/_142810/_143114/_143258 log files (failed submissions) |

---

## Next Steps

1. **backfill_merge_source_fields.py** — inject `art_id`/`clean_ref` fields from IMPORT_JSON_IMPORT/ into extracted_json/
2. **Post-enrichment QC** — spot-check enriched JSONs, verify `ite_intelligence{}` blocks
3. **End-to-end module tests** — M1 build, M2 extract→enrich→DOCX, M3 analysis
4. **ITE question pipeline E2E** — `01→02→03→ite_tag_questions` on 2025 source docs
5. **2018–2019 qid_art_xref crosswalk pass** — 0 entries for these years
6. **Intelligence 2.0 Layer 2** — `article_currency` table via PubMed MCP

**Path conventions (locked):**
- M2/scripts: `SCRIPT_DIR.parent.parent` = PROJECT_ROOT
- M1/scripts/build and M1/scripts/maintain: `SCRIPT_DIR.parent.parent.parent` = PROJECT_ROOT
- M3/scripts: `SCRIPT_DIR.parent.parent` = PROJECT_ROOT
