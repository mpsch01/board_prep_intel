# Fix Tier Reference

Findings are graded into three tiers based on **confidence + auto-application safety**, not severity alone. A LOW-severity cache drift can be Tier 1 (because the fix is mechanical and reversible). A HIGH-severity umbrella article is Tier 3 (because the fix needs judgment).

---

## Tier 1 — Auto-safe

**Definition:** Fix is mechanical, the corrected value is unambiguously derivable from a trusted source (clean_ref, the bridge table, or a known-bad-sequence map), and the change is fully reversible by re-running the QC pipeline.

**Examples:**
- `ENCODING_ARTIFACT` — string-replace `ï‚£` → `≤`. Trivially reversible if wrong (re-run finds it again).
- `TRUNC_TITLE` (exact suffix match) — `UPDATE articles SET title = ?` where corrected value is the full title parsed from `clean_ref` and the current title is a proven suffix.
- `AUTHOR_ARTIFACT` — `UPDATE articles SET author1 = ?` from parsed first segment of clean_ref.
- `CRITIQUE_REF_MISSING_FROM_DB` with `match_score == 1.0` — `INSERT OR IGNORE INTO qid_art_xref(qid, article_id, exam_year) VALUES (...)`.
- All Layer C cache rebuilds (`qid_list`, `citation_count`, `exam_years`, `unique_years`) — pure recomputation from the bridge.

**Behavior:** SQL is generated. User opens the file, eyeballs, runs the whole block.

**SQL convention:** Each statement preceded by a one-line comment with the finding ID:
```sql
-- [A1-0042] articles.title encoding fix
UPDATE articles SET title = 'Heel pain: diagnosis and management' WHERE article_id = 'ART-0230';
```

---

## Tier 2 — Review required

**Definition:** Fix is identifiable but has fuzzy edges — fuzzy citation match, ambiguous truncation, candidate that needs eyeballing. SQL is generated but every statement is gated by a `-- REVIEW:` comment.

**Examples:**
- `CRITIQUE_REF_MISSING_FROM_DB` with `match_score < 1.0` — INSERT generated, but with `-- REVIEW: fuzzy match (0.84)` and the DB+critique citation excerpts inline as evidence.
- `TRUNCATION_CANDIDATE` (Layer A2) — re-extracted PDF text is shown alongside the DB value, but the human decides whether the PDF re-extraction is itself trustworthy.
- `FORMAT_DRIFT` (Layer A3) — e.g., `correct_letter = 'F'` flagged, but the correction depends on which choice the question actually marks as correct.
- `ORPHAN_XREF` (Layer C5) — `DELETE FROM qid_art_xref WHERE qid = ? AND article_id = ?` generated, but typically you want to look at why the orphan exists first.

**Behavior:** SQL is generated, every statement is commented out by default (`-- UPDATE ...`). User uncomments after review, then runs the block.

**SQL convention:**
```sql
-- [B1-0123] CRITIQUE_REF_MISSING_FROM_DB (fuzzy match 0.82) — REVIEW BEFORE UNCOMMENTING
-- Critique: "Reust CE. Acute abdominal pain in children. Am Fam Physician 2016..."
-- DB clean_ref: "Reust C. Acute abdominal pain — pediatric. Am Fam Physician 2016..."
-- INSERT OR IGNORE INTO qid_art_xref(qid, article_id, exam_year) VALUES ('QID-2018-0014', 'ART-1057', 2018);
```

---

## Tier 3 — Manual

**Definition:** Finding represents a real problem, but the fix requires human judgment that the skill cannot mechanize. Reported in the QC report; no SQL generated.

**Examples:**
- `UMBRELLA` — "USPSTF A and B Recommendations" cited across 12 topics. Resolution requires splitting the article into topic-specific records, which the skill can't propose mechanically.
- `NULL_CLEAN_REF` — citation_count > 0 but no clean_ref. Resolution requires finding the citation text in source PDFs.
- `UNMATCHED_CITATION` — critique cites a paper not in the articles table. Feeds the acquisition queue, not a SQL fix.
- `DB_REF_NOT_IN_CRITIQUE` (Layer B2) — informational; may be a legitimate enrichment link. Reported for visibility, not action.

**Behavior:** Listed in the QC report under "Manual triage required" with all evidence inline. No SQL.

---

## File layout

The generated `fixes.sql` is partitioned into three labeled blocks:

```sql
-- ============================================================
-- TIER 1: AUTO-SAFE — review summary, apply whole block
-- Total: N statements
-- ============================================================
BEGIN;
-- [A1-0001] ...
UPDATE ...;
-- ...
COMMIT;

-- ============================================================
-- TIER 2: REVIEW REQUIRED — uncomment after eyeballing each
-- Total: M statements (all commented by default)
-- ============================================================
-- BEGIN;
-- -- [B1-0123] ...
-- -- UPDATE ...;
-- COMMIT;

-- ============================================================
-- TIER 3: MANUAL — see qc_report.md for details, no SQL
-- Total: K findings
-- ============================================================
```

---

## Application workflow

1. User reads `qc_report.md` summary.
2. User opens `fixes.sql` in DB Browser for SQLite or sqlite3 CLI.
3. **Tier 1:** Run the entire BEGIN/COMMIT block. Pre-flight check passes ✔ → apply.
4. **Tier 2:** Per-statement review. Uncomment intended fixes. Run.
5. **Tier 3:** Refer to QC report. Address in separate sessions / workflows.

**Rollback:** Each session's outputs (report + fixes.sql + findings_*.json) archived under `outputs/corpus_qc/{YYYY-MM-DD}/`. Tier 1 blocks wrapped in BEGIN/COMMIT to permit rollback before commit if anything looks wrong.
