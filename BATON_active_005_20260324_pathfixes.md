# BATON — Active Session Handoff
**BATON Number:** 005
**Phase:** PROJECT_OVERHAUL — TEMP_04 Migration + Path Hardcoding Elimination
**Date:** 2026-03-24
**Status:** TEMP_04 (AAFP integration folder) fully migrated. All 30 Python + JS scripts in M2/scripts/ converted to dynamic path resolution. M2/source/ layer created. Git up to date.

---

## REBUILD NORTH STAR — 5 Locked Principles

*Carry forward unchanged in every BATON. Modify only when Mikey explicitly changes one.*

1. **Git = version control layer.** All scripts, schemas, configs in a git repo. Structure the rebuild for easy git adoption — clean module folders, no loose scripts at root, no artifacts mixed with source.
2. **BATON = intent layer.** Sits on top of git. Git tracks what changed; BATON tracks what matters and what's next. Permanent regardless of git adoption.
3. **Formal schemas first.** SQL `CREATE TABLE` defined before build scripts are written. Schema drift is a first-class failure mode.
4. **OUTPUT_SCHEMA for all agents.** Use the SDK's `output_format` parameter. No prompt-hacking for structured output.
5. **Cryptographic hash ART-IDs.** Proof of provenance — the ID is earned by completing the full pipeline. Deferred until library is stable and nnn_XXXX migration is complete.

---

## DEFERRED FLAGS (Carry Forward)

**FLAG 33 — nnn_XXXX ART-ID Scheme:** Designed but NOT implemented. `001_XXXX`–`352_XXXX` for VC-cited, `000_XXXX` for non-VC. Deferred until full migration plan with rollback is written. Subsumed into Warehouse (M1) restructuring.

**FLAG 30 — Scholl Encrypted PDFs:** `scholl_2025_ENCRYPTED_22.pdf`, `_23.pdf`, `_24.pdf` in score analysis raw_pdfs. Password-protected, cannot be parsed until decrypted.

**FLAG 15 — build_merged_docx.js --merged-only run:** Still pending. May be deprioritized given the rebuild.

**FLAG — 87 Misclassified Codon Files:** 87 of the codon-named PDFs are ITE-linked but NOT VC-cited. They have valid ART-IDs but are in the wrong tier. Resolved as part of M1 rebuild.

**FLAG — QID Format Mismatch:** VC gate uses `Q{YEAR}-{NUM}`, DB uses `QID-{YEAR}-{NUM:04d}`. Only 75/229 resolve via direct string match. Use citation strings as workaround. Needs normalization pass.

**FLAG — BATON Archive Naming Debt:** Multiple archived BATONs still have "active" in filename. Will batch-rename during rebuild housekeeping.

**FLAG — Layer 2 Not Started:** `article_currency` table (PubMed freshness tracking) not built. Part of Intelligence 2.0.

**FLAG — Layer 4b Not Started:** `pubmed_alerts` table (new article detection) not built. Part of Intelligence 2.0.

**FLAG — Body System Taxonomy Debt:** DB has inconsistent naming across years. The "Hematologic/ Immune" typo (space before slash) persists. Full taxonomy cleanup pass deferred.

**FLAG — 232 Pre-Existing Orphaned question_ref_pairs:** 232 rows in `question_ref_pairs` have `clean_ref` values that don't match any `articles.clean_ref`. Pre-dates this session — legacy debt from earlier integration runs.

**FLAG — qid_art_xref Divergence:** `qid_art_xref` (1,818 rows) covers only 2020-2025. `question_ref_pairs` (2,722 rows) now covers 2018-2025. Reconcile during M1 rebuild.

**FLAG — M3 Script Duplicates:** `build_clinical_pathways.py` and `build_topic_trends.py` exist in both `01_module.1_warehouse/scripts/maintain/` (canonical) and `03_module.3_analyst/scripts/` (duplicate). Remove M3 copies next housekeeping pass.

**FLAG — Manual Deletes Pending:** `BoardPrep-ContentOutline_HY-ENRICHED-v4.docx` in `02_module.2_processor/source/` is superseded by `00_EX_content_outline_w_q.docx` (larger, newer). Mikey to delete manually (VM cannot rm NTFS files).

