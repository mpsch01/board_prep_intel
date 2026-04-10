-- ============================================================
-- Migration 004: Row Level Security (RLS) Policies
-- Enforces data isolation between residents, faculty, and admins
-- Run AFTER 001, 002, 003
-- ============================================================

-- Enable RLS on all resident-sensitive tables
ALTER TABLE user_profiles         ENABLE ROW LEVEL SECURITY;
ALTER TABLE resident_scores       ENABLE ROW LEVEL SECURITY;
ALTER TABLE score_uploads         ENABLE ROW LEVEL SECURITY;
ALTER TABLE assessment_sessions   ENABLE ROW LEVEL SECURITY;
ALTER TABLE reading_completions   ENABLE ROW LEVEL SECURITY;
ALTER TABLE question_sets         ENABLE ROW LEVEL SECURITY;

-- Helper: get the role of the authenticated user
-- SET search_path prevents object-shadowing attacks on SECURITY DEFINER functions.
CREATE OR REPLACE FUNCTION auth_role()
RETURNS TEXT
LANGUAGE sql
STABLE SECURITY DEFINER
SET search_path = public
AS $$
    SELECT role FROM user_profiles WHERE id = auth.uid();
$$;

-- ============================================================
-- user_profiles policies
-- ============================================================
-- Users can read their own profile
CREATE POLICY "users_read_own_profile"
    ON user_profiles FOR SELECT
    USING (id = auth.uid());

-- Users can update their own profile (non-role fields only).
-- WITH CHECK prevents a resident from escalating their own role.
CREATE POLICY "users_update_own_profile"
    ON user_profiles FOR UPDATE
    USING (id = auth.uid())
    WITH CHECK (
        id = auth.uid()
        AND role = (SELECT role FROM user_profiles WHERE id = auth.uid())
    );

-- Admins can read all profiles
CREATE POLICY "admins_read_all_profiles"
    ON user_profiles FOR SELECT
    USING (auth_role() = 'admin');

-- Admins can update any profile (for role changes)
CREATE POLICY "admins_update_all_profiles"
    ON user_profiles FOR UPDATE
    USING (auth_role() = 'admin');

-- ============================================================
-- resident_scores policies
-- ============================================================
-- Residents can only read their own scores
CREATE POLICY "residents_read_own_scores"
    ON resident_scores FOR SELECT
    USING (resident_id = auth.uid());

-- The Railway API service uses a service_role key — bypasses RLS
-- No INSERT policy needed for anon/authenticated (Railway uses service_role)

-- Faculty and admins can read all scores (for cohort analytics)
CREATE POLICY "faculty_read_all_scores"
    ON resident_scores FOR SELECT
    USING (auth_role() IN ('faculty', 'admin'));

-- ============================================================
-- score_uploads policies
-- ============================================================
CREATE POLICY "residents_manage_own_uploads"
    ON score_uploads FOR ALL
    USING (resident_id = auth.uid());

CREATE POLICY "faculty_read_all_uploads"
    ON score_uploads FOR SELECT
    USING (auth_role() IN ('faculty', 'admin'));

-- ============================================================
-- assessment_sessions policies
-- ============================================================
CREATE POLICY "residents_manage_own_sessions"
    ON assessment_sessions FOR ALL
    USING (resident_id = auth.uid());

CREATE POLICY "faculty_read_all_sessions"
    ON assessment_sessions FOR SELECT
    USING (auth_role() IN ('faculty', 'admin'));

-- ============================================================
-- reading_completions policies
-- ============================================================
CREATE POLICY "residents_manage_own_completions"
    ON reading_completions FOR ALL
    USING (resident_id = auth.uid());

CREATE POLICY "faculty_read_all_completions"
    ON reading_completions FOR SELECT
    USING (auth_role() IN ('faculty', 'admin'));

-- ============================================================
-- question_sets policies (faculty-owned)
-- ============================================================
CREATE POLICY "faculty_manage_own_sets"
    ON question_sets FOR ALL
    USING (faculty_id = auth.uid());

