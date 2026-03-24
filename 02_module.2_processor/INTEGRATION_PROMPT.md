# Guideline Extractor v2 — Integration Prompt

> **Purpose:** Hand this prompt (along with the `Guideline_Extractor_Cookbook.docx`) to any AI assistant or developer. It provides step-by-step instructions to verify, configure, and run the clinical guideline extraction pipeline on a new or existing machine.

---

## What You're Working With

This is a **PDF-to-DOCX clinical guideline extraction pipeline**. You feed it a medical guideline PDF and it produces a structured summary DOCX. The system:

1. **Classifies** the PDF into one of 5 document types (chronic, acute, preventive, diagnostic, RCT)
2. **Extracts** structured clinical data (recommendations, thresholds, populations, medications) via type-specific LLM engines
3. **Synthesizes** a clinical narrative from the extracted JSON
4. **Generates** a professionally styled summary DOCX
5. **Self-calibrates** — scores extraction quality, tracks trends over time, and auto-generates prompt improvements for chronically weak dimensions

The **Guideline_Extractor_Cookbook.docx** is the canonical reference for all architecture, schemas, prompt templates, and configuration. This prompt gets you from zero to a working pipeline.

---

## Step 1: Verify Prerequisites

Before anything else, confirm these are available on the target machine:

```
python --version    # Needs Python 3.10+
node --version      # Needs Node.js 18+
pip show anthropic  # Needs anthropic >= 0.25.0
pip show pdfplumber # Needs pdfplumber >= 0.10.0
```

**If missing, install:**
```
pip install anthropic>=0.25.0 pdfplumber>=0.10.0
```

Node.js dependencies live in `<project_parent>/node_modules/` and include `docx` (for DOCX generation) and `@anthropic-ai/sdk` (for synthesis). Verify:
```
node -e "require('docx'); require('@anthropic-ai/sdk'); console.log('OK')"
```

If that fails, from the parent directory of the project:
```
npm install docx @anthropic-ai/sdk
```

---

## Step 2: Set the API Key

The pipeline uses the **Anthropic API** (Claude). The key must be set as a persistent User environment variable (not session-only) so the Windows context menu integration can find it:

**PowerShell (run once):**
```powershell
[System.Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", "sk-ant-YOUR-KEY-HERE", "User")
```

**Verify it persists (new terminal):**
```powershell
[System.Environment]::GetEnvironmentVariable("ANTHROPIC_API_KEY", "User")
```

The batch script also checks the registry fallback at `HKCU\Environment\ANTHROPIC_API_KEY`, so this covers all launch contexts.

---

## Step 3: Understand the Project Layout

```
guideline_extractor_v2/
├── core/                    # Ingestion pipeline (screening → routing → extraction)
│   ├── ingestion.py         # Entry point: ingest_document(pdf_path) → unified JSON
│   ├── screening.py         # LLM classifier (5 document types + confidence)
│   └── routing.py           # Routes to the correct engine by document_type
│
├── engines/                 # Type-specific extraction engines
│   ├── base_engine.py       # Abstract base with shared extraction logic
│   ├── chronic_engine.py    # Chronic disease guidelines (diabetes, HTN, lipids)
│   ├── acute_engine.py      # Acute/emergency protocols (sepsis, stroke, PE)
│   ├── preventive_engine.py # Screening & prevention (USPSTF, cancer screening)
│   ├── diagnostic_engine.py # Diagnostic criteria (Duke criteria, Wells score)
│   └── rct_engine.py        # Randomized controlled trials
│
├── utils/
│   ├── prompt_builder.py    # LLM API client + prompt construction + supplement loading
│   ├── validator.py         # JSON schema validation
│   ├── preprocess.py        # PDF text extraction (pdfplumber)
│   └── logger.py            # Structured JSON logging
│
├── schemas/
│   ├── unified_schema.json  # unified_v1.0 — the canonical output schema
│   └── extraction_schema.json
│
├── oneclick/                # Standalone right-click-to-extract layer
│   ├── extract_guideline.bat    # Orchestrator (PDF → JSON → synthesis → DOCX → calibrate)
│   ├── synthesize.js            # LLM narrative synthesis (Node.js + Anthropic SDK)
│   ├── build_summary.js         # JSON → styled DOCX (Node.js + docx library)
│   ├── calibrate.py             # Quality scorer + persistence + self-improvement
│   ├── install_context_menu.reg # Adds right-click "Extract Guideline" to Windows
│   └── uninstall_context_menu.reg
│
├── build_cookbook_protocol.js    # Generates the Cookbook DOCX you're reading
├── requirements.txt             # Python deps: anthropic, pdfplumber
└── main.py                      # CLI entry point for programmatic use
```

