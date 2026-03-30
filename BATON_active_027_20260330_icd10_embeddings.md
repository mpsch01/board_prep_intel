# BATON 027 — ICD-10 Vector Embedding Layer
**Date:** 2026-03-30
**Session:** icd10_embeddings + clinical pathway architecture design
**Status:** ICD-10 embedding layer complete. Three new vector tables live in DB.
**Replaces:** BATON_active_026_20260330_aafp_blueprint_unified.md

---

## What Was Done This Session

### 1. Clinical Pathway Architecture — Full Redesign (design only, not yet built)

- **Old approach diagnosed**: `build_clinical_pathways.py` used `questions.subcategory` (now DROPPED)
  to classify articles into engine_types — an indirect, lossy signal that broke when subcategory was dropped.
- **New architecture agreed**: Use `blueprint` (100% filled on both banks) as primary signal.
  Questions directly encode clinical function. Articles serve as content containers.
- **New data flow**:
  - ITE: `questions.blueprint × qid_art_xref × article_icd10.relevance → pathway_role`
  - AAFP: `aafp_questions.blueprint × aafp_qid_art_xref × aafp_question_icd10.relevance → pathway_role`
  - Both feeds → same `clinical_pathways` table
- **New BLUEPRINT_ROLE_MAP** replaces ENGINE_ROLE_MAP (no more engine_type intermediate)
- **Coverage gap identified**: current `clinical_pathways` covers ART-0002–ART-1397 only (1,269 articles).
  ART-1398–1985 gap = 588 articles with zero pathway coverage.
- **`engine_type` on articles**: legacy field, preserved as-is, no longer used in new pathway script.

### 2. ICD-10 Symmetry Gap Identified

Both question banks and article library need symmetric ICD-10 coverage:

| | Article-level ICD-10 | Question-level ICD-10 |
|---|---|---|
| ITE | ✅ `article_icd10` (3,855 rows) — derived from question concept_tags | ❌ no `question_icd10` table |
| AAFP | ❌ no entries in `article_icd10` for ART-1398+ | ✅ `aafp_question_icd10` (4,240 rows) |

Filling these gaps + building the pathway script is the next major task.

### 3. ICD-10 Vector Embedding Layer — COMPLETE

**Script**: `02_module.2_processor/scripts/build_icd10_embeddings.py` (NEW)

**Three new tables:**

| Table | Rows | Description |
|---|---|---|
| `icd10_vec` | 2,219 | One embedding per unique ICD-10 code (OpenAI text-embedding-3-small, 1536d) |
| `article_icd10_vec` | 1,674 | Weighted-avg ICD-10 feature vector per article (93.7% of cited articles) |
| `question_icd10_vec` | 2,733 | Weighted-avg ICD-10 feature vector per question (1,525 ITE + 1,208 AAFP) |

**Coverage:**
- ITE questions: 1,525/1,629 (93.6%) — gap is questions with no linked articles or untagged articles
- AAFP questions: 1,208/1,221 (98.9%) — near-complete, direct question-level ICD-10 path
- Articles: 1,674 of cited articles (93.7%)

**Run output (zero errors):**
```
2219 codes embedded   model: text-embedding-3-small
1674 articles  avg 2.3 codes/article
1525 ITE questions  avg 4.0 codes/q
1208 AAFP questions  avg 3.5 codes/q
```

**What this unlocks:**
- Any question or article can now be positioned in ICD-10 vector space
- Cross-bank comparison in ICD-10 territory (AAFP vs ITE coverage by condition)
- Threshold validation for future Batch API ICD-10 tagging
- Universal bridge: question bank addressable from any ICD-10-coded clinical system
  (EMRs, billing, drug indications, CMS coverage policies, other question banks)

**Weighting scheme**: primary=3, secondary=2, related=1
**Derivation**: zero API cost — pure weighted average of code vectors from `icd10_vec`
**Script is idempotent**: `--embed` skips already-embedded codes; safe to re-run

---

## DB State (current as of BATON 027)

| Item | Value |
|------|-------|
| DB articles | 1,985 |
| DB questions (ITE) | 1,629 (2018–2025) — blueprint 100%, subcategory DROPPED |
| DB questions (AAFP) | 1,221 — blueprint 100%, flattened, subcategory DROPPED |
| article_icd10 | 3,855 rows (ART-0002–ART-1397, derived from ITE concept_tags) |
| aafp_question_icd10 | 4,240 rows (question-level, all AAFP) |
| icd10_vec | 2,219 rows — NEW |
| article_icd10_vec | 1,674 rows — NEW |
| question_icd10_vec | 2,733 rows (1,525 ITE + 1,208 AAFP) — NEW |
| clinical_pathways | 3,093 rows (ART-0002–ART-1397 only — legacy, rebuild pending) |
| qid_art_xref | 2,470 |
| aafp_qid_art_xref | 864 rows |
| PDFs | 404 (49 new articles awaiting download) |
| Next ART-ID | ART-1987 |

