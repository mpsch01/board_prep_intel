# Memory — #PROJECT_OVERHAUL

## Who You're Working With
**Mikey** (Michael Scholl) — Family medicine physician and residency program director. Self-taught data architect. Speaks in concepts and biological analogies. Strong architectural instincts — his design calls are almost always better than first proposals. Has API access (key in env vars). Runs long-running code himself (copy-paste-run pattern).

---

## The Project in One Sentence
ABFM ITE Intelligence System — a queryable Family Medicine board exam knowledge base (1,639 questions, 2018–2025) linked to a clinical guideline library (1,998 articles, 404 PDFs) via a structured SQLite pipeline.

---

## Terms — Decode These First

| Term | Meaning |
|------|---------|
| **ITE** | In-Training Examination (ABFM Family Medicine board exam) |
| **ABFM** | American Board of Family Medicine |
| **VC** | AAFP Board Prep Video Course (48 sessions, the priority filter) |
| **VC gate** | `key_data_files/session_hy_inserts_v7.json` — 352 citations — SOLE criterion for right_click tier |
| **BATON** | Session handoff document. Read the active one first, every session |
| **codon** | Filename format: `Author_Year#@#ART-XXXX@#@.pdf` — start `#@#`, stop `@#@` |
| **ART-ID** | Article primary key (e.g. ART-1234) — embedded in codon filename |
| **QID** | Question ID format: `QID-YYYY-NNNN` (e.g. QID-2024-0042) |
| **right_click / $right_click$** | M2 completed tier: VC_pass + fully enriched (DOCX exists) — folder: `03_right_click/` |
| **local_lite** | M2 completed tier: VC_fail + fully enriched (DOCX exists) — folder: `01_local_lite/` |
| **VC_pass** | M1 staging tier: passed VC gate, awaiting full pipeline (`VC_pass/` folder, was `02_codon/`) |
| **VC_fail** | M1 staging tier: failed VC gate, awaiting full pipeline (`VC_fail/` folder, was `00_non-codon/`) |
| **HY inserts** | High-Yield inserts — the enrichment content injected into the VC outline |
| **enricher** | `ite_intelligence_enricher.py` — primary v4 enricher, Strategy 0 = codon parse |
| **Strategy 0** | Regex parse of codon to extract ART-ID — primary match strategy, always first |
| **the DB** | `00_database/db/ite_intelligence.db` — source of truth, never disposable |
| **PROJECT_ROOT** | 2 levels up from SCRIPT_DIR — `SCRIPT_DIR = Path(__file__).resolve().parent; PROJECT_ROOT = SCRIPT_DIR.parent.parent` (= 3 hops from file) |
| **M1 / M2 / M3 / M4** | Warehouse / Processor / Analyst / Sandbox modules |
| **Module F** | VC Outline Pipeline: 01→02b→03→04→07→08→09→build_v6 |
| **keyword pipeline** | A→B→C→D→E_v4→F→G scripts |
| **Intelligence 2.0** | Layer 1 (ICD-10), Layer 2 (PubMed currency), Layer 3 (Pathways), Layer 4 (Trends) |
| **FLAG 33** | nnn_XXXX ART-ID rename scheme — designed, not yet implemented |
| **derived data** | Disposable: JSONs, DOCXs, CSVs. DB + PDFs + VC gate are protected source data |
| **_index.md** | Ground-truth directory map — `00_#PROJECT_OVERHAUL/_index.md` |
| **TODO: not yet migrated** | Code annotation — path points to correct future location; update when file arrives |

→ Full glossary: `.auto-memory/memory/glossary.md`

---

## Active State (update each session)

