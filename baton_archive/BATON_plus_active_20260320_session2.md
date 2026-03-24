# BATON PLUS — PDF Library Full Audit: 02_codon Verification + Unexamined Folder Cleared

**Date:** March 20, 2026 (Session 2)
**Previous BATON:** `BATON_active_20260320.md` (has_extraction Audit + DB Expansion)
**Status:** MAJOR MILESTONE — All PDF folders audited and processed. Unexamined folder emptied. DB expanded from 1,424 → 1,547 articles across two sessions today. Library cleaned, codon-named, and categorized. 13 articles still need PDFs sourced.

---

## What Was Done This Session

### 1. needs_review Folder Processed (20 → 0 PDFs)
Extracted first ~1000 chars from all 20 PDFs using PyMuPDF. Ran identity-aware DB matching (author surname + distinctive topic keywords) instead of generic fuzzy match. Cross-referenced against VC gate (`session_hy_inserts_v7.json`).

**Results:**
- 1 duplicate deleted (`rheum_lyme-disease.pdf` — duplicate of IDSA_lyme already in library)
- 1 reference sheet left as-is (`BackPainPCP_Treatment_Algorithm.pdf` — no DB record, moved to 00_non-codon)
- 18 new DB records created (ART-1426 through ART-1443) — all confirmed non-VC-cited
- All 18 renamed to codon format and moved to `00_non-codon/`

### 2. 02_codon Folder Audited (73 PDFs)
Permission-locked files unlocked via Windows-side `icacls /reset /T`.

Extracted metadata + first 1000 chars from all 73 PDFs, then verified each PDF's actual content against its embedded ART-ID's DB record.

**Findings:**
- 62 of 73 PDFs matched their claimed ART-ID (content verified correct, all VC-cited)
- 1 duplicate ART-ID discovered: ART-0121 used by two different files (Banerjee celiac + Williams celiac)
- 10 content mismatches: codon filename points to one article but PDF contains a different AFP article from the same journal issue (classic batch-rename error from the original codon migration)

### 3. 02_codon Fixes Executed
**Immediate fixes (5):**
- Renamed `Williams_2022#@#ART-0121@#@.pdf` → `Williams_2022#@#ART-1344@#@.pdf` (DB updated)
- Deleted `Hauk_2017#@#ART-0569@#@.pdf` (contained Kodner glucose article — duplicate of existing copy)
- Deleted `Frazier_2021#@#ART-1132@#@.pdf` (contained onychomycosis article, mislabeled)
- Deleted `Kravets_2016#@#ART-0713@#@.pdf` (contained Letters to the Editor junk, not a real article)
- Swapped `Wigle_2019#@#ART-1332@#@.pdf` with correct anticoagulation PDF from unexamined (verified content match)

**6 mismatched files identified, re-homed (ART-1444 through ART-1449):**
These PDFs contained legitimate AFP articles — just not the ones their codons claimed. Each was identified, given a new ART-ID, and renamed with the correct codon.

| Old Codon (wrong) | Actually contains | New ART-ID | New Codon |
|---|---|---|---|
| Herman_2022#@#ART-0112@#@ | Long COVID/PASC (Herman, Shih, Cheng 2022) | ART-1444 | Herman_Shih_2022#@#ART-1444@#@ |
| Croteau_2014#@#ART-0272@#@ | Acute Pancreatitis (Quinlan 2014) | ART-1445 | Quinlan_2014#@#ART-1445@#@ |
| Leeman_2016#@#ART-0755@#@ | Endometrial Cancer (Braun 2016) | ART-1446 | Braun_Overbeek-Wager_2016#@#ART-1446@#@ |
| Smith_2019#@#ART-1175@#@ | Chronic Neck Pain Nonpharm (Barreto, Svec 2019) | ART-1447 | Barreto_Svec_2019#@#ART-1447@#@ |
| Westerfield_2018#@#ART-1326@#@ | LARC: Difficult Insertions (Prine, Shah 2018) | ART-1448 | Prine_Shah_2018#@#ART-1448@#@ |
| Harris_2023#@#ART-1345@#@ | Osteoporosis Q&A (Harris, Zagar 2023) | ART-1449 | Harris_Zagar_2023#@#ART-1449@#@ |

