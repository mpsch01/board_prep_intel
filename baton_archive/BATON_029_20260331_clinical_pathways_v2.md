# BATON 029 — Clinical Pathways v2 Complete + Desktop Commander Git Access
**Date:** 2026-03-31
**Session:** clinical_pathways_v2 rebuild + Desktop Commander git integration
**Status:** Layer 3 Clinical Pathways fully rebuilt. Both banks. Full ART range. Git now runnable via Desktop Commander.
**Replaces:** BATON_active_028_20260331_icd10_symmetry_complete.md

---

## What Was Done This Session

### 1. Desktop Commander Git Integration — DISCOVERED
Git commits can now be run directly from Claude via Desktop Commander's Python subprocess pattern.
Project path confirmed: `C:\Users\mpsch\Desktop\claude_knowledge\00_#PROJECT_OVERHAUL`
Helper script: `C:\Users\mpsch\Desktop\claude_knowledge\git_runner.py` (general) + `git_commit.py` (commit-specific)
Limitation still applies: cannot `rm` NTFS files from here — deletions still require Windows Explorer/terminal.

**Commits this session:**
- `2e18db9` — housekeeping: add chat_archive to .gitignore
- `9817449` — feat: build_clinical_pathways_v2.py — blueprint-based routing, both banks, full ART range

### 2. `build_clinical_pathways_v2.py` — NEW (CLINICAL-PATHWAY flag CLOSED)

**Script:** `02_module.2_processor/scripts/build_clinical_pathways_v2.py`
**Replaces:** `01_module.1_warehouse/scripts/maintain/build_clinical_pathways.py` (legacy, broken — used dropped subcategory column)

**Key changes from v1:**
- Routing signal: `questions.subcategory` (DROPPED) → `questions.blueprint` (100% filled, both banks)
- Coverage: ART-0002–ART-1397 only → full range ART-0002–ART-1985
- Both banks: ITE (qid_art_xref) + AAFP (aafp_qid_art_xref) vote per article
- New schema columns: `icd10_desc` (was missing), `source_bank` (ITE/AAFP/both/none)
- Replaced: `engine_type` column → `blueprint` column
- Table is fully rebuilt (DROP + RECREATE — derived data, disposable)

**BLUEPRINT_ROLE_MAP (replaces ENGINE_ROLE_MAP):**
```
Acute Care and Diagnosis  × primary   → first_line
Acute Care and Diagnosis  × secondary → second_line
Acute Care and Diagnosis  × related   → referral
Chronic Care Management   × primary   → first_line
Chronic Care Management   × secondary → monitoring
Chronic Care Management   × related   → special_pops
Emergent and Urgent Care  × primary   → first_line
Emergent and Urgent Care  × secondary → second_line
Emergent and Urgent Care  × related   → special_pops
Preventive Care           × primary   → screening_prevention
Preventive Care           × secondary → screening_prevention
Preventive Care           × related   → monitoring
Foundations of Care       × primary   → diagnosis
Foundations of Care       × secondary → monitoring
Foundations of Care       × related   → monitoring
```

**Run results:**
```
Articles profiled:   1,835  (1,804 question-routed, 31 fallback via source_type)
Rows inserted:       4,020  (was 3,093 legacy)
Rows skipped:        0
Distinct articles:   1,757
Distinct ICD-10:     1,334

Pathway role distribution:
  first_line             1,750  (43.5%)
  second_line              768  (19.1%)
  screening_prevention     463  (11.5%)
  monitoring               455  (11.3%)
  referral                 302   (7.5%)
  special_pops             173   (4.3%)
  diagnosis                109   (2.7%)

Source bank distribution:
  ITE        1,023 articles  2,179 rows
  both         671 articles  1,630 rows
  AAFP          63 articles    211 rows
```

**Example pathway — T2DM (E11.*):**
- first_line: 34 articles | monitoring: 29 | second_line: 11 | special_pops: 6
- screening_prevention: 6 | referral: 4 | diagnosis: 2
All 7 roles populated. Clinical blending engine working as designed.

**4 report CSVs written to `00_database/readable_db_files/`:**
- `layer3_pathways_by_article.csv` (1,785 rows)
- `layer3_pathways_by_code_role.csv` (1,974 rows)
- `layer3_pathways_full_detail.csv` (4,020 rows)
- `layer3_pathways_by_parent_code.csv` (1,252 rows)

