import os

ROOT = r"C:\Users\mpsch\Desktop\board_prep_intel"

# CLAUDE.md patches
claude_path = os.path.join(ROOT, "CLAUDE.md")
with open(claude_path, "r", encoding="utf-8") as f:
    txt = f.read()

txt = txt.replace(
    "| Active BATON | `BATON_active_038_20260404_code_review_fixes.md` |",
    "| Active BATON | `BATON_active_038_20260404_code_review_fixes.md` — Option B COMPLETE |"
)
txt = txt.replace(
    "GIT-COMMITTED (code review fixes: 14 defects \u2014 4 critical, 4 high, 4 medium, 2 low)",
    "GIT-COMMITTED (code review fixes + Option B flatten + repo rename to board_prep_intel)"
)
txt = txt.replace(
    "https://github.com/mpsch01/project-overhaul",
    "https://github.com/mpsch01/board_prep_intel"
)
txt = txt.replace(
    r"C:\Users\mpsch\Desktop\claude_knowledge\00_#PROJECT_OVERHAUL" + "\\",
    r"C:\Users\mpsch\Desktop\board_prep_intel" + "\\"
)
txt = txt.replace(
    "6. **Option B** \u2014 Flatten `00_#PROJECT_OVERHAUL/` \u2192 `claude_knowledge/` root (path-safe per `repo_pre_severance.md`)",
    "6. **Option B** \u2014 COMPLETE (2026-04-04): `board_prep_intel/` is now the flat project root on desktop"
)

with open(claude_path, "w", encoding="utf-8") as f:
    f.write(txt)
print("CLAUDE.md patched")

# _index.md patches
idx_path = os.path.join(ROOT, "_index.md")
with open(idx_path, "r", encoding="utf-8") as f:
    txt = f.read()

txt = txt.replace(
    "**Scope:** `00_#PROJECT_OVERHAUL/` only",
    "**Scope:** `board_prep_intel/` (project root \u2014 Option B complete 2026-04-04)"
)
txt = txt.replace(
    "**Last Updated:** 2026-04-04 (BATON 038)",
    "**Last Updated:** 2026-04-04 (BATON 038 \u2014 Option B complete)"
)
txt = txt.replace(
    "> This file maps only the `00_#PROJECT_OVERHAUL` workspace. It does not map the broader `claude_knowledge` tree.",
    "> This file maps the `board_prep_intel/` project root. `00_#PROJECT_OVERHAUL` nesting has been removed (Option B, 2026-04-04)."
)

with open(idx_path, "w", encoding="utf-8") as f:
    f.write(txt)
print("_index.md patched")

# auto-memory-copies/project_overhaul_state.md patches
mem_path = os.path.join(ROOT, "auto-memory-copies", "project_overhaul_state.md")
with open(mem_path, "r", encoding="utf-8") as f:
    txt = f.read()

txt = txt.replace(
    "description: Current PROJECT_OVERHAUL state: BATON 038, code review fixes complete (14 defects), DEFERRED-A still priority",
    "description: BATON 038, Option B complete \u2014 board_prep_intel is flat project root, code review fixes done, DEFERRED-A priority"
)
txt = txt.replace(
    r"C:\Users\mpsch\Desktop\claude_knowledge\00_#PROJECT_OVERHAUL" + "\\",
    r"C:\Users\mpsch\Desktop\board_prep_intel" + "\\"
)
txt = txt.replace(
    "GIT-COMMITTED (code review: 14 defects fixed \u2014 4 critical path/hop bugs + 10 others)",
    "GIT-COMMITTED (code review fixes + Option B flatten + repo renamed board_prep_intel)"
)

with open(mem_path, "w", encoding="utf-8") as f:
    f.write(txt)
print("project_overhaul_state.md patched")

print("All done.")
