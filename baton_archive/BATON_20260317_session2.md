# BATON — ITE Score Analysis Pipeline (Reverse-Engineering + Spec)

**Date:** March 17, 2026 (Session 2)
**Previous BATON:** `BATON_active_20260317.md` (Layer 1 ICD-10 Rebuild)
**Status:** ITE score report PDF format fully reverse-engineered. Pipeline spec complete. Two-resident calibration confirms universal constants. Ready to build.

---

## What Was Done This Session

### 1. ITE Score Report Analysis — Hopkins (ABFM ID: 210357)

Manually analyzed two ABFM ITE 2025 score report PDFs (Blueprint Performance + Body System Performance) for resident Oceana Hopkins, M.D. Full cross-tab analysis, weak area identification, and practice question ranking from `ite_intelligence.db`.

**Deliverables produced:**
- `ITE_2025_Score_Analysis_Hopkins.html` — Interactive report with Chart.js visualizations
- `ITE_2025_Score_Analysis_Hopkins.docx` — Full analysis + 60 ranked practice questions with answers
- `ITE_2025_Practice_Questions_Hopkins.docx` — Questions-only exam with answer key at end

**Key finding during analysis:** Visual PDF color parsing was unreliable (initial analysis: 48.7%, corrected: 72.3%). Required 5+ rounds of manual corrections from zoomed screenshots. This pain point motivated the pipeline work.

### 2. PDF Format Reverse-Engineering (PyMuPDF)

Discovered that ABFM score report PDFs encode correct/incorrect status as explicit RGB color values in the PDF text metadata — no vision model or OCR needed.

**Color signatures (deterministic):**
| Element | RGB | Font | Flags |
|---|---|---|---|
| Incorrect | `(255, 0, 0)` | Helvetica-Bold | 16 |
| Correct | `(0, 128, 0)` | Helvetica | 0 |
| Score axis | `(47, 110, 181)` | Helvetica-Bold | 16 |
| Column header | `(255, 255, 255)` | Helvetica | 0 |

**Score axis formula:** `score = -3.0581 * y + 1703.06` (linear, R²=1.0, validated against all 21 axis labels)

**Blueprint column boundaries (x-coordinate ranges):**
| Column | X Range | Subcategory Columns |
|---|---|---|
| Acute Care | 80–220 | 8 |
| Chronic Care | 220–350 | 8 |
| Emergent/Urgent | 350–470 | 7 |
| Preventive | 470–600 | 5 |
| Foundations | 600–700 | 4 |

**Body System column boundaries (page 1):**
| Column | X Range |
|---|---|
| Cardiovascular | 70–200 |
| Injuries/Musculoskeletal | 200–370 |
| Respiratory | 370–480 |
| Psychiatric/Behavioral | 480–610 |
| Sexual and Reproductive | 610–700 |

### 3. Two-Resident Calibration

Validated all constants against a second resident's reports (Arghyadeep Sarkar, D.O., ABFM ID: 221051).

**Result: Every single constant is identical between residents.**
- Column header x-positions: exact match
- All 32 subcategory x-positions: exact match (zero unique to either)
- Score axis slope/intercept: exact match
- Color signatures: exact match
- Body System header x-positions: exact match
- Page dimensions: exact match (792 × 612)
- Items per blueprint column: exact match (68, 49, 36, 29, 9 = 191)

**Conclusion:** ABFM uses a fixed-layout PDF template. Constants are universal for 2025 ITE.

### 4. Pipeline Specification

Wrote full technical spec covering 5 pipeline stages:
1. **Extract** — PyMuPDF color/position extraction
2. **Classify** — X-coordinate → column mapping
3. **Analyze** — Performance rates, cross-tab, weak area identification
4. **Match** — Relevance-scored practice questions from ITE Intelligence DB
5. **Generate** — HTML + two DOCXs

---

## Files Created This Session

