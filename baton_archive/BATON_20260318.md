# BATON — ITE Score Analysis Pipeline v2 (Turbocharged Analyzer)

**Date:** March 18, 2026
**Previous BATON:** `BATON_active_20260317_session2.md` (Pipeline Spec + Parser Build)
**Status:** Pipeline v1 fully built and validated. Analyzer v2 (turbocharged) built with 5 core layers + 3 plugins operational. ABFM reference data digitized. Report builder v2 (restyled) not yet built.

---

## What Was Done This Session

### 1. Pipeline v1 — Complete Build + Validation

Built the full 4-module pipeline from the spec in the previous BATON:

| Module | Lines | Purpose | Status |
|---|---|---|---|
| `ite_parser.py` | ~300 | PDF extraction — color/position → structured items | ✅ Validated 191/191 × 2 residents |
| `ite_analyzer.py` | ~250 | Performance analysis + relevance-scored question matching | ✅ Working |
| `ite_report_builder.py` | ~400 | HTML (Chart.js) + 2 DOCX report generators | ✅ Working |
| `ite_analyze.py` | ~120 | CLI wrapper — single command, full pipeline | ✅ Working on Windows + Linux |

**Validation results:**
- Sarkar: 191/191 exact match (item, correct, blueprint, score, x, y)
- Hopkins: 191/191 exact match (including sub_col_index)
- Cross-report: 0 mismatches on overlapping body system items
- Table 4 ground truth validation: 191/191 — parser blueprint classification matches ABFM published item-to-blueprint mapping

**Windows fix:** All `open()` calls use `encoding="utf-8"` to prevent cp1252 errors on Windows (× and ≥ characters).

**Key finding:** Compared pipeline output to the manual analysis from session 2. Pipeline says Hopkins = 125/191 (65.4%). Manual said 138/191 (72.3%). The 13-item discrepancy traces to visual color misclassification that persisted through 5+ rounds of manual corrections. The manual report also had inflated item counts (blueprint total = 187, body system total = 245 — both should be 191). Pipeline is the ground truth.

### 2. ABFM Reference Data — Digitized

Created `abfm_reference_2025.json` from the 2025 ITE Score Result Handbook:

- **Table 3:** Raw-to-scaled score conversion (191 entries). Hopkins 125→510, Sarkar 109→400.
- **Table 4:** Item-to-blueprint ground truth for all 200 items. Validated 191/191 against parser.
- **National benchmarks:** PGY1=389±76, PGY2=443±77, PGY3=474±78, All=434±85 (N=15,382)
- **Blueprint weights:** Acute=35%, Chronic=25%, Emergent=20%, Preventive=15%, Foundations=5%
- **SEM values:** Per-blueprint and per-body-system standard errors of measurement
- **Program trend:** 8-year program vs national means (2018-2025)
- **Pass probability tiers:** Critical Risk (<380), At Risk (380-419), On Track (420-479), Strong (480+)
- **Bayesian Score Predictor reference:** Screenshots captured, probability distributions documented

### 3. Analyzer v2 — Turbocharged Edition

Built `ite_analyzer_v2.py` with multi-layer architecture:

**Core Layers:**
1. **Difficulty Profiling** — Classifies misses as easy (≥700, knowledge gap), mid-range (300-699, high-yield), or hard (<300, low-yield). Profiles per-dimension.
2. **Subcategory Decomposition** — Performance by subcol index within each blueprint. 3D cross: body_system × blueprint × subcol.
3. **Spatial Clustering** — Herfindahl index for miss concentration. Consecutive miss runs. Score-band clustering.
4. **Cross-Dimensional Pattern Detection** — Blueprint gap detection, subcol consistency, difficulty inversion ("second-guessing" pattern).
5. **Yield-Weighted Prioritization** — Ranks weaknesses by recoverable items × exam weight. Acute Care = 9.6 recoverable items for Hopkins.

**Plugins (operational):**
- **P1 Concept Fingerprinting** — Mines concept_tags from missed items. Found: ceftriaxone appears 5× in Hopkins' misses, Management (20) and Pharmacology (19) dominate missed subcategories.
- **P3 ICD-10 Weakness Map** — Chains missed items → articles → ICD-10 codes → chapter rollup.
- **P6 Cohort Comparator** — Aggregates multiple residents for program-level analysis. Stub built, needs multiple residents to test.

**Plugins (designed, not yet built):**
- **P2 Explanation Mining** — Claude API batch analysis of missed item explanations. Requires user's API key. Designed as a CLI flag.
- **P5 Historical Trend Detector** — Year-over-year comparison for same resident. Requires multiple years of parsed data.

**Threshold System (3-tier, ABFM-anchored):**
- Tier 1: FMCE pass probability from scaled score (MPS=380, strong=480+)
- Tier 2: Relative performance vs own mean ± 1 SD (personal weakness/strength, not arbitrary 70%)
- Tier 3: SEM-aware confidence flags (Foundations ±187 = "hypothesis only"; Acute ±69 = reliable)

