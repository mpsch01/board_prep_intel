# BATON 054: ITE Report Builder Redesign (v3.2)
**Date:** 2026-04-12
**Previous BATON:** BATON_active_053_20260410_github_sync_housekeeping.md
**Git:** main, 8e4fbbf (pre-commit — session scripts not yet committed)
**Session type:** Active development — ite_report_builder_v2.js major redesign + pipeline fixes

---

## Session Overview

Two-pass redesign of ite_report_builder_v2.js (18 total edits across this session), plus pipeline fixes to ite_analyze_v2.py and ite_analyzer_v3.py. No DB changes.

### Files Modified This Session
- `03_module.3_analyst/scripts/ite_report_builder_v2.js` — 18 design edits (see below)
- `03_module.3_analyst/scripts/ite_analyze_v2.py` — find_prior_analyses() rewrite, YoY improvements, NAMING CHECK, year-labeled outputs
- `03_module.3_analyst/scripts/ite_analyzer_v3.py` — v3.1 bug fix (AAFP query alias), concept_delta, data_quality flags confirmed working

### New Files Created
- `03_module.3_analyst/scripts/abfm_reference_2024.json` — 2024 ABFM national benchmarks (PGY1=414/±78, PGY2=462/±76, PGY3=494/±78, All=456/±84; 194 scored items; MPS=380; SEM=±38)
- Resident folder structure redesigned: `resident_data/ITE_{lastname}_{firstname}/inputs/` + `outputs/` (PDFs in inputs/, analysis files in outputs/)

---

## Report Builder Edits (ite_report_builder_v2.js)

### Pass 1 — 14 Structural/Design Edits
1. **Page order**: Score Analysis title page now first; Exam at a Glance injected after (via `examGlanceSection[]` pattern)
2. **Resident name**: `res.name` displayed under title on page 1
3. **Trend table**: Column widths recalculated to distribute evenly (eliminates rounding drift); legend line added
4. **Score band — no red fill**: Only green/blue bands get color fill; amber/red = neutral light gray (`F0F4F8`)
5. **Score band — passing only**: Confirmed — bandColor null for amber/red → no alarm coloring
6. **EXECUTIVE SUMMARY → EXAM SUMMARY**: Section bar renamed
7. **Tier text removed**: "placing in the X tier" clause deleted from summary
8. **Bullet list**: Exam Summary converted from prose studyNote to `•` bullet list
9. **Category name colors**: YoY table weak-row names changed from RED → DGRAY (bold); current % uses AMBER for weak
10. **Table consolidation**: Section 4a (ITE OVERVIEW TABLE) removed; Section 4b expanded to "BLUEPRINT & BODY SYSTEM PERFORMANCE" with body system table appended
11. **How-to moved**: Difficulty profile "How to read this section" legend moved BEFORE the summary table (not after)
12. **Difficulty colors fixed**: Easy Miss = GREEN (improvable), Hard Miss = RED (most also miss) — was reversed
13. **LHF methodology table**: 2-row explanation of "Improvable Items" and "Priority Score" added above LHF tables
14. **CCW methodology table**: Same explanation added to Category Crossover Weaknesses section

### Pass 2 — 4 Structural Edits + Bonus
15. **Blueprint columns simplified**: Removed "Relative" and "Confidence" columns → now Category, Correct, Total, Rate, SEM only
16. **Easy miss GREEN color**: QID detail table (individual easy misses) score column now GREEN (≥900 = bold, 700–899 = regular)
17. **Improvable items — whole numbers**: `Math.round()` applied throughout LHF tables (was `.toFixed(1)`)
18. **Body system LHF simplified**: Removed Exam Weight and Priority Score columns (no defined ABFM weighting for body systems) → Rank, Body System, Improvable Items only

**Bonus**: MPS question count added to Exam Summary bullets. Formula: `ceil((380/displayScaled - 1) × correct_count)` — linear approximation, accurate ±2 Qs in 330–480 scaled range. Shows "X additional correct answers needed to reach MPS" for below-MPS residents; "Above MPS by X points" for above.

---

## Pipeline Fixes (ite_analyze_v2.py)

