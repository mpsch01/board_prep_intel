# BATON — PDF Library Reorganization: has_extraction Audit + DB Expansion

**Date:** March 20, 2026
**Previous BATON:** `BATON_active_20260319.md` (Architectural Pivot + Pipeline Map)
**Status:** LIBRARY REORGANIZATION SESSION COMPLETE. Audited 64 PDFs in `00_non-codon/has_extraction/`, merged ART-0404 into ART-1254, deleted 16 files (8 WRONG + 2 dupes + 6 MATCH merges), created 28 new DB article records (ART-1398–ART-1425), renamed all survivors to codon format, parked 20 files for review, and reorganized folder structure.

---

## What Was Done This Session

### 1. ART-0404 / ART-1254 Merge (AAA Screening)
Two duplicate DB records existed for the same USPSTF AAA screening article:
- **ART-0404** (3 QIDs, no codon filename)
- **ART-1254** (2 QIDs, had codon filename)

**Merge executed:**
- Reassigned 3 QIDs from ART-0404 → ART-1254 in `qid_art_xref`
- Migrated 3 `article_icd10` rows from ART-0404 → ART-1254
- Deleted ART-0404 from `articles` table
- Updated ART-1254: `codon_filename = 'uspstf_AAA_screening_2019#@#ART-1254@#@.pdf'`, `citation_count = 5`

**Result:** ART-1254 now has 5 QID links, all ICD-10 codes, all clinical pathways. ART-0404 is fully purged.

### 2. has_extraction Audit (64 PDFs)
Extracted metadata (title, author, first 500 chars) from all 64 PDFs using PyMuPDF, then cross-referenced each against:
- `ite_intelligence.db` (3 strategies: codon parse, clean_ref match, keyword/author fuzzy match)
- `session_hy_inserts_v7.json` (VC gate — 388 citation entries across 48 sessions)

Generated `has_extraction_audit.txt` for user review. User annotated each file with one of 8 labels.

### 3. User Review Categories and Actions Taken

| Category | Count | Action |
|---|---|---|
| **MATCH** | 8→6 | Confirmed correct ART-ID match. Renamed to codon. Then deleted all 6 — originals already exist in other tier folders (duplicates). |
| **WRONG** | 8 | Deleted — files incorrectly placed in has_extraction or not useful. |
| **WRONG MATCH — ADD TO DB** | 22 | Audit's fuzzy matcher linked to wrong ART-IDs. Created 22 new DB records with correct metadata. Renamed to codon. |
| **ADD TO DB** | 6 | No DB record existed at all. Created 6 new records. Renamed to codon. |
| **WRONG MATCH — REVIEW** | 5 | AJKD series — moved to `needs_review/` |
| **EXISTS IN DB UNDER DIFF NAME** | 2 | IDSA_LTAC-fever, afp_allergic_rhinitis — moved to `needs_review/` |
| **REVIEW** | 1 | ADA_standards-of-care-2025.pdf — moved to `needs_review/` |
| **Unlabeled** | 12 | Need further review — moved to `needs_review/` |

**Files deleted (16 total):**
1. `hep_hepB.pdf` (WRONG)
2. `hep_hepC_treatment.pdf` (WRONG)
3. `jacc_AF.pdf` (WRONG)
4. `jacc_PE.pdf` (WRONG)
5. `peds_asthma.pdf` (WRONG)
6. `peds_ADHD.pdf` (WRONG)
7. `peds_croup.pdf` (WRONG)
8. `peds_fever.pdf` (WRONG)
9. `APA_PTSD_treatment.pdf` (WRONG MATCH dupe — original in `01_local_lite/`)
10. `acg_celiac_disease.pdf` (WRONG MATCH dupe — same ART as afp_celiac, already in library)
11. `afp_celiac_disease.pdf` (MATCH — original exists in other tier folder)
12. `afp_type2_DM.pdf` (MATCH — original exists in other tier folder)
13. `acg_gallstones.pdf` (MATCH — original exists in other tier folder)
14. `afp_shoulder_pain.pdf` (MATCH — original exists in other tier folder)
15. `afp_iron_deficiency.pdf` (MATCH — original exists in other tier folder)
16. `jacc_cholesterol.pdf` (MATCH — original exists in other tier folder)

### 4. New DB Records Created (28 articles: ART-1398 – ART-1425)

All inserted with `citation_count = 0` and no QID linkages. All are **non-VC-cited** (confirmed via multi-round VC gate search). Metadata was manually corrected from PDF extraction artifacts.

