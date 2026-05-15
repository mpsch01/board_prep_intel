# project_overhaul_state.md
Last updated: 2026-05-15 (BATON 068)

## Module State

| Module | Status | Key Info |
|--------|--------|----------|
| M1 Warehouse | Active | Windows canonical: 1,540 ITE/AAFP active-tier PDFs; Mac local: 971 (lags by 569 — DEFERRED-MAC-PDF-SYNC); 8 build + 38 maintain scripts (no script changes BATON 068) |
| M2 Processor | Active | 75 py + 6 js scripts; enrichment pipeline operational |
| M3 Analyst | Active | 55 py + 4 js + 1 json config; ICD-10, pathways, score analysis, article_currency (Layer 2), longitudinal delta, concept fingerprint enrichment, db_connect utility, citation QC, body system audit/correction; report interpretation guides (resident + faculty, BATON 063); practice question system (exam series + custom sets, BATON 064) |
| M4 Sandbox | Active | 1 py (nl_search_validation.py); experiments + agent prototypes |
| M5 Web Platform | Active | 3 py + 31 tsx + 5 sql; Next.js frontend, Supabase backend, Sanity CMS, Railway FastAPI |
| DB | Stable | 2,206 articles, 1,639 ITE Qs, 1,221 AAFP Qs; qid_art_xref 2,710; article_icd10 4,959, question_icd10 5,774, clinical_pathways 4,959, intersection_centroid_vec 158 — no schema changes BATON 068; Mac DB swapped from stale Apr-16 copy (1,998/2,485) to canonical May-6 copy |
| Skills | Active | .claude/skills/corpus-integrity-qc/ NEW BATON 068 (5 files; Layer C functional; A/B/D + coordinator + subagent prompts deferred); replaces buggy article-citation-qc |

## PDF Library State

### ITE (citation_files/ITE/)
| Tier | Windows canonical | Mac local (BATON 068) | Notes |
|------|-------------------|----------------------|-------|
| VC_fail | 1,056 | 628 | Failed VC gate; awaiting enrichment — Mac lags 428 |
| VC_pass | 309 | 168 | Passed VC gate; awaiting enrichment — Mac lags 141 |
| local_lite | 117 | 117 | Enriched; not VC-cited — synced |
| right_click | 58 | 58 | Enriched + VC-cited (top tier) — synced |
| _dupe_archive | 0 | 0 | Cleared BATON 067 |
| _corrupted_targeted_run | 0 | 0 | Cleared BATON 067 |
| **TOTAL active** | **1,540** | **971** | Mac lags Windows by 569 files (DEFERRED-MAC-PDF-SYNC); gitignored content |

### AAFP (citation_files/AAFP/)
| Count | Status |
|-------|--------|
| 15 | Recovered 2026-04-05 (was 0 after fix_ghost.py) |

AAFP ceiling: 3 paywalled (ART-1959, ART-1972, ART-1967)

## Session Notes (BATON 068)

**2026-05-15 — Cowork → Claude Code Migration Validated + Corpus Integrity QC Skill Scaffold**
- **Migration:** Cowork → Claude Code migration validated; adopted Claude Code as primary development workflow on Mac
- **Built corpus-integrity-qc skill scaffold** (replaces buggy article-citation-qc):
  - 4-layer architecture (text fidelity / citation linkage / structural integrity / report + remediation) with parallel agent dispatch
  - 5 files added under `.claude/skills/corpus-integrity-qc/`: SKILL.md, references/qc_rules.md, references/fix_tiers.md, scripts/utils.py, scripts/layer_c_structural.py
  - **Layer C functional** and validated against canonical DB
  - **Deferred:** Layer A + Layer B + Layer D + coordinator + subagent prompts (DEFERRED-CORPUS-QC-LAYERS-AB-D)
  - **Why:** article-citation-qc had confirmed dict-overwrite bug (`run_citation_qc.py` lines 207–210) producing ~932 false-positive QID_MISMATCH findings against multi-reference `qid_art_xref` table
- **DB swap (no schema/row changes; canonical state restored):**
  - Mac DB at `00_database/db/ite_intelligence.db` was 3 weeks stale (Apr 16 copy: 1,998 articles / 2,485 xref)
  - User staged canonical from gdrive at `00a_database/db/`
  - Swapped: old → `00_database/db/_archive_/ite_intelligence_stale_20260416.db`; new → canonical location
  - Counts now match BATON 067: 2,206 articles, 2,710 qid_art_xref
