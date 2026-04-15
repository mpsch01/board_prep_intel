# project_current_db_state.md
Last verified: 2026-04-15 (BATON 058)

## DB: ite_intelligence.db

| Table | Rows | Notes |
|-------|------|-------|
| articles | 1,998 | +13 new (ART-1987–ART-1999) from BATON 058 QC rebuild; +49 AAFP in BATON 042 |
| questions (ITE) | 1,629 | 2018–2025, blueprint 100% |
| aafp_questions | 1,221 | BRQ, blueprint 100% |
| qid_art_xref | 2,485 | All 8 years (2018–2025); rebuilt from critique ground truth in BATON 058 |
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
| question_full_vec | 1,629 | BLOB – full question embedding with blueprint (NEW – BATON 056) |
| aafp_question_full_vec | 1,221 | BLOB – full AAFP embedding with blueprint+body_system+concept_tags (NEW – BATON 056) |
| blueprint_label_vec | 5 | BLOB – 5 canonical blueprint category label embeddings (NEW – BATON 056) |
| bodysystem_label_vec | 5 | BLOB – 5 canonical body system label embeddings (NEW – BATON 056) |
| question_concepttag_vec | 2,850 | BLOB – concept_tags embedding per question (NEW – BATON 056) |
| intersection_centroid_vec | 135 | BLOB – 71 ITE + 64 AAFP blueprint×body_system centroids (NEW – BATON 056) |

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

## DB Changes (BATON 054)
- No DB modifications this session (2026-04-12)
- Script development: ite_analyze_v2.py, ite_analyzer_v3.py, ite_report_builder_v2.js refined
- New reference file: abfm_reference_2024.json (ABFM 2024 national benchmarks)


## DB Changes (BATON 058)
- articles: 1,985 → 1,998 (+13 new: ART-1987–ART-1999 from critique QC rebuild)
- qid_art_xref: 2,470 → 2,485 (rebuilt from 2018–2025 ITE critique ground truth; replaces parser-inferred xrefs with direct PDF citations)
- No schema changes; no modifications to other tables
- Scripts added: generate_citation_sql.py, pdf_lookup_patch.py, add_missing_articles.py (M3)

## DB Changes (BATON 056)
- 6 new modular vector BLOB tables added (2026-04-14):
  - question_full_vec (1,629 rows) — full question embedding with blueprint
  - aafp_question_full_vec (1,221 rows) — full AAFP embedding with blueprint+body_system+concept_tags
  - blueprint_label_vec (5 rows) — 5 canonical blueprint category label embeddings
  - bodysystem_label_vec (5 rows) — 5 canonical body system label embeddings
  - question_concepttag_vec (2,850 rows) — concept_tags embedding per question
  - intersection_centroid_vec (135 rows) — 71 ITE + 64 AAFP blueprint×body_system centroids
- All new tables populated and verified via build_modular_vectors.py + build_intersection_centroids.py
- Schema note: BATON 056 — Added 6 modular vector BLOB tables (question_full_vec, aafp_question_full_vec, blueprint_label_vec, bodysystem_label_vec, question_concepttag_vec, intersection_centroid_vec)
- No row count changes to existing tables; no modifications to article, question, or reference integrity