# BATON 046: Intelligence 2.0 Layer 2 — article_currency Complete
**Date:** 2026-04-07  
**Git Hash:** 35f025d | **Branch:** main  
**Status:** Layer 2 (PubMed currency tracking) complete and integrated

---

## Session Summary

This session completed **Intelligence 2.0 Layer 2**, implementing PubMed-based article currency tracking for all 1,985 articles in the knowledge base. The deliverable is the new `article_currency` table with two-phase PMID resolution and automated currency classification.

### Root Cleanup (start of session)
- Deleted `README.json` (consolidated into `README.md`)
- Deleted `git_housekeeping.bat`, `git_out.txt` (stale maintenance files)
- Deleted `ABFM_ITE_Module_Overview.docx`, `ABFM_ITE_System_Summary_MedEd.docx` (out of scope)
- Updated `README.md`: absorbed README.json fields, bumped BATON pointer 040→045, corrected PDF tier counts and module script inventory

### Intelligence 2.0 Layer 2: article_currency — COMPLETE

Built `build_article_currency.py` (new M3 script). Tracks currency status for all 1,985 articles via PubMed NCBI API, identifying whether each article is current, has been superseded, or requires manual review.

#### Two-Phase Architecture

**Phase A: PMID Resolution**
- **Strategy 1:** Collective Name query (org abbreviations: AAP, ACOG, ACC, ADA, AHA, etc.)
- **Strategy 2:** Personal author + volume + page
- **Strategy 3:** Page-drop fallback (author + volume only)
- **Result Phase A:**
  - 1,079 resolved (PMID obtained, pending Phase B)
  - 274 check_needed (ambiguous; 2+ candidate PMIDs returned)
  - 632 not_indexed (no PubMed match; org authors, textbooks, pre-PubMed articles)
  - Retry pass (`--retry-not-indexed` flag): recovered ~22 additional articles

**Phase B: Currency Check**
- For each resolved PMID: fetch article metadata + run esearch for newer publications by same author(s)
- Automated title-relevance filter: newer pub must share ≥1 content-word with original title
- Three iterations of false-positive reduction applied:
  1. Title-relevance filter (efetch_batch for API efficiency)
  2. Clinical signals isolation: added `_CLINICAL_SIGNALS` set (words like "diagnosis", "treatment", "management", etc.) — these words are semantically generic but carry blueprint signal
  3. "Block and track" architecture: clinical signal words intercepted before overlap check, stored in `title_signals` JSON column for future blueprint cross-reference

#### Final article_currency State

| Currency Status | Count | % of Total | Meaning |
|---|---|---|---|
| **current** | 1,100 | 55.4% | No relevant newer publication found |
| **not_indexed** | 610 | 30.7% | No PMID resolved (org authors, textbooks, pre-PubMed) |
| **updated** | 169 | 8.5% | Single relevant newer publication found |
| **check_needed** | 106 | 5.3% | 2+ relevant newer publications found; requires human review |

#### New Table Schema

```sql
CREATE TABLE article_currency (
    article_id TEXT PRIMARY KEY,
    pubmed_id TEXT,
    pub_date TEXT,
    pub_title TEXT,
    last_checked TEXT,
    newer_version_pmid TEXT,
    newer_version_date TEXT,
    newer_version_title TEXT,
    currency_status TEXT,
    title_signals TEXT  -- JSON array: clinical category words for future blueprint cross-reference
);
```

#### Key Architectural Decisions

- **`efetch_batch()`:** Fetches up to 5 newer PMIDs in one API call (vs. 5 sequential) — **80% API reduction**
- **`title_signals` column:** "Block and track" pattern — clinical meta-words stripped from overlap check but preserved in labeled container for future blueprint cross-reference
- **`backfill_title_signals()`:** Idempotent migration function; processes existing rows (pure text extraction, no API calls)
- **`_ORG_ABBREV_MAP`:** Maps org codes (AAP, ACOG, ACC, ADA, AHA, etc.) → PubMed [Collective Name] for org-authored articles
- **`--retry-not-indexed` flag:** Re-processes not_indexed rows via UPDATE instead of INSERT
- **`--recheck` flag:** Phase B re-processes 'updated' rows after logic changes

