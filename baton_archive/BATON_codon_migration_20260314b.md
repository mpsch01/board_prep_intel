# BATON — Codon Migration Session 2

**Date:** March 14, 2026 (session 2)
**Previous BATON:** `BATON_codon_migration_20260314.md`
**Status:** Steps 1–4 built and tested. Ready for `--execute`.

---

## What Was Done This Session

### Step 1: `build_match_staging.py` — COMPLETE
Built and iterated the match staging script. Three matching strategies in cascade:

1. **QID reverse lookup** — looks up enriched JSON's linked QIDs in `qid_art_xref`, votes on the most-referenced article. This was the breakthrough: resolved 201/201 Tier 1 files including the 118 that were originally matched via vector similarity.
2. **Author+year from citation metadata** — parses author surname and year from `citation_display` field (handles null `publication_year`).
3. **Title keyword matching** — fallback for filename-only files.

Metadata cross-check (DB author/year vs enriched JSON citation) separates high-confidence matches (the PDF IS the article) from low-confidence matches (supplementary guidelines that share QIDs).

### Steps 2–3: Manual Review — COMPLETE
Mikey reviewed all unmatched files interactively. Results stored in `manual_overrides.json`:

- **14 manual matches** confirmed (including `afp_decision_making_capacity.pdf`, `Gaitonde_Moore_2019.pdf`, `Higdon_Atkinson_2018.pdf`, `afp_incidentalomas.pdf`, `uspstf_lung_cancer_screening.pdf`, `jacc_chest_pain.pdf`, etc.)
- **2 duplicate PDF pairs** identified (`afp_influenza_dx_tx.pdf` = `Gaitonde_Moore_2019.pdf`, `afp_oncologic_emergencies.pdf` = `Higdon_Atkinson_2018.pdf`)
- **41 files omitted** from migration (supplementary guidelines: neuro_, tox_, rheum_, APA_, vaccines, algorithms, ACOG, periop, etc.)
- **ART-0540** identified as duplicate DB row of ART-0539 (both Gulati/Levy 2021 chest pain)

### Step 4: `rename_to_codon.py` — BUILT AND DRY-RUN TESTED
Script built with:
- `--dry-run` default (shows plan, touches nothing)
- `--execute` flag to actually rename
- `--rollback` flag to undo using `rename_log.json`
- Automatic duplicate resolution (picks canonical PDF per ART-ID)
- Collision detection, missing source check, target existence check

**Dry-run result:** 160 renames planned, 0 validation errors, 0 collisions.

---

## Final Numbers

| Category | Count |
|---|---|
| Total PDFs in library | 260 |
| Omitted (non-ITE) | 41 |
| Active (migration) | 219 |
| Matched | 219 (100%) |
| Manual overrides | 14 |
| Unique articles | 160 |
| Duplicate PDFs (auto-resolved) | 59 |
| **Ready for rename** | **160 files → 160 codon filenames** |

---

## Files Created/Modified This Session

| File | Location | Purpose |
|---|---|---|
| `build_match_staging.py` | `02_ite_intelligence/scripts/` | Step 1: match PDFs → articles |
| `rename_to_codon.py` | `02_ite_intelligence/scripts/` | Step 4: rename PDFs to codon format |
| `manual_overrides.json` | `02_ite_intelligence/` | Human-reviewed matches + omit list |
| `match_staging_report.json` | `02_ite_intelligence/logs/` | Machine-readable staging report |
| `match_staging_report.txt` | `02_ite_intelligence/logs/` | Human-readable staging report |
| `rename_log.json` | `02_ite_intelligence/logs/` | Dry-run rename log (will be overwritten on execute) |

---

## Immediate Next Action

**Execute the rename:**
```
cd abfm_prep/02_ite_intelligence
python scripts/rename_to_codon.py --execute
```

This renames 160 PDFs in `01_pdf_guideline_library/` to codon format. The 59 duplicate PDFs stay with their original names (they can be archived or deleted later). The 41 omitted supplementary files are untouched.

**If something goes wrong:**
```
python scripts/rename_to_codon.py --rollback
```

---

## After Rename (Steps 5–8)

### Step 5: Flatten and Clean
- Delete all files in `03_enriched JSON/`, `04_DOCX_summaries/`, `05_ite_ref_json/`
- Delete `crosswalk_index.json`
- Archive `rename_log.json` and 59 duplicate PDFs

### Step 6: Trim the Pipeline
- Simplify `ite_intelligence_enricher.py`: replace 5-strategy `lookup_article()` with codon-only Strategy 0
- Same for `ite_intelligence_enricher_batch.py`
- Rewrite `build_crosswalk_index.py` to parse ART-IDs from filenames (~50 lines)

### Step 7: Full Re-Process
Run the complete pipeline on the clean library:
```
PDF (codon-named) → extract → synthesize → enrich → DOCX → save JSON
```

### Step 8: Verify Integrity
- Confirm 160 PDFs have codon names
- Confirm enricher matched 160/160 (Strategy 0, zero fallbacks)
- Confirm crosswalk shows 160/160 full coverage

---

## Then: Intelligence 2.0 Layers

| Phase | What | Status |
|---|---|---|
| Phase 0 | Codon Migration | Steps 1-4 done, ready for execute |
| Phase 1 | Layer 1: ICD-10 tagging | Waiting on migration |
| Phase 2 | Layer 4a: Topic trends | Can build from existing DB data |
| Phase 3 | Layer 2: PubMed currency | Waiting on migration |
| Phase 4 | Layer 4b: Alert system | Waiting on Layer 2 + trends |
| Phase 5 | Layer 3: Clinical pathways | Waiting on Layer 1 validated |

---

## Known Issues / Decisions Pending

1. **59 duplicate PDFs** — after rename, decide: archive to `07_archive/`? Delete? Leave in place?
2. **41 omitted supplementary PDFs** — stay in library with original names. Future decision: create new ART-IDs for them, or move to `alt_refs/`?
3. **ART-0540** — dead DB row (duplicate of ART-0539). Clean up during Step 6 or leave as-is.
4. **34 duplicate ART-ID assignments in staging report** — these are supplementary guidelines that share QIDs with core articles. The rename script resolves this by picking canonicals, but the underlying QID overlap means the enricher will still match these supplementary PDFs to the wrong article if they're ever re-processed. Not a problem if they stay omitted.

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

Database was NOT modified this session. All changes are to files and scripts only.