**Auto-generated files** (created by the pipeline at runtime):
- `oneclick/calibration_history.json` — Append-only log of every quality calibration run
- `oneclick/prompt_supplements.json` — Auto-generated extraction instructions from chronic gaps
- `oneclick/.calibrated` — Marker file indicating first-run calibration has completed

---

## Step 4: Install the Right-Click Context Menu

This gives you "Extract Guideline" on any PDF and "Extract All Guidelines" on any folder.

1. Open `oneclick/install_context_menu.reg` in a text editor
2. **Verify the path** in the `command` keys points to the actual location of `extract_guideline.bat` on this machine. The default is:
   ```
   C:\Users\mpsch\Desktop\claude_knowledge\guideline_extractor_v2\oneclick\extract_guideline.bat
   ```
   If the project lives elsewhere, update both command paths (for `.pdf` and for `Directory`).
3. **Also verify** the `NODE_MODULES` path in `extract_guideline.bat` (line 14) points to the actual `node_modules` directory. Default:
   ```
   C:\Users\mpsch\Desktop\claude_knowledge\node_modules
   ```
4. Double-click the `.reg` file and confirm the registry merge.

**To uninstall later:** double-click `uninstall_context_menu.reg`.

---

## Step 5: Run Your First Extraction

**Option A — Right-click (recommended for daily use):**
- Right-click any PDF → "Extract Guideline"
- Or right-click a folder of PDFs → "Extract All Guidelines"

**Option B — Command line:**
```cmd
oneclick\extract_guideline.bat "C:\path\to\guideline.pdf"
```

**Option C — With explicit calibration:**
```cmd
oneclick\extract_guideline.bat "C:\path\to\guideline.pdf" --calibrate
```

**What happens on first run:**
1. `[1/5] Extracting clinical content...` — Python reads the PDF, classifies it, routes to the correct engine, and calls the Anthropic API to extract structured data into a temp JSON file
2. `[2/5] Synthesizing clinical narrative...` — Node.js calls the Anthropic API to generate a prose clinical summary from the extracted JSON
3. `[3/5] Generating summary DOCX...` — Node.js builds a styled Word document with all extracted data + narrative
4. `[4/5] Quality check...` — Python scores the extraction on 5 dimensions (recommendations, thresholds, population, summary, medications), persists to `calibration_history.json`, and checks for chronic gaps
5. `[5/5] Done` — Summary DOCX copied to Desktop

**First-run auto-calibration:** The first time you ever run the pipeline, calibration runs automatically (even without `--calibrate`). After that, it only runs when you explicitly pass `--calibrate`. This is controlled by the `.calibrated` marker file in `oneclick/`.

---

## Step 6: Verify the Output

After extraction, check:

1. **The DOCX exists** on your Desktop: `<filename>_summary.docx`
2. **Open it** — you should see:
   - Title and source metadata
   - Document classification (type + confidence)
   - Key recommendations with strength ratings and evidence levels
   - Clinical thresholds with units and context
   - Target population details
   - Medications (if applicable) with dosing
   - A synthesized clinical narrative
3. **Check the quality score** in the console output — PASS (≥ 0.70) means acceptable quality

---

## Step 7: Understand the Self-Improvement Loop

The calibration system gets smarter over time:

