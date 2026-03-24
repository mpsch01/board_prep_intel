# Canonical File Renaming Proposal
**Date:** 2026-03-12
**Applies to:** `00_canonical/` and known named working files
**Status:** PROPOSAL — awaiting approval before any renames execute

---

## Renaming Map

### Exam Files (`EX_`)

| Current Name | Proposed Name | Notes |
|---|---|---|
| `ITE_qbank_20-25_vEXAM.docx` | `00_EX_qbank_vExam_20-25.docx` | Exam-format printable version |
| `ITE_qbank_20-25_vQ&A.docx` | `00_EX_qbank_vQA_20-25.docx` | Q&A format — ampersand removed |
| `ABFM_BoardPrep_ContentOutline_HY-Enriched_v6-resident.docx` | `00_EX_content_outline_w_q.docx` | HY-Enriched version with ITE questions injected |
| `BoardPrep-ContentOutline_SESSION-MAPPED-v2.docx` | `00_EX_content_outline_no_q.docx` | Session-mapped version without ITE questions |

### Report Files (`RPT_`)

| Current Name | Proposed Name | Notes |
|---|---|---|
| `ITE_20-25_exam_analysis.docx` | `00_RPT_ite_analysis_20-25.docx` | Primary ITE analysis report |
| `ITE_20-25_reference_analysis.docx` | `00_RPT_reference_analysis_20-25.docx` | Reference tier analysis |

### AAFP Video Course Files (`AVC_`)

| Current Name | Proposed Name | Notes |
|---|---|---|
| `^AAFP_content_outline^.docx` | `00_AVC_content_outline.docx` | Active status retained, prefix updated, invalid ^ characters removed |
| `AAFP_supplemental_qbank.docx` | `00_AVC_supplemental_qbank.docx` | AVC-sourced supplemental question bank |

### Database Files (`DB_`)

| Current Name | Proposed Name | Notes |
|---|---|---|
| `ITE_qbank_master.xlsx` | `00_DB_qbank_master_20-25.xlsx` | Master question bank — canonical active |
| `ITE_20-25_exam_analysis_workbook.xlsx` | `00_DB_ite_analysis_workbook_20-25.xlsx` | Workbook version of ITE analysis report — canonical active |

### Utility Files

| Current Name | Proposed Name | Notes |
|---|---|---|
| `_index.md` | `_index.md` | Fixed name — do not rename |
| `BATON.md` | `BATON.md` | Fixed name — do not rename |
| `README.json` | `README.json` | Fixed name — do not rename |
| `README_PROJECT.md` | `README_PROJECT.md` | Fixed name — do not rename |

---

---

## Files Confirmed NOT Renamed

Per naming spec — these are excluded from the system:

- All `.py`, `.js`, `.bat` scripts
- All `.json` pipeline files
- `BATON.md`, `README.json`, `README_PROJECT.md`, `_index.md`
- `FILE_NAMING_SPEC.md` (this spec document itself)

---

## Execution Instructions (after approval)

When approved, Desktop Claude should:
1. Rename files exactly as listed in the renaming map above
2. Do NOT modify file contents — rename only
3. Update any references to old filenames found in README.json, README_PROJECT.md, and _index.md
4. Log every rename to REORGANIZATION_LOG_v2.md
5. Move any file being retired (strikethrough in screenshots) to `previous_versions/` with `_v1` suffix — do not delete
