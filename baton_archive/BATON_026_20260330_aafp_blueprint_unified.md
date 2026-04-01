# BATON 026 — AAFP Blueprint Unified + Schema Cleanup
**Date:** 2026-03-30
**Session:** aafp_blueprint + schema cleanup + skill doc update
**Status:** Both corpora fully blueprint-classified. aafp_questions flattened and cleaned.
**Replaces:** BATON_active_025_20260330_2020_2023_blueprint_v2.md

---

## What Was Done This Session

### 1. Blueprint QC — 2018/2019 v1 labels (BATON 025 carry-over)
- All 8 years confirmed populated, all using consistent long-form labels
- v1 (2018-2019): label format identical to v2 and Gold Standard — no normalization issue
- Distribution flag: 2018-2019 show heavier Chronic weighting vs v2 years — methodology note, not an error

### 2. FLAG-D Cleared — Dashboard subcategory constants verified
- 11 subcategories confirmed, 1,221/1,221 total ✓

### 3. FLAG-C Cleared — ite-data-context-skill updated
- DB path fixed (old abfm_prep path → 00_database/db/)
- All entity counts updated (articles, questions, xref tables, ICD-10 tables)
- AAFP corpus fully documented: aafp_questions, aafp_explanations (→ merged), aafp_qid_art_xref, aafp_citations, aafp_citation_raw, aafp_question_icd10
- aafp_questions blueprint column added to skill doc (100% filled)
- Relationship diagram updated to include AAFP branch
- Both skill locations synced (skills_abilities/ + 00_database/schemas/)

### 4. DEFERRED-B deferred further — update_citation_trends.py
- Confirmed built and idempotent (full DELETE + re-insert)
- article_citation_trend already has 1,740 rows through ART-1937
- 49 new AAFP articles (ART-1938–1986) not yet in qid_art_xref (no PDFs yet)
- **Best to run AFTER DEFERRED-A (PDF download + backfill)**

### 5. aafp_questions flattened (flatten_aafp_questions.py — NEW)
- `aafp_explanations` merged into `aafp_questions`: correct_letter, correct_text, explanation, explanation_keywords (1,221/1,221 ✓)
- `aafp_explanations` table dropped
- `aafp_questions.subcategory` dropped (legacy noise — made up in early analysis)
- `questions.subcategory` dropped (same reason — 261 NULLs on 2018-2019, meaningless across the board)
- `questions.topic_label` dropped (440/1629 filled, 2018-2019 only, never extended, superseded by concept_tags)
- Script: `02_module.2_processor/scripts/flatten_aafp_questions.py`

### 6. aafp_questions.blueprint — COMPLETE (blueprint_api_classifier_aafp.py — NEW)
- Batch API classifier: same rubric + 19 gold-standard few-shot examples as ITE v2
- 1,221/1,221 classified, 0 REVIEW items, 91.6% High confidence
- State file: `02_module.2_processor/source/blueprint_aafp_batch_state.json`
- Output xlsx: `02_module.2_processor/source/blueprint_classifications_aafp.xlsx`
- Written to DB via `write_blueprint_aafp_to_db.py --live`
- Scripts: `blueprint_api_classifier_aafp.py` (--wait/--submit/--poll/--retrieve), `write_blueprint_aafp_to_db.py`

### 7. SQLite locking issue documented
- Root cause: sandbox (Linux) and Windows run in different NTFS permission contexts
- WAL/-shm files created by Windows writes not accessible from sandbox
- **Rule:** DB writes always from Windows. Sandbox reads only, with Windows DB tools closed.
- Fix needed: add `timeout=10` + context managers to all scripts (deferred)

---

## DB State (current as of BATON 026)

| Item | Value |
|------|-------|
| DB articles | 1,985 |
| DB questions (ITE) | 1,629 (2018–2025) |
| questions.blueprint | 1,629/1,629 (100%) |
| questions.subcategory | DROPPED |
| questions.topic_label | DROPPED |
| DB questions (AAFP BRQ) | 1,221 |
| aafp_questions.blueprint | 1,221/1,221 (100%) — NEW this session |
| aafp_questions.subcategory | DROPPED |
| aafp_questions schema | Flattened — correct_letter, correct_text, explanation, explanation_keywords merged in |
| aafp_explanations table | DROPPED (data merged into aafp_questions) |
| aafp_question_icd10 | 4,240 rows |
| qid_art_xref | 2,470 |
| aafp_qid_art_xref | 864 rows |
| PDFs | 404 (49 new articles awaiting download) |
| Next ART-ID | ART-1987 |

### Blueprint Distribution (side-by-side QC)

