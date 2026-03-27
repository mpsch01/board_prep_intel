# BATON 008 — Mac QC Sweep + Enrichment Pipeline Repair + Batch API Submission
**Date:** 2026-03-25
**Session platform:** Mac (Cowork VM) — NOT the Windows PC
**Status:** Active
**Preceding BATON:** `BATON_active_007_20260325_m3_pipeline.md`
**Batch API in flight:** `msgbatch_01F8EYo8LCGy9iH2D6kARGPQ` (134 requests, claude-sonnet-4-20250514, submitted ~14:34 EST)

---

## SESSION SUMMARY — What Was Done and Why

This session ran a full QC sweep of all ~77 pipeline scripts after major file reorganization, repaired the enrichment pipeline's broken linkage to 242 pre-codon JSONs, and submitted a Batch API enrichment run. The work happened on Mac via Cowork VM, not the Windows PC.

---

## 1. Full QC Sweep — DB Path Fixes (13 scripts)

### Problem
After the module reorganization (BATON 007), many scripts had broken DB paths. Three patterns identified:

### Pattern A — `BASE_DIR / "db"` → Fixed (10 scripts)
Old path pointed to a non-existent `db/` folder inside the module. Fixed to `PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"`.

| Script | Location |
|--------|----------|
| `batch_db_extract.py` | M2/scripts/ |
| `db_guided_extractor.py` | M2/scripts/ |
| `ite_intelligence_enricher.py` | M2/scripts/ |
| `ite_intelligence_enricher_batch.py` | M2/scripts/ |
| `rematch_unmatched.py` | M2/scripts/ |
| `rebuild_ite_db_v2.py` | M1/scripts/build/ |
| `validate_db_v2.py` | M1/scripts/build/ |
| `build_crosswalk_index.py` | M1/scripts/maintain/ |
| `build_match_staging.py` | M1/scripts/maintain/ |
| `compute_embeddings.py` | M1/scripts/maintain/ |

### Pattern B — Hardcoded Windows `C:\` paths → DEFERRED
5 AAFP scripts. Not fixed because Windows PC is still primary machine. Fix these when/if Mac becomes primary.

| Script | Location |
|--------|----------|
| `aafp_build_session_article_map.py` | M2/scripts/ |
| `aafp_build_video_outline.py` | M2/scripts/ |
| `aafp_fetch_article_text.py` | M2/scripts/ |
| `aafp_match_ite_questions.py` | M2/scripts/ |
| `aafp_parse_transcripts.py` | M2/scripts/ |

### Pattern C — `os.path.join(SCRIPT_DIR, "..", "db")` → Fixed (3 scripts)
Changed to `os.path.join(PROJECT_ROOT, "00_database", "db")`.

| Script | Location |
|--------|----------|
| `build_clinical_pathways.py` | M1/scripts/maintain/ |
| `build_topic_trends.py` | M1/scripts/maintain/ |
| `build_icd10_tags.py` | M3/scripts/ |

### Verification
- 13/13 scripts pass Python syntax check
- 6/6 sampled scripts resolve DB path correctly at runtime
- `PROJECT_ROOT` conventions confirmed:
  - M2/scripts: `SCRIPT_DIR.parent.parent`
  - M1/scripts/build and M1/scripts/maintain: `SCRIPT_DIR.parent.parent.parent`
  - M3/scripts: `SCRIPT_DIR.parent.parent`

---

## 2. Syntax Fix — 09_build_pearl_callouts.py

**Line 194**: `SyntaxError: f-string expression part cannot include a backslash`
- Extracted XML string containing `\n` into a variable before the f-string
- Script now passes syntax check

---

## 3. Node.js Dependencies Installed

`npm init -y && npm install docx sql.js` at project root.
- 7/7 JS files resolve their `require('docx')` and `require('sql.js')` imports
- `node_modules/` already in `.gitignore`
- Note: `npm init` threw `Invalid name: "00_#project_overhaul"` warning due to `#` in folder name — install succeeded anyway

---

## 4. Git Housekeeping

