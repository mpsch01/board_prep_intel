---
name: project_current_db_state
description: Current ite_intelligence.db state as of BATON 005 (March 24 2026), post 2018-2019 integration
type: project
---

## DB State (Post-2018/2019 Integration — Current)

As of BATON 005 (2026-03-24):
- articles: 1,936 rows (ART-0001 through ART-1937, ART-0404 deleted/merged)
- questions: 1,629 rows (2018–2025)
- qid_art_xref: 1,818 rows (2020-2025 only — diverges from question_ref_pairs)
- question_ref_pairs: 2,722 rows (2018–2025)
- article_icd10: 3,855 rows
- clinical_pathways: 4,528 rows
- icd10_rollup: 736 rows
- icd10_code_xref: 1,668 rows

**Keyword coverage (questions table):**
- stem_keywords, explanation_keywords, all_keywords: 1,629/1,629 (100%)
- concept_tags: ~100% (440 new 2018-2019 records backfilled via API)
- body_system_merged: 1,629/1,629 (100%)
- blueprint: ~33% populated (pre-existing gap, not fixed)

**Articles table gaps (389 new 2018-2019 articles):**
- source_type, categories, tier, auto_assigned, engine_type: 0% for ART-1549–ART-1937
- Requires classification + VC gate pipeline pass (BATON 005 Step 8)

**Why:** Track this so future scripts and integrations know the current baseline and can verify deltas.

## DB Insert History
| Session | ART-ID Range | Count |
|---------|-------------|-------|
| Pre-project | ART-0001 – ART-1397 | 1,397 |
| Mar 20 S1 | ART-1398 – ART-1425 | 28 |
| Mar 20 S2 | ART-1426 – ART-1443 | 18 |
| Mar 20 S2 | ART-1444 – ART-1449 | 6 |
| Mar 20 S2 | ART-1450 – ART-1548 | 99 |
| Mar 24 (2018-2019 integration) | ART-1549 – ART-1937 | 389 |
| Deleted | ART-0404 | -1 |
| **TOTAL** | | **1,936** |

## PDF Library State (as of BATON 005)
- 00_non-codon/: ~147 PDFs (codon-named, not yet pipeline-processed)
- 01_local_lite/: 117 PDFs (ITE-linked, not VC-cited)
- 02_codon/: ~90 PDFs (codon-named, ITE-linked, VC-cited)
- 03_right_click/: ~70 PDFs (VC-cited, enriched)
- Total: 404 PDFs

**Next ART-ID:** ART-1938 (if new articles are added)

**How to apply:** New articles from any source continue sequential ART-IDs from ART-1938+. VC gate check (session_hy_inserts_v7.json) determines tier assignment — DB membership alone is not sufficient.
