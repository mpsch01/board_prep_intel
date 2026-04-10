# BATON 051 — Module 5 Housekeeping & Documentation
**Date:** 2026-04-09  
**Branch:** main  
**Git Hash:** 45065a1  
**Status:** SHORT session — no new code written, no DB changes. Module 5 scaffold documented (added by Copilot 2026-04-08).

---

## Session Summary

This was a documentation and verification session. No new scripts were built and no database modifications were made. The primary discovery was that **Copilot had added a complete Module 5 web platform scaffold** via two GitHub commits on April 8 (commits 081bdf7 + 45065a1), which were already synced to the local repository at session start.

### What Was Discovered / Documented

#### 1. **Module 5 Web Platform (05_module.5_web/)**
Added by Copilot via GitHub commits on 2026-04-08.

**Architecture:**
- **Frontend:** Next.js 15 (Netlify)
- **Backend:** Supabase (PostgreSQL + pgvector + Auth + RLS)
- **CMS:** Sanity (editorial workflow)
- **Microservice:** Railway (FastAPI parser)
- **Embeddings:** OpenAI text-embedding-3-small (1536d)

**Two Resident & Faculty Audiences:**
- Residents: score upload, assessments, analytics dashboard, article library search
- Faculty: NL search, curriculum management, article browser

**File Inventory:**
- 3 Python sync scripts: sqlite_to_supabase.py, vector_sync.py, supabase/migrations/
- 35 TypeScript/TSX files (components, pages, API routes, hooks)
- 5 SQL migration files (initial schema + schema evolution)
- Complete env template (NEXT_PUBLIC_* + service credentials)

**Code review fixes already applied (during discovery):**
- CORS headers configured for Netlify origin
- Auth bypass removed from RLS policies
- SQL injection vectors closed
- Null safety checks added to embedding payload
- Magic constants extracted to env variables
- Missing /api/question-sets GET route added

#### 2. **M4 Validation Script**
- nl_search_validation.py added to 04_module.4_sandbox/ — validates pgvector NL search pipeline end-to-end

#### 3. **Project Documentation Sweep**
- CLAUDE.md updated with Module 5 intro + stack summary
- _index.md updated with Module 5 paths
- README.json updated
- REPO_MAP.md updated
- .auto-memory/project_overhaul_state.md updated

#### 4. **Script Count Correction**
- M3 actual count is 15 Python (not 14 as previously listed) — ite_analyzer_v2.py verified present

---

## VERIFIED RECON DATA

**Date:** 2026-04-09  
**Git Hash:** 45065a1  
**Git Branch:** main  
**GitHub Remote:** https://github.com/mpsch01/board_prep_intel (private)

### DB State (Verified Live)

| Table | Rows |
|-------|------|
| articles | 1,985 |
| questions (ITE) | 1,629 |
| aafp_questions | 1,221 |
| qid_art_xref | 2,470 |
| aafp_qid_art_xref | 864 |
| article_icd10 | 4,020 |
| question_icd10 | 5,218 |
| aafp_question_icd10 | 4,753 |
| clinical_pathways | 3,971 |
| pubmed_pmid_cache | 344 |
| article_icd10_vec | 1,757 |
| question_icd10_vec | 2,747 |
| icd10_vec | 2,219 |
| article_currency | 1,985 |
| article_citation_trend | 1,740 |

**Next ART-ID:** ART-1987

### PDF Library State

| Tier | Count |
|------|-------|
| VC_fail | 630 |
| VC_pass | 168 |
| local_lite | 117 |
| right_click | 58 |
| **ITE Total** | **973** |
| AAFP | 15 |
| ITE exams | 16 |
| Dupes archive | 14 |

### Script Counts

| Module | Category | Count |
|--------|----------|-------|
| M1 | Build (Python) | 6 |
| M1 | Maintain (Python) | 26 |
| M2 | Python | 75 |
| M2 | JavaScript | 6 |
| M3 | Python | 15 |
| M3 | JavaScript | 2 |
| M3 | JSON config | 1 |
| M4 | Python | 1 (nl_search_validation.py) |
| M5 | Python | 3 (sync scripts) |
| M5 | TypeScript/TSX | 35 |
| M5 | SQL migrations | 5 |

---

## Deferred Flags (Carry Forward from BATON 050)

### DEFERRED-YOY-ROBUSTNESS
**What:** Year-over-year longitudinal section in ite_report_builder_v2.js needs more robust implementation.  
**Why Deferred:** Initial implementation works for exploratory analysis but fails silently on edge cases.  
**Needs Fixing:** Missing scaled scores, partial year data, multi-year gaps, N>2 year comparisons.  
**Next Action:** Expand longitudinal_delta in ite_analyzer_v3.py; add null checks in renderYoYSection() JS.

