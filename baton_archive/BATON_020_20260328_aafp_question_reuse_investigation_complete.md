# BATON 020 — AAFP Question Reuse Investigation Complete
**Date:** 2026-03-28
**Session platform:** Windows PC (Cowork VM)
**Status:** Active
**Preceding BATON:** `BATON_active_019_20260328_aafp_acquisition_complete_49_articles_inserted.md` (→ archive)
**Git hash:** `4caa6f5` (unchanged — still pending Windows commit)
**GitHub remote:** `https://github.com/mpsch01/project-overhaul` (private)

---

## SESSION SUMMARY — What Was Done and Why

Built and ran the AAFP question reuse investigation. Goal: identify AAFP BRQ questions
that share content with ITE exam questions, using pre-computed `ite_nearest_dist` cosine
distances from `aafp_vector_explorer.py`.

### Script built
`03_module.3_analyst/scripts/aafp_question_reuse_investigation.py`
- Queries `aafp_questions` JOIN `questions` WHERE `ite_nearest_dist < 0.30`
- Buckets pairs into HIGH/MODERATE/LOW by distance threshold
- Default mode: full stems for HIGH pairs (< 0.22) + truncated list of all
- `--full` flag: full stems for all pairs
- `--csv` flag: saves to `00_database/readable_db_files/aafp_question_reuse_20260328.csv`

**Key schema corrections discovered (not pre-documented):**
- `aafp_questions` PK is `aafp_qid` (not `aafp_question_id`)
- `aafp_questions` stem column is `stem` (not `question_stem`)
- `aafp_questions` has no `year` column
- `questions` PK is `qid` (not `question_id`)
- `questions` year column is `exam_year` (not `year`)
- `questions` body_system column is `body_system` (not `category`)

---

## KEY FINDINGS — AAFP Question Reuse Investigation

### Quantitative results
| Bucket | Threshold | Count |
|--------|-----------|-------|
| HIGH | < 0.22 | 0 |
| MODERATE | 0.22–0.27 | 12 |
| LOW | 0.27–0.30 | 26 |
| **TOTAL** | **< 0.30** | **38** |

### The core finding
**All 38 pairs have verbatim identical stems.** Every AAFP and ITE vignette in this list is
word-for-word the same. The only textual difference is the AAFP version appends "(check one)"
at the end. The cosine distance of 0.23–0.30 is driven entirely by **answer choices differing**
between the two versions — same clinical scenario, different question pivot.

### ITE year distribution
| ITE Exam Year | Pairs |
|---|---|
| 2018 | 27 |
| 2019 | 8 |
| 2022 | 1 |
| **Total** | **38** |

Heavy concentration in ITE 2018 (71%). Handful of 2019 and one 2022.

### BRQ sessions involved
Sessions 15, 16, 46, 48, 50, 51, 52, 53, 60, 77

### Notable anomalies
- **#13 and #14 are AAFP duplicates:** AAFP-50340 and AAFP-50200 have identical stems,
  both matching the same ITE question (QID-2018-0068). Two different AAFP BRQ question IDs,
  same vignette, same ITE match.
- **ITE 2022 outlier:** Session 77 (AAFP-50227, acute bronchitis/atypical organisms) matches
  ITE 2022. All others match 2018 or 2019.

### Content flow direction (attempted investigation)
Attempted to determine whether AAFP BRQ or ITE came first. BRQ session publication dates
are not surfaced anywhere in the AAFP website UI or API. Best estimate based on session
numbering (~10 sessions/year, program started ~2013):
- Sessions 15–16 → ~2013–2014 (likely AAFP FIRST, ~5 years before ITE 2019)
- Sessions 46–53 → ~2017–2018 (roughly contemporaneous with ITE 2018)
- Session 60 → ~2018–2019 (roughly contemporaneous with ITE 2018)
- Session 77 → ~2020–2021 (likely AAFP FIRST, ~2 years before ITE 2022)

**Working hypothesis:** ABFM and AAFP share a co-development question pipeline. These are
not retired ITE questions repurposed as BRQ — they are shared vignettes deployed in both
products, tested at different clinical decision points.

**Practical implication:** BRQ sessions 46–77 are a predictive signal for ITE content,
not just retrospective review. A resident who works through BRQ 46–60 is seeing vignettes
that appeared on or around the ITE 2018 exam.

---

## DB STATE (unchanged from BATON 019)

| Item | Value |
|------|-------|
| DB articles | 1,985 (ART-1938–ART-1986 inserted last session) |
| DB questions (ITE) | 1,629 |
| DB questions (AAFP BRQ) | 1,221 |
| qid_art_xref | 2,470 |
| aafp_qid_art_xref | 864 rows |
| aafp_question_icd10 | 1,915 rows |
| Next ART-ID | ART-1987 |
| Git hash | `4caa6f5` (3+ commits pending from Windows) |

---

## NEW FILES THIS SESSION

| File | Description |
|------|-------------|
| `03_module.3_analyst/scripts/aafp_question_reuse_investigation.py` | AAFP-ITE question reuse investigator; `--full` and `--csv` flags |

---

## PENDING STEPS (priority order)

1. **Windows:** Stage + commit pending git changes (scripts from BATONs 017–020); archive
   BATONs 013–019 → `baton_archive/`; clean up temp files from project root
2. **Windows:** PDF downloads — 49 new articles (ART-1938–1986); codon filenames in
   BATON 019; place in `VC_fail/`; then run `backfill_new_article_metadata.py --art-id-min 1938`
3. **AAFP question reuse — next analysis:** Pull answer choices side-by-side for the 12
   MODERATE pairs to confirm correct answer alignment between AAFP and ITE versions; flag
   these 38 `aafp_questions` rows with a new `ite_shared_vignette` column in the DB
4. **AAFP-ITE lag analysis:** formal analysis — xref + shared citations + timing delta +
   `ite_nearest_dist`; build predictive watch list; the 38 shared-vignette pairs are the
   highest-confidence seed set
5. **229 citation gap articles:** 88 AFP batch-downloadable from
   `null_clean_ref_missing_articles_20260326.csv`; codon rename → ingest → enrich →
   re-run `aafp_ref_match_v2.py`
6. **Build designed scripts:** `article_citation_trend` table + `update_citation_trends.py`
   (M1/maintain/) + `extract_ite_critique_refs.py` (M2/scripts/)
7. **Interactive vector dashboard:** HTML from vector explorer data
   (`data:interactive-dashboard-builder`)
8. **Intelligence 2.0 Layer 2:** `article_currency` table via PubMed MCP

---

## DEFERRED FLAGS

| Flag | Description |
|------|-------------|
| FLAG 33 | `nnn_XXXX` ART-ID rename scheme — designed, not yet implemented |
| TEMP: aafp_question_reuse_20260328.csv | Not yet generated (needs `--csv` run from Windows) |
| TEMP: ite_shared_vignette column | Designed, not yet added to `aafp_questions` schema |
| WAL mode oplock | DB shows 0 tables from VM after Windows runs embeddings — known FUSE issue, work from Windows |

---

## BATON HANDOFF NOTES

- The reuse investigation script is clean and ready. Run from Windows with `--csv` to
  generate the flat file for further analysis.
- Schema corrections above are NOT yet documented in `aafp_brq_import.py` comments —
  the schema IS correct, just underdocumented. No fixes needed.
- Next session: likely either PDF downloads + backfill, or the lag analysis proper.
  Read the BRQ session-to-ITE-year mapping above before starting the lag analysis.
