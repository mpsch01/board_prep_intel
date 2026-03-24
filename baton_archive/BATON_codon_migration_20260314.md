# BATON — Codon Migration: PDF→DB Link Gap Analysis Complete
## Session Handoff Document
**Date:** 2026-03-14
**Phase:** Deep diagnostic of why the enricher can't connect PDFs to DB articles. Root cause identified. Codon rename migration scoped.
**Status:** Analysis complete. No code changes made. Ready for implementation.

---

## THE FINDING

**The codon filename system (`Author_Year#@#ART-XXXX@#@.pdf`) was designed to be the durable link between PDFs and DB article records. All 1,397 DB articles have `codon_filename` populated. Zero of 260 library PDFs use it.**

The pipeline has been compensating with a 5-strategy matching cascade in the enricher, keyword matching in the crosswalk builder, and QID-bridging in the backfill script. Each step rediscovers the PDF→article link independently, with its own blind spots. This is why:
- 25 enriched JSONs couldn't match during the batch enricher run
- 67 crosswalk entries are "partial" (no QIDs, no article link)
- 11 of the highest-priority articles appeared "pending" despite having PDFs in the library

**Root cause: 184 of 260 PDFs (71%) were collected in June 2025** — months before the ITE intelligence pipeline and codon system existed. They use clinician-friendly `{source}_{topic}` naming (e.g., `IDSA_MRSA.pdf`, `peds_febrile_seizures.pdf`). The codon rename was never applied retroactively.

---

## WHAT WAS ANALYZED THIS SESSION

### 1. Database Profile (ite_intelligence.db)
- 3 core tables: articles (1,397), questions (1,189), question_ref_pairs (2,069)
- 2 vector tables: article_vec (1,397), question_vec (1,189) — all populated
- Referential integrity: clean. Zero orphans in any direction.
- `blueprint` only populated for 2024-2025 (67% of questions empty)
- `blueprint_cats` column is dead — contains no useful data
- 281 articles have empty `categories` string
- 30 stub articles (citation_count=0, source_type='stub')

### 2. Priority Scoring
Built a study priority score: `citation_count × unique_exam_years × tier_weight`
Tier weights: Must-Read=3, Core=2, Supplementary=1

**Priority distribution:**
| Tier | Count | Extracted | Pending | % Extracted |
|------|-------|-----------|---------|-------------|
| 21+ (critical) | 17 | 6 | 11 | 35% |
| 9-20 (high) | 17 | 15 | 2 | 88% |
| 4-8 (medium) | 129 | 51 | 78 | 40% |
| 1-3 (low) | 1,204 | 247 | 957 | 20% |

Top article: ART-0590 Higdon/Atkinson 2018, "Oncologic emergencies" — score 54 (6 citations, 3 years, Must-Read).

### 3. PDF Library Naming Conventions
At least 15 distinct prefix conventions discovered:

| Prefix | Source | Count | Example |
|--------|--------|-------|---------|
| afp_ | AFP articles | 23 | afp_COPD_dx_mgmt.pdf |
| aafp_ | AAFP guidelines | 17 | aafp_gout.pdf |
| acg_ | ACG (GI) | 24 | acg_GERD.pdf |
| IDSA_ | IDSA (ID) | 31 | IDSA_MRSA.pdf |
| peds_ | Pediatrics (AAP) | 13 | peds_febrile_seizures.pdf |
| jacc_ | JACC (Cardiology) | 10 | jacc_HTN.pdf |
| uspstf_ | USPSTF | 15 | uspstf_skinCA_screening.pdf |
| neuro_ | Neurology | 11 | neuro_migraine.pdf |
| hep_ | Hepatology | 8 | hep_HCC.pdf |
| rheum_ | Rheumatology | 8 | rheum_RA.pdf |
| AJKD_ | Nephrology | 8 | AJKD_CKD+DM2.pdf |
| APA_ | APA (Psych) | 5 | APA_depression.pdf |
| tox_ | Toxicology | 5 | tox_tylenol.pdf |
| pulm_ | Pulmonology | 7 | pulm_COPD.pdf |
| NN_ | Numbered batch | 20 | 01_Hip_Pain_Adults_Chamberlain_2021 (1).pdf |
| Author_ | Author-year | ~10 | Gentry_Gentry_2017.pdf |

Plus: `acog_`, `aap_`, `ADA_`, `ats_`, `endo_`, `periop_`, `VA_`, and one-offs.

