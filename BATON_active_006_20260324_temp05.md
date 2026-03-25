# BATON 006 — TEMP_05 Migration Complete
**Date:** 2026-03-24
**Session:** BATON 005 → 006
**Status:** Active
**Preceding BATON:** `baton_archive/BATON_005_20260324_pathfixes.md` (archive BATON 005 from root)

---

## What Was Done This Session

**TEMP_05_ite_refs_TEMP — Full Migration**

TEMP_05 was the ITE refs pipeline folder (linked refs crosswalk + tier matching). The complete inventory, classification, de-hardcoding, and execution were run in this session.

### Scripts Migrated
| Script | Destination | Notes |
|--------|-------------|-------|
| `build_crosswalk_v2.py` | `02_module.2_processor/scripts/` | De-hardcoded. BATCH_DIRS point to `extracted_json/` subdirs with `# TODO: not yet migrated` annotations. |
| `apply_overrides.py` | `02_module.2_processor/scripts/` | De-hardcoded. Reads `crosswalk_overrides.json` from SCRIPT_DIR (sibling file). |
| `gen_linked_refs_v2.js` | `02_module.2_processor/scripts/` | De-hardcoded. `PROJECT_ROOT = path.resolve(__dirname, "../../")` |
| `match_tiers_to_library.py` | `01_module.1_warehouse/scripts/maintain/` | De-hardcoded. 3-level path: `SCRIPT_DIR.parent.parent.parent`. Output → `archive_canonical/05_acquisition/`. |
| `rebuild_acquisition_list.py` | `01_module.1_warehouse/scripts/maintain/` | De-hardcoded. Removed stale `shutil.copy2` to old `00_canonical/` path — `archive_canonical/05_acquisition/` IS canonical now. |

### Scripts NOT Migrated (Deleted or Deferred)
| Script | Decision |
|--------|----------|
| `gen_gold_tier_v2.js` | **Does not migrate.** Hardcoded to old `01_guideline_extractor/outputs/pre_calibration_archive` path. User directive: delete from TEMP_05. |
| `cri_crossref_v4.py` | **Delete.** One-use diagnostic. Fully hardcoded to `med-nav_rebuild`. Audit question closed. |
| All `tier_match_qc/` scripts | **Delete.** One-use. Audit complete (8 YES verdicts applied). |
| `linked_refs_crosswalk_v2.csv` (TEMP_05 copy) | **Leave in TEMP_05.** `crosswalk_final.csv` is what matters; v2 is intermediate. |

### Config & Data Files Migrated
| File | Destination |
|------|-------------|
| `crosswalk_overrides.json` | `02_module.2_processor/scripts/` (sibling to apply_overrides.py) |
| `linked_refs_crosswalk_final.csv` | `archive_canonical/04_reference_data/` |

### New Root Folder Created
- **`extracted_json/`** — 242 article JSONs (flat), 21 raw_txt files, manifest.json
- 5 empty batch subdirs created as placeholders: `pre_calibration_archive/`, `afp_peds_uspstf_batch/`, `id_renal_gi_hep_batch/`, `jacc_pulm_batch/`, `neuro_tox_rheum_psych_batch/`
- **Not git-tracked** (middle-man data artifacts)
- Flat layout is intentional for now — `build_crosswalk_v2.py` will WARN (not crash) on missing subdirs

### Docs Updated
- `01_module.1_warehouse/scripts/maintain/README.md` — added Reference Tier Matching & Acquisition section
- `_index.md` — updated to BATON 006, added `extracted_json/` root folder, M1/maintain count (11→13), M2/scripts count (41→45+1 config)

---

## Current DB State (unchanged this session)

| Table | Rows |
|-------|------|
| articles | 1,936 |
| questions | 1,629 (2018–2025) |
| question_ref_pairs | 2,722 |
| qid_art_xref | 1,818 |
| article_icd10 | 3,855 |
| clinical_pathways | 4,528 |

---

## Conventions Locked

- **JS rule:** All JS goes to M2/scripts. No exceptions. No de novo JS.
- **Python path pattern (M2/scripts):** `SCRIPT_DIR.parent.parent` = PROJECT_ROOT
- **Python path pattern (M1/scripts/maintain):** `SCRIPT_DIR.parent.parent.parent` = PROJECT_ROOT
- **JS path pattern:** `path.resolve(__dirname, "../../")` = PROJECT_ROOT
- **TODO annotation:** `# TODO: not yet migrated` marks paths that point to future locations (extracted_json/ batch subdirs)
- **Codon filename:** `Author_Year#@#ART-XXXX@#@.pdf`
- **VC gate:** `key_data_files/session_hy_inserts_v7.json` (352 citations)
- **Extracted JSONs:** root-level `extracted_json/` folder; NOT git-tracked; batch subdirs are placeholders until sorting
- **archive_canonical/05_acquisition/ IS canonical** — no copy needed to old `00_canonical/` path (removed from rebuild_acquisition_list.py)

---

## Deferred Flags (Carried Forward)

| Flag | Description |
|------|-------------|
| FLAG 33 | `compute_embeddings.py` + `validate_vector_search.py` deferred — requires vector DB decision |
| M3 duplicates | `build_clinical_pathways.py` + `build_topic_trends.py` in M3/scripts/ pending manual delete (VM cannot rm NTFS) |
| BATCH_DIRS sorting | 242 flat JSONs in `extracted_json/` need to be sorted into 5 named subdirs for `build_crosswalk_v2.py` to use them correctly |
| TEMP_05 Windows cleanup | User to delete from Windows: `gen_gold_tier_v2.js`, `1–21.pdf` gold list PDFs, `cri_crossref_v4.py`, `tier_match_qc/` scripts, `04_outputs/tier_match/` intermediate files |
| Remaining TEMP folders | TEMP_06, TEMP_07, TEMP_08 not yet audited/migrated |
| Old BATON 005 | Archive `BATON_active_005_20260324_pathfixes.md` → `baton_archive/` |

---

## Next Steps

1. **Windows cleanup:** Delete TEMP_05 disposable content (gen_gold_tier_v2.js, gold PDFs 1-21.pdf, cri_crossref_v4.py, tier_match_qc/ scripts, 04_outputs/tier_match/)
2. **BATCH_DIRS sorting (deferred):** Sort 242 flat JSONs into `extracted_json/` batch subdirs when crosswalk pipeline is re-run. Subdirs exist; just need the files moved in.
3. **Continue TEMP migrations:** TEMP_06 → TEMP_07 → TEMP_08 (TEMP_08 was originally flagged in BATON 005 as next)
4. **Git commit** this session's changes

---

## Script Counts (as of BATON 006)

| Location | Count |
|----------|-------|
| M1/scripts/build/ | 6 |
| M1/scripts/maintain/ | 13 |
| M2/scripts/ (Python + JS) | 45 + 1 config JSON |
| M3/scripts/ | 5 (+ 2 pending delete) |
| Total active pipeline scripts | ~69 |
