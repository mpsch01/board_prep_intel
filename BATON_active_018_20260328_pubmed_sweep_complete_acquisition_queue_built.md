# BATON 018 — PubMed Sweep Complete, Acquisition Queue Built
**Date:** 2026-03-28
**Session platform:** Windows PC (Cowork VM)
**Status:** Active
**Preceding BATON:** `BATON_active_017_20260328_aafp_ref_second_pass_complete.md` (→ archive)
**Git hash:** `4caa6f5` (3 commits pending this session)
**GitHub remote:** `https://github.com/mpsch01/project-overhaul` (private)

---

## SESSION SUMMARY — What Was Done and Why

Continuation of the REMAINING citation sweep from BATON 017. Used the PubMed MCP to work through the 129 REMAINING unmatched citations — looking up each by author/year/journal/vol/page to confirm identity, cross-reference against the DB, and separate "linkable today" from "acquisition targets."

**Key finding:** The REMAINING bucket is almost entirely genuinely missing articles — not formatting issues. Of ~88 citations queried (79 named + 9 Cochrane), only 6 were in the DB and linkable. The other 46 confirmed PMIDs are articles that need to be acquired.

---

## 1. New Linkages Applied This Session

6 total new rows added to `aafp_citations` (match_status = 'pubmed_confirmed') and `aafp_qid_art_xref`:

| Citation ID | Article | Match Route |
|-------------|---------|-------------|
| AAFP-50524-C2 | ART-0820 (Martinez Quintero 2021 Thyroiditis) | PubMed confirmed PMID 34913664 → DB author/year |
| AAFP-50306-C3 | ART-0848 (McMurray 2019 Dapagliflozin) | PubMed confirmed PMID 31535829 → DB author/year |
| AAFP-50341-C1 | ART-0867 (Michaudet 2017 Chronic Cough) | PubMed confirmed PMID 29094873 → DB author/year |
| AAFP-50042-C1 | ART-1204 (Stevens 2014 Skin infections IDSA) | Near-exact DB match (author/year check) |
| AAFP-50553-C1 | ART-0238 (Chow 2012 Rhinosinusitis IDSA) | Near-exact DB match |
| AAFP-50697-C1 | ART-1551 (Shaw 2016 DDH Pediatrics) | Near-exact DB match |

**xref after this session: 815 rows, 598 unique questions linked (49.1%)**

---

## 2. Acquisition Queue Built

New file: `00_database/readable_db_files/aafp_pubmed_acquisition_queue_20260328.csv`

**49 rows total** — articles confirmed by PubMed PMID that are NOT currently in the DB:
- 46 with confirmed PMID + PubMed URL
- 3 Cochrane reviews confirmed by CD number but PMID not resolved (Ma 2016, Binks 2006, Dennis 2008)

**Top acquisition categories:**
| Category | Count | Notes |
|----------|-------|-------|
| Cochrane reviews | 9 | Walitt, Venekamp, Keay, Albalawi, Herbert, Yeung, Ma, Binks, Dennis |
| Pediatrics/AAP CPGs | 6 | Lieberthal 2013, Ralston 2014, Wald 2013, Mittal 2014, Byington 2012, Shonkoff 2011 |
| BMJ case/review articles | 8 | Pallan, Nunes, Al-Hussaini, Goundry, Myat, Reddy, Kiire, Binic |
| Cardiology guidelines | 3 | Bonow 2008 (x2), Amsterdam 2014 |
| Family medicine journals | 5 | McDonald, Parish/Simon HSDD, Mansour, Michaudet (already linked) |
| NEJM | 2 | Stewart 2011, Wilson JF 2014 (stable IHD) |
| Ann Intern Med In The Clinic | 3 | Henry 2015, Wilson JF 2011 PCOS, Wilson JF 2014 IHD |

Each row in the CSV has: citation_id, aafp_qid, pmid, pubmed_url, author, year, title, journal, notes.
This is the direct input for the next article acquisition pass.

---

## 3. REMAINING Bucket Final Status

After PubMed sweep:
- 129 REMAINING citations going in
- 6 linked (moved to pubmed_confirmed)
- ~88 queried via PubMed → 46 confirmed PMIDs, all acquisition targets
- ~35 not queried (organizational, UpToDate, truncated, websites — these are effectively irrecoverable or low-yield)
- **Remaining true REMAINING: ~35** (organizational/web sources, no PubMed entry)

The REMAINING bucket has been operationally exhausted. Next linkage step requires article acquisition.

---

## 4. Overall Citation Linkage Summary (as of BATON 018)

| match_status | Count |
|-------------|-------|
| matched (S0 exact) | 724 |
| fuzzy (S1 vol/page+author) | 73 |
| pubmed_confirmed | 6 |
| no_ref | 19 |
| unmatched (remaining) | 778 |
| **Total citations** | **1,600** |

**xref rows: 815 (598 unique AAFP questions = 49.1%)**

**Ceiling without acquisition:** ~815 xref rows. Each acquired article = potentially 1-3 more xref rows.
**Expected after acquisition:** If 46 articles acquired → potentially +50-80 more xref rows → ~865-895 rows (~71% of questions linked).

---

## 5. New Files This Session

| File | Location | Notes |
|------|----------|-------|
| `aafp_pubmed_acquisition_queue_20260328.csv` | `00_database/readable_db_files/` | 49 rows, 46 with PMID + URL |

---

## DB State (as of BATON 018)

