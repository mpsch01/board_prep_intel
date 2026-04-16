# ABFM ITE Intelligence System — board_prep_intel

**Last updated:** 2026-04-16 (BATON 061)
**Status:** Active development
**Active BATON:** `BATON_active_061_20260416_legacy_bodysystem_analyses_complete.md`
**Next ART-ID:** ART-2000
**Git:** `main` → `bc462a3` → `https://github.com/mpsch01/board_prep_intel` (private)

---

## Machine-Readable State

```json
{
  "project": "ABFM ITE Intelligence System",
  "description": "A queryable Family Medicine board exam knowledge base (1,639 ITE + 1,221 AAFP questions, 2018–2025) linked to a clinical guideline library (1,998 articles, 1,004 PDFs) via a structured SQLite pipeline.",
  "baton": "BATON_active_061_20260416_legacy_bodysystem_analyses_complete.md",
  "baton_description": "Stage 1.75 DB body system backfill added; all 7 resident analyses complete; DEFERRED-HUMAN-REVIEW-BODY-SYSTEM closed; article_currency 1,998/1,998 complete.",
  "git_hash": "bc462a3",
  "git_branch": "main",
  "github_remote": "https://github.com/mpsch01/board_prep_intel",
  "last_updated": "2026-04-16",
  "next_art_id": "ART-2000",
  "vc_gate_citations": 352,
  "database": {
    "file": "00_database/db/ite_intelligence.db",
    "articles": 1998,
    "questions_ite": 1639,
    "questions_aafp": 1221,
    "qid_art_xref": 2485,
    "aafp_qid_art_xref": 864,
    "article_icd10": 3952,
    "question_icd10": 5003,
    "aafp_question_icd10": 4753,
    "clinical_pathways": 3971,
    "pubmed_pmid_cache": 344,
    "icd10_vec": 2219,
    "article_icd10_vec": 1757,
    "question_icd10_vec": 2747,
    "article_vec": 1998,
    "question_vec": 1639,
    "aafp_question_vec": 1221,
    "intersection_centroid_vec": 123,
    "article_currency": 1998
  },
  "pdfs": {
    "vc_fail": 630,
    "vc_pass": 168,
    "local_lite": 117,
    "right_click": 58,
    "aafp": 15,
    "ite_exams": 16,
    "total": 1004
  },
  "scripts": {
    "m1_build_py": 8,
    "m1_maintain_py": 26,
    "m2_py": 75,
    "m2_js": 6,
    "m3_py": 50,
    "m3_js": 2,
    "m4_py": 1,
    "m5_py": 3,
    "m5_typescript": 35,
    "m5_sql": 5
  },
  "modules": {
    "m1_warehouse": "01_module.1_warehouse/",
    "m2_processor": "02_module.2_processor/",
    "m3_analyst": "03_module.3_analyst/",
    "m4_sandbox": "04_module.4_sandbox/",
    "m5_web": "05_module.5_web/",
    "database": "00_database/"
  }
}
```

---

## Project Overview

A queryable Family Medicine board exam knowledge base: 1,639 ITE questions (2018–2025) and 1,221 AAFP BRQ questions linked to a clinical guideline library of 1,998 articles and 1,004 PDFs via a structured SQLite pipeline. Both corpora are schema-parallel with full enrichment across body_system, blueprint, concept_tags, and ICD-10. Intelligence 2.0 layers (ICD-10 diagnostic linkage, clinical pathways, citation trend tracking, vector embeddings, cross-corpus semantic similarity) provide structured clinical navigation across the full corpus. System extends beyond exam prep into clinical decision support via the ITE Score Analyzer plugin and Module 5 web platform.

---

## Directory Structure

### 00_database/
Source of truth. Never disposable.
- `db/ite_intelligence.db` — Production SQLite database (1,998 articles, 1,639 ITE questions, 1,221 AAFP questions)
- `readable_db_files/` — CSV exports, human-readable snapshots
- `logs/` — Pipeline run logs
- `schemas/` — clinical_synonym_map.json, icd10_mcp_lookup.json, ite-data-context-skill/

