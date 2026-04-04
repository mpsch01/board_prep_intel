# BATON 034 — PlaywrightCrawler Upgrade + DEFERRED-A Partial (12/49 OA PDFs in VC_fail)
**Date:** 2026-04-03
**Session:** Upgraded citation_crawler actor to PlaywrightCrawler; resolved 12 OA PDF downloads for AAFP acquisition batch; 37 manual PDFs remain
**Status:** GIT-PENDING (commit block provided — needs manual run due to `#` in path) | DEFERRED-A PARTIAL ✅
**Replaces:** BATON_active_033_20260403_citation_crawler_scaffold.md

---

## What Was Done This Session

### 1. citation_crawler Actor — CheerioCrawler → PlaywrightCrawler Upgrade

**Problem:** After actor build 0.1.1 was deployed (BATON 033), the actor was tested against 10 PMC article URLs. It returned 0 results — because PMC viewer pages are React-rendered and the `CheerioCrawler` only parses static HTML (pre-hydration shell had no PDF links).

**Fix:** Upgraded to `PlaywrightCrawler` (Chromium-based, full JS rendering).

**Key technical facts learned:**
- `Actor.log` is an **instance property** in Apify SDK v3 — calling `Actor.log.info()` on the class directly is `undefined` → TypeError. Must `import { log } from 'crawlee'` and use `log.info/error` instead.
- Apify username is `mpsch1` (not `mpsch01`) → use `mpsch1/citation-crawler` or actor ID `rh50nQRP7BupbUF64`
- `async: true` required for MCP tool call to avoid 60s timeout; fetch results separately with `get-actor-output`

**Files modified:**
| File | Change |
|------|--------|
| `apify-actors/citation_crawler/src/main.js` | Major rewrite: CheerioCrawler → PlaywrightCrawler; `cheerio` added for HTML parsing in handler; all `Actor.log.*` → `log.*` from crawlee |
| `apify-actors/citation_crawler/.actor/Dockerfile` | **NEW** — Playwright requires the `apify/actor-node-playwright-chrome:20` base image |
| `apify-actors/citation_crawler/package.json` | Version `0.1.0` → `0.2.0`; added `"playwright": "^1.40.0"` and `"cheerio": "^1.0.0"` |
| `apify-actors/citation_crawler/.actor/actor.json` | Version `0.1` → `0.3`; memory `1024` → `2048` MB (Playwright needs Chromium) |

**Build progression:** 0.1.1 (CheerioCrawler, working but JS-blind) → 0.2.0 (PlaywrightCrawler, broke on Actor.log) → 0.3.0 (fixed log import) → **0.3.1 (deployed, 10/10 PMC articles returned with PDF URLs in 42s)** ✅

---

### 2. DEFERRED-A: OA PDF Download Attempts + Resolution

**Scope:** 49 new AAFP acquisition articles (ART-1938–ART-1986) need PDFs in VC_fail.

**download_aafp_acquisitions.py run results:**
- 46 articles with PMID; NCBI ID converter found PMC IDs for 12
- OA API (`oa.fcgi`) returned PDF URLs for only 2 of the 12 → 10 OA failures

**Root cause of OA failures:** PMC OA API only serves articles in the strict PMC Open Access FTP Subset. Articles readable on PMC but outside this subset (e.g., free-to-read Cochrane reviews, PMC-deposited articles without OA license) return nothing from the OA API.

**Fallback attempt 1 — E-Fetch `rettype=pdf`:** Same OA restriction as OA API. Added to `download_aafp_acquisitions.py` as Strategy 2, but returned failures for all 10.

**Fallback attempt 2 — `download_pmc_actor_batch.py`:** Hardcoded the 9 actor-discovered PDF URLs (from build 0.3.1 run). Direct `requests.get()` returned HTTP 200 but only 1817 bytes — a redirect page. PMC PDF endpoints require a valid browser session, not just an HTTP GET.

**Resolution — Claude in Chrome + Desktop Commander pipeline:**
- Claude in Chrome navigated to each PMC article page and downloaded PDFs via the browser
- Desktop Commander (with Downloads + VC_fail paths in `allowedDirectories`) moved files to VC_fail
- **Complication:** Chrome Acrobat extension (`efaidnbmnnnibpcajpcglclefindmkaj`) hijacks PDF URLs into extension context — required user to disable before pipeline could work
- All 12 OA articles (2 via OA API + 10 via browser) are now in VC_fail ✅

**New M1 maintain script created:** `download_pmc_actor_batch.py` — one-off batch downloader with 9 hardcoded actor-discovered PDF URLs. Documents what was attempted even though direct HTTP download failed. Useful as template for future actor-assisted batch runs.

