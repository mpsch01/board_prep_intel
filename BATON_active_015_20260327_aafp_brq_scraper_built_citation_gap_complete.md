# BATON 015 — AAFP BRQ Scraper Built, 1,221 Questions Imported, M1 Reorganized
**Date:** 2026-03-27
**Session platform:** Windows PC (Cowork VM) + dispatch
**Status:** Active
**Preceding BATON:** `BATON_active_014_20260327_m1_complete_m2_clean_critique_extractor_designed.md` (→ archive)
**Git hash:** `10d8208` (no new commits this session — all filesystem + DB work, no git run yet)

---

## SESSION SUMMARY — What Was Done and Why

Two major workstreams: (1) citation gap list built from ITE Critique PDFs, (2) AAFP BRQ scraper designed, debugged, run, and data imported to DB. Session ran partially via dispatch (Mikey away from PC).

---

### 1. Citation Gap List (229 Unique Unmatched Refs)

- Input: ITE Critique staging JSONs for 2024 and 2025
- Output: `02_module.2_processor/outputs/citation_gap_list_2024_2025.txt`

Structure:
- Section 1: 10 citations cited in BOTH 2024 and 2025 (highest priority)
- Section 2: 115 cited in 2025 only
- Section 3: 104 cited in 2024 only
- Each entry: full formal citation + QIDs that cited it

These 229 articles are cited on ITE exams but have no DB record — highest-priority acquisition targets. The 88 AFP articles from BATON 014 deferred flag likely overlap significantly.

---

### 2. AAFP BRQ Scraper — Full Pipeline

**The source:** AAFP publishes 135 Board Review Question quizzes (10 Q each = 1,350 total). Each question has: stem, 5 answer choices, correct answer, explanation, and "Ref:" citation. Enables AAFP-ITE topic lag analysis.

**Architecture (from takeClinicalQuestion.js):**
- GET `/assessment/take/{assessment_id}/c/{question_id}` → HTML (stem + choices)
- POST same URL → JSON `{IsCorrect, AnswerExplanation, NextQuestionId, ...}`
- `AllowMultipleAnswerAttempts: True` — retry wrong answers until correct
- **Key discovery:** `AnswerExplanation` ONLY populated on IsCorrect=True response (not wrong-answer responses)

**Structural constants (locked):**
- First assessment ID: 13882 (Board Review Questions 01)
- First question ID: 49733
- Formula: `first_q = 49733 + (assessment_id - 13882) * 10`
- Questions per quiz: 10 | Total quizzes: 135

**Bugs hit and fixed:**
1. `first_question_id: None` — intro page has no `/c/{id}` link. Fix: formula-based prediction
2. Empty explanations (72/91 early records) — explanation only returned on correct POST. Fix: capture from whichever POST has non-empty AnswerExplanation, prioritize correct response
3. VM proxy blocks outbound HTTPS — scraper runs on Windows local machine only
4. Windows cmd `&&` + Unicode encoding — fixed with `pushd` + `set PYTHONIOENCODING=utf-8`
5. **FUSE oplock stall** — VM polling of staging JSON while Windows scraper was writing caused an oplock conflict on the SMB-mounted filesystem, freezing the Windows write indefinitely. File frozen mid-write for 30+ minutes. Fix: resume logic added; polling the output file during an active scrape run is forbidden

**Resume logic added (key feature):**
- `load_existing_results(output_file)` reads existing staging file at scrape start
- Valid JSON → parsed, skips already-scraped assessment IDs
- Truncated/corrupted JSON → salvages complete records by finding last `\n  },` boundary, closes array, parses salvaged subset
- Skips quizzes whose assessment_id is already present in results
- Override: delete staging file to force full re-scrape

**Known gap: 129 missing questions**
Resume salvaged 1,221 records across 135 quiz assessment IDs. But 135×10=1,350 expected. The salvage sees all 135 IDs (some quizzes had partial data before the stall), marks them all complete, and skips them. ~13 quizzes are incomplete (< 10 questions). Not blocking — 1,221/1,350 is a solid working dataset. Gap-fill pass deferred.

