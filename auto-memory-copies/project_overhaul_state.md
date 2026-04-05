
---
name: project_overhaul_state
description: BATON 040, EXA PDF pipeline complete — 868 PDFs on disk, 3 new M1 maintain scripts, DEFERRED-G (Unpaywall) next
type: project
---

**Project:** ABFM ITE Intelligence System (Family Medicine board exam knowledge base)
**Root (Windows):** `C:\Users\mpsch\Desktop\board_prep_intel\`
**Active BATON:** `BATON_active_043_20260405_pdf_recovery_skills.md`
**Git:** `main`, latest committed → PDF recovery complete; housekeeping scripts deployed

---

## Current Phase: PDF Recovery Complete — Housekeeping & Skills Deployed

**BATON 043 (2026-04-05):**
- **PDF library fully recovered** — HDD backup 3-step pipeline: 868 PDFs restored + dupe audit; **966 active PDFs** across 4 tiers (VC_fail 623, VC_pass 168, local_lite 117, right_click 58) + 14 quarantined in _dupe_archive/
- **_dupe_archive/ folder created** — 14 single-author duplicate PDFs (same title + author, different years/versions) isolated for audit trail
- **M1 maintain scripts grown to 23** — 2 new recovery scripts added: recover_unpaywall.py + pmc_oa_downloader.py (re-invoked in recovery context)
- **Session housekeeping skills deployed** — index-memory-writer.md agent template + exa-research-search skill v2 updated
- **No DB changes** — source data untouched throughout incident + recovery; DB counts verified live (1,985 articles, 1,629 ITE Q, 1,221 AAFP Q)

**Windows cleanup:** Complete ✓ (BATON 039)

---

## Module State

| Module | Location | Scripts | Status |
|--------|----------|---------|--------|
| M1 Warehouse | `01_module.1_warehouse/` | 6 build + 23 maintain + aafp_brq_scraper.py at scripts/ root | 23 scripts (2 recovery scripts added 2026-04-05) |
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
│   │   ├── VC_fail/        ← 623 PDFs (recovered from HDD backup)
│   │   ├── VC_pass/        ← 168 PDFs (VC gate passed — destined for right_click)
│   │   ├── local_lite/     ← 117 PDFs (VC_fail + fully enriched)
│   │   ├── right_click/    ← 58 PDFs (VC_pass + fully enriched)
│   │   └── _dupe_archive/  ← 14 PDFs (single-author duplicates, quarantined)
│   │   [Total: 966 active PDFs as of 2026-04-05]
│   └── AAFP/               ← AAFP citation PDFs
├── practice_questions/
│   ├── word_docs/          ← 8 ITE DOCX + 13 AAFP DOCX (gitignored)
│   └── excel/              ← 8 ITE XLSX + 13 AAFP XLSX (gitignored)
├── ite_exams/              ← 16 raw PDFs: YYYY_MC.pdf + YYYY_critique.pdf (2018–2025)
└── scripts/
    ├── aafp_brq_scraper.py ← scraper at scripts/ root
    ├── build/              ← 6 scripts
    └── maintain/           ← 23 scripts (recover_unpaywall.py + pmc_oa_downloader.py added)
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

## Key Numbers (as of BATON 043, 2026-04-05)

- **DB articles:** 1,985 (next: ART-1987) — unchanged
- **DB questions (ITE):** 1,629 — unchanged
- **DB questions (AAFP BRQ):** 1,221 — unchanged
- **PDFs (citation tiers, active):** 966 across 4 tiers (was 868 pre-incident, 413 baseline — +553 via recovery)
- **PDFs (quarantined):** 14 in _dupe_archive/ (single-author duplicates)
- **PDFs (ite_exams):** 16 — unchanged
- **M1 maintain scripts:** 23 (was 21 — 2 recovery scripts added)
- **Session changes:** PDF recovery complete via HDD backup 3-step pipeline; _dupe_archive/ created; housekeeping skills deployed

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