**FLAG — VTT Files Not Migrated:** AAFP .vtt transcript files not brought in — decision made that pre-computed `vtt_time_weights.json` is sufficient. If time-on-topic weights ever need recalculation, raw .vtt files remain in old structure.

**FLAG — .bat / .ps1 / .reg Path Updates Deferred:** `extract_guideline.bat`, `batch_reprocess.ps1`, `install_context_menu.reg` contain hardcoded paths but cannot be dynamically resolved at the shell/registry level. These need manual path updates when the project directory moves up a level.

---

## QC PROTOCOL NOTE

**Schema-level population comparison is now a mandatory QC step after any data integration.** For every column in affected tables, compare population rates between old and new records. This catches gaps like `body_system_merged` and the keyword columns that would otherwise be silent failures. Template: check `IS NOT NULL AND != ''` grouped by cohort.

---

## MIGRATION TRACKER

### Migrated This Session (March 24, 2026 — Session 4)

| Item | From | To | Notes |
|------|------|----|-------|
| **TEMP_04_aafp_integration_TEMP** | root TEMP folder | Various destinations below | Full AAFP integration folder migrated |
| Module F scripts (VC outline pipeline) | TEMP_04/05_scripts/ | `02_module.2_processor/scripts/` | 01_build_crosswalk, 02b_generate_hy_inserts, 03_inject_into_outline, 04_inject_poll, 07_inject_supplements, 08_build_supplement, 09_build_pearl, build_v6_resident |
| Keyword library scripts (A-G pipeline) | TEMP_04/keyword_library/scripts/ | `02_module.2_processor/scripts/` | A_outline_terms, B_tfidf_keywords, C_vtt_time_weights, D_keyword_library, E_v4_question_driven, F_extract_question_refs, G_backfill_references |
| Additional pipeline scripts | TEMP_04/05_scripts/ | `02_module.2_processor/scripts/` | build_poll_inserts.py, sg_reweight_v3.py, validate_v4.py, split_by_year.py, hygiene_audit.py, hygiene_fix.py |
| Key data files | TEMP_04/ | `key_data_files/` | session_keyword_library.json, poll_inserts.json, vtt_time_weights.json, README_AAFP_course_integration.json |
| 50 AAFP .txt transcripts | TEMP_04/keyword_library/ | `02_module.2_processor/source/aafp_transcripts/` | Cleaned transcripts — input to B_build_tfidf_keywords.py |
| Content outline DOCX | (Mikey added directly) | `02_module.2_processor/source/` | `00_EX_content_outline_w_q.docx` — 6.1MB, Mar 6, supersedes v4 |
| **M2/source/ layer** | (new) | `02_module.2_processor/source/` | New architectural layer for pipeline source inputs (not code) |

### Path Hardcoding Elimination (This Session)

**30 Python + JS scripts** in `02_module.2_processor/scripts/` converted from `C:\Users\mpsch\Desktop\claude_knowledge\...` hardcoded paths to dynamic resolution:
- Python: `SCRIPT_DIR = Path(__file__).resolve().parent; PROJECT_ROOT = SCRIPT_DIR.parent.parent`
- JS: `const PROJECT_ROOT = path.resolve(__dirname, "../../");`
- Files not yet in new structure annotated with `# TODO: not yet migrated`

**Additional fixes applied this pass:**
- `calibration.py`: corrected `.parent.parent.parent` → `.parent.parent` (depth bug introduced in fix)
- `sg_reweight_v3.py`: secondary hardcoded path inside function body (line ~49)
- `db_guided_extractor.py`: legacy Windows path fallback now uses `BASE_DIR` (already dynamic)
- `build_exemplar_v2.js`: hardcoded old session output path removed
- `build_qbank_exam_version.py`: added `from pathlib import Path` + dynamic QBANK_DIR

**Still hardcoded (deferred — system files):**
- `extract_guideline.bat`
- `batch_reprocess.ps1`
- `install_context_menu.reg`

### Git Commits This Session
| Commit | Description |
|--------|-------------|
| (TEMP_04 migration commit) | TEMP_04 contents migrated to M2/scripts/, M2/source/, key_data_files/ |
| `ed85b06` | `refactor(M2/scripts): replace all hardcoded absolute paths with dynamic resolution` — 30 files, 194 ins / 116 del |

---