**Import stats (dry-run + live):**
- `correct_value` found: 1,221/1,221 (100%) — retry loop worked
- `ref_text` present: 1,202/1,221 (98.4%)
- matched exact: 360 (29.5%)
- fuzzy (author+yr): 264 (21.6%)
- unmatched: 578 (47.3%) — mostly guidelines + format mismatches
- no_ref: 19 (1.6%)
- **Total article-linked: 624/1,221 (51.1%)**

---

### 3. M1 Reorganization — Option B Implemented

AAFP BRQ data moved to M1 as a proper warehouse source (scraper = acquisition tool, not sandbox experiment):

```
01_module.1_warehouse/aafp_brq/
├── scraper/
│   ├── aafp_brq_scraper.py    ← paths updated (OUTPUT_DIR → WAREHOUSE_DIR/staging/)
│   ├── aafp_cookies.json      ← 38 auth cookies (session cookies expire with browser)
│   ├── aafp_quiz_map.json     ← 135 quiz sets
│   └── aafp_explore_dump.txt  ← Q49733 explore reference
└── staging/
    └── aafp_brq_staging.json  ← 1,221 records, 4MB
```

Import script stays in M2 (processor operation): `02_module.2_processor/scripts/aafp_brq_import.py`

---

### 4. DB: `aafp_questions` Table Created + Populated

Table is separate from `questions` (ITE-specific fields incompatible; schema merge would create 30-40% NULL columns). Decision locked: **Option B+C — keep separate, build xref linkage.**

Schema highlights:
- PK: `aafp_qid` = "AAFP-{question_id}" (e.g. AAFP-49733)
- `article_id` FK + `match_status` for article linkage
- `explanation_html` preserved raw for re-extraction without re-scraping

**Integrity check (from Windows, post-import):**

| Table | Rows |
|-------|------|
| articles | 1,936 ✓ |
| questions | 1,629 ✓ |
| qid_art_xref | 2,470 ✓ |
| question_ref_pairs | 2,673 (49 below baseline — pre-existing, not session-caused) |
| article_icd10 | 3,855 ✓ |
| clinical_pathways | 3,093 ✓ |
| icd10_rollup | 614 ✓ |
| icd10_code_xref | 1,006 ✓ |
| **aafp_questions** | **1,221** (new) |

DB file: 35,749,888 bytes. VM read shows "malformed" — FUSE mount artifact from concurrent access; Windows-side queries confirm DB is healthy.

---

## New Files This Session

| File | Location | Notes |
|------|----------|-------|
| `aafp_brq_scraper.py` (v3+resume) | `01_module.1_warehouse/aafp_brq/scraper/` | Canonical location (copied from sandbox) |
| `aafp_cookies.json` | `01_module.1_warehouse/aafp_brq/scraper/` | Session cookies — re-export before next scrape |
| `aafp_quiz_map.json` | `01_module.1_warehouse/aafp_brq/scraper/` | 135 quiz sets |
| `aafp_explore_dump.txt` | `01_module.1_warehouse/aafp_brq/scraper/` | Q49733 reference |
| `aafp_brq_staging.json` | `01_module.1_warehouse/aafp_brq/staging/` | Canonical location |
| `aafp_brq_import.py` | `02_module.2_processor/scripts/` | Reads from M1 staging |
| `citation_gap_list_2024_2025.txt` | `02_module.2_processor/outputs/` | 229 unmatched refs |
| `_DELETE_THESE_FROM_WINDOWS.txt` | `04_module.4_sandbox/` | Cleanup checklist |

**Script count update:**
| Location | Python | JS | Other |
|----------|--------|----|-------|
| M1/build/ | 9 | — | 1 README |
| M1/maintain/ | 16 | — | 1 README |
| M2/scripts/ | **45** (+1 aafp_brq_import.py) | 6 | 1 JSON + 4 Windows |
| M3/scripts/ | 4 | 1 | 2 JSON |

