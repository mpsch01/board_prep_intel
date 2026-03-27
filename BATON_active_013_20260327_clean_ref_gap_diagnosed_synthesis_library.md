# BATON 013 — clean_ref Gap Fully Diagnosed; synthesis_library Isolated; DB Cleanup Complete
**Date:** 2026-03-27
**Session platform:** Windows PC (Cowork VM)
**Status:** Active
**Preceding BATON:** `BATON_active_012_20260326_vfail_enriched_rematch.md` (→ archive)
**Git hash:** `10d8208` (no new commits this session — DB changes only)

---

## SESSION SUMMARY — What Was Done and Why

Four items from the BATON 012 queue closed. No new scripts written. DB patched directly via Python sqlite3. One architectural decision made (synthesis_library isolation).

1. **4 data_corrupt rows NULLed** — question stem text bleeding into ref_raw for QID-2024-0133, QID-2025-0029, QID-2025-0079, QID-2025-0138. ref_raw and clean_ref both set to NULL. Legitimate sibling refs for those QIDs preserved.

2. **clean_ref gap fully diagnosed** — 212 unique missing articles confirmed NOT in DB. These are updated AFP articles (2022-2024) and other journal articles cited by 2024-2025 questions that were never ingested. This is a new article ingestion problem, not a rematch or formatting problem. CSV exported to `00_database/readable_db_files/null_clean_ref_missing_articles_20260326.csv`.

3. **ART-0864 title fixed** — "e45-e67" → "Diagnosis and Treatment of Adults with Community-acquired Pneumonia" (Metlay/Waterer 2019 CAP guideline).