### 4. Unexamined Folder Fully Processed (101 → 0 PDFs)
Permission-locked files unlocked via Windows-side `icacls /reset /T` (path: `C:\Users\mpsch\Desktop\claude_knowledge\clinical_guidelines\01_pdf_guideline_library\00_non-codon\unexamined`).

Extracted metadata from all 101 PDFs. DB-matched by author surname + year.

**Results:**
- 2 duplicates deleted:
  - `Wouk_2019.pdf` — matches ART-1366 (already has codon PDF)
  - `Abraham S, Rivero HG...2014.pdf` — full-citation filename, content identical to `Patel_2024.pdf` (gallstones 2024 update)
- 99 new DB records created (ART-1450 through ART-1548)
- All 99 renamed to codon format and moved to `00_non-codon/`
- `unexamined/` is now **empty**

### 5. ART-ID Architecture Discussion
User questioned whether articles linked to multiple ART-IDs was a schema problem. Investigation confirmed the `qid_art_xref` junction table is correctly designed as many-to-many (composite PK: qid, article_id). The issue is data quality: duplicate/truncated titles in the articles table causing confusion, not a structural flaw. QIDs are the stable anchor; ART-IDs are the fragile side due to multiple ingest paths.

### 6. Future Cryptographic ART-ID Vision (Discussed, Not Implemented)
User's long-term vision: ART-IDs derived from a cryptographic hash generated at pipeline completion. The ID becomes proof of provenance — the only way to receive an ART-ID is to pass through the full download → extraction → enrichment → synthesis pipeline. Also: richer human-readable filename prefixes beyond just Author_Year (topic keywords, specialty, etc.) for easier browsing. **Deferred until library is stable.**

### 7. OneDrive Discovery
The `clinical_guidelines` folder was discovered to be syncing through OneDrive (`.tmp.drivedownload` and `.tmp.driveupload` artifacts present). This explains the recurring permission-lock issues — OneDrive's file-on-demand system blocks local access during sync. The rest of `claude_knowledge` lives locally at `C:\Users\mpsch\Desktop\claude_knowledge\`. The clinical_guidelines folder being in OneDrive is an unintended state. **User is aware but no action taken yet.**

---

## Cumulative Session Stats (Both Sessions Today)

```
                        Start of Day    End of Session 2    Delta
Articles in DB:         1,397           1,547               +150 (net: +151 new, -1 merged ART-0404)
PDFs in library:        411             404                 -7 (net: deletions > 0, reorganized)
Unaudited PDFs:         122             0                   -122 (all audited)
Folders emptied:        0               3                   has_extraction, needs_review, unexamined
```

### New DB Records Created This Session (123 total)
| Batch | ART-ID Range | Count | Source |
|---|---|---|---|
| needs_review | ART-1426 – ART-1443 | 18 | Parked files from earlier audit |
| 02_codon fixes | ART-1444 – ART-1449 | 6 | Mislabeled PDFs re-identified |
| unexamined | ART-1450 – ART-1548 | 99 | Fresh AFP articles (2017–2025) |

### Files Deleted This Session (7 total)
1. `rheum_lyme-disease.pdf` — duplicate of IDSA_lyme
2. `Hauk_2017#@#ART-0569@#@.pdf` — Kodner glucose dupe
3. `Frazier_2021#@#ART-1132@#@.pdf` — onychomycosis mislabel
4. `Kravets_2016#@#ART-0713@#@.pdf` — Letters to Editor junk
5. `Wouk_2019.pdf` — duplicate of ART-1366
6. `Abraham S, Rivero HG...2014.pdf` — duplicate of Patel_2024
7. `Williams_2022#@#ART-0121@#@.pdf` → renamed (not deleted, re-IDed as ART-1344)

---

## Current Folder State (Live)

```
clinical_guidelines/01_pdf_guideline_library/
├── 00_non-codon/                    146 PDFs (all codon-named, processing backlog)
│   ├── has_extraction/              EMPTY
│   │   └── needs_review/            EMPTY
│   └── unexamined/                  EMPTY
│
├── 01_local_lite/                   117 PDFs
│
├── 02_codon/                        70 PDFs (all verified correct content)
│
└── 03_right_click/                  71 PDFs

TOTAL: 404 PDFs
```

