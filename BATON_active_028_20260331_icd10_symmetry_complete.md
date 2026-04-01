# BATON 028 — ICD-10 Symmetry Complete + PubMed Layer 2 Seed
**Date:** 2026-03-31
**Session:** ICD-10 symmetry (both banks), PubMed citation crawler, related cap
**Status:** ICD-10 symmetry fully achieved. 4 new M2 scripts. pubmed_pmid_cache seeded.
**Replaces:** BATON_active_027_20260330_icd10_embeddings.md

---

## What Was Done This Session

### 1. ICD-10 Symmetry — COMPLETE (both sides, zero API cost)

The ICD-10 gap that entered BATON 027 as a deferred flag is now fully closed.

**The gap coming in:**

| | Article-level ICD-10 | Question-level ICD-10 |
|---|---|---|
| ITE | ✅ `article_icd10` (3,855 rows) | ❌ no `question_icd10` table |
| AAFP | ❌ no entries for AAFP articles | ✅ `aafp_question_icd10` (4,240 rows) |

**The gap now:**

| | Article-level ICD-10 | Question-level ICD-10 |
|---|---|---|
| ITE | ✅ `article_icd10` (4,137 rows) | ✅ `question_icd10` (5,284 rows) |
| AAFP | ✅ `article_icd10` (+282 AAFP rows) | ✅ `aafp_question_icd10` (4,753 rows) |

---

### 2. `build_ite_question_icd10.py` — NEW

**Script:** `02_module.2_processor/scripts/build_ite_question_icd10.py`
**Method:** Propagation — `article_icd10 → qid_art_xref → question_icd10` (zero API)
**Key design decisions:**
- Textbook filter: `WHERE ar.source_type != 'Textbook'` — prevents broad-coverage textbook ICD-10 bleeding into focused question tags (discovered via poison ivy question getting 34 retinopathy codes)
- Tier-aware cap: ALL primary + secondary kept; related capped at top 3 per question ranked by contributing article frequency
- Relevance promotion: best relevance wins per (qid, icd10_code) across all linked articles

**Results:**
```
question_icd10 rows:        5,284
Questions tagged:           1,512 / 1,629  (92.8%)
Relevance breakdown:        51.6% primary / 30.8% secondary / 17.6% related
```
Near-perfect alignment with source `article_icd10` distribution (52.7% / 31.7% / 15.6%).

---

### 3. `backfill_aafp_article_icd10.py` — NEW

**Script:** `02_module.2_processor/scripts/backfill_aafp_article_icd10.py`
**Method:** Reverse propagation — `aafp_question_icd10 → aafp_qid_art_xref → article_icd10`
**Key design:** `INSERT OR IGNORE` — never overwrites existing ITE article entries. Only fills AAFP articles with question links that had no existing ICD-10.
**Results:**
```
article_icd10 rows added:   282
AAFP articles filled:       86
Related codes trimmed (cap): 117
```
Remaining 362 AAFP articles with no ICD-10: no question links → not reachable by propagation.

---

### 4. `build_pubmed_citation_icd10.py` — NEW

**Script:** `02_module.2_processor/scripts/build_pubmed_citation_icd10.py`
**Method:** JOURNAL_MISSING citations → NCBI eutils (free, no key) → PMID → MeSH terms → ICD-10 via DB lookup
**Target:** 377 JOURNAL_MISSING citations in `aafp_citations.unmatched_class`

**3-pass PMID lookup:**
1. author + year + journal (tight)
2. author + year + volume + page (no journal)
3. author + year only (unambiguous single result only)

**MeSH → ICD-10:** case-insensitive text matching against `article_icd10` descriptions (1,334 codes loaded). MajorTopicYN=Y → `secondary`; N → `related`.

**Side effect:** Each resolved PMID stored in new `pubmed_pmid_cache` table (Layer 2 seed).

**Results:**
```
Citations processed:        377
PMID resolved:              344 / 377  (91.2%)
MeSH returned:              342
ICD-10 rows inserted:       921  → aafp_question_icd10
pubmed_pmid_cache rows:     344
```

**Key bugs fixed during this session:**
- `aafp_citations.match_status` vs `unmatched_class` — JOURNAL_MISSING is in the latter column
- `pubmed_pmid_cache.citation_id INTEGER` → `TEXT` (citation_ids are strings like 'AAFP-49863-C1')

---

### 5. `apply_aafp_related_cap.py` — NEW

**Script:** `02_module.2_processor/scripts/apply_aafp_related_cap.py`
**Method:** Same tier-aware cap as ITE side; ranks by global code frequency (how many questions share each related code) since PubMed rows have no article provenance chain.

**Results:**
```
Related rows before cap:    1,540
Questions over cap (>3):    151
Rows deleted:               408
```

**Final aafp_question_icd10 state:**
```
Total rows:     4,753
primary:        2,003  (42.1%)
secondary:      1,618  (34.0%)
related:        1,132  (23.8%)
```
Related% higher than ITE (17.6%) — expected. PubMed MeSH is inherently broader vocabulary than Claude-tagged article ICD-10.

---

### 6. New Table: `pubmed_pmid_cache`

