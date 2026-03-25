# BATON 007 — TEMP_06 + TEMP_07 + TEMP_08 Migrations Complete
**Date:** 2026-03-25
**Session:** BATON 006 → 007
**Status:** Active
**Preceding BATON:** `BATON_active_006_20260324_temp05.md` (archive to `baton_archive/` from Windows)
**Git hash:** `cedab1c`

---

## What Was Done This Session

### 1. TEMP_06 — ITE Question Pipeline Migration (from session summary)

All 9 scripts migrated to `02_module.2_processor/scripts/` with dynamic paths:

| Script | Notes |
|--------|-------|
| `00_body_system_extractor.py` | Body system label extractor from ABFM blueprint PDFs |
| `01_ite_extractor.py` | ITE PDF extraction (questions → CSV). EXAM_YEAR = "2025" at top, overridable with --year |
| `02_ite_categorizer.py` | SBERT + XGBoost body system classifier. Reads from REF_DATA |
| `03_ite_merger.py` | Merge new-year CSV into master bank |
| `ite_tag_questions.py` | Claude API batch tagger (Haiku). Tags: BlueprintCategory, Subcategory, QuestionType, ClinicalFocus. Resumable. |
| `ite_build_from_text.py` | Text-input extractor (pure CLI utility) |
| `ite_merge_csv.py` | Generic CSV merge utility (--master / --incoming / --out / --priority) |
| `ite_diff_banks.py` | Diffs two question banks: MISSING_IN_LEFT/RIGHT, STEM_DRIFT, ANSWER_MISMATCH |
| `ite_check_columns.py` | QA audit — null-checks on pipeline CSV outputs |

**Reference data migrated to `archive_canonical/04_reference_data/`:**
- `body_system_labels_2022_2024.csv`, `body_system_labels_all.csv`, `clinical_category_labels.csv`, `med_term_library.txt`
- `Updated_QA_Categories.xlsx`, `misclassified_manual_review.xlsx`
- 6 ABFM blueprint PDFs (2022–2024)

**New directories created:**
- `02_module.2_processor/source/ite_source/` — holds 2025_ITE_Questions.docx + 2025_ITE_Critique.docx

**TEMP_06 cleared by Mikey** (confirmed deleted from Windows).

---

### 2. TEMP_07 + TEMP_08 — Score Analysis Pipeline Migration

M3/scripts already contained all 4 active pipeline scripts — no script migration needed. Remaining work was data and config file placement.

**New M3 structure created:**

```
03_module.3_analyst/
├── scripts/                      ← existing (5 scripts)
│   ├── ite_analyze_v2.py         ← CLI entry point (already here)
│   ├── ite_analyzer_v2.py        ← 5-layer analysis engine (already here)
│   ├── ite_parser.py             ← PyMuPDF PDF parser (already here)
│   ├── ite_report_builder_v2.js  ← Node DOCX builder (already here)
│   ├── build_icd10_tags.py       ← ICD-10 tagger (already here)
│   ├── abfm_reference_2025.json  ← NEW: ABFM benchmarks, score conversion, SEM values
│   └── ite_parser_config.json    ← NEW: parser calibration (column positions, color sigs)
├── docs/                         ← NEW (git-tracked)
│   ├── ITE_SCORE_ANALYSIS_PIPELINE.md
│   └── README_ite_score_analysis.json
├── outputs/                      ← NEW (gitignored — derived)
│   ├── hopkins_2025/
│   │   ├── analysis_v2.json
│   │   └── score_analysis.json
│   └── sarkar_2025/
│       ├── analysis_v2.json
│       └── score_analysis.json
└── resident_data/                ← NEW (gitignored — binary PDFs)
    ├── hopkins_2025_blueprint.pdf
    ├── hopkins_2025_bodysystem.pdf
    ├── sarkar_2025_blueprint.pdf
    ├── sarkar_2025_bodysystem.pdf
    ├── scholl_2025_ENCRYPTED_22.pdf
    ├── scholl_2025_ENCRYPTED_23.pdf
    └── scholl_2025_ENCRYPTED_24.pdf
```

**Reference handbooks copied to `archive_canonical/04_reference_data/`:**
- `2024ITEScoreResultHandbook.pdf`
- `2025ITEScoreResultHandbook.pdf`

**`.gitignore` additions:**
- `03_module.3_analyst/outputs/` — derived JSON analysis outputs
- `03_module.3_analyst/resident_data/` — resident score PDFs
- `extracted_json/` — 249 article enrichment JSONs (pipeline artifacts, not scripts)

