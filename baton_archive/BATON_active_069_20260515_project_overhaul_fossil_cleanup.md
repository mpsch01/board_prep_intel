# BATON 069 — 2026-05-15 — PROJECT_OVERHAUL Fossil Cleanup

**Active Session Handoff Document for board_prep_intel**

---

## Session Overview

| Item | Value |
|------|-------|
| **Date** | 2026-05-15 |
| **Previous BATON** | BATON_active_068_20260515_claude_code_migration_corpus_qc_built.md |
| **Git Hash (pre-housekeeping-commit)** | a3ef508 |
| **Branch** | claude/xenodochial-pike-667d6a (worktree off main) |
| **Primary Goal** | Eliminate residual `#PROJECT_OVERHAUL` fossil references across live config/code after Mikey flagged the `#` character as a known problem source |
| **Status** | Complete — all live `00_#PROJECT_OVERHAUL` references removed; `project_overhaul_state.md` renamed to `project_session_log.md` with git history preserved; CLAUDE.md H1 corrected |

---

## DATABASE STATE

*(Inherited from BATON 068 — no DB writes, no schema changes, no row changes this session.)*

| Table | Rows | Notes |
|-------|------|-------|
| articles | 2,206 | matches BATON 067/068 |
| questions (ITE) | 1,639 | blueprint 100%, body_system normalized |
| aafp_questions | 1,221 | blueprint 100%, concept_tags 100% |
| qid_art_xref | 2,710 | multi-reference (avg 1.6 refs/q) |
| aafp_qid_art_xref | 864 | 643 unique questions linked (52.7%) |
| article_icd10 | 4,959 | |
| question_icd10 | 5,774 | |
| aafp_question_icd10 | 4,753 | |
| clinical_pathways | 4,959 | |
| pubmed_pmid_cache | 344 | Layer 2 seed |
| article_icd10_vec | 1,757 | |
| question_icd10_vec | 2,747 | |
| icd10_vec | 2,219 | OpenAI text-embedding-3-small (1536d) |
| intersection_centroid_vec | 158 | |
| article_currency | 2,206 | |

**Next ART-ID:** ART-2208 (unchanged)
**No schema changes this session. No row changes.**

---

## PDF LIBRARY

*(Inherited from BATON 068 — Mac local state still lags Windows canonical by 569 files. PDFs gitignored; sync pending.)*

| Tier | Mac | Windows canonical | Notes |
|------|-----|-------------------|-------|
| VC_fail | 628 | 1,056 | Mac missing 428; sync pending |
| VC_pass | 168 | 309 | Mac missing 141; sync pending |
| local_lite | 117 | 117 | Synced |
| right_click | 58 | 58 | Synced |
| AAFP | 15 | 15 | Synced |
| ite_exams | 16 | 16 | All 8 years (2018–2025) × MC + critique |
| **ITE active total (Mac)** | **971** | **1,540** | (VC_fail + VC_pass + local_lite + right_click) |

See **DEFERRED-MAC-PDF-SYNC** below (carry-forward from BATON 068).

---

## Session Summary

### Pure cleanup session — no functional changes, no DB writes, no PDF acquisition, no script feature additions.

The session opened immediately after BATON 068 wrap-up, while Mikey was reviewing the housekeeping output. He spotted the `#PROJECT_OVERHAUL` token in the CLAUDE.md H1 heading and asked whether stray `#` characters were problematic. That single observation triggered a focused fossil-cleanup pass.

#### What was wrong

Investigation found **three problem layers**:

1. **CLAUDE.md H1 heading itself.** `# Memory — #PROJECT_OVERHAUL`. Markdown-safe (the inner `#` is mid-line heading text, not a second header), but cosmetically weird and a tripwire for any tooling that treats `#` as a special character.

2. **Live path references to `00_#PROJECT_OVERHAUL`.** The literal folder name from an earlier era survived in five live config/code locations. The `#` character is a URL fragment delimiter — any tooling that URL-encodes paths would silently truncate at `#`. Real bug risk:
   - `01_module.1_warehouse/README.json` — `"folder": "00_#PROJECT_OVERHAUL/01_module.1_warehouse"` (live config value)
   - 4 Python files with path-resolution comments referencing `00_#PROJECT_OVERHAUL/`
   - 4 mirrored data-context-skill `.md` files (Windows absolute-path docs)

3. **The `project_overhaul_state.md` filename.** A fossil from the early M1–M5 module reorganization (~March 2026, BATON 030 era). The file's actual role for the last ~40 sessions has been the project's running session log + state snapshot — the original name no longer described its function.