```
Extract PDF → Score quality → Persist to history → Detect chronic gaps
                                                         ↓
Future extractions ← prompt_supplements.json ← Auto-generate targeted fixes
```

**How it works:**
- Every calibration run appends to `oneclick/calibration_history.json`
- After each run, the system scans the last 5 runs for **chronic gaps** — the same dimension+sub_metric scoring below threshold in 3+ of the last 5 runs
- When chronic gaps are found, `oneclick/prompt_supplements.json` is auto-generated with targeted instructions
- `utils/prompt_builder.py` reads those supplements and appends them to extraction prompts on future runs
- Net effect: if "thresholds.unit_rate" is chronically weak, the system auto-adds "ALWAYS include measurement units" to all future extraction prompts

**To force a recalibration cycle** (useful after processing a batch):
```cmd
python oneclick\calibrate.py <folder_of_jsons>
```

**To see the trend report:**
```cmd
python oneclick\calibrate.py <file_or_folder> --report
```

---

## Step 8: Portability Checklist

If moving this pipeline to a new machine, update these machine-specific values:

| File | Line | What to change |
|------|------|----------------|
| `oneclick/extract_guideline.bat` | 14 | `NODE_MODULES` path |
| `oneclick/install_context_menu.reg` | 9, 17 | Path to `extract_guideline.bat` |

Everything else (Python code, Node.js scripts, schemas, calibration history) is path-independent and portable.

**Fresh-machine setup in order:**
1. Install Python 3.10+, Node.js 18+
2. `pip install anthropic pdfplumber`
3. `npm install docx @anthropic-ai/sdk` (in parent directory)
4. Set `ANTHROPIC_API_KEY` as persistent User env var
5. Update the two hardcoded paths above
6. Double-click `install_context_menu.reg`
7. Delete `oneclick/.calibrated` to trigger first-run calibration
8. Right-click a PDF → "Extract Guideline"

---

## Step 9: Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `[ERROR] ANTHROPIC_API_KEY is not set` | Key not in env or registry | Set via PowerShell `SetEnvironmentVariable` (Step 2) |
| `Python extraction failed` | Missing deps or wrong Python version | `pip install -r requirements.txt`, verify Python 3.10+ |
| `DOCX generation failed` | Node.js can't find `docx` module | Check `NODE_MODULES` path in bat file, run `npm install docx` |
| Unicode errors in console | Windows code page mismatch | The bat file sets `chcp 65001`; ensure terminal supports UTF-8 |
| Score shows `NEEDS TUNING` | Extraction quality below 0.70 | Run 3+ calibrations to trigger supplement generation, then re-extract |
| `calibrate.py` errors on old JSON | JSON doesn't match expected schema | Ensure JSON has `extraction`, `classification`, and `metadata` top-level keys |

---

## Reference: The 5 Quality Dimensions

| Dimension | Weight | What It Measures |
|-----------|--------|-----------------|
| Recommendations | 30% | Strength ratings, evidence levels, recommendation length |
| Thresholds | 25% | Units present, contextual info, specificity of values |
| Population | 20% | Specificity of 5 population fields (penalizes vague terms) |
| Summary | 15% | Length, sentence count, absence of vague filler |
| Medications | 10% | Dose rates, drug class identification (only if meds present) |

**Scoring:** Each dimension produces 0.0–1.0. Weighted average = overall score.
**Verdict:** ≥ 0.70 = PASS, < 0.70 = NEEDS TUNING.
**Gap threshold:** Dimension < 0.70 triggers a gap finding (< 0.50 = HIGH priority).

---

## Reference: Key Models and Versions

| Component | Value |
|-----------|-------|
| Extraction model | `claude-sonnet-4-20250514` |
| Synthesis model | `claude-sonnet-4-6` |
| Engine version | `guideline_extractor_v2.3` |
| Schema version | `unified_v1.0` |
| Pass threshold | 0.70 |
| Chronic gap trigger | 3+ occurrences in last 5 runs |
