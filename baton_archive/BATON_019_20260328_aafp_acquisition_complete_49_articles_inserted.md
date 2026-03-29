# BATON 019 — AAFP Acquisition Complete: 49 Articles Inserted, xref 815→864
**Date:** 2026-03-28
**Session platform:** Windows PC (Cowork VM)
**Status:** Active
**Preceding BATON:** `BATON_active_018_20260328_pubmed_sweep_complete_acquisition_queue_built.md` (→ archive)
**Git hash:** `4caa6f5` (unchanged — pending Windows commit)
**GitHub remote:** `https://github.com/mpsch01/project-overhaul` (private)

---

## SESSION SUMMARY — What Was Done and Why

Executed the AAFP article acquisition pipeline from BATON 018. Built `batch_insert_aafp_articles.py`, which:
1. Reads `aafp_pubmed_acquisition_queue_20260328.csv` (49 rows)
2. Fetches `aafp_citation_raw.raw_text` for each citation_id → uses as `clean_ref`
3. Assigns sequential ART-IDs (ART-1938 through ART-1986)
4. Builds codon filenames (`Author_Year#@#ART-XXXX@#@.pdf`), deduping Bonow 2008 → `Bonow_2008` + `Bonow_2008_b`
5. **Directly links** `aafp_citations` (match_status = 'aafp_acquisition') and inserts `aafp_qid_art_xref` rows — bypasses matcher for non-standard page formats (ITC, e-pages)
6. Runs `aafp_context_propagator.py` — propagates body_system/source_type/ICD-10 to newly linked questions

**Design note:** Using `raw_text` as `clean_ref` was the key decision. Since the raw_text IS the citation text the matcher would try to match against, this guarantees S2 vol/page matching would also work — we just short-circuited it for the non-standard formats (ITC page numbers, e-prefix pages, Cochrane without standard vol/page). Matcher `--stats` confirmed totals.

---

## 1. Articles Inserted

**49 new articles: ART-1938 through ART-1986**

| ART-ID Range | Count | Source Types |
|---|---|---|
| ART-1938–1986 | 49 | Cochrane(9), BMJ(7), Pediatrics(7), Other Journal(15), Annals(3), Guideline/Org(3), Circulation(3), NEJM(2) |

Key articles:
- Cochrane reviews: Walitt 2015, Venekamp 2016, Albalawi 2011, Herbert 2011, Yeung 2011, Keay 2012, Ma 2016, Binks 2006, Dennis 2008
- AAP CPGs: Lieberthal 2013 (AOM), Ralston 2014 (bronchiolitis), Wald 2013 (sinusitis), Mittal 2014, Byington 2012
- Cardiology guidelines: Bonow 2008 (x2), Amsterdam 2014
- IDSA: Nahid 2016 (tuberculosis)
- NEJM: Stewart 2011, Wilson JF 2014

Bonow 2008 dedup: `Bonow_2008` (Circulation, ART-1985) + `Bonow_2008_b` (JACC, ART-1986)

---

## 2. DB State After This Session

| Table | Before | After | Delta |
|-------|--------|-------|-------|
| articles | 1,936 | 1,985 | +49 |
| aafp_citations | 1,600 | 1,600 | 0 (match_status updated) |
| aafp_qid_art_xref | 815 | 864 | +49 |
| Unique AAFP questions linked | 598 (49.1%) | 643 (52.7%) | +45 |
| aafp_question_icd10 | 1,876 | 1,915 | +39 |
| aafp_questions.body_system | — | 594/1221 (48.6%) | populated |

**aafp_citations match_status breakdown (post-session):**
| Status | Count |
|--------|-------|
| matched (S0 exact) | 724 |
| unmatched | 717 |
| fuzzy (S1 vol/page+author) | 73 |
| aafp_acquisition | 49 |
| no_ref | 19 |
| s5_guideline | 7 |
| pubmed_confirmed | 6 |
| s4_cochrane_cd | 2 |
| s2_space_volpage | 2 |
| s3_afp_title | 1 |
| **Total** | **1,600** |

---

## 3. New Files This Session

| File | Location | Notes |
|------|----------|-------|
| `batch_insert_aafp_articles.py` | `02_module.2_processor/scripts/` | Acquisition insert script — dry-run + full mode |

---

## 4. Pending Steps After Article Acquisition

### Immediate (next session)

**Step 1 — Embeddings for new articles (run on Windows, needs OPENAI_API_KEY):**
```powershell
cd 00_#PROJECT_OVERHAUL
python 01_module.1_warehouse/scripts/build/compute_embeddings.py --new-only
```
*Cost: ~$0.006 for 49 articles. Runtime: ~5-10 seconds.*
*After this, run `aafp_vector_explorer.py --save --new-only` to update KNN/ite_nearest_dist.*

