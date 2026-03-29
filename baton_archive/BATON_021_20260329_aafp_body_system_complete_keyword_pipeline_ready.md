# BATON 021 — AAFP Body System Complete, Keyword Pipeline Ready
**Date:** 2026-03-29
**Session platform:** Windows PC (Cowork VM)
**Status:** OPEN — session in progress
**Preceding BATON:** `BATON_active_020_20260328_aafp_question_reuse_investigation_complete.md` (→ archive)
**Git hash:** `066a94f` (new scripts pending commit this session)
**GitHub remote:** `https://github.com/mpsch01/project-overhaul` (private)

---

## SESSION SUMMARY — What Was Done and Why

Goal: complete the AAFP BRQ question enrichment pipeline through body_system assignment,
preparing the corpus for AAFP vs ITE trend comparison and API-based concept_tags + ICD-10 enrichment.

### 1. Housekeeping (completed)
- Git: 4 commits pushed → `066a94f` (housekeeping, ref matching scripts, acquisition scripts, reuse investigation)
- BATONs 018 and 019 archived and committed
- `_index.md` updated to BATON 020 state

### 2. `aafp_merge_keywords.py` v1 (new — M2/scripts/)
Merges `stem_keywords` (aafp_questions) + `explanation_keywords` (aafp_explanations) into
unified `all_keywords` column on `aafp_questions`. Mirrors ITE questions schema exactly.
- Stem terms first (priority); explanation terms appended if not already present
- 1,221/1,221 populated. Both keyword fields were 100% populated — no gaps.
- Schema: `ALTER TABLE aafp_questions ADD COLUMN all_keywords TEXT`

### 3. `aafp_assign_body_system.py` v2 (new — M2/scripts/)
Three-tier body_system classifier for all 1,221 AAFP BRQ questions:

| Tier | Method | n | Description |
|------|--------|---|-------------|
| 1 | `propagated` | 533 | Article xref — authoritative (from aafp_context_propagator) |
| 1 | `propagated_compound` | 61 | Multi-category article → primary value taken |
| 2 | `neighbor` | 104 | ITE nearest question (dist < 0.45) |
| 3 | `keyword_freq` | 447 | Frequency classifier ≥ 1.10 confidence |
| 3 | `neighbor_lowconf` | 75 | Classifier < 1.10 confidence → ITE neighbor fallback |
| 3 | `neighbor_fallback` | 1 | No keywords → ITE neighbor |

**Classifier design:**
- Frequency table built from 1,629 ITE questions (ground-truth corpus), 5,825 terms, 16 body systems
- `correct_text` weighted 3× (names the diagnosis directly)
- Stopword filter: removes demographic/generic terms ("male", "female", "year old", "patient"…)
  that appear across all body systems and cause false Reproductive: Male/Female assignments
- Confidence threshold 1.10: below this → ITE neighbor fallback instead of uncertain classifier
- `body_system_method` column added to track every assignment (auditable)

**QC findings and fixes:**
- Label variants normalized: `Hematologic/Immune` → `Hematologic/ Immune` (41 rows),
  `Reproductive:Female` → `Reproductive: Female` (52 rows), `Reproductive:Male` → `Reproductive: Male` (2 rows)
- Compound labels resolved: 61 propagated questions had multi-value body_system from article categories
  (e.g., "Cardiovascular, Endocrine, Nephrologic") → primary value kept, method = `propagated_compound`

**Final body_system distribution (1,221 AAFP questions):**
| Body System | n | % |
|---|---|---|
| Cardiovascular | 156 | 12.8% |
| Musculoskeletal | 139 | 11.4% |
| Respiratory | 120 | 9.8% |
| Gastrointestinal | 110 | 9.0% |
| Population-Based Care | 97 | 7.9% |
| Reproductive: Female | 84 | 6.9% |
| Psychogenic | 82 | 6.7% |
| Integumentary | 78 | 6.4% |
| Endocrine | 70 | 5.7% |
| Hematologic/ Immune | 67 | 5.5% |
| Nephrologic | 45 | 3.7% |
| Special Sensory | 44 | 3.6% |
| Neurologic | 43 | 3.5% |
| Patient-Based Systems | 32 | 2.6% |
| Reproductive: Male | 27 | 2.2% |
| Nonspecific | 27 | 2.2% |

### 4. `aafp_enrich_concept_tags.py` v1 (new — M2/scripts/)
API enrichment script: adds `concept_tags`, `subcategory`, and ICD-10 rows to all 1,221 AAFP BRQ questions.
Mirrors the ITE enrichment schema so AAFP and ITE are directly comparable for trend analysis.

**Output schema (same as ITE):**
- `concept_tags` TEXT (JSON): `{diagnoses, drugs, guidelines, thresholds, concept_summary}`
- `subcategory` TEXT: Diagnosis, Management, Pharmacology, Screening, Workup, Prevention, Counseling, Prognosis/Risk, Treatment, Interpretation, Pathophysiology
- ICD-10 rows inserted into `aafp_question_icd10` for uncovered questions (632 remaining after aafp_context_propagator)

**Two context modes (one script, `--mode` flag):**
- `--mode linked` (643 Q): prompt includes article title + categories from xref JOIN
- `--mode unlinked` (578 Q): prompt uses ITE nearest neighbor stem (if dist < 0.50) as supplemental context
- `--mode all` (default): processes all 1,221

**Resume safety:** skips rows where `concept_tags IS NOT NULL` by default. `--rerun` flag to reprocess.

