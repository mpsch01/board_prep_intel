# Deprecated Skills Archive

This directory holds **retired** Claude Code skills that were superseded by newer
skills or workflow changes. Material is preserved for historical reference and
potential script salvage — not for active use.

**Do not invoke these skills directly.** They are archived for reading only.

---

## Layout

```
deprecated_skills/
└── <skill-name>/
    ├── README.md           — why this was deprecated, what replaced it, what's salvageable
    ├── project-level/      — copy of the project-level `.claude/skills/<name>/` at retirement
    ├── user-level/         — copy of the user-level `~/.claude/skills/<name>/` at retirement
    ├── cowork-zip.skill    — (optional) Cowork-era `.skill` zip if one existed
    └── <other-artifacts>/  — strays, related M-module scripts, etc.
```

---

## Entries

### `article-citation-qc/` (retired 2026-05-18)
Replaced by **`corpus-integrity-qc`** (`.claude/skills/corpus-integrity-qc/`) per
BATON 068. Both shadow copies (user-level + project-level), the Cowork `.skill`
zip, AND the two M3-stray scripts that surfaced during BATON 073 cleanup are
preserved here. The user-level copy contains the most evolved scripts
(`generate_citation_sql.py`, `add_missing_articles.py`, `pdf_lookup_patch.py`)
which may be useful as reference if logic needs to be ported into corpus-integrity-qc.

### `user_level_shadow_copies_2026-05-18/` (retired 2026-05-18)
Point-in-time snapshot of `C:\Users\mpsch\.claude\skills\` taken during BATON
073 amendment, just before the user-level shadow skills were retired. The
"best version per skill" was promoted to project-level (`.claude/skills/`) —
see the snapshot's own README for the per-skill decisions table. Includes
shadow copies of `baton-pipeline-qc`, `board-startup`, `body-system-qc`,
`exa-research-search`, `methodology-scout`, `methodology_scout` (orphan typo
dir), `repo-error-review`, plus duplicate copies of the article-citation-qc
shadow (which is also curated separately above).
