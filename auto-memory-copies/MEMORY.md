# .auto-memory/MEMORY.md — Memory Index
Last updated: 2026-05-07 (BATON 067)

## Active Memory Files
- [project_overhaul_state.md](project_overhaul_state.md) — Module state, PDF counts, key numbers, deferred flags, Intelligence 2.0 layer status — updated BATON 067
- [project_current_db_state.md](project_current_db_state.md) — DB table row counts (2,206 articles, 1,639 ITE Qs), schema state; body_system + body_system_merged fully normalized; article_currency complete 2,206; clinical_pathways, intersection_centroid_vec, article_icd10, question_icd10 enriched — all stable BATON 067 (no DB changes)
- [rebuild_structuring_guidelines.md](rebuild_structuring_guidelines.md) — Locked rules and architecture principles
- Project terminology decoder — see `Terms — Decode These First` table in `CLAUDE.md` (no separate glossary.md file exists; CLAUDE.md is the single source of truth for term definitions)

## Session Feedback + Policy Updates
- [feedback_reco_cleanup_closed.md](feedback_reco_cleanup_closed.md) — RECO folder cleanup DONE; never carry forward
- [feedback_js_rule_update.md](feedback_js_rule_update.md) — JS rule relaxed: "Build in whatever language fits; flag if multilingual clutter accumulates"
- [feedback_git_github_desktop.md](feedback_git_github_desktop.md) — Git commits via GitHub Desktop only; never CLI git from Linux sandbox (NTFS index.lock deadlocks). Produce staged-file list + commit message; update CLAUDE.md after user returns hash.

## Practice Q Coverage Fix (BATON 052)
- [DEFERRED-PRACTICE-Q-COVERAGE: Root causes found and fixed](memory/feedback_psychogenic_retired.md) — Psychogenic body system fully retired; 3 root causes resolved

## Bug Fixes (BATON 049)
- **BUG-047-01 FIXED** — ite_parser.py exam_year extraction: now parses from PDF text instead of hardcoded 2025 fallback
- **BUG-047-02 FIXED** — ite_analyzer_v3.py body system normalization: added BODYSYSTEM_PDF_NORM dict + _normalize_body_system() function to handle PDF vs blueprint capitalization inconsistencies
- **BUG-047-03 FIXED** — ite_analyze_v2.py: imports normalize function, applies to body_system_scaled dict, prefers official score from score report when available
- Test validation: Scholl_2022, 2023, 2024, Sarkar_2025, Hopkins_2025 all passing

## Deployments (BATON 051)
- [Module 5 web platform scaffold added](project_overhaul_state.md) — 05_module.5_web/ (Next.js+Supabase+Sanity+Railway) committed by Copilot 2026-04-08; docs updated BATON 051

## Script Refactoring (BATON 054)
- [ite_report_builder_v2.js: 18-edit multi-year resident redesign](feedback_report_builder_redesign_054.md) — Major revision for improved year-over-year rendering; ABFM reference benchmark integration; section 3b temporal aggregation hardened

## Architecture Decisions (BATON 055)
- [ICD-10 Hidden Enrichment Layer](architecture_icd10_hidden_enrichment.md) — ICD-10 codes used as taxonomy-stable scoring layer in practice question matching; invisible to resident reports; taxonomy-stable precision without concept-tag label variance

## Architecture Decisions (BATON 056)
- [Modular Vector Architecture](memory/modular_vector_architecture.md) — 5-dimensional embedding scheme (blueprint labels, body system labels, concept tags, full question, intersection centroids) for semantic+structural matching in Tier 1 practice question retrieval; enables learner ICD-10 profile integration and future ablation studies

## Vector Integration (BATON 057)
- [db_connect.py — immutable URI DB utility](db_connect_utility.md) — Use open_db() for sandbox SQLite queries; immutable=1 avoids journal file errors on NTFS mount

## ITE Report Interpretation Guides (BATON 063)
- **DEFERRED-REPORT-GUIDE CLOSED** — Two interpretation guides written for ITE reports:
  - build_resident_guide.py → ITE_Report_Guide_Resident_v2.docx (action-oriented, gold ACTION callouts for weak areas, resident audience)
  - build_faculty_guide.py → ITE_Report_Guide_Faculty_v2.docx (methodology-focused, DATA SOURCE + LIMITATION callouts, faculty advisor audience)
- **word_doc_defaults.py enhanced:** add_section_header() now supports level 1/2 differentiation (spacing + shading conditional on header level)
- **Rule 14 added to CLAUDE.md:** All Python .docx generation scripts must import and use word_doc_defaults.py (complements Rule 5: no de novo JS for new Word doc code)
- **JS versions also created** (build_resident_guide.js, build_faculty_guide.js) for completeness, but Python versions are canonical per Rule 14
- **M3 script count:** 50 py + 2 js → 52 py + 4 js (added 2 py + 2 js guide builders)
- **DB state:** All counts stable; no schema changes

