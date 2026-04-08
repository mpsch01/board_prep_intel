-- ============================================================
-- Migration 001: Core Content Tables
-- Mirrors the SQLite schema from ite_intelligence.db
-- Run in order: 001 → 002 → 003 → 004 → 005
-- ============================================================

-- Enable pgvector extension (run once per project)
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- articles — 1,985 rows
-- ============================================================
CREATE TABLE IF NOT EXISTS articles (
    clean_ref              TEXT PRIMARY KEY,
    article_id             TEXT UNIQUE NOT NULL,
    author1                TEXT,
    author2                TEXT,
    year                   TEXT,
    canonical_filename     TEXT,
    codon_filename         TEXT,
    tier                   TEXT,          -- VC_fail | VC_pass | local_lite | right_click
    source_type            TEXT,          -- afp | guideline | uspstf | rct | review | stub | …
    engine_type            TEXT,          -- acute_protocol | chronic_guideline | preventive_guideline | diagnostic_guideline | rct
    citation_count         INTEGER DEFAULT 0,
    unique_years           INTEGER DEFAULT 0,
    exam_years             JSONB,         -- e.g. [2021, 2022, 2024]
    blueprint              TEXT,          -- Acute | Chronic | Emergent | Preventive | Foundations
    body_system            TEXT,
    concept_tags           JSONB          -- {diagnoses, drugs, procedures, concept_summary}
);

CREATE INDEX IF NOT EXISTS idx_articles_article_id    ON articles(article_id);
CREATE INDEX IF NOT EXISTS idx_articles_tier          ON articles(tier);
CREATE INDEX IF NOT EXISTS idx_articles_blueprint     ON articles(blueprint);
CREATE INDEX IF NOT EXISTS idx_articles_body_system   ON articles(body_system);
CREATE INDEX IF NOT EXISTS idx_articles_source_type   ON articles(source_type);

-- ============================================================
-- questions (ITE) — 1,629 rows
-- ============================================================
CREATE TABLE IF NOT EXISTS questions (
    qid                    TEXT PRIMARY KEY,  -- QID-YYYY-NNNN
    exam_year              INTEGER,
    question_text          TEXT,
    choices                JSONB,
    correct_answer         TEXT,
    explanation            TEXT,
    body_system            TEXT,
    body_system_merged     TEXT,              -- use this for trend queries
    blueprint              TEXT,
    concept_tags           JSONB
);

CREATE INDEX IF NOT EXISTS idx_questions_exam_year         ON questions(exam_year);
CREATE INDEX IF NOT EXISTS idx_questions_blueprint         ON questions(blueprint);
CREATE INDEX IF NOT EXISTS idx_questions_body_system       ON questions(body_system_merged);

-- ============================================================
-- aafp_questions — 1,221 rows
-- ============================================================
CREATE TABLE IF NOT EXISTS aafp_questions (
    aafp_qid               TEXT PRIMARY KEY,  -- AAFP-NNNN
    stem                   TEXT,
    choices                JSONB,
    correct_letter         TEXT,
    correct_text           TEXT,
    explanation            TEXT,
    body_system            TEXT,
    blueprint              TEXT,
    concept_tags           JSONB,
    ite_nearest_qid        TEXT
);

CREATE INDEX IF NOT EXISTS idx_aafp_questions_blueprint    ON aafp_questions(blueprint);
CREATE INDEX IF NOT EXISTS idx_aafp_questions_body_system  ON aafp_questions(body_system);

-- ============================================================
-- qid_art_xref — 2,470 rows  (ITE questions ↔ articles)
-- ============================================================
CREATE TABLE IF NOT EXISTS qid_art_xref (
    qid        TEXT NOT NULL REFERENCES questions(qid),
    article_id TEXT NOT NULL REFERENCES articles(article_id),
    PRIMARY KEY (qid, article_id)
);

CREATE INDEX IF NOT EXISTS idx_qid_art_xref_article_id ON qid_art_xref(article_id);
CREATE INDEX IF NOT EXISTS idx_qid_art_xref_qid        ON qid_art_xref(qid);

-- ============================================================
-- aafp_qid_art_xref — 864 rows  (AAFP questions ↔ articles)
-- ============================================================
CREATE TABLE IF NOT EXISTS aafp_qid_art_xref (
    aafp_qid   TEXT NOT NULL REFERENCES aafp_questions(aafp_qid),
    article_id TEXT NOT NULL REFERENCES articles(article_id),
    PRIMARY KEY (aafp_qid, article_id)
);

