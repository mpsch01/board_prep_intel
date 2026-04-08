import { defineType, defineField } from "sanity";

/**
 * facultyAnnouncement — broadcast message to residents.
 * Displayed on the resident dashboard.
 */
export const facultyAnnouncement = defineType({
  name: "facultyAnnouncement",
  title: "Faculty Announcement",
  type: "document",
  fields: [
    defineField({
      name: "title",
      title: "Title",
      type: "string",
      validation: (R) => R.required(),
    }),
    defineField({
      name: "body",
      title: "Message Body",
      type: "array",
      of: [{ type: "block" }],
    }),
    defineField({
      name: "audience",
      title: "Audience",
      type: "string",
      options: {
        list: [
          { title: "All Residents", value: "all" },
          { title: "Specific Cohort", value: "cohort" },
        ],
        layout: "radio",
      },
      initialValue: "all",
    }),
    defineField({
      name: "cohort",
      title: "Cohort (if specific)",
      type: "reference",
      to: [{ type: "residentCohort" }],
      hidden: ({ document }) => document?.audience !== "cohort",
    }),
    defineField({
      name: "pinned",
      title: "Pinned to Top",
      type: "boolean",
      initialValue: false,
    }),
    defineField({
      name: "publishedAt",
      title: "Publish Date",
      type: "datetime",
      description: "Leave blank for immediate publish on save",
    }),
    defineField({
      name: "expiresAt",
      title: "Expiry Date",
      type: "datetime",
      description: "Announcement hidden from residents after this date",
    }),
  ],
  preview: {
    select: { title: "title", pinned: "pinned" },
    prepare: ({ title, pinned }) => ({
      title: `${pinned ? "📌 " : ""}${title}`,
    }),
  },
  orderings: [
    {
      title: "Publish Date, Newest First",
      name: "publishedAtDesc",
      by: [{ field: "publishedAt", direction: "desc" }],
    },
  ],
});
