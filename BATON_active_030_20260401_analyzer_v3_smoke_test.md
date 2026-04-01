# BATON 030 — ite_analyzer_v3 Smoke Test Complete + Bugs Fixed
**Date:** 2026-04-01
**Session:** ite_analyzer_v3 smoke test + entry point patching
**Status:** v3 pipeline runs end-to-end. Return code 0. Both DOCXs generated. One known bug flagged (question distribution).
**Replaces:** BATON_active_029_20260331_clinical_pathways_v2.md

---

## What Was Done This Session

### 1. ICD-10 Vector Rebuild — COMPLETED (from BATON 029 Next Steps)
`build_icd10_embeddings.py --derive` was run at the start of session. Completed successfully.
- `article_icd10_vec`: rebuilt (was stale)
- `question_icd10_vec`: rebuilt (was stale)
Zero API cost — weighted average of existing `icd10_vec` embeddings.

### 2. `ite_analyzer_v3.py` — NEW (built last session, smoke tested this session)

**Script:** `03_module.3_analyst/scripts/ite_analyzer_v3.py`
**Status:** Syntax verified. Smoke test PASS (return code 0). All 9 analysis layers populate.

**9 analysis layers:**
1. `performance` — blueprint + body system + cross_tab + weak_areas
2. `icd10_weakness_map` — ICD-10 clusters for weak dimensions
3. `concept_clustering` — top_diagnoses, top_drugs, top_guidelines, recurring_diagnoses/drugs
4. `pathway_gap_map` — clinical_pathways roles for weak ICD-10 codes
5. `benchmark_comparison` — PGY-level national benchmark
6. `year_over_year` — multi-year trend (if prior scores available)
7. `body_system_blueprint_matrix` — cross-tab heatmap
8. `priority_list` — ranked weak dimensions
9. `practice_questions` — 20 questions from Tier 1/2/3 (ITE + AAFP)

**Key design:**
- Relevance scoring: `TIER_WEIGHT[tier] * priority_score + bonuses` — global ranking across both banks
- Tier 1: direct match (blueprint/body_system/cross_tab)
- Tier 2: ICD-10 sibling via `question_icd10` / `aafp_question_icd10`
- Tier 3: vector similarity via `question_icd10_vec`
- AAFP source label: `"AAFP BRQ"`, ITE: `"ITE {exam_year}"`

### 3. Bugs Fixed During Smoke Test (5 fixes total)

| Fix | File | Issue | Resolution |
|-----|------|-------|------------|
| Entry point import crash | `ite_analyze_v2.py` | `from ite_analyzer import ...` — v1 module gone | Wrapped in try/except; inline `export_analysis` fallback |
| `_not_in()` AAFP col | `ite_analyzer_v3.py` | `q.qid` doesn't exist on `aafp_questions` | Added `col` parameter; AAFP callers pass `"q.aafp_qid"` |
| `_not_in()` vec table | `ite_analyzer_v3.py` | `q.qid` used in `question_icd10_vec` scan (no alias) | Tier 3 uses `col="qid"` (bare, no table prefix) |
| Unicode print crash | `ite_analyze_v2.py` | `⚠ ✓` emoji choke Windows cp1252 console | Replaced all emoji with ASCII equivalents |
| `subcatAnalysis` undefined | `ite_report_builder_v2.js` | v2-era variable referenced but never assigned in v3 path | Added definition: `const subcatAnalysis = data.plugins?.subcategory_decomposition \|\| null;` |

### 4. `ite_analyzer_v2.py` — DEPRECATED header added (last session)

Header added to `ite_analyzer_v2.py`:
```python
# DEPRECATED — superseded by ite_analyzer_v3.py
# subcategory column was dropped → Layer 2 will crash
# AAFP question bank not connected
```
Still importable via `--v2-only` flag for reference.

### 5. `ite_analyze_v2.py` entry point — updated (last session + this session patches)

Now routes to `analyze_v3` by default. Flags:
- (default): v3 analyzer → Node.js report builder v2
- `--v2-only`: deprecated v2 analyzer path
- `--v1-only`: full v1 fallback (if v1 modules exist)

### 6. Smoke Test Results — Hopkins 2025

**Resident:** Oceana Hopkins, M.D.  
**Score:** 65.4% (125/191), Exam Year 2025, PGY2

**Blueprint weak areas:** Acute Care (55.9%), Emergent/Urgent (61.1%), Foundations (66.7%), Preventive (69.0%)  
**Body system weak areas:** Injuries/MSK (54.5%), Respiratory (50.0%), Psychiatric (66.7%), Sexual & Repro (66.7%)

**Output files (in `03_module.3_analyst/reports/test_v3/`):**
- `ITE_2025_v3_Analysis_Oceana_Hopkins.docx` (43,817 bytes) ✅
- `ITE_2025_v3_Exam_Oceana_Hopkins.docx` (19,804 bytes) ✅
- `analysis_v2.json` (103,038 bytes) ✅

---

## Known Bug — QUESTION-DIST-001

**Description:** All 20 practice questions targeted "Acute Care" dimension only. Body system dimensions (Injuries/MSK, Respiratory) and other blueprints (Emergent/Urgent, Foundations, Preventive) returned 0 candidates from Tier 1.

**Symptom from Node.js:** `Warnings: "Injuries/Musculoskeletal" (0 questions), "Respiratory" (0 questions), "Emergent/Urgent" (0 questions), "Foundations" (0 questions), "Preventive" (0 questions)`

