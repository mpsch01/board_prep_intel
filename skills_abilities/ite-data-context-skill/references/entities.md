# Entity Definitions & Relationships

## Article (Reference)

**What it represents**: A clinical reference (journal article, guideline, or other source) that has been cited in the explanation/answer of at least one ABFM ITE exam question. Not all articles have linked questions — 30 are legitimate "orphans" imported from tier lists but never directly cited.

**Primary table**: `articles`
**Primary key**: `clean_ref` (TEXT) — the original cleaned citation string. This is stable and used as the FK throughout.
**Secondary key**: `article_id` (TEXT, UNIQUE) — stable short ID formatted as `ART-NNNN` (e.g., `ART-0470`). Assigned alphabetically by clean_ref at DB build time.

**ID formats**:
- `clean_ref`: Full citation text, e.g., `"Smith DK, Lennon RP, Carlsgaard PB: Managing hypertension using combination therapy. Am Fam Physician 2020;101(6):341-348"`
- `article_id`: `ART-0001` through `ART-1985` — zero-padded 4-digit integer. Next ID: ART-1987.
- `canonical_filename`: `Smith_Lennon_2020` — derived from author1, author2, year
- `codon_filename`: `Smith_Lennon_2020#@#ART-0470@#@.pdf` — canonical + codon delimiters wrapping article_id

**Codon filename convention**:
- Start delimiter: `#@#`
- Stop delimiter: `@#@`
- Format: `{canonical_filename}#@#{article_id}@#@.pdf`
- Rationale: Short stable ID keeps filenames under 100 chars. Full QID list lives in DB, not in the filename.
- Note: 76 non-codon PDFs remain in the library (original filenames, no DB match).

## Question

**What it represents**: A single ABFM In-Training Exam question, with full stem text, answer choices, correct answer, explanation, and preprocessed semantic tags.

**Primary table**: `questions`
**Primary key**: `qid` (TEXT) — formatted as `QID-{year}-{nnnn}`, e.g., `QID-2020-0001`

**ID format**:
- Year range: 2020–2025 (6 exam years)
- Per-year numbering: 0001 through ~0200 (resets each year)
- Total: 1,189 questions

**Important**: The source JSON (`ite_questions_clean.json`) uses global sequential numbering (2021 starts at 201, 2022 at 401, etc.). The DB uses per-year numbering. The `rebuild_ite_db_v2.py` script handles this translation.

**Key column**: `body_system_merged` — normalized body system name for longitudinal analysis. Maps 2024 renamed categories back to historical equivalents. Always use this for trend queries instead of `body_system`.

## Question↔Article Link (Junction)

**What it represents**: A single citation relationship — "question Q cited article A in its explanation."

**Primary table**: `question_ref_pairs`
**Primary key**: `id` (INTEGER AUTOINCREMENT)
**Foreign keys** (by convention, not enforced):
- `qid` → `questions.qid`
- `clean_ref` → `articles.clean_ref`

**Cardinality**: Many-to-many. One question can cite multiple articles (avg ~1.7). One article can be cited by multiple questions (high-yield articles have 5+ citations).

## QID↔Article Crossref (Ergonomic Join Table)

**What it represents**: A denormalized crossref table that links questions to articles using `article_id` instead of the unwieldy `clean_ref` string. Provides a more ergonomic join path for queries that don't need the full citation text.

**Primary table**: `qid_art_xref`
**Primary key**: `(qid, article_id)` composite
**Row count**: 2,470

**Columns**:
| Column | Type | Description |
|--------|------|-------------|
| `qid` | TEXT | FK → `questions.qid` |
| `article_id` | TEXT | FK → `articles.article_id` |
| `tier` | TEXT | Article tier at time of xref build |
| `exam_year` | INTEGER | Denormalized exam year |
| `author1` | TEXT | First author surname |
| `year` | TEXT | Publication year |

