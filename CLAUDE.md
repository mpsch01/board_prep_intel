# Memory — #PROJECT_OVERHAUL

## Who You're Working With
**Mikey** (Michael Scholl) — Family medicine physician and residency program director. Self-taught data architect. Speaks in concepts and biological analogies. Strong architectural instincts — his design calls are almost always better than first proposals. Has API access (key in env vars). Runs long-running code himself (copy-paste-run pattern).

---

## The Project in One Sentence
ABFM ITE Intelligence System — a queryable Family Medicine board exam knowledge base (1,629 questions, 2018–2025) linked to a clinical guideline library (1,936 articles, 404 PDFs) via a structured SQLite pipeline.

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
| **right_click / $right_click$** | M2 completed tier: VC_pass + fully enriched (DOCX exists) |
| **local_lite** | M2 completed tier: VC_fail + fully enriched (DOCX exists) |
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
| Active BATON | `BATON_active_015_20260327_aafp_brq_scraper_built_citation_gap_complete.md` |
| DB articles | 1,936 |
| DB questions (ITE) | 1,629 (2018–2025) |
| DB questions (AAFP BRQ) | 1,221 (`aafp_questions` table — separate from `questions`) |
| PDFs | 404 across 4 tiers |
| qid_art_xref | 2,470 (all 8 years: 2018–2025) |
| M1 scripts | 9 build + 16 maintain + aafp_brq/scraper (self-contained build sequence) |
| M2 scripts | 45 Python + 6 JS + 1 JSON + 4 Windows (all paths dynamic) |
| M3 scripts | 4 Python + 1 JS + 2 JSON config |
| Next ART-ID | ART-1938 |
| Git branch | `main`, latest `10d8208` |

→ Full state: `.auto-memory/project_overhaul_state.md` and `.auto-memory/project_current_db_state.md`

---

## Module Map

| Module | Path | What it does |
|--------|------|--------------|
| M1 Warehouse | `01_module.1_warehouse/` | PDF library (4 tiers) + build/ + maintain/ scripts |
| M2 Processor | `02_module.2_processor/` | Extraction, enrichment, DOCX builders + source/ inputs |
| M3 Analyst | `03_module.3_analyst/` | ICD-10 tagging, pathways, trends, score analysis |
| M4 Sandbox | `04_module.4_sandbox/` | Experiments, agents |
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
8. **Git from Windows.** VM can stage/commit but cannot `rm` NTFS files. Deletions happen from Windows.
9. **Strategy 0 in every enricher.** Codon parse is always the first matching strategy.
10. **Schemas before scripts.** SQL `CREATE TABLE` defined before build scripts are written.

→ Full principles: `.auto-memory/rebuild_structuring_guidelines.md`

---

## Next Steps (as of BATON 015, 2026-03-27)
1. **Windows:** Archive BATONs 013 + 014 → `baton_archive/`; delete sandbox originals per `04_module.4_sandbox/_DELETE_THESE_FROM_WINDOWS.txt`
2. **AAFP ref matching second pass** — 578 unmatched refs; volume/page extraction + title keyword match for guidelines → target 70-80%
3. **Build `aafp_qid_art_xref` table** — parallel to qid_art_xref; populate from `aafp_questions.article_id` + second-pass matches
4. **AAFP-ITE lag analysis** — after xref populated; query shared article citations, compute timing delta, build predictive watch list
5. **Build designed scripts** — `article_citation_trend` table + `update_citation_trends.py` (M1/maintain/) + `extract_ite_critique_refs.py` (M2/scripts/)
6. **229 citation gap articles** — 88 AFP batch-downloadable from `null_clean_ref_missing_articles_20260326.csv`; codon rename → ingest → enrich
7. **Intelligence 2.0 Layer 2** — `article_currency` table via PubMed MCP
