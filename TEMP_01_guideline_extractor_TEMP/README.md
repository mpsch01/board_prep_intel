# Guideline Extraction Pipeline v2.3

**Last updated:** 2026-03-14

A high-performance extraction pipeline for clinical guideline PDFs, powered by Claude API (Anthropic). Automatically segments PDFs into clinical domains and generates enriched JSON + DOCX outputs.

## Overview

This pipeline extracts structured data from clinical guideline PDFs using a 5-engine architecture:
- **ChronicRisk** — Chronic disease management guidelines
- **AcuteProtocol** — Acute condition response protocols
- **Preventive** — Preventive care recommendations
- **Diagnostic** — Diagnostic criteria and workup pathways
- **RCT** — Randomized controlled trial evidence integration

### Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Extract a single PDF
python main.py --input "path/to/guideline.pdf" --output outputs/

# Run calibration check
python calibration.py --scan

# Batch extract with timing
python run_timed.py --batch documents/ --workers 4
```

## Architecture

### Core Modules
- **`core/ingestion.py`** — PDF parsing and page segmentation
- **`core/routing.py`** — Engine selection and task distribution
- **`core/screening.py`** — Quality validation and confidence scoring
- **`engines/`** — Domain-specific extraction engines
- **`utils/`** — Logging, preprocessing, prompt building, validation

### Entry Points
- **`main.py`** — CLI orchestrator (v2.3)
- **`run_test_batch.py`** — Test batch runner
- **`run_timed.py`** — Timing profiler wrapper
- **`reextract_gold_list.py`** — Re-extract baseline gold set
- **`pre_scan.py`** — Library pre-flight scanner

### Windows Integration
- **`oneclick/`** — Right-click context menu extraction system (28 files)
  - `extract_guideline.bat` — Windows batch entry point
  - `install_context_menu.reg` — Registry installer
  - Automatic DOCX summary generation
  - Run logs and sample outputs in `oneclick/logs/`

## Data Flow

**Input Sources:**
- PDFs: `clinical_guidelines/01_pdf_guideline_library/`

**Output Destinations:**
- DOCX: `clinical_guidelines/02_docx_guideline_library/`
- JSON: `clinical_guidelines/03_enriched_json/`

**Local Staging:**
- `documents/` — Empty (test PDFs moved offsite)
- `outputs/` — Extraction results, summaries, calibration reports
  - `outputs/historical_calibration/` — Baseline calibration data (43 files)

## Configuration

### Schemas
- **`schemas/extraction_schema.json`** — Main extraction template
- **`schemas/unified_schema.json`** — Unified output format

### Prompts
- **`prompts/`** — 4 candidate prompt templates for engine tuning

### Integration & Protocol
- **`INTEGRATION_PROMPT.md`** — Integration guide for new environments
- **`ABFM_GuidanceExtraction_Protocol_v2.docx`** — Protocol specification

## Dependencies

- `anthropic` — Claude API client
- `pdfplumber` — PDF text extraction
- See `requirements.txt` for full list

## Build Scripts

JavaScript-based protocol and documentation builders (Node.js):
- `build_changelog.js` — Changelog generator
- `build_cookbook_protocol.js` — Cookbook protocol
- `build_oneclick_protocol.js` — One-click system protocol
- `build_protocol_v3.js` — Protocol v3 specification

## Logs & History

- **`logs/`** — 608 run logs (development period: March 3–13, 2026)
- **`oneclick/calibration_history.json`** — One-click calibration record
- **`outputs/`** — Summary JSONs and migration reports

## Archival

- **`07_archive/`** — 6 deprecated migration/test scripts from v1 and v2.0

## Status

- **Pipeline Version:** v2.3
- **Architecture:** 5-engine extraction
- **Extraction Method:** Claude API (via Anthropic SDK)
- **Last Calibration:** 2026-03-14
- **Mode:** Production-ready
