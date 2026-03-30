# BATON 025 — 2020-2023 Blueprint Rewritten (v2 Classifier)
**Date:** 2026-03-30
**Session:** blueprint_api_classifier_v2 built + run + written to DB
**Status:** blueprint column 100% filled (1,629/1,629) — v2 labels for 2020-2023
**Replaces:** BATON_active_024_20260329_blueprint_complete.md

---

## What Was Done This Session

### Context
BATON 024 had already written 2018-2023 blueprint labels using `blueprint_api_classifier.py` + `blueprint_emergent_pass.py`.
This session Mikey reviewed an alternative model's forced-quota output (exactly 70/50/40/30/10 per year, compromised labels), prompted building a second-generation classifier.

### blueprint_api_classifier_v2.py (NEW)
- **File:** `02_module.2_processor/scripts/blueprint_api_classifier_v2.py`
- Real batching: 10 questions per API call (80 calls for 800 questions, ~$3-4)
- 19 gold-standard few-shot examples (from 2024/2025 ITE official tables)
- Full clinical-job rubric in system prompt (EXPLANATION.txt methodology)
- Checkpoint/resume support (`--start-row`), JSON array response
- Output columns: question_id, year, question_number, blueprint_category, confidence, justification, question_stem
- **Source:** `02_module.2_processor/source/blueprint_classifications_v2.xlsx` (800 rows)
- 4 manual corrections applied post-run:
  - Q2020-002: Emergent → Preventive (nursing home influenza prophylaxis)
  - Q2020-025: Acute → Foundations (anorexia HPA axis - standalone knowledge)
  - Q2020-065: Acute → Foundations (food allergens - pure factual recall)
  - Q2023-696: Emergent → Acute (kidney stone - initial workup of new complaint)

### write_blueprint_to_db.py (NEW)
- **File:** `02_module.2_processor/scripts/write_blueprint_to_db.py`
- Key fix resolved: `question_number` column does not exist — table uses `qid` as key
- Maps xlsx sequential QIDs (Q2020-001→800) to DB QIDs (QID-2020-0001 format)
- Dry-run: 794/800 matched (6 permanently missing from DB — see below)
- 794/794 stem verification: ✓ exact text match on all matched rows
- **Live run: 794 rows updated, 6 skipped**

### 6 Permanently Missing QIDs (documented)
These questions do not exist in the DB — not a mapping error:
| xlsx QID | DB QID attempted |
|----------|-----------------|
| Q2020-134 | QID-2020-0134 |
| Q2020-138 | QID-2020-0138 |
| Q2021-250 | QID-2021-0050 |
| Q2021-368 | QID-2021-0168 |
| Q2022-575 | QID-2022-0175 |
| Q2023-604 | QID-2023-0004 |

---

## DB State (current as of BATON 025)

| Item | Value |
|------|-------|
| DB articles | 1,985 |
| DB questions (ITE) | 1,629 (2018–2025) |
| questions.blueprint | **1,629/1,629 (100%)** |
| DB questions (AAFP BRQ) | 1,221 |
| aafp_questions.concept_tags | 1,221/1,221 (100%) |
| aafp_questions.subcategory | 1,221/1,221 (100%) |
| aafp_question_icd10 | 4,240 rows — relevance normalized |
| qid_art_xref | 2,470 |
| aafp_qid_art_xref | 864 rows (643 unique questions, 52.7%) |
| PDFs | 404 (49 new articles awaiting PDF download) |
| Next ART-ID | ART-1987 |

### questions.blueprint Distribution (all 8 years)

| Year | Total | Acute | Chronic | Emergent | Preventive | Foundations | Method |
|------|-------|-------|---------|----------|------------|-------------|--------|
| 2018 | 240 | — | — | — | — | — | v1 classifier |
| 2019 | 200 | — | — | — | — | — | v1 classifier |
| 2020 | 198 | 90 (45.5%) | 41 (20.7%) | 20 (10.1%) | 33 (16.7%) | 14 (7.1%) | v2 classifier |
| 2021 | 198 | 101 (51.0%) | 43 (21.7%) | 21 (10.6%) | 22 (11.1%) | 11 (5.6%) | v2 classifier |
| 2022 | 199 | 100 (50.3%) | 47 (23.6%) | 14 (7.0%) | 24 (12.1%) | 14 (7.0%) | v2 classifier |
| 2023 | 199 | 95 (47.7%) | 41 (20.6%) | 27 (13.6%) | 22 (11.1%) | 14 (7.0%) | v2 classifier |
| 2024 | 195 | — | — | — | — | — | Gold Standard |
| 2025 | 200 | — | — | — | — | — | Gold Standard |