### 4. File Age Analysis
| Group | Count | Origin | Purpose |
|-------|-------|--------|---------|
| Pre-2026 (June 2025) | 184 | Personal clinical library | Topic-named, no pipeline awareness |
| 2026 (March) | 76 | ITE pipeline project | Mix of afp_, NN_, Author_ conventions |

### 5. Enricher Matching Cascade — Why It Fails
The enricher's `lookup_article()` (in `ite_intelligence_enricher.py`) has 5 strategies:

| Strategy | What it does | Why it fails on prefix-named PDFs |
|----------|-------------|-----------------------------------|
| S1: clean_ref | Direct lookup from source block | Only in v1.1+ JSONs — most don't have it |
| S2: Author+Year | Parse `_Author_YYYY` from filename | `afp_COPD_dx_mgmt` has no author, no year |
| S3: Title keywords+Year | 2 specific title words (freq ≤10) + year | Year missing in ~7 JSONs; keywords too common (e.g., "obstructive"=19, "pulmonary"=16) |
| S4: Org patterns+Year | USPSTF/CDC patterns only | AFP, IDSA, ACG, AAP not mapped |
| S5: Vector similarity | Semantic fallback (sqlite-vec) | Requires sqlite-vec + OPENAI_API_KEY at runtime |

### 6. Enriched JSON Status (228 total)
| Category | Count | Notes |
|----------|-------|-------|
| Already have ite_intelligence | 203 | Working correctly |
| Missing publication_year, no ite | 11 | Strategy 3 can't fire without year |
| Has year, no ite, S3 fails | 13 | Keywords too common or no DB match |
| No title at all | 1 | — |

### 7. Auto-Matchable PDFs for Codon Rename
| Category | Count |
|----------|-------|
| Can auto-match to DB article NOW | 115 |
| Unmatched (need extraction or manual) | 145 |
| Of the 145: no enriched JSON yet | ~50 |
| Of the 145: title too generic / no year | ~55 |
| Of the 145: probably not in DB at all | ~40 |

---

## THE FIX — Codon Rename Migration

### What it is
Rename library PDFs from their current names to their DB `codon_filename` values. This deploys the naming system you already designed — `Author_Year#@#ART-XXXX@#@.pdf` — so the ART-ID is embedded in the filename and every downstream step can parse it directly.

### What it changes
- Enricher: ART-ID parsed from filename → direct DB lookup. Strategies 2-5 become fallbacks only.
- Crosswalk builder: reads ART-ID from filename, no more keyword guessing.
- Backfill script: direct article_id lookup, no QID-bridging needed.
- Future pipeline: any new PDF gets codon-renamed at ingest, before extraction starts.

### Implementation plan

**Phase 1: Add Strategy 0 to enricher (one function)**
New strategy at top of `lookup_article()`:
```python
# Strategy 0: Codon filename — parse ART-ID from filename
codon_match = re.search(r'#@#(ART-\d+)@#@', file_name)
if codon_match:
    art_id = codon_match.group(1)
    cur.execute("SELECT clean_ref, tier FROM articles WHERE article_id=?", (art_id,))
    row = cur.fetchone()
    if row:
        return _build_payload(conn, row[0], row[1], "codon_filename")
```
This is ~6 lines. Once codon filenames exist, this fires first and skips everything else.

**Phase 2: Rename script (new: `rename_to_codon.py`)**
For each PDF in the library:
1. Try to match to a DB article (using the 115-file map from this session)
2. Look up `codon_filename` from DB
3. Rename PDF: `afp_COPD_dx_mgmt.pdf` → `Gentry_Gentry_2017#@#ART-0487@#@.pdf`
4. Update enriched JSON `source.file_name` to match
5. Update DOCX filename if applicable
6. Log every rename for rollback

**DRY-RUN FIRST.** Script outputs the full rename map without touching files. User reviews, then `--execute` flag applies.

**Phase 3: Rebuild crosswalk**
Re-run `build_crosswalk_index.py` after renames. Crosswalk now links via codon-parsed ART-IDs.

**Phase 4: Re-run batch enricher on the 25 no-match files**
With codon filenames, these should all match on Strategy 0.

**Phase 5: Pipeline ingest step (future)**
Add codon-rename as Step 0 of `extract_guideline.bat`. When a new PDF enters the pipeline, it gets matched to a DB article and renamed before extraction. If no DB match exists, it proceeds with the original name and Strategies 1-5 handle it.

### What NOT to rename
- PDFs that don't match any DB article (supplementary references, vaccine schedules, etc.) — keep current names
- PDFs in `alt_refs/` — not part of the main pipeline
- Harrison's — uses page extractor, not standard pipeline

