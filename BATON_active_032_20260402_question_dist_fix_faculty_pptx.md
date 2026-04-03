# BATON 032 — QUESTION-DIST-001 Fix + Faculty Presentation PPTX
**Date:** 2026-04-02
**Session:** Practice question distribution bug fixed; faculty meeting deck built and QA'd
**Status:** QUESTION-DIST-001 CLOSED. PPTX delivered. Git committed. PRESENTATION flag CLOSED.
**Replaces:** BATON_active_031_20260401_aafp_qa_docs.md

---

## What Was Done This Session

### 1. QUESTION-DIST-001 — FIXED ✅
**Script:** `03_module.3_analyst/scripts/ite_analyzer_v3.py`
**Root cause:** `_compute_relevance` used `priority_score` as a raw multiplier. "Acute Care" had a priority_score of 33.6 (high exam weight × many missed items) vs ≤ 6.8 for all other dimensions. Relevance scores: Acute Care ≈ 101.8, all others ≤ 21.4 → all 20 practice question slots monopolized by one dimension.

**Fix location:** `match_practice_questions_v3()` — replaced final `return ranked[:target_count]` with a 25-line dimension diversity cap:
- Cap per dimension = `ceil(target / n_active_dims)` (ceiling division, min 2)
- With 8 active dims and target 20 → cap = 3 per dimension
- Overflow candidates fill remaining slots in relevance order after diverse slots are filled

**Smoke test — Hopkins 2025 (post-fix):**
- Distribution: 3× Acute Care, 3× Injuries/MSK, 3× Emergent/Urgent, 3× Respiratory, 3× Cross-tab dims, 2× Sexual/Repro (+ other dims)
- `T1:20 T2:0 T3:0` — all questions matched at Tier 1 (direct DB match)
- Spans 4+ blueprint types ✅

**Important note on BATON 031 attribution:** BATON 031 listed `BODYSYSTEM_PDF_TO_DB` map as the suspected cause. That was incorrect — the map was fine. Root cause was the priority scoring monopoly in `_compute_relevance`, not the dimension lookup.

---

### 2. Git Commit — `279049a`
Staged and committed:
- `03_module.3_analyst/scripts/ite_analyzer_v3.py` (QUESTION-DIST-001 fix)
- BATON 031 archived to `baton_archive/`

Previous uncommitted files from BATON 029–031 (listed in BATON 031 Next Steps) still need staging. They exist in the repo working tree but were not part of this commit. Add in next session:
```
git add 03_module.3_analyst/scripts/ite_analyze_v2.py
git add 03_module.3_analyst/scripts/ite_analyzer_v2.py
git add 03_module.3_analyst/scripts/ite_report_builder_v2.js
git add 03_module.3_analyst/scripts/export_aafp_ite_relationships.py
git add 03_module.3_analyst/scripts/word_doc_defaults.py
git add 03_module.3_analyst/scripts/build_aafp_qa.py
git add 03_module.3_analyst/scripts/build_aafp_qa_file1.py
git add 03_module.3_analyst/scripts/build_faculty_pptx.js
```

---

### 3. Faculty Meeting Presentation — BUILT + QA'd ✅
**Script:** `03_module.3_analyst/scripts/build_faculty_pptx.js` (PptxGenJS)
**Output:** `03_module.3_analyst/reports/ITE_Intelligence_FacultyPresentation_2025.pptx`
**Audience:** Faculty peers (not leadership). Goal: show-and-tell + demo. 5–10 min.

**7-slide structure:**
| Slide | Title | Key Content |
|-------|-------|-------------|
| 1 | Title | ITE Intelligence System — dark navy + gold bar motif |
| 2 | The Problem | 191 questions / 14 body systems / 5 blueprints → single number |
| 3 | What We Built | 2,850 Questions / 1,985 Articles / 4,137 ICD-10 tags |
| 4 | How It Works | 4-step flow: Upload → Parse → Identify → Match |
| 5 | Live Example | Hopkins 65.4% — score breakdown + post-fix dimension distribution bar chart |
| 6 | The Deliverables | Analysis Report card + Practice Exam card (feature lists) |
| 7 | What's Next | LIVE × 3 + BUILDING × 1 status rows |

