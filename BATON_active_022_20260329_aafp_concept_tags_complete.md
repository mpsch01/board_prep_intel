# BATON 022 — AAFP Concept Tags Complete, Full Enrichment Pipeline Done
**Date:** 2026-03-29
**Session platform:** Windows PC (Cowork VM)
**Status:** OPEN — session closing
**Preceding BATON:** `BATON_active_021_20260329_aafp_body_system_complete_keyword_pipeline_ready.md` (→ archive)
**Git hash:** `066a94f` (new scripts pending commit — see step 1 below)
**GitHub remote:** `https://github.com/mpsch01/project-overhaul` (private)

---

## SESSION SUMMARY — What Was Done and Why

Goal: run `aafp_enrich_concept_tags.py` for all 1,221 AAFP BRQ questions — adding concept_tags,
subcategory, and ICD-10 to bring AAFP schema to parity with ITE schema.

### 1. Model Selection (completed in this session)
- Built `aafp_model_comparison.py` — 10-question Haiku vs Sonnet side-by-side comparison
  (5 linked + 5 unlinked, ordered by body_system)
- Result: near-identical quality. Subcategory agreement 100%. One Haiku ICD-10 hallucination
  (text string instead of code) caught by regex filter. Sonnet marginally better on guidelines
  specificity (named TRED-HF trial explicitly). Decision: **Haiku 4.5 sufficient at ~3× cost savings.**
- Estimated cost: ~$1.10 Haiku vs ~$4.20 Sonnet (batch pricing not used — live API)

### 2. Linked batch — `--mode linked` (643 questions)
- Run completed. concept_tags + subcategory: 643/643 populated.
- ICD-10 showed `icd10+0` per question — explained: `aafp_context_propagator.py` had already
  covered 589/643 linked questions; remaining 54 received new ICD-10 codes.
- Linked batch contribution: ~54 new ICD-10 question coverages.

### 3. Unlinked batch — `--mode unlinked` (578 questions)
- Run completed. concept_tags + subcategory: 578/578 populated.
- ICD-10 inserted: **2,150 new rows** — unlinked questions had no prior coverage, every enriched
  question generated fresh ICD-10 codes.
- Errors: 0

### 4. Final QC (post-unlinked run, `qc_check.py`)
```
concept_tags:  1221/1221 (100.0%)
subcategory:   1221/1221 (100.0%)
icd10 (dist):  1208/1221 (98.9%)
```
13 questions without ICD-10 — expected (abstract/nonspecific questions where no valid ICD-10 code
was generated or passed the regex filter). Not a gap worth addressing.

**Subcategory distribution (1,221 AAFP questions):**
| Subcategory | n |
|---|---|
| Management | 326 |
| Diagnosis | 308 |
| Pharmacology | 111 |
| Treatment | 98 |
| Workup | 97 |
| Prevention | 87 |
| Screening | 76 |
| Counseling | 42 |
| Interpretation | 34 |
| Prognosis/Risk | 28 |
| Pathophysiology | 14 |

**Body system coverage: all 16 systems at 100%** (1,221/1,221)

---

## DB STATE (post-session)

| Item | Value |
|------|-------|
| DB articles | 1,985 |
| DB questions (ITE) | 1,629 |
| DB questions (AAFP BRQ) | 1,221 |
| aafp_questions.all_keywords | 1,221/1,221 (100%) |
| aafp_questions.body_system | 1,221/1,221 (100%) |
| aafp_questions.body_system_method | 1,221/1,221 (100%) |
| aafp_questions.concept_tags | **1,221/1,221 (100%) — COMPLETE this session** |
| aafp_questions.subcategory | **1,221/1,221 (100%) — COMPLETE this session** |
| qid_art_xref | 2,470 |
| aafp_qid_art_xref | 864 rows |
| aafp_question_icd10 | **~4,065 rows (1,208 unique questions, 98.9%)** |
| Next ART-ID | ART-1987 |
| Git hash | `066a94f` (new scripts pending commit) |

---

## NEW FILES THIS SESSION

