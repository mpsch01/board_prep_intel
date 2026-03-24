# Table: question_ref_pairs

**Location**: `ite_intelligence.db` → `question_ref_pairs`
**Description**: Junction table linking questions to the articles cited in their explanations. One row per citation — a question citing 3 articles produces 3 rows.
**Primary Key**: `id` (INTEGER AUTOINCREMENT)
**Row Count**: 2,069
**Update Frequency**: Rebuilt via `rebuild_ite_db_v2.py`.

## Columns

| Column | Type | Description | Notes |
|--------|------|-------------|-------|
| `id` | INTEGER | Auto-incrementing PK | Sequence max: 2,069. |
| `qid` | TEXT | FK → `questions.qid` | e.g., `QID-2020-0001`. Not enforced. |
| `clean_ref` | TEXT | FK → `articles.clean_ref` | Full citation string. Not enforced. |
| `ref_raw` | TEXT | Original raw citation text | Before cleaning. May differ from `clean_ref`. |
| `tier` | TEXT | Tier at time of pairing | May differ from current `articles.tier` if re-tiered. |
| `match_score` | REAL | 0.0–1.0 match confidence | 1.0 = exact match. |
| `ref_index` | INTEGER | Citation order within question | 1 = first reference, 2 = second, etc. |
| `match_status` | TEXT | Quality of the link | See distribution below. |
| `exam_year` | INTEGER | Denormalized exam year | Copied from `questions.exam_year` for fast filtering. |

## match_status Distribution

| Status | Count | Description |
|--------|-------|-------------|
| matched | 1,316 | Clean exact match |
| fuzzy_matched | 409 | Resolved via fuzzy string matching |
| partial | 196 | Some ambiguity remains |
| unmatched | 148 | Could not confidently link |

## Relationships

```
questions.qid ──── question_ref_pairs.qid
                              │
articles.clean_ref ── question_ref_pairs.clean_ref
```

## Sample Queries

### Articles most frequently cited (via pairs)
```sql
SELECT a.article_id, a.canonical_filename, a.tier, COUNT(*) AS times_cited
FROM question_ref_pairs p
JOIN articles a ON p.clean_ref = a.clean_ref
WHERE p.match_status IN ('matched', 'fuzzy_matched')
GROUP BY a.article_id
ORDER BY times_cited DESC
LIMIT 15;
```

### Questions with multiple references
```sql
SELECT qid, COUNT(*) AS ref_count
FROM question_ref_pairs
GROUP BY qid
HAVING ref_count > 1
ORDER BY ref_count DESC;
```

### Match quality by exam year
```sql
SELECT exam_year, match_status, COUNT(*) AS n
FROM question_ref_pairs
GROUP BY exam_year, match_status
ORDER BY exam_year, n DESC;
```