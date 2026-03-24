# BATON — Major Cleanup + Redundancy Elimination Complete
## Session Handoff Document
**Date:** 2026-03-14
**Phase:** Repository-wide audit, redundancy elimination, README overhaul. Crosswalk index is next.
**Status:** All stale artifacts archived offsite. READMEs rewritten to match current reality. Ready for crosswalk build.

---

## WHAT WAS DONE THIS SESSION (2026-03-14)

### 1. Batch vs Enriched JSON Comparison
- Compared `01_guideline_extractor/outputs/` batch folders with `clinical_guidelines/03_enriched JSON/`
- Finding: batch outputs are **earlier, inferior versions** — same schema minus `ite_intelligence` key
- Enriched versions consistently larger (e.g., jacc_HTN: 66K enriched vs 37K batch)
- 10 exact filename matches, 0 identical content — all enriched versions are upgraded
- 32 numbered generics (10_extracted.json etc.) from gold_list baseline — early test outputs

### 2. Pipeline Code Discovery
- User caught that `01_guideline_extractor/` contains the **live extraction pipeline** (v2.3)
- Pipeline code: main.py, core/, engines/ (5 engines), utils/, schemas/, prompts/
- One-click system: oneclick/ (right-click Windows context menu extraction)
- Build scripts: build_oneclick_protocol.js, build_protocol_v3.js, etc.
- **Cannot archive the whole folder** — only data artifacts are safe to remove

### 3. Redundancy Cleanup — Items Moved Offsite
The following were moved to the user's offsite archive folder:

**From clinical_guidelines/:**
- `med-nav_rebuild/` — 301 files, CRI sprint artifact (March 2, 2026), no downstream consumers

**From abfm_prep/01_guideline_extractor/:**
- `documents/` subfolders — gold_2, gold_list, gold_2_retest, parallel_test, test_parallel, test_parallel2, timing_test (57 test-input PDFs, all copies of library PDFs)
- `outputs/` batch folders — afp_peds_uspstf_batch, afp_test_batch, jacc_pulm_batch, neuro_tox_rheum_psych_batch, id_renal_gi_hep_batch, ab_test, dupe_total_files
- Pre-calibration archive, calibration runs 1/3/4

**From claude_knowledge/ top level:**
- `guideline_extractor_v1/` — 35 files, prototype superseded by v2.3
- `guideline_lib_linked/` — 235 files, exact duplicate of enriched JSON + old staging
- `data_plug-in/` — 9 files, redundant copies of installed plugin skills

**Deleted (empty/junk):**
- `claude_root_working/`, `$Temp/`, `.tmp.drivedownload/`, `.tmp.driveupload/`

### 4. Outputs Folder Reorganization
- User consolidated `gold_2_v23_baseline/` (15 JSONs) and `gold_list_v23_baseline/` (22 JSONs) into `historical_calibration/`
- Calibration reports (6 files) already in historical_calibration/
- Remaining loose files in outputs/: 1 stray extraction JSON, 3 migration/prescan summaries
- `documents/` is now empty (0 files)

### 5. Full Repository Audit
- Scanned entire `claude_knowledge/` top level for redundancies
- Identified and removed: guideline_extractor_v1, data_plug-in, empty folders
- Kept: scratch_scripts/, house_keeping_hub/, node_modules/, build_protocol.js
- Noted: `04_aafp_integration/07_archive/` is 494.9 MB — almost entirely one OCR'd PDF (AAFP-presentations_combined-OCR.pdf). Not a redundancy issue, just a large file.

### 6. README Overhaul — All 6 Files Rewritten
- `clinical_guidelines/README.md` — removed med-nav refs, updated counts (257 PDFs, 211 DOCX, 195 JSON)
- `clinical_guidelines/README.json` — restructured, removed CRI references
- `01_guideline_extractor/README.md` — corrected path refs, documented pipeline code vs data artifacts
- `01_guideline_extractor/README.json` — updated to reflect cleaned outputs/
- `claude_knowledge/README.json` — updated top-level structure, removed archived folders
- `claude_knowledge/README_PROJECT.md` — full rewrite reflecting post-cleanup state

---

## CURRENT STATE — Post-Cleanup Inventory

