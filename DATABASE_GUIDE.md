# ITE Intelligence Database Guide

**Database:** `00_database/db/ite_intelligence.db`
**Engine:** SQLite 3 (with optional `sqlite-vec` extension for vector search)
**Schema version:** v2 (rebuilt 2026-03-10; AAFP corpus added 2026-03-29)
**Last updated:** 2026-04-08 (BATON 048)

---

## Part 1 — Database Contents

The database is organized into five functional groups:

1. **Core content** — articles, questions, and question-article junction tables
2. **ICD-10 diagnostic layer** — per-article and per-question diagnostic code assignments
3. **Clinical intelligence layer** — pathways, citation trends, PubMed seed
4. **ICD-10 taxonomy** — code hierarchy (specific → parent)
5. **Vector embeddings** — dense semantic representations for similarity search

---

### 1.1 Core Content Tables

#### `articles` — 1,985 rows

The central reference library. One row per unique clinical guideline, journal article, or other source that has been cited in the explanation of at least one ABFM ITE or AAFP BRQ question (plus 30 legitimate "orphans" imported from tier lists but never directly cited).

**Primary key:** `clean_ref` (TEXT) — the original cleaned citation string. Stable and used as the FK throughout legacy join paths.
**Secondary key:** `article_id` (TEXT, UNIQUE) — short ID in format `ART-NNNN` (zero-padded, e.g. `ART-0470`).

| Key Column | Type | Description |
|---|---|---|
| `clean_ref` | TEXT PK | Full citation text — the durable, human-readable identifier |
| `article_id` | TEXT UNIQUE | Short stable ID: `ART-0001` through `ART-1986` |
| `author1`, `author2` | TEXT | Parsed author surnames used to build filenames |
| `year` | TEXT | Publication year |
| `canonical_filename` | TEXT | `Author1_Author2_Year` — base filename without extension |
| `codon_filename` | TEXT | `Author1_Author2_Year#@#ART-XXXX@#@.pdf` — the durable PDF link |
| `tier` | TEXT | Pipeline staging: `VC_fail` / `VC_pass` / `local_lite` / `right_click` |
| `source_type` | TEXT | Content class: `afp`, `guideline`, `uspstf`, `rct`, `review`, `stub`, … |
| `engine_type` | TEXT | Clinical function: `acute_protocol`, `chronic_guideline`, `preventive_guideline`, `diagnostic_guideline`, `rct` |
| `citation_count` | INTEGER | Number of distinct ITE questions that cited this article |
| `unique_years` | INTEGER | Number of distinct exam years in which this article was cited |
| `exam_years` | TEXT | JSON array of exam years (e.g. `[2021, 2022, 2024]`) |
| `blueprint` | TEXT | ABFM blueprint category (Acute / Chronic / Emergent / Preventive / Foundations) |
| `body_system` | TEXT | ABFM body system category |
| `concept_tags` | TEXT | Claude-preprocessed JSON: diagnoses, drugs, procedures, concept summary |

**Tier system:**

| Tier | Count | Meaning |
|------|-------|---------|
| `VC_fail` | 1,448 | Not in VC gate — lower priority; awaiting pipeline |
| `VC_pass` | 362 | Passed VC gate — high-yield; awaiting pipeline |
| `local_lite` | 117 | Pipeline complete: VC_fail + DOCX exists |
| `right_click` | 58 | Pipeline complete: VC_pass + DOCX exists — highest priority |

The **VC gate** (`key_data_files/session_hy_inserts_v7.json`, 352 citations from the AAFP Board Prep Video Course) is the sole criterion for `VC_pass` vs. `VC_fail`. DB membership alone is not sufficient for `right_click` status.

---

#### `questions` — 1,629 rows

All ABFM In-Training Exam questions from 2018–2025.

**Primary key:** `qid` (TEXT) — format `QID-YYYY-NNNN`, e.g. `QID-2024-0042`.

