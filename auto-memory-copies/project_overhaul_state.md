---
name: project_overhaul_state
description: Current PROJECT_OVERHAUL state as of BATON 028 (2026-03-31) — ICD-10 symmetry complete, PubMed crawler built, Layer 2 seeded
type: project
---

**Project:** ABFM ITE Intelligence System (Family Medicine board exam knowledge base)
**Root (Windows):** `C:\Users\mpsch\Desktop\claude_knowledge\00_#PROJECT_OVERHAUL\`
**Active BATON:** `BATON_active_028_20260331_icd10_symmetry_complete.md`
**Git:** `main`, latest committed `066a94f` (commit pending: 6 new M2 scripts + BATONs + housekeeping)

---

## Current Phase: ICD-10 Symmetry Complete

BATON 028 session completed the ICD-10 symmetry work that was the primary deferred flag from BATON 027. Both question banks and both article levels now have ICD-10 coverage. Zero API cost — all propagation and PubMed eutils.

**What was built:**
- `build_ite_question_icd10.py` — propagation from article_icd10 → qid_art_xref → NEW `question_icd10` table (5,284 rows, 92.8% ITE coverage)
- `backfill_aafp_article_icd10.py` — reverse propagation to fill 86 AAFP articles in article_icd10 (+282 rows)
- `build_pubmed_citation_icd10.py` — PubMed eutils crawler for 377 JOURNAL_MISSING citations → 344 PMIDs → MeSH → 921 new aafp_question_icd10 rows; 91.2% resolution rate
- `apply_aafp_related_cap.py` — tier-aware cap on aafp_question_icd10 related codes (408 rows trimmed)
- `pubmed_pmid_cache` table — NEW — 344 rows; Layer 2 seed for article_currency

---

## Module State

| Module | Location | Scripts | Status |
|--------|----------|---------|--------|
| M1 Warehouse | `01_module.1_warehouse/` | 9 build + 16 maintain + aafp_brq/scraper | Self-contained; PDF download (49 articles) pending |
| M2 Processor | `02_module.2_processor/scripts/` | 65 Python + 6 JS + 1 JSON + 4 Windows | +4 scripts this session |
| M3 Analyst | `03_module.3_analyst/` | 5 Python + 1 JS + 2 JSON config | Unchanged |
| M4 Sandbox | `04_module.4_sandbox/` | Experiments placeholder | Cleanup pending |
| DB | `00_database/db/ite_intelligence.db` | Source of truth | 1,985 articles, 1,629 ITE Q, 1,221 AAFP Q |

---

## Key Numbers (as of BATON 028, 2026-03-31)

- **DB articles:** 1,985 (next = ART-1987; 49 new AAFP articles awaiting PDF download)
- **DB questions (ITE):** 1,629 (2018–2025, all years complete; blueprint 100%)
- **DB questions (AAFP BRQ):** 1,221 (blueprint 100%, concept_tags 100%)
- **question_icd10 (ITE):** 5,284 rows — NEW — 1,512/1,629 questions (92.8%)
- **article_icd10:** 4,137 rows (+282 AAFP backfill)
- **aafp_question_icd10:** 4,753 rows (~99% AAFP coverage)
- **pubmed_pmid_cache:** 344 rows (Layer 2 seed)
- **PDFs:** 404 across 4 tiers
- **qid_art_xref:** 2,470 rows (all 8 years: 2018–2025)
- **aafp_qid_art_xref:** 864 rows (643 unique questions linked, 52.7%)
- **M2 scripts:** 65 Python + 6 JS + 1 JSON + 4 Windows (all paths dynamic)

---

## ICD-10 Symmetry State (COMPLETE)

| | Article-level | Question-level |
|---|---|---|
| ITE | article_icd10: 4,137 rows | question_icd10: 5,284 rows ✅ |
| AAFP | article_icd10: +282 AAFP rows ✅ | aafp_question_icd10: 4,753 rows ✅ |

---

## Intelligence 2.0 Layer Status

| Layer | Status |
|-------|--------|
| Layer 1 — ICD-10 | COMPLETE — full symmetry both banks (2026-03-31) |
| Layer 2 — PubMed currency | SEEDED — 344 PMIDs in pubmed_pmid_cache. article_currency table not yet built. |
| Layer 3 — Clinical pathways | PARTIAL — 3,093 rows (ART-0002–ART-1397). Rebuild pending (blueprint-based v2). |
| Layer 4 — Trends/alerts | article_citation_trend built, update_citation_trends.py ready to run |

---

## Active Deferred Flags

| Flag | Priority | Description |
|------|----------|-------------|
| CLINICAL-PATHWAY | HIGH | Rebuild clinical_pathways_v2.py — blueprint signal, both banks, full ART range |
| DEFERRED-A | HIGH | PDF download: 49 new AAFP articles ART-1938–1986 |
| Q-ICD10-VEC | MEDIUM | Rebuild question_icd10_vec + article_icd10_vec (both stale) |
| DEFERRED-F | MEDIUM | Intelligence 2.0 Layer 2 — article_currency (344 PMIDs already cached) |
| DEFERRED-B | MEDIUM | update_citation_trends.py — run after DEFERRED-A |
| DEFERRED-D | MEDIUM | 229 citation gap articles (88 AFP batch-downloadable) |
| Q-VEC-GAP | MEDIUM | Fill question_vec gaps: 440 ITE (2018–2019) + 1,221 AAFP |
| DEFERRED-C | MEDIUM | AAFP vs ITE trend comparison |
| DEFERRED-E | LOW | Interactive vector dashboard |

---

## Next Steps (BATON 028 priority order)

1. **Git commit** — 6 new M2 scripts + BATONs 025-028 + CLAUDE.md + README.json + memory files; archive BATONs 025-027
2. **Rebuild clinical_pathways_v2.py** — blueprint-based, both banks, full ART range ART-0002–ART-1985
3. **Rebuild ICD-10 vector layers** — `python scripts/build_icd10_embeddings.py --derive`
4. **PDF download** — 49 articles (ART-1938–1986) → `download_aafp_acquisitions.py`
5. **Intelligence 2.0 Layer 2** — `article_currency` table (344 PMIDs already cached)

---

## Path Convention (locked)

| Module | Pattern | Resolves to |
|--------|---------|-------------|
| M2/scripts | `SCRIPT_DIR = Path(__file__).resolve().parent; PROJECT_ROOT = SCRIPT_DIR.parent.parent` | PROJECT_ROOT |
| M1/scripts/build, M1/scripts/maintain | same | PROJECT_ROOT |
| M3/scripts | `SCRIPT_DIR.parent.parent` | PROJECT_ROOT |
