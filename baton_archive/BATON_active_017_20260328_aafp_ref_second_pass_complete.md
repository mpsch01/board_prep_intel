# BATON 017 — AAFP Ref Second-Pass Matching Complete
**Date:** 2026-03-28
**Session platform:** Windows PC (Cowork VM)
**Status:** Active
**Preceding BATON:** `BATON_active_016_20260327_aafp_enrichment_complete_ite_similarity_scored.md` (→ archive)
**Git hash:** `4caa6f5` (BATON 016 hash — new commit needed this session)
**GitHub remote:** `https://github.com/mpsch01/project-overhaul` (private)

---

## SESSION SUMMARY — What Was Done and Why

Short session. Verified Windows cleanup from BATON 016, then completed the AAFP ref matching second pass (Option 3). Built `aafp_ref_match_v2.py` — a standalone second-pass matcher using 4 strategies beyond what aafp_brq_import.py can do. Found and committed 12 new matches. Diagnosed the true ceiling of the unmatched pool.

---

### 1. Windows Cleanup Verification

- BATONs 013, 014, 015 confirmed archived in `baton_archive/`
- Sandbox originals confirmed deleted
- Git commit `4caa6f5` confirmed (BATON 016 content)
- **Still pending:** sandbox file deletions + baton_archive additions are staged but uncommitted. Run:
  ```
  git add -A && git commit -m "housekeeping: archive BATONs 013-015, clear sandbox"
  ```

---

### 2. aafp_ref_match_v2.py — Second-Pass Matcher

New script: `02_module.2_processor/scripts/aafp_ref_match_v2.py`

**Four strategies (applied in order, first match wins):**
- **S2** Space-tolerant vol/page + author — catches `YYYY; VOL(ISS): PAGE` with spaces
- **S3** AFP title keyword + year — matches AFP articles with non-standard summary clean_ref
- **S4** Cochrane CD number — exact CD-number match (e.g. CD006245)
- **S5** Guideline/society keyword + year — USPSTF/AHA/CDC statements, with first-author surname check to prevent cross-guideline false positives

**Design principle:** precision over recall. If multiple articles match = skip (ambiguous). One unambiguous match only.

**Run modes:** `--dry-run`, `--verbose`, `--stats`

**QC performed:** dry-run with `--verbose` revealed 1 false positive (Jessup 2009 ACCF/AHA Guidelines matched to Surawicz AHA/ACCF/HRS — different guidelines sharing keyword set). Fixed by adding first-author surname check to S5. Re-ran dry-run: clean. Then committed.

---

### 3. Results

| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| aafp_qid_art_xref rows | 797 | 809 | +12 |
| Unique questions linked | 586 | 596 | +10 |
| Link rate | 48.0% | 48.8% | +0.8% |

**Match breakdown:**
| Strategy | New Matches |
|----------|-------------|
| S2 space vol/page | 2 |
| S3 AFP title keyword | 1 |
| S4 Cochrane CD# | 2 |
| S5 guideline keyword | 7 |
| **Total** | **12** |

**aafp_citations match_status (final):**
| Status | Count |
|--------|-------|
| unmatched | 772 |
| matched | 724 |
| fuzzy | 73 |
| no_ref | 19 |
| s5_guideline | 7 |
| s4_cochrane_cd | 2 |
| s2_space_volpage | 2 |
| s3_afp_title | 1 |

---

### 4. Ceiling Diagnosis — Why Not More

Full breakdown of the 784 unmatched pool:

| Category | Count | Recoverable by matching? |
|----------|-------|--------------------------|
| Truncated scraper artifacts | 112 | No — no content |
| Journal articles not in DB | ~381 | No — articles don't exist yet |
| Books/textbooks | 154 | No — not in journal DB |
| Guideline/society statements | 60 | Partial — 7 matched |
| Cochrane reviews | 11 | Partial — 2 matched |
| Journal (spaces in vol/page) | 3 | Yes — 2 matched |
| AFP (in DB, different format) | ~202 | Mostly no — articles genuinely missing |