| Key Column | Type | Description |
|---|---|---|
| `qid` | TEXT PK | Per-year format: `QID-{year}-{nnnn}` |
| `exam_year` | INTEGER | 2018–2025 |
| `question_text` | TEXT | Full question stem |
| `choices` | TEXT | JSON array of answer choices |
| `correct_answer` | TEXT | Correct answer letter |
| `explanation` | TEXT | Full explanation text |
| `body_system` | TEXT | ABFM original body system label |
| `body_system_merged` | TEXT | Normalized label — maps 2024 renames back to historical equivalents; **always use this for trend queries** |
| `blueprint` | TEXT | ABFM blueprint category (100% filled via Claude Batch API) |
| `concept_tags` | TEXT | Claude-preprocessed JSON with `diagnoses`, `drugs`, `procedures`, `concept_summary` |

---

#### `aafp_questions` — 1,221 rows

Questions from the AAFP's online Board Review course — a parallel question bank used as a priority filter and for cross-corpus analysis. Schema is parallel to ITE questions.

**Primary key:** `aafp_qid` (TEXT) — format `AAFP-NNNN`.

| Key Column | Type | Description |
|---|---|---|
| `aafp_qid` | TEXT PK | `AAFP-NNNN` format |
| `stem` | TEXT | Question stem |
| `choices` | TEXT | JSON array of answer choices |
| `correct_letter` | TEXT | Correct answer letter (`A`–`E`) |
| `correct_text` | TEXT | Correct answer full text |
| `explanation` | TEXT | Plain-text explanation |
| `body_system` | TEXT | Body system category |
| `blueprint` | TEXT | ABFM blueprint category (100% filled) |
| `concept_tags` | TEXT | Same schema as ITE `concept_tags` |
| `ite_nearest_qid` | TEXT | Nearest ITE question by vector distance |
| `ite_nearest_dist` | REAL | Vector distance to nearest ITE question (38 pairs ≤ 0.30 = likely direct reuse) |

---

#### `question_ref_pairs` — 2,673 rows

The canonical junction table. One row per question-article citation: "question Q cited article A in its explanation." This is the source-of-truth for the Q↔A relationship, using the stable `clean_ref` primary key.

**Primary key:** `id` (INTEGER AUTOINCREMENT)

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Auto-assigned row ID |
| `qid` | TEXT | FK → `questions.qid` |
| `clean_ref` | TEXT | FK → `articles.clean_ref` |
| `match_status` | TEXT | `matched` / `new` / `unmatched` / `fuzzy_matched` / `partial` |
| `tier` | TEXT | Article tier at time of import |
| `exam_year` | INTEGER | Denormalized exam year |

**match_status distribution:**

| Status | Count | Meaning |
|---|---|---|
| `matched` | 1,698 | Clean exact match |
| `new` | 389 | Added in most recent rebuild cycle |
| `unmatched` | 246 | Could not confidently link |
| `fuzzy_matched` | 154 | Fuzzy string matching resolved the link |
| `fuzzy` | 120 | Legacy label from earlier build |
| `partial` | 66 | Some ambiguity remains |

---

#### `qid_art_xref` — 2,470 rows

Ergonomic crossref table. Mirrors `question_ref_pairs` but uses `article_id` (short, readable) instead of `clean_ref` (long citation text). Excludes unmatched/partial pairs — row count (2,470) is lower than `question_ref_pairs` (2,673) for this reason.

**Primary key:** `(qid, article_id)` composite

Use this table for queries that join questions to articles by `article_id`. Use `question_ref_pairs` when you need `match_status`, `match_score`, or `ref_raw`.

---

#### `aafp_qid_art_xref` — 864 rows

Parallel crossref table for AAFP questions. Maps AAFP BRQ questions to articles via `article_id`.

**Primary key:** `(aafp_qid, article_id)` composite
**Coverage:** 643 unique AAFP questions linked (52.7% of 1,221)

