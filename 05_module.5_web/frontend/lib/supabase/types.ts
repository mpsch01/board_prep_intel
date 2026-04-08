/**
 * Supabase TypeScript type definitions.
 *
 * Generate the full auto-typed version with:
 *   npx supabase gen types typescript --project-id YOUR_PROJECT_ID > lib/supabase/types.ts
 *
 * The manual definitions below cover the tables used most frequently
 * in server components and are sufficient until you run the generator.
 */

export type UserRole = "resident" | "faculty" | "admin";

export interface UserProfile {
  id: string;
  role: UserRole;
  display_name: string | null;
  abfm_id: string | null;
  program: string | null;
  cohort_year: number | null;
  created_at: string;
  updated_at: string;
}

export interface Article {
  clean_ref: string;
  article_id: string;
  author1: string | null;
  author2: string | null;
  year: string | null;
  canonical_filename: string | null;
  codon_filename: string | null;
  tier: "VC_fail" | "VC_pass" | "local_lite" | "right_click" | null;
  source_type: string | null;
  engine_type: string | null;
  citation_count: number;
  unique_years: number;
  exam_years: number[] | null;
  blueprint: string | null;
  body_system: string | null;
  concept_tags: ConceptTags | null;
}

export interface ConceptTags {
  diagnoses: string[];
  drugs: string[];
  procedures: string[];
  concept_summary: string;
}

export interface Question {
  qid: string;
  exam_year: number;
  question_text: string;
  choices: { letter: string; text: string }[];
  correct_answer: string;
  explanation: string;
  body_system: string | null;
  body_system_merged: string | null;
  blueprint: string | null;
  concept_tags: ConceptTags | null;
}

export interface AafpQuestion {
  aafp_qid: string;
  stem: string;
  choices: { letter: string; text: string }[];
  correct_letter: string;
  correct_text: string;
  explanation: string;
  body_system: string | null;
  blueprint: string | null;
  concept_tags: ConceptTags | null;
  ite_nearest_qid: string | null;
}

export interface ResidentScore {
  id: number;
  resident_id: string;
  exam_year: number;
  item_number: number;
  qid: string | null;
  answered_correct: boolean;
  blueprint: string | null;
  body_system: string | null;
  uploaded_at: string;
}

export interface AssessmentSession {
  id: string;
  resident_id: string;
  assignment_id: string | null;
  qids: string[];
  responses: Record<string, SessionResponse>;
  status: "active" | "completed" | "abandoned";
  started_at: string;
  completed_at: string | null;
}

export interface SessionResponse {
  selected: string;
  correct: boolean;
  answered_at: string;
}

export interface ArticleCitationTrend {
  article_id: string;
  years_cited: string;
  distinct_year_count: number;
  first_cited_year: number;
  most_recent_year: number;
  consecutive_streak: number;
  is_watch_list: boolean;
}

export interface ArticleCurrency {
  article_id: string;
  pubmed_id: string | null;
  pub_date: string | null;
  pub_title: string | null;
  last_checked: string | null;
  newer_version_pmid: string | null;
  newer_version_date: string | null;
  newer_version_title: string | null;
  currency_status: "current" | "updated" | "check_needed" | "not_indexed" | null;
  title_signals: string[] | null;
}

export interface QuestionSet {
  id: string;
  faculty_id: string;
  name: string;
  query: string | null;
  qids: string[];
  article_ids: string[] | null;
  created_at: string;
  updated_at: string;
}

// Minimal Database type for createBrowserClient<Database> generic
export interface Database {
  public: {
    Tables: {
      user_profiles: { Row: UserProfile };
      articles: { Row: Article };
      questions: { Row: Question };
      aafp_questions: { Row: AafpQuestion };
      resident_scores: { Row: ResidentScore };
      assessment_sessions: { Row: AssessmentSession };
      article_citation_trend: { Row: ArticleCitationTrend };
      article_currency: { Row: ArticleCurrency };
      question_sets: { Row: QuestionSet };
    };
  };
}