### 01_module.1_warehouse/
PDF library (4 tiers, 973 ITE + 15 AAFP + 16 exam PDFs) + pipeline build and maintenance scripts.
- `citation_files/ITE/VC_fail/` — 630 PDFs: bulk; lowest citation priority
- `citation_files/ITE/VC_pass/` — 168 PDFs: codon-named, VC-cited, awaiting full pipeline
- `citation_files/ITE/local_lite/` — 117 PDFs: VC_fail + fully enriched (pipeline complete)
- `citation_files/ITE/right_click/` — 58 PDFs: VC_pass + fully enriched (highest-value tier)
- `citation_files/AAFP/` — 15 AAFP citation PDFs (recovered 2026-04-05)
- `citation_files/_dupe_archive/` — 14 duplicate PDFs archived
- `citation_files/ite_exams/` — 16 raw PDFs: YYYY_MC.pdf + YYYY_critique.pdf (2018–2025)
- `practice_questions/` — 42 Q&A deliverables: 8 ITE DOCX + 8 ITE XLSX + 13 AAFP DOCX + 13 AAFP XLSX (gitignored; regenerable from DB)
- `build/` — 8 scripts: self-contained full rebuild sequence
- `maintain/` — 26 scripts: recurring DB population and maintenance operations
- `scripts/aafp_brq_scraper.py` — scraper at scripts/ root (Windows-only)

### 02_module.2_processor/
Extraction, enrichment, and DOCX build pipeline.
- `scripts/` — 75 Python + 6 JS; includes `core/` (4py), `engines/` (7py), `utils/` (6py) packages + `source/` (transcripts, blueprint xlsx), `outputs/` (staging JSONs), `prompts/` (templates)

### 03_module.3_analyst/
ICD-10 tagging, clinical pathways, trend analysis, score analysis, body system QC/normalization, AAFP-ITE reuse investigation.
- `scripts/` — 50 Python + 2 JS (ite_analyzer_v3.py, ite_parser.py, ite_report_builder_v2.js, build_article_currency.py, body-system-qc pipeline, normalization scripts, etc.)
- `docs/` — per-resident analysis output docs
- `resident_data/` — raw ABFM score report PDFs, structured as `ITE_{lastname}_{firstname}/inputs/` + `outputs/` (not git-tracked)

### 04_module.4_sandbox/
Experiments and agent prototypes.
- `scripts/` — nl_search_validation.py (validates pgvector NL search pipeline)

### 05_module.5_web/
Interactive web platform (Next.js + Supabase + Sanity + Railway FastAPI). Scaffolded 2026-04-09.
- `frontend/` — Next.js 15 app (Netlify deployment)
- `supabase/` — PostgreSQL + pgvector migrations + sync scripts
- `sanity/` — CMS schemas (curriculum content)
- `api/` — Railway FastAPI (PDF score parser)
- `scripts/` — 3 py sync + 35 TypeScript/TSX + 5 SQL migrations

### _archive_/
Curated deliverables: curriculum definitions, question bank, analysis outputs, reference data, acquisition lists. Also houses retired artifacts from Sweep 1 (docx_guideline_library/).

### baton_archive/
All archived BATON session handoff documents (BATON 024–059).

### extracted_json/
Middle-man layer (not git-tracked).
- `synthesis_library/` — 242 legacy pre-pipeline flat JSONs (inert, no ART-IDs)
- `VC_pass_batch/` — 95 enriched JSONs (VC_pass tier)
- `VC_fail_batch/` — 147 enriched JSONs (VC_fail tier)
- Root: `manifest.json` only

### key_data_files/
Critical reference data:
- `session_hy_inserts_v7.json` — VC gate (352 citations, sole right_click criterion)
- `null_clean_ref_missing_articles_20260326.csv` — 212 missing articles list
- `FILE_NAMING_SPEC.md`, `ITE_Intelligence_2.0_Architecture.md`

---

## Database State (as of 2026-04-16, BATON 061)

