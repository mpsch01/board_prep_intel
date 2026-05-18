# BATON 072 — 2026-05-18 — Device Handoff (Mac → Windows)

**Active Session Handoff Document for board_prep_intel**

---

## Session Overview

| Item | Value |
|------|-------|
| **Date** | 2026-05-18 |
| **Previous BATON** | BATON_active_071_20260518_custom_skills_project_level.md |
| **Git Hash (pre-housekeeping-commit)** | 2079a2f |
| **Branch** | claude/awesome-chandrasekhar-3ae317 (fresh Claude Code worktree off main) |
| **Primary Goal** | Orientation pass + corpus-integrity-qc status update; pause and hand off to the Windows big-rig PC for the actual corpus-qc V1 testing run. **Mid-session expansion:** revise session-housekeeping skill end-to-end so the agent owns the full push→PR→review→authorize→merge→prune→verify cycle (V3 + V3.1). |
| **Status** | Complete — orientation done, corpus-qc plan rehearsed, no code/DB/PDF changes. Session-housekeeping skill upgraded to V3.1 (chat-level auth gate + merge-commit-only style). PR #17 merged via the new V3.1 flow at `34867ce`; ready to resume on Windows. |

---

## What Happened This Session

Mikey opened a new Claude Code session, ran `/board-startup`, and asked for a corpus-integrity-qc progress recap before kicking off the BATON 071 carry-forward testing pass. After delivering the recap (what's built, what's left, known bugs / circle-back items, the worktree path caveat for `run_qc.py`, and the `fix-applier` first-use plan), Mikey decided to **move the work to the big rig PC** rather than execute on Mac. No scripts were run, no DB writes occurred, no PDFs were touched.

**Late-session addition (post-initial-housekeeping):** while reviewing the BATON 072 PR, Mikey rewrote the end-of-session GitHub-sync workflow in two iterations. The session-housekeeping skill now owns the full round-trip including the merge itself:

