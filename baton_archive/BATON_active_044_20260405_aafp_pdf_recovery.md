# BATON 044 — AAFP PDF Recovery + Deferred Flag Cleanup

**Date:** 2026-04-05
**Session:** AAFP citation_files/ recovery; deferred flag resolution (H closed, A archived, J closed)
**Status:** ACTIVE
**Replaces:** BATON_active_043_20260405_pdf_recovery_skills.md
**Git Commit:** 33f5476

---

## What Happened This Session

### PART 1: Deferred Flag Resolution
- **DEFERRED-H (CLOSED):** Legacy non-codon PDFs confirmed as true duplicates — no new downloads needed.
- **DEFERRED-A (ARCHIVED):** 37 manual ITE PDFs represent permanent ceiling. These are subscription-only (34) + Cochrane (3). No further action possible without institutional access. Flag archived permanently.
- **DEFERRED-J (CLOSED):** exa-research-search skill Phase 2 was truncated in prior BATON. User uploaded complete version (research-doc-finder.txt). Written to Windows path via Desktop Commander in 14 chunks. Phase 2 now contains: URL classification cascade (direct_pdf / pmc_fulltext / open_access / landing_page / not_found), PMC transform, AAFP .html→.pdf resolution, two download paths (Path A: M1 pipeline for DB articles, Path B: new paper download agent), full Python download script with %PDF validation, 10 safety rules.

### PART 2: AAFP PDF Recovery
citation_files/AAFP/ was empty after fix_ghost.py incident. 64 AAFP-only articles required recovery.

**Recovery Pipeline:**
1. Built `aafp_pdf_downloader.py` (M1 maintain) — 16 articles with confirmed URLs: 9 PMC (primary/EuropePMC fallback), 4 direct PDF, 2 OA, 1 university repo. PMC direct requests blocked (HTTP 403).
2. Built `aafp_pmc_oa_downloader.py` (M1 maintain) — 9 PMC articles via NCBI OA API (oa.fcgi). Result: 4/9 downloaded (Dennis_2008 direct PDF, Metlay_Waterer_2019/Islam_2016/Khan_2010 via tgz extract), 5/9 not_oa (paywalled at PMC level).
3. User downloaded 2 NEJM articles via hospital institutional access (Young_Fadok_2018 diverticulitis, Stewart_2011 depression during pregnancy) + 2 Cochrane articles (Keay_2012 preoperative testing, Albalawi_2011 intranasal ipratropium). Renamed and moved to citation_files/AAFP/ with codon filenames.
4. ART-1946 (Binks_2006) verified: university repo file LeePsychological.pdf confirmed correct — "Psychological therapies for borderline personality disorder" Cochrane 2006 — Lee is co-author, Binks is lead. Content matches.

**Final AAFP count:** 15 PDFs in citation_files/AAFP/

**Remaining paywalled AAFP articles (3):**
- ART-1959 Binic_2011 (PMC4996308) — not_oa
- ART-1972 Byington_2012 (PMC4074609) — not_oa
- ART-1967 Verbalis_2007 (PMC2643091) — not_oa

---

## DEFERRED FLAGS (Active)

| Flag | Status | Description |
|------|--------|-------------|
| DEFERRED-A | ARCHIVED | 37 manual ITE PDFs (subscription-only + Cochrane) — permanent ceiling documented |
| DEFERRED-F | PENDING | Intelligence 2.0 Layer 2: article_currency via PubMed (344 PMIDs in pubmed_pmid_cache; NCBI API key set) |
| DEFERRED-AAFP-PAYWALL | NEW | 3 AAFP articles paywalled — requires institutional/interlibrary access — ART-1959, ART-1972, ART-1967 |
| DEFERRED-I | PENDING | unpaywall_scanner --from-csv extension (low priority) |

---

## Library State

### AAFP Citation Files (NEW)
```
citation_files/AAFP/: 15 PDFs (recovered this session from 0)
- Codon-renamed, ready for enrichment pipeline
```

