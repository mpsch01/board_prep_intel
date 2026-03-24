# BATON — Active Session Handoff
**BATON Number:** 004
**Phase:** PROJECT_OVERHAUL — M1 Scripts Migration Complete
**Date:** 2026-03-24
**Status:** `01_module.1_warehouse/scripts/build/` and `maintain/` created and fully populated. 11 scripts in their correct homes. M2/scripts cleaned to 10 pure processor-tier scripts. Git init is now unblocked.

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

---

## QC PROTOCOL NOTE

**Schema-level population comparison is now a mandatory QC step after any data integration.** For every column in affected tables, compare population rates between old and new records. This catches gaps like `body_system_merged` and the keyword columns that would otherwise be silent failures. Template: check `IS NOT NULL AND != ''` grouped by cohort.

---

## MIGRATION TRACKER

### Migrated This Session (March 24, 2026 — Session 3)
| Item | From | To | Notes |
|------|------|----|-------|
| `aafp_cleanup_filenames.py` | `02_module.2_processor/scripts/` | `01_module.1_warehouse/scripts/maintain/` | PDF naming tool — M1 correct home |
| `aafp_fill_gaps.py` | `02_module.2_processor/scripts/` | `01_module.1_warehouse/scripts/maintain/` | PDF acquisition — M1 correct home |
| `aafp_retry_playwright.py` | `02_module.2_processor/scripts/` | `01_module.1_warehouse/scripts/maintain/` | PDF acquisition — M1 correct home |
| `aafp_retry_selenium.py` | `02_module.2_processor/scripts/` | `01_module.1_warehouse/scripts/maintain/` | PDF acquisition — M1 correct home |
| `aafp_top20_downloader.py` | `02_module.2_processor/scripts/` | `01_module.1_warehouse/scripts/maintain/` | PDF acquisition — M1 correct home |
| `build_crosswalk_index.py` | `02_module.2_processor/scripts/` | `01_module.1_warehouse/scripts/maintain/` | Warehouse tool — M1 correct home |
| `integrate_2018_2019.py` | `02_module.2_processor/scripts/` | `01_module.1_warehouse/scripts/build/` | One-time DB build — already run |
| `aafp_vc_batch_download.py` | `skills_abilities/agents/scripts/` | `01_module.1_warehouse/scripts/maintain/` | PDF acquisition — M1 correct home |
| `rebuild_ite_db_v2.py` | local machine (old `02_ite_intelligence/scripts/`) | `01_module.1_warehouse/scripts/build/` | Primary DB constructor |
| `compute_embeddings.py` | local machine (old `02_ite_intelligence/scripts/`) | `01_module.1_warehouse/scripts/build/` | Vector embeddings (deferred) |
| `validate_db_v2.py` | local machine (old `02_ite_intelligence/scripts/`) | `01_module.1_warehouse/scripts/build/` | Post-build QC |
| `build_match_staging.py` | local machine (old `02_ite_intelligence/scripts/`) | `01_module.1_warehouse/scripts/maintain/` | ART-ID match staging |
| `rename_to_codon.py` | local machine (old `02_ite_intelligence/scripts/`) | `01_module.1_warehouse/scripts/maintain/` | Codon rename executor |
| `build_clinical_pathways.py` | local machine | `01_module.1_warehouse/scripts/maintain/` | Layer 3 builder (also in M3 — duplicate) |
| `build_topic_trends.py` | local machine | `01_module.1_warehouse/scripts/maintain/` | Layer 4a builder (also in M3 — duplicate) |

### M1/scripts Final State
```
01_module.1_warehouse/scripts/
├── build/   (6 scripts + README)
│   ├── build_clean_question_bank.py   ← Excel → ite_questions_clean.json
│   ├── rebuild_ite_db_v2.py
│   ├── integrate_2018_2019.py         ← already run
│   ├── validate_db_v2.py
│   ├── compute_embeddings.py          ← deferred (FLAG 33)
│   └── validate_vector_search.py      ← deferred (FLAG 33)
└── maintain/  (11 scripts + README)
    ├── aafp_cleanup_filenames.py
    ├── aafp_fill_gaps.py
    ├── aafp_retry_playwright.py
    ├── aafp_retry_selenium.py
    ├── aafp_top20_downloader.py
    ├── aafp_vc_batch_download.py
    ├── build_crosswalk_index.py
    ├── build_match_staging.py
    ├── rename_to_codon.py
    ├── build_clinical_pathways.py
    └── build_topic_trends.py
```

