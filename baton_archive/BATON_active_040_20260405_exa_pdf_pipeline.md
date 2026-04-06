# BATON 040 — EXA PDF Discovery + Mass Download Pipeline
**Date:** 2026-04-05
**Session:** Cowork desktop session — EXA/NCBI API setup + full PDF library expansion
**Status:** IN PROGRESS — housekeeping complete; git pending
**Replaces:** BATON_active_039_20260404_schema_docs_cleanup.md

---

## What Was Done This Session

### 1. Session Startup Skill — COMPLETE ✅
- Built `board-startup` skill installed at `C:\Users\mpsch\.claude\skills\board-startup\SKILL.md`
- Reads 4 orientation files in parallel on session start (_index.md, BATON, CLAUDE.md, README.json)
- Triggered by: "orient me", "startup", "where did we leave off", "what's in the BATON", etc.
- Added mandatory startup block to Cowork project instructions

### 2. API Keys Set in System Environment — COMPLETE ✅
All four keys now live in Windows user-level env vars (persist across sessions, no `$env:` injection needed):
| Variable | Purpose |
|----------|---------|
| `EXA_API_KEY` | EXA semantic search API (ef5361f6...) |
| `NCBI_API_KEY` | PubMed / NCBI E-utilities (850bd537...) |
| `AAFP_USERNAME` | AAFP login email (scholl.michael.p@gmail.com) |
| `AAFP_PASSWORD` | AAFP login password |

Set with: `[System.Environment]::SetEnvironmentVariable("KEY", "value", "User")`

### 3. exa_pdf_finder.py — COMPLETE ✅
**Path:** `01_module.1_warehouse/scripts/maintain/exa_pdf_finder.py`
- Scans PDF folders on disk via codon regex to build on-disk ART-ID set
- Queries DB for all articles missing physical PDFs
- Calls EXA API (`type: "auto"`, `num_results: 5`) for each article
- Classifies results: `direct_pdf` / `pmc_fulltext` / `open_access` / `landing_page` / `not_found`
- Saves incrementally every 10 articles to `exa_pdf_queue.json` + `exa_pdf_queue.csv`
- Flags: `--tier`, `--source`, `--limit`, `--resume`, `--dry-run`

**Full library run results (1,572 articles without PDFs):**
| Classification | Count |
|----------------|-------|
| direct_pdf | 259 |
| open_access | 332 |
| pmc_fulltext | 109 |
| landing_page | 872 |
| not_found | 0 |
| **Actionable total** | **700 (44.5%)** |

**AFP (open_access) breakdown:** 199 AAFP articles — all freely accessible at .pdf URL (no login needed; articles ≥ 12 months old are open access; newest in queue = 2024)

**EXA API cost:** ~$7–8 total for 1,572 searches (type: "auto" + highlights compact)

### 4. exa_pdf_downloader.py — COMPLETE ✅
**Path:** `01_module.1_warehouse/scripts/maintain/exa_pdf_downloader.py`
- Reads `exa_pdf_queue.csv`, resolves download URL per strategy:
  - `direct` — fetch PDF URL directly
  - `aafp` — swap `.html` → `.pdf` on AAFP article pages
  - `pmc` — construct `pmc.ncbi.nlm.nih.gov/articles/PMC{id}/pdf/` URL
- Verifies Content-Type + `%PDF` magic bytes before saving
- Names output with codon format: `Author_Year#@#ART-ID@#@.pdf`
- Saves to `citation_files/ITE/{tier}/`
- AAFP session cookie hook available for gated content (env: `AAFP_SESSION_COOKIE`)
- Flags: `--classification`, `--tier`, `--limit`, `--resume`, `--dry-run`

**Full run results (558 articles = 566 actionable - 8 already on disk):**
| Strategy | Downloaded | Failed | Rate |
|----------|-----------|--------|------|
| direct (259) | 215 | 44 | 83% |
| aafp (198) | 190 | 8 | 96% |
| pmc (109) | 0 | 109 | 0% — blocked by 403 |

PMC failure mode: NCBI's `/pdf/` endpoint actively blocks automated Python requests (403 + remote disconnect). EuroPMC fallback also blocked.