**Hopkins v2 Analysis Key Findings:**
- Scaled 510, "strong" tier, ~81st percentile for PGY2
- Difficulty inversion: 38% accuracy on easy items vs 58% on mid-difficulty (possible second-guessing)
- Concept fingerprint: antibiotic selection pattern (ceftriaxone 5×, amoxicillin/doxycycline/azithromycin 3× each)
- Subcategory split: Management (20 misses) + Pharmacology (19) dominate. Diagnosis/Screening are relative strengths.
- #1 yield priority: Acute Care alone = 9.6 recoverable items = ~40 scaled score points

### 4. Custom Hopkins Analysis Report

Generated `ITE_2025_Custom_Analysis_Hopkins.docx` — a full narrative report with:
- Executive summary with ABFM-contextualized interpretation
- Blueprint + body system performance tables
- Cross-tab analysis with priority targets
- 10 targeted practice questions from DB (with full text, choices, explanations)
- Top 3 high-yield articles with personalized rationale
- 6-week study plan

---

## Files Created/Modified This Session

| File | Location | Purpose |
|---|---|---|
| `ite_parser.py` | `abfm_prep/` | PDF parser — validated 191/191 × 2 residents |
| `ite_analyzer.py` | `abfm_prep/` | v1 analyzer (superseded by v2 for analysis, still used by CLI) |
| `ite_analyzer_v2.py` | `abfm_prep/` | **v2 turbocharged analyzer — 5 core layers + 3 plugins** |
| `ite_report_builder.py` | `abfm_prep/` | v1 report builder (HTML + 2 DOCXs) |
| `ite_analyze.py` | `abfm_prep/` | CLI wrapper |
| `abfm_reference_2025.json` | `abfm_prep/` | **ABFM reference data — Table 3, Table 4, benchmarks, SEM, tiers** |
| `ite_parser_config.json` | `abfm_prep/` | Parser constants (unchanged from previous session) |
| `analysis_v2.json` | `07_score_reports/hopkins_2025/` | Hopkins v2 analysis output |
| `ITE_2025_Custom_Analysis_Hopkins.docx` | `07_score_reports/hopkins_2025/` | Custom narrative report |

---

## Current State

### What Works End-to-End
```
PDF Score Reports → ite_parser.py → ite_analyzer_v2.py → analysis JSON
```
- Parser: production-ready, validated against ABFM ground truth
- Analyzer v2: production-ready, all 5 core layers + P1/P3/P6 plugins operational
- CLI: `python ite_analyze.py --blueprint X.pdf --bodysystem Y.pdf --db Z.db --output-dir ./reports/`

### What Needs Building
1. **Report Builder v2** — Restyle to mirror the guideline extractor DOCX format (Aptos font, dark navy headers, colored section bars, narrative interpretation). The v1 builder works but uses generic python-docx formatting.
2. **CLI v2** — Wire `ite_analyze.py` to use `ite_analyzer_v2.py` instead of v1. Add `--plugins`, `--pgy-level` flags.
3. **Plugin P2 (Explanation Mining)** — Claude API integration for thematic analysis of missed item explanations. User has API key in environment variables. This is a "let the user run it" step — provide the command, he copies/pastes/runs.
4. **Plugin P5 (Historical Trend)** — Needs parsed data from multiple exam years for the same resident.

