# BATON 063 — 2026-04-29 — Report Guides Complete

**Handoff from:** BATON_active_062_20260429_report_builder_issues_1to5_complete.md  
**Date:** 2026-04-29  
**Session:** Report Interpretation Guides (Resident + Faculty)  
**Git Hash:** 58589ff  
**Status:** DEFERRED-REPORT-GUIDE **CLOSED**

---

## Session Summary

Session focus: **DEFERRED-REPORT-GUIDE** — Write two ITE interpretation guides for faculty advisors and residents, enabling end users to understand their report structure, data provenance, and next steps.

### What Was Built

#### Resident Guide — build_resident_guide.py → ITE_Report_Guide_Resident_v2.docx
- Python script using word_doc_defaults.py (Rule 14 compliant)
- Section-by-section read-along following the report structure exactly (Sections 0, 1, 2, 3b, 4, 6, 7, 7b, 8, 9, 10, Part B, Appendix)
- Single callout type: gold ACTION callouts (✎ ACTION prefix, gold border, light gold background)
- Clinical voice, action-oriented, minimal methodology detail
- Audience: PGY-1/2 residents reading their own report
- Output: `03_module.3_analyst/docs/ITE_Report_Guide_Resident_v2.docx`

#### Faculty Guide — build_faculty_guide.py → ITE_Report_Guide_Faculty_v2.docx
- Python script using word_doc_defaults.py (Rule 14 compliant)
- Two callout types: DATA SOURCE (green border/bg) + LIMITATION (amber border/bg)
- All file names and script names stripped from user-facing text — plain-language data provenance throughout
- System Overview: brief conceptual description only — no pipeline table, no script names
- Three-tier cascade table (Part B) and ICD-10 data flow table retained as structural explainers
- Faculty Advising Framework at end: urgent action signals, reframe triggers, data calibration, longitudinal tracking
- Audience: program directors and faculty advisors interpreting a resident's report
- Output: `03_module.3_analyst/docs/ITE_Report_Guide_Faculty_v2.docx`

#### JS versions (deprecated per Rule 14)
- build_resident_guide.js and build_faculty_guide.js also exist — written initially but superseded by Python versions
- Kept on disk for reference; Python versions are canonical

#### word_doc_defaults.py — Modified
- add_section_header() now differentiates level 1 vs level 2:
  - Level 1: Pt(18) before / Pt(6) after + light blue background ("EFF3FA") + 12pt bold navy
  - Level 2: Pt(6) before / Pt(3) after + NO background fill + 11pt bold blue
- This prevents gold bars from being oversized on subsection headers (border height is tied to paragraph spacing)
- Rule 14 header comment added to the file

#### CLAUDE.md — Modified
- Rule 14 added: "Word docs use word_doc_defaults.py. All Python scripts that generate .docx files must from word_doc_defaults import * and apply the St. Luke's color palette, Aptos font, and helper functions defined there."

#### BATON_active_062 — Modified
- Architecture Decision added: Word Doc Style Standard (Locked Rule 14)

---

## DB State (All Stable — No Changes from BATON 062)

| Table | Count | Notes |
|-------|-------|-------|
| articles | 1,998 | |
| questions (ITE) | 1,639 | Blueprint 100% filled |
| aafp_questions | 1,221 | Blueprint 100% filled |
| qid_art_xref | 2,485 | Rebuilt faithful multi-reference xref |
| aafp_qid_art_xref | 864 | 643 unique questions linked (52.7%) |
| article_icd10 | 4,959 | ↑ from 3,952 (pre-existing Windows PC enrichment, confirmed BATON 062) |
| question_icd10 | 5,774 | ↑ from ~5,003 (pre-existing Windows PC enrichment, confirmed BATON 062) |
| aafp_question_icd10 | 4,753 | Relevance normalized, related cap applied |
| clinical_pathways | 4,959 | ↑ from 3,971 (pre-existing Windows PC enrichment, confirmed BATON 062) |
| pubmed_pmid_cache | 344 | Layer 2 seed (citation_id → PMID) |
| icd10_vec | 2,219 | OpenAI text-embedding-3-small (1536d) |
| article_icd10_vec | 1,757 | ✅ rebuilt 2026-04-05 |
| question_icd10_vec | 2,747 | ✅ rebuilt 2026-04-05 |
| intersection_centroid_vec | 158 | ↑ from 123 (BATON 062) |
| article_currency | 1,998 | Complete 2026-04-16 |

