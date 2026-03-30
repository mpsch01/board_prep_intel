# ITE Intelligence Data Analyst

A domain-specific data context skill for querying and analyzing the ABFM In-Training Examination (ITE) intelligence database.

## Database

- **Engine**: SQLite 3 (with optional `sqlite-vec` extension for vector search)
- **Path** (relative to project root): `00_database/db/ite_intelligence.db`
- **Windows absolute**: `C:\Users\mpsch\Desktop\#PROJECT_OVERHAUL\00_database\db\ite_intelligence.db`
- **Schema version**: v2 (rebuilt 2026-03-10 via `rebuild_ite_db_v2.py`; AAFP corpus added 2026-03-29)

## Mission

Transform a static reference library into a queryable, exam-aware knowledge base. Every clinical guideline is understood not just for what it says, but for **how the ABFM has tested it**.

## Design Philosophy: Preprocessing-First

All deterministic work happens at DB build time. The right-click enrichment pipeline only does: match-and-grab → Claude semantic interpretation → write JSON. If something can be computed at build time, it must not be computed at runtime.

## SQL Dialect Notes

- SQLite 3 — no window functions before 3.25, no CTEs before 3.8.3 (both available in Python 3.12's sqlite3)
- JSON fields stored as TEXT — use `json_extract()` for queries on `exam_years`, `qid_list`, `choices`, `concept_tags`
- Virtual tables (`article_vec`, `question_vec`) require the `sqlite-vec` extension loaded at runtime
- No foreign key constraints are enforced (PRAGMA foreign_keys is OFF by default) — joins are by convention
- Text matching is case-sensitive by default — always use `LOWER()` or `COLLATE NOCASE`

## Entity Model

See: `references/entities.md`

### Core Entities
| Entity | Table | Primary Key | Count |
|--------|-------|-------------|-------|
| Article (reference) | `articles` | `clean_ref` (TEXT) | 1,985 |
| ITE Question | `questions` | `qid` (TEXT) | 1,629 |
| AAFP BRQ Question | `aafp_questions` | `aafp_qid` (TEXT) | 1,221 (blueprint 100% filled) |
| Question↔Article Link | `question_ref_pairs` | `id` (INTEGER AUTO) | 2,673 |
| ITE QID↔ART Crossref | `qid_art_xref` | `(qid, article_id)` composite | 2,470 |
| AAFP QID↔ART Crossref | `aafp_qid_art_xref` | `(aafp_qid, article_id)` composite | 864 |
| Article ICD-10 Tags | `article_icd10` | `(article_id, icd10_code)` | 3,855 |
| AAFP Question ICD-10 | `aafp_question_icd10` | `(aafp_qid, icd10_code)` | 4,240 |
| ICD-10 Rollup | `icd10_rollup` | `parent_code` (TEXT) | 614 |
| ICD-10 Code Crossref | `icd10_code_xref` | `icd10_code` (TEXT) | 1,006 |
| Clinical Pathways | `clinical_pathways` | `(article_id, icd10_code)` | 3,093 |
| Citation Trends | `article_citation_trend` | `article_id` (TEXT) | 1,740 |
| Article Embedding | `article_vec` | `article_id` (TEXT) | ~1,397 |
| ITE Question Embedding | `question_vec` | `qid` (TEXT) | ~1,189 |

### Key Relationships
- **articles ↔ ITE questions**: Many-to-many via `question_ref_pairs` (canonical join path, uses `clean_ref`)
- **articles ↔ ITE questions**: Also joinable via `qid_art_xref` (ergonomic path, uses `article_id`)
- **articles ↔ AAFP questions**: Via `aafp_qid_art_xref` (ergonomic path, uses `article_id`)
- **aafp_questions**: self-contained — includes correct_letter, correct_text, explanation, explanation_keywords directly (merged 2026-03-30; `aafp_explanations` dropped)
- **articles ↔ ICD-10 codes**: Via `article_icd10` (primary/secondary/related relevance)
- **AAFP questions ↔ ICD-10 codes**: Via `aafp_question_icd10`
- **articles ↔ clinical pathways**: Via `clinical_pathways` (article_id + icd10_code → pathway_role)
- **ICD-10 specific→parent**: Via `icd10_code_xref` → `icd10_rollup`
- Join via pairs: `question_ref_pairs.clean_ref = articles.clean_ref` AND `question_ref_pairs.qid = questions.qid`
- Join via xref: `qid_art_xref.article_id = articles.article_id` AND `qid_art_xref.qid = questions.qid`
- One article can be cited by multiple questions; one question can cite multiple articles

## Knowledge Base Navigation

| Domain | Reference File | What It Covers |
|--------|---------------|----------------|
| Entities & IDs | `references/entities.md` | Entity definitions, ID formats, relationships, qid_art_xref, AAFP tables |
| Metrics & KPIs | `references/metrics.md` | Citation count, TF-IDF scoring, enrichment confidence |
| Articles table | `references/tables/articles.md` | 18 columns, source_type/tier distributions, 3 sample queries |
| ITE Questions table | `references/tables/questions.md` | 16 columns, concept_tags JSON schema, blueprint column, exam_year distribution 2018–2025 |
| Pairs table | `references/tables/question_ref_pairs.md` | Junction table, match_status distribution, 3 sample queries |
| ITE QID-ART Crossref | `references/tables/qid_art_xref.md` | Ergonomic join table using article_id instead of clean_ref |
| Vector tables | `references/tables/vectors.md` | Embedding tables, similarity search |
| Clinical Pathways | `references/tables/clinical_pathways.md` | Layer 3 blending engine, pathway roles, engine_type |
| Pipeline & Scripts | `references/pipeline.md` | v4 enrichment pipeline, script inventory, data flow |
| Filters & Gotchas | `references/gotchas.md` | Common pitfalls, required exclusions |

## Standard Filters

Always apply unless user explicitly says otherwise:

```sql
-- Exclude orphan articles (no linked questions)
WHERE citation_count > 0

-- Exclude garbled/stub articles
WHERE source_type != 'stub' AND article_id != 'ART-0001'
```

## Common Query Patterns

### 1. High-yield articles (most-cited across exam years)
```sql
SELECT article_id, canonical_filename, tier, citation_count, unique_years, exam_years
FROM articles
WHERE citation_count > 0
ORDER BY citation_count DESC, unique_years DESC
LIMIT 20;
```

### 2. Questions by body system and year (use body_system_merged for trends)
```sql
SELECT qid, exam_year, body_system_merged, subcategory, question_text
FROM questions
WHERE body_system_merged = 'Cardiovascular' AND exam_year = 2024
ORDER BY qid;
```

### 3. All questions linked to a specific article
```sql
SELECT q.qid, q.exam_year, q.body_system_merged, q.question_text, q.concept_tags
FROM questions q
JOIN question_ref_pairs p ON q.qid = p.qid
WHERE p.clean_ref = (SELECT clean_ref FROM articles WHERE article_id = 'ART-0470')
ORDER BY q.exam_year;
```

### 4. Concept tag search (what questions test a specific drug/diagnosis)
```sql
SELECT qid, exam_year, body_system_merged,
       json_extract(concept_tags, '$.concept_summary') AS summary
FROM questions
WHERE LOWER(concept_tags) LIKE '%empagliflozin%'
ORDER BY exam_year;
```

### 5. Cross-year trending (which topics appear repeatedly)
```sql
SELECT json_extract(q.concept_tags, '$.diagnoses') AS dx_tags,
       COUNT(DISTINCT q.exam_year) AS years_tested,
       COUNT(*) AS total_questions,
       GROUP_CONCAT(DISTINCT q.exam_year) AS which_years
FROM questions q
WHERE q.concept_tags IS NOT NULL
GROUP BY dx_tags
HAVING years_tested >= 3
ORDER BY years_tested DESC, total_questions DESC;
```

### 6. Enrichment pipeline coverage
```sql
SELECT match_status, COUNT(*) AS n,
       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM question_ref_pairs), 1) AS pct
FROM question_ref_pairs
GROUP BY match_status
ORDER BY n DESC;
```

### 7. Year-over-year body system trends (use merged taxonomy)
```sql
SELECT exam_year, body_system_merged, COUNT(*) AS n
FROM questions
GROUP BY exam_year, body_system_merged
ORDER BY exam_year, n DESC;
```

### 8. Clinical pathway for a condition (Layer 3)
```sql
SELECT cp.pathway_role, a.canonical_filename, a.engine_type, cp.relevance,
       a.citation_count, a.tier
FROM clinical_pathways cp
JOIN articles a ON cp.article_id = a.article_id
WHERE cp.icd10_code LIKE 'E11%'
  AND a.citation_count > 0
ORDER BY cp.pathway_role, cp.relevance, a.citation_count DESC;
```

### 9. Full pathway with exam questions (Layer 3 + questions)
```sql
SELECT cp.pathway_role, a.canonical_filename, q.qid, q.exam_year,
       q.subcategory, q.body_system_merged
FROM clinical_pathways cp
JOIN articles a ON cp.article_id = a.article_id
JOIN qid_art_xref x ON a.article_id = x.article_id
JOIN questions q ON x.qid = q.qid
WHERE cp.icd10_code LIKE 'I10%'
ORDER BY cp.pathway_role, q.exam_year;
```
