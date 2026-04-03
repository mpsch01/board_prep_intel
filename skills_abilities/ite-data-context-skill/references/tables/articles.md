# Table: articles

**Location**: `ite_intelligence.db` → `articles`
**Description**: One row per unique clinical reference. Contains parsed metadata, tier classification, citation stats, and preprocessed filename components. All fields are populated at DB build time.
**Primary Key**: `clean_ref` (TEXT)
**Row Count**: 1,985
**Update Frequency**: Rebuilt via `rebuild_ite_db_v2.py` when source data changes.

## Columns

| Column | Type | Description | Notes |
|--------|------|-------------|-------|
| `clean_ref` | TEXT | Original cleaned citation string | PK. Stable across rebuilds. Can be very long (200+ chars). |
| `article_id` | TEXT | Stable short ID: `ART-0001` | UNIQUE. Assigned alphabetically at build time. |
| `author1` | TEXT | Parsed first author surname | May be org name (e.g., "USPSTF", "AAP") for guidelines. |
| `author2` | TEXT | Parsed second author surname | NULL for single-author or org-authored refs. |
| `year` | TEXT | Publication year | Stored as TEXT, not INTEGER. NULL for some non-standard refs. |
| `title` | TEXT | Parsed title from clean_ref | Parsing quality varies — period-format vs. colon-format refs. |
| `source_type` | TEXT | Journal/source classification | See distribution below. |
| `categories` | TEXT | Body system categories | From tiers CSV. Comma-separated when multiple. |
| `blueprint_cats` | TEXT | ABFM blueprint categories | Often empty. |
| `tier` | TEXT | Must-Read / Core / Supplementary | See metrics.md for definitions. |
| `auto_assigned` | TEXT | "Yes" or "No" | Whether tier was auto-assigned vs. manually curated. |
| `citation_count` | INTEGER | Number of linked questions | 0 for orphan articles. |
| `unique_years` | INTEGER | Distinct exam years cited | 0–6. |
| `exam_years` | TEXT | JSON array of years | e.g., `[2020, 2022, 2024]`. Use `json_extract()`. |
| `qid_list` | TEXT | JSON array of linked QIDs | e.g., `["QID-2020-0001", "QID-2022-0045"]`. |
| `canonical_filename` | TEXT | Clean filename stem | `Smith_Moore_2019`. Apostrophes stripped. |
| `codon_filename` | TEXT | Full codon filename | `Smith_Moore_2019#@#ART-0470@#@.pdf` |
| `citation_display` | TEXT | Formatted citation for DOCX | Truncated to ~180 chars with ellipsis if needed. |
| `extraction_status` | TEXT | Pipeline status | `extracted` or `pending`. Tracks JSON extraction, not enrichment completion. |
| `engine_type` | TEXT | Article's clinical function | `acute_protocol` (1,169), `chronic_guideline` (284), `preventive_guideline` (268), `diagnostic_guideline` (237), `rct` (27). Classified at DB build time from subcategories + source_type. |

## source_type Distribution

| source_type | Count |
|-------------|-------|
| AFP | 700 |
| Other Journal | 649 |
| Guideline/Org | 233 |
| NEJM | 91 |
| JAMA | 76 |
| Pediatrics | 48 |
| Annals | 43 |
| Circulation | 38 |
| Textbook | 34 |
| BMJ | 32 |
| Chest | 18 |
| Lancet | 14 |
| Cochrane | 9 |

## tier Distribution (Pipeline Staging Tiers)

| tier | Count | Meaning |
|------|-------|---------|
| VC_fail | 1,448 | Failed VC gate — not in the 352 high-yield AAFP VC citations |
| VC_pass | 362 | Passed VC gate — in the 352 VC citations, awaiting full enrichment |
| local_lite | 117 | Completed (VC_fail + DOCX exists) |
| right_click | 58 | Completed (VC_pass + DOCX exists) — highest priority tier |

**Note**: These are pipeline staging tiers, not priority rankings. The VC gate (`key_data_files/session_hy_inserts_v7.json`, 352 citations) is the sole criterion for VC_pass vs. VC_fail. `right_click` and `local_lite` are the two "M2 completed" tiers — article has been fully extracted, enriched, and has a DOCX output.

## Sample Queries

### Top Must-Read articles by citation count
```sql
SELECT article_id, canonical_filename, citation_count, unique_years, exam_years
FROM articles
WHERE tier = 'Must-Read'
ORDER BY citation_count DESC;
```

### Articles by source type with exam coverage
```sql
SELECT source_type, COUNT(*) AS n_articles,
       SUM(citation_count) AS total_citations,
       AVG(citation_count) AS avg_citations
FROM articles
WHERE citation_count > 0
GROUP BY source_type
ORDER BY total_citations DESC;
```

### Find article by partial author/title match
```sql
SELECT article_id, canonical_filename, tier, citation_count
FROM articles
WHERE LOWER(clean_ref) LIKE '%empagliflozin%'
   OR LOWER(canonical_filename) LIKE '%empagliflozin%';
```