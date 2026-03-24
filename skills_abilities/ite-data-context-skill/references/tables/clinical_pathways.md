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
| `engine_type` | TEXT | Article's engine classification |
| `relevance` | TEXT | primary / secondary / related (from article_icd10) |
| `confidence` | TEXT | Match confidence level |

**Row count**: 4,528
**Built by**: `build_clinical_pathways.py` (zero API calls)

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

## Articles.engine_type Column

Added in Layer 3 build. Classifies each article into one of 5 engine types:

| Engine Type | Count | Classification Source |
|-------------|-------|---------------------|
| `preventive_guideline` | ~200 | Screening/Prevention subcategories |
| `diagnostic_guideline` | ~250 | Diagnosis/Workup/Interpretation/Pathophysiology subcategories |
| `chronic_guideline` | ~350 | Prognosis/Counseling + Pharmacology/Management with chronic categories |
| `acute_protocol` | ~300 | Treatment + Pharmacology/Management with acute categories |
| `rct` | ~250 | RCT source types (NEJM, JAMA, Lancet, BMJ, etc.) |

1,366 articles classified, 31 NULL (non-cited stubs with no linked questions).

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

### Pathway role distribution by engine type
```sql
SELECT engine_type, pathway_role, COUNT(*) AS n
FROM clinical_pathways
GROUP BY engine_type, pathway_role
ORDER BY engine_type, n DESC;
```

## Readable CSV Files

| File | Rows | Content |
|------|------|---------|
| `layer3_pathways_by_article.csv` | 1,366 | One row per article with engine_type + pathway_role summary |
| `layer3_pathways_by_code_role.csv` | 2,712 | Grouped by (icd10_code, pathway_role) with article counts |
| `layer3_pathways_by_parent_code.csv` | 1,804 | Rolled up to 3-char parent codes |
| `layer3_pathways_full_detail.csv` | 4,528 | Every row from clinical_pathways table |

Location: `abfm_prep/02_ite_intelligence/readable_db_files/`
