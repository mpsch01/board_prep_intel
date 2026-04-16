# project_current_db_state.md
Last verified: 2026-04-16 (BATON 061)

## DB: ite_intelligence.db

| Table | Rows | Notes |
|-------|------|-------|
| articles | 1,998 | +13 new (ART-1987–ART-1999) from BATON 058 QC rebuild; +49 AAFP in BATON 042 |
| questions (ITE) | 1,639 | 2018–2025 (+10 recovered this session), blueprint 100% |
| aafp_questions | 1,221 | BRQ, blueprint 100% |
| qid_art_xref | 2,485 | All 8 years (2018–2025); rebuilt from critique ground truth in BATON 058 |
| aafp_qid_art_xref | 864 | 643 unique Qs linked |
| article_icd10 | 3,952 | Rebuilt 2026-04-16 with synonym normalization (−68 from prior 4,020) |
| question_icd10 | ~5,003 | ~89.9% ITE coverage (1,474/1,639 ITE questions tagged) — updated 2026-04-16 |
| aafp_question_icd10 | 4,753 | Relevance normalized |
| clinical_pathways | 3,971 | Blueprint-based, rebuilt 2026-03-31; cleaned −49 no_match rows |
| article_citation_trend | 1,740 | Longitudinal citation tracking + watch_list flag |
| article_currency | 1,998 | ✅ COMPLETE 2026-04-16 — Layer 2 Intelligence complete; status enum (current:1100, updated:169, check_needed:106, not_indexed:610); title_signals JSON array column |
| pubmed_pmid_cache | 344 | Layer 2 seed |
| article_icd10_vec | 1,757 | Rebuilt 2026-04-05 |
| question_icd10_vec | 2,747 | Rebuilt 2026-04-05 |
| icd10_vec | 2,219 | text-embedding-3-small (1536d) |
| article_vec | 1,998 | sqlite-vec virtual table (rebuilt 2026-04-16) |
| question_vec | 1,639 | sqlite-vec virtual table (rebuilt 2026-04-16) |
| aafp_question_vec | 1,221 | sqlite-vec virtual table |
| question_full_vec | 1,639 | BLOB – full question embedding with blueprint (NEW – BATON 056) |
| aafp_question_full_vec | 1,221 | BLOB – full AAFP embedding with blueprint+body_system+concept_tags (NEW – BATON 056) |
| blueprint_label_vec | 5 | BLOB – 5 canonical blueprint category label embeddings (NEW – BATON 056) |
| bodysystem_label_vec | 5 | BLOB – 5 canonical body system label embeddings (NEW – BATON 056) |
| question_concepttag_vec | 2,850 | BLOB – concept_tags embedding per question (NEW – BATON 056) |
| intersection_centroid_vec | 123 | BLOB – 71 ITE + 52 AAFP blueprint×body_system centroids (rebuilt 2026-04-16) |

## Schema Notes
- subcategory + topic_label DROPPED from questions (ITE)
- aafp_questions: correct_letter, correct_text, explanation merged in; subcategory + aafp_explanations DROPPED
- QID format: QID-YYYY-NNNN (per-year numbering, resets each exam year)
- ART-ID format: ART-XXXX (zero-padded 4 digits)
- Next ART-ID: ART-2000
- **body_system field:** Fully normalized to post-2024 ABFM canonical taxonomy (Psychiatric/Behavioral, Sexual and Reproductive, Injuries/Musculoskeletal) for ITE 2018-2021, 2024-2025, and all AAFP (BATON 060)
- **body_system_merged field:** Forward mapping applied (BATON 060)

## Schema Notes — article_currency (NEW, BATON 046)
- Columns: article_id (FK), status (ENUM: 'current', 'updated', 'check_needed', 'not_indexed'), title_signals (TEXT JSON array), pubmed_pmid (INT FK)
- status breakdown: current:1100, updated:169, check_needed:106, not_indexed:610
- title_signals: JSON array of clinical category keywords (extracted from blueprint cross-reference; used for future filtering + human review)
- Populated via build_article_currency.py (M3 script)

## DB Changes (BATON 061)
- No new rows added; field corrections + analysis completions only
- article_currency: 1,985 → 1,998 (updated for 13 new articles ART-1987–ART-1999)
- All 7 resident analyses re-run with Stage 1.75 DB body_system backfill
- ite_analyze_v2.py: New Stage 1.75 DB body_system backfill pipeline added
- ite_analyzer_v3.py: pathway_gap_map() LEFT JOIN fixed (icd10_desc column now included)
- intersection_centroid_vec: verified complete (123 rows, 71 ITE + 52 AAFP)

