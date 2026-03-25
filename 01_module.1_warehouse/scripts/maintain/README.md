# M1 / scripts / maintain — Warehouse Maintenance Scripts

**Definition:** Scripts that assume the DB exists and has data. Operational and recurring —
used to keep the warehouse current, extend it with new layers, and manage the PDF library.

---

## Scripts Present

### PDF Acquisition & Management
| Script | What It Does |
|--------|-------------|
| `aafp_fill_gaps.py` | Scrapes AAFP top-20, downloads missing PDFs into warehouse |
| `aafp_vc_batch_download.py` | Batch download for VC-cited articles |
| `aafp_top20_downloader.py` | Top-20 article downloader (AAFP) |
| `aafp_retry_playwright.py` | Browser-auth fallback for paywalled PDFs |
| `aafp_retry_selenium.py` | Selenium fallback for paywalled PDFs |
| `aafp_cleanup_filenames.py` | Fixes ALL-CAPS author names in PDF filenames |

### Codon & Crosswalk
| Script | What It Does |
|--------|-------------|
| `build_crosswalk_index.py` | Scans warehouse for codon filenames → builds crosswalk_index.json |
| `build_match_staging.py` | Proposes ART-ID matches for unmatched PDFs (staging review) |
| `rename_to_codon.py` | Executes approved codon renames on PDFs in warehouse |

### Reference Tier Matching & Acquisition
| Script | What It Does | Output |
|--------|-------------|--------|
| `match_tiers_to_library.py` | Scans warehouse PDFs against `ABFM_ITE_ReferenceTiers_Expanded_v1369.csv`; classifies each ref as MATCHED/NOT_FOUND | `archive_canonical/05_acquisition/match_summary.csv`, `matched_high.csv`, `not_found.csv`, `match_report.json` |
| `rebuild_acquisition_list.py` | Reads `match_summary.csv` → builds confirmed present list and ranked acquisition XLSX | `archive_canonical/05_acquisition/confirmed_present.csv`, `ABFM_ITE_ReferenceAcquisitionList_Core_Ranked.xlsx` |

**Typical use:** Run `match_tiers_to_library.py` first, then `rebuild_acquisition_list.py`. Together they answer "what do we have, what do we still need, and what should we prioritize acquiring?"

---

### Intelligence Layers (DB enrichment — needs live data)
| Script | What It Does | Output |
|--------|-------------|--------|
| `build_clinical_pathways.py` | Layer 3: builds `clinical_pathways` table | 4,528+ rows |
| `build_topic_trends.py` | Layer 4a: builds topic trend CSVs | body_system/subcategory/concept_tag trends |

> **Note:** `build_clinical_pathways.py` and `build_topic_trends.py` also exist in
> `03_module.3_analyst/scripts/` — M1 is the canonical home. M3 copies are duplicates
> to be removed during next housekeeping pass.

---

## Typical Use Patterns

**Adding new PDFs to warehouse:**
```
1. aafp_fill_gaps.py or aafp_vc_batch_download.py   → download new PDFs
2. aafp_cleanup_filenames.py                         → fix naming
3. build_match_staging.py                            → propose ART-ID matches
4. rename_to_codon.py                                → apply approved renames
5. build_crosswalk_index.py                          → rebuild crosswalk
```

**Rebuilding intelligence layers:**
```
1. build_clinical_pathways.py   → Layer 3 (pathways)
2. build_topic_trends.py        → Layer 4a (trends)
```

---

*Last updated: 2026-03-24 (BATON 005 → 006 session — added match_tiers_to_library.py, rebuild_acquisition_list.py from TEMP_05 migration)*
