# REPO MAP — board_prep_intel
**What this is:** Current-state architectural overview. High-level only — not a file tree (see `_index.md`).
**Last Updated:** 2026-04-05 (BATON 043)
**Root:** `C:\Users\mpsch\Desktop\board_prep_intel\` (Option B complete — flat since 2026-04-04)
**Git:** `main` → `https://github.com/mpsch01/board_prep_intel` (private) | latest: `fbf6b00`

---

## What This System Is

A queryable Family Medicine board exam knowledge base. Two data banks — **1,629 ITE questions** (ABFM, 2018–2025) and **1,221 AAFP BRQ questions** — linked to a clinical guideline library of **1,985 articles** and **~414 PDFs** via a structured SQLite pipeline. Used for resident study tools, ITE score analysis, and clinical decision support development.

---

## Module Status

| Module | Path | Role | Scripts | Status |
|--------|------|------|---------|--------|
| **M1 Warehouse** | `01_module.1_warehouse/` | Store PDFs; build/maintain DB | 6 build + 23 maintain + 1 scraper | ✅ Stable — PDF recovery complete |
| **M2 Processor** | `02_module.2_processor/` | Extract, enrich, tag, build DOCXs | 75 py + 6 JS in scripts/; core/engines/utils packages | ✅ Stable — 14 defects fixed BATON 038 |
| **M3 Analyst** | `03_module.3_analyst/` | Score analysis, ICD-10, pathways, Q&A deliverables | 13 py + 2 JS | ✅ Stable |
| **M4 Sandbox** | `04_module.4_sandbox/` | Experiments, agent prototypes | ad hoc | 🔵 Idle |
| **DB** | `00_database/db/ite_intelligence.db` | Source of truth | — | ✅ Current |

---

## DB State (2026-04-05)

| Table | Rows | Notes |
|-------|------|-------|
| articles | **1,985** | ART-0001–ART-1986; next = ART-1987 |
| questions (ITE) | **1,629** | 2018–2025; blueprint 100%; subcategory DROPPED |
| aafp_questions | **1,221** | blueprint 100%; flattened schema |
| article_icd10 | 4,020 | ITE chain + AAFP backfill; rebuilt 2026-04-05 |
| question_icd10 | 5,284 | 92.8% ITE coverage |
| aafp_question_icd10 | 4,753 | relevance normalized |
| clinical_pathways | 4,020 | blueprint-based, both banks |
| article_citation_trend | 1,740 | longitudinal tracking |
| pubmed_pmid_cache | 344 | Layer 2 seed (PMIDs) |
| icd10_vec | 2,219 | OpenAI text-embedding-3-small (1536d) |
| article_icd10_vec | 1,757 | rebuilt 2026-04-05 |
| question_icd10_vec | 2,747 | rebuilt 2026-04-05 |
| question_vec | 1,629 | sqlite-vec; 100% ITE |
| aafp_question_vec | 1,221 | sqlite-vec; 100% AAFP |

---

## Data Pipeline

```
INPUTS
  ITE exam PDFs (ite_exams/)        →  M2 extraction scripts
  Guideline PDFs (citation_files/)  →  M2 enricher + DOCX builders
  AAFP BRQ scraped data             →  M2 AAFP pipeline
  Score report PDFs                 →  M3 parser
        ↓
  ite_intelligence.db  ←  source of truth for everything downstream
        ↓
OUTPUTS
  practice_questions/   (42 Q&A DOCX + XLSX — regenerable)
  enriched DOCX library (_archive_/docx_guideline_library/ — 1,518 files)
  ITE score reports     (M3/reports/)
  Intelligence layers   (00_database/readable_db_files/)
```

### Key Pipeline Sequences

**New guideline PDF → enriched DOCX:**
`codon rename` → `ite_intelligence_enricher.py` (Strategy 0) → `synthesize.js` → `build_summary.js` → `right_click/` or `local_lite/`

**New ITE exam year:**
`01_ite_extractor.py --year` → `02_ite_categorizer.py` → `03_ite_merger.py` → `preprocess_concept_tags.py` → `compute_embeddings.py --new-only`

**New article batch → DB:**
PDFs codon-named → `VC_fail/` → `backfill_new_article_metadata.py --art-id-min XXXX`

