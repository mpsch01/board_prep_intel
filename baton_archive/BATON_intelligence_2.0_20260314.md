# BATON — ITE Intelligence 2.0: Migration + Architecture Vision
## Session Handoff Document
**Date:** 2026-03-14 (Session 2 of the day — follows diagnostic session)
**Phase:** Architecture design complete. Migration plan locked. 2.0 vision captured.
**Status:** Ready to build. Start with match-folder staging script.

---

## ⚑ WHAT HAPPENED THIS SESSION

This session evolved from "fix the enricher matching" into a complete architectural rethink. The key insight: **instead of building permanent infrastructure to compensate for messy filenames, fix the filenames.** Rename every PDF to codon format, nuke all derivative files, strip the band-aids from the pipeline, and re-process clean.

Then we went bigger: the clean foundation enables **Intelligence 2.0** — four new data layers that transform this from an ITE study tool into a clinical knowledge intelligence system.

### Decisions Made

1. **Codon migration via match-folder staging** — group PDFs with their matched derivatives in review folders, rename from there, then flatten back. Human-reviewable checkpoint before anything irreversible.

2. **Nuke and re-process** — delete all enriched JSONs, DOCX summaries, ITE ref JSONs after rename. Re-run the full pipeline from scratch on clean codon-named files. Fresh extractions with current pipeline = consistent quality.

3. **DB is the foundation, not the target** — the database (all tagging, tiers, QID linkages, vector embeddings, priority scores) survives untouched. It's the source of truth for the migration AND the foundation for 2.0 layers.

4. **Shared `article_resolver.py` module** — single source of truth for PDF→DB matching. Both enrichers and the crosswalk builder import from it. Post-migration this is ~10 lines (codon parse + DB query).

5. **Four new intelligence layers** scoped and designed (see Architecture section).

6. **Alert system** — PubMed-based new article detection, scored against historical ITE patterns. "Alert: possible ITE article" when a new publication matches trending topic + key journal + key author.

### Artifacts Created

| File | Location | Description |
|------|----------|-------------|
| ITE_Intelligence_2.0_Architecture.md | claude_knowledge/ | Full blueprint — migration plan + 4 layers + schemas + build order |
| BATON_intelligence_2.0_20260314.md | claude_knowledge/ | This document |
| `qid_art_xref` table | ite_intelligence.db | NEW TABLE — 1,818 rows, QID ↔ ART-ID reference crosswalk |

### Code Changes Applied

| File | Change | Status |
|------|--------|--------|
| `ite_intelligence_enricher.py` | Added Strategy 0 (codon parse) at top of `lookup_article()` | APPLIED (line 242) |
| `ite_intelligence_enricher_batch.py` | Strategy 0 addition | NOT YET — interrupted by architecture pivot |

---

## ⚑ DEFERRED FLAGS — ACTIVE

### FLAG 1 — ITE Enrichment Quality Dimension
**Status: OPEN** — Add 6th dimension to calibrate.py. Deferred until post-migration pipeline is stable.

### FLAG 3 — Retroactive synthesis batch
**Status: SUPERSEDED** — Full re-process (migration step 7) will regenerate all derivatives with synthesis blocks. No separate retrofit needed.

### FLAG 5 — tier_rationale still generic boilerplate
**Status: OPEN** — Fix during pipeline trim (migration step 6). When simplifying the enricher, upgrade the prompt to generate data-driven rationale.

### FLAG 6 — enrichment_confidence uncalibrated
**Status: OPEN** — Fix during pipeline trim. Compute from match_method + citation_count instead of Claude's guess.

### FLAG 7 — acg_IBD persistent no_match
**Status: OPEN** — Will surface naturally during Tier 2/3 resolution (migration step 2). If it's not in the DB, decide whether to add it or discard the PDF.

### FLAG 10 — Crosswalk Index
**Status: SUPERSEDED** — Crosswalk builder will be rewritten as part of pipeline trim (migration step 6). Post-migration version parses ART-IDs from filenames. ~50 lines replaces 300.