- **`find_prior_analyses(output_dir, current_year)`**: Rewritten to take year as param, looks for `analysis_v2_{YYYY-1}.json` in same `outputs/` dir (was sibling-folder pattern — eliminated folder naming constraints)
- **`compute_longitudinal_delta()`**: Added None-safe pct delta, `data_quality` flags, `concept_delta` (top 10 diagnoses/drugs/guidelines from prior year for 🔁/🆕 badges)
- **NAMING CHECK block**: Validates `ITE_{lastname}_{firstname}/inputs/` + `outputs/` structure on each run; prints full example command on failure
- **Output filename pattern**: Now year-labeled — `analysis_v2_{exam_year}.json`, `score_analysis_{exam_year}.json`
- **Stage 2.5 call updated**: Passes `int(analysis.get("exam_year", 0))` to `find_prior_analyses()`

---

## Design Decisions Locked This Session

1. **Body system LHF table has no exam weight/priority score** — body systems lack ABFM-defined weighting; showing just improvable count is honest
2. **Score band colors: green/blue only** — below MPS should not be alarming red in a longitudinal report; neutral gray prevents defensive reactions from residents
3. **Improvable items = whole numbers** — fractional items (3.6) are fictitious precision; round to nearest
4. **Exam at a Glance after title** — better reader journey: orient yourself first, then see the national context, then dive into individual performance
5. **Linear MPS estimate is acceptable** — ABFM uses IRT but linear interpolation is accurate within ±2 Qs in the typical resident range; caveat displayed in document

---

## DB State (no changes this session)

| Table | Rows |
|-------|------|
| articles | 1,985 |
| questions (ITE) | 1,629 |
| aafp_questions | 1,221 |
| qid_art_xref | 2,470 |
| aafp_qid_art_xref | 864 |
| article_icd10 | 4,020 |
| question_icd10 | 5,218 |
| aafp_question_icd10 | 4,753 |
| clinical_pathways | 3,971 |
| pubmed_pmid_cache | 344 |
| article_icd10_vec | 1,757 |
| question_icd10_vec | 2,747 |
| icd10_vec | 2,219 |
| article_currency | 1,985 |

PDF library: VC_fail: 630 | VC_pass: 168 | local_lite: 117 | right_click: 58 | AAFP: 15 | Total: 988

---

## DEFERRED FLAGS

| Flag | Status | Description |
|------|--------|-------------|
| DEFERRED-YOY-ROBUSTNESS | ACTIVE | Month-by-month rollup edge-case handling in ite_analyzer_v3.py needs testing with dense temporal data |
| DEFERRED-PGY-BENCHMARKS | ACTIVE | Awaiting PGY 1-4 data from Mikey to integrate cohort benchmarks into reports |
| DEFERRED-PROGRAM-TREND | NEW | abfm_reference_YYYY.json `program_trend` values are null — Mikey to supply historical program aggregate scores |
| DEFERRED-RESIDENT-FOLDER-MIGRATION | NEW | Existing resident folders use old flat structure; new structure is inputs/outputs — existing folders not yet migrated |
| FLAG-33-NNN-RENAME | DEFERRED | nnn_XXXX ART-ID rename scheme — designed but not implemented |

---

## Next Steps

### Immediate (next session)
1. **Mikey to review** updated Pjetergjoka 2025 DOCX — confirm report design is satisfactory before continuing
2. **Program trend data** — Mikey to supply historical program aggregate scores for abfm_reference JSON files
3. **DEFERRED-YOY-ROBUSTNESS** — edge-case testing with dense temporal data in ite_analyzer_v3.py

### Short-term
4. **Resident folder migration** — migrate existing flat resident_data folders to inputs/outputs structure
5. **Module 5 setup** — Provision Supabase project, run migrations, sync SQLite → Supabase, deploy Railway FastAPI + Netlify
6. **DEFERRED-PGY-BENCHMARKS** — once Mikey provides PGY 1-4 data

### Notes
- Q: "are we able to calculate approximately how many more correct answers are needed to meet the MPS?" → YES, implemented as bonus in Exam Summary bullets
- Q: "where is historical vs program trend data coming from?" → national values from ABFM published ITE technical reports (public); program values = null until Mikey supplies historical aggregates

---

*BATON 054 written by Claude during session-housekeeping. Previous BATON 053 → baton_archive/.*