**To run (from Windows, copy-paste):**
```
cd C:\path\to\00_#PROJECT_OVERHAUL
python 02_module.2_processor/scripts/aafp_enrich_concept_tags.py --dry-run --mode linked
python 02_module.2_processor/scripts/aafp_enrich_concept_tags.py --mode linked
python 02_module.2_processor/scripts/aafp_enrich_concept_tags.py --mode unlinked
```
Requires: `pip install anthropic` + `ANTHROPIC_API_KEY` in env.
Estimated runtime: ~20-40 min for all 1,221 questions at 0.5s sleep.

---

### 5. Undocumented scripts discovered (M1/maintain/)
Two fully-built scripts found that were not in `_index.md`:
- `update_citation_trends.py` — v1, 200 lines. Was listed as "planned, not yet built." IS built.
  Populates/refreshes `article_citation_trend` table. Full refresh mode + `--report` flag.
- `download_aafp_acquisitions.py` — 319 lines. Never documented.
  Downloads 49 AAFP acquisition article PDFs from PMC using NCBI ID converter, renames to codon format.
  **Ready to run from Windows to download the 49 pending PDFs.**

---

## DB STATE (post-session)

| Item | Value |
|------|-------|
| DB articles | 1,985 |
| DB questions (ITE) | 1,629 |
| DB questions (AAFP BRQ) | 1,221 |
| aafp_questions.all_keywords | 1,221/1,221 (100%) — NEW this session |
| aafp_questions.body_system | 1,221/1,221 (100%) — NEW this session |
| aafp_questions.body_system_method | 1,221/1,221 (100%) — NEW this session |
| aafp_questions.concept_tags | 0/1,221 (0%) — column added, ready for API run |
| aafp_questions.subcategory | 0/1,221 (0%) — column added, ready for API run |
| qid_art_xref | 2,470 |
| aafp_qid_art_xref | 864 rows |
| aafp_question_icd10 | 1,915 rows |
| Next ART-ID | ART-1987 |
| Git hash | `066a94f` (new scripts pending commit) |

---

## NEW FILES THIS SESSION

| File | Description |
|------|-------------|
| `02_module.2_processor/scripts/aafp_merge_keywords.py` | Merges stem + explanation keywords → all_keywords (1221/1221) |
| `02_module.2_processor/scripts/aafp_assign_body_system.py` v2 | 3-tier body_system classifier; stopwords; confidence threshold; `--dry-run`, `--rerun-kwfreq` flags |
| `02_module.2_processor/scripts/aafp_enrich_concept_tags.py` | API enrichment: concept_tags + subcategory + ICD-10; --mode linked\|unlinked\|all; resume-safe |

---

## PENDING STEPS (priority order)

1. **Windows:** commit new scripts + BATON 021 → push
   ```
   git add 02_module.2_processor/scripts/aafp_merge_keywords.py
   git add 02_module.2_processor/scripts/aafp_assign_body_system.py
   git add 02_module.2_processor/scripts/aafp_enrich_concept_tags.py
   git add BATON_active_021_20260329_aafp_body_system_complete_keyword_pipeline_ready.md
   git add _index.md
   git commit -m "feat: aafp keyword pipeline complete + concept_tags enricher (body_system 1221/1221, concept_tags API-ready)"
   git push origin main
   ```

2. **Windows:** run `aafp_enrich_concept_tags.py` — API enrichment for concept_tags + subcategory + ICD-10
   ```
   python 02_module.2_processor/scripts/aafp_enrich_concept_tags.py --mode linked
   python 02_module.2_processor/scripts/aafp_enrich_concept_tags.py --mode unlinked
   ```
   **Prerequisite:** `pip install anthropic` + ANTHROPIC_API_KEY in env vars

3. **Windows:** run `download_aafp_acquisitions.py` — downloads 49 AAFP acquisition PDFs from PMC
   Then run `backfill_new_article_metadata.py --art-id-min 1938`

4. **Windows:** run `update_citation_trends.py` — builds `article_citation_trend` table
   (was "planned" but IS already built — see discovery above)

5. **AAFP vs ITE trend comparison** — now unblocked:
   - `build_topic_trends.py` re-run to include 2018-2019 in ITE trend CSVs
   - Side-by-side body system distribution: AAFP (1,221 Q) vs ITE (1,629 Q, 2018-2025)
   - After API enrichment: concept_tag comparison + ICD-10 overlap analysis

6. **229 citation gap articles** — 88 AFP batch-downloadable from `null_clean_ref_missing_articles_20260326.csv`

7. **Intelligence 2.0 Layer 2** — `article_currency` table via PubMed MCP

---

## DEFERRED FLAGS

| Flag | Description |
|------|-------------|
| FLAG 33 | `nnn_XXXX` ART-ID rename scheme — designed, not yet implemented |
| WAL mode oplock | DB shows 0 tables from VM after Windows runs embeddings — known FUSE issue |
| `ite_shared_vignette` column | Designed for `aafp_questions`, not yet added (deprioritized — 38 pairs insufficient signal) |

---

## BATON HANDOFF NOTES

- `aafp_assign_body_system.py --rerun-kwfreq` is safe to re-run at any time (only touches keyword_freq rows)
- The `body_system_method` column is the audit trail — use it to QC or spot-correct assignments
- `update_citation_trends.py` is READY to run — do not list as "planned" in future docs
- `download_aafp_acquisitions.py` is READY to run from Windows — 49 PDFs, PMC open access
- Next session: likely API enrichment runs (Mikey copy-paste-runs from Windows) or trend comparison