#### Cleanup A — Removed all live `00_#PROJECT_OVERHAUL` references

- `01_module.1_warehouse/README.json` — `"folder"` value corrected to `"01_module.1_warehouse"`.
- 4 Python comments updated (`build_crosswalk_index.py`, `preprocess_concept_tags.py`, `aafp_question_reuse_investigation.py`, `batch_db_extract.py`) — all `00_#PROJECT_OVERHAUL/` → `board_prep_intel/`.
- 4 data-context-skill `.md` files updated (`skills_abilities/ite-data-context-skill/` × 2 + `00_database/schemas/ite-data-context-skill/` × 2): Windows absolute path corrected from `C:\Users\mpsch\Desktop\claude_knowledge\00_#PROJECT_OVERHAUL\...` to `C:\Users\mpsch\Desktop\board_prep_intel\...`, and a `Mac absolute` row added.
- `CLAUDE.md` line 40 (Module Map row) — corrected.
- `_index.md` line 6 (historical note) — rephrased without `00_#`.
- `.auto-memory/reference_baton_protocol.md` + mirror — 4 path examples corrected.

#### Cleanup B — Renamed `project_overhaul_state.md` → `project_session_log.md`

Both copies renamed via `git mv` (history preserved):
- `.auto-memory/project_overhaul_state.md` → `.auto-memory/project_session_log.md`
- `auto-memory-copies/project_overhaul_state.md` → `auto-memory-copies/project_session_log.md`

The file's own H1 was updated and a rename-note block added (both copies).

All dependent pointers updated to the new name:
- `CLAUDE.md` bottom "Full state" pointer line
- `.auto-memory/MEMORY.md` × 3 occurrences (index entries) + its mirror in `auto-memory-copies/MEMORY.md`
- `.auto-memory/feedback_yoy_robustness_deferred.md` + mirror
- `.auto-memory/feedback_housekeeping.md` + mirror
- `.claude/skills/session-housekeeping/agents/index-memory-writer.md` (live skill template)
- `_housekeeping/agents/index-memory-writer.md` (local reference copy)

#### Cleanup C — CLAUDE.md H1 heading

`# Memory — #PROJECT_OVERHAUL` → `# Memory — ITE Intelligence System`.

#### Intentional historical mentions preserved

Three places intentionally retain "PROJECT_OVERHAUL" as historical context (not live refs, no `00_#` prefix):
- `.auto-memory/rebuild_structuring_guidelines.md` description: "the M1-M5 module rebuild (originally tagged 'PROJECT_OVERHAUL' in March 2026)"
- `.auto-memory/project_new_architecture.md` description: same pattern
- The renamed `project_session_log.md` H1 block contains a rename-note explaining the prior name

#### Commit

All cleanup landed in one commit:
- **`a3ef508`** — "Cleanup: remove all live PROJECT_OVERHAUL fossils + rename overhaul_state → session_log"
- **27 files changed, 53 insertions, 45 deletions, 2 git renames** (history preserved).

#### Verification

Final `grep -rn "00_#PROJECT_OVERHAUL"` against live files (excluding `baton_archive/` and the frozen `_archive_/session_housekeeping_20260403.json`): **zero matches**. All remaining `PROJECT_OVERHAUL` mentions are intentional historical-context notes.

---

## SCRIPT INVENTORY

*(Inherited from BATON 068 — no new scripts, no removed scripts.)*

| Module | Category | Count | Notes |
|--------|----------|-------|-------|
| M1 | Build (Python) | 8 | unchanged |
| M1 | Maintain (Python) | 38 | unchanged |
| M1 | scripts/ root | 1 | `aafp_brq_scraper.py` |
| M2 | Python | 75 | unchanged |
| M2 | JavaScript | 6 | unchanged |
| M3 | Python | 55 | unchanged |
| M3 | JavaScript | 4 | unchanged |
| M3 | JSON config | 6 | unchanged |
| M4 | Python | 1 | unchanged |
| M5 | Python sync | 3 | unchanged |
| M5 | TypeScript/TSX | 35 | unchanged |
| M5 | SQL migrations | 5 | unchanged |

The `corpus-integrity-qc` skill scaffold (5 files) added in BATON 068 is unchanged this session. No new scripts, no removed scripts.

---

## DEFERRED FLAGS

**No new deferred flags this session.** Pure cleanup work. All flags below carry forward unchanged.

### Carry-forward from BATON 068

