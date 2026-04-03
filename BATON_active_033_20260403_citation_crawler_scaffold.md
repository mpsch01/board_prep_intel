# BATON 033 — Citation Crawler Actor Scaffold + Session Housekeeping
**Date:** 2026-04-03
**Session:** Verified closed flags, fixed compute_embeddings schema drift, built citation_crawler Apify actor from scratch
**Status:** GIT-PENDING CLOSED ✅ | Q-VEC-GAP CLOSED ✅ | citation_crawler scaffold committed
**Replaces:** BATON_active_032_20260402_question_dist_fix_faculty_pptx.md

---

## What Was Done This Session

### 1. GIT-PENDING — VERIFIED CLOSED ✅
Confirmed all 8 scripts from BATON 029–031 are committed. Per-script check via `git log --oneline -1 -- <file>`:
- `ite_analyze_v2.py`, `ite_analyzer_v2.py`, `ite_report_builder_v2.js` → `c2dc133`
- `export_aafp_ite_relationships.py`, `word_doc_defaults.py`, `build_aafp_qa.py`, `build_aafp_qa_file1.py` → `dbbc974`
- `build_faculty_pptx.js` → `1a6b048`

Flag was stale — already closed before this session. BATON 032 git hash listed as `1a6b048`; actual HEAD was `9389974` (additional commits had landed post-BATON). README.json renamed to README.md in `ee850fa`.

---

### 2. Q-VEC-GAP — VERIFIED CLOSED ✅
Dry-run of `compute_embeddings.py --new-only --dry-run` returned 0 gaps across all three corpora:
- `article_vec`: 0 missing
- `question_vec`: 0 missing
- `aafp_question_vec`: 0 missing

Flag was stale — embeddings were completed in a prior session (BATON 030 rebuild pass).

---

### 3. compute_embeddings.py — Schema Drift Fixed
**File:** `01_module.1_warehouse/scripts/build/compute_embeddings.py`
**Root cause:** Schema changes from BATON 024 were not reflected in the script.

Two fixes applied:
1. `embed_questions()` SELECT: removed `q.subcategory` column (dropped BATON 024)
   - Also cleaned `build_question_text()`: removed subcategory from System line
2. `embed_aafp_questions()`: removed JOIN on `aafp_explanations` table (merged into `aafp_questions` BATON 024)
   - Changed `e.correct_text, e.explanation` → `q.correct_text, q.explanation` (direct columns)

**Committed in:** `e26a748`

---

### 4. citation_crawler Apify Actor — BUILT FROM SCRATCH
**Goal:** Custom Apify Actor callable via Apify MCP. Replaces the Copilot stub that was in `citation_crawler.JSON`.

**Architecture decisions:**
- Apify SDK v3 + Crawlee (not legacy v1/v2 `Apify.main()`)
- ESM module (`"type": "module"`)
- Two operating modes:
  - **Deterministic** (`articleUrls`): direct article URL list, no crawling — for DEFERRED-A (49 known articles)
  - **Crawl** (`startUrls`): publisher landing page → article link discovery → extract
- No date gating by default (`dateFrom: null`) — clinical guidelines are evergreen
- Metadata extraction priority: Schema.org JSON-LD → OpenGraph/Dublin Core → citation meta tags → DOM selectors
- PDF discovery: `.pdf` extension, `/pdf/` paths, `format=pdf`, `media=pdf` publisher patterns
- DOI extraction: 4-layer fallback — JSON-LD → citation meta → `doi.org` link → URL regex
- Output fields: `sourceUrl`, `loadedUrl`, `sourceDomain`, `loadedDomain`, `title`, `authors`, `journal`, `publishedAt`, `doi`, `abstract`, `wordCount`, `pdfUrls`, `retrievedAt`, `[html]`

**Files created:**
```
apify-actors/citation_crawler/
  .actor/actor.json       ← Apify actor metadata (actorSpecification v1)
  src/main.js             ← full actor (405 lines, SDK v3 + Crawlee)
  package.json            ← dependencies: apify ^3.2, crawlee ^3.9, chrono-node ^2.7
  INPUT_SCHEMA.json       ← Apify UI config (all inputs documented with examples)
```

