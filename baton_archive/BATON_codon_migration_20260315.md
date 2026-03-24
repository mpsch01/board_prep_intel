# BATON — Codon Migration Session 4: MIGRATION COMPLETE

**Date:** March 15, 2026
**Previous BATON:** `BATON_codon_migration_20260314c.md`
**Status:** FLAG 12 CLOSED. Full codon migration complete. v4 pipeline operational.

---

## What Was Done This Session

### Step 5: Flatten Derivatives — COMPLETE
Deleted 551 files to clear the deck for re-processing:
- 245 DOCXs from `02_docx_guideline_library/`
- 228 enriched JSONs from `03_enriched JSON/`
- 34 files from `04_need_extraction/`
- 1 crosswalk_index.json
- 43 duplicate PDFs from `01_pdf_guideline_library/`

Library reduced from 260 → 217 PDFs (141 codon + 76 original).

### Step 6: Pipeline Trim — COMPLETE
Three scripts rewritten to v4 (codon-first, 2-strategy lookup only):

| Script | Before | After | Key Changes |
|---|---|---|---|
| `ite_intelligence_enricher.py` | v3, 652 lines, 5 strategies + vector search | v4, 466 lines, codon + clean_ref | Removed sqlite_vec, openai, Strategies 2-5, `_TITLE_STOPWORDS`, `_strip_apostrophes()`, `_title_keywords()`, `_word_freq_in_db()`, `_get_query_embedding()` |
| `ite_intelligence_enricher_batch.py` | No Strategy 0, hardcoded Windows path | v4, Strategy 0 added, relative paths | Removed Strategies 2-4, fixed `C:\Users\mpsch\...` path, updated confidence + prompt |
| `build_crosswalk_index.py` | v1.3, 331 lines, 3-pass matching | v2.0, 135 lines, codon-only parse | Complete rewrite: parse ART-ID from filename → DB lookup → done |

Additionally:
- `convert_pdfs_to_json.py` v1.2 — archived extraction script updated: `_extracted.json` suffix, relative paths, flat output to `03_enriched JSON/`

### FLAGS Resolved in Step 6
- **FLAG 5** — tier_rationale prompt upgraded: now requires specific clinical concepts, citation count, year span, and tier designation. No more generic boilerplate.
- **FLAG 6** — confidence computation: `codon_filename → high`, `clean_ref → high`, `else → low`. No more ambiguous medium tiers from fuzzy matching.

### Step 7: Full Re-Process — COMPLETE
Ran complete v4 pipeline on Windows:
```
convert_pdfs_to_json.py → 217/217 PDFs extracted
enricher_batch.py --submit → 141 requests submitted to Anthropic Batch API
enricher_batch.py --write → 141/141 enriched, 0 errors
build_crosswalk_index.py → 141 codon matched, 76 unmatched
```

**Bug fixed during submit:** Duplicate `custom_id` error — long similar slugified filenames collided after 64-char truncation. Fixed by appending index counter to base_id.

### Step 8: Verify Integrity — COMPLETE

| Check | Result |
|---|---|
| Extracted JSONs | 217/217 |
| Enriched with ite_intelligence | 141/141 |
| Match method = codon_filename | 141/141 (100%) |
| Has linked_qids | 141/141 |
| Confidence = high | 141/141 (100%) |
| Non-enriched (no DB match) | 76 (expected) |
| Crosswalk codon matched | 141/217 |
| Tier breakdown | Core: 108, Must-Read: 18, Supplementary: 15 |
| Total linked citations | 359 (avg 2.5/article) |
| Spot-check content quality | tier_rationale references specific clinical concepts |

---

## Pipeline v4 — Operational

Run from `C:\Users\mpsch\Desktop\claude_knowledge`:

```powershell
# Step 1: Extract (no API, pdfplumber)
python abfm_prep\02_ite_intelligence\scripts\convert_pdfs_to_json.py --pdf_dir "clinical_guidelines\01_pdf_guideline_library"

# Step 2: Enrich (Batch API — 50% cheaper)
python abfm_prep\02_ite_intelligence\scripts\ite_intelligence_enricher_batch.py --submit --dir "clinical_guidelines\03_enriched JSON"
python abfm_prep\02_ite_intelligence\scripts\ite_intelligence_enricher_batch.py --poll
python abfm_prep\02_ite_intelligence\scripts\ite_intelligence_enricher_batch.py --write

# Step 3: Crosswalk
python abfm_prep\02_ite_intelligence\scripts\build_crosswalk_index.py
```

DB lookup: Strategy 0 (codon parse `#@#ART-XXXX@#@` from filename) → Strategy 1 (clean_ref exact match) → no_match.

---

## Current State of `01_pdf_guideline_library/`

- **141 files** with codon names: `Author_Year#@#ART-XXXX@#@.pdf`
- **76 files** with original names (35 low-confidence deferred + 41 supplementary/non-ITE)

