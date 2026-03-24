# BATON — Single Document Extraction
**Mode:** Ad Hoc | Single PDF → JSON → Word Doc
**Version:** 1.0 | 2026-03-07
**Root:** `C:\Users\mpsch\Desktop\claude_knowledge\`

---

## Context

This is a single-document extraction pipeline. A PDF (clinical guideline, RCT, review article, or any clinical document) is converted to a structured JSON and then rendered as a formatted Word document. No pipeline migration, no crosswalk, no housekeeping required.

**Output destination:**
`board_prep/ite_refs/04_outputs/linked_refs/`

**Tools required:**
- Desktop Commander MCP (filesystem R/W)
- Python 3.12
- Node.js + docx 9.5.3
- `guideline_extractor_v2/main.py`

---

## Your Job Before Running

Confirm the following with the user before starting:
1. What is the PDF filename and where is it located?
2. Is this a guideline, RCT, review article, or other? (affects extraction prompt tuning)
3. Any specific sections to prioritize? (e.g., thresholds only, recs only, full extraction)

If the user says "extract this" with a file reference, assume full extraction and proceed.

---

## Execution Steps

### Step 1 — Locate the PDF
```
Confirm file exists at the stated path.
If in clinical_guidelines/practice/, note the subfolder.
If dropped elsewhere, confirm exact path before proceeding.
```

### Step 2 — Run Extraction
```bash
cd C:\Users\mpsch\Desktop\claude_knowledge\guideline_extractor_v2
python main.py --input "[full path to PDF]" --output outputs/ad_hoc/
```
- If `outputs/ad_hoc/` does not exist, create it first
- Confirm extraction completed and JSON was written
- Note the output JSON filename

### Step 3 — Calibration Check
```bash
python calibration.py --input outputs/ad_hoc/[output_filename].json
```
- Report the confidence score to the user
- If conf < 0.85: flag specific sections with low confidence before proceeding
- If conf ≥ 0.85: proceed to doc generation

### Step 4 — Generate Word Doc
Use Node.js + docx 9.5.3. Read the JSON and render a structured Word document with the following sections (include only sections present in the JSON — do not generate empty sections):

| Section | Formatting |
|---|---|
| Title + Source + Extraction metadata | Header block, dark fill |
| Clinical Summary | Plain paragraph |
| Target Population | Table |
| Key Diagnostic Thresholds | Table with Parameter / Value / Unit / Context columns |
| Clinical Recommendations | Table with Recommendation / Strength / Evidence columns |
| Medications | Table with Drug / Dose / Class / Indication columns |
| Red Flags / Alarm Features | Bullet list |
| Follow-up / Monitoring | Bullet list or table |

**Color coding:**
- Strong / Grade A recommendations → green row highlight
- Conditional / Grade B → yellow row highlight
- Grade C or ungraded → no highlight
- Red Flags section header → red fill

**Output filename:** `[source_slug]_extracted.docx`
Example: `AFP_lower_extrem_PVD_extracted.docx`

### Step 5 — Write to Output Folder
```
Copy final .docx to:
C:\Users\mpsch\Desktop\claude_knowledge\board_prep\ite_refs\04_outputs\linked_refs\
```
Confirm file is present before reporting completion.

### Step 6 — Report to User
Provide a brief summary:
- Document title and source
- Calibration confidence score
- Section count (how many sections rendered)
- Any low-confidence sections flagged
- Full output path

---

## Technical Constraints
- DOCX editing: unpack.py → edit XML → pack.py --original (never pandoc)
- `w:shd` must come BEFORE `w:spacing` in `<w:pPr>` — schema enforced
- Node.js docx 9.5.3 is the doc generator — do not use python-docx for formatted output
- Do not overwrite any existing file without confirming with user first

---

## What NOT to Do
- Do not migrate this JSON to `ite_refs/04_outputs/ingested/json/` — that is batch pipeline only
- Do not run crosswalk scripts
- Do not update READMEs or `_index.md` — housekeeping not required for ad hoc extractions
- Do not proceed past Step 3 if calibration score is below 0.85 without explicit user approval
