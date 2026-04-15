# BATON_active_057
## Vector Integration, Unified Practice Question Table, DB Utilities

**Date:** 2026-04-15  
**Session focus:** Closed DEFERRED-VECTOR-TIER1-REWRITE; rewrote practice questions section; added db_connect.py utility; diagnosed Python alias issue.  
**Previous BATON:** BATON_active_056_20260414_resident_reorg_report_fixes_modular_vectors.md  
**Git hash (pre-commit):** 7256305 | **Branch:** main

---

## 1. What Happened This Session

Three closed deferred flags and one new utility:

### A. DEFERRED-VECTOR-TIER1-REWRITE — CLOSED
Integrated modular vector tables (`question_concepttag_vec`, `intersection_centroid_vec`) into Tier 1 of `match_practice_questions_v3()` in `03_module.3_analyst/scripts/ite_analyzer_v3.py`.

**Three new functions:**
1. `_build_concept_profile(db, wrong_qids)` — Averages embeddings from `question_concepttag_vec` for all resident missed questions; outputs single 1536-dim profile vector representing semantic weakness fingerprint.
2. `_centroid_dim_boost(db, dim, dim_type, profile_vec)` — For cross_tab dimensions only: loads `intersection_centroid_vec`, computes cosine similarity to resident profile, returns priority multiplier in `[CENTROID_BOOST_MIN=0.90, CENTROID_BOOST_MAX=1.20]`.
3. `_apply_concept_vec_bonus(db, all_candidates, profile_vec, weight=0.8)` — Post-pool: batch-loads `question_concepttag_vec` for all candidates, adds `cosine_sim × 0.8` to relevance_score.

**Integration points in `match_practice_questions_v3()`:**
- After wrong-QID loop: `concept_profile = _build_concept_profile(db, wrong_qids)`
- In dimension loop: `priority_score = raw × _centroid_dim_boost(...)` before T1/T1b/T2
- After T1c concept selection, before fingerprint bonus: `_apply_concept_vec_bonus(db, all_candidates, concept_profile)`

**Constants added:**
- `CONCEPT_VEC_BONUS_WEIGHT = 0.8`
- `CENTROID_BOOST_MIN = 0.90`
- `CENTROID_BOOST_MAX = 1.20`

**Vectors do NOT filter.** Same SQL WHERE clause gathers candidates. Vectors re-rank assembled pool by semantic proximity to resident's specific missed questions. All 5 tests in `test_v3_changes.py` pass.

### B. PRACTICE-Q-TWO-TABLE — CLOSED
Rewrote practice questions section in `03_module.3_analyst/scripts/ite_report_builder_v2.js`:
- Removed `singleQs`/`crossQs` split ("SINGLE WEAK AREA" and "CROSS-CATEGORY" tables were misleading).
- Added `PURPLE = "6B3FA0"` color constant for cross-category targeting.
- Added `targetingColor(targeting)` helper: BLUE = blueprint dim, GREEN = body system dim, PURPLE = cross-tab, AMBER = concept fingerprint.
- Added description paragraph explaining multi-signal selection model.
- Added stats line: `N questions · X ITE / Y AAFP BRQ · T1/T2/T3 counts · N weak areas covered`.
- Weak areas count from `yield_priorities` filtered to non-cross-tab dims (accurate count, e.g., 6 not 9).
- Single unified table sorted by `relevance_score` descending.

### C. db_connect.py — NEW UTILITY
Created `03_module.3_analyst/scripts/db_connect.py`:
- Uses SQLite URI mode with `immutable=1` — skips journal/lock file creation.
- Resolves DB path relative to script location (works from any working directory).
- Exports `open_db(path=None)` function and `db()` context manager.
- Fixes "unable to open database file" error when querying DB from Linux sandbox root.
- Self-tests with `python db_connect.py`.

**Usage:** `from db_connect import open_db; db = open_db(); cursor = db.cursor()`.

### D. Python PATH / Windows App Execution Aliases (DIAGNOSTIC)
Identified that `python` command wasn't resolving in Desktop Commander despite Python 3.12 in user PATH. Root cause: Windows App Execution Aliases for `python.exe` and `python3.exe` were enabled (Store stubs intercepting command). Mikey disabled both aliases in Settings → Apps → Advanced app settings → App execution aliases. `python.exe` now resolves correctly with full path or `.exe` extension in Desktop Commander.

