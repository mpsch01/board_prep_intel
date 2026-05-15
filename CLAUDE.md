# Memory — ITE Intelligence System

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
| **_index.md** | Ground-truth directory map — `board_prep_intel/_index.md` |
| **TODO: not yet migrated** | Code annotation — path points to correct future location; update when file arrives |
| **Exam version** | Test-taking output of question set generation — questions + answer choices + answer key table at end; no explanations visible |
| **Study Guide version** | Review output — questions + correct answer (navy bold) + explanation body (shaded box) + References section (one citation per paragraph) after each question |
| **bracket notation** | User syntax for custom question set requests: `[count] [filters] [bank]` — `+` across types = AND, `+` within same type = OR |
| **custom_question_sets** | Output folder for content-filtered question sets: `03_module.3_analyst/custom_question_sets/YYYY-MM-DD/` |

→ Full glossary: `.auto-memory/memory/glossary.md`

---

## Active State (update each session)

| Item | Value |
|------|-------|
| Active BATON | `BATON_active_070_20260515_corpus_qc_skill_v1.md` — corpus-integrity-qc skill V1 build (Layers A, B, D + coordinator + 4 agent templates); end-to-end smoke test produces 2,538 findings split into 1,914 Tier 1 / 66 Tier 2 / 558 Tier 3; no DB/PDF/schema changes |
| DB articles | 2,206 (+13 from critique PDFs: ART-1987–ART-1999; +208 from acquire_missing_citations.py: ART-2000–ART-2207) |
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
| PDFs (ITE citation tiers) | 1,540 across 4 tiers in citation_files/ITE/ (VC_fail:1056, VC_pass:309, local_lite:117, right_click:58) — +159 net since BATON 066 (127 worktree merge + 72 AFP gap closure − 48 dupes − 79 corrupts quarantined/deleted) |
| PDFs (AAFP) | 15 in citation_files/AAFP/ — recovered 2026-04-05 |
| PDFs (ite_exams) | 16 — all 8 years (2018–2025) × MC + critique; naming: YYYY_MC.pdf / YYYY_critique.pdf |
| practice_questions | 42 files — 8 ITE DOCX + 8 ITE XLSX + 13 AAFP DOCX + 13 AAFP XLSX (gitignored, regenerable from DB) |
| qid_art_xref | 2,710 (rebuilt faithful multi-reference xref: 2018-2023 100% linked, 2024 90%, 2025 83.5%; +225 from new articles) |
| aafp_qid_art_xref | 864 rows (643 unique questions linked, 52.7%) |
| M1 scripts | 8 build + 38 maintain + aafp_brq_scraper.py at scripts/ root (BATON 067: aafp_targeted_downloader.py NEW + aafp_fill_gaps.py MODIFIED + 8 BATON 066 merged scripts: jama_chrome_harvester, jama_prep_articlepdf_urls, nejm_doi_lookup, nejm_build_js_batch, nejm_console_script, nejm_move_downloads, nejm_save_server, unpaywall_retry) |
| M2 scripts | 75 Python + 6 JS + 1 JSON in scripts/; core/ (4py) + engines/ (7py) + utils/ (6py) packages; source/ (transcripts, blueprint xlsx, outline DOCX); outputs/ (staging JSONs, citation gap); prompts/ (templates); main.py + requirements.txt at M2 root; extract_ite_critique_refs.py MODIFIED |
| M3 scripts | 55 Python + 4 JS + 6 JSON config (build_cole_exam_series.py + build_exam_series.py + build_custom_question_set.py ADDED BATON 064; ite_analyzer_v3.py MODIFIED BATON 064) |
| M5 scripts | 3 Python sync + 35 TypeScript/TSX + 5 SQL migrations — 05_module.5_web/ scaffold |
| article_currency | 2,206 rows — complete 2026-04-16 (was missing 115 rows); +208 new articles 2026-05-06 |
| Apify actor | `apify-actors/citation_crawler/` — DEPLOYED ✅ actor ID `rh50nQRP7BupbUF64` (`mpsch1~citation-crawler`), build 0.3.1 (PlaywrightCrawler) |
| Next ART-ID | ART-2208 |
| Git branch | claude/reverent-mclaren-575646 worktree → 22dae71 (BATON 070 housekeeping commit; corpus-qc skill V1 build at this hash); main at 57bbe7a awaiting merge |
| GitHub remote | `https://github.com/mpsch01/board_prep_intel` (private) |
| .gitignore strategy | Code + docs on GitHub. Binaries excluded: `*.db`, `*.pdf`, `extracted_json/`, `resident_data/` → local disk / Google Drive |