**Files removed:**
- `apify-actors/citation_crawler/apify.json` — old Copilot stub (was a package.json in disguise)
- `apify-actors/citation_crawler/citation_crawler.JSON` — Copilot raw combined file (UNTRACKED — needs manual delete from Windows Explorer)

**Note:** `apift_smart_article_extractor` (the original forked source) remains at repo root — it was used as reference but is now superseded by `src/main.js`. Can be deleted once actor is deployed and validated.

**Committed in:** `e26a748`

---

### 5. npm audit fix
`npm install` completed in `apify-actors/citation_crawler/`. `npm audit` showed 13 moderate vulnerabilities in `file-type` via `crawlee` dependency chain. Fixed via `npm audit fix`. `node_modules/` is gitignored.

---

## DB State (unchanged this session)

| Table | Rows | Notes |
|-------|------|-------|
| articles | 1,985 | ART-0001 → ART-1986; next = ART-1987 |
| questions (ITE) | 1,629 | blueprint 100% |
| questions (AAFP) | 1,221 | blueprint 100% |
| qid_art_xref | 2,470 | |
| aafp_qid_art_xref | 864 | |
| article_icd10 | 4,137 | |
| question_icd10 | 5,284 | |
| aafp_question_icd10 | 4,753 | |
| clinical_pathways | 4,020 | |
| icd10_vec | 2,219 | |
| article_icd10_vec | 1,674 | rebuilt BATON 030 |
| question_icd10_vec | 2,733 | rebuilt BATON 030 |
| pubmed_pmid_cache | 344 | Layer 2 seed |
| PDFs | 404 | 49 AAFP articles awaiting download |
| Next ART-ID | ART-1987 | |
| Git | main, `e26a748` | clean — all flags resolved |

---

## Deferred Flags

| Flag | Description | Priority |
|------|-------------|----------|
| DEFERRED-A | PDF download: 49 AAFP articles ART-1938–1986 — NOW via citation_crawler actor (deploy first: `apify push`) | **High** |
| DEFERRED-B | `update_citation_trends.py` — run after DEFERRED-A | Medium |
| DEFERRED-C | AAFP vs ITE trend comparison | Medium |
| DEFERRED-D | 229 citation gap articles (88 AFP batch-downloadable) | Medium |
| DEFERRED-E | Interactive vector dashboard | Low |
| DEFERRED-F | Intelligence 2.0 Layer 2 — `article_currency` via PubMed (344 PMIDs cached) | Medium |

**Closed this session:** GIT-PENDING ✅, Q-VEC-GAP ✅
**Loose file (manual cleanup):** `citation_crawler.JSON` in `apify-actors/citation_crawler/` — untracked, delete from Windows Explorer

---

## Next Steps (priority order)

1. **Deploy citation_crawler** — `apify push` from `apify-actors/citation_crawler/` → actor ID `mpsch01~citation-crawler`
2. **DEFERRED-A** — use citation_crawler (deterministic mode, `articleUrls`) to source PDF links for ART-1938–1986; download → codon rename → VC gate
3. **DEFERRED-B** — `update_citation_trends.py` after DEFERRED-A
4. **DEFERRED-F** — Intelligence 2.0 Layer 2: `article_currency` via PubMed (344 PMIDs in `pubmed_pmid_cache`)
5. **DEFERRED-D** — 229 citation gap articles (88 AFP batch-downloadable)

---

## Files Changed This Session

| File | Action |
|------|--------|
| `01_module.1_warehouse/scripts/build/compute_embeddings.py` | MODIFIED — schema drift fix (subcategory + aafp_explanations) |
| `apify-actors/citation_crawler/.actor/actor.json` | NEW — Apify actor metadata |
| `apify-actors/citation_crawler/src/main.js` | NEW — full actor (SDK v3 + Crawlee) |
| `apify-actors/citation_crawler/package.json` | NEW — dependencies |
| `apify-actors/citation_crawler/INPUT_SCHEMA.json` | NEW — Apify UI input schema |
| `apify-actors/citation_crawler/apify.json` | DELETED — old stub |
| `baton_archive/BATON_active_032_*.md` | ARCHIVED (this session) |
| `BATON_active_033_*.md` | This file |
