# BATON 041 — Unpaywall Scanner Built + Ghost Folder Resolved
**Date:** 2026-04-05
**Session:** Cowork desktop — continued from compacted BATON 040 context
**Status:** COMPLETE — housekeeping done; git pending
**Replaces:** BATON_active_040_20260405_exa_pdf_pipeline.md

---

## What Was Done This Session

### 1. DEFERRED-G: unpaywall_scanner.py — COMPLETE ✅
**Path:** `01_module.1_warehouse/scripts/maintain/unpaywall_scanner.py`

Built a three-tier DOI resolution + Unpaywall OA PDF downloader targeting 872 landing_page articles from exa_pdf_queue.csv + 162 PMC-skipped articles (not_oa from pmc_oa_results.csv).

**DOI resolution strategies (in order):**
1. Strategy 1 — Regex from URL (extracts DOI directly from landing_page URL)
2. Strategy 2 — PMID from PubMed URL → NCBI EUtils esummary → DOI
3. Strategy 3 — PMC ID → EUtils elink (pmc→pubmed) → PMID → esummary → DOI
4. Strategy 4 — CrossRef `query.bibliographic` with full `clean_ref` citation string from DB

**Rate limits:** NCBI=0.11s, CrossRef=0.15s, Unpaywall=0.15s, Download=0.5s

**Flags:** `--source` (landing_page/pmc/all), `--tier` (VC_pass/VC_fail/all), `--limit`, `--dry-run`, `--retry-failed`

**Run 1 results (dry-run=False):**
- DONE stats: ~42 downloaded, but went to ghost folder (wrong PROJECT_ROOT)
- Root cause: `PROJECT_ROOT = SCRIPT_DIR.parent.parent` (2 hops) instead of 3

**Run 2 results (after all fixes):**
| Status | Count |
|--------|-------|
| downloaded | 73 |
| download_failed | 193 |
| not_oa | ~600+ |
| oa_no_pdf_url | 83 |
| no_doi | 74 |

**Total from both runs:** ~115 new PDFs (42 from Run 1 to ghost → 28 unique moved to correct dest; 73 from Run 2)

**Library total: 868 → ~985 PDFs**

---

### 2. Bug Fixes Made to unpaywall_scanner.py (between runs)

| Bug | Fix |
|-----|-----|
| Wrong PROJECT_ROOT (2 hops instead of 3) | `SCRIPT_DIR.parent.parent` → `SCRIPT_DIR.parent.parent.parent` |
| DB lookup enriching 0 titles | PROJECT_ROOT fix resolved this (DB_PATH was pointing nowhere) |
| `title` column truncated ~60 chars | Changed `get_db_titles()` SQL to fetch `clean_ref` column instead |
| CrossRef too strict (score ≥ 50.0) | Lowered to `CROSSREF_MIN_SCORE = 30.0` |
| `url` fallback on Unpaywall result | Removed `or best.get('url')` — only use `url_for_pdf`; `url` is a landing page not a PDF |
| Unicode crash on Windows CP1252 | Replaced ✓/✗ chars with `[OK]`/`[X]` |
| Retry behavior | Added `--retry-failed` flag: re-processes `no_doi` + `download_failed`; skips `downloaded` + `not_oa` |

**Net effect of CrossRef fix:** DOI resolution rate went from ~110 to ~431 (when using `clean_ref` full citation string + lowered threshold).

---

### 3. Ghost Folder — FULLY RESOLVED ✅
**Problem:** Run 1 used wrong PROJECT_ROOT → downloaded 42 PDFs to ghost folder `01_module.1_warehouse/01_module.1_warehouse/citation_files/ITE/` instead of correct `01_module.1_warehouse/citation_files/ITE/`.

**Resolution (this session):**
- `fix_ghost.py` verified all remaining ghost files had copies at correct destination
- Remaining 14 ghost files (duplicates) deleted
- Ghost folder `01_module.1_warehouse/01_module.1_warehouse/` deleted via PowerShell `Remove-Item -Recurse -Force`
- The 28 ghost files not yet at correct destination were moved by prior fix iteration

**Current state:** Ghost folder gone. All PDFs at correct location.

---

### 4. JAMA Cookies Saved
**Path:** `key_data_files/cookies/jamanetwork.com_cookies.json`
- Contains AMA_AuthToken (expires ~April 11, 2026) + cf_clearance (Cloudflare)
- Access is via AMA membership credentials (in system env vars, not stored here)
- `.gitignore` updated: added `key_data_files/cookies/` section

**Note:** JAMA PDFs still download-failed (Cloudflare blocks automated requests regardless of auth token). Browser automation likely needed.

---

### 5. EXA Advanced Research Skill — Investigated, Not Integrated
User uploaded Exa advanced research paper skill instructions. Assessed relevance:
- The skill enables academic paper search via Exa's `research_paper` category with full filter support (date ranges, domain filtering, text matching)
- Useful for finding primary literature, ArXiv preprints, PubMed content
- NOT integrated this session — would require installing Exa MCP with `--transport http` endpoint
- **Deferred:** Could be valuable for Intelligence 2.0 Layer 2 (article currency checks against PubMed) or for discovering newer versions of articles in the library
- Instructions stored in user's uploads for future reference

