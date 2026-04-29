# Agent Template: Manifest Writer

## Purpose
Updates the two public-facing manifest files that describe the project to external readers (GitHub, other collaborators). Surgical updates only — do not rewrite entire files.

## Files to Update

| File | Location | What it tracks |
|------|----------|----------------|
| `CLAUDE.md` | project root | Active State table, Next Steps, locked rules, module map |
| `REPO_MAP.md` | project root | Directory structure, counts, BATON pointer |

## Update Protocol

### CLAUDE.md

Only update the `## Active State (update each session)` table and the `## Next Steps` section.

**Active State table rows to update each session:**
- `Active BATON` → new BATON filename + one-line summary
- Any DB row counts that changed (only changed ones — don't touch stable rows)
- `Git branch` → current hash + push status
- Script counts if M1/M2/M3 counts changed

**Next Steps section:**
Replace entirely with current priorities. Use format:
```markdown
### Immediate
1. **FLAG-NAME** — description

### Short-term
2. **FLAG-NAME** — description
```

**DO NOT touch:**
- `## Terms — Decode These First` table
- `## Module Map` table
- `## Locked Rules` section
- Any other section not listed above

### REPO_MAP.md

Update:
- Header timestamp / Last Updated date
- BATON pointer line
- DB count block (if present)
- Script count block (if present)
- Any `Last verified` or `as of` date references

## Rules

1. **Read first.** Always use Read tool before editing.
2. **Surgical edits only.** CLAUDE.md locked rules must never be touched.
3. **Preserve table formatting.** Don't reflow markdown tables — keep column alignment.
4. **Active State only reflects current DB.** Don't pad numbers or add explanatory text to the table cells — keep them terse.

## After Writing

Confirm:
- `CLAUDE.md: Active BATON → 062, {N} DB rows updated, Next Steps replaced`
- `REPO_MAP.md: BATON pointer → 062, date → {YYYY-MM-DD}, {N} counts updated`
