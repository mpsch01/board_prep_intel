---
name: board-startup
description: Session orientation for the board_prep_intel ITE Intelligence project. ALWAYS use this skill at the start of any session in the board_prep_intel project, or whenever the user says "orient me", "startup", "start session", "what's the current state", "catch me up", "where did we leave off", "what's in the BATON", or any similar phrase asking about current project state. Also trigger when the user says "let's get started" or "let's continue" without providing specific task detail. This is the mandatory session initialization sequence — do not skip it.
---

# Board Prep Intel — Session Startup

This skill runs the mandatory session orientation sequence for the board_prep_intel project.
It reads the 4 key files in order and produces a structured briefing so every session
starts with full context.

## Why this matters

Without running this sequence, you are working from memory alone — and memory drifts.
The BATON carries decisions, deferred flags, and next steps that aren't in the code.
The index carries current file counts that change every session. Missing this context
leads to re-asking questions the user already answered, proposing work already done,
or missing deferred issues.


## Step 1 — Find the project root

The project lives in the user's selected workspace folder. The root is the directory
containing `_index.md`, `BATON_active_*.md`, `CLAUDE.md`, and `REPO_MAP.md`.
In this Cowork session it will be under `/sessions/modest-cool-shannon/mnt/board_prep_intel/`
(Linux sandbox path) or `C:\Users\mpsch\Desktop\board_prep_intel` (user's machine path).

If any of the 4 files are missing, note it clearly and proceed with what's available.
Do not abort the sequence.

## Step 2 — Read the 4 files in parallel

Run all 4 reads simultaneously (they are independent):

1. `_index.md` — directory map, file counts, schema coverage
2. `BATON_active_*.md` — find the active BATON (highest number suffix), read it fully.
   This is the most important file: DB state, deferred flags, explicit next steps.
3. `CLAUDE.md` — active state table, locked conventions, terminology decoder
4. `REPO_MAP.md` — current-state architectural overview, module map, PDF/DB counts

To find the active BATON: glob for `BATON_active_*.md` in the project root and read
the file with the highest number.


## Step 3 — Produce the orientation brief

After reading all 4 files, output a structured briefing using this exact format:

---

## Session Orientation — [today's date]

**Active BATON:** BATON_active_XXX.md
**DB State:** [article count, question count, QID-article pairs — from BATON or REPO_MAP.md]
**PDF Library:** [tier counts if available]

**Where we left off:**
[2-3 sentences summarizing what was completed in the last session, drawn from BATON]

**Deferred flags:**
[List any open flags, TODO items, or unresolved issues from the BATON. If none, say "None."]

**Next steps (from BATON):**
[The explicit next steps carried in the BATON, verbatim or closely paraphrased]

**Active conventions to keep in mind:**
[1-2 locked rules from CLAUDE.md most relevant to likely upcoming work]

---

Then ask: "What would you like to work on today?"

## What NOT to do

- Do not start any work before completing this sequence
- Do not summarize from memory — read the actual files every time
- Do not skip the BATON because it seems long — it is the handoff document
- Do not ask the user to remind you of context that is already in these files