---

## Housekeeping Carried Forward

- [ ] **Windows:** Archive BATON 013 → `baton_archive/`
- [ ] **Windows:** Archive BATON 014 → `baton_archive/`
- [ ] **Windows:** Delete original sandbox files (see `04_module.4_sandbox/_DELETE_THESE_FROM_WINDOWS.txt`)
  - `04_module.4_sandbox/aafp_brq_scraper.py`
  - `04_module.4_sandbox/aafp_cookies.json`
  - `04_module.4_sandbox/aafp_quiz_map.json`
  - `04_module.4_sandbox/aafp_explore_dump.txt`
  - `02_module.2_processor/outputs/aafp_brq_staging.json`
- [ ] **Git:** Stage + commit all session changes (see commit list below)

---

## Deferred Flags

| Flag | Description | Priority |
|------|-------------|----------|
| AAFP ref matching (second pass) | 578 unmatched refs — many are AFP articles failing on format differences. Second matcher: volume/page extraction + title keyword for guidelines | HIGH |
| `aafp_qid_art_xref` table | Parallel to qid_art_xref; one row per AAFP question-article link. Enables same join patterns as ITE pipeline | HIGH |
| AAFP-ITE lag analysis | After xref: query shared article citations, compute timing delta, build predictive watch list | HIGH |
| 129 missing AAFP questions | ~13 incomplete quizzes from stalled scrape. Fix resume logic to detect quizzes with < 10 questions; targeted re-scrape | MEDIUM |
| 229 citation gap articles | 88 AFP batch-downloadable from `null_clean_ref_missing_articles_20260326.csv` | HIGH |
| `extract_ite_critique_refs.py` | BATON 014 design, not yet built | HIGH |
| `update_citation_trends.py` | BATON 014 design, not yet built | HIGH |
| `article_citation_trend` table | BATON 014 design, not yet created in DB | HIGH |
| Cookie refresh | `aafp_cookies.json` has session cookies — re-export before any future scrape run | MEDIUM |
| 1 pre-codon VC_fail no_match | `acute-low-back-imaging...` PDF: ART-ID lookup → codon rename | MEDIUM |
| E2E module tests | M1 `build_crosswalk_index.py`, M3 `build_icd10_tags.py` | MEDIUM |
| Intelligence 2.0 Layer 2 | `article_currency` via PubMed MCP | MEDIUM |
| Right_click DOCX regeneration | 71 DOCXs regenerable via build_summary.js | LOW |
| Scholl PDFs | `scholl_2025_ENCRYPTED_22/23/24.pdf` — need password | LOW |

---

## Next Steps (Ordered)

### 1. AAFP ref matching second pass
578 unmatched refs. Strategy: extract volume+page from AAFP ref string, match against `articles.clean_ref`. For guidelines (GOLD, ACC/AHA, USPSTF), keyword title match against articles. Target: 70-80% match rate.

### 2. Build `aafp_qid_art_xref` table
Schema mirrors `qid_art_xref`:
```sql
CREATE TABLE aafp_qid_art_xref (
    aafp_qid    TEXT NOT NULL,
    article_id  TEXT NOT NULL,
    match_status TEXT,
    PRIMARY KEY (aafp_qid, article_id)
);
```
Populate from `aafp_questions.article_id` (where not null) + second-pass matches.

### 3. AAFP-ITE lag analysis query
```sql
SELECT a.article_id, a.clean_ref,
       MIN(x.exam_year) as first_ite_year,
       MIN(aq.assessment_id) as first_aafp_quiz,
       -- derive AAFP quiz year from assessment_id range
       COUNT(DISTINCT x.exam_year) as ite_citation_count,
       COUNT(DISTINCT aq.aafp_qid) as aafp_citation_count
FROM articles a
JOIN qid_art_xref x ON a.article_id = x.article_id
JOIN aafp_questions aq ON a.article_id = aq.article_id
GROUP BY a.article_id
ORDER BY first_ite_year;
```

