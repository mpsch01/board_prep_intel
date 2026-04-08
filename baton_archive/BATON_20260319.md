# BATON — ITE Intelligence System Overhaul Planning
**Date:** March 19, 2026 (Updated — Session 2)**
**Previous BATON:** `BATON_active_20260318_session2.md` (ITE Score Pipeline v2.1 — 3-Tier Cascade + Full Shell)
**Status:** ARCHITECTURAL PIVOT. PDF library download pipeline completed. Deep audit of the codon/VC linkage system revealed the data architecture was built on an incorrect framework. A dedicated overhaul session is being initiated. NO pipeline files should be modified until the overhaul plan is finalized and reviewed.

---

## CRITICAL CONTEXT: What Changed This Session

This session began as a continuation of the PDF download + pipeline processing work but escalated into a full architectural review. The discoveries below fundamentally change the direction of the project. **Read this section before touching anything.**

### The Incorrect Assumption (Now Corrected)
Previous sessions treated **"codon = matched to ite_intelligence.db"** — i.e., any PDF that could be linked to an ART-ID in the database got a codon filename.

**The correct definition, confirmed by Mikey:**
> "Codon = references whose linked questions are **contained within the AAFP Board Prep Video Course Outline**. Non-codon = all refs and Q&A pairs originally derived from 2020-2025 data that do NOT appear as selected questions in the AAFP VC outline."

The Video Course Outline is a **curated subset** of the full 1,189-question ITE exam bank. Not all ITE-linked articles belong in the codon tier. Only articles cited by questions specifically selected for the 48 VC sessions qualify.

### What This Means for the Current Library
The current codon library (146 PDFs) was built against the wrong filter. Analysis against the actual VC session data (`session_hy_inserts_v7.json`) reveals:

| Group | Count | Correct Tier |
|---|---|---|
| Current codon files that ARE VC-cited | 59 | `$right_click$` ✓ correct |
| Current codon files that are NOT VC-cited | 87 | Should be `local_lite` — misclassified |
| VC-cited articles with NO PDF yet | 266 | `$right_click$` — need PDFs sourced |
| Non-VC ITE-linked articles with PDFs (non-codon folder) | ~169 | `local_lite` or uncategorized |

**87 of the 146 current codon files are misclassified** — they are ITE question-linked but not VC-selected. Under the correct framework, they belong in the `local_lite` tier, not the expensive `$right_click$` pipeline.

---

## The Two-Tier Pipeline Architecture (Decision Locked)

### Tier 1: `$right_click$` (Dense Path)
- **Target:** VC-cited articles only (articles whose linked questions appear in the AAFP VC session outline)
- **Processing:** Full extraction via Claude API (multiple API calls per PDF), synthesis, rich contextual DOCX with ITE Intelligence callouts
- **Output:** ~352 DOCX summary documents with full green ITE Intelligence blocks, linked to specific VC sessions and questions
- **Cost:** High (API calls per document) — reserved for highest-yield content
- **Current status:** 59 already processed. 266 still need PDFs sourced, then processing.

### Tier 2: `local_lite` (Local Path)
- **Target:** All ITE-linked articles NOT in the VC outline (~1,138 articles in DB)
- **Processing:** DB-only synthesis — no API calls. Uses existing data in `ite_intelligence.db` (concept tags, citation info, linked question stems, ICD-10 tags, tier classifications)
- **Output:** ~1,138 leaner DOCX documents with DB-sourced context blocks, full ITE question linkage data, but no expensive extraction
- **Cost:** Near-zero (local only)
- **Current status:** Not yet built. Pipeline to be designed in overhaul session.

---

## The ART-ID Rename Proposal (NOT YET IMPLEMENTED — Pending Planning)

### Current Format
```
ART-XXXX  (e.g., ART-0040, ART-1397)
```
All 1,397 articles use the same flat format. No tier signal. No sort order that reflects clinical priority.

### Proposed Format
```
nnn_XXXX
```
Where:
- `001_XXXX` through `352_XXXX` = VC-cited articles (`$right_click$` tier). The `nnn` prefix = sequential 001–352, reflecting position/priority within the VC article set
- `000_XXXX` = non-VC ITE articles (`local_lite` tier)

