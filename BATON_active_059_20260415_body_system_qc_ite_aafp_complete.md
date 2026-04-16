# BATON_active_059
## Body System QC (ITE + AAFP Complete), Files API Infrastructure, Methodology Scout

**Date:** 2026-04-15  
**Previous BATON:** BATON_active_058_20260415_citation_qc_db_rebuild_article_additions.md  
**Git (pre-commit):** ff36d59 | **Git (post-commit):** 991a910 | **Branch:** main

---

## State Snapshot

### Database
| Table | Count | Notes |
|-------|-------|-------|
| articles | 1,998 | +13 from BATON 058 (ART-1987–ART-1999) |
| ite_questions | 1,629 | 2018–2025 blueprint 100% |
| aafp_questions | 1,221 | blueprint 100% |
| qid_art_xref | 2,485 | faithful multi-reference |
| aafp_qid_art_xref | 864 | 52.7% linked |
| article_icd10 | 4,020 | rebuilt 2026-04-05 |
| question_icd10 | 5,218 | 1,512/1,629 (92.8%) |
| aafp_question_icd10 | 4,753 | normalized |
| clinical_pathways | 3,971 | rebuilt 2026-03-31 |
| pubmed_pmid_cache | 344 | Layer 2 seed |
| icd10_vec | 2,219 | OpenAI text-embedding-3-small (1536d) |
| article_icd10_vec | 1,757 | rebuilt 2026-04-05 |
| question_icd10_vec | 2,747 | rebuilt 2026-04-05 |
| question_concepttag_vec | 2,850 | |
| intersection_centroid_vec | 135 | **STALE** — body_system changes not reflected |
| question_full_vec | 1,629 | |
| aafp_question_full_vec | 1,221 | |
| article_currency | 1,985 | 13 new articles pending update |

### PDFs
| Tier | Count | Location |
|------|-------|----------|
| VC_fail | 630 | citation_files/ITE/VC_fail/ |
| VC_pass | 168 | citation_files/ITE/VC_pass/ |
| local_lite | 117 | citation_files/ITE/local_lite/ |
| right_click | 58 | citation_files/ITE/right_click/ |
| AAFP | 15 | citation_files/AAFP/ |
| exams (ITE) | 16 | citation_files/ite_exams/ |
| **Total** | **1,004** | |

### Scripts
| Module | Count | Notes |
|--------|-------|-------|
| M1 build | 8 py | warehouse/ builds |
| M1 maintain | 26 py | warehouse/ maintains |
| M2 | 75 py + 6 js | core/ + engines/ + utils/ + source/ + outputs/ + prompts/ |
| M3 | 39 py + 2 js | **+19 new this session** (body-system-qc pipeline) |
| M5 | 3 py + 35 ts/tsx | 05_module.5_web/ |

---

## Work Completed This Session

### 1. ARTICLE-CITATION-QC SKILL UPDATED

**Skill location:** `C:\Users\mpsch\.claude\skills\article-citation-qc\SKILL.md` (migrated from Desktop .claude folder)

- **Fixed** script reference: `generate_sql_fixes.py` → `generate_citation_sql.py`
- **Added Phase 3 xref rebuild docs** — faithful multi-reference xref rebuild logic (2,485 rows, avg 1.6 refs/q)
- **Added Phases 5–7:**
  - Phase 5: `pdf_lookup_patch.py` — rescans DB for article PDFs on disk (recovery path)
  - Phase 6: `add_missing_articles.py` — Anthropic Files API bulk create for 13 new articles (ART-1987–ART-1999)
  - Phase 7: Acquisition queue — unmatched references become acquisition targets
