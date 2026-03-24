# Metrics & KPIs

## citation_count

**Definition**: Number of distinct exam questions that cited this article in their explanation.
**Source**: `articles.citation_count` (INTEGER)
**Formula**: `COUNT(DISTINCT qid)` from `question_ref_pairs` WHERE `clean_ref` matches.
**Computed at**: DB build time by `rebuild_ite_db_v2.py`
**Range**: 0–12+ (30 articles have 0 = orphans; most have 1–2; high-yield articles have 5+)

## unique_years

**Definition**: Number of distinct exam years (2020–2025) in which this article was cited.
**Source**: `articles.unique_years` (INTEGER)
**Formula**: `COUNT(DISTINCT exam_year)` from linked questions.
**Significance**: Articles cited across multiple years indicate persistent exam relevance — the ABFM keeps coming back to them.

## Tier Classification

**Definition**: Priority ranking of an article for board preparation.
**Source**: `articles.tier` (TEXT)
**Values**:
| Tier | Count | Meaning |
|------|-------|---------|
| Must-Read | 20 | Highest-yield — cited frequently across multiple years |
| Core | 650 | Important — cited at least once, strong exam signal |
| Supplementary | 727 | Lower priority — single citation or auto-assigned |

**Assignment**: Mix of manual curation and auto-assignment (see `articles.auto_assigned`).

## TF-IDF Concept Scoring

**Definition**: Measures how specific a diagnosis concept is to a particular article's exam history vs. the entire question bank.
**Computed at**: Enrichment time by `_compute_concept_tfidf()` in both `ite_intelligence_enricher.py` and `ite_intelligence_enricher_batch.py`
**Not stored in DB** — computed on-the-fly during enrichment and written into the JSON's `linked_qids[].concept_colors`.

**Formula**:
- TF = (questions for this article mentioning concept) / (total questions for this article)
- IDF = log(total_articles / articles whose linked questions mention this concept)
- Score = TF × IDF

**Color buckets** (by tertile of scores for that article):
| Color | Meaning |
|-------|---------|
| Green | Top tertile — concept is specific to this article's exam history |
| Yellow | Middle tertile — moderately specific |
| Red | Bottom tertile — concept appears broadly across the question bank |

## Enrichment Confidence

**Definition**: Programmatic confidence in the DB match quality. Never delegated to Claude — computed deterministically.
**Source**: Written into extraction JSON's `ite_intelligence.enrichment_confidence`
**Not stored in the SQLite DB itself** — lives in the enriched JSON files.

**Rules** (v4, post-codon migration — from `compute_enrichment_confidence()`):
| match_method | Confidence | Rationale |
|---|---|---|
| `codon_filename` | **high** | ART-ID parsed directly from filename codon — deterministic |
| `clean_ref` | **high** | Exact DB primary key match — no ambiguity |
| anything else | low | Should not occur in v4; logged for review |

**Previous rules (v3, retired 2026-03-15)**: The v3 enricher had a 5-strategy cascade with medium confidence tiers for author_year, title_year, and org_year matches, and low confidence for vector_similarity. These were removed when the codon migration made fuzzy matching unnecessary.

## match_method (Enrichment Lookup)

**Definition**: Which lookup strategy successfully matched an extraction JSON to a DB article.
**Source**: Written into extraction JSON's `ite_intelligence._match_method`

**v4 strategies** (current):
1. `codon_filename` — ART-ID parsed from `#@#ART-XXXX@#@` in filename
2. `clean_ref` — exact match on `source.clean_ref` field in JSON

**Retired strategies** (removed in v4): `author_year_exact`, `author_year_title`, `author_year_ambiguous`, `title_year_pair`, `title_year_rare`, `org_year_exact`, `vector_similarity`

## match_status (DB-level pair quality)

**Definition**: Quality of the original question↔article linkage in the DB (not the enrichment match).
**Source**: `question_ref_pairs.match_status`
**Values**:
| Status | Count | Meaning |
|--------|-------|---------|
| matched | 1,316 | Clean exact match between question citation and article |
| fuzzy_matched | 409 | Fuzzy string matching resolved the link |
| partial | 196 | Partial match — some ambiguity remains |
| unmatched | 148 | Could not confidently link — may be noise |
