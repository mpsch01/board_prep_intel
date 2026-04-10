# project_current_db_state.md
Last verified: 2026-04-10 (BATON 052)

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
| article_citation_trend | 1,740 | Longitudinal citation tracking + watch_list flag |
| article_currency | 1,985 | ✅ NEW — Layer 2 Intelligence complete; status enum (current:1100, updated:169, check_needed:106, not_indexed:610); title_signals JSON array column |
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

## Schema Notes — article_currency (NEW, BATON 046)
- Columns: article_id (FK), status (ENUM: 'current', 'updated', 'check_needed', 'not_indexed'), title_signals (TEXT JSON array), pubmed_pmid (INT FK)
- status breakdown: current:1100, updated:169, check_needed:106, not_indexed:610
- title_signals: JSON array of clinical category keywords (extracted from blueprint cross-reference; used for future filtering + human review)
- Populated via build_article_currency.py (M3 script)

## DB Changes (BATON 046)
- article_currency: NEW — 1,985 rows — Layer 2 Intelligence complete
- Scripts added: build_article_currency.py (M3)

## DB Changes (BATON 052)
- questions.body_system_merged: Psychogenic → Psychiatric/Behavioral (120 rows updated, confirmed 2026-04-10 via retire_psychogenic.py)
- aafp_questions.body_system: Psychogenic → Psychiatric/Behavioral (82 rows updated)
- All row counts unchanged from BATON 051