| Blueprint | AAFP (n=1,221) | ITE (n=1,629) |
|---|---|---|
| Acute Care and Diagnosis | 588 (48.2%) | 709 (43.5%) |
| Chronic Care Management | 253 (20.7%) | 403 (24.7%) |
| Emergent and Urgent Care | 166 (13.6%) | 214 (13.1%) |
| Preventive Care | 140 (11.5%) | 206 (12.6%) |
| Foundations of Care | 74 (6.1%) | 97 (6.0%) |

> AAFP runs ~5pts higher Acute, ~4pts lower Chronic vs ITE. Rubric-consistent — reflects content difference (AAFP BRQ leans toward diagnosis/presentation; ITE has more chronic disease management). Emergent and Foundations nearly identical across corpora.

---

## Deferred Flags

| Flag | Description | Priority |
|------|-------------|----------|
| DEFERRED-A | PDF download: 49 new AAFP articles ART-1938–1986 | High |
| DEFERRED-B | `update_citation_trends.py` — run AFTER DEFERRED-A | Medium |
| DEFERRED-C | AAFP vs ITE trend comparison — deeper analysis pending | Medium |
| DEFERRED-D | 229 citation gap articles (88 AFP batch-downloadable) | Medium |
| DEFERRED-E | Interactive vector dashboard | Low |
| DEFERRED-F | Intelligence 2.0 Layer 2 (PubMed MCP article_currency) | Medium |
| FLAG-B | stem_keywords: AAFP/ITE unified but context not identical | Low |
| CLINICAL-PATHWAY | Extend clinical_pathways to ART-1398–1985 + AAFP questions | Medium |
| SQLITE-LOCK | Add timeout=10 + context managers to all scripts | Low |

---

## Next Steps (priority order)

### 1. Git commit (Windows) — overdue
```
git add CLAUDE.md _index.md
git add BATON_active_026_20260330_aafp_blueprint_unified.md
git add baton_archive/   (archive BATONs 025)
git add 02_module.2_processor/scripts/flatten_aafp_questions.py
git add 02_module.2_processor/scripts/blueprint_api_classifier_aafp.py
git add 02_module.2_processor/scripts/write_blueprint_aafp_to_db.py
git add 02_module.2_processor/source/blueprint_classifications_aafp.xlsx
git add 02_module.2_processor/source/blueprint_aafp_batch_state.json
git add skills_abilities/ite-data-context-skill/
git add 00_database/schemas/ite-data-context-skill/
git commit -m "BATON 026: AAFP blueprint complete + schema cleanup (subcategory/topic_label dropped)"
```

### 2. PDF download — 49 new AAFP articles (DEFERRED-A)
```
python 01_module.1_warehouse\scripts\maintain\download_aafp_acquisitions.py
python 01_module.1_warehouse\scripts\maintain\backfill_new_article_metadata.py --art-id-min 1938
```

### 3. update_citation_trends.py (DEFERRED-B — run after step 2)
```
python 01_module.1_warehouse\scripts\maintain\update_citation_trends.py --report
```

### 4. Clinical pathway update (CLINICAL-PATHWAY)
- Extend clinical_pathways to ART-1398–1985 (coverage gap)
- Design AAFP question → pathway linkage (aafp_question_icd10 exists; pathway_role missing)

### 5. AAFP vs ITE trend comparison (DEFERRED-C)
- Both corpora now schema-parallel: blueprint + body_system + concept_tags + ICD-10
- Dashboard ready; deeper analysis pending

### 6. 229 citation gap articles (DEFERRED-D)
- 88 AFP batch-downloadable from null_clean_ref_missing_articles_20260326.csv

---

## Files Changed This Session

| File | Action |
|------|--------|
| `flatten_aafp_questions.py` | NEW — merges aafp_explanations, drops subcategory |
| `blueprint_api_classifier_aafp.py` | NEW — Batch API classifier (--wait/--submit/--poll/--retrieve) |
| `write_blueprint_aafp_to_db.py` | NEW — writes blueprint xlsx to aafp_questions |
| `blueprint_classifications_aafp.xlsx` | NEW — 1,221 rows, 0 REVIEW items |
| `blueprint_aafp_batch_state.json` | NEW — batch state (batch_id, status) |
| `aafp_questions` (DB) | MODIFIED — 4 columns added, subcategory dropped, blueprint added |
| `aafp_explanations` (DB) | DROPPED |
| `questions` (DB) | MODIFIED — subcategory + topic_label dropped |
| `skills_abilities/ite-data-context-skill/` | UPDATED — path, counts, AAFP schema, blueprint |
| `00_database/schemas/ite-data-context-skill/` | SYNCED from skills_abilities/ |
| `CLAUDE.md` | Needs update (Active State table) |
| `BATON_active_026_*.md` | This file |
