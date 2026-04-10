# ITE Score Analyzer — Plugin v1.0.0

ABFM ITE score analysis pipeline for Family Medicine residency programs.
Right-click score report PDFs to run, or invoke commands directly.

## Commands

| Command | Trigger | What It Does |
|---------|---------|--------------|
| `analyze-ite` | Right-click a score PDF | Runs full single-resident analysis → DOCX report + practice questions |
| `cohort-compare` | "compare residents" or "cohort analysis" | Cross-resident comparison → program gaps vs. individual gaps |
| `study-plan` | "study plan for [name]" | Generates weekly study schedule from completed analysis |

## Skills

| Skill | When It Loads |
|-------|---------------|
| `ite-domain` | Any ITE/ABFM/score-related query — domain knowledge, DB schema, pipeline reference |

## Quick Start

1. Drop score PDFs in: `03_module.3_analyst/resident_data/`
2. Right-click a PDF → select **analyze-ite**
3. Follow the prompts — Claude will confirm parameters and give you the run command
4. Paste the output back when done — Claude summarizes findings and links the report

## Tuning Analytics

Edit `03_module.3_analyst/scripts/report_config.json` to change:
- Weakness threshold (default: 70%)
- Practice question count per weak area (default: 5)
- Which report sections to include
- Number of priority items to surface

The pipeline steps themselves are locked and do not change.

## Author

Michael Scholl MD — board_prep_intel project
