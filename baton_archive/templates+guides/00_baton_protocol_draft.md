---
## BATON Protocol — Session Handoff System
**Version:** 2.0 — Updated March 23, 2026

---

### What the BATON Is

The BATON is a structured session handoff document that allows a fresh Claude session to resume work at full context without inheriting an expensive conversation history. It is the single source of truth for pipeline state between sessions.

**Why it exists:** Claude sessions accumulate context (tool calls, file contents, intermediate results) that grows expensive and eventually needs to be cut. Rather than continuing long threads, this project uses short focused sessions with a BATON handoff. A well-written BATON carries ~3% of the tokens of a full conversation while preserving 100% of the actionable state.

**Where it lives:** `00_#PROJECT_OVERHAUL/BATON_active_NNN_YYYYMMDD_HHMM.md`
- Always at the PROJECT_OVERHAUL root
- Always has "active" in filename
- Always has a sequential number (NNN) — first is 001, increments with every new BATON
- **Only one BATON_active file should ever exist at root.** When a new one is written, the old one is archived first. No exceptions.

---

### BATON Numbering Convention

Each BATON gets a sequential 3-digit number prefix: `001`, `002`, `003`...

Format: `BATON_active_NNN_YYYYMMDD_HHMM.md`
Archive format: `BATON_NNN_YYYYMMDD_HHMM.md`

The number makes it instantly clear how many sessions this project has had and makes it easy to reference a specific session ("pull up BATON 014"). Never reuse or skip numbers.

---

### Loading a BATON (Session Start)

When a new session begins with a BATON attached:

1. **Read the BATON fully before doing anything.** Do not ask clarifying questions that are already answered in the document.
2. **Echo back the current state in 3-4 sentences** — phase, open flags, and the immediate next step. This confirms alignment before any work begins.
3. **Treat the NEXT STEPS section as your task queue.** Work top-to-bottom unless instructed otherwise.
4. **Treat DEFERRED FLAGS as frozen.** Do not act on deferred flags unless explicitly asked. Do not lose them — they carry forward to every future BATON.
5. **Treat CRITICAL FILE LOCATIONS as ground truth.** Do not infer paths from context — use what's in the BATON.

---

### "BATON me" — The Seven-Step Handoff Lifecycle

At any natural stopping point, the user may say **"BATON me"** (or equivalent: "update the BATON", "wrap up", "handoff"). This triggers the seven-step handoff lifecycle below. **Follow steps in order.**

---

#### Step 1 — Ask the Auto-Memory Question (BEFORE anything else)

Before archiving or writing anything, ask:

> **"Before I close this out — is there anything from this session that should be added to auto-memory?"**

Wait for the user's response. If they have additions, update the relevant auto-memory file(s) and the MEMORY.md index **before proceeding to Step 2.** Auto-memory is updated first so the new BATON inherits it.

Auto-memory lives at two locations (keep both in sync):
- Live: `/sessions/.auto-memory/` (loaded every session)
- Durable: `re-org_guidance/auto-memory-copies/` (persists on Windows drive)

---

#### Step 2 — Archive the Active Root BATON

**This is non-negotiable and must happen before Step 3.**

1. Identify the current `BATON_active_NNN_YYYYMMDD_HHMM.md` at project root
2. Rename it: drop "active" → `BATON_NNN_YYYYMMDD_HHMM.md`
3. Move it to `baton_archive/`
4. Confirm: **no BATON_active file remains at root** before proceeding

If no active BATON exists at root (fresh start), skip this step.

---

#### Step 3 — Write the New Active BATON

1. Determine the next sequential number (last archived + 1)
2. Create `BATON_active_NNN_YYYYMMDD_HHMM.md` at project root using current timestamp
3. This is now the **only** BATON_active file at root

See "What a Good BATON Contains" below for required sections.

---

#### Step 4 — Update the PROJECT_OVERHAUL Root Index File (`_index.md`)

The `_index.md` maps **only the `00_#PROJECT_OVERHAUL` subfolder** — not the full `claude_knowledge` tree.

1. Scan for structural changes this session: folders created/renamed/moved/deleted, file counts changed
2. If structural changes occurred: update top-level tree, subfolder trees, file counts
3. Append a dated housekeeping log entry for everything that changed (or confirm no-change)
4. Spot-check at least 3 folder counts against disk before writing
5. Stale counts are worse than no index — verify before saving

---

#### Step 5 — Update Root README Files

Update `README.json` and `README_PROJECT.md` if any of the following changed:
- Module folder structure
- Script inventory
- DB record counts
- Phase or architecture decisions

