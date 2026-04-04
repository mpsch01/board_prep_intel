# BATON 037 — Practice Questions Deliverables + M1 Restructure Complete
**Date:** 2026-04-04
**Session:** Continuation of BATON 036 session (post-compaction) — M1 path fixes, ITE Q&A deliverable generator, answer choice formatting fix, ite_exams archive populated
**Status:** GIT-COMMITTED | DEFERRED-A still priority #1
**Replaces:** BATON_active_036_20260404_aafp_qa_deliverables_ite_pipeline.md

---

## What Was Done This Session

### 1. M1 Warehouse Path Updates (all scripts)

BATON 036 described the M1 restructure but flagged path updates as pending. This session completed all of them.

**M1 maintain/ scripts updated** (11 files touched):
- `aafp_cleanup_filenames.py`, `aafp_retry_playwright.py`, `aafp_retry_selenium.py`, `aafp_top20_downloader.py`, `download_aafp_acquisitions.py`, `download_pmc_actor_batch.py`, `pdf_sourcer_agent.py`:
  — DEST_FOLDER / OUTPUT_DIR / STAGING_DIR updated to `citation_files/ITE/VC_fail`
- `aafp_fill_gaps.py`, `aafp_vc_batch_download.py`:
  — Added `CITATION_ITE = WAREHOUSE / "citation_files" / "ITE"` constant
  — CODON_DIR, EXTRACT_DIR, NONCODON_DIR now reference `CITATION_ITE / folder`
- `audit_engine_type_changes.py`, `backfill_new_article_metadata.py`:
  — Added CITATION_ITE constant
  — TIER_FOLDERS dict keys updated: `"01_local_lite"` → `"local_lite"`, `"03_right_click"` → `"right_click"`
  — Path construction changed from `WAREHOUSE / folder` to `CITATION_ITE / folder`

**Pre-existing bug fixed:** `aafp_vc_batch_download.py` had a NameError — `LIBRARY_BASE` referenced in directory scan loop but never defined. Removed the offending `LIBRARY_BASE / "pdf_non-codon"` entry (redundant since EXTRACT_DIR already covers VC_fail).

**M2 script updated:**
- `extract_ite_year.py` line 52: `ite_source` → `ite_exams` (matches actual folder name)

**Scraper script updated:**
- `aafp_brq_scraper.py` (moved from `aafp_brq/scraper/` to `M1/scripts/` last session): removed meaningless `WAREHOUSE_DIR`, set `OUTPUT_DIR = SCRIPT_DIR / "_aafp_staging"`, `QUIZ_MAP_FILE = SCRIPT_DIR / "aafp_quiz_map.json"`
- `aafp_brq_import.py` (M2): STAGING_FILE path updated to `_archive_/02_question_bank/aafp_initial_staging/aafp_brq_staging.json`

---

### 2. `build_ite_qa_deliverables.py` — NEW M3 Script

**Location:** `03_module.3_analyst/scripts/build_ite_qa_deliverables.py`

Generates 1 DOCX + 1 XLSX per ITE exam year (2018–2025) = 16 files total.

**Output:**
- `01_module.1_warehouse/practice_questions/word_docs/ITE_{YEAR}_QA.docx`
- `01_module.1_warehouse/practice_questions/excel/ITE_{YEAR}_QA.xlsx`

**DOCX format:**
- St. Luke's palette (word_doc_defaults.py), gold left-border question header with QID metadata
- Question header shows: `Q{n}  (QID-YYYY-NNNN  ·  body_system  ·  blueprint)`
- Answer choices: **all uniform** (dark text, no bold) — correct answer NOT revealed in choices
- Light blue `✓ Answer:` banner below choices is the sole reveal
- Explanation + reference in small/gray

