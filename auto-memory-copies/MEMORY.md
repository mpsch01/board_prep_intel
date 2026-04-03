# Auto-Memory Index

## User
- [user_profile.md](user_profile.md) — Mikey: family medicine physician, self-taught data architect, builds clinical knowledge systems

## Project
- [project_overhaul_state.md](project_overhaul_state.md) — Current PROJECT_OVERHAUL state: BATON 030, ite_analyzer_v3 built + smoke tested, QUESTION-DIST-001 flagged, faculty presentation pending
- [project_current_db_state.md](project_current_db_state.md) — DB state BATON 030: 1,985 articles, 1,629 ITE Q, 1,221 AAFP Q; ICD-10 vecs rebuilt; clinical_pathways 4,020 rows; M3 has ite_analyzer_v3
- [project_new_architecture.md](project_new_architecture.md) — 4-module rebuild design: Warehouse, Processor, Analyst, Sandbox. AAFP course = external priority filter.
- [project_architecture_tiered_system.md](project_architecture_tiered_system.md) — Two-tier pipeline ($right_click$ vs local_lite), VC gate, codon system, 5 locked rebuild principles

## Rebuild Rules
- [rebuild_structuring_guidelines.md](rebuild_structuring_guidelines.md) — 5 locked rebuild principles: git as version layer, BATON as intent layer, schemas upfront, OUTPUT_SCHEMA for agents, cryptographic hash ART-IDs

## Reference
- [reference_skills_abilities_inventory.md](reference_skills_abilities_inventory.md) — skills_abilities/ folder: ITE data context skill (stale — needs AAFP update), PDF sourcer agent, 17 SDK files, API primer, session-available tools map
- [reference_vc_gate.md](reference_vc_gate.md) — VC Gate: session_hy_inserts_v7.json, 352 citations, sole right_click criterion, QID format mismatch warning
- [reference_baton_protocol.md](reference_baton_protocol.md) — BATON handoff lifecycle (archive → sync → write new), structure, quality standards, naming
- [reference_sdk_docs.md](reference_sdk_docs.md) — Claude Agent SDK docs locations; pdf_sourcer_agent.py built and validated
- [reference_dashboard_style.md](reference_dashboard_style.md) — Data lifecycle dashboard pattern: dark theme, stage-colored nodes, field inventory tables with origin tags, Chart.js charts, real DB stats. Replicate for all module pipelines.
- [reference_word_doc_defaults.md](reference_word_doc_defaults.md) — word_doc_defaults.py: St. Luke's color scheme (navy/gold/blue), Aptos font, US Letter, helper functions. Import in ALL python-docx scripts.

## Feedback
- [feedback_housekeeping.md](feedback_housekeeping.md) — Housekeeping sweeps must always update CLAUDE.md + MEMORY.md (not optional)

## Deep Memory
- [memory/glossary.md](memory/glossary.md) — Full decoder ring: all acronyms, pipeline terms, tier names, script nicknames, deferred flags, TEMP protocol
- [memory/context/working_with_mikey.md](memory/context/working_with_mikey.md) — Behavioral guide: how Mikey thinks, communication patterns, what NOT to do, his phrases decoded
- [memory/projects/ite_intelligence_system.md](memory/projects/ite_intelligence_system.md) — Full project context: DB tables, PDF tiers, codon system, Intelligence 2.0 layers, current state
