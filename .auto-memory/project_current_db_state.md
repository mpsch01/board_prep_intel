# project_current_db_state.md
Last verified: 2026-05-19 (BATON 077)

## DB Changes (BATON 077)
**3 write workflows** this session, all backed up, all invariants preserved (articles=2,206; questions=1,640; qid_art_xref=2,710; sum_citation_count=2,710; distinct_xref_article_ids=1,982). Row counts on all tracked tables UNCHANGED — only column values updated.

| # | Workflow | Targets | DB column updates | Backup file |
|---|----------|---------|-------------------|-------------|
| 1 | Q17 stem recovery | QID-2022-0097 (truncated stem restored from 2022_MC.pdf p.34) | `question_text` (1, 468→646 chars) | `pre_q17_fix_2026-05-19-212808.bak` |
| 2 | Encoding cleanup (dot-leader `ï€®`→`": "` + `Ã?` family ×äóçíáïø) | 34 questions | `question_text` (24) + `explanation` (11) + `choices` (1, JSON-aware) | `pre_encoding_fix_2026-05-19-220232.bak` |
| 3 | QID-2024-0017 blueprint correction (per ABFM tie-breaker) | QID-2024-0017 | `blueprint` (`Acute Care and Diagnosis`→`Chronic Care Management`) | `pre_q2017_blueprint_2026-05-19-222051.bak` |

### Post-session fidelity metrics (all at 0)

| Metric | Pre-BATON-077 | Post |
|---|---|---|
| residual dot-leader `ï€®` | 14 Q / 2,618 triplets | **0** |
| residual `Ã—` (double-encoded) | 8 Q | **0** |
| blueprint disagreements (across all 7 resident reports) | old-fmt ~70% + 1 new-fmt | **0** |

