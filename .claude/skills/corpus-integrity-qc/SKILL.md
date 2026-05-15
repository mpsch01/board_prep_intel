---
name: corpus-integrity-qc
description: >
  End-to-end integrity audit of the ITE Intelligence DB against ABFM ground-truth
  PDFs (critique + exam, 2018–2025). Runs three parallel auditors — text fidelity
  (parsing, encoding, formatting), citation linkage (multi-reference QID↔article),
  and structural integrity (xref + derived-cache consistency) — then produces a
  single tiered QC report with optional SQL remediation. ALWAYS trigger when the
  user mentions: corpus integrity, DB integrity, parsing QC, citation QC, xref QC,
  article verification, ground-truth audit, encoding artifacts, Wing-dings / Symbol
  font problems, truncated questions or explanations, broken references,
  QID-article mismatches, USPSTF umbrella problem, or any concern about the
  fidelity of the DB to the source ABFM PDFs. Also trigger proactively before
  re-running resident analyses if corpus integrity hasn't been verified recently.
---

# Corpus Integrity QC Skill

## Why this skill exists

The ABFM ITE critique + exam PDFs are the **ground truth** for the entire ITE
Intelligence System. The DB is the system under test. This skill verifies that
the DB faithfully represents the ground truth, across three independent layers:

| Layer | Goal | Ground truth |
|-------|------|--------------|
| **A — Text fidelity** | DB content matches PDF text; no encoding/format artifacts | Source PDFs |
| **B — Citation linkage** | Each QID's bag of articles matches the critique's bag | Critique staging JSONs |
| **C — Structural integrity** | Derived caches + second-order links agree with the bridge table | DB itself |

The skill produces:
1. **`qc_report.md`** — findings by layer + severity
2. **`fixes.sql`** — tiered SQL: auto-safe, review-required, manual-only
3. **`findings_{layer}.json`** — per-layer raw outputs for downstream tooling

**Never auto-applies SQL.** Always presents for review.

---

## V1 scope

- **Corpus:** ITE only (1,639 questions, 8 years, 2018–2025). AAFP BRQ is v2.
- **Layer A depth:** Hybrid — detect-only scan + spot re-extraction on flagged QIDs.
- **Fix tiering:** Auto-safe / Review / Manual (see `references/fix_tiers.md`).

---

## Project paths

```
PROJECT_ROOT = board_prep_intel/
DB           = PROJECT_ROOT/00_database/db/ite_intelligence.db
CRITIQUE_DIR = PROJECT_ROOT/01_module.1_warehouse/ite_exams/
STAGING_DIR  = PROJECT_ROOT/02_module.2_processor/outputs/
SKILL        = PROJECT_ROOT/.claude/skills/corpus-integrity-qc/
OUTPUT_DIR   = PROJECT_ROOT/03_module.3_analyst/outputs/corpus_qc/{YYYY-MM-DD}/
```

All scripts use dynamic path resolution: `SCRIPT_DIR = Path(__file__).resolve().parent`
with `PROJECT_ROOT` resolved relative to the staging directory anchor.

---

## Workflow

### Phase 1 — Verify staging JSONs exist (run first, always)

For each year 2018–2025, check `STAGING_DIR/YYYY_critique_refs_staging.json`.
For any missing years, tell the user:

> "I need you to run these extraction commands — one per missing year. Run each
> from `PROJECT_ROOT/02_module.2_processor/scripts/`:"

```bash
python extract_ite_critique_refs.py --pdf ../../01_module.1_warehouse/ite_exams/YYYY_critique.pdf --year YYYY
```

**Do NOT use `--commit`.** Staging mode only.

Wait for confirmation before proceeding.

### Phase 2 — Dispatch three audit agents in parallel

Launch via the `Agent` tool, all in one message:

```
1. structural-integrity-auditor  → findings_layer_c.json
2. citation-linkage-auditor      → findings_layer_b.json
3. text-fidelity-auditor         → findings_layer_a.json
```

Each agent has its own prompt under `agents/`. Each writes its findings JSON to
`OUTPUT_DIR`. Coordinator (main thread) waits for all three to complete.

**Why parallel:** Layers are independent. Layer A is heaviest (PDF re-reads on
flagged items). Layer C is fast but ~20 distinct SQL audits. Layer B is medium.
Parallel cuts wall-clock ~3× and gives each agent a clean context window.

### Phase 3 — Merge findings and generate report

Coordinator reads the three findings JSONs, runs
`scripts/build_report.py` to produce `qc_report.md`. Report structure:

```markdown
# Corpus Integrity QC Report
Generated: {date} | Years covered: {years} | Total findings: N

## Executive Summary
| Layer | Check | Count | Severity |
| ...   | ...   | ...   | ...      |

## Layer A — Text Fidelity Findings
### Encoding artifacts (N) ...
### Truncation candidates (N) ...
### Format drift (N) ...

## Layer B — Citation Linkage Findings
### CRITIQUE_REF_MISSING_FROM_DB (N) ...
### DB_REF_NOT_IN_CRITIQUE (N) ...
### UNMATCHED_CITATION (N) ...
### TRUNC_TITLE / AUTHOR_ARTIFACT / UMBRELLA / NULL_CLEAN_REF ...

## Layer C — Structural Integrity Findings
### qid_list cache drift (N) ...
### citation_count mismatch (N) ...
### exam_years / unique_years drift (N) ...

## Recommended Next Steps
1. Review and apply auto-safe SQL block
2. Manually triage review-tier items
3. ...
```

### Phase 4 — Generate tiered SQL

Run `scripts/generate_fixes.py`. Output `fixes.sql` partitioned into three blocks:

```sql
-- ============================================================
-- TIER 1: AUTO-SAFE — high confidence, no judgment required
-- (encoding fixes, derived-cache rebuilds, exact-match inserts)
-- ============================================================
...

-- ============================================================
-- TIER 2: REVIEW REQUIRED — fuzzy or ambiguous
-- (fuzzy citation matches, candidate truncations)
-- ============================================================
...

-- ============================================================
-- TIER 3: MANUAL — needs human judgment
-- (UMBRELLA, NULL_CLEAN_REF, unmatched citations)
-- ============================================================
-- (report-only; no SQL generated)
```

### Phase 5 — Present to user

Present `qc_report.md` summary + per-tier SQL counts. Wait for explicit approval
per tier before any DB write. Apply via the fix-applier subagent.

---

## After audit

- Update `articles.qid_list` cache if Layer C found drift (regenerate from xref).
- Remind user to re-run resident analyses if any Tier 1 fixes applied.
- Archive `findings_*.json` + `qc_report.md` + `fixes.sql` in OUTPUT_DIR with date.

---

## Locked rules that apply

- **Source data is protected.** Never auto-apply SQL. Never overwrite ground-truth PDFs.
- **Fix the data, not the code.** Findings drive DB-level repairs, not script workarounds.
- **Multi-reference is canonical.** `qid_art_xref` is a many-to-many bridge.
  Never treat one QID as having only one article. (This is the bug the original
  `article-citation-qc` skill had — see BATON 058.)
- **QC after integration.** After fixes applied, run a smoke audit of one resident
  analysis to confirm downstream effects.
