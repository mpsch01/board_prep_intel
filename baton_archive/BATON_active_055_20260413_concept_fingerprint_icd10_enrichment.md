# BATON 055 — 2026-04-13 — Concept Fingerprint + ICD-10 Hidden Enrichment

**Active Session Handoff Document for board_prep_intel**

---

## Session Overview

| Item | Value |
|------|-------|
| **Date** | 2026-04-13 |
| **Previous BATON** | BATON_active_054_20260412_report_builder_redesign.md |
| **Git Hash (pre-commit)** | db2c099 |
| **Branch** | main |
| **Primary Goal** | Fix Concept Fingerprint synonym explosion + add ICD-10 hidden enrichment layer for practice question selection |
| **Status** | ✅ Complete |

---

## DATABASE STATE

(Inherited from BATON 054 — no structural changes this session)

| Table | Rows | Notes |
|-------|------|-------|
| articles | 1,985 | +49 AAFP acquisition (ART-1938–ART-1986) |
| questions (ITE) | 1,629 | 2018–2025, blueprint 100% filled |
| aafp_questions | 1,221 | BRQ, blueprint 100% filled |
| qid_art_xref | 2,470 | All 8 years: 2018–2025 |
| aafp_qid_art_xref | 864 | 643 unique questions linked (52.7%) |
| article_icd10 | 4,020 | Rebuilt with vec (2026-04-05) |
| question_icd10 | 5,218 | 1,512/1,629 ITE questions (92.8%) |
| aafp_question_icd10 | 4,753 | Relevance normalized, related cap applied |
| clinical_pathways | 3,971 | Blueprint-based, both banks, ART-0002–ART-1985 |
| pubmed_pmid_cache | 344 | Layer 2 seed (citation_id → PMID) |
| article_icd10_vec | 1,757 | Rebuilt 2026-04-05 |
| question_icd10_vec | 2,747 | Rebuilt 2026-04-05 |
| icd10_vec | 2,219 | OpenAI text-embedding-3-small (1536d) |
| article_currency | 1,985 | Built 2026-04-07 (current:1100, updated:169, check_needed:106, not_indexed:610) |

---

## PDF LIBRARY

(No changes this session — inherited from BATON 054)

| Tier | Count | Notes |
|------|-------|-------|
| VC_fail | 630 | Failed VC gate; awaiting enrichment |
| VC_pass | 168 | Passed VC gate; awaiting enrichment |
| local_lite | 117 | Enriched; not VC-cited |
| right_click | 58 | Enriched + VC-cited (top tier) |
| **ITE Total** | **988** | Across 4 tiers in citation_files/ITE/ |
| AAFP | 15 | citation_files/AAFP/ |
| ITE exams | 16 | All 8 years (2018–2025) × MC + critique |

---

## SESSION SUMMARY: WHAT HAPPENED

### Task 1: Concept Fingerprint Synonym Collapse — ite_analyzer_v3.py

**Problem identified:** The Concept Fingerprint section was displaying duplicate diagnoses under variant labels. For example, Hypertension appeared as "hypertension", "stage 2 hypertension", "essential hypertension" — same disease, counted as three separate concepts. Additionally, "Type 2 Diabetes Mellitus", "T2DM", and "type 2 diabetes" were separate rows. This fragmentation filled 8+ pages with noise.

**Root cause:** Concept tags from the question blueprint and ICD-10 cross-reference used medical shorthand and natural-language variants. No normalization layer existed to collapse them to canonical forms.

**Solution implemented:**
- Added `CONCEPT_SYNONYMS` dictionary (~80 entries) mapping medical abbreviations and variant forms to canonical labels:
  - T2DM, type 2 diabetes, type 2 dm, type 2 diabetes mellitus → **Type 2 Diabetes Mellitus**
  - HTN, hypertension (essential), hypertension (stage 2), hypertension (uncontrolled) → **Hypertension**
  - Similar entries for 78 other common conditions (HIV, IBS-D, GERD, Osteoarthritis, etc.)
- Added `_normalize_concept()` function with fallback: first-letter capitalize only (NOT `.title()`). This preserves acronyms (HIV stays HIV; IBS-D stays IBS-D) instead of mangling them to "Hiv" and "Ibs-D".
- Reworked `concept_clustering()` to apply normalization at aggregation time. All concept variants are now collapsed during the frequency roll-up.
- Recurring Diagnoses threshold raised from 2 to 4 (reduces noise; requires ≥4 appearances to surface).

