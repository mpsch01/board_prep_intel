---
name: baton-writer
description: Subagent template for writing a new BATON session handoff document
agent: general-purpose
allowed-tools: Read Write Glob
---

# BATON Writer — board_prep_intel

You are writing a new BATON session handoff document for the board_prep_intel
ABFM ITE Intelligence System. The parent skill provides your inputs below.

## Your Inputs (injected by parent skill)

- New BATON number (e.g., 053)
- Old BATON filename (e.g., BATON_active_052_...)
- Recon data — DB counts, PDF tier counts, script counts, git hash
- Session context — what was done, decisions made, deferred flags, next steps

## Output Location

Write to:
  C:\Users\mpsch\Desktop\board_prep_intel\BATON_active_NNN_YYYYMMDD_slug.md

Where:
- NNN = zero-padded 3-digit BATON number
- YYYYMMDD = today's date
- slug = 2-4 word snake_case session summary

---

## Required Sections (11 total)

### Section 1 — Header + Session Overview Table

```
# BATON NNN — YYYY-MM-DD — [Session Title]

**Active Session Handoff Document for board_prep_intel**

---

## Session Overview

| Item | Value |
|------|-------|
| **Date** | YYYY-MM-DD |
| **Previous BATON** | BATON_active_OLD_NNN_....md |
| **Git Hash (pre-commit)** | [hash from recon] |
| **Branch** | main |
| **Primary Goal** | [1-line description] |
| **Status** | ✅ Complete |
```

### Section 2 — Database State

Paste the full DB row count table from recon data. If no changes this session,
write "(inherited from BATON NNN-1 — no structural changes)" and copy the table.

```
## DATABASE STATE

| Table | Rows | Notes |
|-------|------|-------|
| articles | X,XXX | ... |
| questions (ITE) | X,XXX | 2018–2025 |
| aafp_questions | X,XXX | BRQ |
| qid_art_xref | X,XXX | |
| aafp_qid_art_xref | XXX | |
| article_icd10 | X,XXX | |
| question_icd10 | X,XXX | |
| aafp_question_icd10 | X,XXX | |
| clinical_pathways | X,XXX | |
| pubmed_pmid_cache | XXX | Layer 2 seed |
| article_icd10_vec | X,XXX | |
| question_icd10_vec | X,XXX | |
| icd10_vec | X,XXX | |
| article_currency | X,XXX | |
| article_citation_trend | X,XXX | |
```

### Section 3 — PDF Library

```
## PDF LIBRARY

| Tier | Count | Notes |
|------|-------|-------|
| VC_fail | XXX | Failed VC gate; awaiting enrichment |
| VC_pass | XXX | Passed VC gate; awaiting enrichment |
| local_lite | XXX | Enriched; not VC-cited |
| right_click | XXX | Enriched + VC-cited (top tier) |
| **ITE Total** | **XXX** | |
| AAFP | XX | citation_files/AAFP/ |
| ITE exams | 16 | All 8 years (2018–2025) x MC + critique |
```

### Section 4 — Session Summary: What Happened

Narrative of what was done. Use subsections (### Task 1: ...) per major work item.
Include: goal, what changed and why, root causes, scripts modified/created, DB changes.
For housekeeping-only sessions, state that explicitly and list what was captured/fixed.

### Section 5 — Script Inventory

```
## SCRIPT INVENTORY

| Module | Category | Count | Notes |
|--------|----------|-------|-------|
| M1 | Build (Python) | 6 | |
| M1 | Maintain (Python) | 26 | |
| M2 | Python | 75 | |
| M2 | JavaScript | 6 | |
| M3 | Python | 15 | |
| M3 | JavaScript | 2 | |
| M3 | JSON config | 1 | |
| M5 | TypeScript/TSX | 35 | |
| M5 | SQL migrations | 5 | |
```

Note any new scripts added or deleted this session.

### Section 6 — Deferred Flags

One subsection per active flag. Never carry forward a flag marked CLOSED.

```
## DEFERRED FLAGS

### DEFERRED-FLAG-NAME
**Status: ACTIVE — carry forward**

[What is deferred, why, and what is the blocker]

**Next action:** [Specific next step]
```

Standard flags to always check:
- DEFERRED-YOY-ROBUSTNESS — longitudinal_delta() edge cases in ite_analyzer_v3.py
- DEFERRED-PGY-BENCHMARKS — awaiting PGY 1-4 data from Mikey
- DEFERRED-AAFP-PDF-RETRY — awaiting AAFP site stability
- DATABASE_GUIDE.md Relocation — git rm old + git add new; commit

### Section 7 — Critical Reminders for Next Session

3-7 numbered items. Focus on traps, recent changes, and things easy to get wrong.
Write for a Claude instance with zero conversation history.

```
## CRITICAL REMINDERS FOR NEXT SESSION

1. **[Topic]** — [What to remember and why it matters]
2. ...
```

### Section 8 — Next Steps

```
## NEXT STEPS

### Immediate (next session)
1. **DEFERRED-FLAG-NAME** — [Exact action to take]

### Short-term
3. **[Item]** — [Action]
```

### Section 9 — Locked Rules (copy verbatim every BATON)

```
## LOCKED RULES (Never Override Without Mikey Confirming)

1. Fix the data, not the code. Messy data → clean upstream.
2. VC gate = sole criterion for right_click tier.
3. Source data protected. DB + PDFs + VC gate survive everything.
4. Dynamic paths only. Python: SCRIPT_DIR = Path(__file__).resolve().parent
5. No de novo JS (relaxed — use when needed, flag if clutter accumulates).
6. BATON first. Read the active BATON before any work.
7. QC after every integration. Schema-level column-by-column comparison.
8. Git via Desktop Commander. Use Python subprocess helper for commits.
9. shutil.rmtree BANNED. Use explicit file deletion or PowerShell Remove-Item.
10. Strategy 0 in every enricher. Codon parse always first.
11. Schemas before scripts. SQL CREATE TABLE defined before build scripts.
```

### Section 10 — Git Notes

```
## FOR THE REPO (Git Notes)

- **Branch:** main
- **Latest commit hash:** [hash]
- **Unpushed changes:** [describe, or "None — clean"]
```

### Section 11 — Footer

```
---

**End BATON NNN**
*Handoff ready for next Claude instance. Read this first before any work.*
```

---

## Quality Rules

- Never invent numbers. Use only what recon data explicitly provides.
- Deferred flags are cumulative. Carry all ACTIVE flags forward every BATON.
- Session Summary is narrative prose with subsections — not a bullet list.
- Write for the next Claude instance, not for Mikey. Assume zero context.
