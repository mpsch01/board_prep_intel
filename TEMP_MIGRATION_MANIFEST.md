# TEMP Migration Manifest
**Project:** #PROJECT_OVERHAUL — ABFM ITE Intelligence System
**Last updated:** 2026-03-25 (BATON 007)
**Purpose:** Root reference for all TEMP folder migrations. Tracks what each TEMP contained, where it went, and its current disposal status.

---

## Quick Status Board

| TEMP | Name | Migration Status | Windows Delete |
|------|------|-----------------|----------------|
| TEMP_01 | *(unknown)* | Pre-BATON history — no record | ✅ Gone |
| TEMP_02 | *(unknown)* | Pre-BATON history — no record | ✅ Gone |
| TEMP_03 | *(unknown)* | Pre-BATON history — no record | ✅ Gone |
| TEMP_04 | `aafp_integration_TEMP` | ✅ Fully migrated (BATON 004/005) | ✅ Deleted |
| TEMP_05 | `ite_refs_TEMP` | ✅ Fully migrated (BATON 006) | ⏳ Partial — see detail |
| TEMP_06 | *(ITE question pipeline)* | ✅ Fully migrated (BATON 007) | ✅ Deleted by Mikey |
| TEMP_07 | `score_reports_TEMP` | ✅ Fully migrated (BATON 007) | ⏳ Pending Windows delete |
| TEMP_08 | `ite_score_analysis_TEMP` | ✅ Fully migrated (BATON 007) | ⏳ Pending Windows delete |
| TEMP_09 | `afp_library_TEMP` | ✅ Empty shell — nothing to migrate | ⏳ Pending Windows delete |

---

## Detail: Each TEMP

---

### TEMP_01 / TEMP_02 / TEMP_03
**Status:** Pre-BATON system. No documentation exists. Folders are gone from the filesystem. No action needed.

---

### TEMP_04 — `TEMP_04_aafp_integration_TEMP`
**Migrated in:** BATON 004 → BATON 005 session (2026-03-24)
**BATON reference:** `baton_archive/BATON_005_20260324_pathfixes.md`
**What it was:** AAFP Video Course integration folder — Module F VC outline pipeline + keyword library pipeline + source data.

**What migrated where:**

| Content | Destination |
|---------|-------------|
| Module F scripts (9): `01_build_crosswalk`, `02b_generate_hy_inserts`, `03_inject_into_outline`, `04_inject_poll`, `07_inject_supplements`, `08_build_supplement`, `09_build_pearl`, `build_v6_resident` | `02_module.2_processor/scripts/` |
| Keyword pipeline scripts (7): `A_outline_terms`, `B_tfidf_keywords`, `C_vtt_time_weights`, `D_keyword_library`, `E_v4_question_driven`, `F_extract_question_refs`, `G_backfill_references` | `02_module.2_processor/scripts/` |
| Utility scripts (5): `build_poll_inserts.py`, `sg_reweight_v3.py`, `validate_v4.py`, `split_by_year.py`, `hygiene_audit.py`, `hygiene_fix.py` | `02_module.2_processor/scripts/` |
| Key data files (4): `session_keyword_library.json`, `poll_inserts.json`, `vtt_time_weights.json`, `README_AAFP_course_integration.json` | `key_data_files/` |
| 50 AAFP .txt transcripts | `02_module.2_processor/source/aafp_transcripts/` |
| Content outline source DOCX | `02_module.2_processor/source/` |

**What was deleted:** Nothing — all content migrated.
**Windows delete status:** ✅ Deleted. M2 script count went from 10 → 41 scripts.

---

### TEMP_05 — `TEMP_05_ite_refs_TEMP`
**Migrated in:** BATON 006 session (2026-03-24)
**BATON reference:** `baton_archive/BATON_005_20260324_pathfixes.md` (yes — same commit window as BATON 005)
**What it was:** ITE reference crosswalk pipeline — linked refs generation, tier matching, acquisition list.

**What migrated where:**

| Content | Destination |
|---------|-------------|
| `build_crosswalk_v2.py` | `02_module.2_processor/scripts/` |
| `apply_overrides.py` | `02_module.2_processor/scripts/` |
| `gen_linked_refs_v2.js` | `02_module.2_processor/scripts/` |
| `match_tiers_to_library.py` | `01_module.1_warehouse/scripts/maintain/` |
| `rebuild_acquisition_list.py` | `01_module.1_warehouse/scripts/maintain/` |
| `crosswalk_overrides.json` | `02_module.2_processor/scripts/` (sibling config) |
| `linked_refs_crosswalk_final.csv` | `archive_canonical/04_reference_data/` |
| 242 article JSONs (flat) | `extracted_json/` (root, gitignored) |