| File | Location | Purpose |
|---|---|---|
| `ITE_SCORE_ANALYSIS_PIPELINE.md` | `abfm_prep/` | Full technical spec for the scriptable pipeline |
| `ite_parser_config.json` | `abfm_prep/` | Machine-readable constants (colors, boundaries, formula) |
| `blueprint_extraction_hopkins_2025.json` | `abfm_prep/` | Hopkins extraction data (validation baseline) |
| `test_fixture_sarkar_2025.json` | `abfm_prep/` | Sarkar extraction data (test fixture for script validation) |
| `221051_Item_Blueprint_Performance.pdf` | `abfm_prep/` | Sarkar Blueprint PDF (test input) |
| `221051_Item_BodySystem_Performance.pdf` | `abfm_prep/` | Sarkar Body System PDF (test input) |
| `ITE_2025_Score_Analysis_Hopkins.html` | `abfm_prep/` | Hopkins interactive HTML report |
| `ITE_2025_Score_Analysis_Hopkins.docx` | `abfm_prep/` | Hopkins full DOCX report |
| `ITE_2025_Practice_Questions_Hopkins.docx` | `abfm_prep/` | Hopkins questions-only DOCX |

---

## Current State

### Pipeline Readiness
- **Parser config:** Complete (`ite_parser_config.json`)
- **Validation data:** Two residents (Hopkins + Sarkar) with known-good extractions
- **Spec document:** Complete (`ITE_SCORE_ANALYSIS_PIPELINE.md`)
- **Code:** Not yet built — spec only

### Estimated Build Scope
| Module | Lines | Dependencies |
|---|---|---|
| `ite_parser.py` | ~150 | PyMuPDF (fitz) |
| `ite_analyzer.py` | ~200 | sqlite3 |
| `ite_report_builder.py` | ~250 | python-docx, or docx-js (Node) |
| `ite_analyze.py` (CLI) | ~30 | argparse |
| **Total** | **~630** | |

### Known Gaps
- **Subcategory labels:** Not in PDF text — positions exist but labels must come from ABFM reference or DB cross-reference
- **Body System PDF pagination:** Only 5 of 15 systems per page. Must handle multi-page. Only page 1 provided for both residents.
- **Blueprint backfill:** 66.8% of DB questions have empty blueprint field — limits question-matching for some categories

---

## Next Steps (Build Order)

1. **Build `ite_parser.py`** — The high-value piece. PDF in → structured JSON out. Validate against both test fixtures.
2. **Build `ite_analyzer.py`** — Performance calculations + DB queries for practice questions. Reuse the relevance scoring algorithm from this session.
3. **Build `ite_report_builder.py`** — Generate all three output formats. Can reuse patterns from Hopkins report generation.
4. **Build `ite_analyze.py`** — CLI wrapper. `python ite_analyze.py --blueprint X.pdf --bodysystem Y.pdf --db ite_intelligence.db --output-dir ./reports/`
5. **Optional: Cowork skill wrapper** — Package as a plugin for drag-and-drop analysis in Cowork sessions.

---

## Upstream BATON Items Still Open

These carry forward from the previous BATON and are unrelated to this session's work:

- **FLAG 1:** ITE Enrichment Quality Dimension (deferred)
- **FLAG 13 Layer 2:** PubMed Currency (not started)
- **FLAG 15:** User still needs to run `node build_merged_docx.js --merged-only` (139 → 145 DOCXs)
- **Blueprint backfill:** 66.8% of questions have empty blueprint — would significantly improve question matching
- **v2.3 re-extraction:** ~$6.50 batch cost for content-rich DOCXs

---

## Key Architecture Reminders

- **Codon format:** `Author_Year#@#ART-XXXX@#@.pdf`
- **ITE Intelligence DB:** `abfm_prep/02_ite_intelligence/db/ite_intelligence.db`
- **Parser config:** `abfm_prep/ite_parser_config.json` — all extraction constants
- **Pipeline spec:** `abfm_prep/ITE_SCORE_ANALYSIS_PIPELINE.md` — full technical reference
- **Test acceptance criteria:** Parse Sarkar PDFs → compare against `test_fixture_sarkar_2025.json` → expect 191/191 match
- **Relevance scoring:** body_system_weight=10, blueprint_weight=8, subcategory_weight=6, cross_tab_bonus=5, article_bonus=0.5/ea, recency_bonus=0.3/yr
- **Standard DB filters:** Exclude `citation_count = 0`, `source_type = 'stub'`, `article_id = 'ART-0001'`
