---
name: manifest-writer
description: Subagent template for updating CLAUDE.md Active State table and README.json
agent: general-purpose
allowed-tools: Read Write Edit Glob Bash
---

# Manifest Writer — board_prep_intel

You are updating the two project manifest files for the board_prep_intel
ABFM ITE Intelligence System as part of session housekeeping.

## Your Inputs (injected by parent skill)

- New BATON number and filename
- New BATON description (1-line)
- Latest git hash (after this session's commits)
- Recon data — DB counts, PDF counts, script counts, date
- Session changes — what was done this session

## Files You Own

1. C:\Users\mpsch\Desktop\board_prep_intel\CLAUDE.md
2. C:\Users\mpsch\Desktop\board_prep_intel\README.json

Do NOT touch REPO_MAP.md or any other file.

---

## Task 1 — CLAUDE.md Active State Table

Read CLAUDE.md first. Locate the ## Active State section.

Rows to update:

| Row | What to change |
|-----|----------------|
| Active BATON | New filename + description |
| Git branch | Keep "main", update the "latest →" hash |
| DB article count | Update if articles were inserted this session |
| PDF counts | Update if PDF library changed |
| Script counts | Update if scripts added or removed |
| Next ART-ID | Update if new articles inserted |

Active BATON row format:
  `BATON_active_NNN_YYYYMMDD_slug.md` — [1-line session description]

What NOT to change in CLAUDE.md:
- Terms/Glossary table
- Module Map table
- Locked Rules section
- Any content outside the Active State table and Next Steps section

Next Steps section: remove completed items, add new immediate items if any.


## Task 2 — README.json

Read the file first. Confirm it parses as valid JSON before and after editing.

Fields to update:

| Field | New value |
|-------|-----------|
| "baton" | New BATON filename |
| "baton_description" | 1-line session description |
| "git_hash" | Latest commit hash |
| "last_updated" | Today's date (YYYY-MM-DD) |
| "database" fields | Update any row counts that changed |
| "pdfs" fields | Update if PDF library changed |
| "scripts" fields | Update if script counts changed |
| "next_art_id" | Update if new articles were inserted |

Fields NOT to change:
- "project", "description", "github_remote" — static
- "modules" — static path map
- "vc_gate_citations" — only changes if VC gate file changes

JSON validity checklist (verify mentally after every edit):
- Every { has a matching }
- Every [ has a matching ]
- No trailing comma after the last item in any object or array
- File ends with } followed by a newline

If the file was previously truncated (missing closing braces), rewrite it in full
using the Write tool rather than trying to patch it with Edit.

If the git hash is not yet available (commits still pending), write "(pending)"
and flag it for the parent skill to update after the final commit lands.

---

## Quality Rules

- Read before writing. Always read the current file content first.
- Minimal changes only. Change only the fields listed above. Do not reorganize
  or reformat other content.
- JSON validity is non-negotiable. A broken README.json fails QC. When in doubt,
  rewrite the full file.
- CLAUDE.md is the source of truth. If README.json and CLAUDE.md disagree on a
  number, trust CLAUDE.md and update README.json to match.
- The git hash should be the final housekeeping commit hash — not the pre-session
  hash. Coordinate with the parent skill on timing.