---

## Current DB State

| Table | Row Count | Notes |
|---|---|---|
| articles | 1,985 | 2018–2025 ABFM ITE + AAFP acquisition (ART-1938–ART-1986) |
| questions (ITE) | 1,629 | Blueprint 100% filled; subcategory + topic_label dropped |
| aafp_questions | 1,221 | Blueprint 100% filled; flattened schema |
| aafp_qid_art_xref | 864 | 643 unique questions linked (52.7%) |
| qid_art_xref | 2,470 | All 8 years (2018–2025) |
| article_icd10 | 4,020 | Rebuilt with vec (2026-04-05) |
| question_icd10 | 5,218 | 1,512/1,629 ITE (92.8%); 66 no_match deleted |
| aafp_question_icd10 | 4,753 | Relevance normalized, related cap applied |
| clinical_pathways | 3,971 | Rebuilt 2026-03-31; blueprint-based; 49 no_match deleted |
| pubmed_pmid_cache | 344 | Layer 2 seed (citation_id → PMID) |
| icd10_vec | 2,219 | OpenAI text-embedding-3-small (1536d) |
| article_icd10_vec | 1,757 | Rebuilt 2026-04-05 |
| question_icd10_vec | 2,747 | Rebuilt 2026-04-05 |
| **article_currency** | **1,985** | **NEW — Layer 2 complete; tracks PubMed currency** |

---

## PDF Library

| Tier | Count | Source | Notes |
|---|---|---|---|
| VC_fail | 623 | Failed VC gate | Awaiting full enrichment pipeline |
| VC_pass | 168 | Passed VC gate | Awaiting full enrichment pipeline |
| local_lite | 117 | Fully enriched, VC_fail | DOCX exists; M2 complete |
| right_click | 58 | Fully enriched, VC_pass | DOCX exists; M2 complete |
| AAFP | 15 | AAFP acquisition | Sourced 2026-04-05 |
| ITE Exams | 16 | All 8 years | MC + critique (2018–2025) |
| **TOTAL** | **997** | — | Recovered via exa_pdf_downloader + pmc_oa_downloader + recover_unpaywall; 14 dupes archived |

---

## Script Inventory

### M1 Warehouse (`01_module.1_warehouse/`)
- **build/:** 6 Python scripts
- **maintain/:** 25 Python scripts
- **Root:** aafp_brq_scraper.py

### M2 Processor (`02_module.2_processor/`)
- **Core:** 75 Python + 6 JavaScript
- **Subdirectories:** core/ (4py) | engines/ (7py) | utils/ (6py) | prompts/ (templates) | source/ (transcripts, blueprint XLSX, outline DOCX) | outputs/ (staging JSONs, citation gap)

### M3 Analyst (`03_module.3_analyst/`)
- **Total:** 14 Python + 2 JavaScript (**+1 py this session for `build_article_currency.py`**)
- **New:** `build_article_currency.py` — Intelligence 2.0 Layer 2 implementation

### Supporting
- **Apify Actor:** `apify-actors/citation_crawler/` — deployed ✅ (ID: `rh50nQRP7BupbUF64`, build 0.3.1, PlaywrightCrawler)

---

## Deferred Flags

| Flag | Description | Status | Notes |
|---|---|---|---|
| DEFERRED-AAFP-PAYWALL | 3 articles (ART-1959, ART-1972, ART-1967) via interlibrary loan | OPEN | Requires institutional access |
| DEFERRED-F | Intelligence 2.0 Layer 2: article_currency via PubMed | **✅ CLOSED** | **COMPLETE 2026-04-07** |
| DEFERRED-L2-REVIEW | Optional: human review pass on 169 updated + 106 check_needed articles | NEW | Low priority; spot-check if needed |
| DEFERRED-PGY-BENCHMARKS | Add PGY-level expected performance benchmarks to ite-domain skill | OPEN | Mikey to provide data; add to `skills/ite-domain/references/pgy_benchmarks.md` — expected overall % ranges and weak-area patterns by PGY level (1–4); makes score summaries far more clinically meaningful |

