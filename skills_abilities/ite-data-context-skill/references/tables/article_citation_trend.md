# Table: article_citation_trend

**Location**: `ite_intelligence.db` → `article_citation_trend`
**Description**: Pre-computed longitudinal citation data for each article that has appeared in `qid_art_xref`. Tracks which exam years each article was cited, how many consecutive years, and whether it's on a "watch list" for trending relevance. Rebuilt on demand via `update_citation_trends.py` (full DELETE + re-insert).
**Primary Key**: `article_id` (TEXT)
**Row Count**: 1,740

## Columns

| Column | Type | Description | Notes |
|--------|------|-------------|-------|
| `article_id` | TEXT | FK → `articles.article_id` | PK. |
| `years_cited` | TEXT | Comma-separated list of exam years | e.g., `"2020,2022,2024"`. |
| `distinct_year_count` | INTEGER | Count of unique exam years cited | 1–8. |
| `first_cited_year` | INTEGER | Earliest exam year with a citation | |
| `most_recent_year` | INTEGER | Most recent exam year with a citation | |
| `consecutive_streak` | INTEGER | Longest run of back-to-back years cited | e.g., if cited 2022+2023+2024, streak=3. |
| `is_watch_list` | INTEGER | 1 if consecutive_streak ≥ 2, else 0 | Flag for articles gaining momentum. |

## Key Use Cases

This table answers questions like:
- "Which articles have been cited in 5+ exam years?" (longitudinal relevance)
- "Which articles are on a recent multi-year streak?" (trending topics)
- "Which articles appeared only once, years ago?" (potentially stale)

## Sample Queries

### Articles cited in the most exam years (highest longitudinal relevance)
```sql
SELECT t.article_id, a.canonical_filename, a.tier,
       t.years_cited, t.distinct_year_count
FROM article_citation_trend t
JOIN articles a ON t.article_id = a.article_id
WHERE t.distinct_year_count >= 4
ORDER BY t.distinct_year_count DESC, t.most_recent_year DESC;
```

### Watch list — articles on a consecutive-year streak
```sql
SELECT t.article_id, a.canonical_filename, a.tier,
       t.years_cited, t.consecutive_streak, t.most_recent_year
FROM article_citation_trend t
JOIN articles a ON t.article_id = a.article_id
WHERE t.is_watch_list = 1
ORDER BY t.consecutive_streak DESC, t.distinct_year_count DESC;
```

### Recently emerging articles (cited in last 2 years but not before)
```sql
SELECT t.article_id, a.canonical_filename, a.tier,
       t.years_cited, t.first_cited_year, t.most_recent_year
FROM article_citation_trend t
JOIN articles a ON t.article_id = a.article_id
WHERE t.first_cited_year >= 2023
  AND t.distinct_year_count >= 1
ORDER BY t.first_cited_year DESC;
```

### Articles that have dropped off (cited before 2023 but not recently)
```sql
SELECT t.article_id, a.canonical_filename,
       t.years_cited, t.most_recent_year
FROM article_citation_trend t
JOIN articles a ON t.article_id = a.article_id
WHERE t.most_recent_year < 2023
  AND t.distinct_year_count >= 2
ORDER BY t.most_recent_year, t.distinct_year_count DESC;
```

## Rebuild Notes

- **Script**: `update_citation_trends.py` — full DELETE + re-insert from `qid_art_xref`
- **Trigger**: Run after any `qid_art_xref` rebuild (e.g., after adding new exam year data)
- **Source of truth**: `qid_art_xref` — `article_citation_trend` is a derived/disposable table
