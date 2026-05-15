# BATON 067 — AFP PDF Acquisition (72 Articles Closed)

**Date:** 2026-05-07
**Session Type:** PDF Acquisition Phase 4 (DEFERRED-QID-XREF-LIBRARY-GAPS — AFP execution + BATON 066 worktree merge)
**Git Hash (pre-commit):** 6019f69
**Branch:** main
**Previous BATON:** BATON_active_066_20260507_jama_nejm_pdf_harvest_complete.md
**Status:** Successful — BATON 066 worktree merged to main; 72 AFP articles closed (83 → 11); 11 stuck (5 AAFP HTTP 500 server outage, 6 malformed clean_ref/title DB QC needed).

---

## Session Summary

This session executed the BATON 066 follow-on (worktree merge + AFP article acquisition). Two major work streams:

**Stream 1: BATON 066 worktree merge.** Physically moved 127 PDFs (111 VC_fail + 16 VC_pass) from `.claude/worktrees/modest-merkle-df0121/` to main repo path via robocopy. Migrated 8 new BATON 066 maintain scripts + 5 state files via PowerShell `Move-Item`. Verified post-merge counts: VC_fail=988, VC_pass=216 (2 collisions where source codon filename overwrote destination — expected behavior for codon canonical-name overwrites).

**Stream 2: AFP gap closure (83 → 11, 72 articles closed).** Goal: download missing AFP-source articles via authenticated Playwright session.

*Phase 2A — `aafp_fill_gaps.py` (existing script).* Discovered Playwright `expect_download` was timing out because AAFP serves PDFs inline (browser-rendered). Patched to use `context.request.get(pdf_url)` which fetches bytes via the authenticated session cookies. 128/128 downloads succeeded. Identified 89 of 128 created cross-tier codon duplicates (article ART-IDs already on disk in VC_fail with codon names, then re-downloaded into VC_pass). 34 non-codon redundant downloads moved to `_dupe_archive/`. AFP gap closed by 4 (83 → 79).

*Phase 2B — `aafp_targeted_downloader.py` v1 (BROKEN).* Built first version using AAFP's `global-search.html?searchKey=` URL pattern. URL navigation was silently rejected by AAFP — `goto()` calls returned but page never actually navigated to search results. Anchor harvesting picked up homepage chrome links. Downloaded 79 wrong-content corrupt PDFs (all containing the same "Benign Anorectal Conditions" homepage feature, mostly identical bytes). 79 corrupt files quarantined to `_corrupted_targeted_run/`.

*Phase 2C — `aafp_targeted_downloader.py` v2 (TOC-scrape architecture).* Pivoted to scraping monthly issue TOC pages (`/pubs/afp/issues/{YYYY}/{MM00}.html`) with title-similarity matching. Worked perfectly for 2021-2024 (monthly publication era). 13 articles closed, all hashes unique, validated content correct.

*Phase 2D — `aafp_targeted_downloader.py` v3 (3-tier cascade with structured-meta validation).* Added two more tiers:
- Legacy URL construction with **volume parity** mapping (odd vol → Jan-Jun, even vol → Jul-Dec) for pre-2021 biweekly articles. Confirmed by Hainer 2013 vol 87 (odd) issue 10 → 0515, and Pyzocha 2020 vol 102 (even) issue 9 → 1101.
- CrossRef DOI lookup as 3rd-tier fallback for articles with malformed clean_ref.

Replaced fuzzy title matching with **structured citation metadata validation** — compares page's `citation_volume` + `citation_issue` + `citation_firstpage` meta tags to parsed values from clean_ref. Exact 3-way match = bulletproof confirmation. Title-similarity is fallback only. Closed 56 more articles. **Total: 72 closed.**

Auth state persistence: Added Playwright `storage_state` capture to `_aafp_auth.json` (gitignored). First run prompts manual login + saves auth state; subsequent runs skip login entirely. Auto-detects expired session by hitting `/pubs/afp.html` and checking redirect.

