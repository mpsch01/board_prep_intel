---
name: project_current_db_state
description: DB state as of BATON 028 (2026-03-31) — ICD-10 symmetry complete, question_icd10 and pubmed_pmid_cache added
type: project
---

## DB State (as of BATON 028, 2026-03-31)

| Table | Rows | Notes |
|-------|------|-------|
| articles | 1,985 | ART-0001 → ART-1986; next = ART-1987 |
| questions | 1,629 | ITE only — 2018–2025; blueprint 100%, subcategory DROPPED |
| qid_art_xref | 2,470 | All 8 years (2018–2025) |
| question_ref_pairs | 2,722 | |
| article_icd10 | **4,137** | +282 AAFP backfill this session (was 3,855) |
| **question_icd10** | **5,284** | NEW 2026-03-31 — ITE questions → ICD-10 via propagation. 1,512/1,629 (92.8%) coverage. Relevance: 51.6%/30.8%/17.6% |
| aafp_question_icd10 | **4,753** | Updated 2026-03-31: +921 PubMed rows, -408 cap = 4,753. Coverage: ~99% (1,210/1,221). Relevance: 42.1%/34.0%/23.8% |
| **pubmed_pmid_cache** | **344** | NEW 2026-03-31 — Layer 2 seed: citation_id → PMID for JOURNAL_MISSING citations |
| icd10_vec | 2,219 | OpenAI text-embedding-3-small, 1536d |
| article_icd10_vec | 1,674 | Stale — needs rebuild (article_icd10 +282 rows) |
| question_icd10_vec | 2,733 | Stale — needs rebuild (ITE question_icd10 now populated) |
| clinical_pathways | 3,093 | Legacy — ART-0002–ART-1397 only. Rebuild pending (v2 blueprint-based). |
| icd10_rollup | 614 | |
| icd10_code_xref | 1,006 | |
| article_vec | 1,936 | sqlite-vec virtual table |
| question_vec | 1,629 | sqlite-vec virtual table |
| aafp_questions | 1,221 | AAFP BRQ; blueprint 100%, concept_tags 100% |
| aafp_citations | 1,600 | match_status: matched(724) unmatched(717) fuzzy(73) other(86) |
| aafp_citation_raw | 1,600 | |
| aafp_qid_art_xref | 864 | 643 unique questions linked (52.7%) |
| aafp_question_vec | 1,221 | |

---

## ICD-10 Symmetry Summary (complete as of 2026-03-31)

| Layer | Table | Rows | Coverage |
|-------|-------|------|----------|
| ITE article-level | article_icd10 | 4,137 | ART-0002–ART-1397 (ITE tags) + 86 AAFP articles |
| ITE question-level | question_icd10 | 5,284 | 1,512/1,629 (92.8%) |
| AAFP question-level | aafp_question_icd10 | 4,753 | 1,210/1,221 (~99%) |
| PubMed PMID cache | pubmed_pmid_cache | 344 | Layer 2 seed |

---

## New Scripts This Session (BATON 028)

| Script | Location | What it does |
|--------|----------|--------------|
| build_ite_question_icd10.py | M2/scripts/ | Propagates article_icd10 → qid_art_xref → question_icd10. Textbook filter. Tier-aware cap. |
| backfill_aafp_article_icd10.py | M2/scripts/ | Reverse propagates aafp_question_icd10 → aafp_qid_art_xref → article_icd10 (INSERT OR IGNORE) |
| build_pubmed_citation_icd10.py | M2/scripts/ | JOURNAL_MISSING citations → NCBI eutils → PMID → MeSH → ICD-10 → aafp_question_icd10. Idempotent (resume-safe). |
| apply_aafp_related_cap.py | M2/scripts/ | Trims related codes in aafp_question_icd10 to top 3 per question by global frequency |

---

## ART-ID Insert History

| Session | ART-ID Range | Count |
|---------|-------------|-------|
| Pre-project | ART-0001 – ART-1397 | 1,397 |
| Mar 20 S1 | ART-1398 – ART-1425 | 28 |
| Mar 20 S2 | ART-1426 – ART-1548 | 123 (includes ART-0404 deleted) |
| Mar 24 | ART-1549 – ART-1937 | 389 |
| Mar 28 | ART-1938 – ART-1986 | 49 (AAFP acquisition; PDFs pending download) |
| **Next** | ART-1987 | — |

---

## Key Table Notes

**question_icd10** (NEW):
- Propagated from article_icd10 via qid_art_xref
- Textbook filter (source_type != 'Textbook') prevents broad code bleed
- Tier-aware cap: all primary + secondary kept; related capped at top 3 by contributing article frequency
- 117 questions (7.2%) have no ICD-10 path (no linked articles or all links are textbooks)

**pubmed_pmid_cache** (NEW):
- Stores citation_id (TEXT PK) → pmid for JOURNAL_MISSING citations
- 91.2% resolution rate on first run (344/377)
- Layer 2 seed: article_currency can use these PMIDs without re-querying PubMed

**article_icd10_vec + question_icd10_vec**: Both stale. Run `build_icd10_embeddings.py --derive` to refresh.