### 5. pmc_oa_downloader.py — COMPLETE ✅
**Path:** `01_module.1_warehouse/scripts/maintain/pmc_oa_downloader.py`
- Uses NCBI OA API (`oa.fcgi?id=PMC{id}&api_key={key}`) to get authenticated download URLs
- Handles three OA response types:
  - `found` → direct PDF URL (convert ftp:// → https://)
  - `tgz_only` → download tarball, extract PDF from inside using `tarfile` + `io.BytesIO`
  - `not_oa` → article is in PMC but not in OA subset (skip)
- Rate: 0.5s between requests (API key = 10 req/sec allowed)
- Flags: `--dry-run`, `--limit`, `--all-pmc`

**Full run results (109 PMC articles → 95 after skipping already-downloaded):**
| Outcome | Count |
|---------|-------|
| ✓ downloaded (direct OA PDF) | 14 |
| ✓ downloaded (tgz extraction) | 33 |
| ✗ not_oa (paywalled in PMC) | 62 |
| Total new PDFs | **47** |

**tgz extraction:** 33/33 — every tgz package contained a PDF. Zero failures.

### 6. PDF Library Results
| Stage | On Disk |
|-------|---------|
| Session start | 413 |
| After EXA downloader | 821 |
| After PMC OA downloader | 868 |
| **Net gain this session** | **+455 PDFs** |

---

## DB State (unchanged this session — no DB writes)

| Table | Rows |
|-------|------|
| articles | 1,985 |
| questions (ITE) | 1,629 |
| aafp_questions | 1,221 |
| article_icd10 | 4,137 |
| question_icd10 | 5,284 |
| clinical_pathways | 4,020 |
| Next ART-ID | ART-1987 |

---

## Script Counts (updated)

| Location | Python | JS | Notes |
|----------|--------|----|-------|
| M1 build/ | 6 | 0 | unchanged |
| M1 maintain/ | **21** | 0 | +3 new: exa_pdf_finder.py, exa_pdf_downloader.py, pmc_oa_downloader.py |
| M2 scripts/ | 75 | 6 | unchanged |
| M3 scripts/ | 13 | 2 | unchanged |

---

## New Output Files (M1/maintain/ — not git-tracked, disposable)

| File | Contents |
|------|----------|
| `exa_pdf_queue.csv` | 1,572 rows — all articles, classified by EXA |
| `exa_pdf_queue.json` | Same, machine-readable with summary block |
| `exa_download_results.csv` | 558 rows — per-article download outcomes |
| `pmc_oa_results.csv` | 95 rows — PMC OA API + tgz extraction outcomes |
| `exa_run.log` | EXA finder run log |
| `exa_download.log` | Downloader run log |
| `pmc_oa.log` | PMC OA downloader run log |

---

## Deferred Flags

| Flag | Description | Priority | Change |
|------|-------------|----------|--------|
| **DEFERRED-A** | 37 manual PDFs (34 subscription + 3 Cochrane) — now partially addressed; landing_page batch covers many of these; Unpaywall next pass | HIGH | UPDATED |
| **NEW: DEFERRED-G** | **Unpaywall scan** — run 872 landing_page articles + 62 not_oa PMC through Unpaywall API to find hidden open-access versions; first task next round | HIGH | NEW |
| DEFERRED-B | `update_citation_trends.py` after backfill | MEDIUM | unchanged |
| DEFERRED-C | AAFP vs ITE trend comparison | MEDIUM | unchanged |
| DEFERRED-D | 229 citation gap articles (88 AFP batch-downloadable) | MEDIUM | unchanged |
| DEFERRED-E | Interactive vector dashboard | LOW | unchanged |
| DEFERRED-F | Intelligence 2.0 Layer 2 (`article_currency` via PubMed, 344 PMIDs cached) | MEDIUM | unchanged |

---

## Next Session — Start Here

1. **DEFERRED-G (first task):** Unpaywall scan — build `unpaywall_scanner.py` targeting the 872 `landing_page` entries in `exa_pdf_queue.csv` + 62 `not_oa` from `pmc_oa_results.csv`. Unpaywall API: `https://api.unpaywall.org/v2/{doi}?email={email}`. Need DOIs — check if articles table has DOI field or use EUtils to fetch from PMID. Yield estimate: 20–40% of landing_pages may have OA versions.
2. **DEFERRED-A:** Re-evaluate the 37 original manual PDFs against the new `exa_download_results.csv` — some may now be downloaded; remainder = true manual-only.
3. **DEFERRED-F:** Intelligence 2.0 Layer 2 — `article_currency` table via PubMed (344 PMIDs in `pubmed_pmid_cache`); NCBI API key now set.
4. **AAFP login:** If newer AFP articles (<12 months) are needed, implement the AAFP login POST in `exa_pdf_downloader.py` (username/password in env; endpoint TBD via Chrome inspection).

---

## Files Changed This Session

| File | Action |
|------|--------|
| `01_module.1_warehouse/scripts/maintain/exa_pdf_finder.py` | NEW |
| `01_module.1_warehouse/scripts/maintain/exa_pdf_downloader.py` | NEW |
| `01_module.1_warehouse/scripts/maintain/pmc_oa_downloader.py` | NEW |
| `01_module.1_warehouse/scripts/maintain/exa_pdf_queue.csv` | NEW (output, not git-tracked) |
| `01_module.1_warehouse/scripts/maintain/exa_download_results.csv` | NEW (output, not git-tracked) |
| `01_module.1_warehouse/scripts/maintain/pmc_oa_results.csv` | NEW (output, not git-tracked) |
| `C:\Users\mpsch\.claude\skills\board-startup\SKILL.md` | NEW (outside project root) |
| `BATON_active_039_...` | RETIRED → baton_archive/ |
| `CLAUDE.md` | MODIFIED — Active State, PDF count, M1 maintain count |
| `_index.md` | MODIFIED — M1 maintain count, PDF count, housekeeping log |