### Why This Matters
1. **Instant visual identification** — glance at any filename or DB field and know the tier
2. **Auto-sort** — VC articles always sort together, non-VC articles sort together
3. **Scalable** — VC is capped (~352 unique citations), non-VC is the long tail
4. **Pipeline routing** — scripts can branch on prefix without DB lookup

### Migration Scope (Why This Needs Dedicated Planning)
This rename touches EVERYTHING:
- `ite_intelligence.db` → `articles.article_id` field for all 1,397 rows
- `ite_intelligence.db` → `articles.codon_filename` field for all 1,397 rows
- `ite_intelligence.db` → `qid_art_xref.article_id` for all 1,818 rows
- `ite_intelligence.db` → `question_ref_pairs.clean_ref` linkages
- All 220 codon PDF filenames in `pdf_codon/`
- All 218+ enriched JSON files in `03_enriched_JSON/`
- All 191+ DOCX files in `02_docx_guideline_library/`
- `crosswalk_index.json` (146 entries)
- `manual_overrides.json`
- All pipeline scripts that reference ART-IDs

**DO NOT implement this until a full migration plan with rollback strategy is written and reviewed.**

---

## VC Article Set — True Numbers

### Source of Truth
File: `C:\Users\mpsch\Desktop\claude_knowledge\abfm_prep\04_aafp_integration\02_working\session_hy_inserts_v7.json`

This file contains 48 sessions, each with:
- `questions[]` — 5 QIDs per session (229 total across all sessions)
- `refs[]` — citation strings for all articles referenced by those questions, with tier classification and `cited_by` QID list

### Key Counts
| Metric | Count |
|---|---|
| VC sessions | 48 |
| VC QIDs (unique) | 229 |
| Unique citation strings in VC refs | 352 |
| Citations matched to DB articles (`clean_ref` comparison) | 325 |
| Citations NOT in DB (unmatched strings) | 27 |
| VC-matched DB articles that have PDFs (in crosswalk) | 59 |
| VC-matched DB articles with NO PDF | 266 |

### Tier Breakdown of VC Citations
- Must-Read: 9
- Core: 166
- Supplementary: 154
- Unmatched (citation string unparseable): 23

### Important: QID Format Mismatch
The VC JSON uses **original AAFP exam bank numbering**: `Q2021-291`, `Q2023-799`, etc.
The DB uses **internal sequential numbering**: `QID-2021-0291`, `QID-2020-0001`, etc.

These are NOT the same numbering system. The DB has ~200 questions per year (it holds a curated subset of the full exam bank). The VC QIDs reference the full bank (numbers can exceed 800/year).

**Normalization attempt** (`Q{YEAR}-{NUM}` → `QID-{YEAR}-{NUM:04d}`) only resolves **75 of 229** VC QIDs in the DB. The other 154 cannot be matched this way.

**Correct approach for VC linkage:** Use `refs[].citation` strings from the session JSON, not QID matching. Citation strings can be matched to `articles.clean_ref` in the DB. This is how the 325 matches above were found.

---

## Current PDF Library State

### Folder Structure
```
clinical_guidelines/01_pdf_guideline_library/
├── pdf_codon/        ← 220 files (codon-named)
├── pdf_non-codon/    ← 169 files (unnamed/unmatched)
├── README.json
└── README.md
```

### pdf_codon/ (220 files)
- 146 originally from the codon migration (March 15, 2026)
- 74 additional PDFs downloaded via `aafp_fill_gaps.py` that were matched to DB at download time
- All have `Author_Year#@#ART-XXXX@#@.pdf` codon naming
- Of these 220, only **59 are confirmed VC-cited** (true `$right_click$` tier)
- **87 are ITE-linked but not VC-cited** (misclassified — should be `local_lite`)
- Remaining ~74 status unclear pending full VC audit

### pdf_non-codon/ (169 files)
All 169 files have been scanned. Breakdown:

| Subcategory | Count | Description |
|---|---|---|
| Omitted from migration | 41 | Supplementary/algorithm/non-ITE files. Stay as-is. |
| AFP top articles (new, not in DB) | ~86 | 2022–2025 articles not yet in ite_intelligence.db. Need DB records. |
| AFP top articles (in DB, not VC-cited) | ~14 | ITE-linked but not VC-selected. `local_lite` tier. |
| Org-prefix specialty guidelines | ~28 | IDSA_, AJKD_, aafp_, acg_, afp_, jacc_, peds_, pulm_ prefixed files. Not in ITE DB. Reference only. |

**The 41 omitted files** (permanent list):
APA_, neuro_, rheum_, tox_, uspstf_, acog_, endo_, periop_, VA_, Vaccine, BackPain, ADA injectible algo, 2024 ADA Injectable Algorithm

**The ~86 genuinely new AFP articles** (2022–2025, not in DB yet) include:
Silver_2024, Partin_2024, Snyder_2024, Nohria_2024, Matheson_2024, Dabbs_2024, Maharty_2024, Clarke_2023, Chang_2023, Raymond_2023, Frazier_2023, Ramírez_2023, Weaver-Agostoni_2023, Savard_2023, Miller_2023, Creech-Organ_2023, Smith_2023, Garner_2023, Powers_2023, Shen-Wagner_2023, Hitzeman_2022, Sur_2022, Newman_2022, Herness_2022, Randall_2022, David_2022, DeGeorge_2022, Gaddey_2022, Bryce_2022, Viera_2022, plus 50+ others from 2022–2025.

---

## Download Pipeline — Completed State

### What Was Completed
- `aafp_fill_gaps.py` successfully completed downloading the AAFP Top 20 article list
- `_download_log.json` has **174 entries** (downloaded articles)
  - 76 entries with `art_id` set (matched to DB at download time → saved to `pdf_codon/`)
  - 98 entries with `art_id: null` (no DB match at download time → saved to `pdf_non-codon/`)
- All 174 downloaded files confirmed present in library (verified via case-insensitive scan)

### ALL-CAPS Filename Issue (Resolved)
15 files from 2017 era had ALL-CAPS author names from AAFP metadata bug. 8 were in `pdf_codon/`, 7 in `pdf_non-codon/`. These were renamed via PowerShell. Org-prefixed files (ADA_, APA_, IDSA_, etc.) were intentionally left as-is.

### Playwright Auth Fix (Resolved)
2024–2025 AFP articles required authentication. Full browser-native download via Playwright with manual login flow was implemented in `aafp_retry_playwright.py`. Two key bugs fixed:
1. `'BrowserContext' object has no attribute 'expect_download'` → use `page2 = context.new_page()` then `with page2.expect_download()`
2. Navigation interrupted error → remove post-login verification `page.goto()`, replace with `time.sleep(2)`

---

## Script Modifications Made This Session

### `build_match_staging.py`
Location: `C:\Users\mpsch\Desktop\claude_knowledge\abfm_prep\02_ite_intelligence\scripts\`

**Changes:**
1. `PDF_DIR` changed from `01_pdf_guideline_library` → `01_pdf_guideline_library/pdf_non-codon` (scopes to non-codon only)
2. PDF scan changed from `os.listdir(PDF_DIR)` (reverted from `rglob` after first fix) — correct for flat folder

**Why:** Staging script was scanning the top-level directory and finding 0 PDFs (all PDFs are in subdirs). Also, scanning both `pdf_codon/` and `pdf_non-codon/` was causing mismatches — codon files were being re-matched by keyword and sometimes assigned wrong ART-IDs. Scoping to `pdf_non-codon/` only is correct.

**Current limitation:** The staging script has no codon-parsing strategy (no ability to read `#@#ART-XXXX@#@` from filenames). For non-codon files it uses Tier 3 (filename keyword matching only), which matched 0 of 128 active non-codon files successfully. This script is not useful for the non-codon population under the current architecture.

