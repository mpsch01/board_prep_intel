---
name: project_overhaul_state
description: Current PROJECT_OVERHAUL state: BATON 034, citation_crawler upgraded to PlaywrightCrawler (build 0.3.1), DEFERRED-A partial (12/49 OA PDFs done, 37 manual remain)
type: project
---

**Project:** ABFM ITE Intelligence System (Family Medicine board exam knowledge base)
**Root (Windows):** `C:\Users\mpsch\Desktop\claude_knowledge\00_#PROJECT_OVERHAUL\`
**Active BATON:** `BATON_active_034_20260403_playwright_upgrade_deferred_a_partial.md`
**Git:** `main`, latest committed `e26a748` → GIT-PENDING (playwright upgrade + download scripts)

---

## Current Phase: DEFERRED-A Manual PDF Assembly

**BATON 034 (2026-04-03):**
- **citation_crawler upgraded: CheerioCrawler → PlaywrightCrawler** — build 0.3.1 deployed. Key fix: `Actor.log` is undefined in Apify SDK v3 static context — must `import { log } from 'crawlee'`. Apify username corrected: `mpsch1` (not `mpsch01`).
- **Dockerfile added** — `apify/actor-node-playwright-chrome:20` base image required for Playwright; memory 2048 MB.
- **DEFERRED-A partial** — 12/49 AAFP acquisition PDFs now in VC_fail. 12 OA articles downloaded (2 via OA API, 10 via Claude in Chrome pipeline). 37 remain: 34 subscription + 3 Cochrane.
- **Key insight: PMC OA API vs PMC** — OA API only serves the strict PMC Open Access FTP Subset. Articles readable on PMC but outside this subset (Cochrane, deposited articles without OA license) need browser session. Even E-Fetch `rettype=pdf` has the same restriction.
- **download_pmc_actor_batch.py added** — new M1 maintain script (17 total). Documents the actor-discovered URLs; direct HTTP download failed (1817-byte redirect page requires browser session).
- **download_aafp_acquisitions.py enhanced** — added E-Fetch Strategy 2 fallback.

---

## Module State

| Module | Location | Scripts | Status |
|--------|----------|---------|--------|
| M1 Warehouse | `01_module.1_warehouse/` | 9 build + 17 maintain + aafp_brq/scraper | Stable |
| M2 Processor | `02_module.2_processor/scripts/` | 66 Python + 6 JS + 1 config JSON + 4 Windows | Stable |
| M3 Analyst | `03_module.3_analyst/scripts/` | 9 Python + 2 JS + 2 JSON config | Stable |
| DB | `00_database/db/ite_intelligence.db` | Source of truth | 1,985 articles, 1,629 ITE Q, 1,221 AAFP Q |
| Apify | `apify-actors/citation_crawler/` | 1 actor (PlaywrightCrawler) | DEPLOYED ✅ build 0.3.1 (`mpsch1~citation-crawler`, ID `rh50nQRP7BupbUF64`) |

---

## Key Numbers (as of BATON 034, 2026-04-03)

- **DB articles:** 1,985 (next: ART-1987)
- **DB questions (ITE):** 1,629 (2018–2025); blueprint 100%; subcategory + topic_label DROPPED
- **DB questions (AAFP BRQ):** 1,221; blueprint 100%; flattened; aafp_explanations table DROPPED
- **article_icd10:** 4,137 rows
- **question_icd10:** 5,284 rows (92.8% ITE coverage)
- **aafp_question_icd10:** 4,753 rows
- **icd10_vec:** 2,219 rows (OpenAI text-embedding-3-small 1536d)
- **article_icd10_vec:** 1,674 rows (rebuilt 2026-04-01)
- **question_icd10_vec:** 2,733 rows (rebuilt 2026-04-01)
- **question_vec:** 1,629 rows — 100% coverage ✅
- **aafp_question_vec:** 1,221 rows — 100% coverage ✅
- **clinical_pathways:** 4,020 rows (rebuilt 2026-03-31)
- **pubmed_pmid_cache:** 344 rows (Layer 2 seed)
- **PDFs:** ~414 across 4 tiers (VC_fail ~156; 37 AAFP articles still manual pending)

---

## Active Deferred Flags

| Flag | Description | Priority |
|------|-------------|----------|
| DEFERRED-A | 37 manual PDFs remaining: 34 subscription + 3 Cochrane → download → codon rename → VC_fail | **HIGH** |
| DEFERRED-B | `update_citation_trends.py` — run after backfill_new_article_metadata | MEDIUM |
| DEFERRED-C | AAFP vs ITE trend comparison | MEDIUM |
| DEFERRED-D | 229 citation gap articles (88 AFP batch-downloadable) | MEDIUM |
| DEFERRED-E | Interactive vector dashboard | LOW |
| DEFERRED-F | Intelligence 2.0 Layer 2 (`article_currency` via PubMed, 344 PMIDs cached) | MEDIUM |

**Closed this session:** None (DEFERRED-A 12/49 partial)

---

## Next Steps (priority order)

1. **DEFERRED-A manual PDFs** — 37 remaining; institutional/Cochrane access → codon rename → VC_fail
2. **`backfill_new_article_metadata.py --art-id-min 1938`** — run once PDFs assembled
3. **DEFERRED-B** — `update_citation_trends.py` after backfill
4. **DEFERRED-F** — Intelligence 2.0 Layer 2: `article_currency` via PubMed
5. **DEFERRED-D** — 229 citation gap articles