---

## Open Flags

### FLAG 1 — ITE Enrichment Quality Dimension
**Status: OPEN** — Add 6th dimension to calibrate.py. Deferred until post-migration feature work.

### FLAG 5 — tier_rationale still generic boilerplate
**Status: RESOLVED (2026-03-15)** — Prompt now requires specific clinical concepts, citation count, year span, and tier.

### FLAG 6 — enrichment_confidence uncalibrated
**Status: RESOLVED (2026-03-15)** — codon_filename → high, clean_ref → high, else → low.

### FLAG 7 — acg_IBD persistent no_match
**Status: RESOLVED (2026-03-14)** — Renamed to `Farraye_Melmed_2017#@#ART-0398@#@.pdf`.

### FLAG 12 — Codon Rename Migration
**Status: COMPLETE (2026-03-15)** — All 8 steps finished. v4 pipeline operational. 141/217 enriched, all high confidence.

### FLAG 13 — Intelligence 2.0 Layers
**Status: DESIGNED, READY TO BUILD** — Four layers scoped (ICD-10, PubMed currency, clinical pathways, predictive trends). Architecture blueprint in `BATON_intelligence_2.0_20260314.md`. Migration prerequisite satisfied.

### FLAG 14 — Low-Confidence Triage
**Status: OPEN** — 35 files with original names need re-triage. HTML tool exists (`low_confidence_triage.html`). Mikey needs to re-do triage and export decisions JSON.

---

## What's Next

| Priority | Task | Notes |
|---|---|---|
| 1 | FLAG 14: Re-triage 35 low-confidence files | Use existing HTML tool, export JSON, run rename |
| 2 | DOCX generation | Re-run DOCX pipeline to repopulate `02_docx_guideline_library/` |
| 3 | FLAG 13: Intelligence 2.0 | Build the 4 enrichment layers (ICD-10, PubMed, pathways, trends) |
| 4 | FLAG 1: Calibration quality dimension | Add ITE enrichment scoring to calibrate.py |

---

## Files Modified This Session

| File | Location | Change |
|---|---|---|
| `ite_intelligence_enricher.py` | `02_ite_intelligence/scripts/` | v3 → v4: codon-first, Strategies 2-5 removed |
| `ite_intelligence_enricher_batch.py` | `02_ite_intelligence/scripts/` | Strategy 0 added, Strategies 2-4 removed, path fixed, custom_id uniqueness fix |
| `build_crosswalk_index.py` | `02_ite_intelligence/scripts/` | v1.3 → v2.0: complete rewrite, codon-only |
| `convert_pdfs_to_json.py` | `02_ite_intelligence/scripts/` | v1.1 → v1.2: _extracted.json suffix, relative paths, flat output |
| `crosswalk_index.json` | `02_ite_intelligence/` | Rebuilt: 217 entries, 141 codon matched |
| `crosswalk_report.txt` | `02_ite_intelligence/` | Rebuilt: v2.0 coverage report |
| 217 `*_extracted.json` files | `clinical_guidelines/03_enriched JSON/` | New: full pipeline output |
| `manifest.json` | `clinical_guidelines/03_enriched JSON/` | New: extraction manifest |
| `_index.md` | `claude_knowledge/` | Updated: migration complete, all steps logged |
| `README.json` | `claude_knowledge/` | Updated: active_migration status, completed steps |
| `README.json` | `clinical_guidelines/` | Updated: post-migration file counts, pipeline docs |
| This BATON | `claude_knowledge/` | New: session 4 handoff |

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
| This BATON | claude_knowledge/BATON_codon_migration_20260315.md |
| Previous BATON | claude_knowledge/BATON_codon_migration_20260314c.md |
| Architecture Blueprint | claude_knowledge/BATON_intelligence_2.0_20260314.md |
| Enricher v4 | abfm_prep/02_ite_intelligence/scripts/ite_intelligence_enricher.py |
| Batch enricher v4 | abfm_prep/02_ite_intelligence/scripts/ite_intelligence_enricher_batch.py |
| Crosswalk builder v2.0 | abfm_prep/02_ite_intelligence/scripts/build_crosswalk_index.py |
| Extraction script v1.2 | abfm_prep/02_ite_intelligence/scripts/convert_pdfs_to_json.py |
| Crosswalk index | abfm_prep/02_ite_intelligence/crosswalk_index.json |
| ITE Intelligence DB | abfm_prep/02_ite_intelligence/db/ite_intelligence.db |
| PDF library | clinical_guidelines/01_pdf_guideline_library/ |
| Enriched JSONs | clinical_guidelines/03_enriched JSON/ |
| Triage tool | claude_knowledge/low_confidence_triage.html |

---

*Supersedes: BATON_codon_migration_20260314c.md (Steps 1–4). This session completed Steps 5–8 and closed FLAG 12.*