### 4. Build the two BATON 014 designed scripts
- `article_citation_trend` table CREATE in DB
- `update_citation_trends.py` (M1/maintain/)
- `extract_ite_critique_refs.py` (M2/scripts/)

### 5. 88 AFP missing articles batch download
CSV: `00_database/readable_db_files/null_clean_ref_missing_articles_20260326.csv`

---

## AAFP Scraper Reference (locked)

**Cookie refresh before each run:**
1. Chrome → log into aafp.org → export cookies → replace `01_module.1_warehouse/aafp_brq/scraper/aafp_cookies.json`

**Run sequence (from Windows, sandbox folder or M1/aafp_brq/scraper/):**
```powershell
set PYTHONIOENCODING=utf-8
pushd C:\Users\mpsch\Desktop\claude_knowledge\00_#PROJECT_OVERHAUL\01_module.1_warehouse\aafp_brq\scraper
python aafp_brq_scraper.py --discover   # → aafp_quiz_map.json
python aafp_brq_scraper.py --scrape     # → ../staging/aafp_brq_staging.json
```

**DO NOT poll the staging file from the VM while the scraper is running** — causes FUSE oplock conflict, freezes Windows write.

**Formula:** `first_q = 49733 + (assessment_id - 13882) * 10`

---

## Git Commit List (stage but do NOT commit — git index.lock issue on Windows)

**New files to stage:**
```
01_module.1_warehouse/aafp_brq/scraper/aafp_brq_scraper.py
01_module.1_warehouse/aafp_brq/scraper/aafp_cookies.json
01_module.1_warehouse/aafp_brq/scraper/aafp_quiz_map.json
01_module.1_warehouse/aafp_brq/scraper/aafp_explore_dump.txt
01_module.1_warehouse/aafp_brq/staging/aafp_brq_staging.json
02_module.2_processor/scripts/aafp_brq_import.py
02_module.2_processor/outputs/citation_gap_list_2024_2025.txt
04_module.4_sandbox/_DELETE_THESE_FROM_WINDOWS.txt
BATON_active_015_20260327_aafp_brq_scraper_built_citation_gap_complete.md
_index.md
CLAUDE.md
01_module.1_warehouse/README.json
auto-memory-copies/ (all updated files)
```

**Files modified:**
```
04_module.4_sandbox/aafp_brq_scraper.py  (old location — delete after commit)
02_module.2_processor/outputs/aafp_brq_staging.json  (old location — delete after commit)
```

**Suggested commit message:**
```
Add AAFP BRQ scraper + import pipeline; 1,221 questions in DB

- aafp_brq_scraper.py v3: discover/scrape/explore modes, resume logic
  with truncated-JSON salvage, FUSE oplock fix documented
- aafp_brq_import.py: staging JSON → aafp_questions table, two-strategy
  ref matching (51% article linkage on first pass)
- M1 reorganization: aafp_brq/ as proper warehouse source (Option B)
- citation_gap_list_2024_2025.txt: 229 unmatched ITE Critique refs
- aafp_questions table: 1,221 rows, separate from questions (ITE)
- _index.md, CLAUDE.md, README.json updated to current state
```

---

## Conventions Locked (cumulative — additions this session)

- **AAFP scraper = Windows-only** (VM proxy blocks outbound HTTPS)
- **aafp_questions = separate table** from `questions` (Option B+C confirmed)
- **aafp_qid format:** `AAFP-{question_id}` (e.g. AAFP-49733)
- **M1/aafp_brq/ = canonical AAFP home** (scraper/ + staging/)
- **DO NOT poll staging file from VM while scraper runs** — FUSE oplock conflict
- **Resume = automatic** — scraper detects and salvages existing output on restart
- All prior conventions from BATON 014 unchanged