→ Full state: `.auto-memory/project_session_log.md` and `.auto-memory/project_current_db_state.md`

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

## Practice Question System

Three M3 scripts + two Cowork skills (added BATON 064).

### Scripts
| Script | Purpose |
|--------|---------|
| `build_custom_question_set.py` | Content-addressable question set generator — filter by blueprint, body_system, bank, years |
| `build_exam_series.py` | Generalized exam series generator from any resident's analysis JSON |
| `build_cole_exam_series.py` | Cole-specific version (kept as reference; build_exam_series.py is canonical) |

### Filter Logic (custom question sets)
- **AND** across types: `--blueprint X --body-system Y` → questions must match both
- **OR** within type: `--body-system X --body-system Y` → questions from either system
- Bracket notation maps to CLI args via the Cowork skill (`custom-question-set.skill`)

### Output Products (always two per run)
Both land in `03_module.3_analyst/custom_question_sets/YYYY-MM-DD/`:
- `QSet_<N>Q_<label>_Exam.docx` — **Exam version**: questions + answer key table
- `QSet_<N>Q_<label>_StudyGuide.docx` — **Study Guide version**: questions + correct answer + explanation + References section

### Encoding Rules (baked into `build_custom_question_set.py`)
- `_ENCODING_FIXES` table (14 entries) handles Symbol-font artifacts (`ï‚£` → `≤` etc.) and double-encoded Latin chars
- `split_explanation_and_refs()` splits ITE explanation fields at `\nRef:` marker
- `parse_references()` handles pipe-separated (newer) and numbered `2)` (older) citation formats
- References rendered as separate section — one paragraph per citation, gray tiny font

### Cowork Skills
- `ite-exam-series.skill` — triggers on resident exam series requests
- `custom-question-set.skill` — triggers on bracket-notation question set requests; includes `references/glossary.md` with canonical term aliases and pool size estimates

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

## Next Steps (as of BATON 070, 2026-05-15)

### Immediate (next session — testing pass)
1. **Run `run_qc.py` end-to-end on the canonical (non-worktree) DB** — verify all 5 artifacts (3 findings JSONs + qc_report.md + fixes.sql) land in `03_module.3_analyst/outputs/corpus_qc/{today}/`.
2. **Spot-check 10 random Tier 1 SQL statements** before applying — verify each one represents the intended fix when copy-pasted into DB Browser.
3. **Apply Tier 1 via the `fix-applier` agent** with `--tier 1 --approved-by-user 1` — should land 1,914 statements (1,797 cache rebuilds + 93 encoding fixes + 24 author fixes). Closes DEFERRED-LAYER-C-CACHE-REBUILD.
4. **Re-run `run_qc.py`** post-apply to confirm cache-rebuild findings drop to ~0.
5. **Investigate ORPHAN_XREF QID-2024-0067 / ART-2073** — likely 5-min fix; uncomment the Tier 2 DELETE if confirmed. Closes DEFERRED-ORPHAN-XREF-QID-2024-0067.
6. **Bug-fix loop** on anything testing surfaces.

### Short-term (this week)
7. **Re-run all 7 resident analyses** — still carrying from BATON 065+066+067; picks up cache rebuild as side effect.
8. **Mac PDF sync** — pull 569 missing PDFs from Windows/gdrive.
9. **Tier 2 review pass** — eyeball 66 commented statements (42 choices_empty + 23 explanation truncation + 1 orphan_xref).
10. **Cross-tier codon dedupe** — 89 ART-IDs in both VC_fail and VC_pass (carry from BATON 067).

### Medium-term
11. **AAFP BRQ extension of corpus-integrity-qc (v2)** — Layer C ports trivially; Layer A ports easily; Layer B is inapplicable (no AAFP critique PDFs) — replace with per-article scalar checks against AAFP-linked rows.
12. Continue 801-article gap closure by source_type buckets (Layer B's UNMATCHED_CITATION findings are the working set).
13. Apply NEJM DevTools pattern to 144 unpaywall Cloudflare-blocked URLs.