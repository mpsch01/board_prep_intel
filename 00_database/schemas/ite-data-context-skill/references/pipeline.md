# Pipeline & Scripts

## Architecture Overview

```
[PDF Library] → [right-click extract_guideline.bat] → [5-step pipeline] → [enriched JSON + DOCX]
                                                            │
                                                     ite_intelligence.db
                                                     (preprocessed at build time)
```

## Right-Click Pipeline (extract_guideline.bat)

| Step | Script | What It Does |
|------|--------|-------------|
| 1/5 | `ingestion.py` | Extract text from PDF, parse QID codon from filename |
| 2/5 | `synthesize.js` | Generate `clinical_bottom_line` + `practice_pearls` |
| 3/5 | `ite_intelligence_enricher.py` | Match article to DB → Claude generates `ite_intelligence{}` block |
| 4/5 | `build_summary.js` | Generate DOCX with all sections including ITE Intelligence |
| 5/5 | `calibrate.py` | Optional QC scoring (if `--calibrate` flag) |

## Batch Pipeline (for large runs)

Three-script sequence run from PowerShell:

```
convert_pdfs_to_json.py → ite_intelligence_enricher_batch.py → build_crosswalk_index.py
```

| Step | Script | What It Does |
|------|--------|-------------|
| 1/3 | `convert_pdfs_to_json.py` v1.2 | PDF → `*_extracted.json` + `raw_txt/*.raw.txt` via pdfplumber |
| 2/3 | `ite_intelligence_enricher_batch.py` v4 | DB lookup + Anthropic Batch API enrichment (50% cheaper) |
| 3/3 | `build_crosswalk_index.py` v2.0 | Parse codon ART-IDs → `crosswalk_index.json` + coverage report |

The batch enricher has a three-phase workflow:
1. **Submit**: DB lookup for all JSONs → bundle matched files → Batch API call → save state file
2. **Poll**: Check batch processing status
3. **Write**: Pull results → write `ite_intelligence{}` blocks back into JSONs

## DB Build Scripts

| Script | Purpose | Status |
|--------|---------|--------|
| `rebuild_ite_db_v2.py` | Full DB rebuild from source data | COMPLETE |
| `preprocess_keywords_v2.py` | Claude-preprocessed concept_tags for all 1,189 questions | COMPLETE (cost: $2.74) |
| `validate_db_v2.py` | QC report confirming DB integrity | COMPLETE |
| `compute_embeddings.py` | Generate OpenAI embeddings for article_vec + question_vec | COMPLETE (1,397 + 1,189 vectors) |
| `validate_vector_search.py` | Threshold calibration for vector similarity | COMPLETE |

## Enrichment Scripts