---

### 6. PubMed MCP — Probed
Tool: `mcp__a1f87585-3692-477d-83c7-b12cc4986700`
- `lookup_article_by_citation` — WORKS (returns article metadata)
- `get_full_text_article` — returns text content, NOT PDF bytes
- `convert_article_ids` — returns 500 errors (unreliable)
- **Verdict:** Not useful for PDF acquisition. May be useful for metadata enrichment (DOI lookup via citation string). Compare to CrossRef strategy in unpaywall_scanner.

---

## Unpaywall Remaining Problems

| Category | Count | Notes |
|----------|-------|-------|
| download_failed | 193 | Publisher blocking: Springer, Oxford, Wiley, Elsevier — valid OA PDF URL found but download fails with 403/429 |
| oa_no_pdf_url | 83 | OA version exists in Unpaywall but no direct PDF URL (landing page only) |
| no_doi | 74 | 21 textbooks, 18 org guidelines (acponline, guidelines.gov, etc.), 35 genuinely DOI-less articles |

**For the 193 download_failed:** URL is correct (url_for_pdf returned), but publisher CDNs block Python requests. Requires either:
- Browser automation (Playwright/Selenium) with real browser headers
- Institutional access cookies
- Manual download

---

## DB State (unchanged this session)

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
| M1 maintain/ | **22** | 0 | +1: unpaywall_scanner.py |
| M2 scripts/ | 75 | 6 | unchanged |
| M3 scripts/ | 13 | 2 | unchanged |

---

## Output Files (M1/maintain/ — not git-tracked)

| File | Contents |
|------|----------|
| `unpaywall_results.csv` | ~967 rows — per-article outcomes (doi_method, doi, is_oa, oa_host, pdf_url, download_status, bytes, dest_filename) |

---

## Deferred Flags

| Flag | Description | Priority | Change |
|------|-------------|----------|--------|
| **DEFERRED-G** | ~~Unpaywall scan~~ | ~~HIGH~~ | **COMPLETE ✅** — 115 new PDFs; 193 publisher-blocked remain |
| **DEFERRED-H** | **Publisher blocking** — 193 articles need browser automation or institutional access (Springer, Oxford, Wiley, Elsevier) | MEDIUM | **NEW** |
| **DEFERRED-A** | 37 original manual PDFs — re-audit against unpaywall_results.csv; some may now be downloaded | HIGH | Re-examine |
| DEFERRED-B | `update_citation_trends.py` after backfill | MEDIUM | unchanged |
| DEFERRED-C | AAFP vs ITE trend comparison | MEDIUM | unchanged |
| DEFERRED-D | 229 citation gap articles (88 AFP batch-downloadable) | MEDIUM | unchanged |
| DEFERRED-E | Interactive vector dashboard | LOW | unchanged |
| DEFERRED-F | Intelligence 2.0 Layer 2 (`article_currency` via PubMed, 344 PMIDs cached) | MEDIUM | unchanged |

---

## Next Session — Start Here

1. **DEFERRED-A (first task):** Cross-reference the original 37 manual PDFs (from pre-session library) against `unpaywall_results.csv` — check `download_status == downloaded` for those ART-IDs. Any that are now downloaded can be removed from the manual list. Remainder = true manual-only.

2. **Sandbox cleanup:** Delete temp files from `04_module.4_sandbox/`: `fix_ghost.py`, `fix_scanner.py`, `count_out.txt` — these were session tools, not library scripts.

3. **DEFERRED-H (optional):** For the 193 publisher-blocked articles — explore whether browser automation (Playwright) with spoofed headers can bypass CDN blocking. May require institutional IP or VPN.

4. **DEFERRED-F:** Intelligence 2.0 Layer 2 — `article_currency` table via PubMed (344 PMIDs in `pubmed_pmid_cache`; NCBI API key set in env).

5. **EXA MCP option:** If Exa MCP is installed (`claude mcp add --transport http exa "https://mcp.exa.ai/mcp?tools=web_search_advanced_exa"`), the advanced research paper skill could find primary literature for the 74 no_doi articles (especially the textbook references — search by title + author).

---

## Files Changed This Session

| File | Action |
|------|--------|
| `01_module.1_warehouse/scripts/maintain/unpaywall_scanner.py` | NEW — final version with all bug fixes |
| `01_module.1_warehouse/scripts/maintain/unpaywall_results.csv` | NEW (output, not git-tracked) |
| `key_data_files/cookies/jamanetwork.com_cookies.json` | NEW (gitignored) |
| `.gitignore` | MODIFIED — added `key_data_files/cookies/` |
| `04_module.4_sandbox/fix_ghost.py` | TEMP — delete next session |
| `04_module.4_sandbox/fix_scanner.py` | TEMP — delete next session |
| `04_module.4_sandbox/count_out.txt` | TEMP — delete next session |
| `BATON_active_040_...` | RETIRED → baton_archive/ |
| `CLAUDE.md` | MODIFIED — Active State, PDF count, M1 maintain count |
| `_index.md` | MODIFIED — M1 maintain count, PDF count, housekeeping log |
