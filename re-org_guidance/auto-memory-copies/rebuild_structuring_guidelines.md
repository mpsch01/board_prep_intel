---
name: Core Rebuild Structuring Guidelines
description: Locked architectural principles for the PROJECT_OVERHAUL rebuild. Sourced from the ROOT_BATON_DRAFT session (fervent-hopeful-thompson, March 21, 2026). These are not suggestions — they are the design north star.
type: project
---

## Core Rebuild Structuring Guidelines

Confirmed by Mikey on March 23, 2026 as the governing principles for the rebuild.
Originally surfaced in the ROOT_BATON_DRAFT session (March 21, 2026).

---

### 1. Git Is the Version Control Layer

The project codebase — scripts, schemas, configs — belongs in a git repository.
Git tracks **what changed**: which script was edited, which schema was added, what was rolled back and when.
This is not yet implemented, but it is locked as a design direction. The rebuild should be structured to make git adoption trivial (clean module folders, no loose scripts scattered at root, no generated artifacts mixed with source files).

**What git covers:** Python scripts, JS scripts, .bat files, SQL schema definitions, config JSONs, requirements.txt, package.json.
**What git does NOT cover:** The database itself (binary, too large), PDFs, enriched JSONs, DOCX outputs — these are data artifacts, not code.

---

### 2. BATON Is the Intent Layer — Sits on Top of Git, Not Replaced By It

Git solves history. The BATON solves something git cannot: transferring *intent and context* to a stateless collaborator (Claude).

> "Git tracks what changed. The BATON tracks what matters and what's next. When we do get to git, the two will complement each other perfectly — git for the code and data history, BATONs for the session-to-session intelligence handoff."

The BATON protocol is permanent regardless of whether git is adopted. When git comes in, the BATON gets lighter (no need to document which scripts changed — git has that). The BATON's job sharpens to: current phase, active decisions, open flags, and next steps.

---

### 3. Formal Schemas — Define Upfront, Track Changes

Database schema changes must be:
- Defined as explicit SQL `CREATE TABLE` statements (not inferred from code)
- Documented with purpose, field descriptions, and build method
- Tracked in git when git is adopted — schema drift is a first-class failure mode

**Intelligence 2.0 schemas already defined:**
- `article_icd10` — ICD-10 diagnosis tags per article (Layer 1, complete)
- `article_currency` — PubMed freshness tracking, `superseded_by` chains (Layer 2, not started)
- `clinical_pathways` — clinical blending engine, `pathway_role` per ICD-10 (Layer 3, complete)
- `topic_trends` — exam question frequency by category/year (Layer 4a, complete)
- `pubmed_alerts` — new article detection with relevance scoring (Layer 4b, not started)

Any new DB table must have its schema written out before the build script is written. Schema first, code second.

---

### 4. Structured Output for All Agents — OUTPUT_SCHEMA Pattern

All Claude Agent SDK agents must produce structured JSON output using the SDK's `output_format` parameter.
No prompt-hacking ("output EXACTLY this JSON block"). The SDK enforces the schema natively.

```python
OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "article_id": {"type": "string"},
        "status": {"type": "string", "enum": ["downloaded", "not_found", "error"]},
        "url": {"type": "string"},
        ...
    },
    "required": ["article_id", "status"]
}

options = ClaudeAgentOptions(output_format=OUTPUT_SCHEMA, ...)
```

This makes agent outputs programmatically parseable without regex or string manipulation.
Enables downstream analysis (sourcing success rates, failure pattern detection, pipeline metrics).

---

### 5. Cryptographic Hash ART-IDs — Proof of Provenance (Deferred, Locked)

Current ART-IDs are sequential integers (`ART-XXXX`). Long-term design direction: ART-IDs derived from a cryptographic hash generated at pipeline **completion**.

The ID becomes proof of provenance — the only way to receive an ART-ID is to pass through the full pipeline: download → extraction → enrichment → synthesis. If you skip a step, you don't get an ID. The ID is a fingerprint of what produced it, not just a counter.

Also planned: richer human-readable filename prefixes beyond `Author_Year` — topic keywords, specialty, etc. for easier browsing without opening the DB.

**Status:** Deferred until library is stable and the nnn_XXXX migration is complete. Do not implement until a full migration plan with rollback is written and reviewed.

---

### How These Five Work Together

```
Git ──────────────────────── tracks code/schema history
  └─ BATON ─────────────────── tracks session intent + open decisions
       └─ Formal Schemas ──────── defines DB structure upfront
            └─ OUTPUT_SCHEMA ────── enforces structure at agent boundaries  
                 └─ Hash ART-IDs ──── makes provenance immutable at the data level
```

Each layer makes the one above it more reliable. Git gives BATON a stable substrate. Formal schemas give the DB predictable structure. OUTPUT_SCHEMA gives the pipeline clean data at every handoff. Hash ART-IDs make the terminal product (the article record) trustworthy.

---

*Committed to memory: March 23, 2026*
*Source: ROOT_BATON_DRAFT session (fervent-hopeful-thompson, March 21, 2026) + confirmed by Mikey*
