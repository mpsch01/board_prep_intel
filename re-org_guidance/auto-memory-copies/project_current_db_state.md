---
name: project_current_db_state
description: Current ite_intelligence.db state as of March 20 2026 session 2, pre-2018/2019 integration
type: project
---

## DB State (Pre-2018/2019 Integration)

As of BATON_plus_20260320_session2:
- articles: 1,547 rows (ART-0001 through ART-1548, ART-0404 deleted/merged)
- questions: 1,189 rows (2020-2025)
- qid_art_xref: 1,818 rows
- question_ref_pairs: 2,069 rows
- article_icd10: 3,093 rows
- clinical_pathways: 3,093 rows
- Codon coverage: 1,547/1,547 (100%)
- QID-linked articles: 1,342 of 1,547
- Unlinked articles: 205

**Why:** Track this so integration scripts know the starting state and can verify deltas correctly.

## DB Insert History
| Session | ART-ID Range | Count |
|---------|-------------|-------|
| Pre-project | ART-0001 – ART-1397 | 1,397 |
| Mar 20 S1 | ART-1398 – ART-1425 | 28 |
| Mar 20 S2 | ART-1426 – ART-1443 | 18 |
| Mar 20 S2 | ART-1444 – ART-1449 | 6 |
| Mar 20 S2 | ART-1450 – ART-1548 | 99 |
| Deleted | ART-0404 | -1 |

## 13 Articles Missing PDFs (High Priority)
ART-0112, ART-0272, ART-0457, ART-0569, ART-0713, ART-0755, ART-1132, ART-1175, ART-1326, ART-1345 — 6+ are VC-cited.

## PDF Library State
- 00_non-codon/: 146 PDFs (processing backlog, all codon-named)
- 01_local_lite/: 117 PDFs
- 02_codon/: 70 PDFs (all verified correct content)
- 03_right_click/: 71 PDFs
- Total: 404 PDFs

**How to apply:** When adding new article records from 2018-2019 reference parsing, continue sequential ART-IDs from ART-1549+. New articles from pre-2020 exam references are almost certainly non-VC-cited (VC outline only covers 2020-2025 exam questions).