These are persistent records, not operational documents. Update at phase boundaries or when the ground truth changes.

---

#### Step 6 — Update Project Memory (Auto-Memory Sync Check)

Review what was accomplished in Steps 1–5. Ask: does any of this change what a future Claude needs to know from the start? If yes, update the relevant auto-memory file and MEMORY.md index in both locations.

Common triggers:
- Architecture decision locked
- New flag added or resolved
- DB state changed significantly
- New script or module introduced
- Rebuild guideline confirmed or modified

---

#### Step 7 — End Session

Confirm with the user that everything is captured. End cleanly unless directed to continue.

> **"BATON NNN is live. [One sentence on what was captured.] Ready to close unless there's anything else."**

---

### When to Suggest "BATON me" Proactively

- A major task just completed (script run, enrichment batch, parser fix, migration)
- Work is pivoting to a clearly different sub-task or flag
- A long tool-heavy exchange just concluded
- User asks "are we good?" or "is that it?"

Do NOT wait to be asked if a natural seam is obvious. Say: *"That's a good stopping point — want me to BATON this?"*

---

### What a Good BATON Contains

A BATON is not a conversation summary. It is a **state snapshot + task queue**.

| Section | Purpose |
|---|---|
| **Header** | Phase, BATON number, date, one-line status. New Claude should understand where the project stands in 10 seconds. |
| **Rebuild North Star** | The 5 core rebuild structuring guidelines (see below). Stable section — copy forward unchanged unless a guideline is modified. |
| **Deferred Flags** | Numbered open issues with specific, actionable resolution steps. Carry forward every flag until explicitly resolved. Never collapse or summarize flags — preserve the full action spec. |
| **Migration Tracker** | What moved or changed this session. What still needs to migrate into `00_#PROJECT_OVERHAUL`. Keeps the overhaul on track across sessions. |
| **Where We Are** | Quantitative results from the most recent work. Include counts, file names, run identifiers. |
| **What Was Built This Session** | What changed and *why*. Include before/after for bug fixes. Future Claude needs to understand the reasoning, not just the outcome. |
| **Next Steps** | Ordered task queue. Immediate items at top, deferred at bottom. Be specific — include script names, flag numbers, expected outputs. |
| **Critical File Locations** | Full paths for every active file. No assumptions. |
| **Key Architecture Reminders** | Design constants that must not be accidentally changed — codon format, pipeline order, thresholds, schema conventions. |
| **Known Issues** | Low-priority documented items. Prevents re-investigation of already-understood quirks. |

---

### Rebuild North Star — 5 Core Principles (Copy Into Every BATON)

These are locked guidelines for the PROJECT_OVERHAUL rebuild. Carry them forward in every BATON unchanged unless Mikey explicitly modifies one.

1. **Git is the version control layer.** All scripts, schemas, configs belong in a git repo. Structure the rebuild to make git adoption trivial.
2. **BATON is the intent layer.** Sits on top of git. Git tracks what changed; BATON tracks what matters and what's next. Permanent regardless of git adoption.
3. **Formal schemas first.** SQL CREATE TABLE statements defined before build scripts are written. Schema drift is a first-class failure mode.
4. **OUTPUT_SCHEMA for all agents.** Use the SDK's `output_format` parameter. No prompt-hacking for structured output.
5. **Cryptographic hash ART-IDs.** Proof of provenance — the ID is earned by completing the pipeline. Deferred until library is stable.

---

### BATON Quality Standards

- **Flags are complete.** Every open flag from the previous BATON is present — resolved with note, or carried forward unchanged.
- **Next Steps are executable.** A fresh Claude with no prior context should know exactly what to run, edit, or investigate.
- **Architecture reminders are stable.** Codon format, pipeline order, threshold values identical session-to-session unless explicitly changed.
- **File paths are verified.** Do not carry forward stale paths.
- **Status is honest.** Do not write "COMPLETE" for anything with unresolved edge cases unless those are in Known Issues.
- **Rebuild North Star is present.** All 5 principles copied into every BATON.
- **BATON number increments.** Never skip or reuse a number.

---

### Document Hierarchy

| Document | Updated When | Purpose |
|---|---|---|
| `BATON_active_NNN_*.md` | Every session (Steps 2–3) | Operational state — what's open, what's next, what just happened |
| `_index.md` | Every BATON (Step 4) | Ground-truth map of `00_#PROJECT_OVERHAUL` folder only |
| `README.json` / `README_PROJECT.md` | Phase boundaries or ground-truth changes (Step 5) | Persistent project record |
| Auto-memory files | When new durable context is confirmed (Steps 1 + 6) | Cross-session context for Claude |