- **Layer C smoke test results:** 1,798 findings — 1,797 derived-cache drift Tier 1 fixes pending Layer D (mostly 208 ZERO_CITATION_LINKED from BATON-065 articles never having cache initialized); 1 NEW ORPHAN_XREF bug at QID-2024-0067/ART-2073 (QID does not exist in questions table)
- **DB state:** No schema changes; no row-count changes (DB swap restored canonical state)
- **New deferred flags:**
  - DEFERRED-CORPUS-QC-LAYERS-AB-D — Build Layer A + B + D + coordinator + subagent prompts
  - DEFERRED-LAYER-C-CACHE-REBUILD — 1,797 Tier-1 cache-rebuild SQL fixes pending Layer D
  - DEFERRED-ORPHAN-XREF-QID-2024-0067 — QID-2024-0067/ART-2073 references non-existent QID
  - DEFERRED-MAC-PDF-SYNC — Mac lags Windows by 569 PDFs (gitignored)
  - DEFERRED-LOCKED-RULE-8-UPDATE — Rule 8 ("Git via Desktop Commander") is Windows-specific; needs broadening for Mac/Claude Code
- **Next:** Build Layer A + B + D + coordinator; apply Tier-1 cache rebuilds; fix orphan xref; sync Mac PDFs from Windows canonical; update Rule 8 in CLAUDE.md

## Session Notes (BATON 067)

**2026-05-07 — AFP PDF Acquisition: 72 Articles Closed + BATON 066 Worktree Merge**
- **AFP harvest:** 72/83 missing AFP articles acquired via aafp_targeted_downloader.py 3-tier cascade
  - Tier 1: legacy biweekly URL with volume parity check
  - Tier 2: monthly TOC scrape
  - Tier 3: CrossRef DOI lookup
  - Validation gate: structured citation_volume/issue/firstpage meta tag (100% precision when AAFP exposes the tags)
  - Gap closed: 83 → 11 missing
- **BATON 066 worktree merged to main:** 127 PDFs + 8 scripts + 5 state files migrated FROM modest-merkle-df0121 worktree TO main repo via robocopy + Move-Item
- **One NEW M1 maintain script:** aafp_targeted_downloader.py (3-tier cascade harvester)
- **One MODIFIED M1 maintain script:** aafp_fill_gaps.py (Playwright expect_download → context.request.get patch + homepage login URL)
- **One NEW gitignored diagnostic:** _aafp_search_dom_probe.py
- **Eight scripts merged from BATON 066 worktree:** jama_chrome_harvester.py, jama_prep_articlepdf_urls.py, nejm_doi_lookup.py, nejm_build_js_batch.py, nejm_console_script.py, nejm_move_downloads.py, nejm_save_server.py, unpaywall_retry.py
- **M1 maintain script count:** 30 → 38 (+9 net new — counted via underlying state, including pre-merge worktree carryover from BATON 066)
- **Structural cleanup:**
  - citation_files/ITE/_dupe_archive/: emptied (48 files moved to delete_me_pdfs_b65 then deleted)
  - citation_files/ITE/_corrupted_targeted_run/: emptied (79 files moved to delete_me_pdfs_b65 then deleted)
  - delete_me_pdfs_b65/ folder created at project root, then permanently deleted by user
- **.gitignore updated:** Added M1 maintain state-file patterns (_*.json, _*.txt, _*.csv, _*.log; explicit auth file)
- **DB state:** No schema changes; no row-count changes (PDFs only; xref linkage to articles already linked from BATON 065 catalog)
- **DEFERRED-MERGE-WORKTREE-TO-MAIN CLOSED**
- **New deferred flags:**
  - DEFERRED-AAFP-HTTP-500 — AAFP search API returning HTTP 500 for 11 remaining articles; needs alternative entry point
  - DEFERRED-AFP-DATA-QC — AFP-acquired metadata needs spot-check vs articles table
  - DEFERRED-CROSS-TIER-CODON-DUPES — Verify no codon duplicates across VC_fail/VC_pass after batch acquisition
- **New plugins/capabilities:**
  - Persistent-auth pattern (Playwright storage_state via _aafp_auth.json) generalizable to other auth-walled journals
  - URL-pattern recovery via structured citation_volume/issue/firstpage meta tags as alternative to fuzzy title matching (more reliable, 100% precision when exposed)