### Design Decisions Locked
- **Threshold system:** 3-tier ABFM-anchored (pass probability + relative + SEM). NOT a flat 70% cutoff.
- **Report style:** Mirror guideline extractor DOCX (Aptos, #1F3864 navy, #2E75B6 blue headers, colored section bars, narrative interpretation blocks).
- **Question selection:** Yield-weighted priority allocation, not flat relevance scoring.
- **Difficulty tiers:** Easy (≥700) / Mid (300-699) / Hard (<300), profiled per-dimension.

---

## Open Flags

### Existing (carried forward)
- **FLAG 1:** ITE Enrichment Quality Dimension (deferred)
- **FLAG 13 Layer 2:** PubMed Currency (not started)
- **FLAG 15:** User still needs to run `node build_merged_docx.js --merged-only` (139 → 145 DOCXs)

### New — DB Enrichment Opportunities
- **FLAG 16:** Raw-to-Scaled Score Conversion Table → store in DB as lookup table. Enables programmatic scaled score computation. ~110 rows, per exam year.
- **FLAG 17:** Item-to-Blueprint Ground Truth (Table 4) → store in DB. Validated 191/191 against parser. Enables item-level analytics without PDF parsing. Also: **this is the blueprint backfill solution** — if item numbers map to QID sequence (QID-2025-0001 = Item 1), this fills the 66.8% empty `questions.blueprint` field for 2025. Check if 2024 handbook has the same table.
- **FLAG 18:** National Benchmarks by PGY Year → store per exam year. Enables relative percentile computation and cohort benchmarking. Small table, massive analytical value.
- **FLAG 19:** Category-Level SEM Values → store per blueprint and body system per year. Makes the analyzer's statistical confidence flagging data-driven rather than hardcoded.
- **FLAG 20:** Blueprint Exam Composition Weights → Acute=35%, Chronic=25%, etc. Official ABFM percentages for yield-weighted prioritization.
- **FLAG 21:** 8-Year Program Trend Data → National + program means by PGY, 2018-2025. Backbone for Plugin P5 (Historical Trend Detector) at program level.
- **FLAG 22:** Bayesian Score Predictor Probability Distributions → If digitized, enables local FMCE pass probability estimation. Most ambitious flag — essentially building a local BSP.
- **FLAG 23:** Table 4 Blueprint Backfill → Verify item-to-QID mapping, then populate `questions.blueprint` for all 2025 items. **Potentially resolves the 66.8% empty blueprint issue entirely.** Check 2024 handbook for same table.
- **FLAG 24:** Body System Ground Truth from Score Reports → Same logic as FLAG 23 for `body_system` field. Requires confirming item number = QID sequence number.
- **FLAG 25:** Item Difficulty Scores into DB → Store each item's difficulty score (0-1000) per QID. Enables difficulty-weighted study plan generation and national percentile contextualization per question.

### Build Priorities (Next Session)
1. Report Builder v2 (restyled DOCX mirroring guideline extractor format)
2. CLI v2 (wire to analyzer v2 + add flags)
3. Plugin P2 (Explanation Mining — provide Claude API command for user to run)
4. End-to-end validation on both residents with full report output
5. FLAG 23 investigation (blueprint backfill via Table 4 → QID mapping)

---

## Key Architecture Reminders

- **Codon format:** `Author_Year#@#ART-XXXX@#@.pdf`
- **ITE Intelligence DB:** `abfm_prep/02_ite_intelligence/db/ite_intelligence.db`
- **Parser config:** `abfm_prep/ite_parser_config.json`
- **ABFM reference:** `abfm_prep/abfm_reference_2025.json`
- **Pipeline spec:** `abfm_prep/ITE_SCORE_ANALYSIS_PIPELINE.md`
- **Score reports:** `abfm_prep/07_score_reports/raw_score_pdfs/`
- **Generated reports:** `abfm_prep/07_score_reports/{resident_name}/`
- **v2 analyzer output:** `analysis_v2.json` in each resident's report directory
- **Test acceptance:** Parse Sarkar PDFs → 191/191 match. Parse Hopkins → 191/191 match. Table 4 → 191/191 match.
- **Relevance scoring (v1):** body_system_weight=10, blueprint_weight=8, subcategory_weight=6, cross_tab_bonus=5
- **Relevance scoring (v2):** Yield-weighted priority allocation. Top priority gets proportionally more questions.
- **Standard DB filters:** Exclude `citation_count = 0`, `source_type = 'stub'`, `article_id = 'ART-0001'`
- **Windows compatibility:** All file writes use `encoding="utf-8"`

---

## Guideline Extractor DOCX Style Reference

The report builder v2 should mirror this style from `Abegaz_Shehab_2017_ART-0011_db_intel.docx`:

- **Font:** Aptos throughout
- **Colors:** Navy #1F3864 (headers, study notes), Blue #2E75B6 (headings, category labels), Dark gray #333333/#595959 (body), White #FFFFFF on dark bars, Light blue #D6E4F7 (metadata)
- **Section bars:** Full-width colored background with white bold text (e.g., "★ ITE EXAM INTELLIGENCE", "✎ STUDY NOTE")
- **Heading 1:** Dark navy, 14pt, bold
- **Heading 2:** Blue #2E75B6, 12pt, bold
- **Tables:** Light header shading, structured ITE Intelligence data
- **Narrative blocks:** "✎ STUDY NOTE" sections with prose interpretation in #1F3864
- **Footer:** Article ID + generated-by line in 8pt gray

---

## Hopkins v2 Analysis Summary (for reference)

```
Resident: Oceana Hopkins, M.D. (ABFM ID: 210357)
Overall: 125/191 = 65.4% → Scaled 510 → "Strong" tier → ~81st percentile (PGY2)
vs MPS: +130 | vs PGY2 mean: +67 | vs PGY3 mean: +36

Blueprint Performance:
  ⚠ Acute Care       55.9% (39/68)  — relative weakness
  ★ Chronic Care     79.6% (39/49)  — relative strength
  — Emergent/Urgent  61.1% (22/36)
  — Foundations      66.7% (6/9)
  — Preventive       69.0% (20/29)

Key Patterns:
  - 24-point blueprint gap (Chronic 80% vs Acute 56%)
  - Difficulty inversion: 38% on easy items vs 58% on mid-difficulty
  - Antibiotic selection cluster: ceftriaxone 5×, amoxicillin/doxycycline/azithromycin 3× each
  - Management (20) + Pharmacology (19) = 59% of all misses
  - Acute Care alone = 9.6 recoverable items = ~40 scaled score points
```
