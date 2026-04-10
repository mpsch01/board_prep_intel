# report_config.json — Specification

Located at: `C:\Users\mpsch\Desktop\board_prep_intel\03_module.3_analyst\scripts\report_config.json`

This file controls **what the analysis report shows** — not how the pipeline runs. The pipeline steps are locked. Edit this file when you want to:
- Change what counts as a "weak" area
- Turn report sections on or off
- Adjust how many practice questions are generated
- Change output format

---

## Full Schema

```json
{
  "weakness_threshold": 0.70,
  "easy_miss_threshold": 0.80,
  "priority_top_n": 5,
  "question_count_per_area": 5,
  "pgy_default": 3,
  "plugins_default": ["concept", "icd10"],

  "sections": {
    "score_overview":       true,
    "blueprint_analysis":   true,
    "body_system_analysis": true,
    "priority_matrix":      true,
    "easy_misses":          true,
    "practice_questions":   true,
    "study_plan":           true,
    "icd10_crosswalk":      true,
    "concept_tags":         true
  },

  "output_formats": ["docx", "json"],

  "styling": {
    "theme": "st_lukes",
    "font": "Aptos",
    "page_size": "letter"
  }
}
```

---

## Field Reference

### Thresholds

| Field | Type | Default | Meaning |
|-------|------|---------|---------|
| `weakness_threshold` | float (0–1) | `0.70` | Resident score below this % → flagged as weak area |
| `easy_miss_threshold` | float (0–1) | `0.80` | Items where national correct_rate > this value that the resident missed → "easy misses" (high-yield catches) |
| `priority_top_n` | int | `5` | Number of top-priority weak areas to feature in the priority matrix |
| `question_count_per_area` | int | `5` | Practice questions generated per weak area |

### Defaults (used when CLI args not provided)

| Field | Type | Default |
|-------|------|---------|
| `pgy_default` | int | `3` |
| `plugins_default` | list | `["concept", "icd10"]` |

### Sections

Set any section to `false` to exclude it from the output DOCX:

| Section | What It Shows |
|---------|---------------|
| `score_overview` | Overall %, scaled score, percentile, pass tier |
| `blueprint_analysis` | Performance table by ABFM blueprint category |
| `body_system_analysis` | Performance table by organ system |
| `priority_matrix` | Ranked weak areas by weight × deficit |
| `easy_misses` | High-difficulty items that were missed |
| `practice_questions` | DB-linked practice questions for weak areas |
| `study_plan` | Weekly study schedule targeting weak areas |
| `icd10_crosswalk` | ICD-10 → article links for weak areas |
| `concept_tags` | Related clinical concepts by weak area |

### Output

| Field | Values |
|-------|--------|
| `output_formats` | `["docx"]`, `["json"]`, or `["docx", "json"]` |

### Styling

Do not change `styling` unless you know what you're doing — it's tied to the DOCX builder defaults.

---

## Common Edits

**Lower the weakness threshold (catch more gaps):**
```json
"weakness_threshold": 0.65
```

**Increase practice questions:**
```json
"question_count_per_area": 8
```

**Turn off ICD-10 crosswalk (faster run, smaller doc):**
```json
"sections": {
  "icd10_crosswalk": false
}
```

**Show only top 3 priorities:**
```json
"priority_top_n": 3
```
