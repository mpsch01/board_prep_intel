# BATON 039 — Schema Docs Update + Session Orientation Cleanup
**Date:** 2026-04-04
**Session:** Desktop-level Cowork session; orientation + schema doc refresh + housekeeping
**Status:** GIT-COMMITTED ✓ | hash: abe1579
**Replaces:** BATON_active_038_20260404_code_review_fixes.md

---

## What Was Done This Session

### 1. Windows Cleanup (DEFERRED from 038) — COMPLETE ✓
- Mikey deleted 5 deprecated script originals: `M1/build/extract_ite_2018_2019.py`, `integrate_2018_2019.py`, `backfill_keywords_2018_2019.py`, `M1/maintain/rename_to_codon.py`, `build_match_staging.py`
- `claude_knowledge/` folder on Desktop also deleted

### 2. Option B Artifact Cleanup — COMPLETE ✓
- `SEVERANCE_PLAN.md` — deleted
- `option_b_patch.py` — deleted
- `repo_pre_severance.md` — read for orientation, then deleted

### 3. Pre-Severance Orientation + Structural Audit
Read `repo_pre_severance.md` and mapped current structure against it. Findings:

| Location | Pre-Severance | BATON 038 Said | Actual Count |
|---|---|---|---|
| M1 build/ | 9 (3 deprecated) | "9 (3 deprecated)" | **6** (3 deleted ✓) |
| M1 maintain/ | ~20 listed (said "17") | "17 (2 deprecated)" | **18** (2 deleted ✓) |
| M2 scripts/ | "~60" (actually ~73 listed) | "~64" | **75 Python + 6 JS** |
| M3 scripts/ | 11 + 2 new = 13 | "14" | **13 Python + 2 JS** |

**M2 undocumented subdirectories identified and documented:**
- `source/` — AAFP video transcripts, blueprint xlsx, outline DOCX (source data — protected)
- `outputs/` — staging JSONs + citation gap list (derived, disposable)
- `prompts/` — prompt templates

All counts corrected in CLAUDE.md and BATON 038.

### 4. Schema Docs Updated (`00_database/schemas/ite-data-context-skill/references/tables/`)

**questions.md:**
- Removed `subcategory` column row (confirmed dropped from DB)
- Fixed script name: `preprocess_keywords_v2.py` → `preprocess_concept_tags.py`

**articles.md — significant updates:**
- Row count: 1,397 → **1,985**
- `tier` column: completely rewritten — `rename_tier_labels_in_db.py` had already run; actual values are `VC_fail` (1,448) / `VC_pass` (362) / `local_lite` (117) / `right_click` (58); was still documenting Must-Read/Core/Supplementary
- Tier distribution table: replaced with current values
- `source_type` distribution: refreshed (AFP 700, Other Journal 649, 11 categories; prior had 10 with very different counts)
- `extraction_status`: 337/1,060 → 336/1,649
- Sample query: "Must-Read" → "right_click"
- Update Frequency: added `backfill_new_article_metadata.py`
- `auto_assigned` column: flagged as legacy

---

## DB State (unchanged this session)

No DB writes.

| Table | Rows |
|-------|------|
| articles | 1,985 |
| questions (ITE) | 1,629 |
| aafp_questions | 1,221 |
| article_icd10 | 4,137 |
| question_icd10 | 5,284 |
| clinical_pathways | 4,020 |
| Next ART-ID | ART-1987 |

---

## Script Counts (corrected)

| Location | Python | JS | Notes |
|----------|--------|----|-------|
| M1 build/ | 6 | 0 | 3 deprecated deleted ✓ |
| M1 maintain/ | 18 | 0 | 2 deprecated deleted ✓ |
| M2 scripts/ | 75 | 6 | flat scripts/; +core(4py) +engines(7py) +utils(6py) packages |
| M3 scripts/ | 13 | 2 | ite_analyzer_v2.py deprecated; 12 active |
| skills_abilities/agents/scripts/ | 5 | 0 | |

---

## Deferred Flags (unchanged)

| Flag | Description | Priority |
|------|-------------|----------|
| DEFERRED-A | 37 manual PDFs: 34 subscription + 3 Cochrane → download → codon rename → VC_fail → backfill | **HIGH** |
| DEFERRED-B | `update_citation_trends.py` after backfill | MEDIUM |
| DEFERRED-C | AAFP vs ITE trend comparison | MEDIUM |
| DEFERRED-D | 229 citation gap articles (88 AFP batch-downloadable) | MEDIUM |
| DEFERRED-E | Interactive vector dashboard | LOW |
| DEFERRED-F | Intelligence 2.0 Layer 2 (`article_currency` via PubMed, 344 PMIDs cached) | MEDIUM |

---

## Pending (next session)

1. **DEFERRED-A** — 37 manual PDFs (34 subscription + 3 Cochrane) → download → codon rename → `citation_files/ITE/VC_fail/` → `backfill_new_article_metadata.py --art-id-min 1938`
2. **DEFERRED-B** — `update_citation_trends.py` after backfill complete
3. **DEFERRED-F** — Intelligence 2.0 Layer 2: `article_currency` via PubMed (344 PMIDs in `pubmed_pmid_cache`)
4. **Schema docs** — Consider refreshing `vectors.md`, `clinical_pathways.md`, `qid_art_xref.md` (not audited this session)

---

## Files Changed This Session

| File | Action |
|------|--------|
| `CLAUDE.md` | MODIFIED — script counts corrected; M2 subdirs documented; cleanup marked complete |
| `BATON_active_038_20260404_code_review_fixes.md` | MODIFIED — script counts corrected; cleanup marked complete |
| `00_database/schemas/.../articles.md` | MODIFIED — row count, tier column, distributions, extraction_status |
| `00_database/schemas/.../questions.md` | MODIFIED — subcategory removed, script name fixed |
| `SEVERANCE_PLAN.md` | DELETED |
| `option_b_patch.py` | DELETED |
| `repo_pre_severance.md` | DELETED |
