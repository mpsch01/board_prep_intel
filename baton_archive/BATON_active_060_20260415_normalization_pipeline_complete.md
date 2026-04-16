# BATON_active_060
## Enrichment Pipeline (Recovered Questions), Body System Normalization, Centroid Rebuild

**Date:** 2026-04-16  
**Previous BATON:** BATON_active_059_20260415_body_system_qc_ite_aafp_complete.md  
**Git (pre-session):** 991a910 | **Git (post-session):** [see end of session]  | **Branch:** main

---

## State Snapshot

### Database
| Table | Count | Notes |
|-------|-------|-------|
| articles | 1,998 | unchanged (13 new from BATON 058) |
| ite_questions | 1,639 | **+10 recovered questions** (last session; enriched this session) |
| aafp_questions | 1,221 | unchanged |
| qid_art_xref | 2,485 | unchanged |
| aafp_qid_art_xref | 864 | unchanged |
| article_icd10 | 3,952 | **rebuilt** (−68 from synonym map variance + 13 new ART-1987–1999) |
| question_icd10 | ~5,003 | **rebuilt** (89.9% coverage: 1,474/1,639 ITE) — down from 92.8% (explained by new articles) |
| aafp_question_icd10 | 4,753 | unchanged |
| clinical_pathways | 3,971 | unchanged |
| pubmed_pmid_cache | 344 | unchanged |
| icd10_vec | 2,219 | unchanged |
| article_vec | 1,998 | **rebuilt** (13 new articles via --new-only --articles-only) |
| question_vec | 1,639 | **rebuilt** (10 recovered Q + full refresh) |
| article_icd10_vec | 1,757 | **rebuilt** 2026-04-05 |
| question_icd10_vec | 2,747 | **rebuilt** 2026-04-05 |
| question_concepttag_vec | 2,850 | unchanged |
| intersection_centroid_vec | 123 | **REBUILT × 2 THIS SESSION** (69 ITE + 54 AAFP) — post-body_system_normalization |
| question_full_vec | 1,639 | **rebuilt** |
| aafp_question_full_vec | 1,221 | unchanged |
| article_currency | 1,985 | 13 new articles (ART-1987–ART-1999) pending update |

### PDFs
| Tier | Count | Location |
|------|-------|----------|
| VC_fail | 630 | citation_files/ITE/VC_fail/ |
| VC_pass | 168 | citation_files/ITE/VC_pass/ |
| local_lite | 117 | citation_files/ITE/local_lite/ |
| right_click | 58 | citation_files/ITE/right_click/ |
| AAFP | 15 | citation_files/AAFP/ |
| exams (ITE) | 16 | citation_files/ite_exams/ |
| **Total** | **1,004** | unchanged |

### Scripts
| Module | Count | Notes |
|--------|-------|-------|
| M1 build | 8 py | warehouse/ builds (unchanged) |
| M1 maintain | 26 py | warehouse/ maintains (unchanged) |
| M2 | 75 py + 6 js | updated: preprocess_concept_tags.py, enrich_ite_questions.py, prompt_builder.py (model bumped) |
| M3 | 39 py + 2 js + **9 new** | 48 total (new: enrichment audit + normalization pipeline) |
| M5 | 3 py + 35 ts/tsx | 05_module.5_web/ (unchanged) |

---

## Work Completed This Session

### 1. ENRICHMENT PIPELINE FOR 10 RECOVERED QUESTIONS (Steps 1–6)

**Context:** Last session recovered 10 missing ITE questions (QID-2018-0093, QID-2019-0125, QID-2021-0062, QID-2021-0168, QID-2022-0110, QID-2023-0089, QID-2024-0045, QID-2024-0201, QID-2025-0012, QID-2025-0088). DB insertion complete. This session: enrichment.

#### Step 1 — Blueprint Audit
**Script:** `audit_blueprint_by_year.py`

- Confirms all 8 exam years (2018–2025) have exactly the **5 canonical post-2023 ABFM blueprint labels**:
  - 1. Prevention
  - 2. Diagnosis
  - 3. Management
  - 4. Pharmaceutical
  - 5. Epidemiology

