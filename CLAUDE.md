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
| Active BATON | `BATON_active_075_20260519_corpus_qc_v1_testing_pass.md` — Corpus-integrity-qc V1 testing pass + DB-write debut. Ran `run_qc.py` end-to-end (first standalone run), fixed 3 substantive bugs in-flight: (1) PROJECT_ROOT off-by-one in all 5 entry-point scripts (`SCRIPT_DIR.parent×5` → `×4`; SKILL.md doc also corrected), (2) Windows cp1252 console crash on `✓` chars (new `setup_utf8_stdout()` helper in utils.py + UTF-8 to 8 open() calls + 3 subprocess.run() calls), (3) A1 ENCODING_ARTIFACT no-op on `choices` JSON column — discovered SQLite *does* interpret `\u` escapes in string literals (despite docs), fixed via new `_sql_json_escape_expr()` building `char(92) || 'uXXXX'` literals. Then: stratified 10-statement spot-check of Tier 1 (9/10 verified clean, 1 caught bug #3), applied 1,914 Tier 1 statements via inline fix-applier workflow (DB backup 172 MB taken pre-apply; atomic BEGIN/COMMIT; 6 verify COUNTs report deltas); re-ran QC → findings dropped from 2,538 to 624; Layer C went from 1,798 to **0**. Investigated lone ORPHAN_XREF (QID-2024-0067 / ART-2073) — turned out the question exists in `2024_critique.pdf` + `2024_MC.pdf` but had been dropped during ingestion; recovered + inserted with primary fields populated (qid/exam_year/blueprint=Acute Care and Diagnosis/body_system=Hematologic/Immune/question_text/choices/correct_letter=B/correct_text/explanation/reference). DB invariants now hold: `sum(citation_count) == COUNT(xref)` (=2,710), `count(articles with citations) == count(distinct article_id in xref)` (=1,982). 3 deferred flags CLOSED (DEFERRED-LAYER-C-CACHE-REBUILD, DEFERRED-ORPHAN-XREF-QID-2024-0067, DEFERRED-V1-ENCODING-CHOICES-JSON-BUG opened+closed same session); 4 NEW (DEFERRED-LAYER-A5-LANGUAGE-INTEGRITY = Claude-API spell check, DEFERRED-LAYER-A6-RENDER-FIDELITY = DOCX-diff against deliverable, DEFERRED-QID-2024-0067-ENRICHMENT = backfill 4 NULL fields, DEFERRED-LAYER-B-UMBRELLA-PROMOTION-REVIEW = eyeball the +1 promoted umbrella). 8 corpus-integrity-qc files MODIFIED (7 scripts/*.py + SKILL.md). No M1/M2/M3/M4/M5 script-count changes. |
| DB articles | 2,206 (+13 from critique PDFs: ART-1987–ART-1999; +208 from acquire_missing_citations.py: ART-2000–ART-2207) |
| DB questions (ITE) | 1,640 (+10 BATON 060 recovery, +1 QID-2024-0067 recovered 2026-05-19 from 2024 critique gap) — blueprint 100% filled — subcategory + topic_label DROPPED — body_system taxonomy normalized 2026-04-16 |
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
| Git branch | `claude/session-075-corpus-qc-v1-pass` (V3.2 feature branch); main → `65754ea` pre-session (BATON 074 merge commit, "Merge pull request #20"). Session commits: `caf66f4` (BATON 075 housekeeping, 22 files) + hash-backfill commit. PR # filled post-push. Worktree state: clean — `git worktree list` shows only project root. |
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

## Session-Housekeeping Skill (V3.2 — project-level)

**Canonical workflow:** `.claude/skills/session-housekeeping/SKILL.md` (12-item sweep).
Use the **project-level** `session-housekeeping` skill, NOT the upstream
`anthropic-skills:session-housekeeping` (11 items, no GitHub sync).

**Item 12 — GitHub syncing (V3.1+).** Claude owns the full git/GitHub
round-trip at end of session: push → open PR → provide review block in chat →
**wait for explicit chat-level authorization** (`merge it` / `approved` / `go`
/ `lgtm` / `ship it`) → run `gh pr merge --merge --delete-branch` → prune
local + remote → verify single-main state → done. The user authorizes in
chat; Claude executes every git/gh command. Never asks the user to click
web-UI buttons or run git commands.

**Merge style — locked to `--merge --delete-branch`.** Squash and rebase are
**banned**. Every BATON pins intra-session commit hashes as part of its audit
trail (e.g. *"Session commit: 02a770f"*). Merge commits preserve those hashes
AND give a clean per-session view via `git log --merges`. Squash destroys the
hashes; rebase loses the session-boundary marker.

**No worktrees (V3.2 — 2026-05-18).** Sessions run directly in the project
root on a feature branch. Start a session: `git switch -c claude/session-<slug>`
from `main` (or stay on `main` for trivial work). End-of-session: push → PR →
authorize → merge → `git checkout main && git pull && git branch -d
claude/session-<slug>`. **No `git worktree` commands ever.** Worktrees were
retired because they (a) caused path auto-detection to break (`run_qc.py`
PROJECT_ROOT caveat), (b) made `gh pr merge --delete-branch` error on local
cleanup (the DEFERRED-V3.2 wrinkle, now obviated), (c) accumulated stale
debris (4 stale worktrees found at start of this session), and (d) the
"parallel branch isolation" benefit doesn't materialize for solo sequential
sessions. If Claude Code's launcher auto-creates a worktree, opt out at
launch — the housekeeping skill expects direct-on-main work from now on.

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

## Next Steps (as of BATON 075, 2026-05-19 — corpus-qc V1 testing pass complete)

### Immediate (next session)
1. **`/board-startup`** to load BATON 075 + verify DB sanity (articles=2206, questions=**1640**, qid_art_xref=2710, single `main` branch, no worktrees).
2. **Backfill QID-2024-0067 enrichment fields** (DEFERRED-QID-2024-0067-ENRICHMENT). Run keyword extraction + `preprocess_concept_tags.py` scoped to single QID. Lightweight.
3. **Verify QID-2024-0067 blueprint + body_system inferences.** Confirm "Acute Care and Diagnosis" + "Hematologic/Immune" are correct for the acute HIV diagnostic question; if not, single UPDATE.
4. **Tier 2 review pass** (optional this session, or defer) — 65 Tier 2 statements in latest `fixes.sql` (42 FORMAT_DRIFT + 23 TRUNCATION_CANDIDATE). User uncomments specific ones to apply, then dispatches `fix-applier --tier 2 --approved-by-user 1`.
5. **Re-run all 7 resident analyses** — still carrying from BATON 065+066+067. Tier 1 cache fixes may shift reading-list output.
6. **Investigate the 8th UMBRELLA article** (the one promoted by Tier 1 citation_count fix) — DEFERRED-LAYER-B-UMBRELLA-PROMOTION-REVIEW.

### Short-term (this week)
7. **Cross-tier codon dedupe** — 89 ART-IDs in both VC_fail and VC_pass.
8. **Mac PDF sync** (only if Mac work resumes) — pull 567 missing PDFs from Windows/gdrive.

### Medium-term (V1.1 + V1.2 corpus-qc work)
9. **Design + build Layer A4 PDF_DIFF and A6 RENDER_FIDELITY together** (DEFERRED-LAYER-A4-PDF-DIFF + DEFERRED-LAYER-A6-RENDER-FIDELITY). Shared PDF/DOCX re-extraction infrastructure. A4 = DB vs. source-PDF drift; A6 = DB vs. deliverable-DOCX drift.
10. **A5 LANGUAGE_INTEGRITY** as separate V1.2 session (DEFERRED-LAYER-A5-LANGUAGE-INTEGRITY). Claude-API spell/typo/language sanity check; curate clinical dictionary first.
11. **AAFP BRQ extension of corpus-integrity-qc (v2)** — Layer C ports trivially; Layer A ports easily; Layer B is inapplicable — replace with per-article scalar checks against AAFP-linked rows.
12. Continue 801-article gap closure by source_type buckets.
13. Apply NEJM DevTools pattern to 144 unpaywall Cloudflare-blocked URLs.