## Report Builder Improvements + Mac Migration (BATON 062)
- **M3 script enhancements:** ite_analyze_v2.py (body_system_sources provenance tracking, Stage 1.75), ite_analyzer_v3.py (match_top_articles() two-tier personalized/general, linked_qids + selection_basis fields), ite_report_builder_v2.js (5 issues: scoring note, provenance split, consolidated tables, concept fingerprint drugs-only, two-tier reading list with QID glossary)
- **Platform migration:** Project copied from Windows home PC to Mac via external HD; DB + PDFs intact; Mac is now active development machine
- **DB enrichment (pre-existing Windows work):** article_icd10: 3,952 → 4,959 (+1,007); question_icd10: ~5,003 → 5,774 (+771); clinical_pathways: 3,971 → 4,959 (+988); intersection_centroid_vec: 123 → 158 (+35)
- **Git:** Commit 47d6e8e staged, push pending
- **New deferred flag:** DEFERRED-REPORT-GUIDE — write resident and faculty advisor interpretation guides (2 DOCX documents, next session)

## Legacy Analyses Complete + Resident Re-runs (BATON 061)
- **All 7 resident analyses re-run:** Scholl 2022/2023/2024, Sarkar 2025, Hopkins 2025, Pjetergjoka 2024/2025 — complete with Stage 1.75 DB body_system backfill
- **ite_analyze_v2.py Stage 1.75 pipeline:** New permanent DB body_system backfill feature; fetches normalized taxonomy from DB, applies before score rollup
- **ite_analyzer_v3.py pathway_gap_map() fix:** LEFT JOIN corrected (icd10_desc column now included)
- **article_currency complete:** 1,985 → 1,998 rows (includes ART-1987–ART-1999)
- **intersection_centroid_vec verified:** 123 rows, 71 ITE + 52 AAFP blueprintxbody_system centroids
- **DEFERRED-PROGRAM-TREND + DEFERRED-PGY-BENCHMARKS now UNBLOCKED** — all prior blockers cleared

## Normalization + Enrichment Pipeline (BATON 060)
- **body_system fully normalized:** Musculoskeletal rename (48 records), QID-2021-0168 → Respiratory, 376 body_system_merged records synced to post-2024 canonical — apply_body_system_normalization.py
- **DEFERRED-BODY-SYSTEM-MERGED-UPDATE CLOSED** — body_system_merged now correctly mirrors body_system for canonical records; only intentional bridges remain (Psychogenic×38, Patient-Based Systems×4)
- **DEFERRED-CENTROID-REBUILD CLOSED** — intersection_centroid_vec rebuilt (135→123 rows)
- **10 questions recovered + fully enriched** — Steps 1–6 complete (blueprint, body_system, concept tags, ICD-10, vectors, centroids)

## Body System QC Pipeline (BATON 059)
- [body-system-qc skill — complete audit + correction pipeline](project_overhaul_state.md) — 19 new M3 scripts for ITE 2018-2021, 2024-2025 + AAFP 1,221 questions; SVM baseline + Claude classification + review workflow
- **Post-2024 canonical taxonomy locked:** Psychiatric/Behavioral (vs legacy Psychogenic), Sexual and Reproductive, Injuries/Musculoskeletal
- **Files API infrastructure built** — critique_pdf_registry.py tracks 2018-2025 ITE PDFs; extract_critique_refs_v2.py parses citations with parse_legacy() + fallback_citation_scan(); enables ground-truth xref rebuilds
- **Human review queue:** 201 ITE + 129 AAFP questions pending verification before commit; deferred flags: DEFERRED-BODY-SYSTEM-MERGED-UPDATE, DEFERRED-CENTROID-REBUILD, DEFERRED-HUMAN-REVIEW-BODY-SYSTEM

## Phase 2 PDF Acquisition (BATON 065)
- **EXA + Unpaywall batch acquisition:** 281 new PDFs; 208 new articles (ART-1999–ART-2206); +225 qid_art_xref linkages
- **VC_fail 630→879, VC_pass 168→200**
- **Four new M1 maintain scripts:** acquire_missing_citations.py, playwright_auth_downloader.py, browser_pdf_harvester.py, setup_journal_auth.py
- **JAMA/NEJM IP-blocked at Playwright layer** → jama_pending.json output (handed to BATON 066)

