import { defineType, defineField } from "sanity";

/**
 * prescribedReading — links a curriculum session to specific articles
 * from the Supabase knowledge base.
 *
 * Articles are referenced by article_id (e.g. "ART-0470") — Sanity stores
 * only the ID, not the article content.  The frontend fetches article details
 * from Supabase at render time.
 */
export const prescribedReading = defineType({
  name: "prescribedReading",
  title: "Prescribed Reading",
  type: "document",
  fields: [
    defineField({
      name: "session",
      title: "Curriculum Session",
      type: "reference",
      to: [{ type: "curriculumSession" }],
      validation: (R) => R.required(),
    }),
    defineField({
      name: "articles",
      title: "Articles",
      type: "array",
      of: [
        {
          type: "object",
          fields: [
            defineField({
              name: "articleId",
              title: "Article ID",
              type: "string",
              description:
                "ART-NNNN from the Supabase articles table (e.g. ART-0470)",
              validation: (R) =>
                R.required().regex(/^ART-\d{4}$/, {
                  name: "ART-ID format",
                  invert: false,
                }),
            }),
            defineField({
              name: "canonicalFilename",
              title: "Article Reference (display only)",
              type: "string",
              description:
                "Copy-paste canonical_filename from DB for human readability in Studio — not used by the app",
            }),
            defineField({
              name: "priorityTier",
              title: "Priority Tier",
              type: "string",
              options: {
                list: [
                  { title: "Required", value: "required" },
                  { title: "Recommended", value: "recommended" },
                  { title: "Optional", value: "optional" },
                ],
                layout: "radio",
              },
              initialValue: "required",
            }),
            defineField({
              name: "readingNotes",
              title: "Faculty Notes for This Article",
              type: "text",
              rows: 2,
              description: "Optional context for why this article is assigned",
            }),
          ],
          preview: {
            select: { title: "articleId", subtitle: "canonicalFilename" },
          },
        },
      ],
      description:
        "Add one entry per article.  Copy the ART-ID from the database.",
    }),
    defineField({
      name: "dueDate",
      title: "Completion Due Date",
      type: "date",
    }),
    defineField({
      name: "visibleToResidents",
      title: "Visible to Residents",
      type: "boolean",
      description: "Toggle off to draft/hide this reading list",
      initialValue: true,
    }),
  ],
  preview: {
    select: {
      session: "session.title",
      count: "articles",
    },
    prepare: ({ session, count }) => ({
      title: session ?? "Unlinked Reading List",
      subtitle: `${Array.isArray(count) ? count.length : 0} article(s)`,
    }),
  },
});