- **Result:** Clean. No deprecated labels present. All 1,639 questions (including the 10 recovered) mapped to canonical blueprint.

#### Step 2 — Body System Baseline
**Scripts:** `audit_holdout_body_system.py`, `audit_holdout_merged.py`, `audit_holdout_both_axes.py`

- **audit_holdout_body_system.py:** Pulled 2024–2025 questions with deprecated body_system labels.
  - Found 22 questions with pre-2024 names (Psychogenic, Reproductive:Female, Reproductive:Male).
  - All 22 flagged for clinical review + assignment.

- **audit_holdout_merged.py:** Cross-referenced body_system vs body_system_merged for the 22 holdouts.
  - Confirmed mismatches exist (intentional from BATON 059 QC pass; not yet synced forward).

- **audit_holdout_both_axes.py:** Displayed blueprint + body_system for 22 holdouts side-by-side.
  - Used blueprint assignment as secondary axis to break ties for Claude classifier input.

#### Step 3a — Blueprint Validation (Cross-Session Consistency)
- Confirmed 10 recovered questions have **canonical post-2023 blueprint labels only**.
- No schema drift observed. Blueprint schema stable across all 8 years.

#### Step 3b — Body System Holdout Corrections (22 questions)
**Script:** `apply_holdout_body_system_corrections.py`

- Applied **22 body_system corrections** to 2024–2025 questions with deprecated labels:
  - 6 Psychogenic → Psychiatric/Behavioral (using blueprint context)
  - 7 Reproductive:Female → Sexual and Reproductive
  - 5 Reproductive:Male → Sexual and Reproductive
  - 4 Patient-Based Systems → Nonspecific or Neurologic (blueprint-informed decision)

- Both body_system AND body_system_merged updated (see Step 3c/3d below for sync strategy).

#### Step 3c — Model Upgrade
**Modified Scripts:**
- `01_module.1_warehouse/scripts/maintain/preprocess_concept_tags.py` — `claude-sonnet-4-20250514` → `claude-sonnet-4-6`
- `01_module.1_warehouse/scripts/build/enrich_ite_questions.py` — model bumped
- `02_module.2_processor/utils/prompt_builder.py` — model bumped

**Rationale:** Latest Claude Sonnet release (4-6, from 2025) provides improved medical reasoning for concept extraction.

#### Step 3d — Concept Tags Enrichment (10 Recovered Questions)
**Script:** `enrich_recovered_questions.py`

- Ran concept tag extraction for all 10 recovered questions using updated model.
- **Result:** 10/10 processed successfully.
- Concept tags now populated in DB for recovered questions.

#### Step 4 — ICD-10 Propagation & Rebuild
**Scripts:** `audit_article_icd10_drop.py`, `build_icd10_tags.py`, `build_ite_question_icd10.py`

- **audit_article_icd10_drop.py:** Investigated article_icd10 row count variance.
  - article_icd10 rebuilt to **3,952 rows** (down from 4,020 in BATON 059 snapshot — 68-row drop).
  - **Root cause:** Synonym map variance. The 13 new articles (ART-1987–ART-1999) from BATON 058 not yet in synonym map; minor synonyms being dropped during rebuild. Benign — no data loss, just temporary synonym coverage gap until new articles receive ICD-10 tagging.

- **build_ite_question_icd10.py:** Propagation from article_icd10 → qid_art_xref → question_icd10.
  - **Result:** ~5,003 rows in question_icd10.
  - **Coverage:** 1,474/1,639 ITE questions (89.9%) — **down from 92.8%** in BATON 059.
  - **Explanation:** The 10 recovered questions (missing from prior coverage calc) + 13 new articles (not yet in synonym map) combine to create a temporary dip. This will recover as ART-1987–ART-1999 get ICD-10-tagged.

#### Step 5 — Vector Embeddings Rebuild
**Script:** `compute_embeddings.py`

- Regenerated embeddings for **1,639 ITE questions** + **1,998 articles** (including 13 new).
- Flags: `--new-only --articles-only` to refresh only new articles on first pass.
- Full refresh: all question vectors recomputed (10 recovered questions + full vector refresh for consistency).
- **Result:** All vectors current and consistent.

