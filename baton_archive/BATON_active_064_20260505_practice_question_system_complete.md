# BATON 064 — Practice Question System Complete
**Date:** 2026-05-05  
**Hash (pre-commit):** 7920979  
**Previous BATON:** BATON_active_063_20260429_report_guides_complete.md

---

## RECON DATA

- New BATON: 064
- Old BATON: BATON_active_063_20260429_report_guides_complete.md
- Date: 2026-05-05
- Git hash (pre-commit): 7920979
- DB: All tables stable — no changes from BATON 063

DB counts:
- articles: 1,998 | questions (ITE): 1,639 | aafp_questions: 1,221
- qid_art_xref: 2,485 | aafp_qid_art_xref: 864
- article_icd10: 4,959 | question_icd10: 5,774 | aafp_question_icd10: 4,753
- clinical_pathways: 4,959 | pubmed_pmid_cache: 344
- article_icd10_vec: 1,757 | question_icd10_vec: 2,747 | icd10_vec: 2,219
- intersection_centroid_vec: 158 | article_currency: 1,998

PDF counts (gitignored — BATON 063 numbers verified intact):
- VC_fail: 630 | VC_pass: 168 | local_lite: 117 | right_click: 58 | AAFP: 15 | ITE Exams: 16 | Total: 988

Script counts (post-session):
- M1 build: 8 py | M1 maintain: 26 py
- M2: 75 py, 6 js
- M3: 55 py (+3 this session), 4 js (unchanged)

---

## SESSION WORK (what was built this session)

### 1. ite_analyzer_v3.py — MODIFIED
- Added `import re`
- Added Symbol-font dot-leader encoding clean at write time in `export_analysis()`
- New: `_DOTLEADER_RE`, `_clean_str()`, `_clean_analysis_encoding()` — runs at JSON export, strips U+F02E/F02D/F02C artifacts before writing
- Uses `chr(0xF02E)` pattern to avoid encoding issues in source file
- Location: `03_module.3_analyst/scripts/ite_analyzer_v3.py`

### 2. build_cole_exam_series.py — NEW
- Cole-specific exam series generator (5 exams × 40 questions each)
- Key feature: merges original 20 practice questions from analysis JSON into pool, clips N least-fitting to maintain exactly 200 total
- Merge logic: builds `all_200_qids` set, finds `missing_from_200`, injects them, clips bottom N from raw_pool
- Result verified: 5 of original 20 injected, 5 clipped, 200-question pool maintained
- Location: `03_module.3_analyst/scripts/build_cole_exam_series.py`

### 3. build_exam_series.py — NEW (generalizes build_cole_exam_series.py)
- CLI args: `--resident-dir`, `--resident-name`, `--pgy`, `--num-exams`, `--questions`, `--seed`
- Auto-discovers analysis JSON via `find_analysis_json()`
- `derive_display_name()` maps dir names like `ITE_okezia_cole` → `Okezia Cole`
- Same merge-inject logic for original report questions
- Output naming: `ITE_<YEAR>_Practice_Exam_<Letter>_<LastName>.docx`
- Location: `03_module.3_analyst/scripts/build_exam_series.py`

### 4. build_custom_question_set.py — NEW (major new system)
- Content-addressable question set generator
- CLI: `--count`, `--blueprint` (repeatable → OR within type), `--body-system` (repeatable → OR within type), `--bank ITE|AAFP|BOTH`, `--years YYYY-YYYY`, `--label`, `--output-dir`, `--seed`
- AND logic across types (blueprint + body_system together = AND); OR within same type (two `--body-system` = OR)
- `build_query()`: UNION SQL across `questions` (ITE) and `aafp_questions` (AAFP), with column aliasing (`aafp_qid as qid`, `stem as question_text`)
- Encoding fixes: `_ENCODING_FIXES` table (14 entries — Symbol font artifacts like `ï‚£`→`≤`, `ï‚³`→`≥`, `ï‚±`→`±`, plus double-encoded Latin chars)
- Reference parsing: `split_explanation_and_refs()` splits at `\nRef:` marker; `parse_references()` handles pipe-separated (newer) and numbered (older) delimiter formats
- Two output products per run:
  - **Exam version**: questions + answer choices + answer key table at end
  - **Study Guide version**: questions + correct answer (navy bold) + explanation body (shaded box) + References section (separate, one citation per paragraph, gray tiny font)
- Footer metadata line includes: bank · year | blueprint | body_system | QID
- Output dir: `03_module.3_analyst/custom_question_sets/YYYY-MM-DD/`
- Rule 14 compliant: uses word_doc_defaults.py
- Location: `03_module.3_analyst/scripts/build_custom_question_set.py`

### 5. ite-exam-series.skill — NEW (Cowork skill)
- Packaged skill for generating exam series from a resident's completed ITE analysis
- SKILL.md: step-by-step guide (parse → locate analysis JSON → run script → report)
- Location: `board_prep_intel/ite-exam-series.skill`