| File | Description |
|------|-------------|
| `02_module.2_processor/scripts/aafp_enrich_concept_tags.py` | API enrichment: concept_tags + subcategory + ICD-10; --mode linked\|unlinked\|all; resume-safe; Haiku default |
| `02_module.2_processor/scripts/aafp_model_comparison.py` | 10-question Haiku vs Sonnet comparison; writes to aafp_comparison_results.json |
| `qc_check.py` (project root — temp) | Post-run QC script; can be deleted after commit |
| `run_compare.py` (project root — temp) | Comparison runner with file logging; can be deleted after commit |

---

## PENDING STEPS (priority order)

### 1. Windows: git commit (includes 021 session + 022 session scripts)
```
git add 02_module.2_processor/scripts/aafp_merge_keywords.py
git add 02_module.2_processor/scripts/aafp_assign_body_system.py
git add 02_module.2_processor/scripts/aafp_enrich_concept_tags.py
git add 02_module.2_processor/scripts/aafp_model_comparison.py
git add BATON_active_021_20260329_aafp_body_system_complete_keyword_pipeline_ready.md
git add BATON_active_022_20260329_aafp_concept_tags_complete.md
git add _index.md
git add CLAUDE.md
git commit -m "feat: aafp enrichment pipeline complete (body_system + concept_tags + subcategory + ICD-10, all 1221/1221)"
git push origin main
```
**Also delete from project root (not tracked by git, just cleanup):**
- `qc_check.py`
- `run_compare.py`
- `aafp_comparison_results.json` (if present)

**Also archive on Windows (move to `baton_archive/`):**
- `BATON_active_020_20260328_aafp_question_reuse_investigation_complete.md`
- `BATON_active_021_20260329_aafp_body_system_complete_keyword_pipeline_ready.md`

### 2. Windows: run `download_aafp_acquisitions.py` — 49 AAFP acquisition PDFs from PMC
```
python 01_module.1_warehouse/maintain/download_aafp_acquisitions.py
```
Then run:
```
python 02_module.2_processor/scripts/backfill_new_article_metadata.py --art-id-min 1938
```
Place downloaded PDFs in `VC_fail/` folder.

### 3. Windows: run `update_citation_trends.py` — builds `article_citation_trend` table
```
python 01_module.1_warehouse/maintain/update_citation_trends.py
```
(Was listed as "planned" in prior BATONs — script IS already built and ready)

### 4. AAFP vs ITE trend comparison — NOW FULLY UNBLOCKED
Both corpora have matching schema (body_system, concept_tags, subcategory, ICD-10).
- Side-by-side body system distribution: AAFP (1,221 Q) vs ITE (1,629 Q, 2018–2025)
- Subcategory distribution comparison
- ICD-10 overlap analysis (which codes appear in both corpora)
- Re-run `build_topic_trends.py` to include 2018–2019 in ITE trend CSVs

### 5. 229 citation gap articles
- 88 AFP articles batch-downloadable from `null_clean_ref_missing_articles_20260326.csv`
- Codon rename → ingest → enrich → re-run `aafp_ref_match_v2.py`

### 6. Interactive vector dashboard
- HTML dashboard from vector explorer data (`data:interactive-dashboard-builder`)

### 7. Intelligence 2.0 Layer 2
- `article_currency` table via PubMed MCP

---

## DEFERRED FLAGS

| Flag | Description |
|------|-------------|
| FLAG 33 | `nnn_XXXX` ART-ID rename scheme — designed, not yet implemented |
| WAL mode oplock | DB shows 0 tables from VM after Windows runs embeddings — known FUSE issue |
| `ite_shared_vignette` column | Designed for `aafp_questions`, not yet added (deprioritized — 38 pairs insufficient signal) |
| AAFP-ITE lag analysis | 38 shared-vignette pairs are seed set; build predictive watch list when bandwidth available |

---

## BATON HANDOFF NOTES

- AAFP corpus is now schema-parallel to ITE: body_system, concept_tags, subcategory, ICD-10 all populated
- `aafp_enrich_concept_tags.py` is resume-safe — re-running skips populated rows; `--rerun` to force
- 13 questions without ICD-10 are expected gaps — no action needed
- `update_citation_trends.py` and `download_aafp_acquisitions.py` are both READY to run — do not list as "planned"
- Trend comparison is the highest-value next analytical step now that both corpora are enriched