---

#### `aafp_citations` — 1,600 rows

One row per individual parsed citation from AAFP question explanations. Multi-citation references are split (e.g. `AAFP-49733-C1`, `AAFP-49733-C2`).

| Column | Type | Description |
|---|---|---|
| `citation_id` | TEXT PK | e.g. `AAFP-49733-C1` |
| `aafp_qid` | TEXT | FK → `aafp_questions.aafp_qid` |
| `citation_seq` | INTEGER | Sequence number within the question |
| `article_id` | TEXT | FK → `articles.article_id` (NULL if unmatched) |
| `match_status` | TEXT | `matched` / `unmatched` / `partial` |
| `unmatched_class` | TEXT | Classification of why citation didn't match |

---

#### `aafp_citation_raw` — 1,600 rows

Raw untruncated citation text archive. Parallel to `aafp_citations` — preserves the original unparsed text.

---

### 1.2 ICD-10 Diagnostic Layer

#### `article_icd10` — 4,020 rows

ICD-10 diagnostic codes assigned to each article (Layer 1). Each article can have primary, secondary, and related codes, assigned via Claude Batch API.

**Primary key:** `(article_id, icd10_code)` composite

| Column | Description |
|---|---|
| `article_id` | FK → `articles.article_id` |
| `icd10_code` | Specific ICD-10 code (e.g. `E11.9`) |
| `icd10_desc` | Code description |
| `relevance` | `primary` / `secondary` / `related` |

---

#### `question_icd10` — 5,218 rows

ICD-10 codes assigned to each ITE question, propagated from linked articles. Covers 1,512 / 1,629 ITE questions (92.8%).

**Primary key:** `(qid, icd10_code)` composite

Relevance distribution: primary=2,725 / secondary=1,627 / related=932

---

#### `aafp_question_icd10` — 4,753 rows

ICD-10 codes for AAFP BRQ questions, propagated from linked articles. Covers 1,210 / 1,221 AAFP questions (99.1%).

**Primary key:** `(aafp_qid, icd10_code)` composite

---

### 1.3 ICD-10 Taxonomy

#### `icd10_rollup` — 614 rows

3-character parent categories (e.g. `E11` = Type 2 diabetes mellitus) with pre-computed article counts and chapter.

**Primary key:** `parent_code` (TEXT)

| Column | Description |
|---|---|
| `parent_code` | 3-char ICD-10 parent (e.g. `E11`) |
| `parent_desc` | Description |
| `chapter` | ICD-10 chapter (e.g. "Endocrine, nutritional and metabolic diseases") |
| `article_count` | Pre-computed count of linked articles |

---

#### `icd10_code_xref` — 1,006 rows

Maps each specific ICD-10 code (e.g. `E11.9`) to its 3-character parent (e.g. `E11`).

**Primary key:** `icd10_code` (TEXT)

---

### 1.4 Clinical Intelligence Layer

#### `clinical_pathways` — 3,971 rows

Maps each (article, ICD-10 code) pair to a **pathway role** — the clinical function this article serves for that condition. Built deterministically at zero API cost from ABFM subcategory data and engine_type classification.

**Primary key:** `(article_id, icd10_code)` composite

| Column | Description |
|---|---|
| `article_id` | FK → `articles.article_id` |
| `icd10_code` | Specific ICD-10 code |
| `icd10_desc` | Code description |
| `pathway_role` | One of 7 roles (see below) |
| `blueprint` | ABFM blueprint category from linked questions |
| `source_bank` | `ITE` / `AAFP` / `both` — which question bank drives this pathway |
| `relevance` | `primary` / `secondary` / `related` (from article_icd10) |
| `confidence` | All rows currently `high` |

**Pathway roles:**