---

## Deferred Flags

| Flag | Description | Priority |
|------|-------------|----------|
| DEFERRED-A | PDF download: 49 new AAFP articles ART-1938–1986 | High |
| DEFERRED-B | `update_citation_trends.py` — run AFTER DEFERRED-A | Medium |
| DEFERRED-C | AAFP vs ITE trend comparison — deeper analysis | Medium |
| DEFERRED-D | 229 citation gap articles (88 AFP batch-downloadable) | Medium |
| DEFERRED-E | Interactive vector dashboard | Low |
| DEFERRED-F | Intelligence 2.0 Layer 2 (PubMed MCP article_currency) | Medium |
| CLINICAL-PATHWAY | Rebuild clinical_pathways using blueprint signal (design complete, script not yet built) | High |
| ICD10-SYMMETRY | Build ITE question_icd10 (Batch API) + AAFP article_icd10 (aggregate) | High |
| Q-VEC-GAP | Fill question vector gaps: 440 ITE (2018–2019) + 1,221 AAFP → question_vec | Medium |
| SQLITE-LOCK | Add timeout=10 + context managers to all scripts | Low |
| FLAG-B | stem_keywords: AAFP/ITE unified but context not identical | Low |

---

## Next Steps (priority order)

### 1. Git commit (Windows) — now very overdue
```
git add CLAUDE.md _index.md
git add BATON_active_027_20260330_icd10_embeddings.md
git add baton_archive/   (archive BATONs 025 + 026)
git add 02_module.2_processor/scripts/build_icd10_embeddings.py
git add 02_module.2_processor/scripts/flatten_aafp_questions.py
git add 02_module.2_processor/scripts/blueprint_api_classifier_aafp.py
git add 02_module.2_processor/scripts/write_blueprint_aafp_to_db.py
git add 02_module.2_processor/source/blueprint_classifications_aafp.xlsx
git add 02_module.2_processor/source/blueprint_aafp_batch_state.json
git add skills_abilities/ite-data-context-skill/
git add 00_database/schemas/ite-data-context-skill/
git commit -m "BATON 027: ICD-10 embedding layer + AAFP blueprint + schema cleanup"
```

### 2. ICD-10 Symmetry — build missing tables (ICD10-SYMMETRY)
Two scripts needed:
- `build_ite_question_icd10.py` — Batch API: stem + concept_tags + answer_rationale → top 3 ICD-10 per ITE question → `question_icd10` table
- `backfill_aafp_article_icd10.py` — zero API: aggregate `aafp_question_icd10 → aafp_qid_art_xref → article_icd10` for AAFP articles

### 3. Rebuild clinical_pathways (CLINICAL-PATHWAY)
New script: `build_clinical_pathways_v2.py`
- Blueprint-based routing (BLUEPRINT_ROLE_MAP replaces ENGINE_ROLE_MAP)
- Both banks feed same table
- Covers full article range including ART-1398–1985
- Adds `source_bank` column

### 4. PDF download (DEFERRED-A)
```
python 01_module.1_warehouse\scripts\maintain\download_aafp_acquisitions.py
python 01_module.1_warehouse\scripts\maintain\backfill_new_article_metadata.py --art-id-min 1938
```

### 5. Re-run build_icd10_embeddings.py --derive after DEFERRED-A
New AAFP articles will get ICD-10 tags → re-derive article_icd10_vec to include them.

### 6. Fill question vector gaps (Q-VEC-GAP)
Embed 440 ITE (2018–2019) + 1,221 AAFP questions → `question_vec`
Required for full threshold validation pipeline.

---

## Files Changed This Session

| File | Action |
|------|--------|
| `build_icd10_embeddings.py` | NEW — three-phase: embed codes, derive article/question vectors, report |
| `icd10_vec` (DB) | NEW TABLE — 2,219 rows |
| `article_icd10_vec` (DB) | NEW TABLE — 1,674 rows |
| `question_icd10_vec` (DB) | NEW TABLE — 2,733 rows |
| `BATON_active_027_*.md` | This file |
| `CLAUDE.md` | Needs update (Active State table) |
