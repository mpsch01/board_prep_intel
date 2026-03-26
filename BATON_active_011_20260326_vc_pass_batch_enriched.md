# BATON 011 — VC_pass Batch Extracted + Enriched / Nomenclature Change Decided
**Date:** 2026-03-26
**Session platform:** Windows PC (Cowork VM)
**Status:** Active
**Preceding BATON:** `BATON_active_010_20260325_qc_path_fixes_viz.md` (→ archive)
**Git hash:** `02d8a37` (no new commits this session — enrichment output is derived data)

---

## SESSION SUMMARY — What Was Done and Why

Completed PDF-to-JSON extraction for the `02_codon` warehouse tier (94 PDFs), ran batch enrichment via Strategy 0 (100% codon_filename match rate — first clean Strategy-0 batch in project history), confirmed output integrity on Windows, and cross-referenced the 242 legacy flat JSONs against the DB to determine VC gate status. Decided on official nomenclature change: `02_codon` → `VC_pass`, `00_non-codon` → `VC_fail`.

---

## 1. VC_pass Batch — Extraction + Enrichment Complete ✅

### Extraction
```powershell
python scripts\convert_pdfs_to_json.py `
  --pdf_dir "..\01_module.1_warehouse\02_codon" `
  --out_dir "..\extracted_json\02_codon_batch"
```
- **94/94 PDFs extracted** → `extracted_json/02_codon_batch/`
- **94/94 codon present** in `source.file_name` — confirmed via VM scan

### Batch Enrichment
```powershell
python scripts\ite_intelligence_enricher_batch.py --submit --dir "..\extracted_json\02_codon_batch"
python scripts\ite_intelligence_enricher_batch.py --write
```

| Metric | Value |
|--------|-------|
| Submitted | 85 |
| Enriched | 85 |
| Errors | 0 |
| Match method | `codon_filename` — 100% |
| no_match | 9 (all in DB, all 0 linked questions — correct behavior) |

**This is the first 100% Strategy-0 batch in the project.** Previous 129-JSON batch (BATON 008) was 99.2% title-match fallback.

### no_match Investigation (9 files)
All 9 confirmed: ART-ID in DB, 0 linked questions in `qid_art_xref`. Cannot enrich without ITE exam history. Not a defect.

| ART-ID | Article |
|--------|---------|
| ART-1445 | Quinlan_2014 (acute pancreatitis) |
| ART-0864 | Metlay_Waterer_2019 (CAP guideline) ← verify not orphaned from xref |
| ART-1446 | Braun_Overbeek-Wager_2016 (endometrial cancer) |
| ART-1447 | Barreto_Svec_2019 (LARC) |
| ART-1448 | Prine_Shah_2018 (long COVID) |
| ART-1444 | Herman_Shih_2022 (ortho implants) |
| ART-0048 | American_2016 (osteoporosis) |
| ART-1449 | Harris_Zagar_2023 (gallstones) |
| ART-0015 | Abraham_Rivero_2014 (gallstones) |

### VM Cache Note
VM showed enriched files as ~2200 bytes (stale cache). Confirmed on Windows via PowerShell: `6163 bytes` — correct enriched size. VM stale view is normal for NTFS mounts; always verify on Windows if file size looks wrong.

---

## 2. Nomenclature Change — Decided, Not Yet Implemented

**Old → New:**

| Old Name | New Name | Module | Meaning |
|----------|----------|--------|---------|
| `02_codon/` | `VC_pass/` | **M1** | Staged PDFs that passed VC gate → awaiting pipeline |
| `00_non-codon/` | `VC_fail/` | **M1** | Staged PDFs that failed VC gate → awaiting pipeline |
| `right_click/` | `right_click/` | **M2** | VC_pass + fully enriched (DOCX exists) — unchanged |
| `local_lite/` | `local_lite/` | **M2** | VC_fail + fully enriched (DOCX exists) — unchanged |
| `extracted_json/02_codon_batch/` | `extracted_json/VC_pass_batch/` | M2 | Extracted JSONs from VC_pass |
| (future) | `extracted_json/VC_fail_batch/` | M2 | When 146 VC_fail PDFs are extracted |