**When to use**: Use `qid_art_xref` when you want to join questions to articles by `article_id` (shorter, more readable queries). Use `question_ref_pairs` when you need `match_status`, `match_score`, or `ref_raw` fields.

**Note**: Row count (2,470) differs from `question_ref_pairs` (2,673) because `qid_art_xref` excludes unmatched/partial pairs.

```sql
-- Ergonomic: questions for an article using article_id
SELECT q.qid, q.exam_year, q.body_system_merged, q.question_text
FROM questions q
JOIN qid_art_xref x ON q.qid = x.qid
WHERE x.article_id = 'ART-0470'
ORDER BY q.exam_year;
```

## Relationship Diagram

```
articles (1,985)
    │
    ├── clean_ref ─── question_ref_pairs (2,673) ─── qid ─── questions / ITE (1,629)
    │
    ├── article_id ── qid_art_xref (2,470) ─────── qid ─── questions / ITE (1,629)
    │
    ├── article_id ── aafp_qid_art_xref (864) ──── aafp_qid ─── aafp_questions (1,221)
    │
    ├── article_id ── article_icd10 (4,020) ──────── icd10_code ─── icd10_code_xref (1,006) ─── icd10_rollup (614)
    │
    └── article_id ── clinical_pathways (4,020) ──── (pathway_role + source_bank + icd10_code)

questions / ITE (1,629)
    └── qid ── question_icd10 (5,284) ── icd10_code ─── icd10_code_xref ─── icd10_rollup

aafp_questions (1,221)  ← self-contained: stem, choices, correct_letter, correct_text, explanation, concept_tags
    ├── aafp_qid ── aafp_question_icd10 (4,753) ── icd10_code ─── icd10_code_xref ─── icd10_rollup
    └── aafp_qid ── aafp_citations (1,600) ──────── article_id ─── articles

Vector/embedding tables (no sqlite-vec extension needed for icd10_vec family):
    article_vec (1,985) · question_vec (1,629) · aafp_question_vec (1,221)  ← require sqlite-vec
    icd10_vec (2,219) · article_icd10_vec (1,757) · question_icd10_vec (2,747)  ← plain BLOB tables
```

## Article ICD-10 Tags

**What it represents**: ICD-10 diagnostic codes assigned to each article via Anthropic Batch API (Layer 1). Each article can have primary, secondary, and related codes.

**Primary table**: `article_icd10`
**Row count**: 4,020
**Key columns**: `article_id` (FK → articles), `icd10_code`, `icd10_desc`, `relevance` (primary/secondary/related)

## ITE Question ICD-10 Tags

**What it represents**: ICD-10 codes assigned to each ITE question — parallel to article_icd10 but for the question bank.

**Primary table**: `question_icd10`
**Row count**: 5,284 (covers 1,512/1,629 ITE questions = 92.8%)
**Key columns**: `qid` (PK1), `icd10_code` (PK2), `icd10_desc`, `relevance` (primary/secondary/related)
**Relevance distribution**: primary=2,725 / secondary=1,627 / related=932

## ICD-10 Condensation Crosswalk

**What it represents**: Parent-level rollup of ICD-10 codes for high-level querying.

**Tables**:
- `icd10_rollup` (614 rows): 3-char parent categories with pre-computed article counts + chapter
- `icd10_code_xref` (1,006 rows): Maps each specific code to its 3-char parent

**Join chain**: `icd10_rollup` → `icd10_code_xref` → `article_icd10` → `articles` → `qid_art_xref` → `questions`

## Clinical Pathways (Layer 3 — Blending Engine)

**What it represents**: Maps each (article, ICD-10 code) pair to a clinical pathway role — what function the article serves for that condition (screening, diagnosis, first-line treatment, etc.). Built at zero cost from ABFM subcategory data + engine-type classification.

**Primary table**: `clinical_pathways`
**Row count**: 4,020
**Key columns**:

