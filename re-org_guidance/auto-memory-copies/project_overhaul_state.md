---
name: project_overhaul_state
description: PROJECT_OVERHAUL current state - 4-module rebuild in progress, BATON 005, git initialized, all M2 scripts de-hardcoded
type: project
---

**Project:** ABFM Knowledge Base & Extraction Pipeline (`00_#PROJECT_OVERHAUL/` in claude_knowledge directory on user's Windows desktop)

**Current Phase:** PROJECT_OVERHAUL — 4-module rebuild. Structural migration largely complete. Remaining work: TEMP folder audits, articles table gap-fill, Intelligence 2.0 Layer 2.

**Active BATON:** 005 (`BATON_active_005_20260324_pathfixes.md`)

**Sessions Summary (March 21–24, 2026):**
- 4-module architecture established: M1 Warehouse, M2 Processor, M3 Analyst, M4 Sandbox
- DB expanded: 2018-2019 integration added 440 questions, 389 new articles (ART-1549–ART-1937)
- All 4 keyword columns backfilled for 2018-2019 (1,629/1,629 = 100%)
- M1 scripts organized: `build/` (6) + `maintain/` (11)
- M2 scripts fully migrated: 41 Python + JS scripts, all paths dynamic (commit `ed85b06`)
- M2/source/ layer created: content outline DOCX + 50 AAFP transcripts
- Module F (VC outline pipeline) + keyword library (A-G) migrated from TEMP_04
- Git initialized: `main` branch, latest commit `94fdc6a`

**Key Numbers (as of 2026-03-24):**
- DB: 1,936 articles, 1,629 questions (2018–2025), 2,722 question-ref pairs
- article_icd10: 3,855 rows | clinical_pathways: 4,528 rows | qid_art_xref: 1,818 rows
- PDFs: 404 in library (4 tiers in M1 Warehouse)
- Intelligence 2.0: Layers 1 (ICD-10), 3 (Pathways), 4a (Trends) complete. Layer 2 (PubMed) not started
- M2/scripts: 41 scripts (all Python/JS paths dynamic; .bat/.ps1/.reg deferred)

**Active Flags:** 33 (ART-ID rename), 30 (encrypted PDFs), 15 (merged-only run), QID format mismatch, Layer 2 + 4b not built, 232 orphaned question_ref_pairs, M3 duplicates pending delete

**Why:** The project extends beyond exam prep into clinical decision support. The DB is the source of truth. Derivatives (JSONs, DOCXs) are disposable. Pre-compute everything deterministic at ingest.

**How to apply:** Always read the active BATON first — it has the current DB state, deferred flags, and next steps. `_index.md` is the ground-truth directory map. BATON supersedes everything else if there's a conflict.