---

### 3. download_aafp_acquisitions.py — Enhanced Fallback

Script now has 2-strategy fallback:
- **Strategy 1:** PMC OA API → FTP/HTTPS URL (strict OA subset)
- **Strategy 2:** NCBI E-Fetch `rettype=pdf` endpoint (broader PMC coverage, same OA restriction in practice)

Both strategies are clean — if both fail, the article goes to the manual list. No change to overall logic flow.

---

## DEFERRED-A Status

| Category | Count | Status |
|----------|-------|--------|
| OA (downloaded to VC_fail) | 12 | ✅ Done |
| Subscription articles (no PMC ID) | 34 | Manual — institutional access required |
| Cochrane (no PMID) | 3 | Manual — Cochrane Library direct download |
| **Total** | **49** | **12/49 complete; 37 manual remain** |

**Manual download procedure:** Download from institutional/Cochrane access → rename to codon format (`Author_Year#@#ART-XXXX@#@.pdf`) → place in `01_module.1_warehouse/VC_fail/`

Once sufficient PDFs assembled (or when ready to process what's available):
```
python 01_module.1_warehouse/scripts/maintain/backfill_new_article_metadata.py --art-id-min 1938
```

---

## DB State (unchanged this session)

| Table | Rows | Notes |
|-------|------|-------|
| articles | 1,985 | ART-0001 → ART-1986; next = ART-1987 |
| questions (ITE) | 1,629 | blueprint 100% |
| questions (AAFP) | 1,221 | blueprint 100% |
| qid_art_xref | 2,470 | |
| aafp_qid_art_xref | 864 | |
| article_icd10 | 4,137 | |
| question_icd10 | 5,284 | |
| aafp_question_icd10 | 4,753 | |
| clinical_pathways | 4,020 | |
| article_icd10_vec | 1,674 | |
| question_icd10_vec | 2,733 | |
| pubmed_pmid_cache | 344 | Layer 2 seed |
| PDFs | ~414 | VC_fail now ~156 (+10 net new); total +10 |
| Next ART-ID | ART-1987 | |
| Git | main, pending commit | Citation crawler upgrade + download scripts |

---

## Deferred Flags

| Flag | Description | Priority |
|------|-------------|----------|
| DEFERRED-A | 37 manual PDFs remaining: 34 subscription + 3 Cochrane → VC_fail | **High** |
| DEFERRED-B | `update_citation_trends.py` — run after DEFERRED-A complete | Medium |
| DEFERRED-C | AAFP vs ITE trend comparison | Medium |
| DEFERRED-D | 229 citation gap articles (88 AFP batch-downloadable) | Medium |
| DEFERRED-E | Interactive vector dashboard | Low |
| DEFERRED-F | Intelligence 2.0 Layer 2 — `article_currency` via PubMed (344 PMIDs cached) | Medium |

**Closed this session:** None (DEFERRED-A partial — 12/49)

---

## Next Steps (priority order)

1. **DEFERRED-A manual PDFs** — 37 remaining; download from institutional/Cochrane access → codon rename → VC_fail
2. **`backfill_new_article_metadata.py --art-id-min 1938`** — run once all (or a workable batch of) PDFs are in VC_fail
3. **DEFERRED-B** — `update_citation_trends.py` after backfill is run
4. **DEFERRED-F** — Intelligence 2.0 Layer 2: `article_currency` via PubMed (344 PMIDs in `pubmed_pmid_cache`)
5. **DEFERRED-D** — 229 citation gap articles (88 AFP batch-downloadable)

---

## Files Changed This Session

| File | Action |
|------|--------|
| `apify-actors/citation_crawler/src/main.js` | MODIFIED — CheerioCrawler → PlaywrightCrawler; cheerio parse; log import fix |
| `apify-actors/citation_crawler/.actor/Dockerfile` | NEW — Playwright base image |
| `apify-actors/citation_crawler/package.json` | MODIFIED — version 0.2.0; added playwright + cheerio |
| `apify-actors/citation_crawler/.actor/actor.json` | MODIFIED — version 0.3; memory 2048 MB |
| `01_module.1_warehouse/scripts/maintain/download_aafp_acquisitions.py` | MODIFIED — added E-Fetch Strategy 2 fallback |
| `01_module.1_warehouse/scripts/maintain/download_pmc_actor_batch.py` | NEW — one-off batch downloader (9 actor-discovered PMC PDFs) |
| `baton_archive/BATON_active_033_*.md` | ARCHIVED (this session) |
| `BATON_active_034_*.md` | This file |
