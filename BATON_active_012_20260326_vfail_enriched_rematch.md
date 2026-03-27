# BATON 012 — VC_fail Enriched (NC); Nomenclature Sweep Complete; Rematch + Classifier Added
**Date:** 2026-03-26
**Session platform:** Windows PC (Cowork VM)
**Status:** Active
**Preceding BATON:** `BATON_active_011_20260326_vc_pass_batch_enriched.md` (→ archive)
**Git hash:** `10d8208`

---

## SESSION SUMMARY — What Was Done and Why

This session closed the remaining items from BATON 011 and resolved a significant architectural
gap in the enricher. Five things happened:

1. **Nomenclature sweep executed** — `02_codon/` → `VC_pass/`, `00_non-codon/` → `VC_fail/` across
   filesystem, DB, scripts, and docs. 1,761 DB tier rows updated. Committed `609ef99`.

2. **qid_art_xref 2018-2019 gap confirmed closed** — `build_xref_2018_2019.py` had already run
   (360 + 292 = 652 rows). Task closed, not reopened.

3. **VC_fail extraction** — 146/146 PDFs extracted to `extracted_json/VC_fail_batch/`.

4. **Root cause of VC_fail no_match identified** — `_build_payload()` returned `None` when
   `question_ref_pairs` had 0 linked rows for an article, even if Strategy 0 had confirmed the
   article in DB via codon. This caused 145/146 VC_fail articles to log as `no_match` instead of
   producing output. The root cause of the missing question links is a clean_ref linkage gap in
   2024-2025 question_ref_pairs data (230 NULL clean_ref rows).

5. **Enricher fixed (Path B)** — `_build_payload()` no longer returns None on empty questions.
   Strategy 0 success = confirmed DB match, produces `enriched_no_context` block. Re-enrichment:
   144 NC + 1 full context + 1 no_match (1 pre-codon PDF without ART-ID in filename).

---

## 1. Nomenclature Sweep — COMPLETE ✅

**Commits:** `609ef99` (renames + .gitignore), `10d8208` (script + doc updates)

| Item | Status |
|------|--------|
| Windows folder renames (`02_codon/`→`VC_pass/`, `00_non-codon/`→`VC_fail/`, `02_codon_batch/`→`VC_pass_batch/`) | ✅ Done by user |
| `rename_tier_labels_in_db.py` — new script, ran live | ✅ 1,399 + 362 = 1,761 rows updated |
| `backfill_new_article_metadata.py` — TIER_FOLDERS dict updated | ✅ |
| `audit_engine_type_changes.py` — TIER_FOLDERS dict updated | ✅ |
| `CLAUDE.md` tier table updated | ✅ |
| `.auto-memory/memory/glossary.md` updated | ✅ |
| `.gitignore` — added `.fuse_hidden*` and `02_module.2_processor/logs/` | ✅ |
| 46 `.fuse_hidden` files removed from git tracking | ✅ |

---

## 2. clean_ref Linkage Gap — Diagnosed, Partially Fixed

### Root Cause
2024 and 2025 question data was ingested with `clean_ref = NULL` in `question_ref_pairs`.
The `_build_payload()` query joins `question_ref_pairs.clean_ref = articles.clean_ref` — so
articles whose refs appear only in 2024-2025 questions get 0 rows → formerly triggered `no_match`.

### Stats (post-rematch)
| Year | Linked | Total | Pct |
|------|--------|-------|-----|
| 2018 | 361 | 361 | 100.0% |
| 2019 | 292 | 292 | 100.0% |
| 2020 | 314 | 314 | 100.0% |
| 2021 | 333 | 333 | 100.0% |
| 2022 | 341 | 341 | 100.0% |
| 2023 | 329 | 329 | 100.0% |
| 2024 | 251 | 329 | 76.3% |
| 2025 | 279 | 423 | 66.0% |

### Rematch (`rematch_unmatched.py`) — threshold 85
- 8 rows matched and written (all scores 89–100, all colon-vs-comma / capitalization diffs)
- 222 still NULL

