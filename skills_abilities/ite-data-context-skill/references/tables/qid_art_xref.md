# Table: qid_art_xref

**Location**: `ite_intelligence.db` → `qid_art_xref`
**Description**: Ergonomic crossref table linking questions to articles using `article_id` instead of the unwieldy `clean_ref` string. Provides a cleaner join path when you don't need the full match metadata from `question_ref_pairs`.
**Primary Key**: `(qid, article_id)` composite
**Row Count**: 1,818
**Update Frequency**: Rebuilt via `rebuild_ite_db_v2.py` when source data changes.

## Columns

| Column | Type | Description | Notes |
|--------|------|-------------|-------|
| `qid` | TEXT | Question ID | FK → `questions.qid`. e.g., `QID-2020-0001`. |
| `article_id` | TEXT | Article short ID | FK → `articles.article_id`. e.g., `ART-0470`. |
| `tier` | TEXT | Article tier at xref build time | Must-Read / Core / Supplementary. |
| `exam_year` | INTEGER | Denormalized exam year | Copied from question for fast filtering. |
| `author1` | TEXT | First author surname | Denormalized from articles table. |
| `year` | TEXT | Publication year | Denormalized from articles table. |

## Row Count vs question_ref_pairs

`qid_art_xref` has **1,818** rows vs. `question_ref_pairs` with **2,069** rows. The difference (251 rows) comes from excluded unmatched/partial pairs that couldn't be confidently linked to an article_id.

## When to Use

| Use Case | Table | Why |
|----------|-------|-----|
| Quick "which questions cite this article?" | `qid_art_xref` | Clean join on `article_id`, no subquery needed |
| Full match metadata (score, status, raw ref) | `question_ref_pairs` | Has `match_score`, `match_status`, `ref_raw` |
| Comprehensive citation analysis | `question_ref_pairs` | Includes all 2,069 pairs including partial/unmatched |
| Dashboard/report queries | `qid_art_xref` | Shorter joins, pre-filtered to confident matches |

## Sample Queries

### All questions for an article (by article_id — no subquery needed)
```sql
SELECT q.qid, q.exam_year, q.body_system_merged, q.question_text
FROM questions q
JOIN qid_art_xref x ON q.qid = x.qid
WHERE x.article_id = 'ART-0470'
ORDER BY q.exam_year;
```

### High-yield articles with question counts (clean join)
```sql
SELECT x.article_id, a.canonical_filename, a.tier,
       COUNT(*) AS q_count,
       GROUP_CONCAT(DISTINCT x.exam_year) AS years
FROM qid_art_xref x
JOIN articles a ON x.article_id = a.article_id
GROUP BY x.article_id
ORDER BY q_count DESC
LIMIT 20;
```

### Tier distribution of linked articles
```sql
SELECT x.tier, COUNT(DISTINCT x.article_id) AS articles,
       COUNT(*) AS total_links
FROM qid_art_xref x
GROUP BY x.tier
ORDER BY total_links DESC;
```
