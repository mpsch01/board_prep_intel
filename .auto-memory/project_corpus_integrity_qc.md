---
name: Corpus integrity QC skill (replacing article-citation-qc)
description: 4-layer ITE corpus audit skill — text fidelity + citation linkage + structural integrity + tiered fixes; supersedes buggy article-citation-qc
type: project
---

# Corpus Integrity QC Skill — Replacing article-citation-qc

The corpus-integrity-qc skill audits the ITE Intelligence DB against ABFM ground-truth PDFs (critique + exam, 2018–2025). It replaces article-citation-qc, which had a confirmed dict-overwrite bug in `run_citation_qc.py` (lines 207–210) that produced ~932 false-positive QID_MISMATCH findings against the multi-reference `qid_art_xref` table established by BATON 058.

## Architecture (4 layers, parallel agent dispatch)

- **Layer A — text fidelity**
  - Encoding artifacts (Wing-dings / Symbol-font characters, double-encoded Latin chars)
  - Truncated question stems / answer choices / explanations
  - Format drift across years (2018-2019 PDF-only vs 2020-2025 DOCX-derived)
  - Hybrid detect-only + spot re-extract from source PDFs

- **Layer B — citation linkage**
  - Multi-reference-aware: each QID may legitimately link to multiple ART-IDs
  - Critique bag vs DB bag comparison using set-containment semantics (not equality)
  - QID ↔ ART-ID linkage validated against critique PDF ground truth
  - Replaces the broken article-citation-qc QID_MISMATCH check

- **Layer C — structural integrity** ✅ **functional**
  - `qid_list` / `citation_count` / `exam_years` / `unique_years` cache drift detection
  - Orphan xref row detection (xref rows pointing to non-existent QIDs or articles)
  - Validated against canonical DB; 1,798 findings on first smoke test
  - Implemented in `scripts/layer_c_structural.py`

- **Layer D — report + remediation**
  - Tiered SQL output:
    - **Tier 1 — auto-safe** (derived-cache rebuilds; no source data changes)
    - **Tier 2 — review** (clinical/citation corrections needing human sign-off)
    - **Tier 3 — manual** (ambiguous, needs PDF re-inspection)
  - Single consolidated QC report combining findings from Layers A/B/C
  - Optional SQL remediation file split by tier

## v1 Scope

ITE questions + articles only. AAFP BRQ deferred to v2 (different ground-truth source — BRQ HTML scrapes, not PDF critiques).

## Why It Matters

The original article-citation-qc skill is structurally incompatible with the multi-reference `qid_art_xref` schema that BATON 058 established. Without this rebuild, every QC run generates hundreds of spurious "mismatch" alerts. The corpus-integrity-qc skill restores the ability to audit corpus integrity safely and is the QC gate that must clear before any resident analysis re-run.

## Files

- `.claude/skills/corpus-integrity-qc/SKILL.md`
- `.claude/skills/corpus-integrity-qc/references/qc_rules.md` — all checks per layer
- `.claude/skills/corpus-integrity-qc/references/fix_tiers.md` — Tier 1/2/3 policy
- `.claude/skills/corpus-integrity-qc/scripts/utils.py` — ENCODING_FIXES table, AUTHOR_STOP_WORDS, parsers shared across layers
- `.claude/skills/corpus-integrity-qc/scripts/layer_c_structural.py` — functional Layer C

## Open Work (BATON 068)

- **DEFERRED-CORPUS-QC-LAYERS-AB-D** — build Layer A + B + D + coordinator + subagent prompts
- **DEFERRED-LAYER-C-CACHE-REBUILD** — 1,797 Tier-1 cache-rebuild SQL fixes pending Layer D rendering
- **DEFERRED-ORPHAN-XREF-QID-2024-0067** — Layer C surfaced QID-2024-0067/ART-2073 xref row where the QID does not exist in `questions`; needs manual remediation
