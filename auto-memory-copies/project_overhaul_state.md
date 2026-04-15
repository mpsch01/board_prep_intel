# project_overhaul_state.md
Last updated: 2026-04-15 (BATON 059)

## Module State

| Module | Status | Key Info |
|--------|--------|----------|
| M1 Warehouse | Active | 988 ITE/AAFP PDFs (630 VC_fail + 168 VC_pass + 117 local_lite + 58 right_click + 15 AAFP); 8 build + 26 maintain scripts |
| M2 Processor | Active | 75 py + 6 js scripts; enrichment pipeline operational |
| M3 Analyst | Active | 39 py + 2 js + 1 json config; ICD-10, pathways, score analysis, article_currency (Layer 2), longitudinal delta, concept fingerprint enrichment, db_connect utility, citation QC |
| M4 Sandbox | Active | 1 py (nl_search_validation.py); experiments + agent prototypes |
| M5 Web Platform | Active | 3 py + 35 tsx + 5 sql; Next.js frontend, Supabase backend, Sanity CMS, Railway FastAPI |
| DB | Stable | 1,998 articles, 1,629 ITE Qs, 1,221 AAFP Qs |

## PDF Library State

### ITE (citation_files/ITE/)
| Tier | Count | Notes |
|------|-------|-------|
| VC_fail | 630 | Failed VC gate; awaiting enrichment (cleaned -7 from 637, BATON 053) |
| VC_pass | 168 | Passed VC gate; awaiting enrichment |
| local_lite | 117 | Enriched; not VC-cited |
| right_click | 58 | Enriched + VC-cited (top tier) |
| _dupe_archive | 14 | Legacy single-author duplicates; not pipeline |
| **TOTAL active** | **973** | Recovered via EXA+PMC+Unpaywall; updated 2026-04-09 |

### AAFP (citation_files/AAFP/)
| Count | Status |
|-------|--------|
| 15 | Recovered this session (was 0 after fix_ghost.py) |

AAFP ceiling: 3 paywalled (ART-1959, ART-1972, ART-1967)

## Session Notes (BATON 059)

**2026-04-15 – Body System QC Pipeline Complete**
- **Full pipeline built:** 19 new M3 scripts created (extract_score_report_labels.py, condense_taxonomy.py, build_training_set.py, run_svm_baseline.py, run_claude_classifier.py, submit_batch_classification.py, submit_batch_aafp.py, retrieve_batch_results.py, rename_taxonomy_labels.py, fix_taxonomy_names.py, fix_aafp_taxonomy_names.py, generate_body_system_sql.py, svm_review_audit.py, check_aafp_body_system.py, check_aafp_results.py, check_aafp_schema.py, verify_body_system_updates.py, critique_pdf_registry.py, extract_critique_refs_v2.py)
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

**2026-04-15 â€“ Vector Integration, Unified Practice Questions Table, DB Utility**
- **ite_analyzer_v3.py enhancements:** 3 new vector functions added (_build_concept_profile, _centroid_dim_boost, _apply_concept_vec_bonus), 3 constants added for concept weighting, 3 integration points in match_practice_questions_v3() wired to TIER 1 retrieval
- **ite_report_builder_v2.js unification:** removed singleQs/crossQs split, implemented unified practice questions table with PURPLE color coding, added targetingColor() helper, description paragraph rendering, accurate weak area count
- **db_connect.py NEW UTILITY:** SQLite immutable=1 URI utility for sandbox queries; prevents journal file errors on NTFS mounts; added to M3 scripts/
- **Deferred flags CLOSED:** DEFERRED-VECTOR-TIER1-REWRITE (implemented), DEFERRED-PRACTICE-Q-TWO-TABLE (superseded by unified table)
| DEFERRED-BODY-SYSTEM-MERGED-UPDATE | NEW-ACTIVE | body_system_merged mapping must flip to post-2024 canonical (Psychiatric/Behavioral, Sexual and Reproductive, Injuries/Musculoskeletal) for 2018-2021 legacy data |
| DEFERRED-CENTROID-REBUILD | NEW-ACTIVE | intersection_centroid_vec must be rebuilt after body_system field corrections (affects Tier 1 semantic matching) |
| DEFERRED-HUMAN-REVIEW-BODY-SYSTEM | NEW-ACTIVE | 201 ITE + 129 AAFP questions in human_review queue (body_system corrections pending review) |
- **New deferred flags:** DEFERRED-AAFP-BODY-SYSTEM-AUDIT (possible body_system mislabeling in AAFP questions), DEFERRED-KNOWN-DRUGS-EXPANSION (drugs appearing in top diagnoses)
- M3 py script count: 16 â†’ 17 (db_connect.py added)

## Session Notes (BATON 056)

**2026-04-14 â€“ Resident Reorg & Modular Vector Build**
- **Resident data reorganization:** inputs/outputs folder structure created for all 4 residents; stale docs moved to delete_me/
- **ite_parser.py enhancements:** password support added (_find_pdf_password + _open_pdf methods)
- **ite_analyzer_v3.py fixes (12 total):** reading list personalization refinements, KNOWN_DRUGS constant added, prednisone synonym mapping
- **ite_report_builder_v2.js fixes (6 total):** trend table removed, zone label removed, guidelines table removed
- **compute_embeddings.py updates:** text builders updated (blueprint added to ITE, blueprint+body_system+concept_tags to AAFP), --rebuild flag added, BLOB parallel tables introduced
- **New M1 build scripts:** 
  - build_modular_vectors.py â€” blueprint/body_system label embeddings + concept_tag embeddings
  - build_intersection_centroids.py â€” local centroid computation for Tier 1 matching
