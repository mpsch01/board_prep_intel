---
name: reference_vc_gate
description: VC Gate source of truth location and structure — session_hy_inserts_v7.json determines $right_click$ vs local_lite tier
type: reference
---

## VC Gate Source of Truth
File: `abfm_prep/04_aafp_integration/02_working/session_hy_inserts_v7.json`
Windows: `C:\Users\mpsch\Desktop\claude_knowledge\abfm_prep\04_aafp_integration\02_working\session_hy_inserts_v7.json`

Structure: 48 sessions keyed by session_id ("02"–"48")
- `questions[]`: 5 QIDs per session (229 total)
- `refs[]`: citation strings with tier, match_score, cited_by QID list

Key counts:
- 352 unique citation strings
- 325 matched to DB articles via clean_ref
- 27 unmatched (FLAG 34)

**IMPORTANT:** QID format mismatch — VC JSON uses `Q{YEAR}-{NUM}` (full exam bank numbering, numbers can exceed 800/year). DB uses `QID-{YEAR}-{NUM:04d}` (curated subset, ~200/year). Only 75/229 resolve via normalization. Use citation strings for matching, NOT QIDs.

## MASTER_MAP.html
Location: `abfm_prep/PIPELINE_MAP.html` (later versioned as `MASTER_MAP.html`)
7 modules: ⓪ ITE Question Bank, Ⓕ VC Outline, Ⓐ PDF Acquisition, Ⓑ Match/Route/Rename, Ⓒ Extraction→Enrichment→DOCX, Ⓓ Intelligence Layers, Ⓔ ITE Score Analysis

## Pipeline Scripts (Module C — $right_click$ path)
```
01_guideline_extractor/
  main.py → synthesize.js → ite_intelligence_enricher.py → build_crosswalk_index.py → build_summary.js
```
Orchestrated by `extract_guideline.bat` (Windows right-click context menu)

Three extraction strategies:
1. Single-file CLI: main.py (standard, one API call)
2. Bulk async: batch_db_extract.py (Batch API, 50% cheaper)
3. DB-guided: db_guided_extractor.py ("flashlight" — DB clues guide focused Claude call)