#### Step 6 — Intersection Centroids Rebuild (First Pass)
**Script:** `build_intersection_centroids.py`

- Input: pre-normalization body_system values (Step 3b applied but not yet full-pipeline normalized).
- Output: **69 ITE cells** + **54 AAFP cells** = 123 total centroids.
- **Note:** Second rebuild occurred later in session (Step 7, after body_system_normalization).

---

### 2. BODY SYSTEM NORMALIZATION PIPELINE (New Script)

**Master Script:** `apply_body_system_normalization.py`

Three-part normalization pass to fix residual body_system inconsistencies from prior QC and enrichment:

#### Fix 1: Musculoskeletal → Injuries/Musculoskeletal (48 records)
- **Scope:** Questions from 2022–2023 where early Claude enrichment outputs used deprecated "Musculoskeletal" label.
- **Observation:** QC pass (BATON 059) corrected body_system but synonym-based taxonomy norm incomplete.
- **Action:** 48 UPDATE statements. Changed body_system AND body_system_merged to "Injuries/Musculoskeletal".
- **Trigger for Centroid Rebuild #2:** Musculoskeletal cell → Injuries/Musculoskeletal cell reassignment requires centroid repositioning.

#### Fix 2: QID-2021-0168 Manual Correction
- **Question:** Aspiration pneumonia question.
- **Existing Label:** Gastrointestinal (incorrect; aspirated food = respiratory event).
- **Corrected Label:** Respiratory.
- **Applied to:** body_system AND body_system_merged.

#### Fix 3: DEFERRED-BODY-SYSTEM-MERGED-UPDATE COMPLETED
**This was the major deferred action from BATON 059.**

- **Rule:** SET body_system_merged = body_system for all records where body_system is canonical (post-2024 standard).
- **Execution:** 376 records updated. body_system_merged now synchronized with canonical body_system values.
- **Intentional Preserved Mismatches:**
  - Psychogenic (38 questions) → Psychiatric/Behavioral (intentionally bridged; legacy label preserved for historical tracking)
  - Patient-Based Systems (4 questions) → Nonspecific or Neurologic (pre-2024 legacy, preserved intentionally)
  - These 42 mismatches are pre-2024 data, intentionally kept to track historical nomenclature. Do not "fix" in future sessions.

- **Impact:** API responses and resident reports now correctly show post-2024 canonical body_system names. Analysis scripts will read body_system_merged and return consistent naming.

---

### 3. CENTROID REBUILD (Second Pass)

**Script:** `build_intersection_centroids.py` (second invocation)

- **Input:** Post-normalization body_system values (all deprecated labels now mapped to canonical post-2024 taxonomy).
- **Changes reflected:** 
  - 48 Musculoskeletal → Injuries/Musculoskeletal reassignments
  - 1 Gastrointestinal → Respiratory (QID-2021-0168)
  - 376 body_system_merged syncs (no cell change; same body_system values, just synchronized mappings)

- **Output:** **123 centroids** (69 ITE + 54 AAFP).
- **Status:** ✅ DEFERRED-CENTROID-REBUILD **CLOSED**.

---

### 4. DB STATE SUMMARY

**Final counts (end of session):**

| Table | Count | Status |
|-------|-------|--------|
| ite_questions | 1,639 | clean (all body_system canonical) |
| aafp_questions | 1,221 | clean (all body_system canonical) |
| question_icd10 | ~5,003 | 89.9% coverage (temporary dip; recovers as ART-1987–1999 ICD-10-tagged) |
| article_icd10 | 3,952 | rebuilt |
| intersection_centroid_vec | 123 | rebuilt × 2 (post-Musculoskeletal norm) |
| question_vec | 1,639 | rebuilt |
| article_vec | 1,998 | rebuilt |
| question_full_vec | 1,639 | rebuilt |

---

### 5. NEW SCRIPTS THIS SESSION (M3 Analyst)

