---
name: exa-research-search
description: Search for research papers using Exa advanced search AND optionally download PDFs. Use when the user asks to find papers, search PubMed/arXiv, do a literature review, find guidelines, download papers, or says "search for papers on...", "find research about...", "literature search", "download PDFs for...", "get me the papers on...", or any request for academic/scientific sources. Also trigger for guideline searches relevant to the board_prep_intel project.
---

# Exa Research Paper Search + PDF Downloader

This skill uses `web_search_exa` with `category: "research paper"` to find
academic papers, then optionally downloads PDFs using the M1 download pipeline.

## Two Modes

| Mode | Trigger | What happens |
|------|---------|--------------|
| **Search only** | "find papers on...", "search for research about..." | Exa search → structured results |
| **Search + Download** | "download papers on...", "get PDFs for...", "find and download..." | Exa search → classify URLs → download PDFs with codon naming |

Default to **search only** unless the user explicitly asks for download.

## Tool Restriction (Critical)

ONLY use `web_search_exa` with `category: "research paper"` for the search phase.
Do NOT use other categories or other search tools for this skill.

## Token Isolation (Critical)

Never run Exa searches directly in the main conversation context. ALWAYS spawn
an Agent (subagent) to perform the search:

1. Agent calls `web_search_exa` with `category: "research paper"`
2. Agent merges and deduplicates results
3. Agent returns a distilled summary (structured markdown)
4. Main context stays clean regardless of search volume

Use `subagent_type: "general-purpose"` for the agent.

---

## Phase 1: Search (Both Modes)

### Full Parameter Reference

#### Core
- `query` (required) — the search terms
- `numResults` — number of results to return
- `type` — "auto", "fast", "deep", or "neural"

#### Domain filtering
- `includeDomains` — e.g., ["arxiv.org", "openreview.net", "pubmed.ncbi.nlm.nih.gov"]
- `excludeDomains`

#### Date filtering (ISO 8601)
- `startPublishedDate` / `endPublishedDate`
- `startCrawlDate` / `endCrawlDate`

#### Text filtering
- `includeText` — results must contain ALL terms
- `excludeText` — exclude if ANY term matches

**CRITICAL:** `includeText` and `excludeText` only support **single-item arrays**.
Multi-item arrays (2+ items) cause 400 errors. To match multiple terms, put them
in the `query` string or run separate agent searches.

#### Content extraction
- `textMaxCharacters` / `contextMaxCharacters`
- `enableSummary` / `summaryQuery`
- `enableHighlights` / `highlightsNumSentences` / `highlightsPerUrl` / `highlightsQuery`

#### Additional
- `userLocation`
- `moderation`
- `additionalQueries`
- `maxAgeHours` / `livecrawlTimeout`
- `subpages` / `subpageTarget`

### Agent Prompt Template (Search Phase)

When spawning the agent, use a prompt like:

```
Search for research papers using web_search_exa with these parameters:
- query: "<user's search terms>"
- category: "research paper"
- numResults: <10-20>
- type: "auto"
[include any date filters, domain filters, or text filters as needed]

Return results as a structured markdown list with:
1. Title
2. Authors (if available)
3. Date
4. Brief summary / key finding
5. URL

Deduplicate results. Note any conflicting findings across papers.
```

### Search Output Format

Present results to the user as:

1. **Results** — structured list with title, authors, date, abstract/summary, URL
2. **Sources** — URLs grouped by publication venue
3. **Notes** — methodology differences, conflicting findings, relevance to query

---

## Phase 2: Download (Search + Download Mode Only)

When the user wants PDFs downloaded, run this phase AFTER presenting search results
and getting user confirmation on which papers to download.

### Step-by-Step Workflow

```
Step 1: CLASSIFY — Apply URL classification to every result from Phase 1
Step 2: PRESENT — Show user a table of results with classifications and downloadability
Step 3: CONFIRM — Wait for user to approve (which papers, which destination)
Step 4: RESOLVE — Transform URLs to direct PDF download links
Step 5: DOWNLOAD — Spawn download agent (or run M1 pipeline for DB articles)
Step 6: REPORT — Present download results table + summary
```