> **Methodology note:** 2018-2019 used v1 (sequential, emergent second-pass). 2020-2023 use v2 (batched, gold-standard few-shot). 2024-2025 are ABFM official. Do not compare year-over-year distributions without accounting for methodology shift.

> **Acute distribution note:** v2 classifies Acute at ~47-51% vs ABFM's 35% target. This reflects the clinical-job rubric (new presentation = Acute by default). Not an error — the pre-2024 ABFM distribution is unknown. Flag in trend analysis.

---

## Deferred Flags (carried forward)

| Flag | Description | Priority |
|------|-------------|----------|
| DEFERRED-A | PDF download: 49 new articles ART-1938–1986 | High |
| DEFERRED-B | `update_citation_trends.py` → `article_citation_trend` table | Medium |
| DEFERRED-C | AAFP vs ITE trend comparison — dashboard built; deeper analysis pending | Medium |
| DEFERRED-D | 229 citation gap articles (88 AFP batch-downloadable) | Medium |
| DEFERRED-E | Interactive vector dashboard | Low |
| DEFERRED-F | Intelligence 2.0 Layer 2 (PubMed MCP article_currency) | Medium |
| FLAG-A | ITE subcategory split: 2018–2019 disease-specific vs 2020–2025 canonical | Medium |
| FLAG-B | stem_keywords: AAFP/ITE unified but context not identical — filter in trend analysis | Low |
| FLAG-C | `ite-data-context-skill` stale (old path, old counts, no AAFP schema) | Medium |
| FLAG-D | Dashboard subcategory constants unverified | Medium |

---

## Next Steps (priority order)

### 1. Git commit (Windows) — overdue
```
git add CLAUDE.md _index.md
git add BATON_active_025_20260330_2020_2023_blueprint_v2.md
git add baton_archive/
git add 02_module.2_processor/scripts/blueprint_api_classifier_v2.py
git add 02_module.2_processor/scripts/write_blueprint_to_db.py
git add 02_module.2_processor/source/blueprint_classifications_v2.xlsx
git add aafp_vs_ite_comparison_dashboard.html
git commit -m "BATONs 021-024: AAFP enrichment + dashboard + blueprint v1/v2 complete"
# Archive BATONs 020-024 → baton_archive/ (git rm from Windows)
```

### 2. QC — verify 2018/2019 v1 blueprint distribution
```sql
SELECT exam_year, blueprint, COUNT(*) as n
FROM questions
WHERE exam_year IN (2018, 2019)
GROUP BY exam_year, blueprint
ORDER BY exam_year, blueprint;
```
Confirm v1 labels are populated and distributions are reasonable.

### 3. PDF download — 49 new AAFP articles (DEFERRED-A)
```
python 01_module.1_warehouse\scripts\maintain\download_aafp_acquisitions.py
python 01_module.1_warehouse\scripts\maintain\backfill_new_article_metadata.py --art-id-min 1938
```

### 4. update_citation_trends.py (DEFERRED-B)
- Confirmed built in M1/maintain/
- Populates `article_citation_trend` table

### 5. Verify dashboard subcategory constants (FLAG-D)
```sql
SELECT subcategory, COUNT(*) FROM aafp_questions GROUP BY subcategory ORDER BY COUNT(*) DESC;
```

### 6. Update ite-data-context-skill (FLAG-C)
- Fix path, update counts, add AAFP schemas

### 7. 229 citation gap articles (DEFERRED-D)
- 88 AFP batch-downloadable from `null_clean_ref_missing_articles_20260326.csv`

### 8. Intelligence 2.0 Layer 2 — PubMed currency (DEFERRED-F)

---

## Files Changed This Session

| File | Action |
|------|--------|
| `blueprint_api_classifier_v2.py` | NEW — batched classifier, 19 few-shot examples |
| `blueprint_classifications_v2.xlsx` | NEW — 800 rows, 4 manual corrections |
| `write_blueprint_to_db.py` | NEW — QID-based DB writer, fixed column name bug |
| `questions.blueprint` (DB) | UPDATED — 794 rows overwritten for 2020-2023 (v2 labels) |
| `CLAUDE.md` | UPDATED this session |
| `BATON_active_025_*.md` | This file |
