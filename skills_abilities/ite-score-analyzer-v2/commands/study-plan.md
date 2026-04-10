---
description: >
  Generate a focused weekly study plan from a completed ITE analysis.
  Triggers when user says "study plan", "study schedule", "weekly plan", "what should I study",
  or "build a study plan for {resident name}".
allowed-tools: Read, Write, Bash, Glob, Grep, AskUserQuestion, TodoWrite
argument-hint: [resident_dir]
---

# Generate Study Plan from ITE Analysis

Build a targeted weekly study schedule from an existing ITE analysis.

**Prerequisite:** Resident must have a completed `analysis_v2.json`.

## Step 1: Locate Analysis

If a resident directory is provided via $ARGUMENTS, use it. Otherwise ask:
"Which resident's analysis should I build a study plan from?"

List available analyses:
```cmd
dir "C:\Users\mpsch\Desktop\board_prep_intel\03_module.3_analyst\reports\*\analysis_v2.json" /S /B
```

## Step 2: Read Config and Analysis

Read both files in parallel:
- `report_config.json` → weakness_threshold, priority_top_n
- `{resident_dir}/analysis_v2.json` → weak areas, priority matrix, easy misses

## Step 3: Ask Study Context Questions

Ask (as a single AskUserQuestion with options where applicable):

1. **How many weeks until the ITE?** (determines schedule length)
2. **How many hours per week for board prep?** (determines depth)
3. **Any topics to exclude?** (e.g., already strong, personal exemptions)

If the user says "default" or "standard", assume 12 weeks and 5 hours/week.

## Step 4: Build the Plan

**Priority ranking:** Use the priority matrix from `analysis_v2.json` (already ranked by weight × deficit).

**Allocation logic:**
- Top 3 priority areas → 2 weeks each (deep review)
- Next 3 priority areas → 1 week each (targeted review)
- Easy misses → woven into relevant weeks (quick wins)
- Final 1–2 weeks → mixed review + practice exam simulation

**Per-week structure:**
- Week title: primary focus area
- Study tasks: 3–4 specific actions (read guideline, complete practice questions, review concept tags)
- Article links: pull top 2 articles from `qid_art_xref` for the focus area
- Practice question count: from `question_count_per_area` in report_config.json
- Quick-win easy miss: 1 easy miss item per week if applicable

## Step 5: Output

Generate a DOCX study plan with one section per week. Apply St. Luke's palette styling.

Save as:
```
C:\Users\mpsch\Desktop\board_prep_intel\03_module.3_analyst\reports\{LastName}_{Year}\ITE_{Year}_StudyPlan_{Name}.docx
```

Present the file link and summarize the plan structure in 3–4 sentences — how many weeks, top priority area, estimated question load.
