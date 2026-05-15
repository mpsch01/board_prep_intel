# BATON 068 — 2026-05-15 — Claude Code Migration + Corpus QC Built

**Active Session Handoff Document for board_prep_intel**

---

## Session Overview

| Item | Value |
|------|-------|
| **Date** | 2026-05-15 |
| **Previous BATON** | BATON_active_067_20260507_afp_pdf_acquisition_72_articles_closed.md |
| **Git Hash (pre-commit)** | e6cb648 |
| **Branch** | claude/xenodochial-pike-667d6a (worktree off main; main tip = e6cb648) |
| **Primary Goal** | Validate Cowork → Claude Code migration; rebuild article-citation-qc skill to fix multi-reference bug |
| **Status** | Successful — Claude Code adopted as primary workflow; corpus-integrity-qc Layer C functional and smoke-tested; canonical DB restored via safe swap |

---

## DATABASE STATE

(Canonical state restored this session via DB swap — see Stream 3 in Session Summary.)

| Table | Rows | Notes |
|-------|------|-------|
| articles | 2,206 | matches BATON 067 |
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

**Next ART-ID:** ART-2208
**No schema changes this session.** All DB activity was read-only (corpus QC smoke test + canonical-state swap).

---

## PDF LIBRARY

**Mac local state — lags Windows canonical by 569 files.** PDFs are gitignored; sync pending.

| Tier | Mac | Windows (BATON 067) | Notes |
|------|-----|----------------------|-------|
| VC_fail | 628 | 1,056 | Mac missing 428; sync pending |
| VC_pass | 168 | 309 | Mac missing 141; sync pending |
| local_lite | 117 | 117 | Synced |
| right_click | 58 | 58 | Synced |
| _dupe_archive | 14 | 0 | Mac has stale files BATON 067 deleted on Windows; cleanup pending |
| AAFP | 15 | 15 | Synced |
| ite_exams | 16 | 16 | All 8 years (2018–2025) × MC + critique |
| **ITE active total (Mac)** | **971** | **1,540** | (VC_fail + VC_pass + local_lite + right_click) |

See **DEFERRED-MAC-PDF-SYNC** below.

---

## Session Summary

### Stream 1: Cowork → Claude Code Migration Validated

Confirmed the Mac/Claude Code environment is suitable as the primary platform for board_prep_intel work:

- **CLAUDE.md auto-injects every turn.** No manual read needed at session start — the harness pulls it automatically and the contents are visible in system reminders.
- **All `.skill` files in `.claude/skills/` are discoverable.** New skill scaffolding (corpus-integrity-qc) was registered live during the session without restart.
- **board-startup runs fast on Mac.** Parallel file reads + native SSD beat the Windows + Cowork sandbox path.
- **Sandbox-induced DB lockouts no longer apply.** Native sqlite3 access works. Only standard SQLite contention remains (e.g., DB Browser holding a write transaction can still block writers).
- **Worktrees + git are first-class via Bash.** No Desktop Commander Python-subprocess helper needed for git operations on Mac.

**Decision:** Adopt Claude Code as the primary workflow. Cowork retained for mobile/web access and non-project productivity tooling.

### Stream 2: Built corpus-integrity-qc Skill (Replacement for article-citation-qc)

#### Diagnosed root-cause bug in article-citation-qc

BATON 058 reported 932 QID_MISMATCH findings, framed as "rare parser error" and applied as corrections. The true cause is a structural bug in `run_citation_qc.py`:

- Lines 207–210 load `qid_art_xref` into a Python dict `{qid: article_id}`.
- A dict can only hold ONE article per QID.
- BATON 058 rebuilt `qid_art_xref` as multi-reference (avg 1.6 refs/q), so the dict silently overwrites — last row per QID wins, others get false-flagged as mismatches.
- Math check: 938 single-ref QIDs + (459+145+31+14) × extra-refs ≈ ~975 false-positive opportunities. Matches the reported 932 almost exactly.

Conclusion: BATON 058's "corrections" from this skill were largely structural artifacts of the dict overwrite, not real article-citation mismatches.

#### Designed new corpus-integrity-qc skill with 4 layers + multi-agent architecture

- **Layer A (text fidelity):** encoding artifacts (the "Wing-dings" problem), truncation candidates, format drift, optional spot re-extract from source PDFs.
- **Layer B (citation linkage):** multi-ref-aware bag comparison between `qid_art_xref` and critique staging.
- **Layer C (structural integrity):** xref ↔ articles cache drift (qid_list, citation_count, exam_years, unique_years, orphan rows, etc.).
- **Layer D (report + remediation):** tiered SQL fixes — Tier 1 auto-safe / Tier 2 review-required / Tier 3 manual.

