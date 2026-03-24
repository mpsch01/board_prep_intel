# M1 / scripts / build — Warehouse Construction Scripts

**Definition:** Scripts that assume the DB does not yet exist (or needs full reconstruction).
Structural and one-time — run order matters. Not for day-to-day use.

---

## Scripts Present (complete set)

| Script | What It Does | Status |
|--------|-------------|--------|
| `build_clean_question_bank.py` | Parses `ABFM_ITE_Master_v2.xlsx` → `ite_questions_clean.json` | Prerequisite for rebuild |
| `rebuild_ite_db_v2.py` | Builds all core DB tables and assigns ART-IDs from `ite_questions_clean.json` | Primary DB constructor |
| `extract_ite_2018_2019.py` | Extracts 2018-2019 questions from split PDFs → `ite_2018_2019_extracted.json` | Upstream of enrich + integrate |
| `enrich_ite_questions.py` | Claude API enrichment for 2018-2019 (body_system, ICD-10) → `ite_2018_2019_enriched.json` | Run after extract |
| `integrate_2018_2019.py` | Integrates 2018-2019 ITE questions + articles into DB | ✅ Already run (2026-03-24) |
| `validate_db_v2.py` | QC checkpoint — validates DB structure post-build | Run after rebuild |
| `compute_embeddings.py` | Computes vector embeddings via OpenAI API; populates `article_vec` / `question_vec` tables | Deferred — FLAG 33 |
| `validate_vector_search.py` | Validates vector search tables post-embedding run | Deferred — FLAG 33 |

---

## Full DB Reconstruction Order

```
1. build_clean_question_bank.py   → produces ite_questions_clean.json
2. rebuild_ite_db_v2.py           → builds DB from JSON
3. extract_ite_2018_2019.py       → extracts 2018-2019 from PDFs
4. enrich_ite_questions.py        → Claude API enrichment for 2018-2019
5. integrate_2018_2019.py         → folds in 2018-2019 data (already run)
6. validate_db_v2.py              → confirms DB is sound
7. compute_embeddings.py          → layer 2 embeddings (deferred — FLAG 33)
8. validate_vector_search.py      → confirms vector tables (deferred — FLAG 33)
```

---

*Last updated: 2026-03-24 (BATON 003 → 004 session)*
