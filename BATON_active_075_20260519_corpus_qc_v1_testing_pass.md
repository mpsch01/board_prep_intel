# BATON 075 — 2026-05-19 — Corpus-Integrity-QC V1 Testing Pass + DB Write Debut

**Active Session Handoff Document for board_prep_intel**

---

## Session Overview

| Item | Value |
|------|-------|
| **Date** | 2026-05-19 (started early-AM after BATON 074 merge at 2026-05-19T01:41Z) |
| **Previous BATON** | BATON_active_074_20260518_skill_shadow_cleanup.md (merged via PR #20 at `65754ea`) |
| **Pre-session git hash** | `65754ea` (main, post BATON 074 merge) |
| **Branch** | `claude/session-075-corpus-qc-v1-pass` (V3.2 feature branch; first session-075 branch) |
| **Primary Goal** | Execute the corpus-integrity-qc V1 end-to-end testing pass that's been carrying forward since BATON 070. First-ever run of `run_qc.py` standalone + first-ever DB-writing exercise of the fix-applier safety machinery. |
| **Status** | Complete. End-to-end pass succeeded; 1,914 Tier 1 statements applied cleanly; 3 substantive bugs in the skill itself were discovered and fixed in-flight; 1 missing ITE question (QID-2024-0067, acute HIV) recovered from source PDFs; 3 deferred flags closed, 3 new opened. DB integrity dramatically improved: total findings 2,538 → 624, Layer C dropped from 1,798 to 0. |

---

## What Happened This Session

After `/board-startup` confirmed BATON 074 closed cleanly and PR #20 was merged, user requested a narrative explainer on the corpus-integrity-qc skill before the test pass. Mid-explanation, a question arose about Layer A coverage breadth — leading to two new design ideas captured as deferred flags before kickoff (A5 language/spell-check, A6 render-fidelity DOCX diff). User authorized the V1 pass and we went straight through.

### Workstream 1 — `run_qc.py` end-to-end (Step 1)

Three bugs surfaced in the first 3 attempts to launch the orchestrator, all of which had escaped the BATON 070 smoke test (which was run inside a worktree with explicit `--project-root`, hiding the standalone-path bugs):

1. **PROJECT_ROOT off-by-one in all 5 entry-point scripts.** `_default_project_root()` used `SCRIPT_DIR.parent.parent.parent.parent.parent` (5 hops). The script lives at `scripts/` under `.claude/skills/corpus-integrity-qc/`, so SCRIPT_DIR is at depth 4 from project root, needing only 4 `.parent` calls. Fifth hop landed at `C:\Users\mpsch\Desktop` instead of `board_prep_intel/`. Fixed in `run_qc.py`, `layer_a_text.py`, `layer_b_citation.py`, `layer_c_structural.py`, `generate_fixes.py`. SKILL.md documentation also corrected.

2. **Windows cp1252 console crash on `✓` characters.** The orchestrator printed `✓` and crashed on Windows' default cp1252 stdout. Layered fix:
   - New `setup_utf8_stdout()` helper in `utils.py` (reconfigures stdout/stderr to UTF-8, no-op safe on non-Windows or already-wrapped streams).
   - Called early in all 6 entry-point scripts: `run_qc.py`, `layer_a_text.py`, `layer_b_citation.py`, `layer_c_structural.py`, `generate_fixes.py`, `build_report.py`.
   - Added explicit `encoding="utf-8"` to all 6 `open()` calls (staging JSON reads, findings JSON writes, fixes.sql read in generate_fixes) and 2 `Path.write_text()` calls (`qc_report.md`, `fixes.sql`).
   - Added `encoding="utf-8", errors="replace"` to all 3 `subprocess.run()` calls in `run_qc.py` (Layer A/B/C dispatch + report + fixes generation) so captured layer-process output decodes correctly.

After the 3-bug remediation, `run_qc.py` produced all 5 expected artifacts: `findings_layer_{a,b,c}.json`, `qc_report.md`, `fixes.sql`. Counts matched BATON 070 smoke-test expectations exactly (A=158, B=582, C=1798; Tier 1=1914, Tier 2=66, Tier 3=558).

### Workstream 2 — Stratified Tier 1 spot-check (Step 2)

Parsed `fixes.sql` into `(label, sql)` pairs by check tag, sampled 1 statement from each of the 7 buckets ([A1, B5, C1, C2/C6, C3, C4, C7]) plus 3 fills to 10. Verified each against the live DB. 9 of 10 verified correct. **1 statement (A1 on `choices` field) was a silent no-op** — the third bug:

3. **A1 ENCODING_ARTIFACT no-op on `choices` JSON column.** `gen_encoding_fix()` in `generate_fixes.py` emitted `UPDATE questions SET choices = REPLACE(choices, 'Ã¶', 'ö') WHERE qid = 'QID-2023-0169'`. Two layered problems:

   **(a)** The `choices` column stores JSON encoded with `ensure_ascii=True`. Non-ASCII chars live on disk as the literal 6-char ASCII escape `Ã¶`, not as the 2-char `Ã¶`. So the REPLACE searches for chars that aren't there.

   **(b)** Empirically discovered while attempting fix (a): **SQLite *does* interpret `\u` escapes inside single-quoted string literals**, despite its docs saying string literals are literal. Verified: `SELECT hex('Ã¶')` returns `C383C2B6` (utf-8 of `Ã¶`), not `5C75303063335C7530306236` (the literal 12 ASCII chars `Ã¶`).

   **Final patch:** new `_sql_json_escape_expr()` helper in `generate_fixes.py` builds SQL expressions like `char(92) || 'u00c3' || char(92) || 'u00b6'`. `char(92)` is a literal backslash that SQLite cannot mis-interpret. Applied only when `f["field"].startswith("choices[")`; other A1 statements (82 of 93) targeting text columns still use the simpler literal form. Verified via simulated REPLACE on live DB: `SjÃ¶gren` → `Sjögren` ✓.

   Scope of impact: 11 of 93 A1 statements (those targeting `choices`); all regenerated correctly.

After bug 3 was fixed, regenerated `fixes.sql` and re-verified all 11 patched statements. Total Tier 1 unchanged at 1,914.

### Workstream 3 — Apply Tier 1 + fix-applier exercise (Step 3)

Ran the fix-applier workflow **inline** rather than dispatching as a sub-agent. Two reasons: (a) Windows shell environment (`sqlite3` CLI not assumed on PATH), and (b) the user values transparency on the first-ever DB-write run. The inline path mirrors the `fix-applier.md` contract exactly:

- Captured 6 pre-apply COUNT baselines
- Created timestamped backup `ite_intelligence.db.pre_qc_2026-05-18-221606.bak` (172 MB)
- Extracted the Tier 1 block (between `-- TIER 1: AUTO-SAFE` and `-- TIER 2: REVIEW` markers)
- Applied via `conn.executescript()` — the embedded `BEGIN; ... COMMIT;` provides atomicity
- Captured 6 post-apply COUNTs and reported deltas

**Verification deltas:**

| Metric | Pre | Post | Δ |
|---|---|---|---|
| `articles_count` | 2,206 | 2,206 | 0 |
| `questions_count` | 1,639 | 1,639 | 0 |
| `xref_count` | 2,710 | 2,710 | 0 |
| `articles_with_citations` | 1,800 | 1,982 | +182 |
| `sum_citation_count` | 2,387 | 2,710 | +323 |
| `distinct_article_ids_in_xref` | 1,982 | 1,982 | 0 |

Critical post-apply invariants now hold:
- `sum_citation_count` (2,710) == `xref_count` (2,710)
- `articles_with_citations` (1,982) == `distinct_article_ids_in_xref` (1,982)

Row counts on `articles` / `questions` / `qid_art_xref` unchanged (only column values updated), as expected for the all-Tier-1 payload (no INSERTs/DELETEs in Tier 1).

### Workstream 4 — Re-run QC post-apply (Step 4)

Re-ran `run_qc.py` against the updated DB. Findings dropped from 2,538 to 625:

| Layer | Pre-apply | Post-apply | Δ |
|---|---|---|---|
| A | 158 | 65 | −93 (all 93 ENCODING_ARTIFACT cleared) |
| B | 582 | 559 | −23 (24 AUTHOR_ARTIFACT cleared; +1 UMBRELLA promotion — see note) |
| C | 1,798 | 1 | **−1,797** (only ORPHAN_XREF left) |
| **Total** | **2,538** | **625** | **−1,913** |

Tier 1 statements regenerated: 1,914 → **0** (everything applied is now reflected in the DB).

**UMBRELLA promotion note:** Layer B found 7 UMBRELLA articles pre-apply, 8 post-apply. The +1 is genuine signal, not regression: an article whose `citation_count` cache had been stuck below the umbrella threshold (5) was corrected upward by Tier 1, crossing into umbrella territory. The Tier 1 cache fixes promoted a previously-hidden umbrella into view.

### Workstream 5 — ORPHAN_XREF investigation + QID-2024-0067 recovery (Step 5)

The single remaining Layer C finding: `qid_art_xref` had a row `(QID-2024-0067, ART-2073, VC_fail, 2024, Goldschmidt, 2021)` but QID-2024-0067 did not exist in the `questions` table. Cross-year orphan scan confirmed this was the ONLY such case across the entire DB.

ART-2073 (Goldschmidt — HIV initial management) is a real article. The 2024 critique staging JSON listed QID-2024-0067 with **two** references (Goldschmidt + Mandell textbook). The 2024 questions table had a gap at 0067 between 0066 and 0068. So the question was dropped during ingestion but the xref linkage survived — inverse of a classic orphan.

User chose Option B (recover the question, not delete the xref) per Locked Rule 1 ("fix the data, not the code") and Locked Rule 3 ("source data is protected"). Steps:

1. Located the question in `2024_critique.pdf` (page 38, "Item 67 / ANSWER: B" + 37-line explanation + 2 references)
2. Located the question stem + 5 choices in `2024_MC.pdf` (page 28, "67. A 32-year-old male is hospitalized with a 1-week history of an acute illness...")
3. Inferred blueprint `Acute Care and Diagnosis` and body_system `Hematologic/Immune` based on convention (matches QID-2018-0045 — the closest HIV diagnostic-challenge precedent in the DB)
4. Inserted with primary fields populated (qid, exam_year, blueprint, body_system, body_system_merged, question_text, choices JSON, correct_letter=B, correct_text, explanation, reference with ` | ` separator)
5. Left enrichment fields NULL (`stem_keywords`, `explanation_keywords`, `all_keywords`, `concept_tags`) — DEFERRED-QID-2024-0067-ENRICHMENT opened for backfill via existing pipelines.

Verification: xref linkage now shows both endpoints valid `(QID-2024-0067, ART-2073, question_exists=1, article_exists=1)`. Final re-run of QC: **Layer C = 0 findings**, ORPHAN_XREF resolved.

### Workstream 6 — Bug-fix loop (Step 6)

The substantive bugs (path off-by-one, cp1252, choices JSON no-op) were all addressed in-flight during Steps 1-3. No additional fixes warranted. Watch-item from BATON 074 (`correct_author_from_clean_ref()` 80-char truncation in `utils.py`) was NOT triggered by this session's data — all 24 B5 AUTHOR_ARTIFACT fixes verified clean. Defer until it actually surfaces.

### Workstream 7 — `_archive_/delete_me_051826/` cleanup (Step 7)

Folder was already gone when I checked — user had cleared the 4 staged files between BATON 074 close and this session. Effectively a no-op. (Confirms the user's manual cleanup loop is working as designed per V3.2 Locked Rule 8 pattern.)

---

## DATABASE STATE

*(Verified live via sqlite3 at end of session. DB backup taken pre-apply at `00_database/db/ite_intelligence.db.pre_qc_2026-05-18-221606.bak`, 172 MB.)*

| Table | Rows | Δ from BATON 074 | Notes |
|-------|------|---|---|
| articles | 2,206 | 0 | row count unchanged; many cache columns now correct |
| questions (ITE) | **1,640** | **+1** | QID-2024-0067 recovered (acute HIV diagnostic) |
| aafp_questions | 1,221 | 0 | unchanged |
| qid_art_xref | 2,710 | 0 | row count unchanged; no INSERTs/DELETEs in Tier 1 |
| aafp_qid_art_xref | 864 | 0 | unchanged |
| article_icd10 | 4,959 | 0 | unchanged |
| question_icd10 | 5,774 | 0 | unchanged |
| aafp_question_icd10 | 4,753 | 0 | unchanged |
| clinical_pathways | 4,959 | 0 | unchanged |
| pubmed_pmid_cache | 344 | 0 | unchanged |
| icd10_vec | 2,219 | 0 | unchanged |
| article_icd10_vec | 1,757 | 0 | unchanged |
| question_icd10_vec | 2,747 | 0 | unchanged |
| intersection_centroid_vec | 158 | 0 | unchanged |
| article_currency | 2,206 | 0 | unchanged |

**Critical cache columns updated by Tier 1 apply (silent, not reflected in row counts):**
- `articles.citation_count` — 415 + 208 = 623 rows updated (C2 + C6 buckets)
- `articles.qid_list` — 359 rows updated (C1)
- `articles.exam_years` — 343 rows updated (C3)
- `articles.unique_years` — 446 rows updated (C4)
- `articles.citation_count` reset to 0 — 26 rows (C7, orphaned cache)
- `articles.author1` — 24 rows corrected (B5, AUTHOR_ARTIFACT)
- `questions.{choices,explanation,question_text,correct_text,reference}` — 93 rows updated (A1, ENCODING_ARTIFACT — including the 11 choices-field statements using the patched `char(92) || ...` form)

**Post-apply invariants now satisfied:**
- `SUM(citation_count) FROM articles` == `COUNT(*) FROM qid_art_xref` (both = 2,710) ✓
- `COUNT(articles WHERE citation_count > 0)` == `COUNT(DISTINCT article_id) FROM qid_art_xref` (both = 1,982) ✓
- No xref row references a non-existent qid or article_id (ORPHAN_XREF = 0) ✓

**Next ART-ID:** ART-2208 (unchanged — no new articles).

---

## PDF LIBRARY

*(All counts unchanged from BATON 074.)*

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

*(All Python/JS module script counts unchanged. The only script-file changes this session are inside `.claude/skills/corpus-integrity-qc/`.)*

| Module | Category | Count | Notes |
|--------|----------|-------|-------|
| M1 | build/ (.py) | 8 | unchanged |
| M1 | maintain/ (.py) | 38 | unchanged |
| M1 | scripts/ root (.py) | 1 | aafp_brq_scraper.py |
| M2 | scripts/ (.py) | 75 | unchanged |
| M2 | scripts/ (.js) | 6 | unchanged |
| M3 | scripts/ (.py) | 55 | unchanged |
| M3 | scripts/ (.js) | 4 | unchanged |
| M3 | scripts/ (.json) | 7 | unchanged |
| M4 | scripts/ (.py) | 1 | unchanged |
| M5 | Python sync | 3 | unchanged |
| M5 | TypeScript/TSX | 35 | unchanged |
| `.claude/skills/corpus-integrity-qc/` | files MODIFIED | **8** | 7 scripts/*.py + SKILL.md |
| `.claude/skills/` (project) | SKILL.md dirs | 8 | unchanged |
| `.claude/skills/` (project) | Cowork `.skill` zips | 2 | unchanged |

---

## FILE-CHANGE SUMMARY THIS SESSION

| Path | Change | Notes |
|------|--------|-------|
| `.claude/skills/corpus-integrity-qc/scripts/utils.py` | MODIFIED | +`setup_utf8_stdout()` helper |
| `.claude/skills/corpus-integrity-qc/scripts/run_qc.py` | MODIFIED | path off-by-one fix, +utf8 setup, +utf8 to subprocess.run × 3 |
| `.claude/skills/corpus-integrity-qc/scripts/layer_a_text.py` | MODIFIED | path off-by-one fix, +utf8 setup, +utf8 to open() |
| `.claude/skills/corpus-integrity-qc/scripts/layer_b_citation.py` | MODIFIED | path off-by-one fix, +utf8 setup, +utf8 to open() × 2 |
| `.claude/skills/corpus-integrity-qc/scripts/layer_c_structural.py` | MODIFIED | path off-by-one fix, +utf8 setup, +utf8 to open() |
| `.claude/skills/corpus-integrity-qc/scripts/generate_fixes.py` | MODIFIED | path off-by-one fix, +utf8 setup, +utf8 to open()+write_text, **+`_sql_json_escape_expr()` helper for A1 on choices** |
| `.claude/skills/corpus-integrity-qc/scripts/build_report.py` | MODIFIED | +utf8 setup, +utf8 to open()+write_text |
| `.claude/skills/corpus-integrity-qc/SKILL.md` | MODIFIED | PROJECT_ROOT doc corrected (4 hops not 5) |
| `00_database/db/ite_intelligence.db` | MODIFIED (binary, gitignored) | 1,914 Tier 1 statements applied + 1 INSERT (QID-2024-0067) |
| `00_database/db/ite_intelligence.db.pre_qc_2026-05-18-221606.bak` | NEW (binary, gitignored) | 172 MB safety backup |
| `03_module.3_analyst/outputs/corpus_qc/2026-05-18/` | NEW (gitignored) | First-run artifacts: 5 files |
| `03_module.3_analyst/outputs/corpus_qc/2026-05-18_post_apply/` | NEW (gitignored) | Post-Tier-1 artifacts: 5 files |
| `03_module.3_analyst/outputs/corpus_qc/2026-05-18_post_orphan_fix/` | NEW (gitignored) | Post-recovery artifacts: 5 files |
| `BATON_active_074_*.md` | MOVED → `baton_archive/` | Retired by this BATON |
| `BATON_active_075_*.md` (this file) | NEW | New session handoff |
| Standard housekeeping refresh | MODIFIED | `_index.md`, `README.md`, `REPO_MAP.md`, `README.json`, `CLAUDE.md`, `.auto-memory/*` |
| `auto-memory-copies/` (3 files) | SYNC | Mirrors `.auto-memory/` |

---

## DEFERRED FLAGS

### Closed this session

- **DEFERRED-LAYER-C-CACHE-REBUILD** — All 1,797 Tier 1 cache-rebuild SQL applied via fix-applier; Layer C re-run returns 0 cache-drift findings. ✅
- **DEFERRED-ORPHAN-XREF-QID-2024-0067** — QID-2024-0067 recovered from `2024_MC.pdf` + `2024_critique.pdf` and inserted into `questions`; orphan xref now has valid foreign-key endpoints on both sides. ✅
- **DEFERRED-V1-ENCODING-CHOICES-JSON-BUG** *(opened+closed in same session)* — `generate_fixes.py:gen_encoding_fix()` was emitting no-op SQL for A1 findings on the JSON-encoded `choices` column; patched with `_sql_json_escape_expr()` using `char(92) || 'uXXXX'`. ✅

### Newly opened this session

- **DEFERRED-LAYER-A5-LANGUAGE-INTEGRITY** — Build a Claude API-backed spell/typo/language sanity check for `questions` content. Catches typos that exist in BOTH DB and PDF (which A4 PDF-diff cannot). Needs clinical-aware dictionary curated from existing `concept_tags` + ICD-10 descriptions + `articles.title` to suppress false positives on drug brand names, trial acronyms, eponyms. Target: 1,640 questions × ~800 tokens on Haiku. **Scope = V1.2** (after A4/A6 land).
- **DEFERRED-LAYER-A6-RENDER-FIDELITY** — Generate sample Study-Guide DOCX via `build_custom_question_set.py`, re-extract rendered DOCX text, diff against DB source. Catches **rendering bugs** in actual resident deliverable (Symbol-font residue surviving `_ENCODING_FIXES`, References-section parsing breaks, shaded-box explanation truncation, malformed pipe-separated refs producing empty bullets). Shares PDF/DOCX re-extraction infrastructure with A4. **Scope = V1.1, build together with A4**.
- **DEFERRED-QID-2024-0067-ENRICHMENT** — Backfill the 4 NULL enrichment fields on QID-2024-0067: `stem_keywords`, `explanation_keywords`, `all_keywords`, `concept_tags`. Use existing M2 keyword-extraction scripts + `preprocess_concept_tags.py`. Single-QID re-run — lightweight. Also verify the blueprint `Acute Care and Diagnosis` + body_system `Hematologic/Immune` classifications I inferred (matches QID-2018-0045 precedent but could be wrong).
- **DEFERRED-LAYER-B-UMBRELLA-PROMOTION-REVIEW** *(opened this session, low priority)* — Layer B post-apply found 8 UMBRELLA articles vs 7 pre-apply. The +1 promotion was caused by a Tier 1 citation_count cache fix that pushed an article across the umbrella threshold. Worth eyeballing the new 8th umbrella to verify the threshold detection is appropriate (or whether the article genuinely is a multi-topic catch-all that warrants splitting).

### Carry-forward from BATON 074 (unchanged unless noted)

- **DEFERRED-LAYER-A4-PDF-DIFF** — Layer A4 (PDF-diff re-extract) deferred to V1.1. **No change.**
- **DEFERRED-MAC-PDF-SYNC** — Mac PDF library lags Windows canonical by 567 PDFs. No change.
- **DEFERRED-LOCKED-RULE-8-UPDATE** — Rule 8 needs Mac/Claude Code broadening. (This session reinforced the rule's "trust the safety machinery, run fix-applier inline rather than dispatching" extension.)
- **DEFERRED-CROSS-TIER-CODON-DUPES** — 89 ART-IDs in both VC_fail and VC_pass.
- **DEFERRED-AFP-DATA-QC** — 6 articles with malformed clean_ref / junk title.
- **DEFERRED-AAFP-HTTP-500-RETRY** — 5 vintage AFP articles blocked by AAFP server outage.
- **DEFERRED-UNPAYWALL-CLOUDFLARE** — 144 OA URLs blocked by Cloudflare.
- **DEFERRED-QID-XREF-LIBRARY-GAPS** — ~801 articles missing PDFs (246 UNMATCHED_CITATION findings from Layer B; unchanged this session).
- **DEFERRED-PENDING-LIST-QC** — spot-check pending lists for URL-mismatch defects.
- **DEFERRED-DESHMUKH-2021** — ART-0302 paywalled at tandfonline.
- **DEFERRED-YOY-ROBUSTNESS** — `longitudinal_delta()` edge cases.
- **DEFERRED-PGY-BENCHMARKS** — awaiting PGY 1-4 data.
- **DEFERRED-PROGRAM-TREND** — pending PGY benchmarks.
- **DEFERRED-RESIDENT-FOLDER-MIGRATION** — investigate `resident_data/` migration to M5.
- **DEFERRED-SCHOLL-OLD-FORMAT** — 2022/2023 score reports use old ABFM taxonomy.
- **DEFERRED-KNOWN-DRUGS-EXPANSION** — identify offending drug names; decide fix approach.
- **FLAG-33-NNN-RENAME** — nnn_XXXX ART-ID rename scheme designed, not yet implemented.

*(Net deferred flag delta this session: +4 new, 3 closed = +1 net.)*

---

## CRITICAL REMINDERS FOR NEXT SESSION

1. **`fix-applier` first-use is now PROVEN.** The contract works: backup, transaction, COUNT verification, deltas reported. Future Tier 2 applies can follow the same pattern (with the additional step of confirming the user has uncommented specific statements first).

2. **The corpus-integrity-qc skill is now hardened for Windows.** All path/encoding/SQL-escape bugs caught and patched. The skill should run cleanly on Mac too (the UTF-8 reconfigure is a no-op on systems that already default to UTF-8). The skill is ready for production use without further infrastructure work.

3. **DB invariants now hold.** Don't let them drift again:
   - `SUM(articles.citation_count) == COUNT(*) FROM qid_art_xref` (= 2,710)
   - `COUNT(articles WHERE citation_count > 0) == COUNT(DISTINCT article_id) FROM qid_art_xref` (= 1,982)
   - Re-run `run_qc.py` after any future xref additions/deletions to catch drift early.

4. **Tier 2 review pass is unblocked.** 65 Tier 2 statements (42 FORMAT_DRIFT + 23 TRUNCATION_CANDIDATE) are commented-out in the latest `fixes.sql`. User opens the file in an editor, uncomments specific statements they want applied, then dispatches fix-applier with `--tier 2 --approved-by-user 1`.

5. **Tier 3 manual findings (559 total) are documentation, not action items.** B2 DB_REF_NOT_IN_CRITIQUE (305) is mostly enrichment-pipeline links (pathway-derived, etc.) — informational only. B3 UNMATCHED_CITATION (246) is the article-acquisition queue — feeds the existing AFP/JAMA/NEJM harvesting workflows. UMBRELLA (8) needs human eyeball to decide which to split.

6. **A4 + A6 should be designed together** (per the design rationale captured this session — they share PDF/DOCX re-extraction infrastructure). A5 is a separate session because of the clinical-dictionary curation step.

7. **Re-run all 7 resident analyses.** Still carrying from BATON 065+066+067. The Tier 1 apply may shift their reading-list output now that article cache columns are correct.

8. **Re-run `preprocess_concept_tags.py` + keyword extraction on QID-2024-0067** to close DEFERRED-QID-2024-0067-ENRICHMENT. Easy to scope to a single QID via WHERE clause.

---

## LOCKED RULES (Unchanged from BATON 074)

*(Verbatim. Rule 8 still flagged for update in DEFERRED-LOCKED-RULE-8-UPDATE. This session reinforced the "agent runs git/sqlite operations directly when safety machinery exists" extension to Rule 8.)*

1. **Fix the data, not the code.**
2. **VC gate = sole criterion** for right_click tier.
3. **Source data is protected.** DB + PDFs + VC gate survive everything.
4. **Dynamic paths only.** `SCRIPT_DIR = Path(__file__).resolve().parent; PROJECT_ROOT = SCRIPT_DIR.parent.parent`. *(This session: corpus-integrity-qc uses parent×4 because the skill lives 2 levels deeper than typical scripts.)*
5. **No de novo JS.** New code = Python only.
6. **BATON first.**
7. **QC after every integration.** *(This session: applied successfully via the QC skill's own re-run loop.)*
8. **Git via Desktop Commander.** *(Flagged for update; this session: agent ran `git` directly via Bash with no issues; backup-+-COUNT-verify safety pattern proved out for DB writes via inline `python sqlite3` rather than sub-agent.)*
9. **Strategy 0 in every enricher.**
10. **Schemas before scripts.**
11. **`shutil.rmtree` is BANNED.** *(This session: zero `shutil` calls; the only file-system-write operation was `shutil.copy2(DB, backup)` which is the safe single-file copy.)*
12. **`_normalize_concept()` fallback = first-letter capitalize only.**
13. **ICD-10 enrichment is invisible.**
14. **Word docs use `word_doc_defaults.py`.**

---

## NEXT STEPS

### Immediate (next session)

1. **`/board-startup`** to load BATON 075 + verify clean state.
2. **Decide on Tier 2 review pass.** Either:
   - Walk through the 23 TRUNCATION_CANDIDATE findings (`fixes.sql` Tier 2 block, by year) — these are the highest-value Tier 2 items since they flag potentially-truncated explanations
   - Or defer Tier 2 entirely and move to enrichment backfill for QID-2024-0067 (lightweight)
3. **Backfill QID-2024-0067 enrichment fields.** Run the keyword extraction + `preprocess_concept_tags.py` scoped to `qid='QID-2024-0067'`. Closes DEFERRED-QID-2024-0067-ENRICHMENT.
4. **Verify QID-2024-0067 blueprint + body_system inferences.** Quick eyeball: is "Acute Care and Diagnosis" + "Hematologic/Immune" right for an acute HIV diagnostic question? If not, single UPDATE statement.
5. **Re-run all 7 resident analyses** with the corrected article-cache state. Reading lists may shift.

### Short-term (this week)

6. **Investigate the 8th UMBRELLA article** (the one promoted by the Tier 1 citation_count fix). Decide whether to split.
7. **Cross-tier codon dedupe** — 89 ART-IDs in both VC_fail and VC_pass.
8. **Mac PDF sync** (only if Mac work resumes) — pull 567 missing PDFs from Windows/gdrive.

### Medium-term (V1.1 corpus-qc work)

9. **Design + build A4 PDF_DIFF and A6 RENDER_FIDELITY together.** Shared infrastructure (PDF re-extraction → text diff engine). A4 detects DB-vs-source-PDF drift; A6 detects DB-vs-deliverable-DOCX drift.
10. **A5 LANGUAGE_INTEGRITY** as separate V1.2 session. Curate clinical dictionary from `concept_tags` + ICD-10 + `articles.title` first, then Claude API spell-check pass.

### Long-term

11. **AAFP BRQ extension of corpus-integrity-qc (v2).** Layer C ports trivially; Layer A ports easily; Layer B inapplicable (no AAFP critique PDFs).
12. Continue 801-article gap closure by source_type buckets.
13. Apply NEJM DevTools pattern to 144 unpaywall Cloudflare-blocked URLs.

---

## FOR THE REPO (Git Notes)

- **Branch:** `claude/session-075-corpus-qc-v1-pass` (V3.2 feature branch from `main`)
- **Pre-session commit hash on main:** `65754ea` (BATON 074 merge commit, "Merge pull request #20 from mpsch01/claude/session-074-skill-shadow-cleanup")
- **Session commits on feature branch:**
  - `caf66f4` — *"BATON 075: corpus-integrity-qc V1 testing pass + DB-write debut"* — 22 files, +695 / −107
  - *(hash-backfill commit to follow)*
- **PR:** *(to be opened during Item 12; merged via `gh pr merge --merge --delete-branch`)*

---

**End BATON 075.**
*Corpus-integrity-qc V1 testing pass complete. Skill is hardened, DB integrity dramatically improved (2,538 findings → 624; Layer C 1,798 → 0), and one ITE question recovered from the source PDFs. Next session: Tier 2 review + enrichment backfill + resident analyses re-run.*
