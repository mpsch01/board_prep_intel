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

**Definition**: Pipeline staging tier for each article — reflects both VC gate status and whether the article has completed the full enrichment pipeline.
**Source**: `articles.tier` (TEXT)
**Values**:
| Tier | Count | Meaning |
|------|-------|---------|
| VC_fail | 1,448 | Failed VC gate — not in the 352 high-yield AAFP VC citations; awaiting pipeline |
| VC_pass | 362 | Passed VC gate — in the 352 VC citations; awaiting full pipeline |
| local_lite | 117 | Pipeline complete: VC_fail + DOCX exists |
| right_click | 58 | Pipeline complete: VC_pass + DOCX exists — highest priority tier |

**VC gate**: `key_data_files/session_hy_inserts_v7.json` (352 citations from the AAFP Board Prep Video Course). Passing the VC gate is the **sole criterion** for VC_pass vs. VC_fail. DB membership alone is not sufficient for right_click status.

**Completed tiers**: `right_click` and `local_lite` mean the article has been extracted, enriched (Claude API), and has a DOCX output in the DOCX library. These are "M2 complete" articles.

**Note**: These tiers replaced the old Must-Read/Core/Supplementary system during the Project Overhaul.

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
| matched | 1,698 | Clean exact match between question citation and article |
| new | 389 | New pair added in most recent rebuild cycle |
| unmatched | 246 | Could not confidently link — may be noise |
| fuzzy_matched | 154 | Fuzzy string matching resolved the link |
| fuzzy | 120 | Fuzzy match (legacy label from earlier build) |
| partial | 66 | Partial match — some ambiguity remains |