| Script | Purpose | Status |
|--------|---------|--------|
| `ite_intelligence_enricher.py` v4 | Single-file enricher — 2-strategy codon-first lookup | ACTIVE |
| `ite_intelligence_enricher_batch.py` v4 | Batch API enricher — same 2-strategy lookup, 50% cheaper | ACTIVE |
| `clear_and_reenrich.py` | Strip `ite_intelligence` block + re-run enricher on folder | UTILITY |
| `backfill_extraction_status.py` | Mark articles as 'extracted' via QID bridge | COMPLETE |
| `rename_to_codon.py` | Rename PDFs to codon format (Author_Year#@#ART-XXXX@#@.pdf) | COMPLETE |

## Intelligence 2.0 Build Scripts

| Script | Layer | Purpose | Cost | Status |
|--------|-------|---------|------|--------|
| `build_topic_trends.py` | 4a | 3-tier ITE trend CSVs (body_system, subcategory, concept_tags) | $0 | COMPLETE |
| `build_icd10_tags.py` | 1 | Batch API → article_icd10 table + condensation crosswalk | ~$3.28 | COMPLETE |
| `build_clinical_pathways.py` | 3 | Engine-type classification → clinical_pathways table | $0 | COMPLETE |

## Additional Scripts

| Script | Purpose | Status |
|--------|---------|--------|
| `db_guided_extractor.py` | Single Claude call per file using pre-computed DB intelligence | ACTIVE |
| `batch_db_extract.py` | Batch wrapper for db_guided_extractor | ACTIVE |
| `build_match_staging.py` | Build match staging data for triage | UTILITY |

## Enricher Lookup (v4 — 2 Strategies, Codon-First)

The enricher tries to match an extraction JSON to a DB article. First match wins:

### Strategy 0: Codon filename (primary)
- Parses ART-ID directly from the JSON's `source.file_name` or the JSON filename itself
- Regex: `#@#(ART-\d+)@#@`
- Looks up `articles.article_id` for an exact match
- Result: `codon_filename` → always **high** confidence

### Strategy 1: clean_ref (fallback)
- Reads `source.clean_ref` field from the JSON (present in v1.1+ schema)
- Exact match against `articles.clean_ref` (the PK)
- Result: `clean_ref` → always **high** confidence

### No match
- If neither strategy hits, the file is logged as `no_match` for manual review
- Non-codon files (76 in current library) will always be no_match unless they have a `clean_ref` in their JSON

**Previous strategies removed in v4** (2026-03-15): author_year, title_year_pair, title_year_rare, org_year, vector_similarity. These produced low/medium confidence matches that required manual triage. The codon migration eliminated the need for fuzzy matching.

## Data Flow Summary

```
SOURCE DATA                          DB BUILD TIME                    ENRICHMENT TIME
─────────────                        ─────────────                    ───────────────
ite_questions_clean.json ──→ rebuild_ite_db_v2.py ──→ questions table
question_ref_pairs.csv   ──→ rebuild_ite_db_v2.py ──→ question_ref_pairs table
tier lists (CSV)         ──→ rebuild_ite_db_v2.py ──→ articles table
                                     │
                              preprocess_keywords_v2.py ──→ concept_tags (Claude API)
                              compute_embeddings.py     ──→ article_vec, question_vec (OpenAI API)
                                     │
                                     ▼
                         ite_intelligence.db (fully preprocessed)
                                     │
                                     ▼
                         ite_intelligence_enricher.py v4
                              │
                              ├─ lookup_article()  → codon parse or clean_ref match
                              ├─ build_ite_intelligence() → Claude API (semantic interpretation only)
                              ├─ compute_enrichment_confidence() → deterministic (high/high/low)
                              └─ _compute_concept_tfidf() → TF-IDF color-coding per diagnosis
                                     │
                                     ▼
                              Enriched JSON with ite_intelligence{} block
```

## Key Config Constants

| Constant | Value | Location |
|----------|-------|----------|
| `MODEL` | `claude-sonnet-4-20250514` | enricher.py, enricher_batch.py |
| `JSON_DIR` | `clinical_guidelines/03_enriched_JSON` | enricher_batch.py (default target) |
| `PDF_DIR` | `clinical_guidelines/01_pdf_guideline_library/pdf_codon` | build_crosswalk_index.py |

## File Locations

| Item | Path |
|------|------|
| DB | `abfm_prep/02_ite_intelligence/db/ite_intelligence.db` |
| Enricher (single) | `abfm_prep/02_ite_intelligence/scripts/ite_intelligence_enricher.py` |
| Enricher (batch) | `abfm_prep/02_ite_intelligence/scripts/ite_intelligence_enricher_batch.py` |
| DB builder | `abfm_prep/02_ite_intelligence/scripts/rebuild_ite_db_v2.py` |
| PDF-to-JSON | `abfm_prep/02_ite_intelligence/scripts/convert_pdfs_to_json.py` |
| Crosswalk builder | `abfm_prep/02_ite_intelligence/scripts/build_crosswalk_index.py` |
| Questions JSON | `abfm_prep/03_ite_exam/03_database/ite_questions_clean.json` |
| Enriched JSONs | `clinical_guidelines/03_enriched_JSON/` (216 files: 146 enriched + 70 scaffold) |
| PDF library (codon) | `clinical_guidelines/01_pdf_guideline_library/pdf_codon/` |
| PDF library (non-codon) | `clinical_guidelines/01_pdf_guideline_library/pdf_non-codon/` |
| DOCX library | `clinical_guidelines/02_docx_guideline_library/` |
| Pipeline bat | `abfm_prep/01_guideline_extractor/oneclick/extract_guideline.bat` |
| Enricher logs | `abfm_prep/02_ite_intelligence/logs/` |