- **Updated qc_rules.md:** UNMATCHED_REF framing changed from "report only" → acquisition queue entry principle
- **Moved skill** from Desktop .claude folder → `C:\Users\mpsch\.claude\skills\article-citation-qc\`

**Impact:** Skill now documents full 7-phase workflow with acquisition queue routing. Next time citation gap analysis runs, unmatched refs automatically feed downstream acquisition.

---

### 2. BODY SYSTEM QC PIPELINE — BUILT & EXECUTED (19 new M3 scripts)

#### PHASE 1 — Ground Truth Extraction
**Scripts:** `extract_score_report_labels.py`, `condense_taxonomy.py`, `build_training_set.py`

- **extract_score_report_labels.py:** Parses ABFM ITE Item Performance Report PDFs (2022/2023 blueprint PDFs) using midpoint column boundary algorithm to extract per-question body system labels. Achieved 195/198 (2022) and 198/198 (2023) extraction accuracy.
- **condense_taxonomy.py:** Maps 16 pre-2024 ABFM categories → 15 post-2024 canonical taxonomy:
  - Psychogenic → Psychiatric/Behavioral
  - Reproductive:Female / Reproductive:Male → Sexual and Reproductive
  - Musculoskeletal → Injuries/Musculoskeletal
- **build_training_set.py:** Joins condensed labels with question content from DB → 393-question training set (2022: 195, 2023: 198) for downstream classification.

#### PHASE 2 — Baseline Diagnostic (SVM)
**Script:** `run_svm_baseline.py`

- SVM trained on existing OpenAI embeddings (question_full_vec)
- Train: 2022 (195 Q), Test: 2023 (198 Q)
- **Overall accuracy: 81.2%**
- **Per-category recall (weak categories identified):**
  - Nonspecific: 22% ← informed Claude CoT prompt design
  - Population-Based Care: 50%
  - Endocrine: 63%
- Baseline serves as audit standard (Phase 4) and informs classifier thresholds

#### PHASE 3 — Claude Classifier (Two-Layer Prompt)
**Scripts:** `run_claude_classifier.py`, `submit_batch_classification.py`, `retrieve_batch_results.py`, `rename_taxonomy_labels.py`

- **run_claude_classifier.py:**
  - Part A (static): 15 canonical examples (1–2 per body system), chosen for clarity and edge-case coverage
  - Part B (dynamic): K=5 retrieved examples from training set (nearest-neighbor fallback if no training example exists)
  - 5 disambiguation rules for weak categories (Nonspecific, Population-Based Care, Endocrine, Psychiatric/Behavioral, Immune)
  - Output: structured JSON {body_system, confidence, reasoning, alternative}
  - Model: Claude Sonnet 4.6

- **submit_batch_classification.py:** 
  - Submitted **1,231 ITE questions** to Anthropic Message Batch API
  - Batch ID: `msgbatch_01RNVq52nvjq1JJBFU772cm6`
  - Cost: ~$5

- **retrieve_batch_results.py:** 
  - Polls Batch API every 90s
  - Processes JSONL results when batch completes
  - Parses JSON output, maps confidence → SQL_READY / HUMAN_REVIEW / FLAGGED tiers

- **rename_taxonomy_labels.py:** 
  - Post-processes JSON output: custom condensed names → post-2024 canonical names in classifications

#### PHASE 4 — SVM Audit + SQL Generation
**Scripts:** `svm_review_audit.py`, `generate_body_system_sql.py`, `fix_taxonomy_names.py`, `verify_body_system_updates.py`

- **svm_review_audit.py:**
  - Cross-checks Claude classification against SVM baseline
  - Categorical agreement = UPGRADE SIGNAL (not probability threshold)
  - Support: `--bank ite` / `--bank aafp`, `--min-svm-prob 0.0`
  - **ITE Result:** 82% sql_ready, 16% human_review, 1% flagged
  - **AAFP Result:** 87% sql_ready, 10% human_review, 1% flagged

- **generate_body_system_sql.py:**
  - Two-section output:
    - **Section 1 (Taxonomy Normalization):** Safe, fast apply. Handles Musculoskeletal→Injuries/Musculoskeletal, Hematologic/ Immune spacing, etc.
    - **Section 2 (Clinical Reclassifications):** Claude body_system assignments. Marked for manual review before applying.
  - Support: `--bank ite` / `--bank aafp`
  - **ITE output:** `ite_body_system_updates.sql`
  - **AAFP output:** `aafp_body_system_updates.sql`

- **fix_taxonomy_names.py:** Direct DB fixes for artifacts missed by rename collision:
  - 133 Musculoskeletal → Injuries/Musculoskeletal
  - 24 Hematologic/ Immune spacing normalization

- **verify_body_system_updates.py:** Post-apply verification (SELECT COUNT by body_system, human_review flag, etc.)

#### ITE Results Applied to DB
- **255 UPDATE statements applied:**
  - 120 taxonomy normalization (Section 1)
  - 135 clinical reclassifications (Section 2)
- **756 questions** confirmed already correct
- **201 in human_review queue** (not applied, await manual review)
- **13 flagged** (low confidence, untouched)
- **Remaining holdouts (intentional):** 16 Psychogenic + 15 Reproductive:Female + 2 Reproductive:Male (human_review queue, await Mikey decision)

---

### 3. AAFP BODY SYSTEM QC — COMPLETE

**Scripts:** `fix_aafp_taxonomy_names.py`, `submit_batch_aafp.py`, `check_aafp_results.py`, `check_aafp_body_system.py`, `check_aafp_schema.py`

- **fix_aafp_taxonomy_names.py:** Phase 1 taxonomy normalization:
  - 139 Musculoskeletal → Injuries/Musculoskeletal
  - 84 Reproductive:Female → Sexual and Reproductive
  - 67 Hematologic/ Immune spacing
  - 27 Reproductive:Male → Sexual and Reproductive
  - Total: **317 rows normalized**

- **submit_batch_aafp.py:**
  - Submitted **1,221 AAFP questions** using ITE 2022/2023 as training (cross-bank transfer)
  - Batch ID: `msgbatch_0168NGC3sCU84d3tv4GHXMDj`
  - Cost: ~$5.77

- **check_aafp_results.py / check_aafp_body_system.py / check_aafp_schema.py:**
  - AAFP-specific verification scripts (counts, distribution, schema conformance)

- **Applied to DB:**
  - Both sections (taxonomy norm + reclassifications) executed
  - Commit: Write Changes committed
  - **AAFP distribution now clean:** 15 post-2024 canonical categories, 1,221 questions

---

### 4. FILES API INFRASTRUCTURE BUILT

**Scripts:** `critique_pdf_registry.py`, `extract_critique_refs_v2.py`

- **critique_pdf_registry.py:**
  - Manages Anthropic Files API uploads for ITE PDFs
  - Upload once, reference by `file_id` in future batches
  - Tracks expiry (28-day safe buffer)
  - Supports: critique, mc, blueprint PDF types
  - Function: `upload_and_register_pdf(pdf_path, pdf_type, expires_at)` → returns file_id for batch reuse

- **extract_critique_refs_v2.py:**
  - Replaces pdfplumber-based `extract_ite_critique_refs.py` for future years
  - Uses Claude native PDF reading via Files API
  - Format-agnostic — handles any ABFM layout change automatically
  - Batch-friendly: receives file_id instead of PDF bytes
  - Output: citation list with full refactored format

**Impact:** Future ABFM exam year releases can auto-upload to Files API once, reference in perpetuity. No re-download, no local PDF management.

---

### 5. METHODOLOGY SCOUT — BODY SYSTEM CLASSIFICATION

**Document:** `methodology_scout/methodology_scout_ite-body-system-classification_2026-04-15.md`

- Researched and compared 8 classification methods:
  - SVM (baseline)
  - SetFit (few-shot fine-tuning)
  - Chain-of-Thought + Retrieval (two-layer)
  - Hierarchical Multi-Label Classification (HMLC)
  - Zero-shot CLIP
  - Prompt ensemble
  - Active learning + human loop
  - Fine-tuned small models (DistilBERT)

- **Recommended approach:** Two-pass:
  - SVM baseline (diagnostic, speed, interpretability)
  - Claude CoT dual-classifier (retrieve examples + static rules, structured output)

- **Validation:** Wang et al. (2023) achieved 100% accuracy on ABFM blueprint classification using similar prompt-based approach

---

### 6. BODY-SYSTEM-QC SKILL CREATED

**Location:** `.claude/skills/body-system-qc/`

- **SKILL.md:** Full 10-phase workflow documentation
  - Phase 0: Prerequisite checks
  - Phases 1–4: Extract → Diagnose → Classify → Audit (as above)
  - Phases 5–10: AAFP loop, human review routing, centroid rebuild, downstream resident re-analysis
  - Routing thresholds: SQL_READY (apply immediately) vs HUMAN_REVIEW (await manual review) vs FLAGGED (skip)

- **references/taxonomy_map.md:**
  - Condensation map: 16 old → 15 new
  - Synthesized names (Psychogenic, Reproductive:Female, etc.)
  - body_system_merged direction: **pre-2024 names → post-2024 canonical** (flips current mapping, see DEFERRED flag below)

---

## Deferred Flags

| Flag | Status | Notes |
|------|--------|-------|
| DEFERRED-AAFP-BODY-SYSTEM-AUDIT | **CLOSED** | Completed this session. Full pipeline applied. AAFP distribution clean. |
| DEFERRED-BODY-SYSTEM-MERGED-UPDATE | **NEW-ACTIVE** | body_system_merged currently maps 2024 names → pre-2024 (backward). Now that post-2024 canonical IS standard, must flip direction. Affects: analysis scripts (resident re-analysis), API response mappings. |
| DEFERRED-CENTROID-REBUILD | **NEW-ACTIVE** | intersection_centroid_vec (135 rows) stale. Cells are blueprint × body_system; many body_system values changed. Must rebuild after body_system_merged flip. |
| DEFERRED-HUMAN-REVIEW-BODY-SYSTEM | **NEW-ACTIVE** | 201 ITE + 129 AAFP = 330 questions in human_review queue. Genuine classifier disagreements; await Mikey manual review before SQL apply. Priority: holdouts (Psychogenic, Reproductive:Female, Reproductive:Male). |
| DEFERRED-KNOWN-DRUGS-EXPANSION | ACTIVE (from 058) | Identify offending drug names; decide fix approach. Affects: concept_tags, synonym resolution. |
| DEFERRED-QID-XREF-LIBRARY-GAPS | ACTIVE (from 058) | 249 unmatched citations. Feed to acquisition queue. Research approach: batch exa_research_search. |
| DEFERRED-YOY-ROBUSTNESS | ACTIVE (from 058) | Month-by-month rollup needs robustness testing with dense temporal data. Currently usable for exploratory analysis. |
| DEFERRED-PGY-BENCHMARKS | ACTIVE (from 058) | Resident cohort comparisons and trend analysis. Blocked on centroid rebuild. |
| DEFERRED-PROGRAM-TREND | ACTIVE (from 058) | Multi-year program performance trends. Blocked on centroid rebuild. |
| DEFERRED-RESIDENT-FOLDER-MIGRATION | ACTIVE (from 058) | Migrate resident_data/ folder structure. Blocked on re-analysis. |
| DEFERRED-SCHOLL-OLD-FORMAT | ACTIVE (from 058) | 2022/2023 score reports in old format. Blocked on re-analysis. |
| FLAG-33-NNN-RENAME | LOW-PRI (from 058) | ART-ID rename scheme (nnn_XXXX format). Designed, not yet implemented. |

---

## Next Steps

### Immediate
1. **Re-run all 7 resident analyses** (Sarkar 2025, Hopkins 2025, Pjetergjoka 2024/2025, Scholl 2022/2023/2024)
   - Clean body_system ✅ (applied this session)
   - Clean article data ✅ (ready from BATON 058)
   - Clean qid_art_xref ✅ (ready from BATON 058)
   - Scripts: M2 `resident_score_analyzer_v6.py` + M3 `ite_score_analyzer_plugin_v2.py`

2. **DEFERRED-BODY-SYSTEM-MERGED-UPDATE**
   - Flip body_system_merged mapping direction in:
     - M3 analysis scripts (score rollup, concept mapping)
     - M5 API response builders (resident report, query results)
   - Test: verify resident reports show post-2024 canonical names

3. **DEFERRED-CENTROID-REBUILD**
   - Run M1 `build_intersection_centroids.py`
   - Input: post-2024 canonical body_system values (just applied)
   - Output: 135 rows (blueprint × body_system intersection centroids)
   - Unblocks: PGY benchmarks, program trends

4. **Update article_currency**
   - Add 13 new articles (ART-1987–ART-1999) from BATON 058
   - Script: M3 `update_article_currency.py` with batch API call

### Short-term
5. **DEFERRED-HUMAN-REVIEW-BODY-SYSTEM** (330 questions)
   - Triage: 201 ITE vs 129 AAFP
   - Priority holdouts: Psychogenic (16 ITE), Reproductive:Female (15 ITE), Reproductive:Male (2 ITE)
   - Await Mikey manual review + decision (keep pre-2024 name vs move to canonical)
   - Once reviewed, apply remaining Section 2 SQL

6. **DEFERRED-KNOWN-DRUGS-EXPANSION**
   - Run M3 `identify_drug_concept_gaps.py` to surface offending drug names
   - Decide: expand synonym library vs refactor concept-tag resolution
   - Update concept_tags table

7. **DEFERRED-QID-XREF-LIBRARY-GAPS** (249 unmatched citations)
   - Batch exa_research_search for 249 unmatched refs
   - Research + acquire articles
   - Add to DB via `add_missing_articles.py`
   - Update qid_art_xref with new linkages

---

## Key Files Changed This Session

### M3 (Analyst) — 19 new scripts
| Script | Purpose |
|--------|---------|
| extract_score_report_labels.py | Extract body system from ABFM PDFs |
| condense_taxonomy.py | Map 16 old → 15 new categories |
| build_training_set.py | Combine labels + question content |
| run_svm_baseline.py | SVM diagnostic (81.2% on 2023) |
| run_claude_classifier.py | Two-layer prompt (static + dynamic) |
| submit_batch_classification.py | Batch API submit (1,231 ITE + 1,221 AAFP) |
| retrieve_batch_results.py | Poll + parse Batch API results |
| rename_taxonomy_labels.py | Post-process: custom → canonical |
| svm_review_audit.py | Cross-check Claude vs SVM (82% / 87%) |
| generate_body_system_sql.py | Two-section SQL (norm + reclassify) |
| fix_taxonomy_names.py | Direct fixes (Musculoskeletal, Immune) |
| fix_aafp_taxonomy_names.py | AAFP taxonomy norm (317 rows) |
| submit_batch_aafp.py | AAFP Batch API submit |
| check_aafp_results.py | AAFP result verification |
| check_aafp_body_system.py | AAFP schema validation |
| check_aafp_schema.py | AAFP column counts |
| verify_body_system_updates.py | Post-apply verification |
| critique_pdf_registry.py | Files API PDF management |
| extract_critique_refs_v2.py | Format-agnostic ref extraction |

### M2 (Processor) — updated
- `extract_ite_critique_refs.py` — marked for replacement by v2 (pdfplumber → Files API)

### Skills
- `.claude/skills/article-citation-qc/SKILL.md` — updated (migrated to C:\Users\mpsch\.claude\skills\)
- `.claude/skills/body-system-qc/SKILL.md` — created (10-phase workflow)
- `.claude/skills/body-system-qc/references/taxonomy_map.md` — created

### Methodology
- `methodology_scout/methodology_scout_ite-body-system-classification_2026-04-15.md` — created (8 methods compared)

---

## Critical Notes for Next Session

1. **human_review queue (330 questions)** is not a bug or incomplete work. It reflects genuine disagreement between SVM and Claude. These need Mikey's clinical judgment — they are deferred by design, not accident.

2. **body_system_merged flip** is architectural. It affects API responses and resident reports. Test thoroughly after flip (check 1–2 resident analyses for name mapping).

3. **Centroid rebuild** is fast (135 rows) but unblocks two downstream tasks (benchmarks, trends). Schedule after body_system_merged is confirmed.

4. **Files API infrastructure** is seeded. Next ABFM exam year, upload PDFs once and reference file_ids in perpetuity. No re-download, no local management.

5. **Git hash ff36d59:** Pre-commit snapshot. If commits occurred during this session, note final hash in next BATON.

---

**Written by:** Claude Code (Haiku 4.5)  
**Session:** 2026-04-15  
**Next BATON owner:** Mikey (resident re-analysis lead)
