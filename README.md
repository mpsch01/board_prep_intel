# ABFM ITE Intelligence System — board_prep_intel

**Last updated:** 2026-05-19 (BATON 076)
**Status:** Active development — Tier 2 walk-down + corpus-wide question-text & subscript-orphan cleanup complete. 8 atomic DB-write workflows applied (all backed up; BATON 075 invariants preserved on each). All question-fidelity metrics now at 0: zero empty choices, zero empty correct_text, zero embedded answer-choice blocks in stem, zero wandering-subscript orphans in either question_text or explanation. 4 deferred flags closed, 2 opened (A2 heuristic tuning + new corpus-qc layer checks A7/A8).
**Active BATON:** `BATON_active_076_20260519_tier2_apply_and_corpus_cleanup.md`
**Next ART-ID:** ART-2219 (corrected — recon found 10 articles ART-2208–ART-2218 already present)
**Git:** branch `claude/session-076-tier2-and-qid-followups` (V3.2 feature branch); main → `0b595f9` pre-session (BATON 075 merge commit, "Merge pull request #21"). Session commits: `de9a0f3` (BATON 076 housekeeping, 18 files) + hash-backfill commit. → `https://github.com/mpsch01/board_prep_intel` (private)

---

## Machine-Readable State

```json
{
  "project": "ABFM ITE Intelligence System",
  "description": "A queryable Family Medicine board exam knowledge base (1,640 ITE + 1,221 AAFP questions, 2018–2025) linked to a clinical guideline library (2,206 articles, 1,571 PDFs) via a structured SQLite pipeline.",
  "baton": "BATON_active_076_20260519_tier2_apply_and_corpus_cleanup.md",
  "baton_description": "Tier 2 walk-down + corpus-wide question-text and subscript-orphan cleanup. 8 distinct DB-write workflows: A3 choices_empty re-extraction (42 QIDs); A2 truncation-candidate verification (23 ALREADY_FULL); QID-2024-0067 enrichment backfill via Sonnet 4.6; blueprint+body_system verified; 8th UMBRELLA review (+1 honest signal); question_text contamination cleanup (42 QIDs); wandering-subscript orphan corpus-wide cleanup (206 questions, 239 orphans removed, 176 medical-knowledge recoveries via 14 rules: A1c/B12/FEV1/T4/H2-blocker/α1-/H2O/S3 gallop/HCO3/PaO2/PaCO2/Lp-PLA2/phospholipase A2). Final fidelity metrics all 0 (was 47+117+42+42+41). 4 deferred flags CLOSED, 2 NEW (A2 heuristic tuning + A7/A8 corpus-qc layer checks).",
  "git_hash": "de9a0f3",
  "git_branch": "claude/session-076-tier2-and-qid-followups (V3.2 feature branch from main 0b595f9)",
  "github_remote": "https://github.com/mpsch01/board_prep_intel",
  "last_updated": "2026-05-19",
  "next_art_id": "ART-2219",
  "vc_gate_citations": 352,
  "database": {
    "file": "00_database/db/ite_intelligence.db",
    "articles": 2206,
    "questions_ite": 1640,
    "questions_aafp": 1221,
    "qid_art_xref": 2710,
    "aafp_qid_art_xref": 864,
    "article_icd10": 4959,
    "question_icd10": 5774,
    "aafp_question_icd10": 4753,
    "clinical_pathways": 4959,
    "pubmed_pmid_cache": 344,
    "icd10_vec": 2219,
    "article_icd10_vec": 1757,
    "question_icd10_vec": 2747,
    "article_vec": 2206,
    "question_vec_note": "1639 — sqlite-vec virtual table; not rebuilt for QID-2024-0067 yet",
    "question_vec": 1639,
    "aafp_question_vec": 1221,
    "intersection_centroid_vec": 158,
    "article_currency": 2206
  },
  "pdfs": {
    "vc_fail": 1056,
    "vc_pass": 309,
    "local_lite": 117,
    "right_click": 58,
    "aafp": 15,
    "ite_exams": 16,
    "total": 1571,
    "_note": "ite_total active: 1,540 (excluding ite_exams + AAFP). Post-BATON 067 counts after worktree merge + 72 AFP gap closure − 48 dupes − 79 corrupts."
  },
  "scripts": {
    "m1_build_py": 8,
    "m1_maintain_py": 38,
    "m2_py": 80,
    "m2_py_note": "+5 BATON 076: reextract_a3_choices.py, reextract_a2_explanations.py, clean_question_text_contamination.py, render_partial_4of5_docx.py, fix_subscript_orphans.py",
    "m2_js": 6,
    "m3_py": 55,
    "m3_js": 4,
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
- `db/ite_intelligence.db` — Production SQLite database (2,206 articles, 1,639 ITE questions, 1,221 AAFP questions)
- `readable_db_files/` — CSV exports, human-readable snapshots
- `logs/` — Pipeline run logs
- `schemas/` — clinical_synonym_map.json, icd10_mcp_lookup.json, ite-data-context-skill/

### 01_module.1_warehouse/
PDF library (4 tiers, 1,540 ITE + 15 AAFP + 16 exam PDFs) + pipeline build and maintenance scripts.
- `citation_files/ITE/VC_fail/` — 1,056 PDFs: bulk; lowest citation priority (+66 net since BATON 066)
- `citation_files/ITE/VC_pass/` — 309 PDFs: codon-named, VC-cited, awaiting full pipeline (+93 net since BATON 066)
- `citation_files/ITE/local_lite/` — 117 PDFs: VC_fail + fully enriched (pipeline complete)
- `citation_files/ITE/right_click/` — 58 PDFs: VC_pass + fully enriched (highest-value tier)
- `citation_files/AAFP/` — 15 AAFP citation PDFs (recovered 2026-04-05)
- `citation_files/_dupe_archive/` — 0 PDFs (all 48 BATON 067 dupes consolidated and deleted)
- `citation_files/ite_exams/` — 16 raw PDFs: YYYY_MC.pdf + YYYY_critique.pdf (2018–2025)
- `practice_questions/` — 42 Q&A deliverables: 8 ITE DOCX + 8 ITE XLSX + 13 AAFP DOCX + 13 AAFP XLSX (gitignored; regenerable from DB)
- `build/` — 8 scripts: self-contained full rebuild sequence
- `maintain/` — 38 scripts: recurring DB population and maintenance operations (+9 net BATON 066+067: 8 BATON 066 merged + aafp_targeted_downloader.py NEW BATON 067; aafp_fill_gaps.py MODIFIED BATON 067)
- `scripts/aafp_brq_scraper.py` — scraper at scripts/ root (Windows-only)

### 02_module.2_processor/
Extraction, enrichment, and DOCX build pipeline.
- `scripts/` — 75 Python + 6 JS; includes `core/` (4py), `engines/` (7py), `utils/` (6py) packages + `source/` (transcripts, blueprint xlsx), `outputs/` (staging JSONs), `prompts/` (templates)

### 03_module.3_analyst/
ICD-10 tagging, clinical pathways, trend analysis, score analysis, body system QC/normalization, AAFP-ITE reuse investigation.
- `scripts/` — 55 Python + 4 JS (ite_analyzer_v3.py, ite_parser.py, ite_report_builder_v2.js, build_article_currency.py, body-system-qc pipeline, normalization scripts, build_custom_question_set.py, build_exam_series.py, etc.)
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

## Database State (as of 2026-05-07, BATON 067)

| Table | Rows | Notes |
|-------|------|-------|
| articles | 2,206 | +13 BATON 058 (ART-1987–ART-1999); +208 BATON 065 (ART-2000–ART-2218) via acquire_missing_citations.py |
| questions (ITE) | 1,639 | 2018–2025; blueprint 100%; body_system fully normalized (BATON 060) |
| aafp_questions | 1,221 | blueprint + concept_tags 100%; correct_letter/correct_text/explanation merged in |
| qid_art_xref | 2,710 | all 8 years (2018–2025); rebuilt BATON 058; +225 pairs BATON 065 |
| aafp_qid_art_xref | 864 | 643 unique questions linked (52.7%) |
| article_icd10 | 4,959 | ↑ from 3,952 (pre-existing Windows PC enrichment, confirmed BATON 062) |
| question_icd10 | 5,774 | rebuilt — enrichment via ICD-10 propagation pipeline |
| aafp_question_icd10 | 4,753 | relevance normalized; related cap applied |
| clinical_pathways | 4,959 | ↑ from 3,971 (pre-existing Windows PC enrichment, confirmed BATON 062) |
| article_citation_trend | 1,740 | longitudinal citation tracking + watch_list flag |
| article_currency | 2,206 | ✅ Intelligence 2.0 Layer 2 complete — all articles currency-tracked |
| pubmed_pmid_cache | 344 | Layer 2 seed (citation_id → PMID) |
| icd10_vec | 2,219 | BLOB — OpenAI text-embedding-3-small (1536d) |
| article_icd10_vec | 1,757 | BLOB — rebuilt 2026-04-05 |
| question_icd10_vec | 2,747 | BLOB — rebuilt 2026-04-05 |
| article_vec | 2,206 | sqlite-vec virtual table |
| question_vec | 1,639 | sqlite-vec virtual table |
| aafp_question_vec | 1,221 | sqlite-vec virtual table |
| question_full_vec | 1,639 | BLOB — full question embedding with blueprint (BATON 056) |
| aafp_question_full_vec | 1,221 | BLOB — full AAFP embedding with blueprint+body_system+concept_tags (BATON 056) |
| intersection_centroid_vec | 158 | BLOB — blueprint×body_system centroids — ↑ from 123 (BATON 062) |

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
| Layer 1 — ICD-10 diagnostic linkage | ✅ Built | article_icd10 (4,959) + question_icd10 (5,774) + aafp_question_icd10 (4,753) |
| Layer 2 — PubMed currency | ✅ Built | article_currency (2,206 rows) — complete 2026-04-16; +208 new articles BATON 065 |
| Layer 3 — Clinical pathways | ✅ Built | clinical_pathways (4,959 rows) — ↑ from 3,971 |
| Layer 4 — Trends + alerts | ⬜ Partial | topic_trends built; pubmed_alerts planned |
| Citation trend tracking | ✅ Built | article_citation_trend (1,740 rows) |
| Vector embeddings | ✅ Built | icd10_vec (2,219) + article_icd10_vec (1,757) + question_icd10_vec (2,747) + intersection_centroid_vec (158) |

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

## Deferred Flags (active as of BATON 068)

| Flag | Status | Description |
|------|--------|-------------|
| **NEW: DEFERRED-CORPUS-QC-LAYERS-AB-D** | ACTIVE | Build Layer A + B + D + coordinator + 4 subagent prompts for corpus-integrity-qc |
| **NEW: DEFERRED-LAYER-C-CACHE-REBUILD** | ACTIVE | 1,797 Tier-1 cache-rebuild SQL fixes pending Layer D |
| **NEW: DEFERRED-ORPHAN-XREF-QID-2024-0067** | ACTIVE | QID-2024-0067/ART-2073 references non-existent QID in questions table |
| **NEW: DEFERRED-MAC-PDF-SYNC** | ACTIVE | Mac PDF library lags Windows by 569 files (gitignored) |
| **NEW: DEFERRED-LOCKED-RULE-8-UPDATE** | LOW-PRI | Rule 8 (Git via Desktop Commander) needs broadening for Mac/Claude Code |
| MERGE-WORKTREE-TO-MAIN | RESOLVED | (BATON 067) |
| DEFERRED-AFP-GAP | RESOLVED | (BATON 067) |
| DEFERRED-CROSS-TIER-DEDUPE | ACTIVE | 89 ART-IDs in both VC_fail and VC_pass need consolidation |
| DEFERRED-AFP-DB-DATA-QC | ACTIVE | 6 articles with malformed clean_ref / junk title |
| DEFERRED-AAFP-HTTP-500-RETRY | ACTIVE | 5 vintage AFP articles blocked by AAFP server outage |
| DEFERRED-JAMA-NEJM-PDF-HARVEST | RESOLVED | (BATON 066) |
| DEFERRED-KNOWN-DRUGS-EXPANSION | ACTIVE | Identify offending drug names |
| DEFERRED-QID-XREF-LIBRARY-GAPS | ACTIVE | ~801 articles missing PDFs |
| DEFERRED-PGY-BENCHMARKS | UNBLOCKED | Implement benchmark comparison |
| DEFERRED-PROGRAM-TREND | UNBLOCKED | Implement program-level trend analysis |
| DEFERRED-YOY-ROBUSTNESS | ACTIVE | Month-by-month rollup edge cases |
| DEFERRED-RESIDENT-FOLDER-MIGRATION | ACTIVE | Investigate resident_data/ migration to M5 |
| DEFERRED-SCHOLL-OLD-FORMAT | ACTIVE | 2022/2023 score reports in old ABFM taxonomy |
| FLAG-33-NNN-RENAME | LOW-PRI | Designed, not implemented |

---

## Next Steps (BATON 069)

### Immediate (next session)
1. **Continue corpus-integrity-qc build** — Layer B (citation linkage, multi-ref-aware) — the layer that actually fixes the ~900 false-positive bug. Then Layer A (text fidelity), then coordinator + tiered fix generator (Layer D), then 4 subagent prompts.
2. **Investigate ORPHAN_XREF (QID-2024-0067 / ART-2073, exam_year 2024)** — qid doesn't exist in questions table; likely 5-minute fix once eyeballed.

### Short-term (this week)
3. **Apply Tier-1 Layer C cache rebuilds** — 1,797 auto-safe SQL UPDATEs once Layer D ships.
4. **Mac PDF sync** — pull 569 missing PDFs from Windows/gdrive.
5. **Re-run all 7 resident analyses** — still carrying from BATON 065+066+067.
6. **Cross-tier codon dedupe** — 89 ART-IDs in both VC_fail and VC_pass (carry from BATON 067).
7. **AFP DB data QC** — repair 6 articles with malformed clean_ref / junk title (carry from BATON 067).

### Medium-term
8. AAFP BRQ extension of corpus-integrity-qc (v2).
9. Continue 801-article gap closure by source_type buckets.
10. Apply NEJM DevTools pattern to 144 unpaywall Cloudflare-blocked URLs.

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
**Last Reviewed:** 2026-05-15 (BATON 069, git d85ef22 housekeeping commit; PROJECT_OVERHAUL fossil cleanup; renamed `project_overhaul_state.md` → `project_session_log.md`; no functional changes)