**Step 2 — PDF download (manual, institutional access):**
- Open `00_database/readable_db_files/aafp_pubmed_acquisition_queue_20260328.csv`
- Each row has a `pubmed_url` — download the PDF from your institution
- Rename each PDF to its codon filename (see ART-ID → codon map below)
- Place in `01_module.1_warehouse/VC_fail/` (all are VC_fail tier)
- After PDFs added: `python 01_module.1_warehouse/scripts/maintain/backfill_new_article_metadata.py --art-id-min 1938` → updates tier if any happen to be VC-cited

**Step 3 — After PDFs arrive, run extraction pipeline:**
```powershell
python 02_module.2_processor/main.py --new-only  (or manual batch)
node 02_module.2_processor/scripts/build_summary.js --new-only
```

### ART-ID → Codon filename map (for PDF renaming):

| ART-ID | Codon Filename |
|--------|----------------|
| ART-1938 | Henry_2015#@#ART-1938@#@.pdf |
| ART-1939 | Zawistowski_2003#@#ART-1939@#@.pdf |
| ART-1940 | Islam_2016#@#ART-1940@#@.pdf |
| ART-1941 | Bernard-Bonnin_2006#@#ART-1941@#@.pdf |
| ART-1942 | Walitt_2015#@#ART-1942@#@.pdf |
| ART-1943 | Ma_2016#@#ART-1943@#@.pdf |
| ART-1944 | Venekamp_2016#@#ART-1944@#@.pdf |
| ART-1945 | Albalawi_2011#@#ART-1945@#@.pdf |
| ART-1946 | Binks_2006#@#ART-1946@#@.pdf |
| ART-1947 | Herbert_2011#@#ART-1947@#@.pdf |
| ART-1948 | Yeung_2011#@#ART-1948@#@.pdf |
| ART-1949 | Keay_2012#@#ART-1949@#@.pdf |
| ART-1950 | Dennis_2008#@#ART-1950@#@.pdf |
| ART-1951 | Stewart_2011#@#ART-1951@#@.pdf |
| ART-1952 | Wilson_2014#@#ART-1952@#@.pdf |
| ART-1953 | McDonald_2011#@#ART-1953@#@.pdf |
| ART-1954 | Bocchetta_2006#@#ART-1954@#@.pdf |
| ART-1955 | Manske_2008#@#ART-1955@#@.pdf |
| ART-1956 | Pallan_2012#@#ART-1956@#@.pdf |
| ART-1957 | Nunes_2010#@#ART-1957@#@.pdf |
| ART-1958 | Schwartz_2009#@#ART-1958@#@.pdf |
| ART-1959 | Binic_2011#@#ART-1959@#@.pdf |
| ART-1960 | Al-Hussaini_2014#@#ART-1960@#@.pdf |
| ART-1961 | Foran_2012#@#ART-1961@#@.pdf |
| ART-1962 | Nishizaka_2003#@#ART-1962@#@.pdf |
| ART-1963 | Goundry_2012#@#ART-1963@#@.pdf |
| ART-1964 | Wilson_2011#@#ART-1964@#@.pdf |
| ART-1965 | Nahid_2016#@#ART-1965@#@.pdf |
| ART-1966 | Shonkoff_2011#@#ART-1966@#@.pdf |
| ART-1967 | Verbalis_2007#@#ART-1967@#@.pdf |
| ART-1968 | Parish_2009#@#ART-1968@#@.pdf |
| ART-1969 | Simon_2009#@#ART-1969@#@.pdf |
| ART-1970 | Myat_2012#@#ART-1970@#@.pdf |
| ART-1971 | Lieberthal_2013#@#ART-1971@#@.pdf |
| ART-1972 | Byington_2012#@#ART-1972@#@.pdf |
| ART-1973 | Pantell_2012#@#ART-1973@#@.pdf |
| ART-1974 | Kiire_2012#@#ART-1974@#@.pdf |
| ART-1975 | Khan_2010#@#ART-1975@#@.pdf |
| ART-1976 | Reddy_2010#@#ART-1976@#@.pdf |
| ART-1977 | Mittal_2014#@#ART-1977@#@.pdf |
| ART-1978 | Wald_2013#@#ART-1978@#@.pdf |
| ART-1979 | Amsterdam_2014#@#ART-1979@#@.pdf |
| ART-1980 | Mansour_2008#@#ART-1980@#@.pdf |
| ART-1981 | Grossman_2011#@#ART-1981@#@.pdf |
| ART-1982 | Stengel_2008#@#ART-1982@#@.pdf |
| ART-1983 | Ralston_2014#@#ART-1983@#@.pdf |
| ART-1984 | Moyer_2012#@#ART-1984@#@.pdf |
| ART-1985 | Bonow_2008#@#ART-1985@#@.pdf |
| ART-1986 | Bonow_2008_b#@#ART-1986@#@.pdf |

