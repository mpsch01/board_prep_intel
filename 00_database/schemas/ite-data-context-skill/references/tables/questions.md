# Table: questions

**Location**: `ite_intelligence.db` → `questions`
**Description**: One row per ABFM ITE exam question. Contains full question content (stem, choices, answer, explanation) plus preprocessed keyword and concept tag fields.
**Primary Key**: `qid` (TEXT)
**Row Count**: 1,629
**Update Frequency**: Rebuilt via `rebuild_ite_db_v2.py`. Concept tags populated by `preprocess_concept_tags.py` (M1/scripts/maintain/).

## Columns

| Column | Type | Description | Notes |
|--------|------|-------------|-------|
| `qid` | TEXT | Question ID: `QID-2020-0001` | PK. Per-year numbering (resets each year). |
| `exam_year` | INTEGER | Exam year: 2018–2025 | 8 years of ITE data. |
| `body_system` | TEXT | ABFM body system category | e.g., Cardiovascular, Respiratory, Musculoskeletal. |
| `blueprint` | TEXT | ABFM blueprint category | 1,629/1,629 (100%) populated. Gold Standard for 2024-2025; v2 classifier (batched, few-shot) for 2020-2023; v1 classifier for 2018-2019. Values: "Acute Care and Diagnosis", "Chronic Care Management", "Emergent and Urgent Care", "Foundations of Care", "Preventive Care". |
| `question_text` | TEXT | Full question stem | Can be long (500+ chars). Includes clinical vignette. |
| `choices` | TEXT | JSON array of answer choices | `[{"letter": "A", "text": "..."}, ...]`. Usually 4-5 choices. |
| `correct_letter` | TEXT | Correct answer letter | "A", "B", "C", "D", or "E". |
| `correct_text` | TEXT | Full text of correct answer | Extracted from choices for convenience. |
| `explanation` | TEXT | Full explanation text | Typically 200-800 chars. Contains the teaching point. |
| `reference` | TEXT | Citation string from explanation | May differ slightly from `articles.clean_ref`. |
| `stem_keywords` | TEXT | Keywords extracted from stem | Comma-separated. Legacy field. |
| `explanation_keywords` | TEXT | Keywords from explanation | Comma-separated. Legacy field. |
| `all_keywords` | TEXT | Merged stem + explanation keywords | Comma-separated. Legacy field. |
| `concept_tags` | TEXT | Claude-preprocessed JSON | See schema below. 1,629/1,629 populated (100%). |
| `body_system_merged` | TEXT | Normalized body system name | Maps 2024 renamed categories back to historical names. Use for longitudinal analysis. |

## body_system_merged — Taxonomy Normalization

The 2024 ITE renamed three body system categories. `body_system_merged` maps these back to their historical equivalents for consistent longitudinal analysis. The original `body_system` column is preserved unchanged.

| 2024 Name (body_system) | Historical Name (body_system_merged) | Rows Affected |
|---|---|---|
| `Injuries/Musculoskeletal` | `Musculoskeletal` | 20 |
| `Psychiatric/Behavioral` | `Psychogenic` | 14 |
| `Sexual and Reproductive` | `Reproductive: Female` | 11 |

For all other rows, `body_system_merged = body_system`. Use `body_system_merged` for trend analysis; use `body_system` when you need the exact label the ABFM used that year.

## concept_tags JSON Schema

Every question has a `concept_tags` field containing a JSON object with these keys:

```json
{
  "diagnoses": ["hypertension", "heart failure"],
  "drugs": ["lisinopril/hydrochlorothiazide", "ACE inhibitor", "thiazide diuretic"],
  "guidelines": ["JNC 8", "ACC/AHA 2017"],
  "thresholds": ["BP 162/95 mmHg"],
  "concept_summary": "Tests knowledge of appropriate first-line antihypertensive therapy selection..."
}
```

| Key | Type | Description |
|-----|------|-------------|
| `diagnoses` | Array of strings | Clinical diagnoses tested |
| `drugs` | Array of strings | Medications referenced (brand/generic/class) |
| `guidelines` | Array of strings | Clinical guidelines referenced |
| `thresholds` | Array of strings | Numeric thresholds or cutoffs tested |
| `concept_summary` | String | 1-2 sentence summary of what the question tests |

**Querying concept_tags**:
```sql
-- Find questions testing a specific drug
SELECT qid, exam_year, body_system
FROM questions
WHERE LOWER(concept_tags) LIKE '%metformin%';

-- Extract just the concept_summary
SELECT qid, json_extract(concept_tags, '$.concept_summary') AS summary
FROM questions
WHERE exam_year = 2024;

-- Find questions with a specific guideline reference
SELECT qid, json_extract(concept_tags, '$.guidelines') AS guidelines
FROM questions
WHERE concept_tags LIKE '%USPSTF%';
```

## exam_year Distribution

| Year | Count | Blueprint Method |
|------|-------|-----------------|
| 2018 | 240 | v1 classifier |
| 2019 | 200 | v1 classifier |
| 2020 | 198 | v2 classifier |
| 2021 | 198 | v2 classifier |
| 2022 | 199 | v2 classifier |
| 2023 | 199 | v2 classifier |
| 2024 | 195 | Gold Standard (ABFM official) |
| 2025 | 200 | Gold Standard (ABFM official) |

## Sample Queries

### Questions by body system frequency (use merged for trends)
```sql
SELECT body_system_merged, COUNT(*) AS n,
       ROUND(100.0 * COUNT(*) / 1629, 1) AS pct
FROM questions
GROUP BY body_system_merged
ORDER BY n DESC;
```

### Year-over-year topic shifts (use merged for apples-to-apples)
```sql
SELECT exam_year, body_system_merged, COUNT(*) AS n
FROM questions
GROUP BY exam_year, body_system_merged
ORDER BY exam_year, n DESC;
```