### Bucket classification (`classify_null_refs.py`) — new script
| Bucket | Count | Pct | Action |
|--------|-------|-----|--------|
| well_formed | 179 | 80.6% | Potentially linkable — articles may not yet be in DB |
| web_resource | 26 | 11.7% | USPSTF, CDC, ADA pages — no DB article, expected |
| journal_stub | 13 | 5.9% | Journal/vol/pg only — permanently unmatchable |
| data_corrupt | 4 | 1.8% | Question stem text bleeding into ref field — NULL out |

**Key finding:** The 179 well_formed refs failed fuzzy matching against all 1,936 articles at
threshold 85. This strongly suggests these articles are **not yet in the DB** — they're newer
2024-2025 citations that haven't been ingested. This is the root cause of the ongoing clean_ref
gap and will require new article ingestion, not just rematch tuning.

### 4 data_corrupt rows to NULL out
| QID | ref_raw (truncated) |
|-----|---------------------|
| QID-2024-0133 | "He currently walks 2000–3000 steps daily..." |
| QID-2025-0029 | "The 2018 ARRIVE (A Randomized Trial of Induction..." |
| QID-2025-0079 | "Falls are a common cause of serious injury..." |
| QID-2025-0138 | "The Diagnosis and Treatment of Low Back Pain Work Group..." |

---

## 3. Enricher Fix (Path B) — COMPLETE ✅

**File:** `02_module.2_processor/scripts/ite_intelligence_enricher.py`
**Commit:** `10d8208`

### Change
- `_build_payload()`: removed `if not questions: return None` guard. Always returns payload.
- `process_file()`: new branch for empty questions → writes `enriched_no_context` block
  (no API call, `citation_count=0`, `_no_ite_context=True`). Files with `citation_count=0`
  are NOT skipped on next run → will auto-upgrade to full enrichment once clean_ref is resolved.
- `main()`: new `enriched_no_context` counter + `[NC]` log line.

### VC_fail Re-Enrichment Result
```
Enriched (with ITE context): 1      ← lymphadenopathy article (QID-2024-0072)
Enriched (no context yet):   144    ← confirmed in DB, clean_ref link pending
No DB match:                 1      ← pre-codon PDF (see below)
```

### 1 Remaining no_match
File: `acute-low-back-imaging-xray-mri-or-red-flag-pain-pain-lasting-less-ct-if-mri-con-f2e8420694_extracted.json`

No codon in filename → Strategy 0 found nothing. This PDF is in the VC_fail folder without
a codon rename. Needs: ART-ID lookup → PDF rename with codon → re-extract → re-enrich.

---

## 4. DB State (unchanged from BATON 011)

| Table | Rows | Note |
|-------|------|------|
| articles | 1,936 | |
| questions | 1,629 | |
| question_ref_pairs | 2,722 | 8 rows now have clean_ref (from rematch) |
| qid_art_xref | 1,818 | 2018–2025 complete |
| article_icd10 | 3,855 | |
| clinical_pathways | 3,093 | |

**DB tier breakdown (articles — post rename):**
- `VC_fail`: 1,399
- `VC_pass`: 362
- `local_lite`: 117
- `right_click`: 58

---

## 5. Housekeeping Carried Forward

- [ ] **Windows:** Archive BATON 009, 010, 011 → `baton_archive/`
- [ ] **Windows:** Delete orphan batch logs (`_141856/_142810/_143114/_143258`)
- [ ] **Windows:** Delete M3 duplicates (`build_clinical_pathways.py`, `build_topic_trends.py`)
- [ ] **Windows:** Delete `BATON_active_007_20260325_m3_pipeline.md` from project root
- [ ] **Windows:** Sort 242 flat JSONs into `VC_pass_archive/` and `VC_fail_archive/` subfolders
- [ ] **DB:** NULL out 4 data_corrupt `question_ref_pairs` rows (see Section 2)
- [ ] **DB:** Fix ART-0864 title ("e45-e67" → Metlay/Waterer 2019 CAP guideline)
- [ ] **Cleanup:** Delete temp scripts from Windows Desktop (`show_null_refs.py`, `show_no_match.py`, etc.)