### DEFERRED-CORPUS-QC-LAYERS-AB-D
**Status: ACTIVE — carry forward**

Build remaining components of the corpus-integrity-qc skill: Layer A (text fidelity), Layer B (citation linkage, multi-ref-aware), Layer D (tiered fix generator), coordinator/runner, and 4 subagent prompts. Layer C is functional; scaffold + `utils.py` in place; architecture and decisions locked.

**Next action:** Implement Layer B first (highest-leverage bug fix — fixes the original ~900 false-positive bug), then Layer A detect-only, then coordinator and Layer D.

### DEFERRED-LAYER-C-CACHE-REBUILD
**Status: ACTIVE — carry forward**

1,797 Layer C Tier-1 auto-safe cache-rebuild SQL fixes pending Layer D shipping. Pure recomputation from `qid_art_xref` bridge — fully safe once generator is built.

**Next action:** Apply Tier-1 cache rebuilds once Layer D ships. Will clean up post-BATON-058 drift + initialize cache for the 208 BATON-065 new articles.

### DEFERRED-ORPHAN-XREF-QID-2024-0067
**Status: ACTIVE — carry forward**

`qid_art_xref` row `(QID-2024-0067, ART-2073, exam_year=2024)` references a QID that doesn't exist in the questions table. Likely introduced by `acquire_missing_citations.py` (BATON 065).

**Next action:** Investigate — was QID-2024-0067 renumbered post-acquisition, or is ART-2073 wrongly linked to that QID? Likely a 5-minute fix once eyeballed.

### DEFERRED-MAC-PDF-SYNC
**Status: ACTIVE — carry forward**

Mac PDF library lags Windows canonical by 569 PDFs (428 VC_fail + 141 VC_pass). PDFs are gitignored. Affects only PDF-content-dependent operations (M2 enrichment pipeline, DOCX builds, full re-extraction in Layer A). DB linkage is unaffected.

**Next action:** Sync from gdrive or rsync from the Windows machine. Stale `_dupe_archive/` content (14 files) on Mac should also be removed.

### DEFERRED-LOCKED-RULE-8-UPDATE
**Status: ACTIVE — carry forward**

Rule 8 ("Git via Desktop Commander") is Windows-specific. Now that primary workflow is Claude Code on Mac, the rule needs broadening. Suggested wording: "Git via native tooling — Bash on Mac (Claude Code), Desktop Commander on Windows. Never `--no-verify` or bypass hooks."

Leave rule verbatim for now; update on Mikey's confirmation.

**Next action:** Confirm wording with Mikey, then update Locked Rules in CLAUDE.md and next BATON.

### Carry-forward from BATON 067

### DEFERRED-CROSS-TIER-CODON-DUPES
**Status: ACTIVE — carry forward**

89 ART-IDs have codon PDFs in both VC_fail and VC_pass tiers.

**Next action:** Per ART-ID, compare both versions, keep canonical (larger file or newer mtime) in higher tier (VC_pass), move other to `_dupe_archive/`.

### DEFERRED-AFP-DATA-QC
**Status: ACTIVE — carry forward**

6 AFP articles have malformed `clean_ref` / junk DB title fields. ART-IDs: ART-0349, ART-0362, ART-0452, ART-0680, ART-1072, ART-1797.

**Next action:** DB QC pass: examine each `clean_ref`, repair `title` from extracted clean_ref content, retry `aafp_targeted_downloader.py`.

### DEFERRED-AAFP-HTTP-500-RETRY
**Status: ACTIVE — carry forward**

5 vintage AFP articles (2000-2010) blocked by AAFP server outage. ART-IDs: ART-0044, ART-0642, ART-1564, ART-1811, ART-1822.

**Next action:** Retry monthly. If still blocked after a quarter, switch to PMC fallback or AAFP Foundation library acquisition.

### DEFERRED-UNPAYWALL-CLOUDFLARE
**Status: ACTIVE — carry forward**

144 OA URLs blocked by Cloudflare even with curl-cffi chrome110 impersonation.

**Next action:** Apply NEJM-style DevTools console pattern. Group `unpaywall_results.csv` failed URLs by domain (diabetesjournals.org, ahajournals.org, etc.). Reuse `nejm_console_script.py` as template.

### DEFERRED-QID-XREF-LIBRARY-GAPS
**Status: ACTIVE — carry forward**

~801 articles still missing PDFs (down from 873 at BATON 066 close; 72 AFP closed in BATON 067).

