# BATON 023 — Blueprint Pseudo-Classifier Built
**Date:** 2026-03-29
**Session:** Blueprint pseudo-labeling for ITE 2018–2023 questions
**Status:** Classifiers complete — API run pending
**Replaces:** BATON_active_022_20260329_aafp_concept_tags_complete.md

---

## What Was Done This Session

### Goal
Assign ABFM Blueprint Categories to the 1,234 ITE questions from 2018–2023 that predate ABFM's 2024 blueprint system. The 2024/2025 questions already have Gold Standard ABFM labels in `questions.blueprint`.

### Deliverables — 2 scripts built in `02_module.2_processor/scripts/`

#### 1. `blueprint_pseudo_classifier.py` (regex fallback)
Pure rule-based regex classifier. Useful as a fast/offline reference.

**Final validation accuracy (Gold Standard 2024+2025):**
| Category | Gold n | Accuracy |
|---|---|---|
| Acute Care and Diagnosis | 138 | 79.7% |
| Chronic Care Management | 99 | 72.7% |
| Emergent and Urgent Care | 80 | 75.0% |
| Preventive Care | 59 | 62.7% |
| Foundations of Care | 19 | 36.8% |
| **Overall** | **395** | **72.4%** |

**Key design decisions:**
- Priority order: Emergent → Foundations → Preventive → Chronic → Acute (default)
- `EMERGENT_HARD_EXCLUSIONS`: context override for ethics/autonomy cases (patient-refusal)
- `EMERGENT_EXCLUSIONS`: follow-up/post-event softcopy (suppresses setting-based patterns)
- Whitespace normalization in `classify_question()`: `re.sub(r'\s+', ' ', combined)` — **critical fix** for multi-line question text that was silently breaking `.{0,N}` distance patterns
- `--dry-run / --verbose / --year / --write / --force` flags

**Distribution problem:** On 2018–2023 data, regex labels only 2–5% of questions as Emergent vs. the ~20% target. Patterns have high precision but low recall on pre-2024 phrasing. → **This is why the API classifier was built.**

#### 2. `blueprint_api_classifier.py` (primary — use this for production)
Batch Claude API few-shot classifier. Based on Wang et al. 2025 methodology.

**Design:**
- 25 questions per API call (batch mode — ~9x cheaper than individual calls)
- 10 few-shot examples per category (50 total) from Gold Standard
- Validation split: `--dry-run` uses 2024 as few-shot → validates on 2025 (no leakage)
- Production (`--write`): uses all 395 Gold Standard examples as few-shot
- Concurrent batch workers (default: 4)
- Checkpoint writes every 200 questions (safe against mid-run failure)
- Confirms validation accuracy before writing

**Cost estimates (claude-haiku-4-5-20251001):**
- Validation (395 questions): ~$0.21
- Production (1,234 questions): ~$0.65
- Sonnet option available via `--model sonnet`

**Useful flags:**
```bash
python blueprint_api_classifier.py --estimate-cost       # see cost before running
python blueprint_api_classifier.py --show-examples       # inspect few-shot pool
python blueprint_api_classifier.py --dry-run             # validate vs Gold Standard
python blueprint_api_classifier.py --dry-run --verbose   # + misclassification detail
python blueprint_api_classifier.py --year 2022           # preview 2022 distribution
python blueprint_api_classifier.py --write               # apply to 2018-2023
python blueprint_api_classifier.py --write --force       # overwrite existing
```

### Key Technical Insight (Wang et al. 2025)
ABFM used GPT-4 few-shot with 10 examples per domain on ITE 2022 questions → 81% accuracy at Level 1. Table 2 reveals the **TIME dimension** as the Acute vs. Emergent discriminator: appendicitis imaging question = Emergent because "needs to be addressed in the next hours to 1–2 days or else harm will happen." This concept was embedded throughout both classifiers.

### Provenance Decision
- `questions.blueprint` column stores the exact ABFM category name with no qualifier for ALL years.
- 2024/2025 = ABFM Gold Standard labels (official).
- 2018–2023 = pseudo-labels from API classifier (documented here + CLAUDE.md; not in DB).

---

## DB State (unchanged this session)

| Item | Value |
|---|---|
| DB articles | 1,985 |
| ITE questions | 1,629 (2018–2025) |
| AAFP BRQ questions | 1,221 |
| questions.blueprint | 2024/2025 filled (395); 2018-2023 NULL (1,234 — pending API run) |
| qid_art_xref | 2,470 |
| aafp_qid_art_xref | 864 rows |

---

## Immediate Next Steps

### Step 1: Install anthropic SDK (Windows terminal)
```bash
pip install anthropic --break-system-packages
```

### Step 2: Cost + example check (no API calls until --dry-run)
```bash
python 02_module.2_processor/scripts/blueprint_api_classifier.py --estimate-cost
python 02_module.2_processor/scripts/blueprint_api_classifier.py --show-examples
```

### Step 3: Validation dry-run (~$0.21, ~2-3 min)
```bash
python 02_module.2_processor/scripts/blueprint_api_classifier.py --dry-run
```
Expected accuracy: 78–83% (ABFM's GPT-4 got 81% with 10 examples/domain on same task).

### Step 4: Preview one year before committing
```bash
python 02_module.2_processor/scripts/blueprint_api_classifier.py --year 2022
```
Check that distribution is close to: Acute 35%, Chronic 25%, Emergent 20%, Preventive 15%, Foundations 5%.

### Step 5: Production write (~$0.65, ~5-8 min)
```bash
python 02_module.2_processor/scripts/blueprint_api_classifier.py --write
```
Script will run validation first, then ask for confirmation before writing.

### Step 6: QC after write
```bash
python 02_module.2_processor/scripts/blueprint_api_classifier.py --dry-run  # re-check accuracy
```
Then run schema-level population comparison (standard QC rule):
```sql
SELECT exam_year,
       COUNT(*) total,
       SUM(CASE WHEN blueprint IS NOT NULL THEN 1 ELSE 0 END) filled,
       blueprint,
       COUNT(*) as cat_count
FROM questions
GROUP BY exam_year, blueprint
ORDER BY exam_year, blueprint;
```

### Step 7: Git commit (Windows)
Files to commit: `blueprint_pseudo_classifier.py`, `blueprint_api_classifier.py`, BATONs 021/022/023, CLAUDE.md, _index.md (if updated). Archive 020/021/022 → `baton_archive/`.

---

## Deferred Flags (from BATON 022 — still pending)

| Flag | Item | Status |
|---|---|---|
| DEFERRED-A | PDF download: 49 new articles ART-1938–1986 | Still pending |
| DEFERRED-B | `update_citation_trends.py` → `article_citation_trend` table | Still pending |
| DEFERRED-C | AAFP vs ITE trend comparison | Still pending (unblocked) |
| DEFERRED-D | 229 citation gap articles (88 AFP batch-downloadable) | Still pending |
| DEFERRED-E | Interactive vector dashboard | Still pending |
| DEFERRED-F | Intelligence 2.0 Layer 2 (PubMed MCP article_currency) | Still pending |

---

## Files Modified This Session

| File | Change |
|---|---|
| `02_module.2_processor/scripts/blueprint_pseudo_classifier.py` | NEW — regex classifier, 72.4% accuracy |
| `02_module.2_processor/scripts/blueprint_api_classifier.py` | NEW — batch API classifier |
| `CLAUDE.md` | Updated active BATON, M2 script count, Next Steps |
| `BATON_active_023_20260329_blueprint_classifier_built.md` | This file |
