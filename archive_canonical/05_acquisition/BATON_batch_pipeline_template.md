# BATON — Batch Acquisition Pipeline (Template)
**Mode:** Full Batch | PDF Folder → JSONs → Library Match → Crosswalk → LinkedRefs + GoldTier → Housekeeping
**Version:** 1.2 | 2026-03-07
**Root:** `C:\Users\mpsch\Desktop\claude_knowledge\`

---

## How to Use This Template

This is a reusable template. At the start of every new batch session, ask the user the
Pre-Flight questions to collect the session-specific values that replace every
`<<PLACEHOLDER>>` in this file. Do not proceed past Pre-Flight until all placeholders
are resolved. The current session BATON.md is the authoritative source for any values
not provided directly by the user.

---

## Fixed Paths (never change between sessions)

| Location | Path |
|---|---|
| Knowledge base root | `C:\Users\mpsch\Desktop\claude_knowledge\` |
| Extractor root | `guideline_extractor_v2/` |
| Unified JSON library | `board_prep/ite_refs/04_outputs/ingested/json/` |
| Library matcher script | `board_prep/ite_refs/05_scripts/match_tiers_to_library.py` |
| Tier match output | `board_prep/ite_refs/04_outputs/tier_match/match_summary.csv` |
| Crosswalk scripts | `board_prep/ite_refs/05_scripts/linked_refs_build/` |
| Crosswalk output | `board_prep/ite_refs/04_outputs/linked_refs/linked_refs_crosswalk_final.csv` |
| Doc generators | `board_prep/ite_refs/05_scripts/linked_refs_build/` |
| Canonical output | `00_canonical/01_curriculum/` |
| Previous versions | `00_canonical/01_curriculum/previous_versions/` |
| node_modules (docx) | `claude_knowledge/` root |
| Session BATON | `BATON.md` (root) |

---

## Technical Constraints (apply every session, no exceptions)

**Python execution:**
- Always use full path: `C:\Users\mpsch\AppData\Local\Programs\Python\Python312\python.exe`
- Verify all scripts have `sys.stdout.reconfigure(encoding="utf-8")` at top before running
- Always run from root: `cd C:\Users\mpsch\Desktop\claude_knowledge`

**Node.js execution:**
- Always run generators from `claude_knowledge` root
- `node_modules/docx` installed at root — resolves via directory walk-up ✅
- `--localstorage-file` warning on startup = benign Desktop Commander artifact, ignore
- Root log files (`gold_tier_log.txt`, `gen_log.txt`) — delete after confirming output

**Script placement policy:**
- All new scripts go directly to the appropriate domain `05_scripts/` subfolder — NEVER write to root

**DOCX editing:**
- unpack.py → edit XML → pack.py --original (never pandoc)
- `w:shd` must come BEFORE `w:spacing` in `<w:pPr>` — schema enforced

**Versioning:**
- Never overwrite a canonical file — always move previous version to `previous_versions/` first
- Never delete superseded files

---

## PRE-FLIGHT — Collect Session Variables

Ask the user each of the following before doing anything else.
Record answers and use them to fill every `<<PLACEHOLDER>>` below.

---

**Q1 — Batch folder name**
> "What is the name of the PDF folder for this batch?"
> Example: `id_renal_gi_hep`, `jacc_pulm`, `neuro_tox_rheum`

→ `<<BATCH_FOLDER>>` = _______________
→ Full PDF path: `clinical_guidelines/practice/<<BATCH_FOLDER>>/`
→ Extraction output path: `guideline_extractor_v2/outputs/<<BATCH_FOLDER>>_batch/`

---

**Q2 — Extraction status**
> "Has extraction already been run for this batch (e.g., overnight), or does it need to run now?"

→ `<<EXTRACTION_STATUS>>` = already done / needs to run
→ If already done: skip Phase 1 Steps 1–2, go straight to Step 3 (calibration verify)
→ If needs to run: start at Phase 1 Step 1

---

**Q3 — Expected doc count**
> "How many PDFs are in this batch?"

→ `<<EXPECTED_COUNT>>` = _______________

---

**Q4 — Source ID prefix**
> "What prefix should be used for source_ids when migrating JSONs to the unified library?"
> Current convention: AFP- for AFP/USPSTF/peds batch, ITE- for gold list docs
> Suggest a new prefix based on batch content, confirm with user.

→ `<<SOURCE_PREFIX>>` = _______________

---

**Q5 — Output document version numbers**
> "What version numbers should LinkedRefs and GoldTier be incremented to?"
> Check current BATON.md for current versions — suggest next logical increment.

→ `<<LINKEDREFS_VERSION>>` = _______________ (e.g., v3)
→ `<<GOLDTIER_VERSION>>` = _______________ (e.g., v2)
→ LinkedRefs output filename: `ABFM_BoardPrep_LinkedRefs_<<LINKEDREFS_VERSION>>.docx`
→ GoldTier output filename: `ABFM_BoardPrep_GoldTier_<<GOLDTIER_VERSION>>.docx`

---

**Q6 — Known manual overrides**
> "Are there any new manual overrides (pins or nulls) you want applied to the crosswalk before it runs?"
> Also read current overrides from `finalize_crosswalk.py` and `gen_gold_tier.js` and list them
> for user confirmation — ask if any should be changed or removed given the new batch content.

→ `<<OVERRIDE_UPDATES>>` = confirmed as-is / [list any changes]

---

## Execution Steps

---

### PHASE 1 — EXTRACTION & CALIBRATION

#### Step 1 — Test Batch
*(Skip if <<EXTRACTION_STATUS>> = already done)*
```bash
cd C:\Users\mpsch\Desktop\claude_knowledge\guideline_extractor_v2
C:\Users\mpsch\AppData\Local\Programs\Python\Python312\python.exe run_test_batch.py \
  --input clinical_guidelines/practice/<<BATCH_FOLDER>>/ --n 5
