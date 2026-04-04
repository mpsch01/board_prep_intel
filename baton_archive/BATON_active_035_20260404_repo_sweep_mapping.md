# BATON 035 — Repo Sweep + Mapping + Legacy Cleanup
**Date:** 2026-04-04
**Session:** Sweep 1 structural cleanup; full repo dependency mapping; _archive_ rename fix (11 scripts); repo_pre_severance.md created; 5 legacy scripts deprecated and staged for offsite archive
**Status:** GIT-PENDING | DEFERRED-A still priority #1
**Replaces:** BATON_active_034_20260403_playwright_upgrade_deferred_a_partial.md

---

## What Was Done This Session

### 1. Sweep 1 — Structural Cleanup (completed from BATON 034 continuation)

Root directory reduced to a clean, intentional set of items only:

| Action | Detail |
|--------|--------|
| `docx_guideline_library/` → `_archive_/` | 1,518 legacy DOCXs; derived data; moved from root |
| `archive_canonical/` → `_archive_/` | Rename (not a new folder — existing folder renamed) |
| `apify-actors/` → `skills_abilities/apify-actors/` | Actor source relocated to skills_abilities |
| `apify_smart_article_extractor` | Deleted (Windows) |
| BATON 032/033 duplicates | Deleted from root (Windows) |

**SEVERANCE_PLAN gap (why the rename broke things):** `archive_canonical` was a valid relative path at sweep time — SEVERANCE only targeted absolute Desktop paths. When we renamed the folder, 11 scripts broke at runtime. All 11 were fixed with `replace_all` edits in this session.

**Fixed scripts (archive_canonical → _archive_):**
`00_body_system_extractor.py`, `01_ite_extractor.py`, `02_ite_categorizer.py`, `03_ite_merger.py`, `ite_tag_questions.py`, `ite_check_columns.py`, `build_crosswalk_v2.py`, `apply_overrides.py`, `gen_linked_refs_v2.js` (M2); `match_tiers_to_library.py`, `rebuild_acquisition_list.py` (M1/maintain)

---

### 2. Full Repo Dependency Mapping

Mapped all ~123 scripts across M1 build/, M1 maintain/, M2 scripts/, M3 scripts/, and skills_abilities/agents/scripts/. Key findings:

**Path conventions confirmed:**
- M1 build/ and maintain/: 3 hops to PROJECT_ROOT
- M2 scripts/ and M3 scripts/: 2 hops
- skills_abilities/agents/scripts/: 3 hops
- JS scripts: `path.resolve(__dirname, "../../")` = 2 hops ✅

**Option B assessment:** Flatten is path-safe. Zero scripts break from `00_#PROJECT_OVERHAUL/` → `claude_knowledge/` root. Hop counts are relative — only the prefix changes.

**`build_faculty_pptx.js` verified clean:** No `__dirname`, no DB connection, no path resolution. Standalone PPTX builder with hardcoded slide content. Not a dependency concern.

**Node.js DOCX builders:** All 6 depend on `NODE_PATH` env var (no package.json at project root). Windows environment-dependent — unresolved, not blocking.

**Persistent map created:** `repo_pre_severance.md` at project root — full script-level inventory with hop counts, read/write paths, dependency notes, and irregularities. Reference for Option B planning.

---

### 3. Legacy Script Deprecation + Offsite Archive

5 scripts identified as dead/pre-overhaul. Deprecation headers added, gathered into `01_module.1_warehouse/scripts/_legacy/`, and moved to offsite archive by user.

| Script | Reason |
|--------|--------|
| `build/extract_ite_2018_2019.py` | Already run; reads from dead `/sessions/fervent-hopeful-thompson/` path |
| `build/integrate_2018_2019.py` | Already run; wrong hop count (2 instead of 3) |
| `build/backfill_keywords_2018_2019.py` | Deprecated 2026-03-29; superseded by unified_keyword_extractor.py |
| `maintain/rename_to_codon.py` | Pre-overhaul; 4-hop PROJ_ROOT + dead warehouse paths; non-functional |
| `maintain/build_match_staging.py` | Pre-overhaul; dead warehouse paths (01_pdf_guideline_library/); non-functional |

**⚠ Windows cleanup still needed:** Originals remain in `build/` and `maintain/` with deprecation headers. Delete from Windows:
- `01_module.1_warehouse/scripts/build/extract_ite_2018_2019.py`
- `01_module.1_warehouse/scripts/build/integrate_2018_2019.py`
- `01_module.1_warehouse/scripts/build/backfill_keywords_2018_2019.py`
- `01_module.1_warehouse/scripts/maintain/rename_to_codon.py`
- `01_module.1_warehouse/scripts/maintain/build_match_staging.py`

