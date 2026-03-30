# BATON 024 — Blueprint Labeling Complete (All 1,629 ITE Questions)
**Date:** 2026-03-29
**Session:** Blueprint pseudo-labeling production run + emergent second pass
**Status:** Blueprint column 100% filled — analytics now unblocked
**Replaces:** BATON_active_023_20260329_blueprint_classifier_built.md
            BATON_active_023_20260329_dashboard_qc_relevance_normalized.md

> Two parallel sessions ran on 2026-03-29. Both BATON 023s are archived. This BATON consolidates their state.

---

## What Was Done — Session A (Dashboard + QC + Keywords)

### AAFP vs ITE Comparison Dashboard
- **File:** `aafp_vs_ite_comparison_dashboard.html` (workspace root)
- 4 tabs: Body System | Subcategory | ICD-10 Hot Zones | ITE Year Trends
- Patched same session: all 16 ITE body system constants corrected (were summing to 1,844 ≠ 1,629)

### Data Exploration QC
| Issue | Action |
|-------|--------|
| aafp_question_icd10.relevance: 74 distinct labels | **FIXED** → normalized to 3 canonical values (primary/secondary/related) |
| stem_keywords: AAFP avg 209 chars vs ITE 59 chars | **FIXED** → unified_keyword_extractor.py; both now TF-IDF unigrams, avg ~102 chars |
| ITE subcategory split (2018-2019 disease-specific vs 2020-2025 canonical) | Documented (FLAG-A) |
| dashboard subcategory constants unverified | Documented (FLAG-D) |

### New Script
- `unified_keyword_extractor.py` — replaces `add_keywords.py` + `backfill_keywords_2018_2019.py` + `aafp_keyword_extractor.py`; TF-IDF unigrams, top 12; re-generated stem_keywords for all 1,629 ITE + 1,221 AAFP questions

---

## What Was Done — Session B (Blueprint Classifier)

### blueprint_api_classifier.py (modified)
- Default model changed to `claude-sonnet-4-6` (was haiku)
- Two rounds of system prompt refinement based on confusion matrix analysis:
  - Added Acute/Chronic TRAP notes + decision box + 6 labeled examples
  - Added Emergent/Acute 24-hour harm test box + "default to Acute when uncertain"
- Third round: Mikey's manual review of 10 borderline questions added clinical rules:
  - TASK discriminator over patient background
  - Post-surgical complications → Chronic
  - Critical lab values → Acute
  - Medication risk profile questions → Chronic
  - Hemodynamic instability / vasopressors → Emergent
  - O2 sat <94% + active treatment decision → Emergent
- **Accuracy ceiling: 70.4–70.6%** (confirmed across 3 dry-run attempts — prompt not the bottleneck)
- Root cause: Gold Standard has ~3/10 borderline questions with debatable labels; Acute/Chronic boundary is genuinely ambiguous for ~59 questions

### blueprint_api_classifier.py — Production Run
- **Wrote 1,234 classifications → questions.blueprint (2018-2023)**
- Distribution: Acute 42.6% / Chronic 30.5% / Emergent 10.4% / Preventive 10.6% / Foundations 5.9%

### blueprint_emergent_pass.py (NEW)
- Binary Emergent-only second pass on 526 Acute-labeled 2018-2023 questions
- Sonnet default; 20 Emergent + 10 Acute boundary examples
- Dry-run metrics: Recall 71.2%, Precision 75.0%, False +ve 13.8%
- **Wrote 16 flips → Emergent (526 → 510 Acute; 128 → 144 Emergent)**
- Post-emergent-pass: Emergent 11.7% vs 20% target

### Key Decision: Accept Distribution Skew
Pre-2024 Emergent under-representation (11.7% vs 20%) is a **known limitation, not a bug**.
- ABFM blueprint targets apply to 2024+ exam design; pre-2024 distribution is unknown
- Forcing the distribution would erase a potentially real signal (ABFM shifted exam composition in 2024)
- Emergent pseudo-labels are conservative estimates; flag in any pre-2024 Emergent analysis

---

## DB State (current as of BATON 024)

| Item | Value |
|------|-------|
| DB articles | 1,985 (+49 AAFP acquisition: ART-1938–ART-1986) |
| DB questions (ITE) | 1,629 (2018–2025) |
| questions.blueprint | **1,629/1,629 (100%)** — 2024/2025 Gold Standard; 2018-2023 API pseudo-label |
| questions.stem_keywords | 1,629/1,629 — TF-IDF unigrams (re-unified this session) |
| DB questions (AAFP BRQ) | 1,221 |
| aafp_questions.concept_tags | 1,221/1,221 (100%) |
| aafp_questions.subcategory | 1,221/1,221 (100%) |
| aafp_questions.stem_keywords | 1,221/1,221 — TF-IDF unigrams (re-unified this session) |
| aafp_question_icd10 | 4,240 rows — relevance normalized (primary/secondary/related) |
| qid_art_xref | 2,470 |
| aafp_qid_art_xref | 864 rows (643 unique questions, 52.7%) |
| PDFs | 404 (49 new articles awaiting PDF download) |
| Next ART-ID | ART-1987 |

