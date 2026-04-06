---
name: feedback_housekeeping
description: Full housekeeping sweep checklist — 11 items, check every one, update only if needed
type: feedback
---

When the user requests a "housekeeping sweep", "housekeeping update", or any similarly named task, check ALL 11 items below. **If no updates are needed for an item, that's fine — do not force updates. But check every item every time.**

1. **`_index.md`** — rewrite to reflect current directory structure, script counts, and DB numbers
2. **New BATON** — increment BATON number, document all session decisions + deferred flags + next steps + rationale (*why* behind decisions, not just what was done)
3. **Retire old BATON** — move the previous active BATON to `baton_archive/`
4. **`CLAUDE.md`** — update Active State table (BATON pointer, git hash, script counts) + Next Steps section
5. **`.auto-memory/MEMORY.md`** — update index descriptions to reflect current memory file state
6. **`.auto-memory/project_overhaul_state.md`** — update module state, key numbers, deferred flags
7. **`.auto-memory/project_current_db_state.md`** — update table row counts and any schema changes
8. **Root READMEs** — update both `README.json` AND `README_PROJECT.md` with current BATON pointer, DB numbers, module script counts, and any structural changes. These are the human-readable entry points for anyone opening the project cold.
9. **`auto-memory-copies/`** — sync local memory backup files (git-tracked mirror of `.auto-memory/`)
10. **Projects Folder Instructions** — check if conventions, modules, architecture, or session startup docs have changed; update if so
11. **Git** — stage and commit any new or modified scripts; confirm clean working tree

**Why the READMEs keep going stale:** They were listed last and got deprioritized when sessions ran long. They now have equal weight as all other items — check them explicitly, every sweep.

**How to apply:** Do not declare a housekeeping sweep complete until all 11 items have been checked. If context runs short, flag exactly which items remain — do not silently skip them.
