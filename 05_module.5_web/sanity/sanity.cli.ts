import { defineCliConfig } from "sanity/cli";

export default defineCliConfig({
  api: {
    projectId: process.env.SANITY_PROJECT_ID ?? "REPLACE_ME",
    dataset: process.env.SANITY_DATASET ?? "production",
  },
});
