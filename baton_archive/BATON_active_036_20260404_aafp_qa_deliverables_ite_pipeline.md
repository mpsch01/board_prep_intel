# BATON 036 — AAFP Q&A Deliverables + ITE 2026 Pipeline Design
**Date:** 2026-04-04
**Session:** Long dual-context session — repo sweep continuation (from compaction) + new ITE pipeline design + M1 warehouse restructure + AAFP Q&A deliverable generator
**Status:** GIT-COMMITTED | DEFERRED-A still priority #1
**Replaces:** BATON_active_035_20260404_repo_sweep_mapping.md

---

## What Was Done This Session

### 1. ITE 2026 PDF-Native Pipeline (designed + built)

Corrected a fundamental misunderstanding carried from early pipeline docs: **ABFM delivers PDFs only** — never Excel. The 2018-2019 Excel-based extraction was a one-time artifact and should not be a recurring pattern.

Two new scripts built for the PDF-native ITE exam pipeline:

**`02_module.2_processor/scripts/extract_ite_year.py`** (NEW)
- PDF → DB direct; no CSV intermediate
- Pass 1: Questions PDF → extracts stem + A-E choices as JSON array → INSERTs into `questions` table with `QID-YYYY-NNNN` assigned at INSERT (first write = canonical name, same principle as codon)
- Pass 2: Critique PDF → extracts correct_letter, correct_text, explanation, citation strings → UPDATEs `questions`; INSERTs citations into `question_ref_pairs` with `match_status='pending'`
- `--dry-run` mode; collision guard if year already in DB
- ITE_SOURCE: `PROJECT_ROOT / "01_module.1_warehouse" / "ite_source"` ← M1 first, always

**`02_module.2_processor/scripts/classify_ite_year.py`** (NEW)
- Reads from DB (`body_system IS NULL AND exam_year = YYYY`)
- SBERT (all-MiniLM-L6-v2) + XGBoost classifier — separated into own script due to 30–60s model load time
- Training data: `Updated_QA_Categories.xlsx`, `misclassified_manual_review.xlsx`, `body_system_labels_2022_2024.csv`
- Updates `body_system` in place

**`01_module.1_warehouse/ite_source/README.txt`** (NEW)
- Documents naming convention: `{YEAR}_ITE_Questions.pdf`, `{YEAR}_ITE_Critique.pdf`
- Note: 2025 PDFs previously at M2 `source/ite_source/` — migrate to here
- Pipeline entry point: `extract_ite_year.py --year 2026 --dry-run`

**Design principle confirmed:** "Whatever is brought in raw should get its new name ASAP." QID-YYYY-NNNN assigned at moment of extraction — same logic as codon filename at warehouse entry.

---

### 2. M1 Warehouse Restructure

User finalized M1 as a true **working archive** with data pools:

```
01_module.1_warehouse/
├── citation_files/         ← renamed (was open folders at root)
│   ├── ITE/
│   │   ├── VC_pass/       (was 02_codon/)
│   │   ├── VC_fail/       (was 00_non-codon/)
│   │   ├── 01_local_lite/
│   │   └── 03_right_click/
│   └── AAFP/              (was aafp_brq/ — citation PDFs only)
├── practice_questions/     ← NEW data pool
│   ├── word_docs/         ← AAFP Q&A DOCX output (13 files, gitignored)
│   └── excel/             ← AAFP Q&A XLSX output (13 files, gitignored)
├── ite_source/             ← NEW — exam PDFs land here first
├── citation_docs/          ← unchanged (docx_guideline_library mirror)
└── scripts/               ← unchanged
```

**⚠ PENDING: M1 path updates** — Scripts that reference `VC_fail/`, `VC_pass/`, `01_local_lite/`, `03_right_click/` at the old M1 root now need `citation_files/ITE/` prepended. Estimated 8–10 script touches. Not yet done.

---

### 3. AAFP Q&A Deliverable Generator

**`03_module.3_analyst/scripts/build_aafp_qa_deliverables.py`** (NEW)

Generates 26 files: 13 DOCX + 13 XLSX — the full AAFP Board Review Question set as study deliverables.

**Chunking:** Greedy, ~100 Q per file, whole quizzes only — never split a quiz.

**Naming convention:**
- Display number from quiz_title ("Board Review Questions NN")
- Series 1 (assessment_id ≤ 13980): title number as-is (001–099)
- Series 2 (assessment_id ≥ 13981): title number + 99 (100–136, "quiz n+99 convention")
- Files named by display range: `AAFP_quiz_NNN-NNN`

**Output — 13 files, confirmed layout:**

