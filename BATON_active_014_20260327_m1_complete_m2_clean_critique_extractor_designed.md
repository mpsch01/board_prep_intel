# BATON 014 — M1 Build Complete, M2 Cleaned, Critique Extractor + Citation Trend Designed
**Date:** 2026-03-27
**Session platform:** Windows PC (Cowork VM)
**Status:** Active
**Preceding BATON:** `BATON_active_013_20260327_clean_ref_gap_diagnosed_synthesis_library.md` (→ archive)
**Git hash:** `10d8208` (no new commits this session — filesystem + design work only)

---

## SESSION SUMMARY — What Was Done and Why

Heavy housekeeping + architectural session. No new scripts built. Four major workstreams completed.

### 1. Windows Housekeeping (BATON 013 queue cleared)
All 6 items from BATON 013 closed:
- `synthesis_library/` fully populated — all 242 legacy flat JSONs moved from extracted_json/ root (confirmed correct: all were pre-pipeline downloads from the auto-download setup, not just the 54 originally scoped)
- Orphan batch log folders deleted (`_141856/_142810/_143114/_143258`)
- BATON 012 archived → `baton_archive/`
- M3 duplicates deleted (`build_clinical_pathways.py`, `build_topic_trends.py` from M3/scripts/)
- `BATON_active_007_20260325_m3_pipeline.md` deleted from root
- Desktop temp scripts cleared

### 2. Full Project Inventory Sweep
Compared current state to original inventory (March 21, 2026). Key findings:
- DB grown substantially: 1,547 → 1,936 articles, 1,189 → 1,629 questions
- Intelligence 2.0 layers all new (article_icd10, clinical_pathways, icd10_rollup, icd10_code_xref, vec tables)
- **qid_art_xref corrected:** live count = 2,470 (not 1,818 in BATON 013) — `build_xref_2018_2019.py` ran after BATON 013 was written, adding 2018-2019 xref rows
- DOCX library (1,518 files pre-overhaul): confirmed missing but not a real loss. Metadata-only DOCXs not worth recovering. Right_click DOCXs (71) regenerable from pipeline.
- Folder cleanup: sectional_READMEs, tagging_bundle, re-org_guidance, map files all deleted. auto-memory-copies moved to root. re-org_guidance keep files moved to key_data_files/.