---

## Next Steps

1. **ite-score-analyzer plugin v1.0.0** — Built this session; install via `skills_abilities/ite-score-analyzer-v2/ite-score-analyzer.plugin`
2. **DEFERRED-PGY-BENCHMARKS** — Add PGY-level performance benchmark data to ite-domain skill once Mikey provides (expected % ranges by PGY level 1–4)
3. **exa-research-search Phase 2** — Resume normal roadmap: literature search expansion + clinical pathways pipeline
4. **Intelligence 2.0 Layer 3 planning** — Clinical pathways enrichment (Layer 3 = `clinical_pathways` with `pathway_role`)
5. **DEFERRED-AAFP-PAYWALL** — Pursue 3 paywalled articles via institutional/interlibrary loan
6. **Optional: article_currency review** — Spot-check 169 `updated` + 106 `check_needed` rows; build query report if needed
7. **When resident-facing report needed** — Re-enable full question rendering in `ite_report_builder_v2.js` (currently compact reference table mode)
8. **title_signals forward use** — When blueprint enrichment resumes, query `article_currency.title_signals` to cross-reference article-level category signals vs. existing blueprint assignments

---

## Locked Rules (no changes from BATON 045)

1. **Fix the data, not the code.** If a script gets complex to handle messy data → clean upstream.
2. **VC gate = sole criterion** for right_click tier. DB membership alone insufficient.
3. **Source data protected.** DB + PDFs + VC gate survive everything. Derived files (JSON, DOCX, CSV) disposable.
4. **Dynamic paths only.** Python: `SCRIPT_DIR = Path(__file__).resolve().parent; PROJECT_ROOT = SCRIPT_DIR.parent.parent`. JS: `path.resolve(__dirname, "../../")`.
5. **Build in whatever language fits; flag if clutter accumulates.** JS rule relaxed (was "no de novo JS").
6. **BATON first.** Read active BATON before any work session.
7. **QC after every integration.** Schema-level column-by-column comparison, old cohort vs. new.
8. **Git via Desktop Commander.** Python subprocess helper (`claude_knowledge/git_runner.py`). NTFS file deletions still require Windows Explorer/terminal.
9. **shutil.rmtree is BANNED.** Use explicit file-by-file deletion or PowerShell Remove-Item. It bypasses Recycle Bin and is irreversible.
10. **Strategy 0 in every enricher.** Codon parse always first matching strategy.
11. **Schemas before scripts.** SQL CREATE TABLE defined before build scripts written.

---

## Git Status

| Item | Value |
|---|---|
| Hash | 35f025d |
| Branch | main |
| Status | Clean; all work committed |
| GitHub Remote | `https://github.com/mpsch01/board_prep_intel` (private) |
| .gitignore | Code + docs on GitHub; binaries excluded (`*.db`, `*.pdf`, `extracted_json/`, `resident_data/`) |

---

## Hand-Off Notes for Next Session

- **Layer 2 is closed.** The `article_currency` table is complete, integrated, and should not require further work unless DEFERRED-L2-REVIEW is prioritized.
- **title_signals preserved.** The `title_signals` JSON column contains clinical meta-words for future blueprint cross-reference; this is foundational work for Layer 3 (pathway enrichment).
- **PMID seed stable.** The `pubmed_pmid_cache` table (344 rows) remains the source of truth for citation_id → PMID mapping; do not regenerate unless ICD-10 schema changes.
- **No new dependencies.** build_article_currency.py uses only existing NCBI API key and standard libraries; no new package requirements.
- **Next major work:** exa-research-search Phase 2 or clinical_pathways enrichment (Layer 3).

---

**Prepared by:** Claude (Agent)  
**For:** Mikey (Michael Scholl)  
**Session:** 2026-04-07
