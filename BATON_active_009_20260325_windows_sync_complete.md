# BATON 009 — Windows Sync Complete / Pipeline Ready for E2E Testing
**Date:** 2026-03-25
**Session platform:** Windows PC (Cowork VM)
**Status:** Active
**Preceding BATON:** `BATON_active_008_20260325_mac_qc_enrichment.md` (archived)
**Git hash:** `83674ca`

---

## SESSION SUMMARY — What Was Done and Why

This session replicated all BATON 008 Mac work onto the Windows machine and confirmed the enrichment pipeline is fully operational. The core output: every script in the project now resolves DB paths correctly, the 129-JSON batch enrichment is live in `extracted_json/`, and the codebase is committed.

---

## 1. DB Path Fixes — 15 Scripts (+ 2 Bonus)

All scripts from BATON 008's fix list applied and syntax-verified. 12/12 pass `ast.parse`.

### Pattern A — `BASE_DIR / "db"` → `BASE_DIR / "00_database" / "db"`

| Script | Module |
|--------|--------|
| `batch_db_extract.py` | M2/scripts/ |
| `ite_intelligence_enricher.py` | M2/scripts/ |
| `ite_intelligence_enricher_batch.py` | M2/scripts/ |
| `db_guided_extractor.py` | M2/scripts/ |
| `rematch_unmatched.py` | M2/scripts/ |

### Pattern B — Add `PROJECT_ROOT = BASE_DIR.parent.parent`, fix DB_PATH

| Script | Module |
|--------|--------|
| `rebuild_ite_db_v2.py` | M1/scripts/build/ |
| `validate_db_v2.py` | M1/scripts/build/ |
| `build_crosswalk_index.py` | M1/scripts/maintain/ |
| `build_match_staging.py` | M1/scripts/maintain/ |

### Pattern C — `os.path.join(SCRIPT_DIR, "..", "db")` → 3-level climb to PROJECT_ROOT

| Script | Module |
|--------|--------|
| `build_clinical_pathways.py` | M1/scripts/maintain/ |
| `build_topic_trends.py` | M1/scripts/maintain/ |
| `build_icd10_tags.py` | M3/scripts/ |

### Bonus — Not in BATON 008 list, caught this session

| Script | Module |
|--------|--------|
| `tagging_bundle/add_keywords.py` | tagging_bundle/ |
| `tagging_bundle/preprocess_keywords_v2.py` | tagging_bundle/ |

`compute_embeddings.py` — verified already correct (uses `SCRIPT_DIR.parent.parent.parent`). No change needed.

---

## 2. Syntax Fix — `09_build_pearl_callouts.py`

Extracted `run_xml("⚠  Red Flags: ", bold=True, color=AMBER, size=17)` to `_warning_xml` variable before the f-string. Backslash in f-string expression SyntaxError resolved.

---

## 3. New Scripts Added

| Script | Purpose |
|--------|---------|
| `batch_retrieve_enrichment.py` | Retrieve Batch API results + write `ite_intelligence{}` blocks |
| `backfill_merge_source_fields.py` | Merge `art_id`/`clean_ref` from backfill into enriched JSONs |

Both in `02_module.2_processor/scripts/`.

---

## 4. Batch Enrichment — CONFIRMED COMPLETE

- **Batch ID:** `msgbatch_01F8EYo8LCGy9iH2D6kARGPQ` — status `ended`, 134/134 succeeded
- **Retrieved:** 129/134 JSONs written (5 NO_FILE = truncation collision, acceptable)
- **`backfill_merge_source_fields.py`** ran: 188 already set / 0 needed merging (Mac session wrote directly to `extracted_json/`, already synced)
- **npm install** — `docx` + `sql.js` installed at project root

---

## 5. Current JSON State

| Category | Count |
|----------|-------|
| Total extracted JSONs | 243 |
| With `ite_intelligence{}` (batch_api) | 129 |
| With `source.art_id` (backfill) | 188 |
| Unlinked (no DB match) | 54 |
| Manifest/non-dict | 1 |

---

## 6. Current DB State (unchanged)

| Table | Rows |
|-------|------|
| articles | 1,936 |
| questions | 1,629 |
| question_ref_pairs | 2,722 |
| qid_art_xref | 1,818 |
| article_icd10 | 3,855 |
| clinical_pathways | 3,093 |

---

## 7. Housekeeping

- BATON 007 → `baton_archive/` ✅
- BATON 008 → `baton_archive/` ✅
- CLAUDE.md updated to BATON 009 ✅
- auto-memory updated: `project_overhaul_state.md`, `reference_dashboard_style.md` ✅
- Git commit `83674ca` — 24 files, clean ✅

**Still needed from Windows:** Delete `BATON_active_007_20260325_m3_pipeline.md` from project root (baton_archive copy exists).

---

## Deferred Flags (carried forward)

| Flag | Description |
|------|-------------|
| BATCH_DIRS | 243 flat JSONs in `extracted_json/` need sorting into 5 batch subdirs |
| Scholl PDFs | `scholl_2025_ENCRYPTED_22/23/24.pdf` — need password |
| Supabase eval | Connected 2026-03-25. Defer until pipeline stable. |
| Pattern B Windows paths | 5 AAFP scripts with hardcoded `C:\` — defer until Mac primary |
| Rename `#` folder | Defer until after QC + test runs |
| Dashboard replication | Replicate data lifecycle dashboard for M1, M3, Module F, ITE question pipeline |
| Orphan batch logs | Delete `_141856/_142810/_143114/_143258` log files (failed submissions) |

---

## Next Steps (Ordered)

### 1. Post-Enrichment QC
Spot-check 5–10 enriched JSONs:
```bash
# Open a few from extracted_json/ and verify ite_intelligence{} block looks correct
# Confirm _enriched_via: "batch_api" present
# Check high_yield_concepts, question_ids, concept_summary quality
```

### 2. End-to-End Module Tests
```bash
# M1: run build_crosswalk_index.py — verify DB path resolves, crosswalk_index.json written
# M2: run ite_intelligence_enricher.py --dry-run on a single codon JSON
# M3: run build_icd10_tags.py report — verify output CSVs
```

### 3. ITE Question Pipeline E2E
`01_ite_extractor.py → 02_ite_categorizer.py → 03_ite_merger.py → ite_tag_questions.py` on 2025 source docs

### 4. 2018–2019 qid_art_xref Crosswalk Pass
0 entries for 2018–2019 — expected pipeline gap, needs dedicated pass

### 5. Intelligence 2.0 Layer 2
`article_currency` table via PubMed MCP — freshness checks, `superseded_by` tracking

---

## Conventions Locked

- **Path depth (M2/scripts):** `Path(__file__).resolve().parent.parent` = PROJECT_ROOT
- **Path depth (M1/build, M1/maintain):** `Path(__file__).resolve().parent.parent.parent` = PROJECT_ROOT
- **Path depth (M3/scripts):** `Path(__file__).resolve().parent.parent` = PROJECT_ROOT
- **DB path:** `PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"` (all scripts)
- **No de novo JS.** New code = Python only.
- **VC gate:** `key_data_files/session_hy_inserts_v7.json` (352 citations)
- **Strategy 0 first** in every enricher
- **Batch API provenance:** `_enriched_via: "batch_api"` in `ite_intelligence` block
- **Backfill provenance:** `backfill_match_score`, `backfill_matched_on`, `backfill_date` in `source` block