- **Next:** Apply NEJM DevTools pattern to 144 Cloudflare-blocked unpaywall URLs; spot-check pending list integrity (DEFERRED-PENDING-LIST-QC); re-run resident analyses on Mac after git pull

## Session Notes (BATON 066)

**2026-05-07 — JAMA + NEJM PDF Harvest Complete**
- **127 new PDFs harvested via DevTools-console pattern** (in worktree pending merge to main path)
  - JAMA: 50/50 articles harvested (jama_chrome_harvester.py — Chrome-driven fetcher proven 100% success)
  - NEJM: 76/89 articles harvested (nejm_doi_lookup.py + nejm_console_script.py — Crossref DOI resolver + DevTools-paste batch download)
- **Eight new M1 maintain scripts** (in `01_module.1_warehouse/scripts/maintain/`, all pending merge):
  - jama_chrome_harvester.py — Chrome-driven JAMA fetcher (50/50 proven)
  - jama_prep_articlepdf_urls.py — articlepdf URL pre-builder
  - nejm_doi_lookup.py — Crossref DOI resolver (76/89)
  - nejm_build_js_batch.py — generate JS for batch downloads
  - nejm_console_script.py — DevTools-paste script generator
  - nejm_move_downloads.py — Downloads → tier mover
  - nejm_save_server.py — local CORS server (failed approach, kept for reference)
  - unpaywall_retry.py — partial OA retry via curl-cffi
- **Methodology breakthrough:** DevTools-console paste pattern unblocks browser-auth journals where Playwright/curl are IP-blocked or hit Cloudflare; user pastes generated JS into DevTools console while signed in
- **DEFERRED-NEJM-PHASE-2 + DEFERRED-JAMA-PHASE-2 CLOSED**
- **DB state:** No schema changes; no row-count changes (PDFs only; xref linkage to be done after merge)
- **M1 maintain script count:** 30 → 36 (+8 new) post-merge — currently in worktree
- **Deferred flags NEW:**
  - DEFERRED-MERGE-WORKTREE-TO-MAIN — 127 PDFs + 8 scripts physically in worktree, need merge to main repo path (Step 1 next session)
  - DEFERRED-UNPAYWALL-CLOUDFLARE — 144 OA URLs blocked by Cloudflare, need DevTools-paste pattern
  - DEFERRED-DESHMUKH-2021 — ART-0302 paywalled at tandfonline, no T&F auth
  - DEFERRED-PENDING-LIST-QC — jama_pending.json had wrong URL bug, sweep recommended
- **Next:** Merge worktree to main; run xref linkage on 127 new PDFs; apply DevTools-paste pattern to unpaywall Cloudflare blockers

## Session Notes (BATON 065)

**2026-05-06 — Phase 2 PDF Acquisition (EXA + Unpaywall)**
- **Articles acquired:** acquire_missing_citations.py batch run — 208 new articles (ART-1999–ART-2206)
- **PDF downloads:** 281 new PDFs via exa_pdf_downloader + unpaywall batch integration
  - VC_fail: 630 → 879 (+249)
  - VC_pass: 168 → 200 (+32)
  - local_lite, right_click, AAFP: unchanged
- **JAMA/NEJM blocked:** playwright_auth_downloader.py created but IP-blocked; jama_pending.json output for Claude Code handoff
- **Four new M1 maintain scripts:**
  - acquire_missing_citations.py — batch article import + xref linkage
  - playwright_auth_downloader.py — journal auth + download (blocked)
  - browser_pdf_harvester.py — browser-based paywalled journal harvester
  - setup_journal_auth.py — journal authentication setup utility
- **DB state:** articles 1,998 → 2,206; qid_art_xref 2,485 → 2,710 (+225); article_currency 1,998 → 2,206 (mirrors articles)
- **Deferred flag update:** DEFERRED-QID-XREF-LIBRARY-GAPS — partially addressed — 50 JAMA pending (jama_pending.json), ~65 NEJM pending (IP block)
- **M1 maintain script count:** 26 → 30 (+4 new)
- **Next:** JAMA/NEJM access strategy; consider user-supplied credentials or alternative acquisition pathways

## Session Notes (BATON 064)

**2026-05-05 – Practice Question System Complete**
- **Three new M3 scripts:**
  - build_cole_exam_series.py — Cole-specific exam series generator; merges original 20 report questions into 200-question pool, clips least-fitting to maintain count
  - build_exam_series.py — Generalized exam series generator (CLI: --resident-dir, --resident-name, --pgy, --num-exams, --questions, --seed); auto-discovers analysis JSON; same merge-inject logic
  - build_custom_question_set.py — Content-addressable question set generator; AND/OR filter logic (blueprint + body_system); produces Exam version + Study Guide version DOCX; reference block parsed and rendered as separate "References" section; encoding fix table (14 entries); QID in footer metadata