4. **54 flat JSONs isolated to synthesis_library/** — June 2024 pre-pipeline guideline downloads (AASLD, ACG, IDSA, ACC/AHA, USPSTF etc.) moved from extracted_json/ root to `extracted_json/synthesis_library/`. Zero ITE citations — not blocking anything. README.md written with origin, current state, and 5-step future integration path. PowerShell move script at `synthesis_library/move_files.ps1` — **Mikey to run on Windows.**

5. **sqlite-vec installed in VM** — `pip install sqlite-vec --break-system-packages`. Loads clean, both vec tables queryable (1,936 article_vec / 1,629 question_vec). Note: VM filesystem resets between sessions — re-run install if vec queries fail.

---

## 1. DB Changes This Session

| Change | Detail |
|--------|--------|
| question_ref_pairs | 4 rows: ref_raw + clean_ref → NULL (data_corrupt) |
| articles | ART-0864 title fixed |

**DB row counts unchanged** (no new records added):

| Table | Rows |
|-------|------|
| articles | 1,936 |
| questions | 1,629 |
| question_ref_pairs | 2,722 (4 rows now fully NULL) |
| qid_art_xref | 1,818 |
| article_icd10 | 3,855 |
| clinical_pathways | 3,093 |

---

## 2. clean_ref Gap — Full Picture

### Missing article count: 212 unique refs
- **88 AFP** — batch downloadable via AAFP downloader
- **66 Other** — mixed journals/guidelines, manual acquisition
- **13 USPSTF** — web resources, no PDF needed
- **12 JAMA** — paywall/manual
- **5 CDC** — web resources
- **5 Circulation, 5 NEJM, 5 ObGyn, 4 Cochrane, 4 Pediatrics, 3 Lancet, 1 AnnInternMed, 1 BMJ** — manual/paywall

**Root cause confirmed:** 2024-2025 ABFM questions cite updated AFP articles (new authors, newer publication years) on topics already covered by older articles in the DB. The DB has 2016-2021 versions; questions cite 2022-2024 updates. New ingestion pass required — not a rematch or formatting fix.

**CSV:** `00_database/readable_db_files/null_clean_ref_missing_articles_20260326.csv`

### clean_ref linkage stats (post this session)
| Year | Linked | Total | Pct |
|------|--------|-------|-----|
| 2018–2023 | All | All | 100% |
| 2024 | 251 | 329 | 76.3% |
| 2025 | 279 | 423 | 66.0% |

---

## 3. synthesis_library/ — Architecture Decision

**Location:** `extracted_json/synthesis_library/`
**Contents:** 54 pre-pipeline guideline JSONs (June 2024 downloads)
**Status:** Inert — no pipeline reads from this folder
**README:** Full integration path documented (5 steps: index → ART-IDs → PDFs → enrich → synthesis pipeline)
**Action needed (Windows):** Run `synthesis_library/move_files.ps1` to move 54 files from extracted_json root

---

## 4. Housekeeping Carried Forward

- [ ] **Windows:** Run `synthesis_library/move_files.ps1` — move 54 JSONs from extracted_json/ root
- [ ] **Windows:** Archive BATON 012 → `baton_archive/`
- [ ] **Windows:** Delete orphan batch logs (`_141856/_142810/_143114/_143258`)
- [ ] **Windows:** Delete M3 duplicates (`build_clinical_pathways.py`, `build_topic_trends.py`)
- [ ] **Windows:** Delete `BATON_active_007_20260325_m3_pipeline.md` from project root
- [ ] **Windows:** Sort VC_fail_batch / VC_pass_batch JSONs into archive subfolders (low priority)
- [ ] **Windows:** Delete temp scripts from Desktop (`show_null_refs.py`, `show_no_match.py`, etc.)

---

## Deferred Flags

| Flag | Description | Priority |
|------|-------------|----------|
| 212 missing articles (clean_ref gap) | New 2024-2025 AFP + other articles not yet in DB — need ingestion pass | HIGH |
| 1 pre-codon VC_fail no_match | `acute-low-back-imaging...` PDF needs ART-ID lookup + codon rename | MEDIUM |
| E2E module tests | M1 `build_crosswalk_index.py`, M3 `build_icd10_tags.py` | MEDIUM |
| Intelligence 2.0 Layer 2 | `article_currency` table via PubMed MCP — freshness checks, superseded_by | MEDIUM |
| 54 synthesis_library JSONs | Move script pending (Windows); future integration path documented | LOW |
| Scholl PDFs | `scholl_2025_ENCRYPTED_22/23/24.pdf` — need password | LOW |
| Dashboard replication | Replicate lifecycle dashboard for M1, M3, Module F | LOW |
| Pattern B Windows paths | 5 AAFP scripts with hardcoded `C:\` — defer until Mac primary | LOW |

---

## Next Steps (Ordered)

### 1. 88 AFP missing articles — batch download pass
The CSV has all 88 AFP refs. Feed them into `aafp_vc_batch_download.py` or equivalent. Each downloaded PDF needs a codon rename → ingest → enrich pass. This is the highest-leverage action to close the 2024-2025 clean_ref gap.

### 2. E2E module tests
- M1: `build_crosswalk_index.py` — verify crosswalk rebuilds cleanly against current warehouse
- M3: `build_icd10_tags.py` — verify ICD-10 tag report runs against current DB

### 3. Intelligence 2.0 Layer 2
`article_currency` table via PubMed MCP. Schema:
```sql
CREATE TABLE article_currency (
    article_id TEXT PRIMARY KEY,
    pubmed_id TEXT,
    last_checked DATE,
    is_current INTEGER DEFAULT 1,
    superseded_by TEXT,
    currency_note TEXT
);
```
PubMed MCP is available (`mcp__a1f87585...`). Start with a sample batch of high-citation articles.

### 4. Pre-codon VC_fail no_match
`acute-low-back-imaging-xray-mri-or-red-flag-pain...` PDF in VC_fail has no codon.
Steps: identify article → look up ART-ID → rename PDF with codon → re-extract → re-enrich.

---

## Conventions Locked (cumulative)

- **Path standard (ALL new scripts):**
  ```python
  SCRIPT_DIR   = Path(__file__).resolve().parent
  PROJECT_ROOT = SCRIPT_DIR.parent.parent
  ```
- **DB path:** `PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"`
- **No de novo JS.** New code = Python only.
- **VC gate:** `key_data_files/session_hy_inserts_v7.json` (352 citations)
- **Strategy 0 first** in every enricher — codon parse is always primary
- **Tier staging names:** `VC_pass` (→ right_click), `VC_fail` (→ local_lite)
- **Enricher contract:** Strategy 0 success = DB match = output produced (even if 0 linked Qs)
- **enriched_no_context:** `_no_ite_context=True`, `citation_count=0`. NOT skipped on next run.
- **extracted_json subfolders:** `VC_pass_batch/`, `VC_fail_batch/`, `synthesis_library/`
- **synthesis_library/:** Inert — pre-pipeline June 2024 guidelines. No pipeline reads this folder.
- **git from Windows** — VM can stage/commit but cannot `rm` NTFS files
- **sqlite-vec:** `pip install sqlite-vec --break-system-packages` (VM only, re-run each session)