| ART-ID | Codon Filename | Author | Year | Specialty Area |
|---|---|---|---|---|
| ART-1398 | Rabins_2007#@#ART-1398@#@.pdf | Rabins | 2007 | Psychiatry (Alzheimer's) |
| ART-1399 | Gelenberg_2010#@#ART-1399@#@.pdf | Gelenberg | 2010 | Psychiatry (MDD) |
| ART-1400 | Eikelboom_2017#@#ART-1400@#@.pdf | Eikelboom | 2017 | Cardiology (COMPASS trial) |
| ART-1401 | Nicolle_2019#@#ART-1401@#@.pdf | Nicolle | 2019 | Infectious Disease (ASB) |
| ART-1402 | Baddour_2005#@#ART-1402@#@.pdf | Baddour | 2005 | Infectious Disease (Endocarditis) |
| ART-1403 | Hill_2006#@#ART-1403@#@.pdf | Hill | 2006 | Infectious Disease (Travel Med) |
| ART-1404 | Miller_2024#@#ART-1404@#@.pdf | Miller | 2024 | Infectious Disease (Micro Lab) |
| ART-1405 | AAOS_2019#@#ART-1405@#@.pdf | AAOS | 2019 | Orthopedics (PJI) |
| ART-1406 | VA_DoD_2022#@#ART-1406@#@.pdf | VA_DoD | 2022 | Psychiatry (MDD) |
| ART-1407 | Patel_2022#@#ART-1407@#@.pdf | Patel | 2022 | GI (CRC Screening) |
| ART-1408 | Robertson_2017#@#ART-1408@#@.pdf | Robertson | 2017 | GI (FIT Screening) |
| ART-1409 | Tran_2016#@#ART-1409@#@.pdf | Tran | 2016 | GI/Hepatology (Liver + Pregnancy) |
| ART-1410 | Joglar_2024#@#ART-1410@#@.pdf | Joglar | 2024 | Cardiology (AFib) |
| ART-1411 | Messe_2020#@#ART-1411@#@.pdf | Messe | 2020 | Neurology (PFO + Stroke) |
| ART-1412 | AAN_2014#@#ART-1412@#@.pdf | AAN | 2014 | Neurology (Stroke Prevention) |
| ART-1413 | Iverson_2010#@#ART-1413@#@.pdf | Iverson | 2010 | Neurology (Dementia + Driving) |
| ART-1414 | AAN_2012#@#ART-1414@#@.pdf | AAN | 2012 | Neurology (Migraine Prevention) |
| ART-1415 | Oskoui_2019#@#ART-1415@#@.pdf | Oskoui | 2019 | Neurology (Peds Migraine Acute Tx) |
| ART-1416 | Oskoui_2019#@#ART-1416@#@.pdf | Oskoui | 2019 | Neurology (Peds Migraine Prevention) |
| ART-1417 | Turan_2017#@#ART-1417@#@.pdf | Turan | 2017 | Neurology (Intracranial Atherosclerosis) |
| ART-1418 | Wolraich_2019#@#ART-1418@#@.pdf | Wolraich | 2019 | Pediatrics (ADHD) |
| ART-1419 | Chang_2017#@#ART-1419@#@.pdf | Chang | 2017 | Pulmonology (Cough/Bronchiolitis) |
| ART-1420 | Cobaugh_2007#@#ART-1420@#@.pdf | Cobaugh | 2007 | Toxicology (Atypical Antipsychotic) |
| ART-1421 | Scharman_2006#@#ART-1421@#@.pdf | Scharman | 2006 | Toxicology (Diphenhydramine) |
| ART-1422 | Caravati_2007#@#ART-1422@#@.pdf | Caravati | 2007 | Toxicology (Rodenticide) |
| ART-1423 | Nelson_2007#@#ART-1423@#@.pdf | Nelson | 2007 | Toxicology (SSRI) |
| ART-1424 | Dart_2006#@#ART-1424@#@.pdf | Dart | 2006 | Toxicology (Acetaminophen) |
| ART-1425 | USPSTF_2022#@#ART-1425@#@.pdf | USPSTF | 2022 | Preventive (Aspirin CVD) |

### 5. VC Gate Re-Check (All 28 Confirmed Non-VC-Cited)
Multi-round verification against `session_hy_inserts_v7.json`:
- **Round 1:** Token overlap with 4+ hit threshold → false positives from generic terms ("treatment", "guideline")
- **Round 2:** Author surname + year + distinctive title words, score ≥5 → 0 matches (appropriately strict)
- **Round 3:** Exact author/topic keyword search → found 4 topic-adjacent but non-matching citations
- **Conclusion:** All 28 are genuinely non-VC-cited. The original audit's VC tags came from incorrectly matched DB articles (the fuzzy matcher linked PDFs to wrong ART-IDs that happened to be VC-cited).

### 6. QID Linkage Check
All 28 new articles (ART-1398–ART-1425) have **0 QID links** in `qid_art_xref`. They are DB-registered but not linked to any ITE exam questions.