CREATE INDEX IF NOT EXISTS idx_aafp_qid_art_xref_article_id ON aafp_qid_art_xref(article_id);

-- ============================================================
-- ICD-10 taxonomy
-- ============================================================
CREATE TABLE IF NOT EXISTS icd10_rollup (
    parent_code   TEXT PRIMARY KEY,
    parent_desc   TEXT,
    chapter       TEXT,
    chapter_desc  TEXT
);

CREATE TABLE IF NOT EXISTS icd10_code_xref (
    icd10_code   TEXT PRIMARY KEY,
    icd10_desc   TEXT,
    parent_code  TEXT REFERENCES icd10_rollup(parent_code)
);

CREATE INDEX IF NOT EXISTS idx_icd10_code_xref_parent ON icd10_code_xref(parent_code);

-- ============================================================
-- ICD-10 diagnostic layer
-- ============================================================
CREATE TABLE IF NOT EXISTS article_icd10 (
    article_id  TEXT NOT NULL REFERENCES articles(article_id),
    icd10_code  TEXT NOT NULL REFERENCES icd10_code_xref(icd10_code),
    relevance   REAL,
    PRIMARY KEY (article_id, icd10_code)
);

CREATE INDEX IF NOT EXISTS idx_article_icd10_code ON article_icd10(icd10_code);

CREATE TABLE IF NOT EXISTS question_icd10 (
    qid        TEXT NOT NULL REFERENCES questions(qid),
    icd10_code TEXT NOT NULL REFERENCES icd10_code_xref(icd10_code),
    relevance  REAL,
    PRIMARY KEY (qid, icd10_code)
);

CREATE INDEX IF NOT EXISTS idx_question_icd10_code ON question_icd10(icd10_code);

CREATE TABLE IF NOT EXISTS aafp_question_icd10 (
    aafp_qid   TEXT NOT NULL REFERENCES aafp_questions(aafp_qid),
    icd10_code TEXT NOT NULL REFERENCES icd10_code_xref(icd10_code),
    relevance  REAL,
    PRIMARY KEY (aafp_qid, icd10_code)
);

-- ============================================================
-- Clinical intelligence layer
-- ============================================================
CREATE TABLE IF NOT EXISTS clinical_pathways (
    article_id   TEXT NOT NULL REFERENCES articles(article_id),
    icd10_code   TEXT NOT NULL REFERENCES icd10_code_xref(icd10_code),
    pathway_role TEXT,   -- screening | diagnosis | first_line_treatment | monitoring | …
    source_bank  TEXT,   -- ITE | AAFP | both
    PRIMARY KEY (article_id, icd10_code)
);

CREATE INDEX IF NOT EXISTS idx_clinical_pathways_icd10 ON clinical_pathways(icd10_code);
CREATE INDEX IF NOT EXISTS idx_clinical_pathways_role  ON clinical_pathways(pathway_role);

CREATE TABLE IF NOT EXISTS article_citation_trend (
    article_id            TEXT PRIMARY KEY REFERENCES articles(article_id),
    years_cited           TEXT,              -- comma-separated exam years
    distinct_year_count   INTEGER DEFAULT 0,
    first_cited_year      INTEGER,
    most_recent_year      INTEGER,
    consecutive_streak    INTEGER DEFAULT 0,
    is_watch_list         BOOLEAN DEFAULT FALSE  -- consecutive_streak >= 2
);

-- ============================================================
-- article_currency (Intelligence 2.0 Layer 2)
-- ============================================================
CREATE TABLE IF NOT EXISTS article_currency (
    article_id          TEXT PRIMARY KEY REFERENCES articles(article_id),
    pubmed_id           TEXT,
    pub_date            TEXT,
    pub_title           TEXT,
    last_checked        TEXT,
    newer_version_pmid  TEXT,
    newer_version_date  TEXT,
    newer_version_title TEXT,
    currency_status     TEXT,  -- current | updated | check_needed | not_indexed
    title_signals       JSONB  -- clinical category words for blueprint cross-reference
);

CREATE INDEX IF NOT EXISTS idx_article_currency_status ON article_currency(currency_status);
