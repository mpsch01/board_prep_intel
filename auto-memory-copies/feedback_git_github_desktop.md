---
name: Git via GitHub Desktop — never CLI
description: Git commits must be done by user in GitHub Desktop, not via CLI. Claude prepares the staged-file list and commit message.
type: feedback
---

Never attempt `git add`, `git commit`, or `git rm` from the Linux sandbox during housekeeping. NTFS index.lock conflicts on the Windows-mounted repo cause frequent deadlocks that require manual intervention to clear.

**Why:** The `.git/index.lock` file gets created by git operations from the Linux sandbox and cannot be deleted from Linux (NTFS permissions). Clearing it requires Windows MCP PowerShell, which itself frequently times out. The whole sequence is fragile and wastes session time.

**How to apply:** At the end of every session housekeeping:
1. Produce a grouped **Files to Stage** list (new files / modified scripts / modified docs / deletions)
2. Produce a ready-to-paste **Commit message** ending with `Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>`
3. Ask the user to commit via GitHub Desktop and paste back the short hash
4. Update the `Git branch` row in CLAUDE.md Active State with: `main, latest → NEWHASH (post-commit)`

This also applies to any mid-session git operations — if git is needed, ask the user to run it rather than attempting from CLI.