### Step 1: URL Classification

Apply this classification cascade to each result URL (order matters — first match wins):

```
CLASSIFY(url):
  if url is empty/null              → "not_found"
  if url ends with ".pdf"           → "direct_pdf"

  # PMC check (3 patterns)
  if "pmc.ncbi.nlm.nih.gov/articles/PMC" in url  → "pmc_fulltext"
  if "ncbi.nlm.nih.gov/pmc/articles" in url       → "pmc_fulltext"
  if "europepmc.org/articles/PMC" in url           → "pmc_fulltext"

  # Open access check (14 domains)
  if any of these in url → "open_access":
    biomedcentral.com/articles, frontiersin.org, mdpi.com,
    plos (any subdomain), elifesciences.org, bmj.com/content,
    academic.oup.com, onlinelibrary.wiley.com/doi/full,
    aafp.org/pubs/afp, cdc.gov, who.int, cochranelibrary.com,
    ginasthma.org, uspreventiveservicestaskforce.org

  # Paywall check (11 domains)
  if any of these in url → "landing_page":
    jamanetwork.com, nejm.org, ahajournals.org,
    publications.aap.org, pediatrics.aappublications.org,
    acc.org/Latest, sciencedirect.com,
    link.springer.com/article, journals.lww.com,
    annals.org, thelancet.com

  # Default fallback
  → "landing_page"
```

Downloadable: `direct_pdf`, `pmc_fulltext`, `open_access`
Not downloadable: `landing_page`, `not_found`

### Step 2: Present Classification Table

Show the user a table like this BEFORE any downloads:

```markdown
| # | Title (Year) | Classification | Downloadable? | URL (truncated) |
|---|-------------|----------------|---------------|-----------------|
| 1 | Smith 2024 — Hypertension Guidelines | direct_pdf | YES | uspstf.org/...pdf |
| 2 | Jones 2023 — BP Management Review | pmc_fulltext | YES | pmc.ncbi.nlm.../PMC9876543 |
| 3 | Lee 2024 — Resistant HTN | open_access | YES | frontiersin.org/articles/... |
| 4 | Brown 2023 — Novel Antihypertensives | landing_page | NO (paywalled) | nejm.org/doi/... |

Summary: 3 downloadable, 1 paywalled
```

### Step 3: Confirm

Ask the user:
- "Download all 3 available papers?" (or let them pick specific ones)
- For **DB articles** (have ART-IDs): confirm tier for codon naming
- For **new papers** (no ART-IDs): downloads go to `04_module.4_sandbox/exa_downloads/`

### Step 4: Resolve Download URLs

Transform classified URLs into direct PDF download links:

**direct_pdf** — use URL as-is (already a .pdf link)

**pmc_fulltext** — extract PMC numeric ID via regex `PMC(\d+)`, then:
- Primary:  `https://pmc.ncbi.nlm.nih.gov/articles/PMC{id}/pdf/`
- Fallback: `https://europepmc.org/backend/ptpmcrender.fcgi?accid=PMC{id}&blobtype=pdf`

**open_access** — strategy depends on domain:
- **AAFP** (`aafp.org/pubs/afp/issues`): swap `.html` → `.pdf` at end of URL
  - Requires `AAFP_SESSION_COOKIE` env var for gated AFP content
- **Other OA sites** (BMC, Frontiers, MDPI, PLOS, etc.): attempt the URL directly
  - Many OA sites serve PDF from the article page URL with `/pdf` appended
  - Or try adding `.pdf` to the URL
  - If neither works, flag as "needs manual download"

### Step 5: Download

Two paths depending on whether papers are in the DB:

#### Path A: Existing DB Articles (have ART-IDs) — Use M1 Pipeline

If the user is filling gaps in the existing library, leverage the full M1 infrastructure:

```bash
# Step 5a: Run the finder to build/update the queue
python 01_module.1_warehouse/scripts/maintain/exa_pdf_finder.py --tier VC_pass --dry-run

# Step 5b: Review the queue
# (read exa_pdf_queue.csv to confirm what will be downloaded)

# Step 5c: Dry-run the downloader
python 01_module.1_warehouse/scripts/maintain/exa_pdf_downloader.py --dry-run

# Step 5d: Execute (after user confirms dry-run output)
python 01_module.1_warehouse/scripts/maintain/exa_pdf_downloader.py --classification direct_pdf
python 01_module.1_warehouse/scripts/maintain/exa_pdf_downloader.py --classification pmc_fulltext
python 01_module.1_warehouse/scripts/maintain/exa_pdf_downloader.py --classification open_access
```

M1 pipeline handles: codon filenames (`Author_Year#@#ART-XXXX@#@.pdf`), tier routing,
PMC/AAFP transforms, resume, rate limiting, results CSV logging.

#### Path B: New Papers (no ART-IDs) — Spawn Download Agent

For papers found via search that aren't in the DB yet, spawn a `general-purpose`
agent to download them to the staging folder.

**Download Agent Prompt Template:**

```
Download the following PDFs to the staging folder. For EACH paper, use Bash to run
a Python download script. Wait 2 seconds between downloads.

Destination folder: 04_module.4_sandbox/exa_downloads/
(Create it if it doesn't exist.)

Papers to download:
1. Title: "<title>"
   Author: "<author>"
   Year: <year>
   Classification: <direct_pdf|pmc_fulltext|open_access>
   URL: "<url>"
   Resolved PDF URL: "<resolved_url>"  (apply PMC/AAFP transform if needed)
   Filename: "<Author_Year_short_title>.pdf"

[repeat for each paper]

For EACH paper, run this Bash command (substituting values):

python -c "
import requests, sys, time
from pathlib import Path

url = '<RESOLVED_PDF_URL>'
fallback = '<FALLBACK_URL_OR_EMPTY>'
dest = Path('04_module.4_sandbox/exa_downloads/<FILENAME>')
dest.parent.mkdir(parents=True, exist_ok=True)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/pdf,application/octet-stream,*/*',
    'Accept-Language': 'en-US,en;q=0.9',
}
MAX_BYTES = 50 * 1024 * 1024
MIN_BYTES = 1024

def try_download(target_url):
    resp = requests.get(target_url, headers=HEADERS, timeout=30, stream=True, allow_redirects=True)
    if resp.status_code != 200:
        return False, f'HTTP {resp.status_code}'
    content_type = resp.headers.get('Content-Type', '').lower()
    first_chunk = next(resp.iter_content(chunk_size=8), b'')
    is_pdf = 'pdf' in content_type or 'octet-stream' in content_type or first_chunk.startswith(b'%PDF')
    if not is_pdf:
        return False, f'Not PDF (Content-Type: {content_type[:40]})'
    with open(dest, 'wb') as f:
        f.write(first_chunk)
        size = len(first_chunk)
        for chunk in resp.iter_content(8192):
            f.write(chunk)
            size += len(chunk)
            if size > MAX_BYTES:
                dest.unlink()
                return False, 'Too large (>50MB)'
    if size < MIN_BYTES:
        dest.unlink()
        return False, f'Too small ({size} bytes)'
    return True, f'OK ({size // 1024} KB)'

success, msg = try_download(url)
if not success and fallback:
    print(f'  Primary failed ({msg}), trying fallback...')
    success, msg = try_download(fallback)
if success:
    print(f'OK: {dest.name} — {msg}')
else:
    print(f'FAIL: {dest.name} — {msg}')
    if dest.exists():
        dest.unlink()
"

After ALL downloads, return a summary in this exact format:

DOWNLOAD RESULTS:
| # | Title | Filename | Status | Size |
|---|-------|----------|--------|------|
| 1 | ... | ... | OK (245 KB) | ... |
| 2 | ... | ... | FAIL (HTTP 403) | — |

SUMMARY: X/Y downloaded successfully. Z failed.
STAGING FOLDER: 04_module.4_sandbox/exa_downloads/
```