```
- Report calibration scores for all 5 docs
- Target: ≥ 0.94 — flag any score below threshold before proceeding
- **Hard stop if any score < 0.94 — wait for user approval before full batch**

#### Step 2 — Full Batch Extraction
*(Skip if <<EXTRACTION_STATUS>> = already done)*
```bash
C:\Users\mpsch\AppData\Local\Programs\Python\Python312\python.exe main.py \
  --input clinical_guidelines/practice/<<BATCH_FOLDER>>/ \
  --output outputs/<<BATCH_FOLDER>>_batch/
```
- Report any failed PDFs immediately
- Confirm JSON count matches <<EXPECTED_COUNT>> before proceeding

#### Step 3 — Calibration Verify
*(Always run — even if extraction was pre-run)*
```bash
cd C:\Users\mpsch\Desktop\claude_knowledge
C:\Users\mpsch\AppData\Local\Programs\Python\Python312\python.exe \
  guideline_extractor_v2/calibration.py \
  --input guideline_extractor_v2/outputs/<<BATCH_FOLDER>>_batch/
```
Report to user:
- Mean confidence score across batch (target ≥ 0.94)
- Count of docs below threshold
- Gap analysis for any low-confidence docs
- **Hard stop — do not proceed to migration until user approves**

---

### PHASE 2 — MIGRATION

#### Step 4 — Migrate to Unified JSON Library
```bash
C:\Users\mpsch\AppData\Local\Programs\Python\Python312\python.exe \
  guideline_extractor_v2/migrate_to_unified.py \
  --source guideline_extractor_v2/outputs/<<BATCH_FOLDER>>_batch/ \
  --dest board_prep/ite_refs/04_outputs/ingested/json/ \
  --prefix <<SOURCE_PREFIX>>
```
- Report file count in `ingested/json/` before and after
- Report any naming conflicts
- Update `manifest.json` — confirm entry count reflects new total

---

### PHASE 3 — LIBRARY MATCHER

#### Step 5 — Re-run Library Matcher
```bash
C:\Users\mpsch\AppData\Local\Programs\Python\Python312\python.exe \
  board_prep/ite_refs/05_scripts/match_tiers_to_library.py
```
Report to user:
- confirmed_present count before vs after (should increase)
- Must-Read coverage (target: 20/20)
- Any unexpected drops — investigate before proceeding
- Output: `board_prep/ite_refs/04_outputs/tier_match/match_summary.csv`

---

### PHASE 4 — CROSSWALK (with QC Gates)

#### Step 6 — Review and Update Overrides in finalize_crosswalk.py
```
Open board_prep/ite_refs/05_scripts/linked_refs_build/finalize_crosswalk.py
Read all current hardcoded manual overrides — list them for the user
Apply any changes from <<OVERRIDE_UPDATES>>
Confirm final override list with user before proceeding
```

#### Step 7 — Review and Update MANUAL_OVERRIDES in gen_gold_tier.js
```
Open board_prep/ite_refs/05_scripts/linked_refs_build/gen_gold_tier.js
Read the MANUAL_OVERRIDES map — list all current entries for the user
Apply any changes from <<OVERRIDE_UPDATES>>
Confirm with user before proceeding
```

#### Step 8 — Run Crosswalk
```bash
cd C:\Users\mpsch\Desktop\claude_knowledge
C:\Users\mpsch\AppData\Local\Programs\Python\Python312\python.exe \
  board_prep/ite_refs/05_scripts/linked_refs_build/build_crosswalk_v2.py