| Role | Clinical meaning |
|---|---|
| `screening_prevention` | Screening criteria, risk tools, prevention protocols |
| `diagnosis` | Diagnostic criteria, sensitivity/specificity, staging systems |
| `first_line` | Initial treatment, always appropriate early step |
| `second_line` | RCT-tested alternatives, escalation when first-line fails |
| `monitoring` | Lab intervals, titration protocols, red flags |
| `referral` | When to refer out, specialist criteria |
| `special_pops` | Pediatric, geriatric, pregnant, renal-adjusted dosing |

---

#### `article_citation_trend` — 1,740 rows

Pre-computed longitudinal citation data for each article that has ever appeared in `qid_art_xref`. Rebuilt on demand via `update_citation_trends.py`.

**Primary key:** `article_id` (TEXT)

| Column | Description |
|---|---|
| `article_id` | FK → `articles.article_id` |
| `years_cited` | Comma-separated list of exam years |
| `distinct_year_count` | Number of distinct exam years cited |
| `first_cited_year` | Earliest exam year |
| `most_recent_year` | Latest exam year |
| `consecutive_streak` | Longest run of consecutive exam years |
| `is_watch_list` | `1` if `consecutive_streak ≥ 2` — signals persistent exam relevance |

---

#### `pubmed_pmid_cache` — 344 rows

Seed table for Intelligence 2.0 Layer 2 (article currency). Maps AAFP `citation_id` values to PubMed PMIDs for freshness checking.

**Primary key:** `citation_id` (TEXT)

| Column | Description |
|---|---|
| `citation_id` | e.g. `AAFP-49863-C1` — links to `aafp_citations.citation_id` |
| `pmid` | PubMed ID |
| `lookup_date` | Date PMID was retrieved |
| `mesh_count` | Number of MeSH terms on the PubMed record |

---

### 1.5 Vector Embeddings

All embedding tables use OpenAI `text-embedding-3-small` (1536 dimensions).

**Tables requiring `sqlite-vec` extension (virtual tables):**

| Table | Rows | Key | What is embedded |
|---|---|---|---|
| `article_vec` | 1,985 | `article_id` | Article title + org + year |
| `question_vec` | 1,629 | `qid` | Question stem + concept summary |
| `aafp_question_vec` | 1,221 | `aafp_qid` | AAFP question stem + concept summary |

**Plain BLOB tables (no extension needed):**

| Table | Rows | Key | What is embedded |
|---|---|---|---|
| `icd10_vec` | 2,219 | `icd10_code` | ICD-10 code description |
| `article_icd10_vec` | 1,757 | `article_id` | Article's assigned ICD-10 code descriptions |
| `question_icd10_vec` | 2,747 | `qid`/`aafp_qid` + `source_bank` | Question's assigned ICD-10 code descriptions |

---

## Part 2 — Table Linkages

### 2.1 Entity Relationship Diagram

```
articles (1,985)
    │
    ├─── clean_ref ──────── question_ref_pairs (2,673) ──── qid ──── questions / ITE (1,629)
    │                         (canonical junction — match_status)
    │
    ├─── article_id ─────── qid_art_xref (2,470) ──────── qid ──── questions / ITE (1,629)
    │                         (ergonomic xref — no unmatched pairs)
    │
    ├─── article_id ─────── aafp_qid_art_xref (864) ────── aafp_qid ── aafp_questions (1,221)
    │
    ├─── article_id ─────── article_icd10 (4,020) ────────── icd10_code ─┐
    │                                                                      │
    ├─── article_id ─────── clinical_pathways (3,971) ────── icd10_code  │
    │                          (pathway_role + source_bank)               │
    │                                                                      ▼
    ├─── article_id ─────── article_citation_trend (1,740)    icd10_code_xref (1,006)
    │                                                                      │
    └─── article_vec (1,985) ← sqlite-vec virtual table                   ▼
                                                              icd10_rollup (614)

questions / ITE (1,629)
    ├─── qid ──────────── question_icd10 (5,218) ─── icd10_code ─── icd10_code_xref ─── icd10_rollup
    └─── question_vec (1,629) ← sqlite-vec virtual table

aafp_questions (1,221)
    ├─── aafp_qid ─────── aafp_question_icd10 (4,753) ─── icd10_code ─── icd10_code_xref ─── icd10_rollup
    ├─── aafp_qid ─────── aafp_citations (1,600) ─────── citation_id ─── pubmed_pmid_cache (344)
    └─── aafp_question_vec (1,221) ← sqlite-vec virtual table

ICD-10 embeddings (no extension needed):
    icd10_vec (2,219) · article_icd10_vec (1,757) · question_icd10_vec (2,747)
```