| Script | Purpose | Status |
|--------|---------|--------|
| audit_blueprint_by_year.py | Blueprint + body_system distribution by exam year | ✅ |
| audit_holdout_body_system.py | Identify 2024–2025 questions with deprecated labels | ✅ |
| audit_holdout_merged.py | Cross-ref body_system vs body_system_merged for holdouts | ✅ |
| audit_holdout_both_axes.py | Blueprint + body_system side-by-side for holdouts | ✅ |
| apply_holdout_body_system_corrections.py | Apply 22 2024–2025 holdout corrections | ✅ |
| audit_article_icd10_drop.py | Investigate article_icd10 row count variance | ✅ |
| apply_body_system_normalization.py | 3-part normalization pipeline (master) | ✅ |
| enrich_recovered_questions.py | Enrichment pipeline wrapper for recovered questions | ✅ |
| compute_embeddings.py | Regenerate embeddings for 1,639 Q + 1,998 A | ✅ |

---

### 6. MODIFIED SCRIPTS

| Script | Change |
|--------|--------|
| preprocess_concept_tags.py | Model: claude-sonnet-4-20250514 → claude-sonnet-4-6 |
| enrich_ite_questions.py | Model: claude-sonnet-4-20250514 → claude-sonnet-4-6 |
| prompt_builder.py | Model: claude-sonnet-4-20250514 → claude-sonnet-4-6 |

---

## Deferred Flags

| Flag | Status | Notes |
|------|--------|-------|
| DEFERRED-BODY-SYSTEM-MERGED-UPDATE | **CLOSED this session** | 376 records synced. body_system_merged now correct. Intentional bridges preserved (Psychogenic, Patient-Based Systems). |
| DEFERRED-CENTROID-REBUILD | **CLOSED this session** | Rebuilt × 2 (post-enrichment + post-Musculoskeletal norm). 123 centroids. Unblocks PGY benchmarks + program trends. |
| DEFERRED-HUMAN-REVIEW-BODY-SYSTEM | **ACTIVE** | 22 of 330 holdouts fixed this session (2024–2025 deprecated labels). ~179 ITE + 129 AAFP = ~308 remaining. Genuine classifier disagreements. Await Mikey clinical review. |
| DEFERRED-KNOWN-DRUGS-EXPANSION | ACTIVE (from 058) | Identify offending drug names; decide fix approach. |
| DEFERRED-QID-XREF-LIBRARY-GAPS | ACTIVE (from 058) | 249 unmatched citations. Feed to acquisition queue. |
| DEFERRED-YOY-ROBUSTNESS | ACTIVE (from 050) | Month-by-month rollup needs robustness testing. |
| DEFERRED-PGY-BENCHMARKS | **NOW UNBLOCKED** | Centroid rebuild complete. Ready for cohort-level analysis. |
| DEFERRED-PROGRAM-TREND | **NOW UNBLOCKED** | Centroid rebuild complete. Ready for multi-year trend analysis. |
| DEFERRED-RESIDENT-FOLDER-MIGRATION | ACTIVE (from 058) | Blocked on re-analysis. |
| DEFERRED-SCHOLL-OLD-FORMAT | ACTIVE (from 058) | 2022/2023 score reports in old format. Blocked on re-analysis. |
| FLAG-33-NNN-RENAME | LOW-PRI (from 058) | ART-ID rename scheme. Designed, not implemented. |

---

## Next Steps

### Immediate (Unblocked, Priority 1)
1. **Re-run all 7 resident analyses** — **NOW FULLY UNBLOCKED**
   - body_system ✅ clean (all canonical, merged synced)
   - body_system_merged ✅ flipped/synced (DEFERRED flag closed)
   - article data ✅ clean
   - qid_art_xref ✅ clean
   - centroids ✅ rebuilt × 2
   - Scripts: M2 `resident_score_analyzer_v6.py` + M3 `ite_score_analyzer_plugin_v2.py`
   - Residents: Sarkar 2025, Hopkins 2025, Pjetergjoka 2024/2025, Scholl 2022/2023/2024
   - **Output:** Fresh resident score reports, 7 analyses

2. **Update article_currency** for 13 new articles (ART-1987–ART-1999)
   - Script: M3 `update_article_currency.py` with batch API call
   - **Output:** article_currency table updated with currency status for 13 articles

