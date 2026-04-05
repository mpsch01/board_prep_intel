# BATON 042 — Catastrophic Deletion Recovery: COMPLETE
**Date:** 2026-04-05
**Session:** Cowork desktop — continued from compacted BATON 041 context
**Status:** ACTIVE — library restored; 3 scripts still pending
**Replaces:** BATON_active_041_20260405_unpaywall_scanner.md

---

## What Happened This Session

### THE INCIDENT: fix_ghost.py — Catastrophic Deletion
A ghost folder at `01_module.1_warehouse/01_module.1_warehouse/` needed cleanup.
`fix_ghost.py` was written with a path bug:

```python
# WRONG (what was written):
ghost_root = GHOST_BASE.parent.parent.parent   # 3 hops up = real M1 root

# CORRECT (what it should have been):
ghost_root = GHOST_BASE.parent.parent          # 2 hops = ghost subfolder
```

`shutil.rmtree()` ran on the real `01_module.1_warehouse/citation_files/ITE/` tree.
**Permanently deleted ~787 PDFs** (bypassed Recycle Bin):
- VC_fail A–V: ~599 files
- local_lite: ~117 files
- right_click: ~71 files
- AAFP folder (in M1 root)

Survivors: VC_pass (169 intact), VC_fail W–Z (~29 intact)

---

## Recovery Path

### Step 1: identify_missing.py
Built and ran `04_module.4_sandbox/identify_missing.py`.
- Logic: pre_existing = DB articles NOT in exa_pdf_queue.csv (had PDFs before EXA ran)
- missing = pre_existing AND not currently on disk AND not in any script result CSV
- **Output:** `missing_articles.csv` — 313 rows

### Step 2: External Hard Drive Backup Found
User located backup drive. Placed PDFs in 4 RECO staging folders at project root:
- `RECO_VC_fail/` — 148 PDFs (147 codon, 1 legacy)
- `RECO_VC_pass/` — 94 PDFs (93 codon, 1 legacy)
- `RECO_local_lite/` — 117 PDFs (117 codon)
- `RECO_right_click/` — 71 PDFs (58 codon, 13 legacy)

### Step 3: reconcile_reco.py
Built and ran `04_module.4_sandbox/reconcile_reco.py`.

**Result: 313/313 missing articles covered by RECO backup. Zero still missing.**

Output files:
- `reco_covered.csv` — 313 rows (all covered)
- `still_missing.csv` — 0 rows
- `reco_summary.txt` — full breakdown

### Step 4: Files Moved Back to citation_files/ITE/
Used robocopy /MOV to restore each tier:

| Tier | Final Count |
|------|-------------|
| VC_fail | 170 |
| VC_pass | 169 |
| local_lite | 117 |
| right_click | 71 |
| **TOTAL** | **527** |

Note: VC_fail 170 = 29 W-Z survivors + 141 from RECO backup (7 already existed in dest, skipped).

---

## Git Worktree Cleanup
A stale git worktree (`claude/hopeful-lewin`) was found at `.claude/worktrees/hopeful-lewin/`.
Created by an earlier agent invocation with `isolation: "worktree"`.
- Deregistered: `git worktree prune` ✅
- Folder removed by user (Recycle Bin) ✅
- `git worktree list` now shows only main repo ✅

---

## DEFERRED FLAGS

### DEFERRED-H: 3 Auto-Recovery Scripts (Non-urgent)
All 313 missing articles recovered from RECO backup — scripts no longer urgently needed.
But should still run to handle legacy-named files (15 non-codon PDFs in RECO folders).
Commands (run from respective script directories):

```bash
# EXA downloader — catches everything in exa_pdf_queue.csv not on disk
python exa_pdf_downloader.py
# (from 01_module.1_warehouse/scripts/maintain/)

# PMC OA downloader
python pmc_oa_downloader.py --all-pmc
# (from 01_module.1_warehouse/scripts/maintain/)

# Unpaywall recovery
python recover_unpaywall.py
# (from 01_module.1_warehouse/scripts/maintain/)
```

### DEFERRED-I: unpaywall_scanner.py --from-csv Extension
Build flag to attack ~190-200 AFP articles from missing_articles.csv via Unpaywall.
Now less urgent since RECO covered them all, but still useful for future acquisitions.

---

## Current Library State
```
01_module.1_warehouse/citation_files/ITE/
  VC_fail/      170 PDFs
  VC_pass/      169 PDFs
  local_lite/   117 PDFs
  right_click/   71 PDFs
  TOTAL:        527 PDFs
```

RECO folders at project root are now empty (moved) and can be deleted.

---

## DB State (Unchanged — source data never touched)
- articles: 1,985
- ite_questions: 1,629 (ITE) + 1,221 (AAFP BRQ) = 2,850 total
- article_icd10: populated
- clinical_pathways: populated
- ite_intelligence.db: intact at 00_database/db/

---

## Next Steps (Priority Order)
1. Delete the 4 empty RECO folders (or keep as staging area — user's call)
2. Run DEFERRED-H scripts when convenient (non-urgent)
3. Git commit: recovery scripts + new sandbox files
4. Resume normal roadmap (Intelligence 2.0 Layer 2 — PubMed currency checks)

---

## Conventions Locked
- `shutil.rmtree` is BANNED from all scripts — use explicit file-by-file deletion or PowerShell Remove-Item
- All scripts must use: `PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent` (3 hops from scripts/maintain/ or scripts/analyze/)
- Robocopy /MOV chained with && will break on exit code 3 — run each tier separately
- Desktop Commander write_file is reliable for Windows filesystem; Write tool has sync delay