## WHERE WE ARE

**DB:** 1,936 articles, 1,629 questions (2018–2025), 2,722 question-ref pairs, 3,855 article-ICD10 entries, 1,818 QID-art xref pairs
**Keyword coverage:** 1,629/1,629 (100%) — all four columns across all years
**PDF Library:** 404 PDFs across 4 tiers in `01_module.1_warehouse/`
**M1 Scripts:** `build/` (6 scripts), `maintain/` (11 scripts) — COMPLETE
**M2 Scripts:** 41 Python + JS scripts — all path hardcoding eliminated (commit `ed85b06`)
**M2 Source:** `02_module.2_processor/source/` — `00_EX_content_outline_w_q.docx` + `aafp_transcripts/` (50 .txt files)
**M3 Scripts:** 7 scripts (2 flagged as duplicates pending deletion)
**Intelligence 2.0:** Layers 1 (ICD-10), 3 (Pathways), 4a (Trends) complete. Layers 2 + 4b not started.
**Git:** ✅ Active — commit `ed85b06` on `main`. Run all future git commands from Windows (Git Bash / Terminal), not through VM.

---

## WHAT WAS BUILT THIS SESSION (March 24, 2026 — Session 4)

| Item | What Changed | Why |
|------|-------------|-----|
| **TEMP_04 migrated** | ~20 scripts, 4 key data files, 50 transcripts, 1 source DOCX relocated to permanent homes | TEMP_04 was the last AAFP integration TEMP folder — module F pipeline now fully inside the project |
| **M2/source/ layer created** | New subfolder established with content outline DOCX + 50 AAFP transcripts | Pipeline inputs (not code) need a stable, versioned home adjacent to the scripts that consume them |
| **30 scripts de-hardcoded** | All `C:\Users\mpsch\...` paths replaced with `SCRIPT_DIR / PROJECT_ROOT` dynamic resolution | Entire project directory will be moved up a level when overhaul replaces pre-overhaul directory |
| **calibration.py depth bug fixed** | `.parent.parent.parent` → `.parent.parent` | Was pointing one level above PROJECT_ROOT (bug introduced during fix) |
| **key_data_files/ additions** | 4 new files: keyword_library, poll_inserts, vtt_time_weights, README_AAFP | Pipeline inputs now in permanent location |

---

## NEXT STEPS (Ordered)

1. ~~Integrate 2018-2019 questions~~ — **DONE**
2. ~~Populate 4 keyword columns for 2018-2019 questions~~ — **DONE**
3. ~~Create M1 scripts subfolders and migrate warehouse scripts~~ — **DONE**
4. ~~Initialize git repo~~ — **DONE**
5. ~~Housekeeping pass~~ — **DONE**
6. ~~Complete extractor stack migration~~ — **DONE**
6b. ~~TEMP_04 migration (Module F + keyword pipeline)~~ — **DONE**
6c. ~~Eliminate hardcoded paths from all Python/JS scripts~~ — **DONE (30 scripts, commit ed85b06)**

7. **TEMP_08 — ite_score_analysis TEMP folder** — score report PDFs + M3 configs pending migration. Same TEMP workflow: inventory → classify → execute → commit → delete.

8. **Articles table gaps** — 389 new articles still 0% for source_type, categories, tier, auto_assigned, engine_type. Requires classification + VC gate pipeline pass.

9. **Build Intelligence 2.0 Layer 2** — `article_currency` table. PubMed MCP is already connected.

10. **Manual deletes by Mikey:**
    - `BoardPrep-ContentOutline_HY-ENRICHED-v4.docx` from `02_module.2_processor/source/`
    - `build_clinical_pathways.py` + `build_topic_trends.py` from `03_module.3_analyst/scripts/`

---

## CRITICAL FILE LOCATIONS

