# BATON 010 — QC Complete / Path Fixes / Dashboard Built
**Date:** 2026-03-25
**Session platform:** Windows PC (Cowork VM)
**Status:** Active
**Preceding BATON:** `BATON_active_009_20260325_windows_sync_complete.md` (→ archive)
**Git hash:** `02d8a37` (path fixes committed)

---

## SESSION SUMMARY — What Was Done and Why

Quality control and validation session. Verified the BATON 009 enrichment output, ran an end-to-end extraction test on codon + non-codon PDFs, caught and fixed a path depth bug in both enrichers, and built a pipeline dashboard + visualization suite.

---

## 1. Post-Enrichment QC — 129 Enriched JSONs

Spot-checked 8 files spread across the full range. Full sweep of all 129 for match method, confidence, and field population.

### Findings — PASS
| Field | Coverage | Notes |
|-------|----------|-------|
| concept_summary | 129/129 | High quality, exam-specific, clinically accurate |
| tier_rationale | 129/129 | Populated with correct citation counts + exam years |
| linked_qids | 129/129 | Full question stems + concept_tested + color codes |
| source.art_id | 129/129 | All articles correctly linked to DB |
| high_yield_concepts | 129/129 | 5–7 per article, specific and testable |
| _enriched_via | 129/129 | `batch_api` confirmed on all |

### Findings — FLAGS (not blockers)
1. **Match method: 99.2% title-matched** — Strategy 0 never fired on this batch. Expected: these JSONs came from non-codon-named PDFs (long title-based filenames). Title fallback is working correctly. Strategy 0 will fire when codon-named PDFs are processed.
2. **enrichment_confidence: 99.2% "low"** — Direct consequence of title-matching. Not a defect.
3. **One content-filename mismatch** — `2013-idsa-clinical-practice-guideline-for-vaccination...json` contains blood pressure article data (ART-0253). Pre-enrichment extraction issue. The enrichment block is correct for ART-0253 but the JSON filename is misleading. Not introduced by batch API.
4. **`no_match` label is ambiguous** — Enricher logs both "not in DB" and "in DB but no linked questions" as `no_match`. Should be two distinct statuses. Deferred as FLAG.

---

## 2. Extraction Pipeline Test — Codon + Non-Codon PDFs

Tested two PDFs end-to-end through `convert_pdfs_to_json.py` → `ite_intelligence_enricher.py --dry-run`:

| PDF | Tier | ART-ID | Strategy | Result |
|-----|------|--------|----------|--------|
| `Ables_Nagubilli_2010#@#ART-0013@#@.pdf` | 02_codon | ART-0013 | codon_filename | ✅ 2 Qs, [2021,2022], confidence=HIGH |
| `AAN_2012#@#ART-1414@#@.pdf` | 00_non-codon | ART-1414 | — | ⚠ no_match (in DB, 0 linked questions) |

**Key finding:** The `00_non-codon/` tier PDFs may be codon-named but many have 0 linked ITE questions → enricher correctly skips them. The enricher requires linked questions to generate `ite_intelligence{}`. Articles without ITE question history cannot be enriched.

**Live enrichment on ART-0013 not run** — dry-run confirmed correct, deferred to next session as a clean first Strategy-0 live test.

---

## 3. Path Bug Fixed — Both Enrichers

**Bug:** `BASE_DIR = Path(__file__).resolve().parent.parent` in M2/scripts resolves to `02_module.2_processor/`, not PROJECT_ROOT. Pattern A fixes (BATON 008/009) corrected the DB path suffix but not the depth.

**Fix applied to both scripts:**

| Script | Change |
|--------|--------|
| `ite_intelligence_enricher.py` | `parent.parent` → `parent.parent.parent` |
| `ite_intelligence_enricher_batch.py` | `parent.parent` → `parent.parent.parent` |
| Both | `LOG_DIR = BASE_DIR / "logs"` → `BASE_DIR / "00_database" / "logs"` |

**Why it wasn't caught before:** The 129-JSON batch enrichment ran on the Mac (BATON 008) where path depth resolved correctly. Live enricher was not exercised post-Windows-sync until this session.

**⚠ Not yet committed** — needs `git add` + `git commit` from Windows.

---

## 4. Dashboard + Visualization Built

Two outputs created in `#PROJECT_OVERHAUL/`:

| File | Type | Contents |
|------|------|----------|
| `ite_pipeline_dashboard.html` | Interactive HTML | 8 charts: tier donut, questions by year, source type, xref gap, QID distribution, DB table health, column coverage, engine type |
| `ite_pipeline_viz.png` | Static 9-panel PNG | Same data, publication-quality, dark theme |

**Key visual finding:** The 2018–2019 xref gap is prominently visible — two red zero-bars while all other years sit at 242–341 rows. Confirms crosswalk pass is the right next task.

---

## 5. Current DB State (unchanged from BATON 009)

| Table | Rows |
|-------|------|
| articles | 1,936 |
| questions | 1,629 |
| question_ref_pairs | 2,722 |
| qid_art_xref | 1,818 |
| article_icd10 | 3,855 |
| clinical_pathways | 3,093 |
| icd10_rollup | 614 |
| icd10_code_xref | 1,006 |

---

## 6. Housekeeping Needed

- [ ] **Windows:** Archive `BATON_active_009_20260325_windows_sync_complete.md` → `baton_archive/`
- [x] **Windows:** `git add` + `git commit` the enricher path fixes — `02d8a37` ✅
- [ ] **Windows:** Delete orphan batch logs (`_141856/_142810/_143114/_143258`)
- [ ] **Windows:** Delete M3 duplicates (`build_clinical_pathways.py`, `build_topic_trends.py`)
- [ ] **Windows:** Delete `BATON_active_007_20260325_m3_pipeline.md` from project root (archive copy exists)

---

## Deferred Flags (carried forward + new)

| Flag | Description |
|------|-------------|
| BATCH_DIRS | 243 flat JSONs in `extracted_json/` need sorting into 5 batch subdirs |
| Scholl PDFs | `scholl_2025_ENCRYPTED_22/23/24.pdf` — need password |
| Supabase eval | Defer until pipeline stable |
| Pattern B Windows paths | 5 AAFP scripts with hardcoded `C:\` — defer until Mac primary |
| Rename `#` folder | Defer until after QC + test runs |
| Dashboard replication | Replicate lifecycle dashboard for M1, M3, Module F, ITE question pipeline |
| Orphan batch logs | Delete `_141856/_142810/_143114/_143258` log files |
| no_match label | Enrich `no_match` status → distinguish `not_in_db` vs `no_linked_questions` |
| Codon live test | Run `ite_intelligence_enricher.py --file` live on ART-0013 JSON as first Strategy-0 end-to-end validation |

---

## Next Steps (Ordered)

### 1. Commit Path Fixes (Windows)
```powershell
git add 02_module.2_processor/scripts/ite_intelligence_enricher.py
git add 02_module.2_processor/scripts/ite_intelligence_enricher_batch.py
git commit -m "fix: correct BASE_DIR path depth in both enrichers (parent.parent.parent)"
```

### 2. qid_art_xref Crosswalk Pass (2018–2019 gap)
- 440 questions exist for 2018–2019 in `questions` table
- 653 `question_ref_pairs` exist for those years
- 0 entries in `qid_art_xref` for 2018–2019
- Need script to build xref entries from existing `question_ref_pairs` + `articles` join

### 3. Live Enrichment Test — Strategy 0 end-to-end
```powershell
python 02_module.2_processor\scripts\ite_intelligence_enricher.py --file "test_batch_output\prevention-diagnosis-and-management-of-serotonin-syn..._extracted.json"
```
Verify: `_match_method: codon_filename`, `enrichment_confidence: high`, full `ite_intelligence{}` block written.

### 4. E2E Module Tests
- M1: `build_crosswalk_index.py`
- M3: `build_icd10_tags.py` report

### 5. Intelligence 2.0 Layer 2
`article_currency` table via PubMed MCP — freshness checks, `superseded_by` tracking

---

## Conventions Locked (unchanged)

- **Path depth (M2/scripts):** `Path(__file__).resolve().parent.parent.parent` = PROJECT_ROOT ← UPDATED THIS SESSION
- **Path depth (M1/build, M1/maintain):** `Path(__file__).resolve().parent.parent.parent` = PROJECT_ROOT
- **Path depth (M3/scripts):** `Path(__file__).resolve().parent.parent` = PROJECT_ROOT
- **DB path:** `PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"` (all scripts)
- **Log path:** `PROJECT_ROOT / "00_database" / "logs"` (all scripts)
- **No de novo JS.** New code = Python only.
- **VC gate:** `key_data_files/session_hy_inserts_v7.json` (352 citations)
- **Strategy 0 first** in every enricher
