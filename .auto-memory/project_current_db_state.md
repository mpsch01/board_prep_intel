# project_current_db_state.md
Last updated: 2026-04-05 (BATON 044)

## DB: ite_intelligence.db

| Table | Rows | Notes |
|-------|------|-------|
| articles | 1,985 | +49 AAFP in BATON 042 |
| questions (ITE) | 1,629 | 2018–2025, blueprint 100% |
| aafp_questions | 1,221 | BRQ, blueprint 100% |
| qid_art_xref | 2,470 | All 8 years (2018–2025) |
| aafp_qid_art_xref | 864 | 643 unique Qs linked |
| article_icd10 | 4,020 | Rebuilt 2026-04-05 with vec |
| question_icd10 | 5,284 | 92.8% ITE coverage |
| aafp_question_icd10 | 4,753 | Relevance normalized |
| clinical_pathways | 4,020 | Blueprint-based, rebuilt 2026-03-31 |
| pubmed_pmid_cache | 344 | Layer 2 seed |
| article_icd10_vec | 1,757 | Rebuilt 2026-04-05 |
| question_icd10_vec | 2,747 | Rebuilt 2026-04-05 |
| icd10_vec | 2,219 | text-embedding-3-small (1536d) |

## Schema Notes
- subcategory + topic_label DROPPED from questions (ITE)
- aafp_questions: correct_letter, correct_text, explanation merged in; subcategory + aafp_explanations DROPPED
- QID format: QID-YYYY-NNNN (per-year numbering, resets each exam year)
- ART-ID format: ART-XXXX (zero-padded 4 digits)
- Next ART-ID: ART-1987

## No DB changes this session (BATON 044)
All work was PDF recovery and script creation. DB is stable.
