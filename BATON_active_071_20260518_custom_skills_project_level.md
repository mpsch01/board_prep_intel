# BATON 071 — 2026-05-18 — Custom Skills Promoted to Project Level

**Active Session Handoff Document for board_prep_intel**

---

## Session Overview

| Item | Value |
|------|-------|
| **Date** | 2026-05-18 |
| **Previous BATON** | BATON_active_070_20260515_corpus_qc_skill_v1.md |
| **Git Hash (pre-housekeeping-commit)** | fdf50d3 |
| **Branch** | claude/frosty-napier-bfb7b2 (worktree off main) |
| **Primary Goal** | Make all board_prep_intel-specific custom skills available as bare slash commands by copying them into project-level `.claude/skills/` (previously only reachable via the `anthropic-skills:` namespace prefix). |
| **Status** | Complete — 5 skills copied into `.claude/skills/`, project-level slash menu now exposes the full custom set without the namespace prefix. |

---

## DATABASE STATE

*(Inherited from BATON 070 — no DB writes, no schema changes, no row changes this session. All 15 audited tables match BATON 070 exactly.)*

| Table | Rows | Notes |
|-------|------|-------|
| articles | 2,206 | unchanged |
| questions (ITE) | 1,639 | unchanged |
| aafp_questions | 1,221 | unchanged |
| qid_art_xref | 2,710 | unchanged |
| aafp_qid_art_xref | 864 | unchanged |
| article_icd10 | 4,959 | unchanged |
| question_icd10 | 5,774 | unchanged |
| aafp_question_icd10 | 4,753 | unchanged |
| clinical_pathways | 4,959 | unchanged |
| pubmed_pmid_cache | 344 | unchanged |
| article_icd10_vec | 1,757 | unchanged |
| question_icd10_vec | 2,747 | unchanged |
| icd10_vec | 2,219 | unchanged |
| intersection_centroid_vec | 158 | unchanged |
| article_currency | 2,206 | unchanged |

**Next ART-ID:** ART-2208 (unchanged). **No schema changes. No row changes.**

---

## PDF LIBRARY

*(Inherited from BATON 070 — Mac local still lags Windows canonical by 567 files. PDFs gitignored; sync pending. Counts verified this session via direct `find` count and match the BATON 070 / DEFERRED-MAC-PDF-SYNC delta within the expected range — no regression.)*

| Tier | Mac (verified BATON 071) | Windows canonical | Notes |
|------|--------------------------|-------------------|-------|
| VC_fail | 630 | 1,056 | DEFERRED-MAC-PDF-SYNC |
| VC_pass | 168 | 309 | DEFERRED-MAC-PDF-SYNC |
| local_lite | 117 | 117 | Synced |
| right_click | 58 | 58 | Synced |
| AAFP | 15 | 15 | Synced |
| ite_exams | 16 | 16 | Synced |
| **ITE active total (Mac)** | **973** | **1,540** | (VC_fail + VC_pass + local_lite + right_click) |

---

## Session Summary

### Small infrastructure session — promoted 5 custom skills from plugin-only to project-level so they appear as bare slash commands without the `anthropic-skills:` prefix. No DB, PDF, schema, or pipeline-script changes.

#### What changed

User noticed `/board-startup` wasn't autocompleting from the bare slash menu — only `/anthropic-skills:board-startup` resolved. Root cause: project-level skills (in `.claude/skills/`) appear bare; plugin skills require the namespace prefix. Two board_prep_intel customs were already overridden into the project (`session-housekeeping`, `corpus-integrity-qc`) plus two `.skill`-format zips (`custom-question-set.skill`, `ite-exam-series.skill`); the remaining 5 board_prep_intel-specific skills were still plugin-only.

**Action:** copied 5 skill directories from the Claude Code plugin store into `.claude/skills/`:

| Skill | Files | Source |
|---|---|---|
| `board-startup/` | SKILL.md (78 lines) | Session orientation — `orient me` / `catch me up` / `BATON` triggers |
| `body-system-qc/` | SKILL.md (229 lines) | Two-layer Claude CoT + SVM body_system reclassifier |
| `article-citation-qc/` | SKILL.md (164 lines) + `references/` + `scripts/` | Pre-corpus-qc article QC pipeline (still useful as a focused QID↔article check) |
| `baton-pipeline-qc/` | SKILL.md (133 lines) | BATON-aware pipeline operator |
| `repo-error-review/` | SKILL.md (217 lines) | Read-only repo-wide audit |

Plugin-namespace versions remain available too — they live in the Claude Code plugin store and continue to load as `anthropic-skills:<name>`. The project copies override / shadow nothing; the slash menu just now exposes both bare and namespaced entries for these 5 skills.

#### What stays plugin-only (intentional)

General-purpose Anthropic skills (not project-specific): `docx`, `pdf`, `pptx`, `xlsx`, `skill-creator`, `theme-factory`, `consolidate-memory`, `doc-coauthoring`, `exa-research-search`, `methodology-scout`, `setup-cowork`, `schedule`. These are best invoked via the `anthropic-skills:` prefix so the project skill list stays focused on board_prep_intel work.

#### Project skill inventory (final, BATON 071)

```
.claude/skills/
├── article-citation-qc/        (NEW BATON 071 — promoted from plugin)
├── baton-pipeline-qc/          (NEW BATON 071 — promoted from plugin)
├── board-startup/              (NEW BATON 071 — promoted from plugin)
├── body-system-qc/             (NEW BATON 071 — promoted from plugin)
├── corpus-integrity-qc/        (built BATON 068+070, 15 files, V1 complete)
├── custom-question-set.skill   (cowork zip — BATON 064)
├── ite-exam-series.skill       (cowork zip — BATON 064)
├── repo-error-review/          (NEW BATON 071 — promoted from plugin)
└── session-housekeeping/       (V2 override of upstream skill — BATON 070)
```

9 entries total (7 directories with SKILL.md + 2 zip-format `.skill` files).

#### Files touched this session

```
New (untracked):
  .claude/skills/article-citation-qc/      (SKILL.md + references/ + scripts/)
  .claude/skills/baton-pipeline-qc/        (SKILL.md)
  .claude/skills/board-startup/            (SKILL.md)
  .claude/skills/body-system-qc/           (SKILL.md)
  .claude/skills/repo-error-review/        (SKILL.md)

Modified (this housekeeping pass):
  CLAUDE.md                                (Active State BATON pointer + git hash)
  README.md                                (BATON pointer + git hash)
  README.json                              (BATON pointer + git hash)
  REPO_MAP.md                              (BATON pointer + skill inventory)
  _index.md                                (header + BATON 071 entry)
  .auto-memory/MEMORY.md                   (header date + active BATON reference)
  .auto-memory/project_session_log.md      (Session Notes BATON 071 prepended)
  .auto-memory/project_current_db_state.md (header date + DB Changes BATON 071 block)
  auto-memory-copies/*                     (synced from .auto-memory/)

Renamed (git mv):
  BATON_active_070_20260515_corpus_qc_skill_v1.md → baton_archive/
```

---

## SCRIPT INVENTORY

*(M1/M2/M3/M4/M5 scripts unchanged. Skill scripts unchanged. Only thing new is 5 skill directories under `.claude/skills/`.)*

| Module | Category | Count | Δ |
|--------|----------|-------|---|
| M1 | Build (Python) | 8 | unchanged |
| M1 | Maintain (Python) | 38 | unchanged |
| M1 | scripts/ root | 1 | unchanged |
| M2 | Python | 75 | unchanged |
| M2 | JavaScript | 6 | unchanged |
| M3 | Python | 55 | unchanged |
| M3 | JavaScript | 4 | unchanged |
| M3 | JSON config | 6 | unchanged |
| M4 | Python | 1 | unchanged |
| M5 | Python sync | 3 | unchanged |
| M5 | TypeScript/TSX | 35 | unchanged |
| M5 | SQL migrations | 5 | unchanged |
| `.claude/skills/` (project-level) | Directories with SKILL.md | **7** | **+5** (board-startup, body-system-qc, article-citation-qc, baton-pipeline-qc, repo-error-review) |
| `.claude/skills/` (project-level) | Cowork `.skill` zips | 2 | unchanged |

