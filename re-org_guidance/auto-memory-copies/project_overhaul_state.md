---
name: project_overhaul_state
description: Current PROJECT_OVERHAUL state: BATON 012, nomenclature sweep complete, VC_fail enriched (NC), rematch + classifier added
type: project
---

**Project:** ABFM ITE Intelligence System (Family Medicine board exam knowledge base)
**Root (Windows):** `C:\Users\mpsch\Desktop\claude_knowledge\00_#PROJECT_OVERHAUL\`
**Active BATON:** `BATON_active_012_20260326_vfail_enriched_rematch.md`
**Git:** `main`, latest committed `10d8208`

---

## Current Phase: VC_fail Enriched (No-Context); clean_ref Linkage Gap Diagnosed

BATON 012 session: Nomenclature sweep complete (VC_pass/VC_fail live everywhere). VC_fail 146 PDFs extracted and enriched. Root cause of 145/146 no_match identified: `_build_payload()` returned None on empty question list. Fixed: enricher now writes `enriched_no_context` blocks for DB-confirmed articles with no linked questions. 8 new clean_ref links via rematch. `classify_null_refs.py` built — 222 NULL rows classified into buckets.

---

## Module State

| Module | Location | Scripts | Status |
|--------|----------|---------|--------|
| M1 Warehouse | `01_module.1_warehouse/` | 6 build + 14 maintain | All DB paths fixed; rename_tier_labels_in_db.py added |
| M2 Processor | `02_module.2_processor/scripts/` | 53 Python + 6 JS + 1 config JSON | classify_null_refs.py added; enricher Path B fix applied |
| M3 Analyst | `03_module.3_analyst/` | 4 Python + 1 JS + 2 JSON config | DB path fixed |
| M4 Sandbox | `04_module.4_sandbox/` | Empty placeholder | N/A |
| DB | `00_database/db/ite_intelligence.db` | Source of truth | 1,936 articles, 1,629 questions |

---

## Key Numbers (as of BATON 012, 2026-03-26)

- **DB articles:** 1,936 (ART-0001 → ART-1937; next = ART-1938)
- **DB questions:** 1,629 (2018–2025, all years complete)
- **PDFs:** 404 across 4 tiers (VC_fail 146 / local_lite 117 / VC_pass 94 / right_click ~58)
- **DB tier:** VC_fail 1,399 / VC_pass 362 / local_lite 117 / right_click 58
- **M2 scripts:** 53 Python + 6 JS + 1 config JSON (all paths dynamic)
- **M3 scripts:** 4 Python + 1 JS + 2 JSON config
- **extracted_json/:** VC_pass_batch/ (94 JSONs, enriched) + VC_fail_batch/ (146 JSONs, 144 NC + 1 OK + 1 no_match) + ~249 legacy flat
- **VC gate:** `key_data_files/session_hy_inserts_v7.json` — 352 citations
- **qid_art_xref:** 1,818 rows — all 8 years complete (2018–2025)
- **question_ref_pairs:** 2,722 rows — 8 linked via rematch; 222 still NULL clean_ref

---

## clean_ref Linkage Gap

| Year | Linked | Total | Pct |
|------|--------|-------|-----|
| 2018–2023 | All | All | 100% |
| 2024 | 251 | 329 | 76.3% |
| 2025 | 279 | 423 | 66.0% |

**222 NULL clean_ref rows** classified:
- 179 well_formed — likely new 2024-2025 articles NOT yet in DB
- 26 web_resource — USPSTF/CDC pages, expected
- 13 journal_stub — permanently unmatchable
- 4 data_corrupt — question stem text bleed, need to be NULL'd

---

## Path Convention (locked)

| Module | Pattern | Resolves to |
|--------|---------|-------------|
| M2/scripts | `SCRIPT_DIR = Path(__file__).resolve().parent; PROJECT_ROOT = SCRIPT_DIR.parent.parent` | PROJECT_ROOT |
| M1/scripts/build, M1/scripts/maintain | same | PROJECT_ROOT |
| M3/scripts | `SCRIPT_DIR.parent.parent` | PROJECT_ROOT |

---

## Enricher Contract (locked as of BATON 012)

- **Strategy 0 success** = DB match confirmed = output produced (even if 0 linked questions)
- **enriched_no_context**: `_no_ite_context=True`, `citation_count=0`. NOT skipped on next run — will auto-upgrade when clean_ref linkage resolved.
- **no_match**: article truly not found in DB (no ART-ID, no clean_ref match)

---

## Active Deferred Flags

| Flag | Description | Priority |
|------|-------------|----------|
| 179 well_formed NULL clean_ref | Likely new articles not yet in DB — need ingestion | HIGH |
| 4 data_corrupt rows | NULL them out in question_ref_pairs | MEDIUM |
| 1 pre-codon VC_fail no_match | `acute-low-back-imaging...` PDF needs ART-ID + codon rename | MEDIUM |
| 54 no-art-id flat JSONs | Title-match pass to link to DB | MEDIUM |
| ART-0864 title fix | Stored as "e45-e67"; fix to Metlay/Waterer 2019 CAP | LOW |
| Scholl PDFs | scholl_2025_ENCRYPTED_22/23/24.pdf — need password | LOW |
| E2E module tests | M1 `build_crosswalk_index.py`, M3 `build_icd10_tags.py` | MEDIUM |
| Intelligence 2.0 Layer 2 | `article_currency` via PubMed MCP | MEDIUM |
| Flat JSON sort | Sort 249 legacy flat JSONs into VC_pass/VC_fail archive subfolders | LOW |
| Housekeeping | Archive BATONs 009-011, delete orphan logs, delete M3 duplicates | LOW |

---

## Next Steps

1. **NULL out 4 data_corrupt rows** in question_ref_pairs
2. **Investigate 179 well_formed NULL clean_ref rows** — are these in DB with different formatting, or genuinely new articles?
3. **ART-0864 title fix**
4. **E2E module tests** — M1 `build_crosswalk_index.py`, M3 `build_icd10_tags.py`
5. **Intelligence 2.0 Layer 2** — `article_currency` via PubMed MCP
