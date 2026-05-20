# BATON 077 — 2026-05-19 — Resident Re-run + Blueprint Parser Fix + Encoding DB Cleanup

**Active Session Handoff Document for board_prep_intel**

---

## Session Overview

| Item | Value |
|------|-------|
| **Date** | 2026-05-19 (third session of the same calendar day, after BATON 075 + 076) |
| **Previous BATON** | `BATON_active_076_20260519_tier2_apply_and_corpus_cleanup.md` (merged via PR #22 at `c9f1f90`) |
| **Pre-session git hash** | `c9f1f90` (main, BATON 076 merge commit) |
| **Branch** | `claude/session-077-q17-and-encoding-fixes` (V3.2 feature branch) |
| **Primary Goal** | Review a Mac QC-handoff note (dot-leader/encoding artifacts in Cole's deliverables) → fix Q17 + safest encoding gaps → re-run all 7 resident analyses for real-world testing. The re-run surfaced two latent parser bugs that were then fixed end-to-end. |
| **Status** | Complete. 3 code commits' worth of work (2 committed: `f091abd`, `ae47b77`; housekeeping to follow), 3 DB-write workflows (gitignored), all 7 resident analyses re-run + QC-verified. Closed the long-overdue DEFERRED-RESIDENT-ANALYSES-RERUN. |

---

## What Happened This Session

The session began as a review of a focused QC-handoff note (`qc_handoff` on the Desktop) that Mac-Claude wrote after spot-fixing Cole's ITE practice deliverables. Reviewing it against the **canonical Windows DB** showed most of its findings were already resolved by BATON 076 (the Mac was on a pre-075 stale DB) — but it surfaced genuinely-new encoding gaps (the Symbol-font dot-leader `ï€®` family + `Ã—` double-encoding) and a content gap (Cole's broken "Q17"). Fixing those, then re-running all 7 resident analyses as "real-life testing," uncovered **two latent bugs in the resident-analysis pipeline** that had been silently producing wrong output for years. Both were fixed, validated, and the corpus is now materially more correct.

### Workstream 1 — QC-handoff review (no changes; triage only)

Verified each handoff finding against the live DB:
- **Already fixed by BATON 076:** empty `A)B)C)D)E)` template blocks (0 in DB), trailing pagenum in choices (0), bulk subscript orphans (~0). These were artifacts in Cole's files only because the Mac DB was 3 weeks stale.
- **Genuinely new + verified present:** dot-leader `ï€®` (14 questions / 2,618 triplets — clinical lab tables: `Plateletsï€®ï€®…`), `Ã—`/`Ã?` double-encoding family (8 patterns: `× ä ó ç í á ï ø`, ~22 occ).
- **Note's fix was WRONG for one item:** the doubled-quote `””` (20 questions) in the canonical DB are citation *title separators* (colon/em-dash), not numeric ranges — a blanket en-dash collapse would mangle them. Left alone.
- Confirmed the note's bug claim: `build_custom_question_set.py:63` `_DOTLEADER` targeted raw PUA codepoints but the DB stores the triple-mojibake form → the regex was dead code.

### Workstream 2 — Q17 stem recovery (QID-2022-0097)

The handoff's "Cole Q17" = **QID-2022-0097**. BATON 076's A3 fix had populated its choices, but the **stem was still truncated** mid-sentence ("…you note the presence of a"). Recovered the full stem from `2022_MC.pdf` p.34 (item 97): "…a 2.5×2.5-cm perianal abscess. A point-of-care glucose level is 172 mg/dL and the results of a CBC are pending. Which one of the following would be the most appropriate next step?" Applied a single `question_text` UPDATE (468 → 646 chars), backed up, invariants preserved.

### Workstream 3 — Encoding-table extensions (code, commit `f091abd`)

Extended the two encoding tables (code-only, zero DB writes at this step):
- `03_module.3_analyst/scripts/build_custom_question_set.py` — fixed the dead `_DOTLEADER` regex to match the triple-mojibake form (collapse to `": "` so lab tables read `Platelets: 112,000`), added the 8 `Ã?` entries to `_ENCODING_FIXES`.
- `.claude/skills/corpus-integrity-qc/scripts/utils.py` — same `Ã?` additions + a `DOTLEADER_RE` so the QC layer *detects* the family.
Verified against live DB content (idempotent; renders clean).

### Workstream 4 — First re-run pass (surfaced 2 bugs)

Re-ran all 7 analyses (Scholl 2022/23/24, Pjetergjoka 2024/25, Hopkins 2025, Sarkar 2025) in **score-report mode** (per Mikey: use the official ABFM score reports where available; Pjetergjoka's encrypted reports auto-authenticate via `_find_pdf_password`). PGY levels: Scholl 1/2/3, Pjetergjoka 1/2 (from score reports), Hopkins 3 + Sarkar 1 (per Mikey, no score report on file). This first pass surfaced:
- **Bug A — UTF-8 console crash.** `ite_analyze_v2.py` crashed printing the `✓` glyph in its NAMING CHECK on the Windows cp1252 console. Fixed with a stdout/stderr UTF-8 reconfigure at module top (committed in `ae47b77`).
- **Bug B — resident DOCX render garbling.** The Node report builder (`ite_report_builder_v2.js`) has *no* encoding cleanup, so dot-leader/`Ã—` from the DB rendered garbled into resident DOCX (e.g., `ITE_2024_v3_Exam_Michael_Scholl.docx`: 295 dot-leaders). → motivated Workstream 5.
- **Anomaly — denominators 123/125 for 2022/2023** (vs ~195 expected). → investigated in Workstream 6.

### Workstream 5 — Encoding DB-fix (gitignored DB; 34 rows)

Cleaned the dot-leader + `Ã?` families **in the DB itself** (the right fix per Locked Rule 1 — fixes every downstream path, including the encoding-blind Node report builder). Scoped transforms only: dot-leader `ï€®` → `": "`, `Ã?` family substitution. Left doubled-quote + smart quotes untouched. JSON-aware for the `choices` column. Result: **34 rows updated** (24 question_text, 11 explanation, 1 choices), invariants 2206/1640/2710 preserved, residual dot-leader **0** and `Ã—` **0**.

### Workstream 6 — Fix #1: parse_blueprint multi-page (code, commit `ae47b77`)

Root cause of 123/125: the old-format (2018–2023) ABFM blueprint report is a **2-page** PDF, but `parse_blueprint` hard-read `doc[0]` only ("Blueprint is always single-page" — true for 2024+, false for legacy). Per-page colored-item counts confirmed: 2022 = page1 123 + page2 72 = 195; 2023 = 125 + 73 = 198. Fixed `ite_parser.py` to loop **all** pages (like `parse_bodysystem` already does), aggregate items, scan every page for the deleted-item note, dedupe by item number. Result: 2022 123→**195**, 2023 125→**198**; single-page years unchanged.

### Workstream 7 — Option C: Stage 1.8 blueprint DB cross-check + derive (code, commit `ae47b77`)

Added a new stage in `ite_analyze_v2.py` (alongside the Stage 1.75 body_system backfill): **blueprint is now derived from the normalized DB by QID** (authoritative), with a cross-check that compares against the PDF-position blueprint and flags disagreements. Comparison done in the analyzer's native short-name space via the existing `BLUEPRINT_DB_TO_PDF` map so only **true** category disagreements are flagged (not PDF-short vs DB-full naming noise). `blueprint_xcheck` (derived/agree/disagreements) stored in the analysis JSON.

### Workstream 8 — MAJOR FINDING: old-format blueprint was ~70% mis-categorized

The cross-check revealed the legacy 2-page reports' column geometry does **not** map to the new-format column positions the parser assumes:
- **Old format (2022/2023): ~70% disagreement** (2022: 136/195, 2023: 138/198). The PDF-position blueprint was ~70% *wrong* — items attributed to the wrong blueprint category. The DB (normalized) corrects it.
- **New format (2024/2025): 0–1 disagreement** (2024: 194/195, 2025/Hopkins/Sarkar: 191/191). This validates both the DB normalization AND the QID→item mapping.

Implication: every prior Scholl 2022/2023 report had ~70% of items in the wrong blueprint category — wrong per-category breakdowns, weak areas, cross-tab, and reading lists for those two years. (Overall score unaffected — it's from the score report. This was a *categorization* bug, not extraction or rendering.)

### Workstream 9 — QID-2024-0017 correction (the one new-format disagreement)

The single recurring new-format disagreement (Scholl 2024 + Pjetergjoka 2024, item 17 = QID-2024-0017): DB had `Acute Care and Diagnosis`, ABFM placed it in Chronic Care. The question is a gradual-onset posterior tibial **tendinopathy** managed conservatively — clinically Chronic Care Management, and that's where ABFM placed it. **Corrected the DB → `Chronic Care Management`** (per Mikey: "the default is always the ABFM published data"). Re-ran the 3 affected reports → **all 7 now show 0 blueprint disagreements.**

### Workstream 10 — Final re-run + QC

All 7 re-run after every fix. Verified: correct denominators (2022:195, 2023:198, others full), DB-authoritative blueprint, **0 encoding artifacts in every JSON and DOCX** (the previously-garbled Scholl 2024 Exam now clean), official YoY scaled deltas (Scholl 440→480→500, Pjetergjoka 350→370), reading lists shifted vs baseline (overlap 3–7/15 — the substrate of the re-run).

### Workstream 11 — Memory

Saved a feedback memory (`~/.claude/projects/.../memory/feedback_abfm_published_authoritative.md`): **Option C (DB-derived blueprint) is the working approach; ABFM published data is the tie-breaker** when DB and ABFM conflict — correct the DB to match. Includes the format-dependent nuance (new-format → parser/ABFM reliable; old-format → DB stands).

---

## DATABASE STATE

*(Verified live via sqlite3 during housekeeping recon. Row counts UNCHANGED from BATON 076 — only column values updated.)*

| Table | Rows | Δ from BATON 076 |
|-------|------|---|
| articles | 2,206 | 0 |
| questions (ITE) | 1,640 | 0 |
| aafp_questions | 1,221 | 0 |
| qid_art_xref | 2,710 | 0 |
| aafp_qid_art_xref | 864 | 0 |
| article_icd10 | 4,959 | 0 |
| question_icd10 | 5,774 | 0 |
| clinical_pathways | 4,959 | 0 |
| article_currency | 2,206 | 0 |
| pubmed_pmid_cache | 344 | 0 |
| icd10_vec | 2,219 | 0 |
| intersection_centroid_vec | 158 | 0 |

**Column updates this session (gitignored DB; not in git):**
- `questions.question_text`: QID-2022-0097 stem recovery (1) + encoding cleanup (24)
- `questions.explanation`: encoding cleanup (11)
- `questions.choices`: encoding cleanup (1, JSON-aware)
- `questions.blueprint`: QID-2024-0017 `Acute Care and Diagnosis` → `Chronic Care Management` (1)

**Invariants preserved on every apply:** SUM(citation_count)=2,710 = DISTINCT article_id in xref (1,982 articles citation_count>0); max article_id ART-2218 → **next ART-ID = ART-2219**.

**Post-session fidelity metrics:** residual dot-leader `ï€®` = **0**, residual `Ã—` = **0**, blueprint disagreements across all 7 reports = **0**.

**Backup files (gitignored, `00_database/db/`):** 3 new this session — `pre_q17_fix_2026-05-19-212808.bak`, `pre_encoding_fix_2026-05-19-220232.bak`, `pre_q2017_blueprint_2026-05-19-222051.bak` (~164 MB each). Plus 6 from BATON 075/076. **Recommend pruning the BATON-075/076 backups next session** (stability confirmed).

---

## PDF LIBRARY

*(Unchanged from BATON 076.)*

| Tier | Count |
|------|-------|
| ITE/VC_fail | 1,056 |
| ITE/VC_pass | 309 |
| ITE/local_lite | 117 |
| ITE/right_click | 58 |
| AAFP | 15 |
| ite_exams | 16 |
| **ITE active total** | **1,540** |

---

## SCRIPT INVENTORY

*(No new scripts — all edits to EXISTING files. Counts unchanged from BATON 076.)*

| Module | Count | Files modified this session |
|--------|-------|------------------------------|
| M1 build/maintain (.py) | 8 / 38 | — |
| M2 scripts (.py / .js) | 80 / 6 | `build_custom_question_set.py` (encoding) |
| M2 corpus-qc skill | — | `.claude/skills/corpus-integrity-qc/scripts/utils.py` (encoding) |
| M3 scripts (.py / .js) | 55 / 4 | `ite_parser.py` (multi-page), `ite_analyze_v2.py` (UTF-8 + Stage 1.8 Option C) |

---

## DEFERRED FLAGS

### Closed this session
- **DEFERRED-RESIDENT-ANALYSES-RERUN** — finally closed. All 7 re-run + QC-verified against the cleaned DB. (Carried since BATON 065/066/067/075/076.)
- **Q17 content gap** (QC-handoff item) — QID-2022-0097 stem recovered.
- **Dot-leader + Ã encoding** (QC-handoff items) — fixed at DB source + render paths.

### Newly opened this session
- **DEFERRED-BLUEPRINT-XCHECK-AUTOFIX** — enhancement: have Stage 1.8 emit a ready-to-run DB `UPDATE` for each *new-format* disagreement (set DB blueprint = ABFM/parser value), turning the flagged list into one-click ABFM-tie-breaker corrections. Not needed now (flag-then-fix works); build when disagreements accumulate.
- **DEFERRED-PATIENT-BASED-SYSTEMS-RESIDUAL** — one stray old-taxonomy `body_system` label (`Patient-Based Systems`) persists in 2018–2023 questions (2024/2025 don't have it). A residual gap in BATON 059–061 normalization. Remap to canonical equivalent.
- **DEFERRED-DOUBLED-QUOTE** — 20 questions have `””` in citation title positions (colon/em-dash). Context-varies → needs per-case handling, NOT a blanket fix. Left intentionally.
- **DEFERRED-C1-CONTROLS** — 47 questions contain C1 control chars (U+0080–009F). Invisible; defensive strip after verifying truly stray. Left intentionally.
- **DEFERRED-REPORT-BUILDER-ENCODING** — `ite_report_builder_v2.js` has no encoding cleanup; currently moot (DB is clean at source) but if new artifacts enter the DB, resident DOCX would garble again. Low priority given DB-source cleaning is the policy.

### Carry-forward (unchanged from BATON 076)
DEFERRED-LAYER-A2-HEURISTIC-TUNING, DEFERRED-CORPUS-QC-LAYER-A7-A8, DEFERRED-LAYER-A4-PDF-DIFF, DEFERRED-LAYER-A5-LANGUAGE-INTEGRITY, DEFERRED-LAYER-A6-RENDER-FIDELITY, DEFERRED-MAC-PDF-SYNC (567 PDFs), DEFERRED-LOCKED-RULE-8-UPDATE, DEFERRED-CROSS-TIER-CODON-DUPES (89), DEFERRED-AFP-DATA-QC, DEFERRED-AAFP-HTTP-500-RETRY, DEFERRED-UNPAYWALL-CLOUDFLARE (144), DEFERRED-QID-XREF-LIBRARY-GAPS (~801), DEFERRED-PENDING-LIST-QC, DEFERRED-DESHMUKH-2021, DEFERRED-YOY-ROBUSTNESS, DEFERRED-PGY-BENCHMARKS, DEFERRED-PROGRAM-TREND, DEFERRED-RESIDENT-FOLDER-MIGRATION, DEFERRED-SCHOLL-OLD-FORMAT (now substantially addressed by Fix #1 + Option C — the parsing + categorization are correct; can likely close after a confirmation pass), DEFERRED-KNOWN-DRUGS-EXPANSION, FLAG-33-NNN-RENAME.

---

## CRITICAL REMINDERS FOR NEXT SESSION

1. **The resident reports are now correct and current.** All 7 regenerated against the cleaned DB with correct denominators, DB-authoritative blueprint, and 0 encoding artifacts. The 2022/2023 reports in particular are materially different from the old ones (the ~70% blueprint mis-categorization is fixed).
2. **Blueprint is now DB-authoritative (Option C).** Both the resident analysis AND the custom-question-set skill read blueprint from the DB — a single source of truth. Fixing a DB blueprint label benefits both. ABFM is the tie-breaker for conflicts (see memory).
3. **The Stage 1.8 cross-check is a standing QC tool.** Any future resident run prints blueprint disagreements; on new-format years these are DB-error candidates to fix toward ABFM.
4. **9 DB backups in `00_database/db/` (~1.5 GB total).** Prune the BATON-075/076 ones next session.
5. **`DEFERRED-SCHOLL-OLD-FORMAT` is largely resolved** — consider formally closing after a spot-check of the regenerated 2022/2023 reports.

---

## NEXT STEPS

### Immediate (next session)
1. **`/board-startup`** to load BATON 077 + verify state (articles=2206, questions=1640, qid_art_xref=2710, single `main`, no worktrees, 0 dot-leader, 0 blueprint disagreements on a sample re-run).
2. **Decide on DEFERRED-BLUEPRINT-XCHECK-AUTOFIX** — build the one-click ABFM-tie-breaker corrector, or keep manual.
3. **Quick wins:** remap `Patient-Based Systems` residual (DEFERRED-PATIENT-BASED-SYSTEMS-RESIDUAL); spot-check + close DEFERRED-SCHOLL-OLD-FORMAT.

### Short-term
4. Investigate the doubled-quote (citation separators) + C1-control cleanups (both deferred this session).
5. Build A7/A8 corpus-qc layer checks (embedded-choices + wandering-subscript) — carry from BATON 076.
6. Prune old DB backups.

### Medium / long-term
7. A4 PDF_DIFF + A6 RENDER_FIDELITY corpus-qc layers; A5 LANGUAGE_INTEGRITY.
8. AAFP BRQ extension of corpus-integrity-qc (v2).
9. Continue 801-article gap closure; NEJM DevTools pattern for 144 Cloudflare-blocked URLs.

---

## FOR THE REPO (Git Notes)

- **Branch:** `claude/session-077-q17-and-encoding-fixes` (V3.2 feature branch from `main`)
- **Pre-session hash on main:** `c9f1f90` (BATON 076 merge — "Merge pull request #22")
- **Session commits on feature branch:**
  - `f091abd` — *"QC follow-up: Q17 stem recovery + dot-leader/Ã encoding-table extensions"* (2 files)
  - `ae47b77` — *"ITE analysis: multi-page blueprint parse + DB-authoritative blueprint cross-check + UTF-8 fix"* (2 files)
  - `b7b5b75` — *"BATON 077: resident re-run + blueprint parser fix + encoding DB cleanup"* (housekeeping, 13 files)
  - *(hash-backfill commit follows, propagating `b7b5b75`)*
- **PR:** *(to be opened during Item 12; merged via `gh pr merge --merge --delete-branch`)*

---

**End BATON 077.**
*Reviewed a Mac QC-handoff, recovered Q17, then re-ran all 7 resident analyses — which surfaced and fixed two latent pipeline bugs: blueprint reports were only reading page 1 of legacy 2-page PDFs (denominator 123/195), and the blueprint dimension was ~70% mis-categorized for 2022/2023 because PDF-column geometry differs across ABFM eras. Now: multi-page parse + DB-authoritative blueprint (Option C, ABFM tie-breaker), encoding cleaned at DB source, all 7 reports correct. Next session: optional auto-fix enhancement + remaining encoding/normalization residuals.*