**Next action:** Tackle remaining gaps by source_type bucket. Major buckets: Other Journal (397), Guideline/Org (107), Pediatrics (39), Annals (36), Circulation (29), BMJ (29), Lancet (12), Chest (11).

### DEFERRED-PENDING-LIST-QC
**Status: ACTIVE — carry forward**

`jama_pending.json` had ART-0302/ART-0020 URL mismatch in BATON 066. Suggests other pending lists may have similar ART→URL mismatches.

**Next action:** Spot-check 5-10 random entries per pending list. If mismatch rate >1/10, sweep all pending lists.

### DEFERRED-DESHMUKH-2021
**Status: ACTIVE — carry forward**

ART-0302 (Deshmukh 2021, J Matern Fetal Neonatal Med, DOI 10.1080/14767058.2019.1649650) paywalled at tandfonline.com.

**Next action:** Mikey needs T&F institutional access — check St. Luke's library access or interlibrary loan.

### DEFERRED-YOY-ROBUSTNESS
**Status: ACTIVE — carry forward**

`ite_analyzer_v3.py` `longitudinal_delta()` function has edge cases with dense temporal data.

**Next action:** Test with dense temporal patterns (resident with exams every 2 weeks for 12 months).

### DEFERRED-PGY-BENCHMARKS
**Status: ACTIVE — carry forward**

Awaiting PGY 1-4 data from Mikey.

**Next action:** Implement once dataset is provided.

### DEFERRED-PROGRAM-TREND
**Status: ACTIVE — carry forward**

Program-level trend analysis implementation pending.

**Next action:** Design after PGY benchmarks land.

### DEFERRED-RESIDENT-FOLDER-MIGRATION
**Status: ACTIVE — carry forward**

Investigate `resident_data/` migration to M5.

**Next action:** Audit current `resident_data/` contents and M5 ingest requirements before migrating.

### DEFERRED-SCHOLL-OLD-FORMAT
**Status: ACTIVE — carry forward**

2022/2023 score reports use old ABFM taxonomy.

**Next action:** Map old taxonomy to current body_system labels; rerun affected resident analyses.

### DEFERRED-KNOWN-DRUGS-EXPANSION
**Status: ACTIVE — carry forward**

Identify offending drug names; decide fix approach.

**Next action:** Collect concrete examples and decide whether to expand drug dictionary or change normalization.

### FLAG-33-NNN-RENAME
**Status: ACTIVE — carry forward**

nnn_XXXX ART-ID rename scheme — designed, not yet implemented.

**Next action:** Implementation deferred until prioritized.

---

## CRITICAL REMINDERS FOR NEXT SESSION

1. **The file `project_overhaul_state.md` was renamed to `project_session_log.md` in this session.** Both copies (`.auto-memory/` and `auto-memory-copies/`) renamed via `git mv` — history preserved. Session-housekeeping skill templates already updated to target the new name. Do not look for `project_overhaul_state.md` — it no longer exists.

2. **`#PROJECT_OVERHAUL` is now gone from all live config/code.** Only intentional historical-context mentions remain in `rebuild_structuring_guidelines.md`, `project_new_architecture.md`, and the renamed file's own H1 rename-note block. If you see the literal string `00_#PROJECT_OVERHAUL` anywhere in live code/config, it is a regression and should be fixed.

3. **CLAUDE.md H1 heading is now `# Memory — ITE Intelligence System`** (no `#PROJECT_OVERHAUL`).

4. **The corpus-integrity-qc skill is registered live but partial.** Only Layer C is functional. Do not run the skill end-to-end yet — Layer B + Layer A + Layer D + coordinator are still missing. Continuing the build is the immediate next-session item.

5. **Mac DB is now canonical** (post-BATON-068 swap). The stale Apr-16 copy is preserved at `00_database/db/_archive_/ite_intelligence_stale_20260416.db` — do not use; it is 3 weeks behind reality.

6. **Mac PDF library still lags Windows by 569 files** (DEFERRED-MAC-PDF-SYNC). PDFs are gitignored — sync from gdrive or rsync from Windows before running M2 enrichment or Layer A spot re-extraction at scale.

7. **No DB or schema changes this session.** Pure config/docs cleanup. Row counts identical to BATON 068.

---

## NEXT STEPS

### Immediate (next session)
1. **Continue corpus-integrity-qc build: Layer B** (citation linkage, multi-reference set-comparison) — the layer that actually fixes the original ~900 false-positive bug. Reuse `connect_db_readonly()` from `utils.py`. Compare DB bag vs critique bag per QID using set-containment semantics.
2. **Investigate ORPHAN_XREF (QID-2024-0067 / ART-2073, exam_year 2024)** — likely 5-minute fix once we look at it.

