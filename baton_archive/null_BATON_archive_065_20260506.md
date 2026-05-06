# null_BATON_archive_065 — 2026-05-06 — Null Session / Deferred Flag Decisions

**Handoff from:** BATON_active_064_20260505_practice_question_system_complete.md
**Date:** 2026-05-06
**Session type:** Planning / orientation only — no code written, no DB changes
**Git hash:** 7920979 (verified clean, no changes)
**Status:** NULL SESSION

---

## Session Summary

Orientation session. Git and DB state verified against BATON 064 — all counts matched.
Three deferred flags reviewed and dispositioned. No scripts written, no DB modified.

---

## Deferred Flag Decisions

| Flag | Previous Status | Decision | Rationale |
|------|----------------|----------|-----------|
| DEFERRED-PROGRAM-TREND | UNBLOCKED | **SCRAPPED** ✅ | Missing pre-2024 handbooks; only 2024 + 2025 available. Incomplete resident cohort data. 8-year trend series not reconstructable. |
| DEFERRED-PGY-BENCHMARKS | UNBLOCKED | **SHELVED** 🟡 | Infrastructure already exists (--pgy-level flag, compute_thresholds(), PGY benchmarks in reference JSON). Gap is report surface area only. Shelved until resident reports are re-run and gap is visible in real output. |
| DEFERRED-QID-XREF-LIBRARY-GAPS | ACTIVE | **PLAN ESTABLISHED** — work deferred to next session | Full analysis completed this session (see below). |

---

## QID-XREF-LIBRARY-GAPS Analysis (completed this session)

### Current State
- 52 QIDs with zero xref entries (19 from 2024, 33 from 2025)
- 246 `question_ref_pairs` rows with `clean_ref IS NULL`
- 207 unique unmatched citations after removing Silbernagel extraction artifact
- 229 affected QID links

### Silbernagel Artifact (confirmed)
`Silbernagel KG, Hanlon S, Sprague A. J Athl Train. 2020;55(5):438-447.` was incorrectly assigned to 15 unrelated questions by the 2025 critique PDF parser. None of those questions are about Achilles tendinopathy. Artifact in gap file — not a real gap.

### Gap Breakdown (by journal)
| Journal | Count | Acquirability |
|---------|-------|---------------|
| Am Fam Physician | 85 | High (open access) |
| Other | 59 | Mixed |
| Textbook chapters | 14 | Irrecoverable |
| JAMA | 12 | Moderate (some PMC) |
| NEJM | 8 | Low (paywalled) |
| Obstet Gynecol | 4 | Mixed |
| Pediatrics | 4 | Mixed |
| Lancet | 3 | Low (paywalled) |
| Diabetes Care | 2 | Moderate |
| Circulation | 2 | Moderate |

### Key Clarifications Made
- **Citation string** = raw text in `question_ref_pairs.ref_raw` — known, but unresolvable to an ART-ID
- **Article record** = structured row in `articles` with ART-ID — doesn't exist for these 249
- **PDF** = physical file in citation_files/ — doesn't exist for these 249
- The 249 are missing BOTH article records AND PDFs
- ~973 PDFs actually on disk (not 1,958 — `citation_only=0` does not mean PDF exists)
- `qid_art_xref` is complete and faithful from BATON 058; gap is upstream acquisition only

### Planned PDF Run (next session)
**Phase 1 — 249 missing citations (new records + PDFs)**
- New script needed: `acquire_missing_citations.py`
- Reads `question_ref_pairs WHERE clean_ref IS NULL`
- Searches Exa per citation, classifies URL, downloads PDF to staging
- Inserts article records (starting ART-2000) + xref links
- AFP articles (~85) expected highest hit rate via `aafp.org/pubs/afp`
- Textbook chapters (~14) → add as citation_only records, no PDF

**Phase 2 — Existing records without PDFs (~1,025 records)**
- Infrastructure already exists in M1
- User runs on Windows terminal:
  ```
  python 01_module.1_warehouse/scripts/maintain/exa_pdf_finder.py --dry-run
  python 01_module.1_warehouse/scripts/maintain/exa_pdf_finder.py
  python 01_module.1_warehouse/scripts/maintain/exa_pdf_downloader.py --dry-run
  python 01_module.1_warehouse/scripts/maintain/exa_pdf_downloader.py
  python 01_module.1_warehouse/scripts/maintain/pmc_oa_downloader.py
  python 01_module.1_warehouse/scripts/maintain/unpaywall_scanner.py
  ```

---

## DB State (Unchanged from BATON 064)

| Table | Count |
|-------|-------|
| articles | 1,998 |
| questions (ITE) | 1,639 |
| aafp_questions | 1,221 |
| qid_art_xref | 2,485 |
| aafp_qid_art_xref | 864 |
| article_icd10 | 4,959 |
| question_icd10 | 5,774 |
| aafp_question_icd10 | 4,753 |
| clinical_pathways | 4,959 |
| article_currency | 1,998 |

---

## Files Modified / Created

None. Null session.

---

## Deferred Flags Carried Forward

| Flag | Status |
|------|--------|
| DEFERRED-QID-XREF-LIBRARY-GAPS | **ACTIVE** — PDF run planned for next session |
| DEFERRED-PGY-BENCHMARKS | **SHELVED** — revisit after resident reports re-run |
| DEFERRED-PROGRAM-TREND | **SCRAPPED** ✅ |

---

## Next Steps

1. **PDF Run — Phase 1**: Write `acquire_missing_citations.py`; run against 249 unmatched citations; add article records + xref links
2. **PDF Run — Phase 2**: Run existing M1 pipeline (`exa_pdf_finder` → `exa_pdf_downloader` → `pmc_oa_downloader` → `unpaywall_scanner`)
3. **Re-run all 7 resident analyses** (BATON 063/064 holdover — git pull → batch run on Windows)

---

**End null_BATON_archive_065**