---

## DB State (unchanged this session)

Same as BATON 034. No DB writes this session.

| Table | Rows |
|-------|------|
| articles | 1,985 |
| questions (ITE) | 1,629 |
| aafp_questions | 1,221 |
| article_icd10 | 4,137 |
| question_icd10 | 5,284 |
| clinical_pathways | 4,020 |
| article_icd10_vec | 1,674 |
| question_icd10_vec | 2,733 |
| pubmed_pmid_cache | 344 |
| PDFs | ~414 (37 AAFP acquisition manual pending) |
| Next ART-ID | ART-1987 |

---

## Script Counts (updated after _legacy cleanup)

| Location | Python | JS | Notes |
|----------|--------|----|-------|
| M1 build/ | 6 (was 9) | 0 | 3 deprecated (headers applied; originals pending Windows delete) |
| M1 maintain/ | 15 (was 17) | 0 | 2 deprecated (headers applied; originals pending Windows delete) |
| M2 scripts/ | ~60 | 6 | Stable |
| M3 scripts/ | 11 | 2 | Stable; build_faculty_pptx.js verified clean |
| skills_abilities/agents/ | 5 | 0 | Stable |

---

## Deferred Flags (unchanged)

| Flag | Description | Priority |
|------|-------------|----------|
| DEFERRED-A | 37 manual PDFs remaining: 34 subscription + 3 Cochrane → VC_fail | **HIGH** |
| DEFERRED-B | `update_citation_trends.py` after backfill | MEDIUM |
| DEFERRED-C | AAFP vs ITE trend comparison | MEDIUM |
| DEFERRED-D | 229 citation gap articles (88 AFP batch-downloadable) | MEDIUM |
| DEFERRED-E | Interactive vector dashboard | LOW |
| DEFERRED-F | Intelligence 2.0 Layer 2 (`article_currency` via PubMed, 344 PMIDs cached) | MEDIUM |

---

## Next Steps (priority order)

1. **Windows cleanup** — Delete 5 deprecated script originals from build/ and maintain/ (listed above)
2. **DEFERRED-A manual PDFs** — 37 remaining; institutional/Cochrane access → codon rename → VC_fail
3. **`backfill_new_article_metadata.py --art-id-min 1938`** — once PDFs assembled
4. **DEFERRED-B** — `update_citation_trends.py` after backfill
5. **Option B planning** — Flatten `00_#PROJECT_OVERHAUL/` → `claude_knowledge/` root (path-safe per repo_pre_severance.md analysis)
6. **DEFERRED-F** — Intelligence 2.0 Layer 2: `article_currency` via PubMed

---

## Files Changed This Session

| File | Action |
|------|--------|
| `repo_pre_severance.md` | NEW — full script inventory + dependency map (123 scripts) |
| `_index.md` | MODIFIED — BATON pointer, sweep log, deprecated scripts noted |
| `CLAUDE.md` | MODIFIED — Active BATON, script counts |
| `auto-memory-copies/project_overhaul_state.md` | MODIFIED |
| `01_module.1_warehouse/scripts/build/extract_ite_2018_2019.py` | MODIFIED — deprecation header |
| `01_module.1_warehouse/scripts/build/integrate_2018_2019.py` | MODIFIED — deprecation header |
| `01_module.1_warehouse/scripts/maintain/rename_to_codon.py` | MODIFIED — deprecation header |
| `01_module.1_warehouse/scripts/maintain/build_match_staging.py` | MODIFIED — deprecation header |
| `01_module.1_warehouse/scripts/_legacy/` | CREATED → moved to offsite archive by user |
| `BATON_active_035_*.md` | This file |

**From previous context window (BATON 034 continuation, before compaction):**

| File | Action |
|------|--------|
| 11 M1/M2 scripts | MODIFIED — `archive_canonical` → `_archive_` (replace_all) |
| `_index.md` | MODIFIED — structural refresh, sweep log, DB counts |
| `CLAUDE.md` | MODIFIED — tier folder names, term table |
| `README.md` | MODIFIED — tier names, archive section, next steps |
| `README_PROJECT.md` | MODIFIED — archive section name |
| `auto-memory-copies/reference_skills_abilities_inventory.md` | CREATED |
| `_archive_/session_housekeeping_20260403.json` | MOVED from root |
| `baton_archive/BATON_active_034_*.md` | RETIRED (move via Windows) |
