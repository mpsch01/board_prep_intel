# project_overhaul_state.md
Last updated: 2026-04-06 (BATON 045)

## Module State

| Module | Status | Key Info |
|--------|--------|----------|
| M1 Warehouse | Active | 966 ITE PDFs (4 tiers) + 15 AAFP PDFs; 6 build + 25 maintain scripts |
| M2 Processor | Active | 75 py + 6 js scripts; enrichment pipeline operational |
| M3 Analyst | Active | 13 py + 2 js; ICD-10, pathways, score analysis |
| M4 Sandbox | Active | Experiments + agent prototypes |
| DB | Stable | 1,985 articles, 1,629 ITE Qs, 1,221 AAFP Qs |

## PDF Library State

### ITE (citation_files/ITE/)
| Tier | Count | Notes |
|------|-------|-------|
| VC_fail | 623 | Failed VC gate; awaiting enrichment |
| VC_pass | 168 | Passed VC gate; awaiting enrichment |
| local_lite | 117 | Enriched; not VC-cited |
| right_click | 58 | Enriched + VC-cited (top tier) |
| _dupe_archive | 14 | Legacy single-author duplicates; not pipeline |
| **TOTAL active** | **966** | Recovered via EXA+PMC+Unpaywall after fix_ghost.py incident |

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
| DEFERRED-F | ACTIVE | Intelligence 2.0 Layer 2 — article_currency via PubMed |
| DEFERRED-H | CLOSED | Legacy non-codon PDFs confirmed duplicates |
| DEFERRED-I | LOW PRI | unpaywall_scanner --from-csv extension |
| DEFERRED-J | CLOSED | exa-research-search Phase 2 completed |

## Intelligence 2.0 Status
- Layer 1 (ICD-10): Complete — 4,020 rows article_icd10; question_icd10 5,218 rows (cleaned -66 no_match)
- Layer 2 (PubMed currency): DEFERRED-F — 344 PMIDs seeded; build article_currency table next
- Layer 3 (Clinical pathways): Complete — 3,971 rows (cleaned -49 no_match)
- Layer 4 (Trends): Partial — trend CSV files in readable_db_files/

## Key Artifacts
- VC gate: key_data_files/session_hy_inserts_v7.json (352 citations)
- Codon format: Author_Year#@#ART-XXXX@#@.pdf
- DB: 00_database/db/ite_intelligence.db (source of truth, never disposable)
