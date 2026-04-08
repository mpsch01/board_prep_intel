/**
 * /resident/assessment/[id] — Question-by-question exam interface.
 *
 * [id] = Sanity assessmentAssignment._id
 *
 * This page:
 *   1. Loads the assignment definition from Sanity
 *   2. Resolves the question list from Supabase (dynamic or static)
 *   3. Creates or resumes an assessment_sessions row
 *   4. Renders the AssessmentRunner client component
 */
import { redirect, notFound } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { sanityClient } from "@/lib/sanity/client";
import AssessmentRunner from "@/components/resident/AssessmentRunner";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function AssessmentPage({ params }: PageProps) {
  const { id: assignmentId } = await params;

  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/login");

  // Load assignment from Sanity
  const assignment = await sanityClient.fetch(
    `*[_type == "assessmentAssignment" && _id == $id && visibleToResidents == true][0] {
      _id, title, selectionMode, questionCount, sourceBank,
      examYears, blueprintCategories, bodySystems, resolvedQids, instructions
    }`,
    { id: assignmentId }
  );

  if (!assignment) notFound();

  // Resolve QIDs
  let qids: string[] = [];

  if (assignment.selectionMode === "static" && assignment.resolvedQids?.length) {
    qids = assignment.resolvedQids;
  } else {
    // Dynamic: query Supabase with filters
    let query = supabase.from("questions").select("qid");

    if (assignment.examYears?.length) {
      query = query.in("exam_year", assignment.examYears);
    }
    if (assignment.blueprintCategories?.length) {
      query = query.in("blueprint", assignment.blueprintCategories);
    }
    if (assignment.bodySystems?.length) {
      query = query.in("body_system_merged", assignment.bodySystems);
    }

    const { data: qRows } = await query.limit(assignment.questionCount ?? 20);
    qids = (qRows ?? []).map((r: { qid: string }) => r.qid);
  }

  if (qids.length === 0) {
    return (
      <main style={{ padding: "2rem" }}>
        <h1>{assignment.title}</h1>
        <p style={{ color: "var(--color-text-muted)", marginTop: "1rem" }}>
          No questions matched the assignment filters. Contact your program director.
        </p>
      </main>
    );
  }

  // Find or create an active session
  const { data: existingSession } = await supabase
    .from("assessment_sessions")
    .select("id, qids, responses, status")
    .eq("resident_id", user.id)
    .eq("assignment_id", assignmentId)
    .eq("status", "active")
    .maybeSingle();

  let sessionId: string;
  let sessionResponses: Record<string, unknown> = {};

  if (existingSession) {
    sessionId = existingSession.id;
    sessionResponses = existingSession.responses ?? {};
  } else {
    const { data: newSession } = await supabase
      .from("assessment_sessions")
      .insert({
        resident_id: user.id,
        assignment_id: assignmentId,
        qids,
        status: "active",
      })
      .select("id")
      .single();
    sessionId = newSession!.id;
  }

  // Fetch question details for the resolved QIDs
  const { data: questionRows } = await supabase
    .from("questions")
    .select("qid, exam_year, question_text, choices, correct_answer, explanation, blueprint, body_system_merged")
    .in("qid", qids);

  const questionMap = new Map(
    (questionRows ?? []).map((q: { qid: string }) => [q.qid, q])
  );
  const orderedQuestions = qids
    .map((qid) => questionMap.get(qid))
    .filter(Boolean);

  return (
    <main style={{ maxWidth: "900px", margin: "0 auto", padding: "2rem 1rem" }}>
      <h1 style={{ fontSize: "1.5rem", marginBottom: "0.5rem" }}>{assignment.title}</h1>
      {assignment.instructions && (
        <p style={{ color: "var(--color-text-muted)", marginBottom: "1.5rem" }}>
          {assignment.instructions}
        </p>
      )}
      <AssessmentRunner
        sessionId={sessionId}
        questions={orderedQuestions as never[]}
        initialResponses={sessionResponses as never}
      />
    </main>
  );
}
