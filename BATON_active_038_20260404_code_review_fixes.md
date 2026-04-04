# BATON 038 — Third-Party Code Review Fixes
**Date:** 2026-04-04
**Session:** Code review received; 14 confirmed defects fixed across 4 severity levels
**Status:** GIT-COMMITTED ✓ | Option B (flatten + rename) COMPLETE ✓ | DEFERRED-A still priority #1
**Replaces:** BATON_active_037_20260404_practice_questions_deliverables_m1_restructure.md

---

## What Was Done This Session

### 1. Third-Party Code Review

A full repository scan was performed externally (Claude Sonnet 4.6, GitHub Actions runner).
Original report: 23 defects across 4 severity levels.

**After triage with Mikey:**
- MEDIUM-5 (keyword pipeline tier labels) → retired/dead code. Struck from fix list.
- LOW-4 (ite_analyzer_v2.py deprecation header) → already present and complete. No change needed.
- Revised live defect count: **14 fixed** (4 critical, 4 high, 4 medium, 2 low)

---

### 2. CRITICAL Fixes

**C1 · `preprocess_concept_tags.py`** — Path + model ID (M1/scripts/maintain/)
- `PROJECT_ROOT = SCRIPT_DIR.parent.parent` → `SCRIPT_DIR.parent.parent.parent` (3 hops — 1 was pointing to M1 module dir, not project root)
- `MODEL = "claude-sonnet-4-6"` → `"claude-sonnet-4-20250514"` (invalid model ID)
- Docstring PATH NOTE updated to reflect actual M1/scripts/maintain/ location

**C2 · `batch_db_extract.py`** — Hop count + LOG_DIR + JSON_DIR (M2/scripts/)
- `BASE_DIR = Path(__file__).resolve().parent.parent` → `.parent.parent.parent` (lands at project root, not module dir)
- `LOG_DIR = BASE_DIR / "logs"` → `BASE_DIR / "00_database" / "logs"`
- `JSON_DIR = BASE_DIR.parent.parent / "clinical_guidelines" / ...` → `BASE_DIR / "extracted_json"` (was pointing 2 levels above project root)

**C3 · `db_guided_extractor.py`** — Hop count + schema drift (M2/scripts/)
- Same `BASE_DIR` hop count fix as C2
- `LOG_DIR` fixed to `00_database/logs/`
- Removed `q.subcategory` from SELECT and `"subcategory"` from `cols` list (column was dropped from questions table per BATON 024)

**C4 · `build_icd10_tags.py`** — SCHEMAS_DIR + OUTPUT_DIR (M3/scripts/)
- NOTE: DB_PATH was already correct (2 `..` hops) — reviewer's count was off. Only directory pointers needed fixing.
- `SCHEMAS_DIR`: `../schemas` → `../../00_database/schemas` (was pointing to non-existent `03_module.3_analyst/schemas/`)
- `OUTPUT_DIR`: `../readable_db_files` → `../../00_database/readable_db_files` (same mismatch)

---

### 3. HIGH Fixes

**H1 · `extract_ite_year.py`** — Filename pattern (already flagged in BATON 037 Pending)
- Docstring updated: `{YEAR}_ITE_Questions.pdf` / `{YEAR}_ITE_Critique.pdf` → `{YEAR}_MC.pdf` / `{YEAR}_critique.pdf`
- Executed code (lines 312–313) updated to match

**H2 · `audit_engine_type_changes.py`** — Missing `exists()` guard
- Added `if not path.exists(): continue` before `os.listdir(path)` in tier folder scan loop
- Matches the guard already present in `backfill_new_article_metadata.py`

**H3 · `build_crosswalk_index.py`** — Wrong output paths + non-existent PDF_DIR
- `OUT_JSON` / `OUT_REPORT`: was writing to `M1/scripts/` → now `ROOT / "00_database" / "crosswalk" /` (matches tracked location)
- Replaced `PDF_DIR = ROOT / "clinical_guidelines" / ...` (external, non-repo path that crashed at runtime) with `CITATION_ITE` + `TIER_DIRS` multi-tier scan
- New scan iterates all 4 tiers (`VC_fail`, `local_lite`, `VC_pass`, `right_click`) with `exists()` guard per tier