---

### 2.2 Primary Key Conventions

| Table | Primary Key | Type | Notes |
|---|---|---|---|
| `articles` | `clean_ref` | TEXT | Full citation string; long but stable |
| `articles` | `article_id` | TEXT UNIQUE | `ART-NNNN` — ergonomic, use for new joins |
| `questions` | `qid` | TEXT | `QID-YYYY-NNNN` |
| `aafp_questions` | `aafp_qid` | TEXT | `AAFP-NNNN` |
| `question_ref_pairs` | `id` | INTEGER | Auto-increment |
| `qid_art_xref` | `(qid, article_id)` | composite | |
| `aafp_qid_art_xref` | `(aafp_qid, article_id)` | composite | |
| `article_icd10` | `(article_id, icd10_code)` | composite | |
| `question_icd10` | `(qid, icd10_code)` | composite | |
| `aafp_question_icd10` | `(aafp_qid, icd10_code)` | composite | |
| `clinical_pathways` | `(article_id, icd10_code)` | composite | |
| `icd10_rollup` | `parent_code` | TEXT | 3-char ICD-10 |
| `icd10_code_xref` | `icd10_code` | TEXT | Specific ICD-10 code |
| `article_citation_trend` | `article_id` | TEXT | |
| `pubmed_pmid_cache` | `citation_id` | TEXT | e.g. `AAFP-49863-C1` |

**SQLite note:** No foreign key constraints are enforced (`PRAGMA foreign_keys` is OFF by default). All joins are by convention. Do not assume referential integrity is automatically maintained.

---

### 2.3 The Two Article↔Question Join Paths

There are two ways to join questions to articles. Choose based on what you need:

**Path A — via `question_ref_pairs` (canonical, uses `clean_ref`):**
```sql
SELECT q.qid, q.exam_year, q.question_text, a.article_id, p.match_status
FROM questions q
JOIN question_ref_pairs p ON q.qid = p.qid
JOIN articles a ON p.clean_ref = a.clean_ref
WHERE a.article_id = 'ART-0470';
```
Use this when you need `match_status`, `match_score`, or `ref_raw` from the pairs table.

**Path B — via `qid_art_xref` (ergonomic, uses `article_id`):**
```sql
SELECT q.qid, q.exam_year, q.body_system_merged, q.question_text
FROM questions q
JOIN qid_art_xref x ON q.qid = x.qid
WHERE x.article_id = 'ART-0470'
ORDER BY q.exam_year;
```
Use this for most analytical queries — shorter, more readable, excludes unmatched/partial rows.

---

### 2.4 Full ICD-10 Join Chain

From a broad condition category down to linked exam questions:

```sql
-- All ITE questions linked to a 3-char ICD-10 parent (e.g. E11 = Type 2 DM)
SELECT r.parent_code, r.parent_desc,
       q.qid, q.exam_year, q.blueprint, q.body_system_merged
FROM icd10_rollup r
JOIN icd10_code_xref cx ON r.parent_code = cx.parent_code
JOIN article_icd10 ai ON cx.icd10_code = ai.icd10_code
JOIN articles a ON ai.article_id = a.article_id
JOIN qid_art_xref x ON a.article_id = x.article_id
JOIN questions q ON x.qid = q.qid
WHERE r.parent_code = 'E11'
ORDER BY q.exam_year;
```