**What was deleted:** `gen_gold_tier_v2.js` (hardcoded to old structure, deliverable already exists), `cri_crossref_v4.py` (one-use diagnostic), `tier_match_qc/` scripts (one-use audit, complete), intermediate tier_match CSVs.

**Windows delete status:** ⏳ **Partial — still pending:**
- `TEMP_05_ite_refs_TEMP/gen_gold_tier_v2.js`
- `TEMP_05_ite_refs_TEMP/cri_crossref_v4.py`
- `TEMP_05_ite_refs_TEMP/tier_match_qc/` scripts
- `TEMP_05_ite_refs_TEMP/04_outputs/tier_match/` intermediate files

---

### TEMP_06 — *(ITE Question Pipeline)*
**Migrated in:** BATON 007 session (2026-03-25)
**BATON reference:** `BATON_active_007_20260325_m3_pipeline.md`
**What it was:** ITE question extraction and classification pipeline — PDF extraction, body system categorization, Claude API enrichment.

**What migrated where:**

| Content | Destination |
|---------|-------------|
| `00_body_system_extractor.py` | `02_module.2_processor/scripts/` |
| `01_ite_extractor.py` | `02_module.2_processor/scripts/` |
| `02_ite_categorizer.py` | `02_module.2_processor/scripts/` |
| `03_ite_merger.py` | `02_module.2_processor/scripts/` |
| `ite_tag_questions.py` | `02_module.2_processor/scripts/` |
| `ite_build_from_text.py` | `02_module.2_processor/scripts/` |
| `ite_merge_csv.py` | `02_module.2_processor/scripts/` |
| `ite_diff_banks.py` | `02_module.2_processor/scripts/` |
| `ite_check_columns.py` | `02_module.2_processor/scripts/` |
| `body_system_labels_2022_2024.csv`, `body_system_labels_all.csv`, `clinical_category_labels.csv`, `med_term_library.txt` | `archive_canonical/04_reference_data/` |
| `Updated_QA_Categories.xlsx`, `misclassified_manual_review.xlsx` | `archive_canonical/04_reference_data/` |
| 6 ABFM blueprint PDFs (2022–2024) | `archive_canonical/04_reference_data/` |
| `2025_ITE_Questions.docx`, `2025_ITE_Critique.docx` | `02_module.2_processor/source/ite_source/` |

**What was deleted:** `tag_bank.py` (missing `tagger_rules` dependency, superseded by `ite_tag_questions.py`).
**Windows delete status:** ✅ Deleted by Mikey (confirmed same session).

---

### TEMP_07 — `TEMP_07_score_reports_TEMP`
**Migrated in:** BATON 007 session (2026-03-25)
**BATON reference:** `BATON_active_007_20260325_m3_pipeline.md`
**What it was:** Earlier staging of ITE score analysis outputs — Hopkins and Sarkar v1/v2 reports, raw score PDFs (original unclean filenames). Fully superseded by TEMP_08.

**What migrated where:** Nothing — all unique content was already in TEMP_08 with cleaner filenames. TEMP_07 was the messy predecessor; TEMP_08 is the clean canonical version.

**What was deleted / superseded:**
- All DOCXs (v1 and v2 iterations) — derived, regenerable
- Analysis JSONs (`score_analysis.json`, `analysis_v2.json`) — canonical copies taken from TEMP_08
- Raw PDFs with legacy names (`AS_body-system (3).pdf`, `hopkins_body-system (1).pdf`, etc.) — superseded by clean TEMP_08 names
- Screenshots (`.png`) — deleted
- `scholl_204999_ITE_SCORE (22/23/24).pdf` — superseded by clean `scholl_2025_ENCRYPTED_*.pdf` in TEMP_08

**Windows delete status:** ⏳ **Pending** — delete `TEMP_07_score_reports_TEMP/` entirely.

---

### TEMP_08 — `TEMP_08_ite_score_analysis_TEMP`
**Migrated in:** BATON 007 session (2026-03-25)
**BATON reference:** `BATON_active_007_20260325_m3_pipeline.md`
**What it was:** Full ITE score analysis pipeline v2 — parser, analyzer, CLI, report builder, reference configs, resident score PDFs, final analysis outputs.

