# PDF Download Strategy for board_prep_intel

You are working on board_prep_intel, an ABFM ITE Intelligence System—a SQLite-backed knowledge base of 1,639 Family Medicine board exam questions linked to 1,998 clinical guideline articles.

Your task: Download academic journal article PDFs (JAMA and NEJM) for which the user is already authenticated in Chrome, rename them with a standardized filename format (codon naming), and organize them into tier folders.

## The Core Problem

The user needs to download ~50 JAMA articles and ~65 NEJM articles as PDFs. They are authenticated to both journals via Chrome (institutional access through St. Luke's Hospital-Bethlehem), but programmatic download methods (Python requests, curl, Playwright with cookies, XHR) all fail due to:

- **JAMA**: Quantum Metric analytics JS (`cdn.quantummetric.com/qscripts/quantum-ama.js`) intercepts and blocks all programmatic fetch() and XHR calls, even same-origin requests (status 0 / TypeError: Failed to fetch). Python-based approaches get 403 (Cloudflare).
- **NEJM**: Normal 403 blocks via Cloudflare. Additionally, the IP address 131.106.58.189 is currently rate-limited/blocked due to excessive failed attempts this session; will need to wait hours to days for the block to lift before attempting NEJM.

## What Has Been Tried (and failed)

1. **Python requests library** → 403 (Cloudflare protection)
2. **curl-cffi with Chrome TLS fingerprinting** → Still 403; cf_clearance cookie is tied to exact Chrome version fingerprint that Python cannot replicate
3. **Playwright headless/headful with injected auth cookies** → JAMA times out; NEJM gets stuck on most items
4. **Local HTTP server bridge (browser_pdf_harvester.py)** → Failed due to CORS blocking cross-origin fetch from localhost to jamanetwork.com
5. **JavaScript injection via Claude in Chrome** → fetch() and XHR within JAMA page context are blocked by Quantum Metric analytics. Works for NEJM (same-origin, no analytics blocker).

## Why the "Old School" Approach Should Work

The authenticated Chrome browser can navigate to pages and interact with them natively. The simplest path:
- Navigate to the article page in the user's authenticated Chrome session
- Find the PDF download link in the DOM
- **Click it** (don't fetch it programmatically)
- Chrome downloads the PDF to its default folder natively, bypassing Quantum Metric and Cloudflare

This works because:
- Chrome handles the navigation and download natively (no CORS issues)
- No programmatic fetch() is invoked—just a user-like click
- The authenticated session is already established and live
- Chrome's native download respects the auth cookies and session context
- Quantum Metric only blocks programmatic fetch/XHR, not native downloads

## Your Task

### Step 1: Understand the Input Data
- File: `C:\Users\mpsch\Desktop\board_prep_intel\01_module.1_warehouse\scripts\maintain\jama_pending.json`
- Each entry has: `article_id`, `tier`, `year`, `author`, `title`, `url`
- Example URL: `https://jamanetwork.com/journals/jama/article-abstract/2766169`
- PDF links are in the DOM as `a[href*="articlepdf"]` with full URL pattern: `https://jamanetwork.com/journals/jama/articlepdf/ARTICLE_ID/filename.pdf`

### Step 2: Download PDFs
Using Claude in Chrome (your browser automation tool):
1. For each article in jama_pending.json:
   - Navigate to the article URL
   - Wait for the page to load
   - Locate the PDF download link in the DOM
   - Click it to trigger Chrome's native download
   - Wait for the download to complete (monitor `C:\Users\mpsch\Downloads\`)

When the IP block on NEJM lifts: repeat the same process for NEJM articles (stored in a similar file once you create it).

### Step 3: Rename with Codon Format
Each downloaded PDF must be renamed to: `Author_Year#@#ART-XXXX@#@.pdf`

Example: `Armstrong_2020#@#ART-0089@#@.pdf`

Extract the values from the jama_pending.json entry:
- `Author` = first author's last name from the `author` field
- `Year` = the `year` value
- `ART-XXXX` = the `article_id` value (e.g., `ART-0089`)

### Step 4: Move to Tier Folders
Based on the `tier` value in jama_pending.json, move the renamed PDF to:
- **VC_pass tier**: `C:\Users\mpsch\Desktop\board_prep_intel\01_module.1_warehouse\citation_files\ITE\VC_pass\`
- **VC_fail tier**: `C:\Users\mpsch\Desktop\board_prep_intel\01_module.1_warehouse\citation_files\ITE\VC_fail\`
- **local_lite tier**: `C:\Users\mpsch\Desktop\board_prep_intel\01_module.1_warehouse\citation_files\ITE\local_lite\`
- **right_click tier**: `C:\Users\mpsch\Desktop\board_prep_intel\01_module.1_warehouse\citation_files\ITE\right_click\`

Chrome's default download folder: `C:\Users\mpsch\Downloads\`

## Constraints & Conventions

- **No re-authentication**: Use the user's existing, live Chrome session. Do not attempt to log in or extract cookies.
- **No new browser instances**: Work with the authenticated Chrome browser already open.
- **Script location**: Place any new Python helper script in `01_module.1_warehouse\scripts\maintain\` (e.g., `jama_pdf_downloader.py`)
- **Logging**: Log progress and errors to `jama_download.log` in the same scripts folder
- **No shutil.rmtree**: BANNED. Use explicit file operations if deleting anything.
- **Dynamic paths only**: Use `SCRIPT_DIR = Path(__file__).resolve().parent; PROJECT_ROOT = SCRIPT_DIR.parent.parent` for path resolution

## Success Criteria

- All 50 JAMA PDFs downloaded, renamed with codon format, and moved to correct tier folders
- Log file tracks which downloads succeeded and which failed (with reason)
- For NEJM: when the IP block lifts, the same automation should handle ~65 NEJM articles with minimal changes
- No manual intervention required beyond clicking through any browser security prompts

---

Proceed with the approach that works best given your available tools (Claude in Chrome, filesystem access, Python). You may need to handle per-article delays or retries if downloads are slow. The goal is to make this reliable and repeatable.
