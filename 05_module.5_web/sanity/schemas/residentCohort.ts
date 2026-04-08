import { defineType, defineField } from "sanity";

/**
 * residentCohort — a group of residents sharing a graduation year.
 * Members are referenced by their Supabase auth user ID.
 */
export const residentCohort = defineType({
  name: "residentCohort",
  title: "Resident Cohort",
  type: "document",
  fields: [
    defineField({
      name: "cohortYear",
      title: "Graduation Year (PGY-3)",
      type: "number",
      description: "e.g. 2027 for the class graduating in June 2027",
      validation: (R) => R.required().min(2020).max(2040).integer(),
    }),
    defineField({
      name: "programName",
      title: "Residency Program",
      type: "string",
      description: "e.g. 'Springfield Family Medicine Residency'",
      validation: (R) => R.required(),
    }),
    defineField({
      name: "members",
      title: "Resident Members",
      type: "array",
      of: [
        {
          type: "object",
          fields: [
            defineField({
              name: "supabaseUserId",
              title: "Supabase User ID (UUID)",
              type: "string",
              description: "Copy from Supabase → Authentication → Users",
              validation: (R) => R.required(),
            }),
            defineField({
              name: "displayName",
              title: "Display Name",
              type: "string",
            }),
            defineField({
              name: "pgyYear",
              title: "PGY Year",
              type: "number",
              options: { list: [1, 2, 3] },
            }),
          ],
        },
      ],
    }),
    defineField({
      name: "notes",
      title: "Notes",
      type: "text",
      rows: 3,
    }),
  ],
  preview: {
    select: { title: "programName", subtitle: "cohortYear" },
    prepare: ({ title, subtitle }) => ({
      title,
      subtitle: `Class of ${subtitle}`,
    }),
  },
});