### DEFERRED-PRACTICE-Q-COVERAGE
**What:** Practice question engine returns 0-question warnings for 7 dimensions: Foundations, Preventive, Cardiovascular, Respiratory, Sexual and Reproductive, Psychiatric, Behavioral.  
**Why Deferred:** Root cause unclear — could be qid_art_xref gaps, question_icd10 tagging, or blueprint edge cases.  
**Next Action:** Query qid_art_xref for these dimensions; cross-check question_icd10 coverage by dimension; inspect blueprint tagging.

### DEFERRED-PGY-BENCHMARKS
**What:** Add PGY 1–4 expected score % ranges to Executive Summary.  
**Why Deferred:** Awaiting Mikey's baseline data.  
**Next Action:** Receive PGY benchmarks from Mikey; create pgy_benchmarks.md in key_data_files/; integrate into report_config.json and ite_analyzer_v3.py.

### DEFERRED-AAFP-PDF-RETRY
**What:** Re-run exa_pdf_downloader against AAFP site for stalled downloads.  
**Why Deferred:** AAFP site intermittently unavailable; downstream of network recovery.  
**Next Action:** Monitor AAFP site stability; re-run exa_pdf_downloader when available.

### DATABASE_GUIDE.md Relocation (CARRY from BATON 049)
**What:** Finalize git add/rm to register as rename instead of delete + new file.  
**Why Deferred:** Git index showing D+A instead of R; minor cosmetic issue.  
**Next Action:** Run git rm old path + git add new path; verify git status shows R flag; commit.

---

## Next Steps

### Immediate
1. **DEFERRED-YOY-ROBUSTNESS** — Expand longitudinal_delta edge-case handling in ite_analyzer_v3.py (handle missing years, null scores, >2-year spans)
2. **DEFERRED-PRACTICE-Q-COVERAGE** — Query qid_art_xref for the 7 dimensions with 0 questions; investigate root cause
3. **DOCX Review** — Mikey to verify Pjetergjoka_2024/2025 DOCX output (YoY table render, practice Q dimension spread)

### Short-term
4. **Module 5 Setup** — Provision Supabase project, run migrations, sync SQLite → Supabase, test vector search, deploy Railway FastAPI, deploy Netlify frontend
5. **DEFERRED-PGY-BENCHMARKS** — Receive PGY 1–4 baseline data from Mikey; integrate into report Executive Summary
6. **DATABASE_GUIDE.md Relocation** — git rm old + git add new to register rename; commit
7. **DEFERRED-AAFP-PDF-RETRY** — Re-run exa_pdf_downloader when AAFP site stabilizes

---

## Locked Rules Reminder
1. **Fix the data, not the code** — clean data upstream; avoid script complexity
2. **VC gate = sole criterion** for right_click tier; DB membership alone insufficient
3. **Source data protected** — DB + PDFs + VC gate survive everything; derived files disposable
4. **Dynamic paths only** — Python: `SCRIPT_DIR = Path(__file__).resolve().parent; PROJECT_ROOT = SCRIPT_DIR.parent.parent`; JS: `path.resolve(__dirname, "../../")`
5. **No de novo JS** (rule relaxed per feedback) — use JS when needed; flag if multilingual clutter accumulates
6. **BATON first** — read active BATON before any work
7. **QC after every integration** — schema-level column-by-column population comparison
8. **Git via Desktop Commander** — use Python subprocess helper; cannot rm NTFS files
9. **shutil.rmtree BANNED** — use explicit file-by-file deletion or PowerShell Remove-Item
10. **Strategy 0 in every enricher** — codon parse always first matching strategy
11. **Schemas before scripts** — SQL CREATE TABLE defined before build scripts

---

## For Next Claude Instance (Start Here)

- **Read this BATON first** before any work
- **Module 5 is live:** web platform scaffold in 05_module.5_web/ — code review fixes already applied
- **Five deferred flags carry forward:** YOY robustness, practice Q coverage investigation, PGY benchmarks (awaiting Mikey), AAFP PDF retry, DATABASE_GUIDE.md git rename
- **DB state is current** as of 2026-04-09 — no changes this session
- **Active git hash:** 45065a1 on main branch
- **Key files:**
  - `.auto-memory/project_overhaul_state.md` — full module map and state
  - `CLAUDE.md` — project memory and locked rules
  - `00_#PROJECT_OVERHAUL/_index.md` — ground-truth directory map
  - `05_module.5_web/` — Module 5 web platform (Next.js + Supabase + FastAPI)
  - `key_data_files/session_hy_inserts_v7.json` — VC gate (352 citations)
- **Next immediate action:** address DEFERRED-YOY-ROBUSTNESS or DEFERRED-PRACTICE-Q-COVERAGE (per Mikey's priority)
