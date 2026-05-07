# project_current_db_state.md
Last verified: 2026-05-07 (BATON 067)

## DB: ite_intelligence.db

| Table | Rows | Notes |
|-------|------|-------|
| articles | 2,206 | Stable from BATON 065 (no new articles BATON 067) |
| questions (ITE) | 1,639 | 2018–2025 (+10 recovered), blueprint 100% |
| aafp_questions | 1,221 | BRQ, blueprint 100% |
| qid_art_xref | 2,710 | All 8 years (2018–2025); stable from BATON 065 |
| aafp_qid_art_xref | 864 | 643 unique Qs linked |
| article_icd10 | 4,959 | Stable; pre-existing Windows PC enrichment (BATON 062) |
| question_icd10 | 5,774 | ~89.9%+ ITE coverage; stable (BATON 062) |
| aafp_question_icd10 | 4,753 | Relevance normalized |
| clinical_pathways | 4,959 | Stable (BATON 062) |
| article_citation_trend | 1,740 | Longitudinal citation tracking + watch_list flag |
| article_currency | 2,206 | ✅ COMPLETE — Layer 2 Intelligence; mirrors articles; status enum and title_signals JSON column maintained |
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
| intersection_centroid_vec | 158 | BLOB – Stable (BATON 062) |

## Schema Notes
- subcategory + topic_label DROPPED from questions (ITE)
- aafp_questions: correct_letter, correct_text, explanation merged in; subcategory + aafp_explanations DROPPED
- QID format: QID-YYYY-NNNN (per-year numbering, resets each exam year)
- ART-ID format: ART-XXXX (zero-padded 4 digits)
- Next ART-ID: ART-2219 (last assigned ART-2206 BATON 065; gap reservations brought ceiling to 2219)
- **body_system field:** Fully normalized to post-2024 ABFM canonical taxonomy (Psychiatric/Behavioral, Sexual and Reproductive, Injuries/Musculoskeletal) for ITE 2018-2021, 2024-2025, and all AAFP (BATON 060)
- **body_system_merged field:** Forward mapping applied (BATON 060)

## Schema Notes — article_currency (NEW, BATON 046)
- Columns: article_id (FK), status (ENUM: 'current', 'updated', 'check_needed', 'not_indexed'), title_signals (TEXT JSON array), pubmed_pmid (INT FK)
- title_signals: JSON array of clinical category keywords (extracted from blueprint cross-reference; used for future filtering + human review)
- Populated via build_article_currency.py (M3 script)

## DB Changes (BATON 067)
- **No DB changes this session.** All counts stable from BATON 065.
- Session focus was AFP PDF acquisition (72 articles closed, gap 83 → 11) and BATON 066 worktree merge to main.
- 127 BATON 066 PDFs migrated FROM worktree TO main repo via robocopy + Move-Item.
- Articles for AFP-acquired PDFs were already cataloged from BATON 065 (acquire_missing_citations.py); no new article rows needed.
- **Script changes:** M1 maintain +9 net new (8 BATON 066 scripts merged from worktree + 1 NEW: aafp_targeted_downloader.py); aafp_fill_gaps.py modified (Playwright expect_download → context.request.get patch).
- **Structural cleanup:** _dupe_archive (48) + _corrupted_targeted_run (79) cleared via delete_me_pdfs_b65 staging then permanent deletion.

## DB Changes (BATON 066)
- **No DB changes this session.** All counts stable from BATON 065.
- Session focus was PDF acquisition (JAMA + NEJM) only — 127 new PDFs harvested (in worktree pending merge).
- xref linkage to be performed after worktree merge in next session.
- **Script additions only:** M1 maintain +8 scripts (jama_chrome_harvester.py, jama_prep_articlepdf_urls.py, nejm_doi_lookup.py, nejm_build_js_batch.py, nejm_console_script.py, nejm_move_downloads.py, nejm_save_server.py, unpaywall_retry.py) — all in worktree, pending merge.

## DB Changes (BATON 065)
- **Phase 2 PDF acquisition:** articles 1,998 → 2,206 (+208 new articles ART-1999–ART-2206)
- **qid_art_xref:** 2,485 → 2,710 (+225 citations linked during batch import)
- **article_currency:** 1,998 → 2,206 (mirrors articles table; status enum + title_signals JSON preserved)
- **No schema changes; no modifications to other tables**
- **Script additions:** M1 maintain +4 scripts (acquire_missing_citations.py, playwright_auth_downloader.py, browser_pdf_harvester.py, setup_journal_auth.py)
- **JAMA/NEJM:** playwright_auth_downloader.py IP-blocked; jama_pending.json output created for manual/Claude Code handoff

## DB Changes (BATON 063)
- **No DB changes this session.** All counts stable from BATON 062. Focus was DOCX guide generation (resident + faculty interpretation guides).
- **Script additions only:** M3 build_resident_guide.py, build_faculty_guide.py, build_resident_guide.js, build_faculty_guide.js (Python canonical per Rule 14)
- **word_doc_defaults.py enhanced** with level-aware add_section_header() function

## DB Changes (BATON 062)
- Pre-existing Windows PC enrichment discovered and migrated to Mac:
  - article_icd10: 3,952 → 4,959 (+1,007)
  - question_icd10: ~5,003 → 5,774 (+771)
  - clinical_pathways: 3,971 → 4,959 (+988)
  - intersection_centroid_vec: 123 → 158 (+35)
- No new articles or questions added; no schema changes
- M3 script improvements: ite_analyze_v2.py, ite_analyzer_v3.py, ite_report_builder_v2.js (3 files modified for report builder issues 1-5)
- Platform migration: Project copied from Windows home PC to Mac via external HD; DB and PDFs intact

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

## Key Metric Changes Since BATON 064

| Metric | BATON 064 | BATON 065 | BATON 066 | BATON 067 | Change (064→067) | Notes |
|--------|-----------|-----------|-----------|-----------|------------------|-------|
| articles | 1,998 | 2,206 | 2,206 | 2,206 | +208 | EXA + Unpaywall batch acquisition (BATON 065) |
| qid_art_xref | 2,485 | 2,710 | 2,710 | 2,710 | +225 | New article xref linkages (BATON 065) |
| article_currency | 1,998 | 2,206 | 2,206 | 2,206 | +208 | Mirrors articles table (BATON 065) |
| ITE PDFs (active tiers) | 988 | 1,254 | 1,381 (worktree, pre-merge) | 1,540 (post-merge + AFP) | +552 | EXA/Unpaywall +266 (BATON 065); JAMA/NEJM +127 merged (BATON 067); AFP +72/cleanup -127 (BATON 067) |
| M1 maintain scripts | 26 | 30 | 36 (worktree) | 38 (main; +1 NEW BATON 067) | +12 | +4 BATON 065; +8 BATON 066 merged BATON 067; +1 NEW BATON 067 (aafp_targeted_downloader.py); aafp_fill_gaps.py modified |
| All other tables | stable | stable | stable | stable | 0 | No DB changes BATON 067 |
