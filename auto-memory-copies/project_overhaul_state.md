
---
name: project_overhaul_state
description: BATON 038, Option B complete — board_prep_intel is flat project root, code review fixes done, DEFERRED-A priority
type: project
---

**Project:** ABFM ITE Intelligence System (Family Medicine board exam knowledge base)
**Root (Windows):** `C:\Users\mpsch\Desktop\board_prep_intel\`
**Active BATON:** `BATON_active_039_20260404_schema_docs_cleanup.md`
**Git:** `main`, latest committed → GIT-COMMITTED (code review: 14 defects fixed — 4 critical hop count/path bugs + 10 others)

---

## Current Phase: DEFERRED-A Manual PDF Assembly + Post-Sweep Cleanup

**BATON 037 (2026-04-04):**
- **M1 warehouse restructure completed** — 3-domain layout: `citation_files/`, `practice_questions/`, `ite_exams/`
- **All M1 maintain scripts path-updated** — 11 scripts updated to `citation_files/ITE/` + tier folder key fix (`local_lite`/`right_click`, no numeric prefixes)
- **Pre-existing NameError fixed** — `aafp_vc_batch_download.py`: removed undefined `LIBRARY_BASE` reference
- **`build_ite_qa_deliverables.py` created** — NEW M3 script generating 1 DOCX + 1 XLSX per ITE year (16 files, 2018–2025)
- **Answer choice formatting fixed** — Both `build_ite_qa_deliverables.py` and `build_aafp_qa_deliverables.py`: correct choice no longer highlighted in MC list; only the `✓ Answer:` banner reveals it
- **ITE XLSX simplified** — Body System + Blueprint columns removed (13 columns total)
- **All 42 deliverables regenerated** — 16 ITE + 26 AAFP (word_docs/ + excel/)
- **ite_exams/ archive confirmed** — 16 PDFs, all 8 years, consistent naming: `YYYY_MC.pdf` / `YYYY_critique.pdf`

**Windows cleanup pending:**
- Delete 5 originals: `build/extract_ite_2018_2019.py`, `build/integrate_2018_2019.py`, `build/backfill_keywords_2018_2019.py`, `maintain/rename_to_codon.py`, `maintain/build_match_staging.py`

---

## Module State

| Module | Location | Scripts | Status |
|--------|----------|---------|--------|
| M1 Warehouse | `01_module.1_warehouse/` | 6 build + 18 maintain + aafp_brq_scraper.py at scripts/ root | Cleanup complete; deprecated originals deleted ✓ |
| M2 Processor | `02_module.2_processor/scripts/` | 75 Python + 6 JS + 1 config JSON; +core(4py) +engines(7py) +utils(6py) packages; source/ outputs/ prompts/ subdirs | Stable |
| M3 Analyst | `03_module.3_analyst/scripts/` | 13 Python + 2 JS + 2 JSON config | Stable |
| DB | `00_database/db/ite_intelligence.db` | Source of truth | 1,985 articles, 1,629 ITE Q, 1,221 AAFP Q |
| Apify | `skills_abilities/apify-actors/citation_crawler/` | 1 actor (PlaywrightCrawler) | DEPLOYED ✅ build 0.3.1 (`mpsch1~citation-crawler`, ID `rh50nQRP7BupbUF64`) |

---

## M1 Warehouse Domain Layout (confirmed 2026-04-04)

```
01_module.1_warehouse/
├── citation_files/
│   ├── ITE/
│   │   ├── VC_pass/        ← awaiting enrichment (passed VC gate)
│   │   ├── VC_fail/        ← awaiting enrichment (failed VC gate)
│   │   ├── local_lite/     ← VC_fail + fully enriched
│   │   └── right_click/    ← VC_pass + fully enriched
│   └── AAFP/               ← AAFP citation PDFs
├── practice_questions/
│   ├── word_docs/          ← 8 ITE DOCX + 13 AAFP DOCX (gitignored)
│   └── excel/              ← 8 ITE XLSX + 13 AAFP XLSX (gitignored)
├── ite_exams/              ← 16 raw PDFs: YYYY_MC.pdf + YYYY_critique.pdf (2018–2025)
├── scripts/
│   ├── aafp_brq_scraper.py ← scraper at scripts/ root (moved from aafp_brq/scraper/)
│   ├── build/              ← 9 scripts (3 deprecated)
│   └── maintain/           ← 17 scripts (2 deprecated)
└── README.json
```

---

## Key Numbers (as of BATON 037, 2026-04-04 — DB unchanged)

- **DB articles:** 1,985 (next: ART-1987)
- **DB questions (ITE):** 1,629 (2018–2025); blueprint 100%; subcategory + topic_label DROPPED
- **DB questions (AAFP BRQ):** 1,221; blueprint 100%; flattened; aafp_explanations table DROPPED
- **article_icd10:** 4,137 rows
- **question_icd10:** 5,284 rows (92.8% ITE coverage)
- **aafp_question_icd10:** 4,753 rows
- **icd10_vec:** 2,219 rows (OpenAI text-embedding-3-small 1536d)
- **article_icd10_vec:** 1,674 rows (rebuilt 2026-04-01)
- **question_icd10_vec:** 2,733 rows (rebuilt 2026-04-01)
- **question_vec:** 1,629 rows — 100% coverage ✅
- **aafp_question_vec:** 1,221 rows — 100% coverage ✅
- **clinical_pathways:** 4,020 rows (rebuilt 2026-03-31)
- **pubmed_pmid_cache:** 344 rows (Layer 2 seed)
- **PDFs (citation tiers):** ~414 across 4 tiers (VC_fail ~156; 37 AAFP articles manual pending)
- **PDFs (ite_exams):** 16 (2018–2025 × MC + critique)

---

## Active Deferred Flags

| Flag | Description | Priority |
|------|-------------|----------|
| DEFERRED-A | 37 manual PDFs remaining: 34 subscription + 3 Cochrane → download → codon rename → citation_files/ITE/VC_fail | **HIGH** |
| DEFERRED-B | `update_citation_trends.py` — run after backfill_new_article_metadata | MEDIUM |
| DEFERRED-C | AAFP vs ITE trend comparison | MEDIUM |
| DEFERRED-D | 229 citation gap articles (88 AFP batch-downloadable) | MEDIUM |
| DEFERRED-E | Interactive vector dashboard | LOW |
| DEFERRED-F | Intelligence 2.0 Layer 2 (`article_currency` via PubMed, 344 PMIDs cached) | MEDIUM |

---

## Next Steps (priority order)

1. **Windows cleanup** — Delete 5 deprecated script originals from M1/build/ and M1/maintain/
2. **`extract_ite_year.py` filename update** — `{YEAR}_ITE_Questions.pdf` → `{YEAR}_MC.pdf`; `{YEAR}_ITE_Critique.pdf` → `{YEAR}_critique.pdf`
3. **DEFERRED-A manual PDFs** — 37 remaining; institutional/Cochrane access → codon rename → VC_fail
4. **`backfill_new_article_metadata.py --art-id-min 1938`** — run once PDFs assembled
5. **DEFERRED-B** — `update_citation_trends.py` after backfill
6. **Option B** — flatten `00_#PROJECT_OVERHAUL/` → `claude_knowledge/` root
7. **DEFERRED-F** — Intelligence 2.0 Layer 2: `article_currency` via PubMed
