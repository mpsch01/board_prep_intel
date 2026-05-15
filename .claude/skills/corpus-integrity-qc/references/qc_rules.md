# QC Check Reference

All checks the corpus-integrity-qc skill performs, grouped by layer.

---

## Layer A — Text Fidelity

Ground truth: source PDFs in `01_module.1_warehouse/ite_exams/`.

### A1. ENCODING_ARTIFACT
**Catches:** Mojibake / Symbol-font / Wingdings artifacts in question_text, choices, explanation, or reference fields.

**How detected:** Substring scan against a known-bad sequence table (seeded from `build_custom_question_set.py:_ENCODING_FIXES`):

| Bad sequence | Corrected | Notes |
|---|---|---|
| `ï‚£` | `≤` | Symbol-font less-than-or-equal |
| `ï‚³` | `≥` | Symbol-font greater-than-or-equal |
| `Æ’` | `ƒ` | Latin-1 → UTF-8 mojibake |
| `â€œ` / `â€` | `"` / `"` | Smart-quote mojibake |
| `â€™` | `'` | Apostrophe mojibake |
| `â€"` | `—` | Em-dash mojibake |
| (full table in scripts/utils.py) |

**Severity:** MEDIUM — visible in DOCX outputs, breaks PDF rendering.
**Fix tier:** Tier 1 (auto-safe) — pure string replacement.

### A2. TRUNCATION_CANDIDATE
**Catches:** Fields that appear cut off mid-content.

**How detected:**
- Question text ends without `?`, `.`, or `)` AND length < 95th-percentile-of-year
- Choices field has fewer than expected delimiters
- Explanation ends mid-sentence (no terminal punctuation, length < expected)
- Reference field has dangling pipe `|` or unclosed numbered marker

**Severity:** HIGH — content is materially incomplete.
**Fix tier:** Tier 2 (review) — re-extract from PDF, then update.

### A3. FORMAT_DRIFT
**Catches:** Structural anomalies that suggest parsing errors.

**How detected:**
- `correct_letter` not in {A, B, C, D, E}
- `choices` field doesn't parse into expected count (5 for standard MC)
- `reference` field fails to parse into citation list (mixed numbering + pipe)
- `body_system` / `blueprint` is empty for a year where coverage should be 100%

**Severity:** MEDIUM-HIGH depending on field.
**Fix tier:** Tier 2 (review).

### A4. PDF_DIFF (spot re-extract)
**Catches:** Field-level disagreement between DB and PDF.

**How detected:** For each QID flagged by A1/A2/A3, re-extract from source PDF and produce a per-field diff. Findings include both DB value and PDF value for human review.

**Severity:** Inherited from the triggering check.
**Fix tier:** Tier 2 (review).

---

## Layer B — Citation Linkage

Ground truth: `YYYY_critique_refs_staging.json` files in `02_module.2_processor/outputs/`.

For each QID, compare two bags:
- **DB bag:** `SELECT article_id FROM qid_art_xref WHERE qid = ?`
- **Critique bag:** `_article_id` values from staging records matching that QID with `match_status` ∈ {matched, fuzzy_matched}

### B1. CRITIQUE_REF_MISSING_FROM_DB
**Catches:** Critique cites article X for QID-Y, but no row in `qid_art_xref` links them.

**How detected:** `critique_article_id NOT IN db_bag[qid]`.

**Severity:** HIGH — DB is under-linked. Resident reports may miss a valid source.
**Fix tier:**
- Tier 1 if `match_score == 1.0`: `INSERT OR IGNORE INTO qid_art_xref ...`
- Tier 2 if fuzzy: review-only SQL with `-- FUZZY:` comment

### B2. DB_REF_NOT_IN_CRITIQUE
**Catches:** DB has QID↔Y in xref, but critique doesn't list Y for that QID.

**How detected:** `db_article_id NOT IN critique_bag[qid]`.

**Severity:** LOW — informational. May be legitimate enrichment-pipeline link (e.g., pathway-derived), not a critique citation.
**Fix tier:** Tier 3 (manual / report-only). No SQL generated.

### B3. UNMATCHED_CITATION
**Catches:** Critique cites a paper with no record in `articles` at all.

**How detected:** Staging record with `match_status == 'unmatched'`.

**Severity:** MEDIUM — acquisition queue entry.
**Fix tier:** Tier 3 (manual). Feeds the article-acquisition workflow.

### B4. TRUNC_TITLE
**Catches:** `articles.title` is a fragment of the full title in `clean_ref`.