### `rename_to_codon.py`
Location: `C:\Users\mpsch\Desktop\claude_knowledge\abfm_prep\02_ite_intelligence\scripts\`

**Changes:**
1. `PDF_DIR` changed from `01_pdf_guideline_library` → `01_pdf_guideline_library/pdf_non-codon`

**Why:** Matching change to `build_match_staging.py`. This script reads the staging report and executes renames. It should only operate on the non-codon folder.

**IMPORTANT:** Neither script should be run until the overhaul plan is finalized. The rename_to_codon.py `--execute` flag was NOT run this session. No PDFs were renamed.

---

## Open Flags

### Carried Forward from Previous Sessions
- **FLAG 1:** ITE Enrichment Quality Dimension (deferred)
- **FLAG 13 Layer 2:** PubMed Currency (not started)
- **FLAG 15:** User still needs to run `node build_merged_docx.js --merged-only` (139 → 145 DOCXs). Still pending.
- **FLAG 27:** Report Builder v2 requires `npm install docx` in working directory
- **FLAG 28:** v1 HTML report incompatible with v2 question format (graceful fail, low priority)
- **FLAG 29:** Hardcoded `year = 2025` in subcategory_decomposition and plugin_concept_fingerprint
- **FLAG 30:** `scholl_204999_ITE_SCORE` PDFs are encrypted — need unencrypted versions

### New Flags from This Session
- **FLAG 31 [CRITICAL]:** 87 current codon PDFs are misclassified — ITE-linked but not VC-cited. Must be re-tiered as `local_lite` once overhaul plan is executed.
- **FLAG 32 [CRITICAL]:** 266 VC-cited articles have no PDF. These are the highest-priority `$right_click$` sourcing targets.
- **FLAG 33 [CRITICAL]:** ART-ID rename (`nnn_XXXX`) not yet implemented. All downstream systems still use `ART-XXXX` format. DO NOT mix naming conventions until migration is planned.
- **FLAG 34:** 27 VC citation strings have no DB match. These citations appear in session_hy_inserts_v7.json `refs[]` but could not be matched to `articles.clean_ref`. Need manual resolution.
- **FLAG 35:** QID format mismatch — VC JSON uses `Q{YEAR}-{NUM}`, DB uses `QID-{YEAR}-{NUM:04d}`. Only 75/229 VC QIDs resolve via normalization. Full cross-reference must go through citation strings, not QIDs.
- **FLAG 36:** ~86 new AFP articles (2022–2025) in `pdf_non-codon/` are not in the DB. These need new records added to `ite_intelligence.db` before they can be codon-named or processed.
- **FLAG 37:** `who_infant_feeding.pdf` in `pdf_non-codon/` falsely matched to ART-1320 (Weinfield obesity article) by the staging script. This match is wrong and should be rejected. The file needs manual classification.

---

## Architecture Overhaul — Planning Agenda for New Session

The new dedicated project session should address the following in order:

### Phase 1: Define Canonical Article Sets
1. **Confirm VC article list** — Run comprehensive clean_ref matching against all 352 VC citations to get the authoritative VC article list. Resolve the 27 unmatched citations manually.
2. **Confirm VC QID linkage** — Establish whether QID normalization can be improved or if citation-string is the permanent bridge.
3. **Define `local_lite` set** — All DB articles NOT in the VC set = `local_lite` candidates (~1,138 articles).

### Phase 2: Design the New ID System
1. **Finalize `nnn_XXXX` scheme** — Confirm the 001–352 prefix ceiling. Determine what `nnn` represents (sequential position? session order? priority score?).
2. **Design the mapping table** — Old ART-ID → New ID mapping for all 1,397 articles. This becomes the migration manifest.
3. **Plan rollback strategy** — The old ART-IDs must be preserved as an alias or backup field until all downstream files are confirmed migrated.

### Phase 3: Plan Two-Tier Pipeline Architecture
1. **`$right_click$` pipeline spec** — Define exact processing steps for VC articles. How does DB-guided extraction v2 differ from the original? What API calls are made? What does the DOCX template look like?
2. **`local_lite` pipeline spec** — Design the DB-only synthesis path. What fields from `ite_intelligence.db` are used? What does the leaner DOCX look like? What can be auto-generated without API calls?
3. **Routing logic** — How does a script determine which pipeline a PDF goes through? (Based on prefix after rename, or based on crosswalk lookup?)

### Phase 4: Plan the Migration
1. **DB migration script** — Renumber all ART-IDs, update codon_filename column, update qid_art_xref, preserve old IDs in new `legacy_article_id` column.
2. **File migration script** — Rename all 220 codon PDFs to new scheme. Move 87 misclassified codon PDFs to `pdf_non-codon/`.
3. **JSON migration script** — Update all 218+ enriched JSONs with new article IDs.
4. **DOCX catalog** — Log all existing DOCXs before migration so nothing is lost.
5. **Crosswalk rebuild** — `build_crosswalk_index.py` will need to be re-run after migration to regenerate `crosswalk_index.json`.

### Phase 5: Source Missing PDFs
1. **266 VC articles with no PDF** — These are the priority sourcing targets. Build a sourcing list with author, year, title, DOI for each.
2. **PDF sourcing strategy** — PubMed, AFP website, direct journal access. Likely requires manual sourcing for most.

---

## Key File Locations (All Confirmed Current)

### Database
```
C:\Users\mpsch\Desktop\claude_knowledge\abfm_prep\02_ite_intelligence\db\ite_intelligence.db
  └── articles (1,397 rows) — article_id, title, author1, year, tier, citation_count, codon_filename, clean_ref
  └── questions (1,189 rows) — qid, stem, explanation, body_system, blueprint, concept_tags
  └── qid_art_xref (1,818 rows) — qid, article_id, tier, exam_year [pre-filtered to confident matches]
  └── question_ref_pairs (2,069 rows) — qid, clean_ref, match_status [full match metadata]
