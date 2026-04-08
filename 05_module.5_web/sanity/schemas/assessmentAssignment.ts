import { defineType, defineField } from "sanity";

/**
 * assessmentAssignment — defines a practice question set assigned to residents.
 *
 * The actual questions are fetched from Supabase at runtime using the filters
 * defined here.  The faculty sets the parameters; the frontend assembles the
 * question set dynamically.
 *
 * Alternatively, qids can be pre-resolved and stored in the `resolvedQids`
 * array (e.g. after a faculty search session in the NL search tool).
 */
export const assessmentAssignment = defineType({
  name: "assessmentAssignment",
  title: "Assessment Assignment",
  type: "document",
  fields: [
    defineField({
      name: "title",
      title: "Assignment Title",
      type: "string",
      description: "e.g. 'Cardiovascular — Week 3 Practice Set'",
      validation: (R) => R.required(),
    }),
    defineField({
      name: "session",
      title: "Linked Curriculum Session",
      type: "reference",
      to: [{ type: "curriculumSession" }],
    }),
    defineField({
      name: "cohorts",
      title: "Assigned Cohorts",
      type: "array",
      of: [{ type: "reference", to: [{ type: "residentCohort" }] }],
    }),
    defineField({
      name: "dueDate",
      title: "Due Date",
      type: "date",
    }),

    // ── Filter-based question selection ──────────────────────────────────
    defineField({
      name: "selectionMode",
      title: "Question Selection Mode",
      type: "string",
      options: {
        list: [
          {
            title: "Dynamic (use filters below)",
            value: "dynamic",
          },
          {
            title: "Static (pre-resolved QIDs from NL search)",
            value: "static",
          },
        ],
        layout: "radio",
      },
      initialValue: "dynamic",
    }),
    defineField({
      name: "questionCount",
      title: "Number of Questions",
      type: "number",
      description: "How many questions to include",
      validation: (R) => R.min(1).max(200).integer(),
      initialValue: 20,
    }),
    defineField({
      name: "sourceBank",
      title: "Question Bank",
      type: "string",
      options: {
        list: [
          { title: "ITE (2018–2025)", value: "ITE" },
          { title: "AAFP BRQ", value: "AAFP" },
          { title: "Both", value: "both" },
        ],
      },
      initialValue: "ITE",
    }),
    defineField({
      name: "examYears",
      title: "Exam Years (ITE only)",
      type: "array",
      of: [{ type: "number" }],
      description: "Leave empty to include all years (2018–2025)",
    }),
    defineField({
      name: "blueprintCategories",
      title: "Blueprint Categories",
      type: "array",
      of: [{ type: "string" }],
      options: {
        list: [
          "Acute Care",
          "Chronic Care",
          "Emergent/Urgent",
          "Preventive",
          "Foundations of Medicine",
        ].map((v) => ({ title: v, value: v })),
      },
    }),
    defineField({
      name: "bodySystems",
      title: "Body Systems",
      type: "array",
      of: [{ type: "string" }],
      description: "Leave empty to include all body systems",
    }),

    // ── Static pre-resolved QIDs ─────────────────────────────────────────
    defineField({
      name: "resolvedQids",
      title: "Pre-Resolved QIDs (static mode)",
      type: "array",
      of: [{ type: "string" }],
      description:
        "Paste QIDs from the NL search tool.  Only used when Selection Mode = Static.",
    }),

    defineField({
      name: "instructions",
      title: "Resident Instructions",
      type: "text",
      rows: 3,
      description: "Optional instructions shown to residents before starting",
    }),
    defineField({
      name: "visibleToResidents",
      title: "Visible to Residents",
      type: "boolean",
      initialValue: false,
      description: "Toggle on to publish — residents see it on their dashboard",
    }),
  ],
  preview: {
    select: {
      title: "title",
      session: "session.title",
      due: "dueDate",
    },
    prepare: ({ title, session, due }) => ({
      title,
      subtitle: [session, due ? `Due ${due}` : null].filter(Boolean).join(" · "),
    }),
  },
});
