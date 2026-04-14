# BATON 056 — Resident Reorg, Report Fixes, Modular Vectors

**Date:** 2026-04-14  
**Session duration:** Full  
**Previous BATON:** BATON_active_055_20260413_concept_fingerprint_icd10_enrichment.md  
**Git hash (pre-commit):** 223d0af  
**Branch:** main  
**Status:** ✅ Complete

---

## HEADLINE

Reorganized resident data into modular `inputs/`→`outputs/` structure (Task 1); added PDF password support to score report parser (Task 2); fixed 12 report issues identified from Sarkar review (Task 4); designed and built modular vector architecture — blueprint/body_system label embeddings + per-question concept/ICD-10 vectors + intersection centroids (Task 5). All 4 residents re-analyzed with fresh scoring. Vector tables now live in DB but not yet wired to Tier 1 practice question matching.

---

## SECTION 1: DB STATE

### Verified Row Counts (this session)
| Table | Rows | Status | Notes |
|-------|------|--------|-------|
| articles | 1,985 | ✅ | No change |
| questions (ITE) | 1,629 | ✅ | 2018–2025 complete |
| aafp_questions | 1,221 | ✅ | BRQ bank |
| qid_art_xref | 2,470 | ✅ | |
| aafp_qid_art_xref | 864 | ✅ | 643 unique Qs linked (52.7%) |
| article_icd10 | 4,020 | ✅ | |
| question_icd10 | 5,218 | ✅ | 1,512/1,629 ITE (92.8%) |
| aafp_question_icd10 | 4,753 | ✅ | Relevance normalized, related cap applied |
| clinical_pathways | 3,971 | ✅ | Blueprint-based, both banks |
| pubmed_pmid_cache | 344 | ✅ | Layer 2 seed |
| article_icd10_vec | 1,757 | ✅ | |
| question_icd10_vec | 2,747 | ✅ | |
| icd10_vec | 2,219 | ✅ | |
| article_currency | 1,985 | ✅ | |
| **question_full_vec** | **1,629** | **✅ NEW** | Full question embedding + blueprint in text |
| **aafp_question_full_vec** | **1,221** | **✅ NEW** | Full question embedding + blueprint + body_system + concept_tags |
| **blueprint_label_vec** | **5** | **✅ NEW** | Canonical blueprint label embeddings (shared across all Qs) |
| **bodysystem_label_vec** | **5** | **✅ NEW** | Canonical body system label embeddings (shared across all Qs) |
| **question_concepttag_vec** | **2,850** | **✅ NEW** | Per-question concept_tags embedding (ITE + AAFP) |
| **intersection_centroid_vec** | **135** | **✅ NEW** | 71 ITE + 64 AAFP blueprint×body_system centroids |

### PDF Library
- VC_fail: 630 | VC_pass: 168 | local_lite: 117 | right_click: 58 | AAFP: 15 | ITE exams: 16
- All PDFs recovered via exa_pdf_downloader + pmc_oa_downloader + recover_unpaywall
- 14 duplicates archived in `_dupe_archive/`

### Script Inventory
- M1 build: 8py (+2 new this session: `download_targeted.py`, `verify_resident_structure.py`)
- M1 maintain: 26py
- M2 core: 4py | M2 engines: 7py | M2 utils: 6py | M2 other: 58py + 6js
- M3: 16py + 2js
- M5: 35ts/tsx + 5sql

---

## SECTION 2: SESSION WORK

### Task 1: Resident Data Reorganization

**Objective:** Establish persistent, audit-friendly input/output folder structure for all resident analyses.

**Work done:**
- Created `03_module.3_analyst/resident_data/` as permanent home for all resident work
- Under each resident (Sarkar, Hopkins, Pjetergjoka, Scholl):
  - `inputs/` — source PDFs (score report, blueprint, body system report)
  - `outputs/` — analysis artifacts (DOCX, JSON, CSV)