### 6. custom-question-set.skill — NEW (Cowork skill)
- Packaged skill for content-filtered practice question set generation
- SKILL.md: parse bracket notation → glossary lookup → run script → report
- `references/glossary.md`: canonical term mappings with aliases and pool size expectations
- `evals/evals.json`: 4 eval cases covering all filter permutations
- Location: `board_prep_intel/custom-question-set.skill`

### 7. Lexicon additions (user_vocabulary.md memory updated)
- **Exam version**: test-taking output — questions + answer key table, no explanations visible
- **Study Guide version**: learning output — questions + correct answer + full explanation after each

---

## DEFERRED FLAGS

| Flag | Status | Notes |
|------|--------|-------|
| DEFERRED-QID-XREF-LIBRARY-GAPS | Active | 249 unmatched citations; prioritize by frequency |
| DEFERRED-PGY-BENCHMARKS | ~~REMOVED~~ | Not feasible at this time; not critical to progression — dropped 2026-05-05 |
| DEFERRED-PROGRAM-TREND | ~~REMOVED~~ | Not feasible at this time; not critical to progression — dropped 2026-05-05 |

---

## NEXT STEPS

### Immediate
1. **Re-run all 7 resident analyses** on Mac (BATON 063 item, still pending — git pull required to pick up Issues 1-5 + guide scripts)
2. ~~**Repackage custom-question-set.skill**~~ — ✅ Done — skill overwritten with corrected version 2026-05-05

### Short-term
3. **DEFERRED-QID-XREF-LIBRARY-GAPS** — 249 unmatched citations; prioritize by frequency, acquire missing articles

---

## ARCHITECTURE DECISIONS

### Practice Question System Architecture (new this session)
**Decision:** Content-addressable question set generation uses a single Python script (`build_custom_question_set.py`) with a Cowork skill wrapper, bracket notation for user input, and always produces two output products (Exam + Study Guide).

**AND/OR logic:** Multiple values of the same filter type → OR within that dimension. Values of different types (blueprint + body_system) → AND across dimensions. This matches clinical intent: "give me both cardio and respiratory" = OR, "give me acute care questions that are cardio" = AND.

**Reference formatting:** ITE explanation fields embed `Ref:` block at end. The Study Guide splits these at `\nRef:` and renders them as a separate "References" section with one citation per paragraph — preserving the citation information without cluttering the explanation body.

**Encoding clean strategy:** Symbol font artifacts (UTF-8 bytes of private-use-area codepoints misread as Latin-1) are caught at `clean_text()` call time via `_ENCODING_FIXES` lookup table. Dot-leader artifacts (U+F02E etc.) are caught via regex. Both are transparent to the output consumer.

---

## DB STATE (All Stable)

[Same as BATON 063 — no changes]

| Table | Count |
|-------|-------|
| articles | 1,998 |
| questions (ITE) | 1,639 |
| aafp_questions | 1,221 |
| qid_art_xref | 2,485 |
| aafp_qid_art_xref | 864 |
| article_icd10 | 4,959 |
| question_icd10 | 5,774 |
| aafp_question_icd10 | 4,753 |
| clinical_pathways | 4,959 |
| pubmed_pmid_cache | 344 |
| icd10_vec | 2,219 |
| article_icd10_vec | 1,757 |
| question_icd10_vec | 2,747 |
| intersection_centroid_vec | 158 |
| article_currency | 1,998 |

---

## PDF LIBRARY (Gitignored — BATON 063 numbers, verified intact)

| Tier | Count |
|------|-------|
| VC_fail | 630 |
| VC_pass | 168 |
| local_lite | 117 |
| right_click | 58 |
| AAFP | 15 |
| ITE Exams | 16 |
| **Total** | **988** |

---

## MODULE SCRIPT INVENTORY (Post-BATON 064)

| Module | Python | JS | Notes |
|--------|--------|----|-------|
| M1 (Warehouse) | 34 | 0 | 8 build + 26 maintain (unchanged) |
| M2 (Processor) | 75 | 6 | Unchanged |
| M3 (Analyst) | 55 | 4 | +3 py this session (build_cole_exam_series, build_exam_series, build_custom_question_set) |
| M4 (Sandbox) | (varies) | (varies) | Experiments |
| M5 (Web) | 3 | 35 | Sync + TypeScript/TSX |

---

## GIT STATUS

| Item | Value |
|------|-------|
| Branch | main |
| Hash (pre-commit) | 7920979 |
| Modified | ite_analyzer_v3.py, ite_parser.py |
| New (untracked) | build_cole_exam_series.py, build_exam_series.py, build_custom_question_set.py, ite-exam-series.skill, custom-question-set.skill |
| Next action | Commit staged files; user pushes via GitHub Desktop |

---

End BATON 064
