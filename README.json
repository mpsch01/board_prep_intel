{
  "project_name": "ABFM ITE Intelligence System",
  "description": "Family medicine board exam knowledge base: queryable question bank (1,629 ITE questions, 2018-2025; 1,221 AAFP BRQ questions) linked to a clinical guideline library (1,985 articles, 404 PDFs) via a structured SQLite pipeline. Both ITE and AAFP corpora are schema-parallel with full enrichment (body_system, concept_tags, subcategory, ICD-10). Extends beyond exam prep into clinical decision support.",
  "location": "C:\\Users\\mpsch\\Desktop\\claude_knowledge\\00_#PROJECT_OVERHAUL\\",
  "last_updated": "2026-04-02 (BATON 032)",
  "architecture": "4-module rebuild (PROJECT_OVERHAUL)",
  "active_baton": "BATON_active_032_20260402_question_dist_fix_faculty_pptx.md",
  "git_status": "main branch. Latest committed: 279049a. 8 files unstaged (see BATON 032).",
  "database": {
    "path": "00_database/db/ite_intelligence.db",
    "articles": 1985,
    "questions_ite": 1629,
    "questions_aafp_brq": 1221,
    "question_ref_pairs": 2722,
    "qid_art_xref": 2470,
    "article_icd10": 4137,
    "question_icd10": 5284,
    "aafp_question_icd10": 4753,
    "pubmed_pmid_cache": 344,
    "clinical_pathways": 4020,
    "icd10_rollup": 614,
    "icd10_code_xref": 1006,
    "icd10_vec": 2219,
    "article_icd10_vec": 1674,
    "question_icd10_vec": 2733,
    "article_vec": 1936,
    "question_vec": 1629,
    "aafp_questions": 1221,
    "aafp_explanations": 1221,
    "aafp_citations": 1600,
    "aafp_citation_raw": 1600,
    "aafp_qid_art_xref": 864,
    "aafp_question_vec": 1221,
    "art_id_range": "ART-0001 through ART-1986 (ART-0404 deleted/merged; +49 AAFP acquisition 2026-03-28)",
    "next_art_id": "ART-1987"
  },
  "aafp_questions_column_coverage": {
    "body_system": "100% (1221/1221) — 3-tier classifier",
    "body_system_method": "100% — audit trail",
    "stem_keywords": "100%",
    "all_keywords": "100%",
    "source_type": "100%",
    "ite_nearest_qid": "100%",
    "ite_nearest_dist": "100%",
    "concept_tags": "100% (1221/1221) — Haiku 4.5 API, complete 2026-03-29",
    "subcategory": "100% (1221/1221) — Haiku 4.5 API, complete 2026-03-29"
  },
  "ite_questions_column_coverage": {
    "body_system_merged": "100%",
    "stem_keywords": "100%",
    "all_keywords": "100%",
    "concept_tags": "100%",
    "subcategory": "100%",
    "blueprint": "~33% (pre-existing debt)"
  },
  "module_structure": {
    "00_database": "Source of truth (DB + supporting data, schemas, logs)",
    "01_module.1_warehouse": "PDF library (4 tiers, 404 PDFs) + M1 scripts (build/9, maintain/16) + aafp_brq/scraper+staging",
    "02_module.2_processor": "Extraction + enrichment pipeline (53 Python + 6 JS + 1 JSON + 4 Windows, all paths dynamic)",
    "03_module.3_analyst": "Analysis scripts (9 Python + 2 JS + 2 JSON config)",
    "04_module.4_sandbox": "Experiments placeholder (cleanup pending)"
  },
  "supporting_folders": {
    "archive_canonical": "Curated deliverables (curriculum, question bank, analysis, reference data, acquisition lists)",
    "baton_archive": "Session handoff history (archived BATONs)",
    "extracted_json": "Three subfolders: synthesis_library/ (242 legacy flat JSONs), VC_pass_batch/ (95), VC_fail_batch/ (147). Root clean (manifest.json only).",
    "key_data_files": "Critical reference data: VC gate (session_hy_inserts_v7.json), exam CSVs, missing articles list, FILE_NAMING_SPEC, Intelligence 2.0 architecture, project inventory, script library"
  },
  "pdf_library": {
    "total": 404,
    "VC_fail": "146 PDFs (codon-named, awaiting full pipeline — not VC-cited)",
    "local_lite": "117 PDFs (enriched, not VC-cited — pipeline complete)",
    "VC_pass": "94 PDFs (codon-named, awaiting full pipeline — VC-cited)",
    "right_click": "71 PDFs (VC-cited, fully enriched — pipeline complete)",
    "pending": "49 PDFs for ART-1938–ART-1986 — download_aafp_acquisitions.py ready to run"
  },
  "codon_convention": "Author_Year#@#ART-XXXX@#@.pdf — ART-ID embedded between #@# start and @#@ stop codon. Strategy 0 = regex parse of codon. Primary match strategy in all enrichers.",
  "vc_gate": "key_data_files/session_hy_inserts_v7.json (352 citations — sole criterion for right_click vs local_lite tier assignment)",
  "intelligence_layers": {
    "layer_1_icd10": "COMPLETE — article_icd10 (4,137 rows) + question_icd10 (5,284 rows ITE) + aafp_question_icd10 (4,753 rows). Full symmetry both banks. 2026-03-31.",
    "layer_2_pubmed": "SEEDED — pubmed_pmid_cache (344 PMIDs). article_currency table not yet built.",
    "layer_3_pathways": "COMPLETE — 4,020 rows. blueprint-based routing, both banks (ITE + AAFP), full ART range ART-0002–ART-1985. Rebuilt 2026-03-31. Script: build_clinical_pathways_v2.py.",
    "layer_4a_trends": "COMPLETE — body_system/subcategory/concept_tag trend CSVs",
    "layer_4b_alerts": "NOT STARTED — pubmed_alerts table"
  },
  "designed_not_yet_built": {
    "article_citation_trend": "Companion table: years_cited, distinct_year_count, first_cited_year, most_recent_year, consecutive_streak, is_watch_list. Derived from qid_art_xref via pure SQL.",
    "extract_ite_critique_refs.py": "M2/scripts/ — local PDF-native critique ref extractor. pdfplumber, dispatcher architecture, zero API cost. Replaces DOCX dependency for future year integration."
  },
  "built_not_yet_run": {
    "update_citation_trends.py": "M1/maintain/ — populates article_citation_trend. Pure SQL, no API. ~200 lines. Ready to run.",
    "download_aafp_acquisitions.py": "M1/maintain/ — downloads 49 PMC PDFs for ART-1938–1986; codon filenames; places in VC_fail/. Ready to run."
  },
  "script_path_convention": {
    "python": "SCRIPT_DIR = Path(__file__).resolve().parent; PROJECT_ROOT = SCRIPT_DIR.parent.parent",
    "javascript": "path.resolve(__dirname, '../../') = PROJECT_ROOT",
    "no_hardcoded_paths": "All paths dynamic — no C:\\Users\\... anywhere in scripts",
    "no_de_novo_js": "New code = Python only. Existing JS scripts migrate fine."
  },
  "key_conventions": {
    "source_data_protected": "DB + PDFs + VC gate survive everything. Derivatives (JSONs, DOCXs, CSVs) are disposable.",
    "schema_first": "Define SQL schema before writing build script",
    "fix_data_not_code": "Upstream data cleanup preferred over defensive code complexity",
    "strategy_0_first": "Codon parse always the first matching strategy in every enricher",
    "baton_supersedes_all": "Active BATON is the source of truth for current state"
  },
  "aafp_brq": {
    "description": "AAFP Board Review Questions: 135 quizzes x 10 questions. Separate table schema from ITE questions. Now schema-parallel to ITE (body_system, concept_tags, subcategory, ICD-10 all at 100%).",
    "scraper": "01_module.1_warehouse/aafp_brq/scraper/aafp_brq_scraper.py (Windows-only — VM proxy blocks HTTPS)",
    "staging": "01_module.1_warehouse/aafp_brq/staging/aafp_brq_staging.json (1,221 records, 4MB)",
    "import": "02_module.2_processor/scripts/aafp_brq_import.py",
    "pipeline_order": "aafp_brq_import.py → compute_embeddings.py --aafp-only → aafp_keyword_extractor.py → aafp_merge_keywords.py → aafp_context_propagator.py → aafp_assign_body_system.py → aafp_vector_explorer.py --save → aafp_enrich_concept_tags.py --mode linked → aafp_enrich_concept_tags.py --mode unlinked",
    "key_finding": "Near-identical AAFP-ITE pairs at dist<0.27 confirm likely direct question reuse. 38 shared-vignette pairs identified (BATON 020). Linked vs unlinked mean dist gap: 0.4497 vs 0.6973.",
    "model_selection": "Haiku 4.5 selected for concept_tags enrichment — ~3x cost savings vs Sonnet 4.6 at near-identical quality (BATON 022 comparison study)"
  },
  "deferred_flags": {
    "HIGH": [
      "GIT-PENDING — 8 scripts from BATON 029-031 still unstaged: ite_analyze_v2.py, ite_analyzer_v2.py, ite_report_builder_v2.js, export_aafp_ite_relationships.py, word_doc_defaults.py, build_aafp_qa.py, build_aafp_qa_file1.py, build_faculty_pptx.js",
      "49 PDF download — download_aafp_acquisitions.py ready to run; then backfill_new_article_metadata.py --art-id-min 1938"
    ],
    "MEDIUM": [
      "Intelligence 2.0 Layer 2 — article_currency table; 344 PMIDs already in pubmed_pmid_cache (seed ready)",
      "Run update_citation_trends.py — M1/maintain/, ready to run after PDF download",
      "AAFP vs ITE trend comparison — both corpora schema-parallel; body_system + concept_tags + ICD-10 side-by-side",
      "Interactive vector dashboard — HTML from aafp_vector_explorer data",
      "Fill question vector gaps — 440 ITE (2018–2019) + 1,221 AAFP → question_vec"
    ],
    "LOW": [
      "FLAG 33 — VC_pass ART-ID rename scheme: designed, not implemented",
      "Right_click DOCX regeneration — 71 DOCXs regenerable via build_summary.js",
      "ite_shared_vignette column — designed for aafp_questions, deprioritized (38 pairs insufficient signal)"
    ]
  }
}
