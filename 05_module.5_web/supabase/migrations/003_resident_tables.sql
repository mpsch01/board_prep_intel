-- ============================================================
-- Migration 003: Resident & Auth Tables
-- New tables not in the SQLite DB — resident-specific data
-- ============================================================

-- ============================================================
-- user_profiles — one row per Supabase auth user
-- Links Supabase auth.users.id to application roles
-- ============================================================
CREATE TABLE IF NOT EXISTS user_profiles (
    id           UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    role         TEXT NOT NULL DEFAULT 'resident',  -- resident | faculty | admin
    display_name TEXT,
    abfm_id      TEXT,     -- ABFM candidate ID (residents only)
    program      TEXT,     -- residency program name
    cohort_year  INTEGER,  -- PGY graduation year (e.g. 2027)
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    updated_at   TIMESTAMPTZ DEFAULT NOW()
);

-- Trigger: keep updated_at current
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

CREATE TRIGGER user_profiles_updated_at
    BEFORE UPDATE ON user_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================================
-- resident_scores — item-level exam performance
-- One row per (resident, exam_year, item_number)
-- Populated by the Railway PDF parsing microservice
-- ============================================================
CREATE TABLE IF NOT EXISTS resident_scores (
    id               SERIAL PRIMARY KEY,
    resident_id      UUID NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
    exam_year        INTEGER NOT NULL,
    item_number      INTEGER NOT NULL,         -- 1-indexed item from the score report
    qid              TEXT REFERENCES questions(qid),  -- NULL if no QID match resolved
    answered_correct BOOLEAN NOT NULL,
    blueprint        TEXT,                     -- Acute Care | Chronic Care | Emergent/Urgent | Preventive | Foundations
    body_system      TEXT,
    uploaded_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (resident_id, exam_year, item_number)
);

CREATE INDEX IF NOT EXISTS idx_resident_scores_resident  ON resident_scores(resident_id);
CREATE INDEX IF NOT EXISTS idx_resident_scores_year      ON resident_scores(resident_id, exam_year);
CREATE INDEX IF NOT EXISTS idx_resident_scores_qid       ON resident_scores(qid);

-- ============================================================
-- score_uploads — audit log for each PDF upload
-- ============================================================
CREATE TABLE IF NOT EXISTS score_uploads (
    id             SERIAL PRIMARY KEY,
    resident_id    UUID NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
    exam_year      INTEGER NOT NULL,
    storage_path   TEXT NOT NULL,   -- Supabase Storage object path
    parse_status   TEXT NOT NULL DEFAULT 'pending',  -- pending | processing | complete | failed
    parse_error    TEXT,
    items_parsed   INTEGER,
    uploaded_at    TIMESTAMPTZ DEFAULT NOW(),
    completed_at   TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_score_uploads_resident ON score_uploads(resident_id);

-- ============================================================
-- assessment_sessions — tracks a resident taking a practice set
-- ============================================================
CREATE TABLE IF NOT EXISTS assessment_sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resident_id     UUID NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
    assignment_id   TEXT,             -- Sanity assessmentAssignment._id
    qids            JSONB NOT NULL,   -- ordered array of QIDs in this session
    responses       JSONB DEFAULT '{}',  -- {qid: {selected: "A", correct: true, answered_at: …}}
    status          TEXT DEFAULT 'active',   -- active | completed | abandoned
    started_at      TIMESTAMPTZ DEFAULT NOW(),
    completed_at    TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_assessment_sessions_resident ON assessment_sessions(resident_id);
CREATE INDEX IF NOT EXISTS idx_assessment_sessions_status   ON assessment_sessions(resident_id, status);

-- ============================================================
-- reading_completions — tracks prescribed reading progress
-- ============================================================
CREATE TABLE IF NOT EXISTS reading_completions (
    resident_id  UUID NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
    article_id   TEXT NOT NULL REFERENCES articles(article_id),
    session_id   TEXT NOT NULL DEFAULT '',  -- Sanity curriculumSession._id; '' = not session-specific
    completed_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (resident_id, article_id, session_id)
);

CREATE INDEX IF NOT EXISTS idx_reading_completions_resident ON reading_completions(resident_id);

-- ============================================================
-- question_sets — faculty-saved NL search results
-- ============================================================
CREATE TABLE IF NOT EXISTS question_sets (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    faculty_id   UUID NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
    name         TEXT NOT NULL,
    query        TEXT,          -- original NL query string
    qids         JSONB NOT NULL, -- ordered array of QIDs
    article_ids  JSONB,          -- matched article IDs
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    updated_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE TRIGGER question_sets_updated_at
    BEFORE UPDATE ON question_sets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE INDEX IF NOT EXISTS idx_question_sets_faculty ON question_sets(faculty_id);
