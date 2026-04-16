# project_overhaul_state.md
Last updated: 2026-04-16 (BATON 060)

## Module State

| Module | Status | Key Info |
|--------|--------|----------|
| M1 Warehouse | Active | 988 ITE/AAFP PDFs (630 VC_fail + 168 VC_pass + 117 local_lite + 58 right_click + 15 AAFP); 8 build + 26 maintain scripts |
| M2 Processor | Active | 75 py + 6 js scripts; enrichment pipeline operational |
| M3 Analyst | Active | 50 py + 2 js + 1 json config; ICD-10, pathways, score analysis, article_currency (Layer 2), longitudinal delta, concept fingerprint enrichment, db_connect utility, citation QC, body system audit/correction |
| M4 Sandbox | Active | 1 py (nl_search_validation.py); experiments + agent prototypes |
| M5 Web Platform | Active | 3 py + 35 tsx + 5 sql; Next.js frontend, Supabase backend, Sanity CMS, Railway FastAPI |
| DB | Stable | 1,998 articles, 1,639 ITE Qs (+10 recovered), 1,221 AAFP Qs |

## PDF Library State

### ITE (citation_files/ITE/)
| Tier | Count | Notes |
|------|-------|-------|
| VC_fail | 630 | Failed VC gate; awaiting enrichment (cleaned −7 from 637, BATON 053) |
| VC_pass | 168 | Passed VC gate; awaiting enrichment |
| local_lite | 117 | Enriched; not VC-cited |
| right_click | 58 | Enriched + VC-cited (top tier) |
| _dupe_archive | 14 | Legacy single-author duplicates; not pipeline |
| **TOTAL active** | **988** | Recovered via EXA+PMC+Unpaywall; updated 2026-04-16 |

### AAFP (citation_files/AAFP/)
| Count | Status |
|-------|--------|
| 15 | Recovered 2026-04-05 (was 0 after fix_ghost.py) |

AAFP ceiling: 3 paywalled (ART-1959, ART-1972, ART-1967)

## Session Notes (BATON 060)

**2026-04-16 – Enrichment Pipeline Complete + Body System Normalization**
- **Recovered question enrichment:** 10 questions recovered and enriched through full pipeline (Steps 1-6 completed)
- **Body system corrections applied:** 22 holdout corrections for 2024-2025 deprecated labels (legacy Psychogenic → Psychiatric/Behavioral, etc.)
- **Body system normalization script:** apply_body_system_normalization.py fixed Musculoskeletal (48 QIDs), corrected QID-2021-0168, synced 376 body_system_merged records to post-2024 canonical taxonomy
- **Deferred flags CLOSED:** 
  - DEFERRED-BODY-SYSTEM-MERGED-UPDATE ✅ (body_system_merged flipped to forward mapping)
  - DEFERRED-CENTROID-REBUILD ✅ (intersection_centroid_vec rebuilt: 135 → 123 rows, 71 ITE + 52 AAFP blueprintxbody_system centroids)
- **DB state:** No new rows; field corrections only (body_system normalized for 2018-2021/2024-2025 ITE + all AAFP)
- **Script additions:** 10 new M3 scripts (audit_blueprint_by_year.py, audit_holdout_body_system.py, audit_holdout_merged.py, audit_holdout_both_axes.py, apply_holdout_body_system_corrections.py, audit_article_icd10_drop.py, apply_body_system_normalization.py, enrich_recovered_questions.py, recover_missing_questions.py, apply_recovered_questions.py)
- **Model updates:** claude-sonnet-4-6 deployed in preprocess_concept_tags.py, enrich_ite_questions.py, prompt_builder.py
- **M3 py script count:** 39 → 50 (+10 new)
- **Deferred flags NEW:** DEFERRED-PGY-BENCHMARKS (UNBLOCKED — centroid rebuild complete)

## Session Notes (BATON 059)

**2026-04-15 – Body System QC Pipeline Complete**
- **Full pipeline built:** 19 new M3 scripts created (extract_score_report_labels.py through extract_critique_refs_v2.py)
- **QC Coverage:** ITE questions 2018-2021, 2024-2025 + all 1,221 AAFP questions
- **Skills created:** body-system-qc (full audit + correction pipeline), article-citation-qc updated
- **Methodology directory:** methodology_scout/ created with 1 doc
- **Human review queue:** 201 ITE + 129 AAFP questions pending manual verification (canonical taxonomy: Psychiatric/Behavioral, Sexual and Reproductive, Injuries/Musculoskeletal)
- **Deferred flags:** DEFERRED-AAFP-BODY-SYSTEM-AUDIT CLOSED; NEW: DEFERRED-BODY-SYSTEM-MERGED-UPDATE, DEFERRED-CENTROID-REBUILD, DEFERRED-HUMAN-REVIEW-BODY-SYSTEM
- **M3 py script count:** 20 → 39 (+19 new)

## Session Notes (BATON 058)