- **New DB tables (6 total):** question_full_vec, aafp_question_full_vec, blueprint_label_vec, bodysystem_label_vec, question_concepttag_vec, intersection_centroid_vec
- **All 6 new vector tables populated and verified**
- M1 build script count: 6 â†’ 8 (+2 new)


## Deferred Flags

| Flag | Status | Description |
|------|--------|-------------|
| DEFERRED-YOY-ROBUSTNESS | ACTIVE | Year-over-year section 3b needs more robust implementation; month-by-month trend aggregation logic (BATON 050) |
| DEFERRED-PROGRAM-TREND | NEW | Require program-level trend analysis across multiple residents; benchmark against 2024 ABFM national reference (abfm_reference_2024.json) |
| DEFERRED-RESIDENT-FOLDER-MIGRATION | NEW | Investigate resident_data/ folder state and migration strategy to M5 platform |
| DEFERRED-VECTOR-TIER1-REWRITE | âœ… CLOSED | Implemented in BATON 057 â€” 3 new vector functions + 3 integration points in match_practice_questions_v3() |
| DEFERRED-PRACTICE-Q-TWO-TABLE | âœ… CLOSED | Superseded by unified practice questions table in BATON 057 (removed singleQs/crossQs split) |
| DEFERRED-AAFP-BODY-SYSTEM-AUDIT | CLOSED | AAFP body_system fields may be mislabeled; needs sweep to verify alignment with blueprint |
| DEFERRED-KNOWN-DRUGS-EXPANSION | ACTIVE | Drugs still appearing in top diagnoses table; expand KNOWN_DRUGS constant |
| DEFERRED-QID-XREF-LIBRARY-GAPS | NEW-ACTIVE | 249 unmatched citations in ITE critique refs; 2024: 20 QIDs missing xrefs; 2025: 33 QIDs missing xrefs |
| DEFERRED-SCHOLL-OLD-FORMAT | NEW | Scholl 2022/2023 use old ABFM taxonomy (no canonical mapping); requires manual Psychogenicâ†’Psychiatric/Behavioral remapping |
| DEFERRED-A | ARCHIVED | 37 ITE manual PDFs â€” permanent ceiling (subscription-only) |
| DEFERRED-AAFP-PAYWALL | ACTIVE | 3 AAFP articles paywalled (PMC not_oa): ART-1959 Binic_2011, ART-1972 Byington_2012, ART-1967 Verbalis_2007 |
| DEFERRED-PRACTICE-Q-COVERAGE | âœ… CLOSED | Practice question 0-question warnings for some body systems (Foundations, Preventive, Cardiovascular, Respiratory, Sexual-Reproductive, Psychiatric, Behavioral) â€” qid_art_xref tagging coverage gap (BATON 050) |
| DEFERRED-F | âœ… CLOSED | Intelligence 2.0 Layer 2 complete â€” article_currency built (1,985 rows) |
| DEFERRED-H | CLOSED | Legacy non-codon PDFs confirmed duplicates |
| DEFERRED-I | LOW PRI | unpaywall_scanner --from-csv extension |
| DEFERRED-J | CLOSED | exa-research-search Phase 2 completed |
| DEFERRED-L2-REVIEW | LOW PRI | Optional human review of 169 updated + 106 check_needed article_currency rows (use title_signals cross-reference) |
| DEFERRED-PGY-BENCHMARKS | PARTIALLY SOLVED | ABFM embeds PGY mean + SD in score report PDF; ite_parser.py parse_score_report() extracts; awaiting multi-year archive for trend analysis |

## Intelligence 2.0 Status
- Layer 1 (ICD-10): Complete â€” 4,020 rows article_icd10; question_icd10 5,218 rows (cleaned -66 no_match)
- Layer 2 (PubMed currency): âœ… COMPLETE â€” article_currency 1,985 rows; status enum (current:1100, updated:169, check_needed:106, not_indexed:610); title_signals column (JSON array)
- Layer 3 (Clinical pathways): Complete â€” 3,971 rows (cleaned -49 no_match)
- Layer 4 (Trends): Partial â€” trend CSV files in readable_db_files/

## Plugins & New Capabilities (BATON 049)
- **ite-score-analyzer v1.0.0** â€” ITE score analysis plugin built in `skills_abilities/ite-score-analyzer-v2/`
  - Four skills: analyze-ite (core report parsing), cohort-compare, ite-lookup, study-plan
  - parse_score_report() added to ite_parser.py (longitudinal delta support, Stage 2.5 pipeline)
  - report_config.json analytics configuration created
- **session-housekeeping agent templates** â€“ Agents for baton-writer, index-memory-writer, manifest-writer created in .claude/skills/session-housekeeping/agents/; facilitate repeatable BATON and memory updates
- **Bugs FIXED (BATON 049):**
  - âœ… BUG-047-01: ite_parser.py â€” exam_year now extracted from PDF text (not hardcoded 2025 fallback)
  - âœ… BUG-047-02: ite_analyzer_v3.py â€” added BODYSYSTEM_PDF_NORM alias dict + _normalize_body_system() function for body system name normalization (handles PDF capitalization vs blueprint inconsistencies)
  - âœ… BUG-047-03: ite_analyze_v2.py â€” imports _normalize_body_system, applies it to body_system_scaled dict, uses official score from score report when available
  - Test reports validated: Scholl_2022, Scholl_2023, Scholl_2024, Sarkar_2025, Hopkins_2025
- **BATON 050 improvements (2026-04-08):**
  - ite_analyzer_v3.py: removed recency bonus, removed ORDER BY exam_year DESC from 3 tier SQL queries, changed limits 20â†’60, added current_exam_year exclusion with int cast
  - ite_analyze_v2.py: added --skip-reading-list and --question-count CLI flags; SKIP_READING_LIST env var passed to Node
  - ite_report_builder