### FLAG 11 — Standout ITE References Without PDFs
**Status: SUPERSEDED** — Previous session proved most "missing" PDFs exist under topic-based names. Migration will establish codon names for all matched PDFs, making the gap list accurate.

### FLAG 12 — Codon Rename Migration
**Status: DESIGN COMPLETE, READY TO BUILD** — 8-step plan locked. See Migration Plan below.

### FLAG 13 — Intelligence 2.0 Layers (NEW)
**Status: DESIGNED** — Four layers scoped with SQL schemas. Build order defined. See Architecture section.

---

## MIGRATION PLAN — 8 STEPS

### Step 1: Match-Folder Staging (Dry Run)
**Build:** `build_match_staging.py`
**Input:** `crosswalk_index.json` + `ite_intelligence.db`
**Output:** Dry-run report of proposed folder pairings

Three tiers:
- **Tier 1 (~192 files):** Crosswalk "full coverage" — enriched JSON has `ite_intelligence` block with ART-ID. High confidence.
- **Tier 2 (~43 files):** Enriched JSON exists but missing `ite_intelligence` block. Has title/year/author — needs resolution.
- **Tier 3 (~25 files):** No enriched JSON at all. Filename + PDF metadata only.

### Step 2: Resolve Tier 2+3 Mismatches
**Method:** Claude API batch call (Anthropic Message Batches API — already built)
**Input:** Title, year, authors from enriched JSON (Tier 2) or filename parsing (Tier 3)
**Fallback:** Vector similarity via `article_vec` embeddings
**Output:** Proposed ART-ID + confidence score per file

Good candidate for Mikey to run locally with API key — ~43-68 calls, low cost.

### Step 3: Human Review
Mikey reviews match folders / dry-run report. Confirms pairings, flags bad matches.
**Nothing irreversible has happened yet.**

### Step 4: Rename PDFs
**Build:** `rename_to_codon.py`
Reads confirmed matches → queries `articles.codon_filename` → renames PDFs.
`--dry-run` default, `--execute` to apply. Writes `rename_log.json` for rollback.

### Step 5: Flatten + Clean
Move renamed PDFs back to `01_pdf_guideline_library/`.
Delete: enriched JSONs, DOCX summaries, ITE ref JSONs, `crosswalk_index.json`.
Archive `rename_log.json`.

### Step 6: Pipeline Trim
Simplify codebase — strip band-aids:
- `ite_intelligence_enricher.py`: Replace 5-strategy cascade with codon-only Strategy 0 + fallback logging
- `ite_intelligence_enricher_batch.py`: Same (or import from shared `article_resolver.py`)
- `build_crosswalk_index.py`: Rewrite — parse ART-IDs from filenames (~50 lines)
- Remove: `_word_freq_in_db()`, `_TITLE_STOPWORDS`, `_strip_apostrophes()`, `_title_keywords()`, Strategies 2-5
- Fix FLAGS 5 + 6 while touching the enricher

### Step 7: Full Re-Process
Run complete pipeline on clean, codon-named library:
`PDF (codon) → extract → synthesize → enrich → DOCX → save JSON`
Every file hits Strategy 0, matches instantly, pulls tagging from DB.

### Step 8: Verify Integrity
- 260/260 PDFs have codon names
- Enricher: 260/260 matched via Strategy 0
- Crosswalk: 260/260 full coverage
- DB tagging data intact (spot-check high-priority articles)
- `qid_art_xref` resolves correctly

---

## INTELLIGENCE 2.0 — FOUR LAYERS

### Layer 1: ICD-10 Diagnostic Linkage
**Table:** `article_icd10` (article_id, icd10_code, icd10_desc, relevance)
**What:** Tags each article with ICD-10 codes. Transforms organization from exam-category to diagnosis-based.
**How:** Claude API batch pass on all 1,397 articles → validate against ICD-10 MCP.
**Unlocks:** "Show me everything related to E11" pulls articles across categories.