| Table | Rows | Notes |
|-------|------|-------|
| articles | 1,998 | +13 from BATON 058 QC rebuild (ART-1987–ART-1999) |
| questions (ITE) | 1,639 | 2018–2025; blueprint 100%; body_system fully normalized (BATON 060) |
| aafp_questions | 1,221 | blueprint + concept_tags 100%; correct_letter/correct_text/explanation merged in |
| qid_art_xref | 2,485 | all 8 years (2018–2025); rebuilt from critique ground truth BATON 058 |
| aafp_qid_art_xref | 864 | 643 unique questions linked (52.7%) |
| article_icd10 | 3,952 | rebuilt 2026-04-15 (−68 from synonym map variance) |
| question_icd10 | ~5,003 | 1,474/1,639 ITE questions (89.9%) — rebuilt 2026-04-15 |
| aafp_question_icd10 | 4,753 | relevance normalized; related cap applied |
| clinical_pathways | 3,971 | blueprint-based, both banks — rebuilt 2026-03-31 |
| article_citation_trend | 1,740 | longitudinal citation tracking + watch_list flag |
| article_currency | 1,998 | ✅ Intelligence 2.0 Layer 2 complete 2026-04-16 — all 1,998 articles currency-tracked |
| pubmed_pmid_cache | 344 | Layer 2 seed (citation_id → PMID) |
| icd10_vec | 2,219 | BLOB — OpenAI text-embedding-3-small (1536d) |
| article_icd10_vec | 1,757 | BLOB — rebuilt 2026-04-05 |
| question_icd10_vec | 2,747 | BLOB — rebuilt 2026-04-05 |
| article_vec | 1,998 | sqlite-vec virtual table — rebuilt 2026-04-15 |
| question_vec | 1,639 | sqlite-vec virtual table — rebuilt 2026-04-15 |
| aafp_question_vec | 1,221 | sqlite-vec virtual table |
| question_full_vec | 1,639 | BLOB — full question embedding with blueprint (BATON 056) |
| aafp_question_full_vec | 1,221 | BLOB — full AAFP embedding with blueprint+body_system+concept_tags (BATON 056) |
| intersection_centroid_vec | 123 | BLOB — 69 ITE + 54 AAFP blueprint×body_system centroids — rebuilt 2026-04-16 |

---

## Key Conventions

**Codon filename:** `Author_Year#@#ART-XXXX@#@.pdf`
The ART-ID embedded between `#@#` (start) and `@#@` (stop) codons is the durable DB link. Strategy 0 (regex parse of codon) is always the first matching strategy in every enricher.

**VC gate:** `key_data_files/session_hy_inserts_v7.json` (352 citations). Sole criterion for `right_click` vs `local_lite` tier. DB membership alone is not sufficient.

**Tier pipeline:**
```
PDF acquired → codon rename → VC gate check
                                  ↓ pass → VC_pass/ → pipeline → right_click/
                                  ↓ fail → VC_fail/ → pipeline → local_lite/
```

**Path convention (all Python scripts):**
```python
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH      = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"
```

**Body system taxonomy (post-2024 canonical):** Psychiatric/Behavioral, Sexual and Reproductive, Injuries/Musculoskeletal. Pre-2024 records with deprecated labels (Psychogenic, Reproductive:Female/Male, Musculoskeletal) preserved in body_system; body_system_merged holds canonical forward-mapped value.

**Locked rules:** Fix the data, not the code. Schema before script. Source data is protected. No de novo JS. QC after every integration. Git from Windows. `shutil.rmtree` is BANNED (use PowerShell Remove-Item).

---

## Intelligence 2.0 Layers

| Layer | Status | Table |
|-------|--------|-------|
| Layer 1 — ICD-10 diagnostic linkage | ✅ Built | article_icd10 (3,952) + question_icd10 (~5,003) + aafp_question_icd10 (4,753) |
| Layer 2 — PubMed currency | ✅ Built | article_currency (1,985 rows) — rebuilt 2026-04-07 |
| Layer 3 — Clinical pathways | ✅ Built | clinical_pathways (3,971 rows) — rebuilt 2026-03-31 |
| Layer 4 — Trends + alerts | ⬜ Partial | topic_trends built; pubmed_alerts planned |
| Citation trend tracking | ✅ Built | article_citation_trend (1,740 rows) |
| Vector embeddings | ✅ Built | icd10_vec (2,219) + article_icd10_vec (1,757) + question_icd10_vec (2,747) + intersection_centroid_vec (123) |

