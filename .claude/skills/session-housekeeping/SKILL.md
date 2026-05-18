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
12. **GitHub syncing (Item 12, REVISED BATON 072)** — push to origin → open
    PR if on feature branch → **provide review of PR to user** → **wait for
    explicit authorization in chat** → **agent runs `gh pr merge`** → prune
    local + remote (branch + worktree) → **review post-merge GitHub state**
    → verify single `main` branch with no stale refs → declare done. See
    full Item-12 protocol below.

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

### STEP 4 — GitHub syncing (Item 12, REVISED BATON 072)

**The agent owns this end-to-end, including the merge itself.** The user
authorizes in chat after reviewing the PR; the agent executes every git /
gh command. Do not ask the user to run git commands, click web-UI buttons,
or paste hashes back. The full sequence is: push → PR → **provide review →
wait for authorization** → merge → prune → review GitHub state → verify
single-main → done.

#### Step 4a — Determine sync mode

Check current branch:

```bash
git branch --show-current
```

- **If on `main`** → "direct-to-main" mode (Step 4b). Most common for
  solo-author sessions with no review gate needed.
- **If on a `claude/*` or other feature branch** → "PR mode" (Step 4c).
  Push branch, open PR, provide review, await authorization, merge, prune.

#### Step 4b — Direct-to-main mode

```bash
git push origin main
```

Verify:
```bash
git status                       # working tree clean
git log origin/main -1           # remote tip matches local HEAD
```

Done. No PR. No cleanup needed (no feature branch to remove). Skip to
Step 5 (QC) and Step 6 (final report).

#### Step 4c — PR mode (the full new flow)

**1. Push the feature branch:**
```bash
git push -u origin <branch-name>
```

**2. Create the PR via gh:**
```bash
gh pr create --base main \
  --title "BATON NNN — <short description>" \
  --body "<Summary + Test plan + reference to BATON file>"
```
Body should include:
- Summary bullets (1-3 points)
- Test plan checklist (whatever needs verifying next session)
- Reference: *"See BATON_active_NNN_*.md for full session details."*

**3. Provide PR review to the user.** Output a structured block in chat
the user can scan before authorizing the merge:

```
## PR Ready for Review — #<num>

**URL:** <pr-url>
**Title:** <title>
**Base ← Head:** main ← <branch-name>
**Commits on this branch:** <count>
  - <hash> — <message>
  - <hash> — <message>
**Files changed:** <count> (+<insertions> / -<deletions>)
**Key paths touched:** <bulleted list of top-level dirs / notable files>
**Summary:** <1-2 line restatement of what merging will do>

Authorize merge? Reply "merge it" / "approved" / "go" — or "hold" /
"changes needed" if you want me to wait.
```

Then **stop and wait** for the user's explicit go-ahead in chat. Treat
any of: `merge it`, `approved`, `go`, `lgtm`, `ship it`, `yes merge` —
or close equivalents — as authorization. Treat any expression of
hesitation, change request, or "wait" as a hold; do not merge.

**4. Wait for explicit user authorization.** No timer, no implicit
approval. If the user goes quiet, ask once, then stop.

**5. Merge via `gh pr merge` (always: merge commit + delete remote branch).**
Once authorized:

```bash
gh pr merge <pr-num> --merge --delete-branch
```

**Merge style is locked to `--merge` (merge commit).** Do NOT use
`--squash` or `--rebase`. Reasons board_prep_intel requires merge commit:

1. **Preserves BATON hash references.** Every BATON pins specific
   intra-session commit hashes (e.g. *"Session commit (housekeeping):
   `02a770f`"*, *"Hash-backfill commit: backfills `02a770f` into…"*).
   These are part of the audit trail. `--squash` destroys those hashes
   (they exist only in reflog, 90-day expiry); `--rebase` preserves them
   but loses the session-boundary marker. `--merge` keeps both.
2. **Merge commit IS the session boundary marker.** `git log --merges`
   gives a clean per-PR view across sessions ("BATON 071 merge", "BATON
   072 merge"…) — matches the BATON-as-session-record model.
3. **Standard GitHub default** — matches the rest of the world's mental
   model for git history.

Flag conventions:
- **`--merge`** — always. Creates a merge commit on `main` linking the
  feature branch.
- **`--delete-branch`** — always. Drops the remote feature branch
  atomically with the merge so cleanup doesn't lag.

If the user explicitly requests squash or rebase for a one-off PR
(e.g. *"squash this one, it's just typo fixes"*), honor it for that PR
only — do not change the default. Default remains `--merge`.

**6. Local prune.** Sync local `main` and remove the now-merged feature
branch + worktree:

```bash
# In the canonical main checkout (NOT the worktree):
cd <PROJECT_ROOT>
git checkout main
git pull origin main          # picks up merge commit; fetch.prune drops stale refs

# Delete the local feature branch:
git branch -d <branch-name>   # safe-delete; recognizes merge-commit merges natively

# If a worktree was used this session:
git worktree remove .claude/worktrees/<worktree-dir>
```

With `--merge` style, `git branch -d` recognizes the merge cleanly
because the feature branch tip is reachable from `main` via the merge
commit. If `-d` ever refuses ("not fully merged"), STOP — investigate
what's actually on the branch vs `main` before doing anything else.
Do NOT use `-D` reflexively.

**7. Review GitHub update.** Verify the merge landed and the remote is
clean:

```bash
gh pr view <pr-num> --json state,mergedAt,mergeCommit \
  | python -c "import sys, json; d=json.load(sys.stdin); print(f\"state={d['state']} merged_at={d['mergedAt']} merge_commit={d['mergeCommit']['oid'][:7]}\")"
git ls-remote --heads origin <branch-name>   # should return EMPTY (branch deleted on remote)
git log origin/main --oneline --merges -3     # confirm new merge commit is at tip
git log origin/main --oneline -5              # see merge + the original feature commits
```

Expected:
- `state=MERGED` and a non-null `merged_at` timestamp
- Empty output from `ls-remote --heads` for the feature branch
- A new merge commit visible at `origin/main` tip (matches `mergeCommit.oid`)
- The original feature-branch commits still resolvable by their pre-merge
  hashes (e.g. `git show <pre-merge-hash>` works) — this is the BATON
  hash-reference preservation behavior

**8. Ensure single main branch before finalization.** Final clean-state
verification:

```bash
git worktree list           # should show only the main checkout
git branch                  # should list ONLY `main` (no stale feature branches)
git branch -r               # should not list the deleted remote feature branch
git status                  # clean working tree
```

If any of these surface unexpected state, fix before declaring done.
Common gotchas:
- Stale remote-tracking ref still showing (`origin/<branch>`) → `git fetch --prune` (should be automatic via global config, but re-run if needed).
- Worktree still listed → `git worktree prune` (only if directory is gone but ref persists).
- Local branch not deleted → re-run `git branch -d <branch-name>` after pull.

**9. Done.** All of: PR merged on GitHub, remote branch deleted, local
branch deleted, worktree removed, single `main` checkout, clean status.
Now proceed to Step 5 (QC) and Step 6 (final report). The final report
should reflect post-merge state (commit hash on `main`, PR marked merged).

### STEP 5 — QC validation

Spawn a QC subagent OR run inline (default inline for efficiency). Check all
12 items, report PASS / FAIL / NEEDS_HUMAN for each. Provide the final
summary table to the user.

### STEP 6 — Report

Final summary to the user. Always reflect **post-merge** state (not
pre-merge) when in PR mode:

```
## Housekeeping Complete — BATON NNN

✓ Items passed: X/12
⚠ Needs attention: <any FAILs>
👤 Human review: <Item 10 if applicable>

New BATON: <filename>
Session commits (preserved on main): <list of pre-merge hashes>
PR: #<num> — MERGED (merge commit <hash> on origin/main)
Local state: on main at <hash>, no stale branches, no worktrees, clean status
PDF library: <tier counts>
DB: <key row counts>
```

When in direct-to-main mode the PR line collapses to:
`Remote: origin/main at <hash> (direct push, no PR)`.

---

## Critical Rules

- **Recon before writing.** Stale numbers in BATONs are worse than no numbers.
- **New BATON before retiring old.** Confirm new file on disk first.
- **Git stages specific files.** Never `git add -A` — risk of committing
  secrets (.env), large binaries, or unrelated work-in-progress.
- **The agent owns Item 12 end-to-end, including the merge.** Push, open
  PRs, provide review, **run `gh pr merge` once authorized**, prune locally
  and on origin, verify post-merge GitHub state — all the agent's job. Do
  not ask the user to click web-UI buttons or run git commands.
- **Merge requires explicit chat-level authorization.** After providing
  the PR review block (Step 4c.3), STOP and wait for the user's go-ahead.
  Authorization words: `merge it`, `approved`, `go`, `lgtm`, `ship it`,
  `yes merge`, or close equivalents. Hesitation, "wait", "hold", or
  change-request language = do NOT merge. No timer, no implicit approval.
- **Merge style is locked to `--merge --delete-branch`.** Always merge
  commit, never squash, never rebase. Reason: BATON files pin specific
  intra-session commit hashes as part of the audit trail — `--squash`
  destroys those hashes; `--rebase` loses the session-boundary marker.
  Merge commits preserve both, and `git log --merges` gives a clean
  per-session view across the repo. If the user explicitly requests a
  different style for a one-off PR, honor it for that PR only — do not
  change the default.
- **Never force-push.** No `--force` / `--hard` / etc. without explicit
  user authorization for that specific action. Never `git branch -D`
  reflexively — investigate first if `-d` refuses.
- **Post-merge GitHub review is part of done.** Step 4c.7 verifies the
  merge landed (`gh pr view --json state`), the remote branch is gone
  (`ls-remote --heads` empty), and the merge commit is at `origin/main`
  tip. Step 4c.8 verifies the local side: single `main` branch, no stale
  worktrees, clean status. Both must pass before declaring done.
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
start (if needed), commit + push the branch, open PR, **provide PR review
and wait for chat-level authorization**, run `gh pr merge <num> --merge
--delete-branch`, then remove the worktree as part of Item 12 post-merge
cleanup (Step 4c.6 — `git worktree remove .claude/worktrees/<dir>`).