| Item | Value |
|------|-------|
| Active BATON | `BATON_active_063_20260429_report_guides_complete.md` — Two interpretation guides complete (resident + faculty); word_doc_defaults.py level 1/2 headers; Rule 14 locked. |
| DB articles | 1,998 (+13 from critique PDFs: ART-1987–ART-1999) |
| DB questions (ITE) | 1,639 (+10 recovered; enrichment pipeline complete) — blueprint 100% filled — subcategory + topic_label DROPPED — body_system taxonomy normalized 2026-04-16 |
| DB questions (AAFP BRQ) | 1,221 — blueprint 100% filled — flattened (correct_letter, correct_text, explanation merged in; subcategory + aafp_explanations DROPPED) |
| aafp_questions.blueprint | 1,221/1,221 (100%) — batch API, same rubric as ITE v2 — complete 2026-03-30 |
| aafp_questions.concept_tags | 1,221/1,221 (100%) |
| article_icd10 | 4,959 rows — ↑ from 3,952 (pre-existing Windows PC enrichment, confirmed BATON 062) |
| question_icd10 | 5,774 rows — ↑ from ~5,003 (pre-existing Windows PC enrichment, confirmed BATON 062) |
| aafp_question_icd10 | 4,753 rows — relevance normalized, related cap applied |
| pubmed_pmid_cache | 344 rows — Layer 2 seed (citation_id → PMID) |
| icd10_vec | 2,219 rows — OpenAI text-embedding-3-small (1536d) |
| article_icd10_vec | 1,757 rows — ✅ rebuilt 2026-04-05 |
| question_icd10_vec | 2,747 rows — ✅ rebuilt 2026-04-05 |
| intersection_centroid_vec | 158 rows — ↑ from 123 (BATON 062) |
| clinical_pathways | 4,959 rows — ↑ from 3,971 (pre-existing Windows PC enrichment, confirmed BATON 062) |
| PDFs (ITE citation tiers) | 988 across 4 tiers in citation_files/ITE/ (VC_fail:630, VC_pass:168, local_lite:117, right_click:58) + 15 AAFP — recovered 2026-04-05 via exa_pdf_downloader + pmc_oa_downloader + recover_unpaywall; 14 dupes in _dupe_archive/ |
| PDFs (AAFP) | 15 in citation_files/AAFP/ — recovered 2026-04-05 |
| PDFs (ite_exams) | 16 — all 8 years (2018–2025) × MC + critique; naming: YYYY_MC.pdf / YYYY_critique.pdf |
| practice_questions | 42 files — 8 ITE DOCX + 8 ITE XLSX + 13 AAFP DOCX + 13 AAFP XLSX (gitignored, regenerable from DB) |
| qid_art_xref | 2,485 (rebuilt faithful multi-reference xref: 2018-2023 100% linked, 2024 90%, 2025 83.5%) |
| aafp_qid_art_xref | 864 rows (643 unique questions linked, 52.7%) |
| M1 scripts | 8 build + 26 maintain + aafp_brq_scraper.py at scripts/ root (build_modular_vectors.py + build_intersection_centroids.py added 2026-04-14) |
| M2 scripts | 75 Python + 6 JS + 1 JSON in scripts/; core/ (4py) + engines/ (7py) + utils/ (6py) packages; source/ (transcripts, blueprint xlsx, outline DOCX); outputs/ (staging JSONs, citation gap); prompts/ (templates); main.py + requirements.txt at M2 root; extract_ite_critique_refs.py MODIFIED |
| M3 scripts | 52 Python + 4 JS + 6 JSON config (build_resident_guide.py + build_faculty_guide.py + build_resident_guide.js + build_faculty_guide.js ADDED BATON 063; word_doc_defaults.py MODIFIED BATON 063) |
| M5 scripts | 3 Python sync + 35 TypeScript/TSX + 5 SQL migrations — 05_module.5_web/ scaffold |
| article_currency | 1,998 rows — complete 2026-04-16 (was missing 115 rows) |
| Apify actor | `apify-actors/citation_crawler/` — DEPLOYED ✅ actor ID `rh50nQRP7BupbUF64` (`mpsch1~citation-crawler`), build 0.3.1 (PlaywrightCrawler) |
| Next ART-ID | ART-2000 |
| Git branch | main, latest → 58589ff (push pending from GitHub Desktop) |
| GitHub remote | `https://github.com/mpsch01/board_prep_intel` (private) |
| .gitignore strategy | Code + docs on GitHub. Binaries excluded: `*.db`, `*.pdf`, `extracted_json/`, `resident_data/` → local disk / Google Drive |