```

#### Step 9 — QC Gate Battery
Run all gates in sequence. **Do not proceed past a failing gate — report to user and wait for approval.**

**QC 1 — Must-Read Coverage**
- Verify all Must-Read tier refs have a matched JSON
- Any Must-Read unmatched = HARD BLOCK — must be manually pinned before proceeding
- Report: `X/Y Must-Read refs matched`

**QC 2 — Duplicate JSON Assignments**
- Identify any JSON assigned to more than one citation
- Legitimate (one guideline, multiple related citations): flag for user review, allow with approval
- Illegitimate: run deduplication pass — assign each JSON to its single best citation only

**QC 3 — B-Quality Match Review**
- List all B-quality (partial title overlap) matches
- Show citation string + matched JSON title side by side for each
- User must approve or null each before proceeding

**QC 4 — Zero Duplicates (post-dedup)**
- Confirm zero duplicate JSON assignments remain after deduplication
- Hard stop if any persist

**QC 5 — Displaced Ref Count**
- Report citations displaced by deduplication
- Confirm count is expected given batch size

**QC 6 — Generic Title Spillover Detection**
- Flag any JSON whose title shares 3+ high-frequency non-specific words
  (e.g., "management," "guidelines," "treatment," "diagnosis," "screening,"
  "recommendation," "statement") with 3 or more different citations
- Show all matched citations for each flagged JSON — verify each is topically appropriate
- Pattern-based detection only — not hardcoded to any specific source or organization
- Null any match that cannot be confirmed as topically correct

#### Step 10 — Finalize Crosswalk
```bash
C:\Users\mpsch\AppData\Local\Programs\Python\Python312\python.exe \
  board_prep/ite_refs/05_scripts/linked_refs_build/finalize_crosswalk.py
```
Output: `linked_refs_crosswalk_final.csv`

#### Step 11 — Pre-Lock Human Review
Print a clean summary for the user:
```
Batch:               <<BATCH_FOLDER>>
Total matched:       X  (previous crosswalk: X  |  delta: +X)
Must-Read:           X/20
Core:                X
Supplementary:       X
Unmatched:           X
Manual overrides:    X applied
Nulled matches:      X
```
**Ask user explicitly: "Crosswalk looks like this — proceed to doc generation?"**
Do not auto-proceed. Wait for confirmation.

---

### PHASE 5 — DOCUMENT GENERATION

#### Step 12 — Update Output Paths in Generators
Before running either generator:
```
In gen_linked_refs_v2.js: update OUT_PATH to ABFM_BoardPrep_LinkedRefs_<<LINKEDREFS_VERSION>>.docx
In gen_gold_tier.js:      update OUT_PATH to ABFM_BoardPrep_GoldTier_<<GOLDTIER_VERSION>>.docx
```

#### Step 13 — Regenerate LinkedRefs
```bash
cd C:\Users\mpsch\Desktop\claude_knowledge
node board_prep/ite_refs/05_scripts/linked_refs_build/gen_linked_refs_v2.js
```
- Confirm output file written and file size is reasonable (not empty or truncated)
- Move previous LinkedRefs version to `previous_versions/`
- Copy new version to `00_canonical/01_curriculum/`

#### Step 14 — Regenerate GoldTier
```bash
node board_prep/ite_refs/05_scripts/linked_refs_build/gen_gold_tier.js
```
- Report: how many Must-Read entries promoted from PDF-only → full extracted content
- Gold/grey border cards auto-promote when JSONs are available — no code changes needed
- Move previous GoldTier version to `previous_versions/`
- Copy new version to `00_canonical/01_curriculum/`
- Delete `gold_tier_log.txt` and `gen_log.txt` from root

---

### PHASE 6 — HOUSEKEEPING

#### Step 15 — Update READMEs
Update only READMEs in folders touched this session:
- `linked_refs/README.json` — session, last_updated, match counts, doc versions
- `ite_refs/README.json` — ingested JSON count, crosswalk state, manifest count
- `guideline_extractor_v2/outputs/<<BATCH_FOLDER>>_batch/README.json` — create if new

#### Step 16 — Update `_index.md`
- Bump session header and last_updated date
- Add new canonical docs to 00_canonical table
- Mark superseded docs as ⚠️ SUPERSEDED
- Add session log entries for all major actions

#### Step 17 — Clean Temp Files
- Delete root log files and any probe/test files
- Move intermediate CSVs to `previous_versions/` — never delete
- Confirm root and all working folders are clean

#### Step 18 — Write Session BATON
Update `BATON.md` at root with:
- Session label (increment from current)
- What was done this session (table format)
- Current canonical state (all files with ✅ / ⚠️ status)
- Primary goal for next session (step-by-step)
- Any new or updated technical notes

---

## Hard Stops — Always Wait for User Before Proceeding
- Calibration score below 0.94 at any point
- Must-Read ref unmatched after QC 1
- Unresolved duplicate after QC 4
- Pre-lock crosswalk review (Step 11)
- Any canonical file about to be overwritten
- Any override in `finalize_crosswalk.py` or `gen_gold_tier.js` that looks stale or incorrect
