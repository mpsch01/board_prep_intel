---
name: BATON Protocol — Session Handoff System v2.0
description: Seven-step session handoff lifecycle. Sequential BATON numbering, auto-memory check first, archive-then-replace at root, migration tracker, 5 rebuild principles in every BATON. Updated March 23, 2026.
type: reference
---

## BATON Protocol v2.0

The BATON is a structured session handoff document — state snapshot + task queue, NOT a conversation summary. ~3% token cost, 100% actionable state preserved.

### Location & Naming
- **Active:** `board_prep_intel/BATON_active_NNN_YYYYMMDD_HHMM.md` (project root, ONE file only)
- **Archived:** `board_prep_intel/baton_archive/BATON_NNN_YYYYMMDD_HHMM.md` (drop "active", keep number + datetime)
- **NNN = sequential 3-digit number.** 001, 002, 003... Never skip or reuse.

### Session Start (Loading a BATON)
1. Read BATON fully before doing anything
2. Echo back current state in 3-4 sentences (phase, open flags, immediate next step)
3. Work NEXT STEPS top-to-bottom unless instructed otherwise
4. DEFERRED FLAGS are frozen — carry forward, do not act on unless asked
5. CRITICAL FILE LOCATIONS are ground truth — do not infer paths

### "BATON me" — Seven-Step Lifecycle (follow in order)

**Step 1 — Ask the auto-memory question FIRST (before anything else):**
> "Before I close this out — is there anything from this session that should be added to auto-memory?"
Wait for response. Update auto-memory BEFORE proceeding to Step 2.
Both locations: live `/sessions/.auto-memory/` AND durable `re-org_guidance/auto-memory-copies/`.

**Step 2 — Archive the active root BATON:**
Rename → drop "active" → move to `baton_archive/`. Confirm NO BATON_active file remains at root before Step 3.

**Step 3 — Write the new active BATON:**
Next sequential number (last archived + 1). `BATON_active_NNN_YYYYMMDD_HHMM.md` at project root. Only one exists at root at any time.

**Step 4 — Update `_index.md`:**
Maps `board_prep_intel` subfolder ONLY (not full claude_knowledge tree). Update trees/counts if structure changed. Append dated housekeeping log entry. Spot-check 3+ folder counts against disk.

**Step 5 — Update root README files:**
`README.json` + `README_PROJECT.md` if module structure, script inventory, DB counts, or architecture decisions changed.

**Step 6 — Sync auto-memory:**
Did Steps 1–5 produce anything new and durable? If yes, update relevant auto-memory file(s) and MEMORY.md index in both locations.

**Step 7 — End session:**
> "BATON NNN is live. [One sentence summary.] Ready to close unless there's anything else."

### BATON Required Sections
- **Header:** BATON number, phase, date, one-line status (10-second orientation)
- **Rebuild North Star:** 5 locked principles (copy forward unchanged every BATON — see below)
- **Deferred Flags:** Numbered open issues with full action specs — never collapse or summarize
- **Migration Tracker:** What moved/changed this session; what still needs to come into `board_prep_intel`
- **Where We Are:** Quantitative results, counts, filenames, run identifiers
- **What Was Built:** What changed and *why*, before/after for bug fixes
- **Next Steps:** Ordered, executable by fresh Claude with zero prior context
- **Critical File Locations:** Full paths, no assumptions
- **Key Architecture Reminders:** Design constants (codon format, pipeline order, thresholds)
- **Known Issues:** Low-priority, documented, prevents re-investigation

### Rebuild North Star — Include in Every BATON
1. **Git = version control layer.** Scripts/schemas/configs in a git repo. Structure rebuild for easy git adoption.
2. **BATON = intent layer.** On top of git. Git tracks what changed; BATON tracks what matters. Permanent.
3. **Formal schemas first.** SQL defined before build scripts. Schema drift is a first-class failure mode.
4. **OUTPUT_SCHEMA for all agents.** SDK `output_format` parameter. No prompt-hacking.
5. **Cryptographic hash ART-IDs.** Proof of provenance. Deferred until library is stable.

### Proactive Trigger — Suggest BATON When:
- Major task just completed
- Work pivoting to a different sub-task or flag
- Long tool-heavy exchange just concluded
- User asks "are we good?" or "is that it?"

### Quality Standards
- All flags present (resolved with note, or carried forward)
- Next Steps executable by fresh Claude with zero prior context
- Rebuild North Star present in every BATON
- BATON number increments (never skip/reuse)
- File paths verified (no stale paths)
- Status honest (no "COMPLETE" with unresolved edge cases unless in Known Issues)

### Document Hierarchy
- `BATON_active_NNN_*.md` → operational state (every session)
- `_index.md` → ground-truth map of `board_prep_intel` only (every BATON, Step 4)
- `README.json` / `README_PROJECT.md` → persistent project record (phase boundaries, Step 5)
- Auto-memory files → cross-session Claude context (Steps 1 + 6)
