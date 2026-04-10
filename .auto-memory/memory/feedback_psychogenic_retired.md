---
name: Psychogenic fully retired
description: "Psychogenic" was a legacy body system category — not a real clinical term. Fully retired 2026-04-10.
type: project
---

"Psychogenic" was the legacy DB-side canonical value for psychiatric/behavioral questions. Retired 2026-04-10.

## Why

Not a real clinical category — artifact of early categorization. Confusing and misleading to domain experts.

## What Was Done

**DB Migration:** 12 script files updated, DB migrated (120 rows questions.body_system_merged + 82 rows aafp_questions.body_system → Psychiatric/Behavioral). questions.body_system (source data from original ABFM PDFs) intentionally left untouched.

**Scripts updated:**
1. ite_analyzer_v3.py — BODYSYSTEM_PDF_NORM dict expanded + runtime normalization
2. ite_parser.py — PDF text parser recognizes pre-2024 variants
3. 00_database/scripts/retire_psychogenic.py — NEW migration script
4. 9 additional analysis + pipeline scripts — import normalize function

**Root causes (DEFERRED-PRACTICE-Q-COVERAGE) fully resolved:**
- Root Cause 1: JS threshold mismatch (relative vs hard 0.70) — Fix A in ite_report_builder_v2.js
- Root Cause 2: PDF compound header split ("Psychiatric/Behavioral" rendered as 2 spans) — Fix B in ite_parser.py
- Root Cause 3: BODYSYSTEM_PDF_TO_DB mapped "Psychiatric/Behavioral" → legacy ["Psychogenic"] — Fix C in ite_analyzer_v3.py + v2

## How to Apply

If you see "Psychogenic" in derived columns or new code, replace with "Psychiatric/Behavioral". 

**Never modify questions.body_system** (original source data from ABFM PDFs).

## 4 Intentional Legacy Aliases Kept in Code

These are kept for backwards compatibility and to document the history:

1. **BODYSYSTEM_PDF_NORM** in ite_analyzer_v3.py — normalizes old DB values at runtime
2. **BS_SYSTEMS** in ite_parser.py — comment only; recognizes pre-2024 PDF text variants
3. Comment in 00_body_system_extractor.py — explains original categorization
4. Docstring in 02b_generate_hy_inserts_v2.py — references legacy naming

These do NOT propagate new "Psychogenic" data — they are defensive aliases only.