Final state: 11 stuck AFP articles. 5 fail with HTTP 500 from AAFP (server-side outage on vintage 2000-2010 PDFs — confirmed by Mikey navigating manually to one URL and seeing AAFP's "Technical Issues" error page). 6 fail because clean_ref is malformed (junk DB titles like "Online", "402", "what you should know") AND CrossRef returns unrelated articles (e.g., Springer book chapters with similar titles).

End-of-session cleanup: Confirmed all 127 quarantined files (48 dupes + 79 corrupt) were truly bad via codon canonical-match check + page-1 text content verification. Consolidated to `delete_me_pdfs_b65/` at project root with `dupe__` and `corrupt__` prefixes. User then permanently deleted that folder.

VALIDATION: 289 newly-downloaded codon files in VC_fail/VC_pass verified via SHA256 — all 289 unique content hashes. Zero corruption.

---

## Current DB State

| Table | Rows | Notes |
|-------|------|-------|
| articles | 2,206 | unchanged this session |
| questions (ITE) | 1,639 | blueprint 100%, body_system normalized |
| aafp_questions | 1,221 | blueprint 100%, concept_tags 100% |
| qid_art_xref | 2,710 | unchanged |
| aafp_qid_art_xref | 864 | unchanged |
| article_icd10 | 4,959 | unchanged |
| question_icd10 | 5,774 | unchanged |
| aafp_question_icd10 | 4,753 | unchanged |
| clinical_pathways | 4,959 | unchanged |
| pubmed_pmid_cache | 344 | unchanged |
| article_icd10_vec | 1,757 | unchanged |
| question_icd10_vec | 2,747 | unchanged |
| icd10_vec | 2,219 | unchanged |
| intersection_centroid_vec | 158 | unchanged |
| article_currency | 2,206 | unchanged |

**Next ART-ID:** ART-2208

**No schema changes this session.** Pure PDF acquisition + worktree merge — no DB writes.

---

## PDF Library

| Tier | Count | Notes |
|------|-------|-------|
| VC_fail | 1,056 | post-merge from worktree (988) + 72 AFP additions = 1,056 (some net of overwrites) |
| VC_pass | 309 | post-merge BATON 066 + AFP additions |
| local_lite | 117 | unchanged |
| right_click | 58 | unchanged |
| _dupe_archive | 0 | cleared — 48 quarantined files moved to `delete_me_pdfs_b65/` then deleted by user |
| _corrupted_targeted_run | 0 | cleared — 79 quarantined files moved to `delete_me_pdfs_b65/` then deleted by user |
| AAFP | 15 | unchanged |
| ite_exams | 16 | unchanged |
| **Total ITE active tiers** | **1,540** | (VC_fail + VC_pass + local_lite + right_click) |

Organization: `citation_files/ITE/{VC_fail,VC_pass,local_lite,right_click}/`, `citation_files/AAFP/`, `citation_files/ite_exams/`.

**Articles still missing PDFs:** ~801 (down from 873 at BATON 066 close — 72 AFP articles closed this session).

---

## Script Inventory

### M1 Warehouse (`01_module.1_warehouse/scripts/`)
- **build/**: 8 .py — Standard suite, unchanged this session
- **maintain/**: 38 .py main + 1 root scraper (`aafp_brq_scraper.py`)
  - **+9 net new this session:** 8 BATON 066 worktree-merged scripts (jama_*, nejm_*, unpaywall_retry) + `aafp_targeted_downloader.py` (NEW)

**NEW this session:**
- `aafp_targeted_downloader.py` — 3-tier cascade: legacy URL with volume parity + monthly TOC scrape + CrossRef DOI fallback. Replaced fuzzy title matching with structured `citation_volume`/`citation_issue`/`citation_firstpage` meta validation. Includes Playwright `storage_state` auth persistence to `_aafp_auth.json`.
- `_aafp_search_dom_probe.py` — diagnostic tool (gitignored under `_*.py`)

**MODIFIED this session:**
- `aafp_fill_gaps.py` — patched: `expect_download` → `context.request.get()` (AAFP serves PDFs inline, not as downloads); homepage login URL `https://www.aafp.org/` (was 404'd `home/login.html`)
- `jama_pending.json` — BATON 066 annotation, propagated from worktree merge
- `unpaywall_results.csv` — BATON 066 retry log, propagated from worktree merge

### M2 Processor (`02_module.2_processor/scripts/`)
- 75 .py + 6 .js — Standard suite, no changes this session

### M3 Analyst (`03_module.3_analyst/scripts/`)
- 55 .py + 4 .js + 6 JSON config — Standard suite, no changes this session

### M5 Web (`05_module.5_web/`)
- 3 .py sync + 35 TS/TSX + 5 SQL migrations — Standard suite, no changes this session

---

## Known Bugs / Open Issues

| ID | Issue | Impact | Status | Fix |
|----|-------|--------|--------|-----|
| BUG-AAFP-EXPECT-DOWNLOAD | `aafp_fill_gaps.py` used Playwright `expect_download` which never fires because AAFP serves PDFs inline (browser-rendered) | Original Phase 2 timed out on every download attempt | FIXED | Replaced with `context.request.get(pdf_url)` which fetches bytes via authenticated session cookies. PDF arrives as `response.body()` bytes, written to disk. |
| BUG-AAFP-CSS-89-DUPES | `aafp_fill_gaps.py` title-similarity threshold of 0.72 too strict — 89 articles with codon PDFs already on disk got re-downloaded with codon names into VC_pass | Pollutes VC_pass tier purity; 89 ART-IDs now have PDFs in both VC_fail AND VC_pass | OPEN (DEFERRED-CROSS-TIER-CODON-DUPES) | Future cleanup: pick canonical version per ART-ID (likely larger file), move others to `_dupe_archive/` |
| BUG-AAFP-SEARCH-URL-INTERCEPT | `aafp_targeted_downloader.py` v1 used AAFP's URL-driven search (`/global-search.html?searchKey=X`) which was silently rejected; resulted in 79 corrupt downloads of homepage feature article | Initial broken run wrote 79 wrong-content PDFs with correct codon names — silent data corruption | FIXED | Pivoted to monthly TOC scrape + legacy biweekly URL construction with volume parity + CrossRef fallback. Added structured `citation_volume`/`issue`/`firstpage` meta validation gate before any save. |
| BUG-AAFP-HOMEPAGE-LOGIN | `aafp_fill_gaps.py` originally pointed Playwright at `https://www.aafp.org/home/login.html` which 404s | User had to manually click AAFP logo to navigate to homepage to log in | FIXED | Both AAFP scripts now open `https://www.aafp.org/` (homepage) at login step |
| BUG-PENDING-LIST-URL-MISMATCH | `jama_pending.json` had wrong URL for ART-0302 (URL actually resolved to ART-0020 = Achten 2019, not Deshmukh 2021) | Wrong PDF would have filed under wrong ART-ID — caught manually by author/year mismatch on download | CARRIED FORWARD (FIXED entry, retained for traceability) | Renamed downloaded PDF to ART-0020 codon; ART-0302 still missing (T&F paywalled). Spot-check other pending lists for similar URL mismatches — see DEFERRED-PENDING-LIST-QC. |
| BUG-CHROME-MCP-USER-ACTIVATION | Chrome MCP `javascript_tool` injection cannot trigger `<a download>.click()` — Chrome blocks because injected JS lacks transient user activation | Cannot use Chrome MCP for any browser-auth-required PDF download via download attribute | WORKAROUND DOCUMENTED (carried forward) | Generate paste-ready JS, have user paste into DevTools Console (carries activation). Pattern: `nejm_console_script.py`. |
| BUG-CHROME-PNA-LOCALHOST | Chrome Private Network Access blocks `fetch()`/`sendBeacon`/form-submit from public origins to localhost servers, even with `Access-Control-Allow-Private-Network: true` | "POST PDF bytes to local Python server" architecture cannot work for browser-auth-required journals | DOCUMENTED — DEAD END (carried forward) | Avoid this pattern. `nejm_save_server.py` retained only as reference. |

---

## Deferred Flags

| Flag | Status | Notes | Next Action |
|------|--------|-------|-------------|
| DEFERRED-QID-XREF-LIBRARY-GAPS | OPEN | Reduced significantly. Started session at 873 articles missing PDFs. After this session: ~801 missing (closed ~72 AFP articles). | Tackle remaining gaps by source_type. Major buckets: Other Journal (397), Guideline/Org (107), Pediatrics (39), Annals (36), Circulation/BMJ (29 each). |
| DEFERRED-MERGE-WORKTREE-TO-MAIN | CLOSED | Resolved 2026-05-07 — robocopy moved 127 PDFs and Move-Item migrated 13 files (8 scripts + 5 state files) from worktree to main | (resolved this session) |
| DEFERRED-NEJM-PHASE-2 | CLOSED (BATON 066) | 76/76 NEJM PDFs acquired via DevTools console paste pattern | (resolved 2026-05-07 BATON 066) |
| DEFERRED-JAMA-PHASE-2 | CLOSED (BATON 066) | 50/50 JAMA PDFs acquired via Chrome MCP + token-signed CDN URL pattern | (resolved 2026-05-07 BATON 066) |
| DEFERRED-AAFP-HTTP-500 | OPEN (NEW) | 5 AFP articles (vintage 2000-2010) blocked by AAFP server outage. URLs validate correctly via citation_volume/issue/firstpage meta but `.pdf` returns HTTP 500. Confirmed AAFP-side via "Technical Issues" page. ART-IDs: ART-0044 (2007), ART-0642 (2000), ART-1564 (2000), ART-1811 (2000), ART-1822 (2010) | Retry monthly. If still blocked after a quarter, switch to PMC fallback or AAFP Foundation library acquisition. |
| DEFERRED-AFP-DATA-QC | OPEN (NEW) | 6 AFP articles with malformed clean_ref / junk DB title fields. Blocks both URL construction (clean_ref doesn't parse) and CrossRef (returns unrelated articles for junk-title queries). ART-IDs: ART-0349 (EBM glossary), ART-0362 (Eichelberger), ART-0452 (Franck), ART-0680 (Killeen), ART-1072 (Risk), ART-1797 (Screening) | DB QC pass: examine each clean_ref, repair title field from extracted clean_ref content, retry `aafp_targeted_downloader.py` |
| DEFERRED-CROSS-TIER-CODON-DUPES | OPEN (NEW) | 89 ART-IDs now have codon PDFs in BOTH VC_fail and VC_pass tiers (created by `aafp_fill_gaps.py` title-similarity matching at 0.72 threshold being too strict — articles already on disk in VC_fail got re-downloaded into VC_pass) | Dedupe pass: per ART-ID, compare both versions, keep canonical (likely the larger/newer file), move other to `_dupe_archive/` |
| DEFERRED-UNPAYWALL-CLOUDFLARE | OPEN (BATON 066) | 144 OA URLs blocked by Cloudflare even with curl-cffi chrome110 impersonation | Apply NEJM-style DevTools console pattern, group failed URLs by domain, run console-paste sessions per origin |
| DEFERRED-DESHMUKH-2021 | OPEN (BATON 066) | ART-0302 (Deshmukh 2021, J Matern Fetal Neonatal Med, DOI 10.1080/14767058.2019.1649650) paywalled at tandfonline.com | Mikey needs T&F institutional access — check St. Luke's library access, or interlibrary loan |
| DEFERRED-PENDING-LIST-QC | OPEN (BATON 066) | `jama_pending.json` had ART-0302/ART-0020 URL mismatch. Suggests other pending lists may have similar ART→URL mismatches | Spot-check 5-10 random entries: open URL, verify resulting filename matches expected author. If mismatch rate >1/10, sweep all pending lists. |
| DEFERRED-YOY-ROBUSTNESS | OPEN (carry forward) | `ite_analyzer_v3.py` longitudinal_delta() function with dense temporal data edge cases | Test with dense temporal patterns (resident with exams every 2 weeks for 12 months) |

---

## Validation Results

**SHA256 hash audit on 289 newly-downloaded codon files** (VC_fail + VC_pass deltas this session):
- 289 unique content hashes — zero corruption, zero duplicates within new files.
- All files verified as valid PDFs via `%PDF` magic byte header.
- All filenames matched `Author_Year#@#ART-XXXX@#@.pdf` codon pattern.

**AFP gap-closure validation:**
- Pre-session: 83 AFP articles missing PDFs.
- Post-session: 11 missing (5 HTTP 500 server outage + 6 DB clean_ref/title issues).
- 72 articles closed = 86.7% gap closure for AFP source_type.

**Worktree merge validation:**
- robocopy log confirmed 127 PDFs transferred (111 VC_fail + 16 VC_pass).
- Post-merge counts: VC_fail = 988, VC_pass = 216 (2 collisions due to codon canonical-name overwrites — expected).
- 8 maintain scripts + 5 state files migrated via `Move-Item`.

**Quarantine audit:**
- 127 files in `_dupe_archive/` (48) and `_corrupted_targeted_run/` (79) confirmed truly bad via:
  - Codon canonical-match check (codon ART-ID maps to wrong content)
  - Page-1 text extraction comparing claimed vs actual article
- Consolidated to `delete_me_pdfs_b65/` with `dupe__` / `corrupt__` prefixes; user permanently deleted folder.

---

## Next Steps

### Immediate (before next session)
1. **User commits via GitHub Desktop.** Stage: new BATON 067, retired BATON 066 (move to `baton_archive/`), `.gitignore` update (added `_*.json`, `_*.txt`, `_*.csv`, `_*.log` to maintain ignore patterns), modified scripts (`CLAUDE.md`, `aafp_fill_gaps.py`, `jama_pending.json`, `unpaywall_results.csv`), and 10 new untracked `.py` scripts: `aafp_targeted_downloader.py` + 8 BATON 066 maintain scripts (`jama_chrome_harvester.py`, `jama_prep_articlepdf_urls.py`, `nejm_doi_lookup.py`, `nejm_build_js_batch.py`, `nejm_console_script.py`, `nejm_move_downloads.py`, `nejm_save_server.py`, `unpaywall_retry.py`). Note: `_aafp_search_dom_probe.py` matches `_*.py` gitignore pattern (verify before commit).
2. **Re-run all 7 resident analyses on Mac after git pull** (carryover from BATON 065 + 066 — still pending).

### Short-term (this week)
3. **Cross-tier codon dedupe** (DEFERRED-CROSS-TIER-CODON-DUPES). Write a one-shot script that, for each ART-ID with codon PDFs in both VC_fail and VC_pass, picks the canonical version (largest file size or newest mod time), keeps it in the higher tier (VC_pass), moves the other to `_dupe_archive/`.
4. **AFP DB data QC** (DEFERRED-AFP-DATA-QC). Repair the 6 malformed clean_ref / title fields. Use clean_ref text extraction to populate title where current title is junk ("Online", "402", "what you should know"). Then re-run `aafp_targeted_downloader.py` to close those 6.
5. **Apply NEJM DevTools pattern to 144 unpaywall Cloudflare-blocked URLs** (DEFERRED-UNPAYWALL-CLOUDFLARE). Group `unpaywall_results.csv` failed URLs by domain (diabetesjournals.org, ahajournals.org, etc.). Reuse `nejm_console_script.py` as template, swap URL pattern.

### Medium-term (next 2 weeks)
6. **Tackle remaining 801-article broader gap** by source_type buckets: Other Journal (397), Guideline/Org (107), Pediatrics (39), Annals (36), Circulation (29), BMJ (29), Lancet (12), Chest (11). Each origin gets its own console-paste session or targeted script.
7. **AAFP HTTP 500 retry** (DEFERRED-AAFP-HTTP-500). Wait for AAFP to fix the vintage-PDF archive. Re-run `aafp_targeted_downloader.py` with the 5 affected ART-IDs once a month until resolved or 3 months pass, then escalate (PMC fallback or AAFP Foundation library).
8. **Spot-check pending list integrity** (DEFERRED-PENDING-LIST-QC). Pick 5-10 entries from `jama_pending.json` and any other pending lists, navigate to each URL, verify the resolved filename matches the pending entry's claimed author/year.

---

## Locked Rules

(Copied verbatim from BATON 066 — never modify without explicit instruction.)

1. **Fix the data, not the code.** If a script gets complex to handle messy data → clean the data upstream instead.
2. **VC gate = sole criterion** for right_click tier. DB membership alone is not sufficient.
3. **Source data is protected.** DB + PDFs + VC gate survive everything. Derived files are disposable.
4. **Dynamic paths only.** Python: `SCRIPT_DIR = Path(__file__).resolve().parent; PROJECT_ROOT = SCRIPT_DIR.parent.parent`. JS: `path.resolve(__dirname, "../../")`.
5. **No de novo JS.** Existing JS scripts migrate fine. New code = Python only (relaxed: use JS when needed, flag if clutter accumulates).
6. **BATON first.** Read the active BATON before any work. It has deferred flags and current state.
7. **QC after every integration.** Schema-level column-by-column population comparison, old cohort vs new.
8. **Git via Desktop Commander.** Claude can run git commits via Desktop Commander Python subprocess (helper: `claude_knowledge/git_runner.py`). Cannot `rm` NTFS files — deletions still require Windows Explorer/terminal.
9. **`shutil.rmtree` is BANNED.** Use explicit file-by-file deletion or PowerShell Remove-Item. shutil.rmtree bypasses Recycle Bin and is irreversible.
10. **Strategy 0 in every enricher.** Codon parse is always the first matching strategy.
11. **Schemas before scripts.** SQL `CREATE TABLE` defined before build scripts are written.
12. **`_normalize_concept()` fallback = first-letter capitalize only.** Never `.title()` — it mangles acronyms (HIV → Hiv, IBS-D → Ibs-D). Use `stripped[0].upper() + stripped[1:]`. Add new synonym entries for any canonical form that needs resolution.
13. **ICD-10 enrichment is invisible.** `icd10_profile` is passed to `match_practice_questions_v3()` as a hidden scoring signal and must never appear in the resident report. ICD-10 codes are internal precision machinery only.
14. **Word docs use `word_doc_defaults.py`.** All Python scripts that generate `.docx` files must `from word_doc_defaults import *` and apply the St. Luke's color palette, Aptos font, and helper functions defined there.

---

## Git Status

**Hash:** 6019f69 (pre-commit; will update after user commits)
**Branch:** main

**Modified files this session:**
- `.gitignore` — added M1 maintain state-file ignore patterns (`_*.json`, `_*.txt`, `_*.csv`, `_*.log`)
- `01_module.1_warehouse/scripts/maintain/aafp_fill_gaps.py` — patched `expect_download` → `context.request.get()`; homepage login URL fix
- `01_module.1_warehouse/scripts/maintain/jama_pending.json` — BATON 066 annotation, propagated from worktree merge
- `01_module.1_warehouse/scripts/maintain/unpaywall_results.csv` — BATON 066 retry log, propagated from worktree merge
- `CLAUDE.md` — will be updated by manifest-writer

**Untracked / new files (this session + pending merge from BATON 066 worktree):**
- `01_module.1_warehouse/scripts/maintain/aafp_targeted_downloader.py` — NEW: 3-tier cascade (legacy URL + TOC scrape + CrossRef DOI)
- `01_module.1_warehouse/scripts/maintain/_aafp_search_dom_probe.py` — NEW: diagnostic tool (gitignored under `_*.py`)
- `01_module.1_warehouse/scripts/maintain/jama_chrome_harvester.py` — BATON 066, pending merge
- `01_module.1_warehouse/scripts/maintain/jama_prep_articlepdf_urls.py` — BATON 066, pending merge
- `01_module.1_warehouse/scripts/maintain/nejm_doi_lookup.py` — BATON 066, pending merge
- `01_module.1_warehouse/scripts/maintain/nejm_build_js_batch.py` — BATON 066, pending merge
- `01_module.1_warehouse/scripts/maintain/nejm_console_script.py` — BATON 066, pending merge
- `01_module.1_warehouse/scripts/maintain/nejm_move_downloads.py` — BATON 066, pending merge
- `01_module.1_warehouse/scripts/maintain/nejm_save_server.py` — BATON 066, pending merge
- `01_module.1_warehouse/scripts/maintain/unpaywall_retry.py` — BATON 066, pending merge

**Gitignored changes (do not stage):**
- 72 new AFP PDFs across `citation_files/ITE/{VC_fail,VC_pass}/`
- 127 BATON 066 PDFs merged into main repo path (already gitignored)
- State files matching `_*.json`, `_*.txt`, `_*.csv`, `_*.log` in `01_module.1_warehouse/scripts/maintain/`
- `_aafp_auth.json` (Playwright storage_state — auth cookies)

**Next commit:** Stage BATON 067 (this file), retire BATON 066 to `baton_archive/`, `.gitignore` update, modified scripts, and 10 new `.py` scripts (verify `_aafp_search_dom_probe.py` ignored under `_*.py` pattern).

---

## Hand-Off Notes

### For Mikey
- **72 AFP articles closed; 11 stuck.** 5 are AAFP server outages (HTTP 500 on vintage 2000-2010 PDFs — confirmed AAFP-side). 6 need DB QC: their `clean_ref` or `title` fields are junk ("Online", "402", "what you should know"), which breaks both URL construction and CrossRef lookup.
- **`aafp_targeted_downloader.py` is the canonical AFP retrieval pattern going forward.** Three-tier cascade with structured citation-meta validation. Reusable for the remaining gap.
- **Auth state persists.** First run prompts manual login → saves `_aafp_auth.json` → subsequent runs are passwordless until session expires.
- **Quarantined files were permanently deleted by you.** 127 bad files (48 dupes + 79 corrupt) consolidated to `delete_me_pdfs_b65/` then deleted. All 289 new codon files passed SHA256 uniqueness audit — zero corruption.
- **BATON 066 worktree fully merged.** All 127 PDFs + 8 scripts + 5 state files now in main repo path. Worktree can be removed.
- **Re-run resident analyses on Mac** still pending from BATON 065 + 066. Do this after `git pull`.

### For Next Session
- Read BATON 067 first.
- The 89 cross-tier codon duplicates (DEFERRED-CROSS-TIER-CODON-DUPES) are the cleanup priority — they pollute VC_pass tier purity.
- Highest-leverage acquisition next is the 144 unpaywall Cloudflare-blocked URLs — already free OA, just need DevTools-paste workaround per origin.
- 6 AFP articles need DB clean_ref/title repair before they can be downloaded — this is a small but blocking data QC task.
- The 5 AFP HTTP-500 articles need monthly retry, not session work.

### Architecture Notes (new this session)
- **AAFP serves PDFs inline (browser-rendered), not as downloads.** Playwright `expect_download` never fires. Use `context.request.get(pdf_url)` to fetch bytes via authenticated session cookies. Same pattern likely applies to other inline-rendering journal sites.
- **AFP biweekly volume parity (pre-2021).** Odd vol number → Jan-Jun publication; Even vol number → Jul-Dec publication. Confirmed by Hainer 2013 vol 87 issue 10 → 0515, Pyzocha 2020 vol 102 issue 9 → 1101. Applies to AFP biweekly era only; 2021-onward is monthly with `{YYYY}/{MM00}.html` TOC URLs.
- **Structured citation-meta validation is bulletproof.** Comparing page's `citation_volume` + `citation_issue` + `citation_firstpage` meta tags to parsed values from `clean_ref` gives exact-match confirmation that beats fuzzy title similarity. Use this pattern for any journal site that emits Highwire-style meta tags.
- **AAFP global-search URL is silently rejected.** Direct navigation to `/global-search.html?searchKey=X` fails to load search results — anchor harvesting picks up homepage chrome. Use TOC scrape or direct article URL construction instead.

### Database
- DB unchanged this session. All counts identical to BATON 066 close. Confirm with `SELECT COUNT(*) FROM articles;` on next session start (`articles=2,206`, `qid_art_xref=2,710`, etc.).

### Filesystem
- **BATON 066 worktree was at:** `C:\Users\mpsch\Desktop\board_prep_intel\.claude\worktrees\modest-merkle-df0121\` — fully merged this session, can now be pruned.
- **Quarantine folder `delete_me_pdfs_b65/`** at project root was permanently deleted by user this session.
- **`_aafp_auth.json`** (Playwright auth state) is gitignored under `_*.json` pattern. Persists AAFP session across script runs.
- **Agent template path (Windows-specific):** `board_prep_intel/.claude/skills/session-housekeeping/agents/` — NOT the Cowork skills-plugin folder (that's Mac path). Carries forward.

---

## Glossary Reminders

(Copied verbatim from CLAUDE.md / BATON 066. Do not edit.)

| Term | Meaning |
|------|---------|
| **ITE** | In-Training Examination (ABFM Family Medicine board exam) |
| **ABFM** | American Board of Family Medicine |
| **VC** | AAFP Board Prep Video Course (48 sessions, the priority filter) |
| **VC gate** | `key_data_files/session_hy_inserts_v7.json` — 352 citations — SOLE criterion for right_click tier |
| **BATON** | Session handoff document. Read the active one first, every session |
| **codon** | Filename format: `Author_Year#@#ART-XXXX@#@.pdf` — start `#@#`, stop `@#@` |
| **ART-ID** | Article primary key (e.g. ART-1234) — embedded in codon filename |
| **QID** | Question ID format: `QID-YYYY-NNNN` (e.g. QID-2024-0042) |
| **right_click / $right_click$** | M2 completed tier: VC_pass + fully enriched (DOCX exists) — folder: `03_right_click/` |
| **local_lite** | M2 completed tier: VC_fail + fully enriched (DOCX exists) — folder: `01_local_lite/` |
| **VC_pass** | M1 staging tier: passed VC gate, awaiting full pipeline |
| **VC_fail** | M1 staging tier: failed VC gate, awaiting full pipeline |
| **enricher** | `ite_intelligence_enricher.py` — primary v4 enricher, Strategy 0 = codon parse |
| **Strategy 0** | Regex parse of codon to extract ART-ID — primary match strategy, always first |
| **the DB** | `00_database/db/ite_intelligence.db` — source of truth, never disposable |
| **PROJECT_ROOT** | 2 levels up from SCRIPT_DIR — `SCRIPT_DIR = Path(__file__).resolve().parent; PROJECT_ROOT = SCRIPT_DIR.parent.parent` |
| **M1 / M2 / M3 / M4 / M5** | Warehouse / Processor / Analyst / Sandbox / Web modules |
| **derived data** | Disposable: JSONs, DOCXs, CSVs. DB + PDFs + VC gate are protected source data |

---

**BATON 067 Complete.** BATON 066 worktree merged to main; 72 AFP articles closed via 3-tier `aafp_targeted_downloader.py` cascade with structured citation-meta validation; 11 AFP articles remain stuck (5 AAFP HTTP 500 server outage + 6 DB clean_ref/title QC needed).
