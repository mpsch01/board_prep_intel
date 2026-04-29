# Agent Template: Index + Memory Writer

## Purpose
Updates the four memory/index files that track project state between sessions. Always reads each file before editing — never overwrites from scratch.

## Files to Update

| File | Location | What it tracks |
|------|----------|----------------|
| `_index.md` | project root | Directory map, active BATON pointer, script/DB counts |
| `MEMORY.md` | `.auto-memory/` | Index of all memory files; session highlights |
| `project_overhaul_state.md` | `.auto-memory/` | Module state, PDF counts, session notes (running log) |
| `project_current_db_state.md` | `.auto-memory/` | DB table row counts, schema state, enrichment status |

## Update Protocol

### _index.md
- Update `Last Updated` date
- Update active BATON filename
- Update DB count block (articles, questions, key enrichment tables)
- Update script counts if changed
- Add a one-line entry to the `Completed` log at top

### MEMORY.md
- Update `Last updated` line
- Update description lines for `project_overhaul_state.md` and `project_current_db_state.md` to reference new BATON
- Add a new section entry summarizing this session's key decisions/changes
- Add any new deferred flags to Open Items

### project_overhaul_state.md
- Update `Last updated` line
- Update Module State table (DB counts, script counts)
- **Prepend** a new `## Session Notes (BATON {NNN})` block — NEVER delete old session notes
- Update Open Items / Deferred Flags table

### project_current_db_state.md
- Update `Last verified` date
- Update all table row counts to verified live numbers
- Add `## DB Changes (BATON {NNN})` section noting what changed and why
- If counts are higher than last BATON without explanation, note as "↑ pre-existing enrichment (source: {context})"

## Rules

1. **Read first.** Use the Read tool on each file before editing.
2. **Prepend session notes**, never replace. The running log is the historical record.
3. **Use verified numbers only.** Never estimate or round. If a count is approximate, write `~N`.
4. **Preserve all existing content** except stale dates and counts.
5. **One Edit call per file**, not multiple partial edits. Build the full replacement block, then apply.

## After Writing

Confirm each file was updated with a one-line summary:
- `_index.md: BATON pointer updated → 062, DB counts refreshed`
- `MEMORY.md: BATON 062 section added, Open Items updated`
- `project_overhaul_state.md: Session Notes (BATON 062) prepended, DB counts updated`
- `project_current_db_state.md: All counts refreshed, DB Changes section added`