**What migrated where:**

| Content | Destination |
|---------|-------------|
| `pipeline/abfm_reference_2025.json` | `03_module.3_analyst/scripts/` |
| `pipeline/ite_parser_config.json` | `03_module.3_analyst/scripts/` |
| `pipeline/ITE_SCORE_ANALYSIS_PIPELINE.md` | `03_module.3_analyst/docs/` |
| `README_ite_score_analysis.json` | `03_module.3_analyst/docs/` |
| `raw_pdfs/reference/2024ITEScoreResultHandbook.pdf` | `archive_canonical/04_reference_data/` |
| `raw_pdfs/reference/2025ITEScoreResultHandbook.pdf` | `archive_canonical/04_reference_data/` |
| `raw_pdfs/hopkins_2025_blueprint.pdf`, `_bodysystem.pdf` | `03_module.3_analyst/resident_data/` |
| `raw_pdfs/sarkar_2025_blueprint.pdf`, `_bodysystem.pdf` | `03_module.3_analyst/resident_data/` |
| `raw_pdfs/scholl_2025_ENCRYPTED_22/23/24.pdf` | `03_module.3_analyst/resident_data/` |
| `reports/*/score_analysis.json`, `analysis_v2.json` | `03_module.3_analyst/outputs/` |

**Note:** `pipeline/*.py` and `pipeline/*.js` were already present in `03_module.3_analyst/scripts/` — no script migration needed.

**What was deleted / not migrated:**
- `pipeline/v1/` — superseded scripts
- `archive/` — all test iterations, v1 reports (confirmed `safe_to_delete: true` per README)
- All DOCXs in `reports/` — derived, regenerable

**Windows delete status:** ⏳ **Pending** — delete `TEMP_08_ite_score_analysis_TEMP/` entirely.

---

### TEMP_09 — `TEMP_09_afp_library_TEMP`
**Migrated in:** N/A — empty shell
**What it was:** A folder with a single empty `scripts/` subdirectory. Never populated.
**Windows delete status:** ⏳ **Pending** — delete `TEMP_09_afp_library_TEMP/` entirely (2 empty dirs).

---

## Outstanding Windows Deletes

The following require manual deletion from Windows (VM cannot `rm` NTFS files):

### Root TEMP folders (delete entirely):
- [ ] `TEMP_07_score_reports_TEMP/`
- [ ] `TEMP_08_ite_score_analysis_TEMP/`
- [ ] `TEMP_09_afp_library_TEMP/`

### TEMP_05 remnants (partial delete inside folder):
- [ ] `TEMP_05_ite_refs_TEMP/gen_gold_tier_v2.js`
- [ ] `TEMP_05_ite_refs_TEMP/cri_crossref_v4.py`
- [ ] `TEMP_05_ite_refs_TEMP/tier_match_qc/` (directory + contents)
- [ ] `TEMP_05_ite_refs_TEMP/04_outputs/tier_match/` (directory + contents)

### M3 duplicate scripts (delete from M3/scripts/):
- [ ] `03_module.3_analyst/scripts/build_clinical_pathways.py`
- [ ] `03_module.3_analyst/scripts/build_topic_trends.py`

### Root BATON cleanup:
- [ ] `BATON_active_006_20260324_temp05.md` — move to `baton_archive/` or delete (archive copy exists)

---

## Conventions Established by TEMP Campaign

These patterns emerged from the migration work and are now locked:

1. **TEMP folder protocol:** Audit → classify (migrate / delete / protect) → de-hardcode scripts → copy files → git add tracked files → commit → Windows delete TEMP.
2. **Dynamic path depth:** M2/scripts = `SCRIPT_DIR.parent.parent`; M1/maintain = `SCRIPT_DIR.parent.parent.parent`; M3/scripts = `SCRIPT_DIR.parent.parent` (but `ite_analyze_v2.py` takes `--db` as CLI arg).
3. **Config JSONs travel with their sibling script** — `ite_parser_config.json` and `abfm_reference_2025.json` live in M3/scripts/ next to the scripts that load them via `Path(__file__).parent`.
4. **No de novo JS** — existing JS scripts migrate fine; all new code is Python only.
5. **`extracted_json/` is gitignored** — middle-man article enrichment artifacts, not tracked.
6. **Resident data is gitignored** — `03_module.3_analyst/resident_data/` holds protected PHI-adjacent PDFs; covered by `*.pdf` rule + explicit directory rule.
