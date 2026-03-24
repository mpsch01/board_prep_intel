# BATON — Codon Migration Session 3: Rename Executed

**Date:** March 14, 2026 (session 3)
**Previous BATON:** `BATON_codon_migration_20260314b.md`
**Status:** 141 PDFs renamed to codon format. Low-confidence matches deferred. Ready for Steps 5–8.

---

## What Was Done This Session

### Step 4 Executed: `rename_to_codon.py --execute` — COMPLETE
141 PDFs in `01_pdf_guideline_library/` renamed from topic-based names to codon format (`Author_Year#@#ART-XXXX@#@.pdf`). Zero failures. Rollback log written.

### Low-Confidence Match Audit — 35 Files Deferred
Before executing, we audited all 35 low-confidence matches (1-QID vote, thin evidence). Findings:

- Almost all were QID-bridge artifacts — the PDF and matched article shared an ITE question but are different publications
- Examples: 5 different IDSA PDFs all collapsed onto ART-1053 "Acute hand infections"; CRC screening → lung cancer screening; allergic rhinitis → pneumonia
- An interactive HTML triage tool was built (`low_confidence_triage.html`) — Mikey triaged all 35, confirmed only 3–4 as correct, but the export wasn't saved
- **Decision: omit all 35 from this rename cycle.** `rename_to_codon.py` updated to skip `confidence == "low"` entries. They remain with original filenames for future triage.

### Script Modification: `rename_to_codon.py`
Added low-confidence exclusion filter in `build_rename_plan()`:
- Line 80: `and r.get("confidence") != "low"` added to active_matched filter
- Lines 144–151: Low-confidence files added to skipped list with reason "Low confidence — deferred for triage"

---

## Final Numbers

| Category | Count |
|---|---|
| Total PDFs in library | 260 |
| Codon-renamed (this session) | 141 |
| Omitted (non-ITE supplementary) | 41 |
| Duplicates (skipped by dedup logic) | 43 |
| Low-confidence deferred | 35 |
| Rename failures | 0 |
| Unique ART-IDs in codon names | 141 |

---

## Current State of `01_pdf_guideline_library/`

- **141 files** with codon names: `Author_Year#@#ART-XXXX@#@.pdf`
- **119 files** with original names (41 omitted + 43 duplicates + 35 low-confidence)
- All codon names validated: correct `#@#ART-NNNN@#@` pattern, 141 unique ART-IDs, zero malformed

---

## Files Modified This Session

| File | Location | Change |
|---|---|---|
| `rename_to_codon.py` | `02_ite_intelligence/scripts/` | Added low-confidence exclusion filter |
| `rename_log.json` | `02_ite_intelligence/logs/` | Updated: mode=execute, 141 renamed, 0 errors |
| `low_confidence_triage.html` | `claude_knowledge/` | Interactive triage tool for the 35 deferred files |
| 141 PDFs | `01_pdf_guideline_library/` | Renamed to codon format |

---

## Deferred: Low-Confidence Triage (35 files)

These files need proper manual review before codon rename. The triage tool (`low_confidence_triage.html`) is ready — Mikey needs to re-do the triage and export the decisions JSON. The rename script can then incorporate those decisions.

Key groups among the 35:
- **AJKD_ series (5):** CKD subspecialty guidelines — matched to wrong articles via shared QIDs
- **IDSA_ series (9):** Infectious disease guidelines — 5 collapsed onto "Acute hand infections"
- **acg_ series (6):** GI guidelines — CRC screening matched to lung cancer screening, etc.
- **afp_ series (3):** AFP articles — allergic rhinitis to pneumonia, etc.
- **Others (12):** Mix of COMPASS, JACC afib, peds ADHD, USPSTF, WHO

Some may have correct matches in the DB under different articles; some are likely supplementary guidelines not represented in the DB at all.

---

## Immediate Next Steps (Steps 5–8)

