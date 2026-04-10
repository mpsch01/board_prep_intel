# .auto-memory/MEMORY.md — Memory Index
Last updated: 2026-04-10 (BATON 052)

## Active Memory Files
- [project_overhaul_state.md](project_overhaul_state.md) — Module state, PDF counts, key numbers, deferred flags, Intelligence 2.0 layer status
- [project_current_db_state.md](project_current_db_state.md) — DB table row counts (1,985 articles, 1,629 ITE Qs), schema state, article_currency NEW
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

## Open Items (BATON 049)
- **DEFERRED-PRACTICE-Q-COVERAGE** — Practice question 0-question warnings detected for Foundations, Preventive, Cardiovascular, Respiratory, Sexual-Reproductive, Psychiatric, Behavioral body systems; indicates qid_art_xref tagging coverage gap in blueprint cells
