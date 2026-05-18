---
name: body-system-qc
description: >
  Full pipeline for auditing and correcting ITE and AAFP question body_system field values.
  Uses ABFM ground-truth score report PDFs (2022-2023) as training labels, then runs a
  two-layer Claude CoT + SVM dual-classifier to reclassify all years. Outputs SQL UPDATE
  statements split into taxonomy normalization (fast apply) and clinical reclassification
  (review before applying). ALWAYS trigger this skill when the user mentions: body system
  corrections, body_system QC, wrong body system labels, body system audit, reclassify
  questions, or any concern about the accuracy of body_system values across ITE or AAFP years.
---

# Body System QC Skill

## What this skill does

Corrects the `body_system` field in the `questions` (ITE) and `aafp_questions` (AAFP) tables
using a dual-classifier pipeline:

1. **Extract** ABFM ground-truth body system labels from ITE score report PDFs (2022-2023)
2. **Condense** the 16 pre-2024 ABFM categories to the 15 post-2024 canonical taxonomy
3. **Build** a training set by joining labels with question content from DB
4. **Classify** all unlabeled questions using Claude CoT + dynamic few-shot retrieval (Batch API)
5. **Audit** human_review cases with SVM — dual-classifier agreement upgrades to sql_ready
6. **Generate** SQL UPDATE statements split into taxonomy-norm and reclassification sections

Final taxonomy (15 categories, post-2024 ABFM canonical):
  Cardiovascular, Endocrine, Gastrointestinal, Hematologic/Immune,
  Injuries/Musculoskeletal, Integumentary, Nephrologic, Neurologic,
  Nonspecific, Patient-Based Systems, Population-Based Care,
  Psychiatric/Behavioral, Respiratory, Sexual and Reproductive, Special Sensory

---

## Project paths

```
PROJECT_ROOT = board_prep_intel/
DB           = PROJECT_ROOT/00_database/db/ite_intelligence.db
SCRIPTS      = PROJECT_ROOT/03_module.3_analyst/scripts/
OUTPUT_DIR   = PROJECT_ROOT/03_module.3_analyst/outputs/body_system_labels/
SCORE_REPORTS = PROJECT_ROOT/03_module.3_analyst/resident_data/ITE_michael_scholl/inputs/
```

---

## Scripts (all in 03_module.3_analyst/scripts/)

| Script | Purpose |
|--------|---------|
| `extract_score_report_labels.py` | Parse ABFM score report PDFs → question→body_system lookup |
| `condense_taxonomy.py` | Map 16 pre-2024 categories → 15 post-2024 canonical |
| `build_training_set.py` | Join labels + DB question content → training JSON |
| `run_svm_baseline.py` | Pass 1: SVM diagnostic (train 2022, test 2023) |
| `submit_batch_classification.py` | Pass 2: Submit ITE questions to Anthropic Batch API |
| `submit_batch_aafp.py` | Pass 2 (AAFP): Submit AAFP questions to Batch API |
| `retrieve_batch_results.py` | Poll batch status + download results when done |
| `svm_review_audit.py` | SVM cross-check on human_review cases; upgrades agreements |
| `generate_body_system_sql.py` | Generate SQL UPDATE statements (2 sections) |
| `rename_taxonomy_labels.py` | Post-process rename custom names → post-2024 canonical |
| `fix_taxonomy_names.py` | Direct DB fix for naming artifacts (Musculoskeletal spacing, etc.) |
| `fix_aafp_taxonomy_names.py` | Same for AAFP questions |
| `verify_body_system_updates.py` | Verify ITE DB changes after applying SQL |
| `check_aafp_body_system.py` | Verify AAFP DB changes after applying SQL |

---

## Workflow — Full Pipeline (ITE)

### Phase 1 — Extract ground truth from ABFM score report PDFs

```bash
cd PROJECT_ROOT/03_module.3_analyst/scripts/
python extract_score_report_labels.py --auto
python condense_taxonomy.py
```

Reads `scholl_2022_Item_Blueprint_Performance.PDF` and `scholl_2023_blueprint.PDF`.
Outputs `score_report_labels_2022.json`, `score_report_labels_2023.json`,
`condensed_labels_2022.json`, `condensed_labels_2023.json` to OUTPUT_DIR.

### Phase 2 — Build training set (run on Windows — needs DB access)

```powershell
python build_training_set.py
```

Joins condensed labels with ITE question content from DB.
Outputs `body_system_training_set.json`.

