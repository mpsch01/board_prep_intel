# Project Severance Plan
**Created:** 2026-04-03  
**Source:** Mikey's whiteboard scan (GitHub asset `04b4c357-3008-47d9-9645-c33e0643701c`)  
**Status Assessment:** Phase 1 ~92% complete, Phase 3 done, Phases 2 & 4 pending

---

## Overview

Use `C:\Users\mpsch\Desktop\board_prep_repo_02\claude_knowledge` as the canonical root, but do not flatten
`00_PROJECT_OVERHAUL` into the root yet. The cleanest path is:

`claude_knowledge` becomes the **umbrella root**  
`claude_knowledge\00_PROJECT_OVERHAUL` becomes the **active next-gen system**  
legacy stays alive until cutover/archive is complete  
only after a successful cutover do you decide whether to flatten or keep the **modularized** subtree

> **Why:** flattening now mixes two changes at once — path severing AND physical relocation.
> That makes failures ambiguous and rollback messy.

---

## Recommended End State

**Short term:**
- Active: `00_PROJECT_OVERHAUL`
- Legacy/read-only: `abfm_prep`, `clinical_guidelines`, `agents`, `01_canonical`

**Long term:**
- Either keep `00_PROJECT_OVERHAUL` as the active system inside the root
- Or flatten it into root only after 2–3 clean validation cycles

> I found 13 live runtime scripts in the overhaul tree that still hardcode the old
> `C:\Users\mpsch\Desktop\claude_knowledge\...` assumptions, so severing is still required
> even under the new root.

---

## Phase 1: Path Severing

**Goal:** make `00_PROJECT_OVERHAUL` runnable from the current repo root without touching legacy paths.

Introduce one shared path contract for Python.

**Suggested constants:**
```python
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent[n]
OVERHAUL_ROOT = PROJECT_ROOT / "00_PROJECT_OVERHAUL"
then derive DB_PATH, warehouse dirs, output dirs from OVERHAUL_ROOT
```
Do the same for Windows wrappers.

`.bat`: use `%~dp0` and derive upward from script location  
`.ps1`: use `$PSScriptRoot`  
Remove all absolute `Desktop\claude_knowledge` references  
Fix the runtime scripts first, not docs.

**Priority files:**
- `01_module.1_warehouse/scripts/maintain/aafp_fill_gaps.py`
- `01_module.1_warehouse/scripts/maintain/aafp_retry_playwright.py`
- `01_module.1_warehouse/scripts/maintain/aafp_retry_selenium.py`
- `01_module.1_warehouse/scripts/maintain/aafp_top20_downloader.py`
- `01_module.1_warehouse/scripts/maintain/aafp_vc_batch_download.py`
- `01_module.1_warehouse/scripts/build/build_clean_question_bank.py`
- `01_module.1_warehouse/scripts/build/rebuild_ite_db_v2.py`
- `02_module.2_processor/scripts/extract_guideline.bat`
- `02_module.2_processor/scripts/batch_reprocess.ps1`
- `skills_abilities/agents/scripts/pdf_sourcer_agent.py`
- `skills_abilities/agents/scripts/run_pdf_sourcer.bat`
- `skills_abilities/agents/scripts/match_afp.py`

Separate runtime references from documentation references.

> Runtime: must be fixed now  
> Docs/BATON/archive: fix later or stamp as historical.

**Exit criteria:**
- No runtime script depends on `C:\Users\mpsch\Desktop\claude_knowledge\...`
- All runtime scripts resolve paths from the current repo root or `00_PROJECT_OVERHAUL`

---

## Phase 2: Validation

**Goal:** prove the overhaul tree is self-contained under the current root.

Add smoke checks.

**Python import smoke tests for M1/M2/M3 entrypoints:**
- Code presence and builder invocation checks
- batch/PowerShell path echo dry-runs
- Validate read-only operations first.

**DB opens from `00_database`**  
Warehouse PDF discovery  
Crosswalk generation dry-run  
Report generation dry-run  
Validate write operations into overhaul-owned outputs only.

- `extracted_json`
- module-local `temp/output` dirs
- No writes into legacy `abfm_prep` or `clinical_guidelines`
- Compare outputs against known baselines.

**Metrics:**
- Row counts
- Output file counts
- Representative report generation
- Crosswalk/article lookup correctness
- Explicitly block legacy writes during validation.

> Treat root legacy dirs as reference data only.  
> If needed, snapshot them before validation.

**Exit criteria:**
- Major workflows complete without legacy-tree dependencies
- Outputs land only in overhaul-owned locations
- Repeated runs are stable

---

## Phase 3: Cutover

**Goal:** make `00_PROJECT_OVERHAUL` the operational default inside `claude_knowledge`.

**Recommended cutover model:**
- Keep physical layout as-is
- Make `claude_knowledge\00_PROJECT_OVERHAUL` the default execution target
- Stop launching workflows from legacy folders
- Concrete cutover steps:

**Update top-level docs:**
- Root README should say active system is `00_PROJECT_OVERHAUL`
- Add root-level launch wrappers if useful.

**`run_overhaul_*` wrappers at repo root:**
- They dispatch into `00_PROJECT_OVERHAUL`
- Freeze legacy runtime paths.

**No new edits in `abfm_prep`, `agents`, `clinical_guidelines`** — only bugfixes if absolutely required for data extraction during transition. Redirect operational habits.

**BATON templates, one-click scripts, report-generation commands, agent scripts:**
- Run one full production cycle from overhaul only.

**Exit criteria:**
- Your normal workflow starts from `claude_knowledge\00_PROJECT_OVERHAUL`
- Legacy folders are no longer part of the active execution path

---

## Phase 4: Archive Strategy

**Goal:** preserve the old system without leaving ambiguity about what is active.

**Recommended archive approach:**
- Keep legacy data, but mark it read-only.

**Candidate legacy folders:**
- `abfm_prep`
- `clinical_guidelines`
- `agents`
- `01_canonical`
- `house_keeping_hub`

**Add an archive manifest.**  
**Suggested file:** `claude_knowledge\LEGACY_ARCHIVE_MANIFEST.md`

Include:
- What is archived
- Why
- Date of cutover
- Whether each folder is authoritative, historical, or disposable
- Snapshot critical databases and inventories.

**DB backup / PDF inventory / crosswalk snapshot / BATON history**

> If you still want the overhaul contents moved up into root, do it as a second project
> after successful cutover, after archive manifest exists, after wrappers and docs point to the new structure.
> My recommendation is to stop after cutover and archive, and only flatten later if there is a strong usability reason.
> The **modularized** subtree is currently an asset, not a problem.

---

## Recommended Decision

**Use this root as canonical:**  
`C:\Users\mpsch\Desktop\board_prep_repo_02\claude_knowledge`  
Make it the operational system.

**`00_PROJECT_OVERHAUL`** — Do not flatten yet. First sever paths, validate, cut over, archive. Flattening is optional after that.

---

## Current Repo Status (as of 2026-04-03)

| Phase | Status | Notes |
|---|---|---|
| Phase 3: Cutover | ✅ Complete | Repo root IS the overhaul tree on GitHub |
| Phase 1: Path Severing | ~92% done | 11 Python + 3 Windows scripts still hardcoded |
| Phase 2: Validation | ❌ Not started | No smoke test suite exists |
| Phase 4: Archive | ❌ Not started | Legacy folders still on local disk only |

### Remaining Hardcoded Scripts (Phase 1 Blockers)

| Script | Issue |
|---|---|
| `01_module.1_warehouse/scripts/maintain/aafp_retry_selenium.py` | `DEST_FOLDER` + `DB_PATH` |
| `01_module.1_warehouse/scripts/maintain/aafp_retry_playwright.py` | `DEST_FOLDER` + `DB_PATH` |
| `01_module.1_warehouse/scripts/maintain/aafp_cleanup_filenames.py` | `DEST_FOLDER` |
| `01_module.1_warehouse/scripts/maintain/aafp_vc_batch_download.py` | `MANIFEST_PATH` |
| `01_module.1_warehouse/scripts/maintain/aafp_top20_downloader.py` | `DEST_FOLDER` + `DB_PATH` |
| `01_module.1_warehouse/scripts/maintain/aafp_fill_gaps.py` | `LIBRARY_BASE`, `EXTRACT_DIR`, `LOG_PATH`, `DB_PATH` |
| `01_module.1_warehouse/scripts/build/rebuild_ite_db_v2.py` | `QUESTIONS_JSON` (old DB path) |
| `01_module.1_warehouse/scripts/build/build_clean_question_bank.py` | Source `.xlsx` + output `.json` |
| `skills_abilities/agents/scripts/match_afp.py` | `DB_PATH` |
| `skills_abilities/agents/scripts/pdf_sourcer_agent.py` | `DB_PATH`, `PDF_LIBRARY`, `AGENTS_DIR` |
| `02_module.2_processor/utils/qid_filename_parser.py` | Example path string (docstring only — not runtime) |
| `02_module.2_processor/scripts/batch_reprocess.ps1` | `$ROOT` hardcoded |
| `02_module.2_processor/scripts/extract_guideline.bat` | `cd` + `set` paths hardcoded |
| `skills_abilities/agents/scripts/run_pdf_sourcer.bat` | All 4 `set` lines hardcoded |

### Priority: Fix Before DEFERRED-A

The AAFP PDF download scripts (`aafp_retry_selenium.py`, `aafp_retry_playwright.py`, `aafp_fill_gaps.py`, `aafp_top20_downloader.py`, `aafp_vc_batch_download.py`) are queued for DEFERRED-A work and **will fail** with hardcoded paths if run from the current repo root.
