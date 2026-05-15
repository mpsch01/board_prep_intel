---
name: session-housekeeping
description: >
  Project-level override of the upstream anthropic-skills:session-housekeeping
  workflow for the board_prep_intel ITE Intelligence project. Adds Item 12
  (GitHub syncing) so Claude owns the full git/GitHub round-trip — push,
  PR create, post-merge cleanup — at the end of every session. Replaces
  the upstream 11-item sweep with a 12-item sweep tailored to this repo
  (Mac primary workflow, project_session_log.md naming, gh CLI for PRs,
  fetch.prune globally configured).
---

# Session Housekeeping — board_prep_intel (V2)

End-of-session sweep. Goal: completeness AND efficiency. Every item gets done,
nothing gets skipped, GitHub state matches local state when finished.

## The 12 Items

1. **`_index.md`** — refresh to reflect current directory structure, script
   counts, DB numbers, BATON pointer.
2. **New BATON** — increment number, document decisions + deferred flags +
   next steps + rationale. Filename: `BATON_active_NNN_YYYYMMDD_<slug>.md`.
3. **Retire old BATON** — `git mv` previous active BATON to `baton_archive/`.
4. **`CLAUDE.md`** — update Active State table (BATON pointer, git hash,
   script counts) + Next Steps section.
5. **`MEMORY.md`** — refresh `.auto-memory/MEMORY.md` header date + any
   entries whose descriptions changed this session.
6. **`project_session_log.md`** — prepend a new "Session Notes (BATON NNN)"
   block; update module-state table where applicable. (File was renamed from
   `project_overhaul_state.md` in BATON 069.)
7. **`project_current_db_state.md`** — refresh header date; prepend a "DB
   Changes (BATON NNN)" block describing schema/row deltas or noting *no
   changes*; never let row counts drift.
8. **`README.json` + `README.md` + `REPO_MAP.md`** — update BATON pointer,
   git hash, DB numbers, module script counts, and any architectural notes
   that changed. (Note: the upstream template mentions `README_PROJECT.md` —
   that file does not exist in this repo; we use `README.md`.)
9. **`auto-memory-copies/`** — sync the three .auto-memory files to their
   git-tracked mirror. After sync, `diff -q` should show no differences.
10. **Projects Folder Instructions** — check if locked rules, modules, or
    architecture changed; if so, flag for the user. Almost always a
    NEEDS_HUMAN item.
11. **Git** — stage modified + new files by name (never `git add -A`), commit
    with a descriptive message ending with the Co-Authored-By line, follow
    with a hash-backfill commit that propagates the new hash into
    `README.json` / `README.md` / `CLAUDE.md` / new BATON.
12. **GitHub syncing (NEW — Item 12)** — push to origin, handle PR creation
    if on a feature branch, wait for user merge approval, then sync local
    main + clean up worktrees. See full Item-12 protocol below.

---

## Execution Protocol

### STEP 0 — Recon (do this yourself, before spawning anything)

Read these files in parallel to gather current state:

```
PROJECT_ROOT = /Users/mpsch/Mac Storage/board_prep_intel/           (Mac)
              = C:\Users\mpsch\Desktop\board_prep_intel              (Windows)
```

Gather:
- **Current BATON**: glob `BATON_active_*.md` at project root → highest
  number → new BATON = highest + 1.
- **DB counts**: query `00_database/db/ite_intelligence.db` via sqlite3 for
  row counts on the standard 15 tables.
- **PDF counts**: count `.pdf` files in each tier under
  `01_module.1_warehouse/citation_files/{ITE/{VC_fail,VC_pass,local_lite,right_click},AAFP}`
  and `ite_exams/`.
- **Script counts**: `.py` and `.js` files in M1 build/maintain, M2 scripts,
  M3 scripts, M5.
- **Git hash**: `git rev-parse --short HEAD`.
- **Git status**: `git status --short` → list of changed + new files.
- **Current branch**: `git branch --show-current`.
- **Worktrees**: `git worktree list` → flag any stale worktrees for cleanup.

### STEP 1 — Author the manifest set