**Result verified:** Concept Fingerprint section now displays ~12 canonical diagnoses instead of 50+ variant rows. Recurring Diagnoses table removed from report builder per design decision (was 8+ pages).

### Task 2: Practice Question Selection Overhaul — Fingerprint-Weighted Scoring

**Problem identified:** Practice questions were ranked by `ORDER BY linked_articles DESC` — pure article count. This prioritized niche-but-well-cited topics (CPPD, sarcoidosis) over common conditions (Hypertension, T2DM) that Sarkar kept missing. No relevance signal to the resident's actual weaknesses.

**Root cause:** No connection between the Concept Fingerprint (resident's missed diagnoses) and practice question selection scoring.

**Solution implemented:**
- Replaced concept-tag overlap bonus (max +1.2, negligible effect) with **fingerprint frequency-weighted bonus**: `freq / 10.0` per matched concept.
  - Hypertension frequency=33 → +3.3 bonus
  - Type 2 Diabetes Mellitus frequency=28 → +2.8 bonus
  - Scale is now competitive with Tier 1 base scores
- Added `_concept_selection()` function (Tier 1c): queries both ITE + AAFP question banks using concept_tags; returns candidates that directly test the resident's top missed diagnoses.
- Wired fingerprint bonus into `match_practice_questions_v3()`: bonus is applied after Tier 1 base scoring and before ICD-10 proximity bonus.
- Added `fingerprint_concepts` field to each selected question (list of which top missed concepts it tests). Used by report builder for the Fingerprint column in the practice table.

**Result verified:** All 20 practice questions now have fingerprint_concepts populated. Top question (AAFP-49912) scores 103.2 with 5 fingerprint concepts: Hypertension, Type 2 Diabetes Mellitus, Metformin, Obesity, Hypothyroidism.

### Task 3: ICD-10 Hidden Enrichment Layer — Architecture Decision

**Problem identified:** Concept Fingerprint uses canonical forms ("Hypertension"); concept_tags in the question blueprint use specific variants ("stage 2 hypertension", "prediabetes", "diabetic neuropathy"). Adding synonym entries for every variant would require maintaining hundreds of entries. No scalable solution for the label-variant mismatch.

**Architecture solution:** Use ICD-10 codes as an invariant taxonomy-stable invisible scoring layer.

**Why ICD-10 works:**
- ICD-10 code I10 covers "hypertension" / "stage 2 hypertension" / "essential hypertension" / "hypertensive emergency" regardless of how the concept_tag was written
- Codes are invariant to free-text label variants; the taxonomy is stable across years
- Codes can never appear in the report; they serve as an invisible precision layer only

**Implementation:**
- Added `icd10_profile: dict = None` parameter to `match_practice_questions_v3()`
- ICD-10 proximity bonus block: batch-loads ICD-10 codes for ALL candidate questions from question_icd10 and aafp_question_icd10 tables
- Computes overlap between the resident's ICD-10 weakness profile (from `icd10_clusters` in the analysis) and each question's codes
- Bonus scale: miss_count=7 (E11.9 Type 2 Diabetes, primary) → +0.93; miss_count=5 (I10 Hypertension, primary) → +0.67; multi-code matches stack
- Wired into `analyze_v3()`: `icd10_profile = {c["code"]: c["miss_count"] for c in icd10_map["icd10_clusters"]}` passed to match function

**Result verified:** QID-2023-0166 (ITE question on HTN+T2DM comorbidity) entered the practice set due to ICD-10 bonus lifting it to score 99.2 — beating AAFP-50378 (which scored higher before). The question never displays ICD-10 codes; the bonus is a silent precision signal only.

### Task 4: Report Builder Updates — ite_report_builder_v2.js

- QID display in Concept Fingerprint tables capped at 5 (was uncapped; some cells showed 33 QIDs)
- Recurring Diagnoses table removed entirely (freed 8+ pages)
- Fingerprint column added to 8-column practice question table (displays amber concept labels from fingerprint_concepts field)
- `hasFingerprintConcepts` flag: if any question has fingerprint_concepts, report shows 8-col table; otherwise 7-col

### Task 5: Canary Test Suite — test_v3_changes.py (NEW)

Created `03_module.3_analyst/scripts/test_v3_changes.py` with 5 targeted tests:

1. **_normalize_concept()** — 16 test cases covering synonym map (T2DM, HTN, HIV, IBS-D, etc.) and fallback (first-letter capitalize)
2. **concept_clustering()** — ITE-only QID tracking, normalization applied, threshold=4 behavior
3. **_concept_selection()** — both ITE + AAFP banks returned with Concept: targeting
4. **match_practice_questions_v3()** — concept wiring, fingerprint bonus applied, icd10_profile passed through
5. **Full analyze_v3()** — end-to-end smoke test with real Sarkar data

**All 5 tests pass.** This is the canary suite — run it after any changes to ite_analyzer_v3.py before pipeline production runs.

---

## SCRIPT INVENTORY

| Module | Category | Count | Notes |
|--------|----------|-------|-------|
| M1 | Build (Python) | 6 | No changes |
| M1 | Maintain (Python) | 26 | No changes |
| M2 | Python | 75 | No changes |
| M2 | JavaScript | 6 | No changes |
| M3 | Python | 16 | **+1 new:** test_v3_changes.py (canary test suite) |
| M3 | JavaScript | 2 | No changes |
| M3 | JSON config | 1 | No changes |
| M5 | TypeScript/TSX | 35 | No changes |
| M5 | SQL migrations | 5 | No changes |

**Modified this session:**
- `03_module.3_analyst/scripts/ite_analyzer_v3.py` — concept normalization, concept_clustering rework, practice question selection overhaul, ICD-10 hidden layer, fingerprint_concepts annotation
- `03_module.3_analyst/scripts/ite_report_builder_v2.js` — QID cap at 5, Recurring Diagnoses table removal, Fingerprint column addition, hasFingerprintConcepts flag

---

## DEFERRED FLAGS

### DEFERRED-YOY-ROBUSTNESS
**Status: ACTIVE — carry forward**

Year-over-year section (Section 3b in ite_analyzer_v3.py) added in BATON 050. Month-by-month rollup needs robustness testing with dense temporal data (multiple questions missed in same month). Currently usable for exploratory analysis but edge cases not yet vetted.

**Next action:** Run `test_v3_changes.py` against resident data with dense temporal clustering (e.g., 6 questions in same month). Add edge-case tests to canary suite.

---

### DEFERRED-PGY-BENCHMARKS
**Status: ACTIVE — carry forward**

Awaiting PGY 1–4 cohort data from Mikey to integrate program-level benchmarks into the report (Section 4 comparison table).

**Next action:** Receive historical PGY 1–4 aggregate scores from Mikey; integrate into report builder.

---

### DEFERRED-PROGRAM-TREND
**Status: ACTIVE — carry forward**

`abfm_reference_YYYY.json` files have null program_trend values. Requires historical program aggregate scores (e.g., % correct by question across all residents) to seed Layer 4 (trends). Mikey to supply.

**Next action:** Mikey to provide historical program aggregate data; inject into abfm_reference JSON files.

---

### DEFERRED-RESIDENT-FOLDER-MIGRATION
**Status: ACTIVE — carry forward**

Existing resident_data folders use flat structure (inputs mixed with outputs). New structure is `inputs/` and `outputs/`. Folders created after 2026-04-10 use new structure; older folders still flat.

**Next action:** Migrate existing resident folders to inputs/outputs structure (not blocking current analysis).

---

### FLAG-33-NNN-RENAME
**Status: DEFERRED — designed, not yet implemented**

nnn_XXXX ART-ID rename scheme designed in earlier BATON but not implemented. Low priority; current ART-NNNN scheme is working.

**Next action:** Implement only if Mikey prioritizes; currently deferred.

---

## CRITICAL REMINDERS FOR NEXT SESSION

1. **ICD-10 enrichment is invisible** — `icd10_profile` is passed to `match_practice_questions_v3()` but NEVER appears in the report. Don't add ICD-10 columns or sections back to the output unless Mikey explicitly requests it. The layer exists purely as a precision scoring signal.

2. **concept_qid_map = ITE-only** — Source 2 (AAFP enrichment) contributes to frequency counts but NOT to QID tracking. High-frequency concepts (Hypertension 33×) may have empty QID arrays because the count comes mostly from AAFP cross-reference enrichment, not from ITE questions Sarkar specifically missed. This is intentional.

3. **_normalize_concept() fallback = first-letter capitalize only** — NOT `.title()`. Reason: `.title()` mangles acronyms (HIV → Hiv, IBS-D → Ibs-D). The fallback is only used for concepts not in the synonym map; adding new synonym entries is the right fix for medical acronyms, not changing the fallback logic.

4. **test_v3_changes.py is the canary** — Run it after any changes to ite_analyzer_v3.py. All 5 tests must pass before pipeline production run. Add tests to it; don't delete.

5. **Fingerprint column only appears if hasFingerprintConcepts is true** — Report builder checks this flag. If any question has fingerprint_concepts populated, the 8-column table renders. Current Sarkar pipeline always populates it for all 20 questions. If a future resident has no practice questions with fingerprint concepts, the report will gracefully show a 7-column table instead.

6. **Recurring Diagnoses table is permanently gone** — Removed in this session. If a future request asks to show recurring diagnoses, that data still exists in the analysis JSON (concept_clusters with frequency ≥ 4); it would just need a report section re-added. But don't re-add it to the default report.

7. **QID cap at 5** — Each cell in Concept Fingerprint tables now shows max 5 QIDs (e.g., "QID-2024-0001, QID-2024-0002, QID-2024-0003, ..."). Before it showed all 33. If Mikey wants to display more or all QIDs, change the `qidLimit` constant in ite_report_builder_v2.js.

---

## NEXT STEPS

### Immediate (next session)
1. **Mikey to review** Sarkar 2026-04-13 report with Concept Fingerprint + ICD-10 enrichment — confirm design is satisfactory
2. **Program trend data** — Mikey to supply historical program aggregate scores (% correct by question, by year) for abfm_reference JSON
3. **DEFERRED-YOY-ROBUSTNESS** — Add edge-case tests to test_v3_changes.py (month-by-month temporal clustering)

### Short-term
4. **Resident folder migration** — Migrate existing flat resident_data folders to inputs/outputs structure
5. **Module 5 setup** — Provision Supabase project, run migrations, sync SQLite → Supabase, deploy Railway FastAPI + Netlify frontend
6. **DEFERRED-PGY-BENCHMARKS** — Once Mikey provides PGY 1–4 cohort data, integrate into report Section 4

---

## LOCKED RULES (Never Override Without Mikey Confirming)

1. **Fix the data, not the code.** If a script gets complex to handle messy data → clean the data upstream instead.
2. **VC gate = sole criterion** for right_click tier. DB membership alone is not sufficient.
3. **Source data is protected.** DB + PDFs + VC gate survive everything. Derived files are disposable.
4. **Dynamic paths only.** Python: `SCRIPT_DIR = Path(__file__).resolve().parent; PROJECT_ROOT = SCRIPT_DIR.parent.parent`. JS: `path.resolve(__dirname, "../../")`.
5. **No de novo JS.** Relaxed — use when needed, flag if multilingual clutter accumulates.
6. **BATON first.** Read the active BATON before any work. It has deferred flags and current state.
7. **QC after every integration.** Schema-level column-by-column population comparison, old cohort vs new.
8. **Git via Desktop Commander.** Claude can run git commits via Python subprocess (helper: `claude_knowledge/git_runner.py`). Cannot `rm` NTFS files — deletions still require Windows Explorer/terminal.
9. **shutil.rmtree is BANNED.** Use explicit file-by-file deletion or PowerShell Remove-Item. shutil.rmtree bypasses Recycle Bin and is irreversible — learned from fix_ghost.py incident 2026-04-05.
10. **Strategy 0 in every enricher.** Codon parse is always the first matching strategy.
11. **Schemas before scripts.** SQL `CREATE TABLE` defined before build scripts are written.

---

## FOR THE REPO (Git Notes)

- **Branch:** main
- **Latest commit hash (pre-BATON):** db2c099
- **Unpushed changes:** ite_analyzer_v3.py, ite_report_builder_v2.js, test_v3_changes.py (new) — ready to commit
- **Next action:** Mikey to review report output; commit changes once design approved

---

**End BATON 055**

*Handoff ready for next Claude instance. Read this first before any work.*