### Still Needs to Come Into `00_#PROJECT_OVERHAUL`
| Item | Current Location | Target Module | Priority |
|------|-----------------|---------------|----------|
| ~~`build_clean_question_bank.py`~~ | ~~old `03_ite_exam/03_database/`~~ | `01_module.1_warehouse/scripts/build/` | ✅ DONE |
| ~~`validate_vector_search.py`~~ | ~~old `02_ite_intelligence/scripts/`~~ | `01_module.1_warehouse/scripts/build/` | ✅ DONE |
| M2 core extractor files (`core/`, `engines/`) | old `01_guideline_extractor/` | `02_module.2_processor/scripts/` | MEDIUM |
| Module F scripts (VC outline pipeline) | old `04_aafp_integration/05_scripts/` | `02_module.2_processor/scripts/` | MEDIUM |
| `ite_questions_clean.json` | old `03_ite_exam/03_database/` | `key_data_files/` | MEDIUM |
| Score report PDFs (Scholl, Hopkins, Sarkar) | old `08_ite_score_analysis/raw_pdfs/` | `00_database/` or EXT | LOW |
| M3 score analysis configs | old `08_ite_score_analysis/pipeline/` | `03_module.3_analyst/scripts/` | LOW |

---

## WHERE WE ARE

**DB:** 1,936 articles, 1,629 questions (2018–2025), 2,722 question-ref pairs, 3,855 article-ICD10 entries, 1,818 QID-art xref pairs
**Keyword coverage:** 1,629/1,629 (100%) — all four columns across all years
**PDF Library:** 404 PDFs across 4 tiers in `01_module.1_warehouse/`
**M1 Scripts:** `build/` (6 scripts), `maintain/` (11 scripts) — COMPLETE
**M2:** core/ (3), engines/ (6), utils/ (5), prompts/candidates/ (4), scripts/ (16), main.py at root — extractor stack migration complete. Module F scripts still pending.
**M3 Scripts:** `03_module.3_analyst/scripts/` — 7 scripts (2 flagged as duplicates)
**Intelligence 2.0:** Layers 1 (ICD-10), 3 (Pathways), 4a (Trends) complete. Layers 2 + 4b not started.
**Agent toolbox:** `skills_abilities/agents/scripts/` — 6 files (aafp_vc_batch_download.py relocated to M1)
**Git:** ✅ DONE — first commit `1166fa8` on `main` (2026-03-24). Run all future git commands from Windows (Git Bash / Terminal), not through the VM.

---

## WHAT WAS BUILT THIS SESSION (March 24, 2026 — Session 3)

| Item | What Changed | Why |
|------|-------------|-----|
| **`01_module.1_warehouse/scripts/build/`** | Created. 4 scripts + README. | Step #3 from BATON 003 — prerequisite for git init. |
| **`01_module.1_warehouse/scripts/maintain/`** | Created. 11 scripts + README. | Step #3 from BATON 003. |
| **M2/scripts cleanup** | 7 scripts relocated to M1. Count: 17 → 10. | Scripts were misplaced — PDF acquisition belongs in warehouse layer, not processor layer. |
| **agents/scripts cleanup** | `aafp_vc_batch_download.py` relocated to M1/maintain. | Same reason — warehouse tool, not agent tool. |
| **README manifests** | `build/README.md` + `maintain/README.md` — each documents present scripts, missing scripts, and run order. | Manifest-as-code pattern for git onboarding and handoff. |
| **`_index.md` updated** | M1 section fully rewritten. M2 count corrected. M3 duplicates flagged. Housekeeping log entry added. | Ground truth stays current. |

---

## NEXT STEPS (Ordered)

1. ~~**Integrate 2018-2019 questions**~~ — **DONE** (Session 1).
2. ~~**Populate 4 keyword columns for 2018-2019 questions**~~ — **DONE** (Session 2).
3. ~~**Create M1 scripts subfolders and migrate warehouse scripts**~~ — **DONE** (Session 3). Git init unblocked.

4. ~~**Initialize git repo**~~ — **DONE** (Session 3). First commit `1166fa8` on `main`. `.gitignore` and `.gitattributes` in place. Future git commands run from Windows.

5. ~~**Housekeeping pass**~~ — **DONE** (Session 3). M3 duplicates deleted. BATON archive renamed (commit `a610baa`). BATON 003 archived.

6. ~~**Complete migration of remaining scripts (extractor stack)**~~ — **DONE** (Session 3). core/, engines/, utils/, prompts/, main.py, + 6 scripts migrated from old 01_guideline_extractor. **Module F scripts (VC outline pipeline) still pending** — old `04_aafp_integration/05_scripts/` → M2/scripts/.