- **V3 (commit `bb2e297`)** — Item 12 revised end-to-end. Agent now opens the PR, **provides a structured review block in chat** (PR URL, commit list, file counts, summary), **waits for explicit chat-level authorization** (words: `merge it` / `approved` / `go` / `lgtm` / `ship it` / `yes merge`), then runs `gh pr merge` itself (no more "user merges in web UI"). 9-substep sequence: push → PR → review → wait → merge → prune → verify GitHub state → verify single-main local state → done.
- **V3.1 (commit `b125176`)** — merge style locked to `--merge --delete-branch`. Squash and rebase are explicitly banned because every BATON pins intra-session commit hashes (e.g. BATON 072's own *"Session commit: 02a770f"* reference). Squash would destroy those hashes; rebase preserves them but loses the session-boundary marker. Merge commit keeps both, and `git log --merges` gives a clean per-session view across the repo.
- **First exercise on PR #17 (commit `34867ce`)** — exercised V3.1 end-to-end on this very PR. Result: merge landed cleanly, remote branch deleted, local branch deleted, worktree removed, single-main verified, and **all 5 session commits remain resolvable on main by their pre-merge hashes** (proves the merge-commit-style rationale).
- **V3.2 wrinkle surfaced (deferred):** running `gh pr merge --delete-branch` from inside the worktree errored because gh's built-in local-side cleanup tried to switch the worktree to `main` (already checked out in the canonical project root). The remote merge + remote branch delete still succeeded; only the local-side cleanup needed manual completion. **Fix proposal:** SKILL.md Step 4c.5 should `cd` to the canonical main checkout before running `gh pr merge`. See DEFERRED-V3.2-WORKTREE-CHECKOUT-ORDER below.

**Net effect on the project:** zero changes to DB / PDFs / pipeline scripts / module code. **One substantive doc/skill change:** `.claude/skills/session-housekeeping/SKILL.md` upgraded from V2 (which stopped at PR-open and deferred the merge to the user) to V3.1 (agent owns the full cycle, merge-commit-only). All BATON 071 carry-forwards remain in place; the next session on Windows picks up exactly where BATON 071 left off — plus inherits the new V3.1 housekeeping workflow when it runs `/session-housekeeping` at end-of-session.

---

## DATABASE STATE

*(Inherited from BATON 071 — no DB writes, no schema changes, no row changes this session.)*

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

*(Inherited from BATON 071 — Mac local still lags Windows canonical by 567 files. Not re-verified this session since no PDF work occurred.)*

| Tier | Mac | Windows canonical | Notes |
|------|-----|-------------------|-------|
| VC_fail | 630 | 1,056 | DEFERRED-MAC-PDF-SYNC |
| VC_pass | 168 | 309 | DEFERRED-MAC-PDF-SYNC |
| local_lite | 117 | 117 | Synced |
| right_click | 58 | 58 | Synced |
| AAFP | 15 | 15 | Synced |
| ite_exams | 16 | 16 | Synced |
| **ITE active total (Mac)** | **973** | **1,540** | |

**Note for next session:** running corpus-qc on Windows means the testing pass will hit the canonical 1,540-PDF library directly — no Mac PDF sync required up-front for the DB-only audit (Layers A/B/C don't read PDFs in V1; A4 PDF-diff is deferred). Mac PDF sync remains a DEFERRED-MAC-PDF-SYNC carry-forward.

---

## SCRIPT INVENTORY

*(All counts unchanged from BATON 071. No script additions, deletions, or modifications this session.)*

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
| `.claude/skills/` (project-level) | Directories with SKILL.md | 7 | unchanged |
| `.claude/skills/` (project-level) | Cowork `.skill` zips | 2 | unchanged |

---

## DEFERRED FLAGS

### Newly opened this session

#### DEFERRED-V3.2-WORKTREE-CHECKOUT-ORDER
**Status: ACTIVE — new this session (5-minute fix when convenient)**

When `gh pr merge --delete-branch` runs from inside a Claude Code worktree, gh's built-in local-side cleanup tries to switch the worktree to `main` and fails (since `main` is already checked out in the canonical project root). The remote-side actions (merge + remote branch delete) still complete successfully, but local cleanup needs manual completion (`git worktree remove`, `git branch -d`, `git fetch --prune`).

**Fix:** `.claude/skills/session-housekeeping/SKILL.md` Step 4c.5 should `cd` to the canonical main checkout **before** running `gh pr merge`:

```bash
cd <PROJECT_ROOT>           # canonical main checkout, not the worktree
gh pr merge <num> --merge --delete-branch
# gh's local checkout + branch delete now works cleanly;
# Step 4c.6 only needs `git worktree remove .claude/worktrees/<dir>`
```

**Why deferred and not fixed now:** the V3.1 flow worked end-to-end on PR #17 in spite of this wrinkle (manual cleanup completed successfully, all verification passed). Patching belongs in a dedicated edit of the SKILL.md rather than buried in the BATON-amendment commit. **Next action:** small SKILL.md edit at start of next housekeeping cycle (or whenever a worktree is used again).

### Closed this session
**None.**

### Carry-forward from BATON 071 (all unchanged)

- **DEFERRED-LAYER-A4-PDF-DIFF** — Layer A4 (PDF-diff re-extract) deferred to corpus-qc V1.1.
- **DEFERRED-LAYER-C-CACHE-REBUILD** — 1,797 Layer C Tier-1 cache rebuild SQL pending application via fix-applier (`--tier 1 --approved-by-user 1`).
- **DEFERRED-ORPHAN-XREF-QID-2024-0067** — single ORPHAN_XREF row to investigate then likely DELETE.
- **DEFERRED-MAC-PDF-SYNC** — Mac PDF library lags Windows canonical by 567 PDFs.
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

## HEADS UP — Mac → Windows Switch (read first on Windows)

Mikey hasn't actively worked from the Windows big rig since **BATON 067 (2026-05-07)** — roughly 11 days dormant. Everything from BATON 068 → 072 happened on Mac. Re-entry friction to watch for:

### Git state on Windows

- **Windows local `main` is at least 4 commits behind origin.** Since 2026-05-07, the following landed on `main` from Mac via PRs / direct pushes:
  - PR #16 — BATON 071 (custom skills promoted to project level) → merge commit + housekeeping commits `fdf50d3` … `79e32a0` … `29d47dd` … `9229b55`
  - `2079a2f` — `.tmp.driveupload` artifact cleanup
  - PR #17 (pending merge) — BATON 072 (this housekeeping)
- **Pre-flight on Windows:**
  ```bash
  cd C:\Users\mpsch\Desktop\board_prep_intel
  git status                       # any uncommitted Windows-side WIP?
  git fetch --all --prune          # see what's new on origin
  git branch --show-current        # confirm on main (or switch if not)
  git pull origin main             # only after PR #17 is merged
  ```
- **If Windows has uncommitted WIP from BATON 067 era** (e.g. leftover state files from `aafp_targeted_downloader.py`, `_aafp_auth.json`, partial Playwright runs): `git status -uno` first, decide whether to stash, commit, or discard before pulling. The `.gitignore` was updated in BATON 067/069 to catch most of these, but old residue may pre-date the ignore rules.

### Database verification (do this before `run_qc.py`)

The Windows DB at `C:\Users\mpsch\Desktop\board_prep_intel\00_database\db\ite_intelligence.db` **should be** the canonical 2,206-article / 2,710-xref DB. **Verify before running anything:**

```bash
python -c "import sqlite3; c=sqlite3.connect('00_database/db/ite_intelligence.db'); print('articles:', c.execute('SELECT COUNT(*) FROM articles').fetchone()[0]); print('questions:', c.execute('SELECT COUNT(*) FROM questions').fetchone()[0]); print('qid_art_xref:', c.execute('SELECT COUNT(*) FROM qid_art_xref').fetchone()[0])"
```

**Expected output (verbatim):**
```
articles: 2206
questions: 1639
qid_art_xref: 2710
```

If Windows shows different numbers, **do NOT proceed with the testing pass** — the DB is stale or has been mutated by something. Source-of-truth canonical is the May-6 copy that BATON 068 pulled from gdrive into Mac; if Windows drifted, pull canonical from gdrive into `00a_db_gdrive_landing/db/` (the established landing zone from BATON 068) before swapping.

### PDF library on Windows

- **Should be 1,540 ITE active + 15 AAFP + 16 ite_exams = 1,571 total.** Quick check:
  ```powershell
  (Get-ChildItem -Recurse 01_module.1_warehouse\citation_files\ITE -Filter *.pdf).Count
  ```
  Expect 1,540 (across VC_fail 1,056 + VC_pass 309 + local_lite 117 + right_click 58).
- **PDFs are NOT needed for the corpus-qc V1 testing pass** (Layers A/B/C are DB-only; A4 PDF-diff is deferred). So even if Windows PDF count is off, it doesn't block the testing pass — but worth knowing about for downstream work.

### Python environment

- **Confirm `python` resolves to the right interpreter on Windows.** The corpus-qc scripts have **zero external deps** — pure stdlib (`sqlite3`, `pathlib`, `json`, `re`, `subprocess`, `argparse`, `concurrent.futures`). Any Python 3.9+ install works.
- Quick check: `python --version` (≥3.9) and `python -c "import sqlite3, concurrent.futures, pathlib; print('ok')"`.
- If `python` resolves to a stale venv from BATON 067 era with broken deps, just use system Python — corpus-qc doesn't need a venv.

### Claude Code skills surface on Windows

- The 5 bare-slash skills promoted in BATON 071 (`/board-startup`, `/body-system-qc`, `/article-citation-qc`, `/baton-pipeline-qc`, `/repo-error-review`) only resolve **bare** after a Claude Code restart on Windows. If they don't show up bare after pull + restart, the fallback `/anthropic-skills:board-startup` etc. always works as a backstop.
- The `corpus-integrity-qc` skill itself is at `.claude/skills/corpus-integrity-qc/` and will be there on Windows after `git pull`.
- **`/session-housekeeping` is now V3.1** (this session — chat-level auth gate + agent runs `gh pr merge --merge --delete-branch` itself; no more "user merges in web UI"). The V3.1 SKILL.md will be on disk after `git pull origin main`, but a Claude Code restart on Windows is needed to load the updated content into the active session. If you forget the restart and trigger `/session-housekeeping` anyway, you'll get the stale (V2 or older plugin) behavior — the symptom is the skill stopping at PR-open and asking you to merge in the web UI instead of providing a review block and waiting for authorization. Same fix as above: restart Claude Code.

### Path conventions on Windows

- All scripts use `Path(__file__).resolve()` so the slash vs backslash issue is handled. **No script changes needed for Windows.**
- The **worktree path caveat for `run_qc.py` still applies** (BATON 070 architectural decision #7) — auto-detected PROJECT_ROOT goes one level too deep if you run from a worktree. On a direct main checkout (no worktree), it works.
- **Canonical Windows invocation:**
  ```cmd
  cd C:\Users\mpsch\Desktop\board_prep_intel
  python .claude\skills\corpus-integrity-qc\scripts\run_qc.py
  ```

### Locked Rule 8 reminder

- Rule 8 still says "Git via Desktop Commander" — that was the **Windows-original** convention. On Windows you can keep using Desktop Commander OR run `git` directly in PowerShell / Git Bash, whichever you prefer. The rule is flagged for update in `DEFERRED-LOCKED-RULE-8-UPDATE` to broaden language; not blocking anything.
- **Rule 11 — `shutil.rmtree` is BANNED — is especially critical on Windows** because it bypasses the Recycle Bin (irreversible). Use PowerShell `Remove-Item` or explicit file-by-file deletion.

### Google Drive sync risk

- If Drive desktop client is still syncing the project folder on Windows, you'll see `.tmp.driveupload` artifacts reappear. The `.gitignore` (updated BATON 069) catches `*.tmp.driveupload` so they won't get tracked, but they clutter `ls` output.
- If they show up: confirm Drive isn't trying to sync the local project folder; the canonical copy lives in gdrive web and pulls into `00a_db_gdrive_landing/db/` as needed (see BATON 068 swap pattern).

### Bottom line

**Five-minute pre-flight on Windows:**
1. `git fetch --all --prune` → check what's new
2. `git status -uno` → check Windows-side WIP
3. Wait for PR #17 merge → `git pull origin main`
4. Run the DB-count sanity check above
5. `/board-startup` → confirm BATON 072 loads
6. Proceed with `run_qc.py`

---

## CRITICAL REMINDERS FOR NEXT SESSION (on Windows)

1. **Top priority remains the corpus-integrity-qc V1 testing pass.** BATON 070's Immediate list and BATON 071's "Immediate (next session)" list both still apply verbatim. No work has been performed against them since BATON 070's smoke test in the worktree.

2. **On Windows, paths look like:**
   - `PROJECT_ROOT = C:\Users\mpsch\Desktop\board_prep_intel\`
   - `DB = C:\Users\mpsch\Desktop\board_prep_intel\00_database\db\ite_intelligence.db` (this is the canonical DB on Windows)
   - `OUTPUT_DIR = C:\Users\mpsch\Desktop\board_prep_intel\03_module.3_analyst\outputs\corpus_qc\2026-05-18\`

3. **Worktree path caveat still in force.** `run_qc.py` auto-detects PROJECT_ROOT as `SCRIPT_DIR.parent.parent.parent.parent.parent` — from a worktree this lands one level too deep. If you spin up a worktree on Windows for the testing pass, pass `--project-root` explicitly. On a direct main checkout the auto-detect works.

4. **Pre-flight `git pull` on Windows.** Windows main is currently at hash `2079a2f` (or wherever it was when the user last pulled). After this housekeeping pass commits + the user-merged PR lands, Windows needs `git pull origin main` to pick up BATON 072 before starting work.

5. **No DB or schema changes this session.** Row counts identical to BATON 071. All 15 audited tables unchanged.

6. **`fix-applier` first-use is still pending.** Built but never exercised. Token contract: `--tier 1 --approved-by-user 1`. Backs up DB before write, runs verification COUNTs, refuses both-tiers-in-one-call.

7. **Known bug to keep on the bug-fix loop radar (BATON 070 #6):** `correct_author_from_clean_ref()` in `.claude/skills/corpus-integrity-qc/scripts/utils.py` truncates derived author at 80 chars, sometimes mid-word. Improvement target for a `utils.py` patch when convenient — Tier 1 SQL is still a net improvement over bare stop-word author1 in the meantime.

---

## NEXT STEPS

### Immediate (next session — on Windows big rig)
1. **`git pull origin main`** in Windows project root to pick up BATON 072.
2. **`/board-startup`** to load BATON 072 + confirm the orientation context carries over cleanly.
3. **Run `run_qc.py` end-to-end on the canonical Windows DB** — verify all 5 artifacts land in `03_module.3_analyst\outputs\corpus_qc\2026-05-18\` (or whatever date stamp the run picks).
4. **Spot-check 10 random Tier 1 SQL statements** before applying — copy-paste each into DB Browser and verify the intended fix.
5. **Apply Tier 1 via the `fix-applier` agent** with `--tier 1 --approved-by-user 1`. Should land ~1,914 statements. Closes DEFERRED-LAYER-C-CACHE-REBUILD.
6. **Re-run `run_qc.py`** post-apply to confirm cache-rebuild findings drop to ~0.
7. **Investigate ORPHAN_XREF QID-2024-0067 / ART-2073** — eyeball, uncomment Tier 2 DELETE if appropriate. Closes DEFERRED-ORPHAN-XREF-QID-2024-0067.
8. **Bug-fix loop** on anything testing surfaces.

### Short-term (this week)
9. **Re-run all 7 resident analyses** — still carrying from BATON 065+066+067.
10. **Tier 2 review pass** — eyeball 66 commented statements.
11. **Cross-tier codon dedupe** — 89 ART-IDs in both VC_fail and VC_pass.

### Medium-term
12. **AAFP BRQ extension of corpus-integrity-qc (v2)** — Layer C ports trivially; Layer A ports easily; Layer B inapplicable — replace with per-article scalar checks against AAFP-linked rows.
13. Continue 801-article gap closure by source_type buckets.
14. Apply NEJM DevTools pattern to 144 unpaywall Cloudflare-blocked URLs.

---

## LOCKED RULES (Never Override Without Mikey Confirming)

*(Verbatim from BATON 071. No changes this session. Rule 8 still flagged for update in DEFERRED-LOCKED-RULE-8-UPDATE.)*

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

- **Branch:** claude/awesome-chandrasekhar-3ae317 (worktree off main, opened + merged + removed this session)
- **Pre-session commit hash on main:** `2079a2f` ("Remove tracked .tmp.driveupload artifacts (pre-gitignore residue)")
- **Session commits on feature branch (all preserved on main via merge commit):**
  - `02a770f` — *"BATON 072 — Device-handoff pause (Mac → Windows big rig)"* — 13 files, +289 / -43
  - `4b8b878` — *"BATON 072 housekeeping: backfill git hash 02a770f"* — 4 files, +6 / -6
  - `a14dcaa` — *"BATON 072: add Mac → Windows switch heads-up section"* — 2 files, +98 / -2
  - `bb2e297` — *"session-housekeeping V3: agent runs gh pr merge after chat-level authorization"* — 1 file, +165 / -60
  - `b125176` — *"session-housekeeping V3.1: lock merge style to --merge (no squash, no rebase)"* — 1 file, +50 / -24
- **PR #17:** **MERGED** at 2026-05-18T22:36:35Z via `gh pr merge 17 --merge --delete-branch`. Merge commit: `34867ce` on `origin/main`. First exercise of the new V3.1 housekeeping flow.
- **Post-merge cleanup completed:** remote branch deleted (verified `git ls-remote --heads` empty); local branch deleted (`git branch -d claude/awesome-chandrasekhar-3ae317` succeeded — exit-clean recognition of the merge-commit-style merge); worktree removed (`git worktree remove .claude/worktrees/awesome-chandrasekhar-3ae317`); stale remote-tracking ref pruned (`git fetch --prune origin`).
- **BATON hash-reference preservation verified:** all 5 pre-merge commit hashes (`02a770f`, `4b8b878`, `a14dcaa`, `bb2e297`, `b125176`) still resolve via `git show` on main — proves the merge-commit-style rationale and validates V3.1's lock against `--squash`.
- **No DB writes, no PDF acquisition, no schema changes, no pipeline-script changes** this session — pure orientation + status conversation + housekeeping paper trail + session-housekeeping skill upgrade.
- **BATON-amendment commit:** follows this edit on `main` directly (no PR — solo author, BATON correction, per V3.1 default direct-on-main worktree policy). Adds: (1) Late-session addition block describing V3 + V3.1 + V3.2; (2) DEFERRED-V3.2-WORKTREE-CHECKOUT-ORDER flag; (3) V3.1 restart note in HEADS UP Claude Code skills subsection; (4) this updated Git Notes section.

---

**End BATON 072.**
*Device-handoff pause — orientation done, plan rehearsed, no pipeline code touched. session-housekeeping skill upgraded to V3.1 (chat-level auth gate + agent-runs-merge + merge-commit-only); first exercise on PR #17 landed cleanly with BATON hash references preserved. Resume corpus-qc V1 testing pass on the Windows big rig.*