### Step 5: Flatten and Clean
- Delete all files in `03_enriched JSON/` and `02_docx_guideline_library/`
- Delete `crosswalk_index.json`
- Archive 59 duplicate PDFs (decide: `07_archive/` or leave in place?)
- Archive `rename_log.json`

### Step 6: Pipeline Trim
- Simplify `ite_intelligence_enricher.py`: codon-only Strategy 0 as primary, log fallbacks
- Same for `ite_intelligence_enricher_batch.py`
- Rewrite `build_crosswalk_index.py` to parse ART-IDs from filenames (~50 lines)
- Fix FLAGS 5 + 6 while touching the enricher

### Step 7: Full Re-Process
Run complete pipeline on clean, codon-named library:
```
PDF (codon) → extract → synthesize → enrich → DOCX → save JSON
```

### Step 8: Verify Integrity
- Confirm 141 codon-named PDFs all match Strategy 0
- Confirm crosswalk shows full coverage for codon files
- DB tagging data intact (spot-check high-priority articles)

---

## Open Flags

### FLAG 1 — ITE Enrichment Quality Dimension
**Status: OPEN** — Add 6th dimension to calibrate.py. Deferred until post-migration.

### FLAG 5 — tier_rationale still generic boilerplate
**Status: OPEN** — Fix during pipeline trim (Step 6).

### FLAG 6 — enrichment_confidence uncalibrated
**Status: OPEN** — Fix during pipeline trim. Compute from match_method + citation_count.

### FLAG 7 — acg_IBD persistent no_match
**Status: RESOLVED THIS SESSION** — `acg_IBD.pdf` was renamed to `Farraye_Melmed_2017#@#ART-0398@#@.pdf` (high confidence match).

### FLAG 12 — Codon Rename Migration
**Status: PHASE 1 COMPLETE** — 141/260 PDFs renamed. 35 low-confidence deferred. Steps 5–8 remain.

### FLAG 13 — Intelligence 2.0 Layers
**Status: DESIGNED, WAITING ON MIGRATION COMPLETE** — Four layers scoped. Build starts after Step 8.

### FLAG 14 — Low-Confidence Triage (NEW)
**Status: OPEN** — 35 files need re-triage. HTML tool exists. Mikey needs to re-export decisions.

---

## Rollback

If anything goes wrong:
```
cd abfm_prep/02_ite_intelligence
python scripts/rename_to_codon.py --rollback
```
This reverses all 141 renames using `logs/rename_log.json`.

---

## DB State (Unchanged)

| Table | Rows |
|---|---|
| `articles` | 1,397 |
| `questions` | 1,189 |
| `question_ref_pairs` | 2,069 |
| `qid_art_xref` | 1,818 |
| `article_vec` | 1,397 |
| `question_vec` | 1,189 |

Database was NOT modified this session.

---

## Critical File Locations

| File | Path |
|---|---|
| This BATON | claude_knowledge/BATON_codon_migration_20260314c.md |
| Previous BATON | claude_knowledge/BATON_codon_migration_20260314b.md |
| Architecture Blueprint | claude_knowledge/ITE_Intelligence_2.0_Architecture.md |
| Rename script | abfm_prep/02_ite_intelligence/scripts/rename_to_codon.py |
| Rename log (execute) | abfm_prep/02_ite_intelligence/logs/rename_log.json |
| Staging report | abfm_prep/02_ite_intelligence/logs/match_staging_report.json |
| Manual overrides | abfm_prep/02_ite_intelligence/manual_overrides.json |
| Triage tool | claude_knowledge/low_confidence_triage.html |
| ITE Intelligence DB | abfm_prep/02_ite_intelligence/db/ite_intelligence.db |
| PDF library | clinical_guidelines/01_pdf_guideline_library/ |

---

*Supersedes: BATON_codon_migration_20260314b.md (Steps 1–4 built). This session executed the rename.*