| Table | Rows | Notes |
|-------|------|-------|
| articles | 1,936 | unchanged |
| questions (ITE) | 1,629 | unchanged |
| aafp_questions | 1,221 | unchanged |
| aafp_citations | 1,600 | 6 new pubmed_confirmed rows |
| aafp_qid_art_xref | 815 | +6 from this session (was 809) |
| aafp_citation_raw | 1,600 | unchanged |
| aafp_question_icd10 | 1,876 | unchanged |
| unmatched_class column | populated | IRRECOVERABLE/JOURNAL_MISSING/REMAINING |

---

## Housekeeping Carried Forward

- [ ] **Windows:** Archive BATONs 013 + 014 + 015 + 016 + 017 → `baton_archive/`
- [ ] **Windows:** Delete sandbox originals per `04_module.4_sandbox/_DELETE_THESE_FROM_WINDOWS.txt`
- [ ] **Windows:** Clean up temp files from project root: `parse_remaining.py`, `show_remaining.py`, `remaining_parsed.json`, `remaining_named.json`
- [ ] **Git:** 3 commits pending this session:
  1. `aafp_ref_match_v2.py` + `classify_unmatched_citations.py` (from BATON 017)
  2. DB changes (6 new pubmed_confirmed rows)
  3. New BATON + CLAUDE.md update

**Suggested commit messages:**
```
git add 02_module.2_processor/scripts/aafp_ref_match_v2.py
git add 02_module.2_processor/scripts/classify_unmatched_citations.py
git commit -m "add aafp_ref_match_v2.py (S2-S5 strategies, 12 matches) + classify_unmatched_citations.py (IRRECOVERABLE/JOURNAL_MISSING/REMAINING)"

git add 00_database/readable_db_files/aafp_pubmed_acquisition_queue_20260328.csv
git add BATON_active_018* CLAUDE.md
git commit -m "PubMed sweep: 6 new pubmed_confirmed linkages, 49-row acquisition queue built"
```

---

## Deferred Flags

| Flag | Description | Priority |
|------|-------------|----------|
| **AAFP article acquisition** | `aafp_pubmed_acquisition_queue_20260328.csv` — 46 articles with PMID URLs ready. Download PDFs, add to articles table with codon filenames, re-run aafp_ref_match_v2.py | **HIGH** |
| **AAFP question reuse investigation** | Query WHERE ite_nearest_dist < 0.30; confirm exact dupes vs paraphrased | **HIGH** |
| **AAFP-ITE lag analysis** | xref + shared citations + timing delta + ite_nearest_dist | **HIGH** |
| **229 citation gap articles** | 88 AFP batch-downloadable from `null_clean_ref_missing_articles_20260326.csv` | **HIGH** |
| **Build designed scripts** | `article_citation_trend` table + `update_citation_trends.py` + `extract_ite_critique_refs.py` | **HIGH** |
| **Interactive vector dashboard** | HTML from vector explorer data (`data:interactive-dashboard-builder`) | **MEDIUM** |
| **Intelligence 2.0 Layer 2** | `article_currency` table via PubMed MCP | **MEDIUM** |
| `extract_ite_critique_refs.py` | BATON 014 design, not yet built | HIGH |
| `update_citation_trends.py` | BATON 014 design, not yet built | HIGH |
| `article_citation_trend` table | BATON 014 design, not yet created | HIGH |
| FLAG 33 | VC_pass ART-ID rename scheme — designed, not implemented | LOW |
| Cookie refresh | `aafp_cookies.json` — re-export before next scrape | MEDIUM |

---

## Next Steps (Ordered)

### 1. Article acquisition from PubMed queue
Open `aafp_pubmed_acquisition_queue_20260328.csv`. Each row has a PubMed URL. Download the PDF (or access via institutional access), add to `articles` table with proper codon filename (next ART-ID = ART-1938+), then re-run:
```powershell
python aafp_ref_match_v2.py  # Will now match the new articles
python compute_embeddings.py --new-only
python aafp_context_propagator.py
python aafp_vector_explorer.py --save --new-only
```

### 2. AAFP question reuse investigation
```sql
SELECT aq.aafp_qid, aq.ite_nearest_qid, aq.ite_nearest_dist,
       aq.stem, q.question_text
FROM aafp_questions aq
JOIN questions q ON aq.ite_nearest_qid = q.qid
WHERE aq.ite_nearest_dist < 0.30
ORDER BY aq.ite_nearest_dist;
```

### 3. AAFP-ITE lag analysis
For questions sharing article citations AND high vector similarity, compute timing delta.

### 4. 88 AFP gap articles
CSV ready: `00_database/readable_db_files/null_clean_ref_missing_articles_20260326.csv`

### 5. Interactive vector dashboard
Build HTML from `aafp_vector_explorer.py` output using `data:interactive-dashboard-builder` skill.

---

## AAFP Pipeline Quick Reference

**Run order for new AAFP data:**
```powershell
python aafp_brq_import.py --rebuild
python compute_embeddings.py --aafp-only
python aafp_keyword_extractor.py
python aafp_context_propagator.py
python aafp_vector_explorer.py --save
```

**After article acquisition (re-run matching):**
```powershell
python aafp_ref_match_v2.py --stats
python aafp_context_propagator.py
python aafp_vector_explorer.py --save --new-only
```

---

## Conventions Locked (additions this session)

- **pubmed_confirmed** = new match_status value in `aafp_citations` + `aafp_qid_art_xref` for PubMed-verified matches
- **aafp_pubmed_acquisition_queue_*.csv** = canonical acquisition target list for REMAINING bucket
- All prior conventions from BATON 017 unchanged