### 7. MATCH Article Cleanup
The 6 MATCH files (ART-0217, ART-0583, ART-0622, ART-0706, ART-0758, ART-0973) were confirmed to be duplicates of PDFs already existing in other tier folders. All had QID links in the DB (ranging from 1 to 7 each). Files deleted from has_extraction; originals remain intact elsewhere.

### 8. Pipeline Processing Status of 28 New Articles
Checked extraction/output folders for artifacts:
- **14 of 28** have some pipeline outputs (extraction JSONs, raw_txt files, occasional DOCXs) — but these use slugified title-based filenames, NOT codon filenames
- **14 of 28** have zero pipeline outputs
- The existing outputs were created before codon rename — filename linkage is broken

### 9. Final File Moves
- 20 pending-review PDFs → `00_non-codon/has_extraction/needs_review/`
- 28 codon-named PDFs → `00_non-codon/` root (treated as fresh/unprocessed)
- `has_extraction/` root is now empty

---

## Current Folder State (Live as of Session End)

```
clinical_guidelines/01_pdf_guideline_library/       (3 files at root)
  MOVE_STUCK_FILES.ps1
  README.json
  desktop.ini

├── 00_non-codon/                    28 codon PDFs + 1 txt (has_extraction_audit.txt)
│   ├── has_extraction/              0 files (empty — can be deleted)
│   │   └── needs_review/            20 PDFs pending manual review
│   └── unexamined/                  102 PDFs (not yet audited)
│
├── 01_local_lite/                   117 PDFs
│
├── 02_codon/                        73 PDFs (19 accessible, 54 permission-locked)
│
└── 03_right_click/                  71 PDFs

TOTAL: 411 PDFs + 4 non-PDF files = 415 files
```

### needs_review/ Contents (20 files)
**Unlabeled (12):** aafp_menopause, acg_gastroparesis, BackPainPCP_Treatment_Algorithm, IDSA_lyme, IDSA_neutropenic_abx, neuro_bells_palsy, neuro_dementia_diagnosis, neuro_trigeminal_neuralgia, pulm_COPD, rheum_RA, rheum_lyme-disease, rheum_steroid-osteoporosis

**WRONG MATCH — REVIEW (5):** AJKD_CKD+DM2, AJKD_CKD+HTN, AJKD_CKD+obesity, AJKD_bone_mineral_d, AJKD_renal-nutrition

**EXISTS IN DB UNDER DIFF NAME (2):** IDSA_LTAC-fever, afp_allergic_rhinitis

**REVIEW (1):** ADA_standards-of-care-2025.pdf

---

## Database State (Post-Session)

```
ite_intelligence.db
├── articles:          1,424 rows  (was 1,397 → +28 new, -1 merged)
├── questions:         1,189 rows  (unchanged)
├── qid_art_xref:      1,818 rows  (unchanged count — 3 reassigned from ART-0404 → ART-1254)
├── article_icd10:     3,093 rows  (3 migrated from ART-0404 → ART-1254)
├── clinical_pathways:  3,093 rows  (unchanged)
└── ART-ID range:      ART-0001 through ART-1425 (ART-0404 deleted)
```

**Key DB changes:**
- ART-0404: DELETED (merged into ART-1254)
- ART-1254: citation_count updated to 5, codon_filename set
- ART-1398 through ART-1425: 28 NEW records, all with citation_count=0, no QID links, no VC citations

---

## Pipeline Processing State

```
03_enriched_JSON/              217 extracted JSON files (slugified title names)
03_enriched_JSON/raw_txt/      217 raw text files
02_docx_guideline_library/     1,518 files (DOCX summaries + variants)
04_need_extraction-batch/      0 files (empty)
```

**Note:** 14 of the 28 new articles have extraction artifacts in `03_enriched_JSON/` under their old slugified title-based filenames. These outputs are NOT linked to the current codon filenames. The other 14 have no pipeline outputs at all. All 28 should be treated as needing fresh pipeline processing.

---

## Open Flags

