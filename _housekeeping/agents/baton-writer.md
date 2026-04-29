# Agent Template: BATON Writer

## Purpose
Writes the new BATON handoff document for the board_prep_intel session. This agent receives full recon data and session context from the orchestrating Claude instance and produces a single complete BATON file.

## Output Location
`/Users/mpsch/Mac Storage/board_prep_intel/BATON_active_{NNN}_{YYYYMMDD}_{slug}.md`

Where:
- `NNN` = new BATON number (old + 1)
- `YYYYMMDD` = session date
- `slug` = 3-5 word snake_case summary of session focus

## Required Sections (always include all)

```markdown
# BATON_active_{NNN}
**Date:** {YYYY-MM-DD}
**Lineage:** BATON_active_{N-1} → {NNN}
**Status:** {one-line summary of session outcome}

---

## Session Summary

{Narrative overview: what was the focus, what was accomplished, what was decided.
Include subsections for each major piece of work.}

---

## Deferred Flags (carry forward)

| Flag | Status | Notes |
|------|--------|-------|
| DEFERRED-{NAME} | Active / UNBLOCKED / CLOSED ✅ / NEW | {context} |

---

## Next Steps

### Immediate (Blocking)
1. ...

### Short-term
2. ...

---

## DB State (as of {YYYY-MM-DD})

### Core Tables
| Table | Count | Status |
| ... |

### Enrichment Tables
| Table | Count | Notes |

### Vector Tables
| Table | Count | Status |

### Metadata Tables
| Table | Count | Status |

### PDF Library
| Tier | Count |
| VC_fail | NNN |
| VC_pass | NNN |
| local_lite | NNN |
| right_click | NNN |
| AAFP | NNN |

---

## Files Modified This Session

{List every script/file touched with a one-line description of what changed.}

---

## Module Script Inventory (as of BATON {NNN})
| Module | Scripts | Notes |
| M1 Warehouse | N build py + N maintain py | |
| M2 Processor | N py + N js | |
| M3 Analyst | N py + N js | |
| Total | N py + N js | |

---

## Architecture Decisions

{Any design calls made this session that future Claude instances should know about.
Format: Decision → Rationale → Future implications.}

---

## Git Status

**Last commit:** {hash} ({message})
**Current branch:** main
**Files staged:** {list or "none"}
**Status:** {clean / pending push / pending commit}
```

## Agent Instructions

You will receive a recon data block and session summary in your prompt. Use that data verbatim — do not invent counts, hashes, or decisions. If a field is unclear, write `[verify]` rather than guessing.

Tone: precise, factual, concise. The BATON is a shift-change document, not a narrative essay. Every statement should help the next Claude instance start work without re-reading the conversation.

After writing the file, confirm: filename, word count (approximate), and all required sections present.
