-- ============================================================
-- Migration 002: Vector Embedding Tables
-- Requires pgvector extension (enabled in 001_core_schema.sql)
-- All vectors are 1536-dimensional (OpenAI text-embedding-3-small)
-- ============================================================

-- ============================================================
-- article_icd10_vec — 1,757 rows
-- Embedding of each article's assigned ICD-10 code descriptions
-- ============================================================
CREATE TABLE IF NOT EXISTS article_icd10_vec (
    article_id  TEXT PRIMARY KEY REFERENCES articles(article_id),
    embedding   vector(1536)
);

CREATE INDEX IF NOT EXISTS idx_article_icd10_vec_embedding
    ON article_icd10_vec
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 50);

-- ============================================================
-- question_icd10_vec — 2,747 rows
-- Embedding of each question's (ITE + AAFP) assigned ICD-10 descriptions
-- ============================================================
CREATE TABLE IF NOT EXISTS question_icd10_vec (
    id          SERIAL PRIMARY KEY,
    qid         TEXT,        -- QID-YYYY-NNNN (ITE) or AAFP-NNNN (AAFP)
    source_bank TEXT,        -- 'ITE' | 'AAFP'
    embedding   vector(1536)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_question_icd10_vec_qid ON question_icd10_vec(qid);

CREATE INDEX IF NOT EXISTS idx_question_icd10_vec_embedding
    ON question_icd10_vec
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 75);

-- ============================================================
-- icd10_vec — 2,219 rows
-- Embedding of ICD-10 code descriptions (for condition-first lookup)
-- ============================================================
CREATE TABLE IF NOT EXISTS icd10_vec (
    icd10_code  TEXT PRIMARY KEY REFERENCES icd10_code_xref(icd10_code),
    embedding   vector(1536)
);

CREATE INDEX IF NOT EXISTS idx_icd10_vec_embedding
    ON icd10_vec
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 50);

-- ============================================================
-- Stored function: search questions by vector similarity
-- Used by the NL search API route
-- ============================================================
CREATE OR REPLACE FUNCTION search_questions_by_embedding(
    query_embedding vector(1536),
    source_bank_filter TEXT DEFAULT NULL,   -- 'ITE' | 'AAFP' | NULL (both)
    match_count INTEGER DEFAULT 15
)
RETURNS TABLE (
    qid         TEXT,
    source_bank TEXT,
    similarity  FLOAT
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        v.qid,
        v.source_bank,
        1 - (v.embedding <=> query_embedding) AS similarity
    FROM question_icd10_vec v
    WHERE (source_bank_filter IS NULL OR v.source_bank = source_bank_filter)
    ORDER BY v.embedding <=> query_embedding
    LIMIT match_count;
$$;

-- ============================================================
-- Stored function: search articles by vector similarity
-- ============================================================
CREATE OR REPLACE FUNCTION search_articles_by_embedding(
    query_embedding vector(1536),
    match_count INTEGER DEFAULT 10
)
RETURNS TABLE (
    article_id  TEXT,
    similarity  FLOAT
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        v.article_id,
        1 - (v.embedding <=> query_embedding) AS similarity
    FROM article_icd10_vec v
    ORDER BY v.embedding <=> query_embedding
    LIMIT match_count;
$$;
