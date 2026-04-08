---
name: JS rule update — build in whatever language fits
description: The no-de-novo-JS rule has been relaxed; use JS or Python based on what fits the task; flag if multilingual clutter accumulates
type: feedback
---

The original "no de novo JS" rule was implemented for a specific purpose (managing codebase complexity) but is no longer a hard constraint.

**Why:** Mikey clarified during BATON 046 session (2026-04-07) that the rule should be context-sensitive, not absolute.

**How to apply:** Build new code in whichever language (Python or JS) best fits the task. If the codebase begins to accumulate significant multilingual clutter (many languages mixing without clear rationale), flag it to the user. Python remains the default for new M3 analytics scripts; JS remains appropriate for DOCX/report generation scripts.