---

## Deferred Flags

| Flag | Description | Priority |
|------|-------------|----------|
| 179 well_formed NULL clean_ref | Likely new 2024-2025 articles not yet in DB — need ingestion | HIGH |
| 1 pre-codon VC_fail no_match | `acute-low-back-imaging...` PDF needs ART-ID lookup + codon rename | MEDIUM |
| 54 no-art-id flat JSONs | Title-match pass to link to DB | MEDIUM |
| ART-0864 title fix | Stored as "e45-e67"; fix to Metlay/Waterer 2019 CAP | LOW |
| Scholl PDFs | `scholl_2025_ENCRYPTED_22/23/24.pdf` — need password | LOW |
| Flat JSON sort | Sort 242 legacy flat JSONs into VC_pass/VC_fail archive subfolders | LOW |
| E2E module tests | M1 `build_crosswalk_index.py`, M3 `build_icd10_tags.py` | MEDIUM |
| Intelligence 2.0 Layer 2 | `article_currency` table via PubMed MCP | MEDIUM |
| Dashboard replication | Replicate lifecycle dashboard for M1, M3, Module F | LOW |
| Pattern B Windows paths | 5 AAFP scripts with hardcoded `C:\` — defer until Mac primary | LOW |

---

## Next Steps (Ordered)

### 1. NULL out 4 data_corrupt rows in question_ref_pairs (quick cleanup)
```sql
UPDATE question_ref_pairs
SET ref_raw = NULL, clean_ref = NULL
WHERE qid IN ('QID-2024-0133','QID-2025-0029','QID-2025-0079','QID-2025-0138')
  AND clean_ref IS NULL
  AND ref_raw LIKE 'He currently%'
     OR ref_raw LIKE 'The 2018 ARRIVE%'
     OR ref_raw LIKE 'Falls are a common%'
     OR ref_raw LIKE 'The Diagnosis and Treatment of Low Back Pain Work Group%';
```
(Run carefully — verify row counts first)

### 2. Investigate the 179 well_formed NULL clean_ref rows
**Question to answer:** Are these articles already in the DB with different clean_ref formatting,
or are they genuinely new articles not yet ingested? Strategy: pick 10 representative well_formed
refs from the classify_null_refs_report.txt and manually look them up in articles table.
If not in DB → new ingestion pass needed for 2024-2025 AFP articles.

### 3. Fix ART-0864 title
```sql
UPDATE articles SET title = 'Diagnosis and Treatment of Adults with Community-acquired Pneumonia'
WHERE article_id = 'ART-0864';
```

### 4. E2E Module Tests
- M1: `build_crosswalk_index.py`
- M3: `build_icd10_tags.py` report

### 5. Intelligence 2.0 Layer 2
`article_currency` table via PubMed MCP — freshness checks, `superseded_by` tracking.

---

## Conventions Locked (cumulative)

- **Path standard (ALL new scripts):**
  ```python
  SCRIPT_DIR   = Path(__file__).resolve().parent
  PROJECT_ROOT = SCRIPT_DIR.parent.parent
  ```
- **DB path:** `PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"`
- **Log path:** `PROJECT_ROOT / "00_database" / "logs"`
- **No de novo JS.** New code = Python only.
- **VC gate:** `key_data_files/session_hy_inserts_v7.json` (352 citations)
- **Strategy 0 first** in every enricher — codon parse is always primary
- **Tier staging names:** `VC_pass` (→ right_click), `VC_fail` (→ local_lite)
- **Enricher contract:** Strategy 0 success = DB match = output produced (even if 0 linked Qs)
- **enriched_no_context:** `_no_ite_context=True`, `citation_count=0`. NOT skipped on next run.
- **extracted_json subfolders:** `VC_pass_batch/`, `VC_fail_batch/`, `VC_pass_archive/`, `VC_fail_archive/`
- **git from Windows** — VM can stage/commit but cannot `rm` NTFS files
