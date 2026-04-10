---
name: index-memory-writer
description: Subagent template for updating _index.md and .auto-memory files during housekeeping
agent: general-purpose
allowed-tools: Read Write Edit Glob Bash
---

# Index + Memory Writer — board_prep_intel

You are updating the directory index and memory files for the board_prep_intel
ABFM ITE Intelligence System as part of session housekeeping.

## Your Inputs (injected by parent skill)

- New BATON number and filename
- Recon data — DB counts, script counts, PDF tier counts, git hash, date
- Session changes — what was added/removed/modified this session

## Files You Own

1. C:\Users\mpsch\Desktop\board_prep_intel\_index.md
2. C:\Users\mpsch\Desktop\board_prep_intel\.auto-memory\project_overhaul_state.md
3. C:\Users\mpsch\Desktop\board_prep_intel\.auto-memory\project_current_db_state.md
4. C:\Users\mpsch\Desktop\board_prep_intel\.auto-memory\MEMORY.md (conditional)

---

## Task 1 — _index.md

Read the file first. It is large — use offset/limit to locate the header rather
than reading all 500+ lines.

What to update:
- "Last Updated" line: update BATON number and session slug
- BATON pointer reference: old filename → new filename
- Session summary line: 1-sentence description of this session
- Script counts: only if scripts were added or removed
- DB row counts: only if tables changed this session

What NOT to change:
- Directory tree structure (only change if directories literally changed)
- File counts that did not change
- Architecture descriptions

Header format:
  Last Updated: YYYY-MM-DD (BATON NNN – [1-sentence session description])


## Task 2 — project_overhaul_state.md

Read the file. Update:
- Line 2: Last updated: YYYY-MM-DD (BATON NNN)
- Module State table: update any counts that changed (PDFs, scripts, DB rows)
- Deferred Flags table: update status of flags closed or changed this session
- Intelligence 2.0 Status: update if any layer changed
- Session notes: append a bullet for this session if significant work was done

What NOT to change:
- Historical session notes — append only, never delete
- Architecture or convention descriptions
- Plugin and capability entries unless they changed

---

## Task 3 — project_current_db_state.md

Read the file. Update:
- Line 2: Last verified: YYYY-MM-DD (BATON NNN)
- DB table row counts: update rows that changed this session
- Schema Notes: add new schema changes (columns added/dropped, new tables)
- DB Changes section: add a new entry if any DB changes were made

If no DB changes this session, only update the header line (BATON + date).

---

## Task 4 — MEMORY.md (conditional — only if something new to remember)

Only update MEMORY.md if the session introduced information that future Claude
instances should know across conversations. Examples:
- A new locked rule was established
- A significant architectural decision was made
- A new deferred flag was created that Claude should proactively watch
- A new tool, plugin, or capability was deployed

If updating, add one line to MEMORY.md index:
  - [Short title](filename.md) — one-line hook (under 150 chars)

Then write the corresponding memory file to .auto-memory/ or .auto-memory/memory/.

Do NOT update MEMORY.md for routine housekeeping with no architectural changes.

---

## Quality Rules

- Read before writing. Never overwrite without reading current content first.
- Edit, don't rewrite. Use Edit tool for targeted changes. Use Write only for
  substantial restructuring.
- Inherit unchanged numbers. If a count didn't change, leave it — don't re-enter
  it from scratch (risk of introducing errors).
- BATON number is usually the only change in housekeeping-only sessions. That is fine.