**Commit `cedab1c`** — 5 files changed, 607 insertions.

**TEMP_07 + TEMP_08 pending Windows delete** (see Windows cleanup below).

---

## Windows Cleanup Required

The following are accumulating in the project root and need to be manually deleted from Windows:

| Item | Action |
|------|--------|
| `TEMP_07_score_reports_TEMP/` | Delete entirely — superseded by M3/outputs/ |
| `TEMP_08_ite_score_analysis_TEMP/` | Delete entirely — all content migrated or archived |
| `TEMP_09_afp_library_TEMP/` | Delete entirely — empty shell (no files, never populated) |
| `BATON_active_006_20260324_temp05.md` | Move to `baton_archive/` (or delete — archive copy exists) |
| `03_module.3_analyst/scripts/build_clinical_pathways.py` | Delete — duplicate, deferred from BATON 006 |
| `03_module.3_analyst/scripts/build_topic_trends.py` | Delete — duplicate, deferred from BATON 006 |

**TEMP_05 items (from BATON 006, still pending):**
- `TEMP_05_ite_refs_TEMP/gen_gold_tier_v2.js`
- `TEMP_05_ite_refs_TEMP/cri_crossref_v4.py`
- `TEMP_05_ite_refs_TEMP/tier_match_qc/` scripts
- `TEMP_05_ite_refs_TEMP/04_outputs/tier_match/` intermediate files
- `BATON_active_005_20260324_pathfixes.md` (root copy — archive in baton_archive/ exists)

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

**Known gap:** 389 articles at 0% fill for `source_type`, `categories`, `tier` columns.

---

## Conventions Locked

- **Path depth (M2/scripts):** `SCRIPT_DIR.parent.parent` = PROJECT_ROOT
- **Path depth (M1/maintain):** `SCRIPT_DIR.parent.parent.parent` = PROJECT_ROOT
- **Path depth (M3/scripts):** `SCRIPT_DIR.parent.parent` = PROJECT_ROOT (but ite_analyze_v2.py takes --db as CLI arg)
- **Parser config:** `ite_parser.py` loads `ite_parser_config.json` via `Path(__file__).parent` (sibling in M3/scripts/)
- **ABFM reference:** `ite_analyzer_v2.py` loads `abfm_reference_2025.json` via `Path(__file__).parent` (sibling in M3/scripts/)
- **Resident PDFs naming:** `{resident}_{year}_{blueprint|bodysystem}.pdf`
- **Scholl PDFs:** Encrypted (FLAG 30) — cannot be processed until password or unencrypted versions available
- **JS rule:** All JS grandfathered only. New code = Python.
- **VC gate:** `key_data_files/session_hy_inserts_v7.json` (352 citations)
- **Codon filename:** `Author_Year#@#ART-XXXX@#@.pdf`

---

## Deferred Flags (Carried Forward)

| Flag | Description |
|------|-------------|
| FLAG 33 | `compute_embeddings.py` + `validate_vector_search.py` deferred — vector DB decision needed |
| BATCH_DIRS sorting | 249 flat JSONs in `extracted_json/` need sorting into 5 named subdirs. Scripts WARN (not crash) until done. |
| Scholl ENCRYPTED PDFs | `scholl_2025_ENCRYPTED_22/23/24.pdf` in M3/resident_data/ — need password or unencrypted versions to process |

---

## Next Steps

1. **Windows cleanup** (see table above — TEMP_07, TEMP_08, TEMP_05 remnants, root BATONs, M3 duplicates)
2. **Articles gap-fill** — 389 articles at 0% for `source_type` / `categories` / `tier`. Schema-level column audit after filling (QC rule).
3. **Intelligence 2.0 Layer 2** — `article_currency` table via PubMed MCP. Check article freshness, track superseded_by.
4. **BATCH_DIRS sorting** (deferred) — when crosswalk pipeline is re-run.
5. **ITE question pipeline end-to-end test** — `01_ite_extractor.py` → `02_ite_categorizer.py` → `03_ite_merger.py` → `ite_tag_questions.py` on 2025 source docs.

---

## Script Counts (as of BATON 007)

| Location | Count |
|----------|-------|
| M1/scripts/build/ | 6 |
| M1/scripts/maintain/ | 13 |
| M2/scripts/ | 47 Python + 6 JS + 1 config JSON + misc (.bat, .ps1, .reg) |
| M3/scripts/ | 4 Python + 1 JS + 2 JSON config (+ 2 pending delete) |
| Total active pipeline scripts | ~77 |