- **ite_analyzer_v3.py modified:** Symbol-font dot-leader encoding clean added at export_analysis() write time; uses chr(0xF02E) pattern
- **Two Cowork skills packaged:** ite-exam-series.skill + custom-question-set.skill (with glossary reference + evals)
- **Lexicon:** "Exam version" and "Study Guide version" added to user_vocabulary.md memory
- **M3 script count:** 52 py + 4 js → 55 py + 4 js
- **DB state:** All tables stable; no changes this session
- **Deferred:** DEFERRED-PGY-BENCHMARKS + DEFERRED-PROGRAM-TREND still UNBLOCKED; DEFERRED-QID-XREF-LIBRARY-GAPS still active; re-running 7 resident analyses still pending from BATON 063

## Session Notes (BATON 063)

**2026-04-29 – ITE Report Interpretation Guides Complete**
- **Two interpretation guides written (DEFERRED-REPORT-GUIDE CLOSED):**
  - build_resident_guide.py → ITE_Report_Guide_Resident_v2.docx (action-oriented narrative for trainees; gold ACTION callouts for weak areas; section-by-section guidance)
  - build_faculty_guide.py → ITE_Report_Guide_Faculty_v2.docx (methodology-focused narrative for advisors; DATA SOURCE + LIMITATION callouts; coaching framework + red flags)
