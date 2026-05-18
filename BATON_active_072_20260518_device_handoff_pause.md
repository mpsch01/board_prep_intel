# BATON 072 — 2026-05-18 — Device Handoff (Mac → Windows)

**Active Session Handoff Document for board_prep_intel**

---

## Session Overview

| Item | Value |
|------|-------|
| **Date** | 2026-05-18 |
| **Previous BATON** | BATON_active_071_20260518_custom_skills_project_level.md |
| **Git Hash (pre-housekeeping-commit)** | 2079a2f |
| **Branch** | claude/awesome-chandrasekhar-3ae317 (fresh Claude Code worktree off main) |
| **Primary Goal** | Orientation pass + corpus-integrity-qc status update; pause and hand off to the Windows big-rig PC for the actual corpus-qc V1 testing run. |
| **Status** | Complete — orientation done, corpus-qc plan rehearsed, no code/DB/PDF changes; ready to resume on Windows. |

---

## What Happened This Session

Mikey opened a new Claude Code session, ran `/board-startup`, and asked for a corpus-integrity-qc progress recap before kicking off the BATON 071 carry-forward testing pass. After delivering the recap (what's built, what's left, known bugs / circle-back items, the worktree path caveat for `run_qc.py`, and the `fix-applier` first-use plan), Mikey decided to **move the work to the big rig PC** rather than execute on Mac. No scripts were run, no DB writes occurred, no PDFs were touched.

**Net effect:** zero file changes outside this housekeeping pass. All BATON 071 carry-forwards remain in place; the next session on Windows picks up exactly where BATON 071 left off.

---

## DATABASE STATE

*(Inherited from BATON 071 — no DB writes, no schema changes, no row changes this session.)*

| Table | Rows | Notes |
|-------|------|-------|
| articles | 2,206 | unchanged |
| questions (ITE) | 1,639 | unchanged |
| aafp_questions | 1,221 | unchanged |
| qid_art_xref | 2,710 | unchanged |
| aafp_qid_art_xref | 864 | unchanged |
| article_icd10 | 4,959 | unchanged |
| question_icd10 | 5,774 | unchanged |
| aafp_question_icd10 | 4,753 | unchanged |
| clinical_pathways | 4,959 | unchanged |
| pubmed_pmid_cache | 344 | unchanged |
| article_icd10_vec | 1,757 | unchanged |
| question_icd10_vec | 2,747 | unchanged |
| icd10_vec | 2,219 | unchanged |
| intersection_centroid_vec | 158 | unchanged |
| article_currency | 2,206 | unchanged |

**Next ART-ID:** ART-2208 (unchanged). **No schema changes. No row changes.**

---

## PDF LIBRARY

*(Inherited from BATON 071 — Mac local still lags Windows canonical by 567 files. Not re-verified this session since no PDF work occurred.)*

| Tier | Mac | Windows canonical | Notes |
|------|-----|-------------------|-------|
| VC_fail | 630 | 1,056 | DEFERRED-MAC-PDF-SYNC |
| VC_pass | 168 | 309 | DEFERRED-MAC-PDF-SYNC |
| local_lite | 117 | 117 | Synced |
| right_click | 58 | 58 | Synced |
| AAFP | 15 | 15 | Synced |
| ite_exams | 16 | 16 | Synced |
| **ITE active total (Mac)** | **973** | **1,540** | |