### Short-term (this week)
3. **Layer A (text fidelity)** + **coordinator** + **Layer D (tiered fix generator)** — round out the corpus-integrity-qc skill.
4. **Apply Tier-1 Layer C cache rebuilds** — 1,797 auto-safe `UPDATE articles SET ...` statements once Layer D ships. Cleans up post-BATON-058 drift + initializes cache for BATON-065 new articles.
5. **Mac PDF sync** — pull 569 missing PDFs from Windows or gdrive.
6. **Re-run all 7 resident analyses** — still carrying from BATON 065+066+067.

### Medium-term (next 2 weeks)
7. **AAFP BRQ extension** of corpus-integrity-qc (v2): Layer C structural integrity easy port; Layer B inapplicable — no AAFP critique PDFs; Layer A easy port.
8. **Continue 801-article gap closure** by source_type buckets.
9. **Apply NEJM DevTools pattern** to 144 unpaywall Cloudflare-blocked URLs.

---

## LOCKED RULES (Never Override Without Mikey Confirming)

*(Copied verbatim from BATON 068. No changes this session. Rule 8 is flagged for update in DEFERRED-LOCKED-RULE-8-UPDATE but rule text remains verbatim pending Mikey's confirmation.)*

1. **Fix the data, not the code.** If a script gets complex to handle messy data → clean the data upstream instead.
2. **VC gate = sole criterion** for right_click tier. DB membership alone is not sufficient.
3. **Source data is protected.** DB + PDFs + VC gate survive everything. Derived files are disposable.
4. **Dynamic paths only.** Python: `SCRIPT_DIR = Path(__file__).resolve().parent; PROJECT_ROOT = SCRIPT_DIR.parent.parent`. JS: `path.resolve(__dirname, "../../")`.
5. **No de novo JS.** Existing JS scripts migrate fine. New code = Python only (relaxed: use JS when needed, flag if clutter accumulates).
6. **BATON first.** Read the active BATON before any work. It has deferred flags and current state.
7. **QC after every integration.** Schema-level column-by-column population comparison, old cohort vs new.
8. **Git via Desktop Commander.** Claude can run git commits via Desktop Commander Python subprocess (helper: `claude_knowledge/git_runner.py`). Cannot `rm` NTFS files — deletions still require Windows Explorer/terminal.
9. **`shutil.rmtree` is BANNED.** Use explicit file-by-file deletion or PowerShell Remove-Item. shutil.rmtree bypasses Recycle Bin and is irreversible.
10. **Strategy 0 in every enricher.** Codon parse is always the first matching strategy.
11. **Schemas before scripts.** SQL `CREATE TABLE` defined before build scripts are written.
12. **`_normalize_concept()` fallback = first-letter capitalize only.** Never `.title()` — it mangles acronyms (HIV → Hiv, IBS-D → Ibs-D). Use `stripped[0].upper() + stripped[1:]`. Add new synonym entries for any canonical form that needs resolution.
13. **ICD-10 enrichment is invisible.** `icd10_profile` is passed to `match_practice_questions_v3()` as a hidden scoring signal and must never appear in the resident report. ICD-10 codes are internal precision machinery only.
14. **Word docs use `word_doc_defaults.py`.** All Python scripts that generate `.docx` files must `from word_doc_defaults import *` and apply the St. Luke's color palette, Aptos font, and helper functions defined there.

---

## FOR THE REPO (Git Notes)

- **Branch:** claude/xenodochial-pike-667d6a (worktree off main)
- **Latest commit hash (pre-housekeeping-commit):** `a3ef508`
- **Session commit history:**
  - `2bf681c` — BATON 068 main content
  - `3aa2111` — BATON 068 git-hash backfill
  - `284b210` — BATON 068 cleanup (00a_database → 00a_db_gdrive_landing rename + .gitignore)
  - `a3ef508` — **THIS SESSION'S CLEANUP COMMIT** (27 files, PROJECT_OVERHAUL fossils removed + `project_overhaul_state.md` renamed to `project_session_log.md`)
- **Unpushed changes:** Pending BATON 069 housekeeping commit (this BATON file + manifests + auto-memory updates).

---

**End BATON 069.**
*Pure cleanup session — no functional changes. Next session priority: corpus-integrity-qc Layer B.*