---

### 2.5 Clinical Pathway Join Pattern

From condition → article pathway role → linked exam questions:

```sql
SELECT cp.pathway_role, a.canonical_filename, a.engine_type,
       q.qid, q.exam_year, q.blueprint
FROM clinical_pathways cp
JOIN articles a ON cp.article_id = a.article_id
JOIN qid_art_xref x ON a.article_id = x.article_id
JOIN questions q ON x.qid = q.qid
WHERE cp.icd10_code LIKE 'I10%'   -- Hypertension
ORDER BY cp.pathway_role, q.exam_year;
```

---

## Part 3 — How Linkages Are Currently Used

### 3.1 M2 Enrichment Pipeline (article → enriched DOCX)

**What it uses:** `articles`, `question_ref_pairs`, `qid_art_xref`, `questions`

When a PDF is processed through the right-click or batch enrichment pipeline:

1. **Lookup** (`lookup_article()`): Parse the `ART-ID` from the codon filename (`#@#ART-XXXX@#@`). Match to `articles.article_id`.
2. **ITE Intelligence block** (`build_ite_intelligence()`): Join `articles → qid_art_xref → questions` to retrieve all exam questions that have ever cited this article, with their exam year, body system, concept tags, and blueprint. This list is passed to Claude to generate the `ite_intelligence{}` block in the enriched JSON.
3. **TF-IDF scoring** (`_compute_concept_tfidf()`): Across all linked questions, compute how specific each concept (diagnosis, drug, procedure) is to this article vs. the full question bank. Colors concept tags green (article-specific) / yellow / red (broadly tested).
4. **DOCX output**: Build summary DOCX that includes the ITE Intelligence section — how many questions, in which years, testing which concepts.

The article-question linkage is what transforms a static PDF into an **exam-aware document**.

---

### 3.2 M3 Resident Score Analysis (ITE report builder)

**What it uses:** `questions`, `question_icd10`, `article_icd10`, `clinical_pathways`, `qid_art_xref`, `articles`

When an ABFM score report PDF is parsed:

1. **Missed question identification**: Parser extracts QIDs for questions the resident answered incorrectly.
2. **Article linkage**: Join `qid_art_xref` → `articles` to find which clinical references underlie the missed questions.
3. **ICD-10 linkage**: Join `question_icd10` → `icd10_code_xref` → `icd10_rollup` to group missed questions by clinical category for pattern recognition.
4. **Clinical pathway context**: Join to `clinical_pathways` to show not just what topic was missed, but which clinical function (screening vs. diagnosis vs. treatment) the resident is weakest in.
5. **Citation trend context**: Join `article_citation_trend` to flag articles on a multi-year streak — missed questions backed by persistently tested articles are highest-priority review items.

The result: a per-resident DOCX report that maps score deficits to specific articles, clinical pathways, and exam year trends.

---

### 3.3 Cross-Corpus Comparison (ITE ↔ AAFP)

**What it uses:** `qid_art_xref`, `aafp_qid_art_xref`, `articles`, `question_vec`, `aafp_question_vec`

1. **Shared article analysis**: An article cited by both ITE and AAFP questions appears in both `qid_art_xref` and `aafp_qid_art_xref`. Articles cited in both banks are the most multiply-validated high-yield references.
2. **Vector similarity**: `question_vec` and `aafp_question_vec` (sqlite-vec) are used to find nearest-neighbor question pairs across banks. The 38 near-identical pairs (distance ≤ 0.30) suggest direct question reuse between AAFP BRQ and ABFM ITE — meaning AAFP prep directly maps to ITE performance.
3. **Body system + blueprint overlay**: Both corpora share the same body system and blueprint taxonomy, enabling direct distribution comparisons (`body_system_merged`, `blueprint`).

---

### 3.4 ICD-10 Navigation (Condition-Centric Queries)