**Score analysis:**
Score PDF → `ite_parser.py` → `ite_analyzer_v3.py` → `ite_report_builder_v2.js` → DOCX report

---

## PDF Warehouse Tiers

| Tier | Folder | Meaning | Count |
|------|--------|---------|-------|
| `VC_fail` | `citation_files/ITE/VC_fail/` | Failed VC gate; awaiting enrichment | 623 |
| `VC_pass` | `citation_files/ITE/VC_pass/` | Passed VC gate; awaiting enrichment | 168 |
| `local_lite` | `citation_files/ITE/local_lite/` | VC_fail + fully enriched | 117 |
| `right_click` | `citation_files/ITE/right_click/` | VC_pass + fully enriched (**priority**) | 58 |

**VC Gate:** `key_data_files/session_hy_inserts_v7.json` — 352 citations — sole criterion for right_click tier.
**Codon filename format:** `Author_Year#@#ART-XXXX@#@.pdf` — ART-ID embedded between start/stop codons.
**_dupe_archive:** 14 duplicate PDFs quarantined; total active across 4 tiers = 966.

---

## Intelligence 2.0 Layers

| Layer | Table | Status |
|-------|-------|--------|
| Layer 1 — ICD-10 crosswalk | `article_icd10`, `question_icd10`, `aafp_question_icd10` | ✅ Complete |
| Layer 2 — Article currency (PubMed) | `pubmed_pmid_cache` (344 PMIDs) | 🟡 Seed ready; `article_currency` table not yet built |
| Layer 3 — Clinical pathways | `clinical_pathways` (4,020 rows) | ✅ Complete |
| Layer 4 — Topic trends | `article_citation_trend` (1,740 rows) | ✅ Built; `update_citation_trends.py` pending (DEFERRED-B) |

---

## Active Deferred Flags

| Flag | Description | Priority |
|------|-------------|----------|
| **DEFERRED-A** | 37 manual PDFs (34 subscription + 3 Cochrane) → download → codon rename → `VC_fail/` → `backfill_new_article_metadata.py --art-id-min 1938` | 🔴 HIGH |
| DEFERRED-B | `update_citation_trends.py` — run after DEFERRED-A backfill | 🟡 MEDIUM |
| DEFERRED-C | AAFP vs ITE trend comparison | 🟡 MEDIUM |
| DEFERRED-D | 229 citation gap articles (88 AFP batch-downloadable) | 🟡 MEDIUM |
| DEFERRED-E | Interactive vector dashboard | 🟢 LOW |
| DEFERRED-F | Intelligence 2.0 Layer 2: `article_currency` via PubMed (344 PMIDs cached) | 🟡 MEDIUM |

---

## Key Files (most important to know)

| File | Why It Matters |
|------|---------------|
| `BATON_active_043_20260405_pdf_recovery_skills.md` | Active session handoff — read first every session |
| `CLAUDE.md` | Project memory: terminology, locked rules, active state, next steps |
| `00_database/db/ite_intelligence.db` | Source of truth — never disposable |
| `key_data_files/session_hy_inserts_v7.json` | VC gate — 352 citations — sole right_click criterion |
| `01_module.1_warehouse/scripts/maintain/backfill_new_article_metadata.py` | Primary article onboarding script |
| `02_module.2_processor/scripts/ite_intelligence_enricher.py` | Primary v4 enricher (Strategy 0 first) |
| `03_module.3_analyst/scripts/word_doc_defaults.py` | Import in ALL python-docx scripts |
| `00_database/schemas/ite-data-context-skill/` | ITE domain skill for DB queries |

---

## What Is and Isn't Git-Tracked

**Tracked:** all `.py`, `.js`, `.json`, `.md`, `.bat`, `.ps1`, `.txt` — code and docs.
**Not tracked:** `*.db`, `*.pdf`, `extracted_json/`, `resident_data/`, `__pycache__/`, `outputs/` — binaries and derived data stay local / Google Drive.

---

## Deprecation Note on _index.md

`_index.md` is the ground-truth file tree but has drifted as of this session (still lists deleted deprecated scripts, old Git remote, old BATON). A sweep of `_index.md` is recommended before the next structural change.