---

## DEFERRED FLAGS

### Newly opened this session
**None.** Trivial infrastructure change with no new tech debt.

### Closed this session
**None.** Slash-menu UX improvement; no architectural flags resolved.

### Carry-forward from BATON 070 (all unchanged)

- **DEFERRED-LAYER-A4-PDF-DIFF** — Layer A4 (PDF-diff re-extract) deferred to corpus-qc V1.1.
- **DEFERRED-LAYER-C-CACHE-REBUILD** — 1,797 Layer C Tier-1 cache rebuild SQL pending application via fix-applier (`--tier 1 --approved-by-user 1`).
- **DEFERRED-ORPHAN-XREF-QID-2024-0067** — single ORPHAN_XREF row to investigate then likely DELETE.
- **DEFERRED-MAC-PDF-SYNC** — Mac PDF library lags Windows canonical by 567 PDFs (verified this session: 426 VC_fail + 141 VC_pass = 567; close to the 569 figure logged in BATON 070).
- **DEFERRED-LOCKED-RULE-8-UPDATE** — Rule 8 needs Mac/Claude Code broadening.
- **DEFERRED-CROSS-TIER-CODON-DUPES** — 89 ART-IDs in both VC_fail and VC_pass tiers.
- **DEFERRED-AFP-DATA-QC** — 6 articles with malformed clean_ref / junk title.
- **DEFERRED-AAFP-HTTP-500-RETRY** — 5 vintage AFP articles blocked by AAFP server outage.
- **DEFERRED-UNPAYWALL-CLOUDFLARE** — 144 OA URLs blocked by Cloudflare.
- **DEFERRED-QID-XREF-LIBRARY-GAPS** — ~801 articles missing PDFs (246 UNMATCHED_CITATION findings from Layer B).
- **DEFERRED-PENDING-LIST-QC** — spot-check pending lists for URL-mismatch defects.
- **DEFERRED-DESHMUKH-2021** — ART-0302 paywalled at tandfonline.
- **DEFERRED-YOY-ROBUSTNESS** — `longitudinal_delta()` edge cases.
- **DEFERRED-PGY-BENCHMARKS** — awaiting PGY 1-4 data.
- **DEFERRED-PROGRAM-TREND** — pending PGY benchmarks.
- **DEFERRED-RESIDENT-FOLDER-MIGRATION** — investigate `resident_data/` migration to M5.
- **DEFERRED-SCHOLL-OLD-FORMAT** — 2022/2023 score reports use old ABFM taxonomy.
- **DEFERRED-KNOWN-DRUGS-EXPANSION** — identify offending drug names; decide fix approach.
- **FLAG-33-NNN-RENAME** — nnn_XXXX ART-ID rename scheme designed, not yet implemented.

---

## CRITICAL REMINDERS FOR NEXT SESSION

1. **Next session is the corpus-integrity-qc V1 testing pass** — BATON 070's top "Immediate" item is still the right starting move (run `run_qc.py` end-to-end on canonical, spot-check Tier 1, apply via `fix-applier` with `--tier 1 --approved-by-user 1`). Nothing about this session changes that priority order.

2. **Restart Claude Code to pick up the new project skills.** The 5 new directories will not appear in the bare slash menu until skills re-index on session start.

3. **`board-startup` is now bare.** At the start of next session, typing `/board-startup` (no namespace) should resolve. If for some reason it doesn't, fall back to `/anthropic-skills:board-startup` — same skill content, same triggers.

4. **PDF count verification revealed no regression.** The 567-PDF Mac-lag is the same DEFERRED-MAC-PDF-SYNC delta that's been carried since BATON 068 (originally logged as 569). Numbers in CLAUDE.md / README / `_index.md` remain authoritative for canonical state.

