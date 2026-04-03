---
name: project_overhaul_state
description: Current PROJECT_OVERHAUL state: BATON 031, AAFP Q&A docs delivered, export pipeline complete, QUESTION-DIST-001 still open
type: project
---

**Project:** ABFM ITE Intelligence System (Family Medicine board exam knowledge base)
**Root (Windows):** `C:\Users\mpsch\Desktop\claude_knowledge\00_#PROJECT_OVERHAUL\`
**Active BATON:** `BATON_active_031_20260401_aafp_qa_docs.md`
**Git:** `main`, latest committed `9817449` — commit pending (8 files across BATON 029–031)

---

## Current Phase: AAFP Q&A Documents Delivered + Export Pipeline Complete

**BATON 028 (2026-03-30):** clinical_pathways rebuilt — 4,020 rows, blueprint-based signal, both banks, full ART-0002–ART-1985 coverage.

**BATON 029 (2026-03-31):** ICD-10 backfills complete — article_icd10 to 4,137 rows (+AAFP), aafp_question_icd10 normalized + related cap applied (4,753 rows), question_icd10 built (5,284 rows, 92.8% ITE coverage). pubmed_pmid_cache seeded (344 rows).

**BATON 030 (2026-04-01):**
- ICD-10 vector rebuild: `article_icd10_vec` + `question_icd10_vec` rebuilt via `--derive` (zero API cost, weighted avg)
- `ite_analyzer_v3.py` BUILT — 9 analysis layers, 3-tier practice question cascade, dual bank (ITE + AAFP BRQ)
- Smoke test PASS: Hopkins 2025, 65.4% (125/191), both DOCXs generated
- Bug flagged: **QUESTION-DIST-001** — all 20 practice questions from "Acute Care" only. Fix before demo.

**BATON 031 (2026-04-01):**
- `export_aafp_ite_relationships.py` run — 4 CSVs in `readable_db_files/`: 34 / 1,555 / 595 / 0 rows
- `word_doc_defaults.py` committed to auto-memory — St. Luke's styling, MUST import in all future python-docx scripts
- `build_aafp_qa.py` BUILT — File 3 Q&A doc, 595 AAFP questions with ITE citation overlap, delivered to resident
- `build_aafp_qa_file1.py` BUILT — File 1 Q&A doc, 34 near-duplicate AAFP questions with matched ITE companion blocks
- Key design: no `is_correct` marking on choices (cover-friendly exam/study guide dual use); `keep_with_next` chained on question blocks
- File 4 verdict: redundant — File 1 already IS the semantic+citation intersection (its JOIN to aafp_qid_art_xref already requires linked articles; STRICT_THRESHOLD 0.22 below min observed dist 0.237)

---

## Module State

| Module | Location | Scripts | Status |
|--------|----------|---------|--------|
| M1 Warehouse | `01_module.1_warehouse/` | 9 build + 16 maintain + aafp_brq/scraper | Stable |
| M2 Processor | `02_module.2_processor/scripts/` | 66 Python + 6 JS + 1 config JSON + 4 Windows | Stable |
| M3 Analyst | `03_module.3_analyst/scripts/` | **9 Python** + 1 JS + 2 JSON config | +4 scripts BATON 031 |
| DB | `00_database/db/ite_intelligence.db` | Source of truth | 1,985 articles, 1,629 ITE Q, 1,221 AAFP Q |

---

## Key Numbers (as of BATON 031, 2026-04-01)

- **DB articles:** 1,985 (next: ART-1987)
- **DB questions (ITE):** 1,629 (2018–2025); blueprint 100%; subcategory + topic_label DROPPED
- **DB questions (AAFP BRQ):** 1,221; blueprint 100%; flattened; subcategory DROPPED
- **article_icd10:** 4,137 rows (+AAFP backfill)
- **question_icd10:** 5,284 rows (92.8% ITE coverage)
- **aafp_question_icd10:** 4,753 rows (normalized, related cap applied)
- **icd10_vec:** 2,219 rows (OpenAI text-embedding-3-small 1536d)
- **article_icd10_vec:** 1,674 rows (rebuilt 2026-04-01)
- **question_icd10_vec:** 2,733 rows (rebuilt 2026-04-01)
- **clinical_pathways:** 4,020 rows (rebuilt 2026-03-31, blueprint-based, both banks)
- **pubmed_pmid_cache:** 344 rows (Layer 2 seed)
- **PDFs:** 404 across 4 tiers (49 AAFP articles awaiting download)
- **M3 scripts:** 9 Python + 1 JS + 2 JSON config
- **AAFP↔ITE CSVs (readable_db_files/):** 4 files (34 / 1,555 / 595 / 0 rows)
- **AAFP Q&A DOCXs (M3/reports/):** 2 — `AAFP_BRQ_ITE_Overlap_QA_v2.docx` (595 Q) + `AAFP_BRQ_NearDuplicate_QA.docx` (34 Q)

---

## Active Deferred Flags

| Flag | Description | Priority |
|------|-------------|----------|
| QUESTION-DIST-001 | Practice question distribution bug — body system dims return 0 candidates, all from Acute Care | **HIGH — fix before demo** |
| PRESENTATION | Faculty meeting PPTX + one-pager — after QUESTION-DIST-001 fixed | HIGH |
| DEFERRED-A | PDF download: 49 new articles ART-1938–1986 | HIGH |
| DEFERRED-B | `update_citation_trends.py` — run after DEFERRED-A | MEDIUM |
| DEFERRED-C | AAFP vs ITE trend comparison | MEDIUM |
| DEFERRED-D | 229 citation gap articles (88 AFP batch-downloadable) | MEDIUM |
| DEFERRED-E | Interactive vector dashboard | LOW |
| DEFERRED-F | Intelligence 2.0 Layer 2 (`article_currency` via PubMed, 344 PMIDs cached) | MEDIUM |
| Q-VEC-GAP | Fill question_vec: 440 ITE (2018–2019) + 1,221 AAFP | MEDIUM |

**Closed flags:** ICD10-SYMMETRY ✅, CLINICAL-PATHWAY ✅, Q-ICD10-VEC ✅, ARTICLE-ICD10-VEC ✅

---

## Next Steps (priority order)

1. **Fix QUESTION-DIST-001** — debug `BODYSYSTEM_PDF_TO_DB` map vs actual `questions.body_system_merged` values
2. **Git commit** — 8 files: `ite_analyzer_v3.py`, `ite_analyze_v2.py`, `ite_analyzer_v2.py`, `ite_report_builder_v2.js`, `export_aafp_ite_relationships.py`, `word_doc_defaults.py`, `build_aafp_qa.py`, `build_aafp_qa_file1.py`
3. **Faculty meeting presentation** — PPTX + one-pager (after bug fix)
4. **PDF download** (DEFERRED-A) — `download_aafp_acquisitions.py` → `backfill_new_article_metadata.py --art-id-min 1938`
5. **Intelligence 2.0 Layer 2** — `article_currency` table (344 PMIDs ready)
