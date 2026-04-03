# Table: aafp_questions

**Location**: `ite_intelligence.db` → `aafp_questions`
**Description**: AAFP Board Review Questions (BRQ) — a separate question bank from the ABFM ITE. Used as a priority filter for the article library and as a parallel enrichment corpus. These are NOT ABFM ITE questions.
**Primary Key**: `aafp_qid` (TEXT)
**Row Count**: 1,221
**ID format**: `AAFP-NNNNN` (e.g., `AAFP-49733`)
**Update Frequency**: Scraped via `aafp_brq/scraper` (self-contained build sequence).

## Columns

| Column | Type | Description | Notes |
|--------|------|-------------|-------|
| `aafp_qid` | TEXT | Question ID: `AAFP-NNNNN` | PK. |
| `question_id` | INTEGER | AAFP internal question integer ID | From AAFP platform. |
| `assessment_id` | INTEGER | AAFP assessment/quiz group ID | Groups questions into quiz sets. |
| `quiz_title` | TEXT | Name of the AAFP quiz | e.g., "Cardiovascular System 1" |
| `question_number` | INTEGER | Ordinal position within quiz | 1–N per quiz. |
| `stem` | TEXT | Full question stem | Equivalent to `question_text` in ITE questions. |
| `choices` | TEXT | JSON array of answer choices | `[{"letter": "A", "text": "..."}, ...]` |
| `url` | TEXT | AAFP platform URL for this question | For reference/source verification. |
| `stem_keywords` | TEXT | Keywords extracted from stem | Comma-separated. |
| `body_system` | TEXT | Body system category | Assigned during scrape. |
| `source_type` | TEXT | Source classification | e.g., AFP, Guideline/Org, etc. |
| `ite_nearest_qid` | TEXT | Nearest ITE question by vector similarity | Pre-computed; points to `questions.qid`. |
| `ite_nearest_dist` | REAL | Vector distance to nearest ITE question | Cosine distance — lower = more similar. |
| `all_keywords` | TEXT | Merged stem + explanation keywords | Comma-separated. |
| `body_system_method` | TEXT | How body_system was assigned | e.g., `classifier`, `manual`. |
| `concept_tags` | TEXT | Claude-preprocessed JSON | Same schema as ITE questions — 1,221/1,221 (100%). |
| `correct_letter` | TEXT | Correct answer letter ("A"–"E") | 1,221/1,221 (100%). Merged in 2026-03-30. |
| `correct_text` | TEXT | Full text of correct answer | 1,221/1,221 (100%). Merged in 2026-03-30. |
| `explanation` | TEXT | Plain-text explanation | 1,221/1,221 (100%). Merged in 2026-03-30. |
| `explanation_keywords` | TEXT | Keywords from explanation | Comma-separated. |
| `blueprint` | TEXT | ABFM blueprint category | 1,221/1,221 (100%). Same 5 categories as ITE. Applied via batch API classifier (same rubric + gold-standard examples as ITE v2). |

## blueprint Distribution

| Blueprint | Count | % |
|-----------|-------|---|
| Acute Care and Diagnosis | 588 | 48.2% |
| Chronic Care Management | 253 | 20.7% |
| Emergent and Urgent Care | 166 | 13.6% |
| Preventive Care | 140 | 11.5% |
| Foundations of Care | 74 | 6.1% |

## Related Tables

| Table | Relationship |
|-------|-------------|
| `aafp_citations` | 1,600 rows — individual parsed citations from AAFP explanations (`citation_id`, `aafp_qid`, `citation_seq`, `article_id`, `match_status`) |
| `aafp_citation_raw` | 1,600 rows — raw untruncated citation text archive (`citation_id`, `aafp_qid`, `raw_text`) |
| `aafp_qid_art_xref` | 864 rows — 643 unique AAFP questions linked to 737 unique articles (52.7% coverage) |
| `aafp_question_icd10` | 4,753 rows — ICD-10 codes for AAFP questions (1,210 unique questions covered) |
| `aafp_question_vec` | 1,221 rows — OpenAI embeddings (sqlite-vec virtual table) |
| `question_icd10_vec` | AAFP rows keyed by `source_bank = 'AAFP'` |

## Sample Queries

### Blueprint distribution comparison — ITE vs AAFP
```sql
SELECT 'ITE' AS bank, blueprint, COUNT(*) AS n,
       ROUND(100.0 * COUNT(*) / 1629, 1) AS pct
FROM questions GROUP BY blueprint
UNION ALL
SELECT 'AAFP' AS bank, blueprint, COUNT(*) AS n,
       ROUND(100.0 * COUNT(*) / 1221, 1) AS pct
FROM aafp_questions GROUP BY blueprint
ORDER BY bank, n DESC;
```

### Find AAFP questions linked to the same article as an ITE question
```sql
SELECT aq.aafp_qid, aq.blueprint, aq.stem,
       a.canonical_filename, a.tier
FROM aafp_questions aq
JOIN aafp_qid_art_xref ax ON aq.aafp_qid = ax.aafp_qid
JOIN articles a ON ax.article_id = a.article_id
JOIN qid_art_xref x ON a.article_id = x.article_id
WHERE x.qid = 'QID-2024-0042';
```

### Search concept_tags for a drug across both banks
```sql
SELECT 'ITE' AS bank, qid AS id, exam_year AS year,
       json_extract(concept_tags, '$.concept_summary') AS summary
FROM questions WHERE LOWER(concept_tags) LIKE '%empagliflozin%'
UNION ALL
SELECT 'AAFP' AS bank, aafp_qid AS id, NULL AS year,
       json_extract(concept_tags, '$.concept_summary') AS summary
FROM aafp_questions WHERE LOWER(concept_tags) LIKE '%empagliflozin%'
ORDER BY bank;
```

### AAFP questions closest to a given ITE question (pre-computed neighbor)
```sql
SELECT aq.aafp_qid, aq.ite_nearest_dist, aq.stem, aq.blueprint
FROM aafp_questions aq
WHERE aq.ite_nearest_qid = 'QID-2024-0042'
ORDER BY aq.ite_nearest_dist;
```
