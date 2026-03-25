# ITE Score Analysis Pipeline — Technical Specification

## Overview

Fully automated pipeline for parsing ABFM ITE score report PDFs, cross-referencing with the ITE Intelligence database, and generating personalized study plans with ranked practice questions.

**Input:** Two ABFM PDF score reports (Blueprint Performance + Body System Performance)
**Output:** Interactive HTML report, DOCX analysis with ranked practice questions, DOCX questions-only exam

---

## Pipeline Architecture

```
[PDF Score Reports] → STAGE 1: Extract → STAGE 2: Classify → STAGE 3: Analyze → STAGE 4: Match → STAGE 5: Generate
```

### Stage 1: PDF Extraction (PyMuPDF)

**Library:** `PyMuPDF (fitz)` — extracts text spans with RGB color metadata, font info, and exact x/y coordinates.

**Color Signatures (deterministic, no ML required):**

| Element | RGB | Font | Flags | Meaning |
|---|---|---|---|---|
| Incorrect answer | `(255, 0, 0)` | Helvetica-Bold | 16 | Red bold = wrong |
| Correct answer | `(0, 128, 0)` | Helvetica | 0 | Green non-bold = right |
| Score axis label | `(47, 110, 181)` | Helvetica-Bold | 16 | Blue = axis marker |
| Column header | `(255, 255, 255)` | Helvetica | 0 | White = category name |
| Notes/metadata | `(0, 0, 0)` | Helvetica | 0 | Black = header text |

**Score Axis (y-coordinate → item difficulty score):**
```
score = -3.0581 * y + 1703.06
```
Linear mapping validated against all 21 axis labels (0–1000 in steps of 50). R² = 1.0.

**Deleted Items:** Extracted from black header text. Pattern: `"Questions X, Y, Z were deleted and excluded from scoring"`

**P-Suffix Items:** Items with "P" appended to the number are excluded from scoring for statistical reasons but still have a correct answer.

### Stage 2: Column Classification

**Blueprint PDF — 5 main columns, identified by x-coordinate boundaries:**

| Column | Header X | Item X Range | Subcategory Columns |
|---|---|---|---|
| Acute Care and Diagnosis | 114.4 | 80–220 | 8 |
| Chronic Care Management | 242.9 | 220–350 | 8 |
| Emergent and Urgent Care | 373.0 | 350–470 | 7 |
| Preventive Care | 522.4 | 470–600 | 5 |
| Foundations of Clinical Medicine | 644.8 | 600–700 | 4 |

Within each main column, items are distributed across subcategory sub-columns at fixed x-offsets (~15.5px spacing). Subcategory labels are NOT embedded in PDF text — they exist only as visual column headers in the chart background. Subcategory names must be mapped from a known ABFM subcategory list or from the database.

**Body System PDF — same color/position scheme, different columns:**

| Column | Header X | Item X Range |
|---|---|---|
| Cardiovascular | 120.5 | 70–200 |
| Injuries/Musculoskeletal | 237.1 | 200–370 |
| Respiratory | 391.4 | 370–480 |
| Psychiatric/Behavioral | 504.9 | 480–610 |
| Sexual and Reproductive | 631.7 | 610–700 |

**IMPORTANT:** The Body System PDF may span multiple pages (5 systems per page, 15 total systems). All pages must be parsed. The Blueprint PDF contains ALL items on a single page.

### Stage 3: Performance Analysis

**Per-dimension scoring:**
```python
for each dimension in [blueprint_categories, body_systems, subcategories]:
    correct = count(items where correct == True and dimension == d)
    total = count(items where dimension == d)
    rate = correct / total
    if rate < 0.70:  # threshold for "weak area"
        weak_areas.append((dimension, rate, total))
```

**Cross-tab analysis (the high-value intersection):**
```python
for bs in body_systems:
    for bp in blueprint_categories:
        items = filter(body_system == bs AND blueprint == bp)
        if len(items) >= 3:  # minimum sample size
            rate = correct_count / total_count
            cross_tab[bs][bp] = rate
```

This identifies specific intersections like "Cardiovascular × Acute Care = 40%" that reveal targeted weak spots invisible in single-dimension analysis.

### Stage 4: Practice Question Matching (ITE Intelligence DB)

**Multi-factor relevance scoring:**
```python
score = 0
# Body system match (strongest signal)
if question.body_system in weak_body_systems:
    score += (1.0 - weak_rate) * 10

# Blueprint category match
if question.blueprint in weak_blueprints:
    score += (1.0 - weak_rate) * 8

# Subcategory match
if question.subcategory in weak_subcategories:
    score += (1.0 - weak_rate) * 6

# Cross-tab bonus (question hits BOTH a weak body system and weak blueprint)
if question.body_system in weak_bs AND question.blueprint in weak_bp:
    score += 5

# Resource richness (more linked articles = more study value)
score += min(linked_article_count, 5) * 0.5

# Recency bonus (newer exam questions preferred)
score += (exam_year - 2019) * 0.3
```

**Target:** Top 60 questions, minimum 10 per weak body system.