Decisions locked:
- v1 scope: ITE only (AAFP BRQ deferred to v2).
- Layer A approach: hybrid (detect-only scan + spot re-extract on flagged QIDs).
- Mismatch semantics: set-containment (critique-driven); EXTRA_IN_DB demoted to Tier 3 informational.
- SQL gating: `INSERT OR IGNORE` for match_score=1.0 only; fuzzy matches generate commented-out review SQL.

#### Built so far

Scaffold under `.claude/skills/corpus-integrity-qc/`:
- `SKILL.md`
- `references/qc_rules.md`
- `references/fix_tiers.md`
- `scripts/utils.py` — salvaged `ENCODING_FIXES` table (15 entries, canonicalized from `build_custom_question_set.py:_ENCODING_FIXES`), `AUTHOR_STOP_WORDS` set, `extract_title_from_clean_ref()`, `is_truncated_title()`, `correct_author_from_clean_ref()`, `connect_db_readonly()`
- `scripts/layer_c_structural.py` — **fully functional, smoke-tested against canonical DB**

#### Layer C smoke-test result (post-swap canonical DB, 2,206 articles / 2,710 xref)

Total findings: **1,798**.

| Finding | Count | Notes |
|---------|-------|-------|
| ZERO_CITATION_LINKED | 208 | The BATON 065 newly-acquired articles never had `citation_count` cache populated |
| UNIQUE_YEARS_MISMATCH | 446 | |
| CITATION_COUNT_MISMATCH | 415 | |
| QID_LIST_CACHE_DRIFT | 359 | |
| EXAM_YEARS_DRIFT | 343 | |
| UNLINKED_CITED_ARTICLE | 26 | Pre-existing, unchanged from old DB |
| ORPHAN_XREF | 1 | **NEW BUG** — see DEFERRED-ORPHAN-XREF-QID-2024-0067 |

New bug surfaced: `qid_art_xref` row references `QID-2024-0067` with `ART-2073` (exam_year 2024), but `QID-2024-0067` does not exist in the questions table. Likely an `acquire_missing_citations.py` (BATON 065) typo or a renumbered question.

### Stream 3: DB Swap (Canonical State Restored)

Discovered the Mac DB at `00_database/db/ite_intelligence.db` was 3 weeks stale:
- mtime Apr 16, articles=1,998, xref=2,485 (pre-BATON-065 state).

User staged the canonical gdrive copy at `00a_database/db/ite_intelligence.db`:
- mtime May 6, articles=2,206, xref=2,710 (matches BATON 067).

Executed a safe swap:
- Old DB → `00_database/db/_archive_/ite_intelligence_stale_20260416.db` (preserved as backup).
- New DB → `00_database/db/ite_intelligence.db` (canonical location).

Verified post-swap counts match BATON 067 exactly. `00a_database/db/ite_intelligence.db` no longer exists; `00a_database/` directory remains in place pending a later decision on whether to remove or repurpose as a gdrive landing zone.

---

## SCRIPT INVENTORY

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
| M5 | TypeScript/TSX | 31 | unchanged |
| M5 | SQL migrations | 5 | unchanged |

### New this session (in worktree, currently untracked — to be committed in this housekeeping wave)

```
.claude/skills/corpus-integrity-qc/
├── SKILL.md
├── references/
│   ├── qc_rules.md
│   └── fix_tiers.md
└── scripts/
    ├── utils.py
    └── layer_c_structural.py
```

No script deletions this session.

---

## DEFERRED FLAGS

### NEW THIS SESSION

### DEFERRED-CORPUS-QC-LAYERS-AB-D
**Status: ACTIVE — carry forward**

Build remaining components of the corpus-integrity-qc skill:
- **Layer A** (text fidelity) — detect-only first; spot re-extract uses pdfplumber on `01_module.1_warehouse/ite_exams/YYYY_critique.pdf`.
- **Layer B** (citation linkage, multi-ref-aware) — the layer that actually fixes the original ~900 false-positive bug. Reuse `connect_db_readonly()` from `utils.py`. Compare DB bag vs critique bag per QID using set-containment semantics.
- **Layer D** (tiered fix generator) — produces `fixes.sql` partitioned by Tier 1 (auto-safe) / Tier 2 (review-required) / Tier 3 (manual).
- **Coordinator/runner** — fans out 3 audit agents in parallel via Agent tool, merges findings JSONs.
- **Subagent prompts** in `.claude/skills/corpus-integrity-qc/agents/` — 3 audit agents (Layers A/B/C) + 1 fix-applier.

