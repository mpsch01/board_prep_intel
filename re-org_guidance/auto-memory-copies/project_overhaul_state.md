---
name: project_overhaul_state
description: PROJECT_OVERHAUL current state - 4-module rebuild in progress, BATON 006, TEMP_05 migrated, extracted_json/ created
type: project
---

**Project:** ABFM Knowledge Base & Extraction Pipeline (`00_#PROJECT_OVERHAUL/` in claude_knowledge directory on user's Windows desktop)

**Current Phase:** PROJECT_OVERHAUL — 4-module rebuild. Structural migration largely complete. Remaining work: TEMP_06/07/08 folder audits, articles table gap-fill (389 new 2018-2019 articles missing source_type/categories/tier), Intelligence 2.0 Layer 2.

**Active BATON:** 006 (`BATON_active_006_20260324_temp05.md`)

**Sessions Summary (March 21–24, 2026):**
- 4-module architecture established: M1 Warehouse, M2 Processor, M3 Analyst, M4 Sandbox
- DB expanded: 2018-2019 integration added 440 questions, 389 new articles (ART-1549–ART-1937)
- All 4 keyword columns backfilled for 2018-2019 (1,629/1,629 = 100%)
- M1 scripts organized: `build/` (6) + `maintain/` (13)
- M2 scripts fully migrated: 45 Python + JS scripts + 1 config JSON, all paths dynamic
- M2/source/ layer: content outline DOCX + 50 AAFP transcripts
- Module F (VC outline pipeline) + keyword library (A-G) migrated from TEMP_04
- TEMP_05 (ITE refs crosswalk pipeline) fully migrated: 5 scripts, 1 config JSON, 1 crosswalk CSV
- `extracted_json/` root folder created: 242 flat JSONs + 5 batch subdir placeholders (NOT git-tracked)
- Git initialized: `main` branch, latest commit `94fdc6a` (next commit staged but blocked by index.lock)

**Key Numbers (as of 2026-03-24, BATON 006):**
- DB: 1,936 articles, 1,629 questions (2018–2025), 2,722 question-ref pairs
- article_icd10: 3,855 rows | clinical_pathways: 4,528 rows | qid_art_xref: 1,818 rows
- PDFs: 404 in library (4 tiers in M1 Warehouse)
- Intelligence 2.0: Layers 1 (ICD-10), 3 (Pathways), 4a (Trends) complete. Layer 2 (PubMed) not started
- M1/maintain: 13 scripts | M1/build: 6 scripts | M2/scripts: 45 scripts + 1 config JSON | M3/scripts: 5 (+2 pending delete)

**Script Location Rules (locked):**
- All JS → M2/scripts (no exceptions, no de novo JS)
- Python M2/scripts path: `SCRIPT_DIR.parent.parent` = PROJECT_ROOT
- Python M1/maintain path: `SCRIPT_DIR.parent.parent.parent` = PROJECT_ROOT
- JS path: `path.resolve(__dirname, "../../")` = PROJECT_ROOT

**Active Flags:** 33 (embeddings deferred), 30 (encrypted PDFs), BATCH_DIRS sorting, M3 duplicates pending delete, git index.lock blocking commit, TEMP_05 Windows cleanup pending, TEMP_06/07/08 not yet audited

**Why:** The project extends beyond exam prep into clinical decision support. The DB is the source of truth. Derivatives (JSONs, DOCXs) are disposable. Pre-compute everything deterministic at ingest.

**How to apply:** Always read the active BATON first — it has the current DB state, deferred flags, and next steps. `_index.md` is the ground-truth directory map. BATON supersedes everything else if there's a conflict.
