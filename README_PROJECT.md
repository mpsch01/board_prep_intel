# claude_knowledge — ABFM Board Exam Preparation & Clinical Knowledge Engineering

**Last updated:** 2026-03-17
**Status:** Production (active development)

## Project Overview

A comprehensive, multi-module knowledge management and extraction system designed to support ABFM board exam preparation through integrated ITE exam intelligence, clinical guideline extraction, AAFP course content management, and Claude API-powered enrichment. Intelligence 2.0 layers (ICD-10 diagnostic linkage, clinical pathways, topic trends) provide structured clinical navigation across the full article and question corpus.

## Directory Structure & Module Overview

### 00_canonical/ (31 MB, 28 files)
Canonical reference data, curricula, and baseline frameworks.
- ABFM curriculum definitions
- Question bank master data
- Domain analysis frameworks
- Reference materials and lookup tables

### abfm_prep/ (796 MB, 1,755 files)
The core ABFM preparation ecosystem with 6 integrated modules:

#### 01_guideline_extractor/ (v2.3)
High-performance extraction pipeline for clinical guideline PDFs.
- **5-engine architecture:** ChronicRisk, AcuteProtocol, Preventive, Diagnostic, RCT
- **Input:** `clinical_guidelines/01_pdf_guideline_library/`
- **Output:** DOCX + enriched JSON
- **Windows integration:** Right-click context menu extraction
- **Status:** Production-ready, calibrated 2026-03-14
- **Key files:** `main.py` (v2.3), `calibration.py`, `run_timed.py`, `oneclick/`

#### 02_ite_intelligence/
ITE exam intelligence database and analytics.
- SQLite DB: 1,397 articles, 1,189 questions, 2,069 QID-ref pairs, vector embeddings
- Intelligence 2.0: ICD-10 diagnostic linkage (3,093 MCP-verified assignments), clinical pathways (3,093 rows, 7 roles), topic trends
- Reusable assets: clinical synonym map (151 entries), MCP ICD-10 lookup cache (1,406 entries)
- Zero-cost deterministic pipeline: `build_icd10_tags.py v2` (MCP-first, no Claude API calls)

#### 03_ite_exam/
ITE exam data processing and normalization.
- Raw exam data ingestion
- Question and answer parsing
- Metadata extraction and validation

#### 04_aafp_integration/
AAFP video course content integration.
- Course content mapping to domains
- Integration with canonical curricula
- Topic cross-referencing

#### 05_ite_refs/
ITE reference article processing and enrichment.
- Article ingestion and parsing
- Topic mapping and indexing
- Citation analysis

#### 06_ite_pipeline/
Master orchestration and coordination layer.
- Module communication and workflow
- Data flow management
- Result aggregation

### clinical_guidelines/ (376 MB, ~1,600 files)
Guideline library repository with three output tiers:

#### 01_pdf_guideline_library/
Source clinical guideline PDFs (216 total: 146 codon-renamed, 70 original names)

#### 02_docx_guideline_library/
1,366 DOCXs — 139 merged (clinical narrative + DB intelligence), 1,227 DB-only

#### 03_enriched_JSON/
217 structured JSON extractions — 146 with ITE intelligence, 71 extracted-only

### house_keeping_hub/ (29 files)
Project organization, architecture documentation, dependency maps, and planning proposals.

### scratch_scripts/ (9 files)
Diagnostic and debugging utility scripts for testing and troubleshooting.

### node_modules/ (8 MB, 384 files)
JavaScript/Node.js dependencies for build tools (`build_protocol.js`, etc.).

## Key Integration Points

### Guideline Extraction Pipeline
```
clinical_guidelines/01_pdf_guideline_library/
    ↓ (01_guideline_extractor v2.3)
    ├→ clinical_guidelines/02_docx_guideline_library/
    └→ clinical_guidelines/03_enriched_json/
```

### ITE Processing Pipeline
```
03_ite_exam/ + 05_ite_refs/
    ↓ (06_ite_pipeline orchestration)
    └→ 02_ite_intelligence/
```

### AAFP & Canonical Integration
```
04_aafp_integration/ ↔ 00_canonical/
    ↓ (cross-referencing & mapping)
    ↓ (feeds 02_ite_intelligence/)
```

## Technology Stack

### Backend & APIs
- **Claude API** (Anthropic SDK) — Main extraction and enrichment engine
- **Python 3** — Core pipeline scripts (PDFPlumber, Anthropic client)
- **Node.js** — Build tools and protocol generators

### Data Formats
- **PDF** — Source guideline documents
- **DOCX** — Extracted guideline summaries
- **JSON** — Structured enriched extractions and metadata
- **Markdown** — Documentation and protocol definitions

