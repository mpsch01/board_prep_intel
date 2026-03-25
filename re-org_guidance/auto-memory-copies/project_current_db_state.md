---
name: project_current_db_state
description: DB state as of BATON 007 session 3 (2026-03-25) — 1,936 articles 100% standardized, vec tables 100% populated, FLAG 33 closed
type: project
---

## DB State (as of BATON 007 session 3, 2026-03-25)

| Table | Rows | Notes |
|-------|------|-------|
| articles | 1,936 | ART-0001 → ART-1937; next = ART-1938 |
| questions | 1,629 | 2018–2025 (all years complete) |
| question_ref_pairs | 2,722 | |
| qid_art_xref | 1,818 | 2018-2019 not yet crosswalked (0 entries for those years) |
| article_icd10 | 3,855 | |
| clinical_pathways | 3,093 | corrected (stale 4,528 in older BATONs) |
| icd10_rollup | 614 | corrected (stale 736 in older BATONs) |
| icd10_code_xref | 1,006 | corrected (stale 1,668 in older BATONs) |
| article_vec | 1,936 | sqlite-vec virtual table, 100% coverage — FLAG 33 closed |
| question_vec | 1,629 | sqlite-vec virtual table, 100% coverage — FLAG 33 closed |

---

## ART-ID Insert History

| Session | ART-ID Range | Count |
|---------|-------------|-------|
| Pre-project | ART-0001 – ART-1397 | 1,397 |
| Mar 20 S1 | ART-1398 – ART-1425 | 28 |
| Mar 20 S2 | ART-1426 – ART-1548 | 123 (includes ART-0404 deleted) |
| Mar 24 (2018-2019 integration) | ART-1549 – ART-1937 | 389 |
| **Next** | ART-1938 | — |

---

## Articles Table Column Coverage (fully standardized 2026-03-25)

| Column | Coverage | Notes |
|--------|----------|-------|
| source_type | 100% | Rule-based journal detection across all 1,936 rows |
| categories | 90.2% (1,747/1,936) | 189 unresolvable — no linked questions or unmapped body systems |
| tier | 100% | Legacy Core/Supplementary/Must-Read fully retired. Tier: non-codon (1,399) / codon (362) / local_lite (117) / right_click (58) |
| engine_type | 100% | right_click + local_lite values preserved (extraction-derived ground truth) |
| auto_assigned | 100% | |

---

## Questions Table Column Coverage

| Column | Coverage | Notes |
|--------|----------|-------|
| body_system_merged | 100% | Backfilled for 2018-2019 |
| stem_keywords | 100% | Backfilled for 2018-2019 |
| explanation_keywords | 100% | Backfilled for 2018-2019 |
| all_keywords | 100% | Backfilled for 2018-2019 |
| concept_tags | ~100% | API batch via preprocess_concept_tags.py |
| blueprint | ~33% | Pre-existing debt — cross-year gap |

---

## Vec Table Details (FLAG 33 — closed 2026-03-25)

- **Model:** OpenAI `text-embedding-3-small`, 1536 dimensions
- **Extension:** `sqlite_vec` (pip install sqlite-vec) + `conn.enable_load_extension(True)` required to query
- **article_vec:** virtual table with shadow tables (_chunks, _info, _rowids, _vector_chunks00)
- **article text:** title | clean_ref | categories | blueprint_cats | tier
- **question text:** question_text[:600] | correct_text | body_system/subcategory | concept_tags (summary, diagnoses, drugs)
- **Incremental update:** `compute_embeddings.py --new-only` (both articles and questions supported)
- **Cost:** ~$0.015 full corpus, ~$0.002 per 1,000-item gap fill

---

## Backup Checkpoints

- `ite_intelligence_pre2018_backup_20260324_001256.db` — pre-2018/2019 integration rollback
- `ite_intelligence_pre_flag15_backup.db` — earlier rollback point
- `ite_intelligence_v1_backup_20260310_095728.db` — v1 snapshot

**How to apply:** When adding new records, continue from ART-1938. Always run `compute_embeddings.py --new-only` after adding articles or questions. Schema-level QC after every integration.