→ Full state: `.auto-memory/project_overhaul_state.md` and `.auto-memory/project_current_db_state.md`

---

## Module Map

| Module | Path | What it does |
|--------|------|--------------|
| M1 Warehouse | `01_module.1_warehouse/` | PDF library (4 tiers) + build/ + maintain/ scripts |
| M2 Processor | `02_module.2_processor/` | Extraction, enrichment, DOCX builders + source/ inputs |
| M3 Analyst | `03_module.3_analyst/` | ICD-10 tagging, pathways, trends, score analysis |
| M4 Sandbox | `04_module.4_sandbox/` | Experiments, agents |
| M5 Web | `05_module.5_web/` | Interactive web platform (Next.js + Supabase + Sanity + Railway FastAPI) |
| DB | `00_database/db/ite_intelligence.db` | Source of truth |
| VC Gate | `key_data_files/session_hy_inserts_v7.json` | 352 citations |

---

## Locked Rules (never override without Mikey confirming)

1. **Fix the data, not the code.** If a script gets complex to handle messy data → clean the data upstream instead.
2. **VC gate = sole criterion** for right_click tier. DB membership alone is not sufficient.
3. **Source data is protected.** DB + PDFs + VC gate survive everything. Derived files are disposable.
4. **Dynamic paths only.** Python: `SCRIPT_DIR = Path(__file__).resolve().parent; PROJECT_ROOT = SCRIPT_DIR.parent.parent`. JS: `path.resolve(__dirname, "../../")`.
5. **No de novo JS.** Existing JS scripts migrate fine. New code = Python only.
6. **BATON first.** Read the active BATON before any work. It has deferred flags and current state.
7. **QC after every integration.** Schema-level column-by-column population comparison, old cohort vs new.
8. **Git via Desktop Commander.** Claude can now run git commits via Desktop Commander Python subprocess (helper: `claude_knowledge/git_runner.py`). Cannot `rm` NTFS files — deletions still require Windows Explorer/terminal.
11. **`shutil.rmtree` is BANNED.** Use explicit file-by-file deletion or PowerShell Remove-Item. shutil.rmtree bypasses Recycle Bin and is irreversible — learned from fix_ghost.py incident 2026-04-05.
9. **Strategy 0 in every enricher.** Codon parse is always the first matching strategy.
10. **Schemas before scripts.** SQL `CREATE TABLE` defined before build scripts are written.
12. **`_normalize_concept()` fallback = first-letter capitalize only.** Never `.title()` — it mangles acronyms (HIV → Hiv, IBS-D → Ibs-D). Use `stripped[0].upper() + stripped[1:]`. Add new synonym entries for any canonical form that needs resolution; don't change the fallback.
13. **ICD-10 enrichment is invisible.** `icd10_profile` is passed to `match_practice_questions_v3()` as a hidden scoring signal and must never appear in the resident report. ICD-10 codes are internal precision machinery only — taxonomy-stable variant matching that bypasses concept-tag label differences.
14. **Word docs use `word_doc_defaults.py`.** All Python scripts that generate `.docx` files must `from word_doc_defaults import *` and apply the St. Luke's color palette, Aptos font, and helper functions defined there. Path: `03_module.3_analyst/scripts/word_doc_defaults.py`. Override only when Mikey explicitly directs otherwise. (Complements Rule 5: new Word doc generation = Python + word_doc_defaults.py, not de novo JS.)

→ Full principles: `.auto-memory/rebuild_structuring_guidelines.md`

---

## Next Steps (as of BATON 063, 2026-04-29)

### Immediate
1. **Re-run all 7 resident analyses** on Windows PC after git pull to pick up Issues 1-5 + new guide scripts
2. **Push commit** — user pushing 58589ff via GitHub Desktop

### Short-term
3. **DEFERRED-PGY-BENCHMARKS** — UNBLOCKED — PGY-level benchmark comparison in report
4. **DEFERRED-PROGRAM-TREND** — UNBLOCKED — Cohort-level trend analysis
5. **DEFERRED-QID-XREF-LIBRARY-GAPS** — 249 unmatched citations; prioritize by frequency