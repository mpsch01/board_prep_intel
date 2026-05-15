# Agent Prompt Templates — corpus-integrity-qc

**Canonical path:** `<PROJECT_ROOT>/.claude/skills/corpus-integrity-qc/agents/`

This directory holds the prompt templates dispatched by the coordinator during
**Phase 2 — Dispatch three audit agents in parallel** (see `../SKILL.md`).

## Cross-platform mirroring

The full path resolves the same on both platforms:

| Platform | Absolute path |
|---|---|
| Mac (Claude Code primary workflow) | `/Users/mpsch/Mac Storage/board_prep_intel/.claude/skills/corpus-integrity-qc/agents/` |
| Windows (mirror) | `C:\Users\mpsch\Desktop\board_prep_intel\.claude\skills\corpus-integrity-qc\agents\` |

When syncing the skill across machines, copy this directory verbatim into the
same relative location under the Windows project root. The coordinator resolves
agent prompts as `SKILL_DIR / "agents" / "{layer_name}-auditor.md"`, so the
filenames must match exactly.

## Expected files (built incrementally)

| File | Layer | Role |
|---|---|---|
| `text-fidelity-auditor.md` | A | Runs `scripts/layer_a_text.py`, writes `findings_layer_a.json`. |
| `citation-linkage-auditor.md` | B | Runs `scripts/layer_b_citation.py`, writes `findings_layer_b.json`. |
| `structural-integrity-auditor.md` | C | Runs `scripts/layer_c_structural.py`, writes `findings_layer_c.json`. |
| `fix-applier.md` | D | Reads `fixes.sql` (after user approval) and applies Tier 1 SQL within a `BEGIN`/`COMMIT`. |

Each agent gets its own clean context window. They are invoked via the `Agent`
tool with `subagent_type: "general-purpose"` and a self-contained prompt that
includes the explicit script path + output path. The coordinator (main thread)
waits for all three to write their findings JSON, then proceeds to Phase 3.

## Locked rule that applies

**Source data is protected.** Agents A/B/C run in detect-only mode with the DB
opened via `connect_db_readonly()` (immutable URI). Only the fix-applier writes
to the DB, and only after explicit per-tier user approval.
