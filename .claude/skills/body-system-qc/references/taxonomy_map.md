# ABFM Body System Taxonomy Map

## Post-2024 Canonical Taxonomy (15 categories — DB standard)

| Category | Notes |
|----------|-------|
| Cardiovascular | Unchanged across all ABFM years |
| Endocrine | Unchanged |
| Gastrointestinal | Unchanged |
| Hematologic/Immune | Note: no space after slash (artifact: "Hematologic/ Immune" = wrong) |
| Injuries/Musculoskeletal | Post-2024 name; pre-2024 ABFM used "Musculoskeletal" |
| Integumentary | Unchanged |
| Nephrologic | Unchanged |
| Neurologic | Unchanged |
| Nonspecific | Unchanged |
| Patient-Based Systems | Unchanged |
| Population-Based Care | Unchanged |
| Psychiatric/Behavioral | Post-2024 name; pre-2024 ABFM used "Psychogenic" |
| Respiratory | Unchanged |
| Sexual and Reproductive | Post-2024 name; pre-2024 ABFM used "Reproductive: Female" + "Reproductive: Male" |
| Special Sensory | Unchanged |

---

## Condensation Map (pre-2024 → post-2024 canonical)

| Pre-2024 ABFM Name | Post-2024 Canonical | Change Type |
|---------------------|---------------------|-------------|
| Psychogenic | Psychiatric/Behavioral | Rename |
| Reproductive: Female | Sexual and Reproductive | Collapse + Rename |
| Reproductive: Male | Sexual and Reproductive | Collapse + Rename |
| Musculoskeletal | Injuries/Musculoskeletal | Rename |
| Cardiovascular | Cardiovascular | Unchanged |
| Respiratory | Respiratory | Unchanged |
| Gastrointestinal | Gastrointestinal | Unchanged |
| Endocrine | Endocrine | Unchanged |
| Integumentary | Integumentary | Unchanged |
| Neurologic | Neurologic | Unchanged |
| Nephrologic | Nephrologic | Unchanged |
| Special Sensory | Special Sensory | Unchanged |
| Hematologic/Immune | Hematologic/Immune | Unchanged |
| Nonspecific | Nonspecific | Unchanged |
| Population-Based Care | Population-Based Care | Unchanged |
| Patient-Based Systems | Patient-Based Systems | Unchanged |

---

## Old AI-Synthesized Names (2018-2019 era — now corrected)

These were produced by `enrich_ite_questions.py` (Claude API, 16-category taxonomy)
and should no longer appear in the DB after body system QC is applied:

| Synthesized Name | Correct Post-2024 Name |
|------------------|----------------------|
| Pulmonary/Critical Care | Respiratory |
| Dermatologic | Integumentary |
| Eyes, Ears, Nose & Throat | Special Sensory |
| Nephrologic/Urologic | Nephrologic |
| Population-Based/Preventive | Population-Based Care |
| Maternity Care | Sexual and Reproductive |
| Nonspecific/Other | Nonspecific |
| Reproductive (Female) | Sexual and Reproductive |
| Reproductive (Male) | Sexual and Reproductive |

---

## body_system_merged Direction (post-QC)

After the body system QC pipeline, `body_system_merged` should map FROM
pre-2024 ABFM names TO post-2024 canonical (forward mapping):

| Raw body_system (2022-2023 ABFM original) | body_system_merged |
|-------------------------------------------|-------------------|
| Psychogenic | Psychiatric/Behavioral |
| Reproductive: Female | Sexual and Reproductive |
| Reproductive: Male | Sexual and Reproductive |
| Musculoskeletal | Injuries/Musculoskeletal |
| All other pre-2024 names | Same value (already canonical) |

For 2018-2021 and 2024-2025 questions (updated by QC pipeline):
body_system already contains post-2024 canonical → body_system_merged = body_system
