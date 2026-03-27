---
name: project_overhaul_state
description: Current PROJECT_OVERHAUL state: BATON 015, AAFP BRQ scraper built + imported, citation gap list built, M1 reorganized with aafp_brq/
type: project
---

**Project:** ABFM ITE Intelligence System (Family Medicine board exam knowledge base)
**Root (Windows):** `C:\Users\mpsch\Desktop\claude_knowledge\00_#PROJECT_OVERHAUL\`
**Active BATON:** `BATON_active_015_20260327_aafp_brq_scraper_built_citation_gap_complete.md`
**Git:** `main`, latest committed `10d8208`

---

## Current Phase: AAFP BRQ Scraped + Imported; Citation Gap List Built

BATON 015 session: Two major workstreams. (1) Citation gap list built from ITE Critique staging JSONs — 229 unique unmatched refs across 2024+2025, prioritized by cross-year overlap. (2) AAFP Board Review Questions scraper designed, debugged, and run: 1,221 Q across 135 quizzes scraped and imported to new `aafp_questions` table (separate from `questions`, Option B+C confirmed). Key discovery: AnswerExplanation only returned on correct-answer POST response. FUSE oplock conflict documented (VM polling staging file froze Windows write). Resume/salvage logic added to scraper. M1 reorganized with `aafp_brq/` as proper warehouse source.

---

## Module State

| Module | Location | Scripts | Status |
|--------|----------|---------|--------|
| M1 Warehouse | `01_module.1_warehouse/` | 9 build + 16 maintain + aafp_brq/scraper | Self-contained build sequence complete; aafp_brq/ added this session |
| M2 Processor | `02_module.2_processor/scripts/` | 45 Python + 6 JS + 1 config JSON + 4 Windows | +1 aafp_brq_import.py this session |
| M3 Analyst | `03_module.3_analyst/` | 4 Python + 1 JS + 2 JSON config | Unchanged |
| M4 Sandbox | `04_module.4_sandbox/` | _DELETE_THESE_FROM_WINDOWS.txt only | Cleanup checklist (originals pending Windows deletion) |
| DB | `00_database/db/ite_intelligence.db` | Source of truth | 1,936 articles, 1,629 ITE Q, 1,221 AAFP BRQ Q |

---

## Key Numbers (as of BATON 015, 2026-03-27)

- **DB articles:** 1,936 (next = ART-1938)
- **DB questions (ITE):** 1,629 (2018–2025, all years complete)
- **DB questions (AAFP BRQ):** 1,221 (new `aafp_questions` table)
- **PDFs:** 404 across 4 tiers (VC_fail 146 / local_lite 117 / VC_pass 94 / right_click 71)
- **qid_art_xref:** 2,470 rows — all 8 years complete (2018–2025)
- **question_ref_pairs:** 2,673 rows (49 below BATON 014 baseline — pre-existing gap, not session-caused)
- **M2 scripts:** 45 Python + 6 JS + 1 config JSON + 4 Windows (all paths dynamic)
- **M1 aafp_brq:** 1,221 records in staging/aafp_brq_staging.json (4MB)
- **VC gate:** `key_data_files/session_hy_inserts_v7.json` — 352 citations
- **Citation gap list:** `02_module.2_processor/outputs/citation_gap_list_2024_2025.txt` — 229 unmatched ITE Critique refs

---

## AAFP BRQ Match Rates (first pass)

| Status | Count | Pct |
|--------|-------|-----|
| matched (exact clean_ref) | 360 | 29.5% |
| fuzzy (author+year) | 264 | 21.6% |
| unmatched | 578 | 47.3% |
| no_ref | 19 | 1.6% |
| **Total article-linked** | **624** | **51.1%** |

578 unmatched = mostly AFP journal articles (format mismatch) + guidelines (GOLD, ACC/AHA, USPSTF). Second-pass matcher planned.

---

## Path Convention (locked)

| Module | Pattern | Resolves to |
|--------|---------|-------------|
| M2/scripts | `SCRIPT_DIR = Path(__file__).resolve().parent; PROJECT_ROOT = SCRIPT_DIR.parent.parent` | PROJECT_ROOT |
| M1/scripts/build, M1/scripts/maintain | same | PROJECT_ROOT |
| M3/scripts | `SCRIPT_DIR.parent.parent` | PROJECT_ROOT |

---

## AAFP Scraper Reference (locked)

- **Scraper location:** `01_module.1_warehouse/aafp_brq/scraper/aafp_brq_scraper.py`
- **Staging output:** `01_module.1_warehouse/aafp_brq/staging/aafp_brq_staging.json`
- **Windows-only** — VM proxy blocks outbound HTTPS
- **Cookie refresh required** before each run: re-export aafp_cookies.json from Chrome → aafp.org
- **DO NOT poll staging file from VM while scraper runs** — FUSE oplock conflict freezes Windows write
- **Formula:** `first_q = 49733 + (assessment_id - 13882) * 10`
- **Resume = automatic** — scraper detects and salvages existing output on restart

---

## Active Deferred Flags

| Flag | Description | Priority |
|------|-------------|----------|
| AAFP ref matching (second pass) | 578 unmatched; AFP format + guideline title keyword matcher | HIGH |
| `aafp_qid_art_xref` table | Parallel to qid_art_xref; one row per AAFP Q-article link | HIGH |
| AAFP-ITE lag analysis | After xref: shared article citations, timing delta, predictive watch list | HIGH |
| 229 citation gap articles | 88 AFP batch-downloadable from null_clean_ref_missing_articles_20260326.csv | HIGH |
| `extract_ite_critique_refs.py` | BATON 014 design, not yet built | HIGH |
| `update_citation_trends.py` | BATON 014 design, not yet built | HIGH |
| `article_citation_trend` table | BATON 014 design, not yet created | HIGH |
| 129 missing AAFP questions | ~13 incomplete quizzes from stall; fix resume to detect < 10 Q quizzes | MEDIUM |
| Cookie refresh | aafp_cookies.json has session cookies — re-export before future scrape | MEDIUM |
| 1 pre-codon VC_fail no_match | `acute-low-back-imaging...` PDF: ART-ID lookup → codon rename | MEDIUM |
| E2E module tests | M1 `build_crosswalk_index.py`, M3 `build_icd10_tags.py` | MEDIUM |
| Intelligence 2.0 Layer 2 | `article_currency` via PubMed MCP | MEDIUM |
| Right_click DOCX regeneration | 71 DOCXs regenerable via build_summary.js | LOW |
| Scholl PDFs | `scholl_2025_ENCRYPTED_22/23/24.pdf` — need password | LOW |

---

## Next Steps

1. **Windows:** Archive BATONs 013 + 014 → `baton_archive/`; delete sandbox originals per `_DELETE_THESE_FROM_WINDOWS.txt`
2. **AAFP ref matching second pass** — volume/page extraction + guideline title keyword → target 70-80%
3. **Build `aafp_qid_art_xref` table** — populate from aafp_questions.article_id + second-pass matches
4. **AAFP-ITE lag analysis** — after xref populated
5. **Build `article_citation_trend` table + `update_citation_trends.py` + `extract_ite_critique_refs.py`**
6. **88 AFP missing articles** batch download from null_clean_ref_missing_articles_20260326.csv
