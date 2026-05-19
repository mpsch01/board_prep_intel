# article-citation-qc — RETIRED

**Retired:** 2026-05-18 (BATON 073 amendment)
**Replaced by:** `corpus-integrity-qc` (`.claude/skills/corpus-integrity-qc/`)
**Replacement rationale:** BATON 068 — the 4-layer corpus-integrity-qc architecture
(text fidelity / citation linkage / structural integrity / report+remediation)
subsumes everything article-citation-qc did and adds Layers A (text) + C (structural)
that article-citation-qc never had. Plus, the original `run_citation_qc.py` had a
confirmed dict-overwrite bug (lines 207–210 in the May 18 version).

---

## What's preserved here

| Subfolder | Source | Notes |
|-----------|--------|-------|
| `user-level/` | `~/.claude/skills/article-citation-qc/` (Apr 15 dir, May 7 scripts) | **Most evolved version.** Has 5 scripts including the superseding `generate_citation_sql.py`, plus `add_missing_articles.py` and `pdf_lookup_patch.py`. References / and SKILL.md describe the full Phase 1–7 workflow. |
| `project-level/` | `.claude/skills/article-citation-qc/` (May 18 BATON 071 promotion) | Older skeleton: 2 scripts (the deprecated `generate_sql_fixes.py` + buggy `run_citation_qc.py`), trimmed SKILL.md. |
| `cowork-zip.skill` | `~/.claude/skills/article-citation-qc.skill` (Apr 15 Cowork export) | Original Cowork-era installable skill zip. |
| `m3-stray-scripts/` | `_archive_/legacy_article_citation_qc/` (BATON 073) | Two stray scripts found untracked in `03_module.3_analyst/scripts/` — `run_citation_qc.py` + `generate_sql_fixes.py`, both May 18. Identical to project-level scripts. |

---

## If you ever need to salvage logic

The user-level scripts (May 7) are the canonical reference. In particular:
- `generate_citation_sql.py` — newer pattern; 3-section SQL output (TRUNC_TITLE / AUTHOR_ARTIFACT / QID_XREF_REBUILD with multi-reference per QID).
- `add_missing_articles.py` — auto-assigns next ART-ID for citations with no DB record.
- `pdf_lookup_patch.py` — for parser-missed QIDs; references manually read from PDFs.

Port into `corpus-integrity-qc` if a use case demands it. Otherwise leave undisturbed.