Layer C is complete and validated; scaffold + `utils.py` are in place; architecture and decisions are locked.

**Next action:** Implement Layer B first (highest-leverage bug fix), then Layer A detect-only, then coordinator and Layer D.

### DEFERRED-LAYER-C-CACHE-REBUILD
**Status: ACTIVE — carry forward**

1,798 Layer C findings ready to fix once Layer D ships:
- Tier 1 auto-safe SQL: 1,797 cache rebuilds (pure recomputation from `qid_art_xref` bridge — fully safe).
- 1 ORPHAN_XREF needs human investigation before SQL (see next flag).

**Next action:** Apply Tier-1 cache rebuilds once Layer D generator is built. Will clean up post-BATON-058 drift + initialize cache for the 208 BATON-065 new articles.

### DEFERRED-ORPHAN-XREF-QID-2024-0067
**Status: ACTIVE — carry forward**

`qid_art_xref` row `(QID-2024-0067, ART-2073, exam_year=2024)` references a QID that doesn't exist in the questions table. Likely introduced by `acquire_missing_citations.py` (BATON 065).

**Next action:** Investigate — was QID-2024-0067 renumbered post-acquisition, or is ART-2073 wrongly linked to that QID? Likely a 5-minute fix.

### DEFERRED-MAC-PDF-SYNC
**Status: ACTIVE — carry forward**

Mac PDF library lags Windows by 569 PDFs (428 VC_fail + 141 VC_pass). PDFs are gitignored. Affects only PDF-content-dependent operations (M2 enrichment pipeline, DOCX builds, full re-extraction in Layer A). DB linkage is unaffected.

**Next action:** Sync from gdrive or rsync from the Windows machine. Stale `_dupe_archive/` content (14 files) on Mac should also be removed.

### DEFERRED-LOCKED-RULE-8-UPDATE
**Status: ACTIVE — carry forward**

Rule 8 ("Git via Desktop Commander") is Windows-specific. Now that primary workflow is Claude Code on Mac, the rule needs broadening. Suggested wording: "Git via native tooling — Bash on Mac (Claude Code), Desktop Commander on Windows. Never `--no-verify` or bypass hooks."

Leave rule verbatim for now; update on Mikey's confirmation.

**Next action:** Confirm wording with Mikey, then update Locked Rules in CLAUDE.md and next BATON.

### CARRY-FORWARD FROM BATON 067

### DEFERRED-CROSS-TIER-CODON-DUPES
**Status: ACTIVE — carry forward**

89 ART-IDs have codon PDFs in both VC_fail and VC_pass tiers (created by `aafp_fill_gaps.py` title-similarity threshold of 0.72 being too strict — articles already on disk in VC_fail got re-downloaded into VC_pass).

**Next action:** Per ART-ID, compare both versions, keep canonical (larger file or newer mtime) in higher tier (VC_pass), move other to `_dupe_archive/`.

### DEFERRED-AFP-DATA-QC
**Status: ACTIVE — carry forward**

6 AFP articles have malformed `clean_ref` / junk DB title fields. Blocks both URL construction and CrossRef lookup. ART-IDs: ART-0349 (EBM glossary), ART-0362 (Eichelberger), ART-0452 (Franck), ART-0680 (Killeen), ART-1072 (Risk), ART-1797 (Screening).

**Next action:** DB QC pass: examine each `clean_ref`, repair `title` from extracted clean_ref content, retry `aafp_targeted_downloader.py`.

### DEFERRED-AAFP-HTTP-500-RETRY
**Status: ACTIVE — carry forward**

5 vintage AFP articles (2000-2010) blocked by AAFP server outage. URLs validate correctly via citation_volume/issue/firstpage meta but `.pdf` returns HTTP 500. AAFP-side confirmed via "Technical Issues" page. ART-IDs: ART-0044 (2007), ART-0642 (2000), ART-1564 (2000), ART-1811 (2000), ART-1822 (2010).

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

**Next action:** Spot-check 5-10 random entries: open URL, verify resulting filename matches expected author. If mismatch rate >1/10, sweep all pending lists.

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

1. **Mac is now the primary platform.** Sandbox-induced DB lockouts are gone, but normal SQLite locking still applies — if DB Browser for SQLite is open with a write transaction, sqlite3 in Python will be blocked. Close or commit changes before running pipelines.