**H4 · `classify_ite_year.py`** — Deprecated XGBoost parameter
- Removed `use_label_encoder=False` from `XGBClassifier(...)` (removed in XGBoost 1.6.0, raises `TypeError` in all current environments)

---

### 4. MEDIUM Fixes

**M1 · `ite_intelligence_enricher_batch.py`** — JSON_DIR default
- `JSON_DIR = BASE_DIR.parent.parent / "clinical_guidelines" / "03_enriched_JSON"` → `BASE_DIR / "extracted_json"`
- Was pointing 2 levels above project root. Now defaults to project-internal `extracted_json/` (still overrideable via `--dir`)

**M2 · `rebuild_ite_db_v2.py`** — LOG_DIR non-standard location
- `LOG_DIR = BASE_DIR / "logs"` → `PROJECT_ROOT / "00_database" / "logs"`
- Was creating `M1/scripts/logs/` — now writes to the canonical log location

**M3 · `build_clinical_pathways.py`** — OUTPUT_DIR wrong module location
- `OUTPUT_DIR = os.path.join(SCRIPT_DIR, "..", "readable_db_files")` → `os.path.join(SCRIPT_DIR, "..", "..", "..", "00_database", "readable_db_files")`
- Was writing to `M1/scripts/readable_db_files/`; downstream scripts reading from `00_database/readable_db_files/` would miss the output

**M4 · `backfill_new_article_metadata.py`** — VC gate cross-check (DEFERRED-A risk)
- Added `"vc_gate_mismatch": 0` counter to stats dict
- Added VC gate re-validation block after tier assignment from warehouse scan:
  - If article lands in `right_click/` or `VC_pass/` from physical folder scan, verify against `session_hy_inserts_v7.json`
  - Mismatch → prints warning + increments counter (does NOT auto-downgrade tier — intentional; physical folder placement is still trusted, but mismatches are surfaced for manual review)
  - Relevant for DEFERRED-A: any of the 37 new PDFs accidentally placed in the wrong tier will be caught at runtime

---

### 5. LOW Fixes

**L1 · `build_topic_trends.py`** — `\p` invalid escape in docstring
- `"C:\path\to\output"` → `"C:\\path\\to\\output"` (SyntaxWarning in Python 3.12+)

**L2 · `clear_and_reenrich.py`** — `\c` invalid escape in docstring
- `python scripts\clear_and_reenrich.py` → `python scripts\\clear_and_reenrich.py`

**L3 · `ite_analyzer_v2.py`** — Already has complete deprecation header (no change needed)
- Header documents: subcategory crash, hardcoded year, AAFP not connected, replaced by v3
- Script count in M3 should note 1 deprecated (now reflected in BATON script counts below)

---

### 6. One Reviewer Finding That Was Wrong

The reviewer flagged `build_icd10_tags.py` DB_PATH as "3 hops above project root." On inspection, DB_PATH already used 2 `..` hops from `03_module.3_analyst/scripts/`, which is correct. Only SCHEMAS_DIR and OUTPUT_DIR were wrong (pointed to non-existent M3-internal folders). DB_PATH untouched.

---

## DB State (unchanged this session)

No DB writes. All tables same as BATON 037/038.

| Table | Rows |
|-------|------|
| articles | 1,985 |
| questions (ITE) | 1,629 |
| aafp_questions | 1,221 |
| article_icd10 | 4,137 |
| question_icd10 | 5,284 |
| clinical_pathways | 4,020 |
| Next ART-ID | ART-1987 |

---

## Script Counts (updated)

| Location | Python | JS | Notes |
|----------|--------|----|-------|
| M1 build/ | 9 | 0 | 3 deprecated headers applied |
| M1 maintain/ | 17 | 0 | 2 deprecated headers applied |
| M2 scripts/ | ~64 | 6 | |
| M3 scripts/ | 14 | 2 | ite_analyzer_v2.py = deprecated (complete header); 13 active |

---

## Deferred Flags (unchanged)