| File | Q Count |
|------|---------|
| AAFP_quiz_001-023 | 103 |
| AAFP_quiz_024-033 | 100 |
| AAFP_quiz_034-043 | 100 |
| AAFP_quiz_044-053 | 100 |
| AAFP_quiz_054-063 | 100 |
| AAFP_quiz_064-073 | 100 |
| AAFP_quiz_074-083 | 100 |
| AAFP_quiz_084-093 | 100 |
| AAFP_quiz_094-104 | 109 |
| AAFP_quiz_105-114 | 100 |
| AAFP_quiz_115-124 | 100 |
| AAFP_quiz_125-135 | 100 |
| AAFP_quiz_136 | 9 |

**DOCX format:** St. Luke's palette (word_doc_defaults.py), gold left-border question headers, green correct-answer highlighting on choices + banner, light blue answer box, explanation + citation in small/gray.

**XLSX format:** Flat table — columns for stem, A/B/C/D/E choices split, correct letter + answer (green), explanation, citation. Frozen header, alternating row shading.

**Source tables:** `aafp_questions` + `aafp_citation_raw` — all 1,221 Q accounted for.

**Usage:**
```bash
python build_aafp_qa_deliverables.py             # all 26 files
python build_aafp_qa_deliverables.py --dry-run   # chunk plan only
python build_aafp_qa_deliverables.py --docx-only
python build_aafp_qa_deliverables.py --xlsx-only
```

**Note:** Files are gitignored (`*.docx`, `*.xlsx`). Regenerate at any time from DB.

---

## DB State (unchanged this session)

No DB writes. All tables same as BATON 035.

| Table | Rows |
|-------|------|
| articles | 1,985 |
| questions (ITE) | 1,629 |
| aafp_questions | 1,221 |
| article_icd10 | 4,137 |
| question_icd10 | 5,284 |
| clinical_pathways | 4,020 |
| article_icd10_vec | 1,674 |
| question_icd10_vec | 2,733 |
| pubmed_pmid_cache | 344 |
| PDFs | ~414 (37 AAFP acquisition manual pending) |
| Next ART-ID | ART-1987 |

---

## Script Counts

| Location | Python | JS | Notes |
|----------|--------|----|-------|
| M1 build/ | 6 | 0 | 3 deprecated headers applied; originals pending Windows delete |
| M1 maintain/ | 15 | 0 | 2 deprecated headers applied; originals pending Windows delete |
| M2 scripts/ | ~62 | 6 | +extract_ite_year.py +classify_ite_year.py |
| M3 scripts/ | 12 | 2 | +build_aafp_qa_deliverables.py |
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

## Pending (not yet done — mark for next session)

1. **Windows cleanup** — Delete 5 deprecated originals from M1 build/ and maintain/ (listed in BATON 035); retire BATON 035 to baton_archive/
2. **M1 path updates** — 8–10 scripts referencing old `VC_fail/`, `VC_pass/` at M1 root → prepend `citation_files/ITE/`
3. **Move 2025 PDFs** — From M2 `source/ite_source/` → M1 `ite_source/` (Windows action)
4. **DEFERRED-A** — 37 manual PDFs; once assembled → `backfill_new_article_metadata.py --art-id-min 1938`
5. **DEFERRED-B** — `update_citation_trends.py` after backfill
6. **Option B** — Flatten `00_#PROJECT_OVERHAUL/` → `claude_knowledge/` root (confirmed path-safe, repo_pre_severance.md)
7. **DEFERRED-F** — Intelligence 2.0 Layer 2: `article_currency` via PubMed

---

## Files Changed This Session

| File | Action |
|------|--------|
| `02_module.2_processor/scripts/extract_ite_year.py` | NEW — PDF-native ITE exam extractor |
| `02_module.2_processor/scripts/classify_ite_year.py` | NEW — SBERT+XGBoost body system classifier |
| `01_module.1_warehouse/ite_source/README.txt` | NEW — exam PDF landing zone docs |
| `03_module.3_analyst/scripts/build_aafp_qa_deliverables.py` | NEW — AAFP Q&A deliverable generator |
| `01_module.1_warehouse/practice_questions/word_docs/` | NEW folder (13 DOCX, gitignored) |
| `01_module.1_warehouse/practice_questions/excel/` | NEW folder (13 XLSX, gitignored) |
| `BATON_active_035_20260404_repo_sweep_mapping.md` | NEW (written previous context window) |
| `BATON_active_036_*.md` | This file |

**From previous context window (pre-compaction, now committed):**

| File | Action |
|------|--------|
| 11 M1/M2 scripts | archive_canonical → _archive_ (replace_all) |
| `repo_pre_severance.md` | NEW — full 123-script inventory + Option B analysis |
| `_index.md` | MODIFIED — BATON 035, sweep log |
| `CLAUDE.md` | MODIFIED — Active BATON 035, script counts, next steps |
| `README.md`, `README_PROJECT.md` | MODIFIED — tier/archive names |
| `_archive_/` | RENAMED from `archive_canonical/` |
| `02_module.2_processor/source/aafp_video_course_transcripts/` | RENAMED from `aafp_transcripts/` |
| 5 M1 scripts | Deprecation headers applied |
