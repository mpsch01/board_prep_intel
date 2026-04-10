/**
 * AssessmentRunner — Client component for the question-by-question exam interface.
 *
 * Persists responses to Supabase in real time so the session can be resumed.
 * Marks the session complete when the resident submits all answers.
 */
"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";

const PASSING_THRESHOLD = 70; // % correct to display green score color

interface Choice {
  letter: string;
  text: string;
}

interface Question {
  qid: string;
  question_text: string;
  choices: Choice[];
  correct_answer: string;
  explanation: string;
  blueprint: string | null;
  body_system_merged: string | null;
  exam_year: number;
}

interface SessionResponse {
  selected: string;
  correct: boolean;
  answered_at: string;
}

interface Props {
  sessionId: string;
  questions: Question[];
  initialResponses: Record<string, SessionResponse>;
}

export default function AssessmentRunner({ sessionId, questions, initialResponses }: Props) {
  const supabase = createClient();
  const [current, setCurrent] = useState(() => {
    // Resume at the first unanswered question
    const firstUnanswered = questions.findIndex((q) => !(q.qid in initialResponses));
    return firstUnanswered === -1 ? questions.length - 1 : firstUnanswered;
  });
  const [responses, setResponses] = useState<Record<string, SessionResponse>>(initialResponses);
  const [selected, setSelected] = useState<string | null>(null);
  const [revealed, setRevealed] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [completed, setCompleted] = useState(
    Object.keys(initialResponses).length === questions.length
  );

  const question = questions[current];
  const totalAnswered = Object.keys(responses).length;
  const progressPct = Math.round((totalAnswered / questions.length) * 100);

  async function submitAnswer() {
    if (!selected || !question) return;
    setSubmitting(true);

    const correct = selected === question.correct_answer;
    const response: SessionResponse = {
      selected,
      correct,
      answered_at: new Date().toISOString(),
    };

    const newResponses = { ...responses, [question.qid]: response };
    setResponses(newResponses);
    setRevealed(true);

    // Persist to Supabase
    const isLast = current === questions.length - 1;
    await supabase
      .from("assessment_sessions")
      .update({
        responses: newResponses,
        ...(isLast ? { status: "completed", completed_at: new Date().toISOString() } : {}),
      })
      .eq("id", sessionId);

    if (isLast) setCompleted(true);
    setSubmitting(false);
  }

  function nextQuestion() {
    setSelected(null);
    setRevealed(false);
    setCurrent((c) => Math.min(c + 1, questions.length - 1));
  }

  if (completed) {
    const correct = Object.values(responses).filter((r) => r.correct).length;
    const pct = Math.round((correct / questions.length) * 100);

    return (
      <div style={{ textAlign: "center", padding: "3rem 1rem" }}>
        <div style={{ fontSize: "3rem", marginBottom: "1rem" }}>🎉</div>
        <h2 style={{ fontSize: "1.5rem", marginBottom: "0.5rem" }}>Assessment Complete!</h2>
        <p style={{ fontSize: "1.25rem", color: pct >= PASSING_THRESHOLD ? "var(--color-success)" : "var(--color-danger)" }}>
          {correct} / {questions.length} correct ({pct}%)
        </p>
        <div style={{ marginTop: "2rem", display: "flex", gap: "1rem", justifyContent: "center" }}>
          <a href="/resident/analytics" style={{ padding: "0.75rem 1.5rem", background: "var(--color-primary)", color: "white", borderRadius: "6px" }}>
            View Analytics
          </a>
          <a href="/resident/dashboard" style={{ padding: "0.75rem 1.5rem", border: "1px solid var(--color-border)", borderRadius: "6px", color: "inherit" }}>
            Back to Dashboard
          </a>
        </div>
      </div>
    );
  }

  if (!question) return null;

  const savedResponse = responses[question.qid];

  return (
    <div>
      {/* Progress bar */}
      <div style={{ marginBottom: "1.5rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.875rem", color: "var(--color-text-muted)", marginBottom: "0.375rem" }}>
          <span>Question {current + 1} of {questions.length}</span>
          <span>{totalAnswered} answered · {progressPct}%</span>
        </div>
        <div style={{ height: "6px", background: "var(--color-border)", borderRadius: "3px" }}>
          <div style={{ height: "100%", width: `${progressPct}%`, background: "var(--color-primary)", borderRadius: "3px", transition: "width 0.3s" }} />
        </div>
      </div>

      {/* Question meta */}
      <div style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)", marginBottom: "0.75rem" }}>
        {question.qid} · ITE {question.exam_year} · {question.blueprint ?? ""} · {question.body_system_merged ?? ""}
      </div>

      {/* Question stem */}
      <p style={{ fontSize: "1.0625rem", lineHeight: 1.6, marginBottom: "1.5rem" }}>
        {question.question_text}
      </p>

      {/* Choices */}
      <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", marginBottom: "1.5rem" }}>
        {question.choices.map((c) => {
          const isSelected = (savedResponse?.selected ?? selected) === c.letter;
          const isCorrect = c.letter === question.correct_answer;
          const showResult = revealed || !!savedResponse;

          let bg = "var(--color-surface)";
          let border = "1px solid var(--color-border)";
          if (showResult && isCorrect) { bg = "#dcfce7"; border = "1px solid var(--color-success)"; }
          else if (showResult && isSelected && !isCorrect) { bg = "#fee2e2"; border = "1px solid var(--color-danger)"; }
          else if (isSelected) { border = "2px solid var(--color-primary)"; }

          return (
            <button
              key={c.letter}
              onClick={() => !showResult && setSelected(c.letter)}
              disabled={showResult}
              style={{ padding: "0.75rem 1rem", background: bg, border, borderRadius: "6px", textAlign: "left", cursor: showResult ? "default" : "pointer", width: "100%", display: "flex", gap: "0.75rem", alignItems: "flex-start" }}
            >
              <span style={{ fontWeight: 700, minWidth: "1.25rem" }}>{c.letter}.</span>
              <span>{c.text}</span>
            </button>
          );
        })}
      </div>

      {/* Explanation (shown after answer) */}
      {(revealed || savedResponse) && (
        <div style={{ background: "#f9fafb", border: "1px solid var(--color-border)", borderRadius: "6px", padding: "1rem", marginBottom: "1.5rem", fontSize: "0.9375rem", lineHeight: 1.6 }}>
          <strong>Explanation: </strong>{question.explanation}
        </div>
      )}

      {/* Action buttons */}
      <div style={{ display: "flex", gap: "0.75rem" }}>
        {!revealed && !savedResponse && (
          <button
            onClick={submitAnswer}
            disabled={!selected || submitting}
            style={{ padding: "0.75rem 1.5rem", background: "var(--color-primary)", color: "white", border: "none", borderRadius: "6px", cursor: !selected ? "not-allowed" : "pointer", opacity: !selected ? 0.7 : 1, fontWeight: 600 }}
          >
            Submit Answer
          </button>
        )}
        {(revealed || savedResponse) && current < questions.length - 1 && (
          <button onClick={nextQuestion} style={{ padding: "0.75rem 1.5rem", background: "var(--color-primary)", color: "white", border: "none", borderRadius: "6px", cursor: "pointer", fontWeight: 600 }}>
            Next Question →
          </button>
        )}
        {(revealed || savedResponse) && current === questions.length - 1 && !completed && (
          <button
            onClick={async () => {
              setSubmitting(true);
              try {
                const { error } = await supabase
                  .from("assessment_sessions")
                  .update({ status: "completed", completed_at: new Date().toISOString() })
                  .eq("id", sessionId);
                if (error) {
                  console.error("Failed to persist session completion:", error);
                  return;
                }
                setCompleted(true);
              } finally {
                setSubmitting(false);
              }
            }}
            disabled={submitting}
            style={{ padding: "0.75rem 1.5rem", background: "var(--color-success)", color: "white", border: "none", borderRadius: "6px", cursor: submitting ? "not-allowed" : "pointer", fontWeight: 600 }}
          >
            Finish Assessment
          </button>
        )}
      </div>
    </div>
  );
}
