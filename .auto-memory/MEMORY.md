# .auto-memory/MEMORY.md — Memory Index
Last updated: 2026-04-15 (BATON 060)

## Active Memory Files
- [project_overhaul_state.md](project_overhaul_state.md) — Module state, PDF counts, key numbers, deferred flags, Intelligence 2.0 layer status
- [project_current_db_state.md](project_current_db_state.md) — DB table row counts (1,998 articles, 1,639 ITE Qs), schema state; body_system + body_system_merged fully normalized (BATON 060)
- [rebuild_structuring_guidelines.md](rebuild_structuring_guidelines.md) — Locked rules and architecture principles
- [glossary.md](glossary.md) — Project terminology decoder

## Session Feedback + Policy Updates
- [feedback_reco_cleanup_closed.md](feedback_reco_cleanup_closed.md) — RECO folder cleanup DONE; never carry forward
- [feedback_js_rule_update.md](feedback_js_rule_update.md) — JS rule relaxed: "Build in whatever language fits; flag if multilingual clutter accumulates"

## Practice Q Coverage Fix (BATON 052)
- [DEFERRED-PRACTICE-Q-COVERAGE: Root causes found and fixed](memory/feedback_psychogenic_retired.md) — Psychogenic body system fully retired; 3 root causes resolved

## Bug Fixes (BATON 049)
- **BUG-047-01 FIXED** — ite_parser.py exam_year extraction: now parses from PDF text instead of hardcoded 2025 fallback
- **BUG-047-02 FIXED** — ite_analyzer_v3.py body system normalization: added BODYSYSTEM_PDF_NORM dict + _normalize_body_system() function to handle PDF vs blueprint capitalization inconsistencies
- **BUG-047-03 FIXED** — ite_analyze_v2.py: imports normalize function, applies to body_system_scaled dict, prefers official score from score report when available
- Test validation: Scholl_2022, 2023, 2024, Sarkar_2025, Hopkins_2025 all passing

## Deployments (BATON 051)
- [Module 5 web platform scaffold added](project_overhaul_state.md) — 05_module.5_web/ (Next.js+Supabase+Sanity+Railway) committed by Copilot 2026-04-08; docs updated BATON 051

## Script Refactoring (BATON 054)
- [ite_report_builder_v2.js: 18-edit multi-year resident redesign](feedback_report_builder_redesign_054.md) — Major revision for improved year-over-year rendering; ABFM reference benchmark integration; section 3b temporal aggregation hardened

## Architecture Decisions (BATON 055)
- [ICD-10 Hidden Enrichment Layer](architecture_icd10_hidden_enrichment.md) — ICD-10 codes used as taxonomy-stable scoring layer in practice question matching; invisible to resident reports; taxonomy-stable precision without concept-tag label variance

## Architecture Decisions (BATON 056)
- [Modular Vector Architecture](memory/modular_vector_architecture.md) — 5-dimensional embedding scheme (blueprint labels, body system labels, concept tags, full question, intersection centroids) for semantic+structural matching in Tier 1 practice question retrieval; enables learner ICD-10 profile integration and future ablation studies

## Vector Integration (BATON 057)
- [db_connect.py — immutable URI DB utility](db_connect_utility.md) — Use open_db() for sandbox SQLite queries; immutable=1 avoids journal file errors on NTFS mount

## Normalization + Enrichment Pipeline (BATON 060)
- **body_system fully normalized:** Musculoskeletal rename (48 records), QID-2021-0168 → Respiratory, 376 body_system_merged records synced to post-2024 canonical — apply_body_system_normalization.py
- **DEFERRED-BODY-SYSTEM-MERGED-UPDATE CLOSED** — body_system_merged now correctly mirrors body_system for canonical records; only intentional bridges remain (Psychogenic×38, Patient-Based Systems×4)
- **DEFERRED-CENTROID-REBUILD CLOSED** — intersection_centroid_vec rebuilt (135→123 rows)
- **10 questions recovered + fully enriched** — Steps 1–6 complete (blueprint, body_system, concept tags, ICD-10, vectors, centroids)
- **Resident re-analyses now FULLY UNBLOCKED** — all prior blockers resolved

## Body System QC Pipeline (BATON 059)
- [body-system-qc skill — complete audit + correction pipeline](project_overhaul_state.md) — 19 new M3 scripts for ITE 2018-2021, 2024-2025 + AAFP 1,221 questions; SVM baseline + Claude classification + review workflow
- **Post-2024 canonical taxonomy locked:** Psychiatric/Behavioral (vs legacy Psychogenic), Sexual and Reproductive, Injuries/Musculoskeletal
- **Files API infrastructure built** — critique_pdf_registry.py tracks 2018-2025 ITE PDFs; extract_critique_refs_v2.py parses citations with parse_legacy() + fallback_citation_scan(); enables ground-truth xref rebuilds
- **Human review queue:** 201 ITE + 129 AAFP questions pending verification before commit; deferred flags: DEFERRED-BODY-SYSTEM-MERGED-UPDATE, DEFERRED-CENTROID-REBUILD, DEFERRED-HUMAN-REVIEW-BODY-SYSTEM

## Open Items (BATON 054)
- **DEFERRED-PROGRAM-TREND** — Multi-resident program-level trends; benchmark against 2024 ABFM national reference
- **DEFERRED-RESIDENT-FOLDER-MIGRATION** — Investigate resident_data/ folder state and M5 integration pathway