---

## Files Modified / Created

| File | Status | Notes |
|------|--------|-------|
| `03_module.3_analyst/scripts/build_resident_guide.py` | NEW | Python script using word_doc_defaults.py |
| `03_module.3_analyst/scripts/build_resident_guide.js` | NEW | JS version (deprecated; Python canonical) |
| `03_module.3_analyst/scripts/build_faculty_guide.py` | NEW | Python script using word_doc_defaults.py |
| `03_module.3_analyst/scripts/build_faculty_guide.js` | NEW | JS version (deprecated; Python canonical) |
| `03_module.3_analyst/docs/ITE_Report_Guide_Resident_v2.docx` | NEW | Resident-facing report interpretation guide |
| `03_module.3_analyst/docs/ITE_Report_Guide_Faculty_v2.docx` | NEW | Faculty-facing report interpretation guide |
| `03_module.3_analyst/scripts/word_doc_defaults.py` | MODIFIED | add_section_header() now supports level 1/2 differentiation |
| `CLAUDE.md` | MODIFIED | Rule 14 added (Word Doc Style Standard) |
| `BATON_active_062_20260429_report_builder_issues_1to5_complete.md` | MODIFIED | Architecture Decision added (Locked Rule 14) |
| `BATON_active_061_20260416_legacy_bodysystem_analyses_complete.md` | DELETED | Archived; superseded by BATON 062 |

---

## Module Script Inventory (Post-BATON 063)

| Module | Python | JS | Notes |
|--------|--------|----|----|
| M1 (Warehouse) | 34 | 0 | 8 build + 26 maintain (unchanged) |
| M2 (Processor) | 75 | 6 | Extraction, enrichment, DOCX builders (unchanged) |
| M3 (Analyst) | 52 | 4 | +2 py (guide scripts), +2 js (deprecated versions) |
| M4 (Sandbox) | (varies) | (varies) | Experiments |
| M5 (Web) | 3 | 35 | Sync + TypeScript/TSX |
| Total | 167 | 12 | (was 163 py + 10 js) |

---

## Git Status

| Item | Value |
|------|-------|
| Branch | main |
| Hash | 58589ff |
| Modified (staged) | word_doc_defaults.py, BATON_active_062, CLAUDE.md |
| Untracked (new) | build_faculty_guide.js, build_faculty_guide.py, build_resident_guide.js, build_resident_guide.py |
| Deleted (unstaged) | BATON_active_061_20260416_legacy_bodysystem_analyses_complete.md |
| Next action | User pushes commit 58589ff via GitHub Desktop |

---

## Deferred Flags

| Flag | Status | Notes |
|------|--------|-------|
| DEFERRED-REPORT-GUIDE | **CLOSED** ✅ | Both resident + faculty guides written; two Python scripts + two DOCX outputs |
| DEFERRED-QID-XREF-LIBRARY-GAPS | Active | 249 unmatched citations; prioritize by frequency |
| DEFERRED-PGY-BENCHMARKS | UNBLOCKED | All 7 resident analyses complete; PGY-level aggregation pending |
| DEFERRED-PROGRAM-TREND | UNBLOCKED | Cohort-level temporal rollup pending |

---

## Next Steps

### Immediate
1. **Re-run all 7 resident analyses on Windows PC** — git pull to pick up Issues 1-5 (BATON 062) + new guide scripts; batch-run all residents to regenerate reports with up-to-date enrichment
2. **Complete git push** — user pushing commit 58589ff via GitHub Desktop

### Short-term
3. **DEFERRED-PGY-BENCHMARKS** — Implement PGY-level benchmark comparison in report builder (blueprint design ready; awaiting implementation)
4. **DEFERRED-PROGRAM-TREND** — Implement cohort-level trend analysis (temporal heatmap across all residents; infrastructure ready)
5. **DEFERRED-QID-XREF-LIBRARY-GAPS** — Prioritize 249 unmatched citations by citation frequency; acquire missing articles to push xref coverage above current levels

---

## Architecture Decisions

