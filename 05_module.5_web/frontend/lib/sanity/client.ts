import { createClient } from "next-sanity";

export const sanityClient = createClient({
  projectId: process.env.NEXT_PUBLIC_SANITY_PROJECT_ID ?? "",
  dataset: process.env.NEXT_PUBLIC_SANITY_DATASET ?? "production",
  apiVersion: "2024-01-01",
  useCdn: true,  // edge-cached reads; set to false for real-time previews
});

// ── GROQ query helpers ──────────────────────────────────────────────────────

/**
 * Fetch all active curriculum sessions (status != draft) for a cohort year.
 */
export async function getSessionsForCohort(cohortYear: number) {
  return sanityClient.fetch(
    `*[_type == "curriculumSession" && status != "draft" && $year in cohorts[]->cohortYear] | order(sessionDate asc) {
      _id,
      title,
      sessionDate,
      facilitator,
      bodySystem,
      blueprintCategories,
      learningObjectives,
      status
    }`,
    { year: cohortYear }
  );
}

/**
 * Fetch all published prescribed readings for a session.
 * Returns article_ids so the frontend can fetch article details from Supabase.
 */
export async function getPrescribedReadingsForSession(sessionId: string) {
  return sanityClient.fetch(
    `*[_type == "prescribedReading" && session._ref == $sessionId && visibleToResidents == true][0] {
      _id,
      dueDate,
      articles[] {
        articleId,
        canonicalFilename,
        priorityTier,
        readingNotes
      }
    }`,
    { sessionId }
  );
}

/**
 * Fetch all visible assessment assignments for a cohort year.
 */
export async function getAssignmentsForCohort(cohortYear: number) {
  return sanityClient.fetch(
    `*[_type == "assessmentAssignment" && visibleToResidents == true && $year in cohorts[]->cohortYear] | order(dueDate asc) {
      _id,
      title,
      dueDate,
      selectionMode,
      questionCount,
      sourceBank,
      examYears,
      blueprintCategories,
      bodySystems,
      resolvedQids,
      instructions,
      "sessionTitle": session->title
    }`,
    { year: cohortYear }
  );
}

/**
 * Fetch pinned + active announcements for the resident dashboard.
 */
export async function getAnnouncements(cohortYear?: number) {
  const now = new Date().toISOString();
  return sanityClient.fetch(
    `*[_type == "facultyAnnouncement"
        && (audience == "all" || (audience == "cohort" && cohort->cohortYear == $year))
        && (publishedAt == null || publishedAt <= $now)
        && (expiresAt == null || expiresAt > $now)
      ] | order(pinned desc, publishedAt desc) {
        _id,
        title,
        body,
        pinned,
        publishedAt
      }`,
    { year: cohortYear ?? 0, now }
  );
}
