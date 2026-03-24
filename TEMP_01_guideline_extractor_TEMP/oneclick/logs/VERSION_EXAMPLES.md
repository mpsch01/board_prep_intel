# Pipeline Version Examples
## Purpose
Reference DOCXs showing the pipeline output at key milestones.
Use these to visually verify that future changes haven't broken rendering.

---

## v2.3 + ITE Intelligence — 2026-03-11

### 01_Hip_Pain_Adults_Chamberlain_2021_summary.docx
- **Article:** Hip Pain in Adults — Chamberlain, AFP 2021
- **Engine:** DiagnosticEngine (diagnostic_guideline, conf=0.95)
- **ITE match:** 5 questions across 4 exam years (2021, 2022, 2023, 2024)
- **Match method:** author_year_exact
- **Features present:**
  - Citation line on page 1
  - Full extraction (recommendations, thresholds, population)
  - Synthesis block (practice pearls, clinical bottom line)
  - ITE Exam Intelligence section with TF-IDF color-coded concept chips
  - Color key strip (green = specific, yellow = moderate, red = common)
  - Concepts sorted green → yellow → red, separated by " | "
  - Dark background (#1A1A2E) on Concept Tested column
- **Notes:** First article validated end-to-end with full visual polish

### 04_Secondary_Hypertension_Charles_2017_summary.docx
- **Article:** Secondary Hypertension — Charles, AFP 2017
- **Engine:** DiagnosticEngine (diagnostic_guideline, conf=0.85)
- **ITE match:** 6 questions across 3 exam years (2020, 2022, 2023)
- **Match method:** author_year_exact
- **Features present:** Same as above
- **Notes:** Second validation article — confirmed pipeline generalizes across articles

---

## What to Check When Comparing
1. ITE section present and populated (not blank)
2. Sub-banner shows question count + years (not match method label)
3. Color key strip visible above table
4. Concept chips colored and sorted correctly
5. Dark background on Concept Tested column only
6. No large whitespace gap before ITE section
7. Citation line present under title banner