### Folder Definitions
- **00_non-codon/**: Processing backlog. All 146 are codon-named with DB records but have NOT been through the extraction/enrichment/synthesis pipeline. Composition: 28 from has_extraction audit + 18 from needs_review + 1 BackPainPCP reference + 99 from unexamined.
- **01_local_lite/**: Articles with DB records, codon-named, locally sourced. Some have pipeline outputs under old slugified filenames.
- **02_codon/**: VC-cited articles with verified correct content. All 70 confirmed content-matches-codon.
- **03_right_click/**: Articles sourced via right-click download. Codon-named, DB records present.

---

## Database State

```
ite_intelligence.db
├── articles:           1,547 rows
├── questions:          1,189 rows
├── qid_art_xref:       1,818 rows
├── article_icd10:      3,093 rows
├── clinical_pathways:   3,093 rows
└── ART-ID range:       ART-0001 through ART-1548 (ART-0404 deleted/merged)

Codon coverage:         1,547/1,547 (100% — every article has a codon_filename)
QID-linked articles:    1,342 (of 1,547)
Unlinked articles:      205 (DB records with no ITE question associations)
```

### DB Insert History (This Project)
| Session | ART-ID Range | Count | Description |
|---|---|---|---|
| Pre-project | ART-0001 – ART-1397 | 1,397 | Original DB |
| Mar 20 S1 | ART-1398 – ART-1425 | 28 | has_extraction audit |
| Mar 20 S2 | ART-1426 – ART-1443 | 18 | needs_review processing |
| Mar 20 S2 | ART-1444 – ART-1449 | 6 | 02_codon mismatch re-IDs |
| Mar 20 S2 | ART-1450 – ART-1548 | 99 | unexamined folder processing |
| **Deleted** | ART-0404 | -1 | Merged into ART-1254 |
| **Total** | | **1,547** | |

---

## Articles Needing PDFs Sourced (13 total)

These ART-IDs exist in the DB but have no PDF anywhere in the library. The original PDFs were either deleted (wrong content), never downloaded, or lost during codon migration.

| ART-ID | Author | Year | Topic | Why Missing |
|---|---|---|---|---|
| ART-0112 | Baird/Herman | 2022 | Pelvic pain (rapid evidence review) | PDF had Long COVID content |
| ART-0272 | Croteau | 2014 | Gallbladder disease | PDF had Quinlan pancreatitis content |
| ART-0457 | Frazier | 2021 | Onychomycosis | PDF deleted (was mislabeled ART-1132) |
| ART-0569 | Hauk | 2017 | ACP Type 2 DM guidelines | PDF deleted (Kodner glucose dupe) |
| ART-0713 | Kravets | 2016 | Hyperthyroidism | PDF deleted (Letters to Editor junk) |
| ART-0755 | Leeman | 2016 | Hypertensive disorders of pregnancy | PDF had endometrial cancer content |
| ART-1132 | Frazier | 2021 | (original record — check what this should be) | PDF deleted |
| ART-1175 | Smith | 2019 | Manipulative therapies (AHRQ) | PDF had Barreto neck pain content |
| ART-1326 | Westerfield | 2018 | Breastfeeding Q&A | PDF had Prine LARC content |
| ART-1345 | Harris | 2023 | (original record — check what this should be) | PDF had osteoporosis content |

**Note:** ART-0112, ART-0272, ART-0755, ART-1175, ART-1326, ART-1345 are all VC-cited articles (their QID links still exist in qid_art_xref). Sourcing these is high priority because the ITE exam references them.

---

## Open Flags

### CRITICAL
- **FLAG 31:** 87 current codon PDFs misclassified — ITE-linked but not VC-cited. Must be re-tiered as `local_lite`.
- **FLAG 32:** 266 VC-cited articles have no PDF. Highest-priority sourcing targets. (Plus the 13 above.)
- **FLAG 33:** ART-ID rename (`nnn_XXXX`) not yet implemented. All downstream systems still use `ART-XXXX`.

### HIGH
- **FLAG 34:** 27 VC citation strings have no DB match. Need manual resolution.
- **FLAG 35:** QID format mismatch — VC JSON uses `Q{YEAR}-{NUM}`, DB uses `QID-{YEAR}-{NUM:04d}`. Only 75/229 resolve.
- **FLAG 43 [NEW]:** 13 articles in DB have no PDF in library (see sourcing list above). 6+ are VC-cited.
- **FLAG 44 [NEW]:** `clinical_guidelines` folder is in OneDrive, causing permission locks. Should be moved to local path or OneDrive sync behavior should be managed. Current workaround: `icacls /reset /T` before each batch.
- **FLAG 45 [NEW]:** DB title quality issue — many older records have page numbers ("137-143") instead of real titles. Low priority but affects searchability.

### MEDIUM
- **FLAG 36:** ~86 new AFP articles (2022–2025) in library not yet in DB. ← **Partially resolved: 99 unexamined articles now in DB. Some may overlap with this count.**
- **FLAG 38:** ~~54 permission-locked files in `02_codon/`~~ **RESOLVED** — unlocked via icacls.
- **FLAG 39:** `has_extraction/` and `needs_review/` and `unexamined/` folders are all empty — can be cleaned up.
- **FLAG 40:** 14 of 28 ART-1398–1425 articles have orphaned pipeline outputs under old slugified filenames in `03_enriched_JSON/`.
- **FLAG 41:** ~~102 unexamined PDFs~~ **RESOLVED** — all processed, folder empty.
- **FLAG 42:** ~~20 needs_review PDFs~~ **RESOLVED** — all processed, folder empty.

### LOW / DEFERRED
- **FLAG 1:** ITE Enrichment Quality Dimension
- **FLAG 13 Layer 2:** PubMed Currency (not started)
- **FLAG 15:** User still needs to run `node build_merged_docx.js --merged-only`
- **FLAG 27:** Report Builder v2 requires `npm install docx` in working directory
- **FLAG 28:** v1 HTML report incompatible with v2 question format
- **FLAG 29:** Hardcoded `year = 2025` in subcategory_decomposition and plugin_concept_fingerprint
- **FLAG 30:** `scholl_204999_ITE_SCORE` PDFs are encrypted — need unencrypted versions
- **FLAG 37:** `who_infant_feeding.pdf` falsely matched to ART-1320

---

## Key Findings / Decisions Locked

### This Session
1. **Batch-rename errors are systematic.** The original codon migration grabbed neighboring AFP articles from the same journal issue. Same author/year, wrong paper. 10 of 73 files in 02_codon had this issue. Root cause: automated rename matched by author+year against the AFP table of contents, not by article content.

2. **Identity-aware matching > fuzzy matching.** Generic fuzzy match (title overlap, token scoring) produces dangerous false positives against the DB because many records have truncated/generic titles. Correct approach: extract actual content, identify the real article, then search DB with specific author + distinctive keywords.

3. **qid_art_xref schema is correct.** Many-to-many junction table with composite PK (qid, article_id). QIDs are the stable anchor. ART-IDs are fragile due to multiple ingest paths.

4. **Every article in the DB now has a codon_filename.** 1,547/1,547 = 100% coverage. This is a major data quality milestone.

5. **The unexamined folder contained 99 unique, clean AFP articles (2017–2025).** Zero duplicates with existing DB records (except Wouk_2019 and the Abraham/Patel gallstones). Minimal parsing issues. This batch was the cleanest of the three audits.

### Carried Forward
6. **Fuzzy matchers produce dangerous false positives.** Always verify through direct citation-string search.
7. **MATCH files were duplicates, not originals.** Correct action was delete, not rename.
8. **Pipeline outputs use slugified titles, not codon filenames.** No automatic linkage. Re-processing needed.

---

## Key File Locations

### Database
```
abfm_prep/02_ite_intelligence/db/ite_intelligence.db
  ├── articles          (1,547 rows)
  ├── questions         (1,189 rows)
  ├── qid_art_xref      (1,818 rows)
  ├── article_icd10     (3,093 rows)
  └── clinical_pathways  (3,093 rows)
```

### PDF Library
```
clinical_guidelines/01_pdf_guideline_library/
  ├── 00_non-codon/          146 PDFs (processing backlog)
  │   ├── has_extraction/    EMPTY
  │   │   └── needs_review/  EMPTY
  │   └── unexamined/        EMPTY
  ├── 01_local_lite/         117 PDFs
  ├── 02_codon/              70 PDFs (all verified)
  └── 03_right_click/        71 PDFs
```

### VC Integration Data
```
abfm_prep/04_aafp_integration/02_working/session_hy_inserts_v7.json
  └── 48 sessions, 352 unique citation strings (THE VC GATE)
```

### Pipeline Outputs
```
clinical_guidelines/02_docx_guideline_library/   1,518 files (DOCX summaries)
clinical_guidelines/03_enriched_JSON/              217 extracted JSONs
clinical_guidelines/03_enriched_JSON/raw_txt/      217 raw text files
```

### Session Artifacts (temporary — in VM working dir)
```
/sessions/loving-dreamy-brown/
  ├── unexamined_extracted.json      (metadata for 101 unexamined PDFs)
  ├── unexamined_authors.json        (parsed author/year/title for 100 PDFs)
  ├── unexamined_inserts.json        (mapping: orig_fn → art_id → codon_fn for 99 inserts)
  ├── codon_02_extracted.json        (metadata for 73 02_codon PDFs)
  ├── needs_review_extracted.json    (metadata for 20 needs_review PDFs)
  ├── needs_review_audit.json        (fuzzy match results)
  └── needs_review_new_records.json  (18 new article mappings)
```

### BATON Archive
```
house_keeping_hub/baton_archive/
  └── (24 archived BATONs from Mar 11–20)
```

### Windows Paths (for icacls and user reference)
```
claude_knowledge root:    C:\Users\mpsch\Desktop\claude_knowledge\
clinical_guidelines:      C:\Users\mpsch\Desktop\claude_knowledge\clinical_guidelines\
  (NOTE: This folder may be in OneDrive sync — see FLAG 44)
```

---

## Codon Filename Convention (Unchanged)
```
Author_Year#@#ART-XXXX@#@.pdf
  Start codon: #@#
  Stop codon:  @#@
  ART-ID:      embedded between start and stop codons
  Example:     Quinlan_2014#@#ART-1445@#@.pdf

  Multi-author: Author1_Author2_Year#@#ART-XXXX@#@.pdf
  Example:      Prine_Shah_2018#@#ART-1448@#@.pdf
```

---

## Pipeline Processing State & Backlog

### Immediate Backlog (146 PDFs in 00_non-codon/)
All codon-named with DB records. None have been through extraction/enrichment/synthesis. These need to flow through: `main.py` (extract) → `synthesize.js` → `ite_intelligence_enricher.py` → `build_summary.js`.

### Pipeline Scripts
```
abfm_prep/03_pipeline/
  ├── main.py                         PDF → JSON extraction
  ├── synthesize.js                   JSON → structured synthesis
  ├── ite_intelligence_enricher.py    DB lookup, Strategy 0 (codon parse)
  └── build_summary.js                JSON → DOCX summaries
```

### Pipeline Bottleneck
With 146 fresh articles + re-runs for ~117 local_lite, this is a large batch. User has API access (Claude API key in env vars). Consider providing batch processing commands for the user to run locally, especially for the extraction step which has the longest runtime.

---

## Next Session Candidates (Ordered by Impact)

1. **Clean up empty folders** — delete `has_extraction/`, `needs_review/`, `unexamined/` (trivial)
2. **Run pipeline on 146-article backlog** — extract/enrich/synthesize the 00_non-codon batch. User can run this locally with API key.
3. **Source 13 missing PDFs** — especially the VC-cited ones (ART-0112, 0272, 0755, 1175, 1326, 1345)
4. **Re-tier 87 misclassified PDFs** (FLAG 31) — move ITE-linked-but-not-VC-cited from 02_codon to local_lite
5. **Address 266 VC-cited articles with no PDF** (FLAG 32) — the big sourcing project
6. **Resolve 27 unmatched VC citation strings** (FLAG 34)
7. **Fix DB title quality** (FLAG 45) — replace page-number titles with real article titles
8. **Move clinical_guidelines out of OneDrive** (FLAG 44) — or configure OneDrive to not lock files

---

## Design Principles (Unchanged — Carried Forward)

1. Fix the data, not the code.
2. The VC outline is the primary gate.
3. The ART-ID must carry tier information (post-migration).
4. Simplest reliable path. Always.
5. No files moved or renamed until the full migration plan is written and tested on a copy.

---

## ITE Score Analysis Pipeline — Carry-Forward Status
*(Separate workstream — not affected by the guideline library reorganization)*

Production-ready as of BATON_20260318_session2. Pending items unchanged:
- FLAG 26: Question matching gap (3/4 weak areas below 5-question minimum)
- FLAG 29: Dynamic exam year in subcategory decomposition
- FLAG 30: Scholl encrypted PDFs
- Plugin P2 (Explanation Mining) — Claude API batch command for user to run

---

*BATON PLUS generated March 20, 2026, Session 2. This document is a comprehensive handoff covering both sessions today.*