- **Stale `index.lock`** removed via Desktop Commander MCP (VM FUSE layer can't delete NTFS artifacts)
- **`.gitignore` updated**: added `.fuse_hidden*` and `\#PROJECT_OVERHAUL/` entries
- **Ghost `#PROJECT_OVERHAUL/` directory** in repo — artifact from `#` in folder name. Mikey trashed it from Finder
- **Decided to defer renaming `#` out of folder name** until after QC and test runs complete

---

## 5. Data Lifecycle Dashboard — `ite_pipeline_data_lifecycle.html`

**Created** a full interactive HTML dashboard (dark theme, Chart.js) documenting the JSON state progression through the pipeline:

- 5 JSON states defined: **raw → extracted → synthesized → enriched → rendered**
- Field inventory with origin tags (PDF parse, Claude API, DB lookup, computed, static default)
- DB schema map showing all 8 tables
- Pipeline coverage charts
- Profiles 88 unique key paths across 242 JSONs
- Traces data flow through 7 scripts: `convert_pdfs_to_json.py → db_guided_extractor.py → synthesize.js → ite_intelligence_enricher.py → build_summary.js → DOCX`

**Dashboard style saved to memory** at `re-org_guidance/auto-memory-copies/reference_dashboard_style.md` for replication across M1, M3, Module F, and ITE question pipeline modules (not started yet).

---

## 6. Enrichment Pipeline Repair — The Big One

### The Problem
The enricher (`ite_intelligence_enricher.py`) uses 2-strategy lookup:
- **Strategy 0**: Codon filename regex (`#@#ART-XXXX@#@`) — fails because 242 JSONs predate codon system
- **Strategy 1**: `source.clean_ref` exact match — fails because JSONs had no `clean_ref` field

Result: **0/242 matches on first dry-run**. These JSONs have old-style filenames like `IDSA_vax_immunocomp.pdf` with no codon and no DB linkage.

### The Fix — `backfill_json_article_links.py` (NEW SCRIPT)
Location: `02_module.2_processor/scripts/backfill_json_article_links.py`

One-time script using Python's built-in `difflib.SequenceMatcher` (100% local, zero API calls) to fuzzy-match each JSON's `source.title` against all 1,936 DB article records (`title` and `clean_ref` columns).

**Thresholds:**
| Range | Label | Action |
|-------|-------|--------|
| ≥ 0.85 | AUTO_MATCH | Written automatically in `--apply` mode |
| 0.60–0.84 | REVIEW | Printed for manual review, NOT auto-written |
| < 0.60 | NO_MATCH | Skipped |

**Execution sequence:**
1. `--dry-run` (default): 101 auto-match / 89 review / 52 no-match
2. `--apply`: 101 auto-matches written to JSONs
3. Mikey manually reviewed all 89 review-band matches in the JSON report
4. **All 89 confirmed correct EXCEPT items 48 and 49** (USPSTF false positives — SequenceMatcher fooled by structural boilerplate "US Preventive Services Task Force Recommendation Statement")
5. Re-ran with `--threshold 0.60 --apply`: applied 87 more
6. 2 false positives (items 48, 49) reverted programmatically
7. 2 additional manual overrides applied (items 45, 46 — IDSA Influenza ART-1275 and IDSA Lyme Disease ART-1433)

**Fields written into each JSON's `source` block:**
```json
{
  "art_id": "ART-XXXX",
  "clean_ref": "Full citation text from DB",
  "backfill_match_score": 0.95,
  "backfill_matched_on": "title",
  "backfill_date": "2026-03-25T17:52:52.194849+00:00"
}
```
Manual overrides have `"backfill_match_score": "manual_override"` and `"backfill_matched_on": "manual_review"`.

### Final Linkage State
| Category | Count |
|----------|-------|
| **Linked (have art_id)** | **188** |
| With linked questions (enrichable) | 134 |
| Without questions (linked but not enrichable) | 54 |
| **Unlinked** | **54** |
| Total JSONs | 242 |

### Enricher Code Fixes (also applied this session)
1. **Glob pattern**: Changed `*.json` excluding `manifest.json` (was `*_extracted.json`)
2. **Non-dict guard**: Added check for `isinstance(doc, dict)` in `process_file()`
3. **DB path**: Fixed from `BASE_DIR / "db"` to `PROJECT_ROOT / "00_database" / "db"` (Pattern A)

---

## 7. Batch API Enrichment — IN FLIGHT

### New Scripts Created
| Script | Purpose |
|--------|---------|
| `batch_submit_enrichment.py` | Builds .jsonl batch file, submits to Anthropic Batch API |
| `batch_retrieve_enrichment.py` | Retrieves results, computes TF-IDF, writes `ite_intelligence{}` blocks |

Both in `02_module.2_processor/scripts/`.

### What Was Submitted
- **Batch ID:** `msgbatch_01F8EYo8LCGy9iH2D6kARGPQ`
- **Requests:** 134 (all JSONs with DB linkage + linked questions)
- **Model:** `claude-sonnet-4-20250514`
- **Cost:** ~50% of real-time pricing (Batch API discount)
- **Expected completion:** Within 24 hours of submission

### Batch Info File
`02_module.2_processor/logs/batch_info_20260325_143424.json`

### How to Retrieve Results
**IMPORTANT — run this from the Mac terminal (or wherever `anthropic` SDK is installed):**

```bash
cd "/path/to/00_#PROJECT_OVERHAUL"
python3 02_module.2_processor/scripts/batch_retrieve_enrichment.py \
  --batch-info "02_module.2_processor/logs/batch_info_20260325_143424.json" \
  --wait
```

The `--wait` flag polls every 30 seconds until the batch completes, then automatically:
1. Downloads all 134 results
2. Saves raw results to `logs/batch_results_raw_*.json`
3. Computes TF-IDF concept colors (local DB query — identical to enricher v4)
4. Builds `linked_qids` array for DOCX rendering
5. Writes `ite_intelligence{}` block into each JSON
6. Tags each with `_enriched_via: "batch_api"` for provenance

Without `--wait`, just checks current status.

### What the Retrieval Script Writes into Each JSON
```json
{
  "ite_intelligence": {
    "exam_years_cited": [2019, 2021, 2022],
    "question_ids": ["QID-2019-0042", "QID-2021-0103", "QID-2022-0067"],
    "citation_count": 3,
    "high_yield_concepts": ["gout flare prophylaxis", "urate-lowering therapy initiation", ...],
    "concept_summary": "ABFM has tested initiation criteria for urate-lowering therapy...",
    "tier_rationale": "Cited 3 times across 2019–2022 ITE exams at local_lite tier...",
    "enrichment_confidence": "high",
    "_match_method": "clean_ref",
    "_enriched_at": "2026-03-25T...",
    "_enriched_via": "batch_api",
    "linked_qids": [
      {
        "qid": "QID-2019-0042",
        "exam_year": 2019,
        "question_stem": "A 58-year-old male with a history of gout...",
        "concept_tested": "gout, urate-lowering therapy | Management of chronic gout",
        "concept_colors": [{"text": "gout", "color": "green"}, ...]
      }
    ],
    "exam_years": [2019, 2021, 2022]
  }
}
```

---

## 8. Log Files Created This Session

All in `02_module.2_processor/logs/`:

| File | What it contains |
|------|-----------------|
| `backfill_dryrun_20260325_135056.json` | First dry-run: 101 auto / 89 review / 52 no-match |
| `backfill_apply_20260325_135419.json` | First apply (101 auto-matches). **Review-band details here** |
| `backfill_apply_20260325_141256.json` | Second apply (87 review-band matches) |
| `enricher_dryrun_20260325_131741.json` | First enricher dry-run (0/242 matches — pre-backfill) |
| `enricher_dryrun_20260325_141410.json` | Second enricher dry-run (134/242 matches — post-backfill) |
| `batch_info_20260325_143424.json` | **Batch API submission info** — batch_id + metadata path |
| `batch_metadata_20260325_143424.json` | Per-request metadata (questions, clean_ref, etc.) for retrieval |
| `batch_enrichment_20260325_143424.jsonl` | The .jsonl file that was submitted |

**Note:** Earlier failed submission attempts left orphan .jsonl and metadata files (timestamps 141856, 142810, 143114, 143258). These can be deleted — only the `_143424` set is the real submission.

---

## 9. Supabase MCP Connected — DEFERRED

Supabase MCP was connected during this session. Evaluation deferred to BATON deferred flags. Potential wins:
- pgvector native (replaces sqlite-vec extension dependency)
- Edge functions for remote querying
- Natural fit for Intelligence 2.0 Layers 2–4

**Do not act on this until pipeline is stable end-to-end.**

---

## Current DB State (unchanged from BATON 007)

| Table | Rows |
|-------|------|
| articles | 1,936 |
| questions | 1,629 (2018–2025) |
| question_ref_pairs | 2,722 |
| qid_art_xref | 1,818 |
| article_icd10 | 3,855 |
| clinical_pathways | 3,093 |
| icd10_rollup | 614 |
| icd10_code_xref | 1,006 |

---

## Current JSON Linkage State

| Category | Count |
|----------|-------|
| Total extracted JSONs | 242 |
| Linked to DB (have `source.art_id`) | 188 |
| — with questions (enrichable) | 134 |
| — without questions | 54 |
| Unlinked (no DB article found) | 54 |
| **Batch enrichment submitted** | **134** |
| Batch enrichment pending retrieval | **134** |

---

## Scripts Created This Session

| Script | Location | Purpose |
|--------|----------|---------|
| `backfill_json_article_links.py` | M2/scripts/ | One-time fuzzy-match JSONs to DB articles via SequenceMatcher |
| `batch_submit_enrichment.py` | M2/scripts/ | Build .jsonl + submit to Anthropic Batch API |
| `batch_retrieve_enrichment.py` | M2/scripts/ | Retrieve batch results + write ite_intelligence blocks |

---

## Deferred Flags (Carried Forward + New)

| Flag | Description |
|------|-------------|
| ~~FLAG 33~~ | **CLOSED** — 100% embedding coverage |
| BATCH_DIRS sorting | 249 flat JSONs need sorting into 5 named subdirs |
| Scholl ENCRYPTED PDFs | Need password or unencrypted versions |
| Supabase evaluation | **NEW** — Connected 2026-03-25. Defer until pipeline stable. |
| Pattern B Windows paths | 5 AAFP scripts with hardcoded `C:\` paths. Fix when Mac becomes primary. |
| Rename `#` from folder | Defer until after QC + test runs complete |
| Dashboard replication | Replicate data lifecycle dashboard for M1, M3, Module F, ITE question pipeline |
| Orphan batch logs cleanup | Delete `_141856`, `_142810`, `_143114`, `_143258` log files (failed submissions) |

---

## Next Steps (Ordered)

### IMMEDIATE — Retrieve Batch Results
```bash
python3 02_module.2_processor/scripts/batch_retrieve_enrichment.py \
  --batch-info "02_module.2_processor/logs/batch_info_20260325_143424.json" --wait
```
This writes `ite_intelligence{}` into 134 JSONs. Verify a few samples after retrieval.

### THEN — Post-Enrichment QC
1. Spot-check 5-10 enriched JSONs for correct `ite_intelligence{}` content
2. Verify `_enriched_via: "batch_api"` tag present
3. Compare structure against any JSONs enriched via real-time enricher (if any exist)

### THEN — Resume Pipeline Testing
1. **End-to-end test** each module (M1 build, M2 extract→enrich→DOCX, M3 analysis)
2. **BATCH_DIRS sorting** — sort 249 flat JSONs into 5 named subdirs
3. **ITE question pipeline E2E** — `01→02→03→ite_tag_questions` on 2025 source docs
4. **2018–2019 qid_art_xref crosswalk pass**

### LATER
5. **Intelligence 2.0 Layer 2** — `article_currency` table via PubMed MCP
6. **Supabase evaluation** — compare against SQLite for production use
7. **Dashboard replication** — M1, M3, Module F, ITE question pipeline

---

## Conventions Locked (all from BATON 007, still active)

- **Path depth (M2/scripts):** `SCRIPT_DIR.parent.parent` = PROJECT_ROOT
- **Path depth (M1/maintain, M1/build):** `SCRIPT_DIR.parent.parent.parent` = PROJECT_ROOT
- **Path depth (M3/scripts):** `SCRIPT_DIR.parent.parent` = PROJECT_ROOT
- **DB path:** `PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"` (all scripts)
- **JS rule:** No de novo JS. New code = Python only.
- **VC gate:** `key_data_files/session_hy_inserts_v7.json` (352 citations)
- **Codon filename:** `Author_Year#@#ART-XXXX@#@.pdf`
- **Strategy 0 first** in every enricher
- **Git from Windows/Mac** — VM FUSE layer can't delete NTFS artifacts
- **Backfill provenance:** JSONs matched via backfill carry `backfill_match_score`, `backfill_matched_on`, `backfill_date` in source block
- **Batch API provenance:** Enriched JSONs carry `_enriched_via: "batch_api"` in `ite_intelligence` block

---

## Script Counts (updated)

| Location | Count |
|----------|-------|
| M1/scripts/build/ | 6 |
| M1/scripts/maintain/ | 13 |
| M2/scripts/ | 50 Python + 6 JS + 1 config JSON |
| M3/scripts/ | 4 Python + 1 JS + 2 JSON config |
| Total active pipeline scripts | ~80 |