5. **No code touched in M1/M2/M3.** All `from import` chains, all SCRIPT_DIR resolutions, all path assumptions — untouched. This session was scoped to a `.claude/skills/` directory edit only.

---

## NEXT STEPS

### Immediate (next session)
1. **`/board-startup`** to load BATON 071 + verify the bare slash command resolves.
2. **Resume BATON 070 Item 1** — run `run_qc.py` end-to-end on canonical DB.
3. **Spot-check 10 random Tier 1 SQL statements** before applying.
4. **Apply Tier 1 via `fix-applier`** with `--tier 1 --approved-by-user 1`. Closes DEFERRED-LAYER-C-CACHE-REBUILD.
5. **Re-run `run_qc.py`** post-apply to confirm cache-rebuild findings drop to ~0.
6. **Investigate ORPHAN_XREF QID-2024-0067 / ART-2073.** Closes DEFERRED-ORPHAN-XREF-QID-2024-0067.

### Short-term (this week)
7. **Re-run all 7 resident analyses** — still carrying from BATON 065+066+067.
8. **Mac PDF sync** — pull 567 missing PDFs from Windows/gdrive.
9. **Tier 2 review pass** — eyeball 66 commented statements.
10. **Cross-tier codon dedupe** — 89 ART-IDs in both VC_fail and VC_pass.

### Medium-term
11. **AAFP BRQ extension of corpus-integrity-qc (v2)** — port Layer C trivially, Layer A easily; replace Layer B with per-article scalar checks.
12. **Continue 801-article gap closure** by source_type buckets.
13. **Apply NEJM DevTools pattern** to 144 unpaywall Cloudflare-blocked URLs.

---

## LOCKED RULES (Never Override Without Mikey Confirming)

*(Verbatim from BATON 070. No changes this session. Rule 8 still flagged for update in DEFERRED-LOCKED-RULE-8-UPDATE.)*

1. **Fix the data, not the code.**
2. **VC gate = sole criterion** for right_click tier.
3. **Source data is protected.** DB + PDFs + VC gate survive everything.
4. **Dynamic paths only.** `SCRIPT_DIR = Path(__file__).resolve().parent; PROJECT_ROOT = SCRIPT_DIR.parent.parent`.
5. **No de novo JS.** New code = Python only.
6. **BATON first.**
7. **QC after every integration.**
8. **Git via Desktop Commander.** *(Flagged for update — Mac/Claude Code workflow now primary.)*
9. **Strategy 0 in every enricher.**
10. **Schemas before scripts.**
11. **`shutil.rmtree` is BANNED.**
12. **`_normalize_concept()` fallback = first-letter capitalize only.**
13. **ICD-10 enrichment is invisible.**
14. **Word docs use `word_doc_defaults.py`.**

---

## FOR THE REPO (Git Notes)

- **Branch:** claude/frosty-napier-bfb7b2 (worktree off main)
- **Pre-housekeeping commit hash:** `fdf50d3` (BATON 070 / "Add project-level session-housekeeping skill (V2) with Item 12 GitHub syncing" — the latest pre-session commit)
- **Session commit (housekeeping):** `79e32a0` — *"BATON 071 — Promote 5 custom skills to project level"* — 21 files changed, 1,914 insertions, 54 deletions, 1 rename (BATON 070 → baton_archive/), 5 skill directories added.
- **Hash-backfill commit:** follows this BATON edit — backfills `79e32a0` into README.json + README.md + CLAUDE.md + this BATON.
- **No DB writes, no PDF acquisition, no schema changes** this session — skill files only.
- **Worktree cleanup:** this worktree (`.claude/worktrees/frosty-napier-bfb7b2`) will be removed during Item 12 post-merge cleanup, per BATON 070's worktree policy (default direct-on-main; worktrees removed after merge).

---

**End BATON 071.**
*Small infrastructure session — five custom skills promoted to project level for bare slash command access. No project state change other than the slash menu surface.*