For a typical session, do this **inline** rather than spawning 3 parallel
agents. The agent-dispatch pattern (baton-writer / index-memory-writer /
manifest-writer in `agents/`) is the fallback when:
- Context budget is tight (we're already past 200k input tokens), OR
- The work is unusually large (>50 files changed, multiple modules touched).

Inline path produces ~⅓ the token cost. Default to inline; escalate to
parallel agents only when context pressure is real.

Write in this order:
1. BATON NNN (the keystone — all other files reference it).
2. CLAUDE.md (Active State + Next Steps).
3. `_index.md` (header + dated session block).
4. `.auto-memory/{MEMORY.md, project_session_log.md, project_current_db_state.md}`.
5. `README.json`, `README.md`, `REPO_MAP.md`.

### STEP 2 — Retire old BATON + sync mirrors

1. **`git mv`** previous BATON to `baton_archive/` (preserves history).
2. **Copy** the 3 .auto-memory files to `auto-memory-copies/`. Verify with
   `diff -q`.

### STEP 3 — Git commit + hash-backfill

1. `git add` each modified + new file **by name**. Never `git add -A`.
2. Commit with descriptive message + Co-Authored-By footer.
3. Backfill the new commit hash into README.json + README.md + CLAUDE.md +
   the new BATON (the "Pre-housekeeping" + "Session commit" rows). Commit
   that as a second commit: *"BATON NNN housekeeping: backfill git hash &lt;hash&gt;"*.

### STEP 4 — GitHub syncing (Item 12, NEW)

**The agent owns this end-to-end.** Do not ask the user to run git
commands themselves. The user merges PRs via the GitHub web UI when one
is created; everything else is the agent's responsibility.

#### Step 4a — Determine sync mode

Check current branch:

```bash
git branch --show-current
```

- **If on `main`** → "direct-to-main" mode. Push directly. Most common case
  for solo-author sessions without need for review-time PR review.
- **If on a `claude/*` or other feature branch** → "PR mode". Push the
  branch, create a PR via `gh`, wait for user approval, merge, cleanup.

#### Step 4b — Direct-to-main mode

```bash
git push origin main
```

Verify:
```bash
git status                       # working tree clean
git log origin/main -1           # remote tip matches local HEAD
```

Done. No PR. No cleanup needed (no feature branch to remove).

#### Step 4c — PR mode

1. **Push the feature branch:**
   ```bash
   git push -u origin <branch-name>
   ```
2. **Create the PR via gh:**
   ```bash
   gh pr create --base main \
     --title "BATON NNN — <short description>" \
     --body "<Summary + Test plan + reference to BATON file>"
   ```
   The body should include:
   - Summary bullets (1-3 points)
   - Test plan checklist (whatever needs verifying next session)
   - Reference: *"See BATON_active_NNN_*.md for full session details."*
3. **Return the PR URL to the user** and stop. The user merges via web UI.
4. **Wait for the user to confirm merge.** Do NOT auto-merge.
5. **Post-merge cleanup** (only when user confirms merge):
   ```bash
   cd <PROJECT_ROOT>
   git checkout main
   git pull origin main          # fetch.prune=true is global, so this prunes too
   git branch -d <branch-name>   # safe-delete; refuses if not fully merged
   ```
   If a worktree was used:
   ```bash
   git worktree remove .claude/worktrees/<worktree-dir>
   ```

#### Step 4d — Verify final state

```bash
git worktree list                # should show only the main checkout
git branch                       # should be on main, no stale feature branches
git status                       # clean
git log --oneline -3             # latest commits including the merge commit
```

If any of these show unexpected state, fix before declaring done.

### STEP 5 — QC validation

Spawn a QC subagent OR run inline (default inline for efficiency). Check all
12 items, report PASS / FAIL / NEEDS_HUMAN for each. Provide the final
summary table to the user.

### STEP 6 — Report

Final summary to the user:

```
## Housekeeping Complete — BATON NNN

✓ Items passed: X/12
⚠ Needs attention: <any FAILs>
👤 Human review: <Item 10 if applicable>

New BATON: <filename>
Local commits: <hashes>
Remote state: <main at hash; PR #N created/merged>
PDF library: <tier counts>
DB: <key row counts>
```

---

## Critical Rules

- **Recon before writing.** Stale numbers in BATONs are worse than no numbers.
- **New BATON before retiring old.** Confirm new file on disk first.
- **Git stages specific files.** Never `git add -A` — risk of committing
  secrets (.env), large binaries, or unrelated work-in-progress.
- **The agent owns Item 12.** Do not delegate GitHub syncing back to the
  user. Push, create PRs, post-merge cleanup are all the agent's job.
- **Never `gh pr merge` autonomously.** Merging affects shared state on
  GitHub — always wait for user authorization. Branch deletion via
  `--delete-branch` after a user-authorized merge is fine.
- **Never force-push.** No `--force` / `--hard` / etc. without explicit
  user authorization for that specific action.
- **`shutil.rmtree` is BANNED** (Locked Rule 11). Use `git worktree remove`
  (which handles cleanup safely) or explicit file-by-file removal.
- **fetch.prune is global.** Set via `git config --global fetch.prune true`
  (already configured BATON 070). Every `git fetch` / `git pull` now auto-
  prunes deleted remote-tracking refs.
- **QC is mandatory.** Don't skip Step 5. If QC surfaces failures, fix
  before reporting done.

---

## Worktree policy (project-level decision, BATON 070)

**Default to direct-on-main** in the project root. Worktrees are useful for
parallel Claude Code agents on different branches, but for solo human +
single-agent sessions they add friction (GitHub Desktop confusion,
branch-checkout conflicts, two-step merge). Only spin up a worktree when:

- Two Claude Code sessions need to operate on different branches concurrently
- A long-running operation must continue while another branch is checked out

When a worktree IS used, the agent owns its lifecycle: create at session
start (if needed), commit + push the branch, open PR, wait for user merge,
then remove the worktree as part of Item 12 post-merge cleanup.