| File | Path | Status |
|------|------|--------|
| ite_intelligence.db | `00_database/db/ite_intelligence.db` | Production — 1,936 articles, 1,629 questions |
| DB Backup (pre-2018) | `00_database/db/ite_intelligence_pre2018_backup_20260324_001256.db` | Rollback point |
| VC Gate JSON | `key_data_files/session_hy_inserts_v7.json` | Production — 352 citations |
| Content Outline | `02_module.2_processor/source/00_EX_content_outline_w_q.docx` | Production — 6.1MB, Mar 6 |
| Active BATON | `BATON_active_005_20260324_pathfixes.md` | This file |
| Previous BATON | `BATON_active_004_20260324_M1scripts.md` | Archive pending |
| M1 build scripts | `01_module.1_warehouse/scripts/build/` | 6 scripts + README |
| M1 maintain scripts | `01_module.1_warehouse/scripts/maintain/` | 11 scripts + README |
| M2 scripts | `02_module.2_processor/scripts/` | 41 scripts (all paths dynamic) |
| M2 source | `02_module.2_processor/source/` | DOCX + 50 transcripts |
| M3 analyst scripts | `03_module.3_analyst/scripts/` | 7 scripts (2 duplicates flagged) |
| PDF Library | `01_module.1_warehouse/` (4 tier subfolders) | 404 PDFs |

---

## KEY ARCHITECTURE REMINDERS

- **4-module architecture is the north star:** Warehouse (M1), Processor (M2), Analyst (M3), Sandbox (M4).
- **M2/source/ is the pipeline source inputs layer.** Not code — documents, transcripts, reference files that the pipeline scripts consume. Lives adjacent to scripts/.
- **Dynamic path pattern (Python):** `SCRIPT_DIR = Path(__file__).resolve().parent; PROJECT_ROOT = SCRIPT_DIR.parent.parent` — scripts in `M2/scripts/` are 2 levels from PROJECT_ROOT.
- **Dynamic path pattern (JS):** `const PROJECT_ROOT = path.resolve(__dirname, "../../");`
- **TODO annotation:** `# TODO: not yet migrated` marks paths pointing to files that haven't arrived in the new structure yet. When the file lands, the path is already correct — just remove the annotation.
- **Language rule: No de novo JS.** Existing JS scripts that already work migrate like any other script. JS inventory: `build_summary.js`, `build_db_docx.js`, `build_merged_docx.js`, `build_exemplar_v2.js`, `synthesize.js`, `ite_report_builder_v2.js`.
- **VC gate = sole criterion** for `$right_click$` vs `local_lite`. DB membership alone is not sufficient.
- **Codon filename format:** `Author_Year#@#ART-XXXX@#@.pdf` — start codon `#@#`, stop codon `@#@`.
- **Source data is protected, derived data is disposable.** DB + PDFs + VC gate survive everything.
- **BATON numbering:** This is BATON 005. Next session writes BATON 006.
- **_index.md scope:** Maps `00_#PROJECT_OVERHAUL` only — not the full claude_knowledge tree.
- **QC protocol:** After any data integration, run schema-level population comparison (column-by-column, old cohort vs new cohort). Non-negotiable.
- **Git on NTFS mount:** VM can stage and commit but cannot `rm` files on the NTFS mount. File deletions happen from Windows (Explorer, Git Bash, or PowerShell).

---

## KNOWN ISSUES

- `README_PROJECT.md` and `README.json` at project root are stale (March 17, reflect old 7-module structure).
- `master_map.JSON` stale — shows 1,397 articles, old paths, partial modules.
- 13 unmapped ICD-10 terms in `clinical_synonym_map.json` (pseudogout, sundowning, etc.).
- Blueprint field: 100% empty for 2018-2019, 66.8% populated for 2020-2025.
- `node_modules/` in `02_module.2_processor/` — reinstallable, excluded from git via .gitignore.
- `qid_art_xref` (1,818 rows, 2020-2025 only) diverges from `question_ref_pairs` (2,722 rows, 2018-2025).
- 232 pre-existing orphaned `question_ref_pairs` rows.
- Old `BATON_active_001_20260323_1200.md` still at project root — Mikey needs to delete manually.
- `build_clean_question_bank.py` and `validate_vector_search.py` still missing from M1/build — need to come from local machine.
- `BoardPrep-ContentOutline_HY-ENRICHED-v4.docx` in M2/source/ — superseded, pending manual delete.
- M3 duplicates (`build_clinical_pathways.py`, `build_topic_trends.py`) — pending manual delete.

---

*Written 2026-03-24 by Claude Sonnet 4.6 · Session type: TEMP_04 Migration + Path Hardcoding Elimination*
*BATON 005 — Fifth numbered BATON under Protocol v2.0*
