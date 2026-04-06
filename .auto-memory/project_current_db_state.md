# project_current_db_state.md
Last updated: 2026-04-06 (BATON 045)

## DB: ite_intelligence.db

| Table | Rows | Notes |
|-------|------|-------|
| articles | 1,985 | +49 AAFP in BATON 042 |
| questions (ITE) | 1,629 | 2018–2025, blueprint 100% |
| aafp_questions | 1,221 | BRQ, blueprint 100% |
| qid_art_xref | 2,470 | All 8 years (2018–2025) |
| aafp_qid_art_xref | 864 | 643 unique Qs linked |
| article_icd10 | 4,020 | Rebuilt 2026-04-05 with vec |
| question_icd10 | 5,218 | 92.8% ITE coverage — cleaned -66 no_match rows |
| aafp_question_icd10 | 4,753 | Relevance normalized |
| clinical_pathways | 3,971 | Blueprint-based, rebuilt 2026-03-31; cleaned -49 no_match rows |
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

## DB Changes (BATON 045)
- question_icd10: 5,284 → 5,218 (-66 no_match rows deleted)
- clinical_pathways: 4,020 → 3,971 (-49 no_match rows deleted)
- Scripts updated: ite_analyzer_v3.py (AAFP quota fix, no_match cleanup, concept_qid_map), ite_report_builder_v2.js (major overhaul — de-identification, section restructuring, compact tables)
