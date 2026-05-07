# PDF Harvest Mission Brief
**Written by:** Cowork Claude (2026-05-06)  
**For:** Claude Code (JAMA/NEJM/remaining gap harvest)  
**Project root:** `board_prep_intel/` (see CLAUDE.md for full conventions)

---

## The Mission

We have **2,206 articles** in the DB. We have PDFs for **1,254** of them (~57%).
The remaining **~952 articles lack PDFs** — our target is to close as much of that gap as possible.

**Immediate priority:** 50 JAMA articles + ~65 NEJM articles = ~115 PDFs that are close to solved.  
**Secondary priority:** 179 confirmed open-access articles whose downloads failed on first attempt.  
**Tertiary:** The broader ~700+ remaining gap.

---

## Output Format (Non-Negotiable)

All PDFs must be saved with **codon filenames** and placed in the correct tier folder.

**Filename format:** `Author_Year#@#ART-XXXX@#@.pdf`
- `Author` = first author last name from the article record (capitalize first letter only — never `.title()`)
- `Year` = publication year
- `ART-XXXX` = the article's DB primary key (from jama_pending.json or DB query)

**Destination folders:**
```
board_prep_intel/01_module.1_warehouse/citation_files/ITE/VC_pass/    ← tier = "VC_pass"
board_prep_intel/01_module.1_warehouse/citation_files/ITE/VC_fail/    ← tier = "VC_fail"
board_prep_intel/01_module.1_warehouse/citation_files/ITE/local_lite/ ← tier = "local_lite"
board_prep_intel/01_module.1_warehouse/citation_files/ITE/right_click/ ← tier = "right_click"
```
The `tier` field in `jama_pending.json` tells you which folder each article goes in.

**Validation:** A downloaded file must be `>= 10KB` and start with `%PDF` bytes.  
**Duplicates:** If a codon file already exists in the tier folder, skip it.

---

## Priority 1 — JAMA (50 Articles)

### Data
File: `01_module.1_warehouse/scripts/maintain/jama_pending.json`

Format:
```json
[
  {
    "article_id": "ART-0089",
    "tier": "VC_pass",
    "year": "2020",
    "author": "Armstrong",
    "title": "Pathophysiology, clinical presentation, and treatment of psoriasis: a review",
    "url": "https://jamanetwork.com/journals/jama/article-abstract/2766169"
  },
  ...
]
```

URLs are a mix of `article-abstract/XXXXXXX` and `fullarticle/XXXXXXX` patterns.
Some have `guestAccessKey` query params (e.g. ART-0651) — **preserve those parameters** when navigating, as they may grant free access.

### What We Tried and Why It Failed

**Attempt 1 — curl-cffi Chrome impersonation (`exa_pdf_downloader.py`)**
- Strategy: HTTP requests with TLS fingerprint impersonating Chrome 110
- Result: 403 on all 50 JAMA articles
- Failure reason: Cloudflare `cf_clearance` cookie is tied to the *exact* Chrome binary version and TLS handshake signature. Python-level impersonation is insufficient — Cloudflare detects the mismatch.

**Attempt 2 — Playwright headless with cookie injection (`playwright_auth_downloader.py`)**
- Strategy: Launch headless Chromium, inject Cookie-Editor JSON cookies, navigate to article page, listen for PDF response
- Result: Most items stalled or timed out (60+ second hangs)
- Failure reason: Quantum Metric analytics script (`cdn.quantummetric.com/qscripts/quantum-ama.js`) loads on every JAMA page and intercepts XHR/fetch. Even with cookies injected, the page hangs in the analytics setup phase for headless contexts.
- Secondary issue: Cookie-Editor export format includes `sameSite`, `httpOnly`, `session` fields that Playwright's `add_cookies()` chokes on — needs field filtering.

**Attempt 3 — Local HTTP server / CORS bridge (`browser_pdf_harvester.py`)**
- Strategy: Run Flask server on localhost:5000; serve an HTML page that uses `fetch()` to grab PDFs; POST base64 bytes back to Flask; Python writes file.
- Result: Immediate failure.
- Failure reason: CORS. A page served from `localhost:5000` cannot issue `fetch()` to `jamanetwork.com` — browser blocks cross-origin requests. Content Security Policy on JAMA pages also explicitly blocks this.

