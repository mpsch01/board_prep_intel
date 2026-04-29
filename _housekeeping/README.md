# _housekeeping/

Session housekeeping templates for the board_prep_intel project.

## ⚠️ MAC ONLY

The `session-housekeeping` skill uses these agent templates when running on the Mac.
On the Windows home PC, the skill reads templates from a separate location outside this repo.
**This folder does not need to be created or maintained on the Windows PC.**

## Contents

### agents/
Subagent prompt templates used by the `session-housekeeping` skill during the end-of-session sweep.

| Template | Purpose |
|----------|---------|
| `baton-writer.md` | Writes the new BATON handoff document |
| `index-memory-writer.md` | Updates `_index.md` and all three `.auto-memory/` files |
| `manifest-writer.md` | Updates `CLAUDE.md` Active State table and `REPO_MAP.md` |

## Usage

The orchestrating Claude instance (running the `session-housekeeping` skill) should:
1. Run Step 0 recon (gather DB counts, git hash, script counts, current BATON number)
2. Read the relevant template from `agents/` before spawning each subagent
3. Pass full recon data + session context in the subagent prompt
4. Spawn all 3 agents in parallel (Wave 1)

Templates were extracted from the session-housekeeping skill's built-in agent prompts and stored here for portability across machines.
Last updated: 2026-04-29 (BATON 062)