---

## 5. Remaining Deferred Flags

| Flag | Description | Priority |
|------|-------------|----------|
| **Embeddings (new-only)** | Run `compute_embeddings.py --new-only` then `aafp_vector_explorer.py --save --new-only` | **HIGH** |
| **PDF download** | Institutional access → download 49 PDFs from pubmed_url column in acquisition_queue CSV → rename to codon format → VC_fail/ | **HIGH** |
| **AAFP question reuse investigation** | Query WHERE ite_nearest_dist < 0.30; confirm exact dupes vs paraphrased | **HIGH** |
| **AAFP-ITE lag analysis** | xref + shared citations + timing delta + ite_nearest_dist; build predictive watch list | **HIGH** |
| **229 citation gap articles** | 88 AFP batch-downloadable from `null_clean_ref_missing_articles_20260326.csv` | **HIGH** |
| **Build designed scripts** | `article_citation_trend` table + `update_citation_trends.py` (M1/maintain/) + `extract_ite_critique_refs.py` (M2/scripts/) | **HIGH** |
| **Interactive vector dashboard** | HTML from vector explorer data (`data:interactive-dashboard-builder`) | **MEDIUM** |
| **Intelligence 2.0 Layer 2** | `article_currency` table via PubMed MCP | **MEDIUM** |
| `extract_ite_critique_refs.py` | BATON 014 design, not yet built | HIGH |
| `update_citation_trends.py` | BATON 014 design, not yet built | HIGH |
| `article_citation_trend` table | BATON 014 design, not yet created | HIGH |
| FLAG 33 | VC_pass ART-ID rename scheme — designed, not implemented | LOW |
| Cookie refresh | `aafp_cookies.json` — re-export before next scrape | MEDIUM |

---

## 6. Housekeeping Carried Forward

- [ ] **Windows:** Stage + commit pending git changes:
  1. From BATON 017: `aafp_ref_match_v2.py` + `classify_unmatched_citations.py`
  2. From BATON 018: `aafp_pubmed_acquisition_queue_20260328.csv` + DB changes
  3. **This session:** `batch_insert_aafp_articles.py` + BATON 019 + CLAUDE.md update
- [ ] **Windows:** Archive BATONs 013–018 → `baton_archive/`
- [ ] **Windows:** Clean up project root temp files: `parse_remaining.py`, `show_remaining.py`, `remaining_parsed.json`, `remaining_named.json`
- [ ] **Windows:** Delete sandbox originals per `04_module.4_sandbox/_DELETE_THESE_FROM_WINDOWS.txt`

**Suggested commit (this session):**
```
git add 02_module.2_processor/scripts/batch_insert_aafp_articles.py
git add BATON_active_019* CLAUDE.md
git commit -m "AAFP acquisition: 49 articles inserted (ART-1938-1986), xref 815->864, 643 questions linked (52.7%)"
```

---

## 7. Conventions Locked (additions this session)

- **aafp_acquisition** = new match_status value in `aafp_citations` + `aafp_qid_art_xref` for acquisition-inserted articles
- **batch_insert_aafp_articles.py** = canonical pattern for inserting new AAFP-sourced articles from a queue CSV; `raw_text` as `clean_ref` ensures matcher compatibility
- `clean_ref` for AAFP-sourced articles = `aafp_citation_raw.raw_text` (not reconstructed from PubMed metadata)
- Bonow 2008 dedup convention: `Bonow_2008` + `Bonow_2008_b` (same author/year, different journals)
- All prior conventions from BATON 018 unchanged

---

## Next Steps (Ordered)

1. **Mikey — Windows:** Run `compute_embeddings.py --new-only` (OpenAI key, ~$0.006, ~10 sec)
2. **Mikey — Windows:** Run `aafp_vector_explorer.py --save --new-only` (updates KNN distances)
3. **Next session:** AAFP question reuse investigation (query ite_nearest_dist < 0.30)
4. **Next session:** AAFP-ITE lag analysis
5. **Next session:** 88 AFP gap articles from `null_clean_ref_missing_articles_20260326.csv`
6. **When PDFs downloaded:** `backfill_new_article_metadata.py --art-id-min 1938` → tier update