## DB Changes (BATON 060)
- questions (ITE): 1,629 → 1,639 (+10 recovered questions enriched this session)
- article_icd10: 4,020 → 3,952 (−68 from synonym map variance in rebuild 2026-04-16)
- question_icd10: ~5,218 → ~5,003 (~89.9% coverage: 1,474/1,639 ITE questions tagged)
- article_vec: rebuilt 2026-04-16 (1,998 rows)
- question_vec: rebuilt 2026-04-16 (1,639 rows)
- intersection_centroid_vec: 135 → 123 rows (rebuilt 2026-04-16: 71 ITE + 52 AAFP centroids)
- body_system field: Fully normalized (22 holdout corrections applied, Musculoskeletal fixed, QID-2021-0168 corrected, 376 body_system_merged records synced)
- No schema changes; no new rows except recovered questions

## DB Changes (BATON 058)
- articles: 1,985 → 1,998 (+13 new: ART-1987–ART-1999 from critique QC rebuild)
- qid_art_xref: 2,470 → 2,485 (rebuilt from 2018–2025 ITE critique ground truth; replaces parser-inferred xrefs with direct PDF citations)
- No schema changes; no modifications to other tables
- Scripts added: generate_citation_sql.py, pdf_lookup_patch.py, add_missing_articles.py (M3)

## DB Changes (BATON 057)
- No row count changes (vector integration only)
- 3 new vector functions in ite_analyzer_v3.py (_build_concept_profile, _centroid_dim_boost, _apply_concept_vec_bonus)
- Unified practice questions table implemented in ite_report_builder_v2.js (removed singleQs/crossQs split)
- db_connect.py utility added (SQLite immutable=1 URI for NTFS compatibility)

## DB Changes (BATON 056)
- 6 new modular vector BLOB tables added (2026-04-14):
  - question_full_vec (1,639 rows) — full question embedding with blueprint
  - aafp_question_full_vec (1,221 rows) — full AAFP embedding with blueprint+body_system+concept_tags
  - blueprint_label_vec (5 rows) — 5 canonical blueprint category label embeddings
  - bodysystem_label_vec (5 rows) — 5 canonical body system label embeddings
  - question_concepttag_vec (2,850 rows) — concept_tags embedding per question
  - intersection_centroid_vec (135 rows) — 71 ITE + 64 AAFP blueprint×body_system centroids (updated to 123 in BATON 060)
- All 6 new vector tables populated and verified

## DB Changes (BATON 054)
- No DB modifications this session (2026-04-12)
- Script development: ite_analyze_v2.py, ite_analyzer_v3.py, ite_report_builder_v2.js refined
- New reference file: abfm_reference_2024.json (ABFM 2024 national benchmarks)

## DB Changes (BATON 052)
- questions.body_system_merged: Psychogenic → Psychiatric/Behavioral (120 rows updated, confirmed 2026-04-10 via retire_psychogenic.py)
- aafp_questions.body_system: Psychogenic → Psychiatric/Behavioral (82 rows updated)
- All row counts unchanged from BATON 051

## DB Changes (BATON 046)
- article_currency: NEW — 1,985 rows — Layer 2 Intelligence complete
- Scripts added: build_article_currency.py (M3)

## Key Metric Changes Since BATON 059

| Metric | BATON 059 | BATON 060 | BATON 061 | Change (059→061) | Notes |
|--------|-----------|-----------|-----------|--------|-------|
| questions (ITE) | 1,629 | 1,639 | 1,639 | +10 | Recovered questions enriched (BATON 060) |
| article_icd10 | 4,020 | 3,952 | 3,952 | −68 | Synonym map normalization variance (BATON 060) |
| question_icd10 | ~5,218 | ~5,003 | ~5,003 | −215 approx | 89.9% coverage update (BATON 060) |
| article_vec | stale | 1,998 | 1,998 | rebuilt | Consistent with articles table (BATON 060) |
| question_vec | stale | 1,639 | 1,639 | rebuilt | Consistent with ITE questions table (BATON 060) |
| article_currency | stale | 1,985 | 1,998 | rebuilt | Layer 2 Intelligence complete (BATON 061) |
| intersection_centroid_vec | 135 | 123 | 123 | −12 | Rebuilt after body_system normalization (BATON 060) |
| M3 scripts | 39 | 50 | 50 | +10 py | Stage 1.75 pipeline additions (BATON 060); pathway fix (BATON 061) |