### Stage 5: Report Generation

Three output formats, all generated programmatically:

1. **Interactive HTML** — Chart.js visualizations, cross-tab heatmaps, collapsible sections
2. **Full DOCX** — Complete analysis + all practice questions with answers and explanations (docx-js or python-docx)
3. **Questions-Only DOCX** — Practice questions without answers, answer key at end

---

## Data Flow Diagram

```
Blueprint_Performance.pdf ──→ extract_blueprint() ──→ {item, correct, blueprint_cat, subcol_idx, score}
                                                              │
Body_System_Performance.pdf ──→ extract_bodysystem() ──→ {item, correct, body_system}
                                                              │
                                                              ▼
                                                    merge_on_item_number()
                                                              │
                                                              ▼
                                              ┌───────────────────────────────┐
                                              │  Unified Item Dataset         │
                                              │  item | correct | blueprint  │
                                              │  body_system | score | sub   │
                                              └───────────────┬───────────────┘
                                                              │
                                              ┌───────────────┼───────────────┐
                                              ▼               ▼               ▼
                                       analyze_dims()  cross_tab()    identify_weak()
                                              │               │               │
                                              └───────────────┼───────────────┘
                                                              │
                                                              ▼
                                                 ite_intelligence.db
                                                   (SQL queries)
                                                              │
                                              ┌───────────────┼───────────────┐
                                              ▼               ▼               ▼
                                        match_qs()    rank_articles()   get_concepts()
                                              │               │               │
                                              └───────────────┼───────────────┘
                                                              │
                                              ┌───────────────┼───────────────┐
                                              ▼               ▼               ▼
                                        report.html    report.docx    questions.docx
```

---

## Key Findings from Reverse Engineering

### What's fully deterministic (zero ambiguity):
- Color extraction: RGB values are exact integers, not probabilistic
- Column assignment: x-coordinate boundaries are fixed per ABFM format
- Score mapping: linear formula, validated against all 21 axis labels
- Item identification: 3-digit zero-padded numbers, uniquely colored

### What needs one-time calibration:
- **Subcategory labels:** The subcategory names (Pharmacology, Management, Diagnosis, etc.) are rendered as visual chart headers but not as extractable text. Need to build a position-to-label map, either from:
  - A reference ABFM document listing subcategory order
  - Manual calibration from one known report
  - Database cross-reference (ITE Intelligence DB has subcategory tags per question)

- **Body System PDF pagination:** Must handle multi-page reports (5 systems per page). Page detection via white-text column headers.

- **Column boundary robustness:** Current boundaries derived from one report. Should validate against 2-3 more reports from different residents to confirm the ABFM uses fixed column positions. If they do (highly likely for a standardized report), the boundaries are universal.

### What's NOT in the PDF:
- Subcategory text labels (only visual)
- Question content / stem / answer choices
- Body system assignment for items not on the Body System report pages provided
- National percentile comparisons (may be on a different report page)

---

## Implementation Plan

### Phase 1: Core Parser (Python, ~200 lines)
```
ite_score_parser.py
├── extract_blueprint(pdf_path) → List[ItemResult]
├── extract_bodysystem(pdf_path) → List[ItemResult]
├── merge_results(blueprint, bodysystem) → UnifiedDataset
├── calculate_performance(dataset) → PerformanceReport
└── export_json(report) → score_analysis.json
```

### Phase 2: Question Matcher (Python + SQLite, ~100 lines)
```
ite_question_matcher.py
├── load_weak_areas(score_analysis.json) → WeakAreas
├── query_practice_questions(db, weak_areas) → RankedQuestions
├── query_top_articles(db, weak_areas) → TopArticles
└── export_study_plan(questions, articles) → study_plan.json
```

### Phase 3: Report Generator (Node.js or Python, ~300 lines)
```
ite_report_builder.js / .py
├── build_html_report(score_analysis, study_plan) → report.html
├── build_full_docx(score_analysis, study_plan) → report.docx
└── build_questions_docx(study_plan) → questions.docx
```

### Phase 4: CLI Wrapper
```bash
python ite_analyze.py \
  --blueprint "210357_Blueprint_Performance.pdf" \
  --bodysystem "210357_BodySystem_Performance.pdf" \
  --db "ite_intelligence.db" \
  --output-dir "./reports/hopkins_2025/"
```

**Estimated total:** ~600 lines of code. One afternoon to build, reusable for every resident forever.

---

## Validation Strategy

For any new report, the pipeline should auto-validate:
1. **Item count check:** Blueprint PDF should yield exactly 191 items (200 - 9 deleted) for 2025. Future years may differ.
2. **Cross-report reconciliation:** Items appearing in both PDFs must agree on correct/incorrect status.
3. **Score sanity:** All scores should fall in 0-1000 range.
4. **Column coverage:** Every item must map to exactly one blueprint category and one body system.
5. **Deleted item extraction:** Verify deleted item numbers match the header note.

---

## Revision History

| Date | Version | Notes |
|---|---|---|
| 2026-03-17 | 1.0 | Initial spec from reverse-engineering Hopkins 2025 report |