**XLSX format (13 columns):**
`#, QID, Year, Stem, A, B, C, D, E, Correct, Correct Answer, Explanation, Reference`
— Body System and Blueprint columns intentionally excluded (they're in the DOCX header for context; not needed in the spreadsheet review format)

**Usage:**
```bash
python build_ite_qa_deliverables.py              # all 16 files
python build_ite_qa_deliverables.py --dry-run    # counts only
python build_ite_qa_deliverables.py --year 2025  # single year
python build_ite_qa_deliverables.py --docx-only
python build_ite_qa_deliverables.py --xlsx-only
```

**Counts (all 8 years generated and verified):**
| Year | Q |
|------|---|
| 2018 | 240 |
| 2019 | 200 |
| 2020 | 198 |
| 2021 | 198 |
| 2022 | 199 |
| 2023 | 199 |
| 2024 | 195 |
| 2025 | 200 |
| **Total** | **1,629** |

---

### 3. Answer Choice Formatting Fix (both scripts)

**Bug:** `build_ite_qa_deliverables.py` and `build_aafp_qa_deliverables.py` both rendered the correct answer choice in green bold text inside the multiple choice list — giving away the answer before residents reached the reveal banner.

**Fix applied to both scripts:** All 4 `is_correct`-dependent font lines in the choices loop changed to hardcoded `bold=False` / `RGB_DARK_TEXT`. `is_correct` now used only to detect which letter matched (needed downstream for the banner) — not applied to any visual formatting in the choices block.

**Design rule locked:** Only the `✓ Answer:` banner (light blue shaded box) reveals the correct answer. MC choices must always appear uniform.

**All files regenerated after fix:**
- 16 ITE files (8 DOCX + 8 XLSX) ✓
- 26 AAFP files (13 DOCX + 13 XLSX) ✓

---

### 4. M1 Warehouse Restructure — Confirmed Complete

Final M1 domain structure on disk:

```
01_module.1_warehouse/
├── citation_files/
│   ├── ITE/
│   │   ├── VC_pass/          ← PDFs passed VC gate, awaiting enrichment
│   │   ├── VC_fail/          ← PDFs failed VC gate, awaiting enrichment
│   │   ├── local_lite/       ← VC_fail + fully enriched (DOCX exists)
│   │   └── right_click/      ← VC_pass + fully enriched (DOCX exists)
│   └── AAFP/                 ← AAFP citation PDFs
├── practice_questions/
│   ├── word_docs/            ← 8 ITE DOCX + 13 AAFP DOCX (gitignored)
│   └── excel/                ← 8 ITE XLSX + 13 AAFP XLSX (gitignored)
├── ite_exams/                ← 16 raw exam PDFs (2018–2025, both MC + critique)
│   ├── YYYY_MC.pdf           ← naming convention: YYYY_MC.pdf
│   └── YYYY_critique.pdf     ← naming convention: YYYY_critique.pdf
│   └── README.txt
├── scripts/
│   ├── aafp_brq_scraper.py   ← moved from aafp_brq/scraper/
│   ├── build/                ← 9 scripts (3 deprecated)
│   └── maintain/             ← 17 scripts (2 deprecated)
└── README.json
```

**ite_exams naming convention confirmed:** All 8 years use `YYYY_MC.pdf` / `YYYY_critique.pdf`. The 2025 files were manually renamed from `2025_ITE_Questions.pdf` / `2025_ITE_Critique.pdf` to match.

**Note for extract_ite_year.py:** The script currently expects `{YEAR}_ITE_Questions.pdf` / `{YEAR}_ITE_Critique.pdf` (from BATON 036 README). Update expected filenames to `{YEAR}_MC.pdf` / `{YEAR}_critique.pdf` when running the 2026 exam pipeline.

---

## DB State (unchanged this session)

No DB writes. All tables same as BATON 035/036.

| Table | Rows |
|-------|------|
| articles | 1,985 |
| questions (ITE) | 1,629 |
| aafp_questions | 1,221 |
| article_icd10 | 4,137 |
| question_icd10 | 5,284 |
| aafp_question_icd10 | 4,753 |
| clinical_pathways | 4,020 |
| article_icd10_vec | 1,674 |
| question_icd10_vec | 2,733 |
| pubmed_pmid_cache | 344 |
| PDFs (ite_exams) | 16 (8 years × MC + critique) |
| PDFs (citation tiers) | ~414 (37 AAFP acquisition manual pending) |
| Next ART-ID | ART-1987 |

---

## Script Counts

| Location | Python | JS | Notes |
|----------|--------|----|-------|
| M1 build/ | 9 | 0 | 3 deprecated headers applied; originals pending Windows delete |
| M1 maintain/ | 17 | 0 | 2 deprecated headers applied; originals pending Windows delete; aafp_brq_scraper.py moved to scripts/ root |
| M2 scripts/ | ~64 | 6 | +extract_ite_year.py +classify_ite_year.py (BATON 036) |
| M3 scripts/ | 14 | 2 | +build_aafp_qa_deliverables.py (036) +build_ite_qa_deliverables.py (037) |
| skills_abilities/agents/ | 5 | 0 | Stable |

---

## Deferred Flags

| Flag | Description | Priority |
|------|-------------|----------|
| DEFERRED-A | 37 manual PDFs remaining: 34 subscription + 3 Cochrane → codon rename → VC_fail | **HIGH** |
| DEFERRED-B | `update_citation_trends.py` after backfill | MEDIUM |
| DEFERRED-C | AAFP vs ITE trend comparison | MEDIUM |
| DEFERRED-D | 229 citation gap articles (88 AFP batch-downloadable) | MEDIUM |
| DEFERRED-E | Interactive vector dashboard | LOW |
| DEFERRED-F | Intelligence 2.0 Layer 2 (`article_currency` via PubMed, 344 PMIDs cached) | MEDIUM |

---

## Pending (mark for next session)

1. **Windows cleanup** — Delete 5 deprecated script originals from M1 build/ and maintain/ (listed in BATON 035)
2. **DEFERRED-A** — 37 manual PDFs; once assembled → `backfill_new_article_metadata.py --art-id-min 1938`
3. **DEFERRED-B** — `update_citation_trends.py` after backfill
4. **`extract_ite_year.py` filename update** — change expected filenames from `{YEAR}_ITE_Questions.pdf` → `{YEAR}_MC.pdf` and `{YEAR}_ITE_Critique.pdf` → `{YEAR}_critique.pdf`
5. **Option B** — Flatten `00_#PROJECT_OVERHAUL/` → `claude_knowledge/` root (confirmed path-safe per `repo_pre_severance.md`)
6. **DEFERRED-F** — Intelligence 2.0 Layer 2: `article_currency` via PubMed

---

## Files Changed This Session

| File | Action |
|------|--------|
| `03_module.3_analyst/scripts/build_ite_qa_deliverables.py` | NEW — ITE Q&A deliverable generator (16 files, 2018–2025) |
| `03_module.3_analyst/scripts/build_aafp_qa_deliverables.py` | MODIFIED — answer choice formatting fix (green/bold removed) |
| `03_module.3_analyst/scripts/build_ite_qa_deliverables.py` | MODIFIED — answer choice fix + XLSX drops body_system/blueprint |
| `01_module.1_warehouse/scripts/maintain/aafp_cleanup_filenames.py` | MODIFIED — citation_files/ITE path |
| `01_module.1_warehouse/scripts/maintain/aafp_retry_playwright.py` | MODIFIED — citation_files/ITE path |
| `01_module.1_warehouse/scripts/maintain/aafp_retry_selenium.py` | MODIFIED — citation_files/ITE path |
| `01_module.1_warehouse/scripts/maintain/aafp_top20_downloader.py` | MODIFIED — citation_files/ITE path |
| `01_module.1_warehouse/scripts/maintain/download_aafp_acquisitions.py` | MODIFIED — citation_files/ITE path |
| `01_module.1_warehouse/scripts/maintain/download_pmc_actor_batch.py` | MODIFIED — citation_files/ITE path |
| `01_module.1_warehouse/scripts/maintain/pdf_sourcer_agent.py` | MODIFIED — citation_files/ITE path |
| `01_module.1_warehouse/scripts/maintain/aafp_fill_gaps.py` | MODIFIED — CITATION_ITE constant + path refactor |
| `01_module.1_warehouse/scripts/maintain/aafp_vc_batch_download.py` | MODIFIED — CITATION_ITE + NameError fix (LIBRARY_BASE removed) |
| `01_module.1_warehouse/scripts/maintain/audit_engine_type_changes.py` | MODIFIED — CITATION_ITE + TIER_FOLDERS keys updated |
| `01_module.1_warehouse/scripts/maintain/backfill_new_article_metadata.py` | MODIFIED — CITATION_ITE + TIER_FOLDERS keys updated |
| `01_module.1_warehouse/scripts/aafp_brq_scraper.py` | MODIFIED — OUTPUT_DIR + QUIZ_MAP_FILE paths for new scripts/ location |
| `02_module.2_processor/scripts/extract_ite_year.py` | MODIFIED — ite_source → ite_exams |
| `02_module.2_processor/scripts/aafp_brq_import.py` | MODIFIED — STAGING_FILE → _archive_ path |
| `01_module.1_warehouse/practice_questions/word_docs/` | 8 ITE DOCX + 13 AAFP DOCX regenerated |
| `01_module.1_warehouse/practice_questions/excel/` | 8 ITE XLSX + 13 AAFP XLSX regenerated |