**Rationale:** "Non-codon" was a misnomer — those files DO have codon-format filenames (`Author_Year#@#ART-XXXX@#@.pdf`). The only meaningful distinction is VC gate pass/fail. M1 holds staging tiers (VC_pass/VC_fail); M2 holds completed tiers (right_click/local_lite). Pipeline flows M1 → M2.

**Implementation scope (housekeeping):**
- [ ] Windows: Rename `01_module.1_warehouse/02_codon/` → `VC_pass/`
- [ ] Windows: Rename `01_module.1_warehouse/00_non-codon/` → `VC_fail/`
- [ ] Windows: Rename `extracted_json/02_codon_batch/` → `extracted_json/VC_pass_batch/`
- [ ] Update `CLAUDE.md` tier table + glossary
- [ ] Update `.auto-memory/memory/glossary.md` and `ite_intelligence_system.md`
- [ ] Update DB `articles.tier` column: `'non-codon'` → `'VC_fail'`, `'codon'` → `'VC_pass'`
- [ ] Update any scripts referencing `02_codon` or `00_non-codon` paths
- [ ] Git commit all renames

---

## 3. extracted_json Subfolder Structure — Decided

Cross-referencing 242 legacy flat JSONs against DB revealed the natural folder organization:

| Subfolder | Count | Contents |
|-----------|-------|----------|
| `VC_pass_batch/` | 94 | ✅ Staged, enriched this session |
| `VC_fail_batch/` | 0 | To be created when 146 VC_fail PDFs are extracted |
| `VC_pass_archive/` | 46 | Completed right_click JSONs (from legacy flat batch) |
| `VC_fail_archive/` | 49 | Completed local_lite JSONs (from legacy flat batch) |
| `pre_calibration_archive/` | — | Historical, keep as-is |

**Remaining unresolved in flat 242:**
- 84 with `non-codon` DB tier → become `VC_fail_archive` once DB tier rename runs
- 9 with `codon` DB tier → become `VC_pass_archive` once fully enriched
- 54 with no art_id → need title-match pass to link to DB

---

## 3b. 9 no_match Articles — Investigated, Closed

All 9 confirmed ITE-naive: in DB, in VC_pass tier (VC-cited), but zero `question_ref_pairs` matches for any exam year. They exist because the VC course cites them, but they've never appeared on the ITE. Enricher behavior is correct — no ite_intelligence block without exam question history.

| ART-ID | Author | Title | cit | Note |
|--------|--------|-------|-----|------|
| ART-1445 | Quinlan 2014 | Acute Pancreatitis | 0 | ITE-naive |
| ART-0864 | Metlay 2019 | e45-e67 ← BAD TITLE | 4 | Title = page range, needs fix |
| ART-1446 | Braun 2016 | Endometrial Cancer | 0 | ITE-naive |
| ART-1447 | Barreto 2019 | Chronic Neck Pain | 0 | ITE-naive |
| ART-1448 | Prine 2018 | LARC: Difficult Insertions | 0 | ITE-naive |
| ART-1444 | Herman 2022 | Long COVID (PASC) | 0 | ITE-naive |
| ART-0048 | American 2016 | Dental Implants AUC | 2 | ITE-naive |
| ART-1449 | Harris 2023 | Osteoporosis Q&A | 0 | ITE-naive |
| ART-0015 | Abraham 2014 | Gallstones | 2 | ITE-naive |

**ART-0864 flagged:** title stored as "e45-e67" (page range). Actual article = Metlay/Waterer 2019 CAP guideline. Manual title fix needed next session.

---

## 4. DB State

| Table | Rows |
|-------|------|
| articles | 1,936 |
| questions | 1,629 |
| question_ref_pairs | 2,722 |
| qid_art_xref | 1,818 |
| article_icd10 | 3,855 |
| clinical_pathways | 3,093 |
| icd10_rollup | 614 |
| icd10_code_xref | 1,006 |

**DB tier breakdown (articles):**
- `non-codon`: 1,399 (to be renamed `VC_fail`)
- `codon`: 362 (to be renamed `VC_pass`)
- `local_lite`: 117
- `right_click`: 58

---

## 5. Housekeeping Carried Forward

