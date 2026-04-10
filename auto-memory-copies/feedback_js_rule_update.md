---
name: JS rule update — build in whatever fits
description: No-de-novo-JS rule relaxed; use JS when it fits, flag multilingual clutter
type: feedback
---

The "no de novo JS" rule (Locked Rule #5 in CLAUDE.md) was implemented for a specific historical reason and is now relaxed.

**Updated rule:** Build in whatever language best fits the task — Python or JS. If the codebase starts accumulating multilingual complexity in a way that becomes clunky to maintain, flag it explicitly to Mikey.

**Why:** The original rule was a guardrail against JS sprawl during a period of active pipeline consolidation. That phase is complete.

**How to apply:** Default to Python for new scripts (it's the dominant language). Use JS when the task calls for it (e.g., existing JS pipeline, Node ecosystem tools). Speak up if language mixing is creating maintenance overhead.
