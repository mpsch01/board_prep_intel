# Entity Definitions & Relationships

## Article (Reference)

**What it represents**: A clinical reference (journal article, guideline, or other source) that has been cited in the explanation/answer of at least one ABFM ITE exam question. Not all articles have linked questions — 30 are legitimate "orphans" imported from tier lists but never directly cited.

**Primary table**: `articles`
**Primary key**: `clean_ref` (TEXT) — the original cleaned citation string. This is stable and used as the FK throughout.
**Secondary key**: `article_id` (TEXT, UNIQUE) — stable short ID formatted as `ART-NNNN` (e.g., `ART-0470`). Assigned alphabetically by clean_ref at DB build time.

**ID formats**:
- `clean_ref`: Full citation text, e.g., `"Smith DK, Lennon RP, Carlsgaard PB: Managing hypertension using combination therapy. Am Fam Physician 2020;101(6):341-348"`
- `article_id`: `ART-0001` through `ART-1397` — zero-padded 4-digit integer
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
**Row count**: 1,818

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

**Note**: Row count (1,818) differs from `question_ref_pairs` (2,069) because `qid_art_xref` excludes unmatched/partial pairs.

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
articles (1,397)
    │
    ├── clean_ref ─── question_ref_pairs (2,069) ─── qid ─── questions (1,189)
    │
    ├── article_id ── qid_art_xref (1,818) ──────── qid ─── questions (1,189)
    │
    ├── article_id ── article_icd10 (4,528) ──────── icd10_code ─── icd10_code_xref (1,668) ─── icd10_rollup (736)
    │
    └── article_id ── clinical_pathways (4,528) ──── (pathway_role + icd10_code)
```

## Article ICD-10 Tags

**What it represents**: ICD-10 diagnostic codes assigned to each article via Anthropic Batch API (Layer 1). Each article can have primary, secondary, and related codes.

**Primary table**: `article_icd10`
**Row count**: 4,528
**Key columns**: `article_id` (FK → articles), `icd10_code`, `icd10_desc`, `relevance` (primary/secondary/related)

## ICD-10 Condensation Crosswalk

**What it represents**: Parent-level rollup of ICD-10 codes for high-level querying.

**Tables**:
- `icd10_rollup` (736 rows): 3-char parent categories with pre-computed article counts + chapter
- `icd10_code_xref` (1,668 rows): Maps each specific code to its 3-char parent

**Join chain**: `icd10_rollup` → `icd10_code_xref` → `article_icd10` → `articles` → `qid_art_xref` → `questions`

## Clinical Pathways (Layer 3 — Blending Engine)

**What it represents**: Maps each (article, ICD-10 code) pair to a clinical pathway role — what function the article serves for that condition (screening, diagnosis, first-line treatment, etc.). Built at zero cost from ABFM subcategory data + engine-type classification.

**Primary table**: `clinical_pathways`
**Row count**: 4,528
**Key columns**:

| Column | Type | Description |
|--------|------|-------------|
| `article_id` | TEXT | FK → `articles.article_id` |
| `icd10_code` | TEXT | Specific ICD-10 code |
| `icd10_desc` | TEXT | Code description |
| `pathway_role` | TEXT | One of 7 roles (see below) |
| `engine_type` | TEXT | Article's engine classification |
| `relevance` | TEXT | primary/secondary/related (from article_icd10) |
| `confidence` | TEXT | Match confidence level |

**Pathway roles**:
- `screening_prevention`: Screening criteria, risk assessment tools, prevention protocols
- `diagnosis`: Diagnostic criteria, "which test" logic, sensitivity/specificity, staging systems
- `first_line`: Initial treatment (pharmacologic or non-pharmacologic), always appropriate early step
- `second_line`: Novel agents, RCT-tested alternatives, escalation when first-line fails
- `monitoring`: Ongoing management, lab intervals, titration protocols, red flags
- `referral`: When to refer out, specialist criteria
- `special_pops`: Pediatric, geriatric, pregnant, renal-adjusted dosing, comorbidity modifications

**Articles.engine_type column** (added in Layer 3):
- `preventive_guideline`, `diagnostic_guideline`, `chronic_guideline`, `acute_protocol`, `rct`
- 1,366 articles classified, 31 NULL (non-cited stubs)
- Classified deterministically from ABFM subcategories + source_type + categories — zero API cost

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

## Vector Embeddings (Optional Extension)

Two virtual tables store OpenAI `text-embedding-3-small` (1536-dim) vectors:
- `article_vec`: keyed by `article_id`, embeds article title + org + year (1,397 vectors)
- `question_vec`: keyed by `qid`, embeds question stem + concept summary (1,189 vectors)

These require the `sqlite-vec` extension loaded at runtime. They were used by Strategy 5 (semantic fallback) in the v3 enrichment pipeline. **In v4, vector search is no longer used for enrichment** — the codon migration eliminated the need for semantic matching. The vectors remain in the DB for potential future analytical use (e.g., "find questions similar to this one").