**Note for next session:** running corpus-qc on Windows means the testing pass will hit the canonical 1,540-PDF library directly — no Mac PDF sync required up-front for the DB-only audit (Layers A/B/C don't read PDFs in V1; A4 PDF-diff is deferred). Mac PDF sync remains a DEFERRED-MAC-PDF-SYNC carry-forward.

---

## SCRIPT INVENTORY

*(All counts unchanged from BATON 071. No script additions, deletions, or modifications this session.)*

| Module | Category | Count | Δ |
|--------|----------|-------|---|
| M1 | Build (Python) | 8 | unchanged |
| M1 | Maintain (Python) | 38 | unchanged |
| M1 | scripts/ root | 1 | unchanged |
| M2 | Python | 75 | unchanged |
| M2 | JavaScript | 6 | unchanged |
| M3 | Python | 55 | unchanged |
| M3 | JavaScript | 4 | unchanged |
| M3 | JSON config | 6 | unchanged |
| M4 | Python | 1 | unchanged |
| M5 | Python sync | 3 | unchanged |
| M5 | TypeScript/TSX | 35 | unchanged |
| M5 | SQL migrations | 5 | unchanged |
| `.claude/skills/` (project-level) | Directories with SKILL.md | 7 | unchanged |
| `.claude/skills/` (project-level) | Cowork `.skill` zips | 2 | unchanged |

---

## DEFERRED FLAGS

### Newly opened this session
**None.** Pure pause/handoff — no new tech debt.

### Closed this session
**None.**

### Carry-forward from BATON 071 (all unchanged)

- **DEFERRED-LAYER-A4-PDF-DIFF** — Layer A4 (PDF-diff re-extract) deferred to corpus-qc V1.1.
- **DEFERRED-LAYER-C-CACHE-REBUILD** — 1,797 Layer C Tier-1 cache rebuild SQL pending application via fix-applier (`--tier 1 --approved-by-user 1`).
- **DEFERRED-ORPHAN-XREF-QID-2024-0067** — single ORPHAN_XREF row to investigate then likely DELETE.
- **DEFERRED-MAC-PDF-SYNC** — Mac PDF library lags Windows canonical by 567 PDFs.
- **DEFERRED-LOCKED-RULE-8-UPDATE** — Rule 8 needs Mac/Claude Code broadening.
- **DEFERRED-CROSS-TIER-CODON-DUPES** — 89 ART-IDs in both VC_fail and VC_pass tiers.
- **DEFERRED-AFP-DATA-QC** — 6 articles with malformed clean_ref / junk title.
- **DEFERRED-AAFP-HTTP-500-RETRY** — 5 vintage AFP articles blocked by AAFP server outage.
- **DEFERRED-UNPAYWALL-CLOUDFLARE** — 144 OA URLs blocked by Cloudflare.
- **DEFERRED-QID-XREF-LIBRARY-GAPS** — ~801 articles missing PDFs (246 UNMATCHED_CITATION findings from Layer B).
- **DEFERRED-PENDING-LIST-QC** — spot-check pending lists for URL-mismatch defects.
- **DEFERRED-DESHMUKH-2021** — ART-0302 paywalled at tandfonline.
- **DEFERRED-YOY-ROBUSTNESS** — `longitudinal_delta()` edge cases.
- **DEFERRED-PGY-BENCHMARKS** — awaiting PGY 1-4 data.
- **DEFERRED-PROGRAM-TREND** — pending PGY benchmarks.
- **DEFERRED-RESIDENT-FOLDER-MIGRATION** — investigate `resident_data/` migration to M5.
- **DEFERRED-SCHOLL-OLD-FORMAT** — 2022/2023 score reports use old ABFM taxonomy.
- **DEFERRED-KNOWN-DRUGS-EXPANSION** — identify offending drug names; decide fix approach.
- **FLAG-33-NNN-RENAME** — nnn_XXXX ART-ID rename scheme designed, not yet implemented.

---

## CRITICAL REMINDERS FOR NEXT SESSION (on Windows)

1. **Top priority remains the corpus-integrity-qc V1 testing pass.** BATON 070's Immediate list and BATON 071's "Immediate (next session)" list both still apply verbatim. No work has been performed against them since BATON 070's smoke test in the worktree.

2. **On Windows, paths look like:**
   - `PROJECT_ROOT = C:\Users\mpsch\Desktop\board_prep_intel\`
   - `DB = C:\Users\mpsch\Desktop\board_prep_intel\00_database\db\ite_intelligence.db` (this is the canonical DB on Windows)
   - `OUTPUT_DIR = C:\Users\mpsch\Desktop\board_prep_intel\03_module.3_analyst\outputs\corpus_qc\2026-05-18\`

3. **Worktree path caveat still in force.** `run_qc.py` auto-detects PROJECT_ROOT as `SCRIPT_DIR.parent.parent.parent.parent.parent` — from a worktree this lands one level too deep. If you spin up a worktree on Windows for the testing pass, pass `--project-root` explicitly. On a direct main checkout the auto-detect works.

4. **Pre-flight `git pull` on Windows.** Windows main is currently at hash `2079a2f` (or wherever it was when the user last pulled). After this housekeeping pass commits + the user-merged PR lands, Windows needs `git pull origin main` to pick up BATON 072 before starting work.

5. **No DB or schema changes this session.** Row counts identical to BATON 071. All 15 audited tables unchanged.

6. **`fix-applier` first-use is still pending.** Built but never exercised. Token contract: `--tier 1 --approved-by-user 1`. Backs up DB before write, runs verification COUNTs, refuses both-tiers-in-one-call.

7. **Known bug to keep on the bug-fix loop radar (BATON 070 #6):** `correct_author_from_clean_ref()` in `.claude/skills/corpus-integrity-qc/scripts/utils.py` truncates derived author at 80 chars, sometimes mid-word. Improvement target for a `utils.py` patch when convenient — Tier 1 SQL is still a net improvement over bare stop-word author1 in the meantime.

---

## NEXT STEPS

### Immediate (next session — on Windows big rig)
1. **`git pull origin main`** in Windows project root to pick up BATON 072.
2. **`/board-startup`** to load BATON 072 + confirm the orientation context carries over cleanly.
3. **Run `run_qc.py` end-to-end on the canonical Windows DB** — verify all 5 artifacts land in `03_module.3_analyst\outputs\corpus_qc\2026-05-18\` (or whatever date stamp the run picks).
4. **Spot-check 10 random Tier 1 SQL statements** before applying — copy-paste each into DB Browser and verify the intended fix.
5. **Apply Tier 1 via the `fix-applier` agent** with `--tier 1 --approved-by-user 1`. Should land ~1,914 statements. Closes DEFERRED-LAYER-C-CACHE-REBUILD.
6. **Re-run `run_qc.py`** post-apply to confirm cache-rebuild findings drop to ~0.
7. **Investigate ORPHAN_XREF QID-2024-0067 / ART-2073** — eyeball, uncomment Tier 2 DELETE if appropriate. Closes DEFERRED-ORPHAN-XREF-QID-2024-0067.
8. **Bug-fix loop** on anything testing surfaces.

### Short-term (this week)
9. **Re-run all 7 resident analyses** — still carrying from BATON 065+066+067.
10. **Tier 2 review pass** — eyeball 66 commented statements.
11. **Cross-tier codon dedupe** — 89 ART-IDs in both VC_fail and VC_pass.

### Medium-term
12. **AAFP BRQ extension of corpus-integrity-qc (v2)** — Layer C ports trivially; Layer A ports easily; Layer B inapplicable — replace with per-article scalar checks against AAFP-linked rows.
13. Continue 801-article gap closure by source_type buckets.
14. Apply NEJM DevTools pattern to 144 unpaywall Cloudflare-blocked URLs.

---

## LOCKED RULES (Never Override Without Mikey Confirming)

*(Verbatim from BATON 071. No changes this session. Rule 8 still flagged for update in DEFERRED-LOCKED-RULE-8-UPDATE.)*

1. **Fix the data, not the code.**
2. **VC gate = sole criterion** for right_click tier.
3. **Source data is protected.** DB + PDFs + VC gate survive everything.
4. **Dynamic paths only.** `SCRIPT_DIR = Path(__file__).resolve().parent; PROJECT_ROOT = SCRIPT_DIR.parent.parent`.
5. **No de novo JS.** New code = Python only.
6. **BATON first.**
7. **QC after every integration.**
8. **Git via Desktop Commander.** *(Flagged for update — Mac/Claude Code workflow now primary.)*
9. **Strategy 0 in every enricher.**
10. **Schemas before scripts.**
11. **`shutil.rmtree` is BANNED.**
12. **`_normalize_concept()` fallback = first-letter capitalize only.**
13. **ICD-10 enrichment is invisible.**
14. **Word docs use `word_doc_defaults.py`.**

---

## FOR THE REPO (Git Notes)

- **Branch:** claude/awesome-chandrasekhar-3ae317 (fresh worktree off main, opened this session)
- **Pre-housekeeping commit hash:** `2079a2f` ("Remove tracked .tmp.driveupload artifacts (pre-gitignore residue)" — the latest pre-session commit on main; worktree was at the same hash on open)
- **Session commit (housekeeping):** *(to be filled in after commit)*
- **Hash-backfill commit:** *(follows session commit — backfills hash into README.json + README.md + CLAUDE.md + this BATON)*
- **No DB writes, no PDF acquisition, no schema changes, no script changes** this session — pure orientation + status conversation + housekeeping paper trail.
- **Worktree cleanup:** this worktree (`.claude/worktrees/awesome-chandrasekhar-3ae317`) will be removed during Item 12 post-merge cleanup once the user merges the PR.

---

**End BATON 072.**
*Device-handoff pause — orientation done, plan rehearsed, no code touched; resume corpus-qc V1 testing pass on the Windows big rig.*
