---
name: project_current_db_state
description: DB state as of BATON 037 (2026-04-04) — DB unchanged from BATON 034; M1 restructure complete; 42 practice Q&A deliverables generated; ite_exams archive confirmed
type: project
---

## DB State (as of BATON 037, 2026-04-04 — unchanged from BATON 034)

| Table | Rows | Notes |
|-------|------|-------|
| articles | 1,985 | ART-0001 → ART-1986; next = ART-1987; +49 AAFP acquisition (PDFs pending) |
| questions | 1,629 | ITE only — 2018–2025; blueprint 100%; subcategory + topic_label DROPPED |
| aafp_questions | 1,221 | Flattened: correct_letter, correct_text, explanation merged in; subcategory DROPPED; blueprint 100% |
| aafp_explanations | DROPPED | Merged into aafp_questions |
| question_ref_pairs | 2,722 | 222 NULL clean_ref |
| qid_art_xref | 2,470 | All 8 years (2018–2025) |
| aafp_qid_art_xref | 864 | 643 unique questions linked (52.7%) |
| article_icd10 | 4,137 | Full coverage — ITE chain + AAFP backfill (2026-03-31) |
| question_icd10 | 5,284 | 1,512/1,629 ITE questions (92.8%) |
| aafp_question_icd10 | 4,753 | Relevance normalized, related cap applied (2026-03-31) |
| clinical_pathways | 4,020 | REBUILT 2026-03-31 — blueprint-based, both banks, ART-0002–ART-1985 |
| icd10_rollup | 614 | |
| icd10_code_xref | 1,006 | |
| pubmed_pmid_cache | 344 | Layer 2 seed (citation_id → PMID) — ready for article_currency build |
| icd10_vec | 2,219 | OpenAI text-embedding-3-small (1536d) per unique ICD-10 code |
| article_icd10_vec | 1,674 | Weighted-avg ICD-10 feature per article — REBUILT 2026-04-01 |
| question_icd10_vec | 2,733 | 1,525 ITE + 1,208 AAFP — REBUILT 2026-04-01 |
| article_vec | 1,985 | sqlite-vec virtual table; 49 new articles embeddings pending |
| question_vec | 1,629 | sqlite-vec virtual table, 100% ITE coverage |
| article_citation_trend | 1,740 | Pre-computed longitudinal data ART-0002–ART-1937 |
| aafp_citations | 1,600 | One parsed citation per row |
| aafp_citation_raw | 1,600 | Full text archive |

---

## ART-ID Insert History

| Session | ART-ID Range | Count |
|---------|-------------|-------|
| Pre-project | ART-0001 – ART-1397 | 1,397 |
| Mar 20 S1 | ART-1398 – ART-1425 | 28 |
| Mar 20 S2 | ART-1426 – ART-1548 | 123 |
| Mar 24 (2018-2019 integration) | ART-1549 – ART-1937 | 389 |
| Mar 28 (AAFP acquisition) | ART-1938 – ART-1986 | 49 |
| **Next** | ART-1987 | — |

---

## Questions Table Column Coverage (ITE, 1,629 rows)

| Column | Coverage | Notes |
|--------|----------|-------|
| body_system_merged | 100% | |
| stem_keywords | 100% | TF-IDF unigrams |
| concept_tags | 100% | JSON: diagnoses, drugs, guidelines, thresholds, concept_summary |
| blueprint | 100% | 2024/2025 Gold Standard; 2018–2023 API pseudo-label (Sonnet 4.6) |
| subcategory | DROPPED | |
| topic_label | DROPPED | |

## aafp_questions Column Coverage (1,221 rows)

| Column | Coverage | Notes |
|--------|----------|-------|
| stem, choices | 100% | |
| correct_letter, correct_text | 100% | Merged from aafp_explanations |
| explanation | 100% | Merged from aafp_explanations |
| explanation_keywords | 100% | |
| concept_tags | 100% | Same schema as ITE |
| body_system | 100% | Note: no body_system_merged (ITE only) |
| blueprint | 100% | Same rubric + 19 gold-standard examples as ITE v2 — Batch API |
| subcategory | DROPPED | |

## Blueprint Distributions

### ITE (1,629 questions)
| Blueprint | Count | % |
|---|---|---|
| Acute Care and Diagnosis | 709 | 43.5% |
| Chronic Care Management | 403 | 24.7% |
| Emergent and Urgent Care | 214 | 13.1% |
| Preventive Care | 206 | 12.6% |
| Foundations of Care | 97 | 6.0% |

### AAFP (1,221 questions)
| Blueprint | Count | % |
|---|---|---|
| Acute Care and Diagnosis | 588 | 48.2% |
| Chronic Care Management | 253 | 20.7% |
| Emergent and Urgent Care | 166 | 13.6% |
| Preventive Care | 140 | 11.5% |
| Foundations of Care | 74 | 6.1% |

---

## ICD-10 Vector Layer (rebuilt 2026-04-01)

| Table | Rows | Description |
|---|---|---|
| icd10_vec | 2,219 | One embedding per unique code |
| article_icd10_vec | 1,674 | Weighted avg of tagged code vectors (primary=3, secondary=2, related=1) |
| question_icd10_vec | 2,733 | Same weighting; ITE via qid_art_xref→article_icd10; AAFP direct from aafp_question_icd10 |

Model: OpenAI text-embedding-3-small, 1536d. Script: `build_icd10_embeddings.py` (--embed / --derive / --report / --all / --dry-run).

---

## Practice Questions Deliverables (as of BATON 037)

All stored in `01_module.1_warehouse/practice_questions/` (gitignored — regenerable from DB).

| Set | DOCX | XLSX | Script |
|-----|------|------|--------|
| ITE (per year, 2018–2025) | 8 files | 8 files | `build_ite_qa_deliverables.py` |
| AAFP (per quiz chunk, 13 chunks) | 13 files | 13 files | `build_aafp_qa_deliverables.py` |

**Design rules locked:**
- MC answer choices are uniform (dark text, no bold) — correct answer NOT shown in choices list
- Only `✓ Answer:` banner (light blue shaded) reveals the correct answer
- ITE XLSX: 13 columns (`#, QID, Year, Stem, A, B, C, D, E, Correct, Correct Answer, Explanation, Reference`) — no body_system/blueprint
- AAFP XLSX: 12 columns (no body_system/blueprint — never had them)

---

## M3 Analyst Scripts (as of BATON 037)

| Script | Status | Notes |
|--------|--------|-------|
| `ite_parser.py` | Stable | PDF extraction, blueprint + body system |
| `ite_analyzer_v3.py` | Stable | 9 layers, 3-tier question cascade, dual bank |
| `ite_analyze_v2.py` | Stable | Entry point; routes to v3 by default |
| `ite_report_builder_v2.js` | Stable | subcatAnalysis fix, pathway gap section |
| `build_icd10_tags.py` | Stable | ICD-10 tagging pipeline |
| `build_aafp_qa_deliverables.py` | NEW (BATON 036) | 26 AAFP Q&A files; answer choice fix applied (BATON 037) |
| `build_ite_qa_deliverables.py` | NEW (BATON 037) | 16 ITE Q&A files (8 DOCX + 8 XLSX) |

---

## Backup Checkpoints

- `ite_intelligence_pre2018_backup_20260324_001256.db` — pre-2018/2019 integration rollback
- `ite_intelligence_pre_flag15_backup.db` — earlier rollback point
- `ite_intelligence_v1_backup_20260310_095728.db` — v1 snapshot
