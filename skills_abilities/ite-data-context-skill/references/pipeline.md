# Pipeline & Scripts

## Architecture Overview

```
[PDF Library] → [right-click extract_guideline.bat] → [5-step pipeline] → [enriched JSON + DOCX]
                                                            │
                                                     ite_intelligence.db
                                                     (preprocessed at build time)
```

## Module Map

| Module | Path | What it does |
|--------|------|--------------|
| M1 Warehouse | `01_module.1_warehouse/` | PDF library (4 tiers) + build/ + maintain/ scripts |
| M2 Processor | `02_module.2_processor/` | Extraction, enrichment, DOCX builders + source/ inputs |
| M3 Analyst | `03_module.3_analyst/` | ICD-10 tagging, pathways, trends, score analysis |
| M4 Sandbox | `04_module.4_sandbox/` | Experiments, agents |
| DB | `00_database/db/ite_intelligence.db` | Source of truth |

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

## M1 DB Build Scripts

| Script | Purpose | Status |
|--------|---------|--------|
| `rebuild_ite_db_v2.py` | Full DB rebuild from source data | COMPLETE |
| `preprocess_keywords_v2.py` | Claude-preprocessed concept_tags for all 1,629 ITE questions | COMPLETE |
| `validate_db_v2.py` | QC report confirming DB integrity | COMPLETE |
| `compute_embeddings.py` | Generate OpenAI embeddings → article_vec + question_vec + aafp_question_vec | COMPLETE (1,985 + 1,629 + 1,221 vectors) |

## M2 Enrichment Scripts

| Script | Purpose | Status |
|--------|---------|--------|
| `ite_intelligence_enricher.py` v4 | Single-file enricher — 2-strategy codon-first lookup | ACTIVE |
| `ite_intelligence_enricher_batch.py` v4 | Batch API enricher — same 2-strategy lookup, 50% cheaper | ACTIVE |
| `clear_and_reenrich.py` | Strip `ite_intelligence` block + re-run enricher on folder | UTILITY |
| `rename_to_codon.py` | Rename PDFs to codon format (`Author_Year#@#ART-XXXX@#@.pdf`) | COMPLETE |
| `build_summary.js` | Generate DOCX from enriched JSON | ACTIVE |

## M3 Intelligence 2.0 Build Scripts

| Script | Layer | Purpose | Cost | Status |
|--------|-------|---------|------|--------|
| `build_icd10_tags.py` | 1 | Batch API → `article_icd10` table + condensation crosswalk | ~$3.28 | COMPLETE |
| `build_question_icd10.py` | 1 | Batch API → `question_icd10` table (ITE + AAFP) | batch API | COMPLETE |
| `build_clinical_pathways.py` | 3 | Blueprint-based → `clinical_pathways` table (both banks) | $0 | COMPLETE (REBUILT 2026-03-31) |
| `build_icd10_embeddings.py` | vec | OpenAI embeddings → `icd10_vec`, `article_icd10_vec`, `question_icd10_vec` | OpenAI | COMPLETE (rebuilt 2026-04-01) |
| `build_topic_trends.py` | 4a | 3-tier ITE trend CSVs (body_system, blueprint, concept_tags) | $0 | COMPLETE |
| `update_citation_trends.py` | trend | Rebuild `article_citation_trend` from `qid_art_xref` | $0 | DEFERRED-B (run after PDF download) |
| `download_aafp_acquisitions.py` | acq | Download new AAFP article PDFs (ART-1938–ART-1986) | $0 | DEFERRED-A |

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
- Non-codon files without a clean_ref in their JSON will always be no_match

**Previous strategies removed in v4** (2026-03-15): `author_year`, `title_year_pair`, `title_year_rare`, `org_year`, `vector_similarity`. These produced low/medium confidence matches requiring manual triage. The codon migration eliminated the need for fuzzy matching.

## Data Flow Summary

```
SOURCE DATA                          DB BUILD TIME                    ENRICHMENT TIME
─────────────                        ─────────────                    ───────────────
ite_questions_clean.json ──→ rebuild_ite_db_v2.py ──→ questions table (1,629)
aafp_brq/ scraper        ──→ aafp_brq build seq  ──→ aafp_questions (1,221)
question_ref_pairs.csv   ──→ rebuild_ite_db_v2.py ──→ question_ref_pairs (2,673)
tier lists (CSV)         ──→ rebuild_ite_db_v2.py ──→ articles (1,985)
                                     │
                              preprocess_keywords_v2.py ──→ concept_tags (Claude Batch API)
                              build_icd10_tags.py        ──→ article_icd10, icd10_code_xref (Claude Batch API)
                              build_question_icd10.py    ──→ question_icd10, aafp_question_icd10 (Claude Batch API)
                              build_clinical_pathways.py ──→ clinical_pathways (deterministic, $0)
                              build_icd10_embeddings.py  ──→ icd10_vec, article_icd10_vec, question_icd10_vec (OpenAI)
                              compute_embeddings.py      ──→ article_vec, question_vec, aafp_question_vec (OpenAI)
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
| `JSON_DIR` | `02_module.2_processor/extracted_json/` | enricher_batch.py (default target) |
| `DB_PATH` | `00_database/db/ite_intelligence.db` | all scripts (dynamic via PROJECT_ROOT) |

## File Locations (project-relative)

| Item | Path |
|------|------|
| DB | `00_database/db/ite_intelligence.db` |
| Enricher (single) | `02_module.2_processor/ite_intelligence_enricher.py` |
| Enricher (batch) | `02_module.2_processor/ite_intelligence_enricher_batch.py` |
| DB builder | `01_module.1_warehouse/build/rebuild_ite_db_v2.py` |
| ITE Questions JSON | `01_module.1_warehouse/source/ite_questions_clean.json` |
| AAFP BRQ scraper | `01_module.1_warehouse/aafp_brq/` |
| M3 Analyst scripts | `03_module.3_analyst/` |
| VC Gate JSON | `key_data_files/session_hy_inserts_v7.json` |
| PDF tiers | `01_module.1_warehouse/` (VC_pass/, VC_fail/, right_click/, local_lite/) |

## Dynamic Path Pattern (mandatory in all scripts)

```python
# Python
from pathlib import Path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent  # 2 hops up from script file
DB_PATH = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"
```

```js
// JavaScript
const path = require('path');
const PROJECT_ROOT = path.resolve(__dirname, '../../');
const DB_PATH = path.join(PROJECT_ROOT, '00_database', 'db', 'ite_intelligence.db');
```