### Layer 2: Article Currency via PubMed
**Table:** `article_currency` (article_id, pubmed_id, last_checked, newer_version_pmid, currency_status)
**What:** Tracks whether each article is still current. Queries PubMed for newer publications.
**How:** PubMed MCP — search by author + topic + date range. Monthly refresh.
**Unlocks:** "Gentry 2017 has a 2024 update" — proactive currency alerts.

### Layer 3: Clinical Pathway Engine (The Blending Engine)
**Table:** `clinical_pathways` (article_id, icd10_code, pathway_role, source_org, confidence)
**What:** For any diagnosis, assembles the complete evidence chain from multiple source organizations. AFP + USPSTF + ADA + ACC/AHA → one cohesive reference organized by care stage (screening, diagnosis, first_line_tx, monitoring, referral).
**How:** Builds on Layer 1. Claude API pass + clinical review by Mikey.
**Unlocks:** Personal UpToDate — "Patient has E11 → here's your evidence chain by care stage."

### Layer 4: Predictive Trend Intelligence + Alert System
**Tables:** `topic_trends` (category, exam_year, question_count) + `pubmed_alerts` (pubmed_id, title, alert_trigger, relevance_score, status)
**What:** Tracks exam topic frequency trends 2020-2024. Automated PubMed monitoring for new publications matching ITE-predictive criteria.
**How:** topic_trends = SQL aggregation from existing data (buildable today). pubmed_alerts = scheduled PubMed API queries.
**Unlocks:** "ALERT: Possible ITE article — ACC/AHA updated heart failure guidelines. Heart failure trending ↑40% in ITE questions."

### How They Connect
```
Layer 1 (ICD-10) → connects articles to diagnoses
Layer 3 (Pathways) → assembles articles into clinical logic per diagnosis
Layer 2 (PubMed) → monitors currency of each article in each pathway
Layer 4 (Trends/Alerts) → predicts what's coming, flags new evidence
→ New article feeds back into Layer 1 → Layer 3 → Layer 2 (cycle)
```

### Build Order
| Phase | What | Effort |
|-------|------|--------|
| Phase 0 | Codon Migration (Steps 1-8) | Medium (1-2 sessions) |
| Phase 1 | Layer 1: ICD-10 tagging | Low (batch API call) |
| Phase 2 | Layer 4a: Topic trends (SQL view) | Low (today) |
| Phase 3 | Layer 2: PubMed currency | Medium |
| Phase 4 | Layer 4b: Alert system (scheduled task) | Medium |
| Phase 5 | Layer 3: Clinical pathways (capstone) | High |

Phases 1+2 can run in parallel. Phase 5 is the capstone — build when Layers 1+2 are validated.

---

## EXTERNAL INTEGRATIONS AVAILABLE

| Tool | Status | Role in 2.0 |
|------|--------|-------------|
| PubMed MCP | Connected | Currency checks, new article alerts, citation lookups |
| ICD-10 MCP | Connected | Code validation, hierarchy navigation, code descriptions |
| Microsoft Learn MCP | Connected | FHIR standards, clinical decision support frameworks |
| Anthropic API (local key) | Available | Batch enrichment, ICD-10 tagging, pathway classification, Tier 2 matching |
| Gmail MCP | Connected | Alert delivery |
| Google Calendar MCP | Connected | Study session scheduling, review reminders |
| Google Drive MCP | Connected | Library backup/sync |

---

## DATABASE STATE — AS OF THIS SESSION

### Existing Tables (Preserved)
| Table | Rows | PK | Notes |
|-------|------|----|-------|
| articles | 1,397 | clean_ref | 19 cols. All have codon_filename populated. |
| questions | 1,189 | qid | 16 cols. blueprint only populated 2024-2025. |
| question_ref_pairs | 2,069 | id (auto) | 9 cols. Many-to-many QID↔article via clean_ref. |
| qid_art_xref | 1,818 | qid+article_id | **NEW this session.** Reference crosswalk. |
| article_vec | 1,397 | — | Vector embeddings (requires sqlite-vec). |
| question_vec | 1,189 | — | Vector embeddings (requires sqlite-vec). |

