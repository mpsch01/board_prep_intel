---
name: project_overhaul_state
description: Current PROJECT_OVERHAUL state: BATON 035, repo sweep complete, 5 legacy scripts deprecated, repo_pre_severance.md created, DEFERRED-A still priority
type: project
---

**Project:** ABFM ITE Intelligence System (Family Medicine board exam knowledge base)
**Root (Windows):** `C:\Users\mpsch\Desktop\claude_knowledge\00_#PROJECT_OVERHAUL\`
**Active BATON:** `BATON_active_035_20260404_repo_sweep_mapping.md`
**Git:** `main`, latest committed `e26a748` → GIT-PENDING (playwright upgrade + download scripts + sweep + mapping)

---

## Current Phase: DEFERRED-A Manual PDF Assembly + Post-Sweep Cleanup

**BATON 035 (2026-04-04):**
- **Repo sweep (Sweep 1) completed** — `archive_canonical/` → `_archive_/`, `apify-actors/` → `skills_abilities/`, 11 scripts fixed for the rename, docx_guideline_library moved.
- **11 scripts fixed** — `archive_canonical` → `_archive_` path references, broken by rename, all fixed with replace_all edits.
- **Full repo mapping created** — `repo_pre_severance.md` at project root: 123 scripts, hop counts, read/write paths, Option B impact assessment.
- **5 legacy scripts deprecated** — deprecation headers applied; gathered into `_legacy/` folder; moved to offsite archive by user. Originals remain in build/ and maintain/ pending Windows delete.
- **`build_faculty_pptx.js` verified clean** — no path deps, no DB connection; standalone PPTX builder.
- **Option B confirmed path-safe** — flatten to claude_knowledge/ root changes no hop counts.

**Windows cleanup pending:**
- Delete 5 originals: `build/extract_ite_2018_2019.py`, `build/integrate_2018_2019.py`, `build/backfill_keywords_2018_2019.py`, `maintain/rename_to_codon.py`, `maintain/build_match_staging.py`
- Retire BATON 034 → `baton_archive/` (Windows move)

---

## Module State

| Module | Location | Scripts | Status |
|--------|----------|---------|--------|
| M1 Warehouse | `01_module.1_warehouse/` | 9 build (3 deprecated) + 17 maintain (2 deprecated) + aafp_brq/scraper | Stable; deprecated originals pending Windows delete |
| M2 Processor | `02_module.2_processor/scripts/` | ~60 Python + 6 JS + 1 config JSON + 4 Windows | Stable |
| M3 Analyst | `03_module.3_analyst/scripts/` | 11 Python + 2 JS + 2 JSON config | Stable; build_faculty_pptx.js verified clean |
| DB | `00_database/db/ite_intelligence.db` | Source of truth | 1,985 articles, 1,629 ITE Q, 1,221 AAFP Q |
| Apify | `skills_abilities/apify-actors/citation_crawler/` | 1 actor (PlaywrightCrawler) | DEPLOYED ✅ build 0.3.1 (`mpsch1~citation-crawler`, ID `rh50nQRP7BupbUF64`) |

---

## Key Numbers (as of BATON 035, 2026-04-04 — unchanged from BATON 034)

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
- **PDFs:** ~414 across 4 tiers (VC_fail ~156; 37 AAFP articles manual pending)

---

## Active Deferred Flags

| Flag | Description | Priority |
|------|-------------|----------|
| DEFERRED-A | 37 manual PDFs remaining: 34 subscription + 3 Cochrane → download → codon rename → VC_fail | **HIGH** |
| DEFERRED-B | `update_citation_trends.py` — run after backfill_new_article_metadata | MEDIUM |
| DEFERRED-C | AAFP vs ITE trend comparison | MEDIUM |
| DEFERRED-D | 229 citation gap articles (88 AFP batch-downloadable) | MEDIUM |
| DEFERRED-E | Interactive vector dashboard | LOW |
| DEFERRED-F | Intelligence 2.0 Layer 2 (`article_currency` via PubMed, 344 PMIDs cached) | MEDIUM |

---

## Next Steps (priority order)

1. **Windows cleanup** — Delete 5 deprecated script originals from M1/build/ and M1/maintain/; retire BATON 034
2. **DEFERRED-A manual PDFs** — 37 remaining; institutional/Cochrane access → codon rename → VC_fail
3. **`backfill_new_article_metadata.py --art-id-min 1938`** — run once PDFs assembled
4. **DEFERRED-B** — `update_citation_trends.py` after backfill
5. **Option B** — flatten `00_#PROJECT_OVERHAUL/` → `claude_knowledge/` root
6. **DEFERRED-F** — Intelligence 2.0 Layer 2: `article_currency` via PubMed
