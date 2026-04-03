---
name: project_overhaul_state
description: Current PROJECT_OVERHAUL state: BATON 032, QUESTION-DIST-001 fixed, faculty PPTX delivered, GIT-PENDING (8 scripts unstaged)
type: project
---

**Project:** ABFM ITE Intelligence System (Family Medicine board exam knowledge base)
**Root (Windows):** `C:\Users\mpsch\Desktop\claude_knowledge\00_#PROJECT_OVERHAUL\`
**Active BATON:** `BATON_active_032_20260402_question_dist_fix_faculty_pptx.md`
**Git:** `main`, latest committed `279049a` — 8 files unstaged (GIT-PENDING)

---

## Current Phase: QUESTION-DIST-001 Fixed + Faculty Presentation Delivered

**BATON 030 (2026-04-01):**
- ICD-10 vector rebuild: `article_icd10_vec` + `question_icd10_vec` rebuilt via `--derive` (zero API cost, weighted avg)
- `ite_analyzer_v3.py` BUILT — 9 analysis layers, 3-tier practice question cascade, dual bank (ITE + AAFP BRQ)
- Smoke test PASS: Hopkins 2025, 65.4% (125/191), both DOCXs generated
- Bug flagged: QUESTION-DIST-001 — all 20 practice questions from "Acute Care" only. Fix before demo.

**BATON 031 (2026-04-01):**
- `export_aafp_ite_relationships.py` run — 4 CSVs in `readable_db_files/`: 34 / 1,555 / 595 / 0 rows
- `word_doc_defaults.py` committed to auto-memory — St. Luke's styling, MUST import in all future python-docx scripts
- `build_aafp_qa.py` BUILT — File 3 Q&A doc, 595 AAFP questions with ITE citation overlap, delivered to resident
- `build_aafp_qa_file1.py` BUILT — File 1 Q&A doc, 34 near-duplicate AAFP questions with matched ITE companion blocks

**BATON 032 (2026-04-02):**
- **QUESTION-DIST-001 FIXED** — root cause: `_compute_relevance` used priority_score as raw multiplier. Acute Care score=33.6 vs ≤6.8 others → monopoly. Fix: dimension diversity cap in `match_practice_questions_v3()` — `ceil(target/n_active_dims)` per dimension (min 2), overflow fills remaining. Hopkins post-fix: 6 dims targeted, 3 per dim. CLOSED ✅
- **BATON 031 misattribution corrected:** bug was priority scoring monopoly, NOT `BODYSYSTEM_PDF_TO_DB` map (map was correct all along)
- **Faculty PPTX BUILT** — `build_faculty_pptx.js` → `ITE_Intelligence_FacultyPresentation_2025.pptx`, 7 slides, St. Luke's palette. QA pass: 4 issues fixed (emoji rendering × 2, slide 3 big-number, slide 5 bar chart post-fix data). PRESENTATION flag CLOSED ✅
- Git partial commit `279049a` — `ite_analyzer_v3.py` + BATON 031 archive. 8 more scripts still unstaged.

---

## Module State

| Module | Location | Scripts | Status |
|--------|----------|---------|--------|
| M1 Warehouse | `01_module.1_warehouse/` | 9 build + 16 maintain + aafp_brq/scraper | Stable |
| M2 Processor | `02_module.2_processor/scripts/` | 66 Python + 6 JS + 1 config JSON + 4 Windows | Stable |
| M3 Analyst | `03_module.3_analyst/scripts/` | **9 Python** + 2 JS + 2 JSON config | +1 JS BATON 032 |
| DB | `00_database/db/ite_intelligence.db` | Source of truth | 1,985 articles, 1,629 ITE Q, 1,221 AAFP Q |

---

## Key Numbers (as of BATON 032, 2026-04-02)

- **DB articles:** 1,985 (next: ART-1987)
- **DB questions (ITE):** 1,629 (2018–2025); blueprint 100%; subcategory + topic_label DROPPED
- **DB questions (AAFP BRQ):** 1,221; blueprint 100%; flattened; subcategory DROPPED
- **article_icd10:** 4,137 rows
- **question_icd10:** 5,284 rows (92.8% ITE coverage)
- **aafp_question_icd10:** 4,753 rows (normalized, related cap applied)
- **icd10_vec:** 2,219 rows (OpenAI text-embedding-3-small 1536d)
- **article_icd10_vec:** 1,674 rows (rebuilt 2026-04-01)
- **question_icd10_vec:** 2,733 rows (rebuilt 2026-04-01)
- **clinical_pathways:** 4,020 rows (rebuilt 2026-03-31, blueprint-based, both banks)
- **pubmed_pmid_cache:** 344 rows (Layer 2 seed)
- **PDFs:** 404 across 4 tiers (49 AAFP articles awaiting download)
- **M3 scripts:** 9 Python + 2 JS + 2 JSON config
- **M3 reports:** AAFP_BRQ_ITE_Overlap_QA_v2.docx + AAFP_BRQ_NearDuplicate_QA.docx + ITE_Intelligence_FacultyPresentation_2025.pptx

---

## Active Deferred Flags

| Flag | Description | Priority |
|------|-------------|----------|
| GIT-PENDING | 8 scripts unstaged from BATON 029–031 + BATON 032 | **HIGH** |
| DEFERRED-A | PDF download: 49 new articles ART-1938–1986 | HIGH |
| DEFERRED-B | `update_citation_trends.py` — run after DEFERRED-A | MEDIUM |
| DEFERRED-C | AAFP vs ITE trend comparison | MEDIUM |
| DEFERRED-D | 229 citation gap articles (88 AFP batch-downloadable) | MEDIUM |
| DEFERRED-E | Interactive vector dashboard | LOW |
| DEFERRED-F | Intelligence 2.0 Layer 2 (`article_currency` via PubMed, 344 PMIDs cached) | MEDIUM |
| Q-VEC-GAP | Fill question_vec: 440 ITE (2018–2019) + 1,221 AAFP | MEDIUM |

**Closed this session:** QUESTION-DIST-001 ✅, PRESENTATION ✅
**Previously closed:** ICD10-SYMMETRY ✅, CLINICAL-PATHWAY ✅, Q-ICD10-VEC ✅, ARTICLE-ICD10-VEC ✅

---

## Next Steps (priority order)

1. **Git commit (GIT-PENDING)** — stage: `ite_analyze_v2.py`, `ite_analyzer_v2.py`, `ite_report_builder_v2.js`, `export_aafp_ite_relationships.py`, `word_doc_defaults.py`, `build_aafp_qa.py`, `build_aafp_qa_file1.py`, `build_faculty_pptx.js`
2. **PDF download** (DEFERRED-A) — `download_aafp_acquisitions.py` → `backfill_new_article_metadata.py --art-id-min 1938`
3. **Intelligence 2.0 Layer 2** — `article_currency` table (344 PMIDs ready)
4. **Fill question vector gaps (Q-VEC-GAP)** — embed 440 ITE (2018–2019) + 1,221 AAFP → `question_vec`