- [ ] **Windows:** Archive BATON 010 → `baton_archive/`
- [ ] **Windows:** Archive BATON 009 → `baton_archive/` (still pending from BATON 010)
- [ ] **Windows:** Delete orphan batch logs (`_141856/_142810/_143114/_143258`)
- [ ] **Windows:** Delete M3 duplicates (`build_clinical_pathways.py`, `build_topic_trends.py`)
- [ ] **Windows:** Delete `BATON_active_007_20260325_m3_pipeline.md` from project root
- [ ] **Windows:** Execute full nomenclature rename (see Section 2 above)
- [ ] **Windows:** Sort 242 flat JSONs into `VC_pass_archive/` and `VC_fail_archive/` subfolders

---

## Deferred Flags (carried forward + new)

| Flag | Description |
|------|-------------|
| VC_fail extraction | Extract 146 `VC_fail/` PDFs → `extracted_json/VC_fail_batch/` (next extraction run) |
| Flat JSON sort | Sort 242 legacy flat JSONs into VC_pass_archive / VC_fail_archive |
| 54 no-art-id JSONs | Need title-match pass to link to DB |
| Scholl PDFs | `scholl_2025_ENCRYPTED_22/23/24.pdf` — need password |
| Supabase eval | Defer until pipeline stable |
| Pattern B Windows paths | 5 AAFP scripts with hardcoded `C:\` — defer until Mac primary |
| Rename `#` folder | Defer until after QC + test runs |
| Dashboard replication | Replicate lifecycle dashboard for M1, M3, Module F, ITE question pipeline |
| Orphan batch logs | Delete `_141856/_142810/_143114/_143258` log files |
| no_match label | Distinguish `not_in_db` vs `no_linked_questions` statuses in enricher |
| ART-0864 verify | CAP guideline — confirm not orphaned from qid_art_xref (has 0 linked Qs) |

---

## Next Steps (Ordered)

### 1. qid_art_xref Crosswalk Pass (2018–2019 gap) ← PRIORITY
- 440 questions exist for 2018–2019 in `questions` table
- 653 `question_ref_pairs` exist for those years
- 0 entries in `qid_art_xref` for 2018–2019
- Write script to build xref entries from `question_ref_pairs` + `articles` join

### 2. Nomenclature Rename (housekeeping sweep)
Execute all renames from Section 2 above. Git commit. Update CLAUDE.md + memory files.

### 3. VC_fail Extraction
```powershell
python scripts\convert_pdfs_to_json.py `
  --pdf_dir "..\01_module.1_warehouse\VC_fail" `
  --out_dir "..\extracted_json\VC_fail_batch"
```
Then batch enrich (title-match fallback expected; confidence = low).

### 4. E2E Module Tests
- M1: `build_crosswalk_index.py`
- M3: `build_icd10_tags.py` report

### 5. Intelligence 2.0 Layer 2
`article_currency` table via PubMed MCP — freshness checks, `superseded_by` tracking

---

## Conventions Locked

- **Path standard (ALL new scripts):**
  ```python
  SCRIPT_DIR   = Path(__file__).resolve().parent   # directory of this script
  PROJECT_ROOT = SCRIPT_DIR.parent.parent          # M2/scripts → M2 → PROJECT_ROOT
  ```
  Existing enricher scripts use `BASE_DIR = Path(__file__).resolve().parent.parent.parent` — equivalent, leave as-is. New scripts use `SCRIPT_DIR` / `PROJECT_ROOT` pattern.
- **Path depth by module:** M2/scripts = 2 hops from SCRIPT_DIR | M3/scripts = 1 hop from SCRIPT_DIR | M1/build+maintain = 2 hops from SCRIPT_DIR
- **DB path:** `PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"`
- **Log path:** `PROJECT_ROOT / "00_database" / "logs"`
- **No de novo JS.** New code = Python only.
- **VC gate:** `key_data_files/session_hy_inserts_v7.json` (352 citations)
- **Strategy 0 first** in every enricher
- **Tier staging names:** `VC_pass` (→ right_click), `VC_fail` (→ local_lite) ← NEW THIS SESSION
- **extracted_json subfolders:** `VC_pass_batch/`, `VC_fail_batch/`, `VC_pass_archive/`, `VC_fail_archive/` ← NEW THIS SESSION
