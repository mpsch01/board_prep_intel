# ICD-10 Hidden Enrichment Layer — BATON 055 Architecture Decision

**Date:** 2026-04-13 (BATON 055)  
**Component:** `ite_analyzer_v3.py` — match_practice_questions_v3() enrichment  
**Status:** Implemented + tested

---

## Overview

The ICD-10 codes table (article_icd10, question_icd10, aafp_question_icd10) now serves a **hidden enrichment layer** for practice question matching. This layer is:

1. **Invisible to the resident** — Not displayed in any report or recommendation
2. **Taxonomy-stable** — ICD-10 codes are normative clinical classification; not subject to concept-tag label variance
3. **Precision layer** — Provides mathematical scoring signal beyond concept tags alone
4. **Analyst-only context** — Used internally in match_practice_questions_v3() for question ranking

---

## Implementation Details

### Data Flow
```
icd10_profile (from resident's questions)
    ↓
[ICD-10 code distribution: {ICD10: count, ...}]
    ↓
match_practice_questions_v3(icd10_profile=icd10_profile, ...)
    ↓
[Internal scoring using question_icd10 coverage]
    ↓
[Ranked practice question recommendations]
    ↓
[Report output — icd10_profile NEVER rendered]
```

### Design Rationale

**Why hidden?**
- Residents work with clinical concepts and body systems — ICD-10 codes add technical overhead without clinical value
- Reporting clarity: one signal (concept-based) to understand per resident

**Why ICD-10 specifically?**
- **Taxonomy stability:** ICD-10 codes are normative and stable across years; concept tags are internal and subject to evolution
- **Cross-domain precision:** Codes map to both clinical pathways (Layer 3) and PubMed research (Layer 2)
- **Precision advantage:** 2,219 unique ICD-10 codes across 4,753 practice question-code pairs enable fine-grained matching that concept tags alone cannot achieve

**Why not replace concept tags?**
- Concept tags remain the primary resident-facing signal (human-readable, clinically intuitive)
- ICD-10 is a *supplementary* enrichment layer, not a replacement
- Dual-signal approach reduces false negatives in question recommendation

---

## Technical Anchor Points

| Item | Details |
|------|---------|
| **icd10_profile** | Dict: {ICD10_code_str: count, ...} — passed to match_practice_questions_v3() |
| **Source tables** | question_icd10 (5,218 rows), aafp_question_icd10 (4,753 rows) |
| **Test coverage** | test_v3_changes.py — 5 test suite validation |
| **Report output** | icd10_profile NOT included in ite_report_builder_v2.js template or HTML |
| **Analyst context** | Available in ite_analyzer_v3.py state for debugging/refinement; not persisted to disk unless explicitly exported |

---

## Future Extensions

1. **Layer 4 trend analysis:** ICD-10 codes could be aggregated into trend reports for program-level analysis (DEFERRED-PROGRAM-TREND)
2. **Pathways refinement:** clinical_pathways scoring could weight ICD-10 code overlap
3. **PubMed intelligence (Layer 2):** article_icd10_vec could be queried for semantic similarity based on resident's ICD-10 profile

---

## Related Decisions

- **Concept tags remain primary:** CLAUDE.md locked rule — concept-based enrichment is the resident-facing signal
- **Hidden-by-design:** No console output, no JSON export, no report rendering for icd10_profile
- **QC:** Verify test_v3_changes.py passes on each M3 analysis run
