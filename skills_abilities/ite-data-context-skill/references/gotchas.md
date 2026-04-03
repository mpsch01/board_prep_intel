# Filters, Gotchas & Common Pitfalls

## Required Standard Filters

### Exclude orphan articles
30 articles have `citation_count = 0` — they were imported from tier lists but never directly cited in any ITE question. Include them only when analyzing the full reference library, not when analyzing exam trends.

```sql
WHERE citation_count > 0
```

### Exclude garbled/stub entries
`ART-0001` has a garbled `clean_ref` (a venous hum description pasted as a citation — cosmetic issue). 30 articles have `source_type = 'stub'` — placeholder entries without real content.

```sql
WHERE source_type != 'stub' AND article_id != 'ART-0001'
```

### Exclude unmatched pairs for citation analysis
148 pairs have `match_status = 'unmatched'` — the link between question and article couldn't be confidently established. For high-confidence analyses:

```sql
WHERE match_status IN ('matched', 'fuzzy_matched')
```

## Data Quality Gotchas

### 1. clean_ref is the PK, not article_id
The natural key is the full citation text (`clean_ref`), which is long and unwieldy. `article_id` (ART-NNNN) is more ergonomic but is a secondary key. When joining to `question_ref_pairs`, you MUST use `clean_ref`, not `article_id`.

```sql
-- CORRECT
JOIN articles a ON p.clean_ref = a.clean_ref

-- WRONG (will fail — question_ref_pairs has no article_id column)
JOIN articles a ON p.article_id = a.article_id
```

**Alternative**: Use `qid_art_xref` for joins by `article_id` — see `references/entities.md`.

### 2. year is TEXT, not INTEGER
`articles.year` is stored as TEXT. Comparisons like `WHERE year > 2020` will work due to SQLite's type affinity, but be explicit:

```sql
WHERE CAST(year AS INTEGER) BETWEEN 2020 AND 2025
```

### 3. JSON fields require json_extract()
`exam_years`, `qid_list`, `choices`, and `concept_tags` are JSON stored as TEXT. Don't try string operations on them for structured queries:

```sql
-- CORRECT
SELECT json_extract(concept_tags, '$.diagnoses') FROM questions;

-- OK for rough searching (LIKE on raw text)
SELECT * FROM questions WHERE concept_tags LIKE '%metformin%';

-- WRONG (won't parse as array)
SELECT * FROM questions WHERE exam_years = '[2020, 2022]';
```

### 4. No foreign key enforcement
SQLite FK constraints are OFF by default and not enforced in this DB. Orphaned references in `question_ref_pairs` can exist. Always use explicit JOINs and check for NULLs.

### 5. extraction_status tracks extraction, not enrichment
The `articles.extraction_status` field has two states: `extracted` or `pending`. This tracks whether the article has been *extracted to JSON*, not whether it has been *enriched* (Claude API). Actual enrichment status is tracked in the JSON files themselves (presence of `ite_intelligence{}` block). Do not rely on this field alone for enrichment coverage — cross-reference with the enriched JSON directory.

### 6. Codon filename convention isn't universal
The majority of PDFs now use the `#@#ART-NNNN@#@` codon format. Some PDFs retain original filenames (pre-project library) and have no DB match via codon. The enricher v4 will fall back to Strategy 1 (clean_ref) for these, but most will be `no_match` unless their JSON has a `clean_ref` field populated. Check `articles.codon_filename` column to see which articles have a codon-formatted filename.

### 7. concept_tags is 100% populated but quality varies
All 1,629 ITE questions and all 1,221 AAFP questions have `concept_tags` populated by Claude, but:
- Some `diagnoses` arrays may include very broad terms ("infection")
- Some `drugs` entries mix brand names, generics, and drug classes
- `thresholds` may be empty for non-numeric questions
- The data was generated in a single $2.74 batch — no human review

### 8. Apostrophe handling in author names
Author names with apostrophes (O'Gurek, O'Brien) have the apostrophe stripped in `canonical_filename` but preserved in `clean_ref`. The enricher's `_strip_apostrophes()` handles this, but raw LIKE queries may miss matches:

```sql
-- This will miss O'Gurek articles
WHERE clean_ref LIKE 'OGurek%'

-- This catches both forms
WHERE clean_ref LIKE 'O%Gurek%' OR REPLACE(clean_ref, '''', '') LIKE 'OGurek%'
```

### 9. QID-2024-0168 known bad link
`QID-2024-0168` (SLE question) is linked to a hip pain article — this is a DB linkage issue, not an enricher bug. The pair exists in `question_ref_pairs` but the connection is wrong.

### 10. Title parsing varies by ref format
Two citation formats exist:
- **Colon format**: `Smith DK: Title text. Journal Year;vol(issue):pages`
- **Period format**: `Smith DK. Title text. Journal. Year;vol(issue):pages`

The `parse_title()` function in `rebuild_ite_db_v2.py` handles colon-format well but period-format parsing is less reliable — the `title` column may contain page numbers or journal names for period-format refs.

### 11. 2024 body system taxonomy change — use body_system_merged for trends
The 2024 ITE renamed three body system categories. Raw `body_system` values will show false drops/spikes for these categories. Always use `body_system_merged` for longitudinal trend analysis:
- `Injuries/Musculoskeletal` (2024 only, 20 rows) → merged to `Musculoskeletal`
- `Psychiatric/Behavioral` (2024 only, 14 rows) → merged to `Psychogenic`
- `Sexual and Reproductive` (2024 only, 11 rows) → merged to `Reproductive: Female`

```sql
-- WRONG for trends (will show Musculoskeletal crashing to 4 in 2024)
SELECT exam_year, body_system, COUNT(*) FROM questions GROUP BY exam_year, body_system;

-- CORRECT for trends (Musculoskeletal stays ~24 in 2024)
SELECT exam_year, body_system_merged, COUNT(*) FROM questions GROUP BY exam_year, body_system_merged;
```

### 12. qid_art_xref row count differs from question_ref_pairs
`qid_art_xref` has 2,470 rows vs. `question_ref_pairs` with 2,673. The xref table excludes unmatched/partial pairs and joins on `article_id` rather than `clean_ref`. Use the appropriate table for your query — xref for clean joins by article_id, pairs for full match metadata.

## Performance Notes

- The DB is moderate-sized (1,985 articles, 1,629 ITE + 1,221 AAFP questions, ~30 tables) — no indexes are defined and none are currently needed. Full table scans on all core tables are fast.
- sqlite-vec virtual table queries require the `sqlite-vec` extension loaded and are the only potentially slow operations.
- `LIKE '%term%'` on `concept_tags` is fine at this scale — no need for FTS.
- BLOB embedding comparisons (icd10_vec, article_icd10_vec, question_icd10_vec) require fetching and decoding in Python — not SQL-native. Use numpy for cosine similarity.
