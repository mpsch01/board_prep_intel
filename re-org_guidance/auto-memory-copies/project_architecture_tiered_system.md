---
name: project_architecture_tiered_system
description: Two-tier pipeline architecture ($right_click$ vs local_lite), nnn_XXXX ART-ID scheme, VC gate, cryptographic hash vision, 5-phase overhaul plan
type: project
---

## Two-Tier Pipeline Architecture (Decision Locked — March 19, 2026)

### The VC Gate
`session_hy_inserts_v7.json` is THE source of truth. 48 sessions, 229 QIDs, 352 unique citation strings. An article's presence in this file's `refs[]` is the ONLY criterion for $right_click$ tier. DB membership alone is NOT sufficient.

**Why:** Previous sessions incorrectly treated "codon = matched to ite_intelligence.db". The correct definition: codon = references whose linked questions are contained within the AAFP Board Prep Video Course Outline. This is a CURATED SUBSET.

### Tier 1: `$right_click$` (Dense Path)
- Target: VC-cited articles only (~352 unique citations)
- Processing: Full extraction via Claude API, synthesis, rich DOCX with ITE Intelligence callouts
- Cost: High (multiple API calls per document)
- Status: 59 processed, 266 need PDFs sourced

### Tier 2: `local_lite` (Local Path)
- Target: All ITE-linked articles NOT in VC outline (~1,138+ articles)
- Processing: DB-only synthesis — zero API calls. Uses concept_tags, citation info, question stems, ICD-10 codes
- Cost: Near-zero
- Status: Not yet built
- "local_lite is a genuine product, not a consolation path"

### The `nnn_XXXX` ART-ID Rename (FLAG 33 — NOT YET IMPLEMENTED)
Current: `ART-XXXX` (flat, no tier signal)
Proposed: `nnn_XXXX` where:
- `001_XXXX` through `352_XXXX` = VC-cited ($right_click$)
- `000_XXXX` = non-VC (local_lite)

Benefits: instant visual tier ID, auto-sort, pipeline routing without DB lookup.
Migration touches EVERYTHING: DB fields, filenames, JSONs, DOCXs, crosswalk, scripts.
**DO NOT implement until full migration plan with rollback strategy is written and reviewed.**

### Cryptographic ART-ID Vision (Future — Deferred Until Library Stable)
ART-IDs derived from cryptographic hash generated at pipeline COMPLETION. The ID = proof of provenance — only way to receive an ART-ID is to pass through the full download → extraction → enrichment → synthesis pipeline. Also: richer human-readable filename prefixes (topic keywords, specialty). Discussed March 20 session 2.

### 5-Phase Overhaul Plan (from BATON_active_20260319)
1. Define Canonical Article Sets (confirm VC list, resolve 27 unmatched citations, define local_lite set)
2. Design New ID System (finalize nnn_XXXX, build mapping table, plan rollback)
3. Plan Two-Tier Pipeline Architecture (spec both pipelines, routing logic)
4. Plan the Migration (DB script, file script, JSON script, DOCX catalog, crosswalk rebuild)
5. Source Missing PDFs (266 VC articles with no PDF)

### Design Principles (Locked)
1. The VC outline is the primary gate
2. The ART-ID must carry tier information
3. Fix the data, not the code
4. No files moved or renamed until migration plan is written and tested on a copy
5. local_lite is a genuine product

**How to apply:** Any new article records should use current sequential ART-XXXX format. The nnn_XXXX migration will renumber everything later. Do not mix conventions.