| Column | Type | Description |
|--------|------|-------------|
| `article_id` | TEXT | FK → `articles.article_id` |
| `icd10_code` | TEXT | Specific ICD-10 code |
| `icd10_desc` | TEXT | Code description |
| `pathway_role` | TEXT | One of 7 roles (see below) |
| `blueprint` | TEXT | ABFM blueprint category from linked questions |
| `source_bank` | TEXT | `ITE`, `AAFP`, or `both` — which question bank drives this pathway |
| `relevance` | TEXT | primary/secondary/related (from article_icd10) |
| `confidence` | TEXT | All rows currently `high` |

**Pathway roles**:
- `screening_prevention`: Screening criteria, risk assessment tools, prevention protocols
- `diagnosis`: Diagnostic criteria, "which test" logic, sensitivity/specificity, staging systems
- `first_line`: Initial treatment (pharmacologic or non-pharmacologic), always appropriate early step
- `second_line`: Novel agents, RCT-tested alternatives, escalation when first-line fails
- `monitoring`: Ongoing management, lab intervals, titration protocols, red flags
- `referral`: When to refer out, specialist criteria
- `special_pops`: Pediatric, geriatric, pregnant, renal-adjusted dosing, comorbidity modifications

**articles.engine_type column** (classifies each article's clinical function):
- `acute_protocol` (1,169), `chronic_guideline` (284), `preventive_guideline` (268), `diagnostic_guideline` (237), `rct` (27)
- All 1,985 articles have engine_type populated
- Classified deterministically from ABFM subcategories + source_type + categories — zero API cost
- Note: engine_type lives in the `articles` table, not in `clinical_pathways`

**Join patterns**:
```sql
-- All articles with their pathway role for a specific condition
SELECT cp.pathway_role, a.canonical_filename, a.engine_type, cp.relevance
FROM clinical_pathways cp
JOIN articles a ON cp.article_id = a.article_id
WHERE cp.icd10_code LIKE 'E11%'
ORDER BY cp.pathway_role, cp.relevance;

-- Full clinical pathway: condition → pathway roles → linked exam questions
SELECT cp.pathway_role, a.canonical_filename, q.qid, q.exam_year, q.subcategory
FROM clinical_pathways cp
JOIN articles a ON cp.article_id = a.article_id
JOIN qid_art_xref x ON a.article_id = x.article_id
JOIN questions q ON x.qid = q.qid
WHERE cp.icd10_code LIKE 'E11%'
ORDER BY cp.pathway_role, q.exam_year;
```

## AAFP Board Review Questions (BRQ)

**What it represents**: Questions from the AAFP's online board prep course — a separate question bank used as a priority filter for the article library. AAFP BRQ questions are NOT ABFM ITE questions; they are a parallel corpus that validates article relevance.

**Primary table**: `aafp_questions`
**Primary key**: `aafp_qid` (TEXT)
**Row count**: 1,221
**Key columns**:
| Column | Type | Description |
|--------|------|-------------|
| `aafp_qid` | TEXT | PK, format `AAFP-NNNN` |
| `stem` | TEXT | Question stem |
| `choices` | TEXT | JSON array of answer choices |
| `body_system` | TEXT | Body system category |
| `concept_tags` | TEXT | Claude-preprocessed JSON (same schema as ITE questions) — 1,221/1,221 (100%) |
| `correct_letter` | TEXT | Correct answer letter ("A"–"E") — 1,221/1,221 (100%) |
| `correct_text` | TEXT | Correct answer full text — 1,221/1,221 (100%) |
| `explanation` | TEXT | Plain-text explanation — 1,221/1,221 (100%) |
| `explanation_keywords` | TEXT | Comma-separated keywords from explanation |
| `blueprint` | TEXT | ABFM blueprint category — 1,221/1,221 (100%). Same 5 categories as ITE. Applied via batch API classifier (same rubric + gold-standard examples as ITE v2). Distribution: Acute 48.2%, Chronic 20.7%, Emergent 13.6%, Preventive 11.5%, Foundations 6.1% |
| `stem_keywords` | TEXT | Extracted keywords |
| `ite_nearest_qid` | TEXT | Nearest ITE question by vector similarity |
| `ite_nearest_dist` | REAL | Vector distance to nearest ITE question |

**AAFP Citation Tables**:
- **`aafp_citations`** (1,600 rows): One row per individual parsed citation — `citation_id`, `aafp_qid`, `citation_seq`, `article_id`, `match_status`, `unmatched_class`. Multi-citation refs are split (e.g. AAFP-49733-C1, AAFP-49733-C2).
- **`aafp_citation_raw`** (1,600 rows): Raw untruncated citation text archive — `citation_id`, `aafp_qid`, `raw_text`.

**AAFP QID↔ART Crossref**:
- **Table**: `aafp_qid_art_xref`
- **Row count**: 864 rows (643 unique AAFP questions linked, 52.7%)
- **Join**: `aafp_qid_art_xref.article_id = articles.article_id`

**AAFP Question ICD-10 Tags**:
- **Table**: `aafp_question_icd10`
- **Row count**: 4,753 rows (covers 1,210/1,221 AAFP questions)
- **Key columns**: `aafp_qid`, `icd10_code`, `icd10_desc`, `relevance` (primary/secondary/related)

**Key query — find ITE + AAFP questions covering the same article**:
```sql
SELECT a.article_id, a.canonical_filename,
       COUNT(DISTINCT x.qid) AS ite_citations,
       COUNT(DISTINCT ax.aafp_qid) AS aafp_citations
FROM articles a
LEFT JOIN qid_art_xref x ON a.article_id = x.article_id
LEFT JOIN aafp_qid_art_xref ax ON a.article_id = ax.article_id
WHERE x.qid IS NOT NULL OR ax.aafp_qid IS NOT NULL
GROUP BY a.article_id
ORDER BY (ite_citations + aafp_citations) DESC
LIMIT 20;
```

## PubMed PMID Cache

**What it represents**: Seed table for Intelligence 2.0 Layer 2 (article currency). Maps citation_id strings from AAFP citation data to PubMed PMIDs for freshness checking.

**Primary table**: `pubmed_pmid_cache`
**Row count**: 344
**Key columns**: `citation_id` (PK, e.g., `AAFP-49863-C1`), `pmid` (TEXT), `lookup_date`, `mesh_count`
**Use**: Join to `aafp_citations.citation_id` to find the PubMed record for any matched article.

## Citation Trend Tracking

**Table**: `article_citation_trend`
**Row count**: 1,740
**What it represents**: Pre-computed longitudinal citation data for each article that has ever appeared in `qid_art_xref`. Rebuilt on demand via `update_citation_trends.py` (full DELETE + re-insert).

**Key columns**: `article_id`, `years_cited` (comma-separated), `distinct_year_count`, `first_cited_year`, `most_recent_year`, `consecutive_streak`, `is_watch_list` (1 if streak ≥ 2)

```sql
-- Articles cited in 3+ consecutive years (watch list)
SELECT article_id, years_cited, consecutive_streak
FROM article_citation_trend
WHERE is_watch_list = 1
ORDER BY consecutive_streak DESC, distinct_year_count DESC;
```

## Vector Embeddings (Optional Extension)

Two virtual tables store OpenAI `text-embedding-3-small` (1536-dim) vectors:
- `article_vec`: keyed by `article_id`, embeds article title + org + year (~1,397 vectors; new articles not yet embedded)
- `question_vec`: keyed by `qid`, embeds question stem + concept summary (~1,189 vectors; 2018-2019 ITE questions not yet embedded)

These require the `sqlite-vec` extension loaded at runtime. They were used by Strategy 5 (semantic fallback) in the v3 enrichment pipeline. **In v4, vector search is no longer used for enrichment** — the codon migration eliminated the need for semantic matching. The vectors remain in the DB for potential future analytical use (e.g., "find questions similar to this one").