### 3. M2 Cleanup + M1 Build Sequence Completed
- Deleted 3 one-time scripts from M2/scripts/: `backfill_merge_source_fields.py`, `build_xref_2018_2019.py`, `batch_retrieve_enrichment.py`
- Moved `backfill_keywords_2018_2019.py` → M1/build/ (it's a build-time operation)
- Moved `preprocess_concept_tags.py` → M1/maintain/ (recurring, DB population)
- **M1/build/ is now a self-contained 9-step rebuild sequence** — no detours into M2
- ite_2018_2019_enriched.json + ite_2018_2019_extracted.json moved to archive_canonical (already integrated)

### 4. Pipeline Architecture Design
Two new scripts designed (not yet built):

**`extract_ite_critique_refs.py`** (M2/scripts/)
- Input: `ITE_yearNNNN_critique.pdf` (ABFM standard release format)
- Local/PDF-native, zero API cost (pdfplumber — already in requirements.txt)
- Dispatcher architecture: `parse_modern()` handles 2025+ format as default; year-specific overrides for format changes
- Matches refs against DB `articles.clean_ref` directly (not legacy CSV)
- Outputs question_ref_pairs format the existing pipeline expects
- Replaces/complements `F_extract_question_refs.py` (which required DOCX)

**`update_citation_trends.py`** (M1/maintain/)
- Populates/refreshes `article_citation_trend` companion table
- Pure SQL computation from `qid_art_xref` — no API, runs in seconds
- Triggered after each new year integration

**`article_citation_trend` table** (schema designed, not yet built):
```sql
CREATE TABLE article_citation_trend (
    article_id          TEXT PRIMARY KEY,
    years_cited         TEXT,        -- "2022,2023,2024,2025"
    distinct_year_count INTEGER,
    first_cited_year    INTEGER,
    most_recent_year    INTEGER,
    consecutive_streak  INTEGER,     -- current streak ending at most_recent_year
    is_watch_list       INTEGER DEFAULT 0  -- 1 if streak >= 2
);
```

**Ref extraction architecture (three paths):**
- Path A — DOCX (2020-2025): `F_extract_question_refs.py` — legacy, already processed
- Path B — PDF + API (2018-2019): `enrich_ite_questions.py` — API extracts refs inline
- Path C — PDF local (future): `extract_ite_critique_refs.py` — planned, zero API cost

---

## 1. DB Changes This Session

No DB changes. All work was filesystem and design.

**DB row counts (verified live 2026-03-27):**

| Table | Rows | Notes |
|-------|------|-------|
| articles | 1,936 | |
| questions | 1,629 | |
| question_ref_pairs | 2,722 | |
| qid_art_xref | 2,470 | Corrected from 1,818 |
| article_icd10 | 3,855 | |
| clinical_pathways | 3,093 | |
| icd10_rollup | 614 | |
| icd10_code_xref | 1,006 | |

---

## 2. Filesystem Changes This Session

### Deleted
- `sectional_READMEs/` (entire folder)
- `tagging_bundle/` (entire folder)
- `re-org_guidance/` (entire folder)
- `master_map.JSON` (root)
- `MASTER_MAP_V.1.html` (root)
- `TEMP_MIGRATION_MANIFEST.md` (root)
- `BATON_active_007_20260325_m3_pipeline.md` (root)
- M2/scripts/: `backfill_merge_source_fields.py`, `build_xref_2018_2019.py`, `batch_retrieve_enrichment.py`
- M3/scripts/: `build_clinical_pathways.py` (duplicate), `build_topic_trends.py` (duplicate)
- DB/logs/: orphan batch log folders `_141856/_142810/_143114/_143258`

### Moved
- `backfill_keywords_2018_2019.py`: M2/scripts/ → M1/build/
- `preprocess_concept_tags.py`: M2/scripts/ → M1/maintain/
- `auto-memory-copies/`: re-org_guidance/ → project root
- From re-org_guidance/ → key_data_files/: `FILE_NAMING_SPEC.md`, `ITE_Intelligence_2.0_Architecture.md`, `project_overhaul_inventory.md`, `RENAMING_PROPOSAL.md`, `script_library.csv`
- BATON 013 → `baton_archive/` (to be done on Windows)
- `extracted_json/` root: 242 flat JSONs → `synthesis_library/`

### Script Count Update
| Location | Python | JS | Other |
|----------|--------|----|-------|
| M1/build/ | 9 | — | 1 README |
| M1/maintain/ | 16 | — | 1 README |
| M2/scripts/ | 44 | 6 | 1 JSON + 4 Windows |
| M3/scripts/ | 4 | 1 | 2 JSON |

---

## 3. Housekeeping Carried Forward

- [ ] **Windows:** Archive BATON 013 → `baton_archive/`
- [ ] **Git:** Stage + commit all session changes

---

## Deferred Flags

| Flag | Description | Priority |
|------|-------------|----------|
| 212 missing articles (clean_ref gap) | 88 AFP batch-downloadable; rest manual | HIGH |
| extract_ite_critique_refs.py | Local PDF-native critique ref extractor — designed, not built | HIGH |
| update_citation_trends.py | Citation trend maintenance script — designed, not built | HIGH |
| article_citation_trend table | Schema designed, not yet built in DB | HIGH |
| 1 pre-codon VC_fail no_match | `acute-low-back-imaging...` PDF needs ART-ID lookup + codon rename | MEDIUM |
| E2E module tests | M1 build_crosswalk_index.py, M3 build_icd10_tags.py | MEDIUM |
| Intelligence 2.0 Layer 2 | article_currency table via PubMed MCP | MEDIUM |
| Right_click DOCX regeneration | 71 DOCXs regenerable via build_summary.js | LOW |
| Scholl PDFs | scholl_2025_ENCRYPTED_22/23/24.pdf — need password | LOW |

---

## Next Steps (Ordered)

### 1. Build the two designed scripts + table
- Create `article_citation_trend` table in DB
- Write `update_citation_trends.py` → M1/maintain/ (pure SQL, ~40 lines)
- Write `extract_ite_critique_refs.py` → M2/scripts/ (pdfplumber, dispatcher architecture)
- Run update_citation_trends.py on existing data to populate table

### 2. 88 AFP missing articles — batch download pass
CSV: `00_database/readable_db_files/null_clean_ref_missing_articles_20260326.csv`
Each downloaded PDF: codon rename → ingest → enrich

### 3. Intelligence 2.0 Layer 2
`article_currency` table via PubMed MCP. Schema already defined in BATON 013.

### 4. E2E module tests
- M1: `build_crosswalk_index.py`
- M3: `build_icd10_tags.py` report

### 5. Pre-codon VC_fail no_match
`acute-low-back-imaging...` PDF: ART-ID lookup → codon rename → re-extract → re-enrich

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
- **Strategy 0 first** in every enricher
- **Tier staging names:** `VC_pass` (→ right_click), `VC_fail` (→ local_lite)
- **M1/build/ = full rebuild sequence** (9 scripts, self-contained)
- **New year integration = Path C** (extract_ite_critique_refs.py) once built
- **article_citation_trend** = companion table, derived from qid_art_xref, pure SQL
- **synthesis_library/** = inert, all legacy flat JSONs (~242). No pipeline reads this folder.
- **git from Windows** — VM can stage/commit but cannot rm NTFS files
- **sqlite-vec:** `pip install sqlite-vec --break-system-packages` (VM only, re-run each session)