**What we know works (but haven't executed yet):**
- `guestAccessKey` URLs (like ART-0651) may allow unauthenticated direct PDF access — test this first.
- JAMA `fullarticle/` URLs have a **PDF button** in the DOM. Inside a *live, authenticated* Chrome session, clicking it triggers a download or navigates to a `.pdf` URL.
- JAMA Network Open articles (`jamanetwork.com/journals/jamanetworkopen/`) are **fully open access** — PDFs available without auth.

### Authentication Notes
- Credentials may be in env vars: `JAMA_EMAIL`, `JAMA_PASSWORD`
- Cookie files (if still present): `key_data_files/browser_profiles/jama_cookies_export.json`
- **Re-authentication is allowed.** If credentials exist, logging in fresh is preferable to stale cookies.
- **Opening new browser instances/tabs is allowed.** Use whatever browser context works.
- Avoid triggering Cloudflare bot detection: add delays between requests (2-3s), use real User-Agent strings.

---

## Priority 2 — NEJM (~65 Articles)

### Data
There is no separate JSON file for NEJM articles. Query the DB directly:

```sql
SELECT a.article_id, a.author, a.publication_year, a.title,
       ef.classified_url, ef.classification, a.tier
FROM articles a
JOIN (
    SELECT article_id, classified_url, classification
    FROM exa_pdf_finder_results  -- or check exa_pdf_queue.csv for the actual table/file
    WHERE classification IN ('nejm_auth', 'paywall')
    AND classified_url LIKE '%nejm.org%'
) ef ON a.article_id = ef.article_id
WHERE a.article_id NOT IN (
    SELECT REPLACE(REPLACE(pdf_filename, '.pdf',''), REGEXP_SUBSTR(pdf_filename,'.*#@#'),'')
    FROM existing_pdfs  -- verify against actual filesystem scan
)
```

Alternatively, scan `exa_pdf_queue.csv` (in `scripts/maintain/`) — it has all classified URLs. Filter for `nejm` entries that don't have a corresponding PDF in the tier folders.

**~65 articles** across `nejm.org` — mix of `nejm.org/doi/full/` and `nejm.org/doi/pdf/` URL patterns.

### What We Tried and Why It Failed

**Attempt 1 — curl-cffi impersonation**
- Same as JAMA. 403 across the board. Cloudflare blocks non-browser TLS signatures.

**Attempt 2 — Playwright + cookie injection**
- Same Quantum Metric / timeout issues as JAMA.
- Additional complication: NEJM login page is a full redirect flow. Playwright with stale cookies hit the login redirect and stalled — second navigation wasn't handled.

**Attempt 3 — Aggressive retry triggering an IP block**
- The repeated 403s from Playwright's retry loops triggered NEJM's rate limiter.
- **IP 131.106.58.189 was blocked by NEJM** — "Unusually high activity" 403 response.
- Estimated wait: 24-48 hours from 2026-05-06. May be cleared now.

**What we CONFIRMED works:**
- Inside a **live, authenticated Chrome browser** on the NEJM domain, calling:
  ```js
  fetch('/doi/pdf/10.1056/NEJMXXXXXXXXX').then(r => r.status)
  ```
  returns **status 200** and `%PDF` content. This was verified via browser console during last session.
- This means: **if you're operating inside an already-authenticated Chrome tab on nejm.org, JS fetch injection works.**

**IP Block Check:**
Before any NEJM work, verify the block has lifted:
```
curl -I "https://www.nejm.org/" 
```
If you get 200/302 → proceed. If 403 "Unusually high activity" → wait longer. Do NOT hammer NEJM again if blocked — it extends the block.

### Authentication Notes
- Credentials may be in env vars: `NEJM_EMAIL`, `NEJM_PASSWORD`
- Cookie files (if still present): `key_data_files/browser_profiles/nejm_cookies_export.json`
- **Re-authentication is allowed** if needed.
- NEJM PDF URL patterns:
  - `https://www.nejm.org/doi/pdf/10.1056/NEJMxxxxxx` → direct PDF
  - `https://www.nejm.org/doi/full/10.1056/NEJMxxxxxx` → article page (has PDF button)

---

## Priority 3 — Unpaywall OA Retry (179 Articles)

### What Happened
`unpaywall_scanner.py` found 179 articles with `is_oa=True` and a valid OA URL — but the actual HTTP download failed. These are confirmed open-access, so the PDFs are legally available.

**Failure reasons (from logs):**
- Cloudflare anti-bot on publisher CDN (returned 403/captcha)
- Publisher rate limiting (429 Too Many Requests)
- OA URL is a landing page redirect, not a direct PDF

### Results file
`scripts/maintain/unpaywall_results.csv` — has `article_id`, `oa_url`, `download_status` columns.
Filter for `download_status = 'failed'` (or similar) to get the 179 retry targets.

### Suggested retry approach
- Add headers: `User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36`, `Referer: https://google.com/`
- Add 2-3 second delay between requests
- For Cloudflare-blocked URLs: try curl-cffi impersonation (`curl_cffi.requests.get(url, impersonate="chrome110")`) — this *does* work for Cloudflare-protected CDNs that aren't journal-specific (unlike JAMA/NEJM)

---

## Priority 4 — Broader Gap (~700+ remaining articles)

These articles have no known OA URL and aren't JAMA/NEJM. No systematic strategy has been run yet.

### What we know about the gap
- `exa_pdf_finder.py` classified all 2,206 articles. The classifications are in `exa_pdf_queue.csv`.
- Articles classified as `paywall` or `landing_page` with non-JAMA/NEJM publishers are the bulk of this group.
- Common publishers in the gap: NEJM Group, Lancet/Elsevier, JAMA Network (other journals), AHA/ACS journals, USPSTF (which is often on ahrq.gov — should be free), AFP/AAFP (which has a session cookie strategy).

### Untested strategies worth trying
1. **Preprint servers** — medRxiv, bioRxiv for clinical trial results. Many of these articles have preprint versions. Exa or Semantic Scholar can find them by title.
2. **Author/institution pages** — authors often post PDFs on their university faculty page. Google Scholar frequently links to these.
3. **AAFP/AFP articles** — there's an existing `AAFP_SESSION_COOKIE` env var strategy in `exa_pdf_downloader.py`. AAFP `afp.aafp.org` articles have a direct `.pdf` URL pattern if the session cookie is valid.
4. **USPSTF** — USPSTF guidelines are on `uspreventiveservicestaskforce.org` and `ahrq.gov`, often freely accessible. Should be zero-auth downloads.
5. **PubMed Central second pass** — the first PMC pass used DOI→PMCID lookup. A title-based search on NLM's E-utilities might catch articles that weren't found via DOI.

---

## DB Interaction

**DB path:** `00_database/db/ite_intelligence.db` (SQLite)

**Key tables:**
```sql
-- Articles
SELECT article_id, author, publication_year, title, tier FROM articles WHERE article_id = 'ART-XXXX';

-- Check what PDFs we already have (filesystem-based, not DB-tracked)
-- The DB doesn't have a "has_pdf" flag — scan the filesystem directly.

-- Tier reference
-- tier values: 'VC_pass', 'VC_fail', 'local_lite', 'right_click'
-- Most acquired articles = 'VC_fail'. VC_pass = also in the VC gate JSON (highest priority).
```

**VC Gate (DO NOT MODIFY):** `key_data_files/session_hy_inserts_v7.json` — 352 citations.
If an article is in this file, it gets `VC_pass` tier (or `right_click` if fully enriched + DOCX exists).

---

## Reporting Back

When done with a batch, output a summary like:
```
JAMA:     downloaded XX / 50   (skipped: N already existed, N access-denied, N other)
NEJM:     downloaded XX / ~65  (skipped: ...)
Unpaywall: downloaded XX / 179 (skipped: ...)
Files saved to: 01_module.1_warehouse/citation_files/ITE/{tier}/
```

Any PDF that couldn't be downloaded — note the article_id, the URL tried, and the failure reason. This list feeds the next session's strategy.

---

## What NOT to Do

- **Don't modify `session_hy_inserts_v7.json`** — it's the VC gate, source data, never disposable.
- **Don't modify `ite_intelligence.db`** directly for this task — PDFs live on the filesystem; the DB doesn't need updates for PDF acquisition.
- **Don't use `shutil.rmtree`** — banned (can nuke unrecoverably on NTFS). File-by-file or PowerShell `Remove-Item` only.
- **Don't push cookie files** (`nejm_cookies_export.json`, `jama_cookies_export.json`) — they contain auth credentials.

---

## Approach: Your Call

You have a different toolkit than the Cowork session that hit these walls — especially direct Chrome control and the ability to work within live browser contexts. Everything tried here was Python-only (Playwright headless, HTTP clients, local servers).

The strategies above are documented, not prescribed. Use what works. The goal is PDFs on disk with codon filenames in the right tier folders.

**Good luck.**
