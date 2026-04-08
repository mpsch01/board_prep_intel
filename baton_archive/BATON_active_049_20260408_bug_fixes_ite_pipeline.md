# BATON 049: ITE Pipeline Bug Fixes (BUG-047-01, 02, 03)
**Date:** 2026-04-08  
**Session Type:** Bug fixes — ITE score analysis pipeline  
**Prior BATON:** BATON_active_048_20260408_skill_templates_housekeeping.md  
**Git Hash:** f2728d9

---

## RECON DATA

**Git Hash:** f2728d9 (branch: main)
**Git Status:** Clean working tree from sandbox perspective. Modified scripts (ite_parser.py, ite_analyzer_v3.py, ite_analyze_v2.py, ite_report_builder_v2.js) — need to be committed.

**DB State (unchanged from BATON 048):**
- articles: 1,985
- questions (ITE): 1,629
- aafp_questions: 1,221
- qid_art_xref: 2,470
- aafp_qid_art_xref: 864
- article_icd10: 4,020
- question_icd10: 5,218
- aafp_question_icd10: 4,753
- clinical_pathways: 3,971
- pubmed_pmid_cache: 344
- article_icd10_vec: 1,757
- question_icd10_vec: 2,747
- icd10_vec: 2,219
- article_currency: 1,985

**PDF Library (on Windows, not visible in sandbox - carry from BATON 048):**
- VC_fail: 630, VC_pass: 168, local_lite: 117, right_click: 58, AAFP: 15, ite_exams: 16, Total: 1,004
- No PDF changes this session

**Script Counts:**
- M1 build: 6 py, M1 maintain: 26 py
- M2: 75 py, 6 js
- M3: 14 py, 2 js (excluding node_modules)

---

## SESSION SUMMARY

This session fixed three open bugs (BUG-047-01, BUG-047-02, BUG-047-03) in the ITE score analysis pipeline and ran all fixes against test data.

**Work Done:**

### BUG-047-01 FIX — Exam Year Hardcoded to 2025 (ite_parser.py)
- **Root cause:** `parse_blueprint()` extracted exam year from `ite_parser_config.json` which had `"source_report": "ABFM ITE 2025"` hardcoded.
- **Fix:** Added regex extraction of exam year directly from PDF page text: `re.search(r'(20\d\d)\s+Item Performance Report', page_text)` with fallback to config filename parsing.
- **Validated:** Scholl_2022 → "Exam Year: 2022", Scholl_2023 → "Exam Year: 2023", Scholl_2024 → "Exam Year: 2024", Sarkar_2025 → "Exam Year: 2025", Hopkins_2025 → "Exam Year: 2025". All correct.

### BUG-047-02 FIX — 2024 Body System Name Variance (ite_analyzer_v3.py + ite_analyze_v2.py)
- **Root cause:** PDF body system header names don't always match DB-side canonical names exactly. No normalization layer existed.
- **Fix:** Added `BODYSYSTEM_PDF_NORM` alias dict and `_normalize_body_system()` function in `ite_analyzer_v3.py`. Applied normalization to all items in `analyze_v3()` after QID map build. Also applied in `ite_analyze_v2.py` to `body_system_scaled` dict from score report.
- **Key aliases:** "Musculoskeletal" → "Injuries/Musculoskeletal", "Hematologic/ Immune" → "Hematologic/Immune", "Psychogenic" → "Psychiatric/Behavioral", "Reproductive: Female"/"Reproductive: Male" → "Sexual and Reproductive"
- **Exported:** `_normalize_body_system` from ite_analyzer_v3.py so ite_analyze_v2.py can import and reuse it.