## AFP PDF Acquisition + BATON 066 Worktree Merge (BATON 067)
- **AFP gap closed 83 → 11** — 72 articles acquired via aafp_targeted_downloader.py 3-tier cascade (legacy biweekly URL with volume parity + monthly TOC scrape + CrossRef DOI lookup; structured citation_volume/issue/firstpage meta tag validation gate, 100% precision when AAFP exposes the tags)
- **BATON 066 worktree fully merged to main** — 127 PDFs + 8 scripts + 5 state files migrated via robocopy + Move-Item
- **One NEW M1 maintain script:** aafp_targeted_downloader.py (3-tier cascade harvester)
- **One MODIFIED M1 maintain script:** aafp_fill_gaps.py (Playwright expect_download → context.request.get patch + homepage login URL)
- **Eight scripts merged from BATON 066 worktree:** jama_chrome_harvester.py, jama_prep_articlepdf_urls.py, nejm_doi_lookup.py, nejm_build_js_batch.py, nejm_console_script.py, nejm_move_downloads.py, nejm_save_server.py, unpaywall_retry.py
- **Structural cleanup:** _dupe_archive (48) + _corrupted_targeted_run (79) cleared via delete_me_pdfs_b65 staging then permanent deletion
- **.gitignore updated:** M1 maintain state-file patterns (_*.json, _*.txt, _*.csv, _*.log; explicit auth file)
- **Persistent-auth pattern (NEW):** Playwright storage_state via _aafp_auth.json — generalizable to other auth-walled journals (T&F, Wiley, etc.)
- **DEFERRED-MERGE-WORKTREE-TO-MAIN CLOSED**
- **New deferred flags:** DEFERRED-AAFP-HTTP-500 (11 remaining AFP articles via API HTTP 500), DEFERRED-AFP-DATA-QC (metadata spot-check), DEFERRED-CROSS-TIER-CODON-DUPES (verify codon non-duplication across tiers)
- **DB state:** No schema changes; no row-count changes (PDFs only)

## JAMA + NEJM PDF Harvest (BATON 066)
- **127 new PDFs harvested** (in worktree pending merge): JAMA 50/50 + NEJM 76/89
- **DevTools-console paste pattern established** — unblocks browser-auth journals where Playwright/curl are IP-blocked or hit Cloudflare
- **Eight new M1 maintain scripts** (in `01_module.1_warehouse/scripts/maintain/`, all in worktree pending merge): jama_chrome_harvester.py, jama_prep_articlepdf_urls.py, nejm_doi_lookup.py, nejm_build_js_batch.py, nejm_console_script.py, nejm_move_downloads.py, nejm_save_server.py, unpaywall_retry.py
- **DEFERRED-NEJM-PHASE-2 + DEFERRED-JAMA-PHASE-2 CLOSED**
- **New deferred flags:** DEFERRED-MERGE-WORKTREE-TO-MAIN, DEFERRED-UNPAYWALL-CLOUDFLARE (144 OA URLs blocked), DEFERRED-DESHMUKH-2021 (ART-0302 paywalled at tandfonline), DEFERRED-PENDING-LIST-QC (jama_pending.json had wrong URL bug)
- **DB state:** No schema changes; no row-count changes (PDFs only; xref linkage to be done after merge)

## Open Items (BATON 067)
- **DEFERRED-AAFP-HTTP-500** — AAFP search API returning HTTP 500 for 11 remaining AFP articles; needs alternative entry point
- **DEFERRED-AFP-DATA-QC** — AFP-acquired metadata needs spot-check vs articles table
- **DEFERRED-CROSS-TIER-CODON-DUPES** — Verify no codon duplicates across VC_fail/VC_pass after batch acquisition
- **DEFERRED-UNPAYWALL-CLOUDFLARE** — Apply DevTools-console paste pattern to 144 OA URLs blocked by Cloudflare
- **DEFERRED-DESHMUKH-2021** — ART-0302 paywalled at tandfonline; no T&F auth available
- **DEFERRED-PENDING-LIST-QC** — jama_pending.json had wrong URL bug; sweep recommended for any other lists with the same defect
- **DEFERRED-QID-XREF-LIBRARY-GAPS** — ~249 unmatched citations (pre-Phase 2); prioritize by frequency
- **DEFERRED-HUMAN-REVIEW-BODY-SYSTEM** — ~308 holdout questions (179 ITE + 129 AAFP) pending manual verification; applies to 2022-2023 legacy data only
- **DEFERRED-PROGRAM-TREND / DEFERRED-PGY-BENCHMARKS** — Both UNBLOCKED — multi-resident program-level trends; benchmark against 2024 ABFM national reference
- **DEFERRED-YOY-ROBUSTNESS** — Year-over-year section 3b needs more robust implementation; month-by-month trend aggregation logic
- **DEFERRED-RESIDENT-FOLDER-MIGRATION** — Investigate resident_data/ folder state and M5 integration pathway
- **Re-run 7 resident analyses on Mac after git pull** (carry-over from BATON 063)
