# REPO MAP — board_prep_intel

**Last Updated:** 2026-04-16 (BATON 061 — Git hash: bc462a3) — Stage 1.75 DB body system backfill; all 7 resident analyses complete; article_currency 1,998 complete

File tree with short descriptions. For full project context see `README.md`.

```
board_prep_intel/
│
├── README.md                          Project overview, DB state, conventions, next steps
├── REPO_MAP.md                        This file — directory tree with descriptions
├── CLAUDE.md                          Project memory: terminology, locked rules, active state
├── DATABASE_GUIDE.md                  DB contents, linkages, current uses, and future applications (moved from 00_database/)
├── _index.md                          Ground-truth file tree (may drift; sweep before structural changes)
├── BATON_active_061_*.md              Active session handoff — read first every session
├── .gitignore                         Excludes *.db, *.pdf, extracted_json/, resident_data/, outputs/
│
├── 00_database/                       Source of truth. Never disposable. (DATABASE_GUIDE.md moved to project root)
│   ├── db/
│   │   └── ite_intelligence.db        Production SQLite DB (gitignored — stays local/Drive)
│   ├── readable_db_files/             CSV exports and human-readable snapshots (gitignored)
│   ├── logs/                          Pipeline run logs
│   ├── crosswalk/
│   │   ├── crosswalk_index.json       Article crosswalk index
│   │   └── crosswalk_report.txt       Crosswalk audit report
│   └── schemas/
│       ├── clinical_synonym_map.json  Clinical term synonyms for ICD-10 matching
│       ├── icd10_mcp_lookup.json      ICD-10 MCP tool lookup table
│       └── ite-data-context-skill/    ITE domain skill for DB queries (SKILL.md + references/)
│
├── 01_module.1_warehouse/             M1 — PDF library + build/maintain DB scripts
│   ├── citation_files/
│   │   ├── ITE/
│   │   │   ├── VC_fail/               630 PDFs: failed VC gate; awaiting enrichment (gitignored)
│   │   │   ├── VC_pass/               168 PDFs: passed VC gate; awaiting enrichment (gitignored)
│   │   │   ├── local_lite/            117 PDFs: VC_fail + fully enriched (gitignored)
│   │   │   ├── right_click/           58 PDFs: VC_pass + fully enriched — priority tier (gitignored)
│   │   │   └── _dupe_archive/         14 duplicate PDFs quarantined (gitignored) — ite_total: 988
│   │   └── AAFP/                      15 PDFs: AAFP citation library (gitignored) — ite_total: 988 (VC_fail:630, VC_pass:168, local_lite:117, right_click:58)
│   ├── ite_exams/                     16 raw ITE exam PDFs: YYYY_MC.pdf + YYYY_critique.pdf (gitignored)
│   └── scripts/
│       ├── aafp_brq_scraper.py        AAFP BRQ scraper (Windows-only)
│       ├── build/                     6 scripts: full DB rebuild sequence
│       └── maintain/                  25 scripts: recurring DB population and maintenance
│
├── 02_module.2_processor/             M2 — Extraction, enrichment, DOCX build pipeline
│   ├── main.py                        Pipeline entry point
│   ├── requirements.txt               Python dependencies
│   ├── PIPELINE_README.md             Pipeline usage docs
│   ├── INTEGRATION_PROMPT.md          Integration context for AI-assisted runs
│   ├── core/                          ingestion.py, routing.py, screening.py
│   ├── engines/                       acute, chronic, diagnostic, preventive, rct engines + base
│   ├── utils/                         Shared utility modules
│   ├── scripts/                       75 py + 6 JS + 1 JSON config; all enrichment/build scripts; extract_ite_critique_refs.py MODIFIED (parse_legacy, fallback_citation_scan)
│   ├── source/
│   │   └── aafp_video_course_transcripts/   VTT transcripts for VC pipeline
│   ├── outputs/                       Staging JSONs + citation gap list (gitignored)
│   └── prompts/
│       └── candidates/                Prompt templates for enrichment
│
├── 03_module.3_analyst/               M3 — Score analysis, ICD-10, pathways, Q&A deliverables
│   ├── scripts/                       50 py + 2 JS + 6 JSON config; ite_parser, ite_analyzer_v3, build_article_currency, report builders, stage_1_75_db_backfill
│   ├── outputs/                       article_qc/ — citation QC audit results and rebuild statistics
│   ├── docs/                          ITE score analysis pipeline docs
│   └── reports/                       Per-resident DOCX reports + faculty PPTX (gitignored)
│
├── 04_module.4_sandbox/               M4 — Experiments and agent prototypes
│   ├── scripts/                       1 py (nl_search_validation.py — validates pgvector NL search pipeline)
│
├── 05_module.5_web/                   M5 — Interactive web platform (Next.js + Supabase + Sanity + Railway FastAPI)
│   ├── frontend/                      Next.js 15 app (Netlify deployment)
│   ├── supabase/                      PostgreSQL + pgvector migrations + sync scripts
│   ├── sanity/                        CMS schemas (curriculum content)
│   ├── api/                           Railway FastAPI (PDF score parser)
│   ├── scripts/                       3 py sync + 35 TypeScript/TSX + 5 SQL migrations
│
├── 05_module.5_web/                   M5 — Interactive web platform (slbfm.com)
│   ├── WEBSITE_BUILD_GUIDE.md         Step-by-step deployment guide for first-time setup
│   ├── README.md                      Architecture overview, setup order, env vars, data flows
│   ├── frontend/                      Next.js 15 app (TypeScript, App Router) → Netlify
│   │   ├── app/                       Page routes: login, resident/, faculty/, admin/, api/
│   │   ├── components/                AssessmentRunner, AnalyticsDashboard (Recharts)
│   │   ├── lib/                       supabase/, sanity/, search/ clients + NL search pipeline
│   │   ├── middleware.ts               Auth guard + role-based routing
│   │   └── netlify.toml               Netlify build config + edge function for auth
│   ├── sanity/                        Sanity Studio — curriculum CMS (sessions, readings, assignments)
│   │   └── schemas/                   residentCohort, curriculumSession, prescribedReading, etc.
│   ├── supabase/                      Cloud DB setup + data sync
│   │   ├── migrations/                001–005 SQL migrations (run in order, once)
│   │   └── sync/                      sqlite_to_supabase.py + vector_sync.py
│   └── api/                           FastAPI microservice → Railway (PDF score parser)
│       ├── main.py                    /health + /parse-score-report routes
│       ├── requirements.txt           fastapi, uvicorn, supabase, PyMuPDF, httpx
│       ├── Procfile / railway.json    Railway deploy config
│       └── parser/                    Copy ite_parser.py + ite_parser_config.json here before deploy
│
├── _archive_/                         Curated deliverables (not disposable)
│   ├── 01_curriculum/                 Curriculum definitions
│   ├── 02_question_bank/              Question bank exports
│   ├── 03_analysis/                   Analysis outputs
│   ├── 04_reference_data/             Reference data
│   └── 05_acquisition/                Acquisition lists
│
├── auto-memory-copies/                Auto-generated memory snapshots
│
├── baton_archive/                     All archived BATON session handoff documents
│   └── templates+guides/              BATON templates and writing guides
│
├── extracted_json/                    Middle-man layer (gitignored — regenerable)
│   ├── synthesis_library/             242 legacy pre-pipeline flat JSONs
│   ├── VC_pass_batch/                 Enriched JSONs for VC_pass tier
│   └── VC_fail_batch/                 Enriched JSONs for VC_fail tier
│
├── key_data_files/                    Critical reference data (protected)
│   ├── session_hy_inserts_v7.json     VC gate — 352 citations — sole right_click criterion
│   ├── FILE_NAMING_SPEC.md            Codon filename format spec
│   ├── ITE_Intelligence_2.0_Architecture.md   Intelligence 2.0 design doc
│   ├── data_exams/                    ITE_YYYY_raw.csv source files (2020–2025)
│   └── [supporting CSVs + JSONs]      Body system map, keyword library, poll inserts, etc.
│
├── article-citation-qc.skill          Installable skill — QC audit of articles table against ITE critique PDFs (2018–2025)
│
└── skills_abilities/                  Agent skills, SDK references, Apify actor
    ├── agents/                        PDF sourcer agent + docs/logs
    ├── apify-actors/
    │   └── citation_crawler/          Deployed Apify actor (build 0.3.1, Playwrigh