**Likely cause:** Body system PDF names may not map to DB `body_system_merged` values via `BODYSYSTEM_PDF_TO_DB`, OR the `_build_where` body_system clause is not matching real DB rows. The first dimension that DOES have matches (Acute Care) fills all 20 slots.

**Priority:** Medium — pipeline is functional, but question diversity is poor for affected residents. Fix before faculty meeting demo.

**Debug approach:**
```python
# Quick check: run in python console against the DB
# Does "Injuries/Musculoskeletal" match any questions.body_system_merged values?
import sqlite3
conn = sqlite3.connect(r"00_database\db\ite_intelligence.db")
print(conn.execute("SELECT DISTINCT body_system_merged FROM questions WHERE body_system_merged LIKE '%Injur%'").fetchall())
print(conn.execute("SELECT DISTINCT body_system FROM aafp_questions WHERE body_system LIKE '%Injur%'").fetchall())
```

---

## DB State (as of BATON 030)

| Table | Rows | Notes |
|-------|------|-------|
| articles | 1,985 | ART-0001 → ART-1986; next = ART-1987 |
| questions (ITE) | 1,629 | blueprint 100%, subcategory DROPPED |
| questions (AAFP) | 1,221 | blueprint 100% |
| qid_art_xref | 2,470 | |
| aafp_qid_art_xref | 864 | |
| article_icd10 | 4,137 | |
| question_icd10 | 5,284 | 92.8% ITE coverage |
| aafp_question_icd10 | 4,753 | |
| pubmed_pmid_cache | 344 | Layer 2 seed |
| icd10_vec | 2,219 | |
| article_icd10_vec | 1,674 | ✅ rebuilt this session |
| question_icd10_vec | 2,733 | ✅ rebuilt this session |
| clinical_pathways | 4,020 | blueprint-based, both banks |
| PDFs | 404 | 49 AAFP articles still awaiting download |
| Next ART-ID | ART-1987 | |
| Git | main, `9817449` | needs commit for this session's changes |

---

## Deferred Flags

| Flag | Description | Priority |
|------|-------------|----------|
| QUESTION-DIST-001 | Practice question distribution bug — all questions targeting single dimension | **High** — fix before demo |
| DEFERRED-A | PDF download: 49 new AAFP articles ART-1938–1986 | High |
| DEFERRED-B | `update_citation_trends.py` — run AFTER DEFERRED-A | Medium |
| DEFERRED-C | AAFP vs ITE trend comparison | Medium |
| DEFERRED-D | 229 citation gap articles (88 AFP batch-downloadable) | Medium |
| DEFERRED-E | Interactive vector dashboard | Low |
| DEFERRED-F | Intelligence 2.0 Layer 2 — `article_currency` table (344 PMIDs cached) | Medium |
| Q-ICD10-VEC | ✅ CLOSED this session | — |
| ARTICLE-ICD10-VEC | ✅ CLOSED this session | — |
| Q-VEC-GAP | Fill question vector gaps: 440 ITE (2018–2019) + 1,221 AAFP → question_vec | Medium |
| PRESENTATION | Faculty meeting presentation (PPTX + one-pager) — deferred until QUESTION-DIST-001 fixed | High |

**Closed this session:** Q-ICD10-VEC ✅, ARTICLE-ICD10-VEC ✅

---

## Next Steps (priority order)

### 1. Fix QUESTION-DIST-001 (before any demo)
Debug `BODYSYSTEM_PDF_TO_DB` and `BLUEPRINT_PDF_TO_DB` maps in `ite_analyzer_v3.py`.
Check what values actually exist in `questions.body_system_merged` vs what the PDF produces.
The fix is likely a mapping correction — 30 min job.

### 2. Git commit — changes from last two sessions
```
git add 03_module.3_analyst/scripts/ite_analyzer_v3.py
git add 03_module.3_analyst/scripts/ite_analyze_v2.py
git add 03_module.3_analyst/scripts/ite_analyzer_v2.py
git add 03_module.3_analyst/scripts/ite_report_builder_v2.js
git commit -m "feat: ite_analyzer_v3 + entry point patches + JS subcatAnalysis fix"
```

### 3. Faculty Meeting Presentation
After QUESTION-DIST-001 is fixed:
- PPTX deck: architecture walkthrough + demo slides
- One-pager: system overview for non-technical audience
- Demo: run Hopkins report live, walk through the DOCX output

### 4. PDF download (DEFERRED-A)
```
python 01_module.1_warehouse\scripts\maintain\download_aafp_acquisitions.py
python 01_module.1_warehouse\scripts\maintain\backfill_new_article_metadata.py --art-id-min 1938
```

### 5. Intelligence 2.0 Layer 2 — `article_currency`
Build `article_currency` table using 344 PMIDs in `pubmed_pmid_cache`.

---

## Files Changed This Session

| File | Action |
|------|--------|
| `ite_analyzer_v3.py` | NEW (built last session) + 3 bug fixes (col param, vec scan, tier2 AAFP) |
| `ite_analyze_v2.py` | UPDATED — v1 imports wrapped; emoji removed; default routes to v3 |
| `ite_analyzer_v2.py` | DEPRECATED header added |
| `ite_report_builder_v2.js` | PATCHED — subcatAnalysis defined; TIER_LABELS updated; concept/ICD/pathway sections |
| `reports/test_v3/` | NEW — smoke test outputs (3 files) |
| `BATON_active_030_*.md` | This file |
