# clinical_pathways Table

**Layer 3 — Clinical Blending Engine**

Maps each (article, ICD-10 code) pair to a clinical pathway role, defining what function the article serves for that condition.

## Schema

| Column | Type | Description |
|--------|------|-------------|
| `article_id` | TEXT | FK → `articles.article_id` |
| `icd10_code` | TEXT | Specific ICD-10 code (e.g., E11.9) |
| `icd10_desc` | TEXT | Human-readable description |
| `pathway_role` | TEXT | Clinical function (7 values — see below) |
| `blueprint` | TEXT | ABFM blueprint category from linked questions |
| `source_bank` | TEXT | `ITE` (2,179), `both` (1,630), `AAFP` (211) — which question bank(s) drive this pathway |
| `relevance` | TEXT | primary / secondary / related (from article_icd10) |
| `confidence` | TEXT | All rows currently `high` |

**Row count**: 4,020 (rebuilt 2026-03-31 — both ITE and AAFP banks, articles ART-0002–ART-1985)
**Built by**: `build_clinical_pathways.py` (zero API calls)

**Note**: The `engine_type` column is on the `articles` table, not on `clinical_pathways`. To get engine_type for pathway queries, JOIN to `articles` on `article_id`.

## Pathway Roles

| Role | Engine Source | Description |
|------|-------------|-------------|
| `screening_prevention` | preventive_guideline (primary/secondary) | USPSTF-style screening criteria, risk assessment tools, prevention protocols, immunization schedules |
| `diagnosis` | diagnostic_guideline (primary/secondary) | Diagnostic criteria, "which test" logic, sensitivity/specificity data, staging systems, classification criteria |
| `first_line` | chronic_guideline (primary) or acute_protocol (primary) | Initial treatment — pharmacologic or non-pharmacologic, the always-appropriate early step |
| `second_line` | rct (primary/secondary) or acute_protocol (secondary) | Novel agents, RCT-tested alternatives, escalation when first-line fails |
| `monitoring` | chronic_guideline (secondary) or preventive_guideline (related) | Ongoing management, lab intervals, titration protocols, red flags to watch |
| `referral` | diagnostic_guideline (related) | When to refer, specialist thresholds, interdisciplinary handoff criteria |
| `special_pops` | chronic/acute/rct (related) | Pediatric, geriatric, pregnant, renal-adjusted dosing, comorbidity modifications |

## articles.engine_type (Join from articles table)

Classifies each article's clinical function. Lives in the `articles` table — join `cp → articles` to access:

| Engine Type | Count | Classification Source |
|-------------|-------|---------------------|
| `acute_protocol` | 1,169 | Treatment + Pharmacology/Management + acute categories |
| `chronic_guideline` | 284 | Prognosis/Counseling + Pharmacology/Management + chronic categories |
| `preventive_guideline` | 268 | Screening/Prevention subcategories |
| `diagnostic_guideline` | 237 | Diagnosis/Workup/Interpretation/Pathophysiology subcategories |
| `rct` | 27 | RCT source types (NEJM, JAMA, Lancet, BMJ, etc.) |

All 1,985 articles have engine_type populated. Classified deterministically from ABFM subcategories + source_type — zero API cost.

## ENGINE_ROLE_MAP

The routing table that converts (engine_type, relevance) → pathway_role:

```
(engine_type, relevance)         → pathway_role
──────────────────────────────────────────────────
(preventive_guideline, primary)  → screening_prevention
(preventive_guideline, secondary)→ screening_prevention
(preventive_guideline, related)  → monitoring
(diagnostic_guideline, primary)  → diagnosis
(diagnostic_guideline, secondary)→ diagnosis
(diagnostic_guideline, related)  → referral
(chronic_guideline, primary)     → first_line
(chronic_guideline, secondary)   → monitoring
(chronic_guideline, related)     → special_pops
(acute_protocol, primary)        → first_line
(acute_protocol, secondary)      → second_line
(acute_protocol, related)        → special_pops
(rct, primary)                   → second_line
(rct, secondary)                 → second_line
(rct, related)                   → special_pops
```

## Sample Queries

### All pathway roles for Type 2 Diabetes
```sql
SELECT cp.pathway_role, COUNT(*) AS n_articles,
       GROUP_CONCAT(DISTINCT a.canonical_filename) AS articles
FROM clinical_pathways cp
JOIN articles a ON cp.article_id = a.article_id
WHERE cp.icd10_code LIKE 'E11%'
  AND a.citation_count > 0
GROUP BY cp.pathway_role
ORDER BY cp.pathway_role;
```

### Which conditions have the most complete pathways (most roles covered)?
```sql
SELECT cp.icd10_code, cp.icd10_desc,
       COUNT(DISTINCT cp.pathway_role) AS roles_covered,
       COUNT(DISTINCT cp.article_id) AS n_articles
FROM clinical_pathways cp
JOIN articles a ON cp.article_id = a.article_id
WHERE a.citation_count > 0
GROUP BY cp.icd10_code, cp.icd10_desc
HAVING roles_covered >= 4
ORDER BY roles_covered DESC, n_articles DESC
LIMIT 20;
```

### Pathway role distribution by engine type (via articles join)
```sql
SELECT a.engine_type, cp.pathway_role, COUNT(*) AS n
FROM clinical_pathways cp
JOIN articles a ON cp.article_id = a.article_id
GROUP BY a.engine_type, cp.pathway_role
ORDER BY a.engine_type, n DESC;
```

### Source bank distribution for a condition
```sql
SELECT cp.source_bank, cp.pathway_role, COUNT(*) AS n_articles
FROM clinical_pathways cp
WHERE cp.icd10_code LIKE 'I10%'
GROUP BY cp.source_bank, cp.pathway_role
ORDER BY cp.pathway_role, cp.source_bank;
```

## Readable CSV Files

| File | Rows | Content |
|------|------|---------|
| `layer3_pathways_by_article.csv` | 1,366 | One row per article with engine_type + pathway_role summary |
| `layer3_pathways_by_code_role.csv` | 2,712 | Grouped by (icd10_code, pathway_role) with article counts |
| `layer3_pathways_by_parent_code.csv` | 1,804 | Rolled up to 3-char parent codes |
| `layer3_pathways_full_detail.csv` | 4,528 | Every row from clinical_pathways table |

Location: `abfm_prep/02_ite_intelligence/readable_db_files/`