### E. Scholl 2024 Analysis — RE-RUN
Re-ran Scholl 2024 analysis twice (vector integration verification, PQ table fix verification). Both clean runs: T1:18 T2:2 T3:0, no warnings.

---

## 2. Database State (No Changes)

| Table | Rows | Status |
|-------|------|--------|
| articles | 1,985 | ✓ |
| questions (ITE) | 1,629 | ✓ |
| aafp_questions | 1,221 | ✓ |
| qid_art_xref | 2,470 | ✓ |
| aafp_qid_art_xref | 864 | ✓ |
| article_icd10 | 4,020 | ✓ |
| question_icd10 | 5,218 | ✓ |
| aafp_question_icd10 | 4,753 | ✓ |
| clinical_pathways | 3,971 | ✓ |
| pubmed_pmid_cache | 344 | ✓ |
| article_icd10_vec | 1,757 | ✓ |
| question_icd10_vec | 2,747 | ✓ |
| icd10_vec | 2,219 | ✓ |
| article_currency | 1,985 | ✓ |
| question_concepttag_vec | 2,850 | ✓ |
| intersection_centroid_vec | 135 | ✓ |
| blueprint_label_vec | 5 | ✓ |
| bodysystem_label_vec | 5 | ✓ |
| question_full_vec | 1,629 | ✓ |
| aafp_question_full_vec | 1,221 | ✓ |

**Next ART-ID:** ART-1987

---

## 3. Code Changes Summary

### M3 Scripts (Analyst Module)

**New files:**
- `03_module.3_analyst/scripts/db_connect.py` — DB connection utility with immutable URI mode.

**Modified files:**
- `03_module.3_analyst/scripts/ite_analyzer_v3.py` — Added `_build_concept_profile()`, `_centroid_dim_boost()`, `_apply_concept_vec_bonus()` functions; three integration points in `match_practice_questions_v3()`.
- `03_module.3_analyst/scripts/ite_report_builder_v2.js` — Removed `singleQs`/`crossQs` split; added unified practice questions table with color-coded Targeting column.
- `03_module.3_analyst/scripts/test_v3_changes.py` — All 5 tests passing.

**Script counts remain:**
- M1 build py: 8 | M1 maintain py: 26
- M2 py: 75 | M2 js: 6
- M3 py: 18 | M3 js: 2 | M3 JSON config: 6

---

## 4. Closed Deferred Flags

### DEFERRED-VECTOR-TIER1-REWRITE — CLOSED
Vectors integrated into `match_practice_questions_v3()`. Tier 1/1b/2 candidate pool unchanged (same SQL). Vectors re-rank post-pool by semantic proximity. All tests pass.

### PRACTICE-Q-TWO-TABLE — CLOSED
Unified practice questions table implemented. Single table sorted by relevance_score, color-coded Targeting column, stats line showing weak areas covered. Replaced old singleQs/crossQs split.

---

## 5. Active Deferred Flags (Carry Forward)

### DEFERRED-YOY-ROBUSTNESS (ACTIVE)
Edge-case testing for year-over-year section in `ite_analyzer_v3.py`. Month-by-month rollup logic functional but untested on edge cases (same Q answered correctly Oct, incorrectly Nov; multiple exams within 7-day windows). Section usable for exploratory analysis; not blocking.
**Next action:** Add edge-case tests to `test_v3_changes.py`. Run on Scholl 3-year chain.

### DEFERRED-PGY-BENCHMARKS (ACTIVE)
PGY 1–4 cohort comparison data for Section 4 of resident report. Mikey to supply historical program aggregate scores.
**Next action:** Await data. Once received, integrate into resident report Section 4.

### DEFERRED-PROGRAM-TREND (ACTIVE)
Historical program aggregate scores for national vs. program comparison table. Mikey to supply year-by-year program mean scores.
**Next action:** Await data. Re-implement table once received.

### DEFERRED-RESIDENT-FOLDER-MIGRATION (PARTIALLY COMPLETE)
Two empty shell folders at project root (`ITE_adona_pjetergjoka_2024/`, `ITE_adona_pjetergjoka_2025/`) need Windows Explorer deletion. Not blocking.
**Next action:** Mikey to delete via Windows Explorer.

### FLAG-33-NNN-RENAME (DEFERRED, LOW PRIORITY)
`nnn_XXXX` ART-ID rename scheme. Designed, not implemented. Post-Module-5 refactor.