### Risk mitigation
- Dry-run mode mandatory before any renames
- Full rename log written (old_name → new_name → ART-ID)
- Crosswalk rebuilt after rename to verify consistency
- Enriched JSON `source.file_name` updated in same atomic operation

---

## OPEN FLAGS — CARRIED FORWARD

### FLAG 1 — ITE Enrichment Quality Dimension
**Status: OPEN** — Add 6th dimension to calibrate.py.

### FLAG 3 — Retroactive synthesis batch
**Status: OPEN, LOW PRIORITY** — AFP 001-100 missing synthesis{} block.

### FLAG 7 — acg_IBD persistent no_match
**Status: OPEN** — Not in DB. Needs investigation.

### FLAG 10 — Crosswalk Index
**Status: BUILT (v1.3), NEEDS UPGRADE** — Currently filename-based matching only. After codon rename, crosswalk should parse ART-IDs directly. Upgrade to v1.4 after Phase 2.

### FLAG 11 — Standout ITE References Without PDFs
**Status: MOSTLY RESOLVED** — This session proved that most "missing" PDFs actually exist under topic-based names. After codon rename, only genuinely missing articles remain.

### FLAG 12 — Codon Rename Migration (NEW)
**Status: SCOPED, READY TO IMPLEMENT**
115 PDFs auto-matchable now. 145 need extraction or manual resolution.
Implementation: Phases 1-5 described above.

### 16 DOCX/JSON NUMBER MISMATCHES
**Status: SUPERSEDED** — Codon rename will establish new canonical filenames for PDFs, JSONs, and DOCXs. The numbered-prefix alignment issue becomes moot.

---

## PRIORITY FOR NEXT SESSION

1. **Phase 1: Add Strategy 0 to enricher** — 6 lines of code
2. **Phase 2: Build and dry-run `rename_to_codon.py`** — review map, then execute
3. **Phase 3: Rebuild crosswalk** — verify all 115 renamed files link correctly
4. **Phase 4: Re-run batch enricher** on previously-unmatched files

---

## DELIVERABLES FROM THIS SESSION

| File | Location | Description |
|------|----------|-------------|
| ite_intelligence_db_profile.md | outputs/ (session temp) | Full DB profile with quality flags |
| ite_intelligence_priority_list.md | claude_knowledge/ | Ranked study priority list with extraction gap analysis |
| BATON_codon_migration_20260314.md | claude_knowledge/ | This document |

---

## KEY DATA POINTS FOR IMPLEMENTATION

**Auto-match map (115 PDFs → ART-IDs):** Generated in-session via title+year matching against DB. The matching script used enriched JSON titles, author parsing from filenames, and DB title keyword overlap. Reproducing this map is the first step of `rename_to_codon.py`.

**Enricher file:** `abfm_prep/02_ite_intelligence/scripts/ite_intelligence_enricher.py`
- `lookup_article()` starts at line 239
- Strategy 0 (codon parse) inserts before line 242

**DB codon_filename field:** All 1,397 articles populated. Query:
```sql
SELECT article_id, codon_filename FROM articles WHERE codon_filename LIKE '%#@#%'
```

**Crosswalk builder:** `abfm_prep/02_ite_intelligence/scripts/build_crosswalk_index.py` (v1.3)

**Batch enricher:** `abfm_prep/02_ite_intelligence/scripts/ite_intelligence_enricher_batch.py`

---

## CRITICAL FILE LOCATIONS

| File | Path |
|------|------|
| BATON (this) | claude_knowledge/BATON_codon_migration_20260314.md |
| Previous BATON | house_keeping_hub/BATON.md |
| ITE Intelligence DB | abfm_prep/02_ite_intelligence/db/ite_intelligence.db |
| Enricher script | abfm_prep/02_ite_intelligence/scripts/ite_intelligence_enricher.py |
| Crosswalk builder | abfm_prep/02_ite_intelligence/scripts/build_crosswalk_index.py |
| Batch enricher | abfm_prep/02_ite_intelligence/scripts/ite_intelligence_enricher_batch.py |
| Crosswalk JSON | abfm_prep/02_ite_intelligence/crosswalk_index.json |
| PDF library | clinical_guidelines/01_pdf_guideline_library/ |
| Enriched JSONs | clinical_guidelines/03_enriched JSON/ |
| DOCX summaries | clinical_guidelines/02_docx_guideline_library/ |
| Priority list | claude_knowledge/ite_intelligence_priority_list.md |