**What it uses:** `article_icd10`, `question_icd10`, `icd10_code_xref`, `icd10_rollup`, `clinical_pathways`

The ICD-10 layer enables condition-first lookups — instead of starting from an article, start from a diagnosis:

- "What articles cover Type 2 diabetes?" → `article_icd10 WHERE icd10_code LIKE 'E11%'`
- "What ITE questions test Type 2 diabetes?" → `question_icd10 WHERE icd10_code LIKE 'E11%'`
- "How many articles cover endocrine conditions broadly?" → `icd10_rollup WHERE chapter = 'Endocrine…'` → join to `icd10_code_xref` → join to `article_icd10`
- "What clinical pathway role does each article serve for hypertension?" → `clinical_pathways WHERE icd10_code LIKE 'I10%'`

This layer is the bridge that connects the exam-centric database to standard clinical vocabulary.

---

### 3.5 Citation Trend Monitoring

**What it uses:** `article_citation_trend`, `qid_art_xref`, `articles`

`article_citation_trend` is pre-computed from `qid_art_xref`. It tracks which articles are cited repeatedly across exam years (not just total citation count, but *consecutive year streaks*). The `is_watch_list` flag (`consecutive_streak ≥ 2`) identifies articles the ABFM keeps returning to — the most reliable signal for "this will be on the exam again."

This is used in M3 reports to prioritize which articles a resident should review first, and it could power an automated alert system when a new exam year's data is ingested.

---

## Part 4 — Future Applications of the Linkages

The database was designed with extensibility in mind. The table linkages described above create multiple expansion surfaces.

---

### 4.1 Intelligence 2.0 Layer 2 — Article Currency (PubMed)

**Tables already seeded:** `pubmed_pmid_cache` (344 rows: `citation_id → pmid`)

**Join path:** `aafp_citations.citation_id = pubmed_pmid_cache.citation_id` → PubMed API using `pmid`

**New table to build:** `article_currency`

```sql
CREATE TABLE article_currency (
    article_id       TEXT PRIMARY KEY,
    pmid             TEXT,
    pub_date         TEXT,
    age_years        REAL,
    superceded_flag  INTEGER,   -- 1 if a newer guideline exists
    checked_date     TEXT
);
```

**How to use it:** Each article that has a PMID can be checked against PubMed for:
- Publication date → age in years
- Whether the journal has published a more recent version
- Whether a newer guideline has superseded it

This adds a **temporal dimension** to the linkage: not just "this article covers E11" but "this article covering E11 is 8 years old, and the ABFM has cited it 5 times since — it is likely outdated but persistently tested."

---

### 4.2 Intelligence 2.0 Layer 4 — Trend Alerts

**Tables already available:** `questions` (8 years, 2018–2025), `question_icd10`, `article_citation_trend`

**New tables to build:** `topic_trends`, `pubmed_alerts`

The year-over-year body system and ICD-10 distribution data in `questions` can be mined to detect:
- Rising topics (more questions each year)
- Declining topics (fewer questions)
- New topics (first appearance in 2023+)

**Linkage pattern:** `question_icd10 → icd10_rollup` grouped by `exam_year` gives a normalized view of how clinical categories change across exam cycles. Linking this to `article_icd10` shows which articles are in the "rising" areas — these should be prioritized for enrichment.

---

### 4.3 New Question Bank Onboarding

**Existing linkage infrastructure is reusable.**

If a new question bank is added (e.g. AOBFP Family Medicine board questions, IM shelf questions, or internal faculty-authored cases), the existing schema already has the parallel structures needed:

1. Create a new `{bank}_questions` table with the same key columns (`qid`, `stem`, `choices`, `blueprint`, `body_system`, `concept_tags`).
2. Create `{bank}_qid_art_xref` to link new questions to `articles` by `article_id`.
3. Create `{bank}_question_icd10` to assign ICD-10 tags (same propagation pipeline already exists for both ITE and AAFP).
4. Run `compute_embeddings.py` to generate `{bank}_question_vec` for cross-corpus similarity.