**2026-04-15 – Citation QC Rebuild & Article Additions**
- **ITE critique ground-truth rebuild:** extract_ite_critique_refs.py modified with parse_legacy() for 2018-2023 Ref: format, fallback_citation_scan() for parser-missed items, overwrite message
- **QC audit complete:** generate_citation_sql.py created; generates full qid_art_xref rebuild SQL from staging JSONs; pdf_lookup_patch.py for direct PDF lookup SQL
- **Article additions:** add_missing_articles.py added 13 new articles (ART-1987–ART-1999) from 2024-2025 QC outputs; full xref links inserted
- **M3 outputs:** new article_qc/ folder created with qc_results.json, article_qc_report.md, article_qc_fixes.sql, pdf_lookup_patch.sql, add_missing_articles.sql
- **Skill created:** article-citation-qc skill (citation QC workflow) tested at 100% pass rate vs 0% baseline in evals
- **DB updates:** articles 1,985 → 1,998 (+13); qid_art_xref 2,470 → 2,485 (rebuilt from critique ground truth)
- **M3 py script count:** 17 → 20 (+3 new: generate_citation_sql.py, pdf_lookup_patch.py, add_missing_articles.py)
- **Deferred flags CLOSED:** DEFERRED-AAFP-BODY-SYSTEM-AUDIT, DEFERRED-KNOWN-DRUGS-EXPANSION, DEFERRED-QID-XREF-LIBRARY-GAPS (NEW-249 unmatched citations; 2024: 20 QIDs; 2025: 33 QIDs missing)

## Session Notes (BATON 057)

**2026-04-15 — Vector Integration, Unified Practice Questions Table, DB Utility**
- **ite_analyzer_v3.py enhancements:** 3 new vector functions added (_build_concept_profile, _centroid_dim_boost, _apply_concept_vec_bonus), 3 constants added for concept weighting, 3 integration points in match_practice_questions_v3() wired to TIER 1 retrieval
- **ite_report_builder_v2.js unification:** removed singleQs/crossQs split, implemented unified practice questions table with PURPLE color coding, added targetingColor() helper, description paragraph rendering, accurate weak area count
- **db_connect.py NEW UTILITY:** SQLite immutable=1 URI utility for sandbox queries; prevents journal file errors on NTFS mounts; added to M3 scripts/
- **Deferred flags CLOSED:** DEFERRED-VECTOR-TIER1-REWRITE (implemented), DEFERRED-PRACTICE-Q-TWO-TABLE (superseded by unified table)
- **New deferred flags:** DEFERRED-BODY-SYSTEM-MERGED-UPDATE, DEFERRED-CENTROID-REBUILD, DEFERRED-HUMAN-REVIEW-BODY-SYSTEM (see BATON 059 for details)
- M3 py script count: 16 → 17 (db_connect.py added)

## Session Notes (BATON 056)

**2026-04-14 — Resident Reorg & Modular Vector Build**
- **Resident data reorganization:** inputs/outputs folder structure created for all 4 residents; stale docs moved to delete_me/
- **ite_parser.py enhancements:** password support added (_find_pdf_password + _open_pdf methods)
- **ite_analyzer_v3.py fixes (12 total):** reading list personalization refinements, KNOWN_DRUGS constant added, prednisone synonym mapping
- **ite_report_builder_v2.js fixes (6 total):** trend table removed, zone label removed, guidelines table removed
- **compute_embeddings.py updates:** text builders updated (blueprint added to ITE, blueprint+body_system+concept_tags to AAFP), --rebuild flag added, BLOB parallel tables introduced
- **New M1 build scripts:** 
  - build_modular_vectors.py — blueprint/body_system label embeddings + concept_tag embeddings
  - build_intersection_centroids.py — local centroid computation for Tier 1 matching
- **New DB tables (6 total):** question_full_vec, aafp_question_full_vec, blueprint_label_vec, bodysystem_label_vec, question_concepttag_vec, intersection_centroid_vec
- **All 6 new vector tables populated and verified**
- M1 build script count: 6 → 8 (+2 new)


## Deferred Flags