### Notes
- Blueprint is now **DB-authoritative** (Option C, Stage 1.8 in `ite_analyze_v2.py`) — both the resident analysis and the custom-question-set skill read blueprint from the DB (single source of truth). ABFM published placement is the tie-breaker for conflicts.
- `parse_blueprint` now reads all pages (Fix #1) — resident-PDF parsing no longer drops legacy 2-page items. (This is a parser fix, not a DB change, but it changes what enters the analysis for 2018–2023.)
- 9 DB backups now in `00_database/db/` (~1.5 GB). Prune the BATON-075/076 ones next session.
- `Patient-Based Systems` old-taxonomy `body_system` label still present in 2018–2023 questions (DEFERRED-PATIENT-BASED-SYSTEMS-RESIDUAL) — not touched this session.

---

## DB Changes (BATON 076)
**8 distinct write workflows** this session, all backed up, all BATON 075 invariants preserved (articles=2,206; questions=1,640; qid_art_xref=2,710; sum_citation_count=2,710; distinct_xref_article_ids=1,982). Row counts on all 13 tracked tables UNCHANGED — only column values updated.

| # | Workflow | Targets | DB column updates | Backup file |
|---|----------|---------|-------------------|-------------|
| 1 | A3 choices_empty re-extraction | 42 QIDs (27 OK 5-of-5 + 15 PARTIAL_4OF5) | `choices` + `correct_text` | `pre_a3_2026-05-19-063039.bak` |
| 2 | TF-IDF keyword refresh + concept_tags backfill | All 1,640 ITE questions (keywords) + QID-2024-0067 (concept_tags via Sonnet 4.6) | `stem_keywords` + `explanation_keywords` + `all_keywords` (1,640) + `concept_tags` (1) | `pre_qid_0067_enrich_2026-05-19-063554.bak` |
| 3 | question_text cleanup + 2 choice fixes | 42 QIDs (qtext) + QID-2020-0162 D + QID-2021-0017 A | `question_text` (42) + `choices` (2) | `pre_qtext_cleanup_2026-05-19-065741.bak` |
| 4 | 2 subscript orphan fixes in PARTIAL_4OF5 explanations | QID-2021-0017 + QID-2021-0107 | `explanation` (2) | `pre_subscript_orphan_2026-05-19-070326.bak` |
| 5 | Corpus-wide subscript orphan cleanup (Phase 1 removal + Phase 2 medical-regex sweep) | 206 questions | `question_text` (~50) + `explanation` (~150) | `pre_subscript_cleanup_2026-05-19-072143.bak` |

### Final fidelity metrics (all at 0 post-session)

| Metric | Pre-session | Post-session |
|---|---|---|
| `questions.choices = '[]'` or NULL | 42 | **0** |
| `questions.correct_text` empty/NULL | 42 | **0** |
| `questions.question_text` with embedded answer-choice block | 41 | **0** |
| `questions.question_text` with wandering subscript orphan | 47 | **0** |
| `questions.explanation` with wandering subscript orphan | 117 | **0** |

### Positive verification — subscripts properly recovered

| Token | Questions containing |
|---|---|
| `A1c` | 47 |
| `B12` | 35 |
| `FEV1` | 19 |
| `T4` | 15 |
| `H2-blocker` | 8 |
| `α1-` | 7 |
| `H2O` | 4 |
| `S3 gallop` | 2 |
| `PaO2` | 2 |
| `PaCO2` | 2 |

### Other DB notes
- Recon during housekeeping found 10 articles ART-2208–ART-2218 (gap at ART-2210) already present at session start, with row count still at 2,206 (12 gap IDs). BATON 075's "Next ART-ID: ART-2208" was stale. **Corrected: next ART-ID = ART-2219.**
- 5 atomic backup files created in `00_database/db/` this session (~164 MB each). All gitignored. Keep until next session confirms stability.

---

## DB Changes (BATON 075)
**Substantive DB writes — first since BATON 060.** Two distinct write workflows:

### Tier 1 SQL apply (1,914 statements, one atomic transaction)
Applied via inline fix-applier workflow against canonical Windows DB. Pre-apply backup taken at `00_database/db/ite_intelligence.db.pre_qc_2026-05-18-221606.bak` (172 MB). All statements wrapped in single `BEGIN;...COMMIT;` for atomicity.

**Per-bucket statement counts:**
- A1 ENCODING_ARTIFACT: 93 (encoding fixes on questions.* text fields; 11 patched for choices JSON column)
- B5 AUTHOR_ARTIFACT: 24 (UPDATE articles SET author1 = ... corrected from clean_ref)
- C1 QID_LIST_CACHE_DRIFT: 359 (UPDATE articles SET qid_list = ...)
- C2 CITATION_COUNT_MISMATCH: 415 (UPDATE articles SET citation_count = ...)
- C3 EXAM_YEARS_DRIFT: 343 (UPDATE articles SET exam_years = ...)
- C4 UNIQUE_YEARS_MISMATCH: 446 (UPDATE articles SET unique_years = ...)
- C6 ZERO_CITATION_LINKED: 208 (UPDATE articles SET citation_count = ... where xref existed but cache was 0)
- C7 UNLINKED_CITED_ARTICLE: 26 (UPDATE articles SET citation_count = 0 where orphaned cache)

### Question recovery (1 INSERT)
QID-2024-0067 (acute HIV diagnostic, exam_year=2024, blueprint=Acute Care and Diagnosis, body_system=Hematologic/Immune, body_system_merged=Hematologic/Immune, correct_letter=B). Recovered from `2024_MC.pdf` page 28 (item 67) + `2024_critique.pdf` page 38. Primary fields populated; 4 enrichment fields NULL (stem_keywords, explanation_keywords, all_keywords, concept_tags) pending backfill via existing pipelines — see DEFERRED-QID-2024-0067-ENRICHMENT.

### Verification deltas

| Metric | Pre | Post | Δ |
|---|---|---|---|
| articles count | 2,206 | 2,206 | 0 |
| questions count | 1,639 | **1,640** | **+1** |
| qid_art_xref count | 2,710 | 2,710 | 0 |
| articles_with_citations | 1,800 | 1,982 | +182 |
| sum_citation_count | 2,387 | 2,710 | +323 |
| distinct_article_ids_in_xref | 1,982 | 1,982 | 0 |

### DB invariants now hold (post-apply, verified)

- `SUM(articles.citation_count) == COUNT(*) FROM qid_art_xref` (= 2,710) ✓
- `COUNT(articles WHERE citation_count > 0) == COUNT(DISTINCT article_id) FROM qid_art_xref` (= 1,982) ✓
- `ORPHAN_XREF rows == 0` (was 1: QID-2024-0067; now QID exists in questions table) ✓

### Full 15-table count verification (post-apply, BATON 075 close)

articles=2206, questions=**1640**, aafp_questions=1221, qid_art_xref=2710, aafp_qid_art_xref=864, article_icd10=4959, question_icd10=5774, aafp_question_icd10=4753, clinical_pathways=4959, pubmed_pmid_cache=344, icd10_vec=2219, article_icd10_vec=1757, question_icd10_vec=2747, intersection_centroid_vec=158, article_currency=2206.

No schema changes. PDF library unchanged. Script counts unchanged for all modules (M1/M2/M3/M4/M5). Only `.claude/skills/corpus-integrity-qc/` files modified (7 scripts/*.py + SKILL.md).

---

## DB Changes (BATON 074)
**No DB changes.** Skill shadow cleanup + archive reorganization session. DB was opened (read-only) for housekeeping recon — full 15-table verification matches BATON 073 verbatim: articles=2206, questions=1639, aafp_questions=1221, qid_art_xref=2710, aafp_qid_art_xref=864, article_icd10=4959, question_icd10=5774, aafp_question_icd10=4753, clinical_pathways=4959, pubmed_pmid_cache=344, icd10_vec=2219, article_icd10_vec=1757, question_icd10_vec=2747, intersection_centroid_vec=158, article_currency=2206. No schema changes, no PDF changes, no script changes. Pure infrastructure session: orphan worktree dir deleted, 9 user-level skill shadows audited + archived + retired, archive structure reorganized.

---

## DB Changes (BATON 073)
**No DB changes.** V3.2 workflow transition session (no worktrees policy + supporting cleanup). DB was opened (read-only) for pre-flight verification and housekeeping recon — counts verified live: articles=2206, questions=1639, aafp_questions=1221, qid_art_xref=2710 (full 15-table verification matches BATON 072 verbatim). No schema changes, no PDF changes, no script changes. Pure infrastructure session: stale worktree cleanup, CLAUDE.md conflict resolution, deprecated M3 scripts archived, session-housekeeping skill V3.1 → V3.2.

---

## DB Changes (BATON 072)
**No DB changes.** Device-handoff pause session — orientation + corpus-integrity-qc status recap, then user pivoted to the Windows big rig. The DB was not opened (read or write) this session. Row counts unchanged from BATON 071 / 070 / 069 / 068 (canonical, swapped in BATON 068). No schema changes, no PDF changes, no script changes.

---

## DB Changes (BATON 071)
**No DB changes.** This session was a `.claude/skills/` directory edit only — 5 skill directories copied from the plugin store into project-level skills. Row counts in all 15 audited tables verified identical to BATON 070 via direct sqlite3 query during housekeeping recon. No schema changes, no PDF changes, no script changes.

---


## DB: ite_intelligence.db

| Table | Rows | Notes |
|-------|------|-------|
| articles | 2,206 | Stable from BATON 065 (no new articles BATON 067) |
| questions (ITE) | 1,639 | 2018–2025 (+10 recovered), blueprint 100% |
| aafp_questions | 1,221 | BRQ, blueprint 100% |
| qid_art_xref | 2,710 | All 8 years (2018–2025); stable from BATON 065 |
| aafp_qid_art_xref | 864 | 643 unique Qs linked |
| article_icd10 | 4,959 | Stable; pre-existing Windows PC enrichment (BATON 062) |
| question_icd10 | 5,774 | ~89.9%+ ITE coverage; stable (BATON 062) |
| aafp_question_icd10 | 4,753 | Relevance normalized |
| clinical_pathways | 4,959 | Stable (BATON 062) |
| article_citation_trend | 1,740 | Longitudinal citation tracking + watch_list flag |
| article_currency | 2,206 | ✅ COMPLETE — Layer 2 Intelligence; mirrors articles; status enum and title_signals JSON column maintained |
| pubmed_pmid_cache | 344 | Layer 2 seed |
| article_icd10_vec | 1,757 | Rebuilt 2026-04-05 |
| question_icd10_vec | 2,747 | Rebuilt 2026-04-05 |
| icd10_vec | 2,219 | text-embedding-3-small (1536d) |
| article_vec | 1,998 | sqlite-vec virtual table (rebuilt 2026-04-16) |
| question_vec | 1,639 | sqlite-vec virtual table (rebuilt 2026-04-16) |
| aafp_question_vec | 1,221 | sqlite-vec virtual table |
| question_full_vec | 1,639 | BLOB – full question embedding with blueprint (NEW – BATON 056) |
| aafp_question_full_vec | 1,221 | BLOB – full AAFP embedding with blueprint+body_system+concept_tags (NEW – BATON 056) |
| blueprint_label_vec | 5 | BLOB – 5 canonical blueprint category label embeddings (NEW – BATON 056) |
| bodysystem_label_vec | 5 | BLOB – 5 canonical body system label embeddings (NEW – BATON 056) |
| question_concepttag_vec | 2,850 | BLOB – concept_tags embedding per question (NEW – BATON 056) |
| intersection_centroid_vec | 158 | BLOB – Stable (BATON 062) |

## Schema Notes
- subcategory + topic_label DROPPED from questions (ITE)
- aafp_questions: correct_letter, correct_text, explanation merged in; subcategory + aafp_explanations DROPPED
- QID format: QID-YYYY-NNNN (per-year numbering, resets each exam year)
- ART-ID format: ART-XXXX (zero-padded 4 digits)
- Next ART-ID: ART-2219 (last assigned ART-2206 BATON 065; gap reservations brought ceiling to 2219)
- **body_system field:** Fully normalized to post-2024 ABFM canonical taxonomy (Psychiatric/Behavioral, Sexual and Reproductive, Injuries/Musculoskeletal) for ITE 2018-2021, 2024-2025, and all AAFP (BATON 060)
- **body_system_merged field:** Forward mapping applied (BATON 060)

## Schema Notes — article_currency (NEW, BATON 046)
- Columns: article_id (FK), status (ENUM: 'current', 'updated', 'check_needed', 'not_indexed'), title_signals (TEXT JSON array), pubmed_pmid (INT FK)
- title_signals: JSON array of clinical category keywords (extracted from blueprint cross-reference; used for future filtering + human review)
- Populated via build_article_currency.py (M3 script)

## DB Changes (BATON 070)
- **2026-05-15 (BATON 070):** No DB changes. Substantive code session — corpus-integrity-qc skill V1 build (Layers A/B/D + coordinator + 4 agent templates). All audit access via `connect_db_readonly()` immutable URI; no possibility of write. Row counts and schema unchanged from BATON 069. End-to-end smoke test of the new pipeline produced 2,538 findings against canonical DB (158 Layer A + 582 Layer B + 1,798 Layer C); 1,914 Tier 1 SQL fixes now queued for application in next session. Confirmed Layer B closes the BATON 058 dict-overwrite bug — zero CRITIQUE_REF_MISSING_FROM_DB findings.

## DB Changes (BATON 069)
- **2026-05-15 (BATON 069):** No DB changes. Cleanup-only session — PROJECT_OVERHAUL fossil references removed; `project_overhaul_state.md` renamed to `project_session_log.md`. Row counts and schema unchanged from BATON 068.

## DB Changes (BATON 068)
- **2026-05-15 (BATON 068):** DB file swapped from stale Apr-16 copy (1,998 articles / 2,485 xref) to canonical May-6 copy (2,206 articles / 2,710 xref). No schema changes. Old DB preserved at `00_database/db/_archive_/ite_intelligence_stale_20260416.db`. New ORPHAN_XREF bug surfaced: QID-2024-0067/ART-2073 references non-existent QID in questions table.
- **Layer C smoke test (corpus-integrity-qc):** 1,798 findings against canonical DB — 1,797 derived-cache drift Tier 1 (mostly 208 ZERO_CITATION_LINKED from BATON-065 articles never having cache initialized) + 1 ORPHAN_XREF as above. No DB writes performed; fixes pending Layer D.
- **No script-count changes; no row-count changes (DB swap restored canonical state established BATON 067).**

## DB Changes (BATON 067)
- **No DB changes this session.** All counts stable from BATON 065.
- Session focus was AFP PDF acquisition (72 articles closed, gap 83 → 11) and BATON 066 worktree merge to main.
- 127 BATON 066 PDFs migrated FROM worktree TO main repo via robocopy + Move-Item.
- Articles for AFP-acquired PDFs were already cataloged from BATON 065 (acquire_missing_citations.py); no new article rows needed.
- **Script changes:** M1 maintain +9 net new (8 BATON 066 scripts merged from worktree + 1 NEW: aafp_targeted_downloader.py); aafp_fill_gaps.py modified (Playwright expect_download → context.request.get patch).
- **Structural cleanup:** _dupe_archive (48) + _corrupted_targeted_run (79) cleared via delete_me_pdfs_b65 staging then permanent deletion.

## DB Changes (BATON 066)
- **No DB changes this session.** All counts stable from BATON 065.
- Session focus was PDF acquisition (JAMA + NEJM) only — 127 new PDFs harvested (in worktree pending merge).
- xref linkage to be performed after worktree merge in next session.
- **Script additions only:** M1 maintain +8 scripts (jama_chrome_harvester.py, jama_prep_articlepdf_urls.py, nejm_doi_lookup.py, nejm_build_js_batch.py, nejm_console_script.py, nejm_move_downloads.py, nejm_save_server.py, unpaywall_retry.py) — all in worktree, pending merge.

## DB Changes (BATON 065)
- **Phase 2 PDF acquisition:** articles 1,998 → 2,206 (+208 new articles ART-1999–ART-2206)
- **qid_art_xref:** 2,485 → 2,710 (+225 citations linked during batch import)
- **article_currency:** 1,998 → 2,206 (mirrors articles table; status enum + title_signals JSON preserved)
- **No schema changes; no modifications to other tables**
- **Script additions:** M1 maintain +4 scripts (acquire_missing_citations.py, playwright_auth_downloader.py, browser_pdf_harvester.py, setup_journal_auth.py)
- **JAMA/NEJM:** playwright_auth_downloader.py IP-blocked; jama_pending.json output created for manual/Claude Code handoff

## DB Changes (BATON 063)
- **No DB changes this session.** All counts stable from BATON 062. Focus was DOCX guide generation (resident + faculty interpretation guides).
- **Script additions only:** M3 build_resident_guide.py, build_faculty_guide.py, build_resident_guide.js, build_faculty_guide.js (Python canonical per Rule 14)
- **word_doc_defaults.py enhanced** with level-aware add_section_header() function

## DB Changes (BATON 062)
- Pre-existing Windows PC enrichment discovered and migrated to Mac:
  - article_icd10: 3,952 → 4,959 (+1,007)
  - question_icd10: ~5,003 → 5,774 (+771)
  - clinical_pathways: 3,971 → 4,959 (+988)
  - intersection_centroid_vec: 123 → 158 (+35)
- No new articles or questions added; no schema changes
- M3 script improvements: ite_analyze_v2.py, ite_analyzer_v3.py, ite_report_builder_v2.js (3 files modified for report builder issues 1-5)
- Platform migration: Project copied from Windows home PC to Mac via external HD; DB and PDFs intact

## DB Changes (BATON 061)
- No new rows added; field corrections + analysis completions only
- article_currency: 1,985 → 1,998 (updated for 13 new articles ART-1987–ART-1999)
- All 7 resident analyses re-run with Stage 1.75 DB body_system backfill
- ite_analyze_v2.py: New Stage 1.75 DB body_system backfill pipeline added
- ite_analyzer_v3.py: pathway_gap_map() LEFT JOIN fixed (icd10_desc column now included)
- intersection_centroid_vec: verified complete (123 rows, 71 ITE + 52 AAFP)

## DB Changes (BATON 060)
- questions (ITE): 1,629 → 1,639 (+10 recovered questions enriched this session)
- article_icd10: 4,020 → 3,952 (−68 from synonym map variance in rebuild 2026-04-16)
- question_icd10: ~5,218 → ~5,003 (~89.9% coverage: 1,474/1,639 ITE questions tagged)
- article_vec: rebuilt 2026-04-16 (1,998 rows)
- question_vec: rebuilt 2026-04-16 (1,639 rows)
- intersection_centroid_vec: 135 → 123 rows (rebuilt 2026-04-16: 71 ITE + 52 AAFP centroids)
- body_system field: Fully normalized (22 holdout corrections applied, Musculoskeletal fixed, QID-2021-0168 corrected, 376 body_system_merged records synced)
- No schema changes; no new rows except recovered questions

## DB Changes (BATON 058)
- articles: 1,985 → 1,998 (+13 new: ART-1987–ART-1999 from critique QC rebuild)
- qid_art_xref: 2,470 → 2,485 (rebuilt from 2018–2025 ITE critique ground truth; replaces parser-inferred xrefs with direct PDF citations)
- No schema changes; no modifications to other tables
- Scripts added: generate_citation_sql.py, pdf_lookup_patch.py, add_missing_articles.py (M3)

## DB Changes (BATON 057)
- No row count changes (vector integration only)
- 3 new vector functions in ite_analyzer_v3.py (_build_concept_profile, _centroid_dim_boost, _apply_concept_vec_bonus)
- Unified practice questions table implemented in ite_report_builder_v2.js (removed singleQs/crossQs split)
- db_connect.py utility added (SQLite immutable=1 URI for NTFS compatibility)

## DB Changes (BATON 056)
- 6 new modular vector BLOB tables added (2026-04-14):
  - question_full_vec (1,639 rows) — full question embedding with blueprint
  - aafp_question_full_vec (1,221 rows) — full AAFP embedding with blueprint+body_system+concept_tags
  - blueprint_label_vec (5 rows) — 5 canonical blueprint category label embeddings
  - bodysystem_label_vec (5 rows) — 5 canonical body system label embeddings
  - question_concepttag_vec (2,850 rows) — concept_tags embedding per question
  - intersection_centroid_vec (135 rows) — 71 ITE + 64 AAFP blueprint×body_system centroids (updated to 123 in BATON 060)
- All 6 new vector tables populated and verified

## DB Changes (BATON 054)
- No DB modifications this session (2026-04-12)
- Script development: ite_analyze_v2.py, ite_analyzer_v3.py, ite_report_builder_v2.js refined
- New reference file: abfm_reference_2024.json (ABFM 2024 national benchmarks)

## DB Changes (BATON 052)
- questions.body_system_merged: Psychogenic → Psychiatric/Behavioral (120 rows updated, confirmed 2026-04-10 via retire_psychogenic.py)
- aafp_questions.body_system: Psychogenic → Psychiatric/Behavioral (82 rows updated)
- All row counts unchanged from BATON 051

## DB Changes (BATON 046)
- article_currency: NEW — 1,985 rows — Layer 2 Intelligence complete
- Scripts added: build_article_currency.py (M3)

## Key Metric Changes Since BATON 064

| Metric | BATON 064 | BATON 065 | BATON 066 | BATON 067 | BATON 068 | Change (064→068) | Notes |
|--------|-----------|-----------|-----------|-----------|-----------|------------------|-------|
| articles | 1,998 | 2,206 | 2,206 | 2,206 | 2,206 | +208 | EXA + Unpaywall batch acquisition (BATON 065) |
| qid_art_xref | 2,485 | 2,710 | 2,710 | 2,710 | 2,710 | +225 | New article xref linkages (BATON 065) |
| article_currency | 1,998 | 2,206 | 2,206 | 2,206 | 2,206 | +208 | Mirrors articles table (BATON 065) |
| ITE PDFs (active tiers, Windows canonical) | 988 | 1,254 | 1,381 (worktree, pre-merge) | 1,540 (post-merge + AFP) | 1,540 (unchanged on Windows) | +552 | EXA/Unpaywall +266 (BATON 065); JAMA/NEJM +127 merged (BATON 067); AFP +72/cleanup -127 (BATON 067) |
| ITE PDFs (Mac local) | n/a | n/a | n/a | n/a | 971 (lags Windows by 569) | — | DEFERRED-MAC-PDF-SYNC (gitignored content) |
| M1 maintain scripts | 26 | 30 | 36 (worktree) | 38 (main; +1 NEW BATON 067) | 38 (unchanged) | +12 | +4 BATON 065; +8 BATON 066 merged BATON 067; +1 NEW BATON 067 (aafp_targeted_downloader.py); aafp_fill_gaps.py modified |
| All other tables | stable | stable | stable | stable | stable | 0 | No DB changes BATON 068 (canonical restored via swap from stale Apr-16 copy) |