CREATE POLICY "admins_read_all_sets"
    ON question_sets FOR SELECT
    USING (auth_role() = 'admin');

-- ============================================================
-- Read-only public content tables
-- Authenticated users (any role) can read questions, articles, etc.
-- No RLS needed because there is no per-user data — enable and allow all reads.
-- ============================================================
ALTER TABLE articles                ENABLE ROW LEVEL SECURITY;
ALTER TABLE questions               ENABLE ROW LEVEL SECURITY;
ALTER TABLE aafp_questions          ENABLE ROW LEVEL SECURITY;
ALTER TABLE qid_art_xref            ENABLE ROW LEVEL SECURITY;
ALTER TABLE aafp_qid_art_xref       ENABLE ROW LEVEL SECURITY;
ALTER TABLE article_icd10           ENABLE ROW LEVEL SECURITY;
ALTER TABLE question_icd10          ENABLE ROW LEVEL SECURITY;
ALTER TABLE aafp_question_icd10     ENABLE ROW LEVEL SECURITY;
ALTER TABLE clinical_pathways       ENABLE ROW LEVEL SECURITY;
ALTER TABLE article_citation_trend  ENABLE ROW LEVEL SECURITY;
ALTER TABLE article_currency        ENABLE ROW LEVEL SECURITY;
ALTER TABLE icd10_rollup            ENABLE ROW LEVEL SECURITY;
ALTER TABLE icd10_code_xref         ENABLE ROW LEVEL SECURITY;
ALTER TABLE article_icd10_vec       ENABLE ROW LEVEL SECURITY;
ALTER TABLE question_icd10_vec      ENABLE ROW LEVEL SECURITY;
ALTER TABLE icd10_vec               ENABLE ROW LEVEL SECURITY;

-- All authenticated users can read content tables
CREATE POLICY "authenticated_read_articles"
    ON articles FOR SELECT TO authenticated USING (true);

CREATE POLICY "authenticated_read_questions"
    ON questions FOR SELECT TO authenticated USING (true);

CREATE POLICY "authenticated_read_aafp_questions"
    ON aafp_questions FOR SELECT TO authenticated USING (true);

CREATE POLICY "authenticated_read_qid_art_xref"
    ON qid_art_xref FOR SELECT TO authenticated USING (true);

CREATE POLICY "authenticated_read_aafp_qid_art_xref"
    ON aafp_qid_art_xref FOR SELECT TO authenticated USING (true);

CREATE POLICY "authenticated_read_article_icd10"
    ON article_icd10 FOR SELECT TO authenticated USING (true);

CREATE POLICY "authenticated_read_question_icd10"
    ON question_icd10 FOR SELECT TO authenticated USING (true);

CREATE POLICY "authenticated_read_aafp_question_icd10"
    ON aafp_question_icd10 FOR SELECT TO authenticated USING (true);

CREATE POLICY "authenticated_read_clinical_pathways"
    ON clinical_pathways FOR SELECT TO authenticated USING (true);

CREATE POLICY "authenticated_read_article_citation_trend"
    ON article_citation_trend FOR SELECT TO authenticated USING (true);

CREATE POLICY "authenticated_read_article_currency"
    ON article_currency FOR SELECT TO authenticated USING (true);

CREATE POLICY "authenticated_read_icd10_rollup"
    ON icd10_rollup FOR SELECT TO authenticated USING (true);

CREATE POLICY "authenticated_read_icd10_code_xref"
    ON icd10_code_xref FOR SELECT TO authenticated USING (true);

CREATE POLICY "authenticated_read_article_icd10_vec"
    ON article_icd10_vec FOR SELECT TO authenticated USING (true);

CREATE POLICY "authenticated_read_question_icd10_vec"
    ON question_icd10_vec FOR SELECT TO authenticated USING (true);

CREATE POLICY "authenticated_read_icd10_vec"
    ON icd10_vec FOR SELECT TO authenticated USING (true);
