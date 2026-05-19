# User-Level Shadow Copies — Snapshot 2026-05-18

**What this is:** A point-in-time copy of `C:\Users\mpsch\.claude\skills\` taken
just before the user-level shadow skills were retired from active use.

**Why archived:** During BATON 073 cleanup, all user-level project-specific skills
were retired in favor of canonical project-level versions at
`<project>/.claude/skills/`. The "best version per skill" was selected and
promoted to project-level (see decisions table below). The user-level copies
are no longer in active use, but per the project's no-delete policy, they are
preserved here.

---

## Per-skill final decisions (which version became canonical at project-level)

| Skill | Canonical source chosen | Rationale |
|-------|-------------------------|-----------|
| `baton-pipeline-qc/` | **User-level** (Apr-13, 7,154 B) → synced to project | User-level had Module Reference table, M3 Run Notes, "BATON is the authority" framing, output-format Module field. Project version was an older skeleton (only M1/M2). |
| `board-startup/` | **Project-level** (May-18, 3,493 B) | Project version references current `REPO_MAP.md`; user-level was stale (referenced obsolete `README.json`). |
| `body-system-qc/` | **Both merged** — project SKILL.md (byte-identical) + user's `references/taxonomy_map.md` synced over | Union of unique content. |
| `exa-research-search/` | **User-level** (Apr-5, 15K) → promoted to project | No prior project-level version. |
| `methodology-scout/` | **User-level** Cowork `.skill` zip → extracted to project | No prior project-level version. Verified zip contained only `SKILL.md` (12,633 B) — complete extraction. |
| `methodology_scout/` (typo dir) | **N/A** — orphan typo-directory. Only file inside was a work-product investigation report (not a skill), rescued to `_archive_/methodology_notes/` | Was never a real skill. |
| `repo-error-review/` | **Project-level** (May-18, LF) | Content-identical to user-level apart from CRLF/LF line endings. |
| `article-citation-qc/` and `article-citation-qc.skill` | **Both retired** — entire skill superseded per BATON 068 | Replaced by `corpus-integrity-qc`. Curated archive at `../article-citation-qc/` with detailed README. |

---

## What lives where (after this archive operation)

| Skill | Active canonical location | Archive |
|-------|---------------------------|---------|
| baton-pipeline-qc | `.claude/skills/baton-pipeline-qc/` (project) | this folder |
| board-startup | `.claude/skills/board-startup/` (project) | this folder |
| body-system-qc | `.claude/skills/body-system-qc/` (project, with references/) | this folder |
| exa-research-search | `.claude/skills/exa-research-search/` (project) | this folder |
| methodology-scout | `.claude/skills/methodology-scout/` (project) | this folder |
| methodology_scout (typo) | n/a | this folder + `_archive_/methodology_notes/` (rescued .md) |
| repo-error-review | `.claude/skills/repo-error-review/` (project) | this folder |
| article-citation-qc | RETIRED (replaced by corpus-integrity-qc) | `../article-citation-qc/user-level/` (curated copy) + this folder (raw snapshot) |
| article-citation-qc.skill | RETIRED | `../article-citation-qc/cowork-zip.skill` + this folder (raw snapshot) |

---

## If you ever need to restore a skill to user-level

Copy from this folder back to `C:\Users\mpsch\.claude\skills\`. But note that
restoring a shadow will re-create the "shadow skills" problem that BATON 073
cleaned up — `~/.claude/skills/` resolves bare-slash commands before
project-level on the same name, so the user-level copy will silently
preempt the canonical project version.

---

*Snapshot taken: 2026-05-18 during BATON 073 amendment.*
