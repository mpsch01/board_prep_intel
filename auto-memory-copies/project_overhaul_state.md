# project_overhaul_state.md
Last updated: 2026-04-08 (BATON 048)

## Module State

| Module | Status | Key Info |
|--------|--------|----------|
| M1 Warehouse | Active | 966 ITE PDFs (4 tiers) + 15 AAFP PDFs; 6 build + 26 maintain scripts |
| M2 Processor | Active | 75 py + 6 js scripts; enrichment pipeline operational |
| M3 Analyst | Active | 14 py + 2 js + 1 json config; ICD-10, pathways, score analysis, article_currency (Layer 2), longitudinal delta |
| M4 Sandbox | Active | Experiments + agent prototypes |
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
| **TOTAL active** | **981** | Recovered via EXA+PMC+Unpaywall; +7 PDFs added (2026-04-08) |

### AAFP (citation_files/AAFP/)
| Count | Status |
|-------|--------|
| 15 | Recovered this session (was 0 after fix_ghost.py) |

AAFP ceiling: 3 paywalled (ART-1959, ART-1972, ART-1967)

## Deferred Flags

| Flag | Status | Description |
|------|--------|-------------|
| DEFERRED-A | ARCHIVED | 37 ITE manual PDFs — permanent ceiling (subscription-only) |
| DEFERRED-AAFP-PAYWALL | ACTIVE | 3 AAFP articles paywalled (PMC not_oa): ART-1959 Binic_2011, ART-1972 Byington_2012, ART-1967 Verbalis_2007 |
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

## Plugins & New Capabilities (BATON 048)
- **ite-score-analyzer v1.0.0** — ITE score analysis plugin built in `skills_abilities/ite-score-analyzer-v2/`
  - Four skills: analyze-ite (core report parsing), cohort-compare, ite-lookup, study-plan
  - parse_score_report() added to ite_parser.py (longitudinal delta support, Stage 2.5 pipeline)
  - report_config.json analytics configuration created
- **session-housekeeping agent templates** – Agents for baton-writer, index-memory-writer, manifest-writer created in .claude/skills/session-housekeeping/agents/; facilitate repeatable BATON and memory updates
- **Open bugs (tracked for v1.1 release):**
  - Exam year 2025 fallback handling in v3 analyzer (edge case when 2025 year label not found)
  - 2024 body system name normalization needed (capitalization inconsistency vs blueprint