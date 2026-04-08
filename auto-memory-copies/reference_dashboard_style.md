---
name: reference_dashboard_style
description: Data lifecycle dashboard pattern — dark theme, stage-colored nodes, field inventory tables, Chart.js. Replicate for all module pipelines.
type: reference
---

# Data Lifecycle Dashboard — Style & Approach Reference

## When to Use
Any time Mikey asks for a module-level data lifecycle map, pipeline visualization, or "show me what gets added where" type request. Replicate this pattern for M1 warehouse, M3 analyst, Module F (VC outline), keyword pipeline, and ITE question pipeline.

## Approach (the process that worked)

### 1. Deep Exploration First
Before building anything visual, run three parallel data gathering passes:
- **Profile the raw data structures** — read actual files, count key paths, check coverage rates
- **Profile the DB schema** — all tables, columns, null rates, distinct counts, sample values
- **Trace every pipeline script** — for each script, document INPUT (files + fields), TRANSFORMS (what it computes), OUTPUT (what it writes), and DB FIELDS USED

Use the `data:explore-data` skill to structure the profiling. Use a subagent (Explore type) to trace script transforms in parallel.

### 2. Gather Real Stats
Query the actual DB and filesystem for live numbers — don't hardcode from memory. Embed the real counts directly into the dashboard as JSON. This makes the dashboard a living snapshot.

### 3. Build the Dashboard
Use the `data:build-dashboard` skill. Single self-contained HTML file with Chart.js via CDN.

## Output Format & Style

### Visual Design
- **Dark theme** — `#0f1117` background, `#1a1d28` cards, subtle borders
- **Color system by pipeline stage:**
  - Red (#FF5630) = raw/PDF/source
  - Orange (#FF8B00) = extraction
  - Yellow (#FFAB00) = synthesis
  - Blue (#4C9AFF) = enrichment/ITE intelligence
  - Green (#36B37E) = output/rendered
  - Purple (#6554C0) = database
  - Teal (#00B8D9) = computed/derived
- **Monospace font** for field names, code references
- **Accent color tags** for field origins: `tag-source`, `tag-claude`, `tag-db`, `tag-compute`, `tag-static`

### Dashboard Sections (in order)
1. **Header** — title, subtitle describing purpose, date badge
2. **KPI row** — 4-6 headline numbers with labels and sub-text
3. **Pipeline flow diagram** — horizontal node chain with arrows showing stages, each node lists the script name and key fields added
4. **State definitions** — horizontal row of badges defining each state name
5. **Field inventory tables** — 2-column grid of detail cards, one per JSON block
6. **Charts** — 2-3 rows of Chart.js visualizations showing current pipeline coverage
7. **DB schema map** — visual layout of all tables with key columns
8. **Footer** — generation date, data source, git state

### Key Principles
- **Every field traced to its origin** — PDF parse, Claude API, DB lookup, computed, or static default
- **Real numbers, not estimates** — query live data for every stat shown
- **Self-contained HTML** — no external dependencies except Chart.js CDN

### File Naming
`{module_or_pipeline}_data_lifecycle.html` — e.g., `ite_pipeline_data_lifecycle.html`

## First Dashboard Created
- `ite_pipeline_data_lifecycle.html` — M2 enrichment pipeline (PDF → JSON → DOCX)
- Created 2026-03-25, BATON 007

## Planned Future Dashboards
- M1 warehouse lifecycle (PDF acquisition → tier assignment → codon rename)
- M3 analyst lifecycle (score PDFs → parse → analyze → report DOCX)
- Module F VC outline lifecycle (keywords → HY inserts → outline injection → resident build)
- ITE question pipeline (source DOCX → extract → categorize → merge → tag)