```sql
CREATE TABLE pubmed_pmid_cache (
    citation_id   TEXT    PRIMARY KEY,
    pmid          TEXT    NOT NULL,
    lookup_date   TEXT    DEFAULT (date('now')),
    mesh_count    INTEGER DEFAULT 0
)
```
344 rows. This is the Layer 2 seed — when `article_currency` is built, the PubMed lookup step is already done for 344 citations.

---

## DB State (current as of BATON 028)

| Item | Value |
|------|-------|
| DB articles | 1,985 |
| DB questions (ITE) | 1,629 (2018–2025) |
| DB questions (AAFP) | 1,221 |
| article_icd10 | **4,137** rows (was 3,855; +282 AAFP backfill) |
| question_icd10 | **5,284** rows — NEW — 1,512/1,629 ITE questions (92.8%) |
| aafp_question_icd10 | **4,753** rows (was 4,240; +921 PubMed, -408 cap = +513 net) |
| pubmed_pmid_cache | **344** rows — NEW |
| icd10_vec | 2,219 rows |
| article_icd10_vec | 1,674 rows (needs rebuild after article_icd10 expansion) |
| question_icd10_vec | 2,733 rows (needs rebuild now that question_icd10 exists) |
| clinical_pathways | 3,093 rows (legacy, rebuild pending) |
| qid_art_xref | 2,470 |
| aafp_qid_art_xref | 864 rows |
| PDFs | 404 (49 new articles awaiting download) |
| Next ART-ID | ART-1987 |
| Git branch | main, commit pending (6 new M2 scripts + BATONs 027+028 + housekeeping) |

---

## Deferred Flags

| Flag | Description | Priority |
|------|-------------|----------|
| DEFERRED-A | PDF download: 49 new AAFP articles ART-1938–1986 | High |
| DEFERRED-B | `update_citation_trends.py` — run AFTER DEFERRED-A | Medium |
| DEFERRED-C | AAFP vs ITE trend comparison | Medium |
| DEFERRED-D | 229 citation gap articles (88 AFP batch-downloadable) | Medium |
| DEFERRED-E | Interactive vector dashboard | Low |
| DEFERRED-F | Intelligence 2.0 Layer 2 — `article_currency` table (344 PMIDs already cached) | Medium |
| CLINICAL-PATHWAY | Rebuild clinical_pathways_v2.py — blueprint-based, both banks, full ART range | High |
| Q-ICD10-VEC | Rebuild question_icd10_vec now that question_icd10 exists (ITE side was empty before) | Medium |
| ARTICLE-ICD10-VEC | Rebuild article_icd10_vec to include +282 new AAFP backfill rows | Low |
| Q-VEC-GAP | Fill question vector gaps: 440 ITE (2018–2019) + 1,221 AAFP → question_vec | Medium |

---

## Next Steps (priority order)

### 1. Git commit (Windows)
```
git add 02_module.2_processor/scripts/build_ite_question_icd10.py
git add 02_module.2_processor/scripts/backfill_aafp_article_icd10.py
git add 02_module.2_processor/scripts/build_pubmed_citation_icd10.py
git add 02_module.2_processor/scripts/apply_aafp_related_cap.py
git add BATON_active_028_20260331_icd10_symmetry_complete.md
git add baton_archive/   (archive BATONs 026 + 027)
git add CLAUDE.md README.json auto-memory-copies/
git commit -m "BATON 028: ICD-10 symmetry complete + PubMed citation crawler"
```

### 2. Rebuild clinical_pathways_v2.py (CLINICAL-PATHWAY)
- Blueprint-based routing (BLUEPRINT_ROLE_MAP replaces ENGINE_ROLE_MAP)
- Both banks feed same table
- Covers full article range ART-0002–ART-1985
- Adds `source_bank` column

### 3. Rebuild ICD-10 vector layers (Q-ICD10-VEC)
```python
python scripts/build_icd10_embeddings.py --derive
```
question_icd10_vec was built when ITE had no question_icd10 — needs rebuild now.

### 4. PDF download (DEFERRED-A)
```
python 01_module.1_warehouse\scripts\maintain\download_aafp_acquisitions.py
python 01_module.1_warehouse\scripts\maintain\backfill_new_article_metadata.py --art-id-min 1938
```
Then re-run `build_icd10_embeddings.py --derive` for new articles.

### 5. Intelligence 2.0 Layer 2 — `article_currency`
`pubmed_pmid_cache` already has 344 PMIDs. Build `article_currency` table to check publication date,
superseded_by status, and freshness flags for cited articles.

---

## Files Changed This Session

| File | Action |
|------|--------|
| `build_ite_question_icd10.py` | NEW — M2/scripts/ |
| `backfill_aafp_article_icd10.py` | NEW — M2/scripts/ |
| `build_pubmed_citation_icd10.py` | NEW — M2/scripts/ |
| `apply_aafp_related_cap.py` | NEW — M2/scripts/ |
| `question_icd10` (DB) | NEW TABLE — 5,284 rows |
| `pubmed_pmid_cache` (DB) | NEW TABLE — 344 rows |
| `article_icd10` (DB) | +282 rows (AAFP backfill) |
| `aafp_question_icd10` (DB) | +921 rows, -408 capped = 4,753 total |
| `BATON_active_028_*.md` | This file |
| `CLAUDE.md` | Updated Active State + Next Steps |
| `README.json` | Updated db counts + intelligence_layers + deferred_flags |
| `auto-memory-copies/` | Updated project_overhaul_state + project_current_db_state |