### claude_knowledge/ (top level)
| Folder | Files | Size | Purpose |
|--------|-------|------|---------|
| 00_canonical/ | 28 | 31 MB | Curriculum, question bank, analysis, reference data |
| abfm_prep/ | 1,755 | 796 MB | 6 numbered modules (extractor → ITE pipeline) |
| clinical_guidelines/ | 742 | 376 MB | Guideline library: PDFs, DOCX, enriched JSON, alt_refs |
| house_keeping_hub/ | 29 | 0.2 MB | Organizational docs, dependency maps, batons |
| scratch_scripts/ | 9 | <0.1 MB | Diagnostic/debugging scripts |
| node_modules/ | 384 | 8 MB | Dependencies for build_protocol.js |

### clinical_guidelines/ (detail)
| Subfolder | Count | Description |
|-----------|-------|-------------|
| 01_pdf_guideline_library/ | 257 PDFs | Consolidated single-source PDF library |
| 02_docx_guideline_library/ | 211 DOCX | Structured summaries (NNN_Topic_summary.docx) |
| 03_enriched JSON/ | 195 JSON | Enriched extractions with ite_intelligence block |
| alt_refs/ | 76 files | Bedside, life_support, vaccine sheets, FMHS reference |

### 01_guideline_extractor/ (pipeline — DO NOT ARCHIVE)
- Pipeline code: main.py, core/, engines/, utils/, schemas/, prompts/
- One-click system: oneclick/ (right-click context menu extraction)
- Build scripts: 4 JS builders
- Historical data: outputs/historical_calibration/ (43 files), logs/ (608 files)
- Empty: documents/ (test PDFs moved offsite)

---

## DEFERRED FLAGS — CURRENT STATE

### FLAG 1 — ITE Enrichment Quality Dimension
**Status: OPEN** (carried from prior session)
calibrate.py scores 5 extraction dimensions. ITE intelligence block not yet scored.
Action: Add 6th dimension to calibrate.py. Suggested weight 10-15%.

### FLAG 3 — Retroactive synthesis batch
**Status: OPEN** (carried from prior session)
AFP batch 001-100 extracted before synthesis layer existed. No synthesis{} block in those JSONs.
Action: Run synthesize.js on those 100 JSONs.

### FLAG 10 — Crosswalk Index (NEW)
**Status: READY TO BUILD**
Master JSON mapping each source PDF to all its derivatives (DOCX, enriched JSON, ITE reference JSON) across all locations. This was the original goal before cleanup — now that redundancies are eliminated, the crosswalk can be built cleanly.

Sources to crosswalk:
1. `clinical_guidelines/01_pdf_guideline_library/` — 257 PDFs (source of truth)
2. `clinical_guidelines/02_docx_guideline_library/` — 211 DOCX summaries
3. `clinical_guidelines/03_enriched JSON/` — 195 enriched JSONs
4. `abfm_prep/05_ite_refs/04_outputs/ingested/json/` — 242 ITE reference JSONs (URL-slug naming with hash suffix, contain `source.title` field)

Challenge: 4 different naming conventions across sources. Previous session built a keyword-based matcher that achieved partial coverage (105 fully covered, 104 partial, 46 zero-coverage). Crosswalk should use similar approach but produce a single authoritative index.

### FLAG 11 — 19 Standout ITE References Without PDFs (NEW)
**Status: OPEN**
Analysis of 5 rising body system topics (Reproductive: Female, Psychogenic, Neurologic, Nonspecific, GI) identified 19 standout references with high ITE citation counts. All have `extraction_status: pending` with no PDFs on disk. Top signal: Silver/Ledford 2021 (4 questions, nerve entrapment).
Action: Acquire these PDFs and run through extraction pipeline.

---

## NEXT SESSION PRIORITIES (in order)

1. **Build crosswalk index** (FLAG 10) — the user is "itching" for this
2. **Acquire standout ITE reference PDFs** (FLAG 11) — optional, user-driven
3. **Retroactive synthesis batch** (FLAG 3) — optional, low priority

---

## TECHNICAL NOTES FOR NEXT SESSION

- Desktop Commander MCP for Windows filesystem access
- Windows cmd shell for process execution (PowerShell has issues)
- `sys.stdout.reconfigure(encoding='utf-8')` required in all Python scripts
- Scripts must be written to Windows filesystem — Desktop Commander can't see Linux VM paths
- Desktop Commander `read_file` returns metadata-only for .md/.json — use Python `open()` via scripts
- SQLite DB at: `abfm_prep/02_ite_intelligence/db/ite_intelligence.db`
- DB schema: `articles` table PK=`clean_ref`, `questions` uses `qid`, `question_ref_pairs` uses `qid`
- Always clean up temp scripts (prefix with `_`) after use
