# project_overhaul_state.md
Last updated: 2026-04-10 (BATON 053)

## Module State

| Module | Status | Key Info |
|--------|--------|----------|
| M1 Warehouse | Active | 973 ITE PDFs (4 tiers) + 15 AAFP PDFs; 6 build + 26 maintain scripts |
| M2 Processor | Active | 75 py + 6 js scripts; enrichment pipeline operational |
| M3 Analyst | Active | 15 py + 2 js + 1 json config; ICD-10, pathways, score analysis, article_currency (Layer 2), longitudinal delta |
| M4 Sandbox | Active | 1 py (nl_search_validation.py); experiments + agent prototypes |
| M5 Web Platform | Active | 3 py + 35 tsx + 5 sql; Next.js frontend, Supabase backend, Sanity CMS, Railway FastAPI |
| DB | Stable | 1,985 articles, 1,629 ITE Qs, 1,221 AAFP Qs |

## PDF Library State

### ITE (citation_files/ITE/)
| Tier | Count | Notes |
|------|-------|-------|
| VC_fail | 630 | Failed VC gate; awaiting enrichment |
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

## Deferred Flags

| Flag | Status | Description |
|------|--------|-------------|
| DEFERRED-YOY-ROBUSTNESS | ACTIVE | Year-over-year section 3b needs more robust implementation; month-by-month trend aggregation logic (BATON 050) |
| DEFERRED-A | ARCHIVED | 37 ITE manual PDFs — permanent ceiling (subscription-only) |
| DEFERRED-AAFP-PAYWALL | ACTIVE | 3 AAFP articles paywalled (PMC not_oa): ART-1959 Binic_2011, ART-1972 Byington_2012, ART-1967 Verbalis_2007 |
| DEFERRED-PRACTICE-Q-COVERAGE | ✅ CLOSED | Practice question 0-question warnings for some body systems (Foundations, Preventive, Cardiovascular, Respiratory, Sexual-Reproductive, Psychiatric, Behavioral) — qid_art_xref tagging coverage gap (BATON 050) |
| DEFERRED-F | ✅ CLOSED | Intelligence 2.0 Layer 2 complete — article_currency built (1,985 rows) |
| DEFERRED-H | CLOSED | Legacy non-codon PDFs confirmed duplicates |
| DEFERRED-I | LOW PRI | unpaywall_scanner --from-csv extension |
| DEFERRED-J | CLOSED | exa-research-search Phase 2 completed |
| DEFERRED-L2-REVIEW | LOW PRI | Optional human review of 169 updated + 106 check_needed article_currency rows (use title_signals cross-reference) |
| DEFERRED-PGY-BENCHMARKS | PARTIALLY SOLVED | ABFM embeds PGY mean + SD in score report PDF; ite_parser.py parse_score_report() extracts; awaiting multi-year archive for trend analysis |

## Intelligence 2.0 Status
- Layer 1 (ICD-10): Complete — 4,020 rows article_icd10; question_icd10 5,218 rows (cleaned -66 no_match)
- Layer 2 (PubMed currency): ✅ COMPLETE — article_currency 1,985 rows; status enum (current:1100, updated:169, check_needed:106, not_indexed:610); title_signals column (JSON array)
- Layer 3 (Clinical pathways): Complete — 3,971 rows (cleaned -49 no_match)
- Layer 4 (Trends): Partial — trend CSV files in readable_db_files/

## Plugins & New Capabilities (BATON 049)
- **ite-score-analyzer v1.0.0** — ITE score analysis plugin built in `skills_abilities/ite-score-analyzer-v2/`
  - Four skills: analyze-ite (core report parsing), cohort-compare, ite-lookup, study-plan
  - parse_score_report() added to ite_parser.py (longitudinal delta support, Stage 2.5 pipeline)
  - report_config.json analytics configuration created
- **session-housekeeping agent templates** – Agents for baton-writer, index-memory-writer, manifest-writer created in .claude/skills/session-housekeeping/agents/; facilitate repeatable BATON and memory updates
- **Bugs FIXED (BATON 049):**
  - ✅ BUG-047-01: ite_parser.py — exam_year now extracted from PDF text (not hardcoded 2025 fallback)
  - ✅ BUG-047-02: ite_analyzer_v3.py — added BODYSYSTEM_PDF_NORM alias dict + _normalize_body_system() function for body system name normalization (handles PDF capitalization vs blueprint inconsistencies)
  - ✅ BUG-047-03: ite_analyze_v2.py — imports _normalize_body_system, applies it to body_system_scaled dict, uses official score from score report when available
  - Test reports validated: Scholl_2022, Scholl_2023, Scholl_2024, Sarkar_2025, Hopkins_2025
- **BATON 050 improvements (2026-04-08):**
  - ite_analyzer_v3.py: removed recency bonus, removed ORDER BY exam_year DESC from 3 tier SQL queries, changed limits 20→60, added current_exam_year exclusion with int cast
  - ite_analyze_v2.py: added --skip-reading-list and --question-count CLI flags; SKIP_READING_LIST env var passed to Node
  - ite_report_builder_v2.js: two-table practice Q layout (single-dim + cross-dim), longitudinal year-over-year section 3b, SKIP_READING_LIST guard on Section 10
  - Git index corruption fixed (del .git\index + git read-tree HEAD via CMD)
  - Ran Pjetergjoka 2024+2025 analysis with 35 questions
  - New deferred flag: DEFERRED-YOY-ROBUSTNESS (year-over-year section robustness)
- **New deferred flag (BATON 049):**
  - DEFERRED-PRACTICE-Q-COVERAGE — Practice question 0-question warnings detected for Foundations/Preventive/Cardiovascular/Respiratory/Sexual-Reproductive/Psychiatric/Behavioral body systems; indicates qid_art_xref tagging coverage gap in some blueprint cells