| Flag | Status | Description |
|------|--------|-------------|
| DEFERRED-YOY-ROBUSTNESS | ACTIVE | Year-over-year section 3b needs more robust implementation; month-by-month trend aggregation logic (BATON 050) |
| DEFERRED-PROGRAM-TREND | UNBLOCKED | Require program-level trend analysis across multiple residents; benchmark against 2024 ABFM national reference (abfm_reference_2024.json); unblocked after centroid rebuild |
| DEFERRED-RESIDENT-FOLDER-MIGRATION | NEW | Investigate resident_data/ folder state and migration strategy to M5 platform |
| DEFERRED-VECTOR-TIER1-REWRITE | ✅ CLOSED | Implemented in BATON 057 — 3 new vector functions + 3 integration points in match_practice_questions_v3() |
| DEFERRED-PRACTICE-Q-TWO-TABLE | ✅ CLOSED | Superseded by unified practice questions table in BATON 057 (removed singleQs/crossQs split) |
| DEFERRED-AAFP-BODY-SYSTEM-AUDIT | ✅ CLOSED | AAFP body_system fields corrected (BATON 059) |
| DEFERRED-BODY-SYSTEM-MERGED-UPDATE | ✅ CLOSED | body_system_merged mapping flipped to post-2024 canonical (Psychiatric/Behavioral, Sexual and Reproductive, Injuries/Musculoskeletal) for 2018-2021 legacy data — completed BATON 060 |
| DEFERRED-CENTROID-REBUILD | ✅ CLOSED | intersection_centroid_vec rebuilt after body_system field corrections (135 → 123 rows); completed BATON 060 |
| DEFERRED-HUMAN-REVIEW-BODY-SYSTEM | ACTIVE | 201 ITE + 129 AAFP questions in human_review queue (body_system corrections pending manual verification) |
| DEFERRED-KNOWN-DRUGS-EXPANSION | ✅ CLOSED | Drugs still appearing in top diagnoses table — completed BATON 058 |
| DEFERRED-QID-XREF-LIBRARY-GAPS | ✅ CLOSED | 249 unmatched citations resolved — completed BATON 058 |
| DEFERRED-SCHOLL-OLD-FORMAT | NEW | Scholl 2022/2023 use old ABFM taxonomy (no canonical mapping); requires manual Psychogenic→Psychiatric/Behavioral remapping |
| DEFERRED-A | ARCHIVED | 37 ITE manual PDFs — permanent ceiling (subscription-only) |
| DEFERRED-AAFP-PAYWALL | ACTIVE | 3 AAFP articles paywalled (PMC not_oa): ART-1959 Binic_2011, ART-1972 Byington_2012, ART-1967 Verbalis_2007 |
| DEFERRED-PRACTICE-Q-COVERAGE | ✅ CLOSED | Practice question 0-question warnings for some body systems (Foundations, Preventive, Cardiovascular, Respiratory, Sexual-Reproductive, Psychiatric, Behavioral) — qid_art_xref tagging coverage gap (BATON 050) |
| DEFERRED-F | ✅ CLOSED | Intelligence 2.0 Layer 2 complete — article_currency built (1,985 rows) |
| DEFERRED-H | CLOSED | Legacy non-codon PDFs confirmed duplicates |
| DEFERRED-I | LOW PRI | unpaywall_scanner --from-csv extension |
| DEFERRED-J | CLOSED | exa-research-search Phase 2 completed |
| DEFERRED-L2-REVIEW | LOW PRI | Optional human review of 169 updated + 106 check_needed article_currency rows (use title_signals cross-reference) |
| DEFERRED-PGY-BENCHMARKS | UNBLOCKED | ABFM embeds PGY mean + SD in score report PDF; ite_parser.py parse_score_report() extracts; awaiting multi-year archive for trend analysis; centroid rebuild removes prior blocker |

## Intelligence 2.0 Status
- Layer 1 (ICD-10): Complete — 3,952 rows article_icd10 (rebuilt 2026-04-16); question_icd10 ~5,003 rows (89.9% coverage, ~1,474 ITE questions)
- Layer 2 (PubMed currency): ✅ COMPLETE — article_currency 1,985 rows; status enum (current:1100, updated:169, check_needed:106, not_indexed:610); title_signals column (JSON array)
- Layer 3 (Clinical pathways): Complete — 3,971 rows (cleaned −49 no_match)
- Layer 4 (Trends): Partial — trend CSV files in readable_db_files/

## Plugins & New Capabilities (BATON 049)
- **ite-score-analyzer v1.0.0** — ITE score analysis plugin built in `skills_abilities/ite-score-analyzer-v2/`
  - Four skills: analyze-ite (core report parsing), cohort-compare, ite-lookup, study-plan
  - parse_score_report() added to ite_parser.py (longitudinal delta support, Stage 2.5 pipeline)
  - report_config.json analytics configuration created
- **session-housekeeping agent templates** — Agents for baton-writer, index-memory-writer, manifest-writer created in .claude/skills/session-housekeeping/agents/; facilitate repeatable BATON and memory updates
- **Bugs FIXED (BATON 049):**
  - ✅ BUG-047-01: ite_parser.py — exam_year now extracted from PDF text (not hardcoded 2025 fallback)
  - ✅ BUG-047-02: ite_analyzer_v3.py — added BODYSYSTEM_PDF_NORM alias dict + _normalize_body_system() function for body system name normalization (handles PDF capitalization vs blueprint inconsistencies)
  - ✅ BUG-047-03: ite_analyze_v2.py — imports _normalize_body_system, applies it to body_system_scaled dict, uses official score from score report when available
  - Test reports validated: Scholl_2022, Scholl_2023, Scholl_2024, Sarkar_2025, Hopkins_2025
