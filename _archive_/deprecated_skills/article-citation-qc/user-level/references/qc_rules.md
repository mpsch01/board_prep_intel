# QC Check Reference

## TRUNC_TITLE
**What it catches:** The `title` field in the articles table is a fragment of the real title — typically the portion *after* the colon in a colon-subtitled article. This is a PDF/text parsing artifact from the original ingest pipeline.

**How it's detected:**
- `title` is a suffix of the title extracted from `clean_ref` (e.g., `clean_ref` = "Heel pain: diagnosis and management", but `title` = "diagnosis and management")
- `title` matches a page-range pattern like "123–154" (DSM-5 style citation)
- `title` is contained within the extracted title and is substantially shorter (< 70% of length)

**Fix type:** SQL UPDATE to `title` field only. Corrected value comes from re-parsing `clean_ref`.

**Severity:** MEDIUM — affects display and searchability, but QID-article linkage is intact.

---

## AUTHOR_ARTIFACT
**What it catches:** The `author1` field contains a parsing stop-word instead of a real author surname. Happens when citations start with organizational prefixes like "Final Recommendation Statement: ..." and the parser grabs "Final" as the author.

**Common artifacts:** "Final", "US", "Updated", "Recommendation", "Task Force", "Services", "Preventive", "Statement", "Committee", "Working", "Group", "Panel", "Centers", "Department"

**How it's detected:** `author1.strip().lower()` is in the stop-word set.

**Fix type:** SQL UPDATE to `author1` field. Corrected value is the first token before the first comma in `clean_ref`.

**Severity:** MEDIUM — affects author-based search and display; QID linkage intact.

---

## UMBRELLA
**What it catches:** A single article record that is being used as a catch-all citation for many unrelated questions — the "umbrella" problem. The clearest example is an article like "USPSTF A and B Recommendations 2018" that absorbs questions about dozens of independent screening topics (breast cancer, lung cancer, obesity, etc.) instead of each topic having its own article record.

**How it's detected:**
- `citation_count >= 5` AND `unique_years >= 3`
- AND the linked QIDs span >= 4 distinct `blueprint_category` values OR >= 3 distinct `body_system` values

**Fix type:** Manual review required. The fix is to identify the specific sub-recommendation for each linked QID and either (a) create a new article record for the specific guideline, or (b) link the QID to an existing more-specific article.

**Severity:** HIGH (if citation_count >= 8) or MEDIUM — causes imprecise article-question linking which degrades resident report quality.

---

## QID_MISMATCH
**What it catches:** The ITE critique PDF (ground truth) says Question QID-YYYY-NNNN cites Article X, but the DB's `qid_art_xref` table has that same QID linked to a different Article Y.

**How it's detected:** For each record in the critique staging JSON with a successful match (matched or fuzzy_matched), compare `staging._article_id` vs `qid_art_xref.article_id` for the same QID.

**Fix type:** Handled by QID_XREF_REBUILD section in `generate_citation_sql.py`. The rebuild replaces per-QID xref rows with critique ground truth for all QIDs that have at least one staging match. Both exact and fuzzy matches are included — the SQL comments label each row's match type.

**Severity:** HIGH — directly causes wrong articles to be surfaced in resident reports.

---

## UNMATCHED_REF
**What it catches:** A citation in the ITE critique PDF that couldn't be matched to any existing article in the DB. This means there's an article referenced by the exam that isn't in our library at all.

**How it's detected:** Staging JSON records where `match_status = 'unmatched'`.

**Fix type:** **Acquisition queue entry** — NOT a data error to discard. Each unmatched citation
should trigger the acquisition pipeline:
1. Run `exa-research-search` skill to locate the paper/guideline online
2. If found: add via `add_missing_articles.py` (Phase 6 of skill workflow)
3. If not found: log in BATON as DEFERRED-QID-XREF-LIBRARY-GAPS

Track total count as "acquisition backlog." Target: reduce toward zero over successive sessions.

**Severity:** MEDIUM — represents a library gap. Doesn't corrupt existing data, but leaves
questions without a proper article link. Locked architectural principle: never discard, always acquire.

---

## NULL_CLEAN_REF
**What it catches:** An article that has been cited in exam questions (`citation_count > 0`) but has no `clean_ref` value. Without a clean_ref, the QC pipeline can't cross-validate this article's title or author, and the enrichment pipeline can't properly index it.

**How it's detected:** `clean_ref IS NULL` AND `citation_count > 0`.

**Fix type:** Add `clean_ref` manually. The citation text should be findable in the original critique PDF for the exam year(s) where this article was cited.

**Severity:** LOW — doesn't affect QID linkage, but degrades enrichment quality and blocks future QC validation.