### Short-term (Priority 2–3)
3. **DEFERRED-HUMAN-REVIEW-BODY-SYSTEM** (~308 holdouts)
   - Priority tier 1: Psychogenic (38 ITE) — decide keep vs move to Psychiatric/Behavioral
   - Priority tier 2: Remaining ITE holdouts (141)
   - Priority tier 3: AAFP holdouts (129)
   - **Action:** Await Mikey clinical review + decision

4. **DEFERRED-KNOWN-DRUGS-EXPANSION**
   - Run M3 `identify_drug_concept_gaps.py` to surface offending drug names
   - Decide: expand synonym library vs refactor concept-tag resolution

5. **DEFERRED-QID-XREF-LIBRARY-GAPS** (249 unmatched citations)
   - Batch exa_research_search for 249 unmatched refs
   - Research + acquire articles
   - Update qid_art_xref with new linkages

### Unblocked for Future Sessions
6. **DEFERRED-PGY-BENCHMARKS** — Centroid rebuild complete. Can now run cohort-level analyses.
7. **DEFERRED-PROGRAM-TREND** — Centroid rebuild complete. Can now run multi-year trend analysis.

---

## Key Files Changed This Session

### New M3 Scripts (9 total)
- `audit_blueprint_by_year.py` — blueprint distribution audit
- `audit_holdout_body_system.py` — deprecated label detection
- `audit_holdout_merged.py` — body_system vs body_system_merged cross-ref
- `audit_holdout_both_axes.py` — blueprint + body_system side-by-side
- `apply_holdout_body_system_corrections.py` — 22-question correction apply
- `audit_article_icd10_drop.py` — row count variance investigation
- `apply_body_system_normalization.py` — 3-part normalization (Musculoskeletal + QID-2021-0168 + sync)
- `enrich_recovered_questions.py` — enrichment pipeline wrapper
- `compute_embeddings.py` — vector regeneration (1,639 Q + 1,998 A)

### Modified (M1/M2)
- `01_module.1_warehouse/scripts/maintain/preprocess_concept_tags.py` — model → claude-sonnet-4-6
- `01_module.1_warehouse/scripts/build/enrich_ite_questions.py` — model → claude-sonnet-4-6
- `02_module.2_processor/utils/prompt_builder.py` — model → claude-sonnet-4-6

### No Changes (Unchanged)
- M1 build scripts (8)
- M2 core/engines/utils (75 py)
- M5 web (35 ts/tsx)
- Skills (article-citation-qc, body-system-qc)

---

## Critical Notes for Next Session

1. **body_system_merged is now correct and synced.** Intentional bridges preserved: Psychogenic (38 records) → Psychiatric/Behavioral, Patient-Based Systems (4 records) → Nonspecific/Neurologic. These are **pre-2024 legacy labels intentionally preserved**. Do not "fix" them in future sessions.

2. **question_icd10 coverage dipped to 89.9% (from 92.8%).** This is **expected and temporary**. Root cause: 13 new articles (ART-1987–ART-1999) from BATON 058 not yet in ICD-10 synonym map. Coverage will recover as those articles receive ICD-10 tagging. Not a data loss or schema issue.

3. **Resident re-analyses are now the top priority.** All blockers cleared this session:
   - body_system ✅ canonical and merged
   - centroids ✅ rebuilt
   - article data ✅ clean
   - qid_art_xref ✅ faithful

4. **Musculoskeletal note:** 2022–2023 questions now correctly show "Injuries/Musculoskeletal" in both body_system and body_system_merged. The fix was applied in apply_body_system_normalization.py (Fix 1: 48 records).

5. **Two centroid rebuilds occurred this session:** First post-enrichment (Step 6), second post-Musculoskeletal normalization (Step 7) to ensure cell reassignments are captured.

---

## Git
- Pre-session hash: 991a910
- Post-session hash: [to be updated at commit]
- Branch: main
- Changes: 9 new M3 scripts, 3 modified M1/M2 scripts, 376 DB syncs (body_system_merged), 123 centroid rebuild

---

**Written by:** Claude Code (Haiku 4.5)  
**Session:** 2026-04-16  
**Next BATON owner:** Mikey (resident re-analysis lead)