### DEFERRED-SCHOLL-OLD-FORMAT (ACTIVE)
Scholl 2022/2023 analyses use pre-2024 ABFM body system taxonomy (Adult Medicine, Care of Children, etc.) which doesn't map 1:1 to 5 canonical body systems. Body system filtering in practice question matching won't work for those years; blueprint filtering still functional.
**Next action:** Mikey to decide: (a) add old→new body system synonym mapping, or (b) skip body system filtering for pre-2024 years.

### DEFERRED-AAFP-BODY-SYSTEM-AUDIT (NEW — ACTIVE)
Issue identified from Scholl 2024 report review: AAFP-51071 is labeled Cardiovascular in the DB but is endocrine content. Root cause: AAFP question `body_system` field may have incorrect tags in the DB. Scope unknown — could be isolated or broader.
**Next action:** Run sweep of AAFP questions to identify mislabeled body systems. Write targeted UPDATE statements for confirmed errors.

### DEFERRED-KNOWN-DRUGS-EXPANSION (NEW — ACTIVE)
Drugs still appearing in top diagnoses table in resident reports. `KNOWN_DRUGS` set in `ite_analyzer_v3.py` is fixed explicit list (~40 entries) that doesn't catch all drug names generated by Claude in `concept_tags`. Options: (a) expand KNOWN_DRUGS with more entries, (b) add drug class suffix pattern matching (-olol, -pril, -statin, -mab, -flozin etc.).
**Next action:** Identify specific drug names appearing in reports. Decide on whack-a-mole vs suffix approach.

---

## 6. Critical Notes for Next Session

### Vector Bonus Is Post-Pool, Not a Filter
`_build_concept_profile()`, `_centroid_dim_boost()`, `_apply_concept_vec_bonus()` all run AFTER SQL candidate gathering. They re-rank, not replace, the Tier 1/1b/2 candidate pool. T3 (question_icd10_vec fallback) is still present but typically doesn't fire when pool fills from earlier tiers.

### db_connect.py for Sandbox DB Queries
Use `from db_connect import open_db; db = open_db()` for any inline diagnostic query from the Linux sandbox. The `immutable=1` URI mode is required — plain `sqlite3.connect(path)` fails from sandbox root due to journal file creation issues on NTFS mount.

### Practice Questions Table Is Now Unified
The `singleQs`/`crossQs` split is gone. One table, sorted by relevance_score, with color-coded Targeting column:
- BLUE = blueprint dimension targeting
- GREEN = body system dimension targeting
- PURPLE = cross-tab dimension targeting
- AMBER = concept fingerprint targeting

Weak area count comes from `yield_priorities` non-cross-tab entries only.

### AAFP Body System Field May Have Errors
AAFP-51071 is confirmed mislabeled (Cardiovascular in DB, actually endocrine content). Audit full AAFP bank before trusting body system filtering for AAFP questions.

### ICD-10 Enrichment Is Invisible
`icd10_profile` is a hidden scoring signal in `match_practice_questions_v3()`. Never displays in resident reports. This is intentional (Locked Rule 13).

### `_normalize_concept()` Fallback = First-Letter Capitalize ONLY
Never `.title()` — mangles acronyms (HIV → Hiv, IBS-D → Ibs-D). Pattern: `stripped[0].upper() + stripped[1:]`. Add new synonym entries for canonical forms that need resolution; don't change fallback.

### test_v3_changes.py Is the Canary
Run after any modification to `ite_analyzer_v3.py`. All 5 tests must pass before publishing resident analyses.

---

## 7. Next Steps (for next session)

### Immediate
1. **DEFERRED-AAFP-BODY-SYSTEM-AUDIT** — Run sweep of AAFP questions for mislabeled body systems; fix confirmed errors.
2. **DEFERRED-KNOWN-DRUGS-EXPANSION** — Identify offending drug names in reports; decide on fix approach (whack-a-mole vs suffix pattern).
3. **Re-run all 7 resident analyses** — Sarkar 2025, Hopkins 2025, Pjetergjoka 2024/2025, Scholl 2022/2023/2024 with new vector integration and unified PQ table.
4. **DEFERRED-SCHOLL-OLD-FORMAT decision** — Mikey to confirm body system alias strategy for 2022/2023.