### ITE Citation Files (Unchanged)
```
VC_fail:     623 PDFs
VC_pass:     168 PDFs
local_lite:  117 PDFs
right_click:  58 PDFs
———————————————————
TOTAL:       966 PDFs
_dupe_archive: 14 dupes
```

### ITE Exams (Unchanged)
```
16 files: 8 years (2018–2025) × MC + critique
```

### Practice Questions (Unchanged)
```
42 files: 8 ITE DOCX + 8 ITE XLSX + 13 AAFP DOCX + 13 AAFP XLSX (gitignored, regenerable)
```

---

## Database State (No writes this session)

| Table | Count | Notes |
|-------|-------|-------|
| articles | 1,985 | +49 AAFP acquisition (ART-1938–ART-1986) |
| questions (ITE) | 1,629 | 2018–2025, blueprint 100% filled |
| aafp_questions | 1,221 | blueprint 100%, concept_tags 100% |
| qid_art_xref | 2,470 | all 8 ITE years |
| aafp_qid_art_xref | 864 | 643 unique questions linked (52.7%) |
| article_icd10 | 4,020 | rebuilt 2026-04-05 |
| question_icd10 | 5,284 | 1,512/1,629 ITE questions (92.8%) |
| aafp_question_icd10 | 4,753 | relevance normalized, related cap applied |
| clinical_pathways | 4,020 | rebuilt 2026-03-31, both banks |
| pubmed_pmid_cache | 344 | Layer 2 seed (citation_id → PMID) |
| icd10_vec | 2,219 | OpenAI text-embedding-3-small (1536d) |
| article_icd10_vec | 1,757 | rebuilt 2026-04-05 |
| question_icd10_vec | 2,747 | rebuilt 2026-04-05 |

---

## Script State (No deletions this session)

| Module | Category | Count | Notes |
|--------|----------|-------|-------|
| M1 | build | 6 py | unchanged |
| M1 | maintain | 25 py | +aafp_pdf_downloader.py, +aafp_pmc_oa_downloader.py |
| M2 | — | 75 py + 6 js | unchanged |
| M3 | — | 13 py + 2 js | unchanged |
| — | root | 1 py | aafp_brq_scraper.py (unchanged) |

**New scripts this session:**
- `01_module.1_warehouse/maintain/aafp_pdf_downloader.py` — URL validation + direct/PMC/OA routing
- `01_module.1_warehouse/maintain/aafp_pmc_oa_downloader.py` — NCBI OA API downloader (tgz extract + PDF extraction)

---

## Git State

**Branch:** main
**Latest Commit:** 33f5476
**Strategy:** Code + docs on GitHub. Binaries excluded (*.db, *.pdf, extracted_json/, resident_data/) → local disk / Google Drive
**Next ART-ID:** ART-1987

---

## Next Steps (Priority Order)

1. **Clean empty RECO folders** (USER TASK) — Windows Explorer/PowerShell housekeeping post-PDF recovery
2. **DEFERRED-F:** Intelligence 2.0 Layer 2 (article_currency table) — PubMed currency via 344 PMIDs
3. **DEFERRED-AAFP-PAYWALL:** 3 articles via institutional/interlibrary access (ART-1959, ART-1972, ART-1967)
4. **Resume roadmap:** VC outline enrichment (Module F pipeline), practice question generation
5. **Intelligence 2.0:** Layers 3–4 continuation (pathways refinement, trend analysis)

---

## Conventions / Decisions This Session

- **citation_files/AAFP/ is now live tier:** 15 PDFs recovered; was previously empty after fix_ghost.py incident
- **aafp_pmc_oa_downloader.py pattern:** Uses NCBI OA API (oa.fcgi) instead of direct PMC PDF URLs — correct approach; PMC direct requests return HTTP 403
- **DEFERRED-A archived:** Permanent ceiling documented; 37 PDFs (subscription + Cochrane) — do not re-open without new institutional access
- **tgz extraction in AAFP recovery:** PMC OA API returns .tar.gz packages; built extractor logic into aafp_pmc_oa_downloader.py
- **Codon naming for AAFP PDFs:** All 15 AAFP PDFs now follow codon scheme (Author_Year#@#ART-XXXX@#@.pdf) for consistency with ITE pipeline