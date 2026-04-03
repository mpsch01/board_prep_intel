# Table: question_icd10 (and aafp_question_icd10)

## question_icd10

**Location**: `ite_intelligence.db` → `question_icd10`
**Description**: ICD-10 diagnostic codes assigned to each ITE question. Parallel to `article_icd10` — same schema, same relevance tiers. Enables condition-level search across the ITE question bank without going through articles.
**Primary Key**: `(qid, icd10_code)` composite
**Row Count**: 5,284
**Coverage**: 1,512 / 1,629 ITE questions (92.8%)

### Columns

| Column | Type | Description | Notes |
|--------|------|-------------|-------|
| `qid` | TEXT | FK → `questions.qid` | PK component 1. |
| `icd10_code` | TEXT | ICD-10 code (e.g., `E11.9`) | PK component 2. |
| `icd10_desc` | TEXT | Code description | Denormalized for convenience. |
| `relevance` | TEXT | `primary` / `secondary` / `related` | Relevance tier for this code to this question. |

### Relevance Distribution

| Relevance | Count |
|-----------|-------|
| primary | 2,725 |
| secondary | 1,627 |
| related | 932 |

---

## aafp_question_icd10

**Location**: `ite_intelligence.db` → `aafp_question_icd10`
**Description**: ICD-10 codes for AAFP BRQ questions. Same schema as `question_icd10`.
**Primary Key**: `(aafp_qid, icd10_code)` composite
**Row Count**: 4,753
**Coverage**: 1,210 / 1,221 AAFP questions (99.1%)

### Columns

| Column | Type | Description |
|--------|------|-------------|
| `aafp_qid` | TEXT | FK → `aafp_questions.aafp_qid` |
| `icd10_code` | TEXT | ICD-10 code |
| `icd10_desc` | TEXT | Code description |
| `relevance` | TEXT | `primary` / `secondary` / `related` |

---

## Join Patterns

### ITE questions for a specific ICD-10 condition
```sql
SELECT qi.qid, qi.relevance, q.exam_year, q.blueprint, q.body_system_merged,
       json_extract(q.concept_tags, '$.concept_summary') AS summary
FROM question_icd10 qi
JOIN questions q ON qi.qid = q.qid
WHERE qi.icd10_code LIKE 'E11%'
  AND qi.relevance = 'primary'
ORDER BY q.exam_year;
```

### How many ITE questions map to each parent ICD-10 category?
```sql
SELECT r.chapter_desc, COUNT(DISTINCT qi.qid) AS unique_qs,
       COUNT(*) AS total_mappings
FROM question_icd10 qi
JOIN icd10_code_xref cx ON qi.icd10_code = cx.icd10_code
JOIN icd10_rollup r ON cx.parent_code = r.parent_code
WHERE qi.relevance = 'primary'
GROUP BY r.chapter_desc
ORDER BY unique_qs DESC;
```

### Cross-bank: conditions covered in both ITE and AAFP questions
```sql
SELECT qi.icd10_code, qi.icd10_desc,
       COUNT(DISTINCT qi.qid) AS ite_questions,
       COUNT(DISTINCT aq.aafp_qid) AS aafp_questions
FROM question_icd10 qi
JOIN aafp_question_icd10 aq ON qi.icd10_code = aq.icd10_code
WHERE qi.relevance = 'primary' AND aq.relevance = 'primary'
GROUP BY qi.icd10_code
ORDER BY (ite_questions + aafp_questions) DESC
LIMIT 20;
```

### ICD-10 codes NOT covered by any linked article (potential gaps)
```sql
SELECT DISTINCT qi.icd10_code, qi.icd10_desc,
       COUNT(DISTINCT qi.qid) AS ite_question_count
FROM question_icd10 qi
LEFT JOIN article_icd10 ai ON qi.icd10_code = ai.icd10_code
WHERE ai.icd10_code IS NULL
  AND qi.relevance = 'primary'
GROUP BY qi.icd10_code
ORDER BY ite_question_count DESC;
```

---

## Relationship to Other ICD-10 Tables

```
question_icd10 (5,284)          article_icd10 (4,020)
    │                                │
    └── icd10_code ─────────────────┤
                                    │
                        icd10_code_xref (1,006)
                                    │
                        icd10_rollup (614) ── chapter/chapter_desc
```

- Join `question_icd10` → `icd10_code_xref` → `icd10_rollup` for chapter-level aggregation
- Join `question_icd10` → `article_icd10` on `icd10_code` to find articles covering the same condition as a question
- Use `clinical_pathways` as a pre-joined view of (article, icd10_code, pathway_role)