**QA fixes applied (v1 → v2):**
1. Slide 3: Replaced `"ICD-10\n+ Pathways"` (huge awkward text) with `"4,137"` (ICD-10 article tag count) — now consistent stat callout across all 3 cards
2. Slide 5: Bar chart updated to post-fix distribution (3 per dim, 6 dims shown, max scale corrected from `/8` to `/3`)
3. Slide 6: Removed emoji `📋` and `📝` from card headers — were rendering as `?` boxes in LibreOffice
4. Slide 7: Replaced `✅` and `🔄` with plain text `LIVE` / `BUILDING` in gold — clean, high contrast

**Design conventions used:**
- St. Luke's palette: NAVY `1B3564`, GOLD `C8922A`, BLUE `2E5F9C`
- Gold left-bar motif on all content slides, dark navy sandwich (title + closing slides)
- `makeShadow()` factory function (never reused objects)
- No accent lines under titles
- PptxGenJS — `bullet: true` (not unicode), no `#` in hex colors

---

## DB State (unchanged this session)

| Table | Rows | Notes |
|-------|------|-------|
| articles | 1,985 | ART-0001 → ART-1986; next = ART-1987 |
| questions (ITE) | 1,629 | blueprint 100% |
| questions (AAFP) | 1,221 | blueprint 100% |
| qid_art_xref | 2,470 | |
| aafp_qid_art_xref | 864 | |
| article_icd10 | 4,137 | |
| question_icd10 | 5,284 | |
| aafp_question_icd10 | 4,753 | |
| clinical_pathways | 4,020 | |
| icd10_vec | 2,219 | |
| article_icd10_vec | 1,674 | rebuilt BATON 030 |
| question_icd10_vec | 2,733 | rebuilt BATON 030 |
| pubmed_pmid_cache | 344 | Layer 2 seed |
| PDFs | 404 | 49 AAFP articles awaiting download |
| Next ART-ID | ART-1987 | |
| Git | main, `279049a` | partial — 8 files still unstaged (see above) |

---

## Deferred Flags

| Flag | Description | Priority |
|------|-------------|----------|
| GIT-PENDING | 8 scripts from BATON 029–031 still need `git add` + commit | **High** |
| DEFERRED-A | PDF download: 49 AAFP articles ART-1938–1986 | High |
| DEFERRED-B | `update_citation_trends.py` — run AFTER DEFERRED-A | Medium |
| DEFERRED-C | AAFP vs ITE trend comparison | Medium |
| DEFERRED-D | 229 citation gap articles (88 AFP batch-downloadable) | Medium |
| DEFERRED-E | Interactive vector dashboard | Low |
| DEFERRED-F | Intelligence 2.0 Layer 2 — `article_currency` via PubMed (344 PMIDs cached) | Medium |
| Q-VEC-GAP | Fill question_vec: 440 ITE (2018–2019) + 1,221 AAFP | Medium |

**Closed this session:** QUESTION-DIST-001 ✅, PRESENTATION ✅

---

## Next Steps (priority order)

1. **Git commit (GIT-PENDING)** — stage and commit the 8 scripts listed above
2. **PDF download (DEFERRED-A)** — `download_aafp_acquisitions.py` → `backfill_new_article_metadata.py --art-id-min 1938`
3. **Citation trends (DEFERRED-B)** — run after DEFERRED-A
4. **Intelligence 2.0 Layer 2** — `article_currency` table via PubMed (344 PMIDs in `pubmed_pmid_cache`)
5. **Fill question vector gaps (Q-VEC-GAP)** — embed 440 ITE (2018–2019) + 1,221 AAFP → `question_vec`

---

## Files Changed This Session

| File | Action |
|------|--------|
| `03_module.3_analyst/scripts/ite_analyzer_v3.py` | MODIFIED — dimension diversity cap in `match_practice_questions_v3()` |
| `03_module.3_analyst/scripts/build_faculty_pptx.js` | NEW — PptxGenJS faculty presentation builder |
| `03_module.3_analyst/reports/ITE_Intelligence_FacultyPresentation_2025.pptx` | NEW — 7-slide faculty deck |
| `baton_archive/BATON_active_031_*.md` | ARCHIVED |
| `BATON_active_032_*.md` | This file |