| Flag | Description | Priority |
|------|-------------|----------|
| DEFERRED-A | 37 manual PDFs remaining: 34 subscription + 3 Cochrane → codon rename → VC_fail | **HIGH** |
| DEFERRED-B | `update_citation_trends.py` after backfill | MEDIUM |
| DEFERRED-C | AAFP vs ITE trend comparison | MEDIUM |
| DEFERRED-D | 229 citation gap articles (88 AFP batch-downloadable) | MEDIUM |
| DEFERRED-E | Interactive vector dashboard | LOW |
| DEFERRED-F | Intelligence 2.0 Layer 2 (`article_currency` via PubMed, 344 PMIDs cached) | MEDIUM |

---

## Completed This Session (late addition)

- **Option B** ✓ — `00_#PROJECT_OVERHAUL/` flattened; modules now live directly at `board_prep_intel/` root on Desktop. GitHub repo renamed to `board_prep_intel`. Remote URL updated. `option_b_patch.py` executed: CLAUDE.md, _index.md, auto-memory-copies/project_overhaul_state.md all patched to reflect new paths/naming.

---

## Pending (next session)

1. **Windows cleanup** — Delete 5 deprecated script originals from M1 build/ and maintain/; delete `claude_knowledge/` folder from Desktop (old container, superseded)
2. **DEFERRED-A** — 37 manual PDFs; once assembled → `backfill_new_article_metadata.py --art-id-min 1938`
3. **DEFERRED-B** — `update_citation_trends.py` after backfill
4. **DEFERRED-F** — Intelligence 2.0 Layer 2: `article_currency` via PubMed
5. **Schema docs** — Update `00_database/schemas/ite-data-context-skill/references/tables/` (questions.md still lists subcategory; articles.md has old tier labels and stale row counts)

---

## Files Changed This Session

| File | Action |
|------|--------|
| `01_module.1_warehouse/scripts/maintain/preprocess_concept_tags.py` | MODIFIED — hop count 2→3, model ID fixed, docstring updated |
| `02_module.2_processor/scripts/batch_db_extract.py` | MODIFIED — hop count 2→3, LOG_DIR + JSON_DIR fixed |
| `02_module.2_processor/scripts/db_guided_extractor.py` | MODIFIED — hop count 2→3, LOG_DIR fixed, subcategory removed from SELECT |
| `03_module.3_analyst/scripts/build_icd10_tags.py` | MODIFIED — SCHEMAS_DIR + OUTPUT_DIR fixed to 00_database/ |
| `02_module.2_processor/scripts/extract_ite_year.py` | MODIFIED — filename pattern: ITE_Questions→MC, ITE_Critique→critique |
| `01_module.1_warehouse/scripts/maintain/audit_engine_type_changes.py` | MODIFIED — exists() guard added to tier folder scan |
| `01_module.1_warehouse/scripts/maintain/build_crosswalk_index.py` | MODIFIED — output paths to 00_database/crosswalk/; multi-tier PDF scan |
| `02_module.2_processor/scripts/classify_ite_year.py` | MODIFIED — use_label_encoder=False removed |
| `02_module.2_processor/scripts/ite_intelligence_enricher_batch.py` | MODIFIED — JSON_DIR default to extracted_json/ |
| `01_module.1_warehouse/scripts/build/rebuild_ite_db_v2.py` | MODIFIED — LOG_DIR to 00_database/logs/ |
| `01_module.1_warehouse/scripts/maintain/build_clinical_pathways.py` | MODIFIED — OUTPUT_DIR to 00_database/readable_db_files/ |
| `01_module.1_warehouse/scripts/maintain/backfill_new_article_metadata.py` | MODIFIED — VC gate cross-check + mismatch counter |
| `01_module.1_warehouse/scripts/maintain/build_topic_trends.py` | MODIFIED — docstring escape fix |
| `02_module.2_processor/scripts/clear_and_reenrich.py` | MODIFIED — docstring escape fix |
| `CLAUDE.md` | MODIFIED — BATON pointer → 038, GitHub remote → board_prep_intel, Windows root path, Option B status |
| `_index.md` | MODIFIED — status line + Option B completion note |
| `auto-memory-copies/project_overhaul_state.md` | MODIFIED — BATON + path references updated for board_prep_intel |
| `option_b_patch.py` | ADDED — one-shot doc patcher script (executed and complete) |