### questions.blueprint Distribution (2018-2023 pseudo-labels, n=1,234)
| Category | Count | % | ABFM Target | Δ |
|----------|-------|---|-------------|---|
| Acute Care and Diagnosis | 510 | 41.3% | 35% | +6.3 |
| Chronic Care Management | 376 | 30.5% | 25% | +5.5 |
| Emergent and Urgent Care | 144 | 11.7% | 20% | -8.3 |
| Preventive Care | 131 | 10.6% | 15% | -4.4 |
| Foundations of Care | 73 | 5.9% | 5% | +0.9 |

---

## M2 Script Inventory Update

| Type | Count |
|------|-------|
| Python | 57 (+unified_keyword_extractor.py, +blueprint_emergent_pass.py) |
| JS | 6 |
| JSON config | 1 |
| Windows | 4 |

---

## Deferred Flags

### Carried from BATON 022 (original)
| Flag | Description | Status |
|------|-------------|--------|
| DEFERRED-A | PDF download: 49 new articles ART-1938–1986 | Pending |
| DEFERRED-B | `update_citation_trends.py` → `article_citation_trend` table | Pending |
| DEFERRED-C | AAFP vs ITE trend comparison | **PARTIALLY DONE** — dashboard built; deeper analysis pending |
| DEFERRED-D | 229 citation gap articles (88 AFP batch-downloadable) | Pending |
| DEFERRED-E | Interactive vector dashboard | Pending |
| DEFERRED-F | Intelligence 2.0 Layer 2 (PubMed MCP article_currency) | Pending |

### New flags from Session A
| Flag | Description | Priority |
|------|-------------|----------|
| FLAG-A | ITE subcategory split: 2018–2019 disease-specific vs 2020–2025 canonical | Medium |
| FLAG-B | stem_keywords: AAFP/ITE unified but context not identical — filter in trend analysis | Low |
| FLAG-C | `ite-data-context-skill` stale (old path, old counts, no AAFP schema) | Medium |
| FLAG-D | Dashboard subcategory constants unverified (same issue as body system constants had) | Medium |

---

## Next Steps (priority order)

### 1. Git commit (Windows) — overdue
```
git add CLAUDE.md _index.md BATON_active_024*.md baton_archive/
git add 02_module.2_processor/scripts/blueprint_api_classifier.py
git add 02_module.2_processor/scripts/blueprint_emergent_pass.py
git add 02_module.2_processor/scripts/unified_keyword_extractor.py
git add aafp_vs_ite_comparison_dashboard.html
git commit -m "BATONs 021-023: AAFP enrichment + dashboard + blueprint complete"
# Archive BATONs 020-023 → baton_archive/ (from Windows, git rm the active files)
```

### 2. QC — blueprint column by year
```sql
SELECT exam_year,
       blueprint,
       COUNT(*) as n
FROM questions
GROUP BY exam_year, blueprint
ORDER BY exam_year, blueprint;
```
Verify: 2024+2025 match known Gold Standard distributions (70/50/40/30/10).

### 3. PDF download — 49 new AAFP articles
```
python 01_module.1_warehouse\scripts\maintain\download_aafp_acquisitions.py
python 01_module.1_warehouse\scripts\maintain\backfill_new_article_metadata.py --art-id-min 1938
```

### 4. update_citation_trends.py
- Confirmed built in M1/maintain/
- Populates `article_citation_trend` table (streak data, is_watch_list)

### 5. AAFP vs ITE trend comparison (unblocked)
- Both corpora now schema-parallel: body_system + subcategory + concept_tags + ICD-10 + blueprint
- Dashboard exists; deeper analysis ready

### 6. Verify dashboard subcategory constants (FLAG-D)
```sql
SELECT subcategory, COUNT(*) FROM aafp_questions GROUP BY subcategory ORDER BY COUNT(*) DESC;
```
Compare to hardcoded constants in `aafp_vs_ite_comparison_dashboard.html`.

### 7. Update ite-data-context-skill (FLAG-C)
- Fix path: `00_database/db/ite_intelligence.db`
- Update counts
- Add AAFP table schemas

### 8. 229 citation gap articles (DEFERRED-D)
- 88 AFP batch-downloadable from `null_clean_ref_missing_articles_20260326.csv`

### 9. Intelligence 2.0 Layer 2 — PubMed currency (DEFERRED-F)
- `article_currency` table via PubMed MCP

---

## Files Changed This Session (both sessions combined)

| File | Action |
|------|--------|
| `blueprint_api_classifier.py` | MODIFIED — Sonnet default, improved system prompt (3 rounds) |
| `blueprint_emergent_pass.py` | NEW — binary Emergent second-pass classifier |
| `unified_keyword_extractor.py` | NEW — replaces 3 legacy keyword scripts |
| `aafp_vs_ite_comparison_dashboard.html` | CREATED + PATCHED |
| `questions.blueprint` (DB) | POPULATED — 1,234 pseudo-labels written (2018-2023) |
| `questions.stem_keywords` etc. (DB) | RE-GENERATED — TF-IDF unigrams unified |
| `aafp_question_icd10.relevance` (DB) | NORMALIZED — 74 → 3 canonical values |
| `CLAUDE.md` | UPDATED this housekeeping sweep |
| `_index.md` | UPDATED this housekeeping sweep |
| `BATON_active_024_*.md` | This file |
