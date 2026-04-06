---
name: New 4-Module Architecture — The Rebuild
description: User's mental model for the PROJECT_OVERHAUL rebuild: 4 modules (Warehouse, Processor, Analyst, Sandbox) plus external sources. Replaces the organic 7-module structure (⓪–Ⓔ+Ⓕ). Designed March 21, 2026.
type: project
---

## The Rebuild — 4-Module Architecture

Mikey decided on March 21, 2026 to tear down the current organic folder structure and rebuild around how he actually thinks about the system. The trigger: he couldn't find things manually — folder names and trees didn't match his mental model.

### External Sources (feeds the system, not owned by the system)
- **ABFM ITE Exams** — annual PDFs, the baseline fuel for the database
- **AAFP Board Prep Video Course** — 48 sessions, .vtt transcripts, companion PDFs. Acts as a **priority filter/lens**, not a module. Once processed, it deposited the VC gate relationship structure into the Warehouse. Now static context.
- **Clinical guideline articles** — PDFs from AAFP, journals, etc.
- **ABFM Score Reports** — per-resident performance PDFs

### Module 1 — Warehouse (verb: *store*)
The DB, the PDF library, the ICD-10 crosswalk, the VC gate, all relationship structures. Everything that *is*. Core repository holding atomic components of higher-level data sources while maintaining critical relationship structure. Every intelligence layer added to the DB is an enhancement revealing more relationships.

### Module 2 — Processor (verb: *transform*)
PDF goes in, structured data + Word doc comes out. Stateless transformation layer. Reads from the Warehouse, does its work, writes back. The $right_click$ pipeline, local_lite builder, all extraction strategies live here. Doesn't *own* data, *processes* data.

### Module 3 — Analyst (verb: *analyze*)
Reads the Warehouse and produces insight. Four faces:
1. **Individual analysis** — ITE score in → weakness map → curated practice questions out
2. **Cohort analysis** — PGY1 vs PGY2 trends, program-level patterns over years
3. **Practice test generation** — historically-informed question curation, targeted to weaknesses
4. **Question synthesis & pattern discovery** — mining how ABFM reuses articles across years to probe concepts from different angles. Predict next probe angle based on historical fingerprints.

### Module 4 — Sandbox (verb: *experiment*)
Where new ideas live until proven. Isolated from production. Things graduate into Modules 1–3 when ready. Agent SDK experiments, PDF Sourcer, cryptographic hash vision — would all start here.

### Design Principles
- Four modules, clean boundaries, each with a clear verb
- Structure matches user's mental model, not engineering categories
- The AAFP course is an external source / priority filter / lens — not a module
- The VC gate is a relationship structure inside the Warehouse, produced by processing the external AAFP source

**Why:** The old 7-module structure (⓪–Ⓔ+Ⓕ) grew organically and stopped matching how Mikey thinks. Folder names were too similar, trees didn't match intent. This rebuild keeps all the right components but reorganizes the vehicle.

**How to apply:** All future folder tree design, script organization, and documentation should align with these 4 modules. Do not revert to the old module numbering or folder structure.
