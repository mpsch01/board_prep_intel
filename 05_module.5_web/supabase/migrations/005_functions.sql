-- ============================================================
-- Migration 005: Utility Functions & Triggers
-- Cohort analytics helpers and auto-profile creation
-- ============================================================

-- ============================================================
-- Auto-create user_profile on new Supabase auth signup
-- Triggered by auth.users INSERT (via Supabase auth hook)
-- ============================================================
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    INSERT INTO user_profiles (id, role, display_name)
    VALUES (
        NEW.id,
        COALESCE(NEW.raw_user_meta_data->>'role', 'resident'),
        COALESCE(NEW.raw_user_meta_data->>'display_name', NEW.email)
    );
    RETURN NEW;
END;
$$;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION handle_new_user();

-- ============================================================
-- Function: cohort body-system summary for a given exam year
-- Used by faculty analytics and admin dashboard
-- ============================================================
CREATE OR REPLACE FUNCTION cohort_body_system_summary(target_year INTEGER)
RETURNS TABLE (
    body_system       TEXT,
    total_items       BIGINT,
    correct_items     BIGINT,
    pct_correct       NUMERIC,
    resident_count    BIGINT
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        rs.body_system,
        COUNT(*)                                               AS total_items,
        COUNT(*) FILTER (WHERE rs.answered_correct = TRUE)    AS correct_items,
        ROUND(
            100.0 * COUNT(*) FILTER (WHERE rs.answered_correct = TRUE)
            / NULLIF(COUNT(*), 0),
            1
        )                                                      AS pct_correct,
        COUNT(DISTINCT rs.resident_id)                         AS resident_count
    FROM resident_scores rs
    WHERE rs.exam_year = target_year
    GROUP BY rs.body_system
    ORDER BY pct_correct ASC;
$$;

-- ============================================================
-- Function: resident body-system summary for a given exam year
-- Used by resident analytics dashboard
-- ============================================================
CREATE OR REPLACE FUNCTION resident_body_system_summary(
    p_resident_id UUID,
    p_exam_year   INTEGER
)
RETURNS TABLE (
    body_system   TEXT,
    total_items   BIGINT,
    correct_items BIGINT,
    pct_correct   NUMERIC
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        rs.body_system,
        COUNT(*)                                              AS total_items,
        COUNT(*) FILTER (WHERE rs.answered_correct = TRUE)   AS correct_items,
        ROUND(
            100.0 * COUNT(*) FILTER (WHERE rs.answered_correct = TRUE)
            / NULLIF(COUNT(*), 0),
            1
        )                                                     AS pct_correct
    FROM resident_scores rs
    WHERE rs.resident_id = p_resident_id
      AND rs.exam_year   = p_exam_year
    GROUP BY rs.body_system
    ORDER BY pct_correct ASC;
$$;

-- ============================================================
-- Function: resident blueprint summary for a given exam year
-- ============================================================
CREATE OR REPLACE FUNCTION resident_blueprint_summary(
    p_resident_id UUID,
    p_exam_year   INTEGER
)
RETURNS TABLE (
    blueprint     TEXT,
    total_items   BIGINT,
    correct_items BIGINT,
    pct_correct   NUMERIC
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        rs.blueprint,
        COUNT(*)                                              AS total_items,
        COUNT(*) FILTER (WHERE rs.answered_correct = TRUE)   AS correct_items,
        ROUND(
            100.0 * COUNT(*) FILTER (WHERE rs.answered_correct = TRUE)
            / NULLIF(COUNT(*), 0),
            1
        )                                                     AS pct_correct
    FROM resident_scores rs
    WHERE rs.resident_id = p_resident_id
      AND rs.exam_year   = p_exam_year
    GROUP BY rs.blueprint
    ORDER BY pct_correct ASC;
$$;

-- ============================================================
-- Function: watch-list articles for a resident's missed questions
-- Returns articles with is_watch_list=TRUE linked to missed items
-- ============================================================
CREATE OR REPLACE FUNCTION resident_watchlist_articles(
    p_resident_id UUID,
    p_exam_year   INTEGER
)
RETURNS TABLE (
    article_id          TEXT,
    canonical_filename  TEXT,
    tier                TEXT,
    consecutive_streak  INTEGER,
    clean_ref           TEXT
)
LANGUAGE sql
STABLE
AS $$
    SELECT DISTINCT
        a.article_id,
        a.canonical_filename,
        a.tier,
        t.consecutive_streak,
        a.clean_ref
    FROM resident_scores rs
    JOIN qid_art_xref x ON x.qid = rs.qid
    JOIN articles a      ON a.article_id = x.article_id
    JOIN article_citation_trend t ON t.article_id = a.article_id
    WHERE rs.resident_id    = p_resident_id
      AND rs.exam_year      = p_exam_year
      AND rs.answered_correct = FALSE
      AND t.is_watch_list   = TRUE
      AND rs.qid IS NOT NULL
    ORDER BY t.consecutive_streak DESC;
$$;
