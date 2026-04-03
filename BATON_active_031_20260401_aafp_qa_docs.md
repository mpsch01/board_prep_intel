# BATON 031 — AAFP Q&A Document Generation
**Date:** 2026-04-01
**Session:** AAFP-ITE relationship export + Q&A document build (File 3 + File 1)
**Status:** Two Q&A docs delivered to resident. QUESTION-DIST-001 still open.
**Replaces:** BATON_active_030_20260401_analyzer_v3_smoke_test.md

---

## What Was Done This Session

### 1. `export_aafp_ite_relationships.py` — RUN + VERIFIED
**Script:** `03_module.3_analyst/scripts/export_aafp_ite_relationships.py`
**Status:** Ran clean. 4 CSVs written to `00_database/readable_db_files/`.

| Output File | Rows | Description |
|-------------|------|-------------|
| `aafp_ite_semantic_similarity.csv` | 34 | AAFP questions with ite_nearest_dist < 0.30 AND linked articles |
| `aafp_ite_question_level_citation_overlap_detail.csv` | 1,555 | One row per AAFP→article→ITE triplet (research layer) |
| `aafp_ite_question_level_citation_overlap_summary.csv` | 595 | One row per AAFP question with ITE overlap count (distributable) |
| `aafp_ite_semantic_and_citation_intersection.csv` | 0 | Empty — STRICT_THRESHOLD 0.22 is below min observed dist (0.237); File 1 already IS the intersection |

**Key finding:** File 3 summary = 595/1,221 AAFP questions (48.7%) share at least one article with an ITE question. Top question (AAFP-50403) overlaps 13 ITE questions via 5 shared articles.

**File 4 verdict:** Redundant. File 1 (semantic_similarity) already requires linked articles via JOIN to aafp_qid_art_xref. File 4 adds nothing — keep as-is, use File 1 instead.

### 2. `word_doc_defaults.py` — COMMITTED TO AUTO-MEMORY
**Script:** `03_module.3_analyst/scripts/word_doc_defaults.py`
St. Luke's / ITE Intelligence color scheme, Aptos font, US Letter. All future python-docx scripts must import this module. Saved to `.auto-memory/reference_word_doc_defaults.md`.

### 3. `build_aafp_qa.py` — NEW (File 3 Q&A document builder)
**Script:** `03_module.3_analyst/scripts/build_aafp_qa.py`
**Output:** `03_module.3_analyst/reports/AAFP_BRQ_ITE_Overlap_QA_v2.docx`

Builds Q&A Word doc from all 595 AAFP questions with ITE citation overlap (File 3), sorted by overlap count descending. Format: cover stats → 25-question navigation sections → badge (overlap tier + quiz + body system) → stem → choices A–E (no pre-marking) → CORRECT ANSWER (green text) → Explanation. `keep_with_next` chained through question block. Uses `word_doc_defaults.py`.

**Stats:** 595 questions | 15 High-Yield (8+ ITE overlap) | 89 Moderate (4–7 ITE overlap)

**Design decision:** No green highlighting on correct choice letter — resident uses document as dual exam/study guide (covers answer while reading choices).

### 4. `build_aafp_qa_file1.py` — NEW (File 1 Q&A document builder)
**Script:** `03_module.3_analyst/scripts/build_aafp_qa_file1.py`
**Output:** `03_module.3_analyst/reports/AAFP_BRQ_NearDuplicate_QA.docx`

Builds Q&A Word doc from 34 AAFP near-duplicate questions (File 1 — dist < 0.30 with linked articles), sorted by distance ASC (closest first). Same Q&A format plus: navy-bordered companion block at bottom of each question showing the matched ITE vignette stem for side-by-side comparison. Distance badge: gold = near-duplicate (<0.25), blue = strong match (0.25–0.27), dark = semantic match (0.27–0.30).

**Stats:** 34 questions | 1 Near-Duplicate (dist 0.237) | 9 Strong Match | 24 Semantic Match

---

## DB State (unchanged from BATON 030)