- **word_doc_defaults.py enhancement:** add_section_header() now differentiates level 1 vs level 2 headers (spacing + shading conditional on level parameter)
- **Rule 14 added to CLAUDE.md:** All Python .docx generation scripts must `from word_doc_defaults import *` and use provided helpers (St. Luke's palette, Aptos font, header functions)
- **JS versions created** (build_resident_guide.js, build_faculty_guide.js) but Python canonical per Rule 14
- **M3 script count:** 50 py + 2 js → 52 py + 4 js
- **DB state:** All tables stable; no changes this session
- **Next:** Re-run resident analyses on Mac after git pull to pick up Issues 1-5; DEFERRED-QID-XREF-LIBRARY-GAPS (249 unmatched citations) remains active

## Session Notes (BATON 062)

**2026-04-29 – Report Builder Issues 1-5 Complete + Mac Migration**
- **M3 script improvements (3 files modified):**
  - ite_analyze_v2.py: Added body_system_sources provenance tracking (Stage 1.75 continues)
  - ite_analyzer_v3.py: Rewrote match_top_articles() to two-tier (personalized/general); added linked_qids + selection_basis fields on articles
  - ite_report_builder_v2.js: Implemented 5 issues: scoring note, body_system provenance split, consolidated tables (Prior% | N/T% | Δ | SEM), concept fingerprint drugs-only filter, two-tier reading list with QID glossary
- **Platform migration:** Project copied from Windows home PC to Mac via external HD; DB and PDFs intact; Mac is now active development machine
- **DB enrichment (pre-existing Windows PC work):** article_icd10 3,952 → 4,959 (+1,007); question_icd10 ~5,003 → 5,774 (+771); clinical_pathways 3,971 → 4,959 (+988); intersection_centroid_vec 123 → 158 (+35)
- **Git status:** Commit 47d6e8e staged; push pending from GitHub Desktop
- **New deferred flag:** DEFERRED-REPORT-GUIDE (write resident + faculty interpretation guides, 2 DOCX documents; next session)
- **No DB schema changes; no new questions or articles**

## Session Notes (BATON 061)

**2026-04-16 – Legacy Body System Analyses Complete + All Resident Re-runs**
- **All 7 resident analyses re-run:** Scholl 2022/2023/2024, Sarkar 2025, Hopkins 2025, Pjetergjoka 2024/2025 — all complete with Stage 1.75 DB body_system backfill
- **article_currency updated:** 1,985 → 1,998 rows (100% complete; includes ART-1987–ART-1999 from critique rebuild)
- **ite_analyze_v2.py enhancement:** Stage 1.75 DB body_system backfill new permanent pipeline feature; fetches normalized body_system from DB, applies before score rollup
- **ite_analyzer_v3.py fix:** pathway_gap_map() LEFT JOIN corrected (icd10_desc column now included; resolves gap analysis rendering)
- **intersection_centroid_vec verified:** 123 rows complete, 71 ITE + 52 AAFP blueprint×body_system centroids
- **Deferred flags status:** DEFERRED-HUMAN-REVIEW-BODY-SYSTEM still active (~308 holdouts); DEFERRED-PGY-BENCHMARKS + DEFERRED-PROGRAM-TREND now fully UNBLOCKED
- **No DB schema changes; resident reports ready for distribution**

## Session Notes (BATON 060)

**2026-04-16 – Enrichment Pipeline Complete + Body System Normalization**
- **Recovered question enrichment:** 10 questions recovered and enriched through full pipeline (Steps 1-6 completed)
- **Body system corrections applied:** 22 holdout corrections for 2024-2025 deprecated labels (legacy Psychogenic → Psychiatric/Behavioral, etc.)
- **Body system normalization script:** apply_body_system_normalization.py fixed Musculoskeletal (48 QIDs), corrected QID-2021-0168, synced 376 body_system_merged records to post-2024 canonical taxonomy
- **Deferred flags CLOSED:** 
  - DEFERRED-BODY-SYSTEM-MERGED-UPDATE ✅ (body_system_merged flipped to forward mapping)
  - DEFERRED-CENTROID-REBUILD ✅ (intersection_centroid_vec rebuilt: 135 → 123 rows, 71 ITE + 52 AAFP blueprintxbody_system centroids)
- **DB state:** No new rows; field corrections only (body_system normalized for 2018-2021/2024-2025 ITE + all AAFP)
- **Script additions:** 10 new M3 scripts (audit_blueprint_by_year.py, audit_holdout_body_system.py, audit_holdout_merged.py, audit_holdout_both_axes.py, apply_holdout_body_system_corrections.py, audit_article_icd10_drop.py, apply_body_system_normalization.py, enrich_recovered_questions.py, recover_missing_questions.py, apply_recovered_questions.py)
- **Model updates:** claude-sonnet-4-6 deployed in preprocess_concept_tags.py, enrich_ite_questions.py, prompt_builder.py
- **M3 py script count:** 39 → 50 (+10 new)
- **Deferred flags NEW:** DEFERRED-PGY-BENCHMARKS (UNBLOCKED — centroid rebuild complete)

## Session Notes (BATON 059)

**2026-04-15 – Body System QC Pipeline Complete**
- **Full pipeline built:** 19 new M3 scripts created (extract_score_report_labels.py through extract_critique_refs_v2.py)
- **QC Coverage:** ITE questions 2018-2021, 2024-2025 + all 1,221 AAFP questions
- **Skills created:** body-system-qc (full audit + correction pipeline), article-citation-qc updated
- **Methodology directory:** methodology_scout/ created with 1 doc
- **Human review queue:** 201 ITE + 129 AAFP questions pending manual verification (canonical taxonomy: Psychiatric/Behavioral, Sexual and Reproductive, Injuries/Musculoskeletal)
- **Deferred flags:** DEFERRED-AAFP-BODY-SYSTEM-AUDIT CLOSED; NEW: DEFERRED-BODY-SYSTEM-MERGED-UPDATE, DEFERRED-CENTROID-REBUILD, DEFERRED-HUMAN-REVIEW-BODY-SYSTEM
- **M3 py script count:** 20 → 39 (+19 new)

## Session Notes (BATON 058)

**2026-04-15 – Citation QC Rebuild & Article Additions**
- **ITE critique ground-truth rebuild:** extract_ite_critique_refs.py modified with parse_legacy() for 2018-2023 Ref: format, fallback_citation_scan() for parser-missed items, overwrite message
- **QC audit complete:** generate_citation_sql.py created; generates full qid_art_xref rebuild SQL from staging JSONs; pdf_lookup_patch.py for direct PDF lookup SQL
- **Article additions:** add_missing_articles.py added 13 new articles (ART-1987–ART-1999) from 2024-2025 QC outputs; full xref links inserted
- **M3 outputs:** new article_qc/ folder created with qc_results.json, article_qc_report.md, article_qc_fixes.sql, pdf_lookup_patch.sql, add_missing_articles.sql
- **Skill created:** article-citation-qc skill (citation QC workflow) tested at 100% pass rate vs 0% baseline in evals
- **DB updates:** articles 1,985 → 1,998 (+13); qid_art_xref 2,470 → 2,485 (rebuilt from critique ground truth)
- **M3 py script count:** 17 → 20 (+3 new: generate_citation_sql.py, pdf_lookup_patch.py, add_missing_articles.py)
- **Deferred flags CLOSED:** DEFERRED-AAFP-BODY-SYSTEM-AUDIT, DEFERRED-KNOWN-DRUGS-EXPANSION, DEFERRED-QID-XREF-LIBRARY-GAPS (NEW-249 unmatched citations; 2024: 20 QIDs; 2025: 33 QIDs missing)

## Session Notes (BATON 057)

**2026-04-15 — Vector Integration, Unified Practice Questions Table, DB Utility**
- **ite_analyzer_v3.py enhancements:** 3 new vector functions added (_build_concept_profile, _centroid_dim_boost, _apply_concept_vec_bonus), 3 constants added for concept weighting, 3 integration points in match_practice_questions_v3() wired to TIER 1 retrieval
- **ite_report_builder_v2.js unification:** removed singleQs/crossQs split, implemented unified practice questions table with PURPLE color coding, added targetingColor() helper, description paragraph rendering, accurate weak area count
- **db_connect.py NEW UTILITY:** SQLite immutable=1 URI utility for sandbox queries; prevents journal file errors on NTFS mounts; added to M3 scripts/
- **Deferred flags CLOSED:** DEFERRED-VECTOR-TIER1-REWRITE (implemented), DEFERRED-PRACTICE-Q-TWO-TABLE (superseded by unified table)
- **New deferred flags:** DEFERRED-BODY-SYSTEM-MERGED-UPDATE, DEFERRED-CENTROID-REBUILD, DEFERRED-HUMAN-REVIEW-BODY-SYSTEM (see BATON 059 for details)
- M3 py script count: 16 → 17 (db_connect.py added)

## Session Notes (BATON 056)

**2026-04-14 — Resident Reorg & Modular Vector Build**
- **Resident data reorganization:** inputs/outputs folder structure created for all 4 residents; stale docs moved to delete_me/
- **ite_parser.py enhancements:** password support added (_find_pdf_password + _open_pdf methods)
- **ite_analyzer_v3.py fixes (12 total):** reading list personalization refinements, KNOWN_DRUGS constant added, prednisone synonym mapping
- **ite_report_builder_v2.js fixes (6 total):** trend table removed, zone label removed, guidelines table removed
- **compute_embeddings.py updates:** text builders updated (blueprint added to ITE, blueprint+body_system+concept_tags to AAFP), --rebuild flag added, BLOB parallel tables introduced
- **New M1 build scripts:** 
  - build_modular_vectors.py — blueprint/body_system label embeddings + concept_tag embeddings
  - build_intersection_centroids.py — local centroid computation for Tier 1 matching
- **New DB tables (6 total):** question_full_vec, aafp_question_full_vec, blueprint_label_vec, bodysystem_label_vec, question_concepttag_vec, intersection_centroid_vec
- **All 6 new vector tables populated and verified**
- M1 build script count: 6 → 8 (+2 new)


## Deferred Flags

| Flag | Status | Description |
|------|--------|-------------|
| DEFERRED-CORPUS-QC-LAYERS-AB-D | NEW/OPEN | Build Layer A + B + D + coordinator + subagent prompts for corpus-integrity-qc skill (Layer C functional BATON 068) |
| DEFERRED-LAYER-C-CACHE-REBUILD | NEW/OPEN | 1,797 Tier-1 derived-cache rebuild SQL fixes pending Layer D rendering (BATON 068) |
| DEFERRED-ORPHAN-XREF-QID-2024-0067 | NEW/OPEN | qid_art_xref row links QID-2024-0067 / ART-2073, but QID-2024-0067 not present in questions table (BATON 068) |
| DEFERRED-MAC-PDF-SYNC | NEW/OPEN | Mac local citation_files/ITE/ lags Windows canonical by 569 PDFs (gitignored content; needs external sync) (BATON 068) |
| DEFERRED-LOCKED-RULE-8-UPDATE | NEW/OPEN | CLAUDE.md Rule 8 ("Git via Desktop Commander") is Windows-specific; needs broadening to cover Mac/Claude Code native git (BATON 068) |
| DEFERRED-AAFP-HTTP-500 | OPEN | AAFP search API returning HTTP 500 for 11 remaining AFP articles; needs alternative entry point (BATON 067) |
| DEFERRED-AFP-DATA-QC | NEW/OPEN | AFP-acquired metadata needs spot-check vs articles table (BATON 067) |
| DEFERRED-CROSS-TIER-CODON-DUPES | NEW/OPEN | Verify no codon duplicates across VC_fail/VC_pass after batch acquisition (BATON 067) |
| DEFERRED-MERGE-WORKTREE-TO-MAIN | ✅ CLOSED | Resolved BATON 067 — 127 PDFs + 8 scripts + 5 state files migrated from worktree to main via robocopy + Move-Item |
| DEFERRED-UNPAYWALL-CLOUDFLARE | OPEN | 144 OA URLs blocked by Cloudflare; apply DevTools-console paste pattern (proven on JAMA/NEJM) (BATON 066) |
| DEFERRED-DESHMUKH-2021 | OPEN | ART-0302 paywalled at tandfonline; no T&F auth available (BATON 066) |
| DEFERRED-PENDING-LIST-QC | OPEN | jama_pending.json had wrong URL bug; sweep recommended for any other lists with the same defect (BATON 066) |
| DEFERRED-NEJM-PHASE-2 | ✅ CLOSED | Resolved BATON 066 — 76/89 NEJM PDFs harvested via Crossref DOI + DevTools-console paste |
| DEFERRED-JAMA-PHASE-2 | ✅ CLOSED | Resolved BATON 066 — 50/50 JAMA PDFs harvested via jama_chrome_harvester.py |
| DEFERRED-REPORT-GUIDE | ✅ CLOSED | Write resident and faculty advisor interpretation guides for the ITE report (2 DOCX documents) — completed BATON 063 |
| DEFERRED-YOY-ROBUSTNESS | ACTIVE | Year-over-year section 3b needs more robust implementation; month-by-month trend aggregation logic (BATON 050) |
| DEFERRED-PROGRAM-TREND | UNBLOCKED | Require program-level trend analysis across multiple residents; benchmark against 2024 ABFM national reference (abfm_reference_2024.json); all blockers cleared (BATON 061) |
| DEFERRED-RESIDENT-FOLDER-MIGRATION | ACTIVE | Investigate resident_data/ folder state and migration strategy to M5 platform |
| DEFERRED-VECTOR-TIER1-REWRITE | ✅ CLOSED | Implemented in BATON 057 — 3 new vector functions + 3 integration points in match_practice_questions_v3() |
| DEFERRED-PRACTICE-Q-TWO-TABLE | ✅ CLOSED | Superseded by unified practice questions table in BATON 057 (removed singleQs/crossQs split) |
| DEFERRED-AAFP-BODY-SYSTEM-AUDIT | ✅ CLOSED | AAFP body_system fields corrected (BATON 059) |
| DEFERRED-BODY-SYSTEM-MERGED-UPDATE | ✅ CLOSED | body_system_merged mapping flipped to post-2024 canonical (Psychiatric/Behavioral, Sexual and Reproductive, Injuries/Musculoskeletal) for 2018-2021 legacy data — completed BATON 060 |
| DEFERRED-CENTROID-REBUILD | ✅ CLOSED | intersection_centroid_vec rebuilt after body_system field corrections (135 → 123 rows); completed BATON 060 |
| DEFERRED-HUMAN-REVIEW-BODY-SYSTEM | ACTIVE | ~308 holdout questions (179 ITE + 129 AAFP) pending manual verification; applies to 2022-2023 legacy data only (2024-2025 + all AAFP normalized BATON 060) |
| DEFERRED-KNOWN-DRUGS-EXPANSION | ✅ CLOSED | Drugs still appearing in top diagnoses table — completed BATON 058 |
| DEFERRED-QID-XREF-LIBRARY-GAPS | ACTIVE | ~249 unmatched citations (pre-Phase 2); prioritize by frequency; partially addressed BATON 065 (+225 xrefs from new articles) |
| DEFERRED-SCHOLL-OLD-FORMAT | NEW | Scholl 2022/2023 use old ABFM taxonomy (no canonical mapping); Stage 1.75 DB backfill now handles transparently; body_system_merged provides forward mapping |
| DEFERRED-A | ARCHIVED | 37 ITE manual PDFs — permanent ceiling (subscription-only) |
| DEFERRED-AAFP-PAYWALL | ACTIVE | 3 AAFP articles paywalled (PMC not_oa): ART-1959 Binic_2011, ART-1972 Byington_2012, ART-1967 Verbalis_2007 |
| DEFERRED-PRACTICE-Q-COVERAGE | ✅ CLOSED | Practice question 0-question warnings for some body systems (Foundations, Preventive, Cardiovascular, Respiratory, Sexual-Reproductive, Psychiatric, Behavioral) — qid_art_xref tagging coverage gap (BATON 050) |
| DEFERRED-F | ✅ CLOSED | Intelligence 2.0 Layer 2 complete — article_currency built (1,998 rows complete BATON 061) |
| DEFERRED-H | CLOSED | Legacy non-codon PDFs confirmed duplicates |
| DEFERRED-I | LOW PRI | unpaywall_scanner --from-csv extension |
| DEFERRED-J | CLOSED | exa-research-search Phase 2 completed |
| DEFERRED-L2-REVIEW | LOW PRI | Optional human review of 169 updated + 106 check_needed article_currency rows (use title_signals cross-reference) |
| DEFERRED-PGY-BENCHMARKS | UNBLOCKED | ABFM embeds PGY mean + SD in score report PDF; ite_parser.py parse_score_report() extracts; all blockers cleared for multi-year trend analysis (BATON 061) |

## Intelligence 2.0 Status
- Layer 1 (ICD-10): Complete — article_icd10 4,959 rows, question_icd10 5,774 rows (BATON 062 enrichment integrated)
- Layer 2 (PubMed currency): ✅ COMPLETE — article_currency 2,206 rows (mirrors articles after BATON 065 acquisition); status enum (current/updated/check_needed/not_indexed); title_signals column (JSON array)
- Layer 3 (Clinical pathways): Complete — clinical_pathways 4,959 rows (BATON 062); ite_analyzer_v3.py pathway_gap_map() LEFT JOIN fixed BATON 061
- Layer 4 (Trends): Partial — trend CSV files in readable_db_files/; DEFERRED-PROGRAM-TREND now unblocked for multi-resident rollup; not advanced this session

## Plugins & New Capabilities (BATON 068)
- **corpus-integrity-qc skill (scaffolded)** — `.claude/skills/corpus-integrity-qc/` — 4-layer ITE corpus audit skill replacing buggy article-citation-qc. Layer C (structural integrity: qid_list / citation_count / exam_years / unique_years cache drift; orphan xref rows) functional and validated. Layers A (text fidelity), B (citation linkage, multi-ref-aware set-containment), D (tiered SQL remediation), and coordinator + subagent prompts deferred. v1 scope: ITE only; AAFP BRQ deferred to v2.
- **Claude Code adopted as primary workflow** — Mac native development via Claude Code CLI; Cowork still available but no longer the daily driver.

## Plugins & New Capabilities (BATON 067)
- **Persistent-auth pattern** — Playwright storage_state via `_aafp_auth.json` reused across script invocations; generalizable to other auth-walled journals (T&F, Wiley, etc.). Sign-in once, persist storage_state, run multiple harvests against authenticated session without re-login.
- **URL-pattern recovery via structured citation meta tags** — citation_volume/issue/firstpage meta tag validation as alternative to fuzzy title matching. 100% precision when AAFP exposes the tags; reduces false-positive matches from title-similarity-only matchers. Pattern applies to any journal site that exposes Highwire-style citation_* meta tags.

## Plugins & New Capabilities (BATON 049)
- **ite-score-analyzer v1.0.0** — ITE score analysis plugin built in `skills_abilities/ite-score-analyzer-v2/`
  - Four skills: analyze-ite (core report parsing), cohort-compare, ite-lookup, study-plan
  - parse_score_report() added to ite_parser.py (longitudinal delta support, Stage 2.5 pipeline)
  - report_config.json analytics configuration created
- **session-housekeeping agent templates** — Agents for baton-writer, index-memory-writer, manifest-writer created in .claude/skills/session-housekeeping/agents/; facilitate repeatable BATON and memory updates
- **Bugs FIXED (BATON 049):**
  - ✅ BUG-047-01: ite_parser.py — exam_year now extracted from PDF text (not hardcoded 2025 fallback)
  - ✅ BUG-047-02: ite_analyzer_v3.py — added BODYSYSTEM_PDF_NORM alias dict + _normalize_body_system() function for body system name normalization (handles PDF capitalization vs blueprint inconsistencies)
  - ✅ BUG-047-03: ite_analyze_v2.py — imports _normalize_body_system, applies it to body_system_scaled dict, uses official score from score report when available
  - Test reports validated: Scholl_2022, Scholl_2023, Scholl_2024, Sarkar_2025, Hopkins_2025
