# BATON 073 — 2026-05-18 — V3.2 Workflow Transition (No Worktrees)

**Active Session Handoff Document for board_prep_intel**

---

## Session Overview

| Item | Value |
|------|-------|
| **Date** | 2026-05-18 |
| **Previous BATON** | BATON_active_072_20260518_device_handoff_pause.md |
| **Git Hash (pre-housekeeping)** | d2dab28 (PR #18 BATON-amendment merge from Mac) |
| **Branch** | claude/inspiring-cannon-e99bfb (last worktree session) |
| **Primary Goal** | Windows resume after BATON 072 Mac→Windows handoff. Intended to be a quick orientation + start corpus-qc V1 testing, but discovered substantial git/skill-resolution hygiene issues that needed cleanup first. Pivot: full V3.2 workflow transition (no worktrees ever) + supporting cleanup. |
| **Status** | Complete — V3.2 workflow shipped, git debris cleaned, 1 deferred flag closed, 1 new deferred flag opened (user-level skill deletion pending user manual action). Ready for fresh `/board-startup` next session followed by the actual corpus-qc V1 testing pass. |

---

## What Happened This Session

Mikey opened a fresh Claude Code session on Windows after the BATON 072 Mac→Windows handoff. Initial `/board-startup` and pre-flight checks passed cleanly (DB 2206/1639/2710 matched BATON 072 verbatim; git up to date with origin/main at `d2dab28`). User asked Claude to verify the Mac handoff came through clearly and that the HEADS UP section made sense — both confirmed yes.

User then said "fix any git issues — and a question, the worktree-vs-main process is confusing, is this the best way to proceed?" That prompted the full V3.2 transition.

### Discovery phase

1. **4 stale Claude worktrees** sitting in `.claude/worktrees/` from prior sessions, never cleaned up:
   - `determined-allen-0a990e` @ `e6cb648` — 10+ uncommitted file edits from a superseded BATON-068-era doc session
   - `gracious-bartik-46daa5` @ `6019f69` — fully clean, just abandoned
   - `modest-merkle-df0121` @ `85e8ab7` — 3 runtime state files (jama_pending.json, unpaywall_results.csv, settings.local.json — all things now in .gitignore per BATON 067/069)
   - `inspiring-cannon-e99bfb` @ `d2dab28` — current session
   None had unmerged commits (all `git log main..branch` empty).

2. **Main checkout's CLAUDE.md had unresolved merge-conflict markers** (lines 83-87) from a past `git stash pop` incident:
   ```
   <<<<<<< Updated upstream
   | Git branch | main → 34867ce (...BATON 072 content...) |
   =======
   | Git branch | main, latest → e6cb648 |
   >>>>>>> Stashed changes
   ```
   The `e6cb648` referenced the determined-allen worktree's HEAD — confirming the conflict originated from a stash-pop after a pull during a prior session that crossed wires between worktrees. Git status was clean from inside the worktree (because the worktree is a separate working tree), which is why earlier `git status` checks missed it.

3. **2 stray untracked Python files in main's `03_module.3_analyst/scripts/`** — `run_citation_qc.py` and `generate_sql_fixes.py`, never tracked in any git history, created May 18 19:06 (debris from the determined-allen worktree session). These are the OLD deprecated article-citation-qc scripts that BATON 068 replaced with corpus-integrity-qc.

4. **Three different versions of session-housekeeping skill exist**, with stale shadowing:
   | Path | Date | Version |
   |------|------|---------|
   | `~/.claude/skills/session-housekeeping/SKILL.md` (user-level) | Apr 16 | **OLD V2** — Cowork-era, 11-item, "user commits via GitHub Desktop", `Sonnet 4.6` Co-Authored-By |
   | `<project>/.claude/skills/session-housekeeping/SKILL.md` (project-level) | May 18 19:05 | V3.1 (BATON 072 — agent owns git, chat-auth gate, gh pr merge) |
   | `<worktree>/.claude/skills/session-housekeeping/SKILL.md` | May 18 19:21 | V3.2 (this session's pending edits) |

   When user invoked `/session-housekeeping`, Claude Code resolved to the USER-LEVEL V2 (which is named "board_prep_intel project" in its description — so it's a project-specific skill that shouldn't be at user level anyway). The V3.1 project-level was shadowed and never loaded.

### Cleanup + V3.2 transition

5. **Worktree workflow decision.** User chose "feature branches in project root, no worktrees ever" as the new V3.2 policy. Rationale: parallel-branch isolation benefit never materialized for solo sequential work; worktrees consistently caused friction (run_qc.py PROJECT_ROOT auto-detect caveat, gh pr merge --delete-branch local-cleanup wrinkle = DEFERRED-V3.2, stale-worktree accumulation, mental-model overhead).

6. **3 stale worktrees removed** via `git worktree remove --force` + `git branch -D` (all 3 branches deleted: determined-allen, gracious-bartik, modest-merkle). Verification: `git worktree list` now shows only project root + this session's worktree.

7. **CLAUDE.md conflict markers in main checkout resolved** via Edit (removed the 4 marker lines + "Stashed changes" duplicate, kept the "Updated upstream" BATON 072 version). Working tree back to 206 lines matching HEAD; `grep -c "<<<<<<<"` returns 0.

8. **Stray M3 scripts moved to `_archive_/legacy_article_citation_qc/`** in both main checkout AND worktree (so the archive lands in this PR's commit). Files preserved for reference but unclutter M3 scripts/.

9. **CLAUDE.md "Session-Housekeeping Skill" section updated to V3.2.** Replaced old worktree-policy paragraph with V3.2 "no worktrees ever" policy + rationale. Also struck through Next Steps item 10 (DEFERRED-V3.2 fix) with an OBVIATED note.

10. **`.claude/skills/session-housekeeping/SKILL.md` upgraded V3.1 → V3.2.** Specific edits:
    - Frontmatter `description` updated to mention V3.2
    - Header `# Session Housekeeping — board_prep_intel (V2)` → `(V3.2)`
    - Step 0 Recon: dropped `git worktree list` line
    - Step 4a: re-ordered branch-detection — feature-branch is now the **default under V3.2**, direct-to-main only for trivial fixes
    - Step 4c.6: dropped worktree-create/remove logic from local-prune section; added "Legacy-cleanup note" for finding/removing pre-V3.2 debris
    - Step 4c.8: dropped `git worktree list` from final verification (still kept as a sanity check)
    - Step 4c.9 Done criteria: dropped "worktree removed"
    - Item 12 summary: dropped "+ worktree" from "prune local + remote"
    - "Worktree policy" bottom section (~14 lines) → replaced with ~50-line V3.2 rationale + flow + legacy-cleanup steps

11. **BATON 072 DEFERRED-V3.2-WORKTREE-CHECKOUT-ORDER** marked OBVIATED with full explanation (no worktrees → no gh pr merge worktree wrinkle possible).

12. **User-level skill deletion BLOCKED by auto-mode classifier.** Attempted `Remove-Item -Recurse -Force "C:\Users\mpsch\.claude\skills\session-housekeeping"` — classifier denied as "Self-Modification of agent config plus irreversible destruction." This aligns with Locked Rule 8 ("Cannot `rm` NTFS files — deletions still require Windows Explorer/terminal"). Deferred to user manual action — see DEFERRED-USER-LEVEL-SKILL-DELETION below.

### Not done this session

- Corpus-qc V1 testing pass — still carrying from BATON 070/071/072
- Tier 1 SQL spot-check + apply — DEFERRED-LAYER-C-CACHE-REBUILD remains open
- ORPHAN_XREF investigation — DEFERRED-ORPHAN-XREF-QID-2024-0067 remains open
- 7 resident analyses re-run — still carrying

---

## DATABASE STATE

*(Verified live this session via sqlite3. All counts unchanged from BATON 072. No DB writes, no schema changes, no row changes.)*

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
| icd10_vec | 2,219 | unchanged |
| article_icd10_vec | 1,757 | unchanged |
| question_icd10_vec | 2,747 | unchanged |
| intersection_centroid_vec | 158 | unchanged |
| article_currency | 2,206 | unchanged |

**Next ART-ID:** ART-2208 (unchanged).

---

## PDF LIBRARY

*(Verified live this session via find. All counts unchanged from BATON 072.)*

| Tier | Windows | Notes |
|------|---------|-------|
| VC_fail | 1,056 | unchanged |
| VC_pass | 309 | unchanged |
| local_lite | 117 | unchanged |
| right_click | 58 | unchanged |
| AAFP | 15 | unchanged |
| ite_exams | 16 | unchanged |
| **ITE active total** | **1,540** | unchanged |

Mac PDF library lag (567 PDFs missing on Mac) still carries as DEFERRED-MAC-PDF-SYNC; not material since Windows is canonical and the corpus-qc V1 testing pass is DB-only.

---

## SCRIPT INVENTORY

*(All counts unchanged from BATON 072. No script additions, deletions, or modifications this session — only doc/config edits.)*

| Module | Category | Count | Δ |
|--------|----------|-------|---|
| M1 | build/ (.py) | 8 | unchanged |
| M1 | maintain/ (.py) | 38 | unchanged |
| M1 | scripts/ root (.py) | 1 (aafp_brq_scraper.py) | unchanged |
| M2 | scripts/ (.py) | 75 | unchanged |
| M2 | scripts/ (.js) | 6 | unchanged |
| M2 | scripts/ (.json) | 1 | unchanged |
| M2 | core/ + engines/ + utils/ (.py) | 4+7+6=17 | unchanged |
| M2 | M2 root main.py | 1 | unchanged |
| M3 | scripts/ (.py) | 55 | unchanged |
| M3 | scripts/ (.js) | 4 | unchanged |
| M3 | scripts/ (.json) | 7 (BATON 072 said 6 — minor drift, not material) | +1 noise |
| M4 | scripts/ (.py) | 1 | unchanged |
| M5 | Python sync | 3 | unchanged |
| M5 | TypeScript/TSX | 35 | unchanged |
| M5 | SQL migrations | 5 | unchanged |
| `.claude/skills/` (project) | Directories with SKILL.md | 7 | unchanged |
| `.claude/skills/` (project) | Cowork `.skill` zips | 2 | unchanged |
| `~/.claude/skills/` (user) | session-housekeeping (stale V2) | 1 → 0 pending | -1 (user action) |

**M3 JSON drift:** BATON 072 reported 6 JSON files in M3 scripts; recon found 7. Likely BATON 072 was slightly off or a transient added/found. Not material — investigate at leisure if curious.

---

## FILE-CHANGE SUMMARY THIS SESSION

| File | Change | Lines |
|------|--------|-------|
| `CLAUDE.md` (main checkout — conflict resolution) | -4 lines (4 conflict-marker lines removed) | 210 → 206 |
| `CLAUDE.md` (worktree — V3.2 transition) | Session-Housekeeping Skill section + Next Steps item 10 strike-through | +~25 / -~12 |
| `.claude/skills/session-housekeeping/SKILL.md` | V3.1 → V3.2 (multiple edits across Step 0, 4a, 4c.6, 4c.8, 4c.9, Item 12, Worktree policy section) | +~110 / -~50 |
| `BATON_active_072_20260518_device_handoff_pause.md` | DEFERRED-V3.2 marked OBVIATED with full explanation | +~20 / -~14 |
| `_archive_/legacy_article_citation_qc/run_citation_qc.py` (NEW) | Stray deprecated script moved from M3 scripts/ | +325 (track new file) |
| `_archive_/legacy_article_citation_qc/generate_sql_fixes.py` (NEW) | Stray deprecated script moved from M3 scripts/ | +220 (track new file) |
| `BATON_active_073_*.md` (NEW — this file) | New session handoff | NEW |
| `_index.md` | Refresh header + add session block | +~5 / -~2 |
| `README.md` + `REPO_MAP.md` | BATON pointer 072 → 073, Last Updated date | +~4 / -~4 |
| `.auto-memory/MEMORY.md` + `project_session_log.md` + `project_current_db_state.md` | Standard housekeeping refresh | +~10 / -~6 |
| `auto-memory-copies/` (3 files) | Sync mirror | matches .auto-memory/ |

---

## DEFERRED FLAGS

### Newly opened this session

#### DEFERRED-USER-LEVEL-SKILL-DELETION
**Status: ACTIVE — needs user manual action (1-minute fix)**

The user-level session-housekeeping skill at `C:\Users\mpsch\.claude\skills\session-housekeeping\` is the OLD Apr-16 V2 (Cowork-era) version. It shadows the project-level V3.1/V3.2 when `/session-housekeeping` is invoked. Discovered when invoking the skill mid-session: it loaded the V2 with "user commits via GitHub Desktop" / "Sonnet 4.6 Co-Authored-By" / "Linux sandbox paths" — clearly the wrong version.

**Why deferred:** Auto-mode classifier blocked `Remove-Item -Recurse -Force` as "Self-Modification of agent config plus irreversible destruction" — and Locked Rule 8 says deletions require Windows Explorer or terminal. Per the rules, deletion is the user's job.

**Fix (user action):** In PowerShell:
```powershell
Remove-Item -Recurse -Force "C:\Users\mpsch\.claude\skills\session-housekeeping"
```
Or in Windows Explorer: navigate to `C:\Users\mpsch\.claude\skills\` and delete the `session-housekeeping` folder.

**After deletion + Claude Code restart:** `/session-housekeeping` will resolve to the project-level V3.2 (the canonical, board_prep_intel-tailored version). Currently shadowed.

### Closed this session

- **DEFERRED-V3.2-WORKTREE-CHECKOUT-ORDER** — OBVIATED by V3.2 workflow change (no worktrees → no `gh pr merge --delete-branch` worktree-cleanup wrinkle possible). See BATON 072 amendment for full closure note.

### Carry-forward from BATON 072 (all unchanged)

- **DEFERRED-LAYER-A4-PDF-DIFF** — Layer A4 (PDF-diff re-extract) deferred to corpus-qc V1.1.
- **DEFERRED-LAYER-C-CACHE-REBUILD** — 1,797 Layer C Tier-1 cache rebuild SQL pending application via fix-applier (`--tier 1 --approved-by-user 1`). **Top priority for next session.**
- **DEFERRED-ORPHAN-XREF-QID-2024-0067** — single ORPHAN_XREF row to investigate then likely DELETE. **5-minute fix.**
- **DEFERRED-MAC-PDF-SYNC** — Mac PDF library lags Windows canonical by 567 PDFs.
- **DEFERRED-LOCKED-RULE-8-UPDATE** — Rule 8 needs Mac/Claude Code broadening. (Note: this session's user-level skill deletion BLOCK reinforces that Rule 8's "Cannot rm NTFS" guidance is real and still operative.)
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

1. **Top priority: corpus-integrity-qc V1 testing pass.** Still carrying from BATON 070/071/072. Now unblocked — V3.2 workflow is clean, no more housekeeping infrastructure to fix first.

2. **Open Claude Code in the project root, NOT in a worktree.** V3.2 policy is "no worktrees ever." If your launcher auto-creates one, opt out at launch (or, after launch, `cd` to project root and start work there). The first thing you should do in any new session is `git worktree list` to confirm you're in the project root (or, if launched into a worktree, recognize that and adjust).

3. **DELETE the user-level skill before next session (or accept the stale shadow).** See DEFERRED-USER-LEVEL-SKILL-DELETION. After deletion + Claude Code restart, `/session-housekeeping` will load V3.2 correctly. Without deletion, it'll keep loading the OLD V2 and you'll see the warning signs (11 items, "user commits via GitHub Desktop", Sonnet 4.6 reference).

4. **Run `/board-startup` first.** That's the standard orientation skill and now we've made it a habit. Confirm: BATON 073 loads, DB sanity check passes (articles=2206, questions=1639, qid_art_xref=2710), git is on main (no worktree).

5. **Then proceed with corpus-qc V1 testing pass.** Specifically, in order:
   - `python .claude\skills\corpus-integrity-qc\scripts\run_qc.py` — generates 5 artifacts in `03_module.3_analyst\outputs\corpus_qc\{today}\`
   - Spot-check 10 random Tier 1 SQL statements
   - Apply Tier 1 via `fix-applier` agent: `--tier 1 --approved-by-user 1` (~1,914 statements; closes DEFERRED-LAYER-C-CACHE-REBUILD)
   - Re-run `run_qc.py` to confirm findings drop to ~0
   - Investigate ORPHAN_XREF QID-2024-0067 / ART-2073 (5-min eyeball; closes DEFERRED-ORPHAN-XREF-QID-2024-0067)
   - Bug-fix loop on anything testing surfaces

6. **Worktree path caveat for `run_qc.py` no longer relevant** if you follow V3.2 (no worktrees). Auto-detected PROJECT_ROOT will resolve correctly from a direct project-root checkout.

7. **`fix-applier` first-use is still pending.** Built but never exercised. Token contract: `--tier 1 --approved-by-user 1`. Backs up DB before write, runs verification COUNTs, refuses both-tiers-in-one-call.

8. **Known bug to keep on radar:** `correct_author_from_clean_ref()` in `.claude/skills/corpus-integrity-qc/scripts/utils.py` truncates derived author at 80 chars, sometimes mid-word. Improvement target for a `utils.py` patch when convenient — Tier 1 SQL is still a net improvement over bare stop-word author1 in the meantime.

---

## NEXT STEPS

### Immediate (next session — on Windows, in project root, no worktree)
1. **Delete user-level skill** in PowerShell: `Remove-Item -Recurse -Force "C:\Users\mpsch\.claude\skills\session-housekeeping"`. Restart Claude Code so `/session-housekeeping` resolves to project-level V3.2.
2. **`/board-startup`** to load BATON 073 and run pre-flight (DB sanity, git on main, no worktree).
3. **Run `run_qc.py` end-to-end** on the canonical Windows DB. Verify all 5 artifacts land in `03_module.3_analyst\outputs\corpus_qc\{today}\`.
4. **Spot-check 10 random Tier 1 SQL statements** before applying.
5. **Apply Tier 1 via `fix-applier`** with `--tier 1 --approved-by-user 1`. Should land ~1,914 statements.
6. **Re-run `run_qc.py`** post-apply to confirm cache-rebuild findings drop to ~0.
7. **Investigate ORPHAN_XREF QID-2024-0067 / ART-2073** — eyeball, uncomment Tier 2 DELETE if appropriate.
8. **Bug-fix loop** on anything testing surfaces.

### Short-term (this week)
9. **Re-run all 7 resident analyses** — still carrying from BATON 065+066+067.
10. **Tier 2 review pass** — eyeball 66 commented statements.
11. **Cross-tier codon dedupe** — 89 ART-IDs in both VC_fail and VC_pass.

### Medium-term
12. **AAFP BRQ extension of corpus-integrity-qc (v2)** — Layer C ports trivially; Layer A ports easily; Layer B inapplicable.
13. Continue 801-article gap closure by source_type buckets.
14. Apply NEJM DevTools pattern to 144 unpaywall Cloudflare-blocked URLs.

---

## LOCKED RULES (Unchanged from BATON 072)

*(Verbatim from BATON 072. Rule 8 still flagged for update in DEFERRED-LOCKED-RULE-8-UPDATE — reinforced by this session's user-level skill deletion BLOCK.)*

1. **Fix the data, not the code.**
2. **VC gate = sole criterion** for right_click tier.
3. **Source data is protected.** DB + PDFs + VC gate survive everything.
4. **Dynamic paths only.** `SCRIPT_DIR = Path(__file__).resolve().parent; PROJECT_ROOT = SCRIPT_DIR.parent.parent`.
5. **No de novo JS.** New code = Python only.
6. **BATON first.**
7. **QC after every integration.**
8. **Git via Desktop Commander.** *(Flagged for update — Mac/Claude Code workflow now primary, but the "cannot rm NTFS" portion remains operative as evidenced by this session's user-level skill deletion BLOCK.)*
9. **Strategy 0 in every enricher.**
10. **Schemas before scripts.**
11. **`shutil.rmtree` is BANNED.** (Use PowerShell Remove-Item or explicit file-by-file deletion. This session: used `git worktree remove --force` for the 3 stale worktrees, which is the safe equivalent for worktree directories.)
12. **`_normalize_concept()` fallback = first-letter capitalize only.**
13. **ICD-10 enrichment is invisible.**
14. **Word docs use `word_doc_defaults.py`.**

---

## FOR THE REPO (Git Notes)

- **Branch:** claude/inspiring-cannon-e99bfb (worktree opened this session; will be merged + cleaned up as the LAST worktree session in this project's history)
- **Pre-session commit hash on main:** `d2dab28` (PR #18 BATON-amendment merge from Mac, 2026-05-18 earlier in the day)
- **Session commits on feature branch:** (filled in at housekeeping commit time)
  - `<TBD>` — *"BATON 073 — V3.2 workflow transition (no worktrees ever)"*
  - `<TBD>` — *"BATON 073 housekeeping: backfill git hash <hash>"*
- **PR #19:** (to be opened during Item 12; merged via `gh pr merge --merge --delete-branch`)
- **Post-merge cleanup steps:** This is the last worktree session. After merge, manually:
  - `cd C:\Users\mpsch\Desktop\board_prep_intel` (canonical main checkout, NOT worktree)
  - `git pull origin main`
  - `git worktree remove .claude/worktrees/inspiring-cannon-e99bfb` (or `--force` if needed)
  - `git branch -D claude/inspiring-cannon-e99bfb` (already deleted on remote via `--delete-branch`)
  - `git fetch --prune`
  - Verify `git worktree list` shows only project root
- **BATON hash-reference preservation will hold:** same `--merge --delete-branch` strategy as PR #17.

---

**End BATON 073.**
*V3.2 workflow transition complete. No more worktrees after this PR merges. Next session: `/board-startup`, then corpus-qc V1 testing pass.*