---

## ITE Score Analyzer (Module 3)

Per-resident longitudinal ITE score analysis pipeline.

**Key scripts:**
- `ite_parser.py` — PDF score report parser; extracts exam_year from PDF text
- `ite_analyzer_v3.py` — Cohort-level aggregator with body system normalization + AAFP query support + vector-based practice question matching
- `ite_report_builder_v2.js` — DOCX report generator; score bands, YoY section, LHF tables, MPS gap calculator
- `abfm_reference_2024.json` — 2024 ABFM national benchmarks (PGY1=414/±78, PGY2=462/±76, PGY3=494/±78, All=456/±84; MPS=380)

**Resident folder structure:**
```
resident_data/ITE_{lastname}_{firstname}/
    inputs/   ← ABFM score report PDFs
    outputs/  ← analysis_v2_{YYYY}.json, score_analysis_{YYYY}.json, DOCX report
```

---

## AAFP BRQ Pipeline

AAFP Board Review Questions (1,221 questions across 135 quizzes) scraped and fully enriched. Schema parallel to ITE questions — both corpora have body_system, blueprint, concept_tags, and ICD-10.

**Key finding:** 38 near-identical AAFP-ITE vignette pairs (dist 0.23–0.30) confirm likely direct question reuse between AAFP BRQ and ABFM ITE (BATON 020).

---

## Deferred Flags (active as of BATON 061)

| Flag | Status | Description |
|------|--------|-------------|
| DEFERRED-KNOWN-DRUGS-EXPANSION | ACTIVE | Identify offending drug names; decide fix approach |
| DEFERRED-QID-XREF-LIBRARY-GAPS | ACTIVE | 249 unmatched citations need article acquisition |
| DEFERRED-PGY-BENCHMARKS | UNBLOCKED | Implement benchmark comparison functionality |
| DEFERRED-PROGRAM-TREND | UNBLOCKED | Implement program-level trend analysis |
| DEFERRED-YOY-ROBUSTNESS | ACTIVE | Month-by-month rollup needs testing with dense temporal data |
| DEFERRED-RESIDENT-FOLDER-MIGRATION | ACTIVE | Investigate resident_data/ migration strategy to M5 |
| DEFERRED-SCHOLL-OLD-FORMAT | ACTIVE | 2022/2023 score reports in old ABFM taxonomy format |
| FLAG-33-NNN-RENAME | LOW-PRI | nnn_XXXX ART-ID rename scheme — designed, not implemented |

---

## Next Steps (BATON 061)

### Immediate
1. Implement PGY benchmark comparison — UNBLOCKED (DEFERRED-PGY-BENCHMARKS)
2. Implement program-level trend analysis — UNBLOCKED (DEFERRED-PROGRAM-TREND)
3. Add `--score-report` flag to batch runner for residents with score PDFs

### Short-term
4. **DEFERRED-KNOWN-DRUGS-EXPANSION** — identify offending drug names
5. **DEFERRED-QID-XREF-LIBRARY-GAPS** — 249 unmatched citations need acquisition

---

## Technology Stack

- **Python 3** — All new scripts. pdfplumber, sqlite3, anthropic SDK, sqlite-vec.
- **Node.js** — Existing JS scripts only (no new JS by convention). ite_report_builder_v2.js, build_faculty_pptx.js, etc.
- **SQLite** — Production DB with sqlite-vec extension for vector search.
- **Claude API** — Enrichment engine (Anthropic SDK). API key in env vars. claude-sonnet-4-6 for classification/enrichment; Haiku 4.5 for batch AAFP enrichment.
- **Next.js + Supabase + Sanity + Railway** — Module 5 web platform (scaffolded 2026-04-09).
- **Apify** — Citation crawler actor (`mpsch1~citation-crawler`, build 0.3.1) deployed for PlaywrightCrawler PDF discovery.

---

**Project Lead:** Michael Scholl, MD
**Last Reviewed:** 2026-04-16 (BATON 061, git bc462a3)