**Key insight:** 380/381 strict-vol/page citations point to articles not in DB. The AFP summary-format clean_ref issue is real but secondary — most AFP citations are also genuinely missing articles. **The path to higher linkage is acquisition, not cleverer matching.**

`aafp_ref_match_v2.py` is permanent infrastructure: re-run it after new articles are ingested and it will automatically pick up previously-unmatched citations.

---

## DB State (as of BATON 017)

| Table | Rows | Notes |
|-------|------|-------|
| articles | 1,936 | |
| questions (ITE) | 1,629 | 2018–2025 |
| qid_art_xref | 2,470 | |
| article_icd10 | 3,855 | |
| clinical_pathways | 3,093 | |
| article_vec | 1,936 | 100% coverage |
| question_vec | 1,629 | 100% coverage |
| aafp_questions | 1,221 | 7 enrichment cols |
| aafp_explanations | 1,221 | explanation_keywords populated |
| aafp_citations | 1,600 | match_status updated |
| aafp_citation_raw | 1,600 | full text archive |
| **aafp_qid_art_xref** | **809** | **596 unique questions linked (48.8%)** |
| aafp_question_vec | 1,221 | 100% coverage |
| aafp_question_icd10 | 1,876 | 577 questions |

---

## Housekeeping Carried Forward

- [ ] **Windows:** Stage + commit pending changes (sandbox deletions + baton_archive additions)
  ```
  git add -A && git commit -m "housekeeping: archive BATONs 013-015, clear sandbox"
  ```
- [ ] **Windows:** Stage + commit this session's new script
  ```
  git add 02_module.2_processor/scripts/aafp_ref_match_v2.py
  git commit -m "add aafp_ref_match_v2.py: second-pass citation matcher (S2-S5 strategies)"
  ```
- [ ] **Windows:** Archive BATON 016 → `baton_archive/`

---

## Deferred Flags (updated from BATON 016)

| Flag | Description | Priority |
|------|-------------|----------|
| **AAFP question reuse investigation** | Query WHERE ite_nearest_dist < 0.30 — exact dupes vs paraphrased? Sets up lag analysis | **HIGH** |
| **AAFP-ITE lag analysis** | xref + shared citations + timing delta + ite_nearest_dist; predictive watch list | HIGH |
| **229 citation gap articles** | 88 AFP batch-downloadable from `null_clean_ref_missing_articles_20260326.csv`; codon rename → ingest → enrich → re-run aafp_ref_match_v2.py | HIGH |
| `extract_ite_critique_refs.py` | BATON 014 design, not yet built | HIGH |
| `update_citation_trends.py` | BATON 014 design, not yet built | HIGH |
| `article_citation_trend` table | BATON 014 design, not yet created | HIGH |
| **Interactive vector dashboard** | HTML from aafp_vector_explorer data; `data:interactive-dashboard-builder` skill | MEDIUM |
| **129 missing AAFP questions** | ~13 incomplete quizzes from stalled scrape | MEDIUM |
| Intelligence 2.0 Layer 2 | `article_currency` via PubMed MCP | MEDIUM |
| Cookie refresh | `aafp_cookies.json` — re-export before next scrape | MEDIUM |
| FLAG 33 | VC_pass ART-ID rename — designed, not implemented | LOW |

---

## Next Steps (Ordered)

1. **Windows git commit** — housekeeping + new script (see above)
2. **AAFP question reuse investigation** — run the dist<0.30 query; confirm exact dupes vs paraphrased
3. **AAFP-ITE lag analysis** — the payoff; shared citations + timing delta + semantic proximity
4. **229 citation gap articles** — acquire AFP batch + others → ingest → re-run aafp_ref_match_v2.py
5. **Interactive vector dashboard** — HTML from vector explorer data

---

## Conventions Locked (additions this session)

- **aafp_ref_match_v2.py** = permanent second-pass infrastructure. Re-run after any new article ingestion.
- **Match statuses:** `s2_space_volpage`, `s3_afp_title`, `s4_cochrane_cd`, `s5_guideline` — distinct from import statuses (`matched`, `fuzzy`)
- **Ceiling rule:** Second-pass matching is exhausted. Higher linkage requires article acquisition, not more strategies.
- All prior conventions from BATON 016 unchanged.