2. **The canonical DB lives at `00_database/db/ite_intelligence.db`** (post-swap this session). The stale Apr-16 copy is at `00_database/db/_archive_/ite_intelligence_stale_20260416.db` — do not use; it is 3 weeks behind reality.

3. **The corpus-integrity-qc skill is registered live but partial.** Only Layer C is functional. Do not run the skill end-to-end yet — Layer B + Layer A + Layer D + coordinator are missing. Continuing the build is the immediate next-session item.

4. **The article-citation-qc skill (old) is still installed but should not be re-run.** It has a confirmed dict-overwrite bug that produces ~900 false-positive QID_MISMATCH findings against multi-reference xref tables. BATON 058's reported corrections from this skill were largely structural artifacts, not real mismatches.

5. **Mac PDF library is incomplete.** 569 PDFs from BATONs 065-067 live only on the Windows machine (gitignored). Sync before running M2 enrichment or Layer A spot re-extraction at scale.

6. **Worktree workflow.** This session was conducted in worktree `xenodochial-pike-667d6a`. The corpus-integrity-qc skill + new BATON live in the worktree. After commit, the worktree will be merged to main. Next session can start fresh from main or continue in the worktree.

---

## NEXT STEPS

### Immediate (next session)
1. **Continue corpus-integrity-qc build: Layer B** (citation linkage, multi-reference set-comparison) — the layer that actually fixes the original ~900 false-positive bug. Reuse `connect_db_readonly()` from `utils.py`. Compare DB bag vs critique bag per QID.
2. **Layer A** (text fidelity — detect-only first; spot re-extract uses pdfplumber on `01_module.1_warehouse/ite_exams/YYYY_critique.pdf`).
3. **Coordinator/runner** that fans out to 3 audit agents in parallel via Agent tool, merges findings JSONs.
4. **Tiered fix generator (Layer D)** producing `fixes.sql` partitioned by Tier 1/2/3.
5. **Subagent prompts** in `.claude/skills/corpus-integrity-qc/agents/` (3 audit + 1 fix-applier).

### Short-term (this week)
6. **Investigate ORPHAN_XREF (QID-2024-0067)** — likely 5-minute fix once we look at it.
7. **Apply Tier-1 cache rebuilds from Layer C** — 1,797 auto-safe `UPDATE articles SET ...` statements once Layer D ships. Cleans up post-BATON-058 drift + initializes cache for BATON-065 new articles.
8. **Mac PDF sync** — pull 569 missing PDFs from Windows or gdrive.
9. **Re-run all 7 resident analyses** — still carrying from BATON 065+066+067.

### Medium-term (next 2 weeks)
10. **AAFP BRQ extension** of corpus-integrity-qc (Layer C structural integrity easy port; Layer B inapplicable — no AAFP critique PDFs; Layer A easy port).
11. **Continue 801-article gap closure** by source_type buckets.
12. **Monthly AAFP HTTP-500 retries.**

---

## LOCKED RULES (Never Override Without Mikey Confirming)

*(Copied verbatim from BATON 067. Rule 8 is flagged for update in DEFERRED-LOCKED-RULE-8-UPDATE but rule text remains verbatim pending Mikey's confirmation.)*

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
- **Latest commit hash (pre-housekeeping):** e6cb648 (main branch tip; new BATON + skill scaffold will be a new commit this session)
- **Unpushed changes:**
  - New BATON 068 (this file)
  - corpus-integrity-qc skill scaffold (5 files):
    - `.claude/skills/corpus-integrity-qc/SKILL.md`
    - `.claude/skills/corpus-integrity-qc/references/qc_rules.md`
    - `.claude/skills/corpus-integrity-qc/references/fix_tiers.md`
    - `.claude/skills/corpus-integrity-qc/scripts/utils.py`
    - `.claude/skills/corpus-integrity-qc/scripts/layer_c_structural.py`
  - Updated CLAUDE.md, README.md, REPO_MAP.md, README.json, _index.md, .auto-memory/* files (manifest-writer pass)
  - DB swap: archived stale Apr-16 DB to `00_database/db/_archive_/ite_intelligence_stale_20260416.db` (gitignored — `.db` is in `.gitignore`)
- **Gitignored changes (do not stage):**
  - `00_database/db/ite_intelligence.db` (canonical post-swap)
  - `00_database/db/_archive_/ite_intelligence_stale_20260416.db` (preserved backup)

---

**End BATON 068.**
*Handoff ready for next Claude instance. Read this first before any work.*