- Migrated all 4 residents into new structure
- Created `delete_me/` folder; moved 13 pre-BATON-055 stale analysis docs (DOCXs + legacy JSONs) into it
- Old year-specific folders (`ITE_adona_pjetergjoka_2024/`, `ITE_adona_pjetergjoka_2025/`) emptied and shells marked for deletion
- Verification script `verify_resident_structure.py` written; confirms all 4 residents have inputs/ + outputs/ + no orphan files

**Files modified/created:**
- `03_module.3_analyst/resident_data/` (new directory structure)
- `03_module.3_analyst/resident_data/[4 residents]/inputs/` — PDF sources
- `03_module.3_analyst/resident_data/[4 residents]/outputs/` — fresh analyses
- `verify_resident_structure.py` — audits folder structure, reports on orphan files

**Status:** ✅ Complete. Two empty shell folders require Windows Explorer deletion (not blocking).

---

### Task 2: Password Support in ite_parser.py

**Objective:** Enable parsing of password-protected score PDFs (e.g., Pjetergjoka's ABFM-issued PDFs).

**Work done:**
- Added `_find_pdf_password(pdf_path: str) -> str | None` — globs for `*_PDF_PASSWORD.txt` in same directory as PDF
  - Convention: `AP_PDF_PASSWORD.txt` for Adona Pjetergjoka, etc.
  - Returns password string or None if file not found
- Added `_open_pdf(pdf_path: str, password: str | None = None) -> fitz.Document`
  - Calls `fitz.open(pdf_path)`
  - Auto-authenticates with password if `doc.needs_pass` is True
  - Fallback: tries empty string password if provided password fails
- Updated all three parse functions to use `_open_pdf()`:
  - `parse_blueprint()`
  - `parse_bodysystem()`
  - `parse_score_report()`

**Test result:**
- Pjetergjoka's password-protected 2024 + 2025 score PDFs now parse successfully
- Official scaled scores extracted correctly: 2024 → 350, 2025 → 370 (+20 YoY)

**Files modified:**
- `03_module.3_analyst/ite_parser.py` — added `_find_pdf_password()`, `_open_pdf()`, updated 3 parse functions

**Status:** ✅ Complete. Convention documented in this BATON.

---

### Task 3: Fresh Resident Analyses (7 runs)

**Objective:** Generate baseline + year-over-year analyses for all 4 residents using new input/output structure + password support.

**Runs completed:**
1. **Sarkar 2025:** 57.1% — first baseline analysis
2. **Hopkins 2025:** 65.4% — first baseline analysis
3. **Pjetergjoka 2024:** 52.3% (ABFM scaled 350)
4. **Pjetergjoka 2025:** 54.5% (ABFM scaled 370, +20 YoY growth)
5. **Scholl 2022:** 64.2% — first in 3-year chain
6. **Scholl 2023:** 68.8% — peak in chain
7. **Scholl 2024:** 65.1% — most recent

**All analyses include:**
- Full Exam at a Glance + score band + FMCE probability
- Easy misses table (top 20 by frequency)
- Top diagnoses + top drugs (ITE-only counts displayed)
- Concept Fingerprint section (normalized strengths + weaknesses)
- ICD-10 weakness map (miss_count ≥ 2)
- Reading list (15 top articles matched to resident's missed QIDs)
- YoY comparison (for Pjetergjoka + Scholl chains)

**Output format:**
- DOCX + JSON per resident-year in `outputs/` folder
- JSON includes raw concept/ICD-10 scoring data for external analysis

**Status:** ✅ Complete. All 7 runs verified; no parsing errors.

---

### Task 4: 12 Report Fixes (ite_analyzer_v3.py + ite_report_builder_v2.js)

**Objective:** Address 12 issues identified from Sarkar 2025 report review by Mikey.

| # | Issue | Fix | File | Status |
|---|-------|-----|------|--------|
| 1 | "Historical National vs. Program Trend" table removed — deferred | Deleted table generation code; program_trend data awaited | ite_analyzer_v3.py | ✅ |
| 2 | Zone label ("Monitoring Zone") shown alongside FMCE band | Removed zone label; score band shows only FMCE probability | ite_report_builder_v2.js | ✅ |
| 3 | FMCE "On Track" threshold was 420; should be 440 | Corrected threshold logic in `get_fmce_band()`; aligns with ABFM research | ite_analyzer_v3.py | ✅ |
| 4 | Pages 1+2 had unnecessary page break | Consolidated title + Exam at a Glance to single page in report builder | ite_report_builder_v2.js | ✅ |
| 5 | Easy misses body_system sometimes empty | Fallback chain: `body_system_merged` → `body_system` → `blueprint` → `—` | ite_analyzer_v3.py | ✅ |
| 6 | QID display showed combined counts instead of ITE-only | Changed: `top_diagnoses`/`top_drugs` now display ITE-only counts from `concept_qid_map` | ite_analyzer_v3.py | ✅ |
| 7 | Concept frequency inflation in Fingerprint | Frequencies displayed are ITE-only (from `concept_qid_map`); combined counts in `_combined` variables used for scoring only | ite_analyzer_v3.py | ✅ |
| 8 | Drug list inclusion errors (e.g., metformin as diagnosis) | Expanded `KNOWN_DRUGS` set to reclassify NSAIDs, lisinopril, atorvastatin, doxycycline, etc. from diagnoses → drugs | ite_analyzer_v3.py | ✅ |
| 9 | Prednisone concept frequency missing | Added synonym entry: prednisone → Corticosteroids; also prednisolone, methylprednisolone, dexamethasone, budesonide | ite_analyzer_v3.py | ✅ |
| 10 | Guidelines table in Fingerprint too broad | Removed `clinical_pathways` table from Concept Fingerprint section (data too summary-level for actionability) | ite_report_builder_v2.js | ✅ |
| 11 | ICD-10 weakness map cluttered with single-miss items | Filtered to show only `miss_count ≥ 2` (suppresses noise from one-off misses) | ite_analyzer_v3.py | ✅ |
| 12 | Reading list too generic (top 15 articles nationally) | Personalized: now queries articles linked to THIS resident's missed QIDs specifically; `match_top_articles()` rewritten; count raised to 15 | ite_analyzer_v3.py | ✅ |

**Files modified:**
- `03_module.3_analyst/ite_analyzer_v3.py` — issues 1, 3, 5, 6, 7, 8, 9, 11, 12
- `03_module.3_analyst/ite_report_builder_v2.js` — issues 2, 4, 10

**Test result:**
- All 7 resident analyses re-run after fixes; no new errors introduced
- Sarkar 2025 report spot-checked: all 12 fixes verified visually
- YoY comparisons still work; no temporal data corruption

**Status:** ✅ Complete. Ready for Mikey review.

---

### Task 5: Modular Vector Architecture — Design + Build

**Objective:** Replace monolithic question embeddings with modular vectors that separately encode blueprint, body system, concept tags, and ICD-10 codes for precision-tuned Tier 1 practice question matching.

#### 5a. Design Decisions

**Core principle:** Each question gets separate vector dimensions, not one combined embedding.

**Design choices:**
- **Blueprint vectors (5 rows):** Text embeddings of canonical blueprint names (e.g., "Chronic Care Management"). Shared across all questions in that blueprint. Computed once, reused.
- **Body system vectors (5 rows):** Text embeddings of 5 canonical PDF-reported body system labels:
  1. Cardiovascular
  2. Injuries/Musculoskeletal
  3. Psychiatric/Behavioral
  4. Respiratory
  5. Sexual and Reproductive
  - DB-side body system field has multiple variant names; synonym table maps all variants to these 5 canonical labels
  - ITE exams report in these 5 categories; AAFP BRQ also mapped to same 5
- **Per-question concept vectors (2,850 rows):** Embedding of each question's `concept_tags` (normalized, deduplicated) — captures semantic topic fingerprint
- **Per-question ICD-10 vectors:** Reused from existing `question_icd10_vec` table (already computed)
- **Intersection centroids (135 rows):** Local numpy computation of mean vector for all questions in each blueprint×body_system cell. Allows fast nearest-neighbor matching within a specific clinical category pair.

**Why separate?** Blueprint and body system change slowly (structural); concept tags + ICD-10 capture semantic variance (high-cardinality). Splitting allows:
- Blueprint/body system queries to use small, cached label vectors
- Concept/ICD-10 scoring to preserve granularity
- Intersection centroids to bootstrap fast category-specific searches
- Easy re-tuning of each dimension independently

#### 5b. Canonical Body System Taxonomy

**ITE exams (2018–2025) report in these 5 categories.**

| Canonical Label | DB Variants (from body_system field) | Notes |
|-----------------|--------------------------------------|-------|
| Cardiovascular | Cardiovascular | Direct |
| Injuries/Musculoskeletal | Musculoskeletal, Injuries | Two variants in DB |
| Psychiatric/Behavioral | Psychiatric/Behavioral, Psychogenic | Two variants; "Psychogenic" added for completeness |
| Respiratory | Respiratory | Direct |
| Sexual and Reproductive | Reproductive: Female, Reproductive: Male, Reproductive | Three variants; canonical form represents both |

**AAFP BRQ (1,221 questions):** Body system field populated with same 5 canonical values via `build_modular_vectors.py` synonym mapping.

**Scholl 2022/2023 note:** Older ABFM taxonomy (Adult Medicine, Care of Children, Emergent & Urgent Care, etc.) doesn't map 1:1 to new 5 categories. Flag: `DEFERRED-SCHOLL-OLD-FORMAT`. Body system filtering won't work for those years; blueprint filtering still functional.

#### 5c. Scripts Built/Updated

**Script 1: `compute_embeddings.py` (UPDATED)**
- Modified `build_question_text()` to include blueprint in concatenated text before embedding
- Modified `build_aafp_question_text()` to include `blueprint + body_system + concept_tags` in text
- Added `--rebuild` flag to force re-computation of `question_full_vec` and `aafp_question_full_vec` tables
- Changes preserve backward compatibility; old single-text-embedding tables still exist if needed

**Script 2: `build_modular_vectors.py` (NEW)**
- Builds `blueprint_label_vec` table (5 rows): canonical blueprint names → text embedding
- Builds `bodysystem_label_vec` table (5 rows): canonical body system names → text embedding
- Builds `question_concepttag_vec` table (2,850 rows): per-question `concept_tags` (deduplicated, normalized) → text embedding
- All three use OpenAI text-embedding-3-small (1536d)
- Handles AAFP body system synonym mapping automatically
- Idempotent: can be re-run without duplication

**Script 3: `build_intersection_centroids.py` (NEW)**
- Computes mean vector for all questions in each blueprint×body_system intersection cell
- ITE: 71 cells (not all combinations populated; only cells with ≥1 question)
- AAFP: 64 cells (similar sparsity)
- Total: 135 rows in `intersection_centroid_vec` table
- Uses numpy locally; no API calls. O(n) complexity.
- Output format: `qid` field set to null; `embedding` field stores blueprint+body_system intersection mean
- Idempotent; can be re-run to refresh

**Integration points (not yet wired, see DEFERRED-VECTOR-TIER1-REWRITE):**
- `match_practice_questions_v3()` in `ite_analyzer_v3.py` currently uses broad WHERE clause: `WHERE blueprint IN (weak_blueprints) AND body_system_merged IN (...)`
- Next session: replace with vector similarity against `intersection_centroid_vec` + re-rank with `question_concepttag_vec` + `question_icd10_vec`

#### 5d. Execution & Cost

**All three scripts run successfully on Mikey's machine:**
```
compute_embeddings.py --rebuild
  → question_full_vec: 1,629 rows (ITE)
  → aafp_question_full_vec: 1,221 rows (AAFP)
  → API cost: ~$0.008

build_modular_vectors.py
  → blueprint_label_vec: 5 rows
  → bodysystem_label_vec: 5 rows
  → question_concepttag_vec: 2,850 rows (ITE + AAFP, deduplicated)
  → API cost: ~$0.006

build_intersection_centroids.py
  → intersection_centroid_vec: 135 rows (71 ITE + 64 AAFP)
  → No API cost (local numpy)
```

**Total API cost this task:** ~$0.014 (well under budget)

**Verification:**
- Row counts match expected values
- All embeddings 1536-dimensional
- Centroid computations validated with sample SQL queries
- No data loss; backward compatibility maintained

**Files created:**
- `03_module.3_analyst/build_modular_vectors.py` — NEW
- `03_module.3_analyst/build_intersection_centroids.py` — NEW
- `03_module.3_analyst/compute_embeddings.py` — UPDATED (blueprint included in text)

**Status:** ✅ Complete. Vector tables built and populated. Tier 1 integration deferred to next session (see DEFERRED-VECTOR-TIER1-REWRITE).

---

## SECTION 3: SCHEMA CHANGES

### New Tables (4)

```sql
CREATE TABLE question_full_vec (
  qid TEXT PRIMARY KEY,
  embedding BLOB NOT NULL,  -- 1536-dim float32, OpenAI text-embedding-3-small
  FOREIGN KEY (qid) REFERENCES questions(qid)
);

CREATE TABLE aafp_question_full_vec (
  qid TEXT PRIMARY KEY,
  embedding BLOB NOT NULL,  -- 1536-dim float32, OpenAI text-embedding-3-small
  FOREIGN KEY (qid) REFERENCES aafp_questions(qid)
);

CREATE TABLE blueprint_label_vec (
  blueprint_name TEXT PRIMARY KEY,
  embedding BLOB NOT NULL,  -- 1536-dim float32
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE bodysystem_label_vec (
  body_system TEXT PRIMARY KEY,
  embedding BLOB NOT NULL,  -- 1536-dim float32
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE question_concepttag_vec (
  qid TEXT PRIMARY KEY,
  body BLOB,  -- JSONL: list of concept tag strings, deduplicated
  embedding BLOB NOT NULL,  -- 1536-dim float32
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (qid) REFERENCES questions(qid)
);

CREATE TABLE intersection_centroid_vec (
  blueprint TEXT NOT NULL,
  body_system TEXT NOT NULL,
  embedding BLOB NOT NULL,  -- 1536-dim float32, mean of all Qs in cell
  question_count INT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (blueprint, body_system)
);
```

### Modified Tables (0)
- No existing schema changes; only new tables added

---

## SECTION 4: RESIDENT DATA & ANALYSIS STATE

### Active Residents (updated this session)

| Resident | 2024 | 2025 | YoY Chain | Notes |
|----------|------|------|-----------|-------|
| **Sarkar, Rishi** | — | 57.1% (2025) | Baseline | First analysis; composite 352 ABFM |
| **Hopkins, [First]** | — | 65.4% (2025) | Baseline | First analysis |
| **Pjetergjoka, Adona** | 52.3% (350) | 54.5% (370) | ✅ Active | Scaled scores from password-protected PDFs; +20 YoY growth |
| **Scholl, Michael** | 64.2% (2022) | 68.8% (2023) | ✅ Active | 3-year chain; 2024: 65.1% |

### Folder Structure (now locked)
```
03_module.3_analyst/resident_data/
├── sarkar_rishi/
│   ├── inputs/
│   │   ├── blueprint.pdf
│   │   ├── bodysystem.pdf
│   │   └── score_report.pdf
│   └── outputs/
│       ├── Sarkar_Rishi_2025_analysis.docx
│       └── Sarkar_Rishi_2025_analysis.json
├── hopkins_[first]/
│   ├── inputs/
│   └── outputs/
├── pjetergjoka_adona/
│   ├── inputs/
│   │   ├── 2024/
│   │   │   ├── score_report.pdf
│   │   │   ├── AP_PDF_PASSWORD.txt
│   │   │   └── [blueprint, bodysystem]
│   │   └── 2025/
│   │       ├── score_report.pdf
│   │       ├── AP_PDF_PASSWORD.txt
│   │       └── [blueprint, bodysystem]
│   └── outputs/
│       ├── Pjetergjoka_Adona_2024_analysis.docx
│       ├── Pjetergjoka_Adona_2024_analysis.json
│       ├── Pjetergjoka_Adona_2025_analysis.docx
│       └── Pjetergjoka_Adona_2025_analysis.json
└── scholl_michael/
    ├── inputs/
    │   ├── 2022/ → [PDFs + AP_PDF_PASSWORD.txt]
    │   ├── 2023/ → [PDFs + AP_PDF_PASSWORD.txt]
    │   └── 2024/ → [PDFs + AP_PDF_PASSWORD.txt]
    └── outputs/
        ├── Scholl_Michael_2022_analysis.docx
        ├── Scholl_Michael_2022_analysis.json
        ├── [2023 & 2024 files]
        └── ...
```

### Cleanup Task (ongoing)
- `delete_me/` folder created with 13 pre-BATON-055 stale analysis files
- Empty shells of old year-specific folders remain at project root (e.g., `ITE_adona_pjetergjoka_2024/`)
- **Requires Windows Explorer deletion** (not blocking current work)

---

## SECTION 5: DEFERRED FLAGS (carry forward)

### 🔴 DEFERRED-YOY-ROBUSTNESS (ACTIVE)
**What:** Year-over-year temporal clustering needs edge-case testing with dense temporal data.  
**Why:** Section 3b (YoY comparison) added in BATON 050. Month-by-month rollup logic functional but untested on edge cases (e.g., same Q answered correctly in Oct, incorrectly in Nov; multiple exams within 7-day windows).  
**Next:** Add edge-case tests to `test_v3_changes.py` that simulate temporal collisions. Run on Scholl 3-year chain.  
**Blocker:** No. YoY section usable for exploratory analysis; robustness testing can follow.

### 🔴 DEFERRED-PGY-BENCHMARKS (ACTIVE)
**What:** PGY 1–4 cohort comparison data for Section 4.  
**Why:** Mikey to supply historical program aggregate scores (mean, SD, percentile by PGY level).  
**Next:** Once data received, integrate into resident report Section 4 ("How You Stack Up"). Requires new `abfm_reference_YYYY_PGYXX.json` files.  
**Blocker:** No. Report works without it; Section 4 shows FMCE band + percentile only.

### 🔴 DEFERRED-PROGRAM-TREND (ACTIVE)
**What:** Historical program aggregate scores for national vs. program comparison.  
**Why:** Table 1 (now deleted) required `program_trend` values. Mikey to supply year-by-year program mean scores.  
**Next:** Once data received, re-implement table in `ite_analyzer_v3.py` + report builder.  
**Blocker:** No. Table removal from BATON 055 already published to resident reports.

### 🟡 DEFERRED-RESIDENT-FOLDER-MIGRATION (PARTIALLY COMPLETE)
**What:** Modular `inputs/`→`outputs/` structure for all residents.  
**Why:** Audit trail + persistent organization.  
**Status this session:** All 4 residents migrated; structure locked. Two empty shell folders (`ITE_adona_pjetergjoka_2024/`, `ITE_adona_pjetergjoka_2025/`) at project root require Windows deletion.  
**Next:** Windows Explorer delete empty shells (or Windows MCP PowerShell Remove-Item). Not blocking further work.  
**Blocker:** No.

### 🟡 FLAG-33-NNN-RENAME (DEFERRED)
**What:** `nnn_XXXX` ART-ID rename scheme.  
**Status:** Designed, not implemented.  
**Priority:** Low. Existing `#@#..@#@` codon format works; rename would be cosmetic.  
**Next:** Queue for post-module-5 refactor.

### 🔴 **DEFERRED-VECTOR-TIER1-REWRITE (NEW — URGENT)**
**What:** Wire modular vector tables into Tier 1 of `match_practice_questions_v3()`.  
**Why:** Vectors are built + populated (Task 5). Current Tier 1 still uses broad WHERE clause (`blueprint IN (weak_blueprints) AND body_system IN (...)`). Vectors enable precision matching by semantic similarity.  
**Design:** Replace WHERE clause with:
  1. Query `intersection_centroid_vec` for blueprint×body_system cell matching resident's weak areas
  2. Compute cosine similarity between resident's `question_concepttag_vec` + `question_icd10_vec` profile and each candidate question
  3. Re-rank by combined score
  4. Return top N questions

**Status this session:** Design complete; code not written.  
**Next:** Build replacement Tier 1 logic. Re-run all 7 resident analyses to verify improved question selection.  
**Blocker:** Yes, for practice question quality. Current questions still acceptable; vector tier will refine matching.  
**Est. effort:** 2–3 hours.

### 🟡 **DEFERRED-PRACTICE-Q-TWO-TABLE (NEW — DESIGNED)**
**What:** Split practice question section into two sub-tables:  
  1. **ITE Body System Questions** — matched to 5 canonical PDF-reported body systems
  2. **Non-ITE Questions** — linked to missed ITE questions in categories not reported on PDF (e.g., psychogenic variants, old taxonomy)

**Why:** Clarifies which questions are "official" ITE-style vs. supplemental.  
**Design:** Report builder JS checks each question's `body_system_merged` against canonical 5. If in canonical set, Table 1; else Table 2.  
**Status this session:** Design complete; code not written.  
**Next:** Implement in `ite_report_builder_v2.js`. Requires no DB changes.  
**Blocker:** No. Current single table functional.

### 🟡 **DEFERRED-SCHOLL-OLD-FORMAT (NEW)**
**What:** Scholl 2022/2023 analyses use pre-2024 ABFM body system taxonomy (Adult Medicine, Care of Children, Emergent & Urgent Care, etc.).  
**Why:** Current 5-canonical body system mapping doesn't handle old taxonomy. Body system filtering in Tier 1 won't work for those years.  
**Scope:** Blueprint filtering still works; Scholl analyses remain usable for that dimension.  
**Status this session:** Identified during modular vector build.  
**Next:** Either (a) add synonym mapping from old→new body systems, or (b) skip body system filtering for pre-2024 years. Flag for Mikey decision.  
**Blocker:** No. Practice questions still match on blueprint dimension.

---

## SECTION 6: NEXT STEPS

### Immediate (next session)

1. **DEFERRED-VECTOR-TIER1-REWRITE** — Wire `intersection_centroid_vec` + `question_concepttag_vec` + `question_icd10_vec` into Tier 1 of `match_practice_questions_v3()`. Build replacement WHERE-clause logic using vector similarity. Est. 2–3 hours.

2. **Re-run all 7 resident analyses** — After Tier 1 rewrite, regenerate all resident outputs (Sarkar 2025, Hopkins 2025, Pjetergjoka 2024/2025, Scholl 2022/2023/2024) to verify improved practice question selection.

3. **DEFERRED-PRACTICE-Q-TWO-TABLE** — Implement two-table split in `ite_report_builder_v2.js` (no DB changes needed). Clarifies ITE-style vs. supplemental questions.

### Short-term (1–2 weeks)

4. **DEFERRED-PROGRAM-TREND** — Await Mikey's historical program aggregate scores. Re-implement comparison table once data arrives.

5. **DEFERRED-PGY-BENCHMARKS** — Await PGY 1–4 cohort data. Integrate into Section 4 comparison once received.

6. **DEFERRED-SCHOLL-OLD-FORMAT decision** — Mikey to confirm: add old→new body system synonym mapping, or skip body system filtering for 2022/2023.

7. **Module 5 setup** — Provision Supabase project; run migrations; sync SQLite → Supabase; deploy Railway FastAPI + Netlify frontend.

---

## SECTION 7: CRITICAL REMINDERS FOR NEXT SESSION

1. **ICD-10 enrichment is invisible.** `icd10_profile` passed to `match_practice_questions_v3()` as hidden scoring signal only. Never appears in resident report output. This is intentional.

2. **concept_qid_map = ITE-only.** `top_diagnoses` and `top_drugs` display ITE-only counts from `concept_qid_map`. Combined counts live in `top_diagnoses_combined` + `top_drugs_combined` variables; used for scoring only, never displayed.

3. **_normalize_concept() fallback = first-letter capitalize ONLY.** NOT `.title()`. Mangles acronyms (HIV → Hiv, IBS-D → Ibs-D). Correct form: `stripped[0].upper() + stripped[1:]`. Add new synonym entries for any canonical form needing resolution; don't change the fallback.

4. **test_v3_changes.py is the canary.** Run test suite after any modifications to `ite_analyzer_v3.py`. All 5 tests must pass before publishing resident analyses.

5. **Password support in parser.** `_find_pdf_password()` globs for `*_PDF_PASSWORD.txt` in same directory as PDF. Convention: `AP_PDF_PASSWORD.txt` for Adona Pjetergjoka, `MS_PDF_PASSWORD.txt` for Michael Scholl, etc. Password strings stored in files (not in code or env vars) for security.

6. **Modular vectors are built but NOT yet wired to Tier 1.** Four new vector tables exist in DB:
   - `blueprint_label_vec` (5 rows)
   - `bodysystem_label_vec` (5 rows)
   - `question_concepttag_vec` (2,850 rows)
   - `intersection_centroid_vec` (135 rows)
   
   Next session: connect them via `DEFERRED-VECTOR-TIER1-REWRITE`. Practice question matching will improve significantly.

7. **Body system synonym table is the source of truth.** 5 canonical PDF labels:
   - Cardiovascular → Cardiovascular (no alias in DB)
   - Injuries/Musculoskeletal → Musculoskeletal, Injuries (2 variants)
   - Psychiatric/Behavioral → Psychiatric/Behavioral, Psychogenic (2 variants)
   - Respiratory → Respiratory (no alias)
   - Sexual and Reproductive → Reproductive: Female, Reproductive: Male, Reproductive (3 variants)
   
   `BODYSYSTEM_PDF_TO_DB` in `ite_analyzer_v3.py` is the authoritative mapping. Keep it in sync with `build_modular_vectors.py`.

8. **Scholl old-taxonomy caveat.** 2022/2023 analyses use pre-2024 body system taxonomy. Body system filtering in practice question matching won't work for those years; blueprint filtering still functional. Awaiting Mikey's decision on alias strategy.

---

## GIT STATUS

**Pre-commit hash:** 223d0af  
**Branch:** main  
**Uncommitted files:** 0 (or all changes staged)  

**Files modified this session:**
- `03_module.3_analyst/ite_analyzer_v3.py` — 12 report fixes + resident data refactor
- `03_module.3_analyst/ite_report_builder_v2.js` — 4 report layout fixes
- `03_module.3_analyst/ite_parser.py` — password support + PDF handling

**Files created this session:**
- `03_module.3_analyst/build_modular_vectors.py` — NEW
- `03_module.3_analyst/build_intersection_centroids.py` — NEW
- `03_module.3_analyst/verify_resident_structure.py` — NEW
- `03_module.3_analyst/resident_data/` — NEW directory structure (all 4 residents)

**Git strategy next session:**
1. Stage all code changes + new M3 scripts
2. Commit with message: `BATON-056: resident reorg, report fixes, modular vectors — ITE×body_system centroids computed; Tier 1 wiring deferred`
3. Push to main

---

## SESSION SUMMARY

**Start:** BATON 055 complete; resident analyses locked at Sarkar concept fingerprint + ICD-10 foundation.  
**End:** 4 new vector tables built + populated; 12 report issues fixed; all 4 residents re-analyzed (7 runs total); residents organized into modular `inputs/`→`outputs/` structure; password support added for ABFM score PDFs.

**Quality metrics:**
- All 7 resident analyses QC-checked; no parsing errors
- Sarkar 2025 report spot-checked against 12-point checklist; all fixes verified
- Vector tables validated (row counts, dimensionality, centroid math)
- Backward compatibility maintained; no breaking changes

**Unblocked readiness:**
- ✅ Resident analyses publishable (Tier 1 practice question matching is acceptable with current WHERE clause; will improve with vectors)
- ✅ YoY comparisons functional (edge-case testing deferred but not blocking)
- ⏳ Module 5 ready to provision (awaiting Mikey approval on Supabase scope)

**Next session critical path:** DEFERRED-VECTOR-TIER1-REWRITE + re-run residents with improved matching.

---

**BATON 056 authored:** 2026-04-14  
**Status:** ✅ Complete. Ready for handoff.