### BUG-047-03 FIX — Report Personalization Issues (ite_report_builder_v2.js + ite_analyze_v2.py)
**Sub-issue A — Official score ignored:**
- **Root cause:** Report builder always read `t1 = data.thresholds.tier1_pass_probability` for score display, ignoring `performance.overall.scaled_score_actual` (official score from score report).
- **Fix:** Added `hasOfficialScore`, `displayScaled`, `displayVsMps`, `displayPgyLevel`, `displayPgyMean`, `displayVsPgy` preference variables. When `scaled_score_source === "official"`, uses actual score fields; otherwise falls back to estimated t1 values.
- **Validated:** Scholl_2024 now shows 500 (official) not 520 (estimated), PGY3 mean of 494, not "PGY2 National".

**Sub-issue B — Body systems not marked as weak:**
- **Root cause:** `weakBlueprints` array only populated from blueprint categories (< 70%). Body system weak areas were analyzed but their questions didn't get "⚠ WEAK AREA:" headers in practice section.
- **Fix:** Added loop after existing blueprint loop to push body systems below 70% into `weakBlueprints`.
- **Validated:** All 5 runs now show body systems in "Weak areas:" console line alongside blueprints.

### TEST RUNS

All 5 resident/year combinations run successfully:
| Resident | Year | Score | Weak Areas Count | Score Source |
|----------|------|-------|-----------------|--------------|
| Scholl | 2022 | Blueprint-only baseline | 3 blueprint | N/A |
| Scholl | 2023 | Blueprint-only baseline | 4 blueprint | N/A |
| Scholl | 2024 | 57.3% raw → 500 scaled | 3 bp + 3 bs | Official (PGY3) ✓ |
| Sarkar | 2025 | 57.1% (109/191) | 5 bp + 5 bs | Estimated |
| Hopkins | 2025 | 65.4% (125/191) | 4 bp + 4 bs | Estimated |

**Longitudinal delta:** Scholl_2024 picked up Scholl_2022 and Scholl_2023 as prior analyses correctly.

### NEW FINDING — Practice Question "0 Questions" Warning
Several weak areas consistently return 0 practice questions from the DB:
- Affected: Foundations, Preventive, Cardiovascular, Respiratory, Sexual and Reproductive, Psychiatric/Behavioral
- Root cause: qid_art_xref or question concept_tags don't cover these body systems/blueprint categories adequately for matching in the practice question engine
- **Not a pipeline bug** — just a DB coverage gap
- **Action needed:** Investigate practice question engine matching for these dimensions; may need to expand qid_art_xref tagging coverage

---

## BUGS STATUS

| ID | Issue | Status | Resolution |
|----|-------|--------|------------|
| BUG-047-01 | Exam year hardcoded 2025 | ✅ FIXED | PDF text regex in ite_parser.py |
| BUG-047-02 | 2024 body system name variance | ✅ FIXED | BODYSYSTEM_PDF_NORM alias map in ite_analyzer_v3.py |
| BUG-047-03 | Report personalization (score + weak areas) | ✅ FIXED | Official score preference vars + body system weak area loop in ite_report_builder_v2.js |
| BUG-NEW-049 | Practice Q "0 questions" for some body systems | 🔵 NEW/OPEN | DB coverage gap — qid_art_xref tagging for Foundations/Preventive/Cardiovascular/Respiratory/Sexual/Psychiatric |

---

## DEFERRED FLAGS (carry forward from BATON 048 + updates)

| Flag | Status | Notes | Next Action |
|------|--------|-------|-------------|
| DEFERRED-AAFP-PAYWALL | OPEN | ART-1959, ART-1972, ART-1967 paywalled | Mikey to coordinate via interlibrary loan |
| DEFERRED-PGY-BENCHMARKS | PARTIALLY SOLVED | ABFM embeds PGY mean in score report | Mikey to provide expected % ranges by PGY 1–4; add pgy_benchmarks.md |
| DEFERRED-L2-REVIEW | LOW PRI | Optional audit: 169 updated + 106 check_needed rows | Manual review window; no blocker |
| DEFERRED-AAFP-SITE | OPEN | AAFP site was down during PDF recovery | Monitor; re-run exa_pdf_downloader on recovery |
| DEFERRED-PRACTICE-Q-COVERAGE | NEW/OPEN | 0-question warnings for Foundations/Preventive/Cardiovascular/Respiratory/Sexual/Psychiatric | Investigate qid_art_xref tagging coverage for body system matching |