```

### VC Integration Data
```
C:\Users\mpsch\Desktop\claude_knowledge\abfm_prep\04_aafp_integration\
  ├── 01_source\outlines\BoardPrep-ContentOutline_SESSION-MAPPED-v2.docx  ← VC outline source
  └── 02_working\session_hy_inserts_v7.json  ← CANONICAL VC DATA (48 sessions, 229 QIDs, 352 article refs)
```

### PDF Library
```
C:\Users\mpsch\Desktop\claude_knowledge\clinical_guidelines\01_pdf_guideline_library\
  ├── pdf_codon\          ← 220 PDFs (codon-named, Author_Year#@#ART-XXXX@#@.pdf)
  └── pdf_non-codon\      ← 169 PDFs (unmatched/unprocessed)
```

### Pipeline Scripts (02_ite_intelligence)
```
C:\Users\mpsch\Desktop\claude_knowledge\abfm_prep\02_ite_intelligence\scripts\
  ├── build_match_staging.py    ← MODIFIED: PDF_DIR now points to pdf_non-codon/ only
  ├── rename_to_codon.py        ← MODIFIED: PDF_DIR now points to pdf_non-codon/ only
  ├── ite_intelligence_enricher.py  ← v4, codon-first (Strategy 0 → Strategy 1 → no_match)
  └── build_crosswalk_index.py  ← rebuilds crosswalk_index.json from codon folder
```

### Supporting Files (02_ite_intelligence root)
```
C:\Users\mpsch\Desktop\claude_knowledge\abfm_prep\02_ite_intelligence\
  ├── crosswalk_index.json    ← 146 entries (codon PDFs → ART-IDs → QIDs/tiers)
  ├── crosswalk_report.txt    ← human-readable crosswalk summary
  ├── manual_overrides.json   ← 14 manual matches, 41 omitted, 2 duplicate pairs
  └── logs\
       ├── match_staging_report.json  ← last run: 169 non-codon files, 1 match (false), 127 unmatched
       └── match_staging_report.txt   ← human-readable version
```

### Download Infrastructure (clinical_guidelines/05_scripts)
```
C:\Users\mpsch\Desktop\claude_knowledge\clinical_guidelines\05_scripts\
  ├── aafp_fill_gaps.py         ← gap-filler: scrapes AAFP top 20, checks library, downloads missing
  ├── aafp_retry_playwright.py  ← auth-required download for 2024-2025 articles (33 files)
  └── _download_log.json        ← 174 entries: {filename, art_id (nullable), title}
```

### Extracted + Enriched Content
```
C:\Users\mpsch\Desktop\claude_knowledge\clinical_guidelines\
  ├── 02_docx_guideline_library\    ← 191+ DOCXs (codon articles processed to date)
  └── 03_enriched_JSON\             ← 218+ *_extracted.json files
```

---

## Codon Filename Convention (Unchanged Until Migration)
```
Author_Year#@#ART-XXXX@#@.pdf
  Start codon: #@#
  Stop codon:  @#@
  ART-ID:      embedded between start and stop codons
  Example:     Gaitonde_Moore_2019#@#ART-0470@#@.pdf
```
Do NOT change this convention until the migration plan is fully designed and approved.

---

## ITE Score Analysis Pipeline — Carry-Forward Status
*(Separate workstream — not affected by the guideline library overhaul)*

The ITE Score Analysis pipeline (analyzer v2, report builder v2) is production-ready as of BATON_20260318_session2. Both Hopkins and Sarkar validated end-to-end. Pending items:
- FLAG 29: Dynamic exam year in subcategory decomposition
- FLAG 30: Scholl encrypted PDFs
- Directory reorganization to `08_ite_score_analysis/` (proposed, not executed)
- Plugin P2 (Explanation Mining) — Claude API batch command for user to run

---

## Design Principles for the Overhaul (Locked)

These were agreed in-session and should guide all planning:

1. **The VC outline is the primary gate.** An article's presence in `session_hy_inserts_v7.json refs[]` is the ONLY criterion for `$right_click$` tier. DB membership alone is not sufficient.
2. **The ART-ID must carry tier information.** The `nnn_XXXX` scheme ensures any system (human or machine) can determine tier from the ID alone without a DB lookup.
3. **Fix the data, not the code.** The misclassification problem is a data problem. The solution is re-sorting the articles into their correct tiers — not building routing logic to compensate for bad tier assignments.
4. **No files moved or renamed until the full migration plan is written and tested on a copy.**
5. **`local_lite` pipeline is a genuine product**, not a consolation path. ~1,138 articles × DB-generated DOCXs = the most comprehensive family medicine board prep reference set ever assembled. That's the vision.

---

## Direct Quote (Mikey, March 19, 2026)
*"we are going to come out on the other side with the cleanest, sharpest, fastest, and most capable data set for this material in the entire world (literally LOL)"*

That's the north star. Plan accordingly.

---

## SESSION 2 ADDITIONS — March 19, 2026 (same day)

### What Happened This Session
This session was entirely focused on building and refining the **Master Pipeline Map** (`PIPELINE_MAP.html`). No pipeline scripts were modified. No files were renamed. This was a documentation and architectural audit session.

---

### PIPELINE_MAP.html — Final State

**File location:** `C:\Users\mpsch\Desktop\claude_knowledge\abfm_prep\PIPELINE_MAP.html`
**Size:** ~84KB · Open in Chrome or Edge for full interactive render.
**Email draft:** Sent to project contact email (draft ID: r4910036009322679137) with summary + file path.

**Final structure — 7 modules:**

| Module | Name | Status |
|---|---|---|
| ⓪ | ITE Question Bank — Foundation Build | Re-run Annually |
| Ⓕ | AAFP VC Outline — Content Generation Pipeline | Production |
| Ⓐ | Guideline PDF Acquisition | Active |
| Ⓑ | Match Staging · VC Routing Gate · Codon Rename | Overhaul Pending |
| Ⓒ | Guideline Extraction → Enrichment → DOCX | $right_click$ Active / local_lite Planned |
| Ⓓ | Database Intelligence Layers | Layers 1–2 Active / Layers 3–4 Planned |
| Ⓔ | ITE Score Analysis — Resident Reports | Production Ready |

Map includes: verified file paths on every node, BAT orchestrator node type, VC routing gate node, human gate node, canonical reference file node type (gold border), complete 26-row script reference table with actual paths.

---

### Key Discoveries from Architectural Audit

#### 1. $right_click$ is LITERALLY a Windows context menu
`01_guideline_extractor\oneclick\` contains:
- `install_context_menu.reg` — installs Windows right-click context menu entry on PDF files
- `extract_guideline.bat` — fires when user right-clicks a guideline PDF

`extract_guideline.bat` orchestrates the full pipeline in sequence:
```
main.py → synthesize.js → ite_intelligence_enricher.py → build_crosswalk_index.py → build_summary.js
```
All in one click. No command line required. This is the primary processing method for single files.

**Implication:** `build_crosswalk_index.py` runs on EVERY right-click, not just after bulk renames. It belongs conceptually between Module B and Module C, not in Module D as an intelligence layer.

#### 2. Script paths were wrong in previous map versions
Correct paths (now locked in PIPELINE_MAP.html):

| Script | Correct Location |
|---|---|
| `main.py` | `01_guideline_extractor\` |
| `synthesize.js` | `01_guideline_extractor\oneclick\` |
| `build_summary.js` | `01_guideline_extractor\oneclick\` |
| `extract_guideline.bat` | `01_guideline_extractor\oneclick\` |
| `install_context_menu.reg` | `01_guideline_extractor\oneclick\` |
| `batch_db_extract.py` | `02_ite_intelligence\scripts\` |
| `ite_intelligence_enricher.py` | `02_ite_intelligence\scripts\` |
| `db_guided_extractor.py` | `02_ite_intelligence\scripts\` |
| `build_merged_docx.js` | `02_ite_intelligence\scripts\docx_build\` |
| `build_db_docx.js` | `02_ite_intelligence\scripts\docx_build\` |
| `ite_analyze_v2.py` | `08_ite_score_analysis\pipeline\` |
| `ite_parser.py` | `08_ite_score_analysis\pipeline\` |
| `ite_analyzer_v2.py` | `08_ite_score_analysis\pipeline\` |
| `ite_report_builder_v2.js` | `08_ite_score_analysis\pipeline\` |

**⚠ UNCONFIRMED:** `aafp_fill_gaps.py`, `aafp_retry_playwright.py`, `aafp_cleanup_filenames.py` — did NOT appear in VM filesystem scan. Previously believed to be in `clinical_guidelines\05_scripts\` but this folder appeared empty in scan. Confirm actual location on-machine before next session references these scripts.

#### 3. Three distinct extraction strategies exist in Module C
Previously the map showed only two (main.py and batch_db_extract.py). There is a third:

| Strategy | Script | Location | Design |
|---|---|---|---|
| Single-file CLI | `main.py` | `01_guideline_extractor\` | Standard. One API call per PDF. |
| Bulk async | `batch_db_extract.py` | `02_ite_intelligence\scripts\` | Batch API, 50% cheaper, async. |
| DB-guided | `db_guided_extractor.py` | `02_ite_intelligence\scripts\` | "Flashlight." DB clue package assembled first (concept_tags, question stems, thresholds), then ONE focused Claude call: raw text + clues → extraction + synthesis combined. Different philosophy — DB guides what Claude looks for. |

#### 4. compute_embeddings.py uses OpenAI API (not Claude)
- **Cost:** ~$0.006 for full corpus (1,397 articles + 1,189 questions)
- **Runtime:** ~30 seconds
- **Output:** sqlite-vec virtual tables `article_vec` and `question_vec` in `ite_intelligence.db`
- **Purpose:** Semantic similarity search — "find articles similar to this question"
- **Requires:** `pip install sqlite-vec openai` and `OPENAI_API_KEY` env var
- **Validated by:** `validate_vector_search.py` (run after embeddings compute)
- This is Intelligence Layer 2 — was entirely missing from all previous map versions.

#### 5. Module F (AAFP VC Content Generation) was entirely absent
The `04_aafp_integration\` pipeline had NO representation in the map. It is now Module Ⓕ. Full pipeline:

```
01_build_crosswalk.py → session_cluster_crosswalk.csv (human review)
  ↓
02b_generate_hy_inserts_v2.py → session_hy_inserts_v7.json ⭐ (THE VC GATE)
  ↓
03_inject_into_outline_v3.py → HY-ENRICHED-v4.docx
  ↓
04_inject_poll_questions.py (adds poll blocks)
07_inject_supplements_v2.py (adds supplement questions)
08_build_supplement_doc.py → ABFM_BoardPrep_Supplement_ITE-Questions_v1.docx
09_build_pearl_callouts.py → ABFM_BoardPrep_ContentOutline_HY-Enriched_v5-pearls.docx ⭐
```

Terminal outputs go to: `C:\Users\mpsch\Desktop\claude_knowledge\00_canonical\01_curriculum\`

**Critical clarification:** `session_hy_inserts_v7.json` is not just a reference file — it is the **output** of `02b_generate_hy_inserts_v2.py`. It is simultaneously:
- The terminal output of Module Ⓕ
- The VC routing gate input to Module Ⓑ (determines $right_click$ vs local_lite)

#### 6. DOCX builder ecosystem is larger than previously mapped
Three builders exist in Module C:

| Script | Location | Role |
|---|---|---|
| `build_summary.js` | `01_guideline_extractor\oneclick\` | Standard enriched DOCX. Part of right-click pipeline. |
| `build_merged_docx.js` | `02_ite_intelligence\scripts\docx_build\` | Merges API-synthesized clinical content + DB intelligence. For codon files with enriched JSONs. Falls back to DB-only. FLAG 15 pending. |
| `build_db_docx.js` | `02_ite_intelligence\scripts\docx_build\` | DB-only DOCX. Used as fallback inside build_merged_docx.js. |

#### 7. Architectural issues identified (for next planning session)
1. **`build_crosswalk_index.py` is in the wrong module** — it's an index utility called by the right-click bat, not an intelligence layer. Architecturally belongs between B and C.
2. **`local_lite` buried in Module C is misleading** — will eventually be the larger pipeline (~1,138 vs ~352 articles). Deserves its own module once built.
3. **Module D conflates two different trigger patterns** — index maintenance (run-after-rename) vs. intelligence enrichment (run-once-per-build). Different cadences.
4. **Duplicate ITE script copies** — ITE score scripts exist in BOTH `08_ite_score_analysis\pipeline\` AND in the `abfm_prep\` root directory. Root copies are likely stale/shortcuts. The `pipeline\` folder is canonical.

---

### session_hy_inserts_v7.json — Structure Confirmed
Mikey uploaded the file directly this session. Structure verified:
```json
{
  "02": {
    "session_id": "02",
    "session_title": "Peripheral Vascular Disease",
    "question_count": 5,
    "questions": [
      {
        "qid": "Q2021-291",
        "year": 2021,
        "focus": "AAA screening recommendations...",
        "stem_preview": "...",
        "kw_score": 3.517,
        "kw_hits": 6
      }
    ],
    "refs": [
      {
        "citation": "Final Recommendation Statement: Abdominal Aortic...",
        "tier": "Must-Read",
        "match_score": 1.0,
        "cited_by": ["Q2021-291"]
      }
    ]
  }
}
```
48 sessions keyed by session_id ("02"–"48"). 229 QIDs. 352 unique citation strings. This is the canonical VC gate.

---

### Next Session Intent
Mikey's exact words: *"then we can really look at it and figure out what we should do to make this thing really hum."*

This signals the **overhaul planning session** is next. The map is the shared artifact for that conversation. Starting point: open PIPELINE_MAP.html, look at the full picture, and start designing what changes would most improve throughput and data integrity.

Priority questions for that session:
1. Should `build_crosswalk_index.py` move to the end of Module B or be called explicitly from Module C setup?
2. Should `local_lite` become its own module (Ⓖ) now, before it's built?
3. What does the overhaul phase sequencing look like? (Phases 1–5 already documented above under Architecture Overhaul section)
4. What's the sourcing plan for the 266 missing VC PDFs?
5. Confirm actual location of `aafp_*.py` download scripts on-machine.

---

### Open Flags — Updated
All flags from Session 1 carried forward. No new flags added this session (audit/documentation only).

**Still most critical:**
- FLAG 15: Run `node build_merged_docx.js --merged-only` (still pending)
- FLAG 31: 87 codon PDFs misclassified — need re-tiering
- FLAG 32: 266 VC articles have no PDF
- FLAG 33: ART-ID rename not implemented
- FLAG 34: 27 VC citation strings unmatched in DB
- FLAG 36: ~86 new AFP articles not in DB