### Phase 3 — SVM baseline diagnostic (run on Windows)

```powershell
python run_svm_baseline.py
```

Trains on 2022, tests on 2023. Outputs `svm_baseline_results.json`.
Shows per-class accuracy — identifies which categories are cleanly separable
vs. where Claude CoT prompt needs targeted rules.

### Phase 4 — Submit Batch API classification (run on Windows)

```powershell
python submit_batch_classification.py
```

Targets all years NOT in training set (2018, 2019, 2020, 2021, 2024, 2025).
Prints batch ID. Uses two-layer prompt:
  - Part A: one canonical example per all 15 categories (static)
  - Part B: K=5 most similar training examples (dynamic retrieval)

### Phase 5 — Retrieve results (run on Windows, polls every 90s)

```powershell
python retrieve_batch_results.py --batch-id msgbatch_XXXX --wait
```

Downloads results when batch completes. Outputs `claude_classifications.json`.

### Phase 6 — Rename taxonomy labels

```powershell
python rename_taxonomy_labels.py
```

Post-process renames our internal condensed names to post-2024 canonical names
in the classification JSON files.

### Phase 7 — SVM audit (upgrades agreements from human_review)

```powershell
python svm_review_audit.py --min-svm-prob 0.0
```

For ITE. SVM trained on same 2022/2023 set. When SVM and Claude agree on category,
upgrades from human_review to sql_ready. Outputs `upgraded_classifications.json`.

Optional flags: `--show-disagreements`, `--show-upgrades`, `--verbose`

### Phase 8 — Generate SQL

```powershell
python generate_body_system_sql.py
```

Outputs `body_system_updates.sql` with two sections:
- Section 1: Taxonomy normalization (safe, fast apply as a block)
- Section 2: Clinical reclassifications (review before applying, reasoning on every line)

### Phase 9 — Apply in DB Browser

1. Open `body_system_updates.sql` in DB Browser Execute SQL tab
2. Paste and run Section 1 → verify → Write Changes
3. Paste and run Section 2 year-by-year → spot-check reasoning → Write Changes

### Phase 10 — Verify and fix residuals

```powershell
python verify_body_system_updates.py
python fix_taxonomy_names.py      # if any Musculoskeletal/spacing artifacts remain
```

---

## Workflow — AAFP (runs after ITE pipeline is complete)

### Quick taxonomy normalization (always run first)

```powershell
python fix_aafp_taxonomy_names.py
python check_aafp_body_system.py
```

### Full reclassification batch

```powershell
python submit_batch_aafp.py
python retrieve_batch_results.py --batch-id msgbatch_XXXX --wait
```

Retrieval writes to `claude_classifications.json` — rename it immediately:
```powershell
python check_aafp_results.py    # renames to aafp_classifications.json + shows routing
```

### SVM audit and SQL for AAFP

```powershell
python svm_review_audit.py --bank aafp --min-svm-prob 0.0
python generate_body_system_sql.py --bank aafp
```

Apply `aafp_body_system_updates.sql` in DB Browser → Write Changes.
Verify with `check_aafp_body_system.py`.

---

## Routing thresholds

| Route | Confidence | Action |
|-------|-----------|--------|
| `sql_ready` | ≥ 0.85 (or SVM agrees) | Include in SQL automatically |
| `human_review` | 0.60–0.84, no SVM agreement | Manual review required |
| `flagged` | < 0.60 | Do not touch DB |

Centroid divergence cross-check: if cosine distance to class centroid > 0.4 AND
confidence ≥ 0.85, downgrade to human_review regardless.

---

## After applying — downstream rebuilds required

1. **`body_system_merged`** — update mapping direction: now normalizes TO post-2024
   canonical names (forward mapping, not backward)
2. **Rebuild intersection centroids** — `build_intersection_centroids.py` in M1
3. **Re-run AAFP body system assignment** — `aafp_assign_body_system.py` (or skip
   if full Claude pipeline already run for AAFP)
4. **Re-run all resident analyses** — clean body_system cascades to all reports

---

## Locked rules

- Source data (DB) is never modified automatically — always present SQL for review first
- Training data: ITE 2022-2023 only (ABFM score report PDFs = ground truth)
- Input: raw Q&A only (stem + choices + correct answer) — no concept tags, no ICD-10
- Taxonomy normalization changes (Psychogenic → Psychiatric/Behavioral etc.) are safe
  to apply as a block; clinical reclassifications require individual review
- After any body_system correction, update body_system_merged and rebuild centroids
