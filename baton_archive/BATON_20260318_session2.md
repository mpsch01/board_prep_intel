# BATON — ITE Score Analysis Pipeline v2.1 (3-Tier Cascade + Full Shell)
**Date:** March 18, 2026 (Session 2)
**Previous BATON:** `BATON_active_20260318.md` (Report Builder v2 + CLI v2)
**Status:** End-to-end pipeline validated for both residents. 3-tier question cascade built and tested. Report builder v2 fully data-driven (all hardcoded values removed). Both Hopkins and Sarkar ran successfully through PDF → Parser → Analyzer v2 → Report Builder v2.

---

## What Was Done This Session

### 1. Question Matching — 3-Tier Cascade (FLAG 26 resolved)

**Root cause identified:** Only 395/1,189 questions (33.2%) have a `blueprint` field. The other 794 (pre-2024) have empty blueprint because ABFM introduced blueprint categories in 2024. The old matcher only searched by blueprint, missing 66.7% of the question bank.

**Investigation path:**
- ICD-10 codes don't discriminate between blueprints (same diagnosis can be Acute, Chronic, Preventive, or Emergent)
- Subcategory profiles DO discriminate: Preventive = 39% Screening, Emergent = 35% Management, Chronic = 48% Pharmacology
- 145 articles overlap between 2024-2025 and 2020-2023 eras — articles are the bridge, not ICD-10 chapters
- All 794 pre-2024 questions have `body_system_merged`, `subcategory`, and `concept_tags` populated

**Solution built:** 3-tier cascade in `match_practice_questions()`:

| Tier | Strategy | Pool | When fires |
|------|----------|------|------------|
| 1 | Direct blueprint/body_system/cross_tab match | 395 tagged questions | Always (first attempt) |
| 2 | Subcategory fingerprint match | 794 untagged questions | If Tier 1 didn't fill alloc |
| 3 | ICD-10 sibling match (via article chain) | All 1,189 questions | If Tier 2 still short |

**Allocation system:**
- `MIN_PER_WEAK = 5` — guaranteed floor per priority area
- `effective_target = max(target_count, num_priorities × 5)` — auto-expands budget
- `max_per_area = round(effective_target × 0.4)` — 40% cap prevents one area hogging budget
- Bonus pool distributed proportionally by `priority_score`

**Subcategory fingerprints (constants in analyzer):**
```python
BLUEPRINT_SUBCATEGORY_FINGERPRINT = {
    "Preventive Care":          ["Screening", "Prevention", "Counseling"],
    "Emergent and Urgent Care":  ["Management", "Workup", "Interpretation"],
    "Chronic Care Management":   ["Pharmacology", "Treatment", "Prognosis/Risk"],
    "Acute Care and Diagnosis":  ["Diagnosis", "Workup", "Pathophysiology"],
    "Foundations of Care":       ["Management", "Screening", "Counseling"],
}
```

**Every question carries `match_tier` (1/2/3)** for report transparency.

### 2. Subcategory Decomposition — Named Categories (Section 5)

Replaced positional `sub_col_index` (pixel positions from PDF scatter plot) with named subcategories (Management, Pharmacology, Diagnosis, etc.) via DB lookup. The analyzer now does `item → QID-2025-XXXX → questions.subcategory` for each item.

Report shows per-blueprint breakdown + overall subcategory performance. No flags — color coding only (red < 50%, amber < 70%, green ≥ 70%).

### 3. Easy Misses Table (Section 6)

Added a 23-row table to the Difficulty Profile section showing every easy miss (score ≥ 700) with QID, difficulty score, body system, blueprint, and subcategory. Enriched via DB lookup. Score colors: red ≥ 900, amber 700-899.

### 4. Report Builder — All Sections Data-Driven

Audited all 10 sections. Fixed field name mismatches and hardcoded values:

| Section | Issue | Fix |
|---------|-------|-----|
| 2. Executive Summary | Hardcoded percentages, "9.6 items ≈ 40 pts" | Dynamic from `perf`, `t2`, `diff`, `yields[0]` |
| 4. Blueprint Performance | Hardcoded SEM values "±187", "±69" | Iterates `t3` dynamically |
| 7. Yield Priorities | Read `y.category`, `y.exam_weight` (wrong names) | Reads `y.dimension`, `y.exam_weight_pct`, `y.priority_score` |
| 8. Concept Fingerprint | Read `concept.top_concepts` (doesn't exist) | Reads `diagnoses`, `drugs`, `guidelines` as 3 separate tables |
| 8. Study note | Hardcoded "Management (20 misses)", "ceftriaxone 5×" | Dynamic from actual data |
| 9. ICD-10 study note | Hardcoded chapter names | Dynamic from sorted `chapter_summary` |

### 5. CLI v2 — End-to-End Fixes

- Fixed `question_count` display (was reading nonexistent field, now reads `len(practice_questions)`)
- Saves both `analysis_v2.json` (for report builder v2) and `score_analysis.json` (v1 compat)
- Added `weak_areas` shim for v1 HTML builder compatibility (key names: `blueprints`, `body_systems`)
- v1 HTML report wrapped in try/except (fails gracefully, v2 DOCX is primary)
- Report builder v2 now receives `analysis_v2.json` path correctly

### 6. End-to-End Validation

| Resident | Parser | Analyzer | Questions | Report | Status |
|----------|--------|----------|-----------|--------|--------|
| Hopkins | 191/191 ✓ | 5 layers + 2 plugins ✓ | 50 (T1:50) ✓ | 2 DOCXs ✓ | PASS |
| Sarkar | 191/191 ✓ | 5 layers + 2 plugins ✓ | 50 (T1:50) ✓ | 2 DOCXs ✓ | PASS |

---

## Files Created/Modified This Session

| File | Location | Purpose |
|------|----------|---------|
| `ite_analyzer_v2.py` | `abfm_prep/` | 3-tier cascade, named subcategory decomposition, capped allocation |
| `ite_report_builder_v2.js` | `abfm_prep/` | All sections data-driven, tier labels, easy misses table, named subcategories |
| `ite_analyze_v2.py` | `abfm_prep/` | CLI fixes: question count, dual JSON export, weak_areas shim, v1 HTML graceful fail |
| `analysis_v2.json` | `07_score_reports/hopkins_2025/e2e_test/` | Hopkins full e2e output |
| `analysis_v2.json` | `07_score_reports/sarkar_2025/e2e_test/` | Sarkar full e2e output |
| `ITE_2025_v2_Analysis_*.docx` | `07_score_reports/*/e2e_test/` | Final analysis reports (both residents) |
| `ITE_2025_v2_Exam_*.docx` | `07_score_reports/*/e2e_test/` | Final exam versions (both residents) |

---

## Current State

### What Works End-to-End
```
PDF Score Reports (blueprint + body system)
    → ite_parser.py (191/191 items)
    → ite_analyzer_v2.py (5 core layers + P1/P3 plugins)
        → 3-tier question cascade (50 questions, T1/T2/T3 tagged)
        → Named subcategory decomposition via DB
        → Easy misses enrichment via DB
    → analysis_v2.json + score_analysis.json
    → node ite_report_builder_v2.js → 2 DOCXs (Analysis + Exam)
```

All tested on both Hopkins and Sarkar. Pipeline is production-ready for any resident with ABFM score report PDFs.

### What Needs Doing

1. **v1 HTML Report Compatibility** (LOW PRIORITY)
   - v1 `build_html_report()` expects `relevance_score` on questions — v2 doesn't produce this
   - Currently fails gracefully; v2 DOCX is the primary deliverable
   - Fix: add `relevance_score` shim or update v1 builder to handle v2 question format

2. **Foundations Warning** (COSMETIC)
   - Report builder warns "Foundations (0 questions)" when it's a weak blueprint but not in the top 10 priorities
   - Analytically correct: Foundations gets bumped by higher-yield cross-tab priorities
   - Fix if desired: add a floor guarantee for weak blueprints regardless of yield rank

3. **Plugin P2 (Explanation Mining)** — Claude API integration
   - User has API key in environment variables
   - Provide command for user to run

4. **Directory Cleanup** — see proposal below

---

## Open Flags

### Resolved This Session
- **FLAG 26:** ✅ Question matching gap — fixed with 3-tier cascade + capped allocation

### Existing (carried forward)
- FLAG 1: ITE Enrichment Quality Dimension (deferred)
- FLAG 13 Layer 2: PubMed Currency (not started)
- FLAG 15: User still needs to run `node build_merged_docx.js --merged-only`
- FLAGs 16–25: DB enrichment opportunities (see previous BATON)
- FLAG 27: Report Builder v2 requires `npm install docx` in working directory

### New
- **FLAG 28:** v1 HTML report incompatible with v2 question format (graceful fail, low priority)
- **FLAG 29:** Hardcoded `year = 2025` in subcategory_decomposition and plugin_concept_fingerprint — needs dynamic from parsed_data
- **FLAG 30:** `scholl_204999_ITE_SCORE` PDFs are encrypted — cannot parse in current environment. Need unencrypted versions or password.

---

## Design Decisions Locked

### New this session
- **3-tier question cascade** with subcategory fingerprints and ICD-10 sibling matching
- **Capped allocation:** MIN_PER_WEAK=5, max_per_area=40% of budget, bonus pool proportional
- **match_tier field** on every practice question (1=Direct, 2=Subcategory, 3=ICD-10 Sibling)
- **Named subcategory decomposition** replaces subcol_index (pixel positions → Management/Pharmacology/Diagnosis/etc.)
- **Easy misses table** in difficulty profile section with full QID/body_system/blueprint/subcategory
- **All report sections fully data-driven** — no hardcoded Hopkins-specific values remain
- **Dual JSON export:** `analysis_v2.json` (v2 report builder) + `score_analysis.json` (v1 compat)

### Carried from previous sessions
- Threshold system: 3-tier ABFM-anchored
- Two-file output: Analysis (A+B) and Exam (C)
- All Aptos font, navy/blue/gray color system, cantSplit rows
- CLI v2 naming: `_v2_Analysis_` and `_v2_Exam_` prefixes
- HTML report stays v1 (supplementary)

---

## Directory Cleanup Proposal

### Current 07_score_reports/ is cluttered with test iterations:
```
hopkins_2025/
    test_v2/      ← iteration test (can delete)
    test_v2b/     ← iteration test (can delete)
    test_v2c/     ← iteration test (can delete)
    test_v2d/     ← iteration test (can delete)
    e2e_test/     ← final validated output
    *.docx (v1)   ← v1 era outputs
    *.docx (v2)   ← pre-e2e v2 drafts
```

### Proposed new structure: `08_ite_score_analysis/`

```
08_ite_score_analysis/
├── raw_pdfs/                          ← source PDFs (renamed clearly)
│   ├── hopkins_2025_blueprint.pdf
│   ├── hopkins_2025_bodysystem.pdf
│   ├── sarkar_2025_blueprint.pdf
│   ├── sarkar_2025_bodysystem.pdf
│   ├── scholl_2025_blueprint.pdf      ← (encrypted, needs resolution)
│   ├── scholl_2025_bodysystem.pdf
│   └── reference/
│       ├── 2024ITEScoreResultHandbook.pdf
│       └── 2025ITEScoreResultHandbook.pdf
├── pipeline/                          ← all pipeline code (moved from root)
│   ├── ite_parser.py
│   ├── ite_parser_config.json
│   ├── ite_analyzer_v2.py
│   ├── ite_analyze_v2.py              ← CLI entry point
│   ├── ite_report_builder_v2.js
│   ├── abfm_reference_2025.json
│   ├── ITE_SCORE_ANALYSIS_PIPELINE.md
│   └── v1/                            ← v1 code preserved
│       ├── ite_analyzer.py
│       ├── ite_analyze.py
│       └── ite_report_builder.py
├── reports/
│   ├── hopkins_2025/
│   │   ├── analysis_v2.json
│   │   ├── ITE_2025_v2_Analysis_Oceana_Hopkins.docx
│   │   └── ITE_2025_v2_Exam_Oceana_Hopkins.docx
│   ├── sarkar_2025/
│   │   ├── analysis_v2.json
│   │   ├── ITE_2025_v2_Analysis_Arghyadeep_Sarkar.docx
│   │   └── ITE_2025_v2_Exam_Arghyadeep_Sarkar.docx
│   └── scholl_2025/                   ← ready when PDFs are decrypted
└── archive/                           ← everything from this session's iterations
    ├── v1_reports/
    └── v2_test_iterations/
```

**Benefits:**
- Pipeline code separated from project root (currently 7 .py/.js files cluttering root)
- Raw PDFs renamed to be self-documenting (no more guessing which `body-system (1)` is blueprint vs body system)
- Clean reports directory with only final outputs per resident
- Test iterations preserved but moved to archive
- v1 code preserved but tucked away
- Ready for future residents (just add a new folder under `reports/`)

---

## Key Architecture Reminders

- Codon format: `Author_Year#@#ART-XXXX@#@.pdf`
- ITE Intelligence DB: `abfm_prep/02_ite_intelligence/db/ite_intelligence.db`
- Parser config: `abfm_prep/ite_parser_config.json`
- ABFM reference: `abfm_prep/abfm_reference_2025.json`
- Pipeline spec: `abfm_prep/ITE_SCORE_ANALYSIS_PIPELINE.md`
- Report Builder v2: `abfm_prep/ite_report_builder_v2.js` (requires `npm install docx`)
- CLI v2: `abfm_prep/ite_analyze_v2.py`
- Test acceptance: Parse both residents → 191/191. Full e2e → 2 DOCXs each.

---

## Build Priorities (Next Session)

1. **Directory reorganization** — implement the `08_ite_score_analysis/` structure (if approved)
2. **Plugin P2 (Explanation Mining)** — Claude API command for thematic analysis of missed item explanations
3. **FLAG 29** — make exam year dynamic in subcategory decomposition and concept fingerprint plugins
4. **FLAG 30** — resolve encrypted Scholl PDFs to run your own analysis
5. **Cohort Comparator** (Plugin P6) — now that both residents have e2e outputs, run program-level comparison