### Short-term
5. **Module 5 setup** — Provision Supabase; run migrations; sync SQLite → Supabase; deploy Railway FastAPI + Netlify.
6. **DEFERRED-PGY-BENCHMARKS** — Await PGY 1-4 data from Mikey; integrate into resident report Section 4.
7. **DEFERRED-PROGRAM-TREND** — Await historical program aggregate scores; re-implement comparison table.
8. **DEFERRED-YOY-ROBUSTNESS** — Add edge-case tests for temporal rollup logic; run on Scholl 3-year chain.

---

## 8. Locked Rules (Unchanged from BATON 056)

1. Fix the data, not the code.
2. VC gate = sole criterion for right_click tier. DB membership alone is not sufficient.
3. Source data is protected. DB + PDFs + VC gate survive everything. Derived files are disposable.
4. Dynamic paths only. Python: `SCRIPT_DIR = Path(__file__).resolve().parent; PROJECT_ROOT = SCRIPT_DIR.parent.parent`. JS: `path.resolve(__dirname, "../../")`.
5. No de novo JS (relaxed — use when needed, flag if clutter accumulates).
6. BATON first. Read the active BATON before any work. It has deferred flags and current state.
7. QC after every integration. Schema-level column-by-column population comparison, old cohort vs new.
8. Git via Desktop Commander Python subprocess helper (`claude_knowledge/git_runner.py`). Cannot `rm` NTFS files — deletions still require Windows Explorer/terminal.
9. `shutil.rmtree` is BANNED. Use explicit file-by-file deletion or PowerShell Remove-Item. shutil.rmtree bypasses Recycle Bin and is irreversible.
10. Strategy 0 in every enricher. Codon parse is always the first matching strategy.
11. Schemas before scripts. SQL `CREATE TABLE` defined before build scripts are written.
12. `_normalize_concept()` fallback = first-letter capitalize ONLY. Never `.title()` — mangles acronyms. Pattern: `stripped[0].upper() + stripped[1:]`. Add new synonym entries for canonical forms; don't change fallback.
13. ICD-10 enrichment is invisible. `icd10_profile` is passed to `match_practice_questions_v3()` as a hidden scoring signal and must never appear in resident report.

---

## 9. Resident Analysis Status

Seven analyses remain in resident_data/:
- **Sarkar 2025** — Awaiting first report run with vector integration + unified PQ table.
- **Hopkins 2025** — Awaiting first report run with vector integration + unified PQ table.
- **Pjetergjoka 2024** — Awaiting first report run with vector integration + unified PQ table.
- **Pjetergjoka 2025** — Awaiting first report run with vector integration + unified PQ table.
- **Scholl 2024** — Re-run completed 2026-04-15; clean run, T1:18 T2:2 T3:0.
- **Scholl 2023** — Awaiting first report run with vector integration + unified PQ table (pre-2024 body system taxonomy issue).
- **Scholl 2022** — Awaiting first report run with vector integration + unified PQ table (pre-2024 body system taxonomy issue).

---

## 10. File Paths Reference

**Key files modified/created this session:**
- `03_module.3_analyst/scripts/db_connect.py` — NEW
- `03_module.3_analyst/scripts/ite_analyzer_v3.py` — MODIFIED (added 3 functions, 3 integration points)
- `03_module.3_analyst/scripts/ite_report_builder_v2.js` — MODIFIED (removed singleQs/crossQs, added unified table)
- `03_module.3_analyst/scripts/test_v3_changes.py` — PASSING (5/5 tests)

**Ground-truth files:**
- `00_database/db/ite_intelligence.db` — Protected source of truth
- `key_data_files/session_hy_inserts_v7.json` — VC gate (352 citations)
- `00_#PROJECT_OVERHAUL/_index.md` — Directory map

---

## 11. Handoff Checklist

- [x] DEFERRED-VECTOR-TIER1-REWRITE closed; vectors wired into Tier 1 matching
- [x] PRACTICE-Q-TWO-TABLE closed; unified table implemented with stats and color-coded targeting
- [x] db_connect.py utility created; immutable URI mode documented
- [x] Python alias issue diagnosed and resolved (Mikey disabled Store stubs)
- [x] Scholl 2024 analysis re-run and clean (T1:18 T2:2 T3:0)
- [x] All 5 tests in test_v3_changes.py passing
- [x] Six new deferred flags documented: AAFP-BODY-SYSTEM-AUDIT, KNOWN-DRUGS-EXPANSION
- [x] Next steps clear: AAFP audit, drug expansion, re-run 7 resident analyses, Scholl old-format decision
- [x] All locked rules carried forward unchanged

**Ready for next session.**