### New Tables Planned (2.0)
- `article_icd10` — Layer 1
- `article_currency` — Layer 2
- `clinical_pathways` — Layer 3
- `topic_trends` — Layer 4a
- `pubmed_alerts` — Layer 4b

### Optional Future Tables
- `study_sessions` — Personal review tracking
- `question_attempts` — Practice question performance
- `article_clusters` — Semantic topic neighborhoods

---

## KEY DATA POINTS

**PDF library:** 260 files. Zero using codon naming. 184 from June 2025 (pre-project), 76 from 2026.
**15+ naming conventions:** afp_, IDSA_, acg_, peds_, neuro_, rheum_, uspstf_, jacc_, aafp_, tox_, APA_, AJKD_, hep_, pulm_, NN_Topic_Author_Year, Author_Year, plus one-offs.
**Crosswalk coverage:** 192 full, 67 partial, 1 need_extraction.
**Priority scoring formula:** citation_count × unique_exam_years × tier_weight (Must-Read=3, Core=2, Supplementary=1).
**Top article:** ART-0590 Higdon/Atkinson 2018, "Oncologic emergencies" — score 54.
**Critical-tier (score 21+):** 17 articles, only 35% extracted.

---

## CRITICAL FILE LOCATIONS

| File | Path |
|------|------|
| This BATON | claude_knowledge/BATON_intelligence_2.0_20260314.md |
| Architecture Blueprint | claude_knowledge/ITE_Intelligence_2.0_Architecture.md |
| Previous BATON (diagnostic) | claude_knowledge/BATON_codon_migration_20260314.md |
| Previous BATON (pipeline) | abfm_prep/02_ite_intelligence/BATON.md |
| ITE Intelligence DB | abfm_prep/02_ite_intelligence/db/ite_intelligence.db |
| Enricher (main) | abfm_prep/02_ite_intelligence/scripts/ite_intelligence_enricher.py |
| Enricher (batch) | abfm_prep/02_ite_intelligence/scripts/ite_intelligence_enricher_batch.py |
| Crosswalk builder | abfm_prep/02_ite_intelligence/scripts/build_crosswalk_index.py |
| Crosswalk JSON | abfm_prep/02_ite_intelligence/crosswalk_index.json |
| PDF library | clinical_guidelines/01_pdf_guideline_library/ |
| Enriched JSONs | clinical_guidelines/03_enriched JSON/ |
| DOCX summaries | clinical_guidelines/02_docx_guideline_library/ |
| Priority list | claude_knowledge/ite_intelligence_priority_list.md |

---

## PRIORITY FOR NEXT SESSION

**Immediate: Migration Step 1**
Build `build_match_staging.py` — the dry-run script that pairs PDFs with their DB matches using crosswalk + DB data. Output a reviewable report before anything moves.

**Then:** Steps 2-8 sequentially, with human review at Step 3.

**After migration complete:** Layer 1 (ICD-10 tagging) + Layer 4a (topic trends SQL view) — both can start immediately on the clean foundation.

---

## DESIGN PRINCIPLES (CARRY FORWARD)

1. **Fix the data, not the code.** Codon rename eliminates the need for complex matching infrastructure.
2. **Each layer is just a table and a query.** No new pipeline steps. Intelligence layers are data on a clean foundation.
3. **Preprocessing over runtime.** Everything deterministic happens up front.
4. **Human checkpoints before irreversible actions.** Dry-run default. Match folders are reviewable.
5. **Modular and additive.** Each layer builds, tests, and validates independently.

---

*Supersedes: BATON_codon_migration_20260314.md (diagnostic session findings — now incorporated into this document and the Architecture Blueprint).*