### Step 6: Report Results

After the download agent returns (or M1 pipeline completes), present to the user:

**Download Results:**

| Paper | Classification | Status | File | Size |
|-------|---------------|--------|------|------|
| Smith 2024 — HTN Guidelines | direct_pdf | OK | `Smith_2024_HTN_Guidelines.pdf` | 245 KB |
| Jones 2023 — BP Review | pmc_fulltext | OK | `Jones_2023_BP_Review.pdf` | 1.2 MB |
| Lee 2024 — Resistant HTN | open_access | FAIL (HTTP 403) | — | — |

**Summary:** 2/3 downloaded, 0 paywalled, 1 failed
**Location:** `04_module.4_sandbox/exa_downloads/` (or M1 tier folder for DB articles)

**Next steps** (suggest to user):
- For failed OA downloads: "Try accessing via institutional login"
- For paywalled papers: "These need manual download from [journal]"
- For new papers downloaded to staging: "Want me to register these in the DB and move to citation_files?"

### Safety Rules

1. **Always ask before downloading.** Present classified results first, let user confirm.
2. **Rate limit**: 2 seconds between downloads minimum.
3. **Never use `shutil.rmtree`** — project-wide ban (fix_ghost.py incident).
4. **Staging folder for non-DB papers**: `04_module.4_sandbox/exa_downloads/`
5. **Codon naming only for DB articles** with known ART-IDs. New papers use `Author_Year_ShortTitle.pdf`.
6. **Report paywalled papers** so user can manually download from institutional access.
7. **PDF validation**: Check for `%PDF` magic bytes at file start. Discard non-PDFs.
8. **Size bounds**: Skip files < 1 KB (error pages) or > 50 MB (not a paper).
9. **No silent overwrites**: If destination file exists, skip and report (don't overwrite).
10. **Agent isolation**: Download agent runs in a subagent to keep main context clean.

---

## When to Use

- Academic papers from arXiv, OpenReview, PubMed, etc.
- Clinical guidelines (USPSTF, AHA, ACOG, etc.)
- Scientific research on specific topics
- Literature reviews with date filtering
- Papers containing specific methodologies or terms
- Evidence searches for board prep content
- **Downloading PDFs** for papers found in search results
- **Building the PDF library** for articles missing physical PDFs

## Examples

### Search only — recent papers on a clinical topic:
```
web_search_exa({
  query: "hypertension management guidelines primary care",
  category: "research paper",
  startPublishedDate: "2024-01-01",
  numResults: 15,
  type: "auto"
})
```

### Search only — papers from specific venues:
```
web_search_exa({
  query: "diabetes screening USPSTF recommendation",
  category: "research paper",
  includeDomains: ["pubmed.ncbi.nlm.nih.gov", "jamanetwork.com"],
  includeText: ["screening"],
  numResults: 20,
  type: "deep"
})
```

### Search + Download — find and get PDFs for a topic:
```
User: "Find and download recent USPSTF guidelines on lung cancer screening"

1. Agent searches → returns 12 results
2. Classify URLs:
   - 3 direct_pdf (USPSTF site)
   - 4 pmc_fulltext
   - 2 open_access (AAFP)
   - 3 landing_page (JAMA, paywalled)
3. Present results + classifications to user
4. User confirms: "download the 9 available ones"
5. Download to staging folder
6. Report: 9 downloaded, 3 paywalled (manual needed)
```

### Batch download for existing DB articles:
```
User: "Run the PDF finder for VC_pass articles, then download what's available"

1. Run exa_pdf_finder.py --tier VC_pass via Bash
2. Review queue output
3. Run exa_pdf_downloader.py --tier VC_pass --dry-run
4. Present dry-run results to user
5. On confirmation, run without --dry-run
```