| Table | Rows | Notes |
|-------|------|-------|
| articles | 1,985 | ART-0001 → ART-1986; next = ART-1987 |
| questions (ITE) | 1,629 | blueprint 100% |
| questions (AAFP) | 1,221 | blueprint 100% |
| qid_art_xref | 2,470 | |
| aafp_qid_art_xref | 864 | |
| article_icd10 | 4,137 | |
| question_icd10 | 5,284 | |
| aafp_question_icd10 | 4,753 | |
| clinical_pathways | 4,020 | |
| icd10_vec | 2,219 | |
| article_icd10_vec | 1,674 | ✅ rebuilt BATON 030 |
| question_icd10_vec | 2,733 | ✅ rebuilt BATON 030 |
| pubmed_pmid_cache | 344 | |
| PDFs | 404 | 49 AAFP articles still awaiting download |
| Next ART-ID | ART-1987 | |
| Git | main, `9817449` | needs commit — multiple sessions of changes |

---

## Deferred Flags

| Flag | Description | Priority |
|------|-------------|----------|
| QUESTION-DIST-001 | Practice question distribution bug — all targeting Acute Care only | **High** — fix before faculty demo |
| PRESENTATION | Faculty meeting PPTX + one-pager — blocked by QUESTION-DIST-001 | **High** |
| DEFERRED-A | PDF download: 49 AAFP articles ART-1938–1986 | High |
| DEFERRED-B | `update_citation_trends.py` — run AFTER DEFERRED-A | Medium |
| DEFERRED-C | AAFP vs ITE trend comparison | Medium |
| DEFERRED-D | 229 citation gap articles (88 AFP batch-downloadable) | Medium |
| DEFERRED-E | Interactive vector dashboard | Low |
| DEFERRED-F | Intelligence 2.0 Layer 2 — `article_currency` table (344 PMIDs cached) | Medium |
| Q-VEC-GAP | Fill question vector gaps: 440 ITE (2018–2019) + 1,221 AAFP → question_vec | Medium |

---

## Next Steps (priority order)

### 1. Fix QUESTION-DIST-001 (before faculty demo)
Debug `BODYSYSTEM_PDF_TO_DB` and `BLUEPRINT_PDF_TO_DB` maps in `ite_analyzer_v3.py`.
Check actual `questions.body_system_merged` values vs. what the PDF score report labels produce.

### 2. Git commit — changes across BATON 029–031
```
git add 03_module.3_analyst/scripts/ite_analyzer_v3.py
git add 03_module.3_analyst/scripts/ite_analyze_v2.py
git add 03_module.3_analyst/scripts/ite_analyzer_v2.py
git add 03_module.3_analyst/scripts/ite_report_builder_v2.js
git add 03_module.3_analyst/scripts/export_aafp_ite_relationships.py
git add 03_module.3_analyst/scripts/word_doc_defaults.py
git add 03_module.3_analyst/scripts/build_aafp_qa.py
git add 03_module.3_analyst/scripts/build_aafp_qa_file1.py
git commit -m "feat: ite_analyzer_v3 + AAFP Q&A builders + word_doc_defaults template"
```

### 3. Faculty Meeting Presentation
After QUESTION-DIST-001 is fixed:
- PPTX deck: architecture walkthrough + demo slides
- One-pager: system overview for non-technical audience
- Demo: run Hopkins report live, walk through DOCX output

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
| `export_aafp_ite_relationships.py` | RUN — 4 CSVs generated in `00_database/readable_db_files/` |
| `word_doc_defaults.py` | NEW (brought in by Mikey) — committed to auto-memory |
| `build_aafp_qa.py` | NEW — File 3 Q&A builder (595 AAFP questions, citation overlap) |
| `build_aafp_qa_file1.py` | NEW — File 1 Q&A builder (34 near-duplicate questions, semantic match) |
| `reports/AAFP_BRQ_ITE_Overlap_QA_v2.docx` | NEW — delivered to resident |
| `reports/AAFP_BRQ_NearDuplicate_QA.docx` | NEW — delivered to resident |
| `00_database/readable_db_files/aafp_ite_*.csv` | NEW — 4 CSVs (34 / 1,555 / 595 / 0 rows) |
| `BATON_active_031_*.md` | This file |