### Tools & Utilities
- **build_protocol.js** — Top-level protocol generator
- **build_changelog.js, build_cookbook_protocol.js, build_oneclick_protocol.js, build_protocol_v3.js** — Specialized protocol builders
- **PDFPlumber** — PDF text and metadata extraction
- **Anthropic SDK** — Claude API integration

## Project Statistics

| Metric | Value |
|--------|-------|
| **Total Files** | ~2,200+ |
| **Total Size** | ~1,200+ MB |
| **Active Modules** | 6 |
| **Core Guidelines** | ~1,600 files (376 MB) |
| **ABFM Prep Data** | 1,755+ files (796 MB) |
| **Reference Data** | 28 files (31 MB) |
| **Pipeline Version** | v2.3 (extraction), v2 (ICD-10 MCP-first) |
| **Intelligence 2.0** | Layer 1 (ICD-10) + Layer 3 (Pathways) + Layer 4a (Trends) complete |
| **Last Updated** | 2026-03-17 |

## Quick Start Guide

### Guideline Extraction
```bash
cd abfm_prep/01_guideline_extractor/
pip install -r requirements.txt

# Single PDF extraction
python main.py --input path/to/guideline.pdf --output outputs/

# Batch extraction with timing
python run_timed.py --batch documents/ --workers 4

# Calibration check
python calibration.py --scan
```

### Windows Right-Click Integration
```bash
# Install context menu
abfm_prep\01_guideline_extractor\oneclick\install_context_menu.reg

# Right-click any PDF in Windows Explorer → "Extract Guideline"
# Auto-generates DOCX summary + JSON extraction
```

### Module Orchestration
```bash
# See 06_ite_pipeline for cross-module coordination
cd abfm_prep/06_ite_pipeline/
python orchestrate.py --full-sync
```

## Configuration & Customization

### Extraction Schemas
- `abfm_prep/01_guideline_extractor/schemas/extraction_schema.json`
- `abfm_prep/01_guideline_extractor/schemas/unified_schema.json`

### Prompt Templates
- `abfm_prep/01_guideline_extractor/prompts/` — 4 candidate templates for engine tuning

### Protocol Definitions
- `abfm_prep/01_guideline_extractor/ABFM_GuidanceExtraction_Protocol_v2.docx`
- `abfm_prep/01_guideline_extractor/INTEGRATION_PROMPT.md`

## Project History & Milestones

### Recent Timeline
- **v2.3 (Current)** — 5-engine architecture, Windows right-click integration, production calibration
- **v2.0–v2.2** — Progressive refinement of extraction engines
- **v1.0** — Initial prototype (archived in `07_archive/`)

### Development Environment
- Active development: March 3–13, 2026 (608 logged runs)
- Last calibration: 2026-03-14
- Cleanup: Removed v1 prototype, legacy working directories, duplicate guideline libraries

## Maintenance & Operations

### Logs & Diagnostics
- **Pipeline logs:** `abfm_prep/01_guideline_extractor/logs/` (608 runs from March development)
- **Calibration history:** `abfm_prep/01_guideline_extractor/oneclick/calibration_history.json`
- **Output summaries:** `abfm_prep/01_guideline_extractor/outputs/` (migration reports, prescan results)

### Data Archival
- **Removed folders** (not in working directory):
  - `guideline_extractor_v1/` — v1 prototype, superseded by v2.3
  - `guideline_lib_linked/` — duplicate of `03_enriched_json`
  - `data_plug-in/` — installed as Claude plugin skills
  - `claude_root_working/` — legacy working directory (empty)

## Known Limitations & Future Work

- **Intelligence 2.0 Layer 2 (PubMed currency):** Not started — article freshness checks, superseded_by tracking
- **13 unmapped ICD-10 terms:** Edge cases (pseudogout, sundowning, etc.) in the synonym map
- **Blueprint backfill:** 66.8% of questions have empty blueprint field
- **documents/ folder:** Currently empty (test PDFs moved offsite for space efficiency)

## Support & Documentation

- **Integration Guide:** `abfm_prep/01_guideline_extractor/INTEGRATION_PROMPT.md`
- **Protocol Spec:** `abfm_prep/01_guideline_extractor/ABFM_GuidanceExtraction_Protocol_v2.docx`
- **Project Index:** `_index.md`
- **Org Docs:** `house_keeping_hub/` — dependency maps, architecture proposals

## License & Attribution

Claude API integration powered by Anthropic. All extracted clinical content respects original source copyright and proper attribution.

---

**Project Lead:** ABFM Preparation Initiative
**Last Reviewed:** 2026-03-17
**Next Review:** TBD