---

## NEXT STEPS

### Immediate
1. **Git commit** — Stage and commit ite_parser.py, ite_analyzer_v3.py, ite_analyze_v2.py, ite_report_builder_v2.js (all modified this session)
2. **DOCX review** — Mikey to open Scholl_2024, Sarkar_2025, Hopkins_2025 DOCXs and confirm: (a) score display correct (official vs estimated), (b) weak area section headers visible, (c) question personalization looks right
3. **Practice Q coverage** — Investigate BUG-NEW-049: why Foundations, Preventive, Cardiovascular, Respiratory, Sexual and Reproductive, Psychiatric/Behavioral return 0 practice questions

### Short-term
4. **DATABASE_GUIDE.md relocation** (carry from 048) — Finalize `git add DATABASE_GUIDE.md && git rm 00_database/DATABASE_GUIDE.md`
5. **Test Agents B & C** — Run next housekeeping sweep; validate _index.md + CLAUDE.md Active State updates from agent templates
6. **DEFERRED-PGY-BENCHMARKS** — Mikey to provide PGY 1–4 expected % ranges; add pgy_benchmarks.md to ite-domain skill
7. **AAFP PDF retry** — Monitor AAFP site recovery; re-run exa_pdf_downloader

### Medium-term
8. **Score report integration for Sarkar + Hopkins 2025** — If score reports become available, re-run with `--score-report` flag for official scores
9. **exa-research-search Phase 2** — Expand guideline library + clinical pathways pipeline (Intelligence 2.0 Layer 3)

---

## LOCKED RULES (No Changes)

1. **Fix the data, not the code.** Messy data → clean upstream, not in script logic.
2. **VC gate = sole criterion** for right_click tier. DB membership alone insufficient.
3. **Source data protected.** DB + PDFs + VC gate survive everything. Derived files (JSON, DOCX, CSV) disposable.
4. **Dynamic paths only.** Python: `SCRIPT_DIR = Path(__file__).resolve().parent; PROJECT_ROOT = SCRIPT_DIR.parent.parent`. JS: `path.resolve(__dirname, "../../")`.
5. **Build in whatever language fits.** Python default; JS when needed; flag if multilingual clutter accumulates.
6. **BATON first.** Read active BATON before any work session.
7. **QC after every integration.** Schema-level, column-by-column, old cohort vs new.
8. **Git via Desktop Commander.** Claude runs commits via DC Python subprocess (helper: `claude_knowledge/git_runner.py`). Cannot rm NTFS files.
9. **shutil.rmtree is BANNED.** Use explicit file-by-file deletion or PowerShell Remove-Item.
10. **Strategy 0 in every enricher.** Codon parse always first matching strategy.
11. **Schemas before scripts.** SQL CREATE TABLE defined before build scripts written.

---

## GLOSSARY REMINDERS

| Term | Reference |
|------|-----------|
| VC gate | key_data_files/session_hy_inserts_v7.json (352 citations) |
| right_click | 03_right_click/ tier: VC_pass + fully enriched |
| local_lite | 01_local_lite/ tier: VC_fail + fully enriched |
| codon | Filename format: Author_Year#@#ART-XXXX@#@.pdf |
| M1/M2/M3/M4 | Warehouse / Processor / Analyst / Sandbox |
| BATON | Session handoff document (this file) |
| _index.md | Ground-truth directory map |
| Intelligence 2.0 | Layers 1–4: ICD-10 / PubMed currency / Pathways / Trends |
| Agent A/B/C | BATON-writer / Index-memory-writer / Manifest-writer |

→ Full glossary: `.auto-memory/memory/glossary.md`
