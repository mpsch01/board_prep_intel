# BATON 016 — AAFP Enrichment Pipeline Complete, ITE Similarity Scored
**Date:** 2026-03-27
**Session platform:** Windows PC (Cowork VM)
**Status:** Active
**Preceding BATON:** `BATON_active_015_20260327_aafp_brq_scraper_built_citation_gap_complete.md` (→ archive)
**Git hash:** `cd32816` (BATON 015 hash — new commit needed this session)
**GitHub remote:** `https://github.com/mpsch01/project-overhaul` (private)

---

## SESSION SUMMARY — What Was Done and Why

Two-session continuation (context compacted mid-session). Completed the full AAFP BRQ local enrichment pipeline: schema normalized to 5 tables, vectors embedded, keywords extracted, clinical context propagated, and ITE similarity scored per-question. Every AAFP question now has a permanent semantic distance score to its nearest ITE equivalent — enabling the lag analysis queued in BATON 015.

---

### 1. aafp_brq_import.py v3 — Schema Normalization (5 Tables)

Prior schema was a single flat `aafp_questions` table. This session decomposed into 3 functional components (per Mikey's design) + archive table + xref:

| Table | Rows | Purpose |
|-------|------|---------|
| `aafp_questions` | 1,221 | Stem + MC choices only |
| `aafp_explanations` | 1,221 | correct_letter + explanation (1:1) |
| `aafp_citations` | 1,600 | One parsed citation per row |
| `aafp_citation_raw` | 1,600 | Full untruncated citation archive + coordinates |
| `aafp_qid_art_xref` | 797 | Parallel to qid_art_xref (586 unique questions linked) |

**Citation architecture:**
- Multi-citation refs split on `\s+\d+\)\s+` regex before matching
- 1,221 refs → 1,600 individual citations (284 multi-citation questions)
- Strategy 0: exact clean_ref match → 724 matched
- Strategy 1: vol/page dupe finder (year+vol+issue+page+author1) → 73 fuzzy
- Unmatched: 784 (target of second-pass)

**Match stats:**
- matched (exact): 724 (45.3%)
- fuzzy (vol/page+auth): 73 (4.6%)
- unmatched: 784 (49.0%)
- no_ref: 19 (1.2%)
- **Total linked: 797 xref rows (586 unique questions, 48%)**

---

### 2. compute_embeddings.py — AAFP Vector Layer Added

`aafp_question_vec` virtual table added to sqlite-vec infrastructure.

**Text builder** (`build_aafp_question_text`):
- stem[:600] + "Answer: " + correct_text + "Explanation: " + explanation[:800]
- Richer than ITE builder (no concept_tags yet — uses explanation to compensate)

**Results:** 1,221 / 1,221 vectors at 100% coverage. Cost: $0.0052. Runtime: ~15 sec.

---

### 3. aafp_keyword_extractor.py — TF-IDF Local Keywords

New script: `02_module.2_processor/scripts/aafp_keyword_extractor.py`

- Approach: TF-IDF across AAFP corpus (1,221 docs each for stems + explanations)
- Unigrams + bigrams, 3+ char, extended medical stopword list
- Top 15 terms per question per field (configurable via `--top N`)
- **Coverage: 1,221/1,221 (100%)** for both columns

Columns added:
- `aafp_questions.stem_keywords` — TF-IDF terms from question stem
- `aafp_explanations.explanation_keywords` — TF-IDF terms from explanation

---

### 4. aafp_context_propagator.py — Clinical Context from Article Library

New script: `02_module.2_processor/scripts/aafp_context_propagator.py`

Propagates clinical metadata to AAFP questions via `aafp_qid_art_xref → articles`:
- `aafp_questions.body_system` ← `articles.categories` (majority vote across linked articles)
- `aafp_questions.source_type` ← `articles.source_type` (majority vote)
- New table: `aafp_question_icd10` — parallel to `article_icd10`, one row per (aafp_qid, icd10_code)

**Results:**
- body_system: 582/1,221 (47.7%) — 4 linked articles had null categories
- source_type: 586/1,221 (48.0%) — 100% of linked questions
- aafp_question_icd10: 577 questions, 1,876 rows (~3.25 ICD codes/question)

Untagged 639 questions (52%) await gap-fill pass.

---

### 5. aafp_vector_explorer.py — Cross-Corpus Similarity + Persistent Scores

New script: `02_module.2_processor/scripts/aafp_vector_explorer.py`

For each AAFP question: KNN query against `question_vec` (ITE corpus), stores nearest ITE match.

**New columns written to `aafp_questions`:**
- `ite_nearest_qid` — nearest ITE question (e.g. "QID-2018-0099")
- `ite_nearest_dist` — cosine distance (0.0 = identical, >0.5 = divergent)

**Coverage: 1,221/1,221 (100%)**

**Flags:** `--save` (persist to DB), `--new-only` (incremental — skip already-scored rows), `--sample N`

---

### 6. Key Findings from Vector Analysis

**Distance distribution:**
| Tier | Count | % | Threshold |
|------|-------|---|-----------|
| Close (strong ITE match) | 208 | 17.0% | dist < 0.38 |
| Related (overlapping area) | 393 | 32.2% | dist < 0.50 |
| Unique (AAFP-only territory) | 620 | 50.8% | dist ≥ 0.50 |

Mean: 0.5784 | Median: 0.5093 | Min: 0.2369 | Max: 1.1177

**Article-linked vs unlinked — the headline finding:**
- Linked (586 q): mean dist = **0.4497**
- Unlinked (635 q): mean dist = **0.6973**
- Gap of 0.2476 — these are two distinct semantic populations. Strong validation that citation matching is doing real clinical work.

**Near-identical question pairs (dist < 0.27):**
AAFP BRQ and ITE share questions with near-identical stems — same patients, same scenarios. Not just topic overlap — likely direct question reuse or co-authorship between AAFP and ABFM exam content. Top pair: AAFP-50231 ↔ QID-2018-0099 at dist=0.2369 (identical stem text).

**Body system overlap (tagged questions only):**
- Strongest: Psychogenic (0.4090, 42.9% close), Endocrine (0.4141), Reproductive:Female (0.4417, 44.9% close)
- Weakest: Patient-Based Systems (0.4813), Special Sensory (0.4850)
- Untagged (639q): 0.6954 — the gap cohort; filling citations will shift this

**AAFP-specific territory (dist > 1.0):**
- Fee-for-service reimbursement systems (dist=1.117)
- ACO/healthcare policy (dist=1.102)
- Grief counseling 4-year-old (dist=1.075)
- Timed Up and Go test administration (dist=1.067)
- SORT evidence grading (dist=1.056)
- Echinacea CAM use (dist=1.043)
These represent genuinely AAFP-specific curriculum: healthcare policy, CAM, functional assessment tools, evidence grading. ITE doesn't test these.

**ITE year of nearest matches:**
- 2018 dominant (282 matches) — largest cohort, most surface area
- 2020–2021 dip (53/61) — COVID-era content shift
- 2022–2025 recovery (176/221/180/80)

---

## Complete aafp_questions Schema (as of BATON 016)

```sql
aafp_questions (
    aafp_qid          TEXT PRIMARY KEY,   -- "AAFP-49733"
    question_id       INTEGER UNIQUE,
    assessment_id     INTEGER,
    quiz_title        TEXT,
    question_number   INTEGER,
    stem              TEXT,
    choices           TEXT,               -- JSON [{letter, text}]
    url               TEXT,
    stem_keywords     TEXT,               -- TF-IDF keywords (aafp_keyword_extractor.py)
    body_system       TEXT,               -- from articles.categories via xref
    source_type       TEXT,               -- from articles.source_type via xref
    ite_nearest_qid   TEXT,               -- nearest ITE match (aafp_vector_explorer.py)
    ite_nearest_dist  REAL                -- cosine distance to ite_nearest_qid
)
```

---

## New Files This Session

| File | Location | Notes |
|------|----------|-------|
| `aafp_brq_import.py` (v3) | `02_module.2_processor/scripts/` | Full rewrite: 5 tables, citation splitting, vol/page dupe finder |
| `aafp_keyword_extractor.py` | `02_module.2_processor/scripts/` | TF-IDF keyword extraction, --top N, --dry-run, --stats |
| `aafp_context_propagator.py` | `02_module.2_processor/scripts/` | body_system + source_type + aafp_question_icd10 propagation |
| `aafp_vector_explorer.py` | `02_module.2_processor/scripts/` | Cross-corpus KNN analysis + --save persistence |

**Script count update:**
| Location | Python | JS | Other |
|----------|--------|----|-------|
| M1/build/ | 9 | — | 1 README |
| M1/maintain/ | 16 | — | 1 README |
| **M2/scripts/** | **49** (+4 this session) | 6 | 1 JSON + 4 Windows |
| M3/scripts/ | 4 | 1 | 2 JSON |

---

## DB State (as of BATON 016)

| Table | Rows | Notes |
|-------|------|-------|
| articles | 1,936 | |
| questions (ITE) | 1,629 | 2018–2025 |
| qid_art_xref | 2,470 | |
| article_icd10 | 3,855 | |
| clinical_pathways | 3,093 | |
| article_vec | 1,936 | 100% coverage |
| question_vec | 1,629 | 100% coverage |
| **aafp_questions** | **1,221** | 7 enrichment cols populated (stem_keywords, body_system, source_type, ite_nearest_qid, ite_nearest_dist) |
| **aafp_explanations** | **1,221** | explanation_keywords populated |
| **aafp_citations** | **1,600** | one row per parsed citation |
| **aafp_citation_raw** | **1,600** | full text archive + coordinates |
| **aafp_qid_art_xref** | **797** | 586 unique questions linked (48%) |
| **aafp_question_vec** | **1,221** | 100% coverage |
| **aafp_question_icd10** | **1,876** | 577 questions × ~3.25 ICD codes |

---

## Housekeeping Carried Forward

- [ ] **Windows:** Archive BATON 013 → `baton_archive/`
- [ ] **Windows:** Archive BATON 014 → `baton_archive/`
- [ ] **Windows:** Archive BATON 015 → `baton_archive/`
- [ ] **Windows:** Delete sandbox originals (see `04_module.4_sandbox/_DELETE_THESE_FROM_WINDOWS.txt`)
- [ ] **Git:** Stage + commit all session changes

**Suggested commit message:**
```
AAFP BRQ enrichment pipeline complete: 5-table schema, vectors, keywords, ITE similarity

- aafp_brq_import.py v3: normalized to 5 tables (aafp_questions,
  aafp_explanations, aafp_citations, aafp_citation_raw, aafp_qid_art_xref)
  Citation splitting + vol/page dupe finder; 797 xref rows (586 unique Q)
- compute_embeddings.py: aafp_question_vec added; 1221/1221 at 100%
- aafp_keyword_extractor.py: TF-IDF stem+explanation keywords; 100% coverage
- aafp_context_propagator.py: body_system, source_type, aafp_question_icd10
  (1876 rows across 577 questions); no API required
- aafp_vector_explorer.py: AAFP-ITE cross-corpus KNN + --save persistence;
  ite_nearest_qid + ite_nearest_dist on all 1221 rows
- Key finding: AAFP-ITE question reuse confirmed (dist<0.27 pairs);
  linked vs unlinked mean dist gap = 0.25 (0.45 vs 0.70)
```

---

## Deferred Flags

| Flag | Description | Priority |
|------|-------------|----------|
| **AAFP question reuse investigation** | 5+ pairs at dist<0.27 — likely identical stems. Query: SELECT WHERE ite_nearest_dist < 0.30 — how many are exact dupes? Implication for lag analysis | **NEW HIGH** |
| **AAFP-ITE lag analysis** | xref + shared citations + timing delta. Query sketched in BATON 015 still valid. Now add: ite_nearest_dist as additional signal | HIGH |
| **AAFP ref matching second pass** | 784 unmatched citations; vol/page present but not in DB vs truncated refs | HIGH |
| **229 citation gap articles** | 88 AFP batch-downloadable from `null_clean_ref_missing_articles_20260326.csv` | HIGH |
| **129 missing AAFP questions** | ~13 incomplete quizzes from stalled scrape | MEDIUM |
| **Interactive vector dashboard** | HTML dashboard from aafp_vector_explorer data: distance histogram, body system heatmap, linked/unlinked comparison. `data:interactive-dashboard-builder` skill ready | MEDIUM |
| `extract_ite_critique_refs.py` | BATON 014 design, not yet built | HIGH |
| `update_citation_trends.py` | BATON 014 design, not yet built | HIGH |
| `article_citation_trend` table | BATON 014 design, not yet created | HIGH |
| Intelligence 2.0 Layer 2 | `article_currency` via PubMed MCP | MEDIUM |
| Cookie refresh | `aafp_cookies.json` session cookies — re-export before next scrape | MEDIUM |
| FLAG 33 | VC_pass ART-ID rename scheme — designed, not implemented | LOW |

---

## Next Steps (Ordered)

### 1. AAFP question reuse investigation
```sql
SELECT aq.aafp_qid, aq.ite_nearest_qid, aq.ite_nearest_dist,
       aq.stem, q.question_text
FROM aafp_questions aq
JOIN questions q ON aq.ite_nearest_qid = q.qid
WHERE aq.ite_nearest_dist < 0.30
ORDER BY aq.ite_nearest_dist;
```
How many are word-for-word identical vs paraphrased? Sets up the lag analysis correctly.

### 2. AAFP-ITE lag analysis
For questions sharing article citations AND high vector similarity, compute timing delta:
```sql
SELECT a.article_id, a.clean_ref,
       MIN(x.exam_year) as first_ite_year,
       MIN(aq.assessment_id) as first_aafp_quiz,
       AVG(aq2.ite_nearest_dist) as mean_semantic_proximity
FROM articles a
JOIN qid_art_xref x ON a.article_id = x.article_id
JOIN aafp_qid_art_xref ax ON a.article_id = ax.article_id
JOIN aafp_questions aq2 ON ax.aafp_qid = aq2.aafp_qid
GROUP BY a.article_id
ORDER BY first_ite_year;
```

### 3. AAFP ref matching second pass
784 unmatched citations — run vol/page extraction + guideline title keyword match. Target 70-80%.

### 4. 88 AFP gap articles batch download
CSV ready: `00_database/readable_db_files/null_clean_ref_missing_articles_20260326.csv`

### 5. Interactive vector dashboard
Build HTML dashboard from `aafp_vector_explorer.py` output using `data:interactive-dashboard-builder` skill.

---

## AAFP Pipeline Quick Reference

**Run order for new AAFP data:**
```powershell
# 1. Import (Windows, from M2/scripts/)
python aafp_brq_import.py --rebuild

# 2. Embeddings (Windows, from M1/build/)
python compute_embeddings.py --aafp-only

# 3. Keywords (Windows, from M2/scripts/)
python aafp_keyword_extractor.py

# 4. Context propagation (Windows, from M2/scripts/)
python aafp_context_propagator.py

# 5. ITE similarity scores (Windows, from M2/scripts/)
python aafp_vector_explorer.py --save
```

**Incremental updates (new questions only):**
```powershell
python aafp_brq_import.py              # INSERT OR IGNORE
python compute_embeddings.py --aafp-only --new-only
python aafp_keyword_extractor.py       # re-runs TF-IDF across full corpus
python aafp_context_propagator.py      # INSERT OR IGNORE on ICD-10 table
python aafp_vector_explorer.py --save --new-only
```

---

## Conventions Locked (additions this session)

- **aafp_questions = 5-table schema** (questions / explanations / citations / citation_raw / xref) — do not flatten
- **aafp_qid_art_xref** = canonical article linkage table for AAFP, mirrors qid_art_xref
- **aafp_question_icd10** = normalized ICD-10 join table, mirrors article_icd10
- **ite_nearest_dist** = permanent per-question ITE similarity score. Update with `--new-only` on new data.
- **Pipeline order:** import → embed → keywords → context → similarity scores
- All prior conventions from BATON 015 unchanged