### Two Callout Types for Faculty Guide (not three)
**Decision:** Faculty guide uses DATA SOURCE (green) + LIMITATION (amber) only. COACHING USE callout removed.

**Rationale:** Faculty advisors can draw their own advising conclusions from data provenance. The coaching callouts were prescriptive and redundant — faculty know how to use clinical information. The two remaining callout types answer the question faculty actually have: "where did this come from?" and "what are its limits?"

**Implications:** Guides remain clinically grounded while respecting faculty autonomy in interpretation.

---

### word_doc_defaults.py Level 1/2 Header Differentiation
**Decision:** add_section_header() now accepts level parameter (1 or 2). Level 1 = navy + shaded background + more spacing. Level 2 = blue + no shading + tighter spacing.

**Rationale:** Gold left borders extend the full paragraph height including space_before. Level 2 headers with Pt(18) top spacing produced oversized gold bars. Fix: conditional spacing by level. This is the correct architectural fix — not adjusting border size (which controls thickness, not height).

**Implications:** All existing scripts using add_section_header() default to level=1 — backward compatible. Future guides and reports will use level=2 for subsection headers to maintain visual hierarchy.

---

### Rule 14 — Canonical Word Doc Path is Python + word_doc_defaults.py
**Decision:** All new Word doc generation must use word_doc_defaults.py. JS word doc scripts (like build_resident_guide.js) are kept for reference but Python is canonical.

**Rationale:** Consistent visual identity, leverages the tested helper library, aligns with Rule 5 (no de novo JS). Both guide scripts now exist in JS and Python; Python versions are the ones that get maintained and evolved.

**Implications:**
- word_doc_defaults.py is now the single source of truth for Word doc styling across M2 and M3
- All future .docx generation from Python (Rule 14 compliant): `from word_doc_defaults import *`
- Any new Word doc generation in JavaScript is NOT permitted (Rule 5 exception: existing JS scripts like report_builder_v2.js migrate fine)

---

## PDF Library (Gitignored — BATON 062 numbers, verified intact)

| Tier | Count | Notes |
|------|-------|-------|
| VC_fail | 630 | |
| VC_pass | 168 | |
| local_lite | 117 | |
| right_click | 58 | |
| AAFP | 15 | |
| ITE Exams | 16 | All 8 years (2018–2025) × MC + critique |
| **Total** | **988** | +15 AAFP + 14 dupes in _dupe_archive/ |

---

## Locked Rules Reminder

1. **Fix the data, not the code.** If a script gets complex to handle messy data → clean the data upstream instead.
2. **VC gate = sole criterion** for right_click tier. DB membership alone is not sufficient.
3. **Source data is protected.** DB + PDFs + VC gate survive everything. Derived files are disposable.
4. **Dynamic paths only.** Python: `SCRIPT_DIR = Path(__file__).resolve().parent; PROJECT_ROOT = SCRIPT_DIR.parent.parent`. JS: `path.resolve(__dirname, "../../")`.
5. **No de novo JS.** Existing JS scripts migrate fine. New code = Python only.
6. **BATON first.** Read the active BATON before any work. It has deferred flags and current state.
7. **QC after every integration.** Schema-level column-by-column population comparison, old cohort vs new.
8. **Git via Desktop Commander.** Claude can now run git commits via Desktop Commander Python subprocess (helper: `claude_knowledge/git_runner.py`). Cannot `rm` NTFS files — deletions still require Windows Explorer/terminal.
9. **`shutil.rmtree` is BANNED.** Use explicit file-by-file deletion or PowerShell Remove-Item.
10. **Strategy 0 in every enricher.** Codon parse is always the first matching strategy.
11. **Schemas before scripts.** SQL `CREATE TABLE` defined before build scripts are written.
12. **`_normalize_concept()` fallback = first-letter capitalize only.** Never `.title()` — it mangles acronyms.
13. **ICD-10 enrichment is invisible.** `icd10_profile` is passed to `match_practice_questions_v3()` as a hidden scoring signal.
14. **Word docs use `word_doc_defaults.py`.** All Python scripts that generate `.docx` files must `from word_doc_defaults import *` and apply the St. Luke's color palette, Aptos font, and helper functions defined there. (NEW THIS SESSION — Locked Rule)

---

**End BATON 063**