7. **Address deferred flags** — nnn_XXXX ART-ID (FLAG 33), QID format normalization — both as part of the M1 rebuild rather than separate passes.

8. **Articles table gaps** — 389 new articles still 0% for source_type, categories, tier, auto_assigned, engine_type. Requires classification + VC gate pipeline pass.

9. **Build Intelligence 2.0 Layer 2** — `article_currency` table. PubMed MCP is already connected.

---

## CRITICAL FILE LOCATIONS

| File | Path | Status |
|------|------|--------|
| ite_intelligence.db | `00_database/db/ite_intelligence.db` | Production — 1,936 articles, 1,629 questions |
| DB Backup (pre-2018) | `00_database/db/ite_intelligence_pre2018_backup_20260324_001256.db` | Rollback point |
| VC Gate JSON | `key_data_files/session_hy_inserts_v7.json` | Production — 352 citations |
| Active BATON | `BATON_active_004_20260324_M1scripts.md` | This file |
| Previous BATON | `BATON_active_003_20260324_0820.md` | Archive pending |
| M1 build scripts | `01_module.1_warehouse/scripts/build/` | 4 scripts + README |
| M1 maintain scripts | `01_module.1_warehouse/scripts/maintain/` | 11 scripts + README |
| M2 processor scripts | `02_module.2_processor/scripts/` | 10 scripts |
| M3 analyst scripts | `03_module.3_analyst/scripts/` | 7 scripts (2 duplicates flagged) |
| Agent Scripts | `skills_abilities/agents/scripts/` | 6 files |
| PDF Library | `01_module.1_warehouse/` (4 tier subfolders) | 404 PDFs |

---

## KEY ARCHITECTURE REMINDERS

- **4-module architecture is the north star:** Warehouse (M1), Processor (M2), Analyst (M3), Sandbox (M4).
- **M1 scripts pattern:** `build/` = scripts that assume the DB doesn't exist yet. `maintain/` = scripts that assume the DB exists and has data. When in doubt: does it need live data to run? → `maintain/`.
- **Language rule: Python only for all new scripts.** Existing JS DOCX scripts (`build_summary.js`, `build_db_docx.js`, `build_merged_docx.js`, `synthesize.js`, `ite_report_builder_v2.js`) are grandfathered — they work, they're isolated, leave them. Do not add new JS to the project.
- **VC gate = sole criterion** for `$right_click$` vs `local_lite`. DB membership alone is not sufficient.
- **Codon filename format:** `Author_Year#@#ART-XXXX@#@.pdf` — start codon `#@#`, stop codon `@#@`.
- **Source data is protected, derived data is disposable.** DB + PDFs + VC gate survive everything.
- **BATON numbering:** This is BATON 004. Next session writes BATON 005.
- **_index.md scope:** Maps `00_#PROJECT_OVERHAUL` only — not the full claude_knowledge tree.
- **QC protocol:** After any data integration, run schema-level population comparison (column-by-column, old cohort vs new cohort). Non-negotiable.

---

## KNOWN ISSUES

- ~~`build_clinical_pathways.py` and `build_topic_trends.py` M3 duplicates~~ — DELETED.
- ~~Multiple archived BATONs had "active" in filename~~ — RENAMED (commit `a610baa`).
- `README_PROJECT.md` and `README.json` at project root are stale (March 17, reflect old 7-module structure).
- `_index.md` BATON 003 → 004 update written this session.
- `master_map.JSON` stale — shows 1,397 articles, old paths, partial modules.
- 13 unmapped ICD-10 terms in `clinical_synonym_map.json` (pseudogout, sundowning, etc.).
- Blueprint field: 100% empty for 2018-2019, 66.8% populated for 2020-2025.
- `node_modules/` in `02_module.2_processor/` — reinstallable, should be excluded from git.
- `qid_art_xref` (1,818 rows, 2020-2025 only) diverges from `question_ref_pairs` (2,722 rows, 2018-2025).
- 232 pre-existing orphaned `question_ref_pairs` rows.
- Old `BATON_active_001_20260323_1200.md` still at project root — Mikey needs to delete manually.
- `build_clean_question_bank.py` and `validate_vector_search.py` still missing from M1/build — need to come from local machine.

---

*Written 2026-03-24 by Claude Sonnet 4.6 · Session type: M1 Scripts Migration*
*BATON 004 — Fourth numbered BATON under Protocol v2.0*
