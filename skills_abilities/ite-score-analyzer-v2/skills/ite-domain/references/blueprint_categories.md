# ITE & AAFP — Canonical Blueprint and Body System Categories

Sourced directly from `ite_intelligence.db` (2018–2025). These are the exact strings used in the database. The PDF parser must match these strings exactly — case-sensitive, including punctuation.

---

## Blueprint Categories

**100% stable** — identical strings across all 8 exam years (2018–2025) for both ITE and AAFP BRQ.

| Category | ITE Questions | AAFP Questions |
|----------|:------------:|:--------------:|
| Acute Care and Diagnosis | 709 | 588 |
| Chronic Care Management | 403 | 253 |
| Emergent and Urgent Care | 214 | 166 |
| Preventive Care | 206 | 140 |
| Foundations of Care | 97 | 74 |

**If the PDF parser returns a blueprint category string NOT in this list → parsing failure. Stop and diagnose before continuing.**

---

## Body System Categories — Standard Strings

These are the stable strings used 2018–2023 and restored in 2025.

| Category | Notes |
|----------|-------|
| Cardiovascular | |
| Respiratory | |
| Musculoskeletal | See 2024 drift below |
| Endocrine | |
| Gastrointestinal | |
| Psychogenic | See 2024 drift below |
| Population-Based Care | |
| Nonspecific | |
| Integumentary | |
| Reproductive: Female | See 2024 drift below |
| Patient-Based Systems | |
| Neurologic | |
| Nephrologic | |
| Hematologic/ Immune | Note: includes a space before `/` — `Hematologic/ Immune` |
| Special Sensory | |
| Reproductive: Male | |

---

## ⚠️ 2024 Body System Category Drift

ABFM **renamed** three body system categories for the 2024 ITE only, then reverted in 2025. This is a documented naming inconsistency in the DB.

| Standard Name | 2024 Name | Notes |
|---------------|-----------|-------|
| `Musculoskeletal` | `Injuries/Musculoskeletal` | 2024 only |
| `Psychogenic` | `Psychiatric/Behavioral` | 2024 only |
| `Reproductive: Female` + `Reproductive: Male` | `Sexual and Reproductive` | Merged in 2024 only |

**Impact on parsing:**
- If processing a **2024** score report and the PDF contains `Injuries/Musculoskeletal`, `Psychiatric/Behavioral`, or `Sexual and Reproductive` → these are valid 2024 category strings. The DB contains both forms.
- The analyzer must handle both forms when filtering questions by body system for 2024.
- When displaying results, normalize to the standard name for consistency (e.g., label `Injuries/Musculoskeletal` as `Musculoskeletal (2024)` in output).

---

## Tip: Validating Parser Output

After PDF extraction, before running analysis, validate category strings:

```python
VALID_BLUEPRINT = {
    "Acute Care and Diagnosis",
    "Chronic Care Management",
    "Emergent and Urgent Care",
    "Preventive Care",
    "Foundations of Care"
}

VALID_BODY_SYSTEM_STD = {
    "Cardiovascular", "Respiratory", "Musculoskeletal", "Endocrine",
    "Gastrointestinal", "Psychogenic", "Population-Based Care", "Nonspecific",
    "Integumentary", "Reproductive: Female", "Patient-Based Systems",
    "Neurologic", "Nephrologic", "Hematologic/ Immune", "Special Sensory",
    "Reproductive: Male"
}

VALID_BODY_SYSTEM_2024 = {
    "Injuries/Musculoskeletal", "Psychiatric/Behavioral", "Sexual and Reproductive"
}

VALID_BODY_SYSTEM = VALID_BODY_SYSTEM_STD | VALID_BODY_SYSTEM_2024
```

If a parsed category doesn't appear in the valid sets, report it as a parsing error rather than silently proceeding with a zero-match analysis.