**Conceptual note (from session discussion):**
Clinical pathways is a relational index, not a tag. An article has no single pathway role — it adopts different roles depending on the ICD-10 condition queried. The same article can be `first_line` for E11 (T2DM), `second_line` for I50 (heart failure), and `monitoring` for N18 (CKD). Questions vote on articles. Articles receive roles. Downstream consumers (study plans, DOCX builders, query interfaces) consume the article index via condition + role.

---

## DB State (as of BATON 029)

| Table | Rows | Notes |
|-------|------|-------|
| articles | 1,985 | ART-0001 → ART-1986; next = ART-1987 |
| questions (ITE) | 1,629 | blueprint 100%, subcategory DROPPED |
| questions (AAFP) | 1,221 | blueprint 100%, subcategory DROPPED |
| qid_art_xref | 2,470 | |
| aafp_qid_art_xref | 864 | |
| article_icd10 | 4,137 | |
| question_icd10 | 5,284 | 92.8% ITE coverage |
| aafp_question_icd10 | 4,753 | ~99% AAFP coverage |
| pubmed_pmid_cache | 344 | Layer 2 seed |
| icd10_vec | 2,219 | |
| article_icd10_vec | 1,674 | ⚠️ stale — needs --derive rebuild |
| question_icd10_vec | 2,733 | ⚠️ stale — needs --derive rebuild |
| **clinical_pathways** | **4,020** | ✅ rebuilt this session — blueprint-based, both banks |
| PDFs | 404 | 49 AAFP articles still awaiting download |
| Next ART-ID | ART-1987 | |
| Git | main, `9817449` | clean |

---

## Deferred Flags

| Flag | Description | Priority |
|------|-------------|----------|
| DEFERRED-A | PDF download: 49 new AAFP articles ART-1938–1986 | High |
| DEFERRED-B | `update_citation_trends.py` — run AFTER DEFERRED-A | Medium |
| DEFERRED-C | AAFP vs ITE trend comparison | Medium |
| DEFERRED-D | 229 citation gap articles (88 AFP batch-downloadable) | Medium |
| DEFERRED-E | Interactive vector dashboard | Low |
| DEFERRED-F | Intelligence 2.0 Layer 2 — `article_currency` table (344 PMIDs cached) | Medium |
| Q-ICD10-VEC | Rebuild question_icd10_vec — `build_icd10_embeddings.py --derive` | Medium |
| ARTICLE-ICD10-VEC | Rebuild article_icd10_vec (+282 new rows) — same script | Low |
| Q-VEC-GAP | Fill question vector gaps: 440 ITE (2018–2019) + 1,221 AAFP → question_vec | Medium |

**Closed this session:** CLINICAL-PATHWAY ✅

---

## Next Steps (priority order)

### 1. ICD-10 vector rebuild (you run this)
```
python 02_module.2_processor\scripts\build_icd10_embeddings.py --derive
```
Refreshes `question_icd10_vec` (now that `question_icd10` ITE side is populated)
and `article_icd10_vec` (+282 AAFP backfill rows). Zero API cost.

### 2. PDF download (DEFERRED-A)
```
python 01_module.1_warehouse\scripts\maintain\download_aafp_acquisitions.py
python 01_module.1_warehouse\scripts\maintain\backfill_new_article_metadata.py --art-id-min 1938
```
Then re-run `build_icd10_embeddings.py --derive` for new articles.

### 3. Citation trends (DEFERRED-B — after PDFs)
```
python 01_module.1_warehouse\scripts\maintain\update_citation_trends.py
```

### 4. Intelligence 2.0 Layer 2 — `article_currency`
Build `article_currency` table using 344 PMIDs in `pubmed_pmid_cache`.
Freshness checks, superseded_by, publication date flags.

### 5. Question vector gaps (Q-VEC-GAP)
Embed 440 ITE (2018–2019) + 1,221 AAFP questions → `question_vec`

---

## Files Changed This Session

| File | Action |
|------|--------|
| `build_clinical_pathways_v2.py` | NEW — M2/scripts/ |
| `clinical_pathways` (DB) | REBUILT — 4,020 rows (DROP + RECREATE) |
| `layer3_pathways_*.csv` (×4) | REBUILT — 00_database/readable_db_files/ |
| `.gitignore` | +chat_archive/ entry |
| `BATON_active_029_*.md` | This file |
| `CLAUDE.md` | Updated Active State + Next Steps |
| `README.json` | Updated clinical_pathways count + intelligence_layers |