### Carried Forward (Previous Sessions)
- **FLAG 1:** ITE Enrichment Quality Dimension (deferred)
- **FLAG 13 Layer 2:** PubMed Currency (not started)
- **FLAG 15:** User still needs to run `node build_merged_docx.js --merged-only`
- **FLAG 27:** Report Builder v2 requires `npm install docx` in working directory
- **FLAG 28:** v1 HTML report incompatible with v2 question format (graceful fail, low priority)
- **FLAG 29:** Hardcoded `year = 2025` in subcategory_decomposition and plugin_concept_fingerprint
- **FLAG 30:** `scholl_204999_ITE_SCORE` PDFs are encrypted — need unencrypted versions
- **FLAG 31 [CRITICAL]:** 87 current codon PDFs misclassified — ITE-linked but not VC-cited. Must be re-tiered as `local_lite`.
- **FLAG 32 [CRITICAL]:** 266 VC-cited articles have no PDF. Highest-priority sourcing targets.
- **FLAG 33 [CRITICAL]:** ART-ID rename (`nnn_XXXX`) not yet implemented. All downstream systems still use `ART-XXXX`.
- **FLAG 34:** 27 VC citation strings have no DB match. Need manual resolution.
- **FLAG 35:** QID format mismatch — VC JSON uses `Q{YEAR}-{NUM}`, DB uses `QID-{YEAR}-{NUM:04d}`. Only 75/229 resolve.
- **FLAG 36:** ~86 new AFP articles (2022–2025) in library not yet in DB.
- **FLAG 37:** `who_infant_feeding.pdf` falsely matched to ART-1320.

### New Flags This Session
- **FLAG 38:** 54 permission-locked files in `02_codon/` — user needs to run `icacls /reset` on Windows side before VM can access.
- **FLAG 39:** `has_extraction/` folder is empty — can be cleaned up (but `needs_review/` subfolder must be preserved).
- **FLAG 40:** 14 of 28 new articles have orphaned pipeline outputs under old slugified filenames in `03_enriched_JSON/`. These could be re-linked or regenerated.
- **FLAG 41:** 102 unexamined PDFs in `00_non-codon/unexamined/` — next audit batch after needs_review is resolved.
- **FLAG 42:** 20 needs_review PDFs in `00_non-codon/has_extraction/needs_review/` — 12 unlabeled + 5 AJKD + 2 exists-under-diff-name + 1 ADA review.

---

## Key Findings / Decisions Locked This Session

1. **Fuzzy matchers produce dangerous false positives.** The original audit's VC-CITED tags were inherited from incorrectly matched DB articles, not from the PDFs themselves. Always verify VC status through direct citation-string search, not through inherited DB attributes.

2. **All 28 new articles are non-VC-cited.** Confirmed through 3 rounds of increasingly targeted search against `session_hy_inserts_v7.json`. Zero matches.

3. **MATCH files were duplicates, not originals.** The 6 MATCH files in has_extraction were copies of PDFs already existing in `01_local_lite/`, `02_codon/`, or `03_right_click/`. Correct action was delete (not rename).

4. **Pipeline outputs use slugified titles, not codon filenames.** There is no automatic linkage between `Rabins_2007#@#ART-1398@#@.pdf` and its extraction JSON `practice-guideline-for-the-treatment-of-patients-with-alzheimer-s-disease-and-4d6b542914_extracted.json`. Re-processing through the pipeline will generate new artifacts with correct naming.

---

## Key File Locations (Updated)

### Database
```
abfm_prep/02_ite_intelligence/db/ite_intelligence.db
  └── articles (1,424 rows)
  └── questions (1,189 rows)
  └── qid_art_xref (1,818 rows)
  └── article_icd10 (3,093 rows)
  └── clinical_pathways (3,093 rows)
```

### PDF Library
```
clinical_guidelines/01_pdf_guideline_library/
  ├── 00_non-codon/          28 codon PDFs (fresh, need processing) + 1 audit txt
  │   ├── has_extraction/    empty
  │   │   └── needs_review/  20 PDFs (pending user review)
  │   └── unexamined/        102 PDFs (not yet audited)
  ├── 01_local_lite/         117 PDFs
  ├── 02_codon/              73 PDFs (54 permission-locked)
  └── 03_right_click/        71 PDFs
```

### VC Integration Data
```
abfm_prep/04_aafp_integration/02_working/session_hy_inserts_v7.json
  └── 48 sessions, 229 QIDs, 352 unique citation strings (THE VC GATE)
```

### Session Artifacts
```
/sessions/loving-dreamy-brown/
  ├── has_extraction_metadata.json     (extracted PDF metadata for 64 files)
  └── new_article_records_clean.json   (mapping of 28 new articles)
```

---

## Codon Filename Convention (Unchanged)
```
Author_Year#@#ART-XXXX@#@.pdf
  Start codon: #@#
  Stop codon:  @#@
  ART-ID:      embedded between start and stop codons
  Example:     Rabins_2007#@#ART-1398@#@.pdf
```

---

## Next Session Candidates (Not Requested — For Reference)

1. **Review 20 needs_review PDFs** — same audit workflow: extract metadata, cross-ref DB + VC gate, get user labels
2. **Audit 102 unexamined PDFs** — the big untouched batch
3. **Resolve 54 permission-locked files** in `02_codon/` (requires Windows-side `icacls /reset`)
4. **Process 28 new articles** through pipeline (extraction → enrichment → DOCX)
5. **Continue overhaul planning** per BATON_active_20260319.md Phase 1–5 agenda

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