**How detected:** See `is_truncated_title()` in scripts/utils.py. Detects colon-split artifacts, page-range artifacts, and short-substring containment.

**Severity:** MEDIUM — display + search affected, linkage intact.
**Fix tier:** Tier 1 — `UPDATE articles SET title = ?`.

### B5. AUTHOR_ARTIFACT
**Catches:** `articles.author1` is a parsing stop-word (e.g., "Final", "US", "Updated").

**How detected:** `author1.lower()` in `AUTHOR_STOP_WORDS` set.

**Severity:** MEDIUM.
**Fix tier:** Tier 1 — `UPDATE articles SET author1 = ?` (corrected from clean_ref).

### B6. UMBRELLA
**Catches:** Single article used as catch-all citation across diverse topics (the "USPSTF A and B Recommendations" pattern).

**How detected:** `citation_count >= 5 AND unique_years >= 3 AND (blueprint_categories >= 4 OR body_systems >= 3)`.

**Severity:** HIGH if citation_count >= 8, else MEDIUM.
**Fix tier:** Tier 3 (manual). Resolution requires splitting umbrella into topic-specific records.

### B7. NULL_CLEAN_REF
**Catches:** Article has `citation_count > 0` but `clean_ref IS NULL`.

**Severity:** LOW.
**Fix tier:** Tier 3 (manual). Populate from critique PDF for the cited years.

---

## Layer C — Structural Integrity

Ground truth: the `qid_art_xref` bridge table itself.

### C1. QID_LIST_CACHE_DRIFT
**Catches:** `articles.qid_list` (JSON cache) disagrees with reverse-query of `qid_art_xref`.

**How detected:**
```sql
-- For each article, compare:
--   cached:   JSON.parse(articles.qid_list)
--   computed: SELECT qid FROM qid_art_xref WHERE article_id = ?
```
Flag if symmetric difference is non-empty.

**Severity:** LOW.
**Fix tier:** Tier 1 — rebuild cache: `UPDATE articles SET qid_list = ?`.

### C2. CITATION_COUNT_MISMATCH
**Catches:** `articles.citation_count` ≠ `COUNT(*) FROM qid_art_xref WHERE article_id = ?`.

**Severity:** LOW.
**Fix tier:** Tier 1 — `UPDATE articles SET citation_count = ?`.

### C3. EXAM_YEARS_DRIFT
**Catches:** `articles.exam_years` (JSON) ≠ `SELECT DISTINCT exam_year FROM qid_art_xref WHERE article_id = ?`.

**Severity:** LOW.
**Fix tier:** Tier 1 — rebuild cache.

### C4. UNIQUE_YEARS_MISMATCH
**Catches:** `articles.unique_years` ≠ length of distinct-exam-years set.

**Severity:** LOW.
**Fix tier:** Tier 1 — `UPDATE articles SET unique_years = ?`.

### C5. ORPHAN_XREF
**Catches:** `qid_art_xref` row points to an `article_id` not in `articles`, or a `qid` not in `questions`.

**Severity:** HIGH — foreign-key integrity violated (FKs not declared but enforced semantically).
**Fix tier:** Tier 2 (review) — typically delete row, but worth eyeballing each case.

### C6. ZERO_CITATION_LINKED
**Catches:** Article has `citation_count == 0` but at least one `qid_art_xref` row points to it.

**Severity:** LOW — inverse of C2.
**Fix tier:** Tier 1 — recompute citation_count.

### C7. UNLINKED_CITED_ARTICLE
**Catches:** Article has `citation_count > 0` but no rows in `qid_art_xref`.

**Severity:** MEDIUM — cache stale, or xref was deleted without cache update.
**Fix tier:** Tier 1 — reset citation_count to 0 (if truly orphaned) OR Tier 3 (manual) if the original citation source can be recovered.

---

## Severity → Fix-tier matrix

| Severity \\ Tier | Tier 1 (auto-safe) | Tier 2 (review) | Tier 3 (manual) |
|---|---|---|---|
| HIGH | B1 (exact-match) | A2, A3, A4, B1 (fuzzy), C5 | B6 (umbrella) |
| MEDIUM | A1, B4, B5 | A3 (some) | B3, C7 (manual case) |
| LOW | C1, C2, C3, C4, C6, C7 (auto case) | — | B2, B7 |

Tier 1 SQL can be auto-applied after user opens the file and confirms.
Tier 2 SQL is generated but flagged with `-- REVIEW:` comments.
Tier 3 produces report-only entries (no SQL).
