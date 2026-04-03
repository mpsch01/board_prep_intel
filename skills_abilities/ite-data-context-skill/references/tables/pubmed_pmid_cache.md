# Table: pubmed_pmid_cache

**Location**: `ite_intelligence.db` → `pubmed_pmid_cache`
**Description**: Seed table for Intelligence 2.0 Layer 2 (article currency). Maps `citation_id` strings (from AAFP citation data) to PubMed PMIDs. Populated via PubMed API lookup. Enables freshness checking — determining if a cited article has been superseded or updated.
**Primary Key**: `citation_id` (TEXT)
**Row Count**: 344

## Columns

| Column | Type | Description | Notes |
|--------|------|-------------|-------|
| `citation_id` | TEXT | FK → `aafp_citations.citation_id` | PK. Format: `AAFP-NNNNN-CN` (e.g., `AAFP-49863-C1`). |
| `pmid` | TEXT | PubMed article ID | TEXT, not INTEGER, to preserve leading zeros if any. |
| `lookup_date` | TEXT | Date PMID was resolved | ISO date string. Default: `date('now')`. |
| `mesh_count` | INTEGER | Number of MeSH terms on PubMed record | 0 if lookup returned no MeSH data. |

## Join Pattern

```sql
-- Find PubMed record for a matched article
SELECT pc.citation_id, pc.pmid, pc.mesh_count,
       a.canonical_filename, a.year, a.tier
FROM pubmed_pmid_cache pc
JOIN aafp_citations ac ON pc.citation_id = ac.citation_id
JOIN articles a ON ac.article_id = a.article_id
WHERE a.citation_count > 0
ORDER BY pc.mesh_count DESC
LIMIT 20;
```

## Context: Intelligence 2.0 Layer 2

This table is the **seed** for the article currency layer — not yet fully built as of 2026-04-03. The planned `article_currency` table (not yet created) will:
- Use `pubmed_pmid_cache` to resolve PMIDs
- Check PubMed for publication date, retraction status, and whether a newer version exists
- Populate fields like `freshness_score`, `superseded_by`, `last_checked`

**Current status**: 344 PMIDs cached from AAFP citation matches (2026-03-31). Layer 2 build is DEFERRED (see BATON).
