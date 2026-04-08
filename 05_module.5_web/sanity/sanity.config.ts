import { defineConfig } from "sanity";
import { structureTool } from "sanity/structure";
import { visionTool } from "@sanity/vision";
import { schemaTypes } from "./schemas";

export default defineConfig({
  name: "board-prep-intel",
  title: "Board Prep Intel — Curriculum Studio",

  // Replace with your Sanity project ID and dataset after running `sanity init`
  projectId: process.env.SANITY_PROJECT_ID ?? "REPLACE_ME",
  dataset: process.env.SANITY_DATASET ?? "production",

  plugins: [
    structureTool({
      structure: (S) =>
        S.list()
          .title("Curriculum")
          .items([
            S.listItem()
              .title("Cohorts")
              .child(S.documentTypeList("residentCohort")),
            S.listItem()
              .title("Curriculum Sessions")
              .child(S.documentTypeList("curriculumSession")),
            S.listItem()
              .title("Assessment Assignments")
              .child(S.documentTypeList("assessmentAssignment")),
            S.listItem()
              .title("Prescribed Readings")
              .child(S.documentTypeList("prescribedReading")),
            S.listItem()
              .title("Announcements")
              .child(S.documentTypeList("facultyAnnouncement")),
          ]),
    }),
    visionTool(),
  ],

  schema: {
    types: schemaTypes,
  },
});
