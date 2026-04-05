
---
name: project_overhaul_state
description: BATON 040, EXA PDF pipeline complete — 868 PDFs on disk, 3 new M1 maintain scripts, DEFERRED-G (Unpaywall) next
type: project
---

**Project:** ABFM ITE Intelligence System (Family Medicine board exam knowledge base)
**Root (Windows):** `C:\Users\mpsch\Desktop\board_prep_intel\`
**Active BATON:** `BATON_active_040_20260405_exa_pdf_pipeline.md`
**Git:** `main`, latest committed → 3 new scripts pending commit (exa_pdf_finder.py, exa_pdf_downloader.py, pmc_oa_downloader.py)

---

## Current Phase: EXA PDF Pipeline Complete — Unpaywall Next

**BATON 040 (2026-04-05):**
- **`exa_pdf_finder.py` built** — EXA semantic search across 1,572 missing articles; outputs exa_pdf_queue.csv + exa_pdf_queue.json; classified 259 direct_pdf + 332 open_access + 109 pmc_fulltext + 872 landing_page
- **`exa_pdf_downloader.py` built** — downloads direct_pdf + AAFP open_access + pmc_fulltext from queue; 397/558 downloaded (215 direct + 190 AAFP + 0 PMC via this script); PDFs 413→821
- **`pmc_oa_downloader.py` built** — NCBI OA API (oa.fcgi); 14 direct OA + 33 tgz extracted (tarball in-memory extraction); 47/95 downloaded; PDFs 821→868
- **AAFP open-access confirmed** — AFP articles ≥12 months old accessible at .pdf URLs without login (HTTP 200); .html→.pdf URL swap works; no auth needed for 2024 and older
- **PMC direct endpoint blocked** — 403 for Python requests; OA API is the correct path
- **62 not_oa PMC + 872 landing_page** — remaining targets for DEFERRED-G (Unpaywall)

**Windows cleanup:** Complete ✓ (BATON 039)

---

## Module State

| Module | Location | Scripts | Status |
|--------|----------|---------|--------|
| M1 Warehouse | `01_module.1_warehouse/` | 6 build + 21 maintain + aafp_brq_scraper.py at scripts/ root | 3 new maintain scripts added 2026-04-05 |
| M2 Processor | `02_module.2_processor/scripts/` | 75 Python + 6 JS + 1 config JSON; +core(4py) +engines(7py) +utils(6py) packages | Stable |
| M3 Analyst | `03_module.3_analyst/scripts/` | 13 Python + 2 JS + 2 JSON config | Stable |
| DB | `00_database/db/ite_intelligence.db` | Source of truth | 1,985 articles, 1,629 ITE Q, 1,221 AAFP Q — unchanged |
| Apify | `skills_abilities/apify-actors/citation_crawler/` | 1 actor (PlaywrightCrawler) | DEPLOYED ✅ build 0.3.1 |

---

## M1 Warehouse Domain Layout (confirmed 2026-04-05)

```
01_module.1_warehouse/
├── citation_files/
│   ├── ITE/
│   │   ├── VC_pass/        ← 94 PDFs (VC gate passed — destined for right_click)
│   │   ├── VC_fail/        ← bulk PDFs (exa downloads landed here)
│   │   ├── local_lite/     ← 117 PDFs (VC_fail + fully enriched)
│   │   └── right_click/    ← 71 PDFs (VC_pass + fully enriched)
│   │   [Total: 868 PDFs across 4 tiers as of 2026-04-05]
│   └── AAFP/               ← AAFP citation PDFs
├── practice_questions/
│   ├── word_docs/          ← 8 ITE DOCX + 13 AAFP DOCX (gitignored)
│   └── excel/              ← 8 ITE XLSX + 13 AAFP XLSX (gitignored)
├── ite_exams/              ← 16 raw PDFs: YYYY_MC.pdf + YYYY_critique.pdf (2018–2025)
└── scripts/
    ├── aafp_brq_scraper.py ← scraper at scripts/ root
    ├── build/              ← 6 scripts
    └── maintain/           ← 21 scripts (3 new: exa_pdf_finder, exa_pdf_downloader, pmc_oa_downloader)
```

---

## EXA Pipeline — Key Artifacts

| File | Location | Description |
|------|----------|-------------|
| `exa_pdf_queue.csv` | M1/scripts/maintain/ | 1,572 articles classified; actionable: direct_pdf + open_access + pmc_fulltext |
| `exa_pdf_queue.json` | M1/scripts/maintain/ | JSON version of queue |
| `exa_download_results.csv` | M1/scripts/maintain/ | Per-article download outcomes from exa_pdf_downloader |
| `pmc_oa_results.csv` | M1/scripts/maintain/ | Per-article PMC OA API outcomes |
| `exa_run.log` / `exa_download.log` / `pmc_oa.log` | M1/scripts/maintain/ | Run logs (gitignored) |

---

## Key Numbers (as of BATON 040, 2026-04-05)

- **DB articles:** 1,985 (next: ART-1987) — unchanged
- **DB questions (ITE):** 1,629 — unchanged
- **DB questions (AAFP BRQ):** 1,221 — unchanged
- **PDFs (citation tiers):** 868 across 4 tiers (was 413 — +455 from EXA pipeline)
- **PDFs (ite_exams):** 16 — unchanged
- **EXA run:** 1,572 articles searched; 44.5% actionable
- **exa_pdf_downloader:** 397/558 downloaded (71.1% success); 161 failed (mostly paywalled)
- **pmc_oa_downloader:** 47/95 (49.5%): 14 direct OA + 33 tgz extracted; 62 not_oa
- **Remaining targets:** 872 landing_page + 62 not_oa PMC → DEFERRED-G (Unpaywall)

---

## Active Deferred Flags

| Flag | Description | Priority |
|------|-------------|----------|
| DEFERRED-G | `unpaywall_scanner.py` — 872 landing_page + 62 not_oa PMC; Unpaywall API (/v2/{doi}?email=); need DOI field check | **HIGH** |
| DEFERRED-A | 37 manual PDFs remaining: 34 subscription + 3 Cochrane → download → codon rename → VC_fail | HIGH |
| DEFERRED-B | `update_citation_trends.py` — run after backfill_new_article_metadata | MEDIUM |
| DEFERRED-C | AAFP vs ITE trend comparison | MEDIUM |
| DEFERRED-D | 229 citation gap articles (88 AFP batch-downloadable) | MEDIUM |
| DEFERRED-E | Interactive vector dashboard | LOW |
| DEFERRED-F | Intelligence 2.0 Layer 2 (`article_currency` via PubMed, 344 PMIDs; NCBI API key set) | MEDIUM |

---

## Next Steps (priority order)

1. **DEFERRED-G** — Build `unpaywall_scanner.py`; check articles table for DOI field; target 872 landing_page + 62 not_oa PMC
2. **DEFERRED-A** — 37 manual PDFs (subscription + Cochrane) → codon rename → VC_fail
3. **`backfill_new_article_metadata.py --art-id-min 1938`** — run once PDF batch assembled
4. **DEFERRED-B** — `update_citation_trends.py` after backfill
5. **DEFERRED-F** — Intelligence 2.0 Layer 2: `article_currency` via PubMed
