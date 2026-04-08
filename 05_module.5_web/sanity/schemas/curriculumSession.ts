import { defineType, defineField } from "sanity";

// ABFM blueprint categories — mirrors the questions.blueprint column
const BLUEPRINT_CATEGORIES = [
  { title: "Acute Care", value: "Acute Care" },
  { title: "Chronic Care", value: "Chronic Care" },
  { title: "Emergent/Urgent", value: "Emergent/Urgent" },
  { title: "Preventive", value: "Preventive" },
  { title: "Foundations of Medicine", value: "Foundations of Medicine" },
];

// ABFM body systems — mirrors the articles.body_system column
const BODY_SYSTEMS = [
  "Cardiovascular",
  "Dermatology",
  "Ear, Nose & Throat",
  "Endocrine",
  "Eyes",
  "Gastrointestinal",
  "Genitourinary",
  "Hematology/Oncology",
  "Infectious Disease",
  "Mental Health",
  "Musculoskeletal",
  "Neurology",
  "Obstetrics/Gynecology",
  "Pulmonary",
  "Renal",
  "Rheumatology",
  "Other",
].map((v) => ({ title: v, value: v }));

/**
 * curriculumSession — one scheduled teaching event.
 * Linked to assessmentAssignment and prescribedReading documents.
 */
export const curriculumSession = defineType({
  name: "curriculumSession",
  title: "Curriculum Session",
  type: "document",
  fields: [
    defineField({
      name: "title",
      title: "Session Title",
      type: "string",
      description: "e.g. 'Abdominal Pain — Acute & Chronic'",
      validation: (R) => R.required(),
    }),
    defineField({
      name: "sessionDate",
      title: "Session Date",
      type: "date",
    }),
    defineField({
      name: "facilitator",
      title: "Facilitator / Lecturer",
      type: "string",
    }),
    defineField({
      name: "cohorts",
      title: "Assigned Cohorts",
      type: "array",
      of: [{ type: "reference", to: [{ type: "residentCohort" }] }],
      description: "Which resident cohort(s) this session is assigned to",
    }),
    defineField({
      name: "bodySystem",
      title: "Primary Body System",
      type: "string",
      options: { list: BODY_SYSTEMS },
    }),
    defineField({
      name: "blueprintCategories",
      title: "Blueprint Categories Covered",
      type: "array",
      of: [{ type: "string" }],
      options: { list: BLUEPRINT_CATEGORIES },
    }),
    defineField({
      name: "learningObjectives",
      title: "Learning Objectives",
      type: "array",
      of: [{ type: "string" }],
      description: "List the specific competencies this session addresses",
    }),
    defineField({
      name: "sessionNotes",
      title: "Session Notes",
      type: "array",
      of: [{ type: "block" }],
      description: "Rich-text notes visible to residents after the session",
    }),
    defineField({
      name: "status",
      title: "Status",
      type: "string",
      options: {
        list: [
          { title: "Draft", value: "draft" },
          { title: "Scheduled", value: "scheduled" },
          { title: "Completed", value: "completed" },
        ],
        layout: "radio",
      },
      initialValue: "draft",
    }),
  ],
  preview: {
    select: {
      title: "title",
      subtitle: "sessionDate",
      status: "status",
    },
    prepare: ({ title, subtitle, status }) => ({
      title,
      subtitle: subtitle ? `${subtitle} — ${status}` : status,
    }),
  },
  orderings: [
    {
      title: "Session Date, Newest First",
      name: "sessionDateDesc",
      by: [{ field: "sessionDate", direction: "desc" }],
    },
  ],
});