The ICD-10 taxonomy tables (`icd10_rollup`, `icd10_code_xref`) are shared and do not need to be rebuilt. The `articles` table is the common reference library — any new question bank that cites the same literature is immediately connected to the existing enrichment infrastructure.

---

### 4.4 Resident Progress Tracking Over Time

**Existing tables:** `questions` (2018–2025 QIDs), `article_citation_trend`

**New table to build:** `resident_scores`

```sql
CREATE TABLE resident_scores (
    resident_id      TEXT,
    exam_year        INTEGER,
    qid              TEXT,
    answered_correct INTEGER,   -- 0 or 1
    body_system      TEXT,      -- denormalized for faster reporting
    blueprint        TEXT,
    PRIMARY KEY (resident_id, exam_year, qid)
);
```

**Linkage advantage:** Because `qid` → `qid_art_xref` → `articles` is already established, a resident's missed questions are immediately linked to:
- The specific article they need to review
- The pathway role they are missing (screening? diagnosis? monitoring?)
- Whether the article is on the persistent `is_watch_list`
- How that article's exam citation frequency has trended

A multi-year resident score table would enable longitudinal learning gap analysis — tracking whether a resident's weaknesses in a specific ICD-10 category or pathway role persist or resolve year over year.

---

### 4.5 Clinical Decision Support Pivot

**Existing linkage:** `clinical_pathways` (condition → pathway role → article) + `article_icd10` (article → diagnosis)

The database already maps clinical conditions (by ICD-10 code) to the articles that address them, organized by clinical function (screening, diagnosis, first-line treatment, monitoring, etc.). This structure is identical to what a clinical decision support system needs to serve a clinician at the point of care.

A new **clinical navigator module** could:
1. Accept an ICD-10 code as input (or a free-text clinical scenario → `icd10_vec` vector search)
2. Return the relevant `clinical_pathways` rows — articles organized by pathway role
3. Join to `article_citation_trend` and `qid_art_xref` to surface which articles are both clinically relevant AND exam-validated
4. Optionally join to `aafp_qid_art_xref` to show AAFP BRQ questions as learning cases

This is an extension, not a rebuild — all the linkages already exist.

---

### 4.6 Automated VC Gate Expansion

**Existing linkage:** `articles.tier` + `key_data_files/session_hy_inserts_v7.json` (the VC gate)

The VC gate is currently a static JSON file (352 citations). A future process could:
1. Compare `article_citation_trend.consecutive_streak` against the VC gate membership
2. Flag articles that have achieved a 3+ year streak but are **not** in the VC gate — these may be newly high-yield but missed by the original AAFP Video Course selection
3. Use `article_icd10` + `clinical_pathways` to ensure the proposed new VC gate candidates cover the full spectrum of pathway roles (not just treatment, but also screening and monitoring)

This would turn the static VC gate into a **data-driven dynamic tier**.

---

## Appendix: SQL Dialect Notes

- **SQLite 3** — window functions available from 3.25; CTEs from 3.8.3 (both available in Python 3.12's sqlite3)
- **JSON columns** — stored as TEXT; use `json_extract()` for `exam_years`, `qid_list`, `choices`, `concept_tags`
- **Virtual tables** — `article_vec`, `question_vec`, `aafp_question_vec` require the `sqlite-vec` extension loaded at runtime
- **Foreign keys** — not enforced by default; all joins are by convention
- **Case sensitivity** — text matching is case-sensitive; always use `LOWER()` or `COLLATE NOCASE`

**Standard filters** (apply unless explicitly overriding):
```sql
-- Exclude orphan articles (no linked questions)
WHERE citation_count > 0

-- Exclude garbled/stub articles
WHERE source_type != 'stub' AND article_id != 'ART-0001'
```

**Dynamic path pattern** (mandatory in all scripts):
```python
from pathlib import Path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"
```
