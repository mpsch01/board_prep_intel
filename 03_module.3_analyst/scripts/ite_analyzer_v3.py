#!/usr/bin/env python3
"""
ite_analyzer_v3.py — ITE Score Analyzer v3 — Full Rebuild

Connected to every DB layer. Both question banks. Clinical pathway context.

ANALYSIS LAYERS:
  1. Basic Performance       — blueprint × body_system × cross-tab
  2. Difficulty Profiling    — easy/mid/hard miss tiers (by item score)
  3. Concept Clustering      — diagnoses + drugs from concept_tags (replaces dropped subcategory)
  4. Spatial Clustering      — consecutive miss runs, subcol concentration
  5. Cross-Dimensional       — blueprint gap, difficulty inversion, diffuse weakness
  6. Yield-Weighted Priority — recoverable points ranking (drives Q selection)
  7. ICD-10 Weakness Map     — direct via question_icd10 + aafp_question_icd10
  8. Pathway Gap Map         — ICD-10 weak codes → clinical_pathways roles (NEW)
  9. Thresholds              — FMCE pass probability, percentile, SEM-aware

PRACTICE QUESTION ENGINE v3:
  Source:  questions (ITE) + aafp_questions (AAFP BRQ) — both banks
  Tier 1:  Direct blueprint + body_system match
  Tier 2:  ICD-10 sibling match via question_icd10 / aafp_question_icd10
  Tier 3:  Vector similarity via question_icd10_vec (cosine distance)
  Ranking: Global relevance score across all candidates — best question wins
  Labels:  "ITE {year}" or "AAFP BRQ" on every question

Changes from v2:
  - subcategory_decomposition() REMOVED (column dropped) → concept_clustering()
  - ICD-10 map now uses question_icd10 directly (not qid_art_xref chain)
  - pathway_gap_map() added — NEW
  - Practice Q matching rebuilt: global ranking, both banks, vector Tier 3
  - Year no longer hardcoded — parsed from score report
  - Tier 2 redesigned: ICD-10 sibling replaces subcategory fingerprint
"""

import json
import math
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH      = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DIFFICULTY_TIERS = {
    "easy_miss":  {"min_score": 700, "label": "Easy Miss (≥700)",  "interpretation": "Most examinees get these right — genuine knowledge gap, highest priority"},
    "mid_range":  {"min_score": 300, "max_score": 699, "label": "Mid-Range (300–699)", "interpretation": "High-yield study targets — greatest ROI"},
    "hard_miss":  {"max_score": 299, "label": "Hard Miss (<300)",  "interpretation": "Most examinees miss these — low-yield to chase"},
}

# Tier weights for practice question relevance scoring
TIER_WEIGHT = {1: 3.0, 2: 2.0, 3: 1.0}

# Minimum AAFP BRQ questions guaranteed in every practice set.
# ITE questions dominate by volume (1,629 vs 1,221), so a floor ensures
# AAFP content is always represented.  Set to 0 to disable the quota.
AAFP_MIN_QUESTIONS = 4

# Vector bonus weights — additive on top of base relevance_score.
# Applied after the full candidate pool is assembled.
# Set CONCEPT_VEC_BONUS_WEIGHT = 0 to disable semantic bonus (e.g., for debugging).
CONCEPT_VEC_BONUS_WEIGHT = 0.8    # max semantic-sim bonus per candidate (cosine ∈ [0,1] × weight)
CENTROID_BOOST_MIN       = 0.90   # minimum cross_tab priority multiplier from centroid sim
CENTROID_BOOST_MAX       = 1.20   # maximum cross_tab priority multiplier from centroid sim

# Pathway role → plain-English gap description
PATHWAY_ROLE_INTERP = {
    "first_line":            "treatment selection gap",
    "second_line":           "escalation therapy gap",
    "monitoring":            "follow-up and titration gap",
    "screening_prevention":  "preventive care gap",
    "referral":              "referral criteria gap",
    "special_pops":          "special populations gap",
    "diagnosis":             "diagnostic workup gap",
}

# ---------------------------------------------------------------------------
# Concept normalization — deduplicates synonym/case variants before counting
# ---------------------------------------------------------------------------

# Lowercase key → canonical display-form value.
# Extend as new API-generated variants are observed in concept_tags.
CONCEPT_SYNONYMS: dict = {
    # Diabetes — T2
    "type 2 dm":                             "Type 2 Diabetes Mellitus",
    "type 2 diabetes":                       "Type 2 Diabetes Mellitus",
    "type 2 diabetes mellitus":              "Type 2 Diabetes Mellitus",
    "t2dm":                                  "Type 2 Diabetes Mellitus",
    "diabetes mellitus type 2":              "Type 2 Diabetes Mellitus",
    "dm type 2":                             "Type 2 Diabetes Mellitus",
    "dm2":                                   "Type 2 Diabetes Mellitus",
    # Diabetes — T1
    "type 1 dm":                             "Type 1 Diabetes Mellitus",
    "type 1 diabetes":                       "Type 1 Diabetes Mellitus",
    "type 1 diabetes mellitus":              "Type 1 Diabetes Mellitus",
    "t1dm":                                  "Type 1 Diabetes Mellitus",
    # Hypertension
    "htn":                                   "Hypertension",
    "hypertension":                          "Hypertension",
    "high blood pressure":                   "Hypertension",
    "arterial hypertension":                 "Hypertension",
    # Heart failure
    "chf":                                   "Heart Failure",
    "congestive heart failure":              "Heart Failure",
    "heart failure":                         "Heart Failure",
    # COPD
    "chronic obstructive pulmonary disease": "COPD",
    "copd":                                  "COPD",
    # CKD
    "ckd":                                   "Chronic Kidney Disease",
    "chronic renal disease":                 "Chronic Kidney Disease",
    "chronic renal failure":                 "Chronic Kidney Disease",
    "renal insufficiency":                   "Chronic Kidney Disease",
    "chronic kidney disease":                "Chronic Kidney Disease",
    # CAD / IHD
    "coronary artery disease":               "Coronary Artery Disease",
    "cad":                                   "Coronary Artery Disease",
    "ischemic heart disease":                "Coronary Artery Disease",
    "ihd":                                   "Coronary Artery Disease",
    # Atrial fibrillation
    "a-fib":                                 "Atrial Fibrillation",
    "afib":                                  "Atrial Fibrillation",
    "atrial fibrillation":                   "Atrial Fibrillation",
    # Asthma
    "asthma":                                "Asthma",
    "reactive airway disease":               "Asthma",
    # Obesity
    "obesity":                               "Obesity",
    "overweight/obesity":                    "Obesity",
    # Hypothyroid
    "hypothyroid":                           "Hypothyroidism",
    "hypothyroidism":                        "Hypothyroidism",
    # GERD
    "gerd":                                  "GERD",
    "gastroesophageal reflux disease":       "GERD",
    "acid reflux":                           "GERD",
    # Depression
    "mdd":                                   "Major Depressive Disorder",
    "major depression":                      "Major Depressive Disorder",
    "major depressive disorder":             "Major Depressive Disorder",
    "depression":                            "Major Depressive Disorder",
    # Dyslipidemia
    "dyslipidemia":                          "Dyslipidemia",
    "hyperlipidemia":                        "Dyslipidemia",
    "hypercholesterolemia":                  "Dyslipidemia",
    # Corticosteroids — prednisone, dexamethasone, methylprednisolone etc.
    "prednisone":                            "Corticosteroids",
    "prednisolone":                          "Corticosteroids",
    "methylprednisolone":                    "Corticosteroids",
    "dexamethasone":                         "Corticosteroids",
    "budesonide":                            "Corticosteroids",
    "fluticasone":                           "Corticosteroids",
    "corticosteroid":                        "Corticosteroids",
    "corticosteroids":                       "Corticosteroids",
    "oral corticosteroids":                  "Corticosteroids",
    "systemic corticosteroids":              "Corticosteroids",
    # -- Guidelines noise --
    # AAFP variants (Claude frequently generates these as "guidelines")
    "aafp":                                  "AAFP",
    "aafp board review":                     "AAFP",
    "aafp family medicine board review":     "AAFP",
    "american academy of family physicians": "AAFP",
    "aafp guidelines":                       "AAFP",
    "aafp 2023":                             "AAFP",
    "aafp 2022":                             "AAFP",
    "aafp 2021":                             "AAFP",
    "aafp 2020":                             "AAFP",
    "aafp 2019":                             "AAFP",
    # ACC/AHA ordering
    "aha/acc":                               "ACC/AHA",
    "aha/acc 2017":                          "ACC/AHA 2017",
    "aha/acc 2018":                          "ACC/AHA 2018",
    "aha/acc 2019":                          "ACC/AHA 2019",
    "aha/acc 2021":                          "ACC/AHA 2021",
    "aha/acc 2022":                          "ACC/AHA 2022",
    "aha/acc 2023":                          "ACC/AHA 2023",
}


def _normalize_concept(name: str) -> str:
    """
    Return canonical display form of a concept tag name.
    - Strips whitespace
    - Resolves known synonym/case variants to a single canonical form
    - Falls back to .title() for unrecognized names so display is consistent
    """
    stripped = name.strip()
    canonical = CONCEPT_SYNONYMS.get(stripped.lower())
    if canonical:
        return canonical
    # No synonym hit — capitalize first letter only (preserves acronyms like HIV, IBS-D)
    # so "prediabetes" and "Prediabetes" land on the same key, while "HIV" stays "HIV".
    return stripped[0].upper() + stripped[1:] if stripped else stripped


# Drug names that may appear in concept_tag "diagnoses" arrays due to tagging
# errors. Any normalized concept key found in this set is reclassified into the
# drugs counter at aggregation time.
KNOWN_DRUGS: set = {
    "metformin", "nsaids", "nsaid", "lisinopril", "corticosteroids",
    "aspirin", "statins", "atorvastatin", "rosuvastatin", "simvastatin",
    "beta blockers", "beta-blockers", "ace inhibitors", "ace inhibitor",
    "angiotensin", "losartan", "amlodipine", "levothyroxine",
    "insulin", "glp-1", "glp1", "sglt2", "sglt-2",
    "warfarin", "apixaban", "rivaroxaban", "clopidogrel",
    "omeprazole", "pantoprazole", "ppis", "ppi",
    "albuterol", "fluticasone",
    "ssri", "ssris", "snri", "snris", "sertraline", "fluoxetine", "escitalopram",
    "antibiotics", "amoxicillin", "azithromycin", "doxycycline",
    "ibuprofen", "naproxen",
    "opioids", "opioid", "naloxone", "buprenorphine",
    "benzodiazepines", "lorazepam", "diazepam",
    "colchicine", "allopurinol", "febuxostat",
}


# Blueprint name mappings (PDF label ↔ DB label)
BLUEPRINT_PDF_TO_DB = {
    "Acute Care":       "Acute Care and Diagnosis",
    "Chronic Care":     "Chronic Care Management",
    "Emergent/Urgent":  "Emergent and Urgent Care",
    "Preventive":       "Preventive Care",
    "Foundations":      "Foundations of Care",
}
BLUEPRINT_DB_TO_PDF = {v: k for k, v in BLUEPRINT_PDF_TO_DB.items()}

# Body system name normalization — maps known PDF/score-report variants to the
# canonical keys used in BODYSYSTEM_PDF_TO_DB. Applied to item body_system fields
# and to body_system_scaled keys from the score report before any analysis runs.
# Extend this when ABFM introduces new naming conventions in future years.
BODYSYSTEM_PDF_NORM = {
    # 2024+ canonical names (identity — already correct)
    "Cardiovascular":            "Cardiovascular",
    "Injuries/Musculoskeletal":  "Injuries/Musculoskeletal",
    "Respiratory":               "Respiratory",
    "Psychiatric/Behavioral":    "Psychiatric/Behavioral",
    "Sexual and Reproductive":   "Sexual and Reproductive",
    "Endocrine":                 "Endocrine",
    "Gastrointestinal":          "Gastrointestinal",
    "Hematologic/Immune":        "Hematologic/Immune",
    "Integumentary":             "Integumentary",
    "Nephrologic":               "Nephrologic",
    "Neurologic":                "Neurologic",
    "Nonspecific":               "Nonspecific",
    "Patient-Based Systems":     "Patient-Based Systems",
    "Population-Based Care":     "Population-Based Care",
    "Special Sensory":           "Special Sensory",
    # Score-report aliases that differ from grid PDF names
    "Musculoskeletal":           "Injuries/Musculoskeletal",  # score report drops "Injuries/"
    "Hematologic/ Immune":       "Hematologic/Immune",        # space variant
    "Psychogenic":               "Psychiatric/Behavioral",    # DB-side name in older reports
    "Reproductive: Female":      "Sexual and Reproductive",   # score report split form
    "Reproductive: Male":        "Sexual and Reproductive",   # score report split form
}


def _normalize_body_system(name: str) -> str:
    """Return the canonical BODYSYSTEM_PDF_TO_DB key for any known body system variant."""
    return BODYSYSTEM_PDF_NORM.get(name, name)


# Body system mappings (PDF label → DB names, one-to-many for merged systems)
BODYSYSTEM_PDF_TO_DB = {
    "Cardiovascular":          ["Cardiovascular"],
    "Injuries/Musculoskeletal": ["Musculoskeletal"],
    "Respiratory":             ["Respiratory"],
    "Psychiatric/Behavioral":  ["Psychiatric/Behavioral"],
    "Sexual and Reproductive": ["Reproductive: Female", "Reproductive: Male"],
    "Endocrine":               ["Endocrine"],
    "Gastrointestinal":        ["Gastrointestinal"],
    "Hematologic/Immune":      ["Hematologic/ Immune"],
    "Integumentary":           ["Integumentary"],
    "Nephrologic":             ["Nephrologic"],
    "Neurologic":              ["Neurologic"],
    "Nonspecific":             ["Nonspecific"],
    "Patient-Based Systems":   ["Patient-Based Systems"],
    "Population-Based Care":   ["Population-Based Care"],
    "Special Sensory":         ["Special Sensory"],
}
BODYSYSTEM_DB_TO_PDF = {}
for pdf_name, db_names in BODYSYSTEM_PDF_TO_DB.items():
    for db_name in db_names:
        BODYSYSTEM_DB_TO_PDF[db_name] = pdf_name

# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

def load_abfm_reference(ref_path: str = None) -> dict:
    if ref_path is None:
        ref_path = Path(__file__).parent / "abfm_reference_2025.json"
    with open(ref_path, encoding="utf-8") as f:
        return json.load(f)

def raw_to_scaled(raw_correct: int, ref: dict) -> int:
    lookup = ref.get("raw_to_scaled_lookup", [])
    if not lookup:
        return 0
    idx = max(0, min(raw_correct, len(lookup) - 1))
    return lookup[idx]

def classify_pass_tier(scaled: int, ref: dict) -> dict:
    tiers = ref.get("pass_probability_tiers", {})
    for tier_name, tier_def in tiers.items():
        lo = tier_def.get("scaled_min", 0)
        hi = tier_def.get("scaled_max", 9999)
        if lo <= scaled <= hi:
            return {"tier": tier_name, "description": tier_def["description"], "scaled": scaled}
    return {"tier": "unknown", "description": "", "scaled": scaled}

# ---------------------------------------------------------------------------
# QID mapping utility
# ---------------------------------------------------------------------------

def build_qid_map(items: list, exam_year) -> dict:
    """Map item numbers → QID strings. Year from parsed score report."""
    return {i["item"]: f"QID-{exam_year}-{i['item']:04d}" for i in items}

# ---------------------------------------------------------------------------
# Vector helpers (for Tier 3)
# ---------------------------------------------------------------------------

def _blob_to_vec(blob: bytes):
    try:
        import numpy as np
        return np.frombuffer(blob, dtype=np.float32).copy()
    except ImportError:
        return None

def _cosine_similarity(a, b) -> float:
    try:
        import numpy as np
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))
    except Exception:
        return 0.0

# ---------------------------------------------------------------------------
# LAYER 1: Basic Performance
# ---------------------------------------------------------------------------

def basic_performance(items: list) -> dict:
    """Per-dimension performance rates and cross-tab."""
    def _dim_perf(items_list, key):
        groups = defaultdict(lambda: {"correct": 0, "total": 0})
        for i in items_list:
            val = i.get(key)
            if val is None:
                continue
            groups[val]["total"] += 1
            if i["correct"]:
                groups[val]["correct"] += 1
        return {
            k: {"correct": v["correct"], "total": v["total"],
                "rate": round(v["correct"] / v["total"], 3) if v["total"] else 0}
            for k, v in sorted(groups.items())
        }

    total   = len(items)
    correct = sum(1 for i in items if i["correct"])
    blueprint   = _dim_perf(items, "blueprint")
    body_system = _dim_perf([i for i in items if i.get("body_system")], "body_system")

    cross_tab = defaultdict(lambda: {"correct": 0, "total": 0})
    for i in items:
        # Use body_system_merged (normalized) for consistent keys across ITE + AAFP
        bsm = i.get("body_system_merged") or i.get("body_system")
        if bsm and i.get("blueprint"):
            key = f"{bsm} × {i['blueprint']}"
            cross_tab[key]["total"] += 1
            if i["correct"]:
                cross_tab[key]["correct"] += 1

    cross_tab = {
        k: {**v, "rate": round(v["correct"] / v["total"], 3) if v["total"] else 0}
        for k, v in sorted(cross_tab.items())
    }

    return {
        "overall": {
            "total": total, "correct": correct, "incorrect": total - correct,
            "pct": round(correct / total * 100, 1) if total else 0,
        },
        "blueprint":   blueprint,
        "body_system": body_system,
        "cross_tab":   cross_tab,
    }

# ---------------------------------------------------------------------------
# LAYER 2: Difficulty Profiling
# ---------------------------------------------------------------------------

def difficulty_profile(items: list, qid_map: dict = None) -> dict:
    missed = [i for i in items if not i["correct"]]

    def _tier(score):
        if score >= 700: return "easy_miss"
        if score >= 300: return "mid_range"
        return "hard_miss"

    overall      = Counter(_tier(i["score"]) for i in missed)
    by_blueprint = defaultdict(Counter)
    by_bodysystem = defaultdict(Counter)

    for i in missed:
        by_blueprint[i.get("blueprint", "Unknown")][_tier(i["score"])] += 1
        if i.get("body_system"):
            by_bodysystem[i["body_system"]][_tier(i["score"])] += 1

    easy_misses = sorted(
        [i for i in missed if i["score"] >= 700],
        key=lambda x: x["score"], reverse=True
    )

    return {
        "overall":        dict(overall),
        "by_blueprint":   {k: dict(v) for k, v in by_blueprint.items()},
        "by_bodysystem":  {k: dict(v) for k, v in by_bodysystem.items()},
        "easy_misses":    [{"item": i["item"], "score": i["score"],
                            "qid": qid_map.get(i["item"]) if qid_map else None,
                            "blueprint": i.get("blueprint"),
                            "body_system": i.get("body_system")} for i in easy_misses],
        "easy_miss_count":  len(easy_misses),
        "mid_range_count":  overall.get("mid_range", 0),
        "hard_miss_count":  overall.get("hard_miss", 0),
        "tier_definitions": DIFFICULTY_TIERS,
    }

# ---------------------------------------------------------------------------
# LAYER 3: Concept Clustering (replaces subcategory decomposition)
# ---------------------------------------------------------------------------

def concept_clustering(items: list, qid_map: dict, db_path: str) -> dict:
    """
    Cluster missed questions by clinical concept: diagnoses, drugs, guidelines.

    Two sources of concept signal:
      1. ITE bank (primary):  concept_tags from the specific ITE questions missed.
         These are the ONLY QIDs stored in concept_qid_map — they point directly
         to the resident's actual exam mistakes.
      2. AAFP bank (additive): concept_tags from AAFP questions in the same weak
         blueprint/body_system areas — broadens the concept frequency counts to
         surface themes the ITE happened not to test this year.  AAFP QIDs are
         NOT added to concept_qid_map (avoids flooding the fingerprint display
         with non-ITE QIDs).

    Normalization: all concept names are passed through _normalize_concept()
    before counting, collapsing common synonym/case variants into a single
    canonical form (e.g. "T2DM", "type 2 diabetes", "DM type 2" → one entry).

    Both banks are 100% concept_tags filled (1,629 ITE + 1,221 AAFP as of 2026-04).
    """
    missed_items  = [i for i in items if not i["correct"]]
    missed_qids   = [qid_map[i["item"]] for i in missed_items if i["item"] in qid_map]

    diagnoses  = Counter()  # combined (Source 1 + Source 2) — used for fingerprint scoring
    drugs      = Counter()
    guidelines = Counter()
    ite_diagnoses  = Counter()  # Source 1 ITE-only — used for display tables
    ite_drugs      = Counter()
    ite_guidelines = Counter()
    items_matched = 0
    aafp_items_matched = 0

    # QID tracking per concept — ITE missed questions ONLY.
    # These feed the fingerprint reference column; capped at 10 per concept.
    ite_dx_qids    = defaultdict(list)
    ite_drug_qids  = defaultdict(list)
    ite_guide_qids = defaultdict(list)

    if missed_qids and db_path:
        db = sqlite3.connect(db_path)
        db.row_factory = sqlite3.Row

        # --- Source 1: ITE questions missed (specific items) ---
        batch_size = 100
        for start in range(0, len(missed_qids), batch_size):
            batch = missed_qids[start:start + batch_size]
            ph = ",".join(["?"] * len(batch))
            rows = db.execute(
                f"SELECT qid, concept_tags FROM questions WHERE qid IN ({ph})", batch
            ).fetchall()
            for row in rows:
                raw  = row["concept_tags"]
                qid  = row["qid"]
                if raw:
                    try:
                        tags = json.loads(raw)
                        for d in tags.get("diagnoses", []):
                            norm = _normalize_concept(d)
                            # Reclassify mistagged drugs into the drugs counter
                            if norm.lower() in KNOWN_DRUGS:
                                drugs[norm] += 1
                                ite_drugs[norm] += 1
                                if len(ite_drug_qids[norm]) < 10:
                                    ite_drug_qids[norm].append(qid)
                            else:
                                diagnoses[norm] += 1
                                ite_diagnoses[norm] += 1
                                if len(ite_dx_qids[norm]) < 10:
                                    ite_dx_qids[norm].append(qid)
                        for d in tags.get("drugs", []):
                            norm = _normalize_concept(d)
                            drugs[norm] += 1
                            ite_drugs[norm] += 1
                            if len(ite_drug_qids[norm]) < 10:
                                ite_drug_qids[norm].append(qid)
                        for g in tags.get("guidelines", []):
                            norm = _normalize_concept(g)
                            guidelines[norm] += 1
                            ite_guidelines[norm] += 1
                            if len(ite_guide_qids[norm]) < 10:
                                ite_guide_qids[norm].append(qid)
                        items_matched += 1
                    except (json.JSONDecodeError, TypeError):
                        pass

        # --- Source 2: AAFP questions in weak areas (topical enrichment) ---
        # Enriches concept COUNTS only — QIDs not added to the tracking maps.
        # Collect weak blueprint/body_system DB names from missed items
        weak_blueprints_db = set()
        weak_bs_db = set()
        for i in missed_items:
            if i.get("blueprint"):
                weak_blueprints_db.add(BLUEPRINT_PDF_TO_DB.get(i["blueprint"], i["blueprint"]))
            if i.get("body_system"):
                for db_name in BODYSYSTEM_PDF_TO_DB.get(i["body_system"], [i["body_system"]]):
                    weak_bs_db.add(db_name)

        if weak_blueprints_db or weak_bs_db:
            where_parts, params = [], []
            if weak_blueprints_db:
                ph = ",".join(["?"] * len(weak_blueprints_db))
                where_parts.append(f"blueprint IN ({ph})")
                params.extend(sorted(weak_blueprints_db))
            if weak_bs_db:
                ph = ",".join(["?"] * len(weak_bs_db))
                where_parts.append(f"body_system IN ({ph})")
                params.extend(sorted(weak_bs_db))

            where_sql = " OR ".join(where_parts)
            aafp_rows = db.execute(f"""
                SELECT aafp_qid, concept_tags FROM aafp_questions
                WHERE ({where_sql}) AND concept_tags IS NOT NULL AND concept_tags != ''
                LIMIT 500
            """, params).fetchall()

            for row in aafp_rows:
                raw = row["concept_tags"]
                if raw:
                    try:
                        tags = json.loads(raw)
                        # Count only — no QID tracking for Source 2
                        for d in tags.get("diagnoses", []):
                            norm = _normalize_concept(d)
                            # Reclassify mistagged drugs
                            if norm.lower() in KNOWN_DRUGS:
                                drugs[norm] += 1
                            else:
                                diagnoses[norm] += 1
                        for d in tags.get("drugs", []):
                            drugs[_normalize_concept(d)] += 1
                        for g in tags.get("guidelines", []):
                            guidelines[_normalize_concept(g)] += 1
                        aafp_items_matched += 1
                    except (json.JSONDecodeError, TypeError):
                        pass

        db.close()

    # Recurring themes = appears ≥4 times (lower threshold generated ~170 rows)
    recurring_diagnoses  = {k: v for k, v in diagnoses.items()  if v >= 4}
    recurring_drugs      = {k: v for k, v in drugs.items()      if v >= 4}

    return {
        # ITE-only counts (Source 1 only) — used for display tables so frequencies
        # reflect actual questions this resident missed, not AAFP enrichment noise.
        "top_diagnoses":     dict(ite_diagnoses.most_common(15)),
        "top_drugs":         dict(ite_drugs.most_common(15)),
        "top_guidelines":    dict(ite_guidelines.most_common(10)),
        # Combined counts (Source 1 + Source 2 AAFP enrichment) — used internally
        # by match_practice_questions_v3 for fingerprint-weighted scoring.
        "top_diagnoses_combined": dict(diagnoses.most_common(15)),
        "top_drugs_combined":     dict(drugs.most_common(15)),
        "recurring_diagnoses": dict(sorted(recurring_diagnoses.items(), key=lambda x: x[1], reverse=True)),
        "recurring_drugs":   dict(sorted(recurring_drugs.items(), key=lambda x: x[1], reverse=True)),
        # QID maps — ITE missed questions only; drives fingerprint reference column
        "concept_qid_map": {
            "diagnoses":  dict(ite_dx_qids),
            "drugs":      dict(ite_drug_qids),
            "guidelines": dict(ite_guide_qids),
        },
        "items_matched":        items_matched,
        "aafp_items_matched":   aafp_items_matched,
        "items_queried":        len(missed_qids),
        "coverage_pct":         round(items_matched / len(missed_qids) * 100, 1) if missed_qids else 0,
    }

# ---------------------------------------------------------------------------
# LAYER 4: Spatial Clustering
# ---------------------------------------------------------------------------

def spatial_clustering(items: list) -> dict:
    missed     = [i for i in items if not i["correct"]]
    all_sorted = sorted(items, key=lambda x: x["item"])

    # Subcol concentration per blueprint
    subcol_concentration = {}
    for bp in set(i.get("blueprint") for i in missed if i.get("blueprint")):
        bp_misses = [i for i in missed if i.get("blueprint") == bp]
        subcols   = Counter(i.get("sub_col_index", -1) for i in bp_misses)
        total_m   = len(bp_misses)
        hhi = sum((c / total_m) ** 2 for c in subcols.values()) if total_m else 0
        dominant  = subcols.most_common(1)[0] if subcols else (None, 0)
        subcol_concentration[bp] = {
            "total_misses":   total_m,
            "unique_subcols": len(subcols),
            "herfindahl":     round(hhi, 3),
            "concentrated":   hhi > 0.4,
            "dominant_subcol":  dominant[0],
            "dominant_count":   dominant[1],
        }

    # Consecutive miss runs (≥3)
    runs, current_run = [], []
    for i in all_sorted:
        if not i["correct"]:
            current_run.append(i["item"])
        else:
            if len(current_run) >= 3:
                runs.append(current_run)
            current_run = []
    if len(current_run) >= 3:
        runs.append(current_run)

    miss_scores = [i["score"] for i in missed]
    score_mean = sum(miss_scores) / len(miss_scores) if miss_scores else 0
    score_sd   = (sum((s - score_mean) ** 2 for s in miss_scores) / len(miss_scores)) ** 0.5 if miss_scores else 0

    return {
        "subcol_concentration":   subcol_concentration,
        "consecutive_miss_runs":  runs,
        "longest_run":            max(len(r) for r in runs) if runs else 0,
        "miss_score_mean":        round(score_mean),
        "miss_score_sd":          round(score_sd),
    }

# ---------------------------------------------------------------------------
# LAYER 5: Cross-Dimensional Patterns
# ---------------------------------------------------------------------------

def cross_dimensional_patterns(items: list, perf: dict) -> dict:
    """
    Detect structural patterns within the cross_tab matrix.
    All patterns are derived from the resident's actual cross_tab data,
    not generic thresholds — each observation should differ meaningfully
    between residents.
    """
    patterns     = []
    overall_rate = perf["overall"]["pct"] / 100
    TARGET_RATE  = 0.70

    cross_tab = perf.get("cross_tab", {})
    if not cross_tab:
        return {"patterns": [], "accuracy_by_difficulty_band": {}}

    # Build per-axis weak-intersection maps
    # weak = rate < TARGET_RATE and at least 3 questions at that intersection
    weak_cells = {
        k: v for k, v in cross_tab.items()
        if v["rate"] < TARGET_RATE and v["total"] >= 3
    }

    # ── Pattern 1: Body system axis collapse ───────────────────────────────
    # A body system appearing weak in 2+ blueprint categories = systemic content gap
    bs_weak_blueprints = defaultdict(list)
    for key in weak_cells:
        parts = key.split(" × ", 1)
        if len(parts) == 2:
            bs, bp = parts
            bs_weak_blueprints[bs].append(bp)

    for bs, blueprints in sorted(bs_weak_blueprints.items(), key=lambda x: -len(x[1])):
        if len(blueprints) >= 2:
            bp_list = ", ".join(sorted(blueprints))
            patterns.append({
                "type":        "body_system_axis_collapse",
                "body_system": bs,
                "blueprints":  blueprints,
                "description": (
                    f"{bs}: weak across {len(blueprints)} blueprint categories "
                    f"({bp_list}). Gap is systemic to this content area, "
                    f"not specific to one care context."
                ),
            })

    # ── Pattern 2: Blueprint axis collapse ─────────────────────────────────
    # A blueprint category appearing weak across 3+ body systems = care-type deficit
    bp_weak_systems = defaultdict(list)
    for key in weak_cells:
        parts = key.split(" × ", 1)
        if len(parts) == 2:
            bs, bp = parts
            bp_weak_systems[bp].append(bs)

    for bp, systems in sorted(bp_weak_systems.items(), key=lambda x: -len(x[1])):
        if len(systems) >= 3:
            sys_list = ", ".join(sorted(systems))
            patterns.append({
                "type":      "blueprint_axis_collapse",
                "blueprint": bp,
                "systems":   systems,
                "description": (
                    f"{bp}: weak in {len(systems)} body systems "
                    f"({sys_list}). Deficit is tied to this care type "
                    f"across multiple content areas."
                ),
            })

    # ── Pattern 3: Concentration ───────────────────────────────────────────
    # Single intersection accounts for disproportionate share of weak cross_tab volume
    if weak_cells:
        total_weak_items = sum(v["total"] for v in weak_cells.values())
        top_key   = max(weak_cells, key=lambda k: weak_cells[k]["total"])
        top_count = weak_cells[top_key]["total"]
        top_share = top_count / total_weak_items if total_weak_items else 0
        if top_share >= 0.30 and len(weak_cells) >= 3:
            top_rate = weak_cells[top_key]["rate"]
            patterns.append({
                "type":        "concentration",
                "intersection": top_key,
                "share_pct":   round(top_share * 100, 0),
                "description": (
                    f"{top_key}: accounts for {top_share*100:.0f}% of all weak "
                    f"cross-intersection volume ({top_count} items, "
                    f"{top_rate*100:.0f}% accuracy). "
                    f"Concentrated gap — high-leverage study target."
                ),
            })

    # ── Difficulty calibration (kept — uses individual item scores) ────────
    bands = defaultdict(lambda: {"correct": 0, "total": 0})
    for i in items:
        band = (i["score"] // 200) * 200
        bands[band]["total"] += 1
        if i["correct"]:
            bands[band]["correct"] += 1

    band_rates = {}
    for band in sorted(bands.keys()):
        c = bands[band]
        if c["total"] >= 3:
            band_rates[band] = round(c["correct"] / c["total"], 3)

    easy_rate = band_rates.get(800, band_rates.get(1000, None))
    mid_rate  = band_rates.get(400, band_rates.get(600, None))
    # Only flag if inversion is substantial (>10 pts) to avoid noise
    if easy_rate is not None and mid_rate is not None and (mid_rate - easy_rate) > 0.10:
        patterns.append({
            "type":        "difficulty_inversion",
            "easy_rate":   easy_rate,
            "mid_rate":    mid_rate,
            "description": (
                f"Easy items ({easy_rate*100:.0f}%) answered less accurately than "
                f"mid-difficulty ({mid_rate*100:.0f}%). "
                f"Possible second-guessing or over-reading on straightforward presentations."
            ),
        })

    return {
        "patterns":                    patterns,
        "accuracy_by_difficulty_band": band_rates,
    }

# ---------------------------------------------------------------------------
# LAYER 6: Yield-Weighted Priorities
# ---------------------------------------------------------------------------

def yield_weighted_priorities(perf: dict, ref: dict) -> list:
    TARGET_RATE = 0.70
    priorities  = []

    for name, p in perf.get("blueprint", {}).items():
        if p["rate"] < TARGET_RATE:
            gap         = TARGET_RATE - p["rate"]
            recoverable = round(gap * p["total"], 1)
            full_name   = BLUEPRINT_PDF_TO_DB.get(name, name)
            weight_pct  = ref.get("blueprint_weights", {}).get(full_name, {}).get("pct", 10)
            priorities.append({
                "dimension":        name,
                "dimension_type":   "blueprint",
                "current_rate":     p["rate"],
                "target_rate":      TARGET_RATE,
                "item_count":       p["total"],
                "recoverable_items": recoverable,
                "exam_weight_pct":  weight_pct,
                "priority_score":   round(recoverable * (weight_pct / 10), 2),
            })

    for name, p in perf.get("body_system", {}).items():
        if p["rate"] < TARGET_RATE:
            gap         = TARGET_RATE - p["rate"]
            recoverable = round(gap * p["total"], 1)
            sem         = ref.get("bodysystem_sem_page1", {}).get(name, 999)
            meaningful  = p["total"] >= 8
            priorities.append({
                "dimension":        name,
                "dimension_type":   "body_system",
                "current_rate":     p["rate"],
                "target_rate":      TARGET_RATE,
                "item_count":       p["total"],
                "recoverable_items": recoverable,
                "sem":              sem,
                "statistically_meaningful": meaningful,
                "priority_score":   round(recoverable * (2 if meaningful else 0.5), 2),
            })

    # cross_tab: use empirical qbank intersection weights from reference JSON
    # Keys match body_system_merged × blueprint (normalized, consistent across banks)
    ite_ct_ref  = ref.get("ite_crosstab_weights", {})
    aafp_ct_ref = ref.get("aafp_crosstab_weights", {})
    for key, p in perf.get("cross_tab", {}).items():
        if p["rate"] < TARGET_RATE and p["total"] >= 3:
            gap         = TARGET_RATE - p["rate"]
            recoverable = round(gap * p["total"], 1)
            # Prefer ITE weight; fall back to AAFP weight; fall back to 2.0 default
            ct_entry    = ite_ct_ref.get(key) or aafp_ct_ref.get(key) or {}
            weight_pct  = ct_entry.get("pct", 2.0)
            priorities.append({
                "dimension":         key,
                "dimension_type":    "cross_tab",
                "current_rate":      p["rate"],
                "target_rate":       TARGET_RATE,
                "item_count":        p["total"],
                "recoverable_items": recoverable,
                "exam_weight_pct":   round(weight_pct, 1),
                "priority_score":    round(recoverable * (weight_pct / 10), 2),
            })

    priorities.sort(key=lambda x: x["priority_score"], reverse=True)
    return priorities

# ---------------------------------------------------------------------------
# LAYER 7: ICD-10 Weakness Map (direct — no qid_art_xref chain)
# ---------------------------------------------------------------------------

def icd10_weakness_map(items: list, qid_map: dict, db_path: str) -> dict:
    """
    Map missed questions directly to ICD-10 codes via question_icd10.
    Faster and more accurate than the v2 indirect chain through articles.
    Covers both ITE (question_icd10) and future AAFP expansion.
    Also rolls up to ICD-10 chapter level via icd10_rollup.
    """
    missed_qids = [qid_map[i["item"]] for i in items
                   if not i["correct"] and i["item"] in qid_map]

    if not missed_qids or not db_path:
        return {"icd10_clusters": [], "chapter_summary": {}, "total_codes_found": 0}

    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row

    icd10_counts  = Counter()
    code_details  = {}
    chapter_counts = Counter()

    batch_size = 100
    for start in range(0, len(missed_qids), batch_size):
        batch = missed_qids[start:start + batch_size]
        ph    = ",".join(["?"] * len(batch))
        rows  = db.execute(f"""
            SELECT qi.qid, qi.icd10_code, qi.icd10_desc, qi.relevance,
                   ir.chapter, ir.chapter_desc
            FROM question_icd10 qi
            LEFT JOIN icd10_rollup ir
                   ON SUBSTR(qi.icd10_code, 1, 3) = ir.parent_code
            WHERE qi.qid IN ({ph})
              AND qi.relevance IN ('primary', 'secondary')
              AND qi.icd10_code != 'no_match'
        """, batch).fetchall()

        for row in rows:
            code = row["icd10_code"]
            icd10_counts[code] += 1
            if code not in code_details:
                code_details[code] = {
                    "description":  row["icd10_desc"],
                    "relevance":    row["relevance"],
                    "chapter":      row["chapter"],
                    "chapter_desc": row["chapter_desc"],
                }
            if row["chapter"]:
                chapter_counts[row["chapter"]] += 1

    db.close()

    return {
        "icd10_clusters": [
            {"code": code, "miss_count": count, **code_details.get(code, {})}
            for code, count in icd10_counts.most_common(20)
            if count >= 2  # suppress single-miss noise
        ],
        "chapter_summary":   dict(chapter_counts.most_common()),
        "total_codes_found": len(icd10_counts),
        "questions_mapped":  len(missed_qids),
    }

# ---------------------------------------------------------------------------
# LAYER 8: Pathway Gap Map (NEW)
# ---------------------------------------------------------------------------

def pathway_gap_map(icd10_map_result: dict, db_path: str, top_n: int = 8) -> dict:
    """
    For the top weak ICD-10 codes, query clinical_pathways to show which
    guideline roles are populated. Tells the resident not just WHERE they're
    weak but WHAT KIND of gap it is.

    Example output for E11 (T2DM):
      first_line: 34 articles — treatment selection gap
      monitoring: 29 articles — follow-up and titration gap
      ...
    """
    clusters = icd10_map_result.get("icd10_clusters", [])[:top_n]
    if not clusters or not db_path:
        return {"pathway_gaps": [], "status": "no_data"}

    top_codes = [c["code"] for c in clusters]
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row

    ph   = ",".join(["?"] * len(top_codes))
    rows = db.execute(f"""
        SELECT cp.icd10_code,
               COALESCE(q.icd10_desc, cp.icd10_code) AS icd10_desc,
               cp.pathway_role,
               COUNT(DISTINCT cp.article_id) AS article_count
        FROM clinical_pathways cp
        LEFT JOIN (
            SELECT DISTINCT icd10_code, icd10_desc
            FROM question_icd10
            WHERE icd10_desc IS NOT NULL
        ) q ON cp.icd10_code = q.icd10_code
        WHERE cp.icd10_code IN ({ph})
        GROUP BY cp.icd10_code, cp.pathway_role
        ORDER BY cp.icd10_code, article_count DESC
    """, top_codes).fetchall()

    db.close()

    # Group by ICD-10 code
    by_code = defaultdict(dict)
    code_desc = {}
    for row in rows:
        code = row["icd10_code"]
        role = row["pathway_role"]
        by_code[code][role] = row["article_count"]
        code_desc[code] = row["icd10_desc"]

    # Build gap entries
    pathway_gaps = []
    for cluster in clusters:
        code       = cluster["code"]
        miss_count = cluster["miss_count"]
        roles      = by_code.get(code, {})

        if not roles:
            continue

        # Dominant role = most articles
        dominant_role = max(roles, key=roles.get)
        interpretation = PATHWAY_ROLE_INTERP.get(dominant_role, dominant_role)

        pathway_gaps.append({
            "icd10_code":     code,
            "description":    cluster.get("description", code_desc.get(code, "")),
            "miss_count":     miss_count,
            "chapter":        cluster.get("chapter"),
            "chapter_desc":   cluster.get("chapter_desc"),
            "pathway_roles":  dict(sorted(roles.items(), key=lambda x: x[1], reverse=True)),
            "dominant_role":  dominant_role,
            "interpretation": interpretation,
            "summary": (
                f"{miss_count} missed question{'s' if miss_count != 1 else ''} — "
                f"{dominant_role} ({roles[dominant_role]} guidelines) — {interpretation}"
            ),
        })

    return {
        "pathway_gaps": pathway_gaps,
        "codes_mapped": len(pathway_gaps),
        "status": "complete",
    }

# ---------------------------------------------------------------------------
# LAYER 9: Thresholds
# ---------------------------------------------------------------------------

def compute_thresholds(perf: dict, ref: dict, pgy_level: str = "All") -> dict:
    overall   = perf["overall"]
    scaled    = raw_to_scaled(overall["correct"], ref)
    pass_tier = classify_pass_tier(scaled, ref)

    benchmark     = ref.get("national_benchmarks", {}).get(pgy_level, {})
    national_mean = benchmark.get("mean_scaled", 434)
    national_sd   = benchmark.get("sd", 85)
    percentile_est = None
    if national_sd > 0:
        z = (scaled - national_mean) / national_sd
        percentile_est = round(50 * (1 + math.erf(z / math.sqrt(2))), 1)

    all_rates = (
        [p["rate"] for p in perf.get("blueprint", {}).values()]
        + [p["rate"] for p in perf.get("body_system", {}).values()]
    )
    if all_rates:
        personal_mean = sum(all_rates) / len(all_rates)
        personal_sd   = (sum((r - personal_mean) ** 2 for r in all_rates) / len(all_rates)) ** 0.5
    else:
        personal_mean = overall["pct"] / 100
        personal_sd   = 0.1

    dimension_classifications = {}
    for dim_type in ["blueprint", "body_system"]:
        for name, p in perf.get(dim_type, {}).items():
            if p["rate"] < personal_mean - personal_sd:
                cls = "relative_weakness"
            elif p["rate"] > personal_mean + personal_sd:
                cls = "relative_strength"
            else:
                cls = "within_range"
            dimension_classifications[name] = {
                "rate": p["rate"], "classification": cls, "items": p["total"],
            }

    sem_flags = {}
    for name in perf.get("blueprint", {}):
        full_name = BLUEPRINT_PDF_TO_DB.get(name, name)
        sem = ref.get("blueprint_sem", {}).get(full_name)
        if sem:
            sem_flags[name] = {"sem": sem, "reliable": sem <= 100,
                                "note": "Statistically reliable" if sem <= 100 else "Large SEM — interpret as hypothesis only"}
    for name in perf.get("body_system", {}):
        sem = ref.get("bodysystem_sem_page1", {}).get(name)
        if sem:
            sem_flags[name] = {"sem": sem, "reliable": sem <= 150,
                                "note": "Statistically reliable" if sem <= 150 else "Large SEM — interpret as hypothesis only"}

    return {
        "tier1_pass_probability": {
            "scaled_score":     scaled,
            "pass_tier":        pass_tier,
            "national_mean":    national_mean,
            "national_sd":      national_sd,
            "percentile_estimate": percentile_est,
            "vs_mps": scaled - ref.get("exam_specs", {}).get("minimum_passing_standard", 380),
        },
        "tier2_relative": {
            "thresholds": {
                "personal_mean":      round(personal_mean, 3),
                "personal_sd":        round(personal_sd, 3),
                "relative_weakness":  round(personal_mean - personal_sd, 3),
                "relative_strength":  round(personal_mean + personal_sd, 3),
            },
            "classifications": dimension_classifications,
        },
        "tier3_sem": sem_flags,
    }

# ---------------------------------------------------------------------------
# PRACTICE QUESTION ENGINE v3
# ---------------------------------------------------------------------------

# Shared column spec — normalized across both banks
# ITE:  question_text, qid, exam_year
# AAFP: stem AS question_text, aafp_qid AS qid, NULL AS exam_year

_ITE_Q_COLS = """
    q.qid                    AS qid,
    'ITE'                    AS source_bank,
    q.exam_year              AS exam_year,
    q.body_system            AS body_system,
    q.body_system_merged     AS body_system_merged,
    q.blueprint              AS blueprint,
    q.question_text          AS question_text,
    q.choices                AS choices,
    q.correct_letter         AS correct_letter,
    q.correct_text           AS correct_text,
    q.explanation            AS explanation,
    q.reference              AS reference,
    q.concept_tags           AS concept_tags
"""

_AAFP_Q_COLS = """
    q.aafp_qid               AS qid,
    'AAFP'                   AS source_bank,
    NULL                     AS exam_year,
    q.body_system            AS body_system,
    q.body_system            AS body_system_merged,
    q.blueprint              AS blueprint,
    q.stem                   AS question_text,
    q.choices                AS choices,
    q.correct_letter         AS correct_letter,
    q.correct_text           AS correct_text,
    q.explanation            AS explanation,
    NULL                     AS reference,
    q.concept_tags           AS concept_tags
"""


def _not_in(selected_qids: set, col: str = "q.qid") -> tuple:
    if not selected_qids:
        return ("", [])
    ph = ",".join(["?"] * len(selected_qids))
    return (f"AND {col} NOT IN ({ph})", list(selected_qids))


def _row_to_dict(row, targeting: str, match_tier: int,
                 linked_articles: int, relevance_score: float) -> dict:
    source_bank = row["source_bank"]
    exam_year   = row["exam_year"]
    source_label = f"ITE {exam_year}" if source_bank == "ITE" and exam_year else "AAFP BRQ"
    return {
        "qid":              row["qid"],
        "source_bank":      source_bank,
        "source_label":     source_label,
        "exam_year":        exam_year,
        "body_system":      row["body_system"],
        "body_system_merged": row["body_system_merged"],
        "blueprint":        row["blueprint"],
        "question_text":    row["question_text"],
        "choices":          row["choices"],
        "correct_letter":   row["correct_letter"],
        "correct_text":     row["correct_text"],
        "explanation":      row["explanation"],
        "reference":        row["reference"],
        "concept_tags":     row["concept_tags"],
        "linked_articles":  linked_articles,
        "targeting":        targeting,
        "match_tier":       match_tier,
        "relevance_score":  round(relevance_score, 3),
    }


def _compute_relevance(match_tier: int, priority_score: float,
                       linked_articles: int, exam_year,
                       has_concept_tags: bool) -> float:
    """
    Global relevance score — determines final ranking across all candidates.
    Higher = more relevant to the resident's specific weakness.
    """
    score = TIER_WEIGHT[match_tier] * max(priority_score, 0.1)

    # Bonus: question has linked guideline articles
    if linked_articles and linked_articles > 0:
        score += 0.5

    # Bonus: question has concept tags (richer for study)
    if has_concept_tags:
        score += 0.3

    return score


def _tier1_direct(db, dim: str, dim_type: str, priority_score: float,
                  selected_qids: set, limit: int = 200) -> list:
    """
    Direct blueprint + body_system match from both banks.

    Candidate pool: 200 per bank (was 60), ordered by exam_year DESC (most recent
    content first — neutral with respect to article counts).  Concept-fingerprint
    relevance boosting happens in match_practice_questions_v3() as a Python-side
    post-processing step so that article count does not gate which questions enter
    the candidate pool at all.
    """
    candidates = []

    def _build_where(table_prefix, use_merged):
        where_parts = ["q.question_text IS NOT NULL AND q.question_text != ''"]
        params = []
        if dim_type == "blueprint":
            db_bp = BLUEPRINT_PDF_TO_DB.get(dim, dim)
            where_parts.append("q.blueprint = ?")
            params.append(db_bp)
        elif dim_type == "body_system":
            db_names = BODYSYSTEM_PDF_TO_DB.get(dim, [dim])
            ph = ",".join(["?"] * len(db_names))
            if use_merged:
                where_parts.append(f"(q.body_system_merged IN ({ph}) OR q.body_system IN ({ph}))")
                params.extend(db_names * 2)
            else:
                where_parts.append(f"q.body_system IN ({ph})")
                params.extend(db_names)
        elif dim_type == "cross_tab":
            parts = dim.split(" × ", 1)
            if len(parts) == 2:
                bs_part, bp_part = parts
                db_names = BODYSYSTEM_PDF_TO_DB.get(bs_part, [bs_part])
                db_bp    = BLUEPRINT_PDF_TO_DB.get(bp_part, bp_part)
                bs_ph    = ",".join(["?"] * len(db_names))
                if use_merged:
                    where_parts.append(f"(q.body_system_merged IN ({bs_ph}) OR q.body_system IN ({bs_ph}))")
                    params.extend(db_names * 2)
                else:
                    where_parts.append(f"q.body_system IN ({bs_ph})")
                    params.extend(db_names)
                where_parts.append("q.blueprint = ?")
                params.append(db_bp)
        return where_parts, params

    excl_sql, excl_params = _not_in(selected_qids)

    # ITE bank — ordered by exam_year DESC (neutral; concept/fingerprint scoring
    # applied in Python post-processing, not at the SQL fetch layer)
    ite_where, ite_params = _build_where("q", use_merged=True)
    sql_ite = f"""
        SELECT {_ITE_Q_COLS},
               COUNT(DISTINCT xa.article_id) AS linked_articles
        FROM questions q
        LEFT JOIN qid_art_xref xa ON q.qid = xa.qid AND xa.article_id != 'ART-0001'
        WHERE {" AND ".join(ite_where)} {excl_sql}
        GROUP BY q.qid
        ORDER BY q.exam_year DESC
        LIMIT ?
    """
    for row in db.execute(sql_ite, ite_params + excl_params + [limit]).fetchall():
        rs = _compute_relevance(1, priority_score, row["linked_articles"],
                                row["exam_year"], bool(row["concept_tags"]))
        candidates.append(_row_to_dict(row, dim, 1, row["linked_articles"] or 0, rs))

    # AAFP bank
    aafp_excl_sql, aafp_excl_params = _not_in(selected_qids, "q.aafp_qid")
    aafp_where, aafp_params = _build_where("q", use_merged=False)
    # AAFP uses stem — remap question_text check
    aafp_where = ["q.stem IS NOT NULL AND q.stem != ''"] + aafp_where[1:]
    sql_aafp = f"""
        SELECT {_AAFP_Q_COLS},
               COUNT(DISTINCT xa.article_id) AS linked_articles
        FROM aafp_questions q
        LEFT JOIN aafp_qid_art_xref xa ON q.aafp_qid = xa.aafp_qid
        WHERE {" AND ".join(aafp_where)} {aafp_excl_sql}
        GROUP BY q.aafp_qid
        ORDER BY linked_articles DESC
        LIMIT ?
    """
    for row in db.execute(sql_aafp, aafp_params + aafp_excl_params + [limit]).fetchall():
        rs = _compute_relevance(1, priority_score, row["linked_articles"],
                                None, bool(row["concept_tags"]))
        candidates.append(_row_to_dict(row, dim, 1, row["linked_articles"] or 0, rs))

    return candidates


def _get_wrong_qid_metadata(db, wrong_qids: list) -> dict:
    """
    Pull ICD-10 codes, concept tags, and linked article IDs for a specific
    set of wrong-answer QIDs.  Used to seed the enriched practice question
    matching from the resident's actual missed items rather than broad
    dimension categories.
    Returns: {"icd10_codes": [...], "concept_tags": set(...), "article_ids": [...]}
    """
    if not wrong_qids:
        return {"icd10_codes": [], "concept_tags": set(), "article_ids": []}

    ph = ",".join(["?"] * len(wrong_qids))

    # ICD-10 codes (primary + secondary) from wrong QIDs
    icd_rows = db.execute(f"""
        SELECT DISTINCT icd10_code FROM question_icd10
        WHERE qid IN ({ph}) AND relevance IN ('primary', 'secondary')
    """, wrong_qids).fetchall()
    icd10_codes = [r["icd10_code"] for r in icd_rows]

    # Concept tags — parse JSON arrays stored on the questions
    tag_rows = db.execute(f"""
        SELECT concept_tags FROM questions
        WHERE qid IN ({ph}) AND concept_tags IS NOT NULL AND concept_tags != ''
    """, wrong_qids).fetchall()
    concept_tags: set = set()
    for row in tag_rows:
        try:
            tags = json.loads(row["concept_tags"])
            if isinstance(tags, list):
                concept_tags.update(str(t).strip() for t in tags if t)
        except (json.JSONDecodeError, TypeError):
            pass

    # Linked article IDs from wrong QIDs
    art_rows = db.execute(f"""
        SELECT DISTINCT article_id FROM qid_art_xref
        WHERE qid IN ({ph}) AND article_id != 'ART-0001'
    """, wrong_qids).fetchall()
    article_ids = [r["article_id"] for r in art_rows]

    return {"icd10_codes": icd10_codes, "concept_tags": concept_tags, "article_ids": article_ids}


def _tier1b_richseed(db, meta: dict, dim: str, priority_score: float,
                     selected_qids: set, limit: int = 60) -> list:
    """
    Article co-link matching anchored to wrong-QID metadata.
    Finds practice questions that are linked to the same guideline articles
    as the resident's specific wrong answers in this dimension — more
    topically precise than the broad category query in Tier 1.
    Scored at Tier 1 weight; concept-tag overlap bonus applied downstream.
    """
    candidates = []
    article_ids = list(meta.get("article_ids") or [])
    if not article_ids:
        return []

    art_ph = ",".join(["?"] * len(article_ids))
    excl_sql,      excl_params      = _not_in(selected_qids)
    aafp_excl_sql, aafp_excl_params = _not_in(selected_qids, "q.aafp_qid")

    # ITE: questions sharing articles with wrong QIDs
    sql_ite = f"""
        SELECT {_ITE_Q_COLS},
               COUNT(DISTINCT xa.article_id) AS linked_articles
        FROM questions q
        JOIN qid_art_xref link ON q.qid = link.qid AND link.article_id IN ({art_ph})
        LEFT JOIN qid_art_xref xa  ON q.qid = xa.qid  AND xa.article_id  != 'ART-0001'
        WHERE q.question_text IS NOT NULL AND q.question_text != ''
          {excl_sql}
        GROUP BY q.qid
        ORDER BY COUNT(DISTINCT link.article_id) DESC
        LIMIT ?
    """
    for row in db.execute(sql_ite, article_ids + excl_params + [limit]).fetchall():
        rs = _compute_relevance(1, priority_score, row["linked_articles"],
                                row["exam_year"], bool(row["concept_tags"]))
        candidates.append(_row_to_dict(row, dim, 1, row["linked_articles"] or 0, rs))

    # AAFP: same article co-link
    sql_aafp = f"""
        SELECT {_AAFP_Q_COLS},
               COUNT(DISTINCT xa.article_id) AS linked_articles
        FROM aafp_questions q
        JOIN aafp_qid_art_xref link ON q.aafp_qid = link.aafp_qid AND link.article_id IN ({art_ph})
        LEFT JOIN aafp_qid_art_xref xa  ON q.aafp_qid = xa.aafp_qid
        WHERE q.stem IS NOT NULL AND q.stem != ''
          {aafp_excl_sql}
        GROUP BY q.aafp_qid
        ORDER BY COUNT(DISTINCT link.article_id) DESC
        LIMIT ?
    """
    for row in db.execute(sql_aafp, article_ids + aafp_excl_params + [limit]).fetchall():
        rs = _compute_relevance(1, priority_score, row["linked_articles"],
                                None, bool(row["concept_tags"]))
        candidates.append(_row_to_dict(row, dim, 1, row["linked_articles"] or 0, rs))

    return candidates


def _tier2_icd10_sibling(db, dim: str, dim_type: str, priority_score: float,
                          selected_qids: set, limit: int = 60,
                          seed_icd10: list = None) -> list:
    """
    ICD-10 sibling match — find questions sharing ICD-10 codes with
    the weak dimension, via question_icd10 and aafp_question_icd10 directly.
    When seed_icd10 is provided (ICD-10 codes from the resident's specific
    wrong answers), those codes are used directly — more precise than
    deriving codes from all questions in the dimension.
    """
    candidates = []

    # Get the ICD-10 codes associated with this dimension
    where_parts, params = [], []
    if dim_type == "blueprint":
        db_bp = BLUEPRINT_PDF_TO_DB.get(dim, dim)
        where_parts.append("q.blueprint = ?")
        params.append(db_bp)
    elif dim_type == "body_system":
        db_names = BODYSYSTEM_PDF_TO_DB.get(dim, [dim])
        ph = ",".join(["?"] * len(db_names))
        where_parts.append(f"(q.body_system_merged IN ({ph}) OR q.body_system IN ({ph}))")
        params.extend(db_names * 2)
    elif dim_type == "cross_tab":
        parts = dim.split(" × ", 1)
        if len(parts) == 2:
            db_names = BODYSYSTEM_PDF_TO_DB.get(parts[0], [parts[0]])
            db_bp    = BLUEPRINT_PDF_TO_DB.get(parts[1], parts[1])
            bs_ph    = ",".join(["?"] * len(db_names))
            where_parts.append(f"(q.body_system_merged IN ({bs_ph}) OR q.body_system IN ({bs_ph}))")
            where_parts.append("q.blueprint = ?")
            params.extend(db_names * 2)
            params.append(db_bp)

    if not where_parts:
        return []

    # Derive ICD-10 codes: prefer wrong-QID seeds (precise) over full-dimension sweep
    if seed_icd10:
        icd_codes = seed_icd10
    else:
        # Fallback: collect ICD-10 codes from ALL questions in this dimension
        icd_rows = db.execute(f"""
            SELECT DISTINCT qi.icd10_code
            FROM questions q
            JOIN question_icd10 qi ON q.qid = qi.qid
            WHERE {" AND ".join(where_parts)}
              AND qi.relevance = 'primary'
        """, params).fetchall()
        icd_codes = [r["icd10_code"] for r in icd_rows]

    if not icd_codes:
        return []

    excl_sql, excl_params = _not_in(selected_qids)
    code_ph = ",".join(["?"] * len(icd_codes))

    # ITE siblings
    sql_ite = f"""
        SELECT {_ITE_Q_COLS},
               COUNT(DISTINCT xa.article_id) AS linked_articles
        FROM questions q
        JOIN question_icd10 qi ON q.qid = qi.qid
        LEFT JOIN qid_art_xref xa ON q.qid = xa.qid AND xa.article_id != 'ART-0001'
        WHERE qi.icd10_code IN ({code_ph})
          AND q.question_text IS NOT NULL AND q.question_text != ''
          {excl_sql}
        GROUP BY q.qid
        ORDER BY linked_articles DESC
        LIMIT ?
    """
    for row in db.execute(sql_ite, icd_codes + excl_params + [limit]).fetchall():
        rs = _compute_relevance(2, priority_score, row["linked_articles"],
                                row["exam_year"], bool(row["concept_tags"]))
        candidates.append(_row_to_dict(row, dim, 2, row["linked_articles"] or 0, rs))

    # AAFP siblings
    aafp_excl_sql2, aafp_excl_params2 = _not_in(selected_qids, "q.aafp_qid")
    sql_aafp = f"""
        SELECT {_AAFP_Q_COLS},
               COUNT(DISTINCT xa.article_id) AS linked_articles
        FROM aafp_questions q
        JOIN aafp_question_icd10 qi ON q.aafp_qid = qi.aafp_qid
        LEFT JOIN aafp_qid_art_xref xa ON q.aafp_qid = xa.aafp_qid
        WHERE qi.icd10_code IN ({code_ph})
          AND q.stem IS NOT NULL AND q.stem != ''
          {aafp_excl_sql2}
        GROUP BY q.aafp_qid
        ORDER BY linked_articles DESC
        LIMIT ?
    """
    for row in db.execute(sql_aafp, icd_codes + aafp_excl_params2 + [limit]).fetchall():
        rs = _compute_relevance(2, priority_score, row["linked_articles"],
                                None, bool(row["concept_tags"]))
        candidates.append(_row_to_dict(row, dim, 2, row["linked_articles"] or 0, rs))

    return candidates


def _tier3_vector_sim(db, missed_qids: list, selected_qids: set,
                      priorities: list, limit: int = 20) -> list:
    """
    Vector similarity fallback using question_icd10_vec.
    Builds a weakness profile vector from missed questions, then finds
    the most similar unselected questions across both banks.
    Requires numpy — gracefully skipped if not available.
    """
    try:
        import numpy as np
    except ImportError:
        return []

    if not missed_qids:
        return []

    # Build weakness profile: average vectors of missed ITE questions
    profile_vecs = []
    ph = ",".join(["?"] * len(missed_qids))
    rows = db.execute(f"""
        SELECT embedding FROM question_icd10_vec
        WHERE qid IN ({ph}) AND source_bank = 'ite'
    """, missed_qids).fetchall()

    for row in rows:
        vec = _blob_to_vec(row["embedding"])
        if vec is not None:
            profile_vecs.append(vec)

    if not profile_vecs:
        return []

    profile = np.mean(np.stack(profile_vecs), axis=0)

    # Score all unselected questions from both banks
    vec_excl_sql, vec_excl_params = _not_in(selected_qids, "qid")
    all_vecs = db.execute(f"""
        SELECT qid, source_bank, embedding
        FROM question_icd10_vec
        WHERE 1=1 {vec_excl_sql}
    """, vec_excl_params).fetchall()

    scored = []
    for row in all_vecs:
        vec = _blob_to_vec(row["embedding"])
        if vec is None:
            continue
        sim = _cosine_similarity(profile, vec)
        scored.append((row["qid"], row["source_bank"], sim))

    scored.sort(key=lambda x: x[2], reverse=True)
    top_qids_ite  = [qid for qid, bank, _ in scored if bank == "ite"][:limit]
    top_qids_aafp = [qid for qid, bank, _ in scored if bank == "aafp"][:limit]
    sim_map       = {qid: sim for qid, _, sim in scored}

    candidates = []
    priority_score = priorities[0]["priority_score"] if priorities else 1.0

    if top_qids_ite:
        ph = ",".join(["?"] * len(top_qids_ite))
        rows = db.execute(f"""
            SELECT {_ITE_Q_COLS},
                   COUNT(DISTINCT xa.article_id) AS linked_articles
            FROM questions q
            LEFT JOIN qid_art_xref xa ON q.qid = xa.qid AND xa.article_id != 'ART-0001'
            WHERE q.qid IN ({ph})
            GROUP BY q.qid
        """, top_qids_ite).fetchall()
        for row in rows:
            sim = sim_map.get(row["qid"], 0.0)
            rs  = _compute_relevance(3, priority_score * sim, row["linked_articles"],
                                     row["exam_year"], bool(row["concept_tags"]))
            candidates.append(_row_to_dict(row, "vector_similarity", 3,
                                           row["linked_articles"] or 0, rs))

    if top_qids_aafp:
        ph = ",".join(["?"] * len(top_qids_aafp))
        rows = db.execute(f"""
            SELECT {_AAFP_Q_COLS},
                   COUNT(DISTINCT xa.article_id) AS linked_articles
            FROM aafp_questions q
            LEFT JOIN aafp_qid_art_xref xa ON q.aafp_qid = xa.aafp_qid
            WHERE q.aafp_qid IN ({ph})
            GROUP BY q.aafp_qid
        """, top_qids_aafp).fetchall()
        for row in rows:
            sim = sim_map.get(row["qid"], 0.0)
            rs  = _compute_relevance(3, priority_score * sim, row["linked_articles"],
                                     None, bool(row["concept_tags"]))
            candidates.append(_row_to_dict(row, "vector_similarity", 3,
                                           row["linked_articles"] or 0, rs))

    return candidates


def _concept_selection(db, top_concepts_dict: dict, selected_qids: set,
                        base_priority: float = 2.5, limit: int = 60) -> list:
    """
    Find questions from BOTH banks (ITE + AAFP) whose concept_tags match the
    resident's top missed diagnoses or drugs.

    This is the bridge between the Concept Fingerprint analysis and the
    practice question engine.  Without this, the fingerprint tells you the
    resident missed Hypertension 33× but the practice set selects by
    Cardiovascular × Chronic Care with no guarantee of Hypertension coverage.

    Scoring: questions matching more top concepts AND higher-frequency concepts
    score higher.  Results compete in the global practice question pool and are
    labeled as "Concept Match" in the match tier column.

    Both banks are returned and labeled correctly:
      ITE bank  → source_label "ITE {year}"
      AAFP bank → source_label "AAFP BRQ"
    """
    if not top_concepts_dict:
        return []

    # Normalize top concepts to lowercase for comparison
    norm_top_set  = {k.lower() for k in top_concepts_dict}
    # Also normalize the display names → for targeting label
    norm_freq_map = {k.lower(): v for k, v in top_concepts_dict.items()}
    # Map: normalized key → canonical display name (from the concept_clustering output)
    norm_to_display = {k.lower(): k for k in top_concepts_dict}

    candidates = []

    # --- ITE bank ---
    excl_sql, excl_params = _not_in(selected_qids)
    ite_rows = db.execute(f"""
        SELECT {_ITE_Q_COLS},
               COUNT(DISTINCT xa.article_id) AS linked_articles
        FROM questions q
        LEFT JOIN qid_art_xref xa ON q.qid = xa.qid AND xa.article_id != 'ART-0001'
        WHERE q.concept_tags IS NOT NULL AND q.concept_tags != '' {excl_sql}
        GROUP BY q.qid
        ORDER BY linked_articles DESC
        LIMIT 600
    """, excl_params).fetchall()

    for row in ite_rows:
        try:
            tags = json.loads(row["concept_tags"])
        except (json.JSONDecodeError, TypeError):
            continue

        q_norms = set()
        for d in tags.get("diagnoses", []):
            q_norms.add(_normalize_concept(d).lower())
        for d in tags.get("drugs", []):
            q_norms.add(_normalize_concept(d).lower())

        matched = norm_top_set & q_norms
        if not matched:
            continue

        # Score = base + weighted frequency contribution of matched concepts
        concept_score = sum(norm_freq_map.get(m, 1) for m in matched)
        relevance = min(base_priority + (concept_score / 15.0), 5.0)
        if row["linked_articles"]:
            relevance += 0.5
        relevance += 0.3  # concept_tags bonus

        # Targeting label = highest-frequency concept matched
        top_match_key = max(matched, key=lambda m: norm_freq_map.get(m, 1))
        targeting = f"Concept: {norm_to_display.get(top_match_key, top_match_key)}"

        candidates.append(_row_to_dict(row, targeting, 1,
                                       row["linked_articles"] or 0, round(relevance, 3)))

    # --- AAFP bank ---
    aafp_excl_sql, aafp_excl_params = _not_in(selected_qids, "q.aafp_qid")
    aafp_rows = db.execute(f"""
        SELECT {_AAFP_Q_COLS},
               COUNT(DISTINCT xa.article_id) AS linked_articles
        FROM aafp_questions q
        LEFT JOIN aafp_qid_art_xref xa ON q.aafp_qid = xa.aafp_qid
        WHERE q.concept_tags IS NOT NULL AND q.concept_tags != '' {aafp_excl_sql}
        GROUP BY q.aafp_qid
        ORDER BY linked_articles DESC
        LIMIT 600
    """, aafp_excl_params).fetchall()

    for row in aafp_rows:
        try:
            tags = json.loads(row["concept_tags"])
        except (json.JSONDecodeError, TypeError):
            continue

        q_norms = set()
        for d in tags.get("diagnoses", []):
            q_norms.add(_normalize_concept(d).lower())
        for d in tags.get("drugs", []):
            q_norms.add(_normalize_concept(d).lower())

        matched = norm_top_set & q_norms
        if not matched:
            continue

        concept_score = sum(norm_freq_map.get(m, 1) for m in matched)
        relevance = min(base_priority + (concept_score / 15.0), 5.0)
        if row["linked_articles"]:
            relevance += 0.5
        relevance += 0.3

        top_match_key = max(matched, key=lambda m: norm_freq_map.get(m, 1))
        targeting = f"Concept: {norm_to_display.get(top_match_key, top_match_key)}"

        candidates.append(_row_to_dict(row, targeting, 1,
                                       row["linked_articles"] or 0, round(relevance, 3)))

    # Sort by relevance; return top N (global mix of ITE + AAFP)
    candidates.sort(key=lambda x: x["relevance_score"], reverse=True)
    return candidates[:limit]


def _build_concept_profile(db, wrong_qids: list):
    """
    Build a resident concept profile vector by averaging question_concepttag_vec
    embeddings for the resident's missed questions (across ALL weak dimensions).

    Returns a numpy float32 array (1536-dim) representing the resident's
    semantic weakness fingerprint, or None if numpy is unavailable or no
    vectors are found.

    Used by:
      - _centroid_dim_boost()  — to weight priority_score per cross_tab cell
      - _apply_concept_vec_bonus() — to score every candidate by semantic proximity
    """
    try:
        import numpy as np
    except ImportError:
        return None

    if not wrong_qids:
        return None

    ph = ",".join(["?"] * len(wrong_qids))
    rows = db.execute(
        f"SELECT embedding FROM question_concepttag_vec WHERE qid IN ({ph})",
        wrong_qids,
    ).fetchall()

    vecs = []
    for row in rows:
        vec = _blob_to_vec(row["embedding"])
        if vec is not None:
            vecs.append(vec)

    if not vecs:
        return None

    return np.mean(np.stack(vecs), axis=0)


def _centroid_dim_boost(db, dim: str, dim_type: str, profile_vec) -> float:
    """
    For cross_tab dimensions only: look up intersection_centroid_vec for the
    matching blueprint × body_system cell.  Compute cosine similarity between
    the resident's concept profile and the centroid, then return a priority_score
    multiplier scaled to [CENTROID_BOOST_MIN, CENTROID_BOOST_MAX].

    Returns 1.0 (no-op) when:
      - dim_type is not 'cross_tab'
      - profile_vec is None
      - no matching centroid found in DB
      - numpy unavailable

    Design intent: a resident who is weak in "Cardiovascular × Chronic Care"
    and whose missed questions are semantically close to the centroid of that
    cell should see a higher priority_score for it — ensuring Tier 1 pulls
    more candidates from that exact intersection rather than distributing
    slots evenly across all weak dimensions.
    """
    if profile_vec is None or dim_type != "cross_tab":
        return 1.0

    parts = dim.split(" × ", 1)
    if len(parts) != 2:
        return 1.0

    bs_part, bp_part = parts
    db_bp    = BLUEPRINT_PDF_TO_DB.get(bp_part, bp_part)
    db_names = BODYSYSTEM_PDF_TO_DB.get(bs_part, [bs_part])

    # Collect matching centroid(s) — one per db body_system name, both source banks.
    centroid_vecs = []
    for bs_name in db_names:
        rows = db.execute(
            "SELECT embedding FROM intersection_centroid_vec "
            "WHERE blueprint = ? AND body_system = ?",
            (db_bp, bs_name),
        ).fetchall()
        for row in rows:
            vec = _blob_to_vec(row["embedding"])
            if vec is not None:
                centroid_vecs.append(vec)

    if not centroid_vecs:
        return 1.0

    try:
        import numpy as np
        centroid = np.mean(np.stack(centroid_vecs), axis=0) if len(centroid_vecs) > 1 else centroid_vecs[0]
        sim = _cosine_similarity(profile_vec, centroid)   # [0.0, 1.0]
        boost = CENTROID_BOOST_MIN + (CENTROID_BOOST_MAX - CENTROID_BOOST_MIN) * sim
        return boost
    except Exception:
        return 1.0


def _apply_concept_vec_bonus(db, all_candidates: dict, profile_vec, weight: float) -> None:
    """
    Score every candidate in all_candidates by cosine similarity of its
    question_concepttag_vec to the resident's concept profile.  Adds
    `sim * weight` as a bonus to each candidate's relevance_score.

    Mutates all_candidates in-place — no return value.
    Silently skips candidates with no stored embedding.

    Batch-loads all candidate embeddings in two SQL queries (ITE + AAFP)
    to avoid N+1 round-trips.

    Called AFTER the full candidate pool is assembled and BEFORE the fingerprint
    frequency bonus, so semantically-aligned questions compete at their correct
    tier weight before concept-frequency inflation.
    """
    if profile_vec is None or not all_candidates or weight == 0:
        return

    ite_qids  = [qid for qid, c in all_candidates.items() if c.get("source_bank") == "ITE"]
    aafp_qids = [qid for qid, c in all_candidates.items() if c.get("source_bank") == "AAFP"]

    emb_map: dict = {}   # qid → numpy vector

    for qid_list in (ite_qids, aafp_qids):
        if not qid_list:
            continue
        ph = ",".join(["?"] * len(qid_list))
        rows = db.execute(
            f"SELECT qid, embedding FROM question_concepttag_vec WHERE qid IN ({ph})",
            qid_list,
        ).fetchall()
        for row in rows:
            vec = _blob_to_vec(row["embedding"])
            if vec is not None:
                emb_map[row["qid"]] = vec

    for qid, cand in all_candidates.items():
        vec = emb_map.get(qid)
        if vec is None:
            continue
        sim = _cosine_similarity(profile_vec, vec)
        cand["relevance_score"] = round(cand["relevance_score"] + sim * weight, 3)


def match_practice_questions_v3(perf: dict, priorities: list, qid_map: dict,
                                 items: list, db_path: str,
                                 target_count: int = 20,
                                 current_exam_year: int = None,
                                 concepts: dict = None,
                                 icd10_profile: dict = None) -> list:
    """
    Select and globally rank practice questions from both ITE + AAFP banks.

    Strategy:
      1. For each top priority dimension, gather candidates from Tier 1 + 2
         (blueprint/body_system/cross_tab match)
      2. Concept-driven selection: questions from both banks whose concept_tags
         match the resident's top missed diagnoses + drugs — bridges the gap
         between the Concept Fingerprint findings and the practice set
      3. If total candidates < target, invoke Tier 3 (vector similarity)
      4. Score all candidates globally with relevance_score
         — Fingerprint freq-weighted bonus: concept_tags matching top missed concepts
         — ICD-10 proximity bonus: question_icd10 matching the resident's ICD-10
           weakness profile (derived from actual missed ITE questions, not enrichment)
      5. Deduplicate, sort by relevance_score, return top target_count
      6. Every question labeled with source_bank + source_label (ITE/AAFP BRQ)

    icd10_profile: {icd10_code: miss_count} built from icd10_weakness_map().
    Used as an invisible scoring layer — never displayed in the report.
    ICD-10 codes are taxonomy-stable (I10 = HTN regardless of text label variant),
    so this fixes the "stage 2 hypertension" ≠ "Hypertension" concept-tag mismatch.
    """
    if not db_path:
        return []

    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row

    all_candidates = {}   # qid → best candidate dict (by relevance_score)
    selected_qids  = set()
    active         = priorities  # ALL weak dimensions — no cap; every weak area gets coverage

    # Pre-compute wrong QIDs and their rich metadata for each active dimension.
    # This anchors Tier 1b + Tier 2 to the resident's specific missed items
    # rather than the full population of questions in that category.
    wrong_qids_by_dim: dict = {}
    wrong_meta_by_dim: dict = {}
    for priority in active:
        dim      = priority["dimension"]
        dim_type = priority["dimension_type"]
        wqids: list = []
        for item in items:
            if item.get("correct"):
                continue
            num = item.get("item")
            if num not in qid_map:
                continue
            if dim_type == "blueprint" and item.get("blueprint") == dim:
                wqids.append(qid_map[num])
            elif dim_type == "body_system" and item.get("body_system") == dim:
                wqids.append(qid_map[num])
            elif dim_type == "cross_tab":
                parts = dim.split(" × ", 1)
                if len(parts) == 2 and item.get("body_system") == parts[0] and item.get("blueprint") == parts[1]:
                    wqids.append(qid_map[num])
        wrong_qids_by_dim[dim] = wqids
        wrong_meta_by_dim[dim] = _get_wrong_qid_metadata(db, wqids) if wqids else {}

    # Build resident concept profile — average of question_concepttag_vec embeddings
    # for ALL missed questions across all dimensions.  Single vector representing the
    # semantic fingerprint of this resident's weakness space.
    # Used in: (1) centroid_dim_boost per cross_tab priority, (2) concept_vec_bonus post-pool.
    all_wrong_qids = list({qid for wqids in wrong_qids_by_dim.values() for qid in wqids})
    concept_profile = _build_concept_profile(db, all_wrong_qids)

    # Tier 1 + Tier 1b (article co-link) + Tier 2 (ICD-10 seeded) per dimension
    for priority in active:
        dim            = priority["dimension"]
        dim_type       = priority["dimension_type"]
        # Centroid boost: for cross_tab dims, scale priority_score by cosine similarity
        # between resident concept profile and the intersection_centroid_vec for this cell.
        # More semantically aligned cell → higher priority → more Tier 1 candidates scored higher.
        centroid_mult  = _centroid_dim_boost(db, dim, dim_type, concept_profile)
        priority_score = priority["priority_score"] * centroid_mult

        meta       = wrong_meta_by_dim.get(dim, {})
        seed_icd10 = meta.get("icd10_codes") or None

        t1  = _tier1_direct(db, dim, dim_type, priority_score, selected_qids)
        t1b = _tier1b_richseed(db, meta, dim, priority_score, selected_qids) if meta else []
        t2  = _tier2_icd10_sibling(db, dim, dim_type, priority_score, selected_qids,
                                    seed_icd10=seed_icd10)

        for cand in t1 + t1b + t2:
            qid = cand["qid"]
            if qid not in all_candidates or cand["relevance_score"] > all_candidates[qid]["relevance_score"]:
                all_candidates[qid] = cand
            selected_qids.add(qid)

    # --- Concept-driven selection (Tier 1c) ---
    # Uses the Concept Fingerprint findings (top missed diagnoses + drugs) to seed
    # practice question selection from BOTH banks.  This ensures the concept
    # fingerprint analysis DRIVES what questions the resident studies — not just
    # the blueprint/body_system dimension breakdown.
    #
    # IMPORTANT: we pass set() here (not selected_qids) so that concept selection
    # can RE-TAG questions already claimed by T1/T2 if concept matching scores them
    # higher.  T1 order-by-linked-articles tends to grab the best Hypertension/T2DM
    # questions already; without re-tagging they'd show up labeled "Chronic Care"
    # instead of "Concept: Hypertension".  Deduplication in the loop below ensures
    # higher-scoring labels win — the global pool handles the rest.
    if concepts:
        # Use combined counts (ITE + AAFP enrichment) for scoring so AAFP context
        # broadens concept coverage; ITE-only counts are used for display only.
        top_dx    = dict(list((concepts.get("top_diagnoses_combined") or concepts.get("top_diagnoses") or {}).items())[:8])
        top_drugs = dict(list((concepts.get("top_drugs_combined")     or concepts.get("top_drugs")     or {}).items())[:5])
        concept_pool = {**top_dx, **top_drugs}   # merged dict, diagnoses take precedence
        if concept_pool:
            concept_cands = _concept_selection(db, concept_pool, set())   # no exclusion
            for cand in concept_cands:
                qid = cand["qid"]
                if qid not in all_candidates or cand["relevance_score"] > all_candidates[qid]["relevance_score"]:
                    all_candidates[qid] = cand
                selected_qids.add(qid)

    # Concept vector bonus — semantic similarity between each candidate's concept
    # embedding and the resident's missed-question concept profile.
    # Applied AFTER full candidate gathering (T1/T1b/T2/T1c) and BEFORE fingerprint
    # bonus, so semantically-aligned questions rise through the global pool at their
    # correct tier weight before concept-frequency inflation.
    # Gracefully skips if concept_profile is None (numpy unavailable, no wrong QIDs,
    # or question_concepttag_vec table empty).
    _apply_concept_vec_bonus(db, all_candidates, concept_profile,
                             weight=CONCEPT_VEC_BONUS_WEIGHT)

    # Fingerprint frequency-weighted bonus — uses combined counts for scoring weight.
    # Combined counts include AAFP enrichment which broadens signal strength.
    # Display tables use ITE-only counts so displayed frequencies are honest.
    if concepts:
        _fp_top_dx    = dict(list((concepts.get("top_diagnoses_combined") or concepts.get("top_diagnoses") or {}).items())[:10])
        _fp_top_drugs = dict(list((concepts.get("top_drugs_combined")     or concepts.get("top_drugs")     or {}).items())[:5])
        _fp_map = {_normalize_concept(k).lower(): v
                   for k, v in {**_fp_top_dx, **_fp_top_drugs}.items()}
        _fp_set = set(_fp_map.keys())
        for qid, cand in all_candidates.items():
            try:
                raw_tags = cand.get("concept_tags")
                if not raw_tags:
                    continue
                tags = json.loads(raw_tags) if isinstance(raw_tags, str) else raw_tags
                q_norms: set = set()
                if isinstance(tags, dict):
                    for d in tags.get("diagnoses", []):  q_norms.add(_normalize_concept(str(d)).lower())
                    for d in tags.get("drugs",      []):  q_norms.add(_normalize_concept(str(d)).lower())
                elif isinstance(tags, list):
                    for d in tags: q_norms.add(_normalize_concept(str(d)).lower())
                matched = _fp_set & q_norms
                if matched:
                    concept_score = sum(_fp_map.get(m, 0) for m in matched)
                    bonus = concept_score / 10.0  # freq=33 → +3.3, freq=5 → +0.5
                    cand["relevance_score"] = round(cand["relevance_score"] + bonus, 3)
            except (json.JSONDecodeError, TypeError, AttributeError):
                pass

    # ICD-10 proximity bonus — invisible scoring layer, never shown in report.
    # Batch-loads ICD-10 codes for every candidate from question_icd10 /
    # aafp_question_icd10, then scores overlap against the resident's ICD-10
    # weakness profile (codes from actual missed ITE questions, taxonomy-stable).
    #
    # ICD-10 codes bypass the concept-tag label-variant problem: "stage 2
    # hypertension", "essential hypertension", "hypertensive emergency" all
    # map to I10 — so a practice question on any HTN variant gets the same
    # boost, regardless of how its concept_tags were written.
    #
    # Bonus scale: miss_count=7 (E11.9 T2DM, primary match) → 7*2/15 = +0.93
    #              miss_count=5 (I10 HTN,  primary match) → 5*2/15 = +0.67
    #              two-code match (E11.9+I10, both primary) → +1.6
    # Complementary to fingerprint bonus — ICD-10 signal is pure-ITE missed Qs.
    if icd10_profile:
        _ite_cand_qids  = [qid for qid, c in all_candidates.items()
                           if c.get("source_bank") == "ITE"]
        _aafp_cand_qids = [qid for qid, c in all_candidates.items()
                           if c.get("source_bank") == "AAFP"]

        _cand_icd10: dict = {}   # {qid: {icd10_code: relevance_str}}

        if _ite_cand_qids:
            _ph = ",".join(["?"] * len(_ite_cand_qids))
            for _r in db.execute(
                f"SELECT qid, icd10_code, relevance FROM question_icd10 "
                f"WHERE qid IN ({_ph}) AND icd10_code != 'no_match'",
                _ite_cand_qids
            ).fetchall():
                _cand_icd10.setdefault(_r["qid"], {})[_r["icd10_code"]] = _r["relevance"]

        if _aafp_cand_qids:
            _ph = ",".join(["?"] * len(_aafp_cand_qids))
            for _r in db.execute(
                f"SELECT aafp_qid AS qid, icd10_code, relevance FROM aafp_question_icd10 "
                f"WHERE aafp_qid IN ({_ph}) AND icd10_code != 'no_match'",
                _aafp_cand_qids
            ).fetchall():
                _cand_icd10.setdefault(_r["qid"], {})[_r["icd10_code"]] = _r["relevance"]

        for qid, cand in all_candidates.items():
            _q_codes = _cand_icd10.get(qid)
            if not _q_codes:
                continue
            _icd_bonus = 0.0
            for _code, _rel in _q_codes.items():
                _pw = icd10_profile.get(_code, 0)
                if _pw:
                    _rel_mult = 2.0 if _rel == "primary" else 1.0
                    _icd_bonus += _pw * _rel_mult / 15.0
            if _icd_bonus:
                cand["relevance_score"] = round(cand["relevance_score"] + _icd_bonus, 3)

    # Exclude current exam year from ITE practice questions.
    # A resident who just sat the 2025 ITE shouldn't receive their own exam
    # questions back as "practice" — exclude them so older content covers the gaps.
    # Cast to int: parser returns exam_year as str; DB candidates store it as int.
    if current_exam_year:
        try:
            _excl_year = int(current_exam_year)
        except (TypeError, ValueError):
            _excl_year = None
        if _excl_year:
            all_candidates = {
                qid: c for qid, c in all_candidates.items()
                if not (c.get("source_bank") == "ITE" and c.get("exam_year") == _excl_year)
            }

    # Tier 3: vector fallback if still below target
    if len(all_candidates) < target_count:
        missed_item_nums = {i["item"] for i in items if not i["correct"]}
        missed_qids = [qid_map[n] for n in missed_item_nums if n in qid_map]
        t3 = _tier3_vector_sim(db, missed_qids, selected_qids, priorities)
        for cand in t3:
            qid = cand["qid"]
            if qid not in all_candidates:
                all_candidates[qid] = cand

    db.close()

    # Global pool — all banks merged and sorted by relevance_score.
    # Merging before dim_cap selection ensures every active weak dimension
    # competes for slots equally, regardless of bank.  Per-bank splitting
    # previously starved low-priority dimensions when higher-volume banks
    # consumed all slots before low-priority dims got representation.
    all_ranked = sorted(all_candidates.values(),
                        key=lambda x: x["relevance_score"], reverse=True)
    aafp_ranked = [c for c in all_ranked if c["source_bank"] == "AAFP"]

    # Dimension diversity cap — ceil(target / n_active_dims), floor of 1.
    # Floor is 1: if only one good question exists for a weak area, use it.
    n_active = max(len(active), 1)
    dim_cap  = max(1, -(-target_count // n_active))   # ceiling division

    def _select_with_dim_cap(pool: list, slots: int, cap: int) -> list:
        """Fill up to `slots` questions from `pool`, max `cap` per targeting dim."""
        counts: dict   = {}
        selected: list = []
        overflow: list = []
        for cand in pool:
            t = cand.get("targeting", "__unset__")
            if counts.get(t, 0) < cap:
                selected.append(cand)
                counts[t] = counts.get(t, 0) + 1
            else:
                overflow.append(cand)
            if len(selected) >= slots:
                break
        for cand in overflow:
            if len(selected) >= slots:
                break
            selected.append(cand)
        return selected[:slots]

    # Two-pass selection — ensures every active weak dimension gets coverage
    # before higher-priority dimensions consume all slots via overflow.
    #
    # Pass 1 (coverage): pick the single best candidate for each active dim.
    #   This reserves N_active slots upfront — one per weak area.
    # Pass 2 (fill): remaining slots filled by global relevance ranking with
    #   dim_cap, so high-priority dims get their extra representation.

    # Pass 1: best-per-dim coverage guarantee
    covered_qids: set = set()
    coverage_selected: list = []
    for priority in active:
        dim_name = priority["dimension"]
        for cand in all_ranked:
            if cand["targeting"] == dim_name and cand["qid"] not in covered_qids:
                coverage_selected.append(cand)
                covered_qids.add(cand["qid"])
                break  # one per dim for now

    # Pass 2: fill remaining slots from global pool (excluding already covered)
    fill_slots    = max(0, target_count - len(coverage_selected))
    remaining_pool = [c for c in all_ranked if c["qid"] not in covered_qids]
    fill_selected  = _select_with_dim_cap(remaining_pool, fill_slots, dim_cap)

    combined = coverage_selected + fill_selected

    # AAFP minimum guarantee — ITE volume advantage can crowd out AAFP.
    # If AAFP count falls below AAFP_MIN_QUESTIONS, swap in best remaining AAFP
    # candidates for the weakest ITE selections that have >1 question for their dim.
    aafp_count = sum(1 for c in combined if c["source_bank"] == "AAFP")
    if aafp_count < AAFP_MIN_QUESTIONS and aafp_ranked:
        combined_qids = {c["qid"] for c in combined}
        aafp_spare    = [c for c in aafp_ranked if c["qid"] not in combined_qids]
        needed        = AAFP_MIN_QUESTIONS - aafp_count
        for cand in aafp_spare[:needed]:
            # Replace lowest-relevance ITE question that isn't sole dim coverage
            combined.sort(key=lambda x: x["relevance_score"])
            for i, c in enumerate(combined):
                dim_count = sum(1 for x in combined if x["targeting"] == c["targeting"])
                if c["source_bank"] == "ITE" and dim_count > 1:
                    combined.pop(i)
                    combined.append(cand)
                    break

    # Re-sort by relevance so the output reads naturally
    combined.sort(key=lambda x: x["relevance_score"], reverse=True)
    return combined[:target_count]


# ---------------------------------------------------------------------------
# Top Articles (updated: includes AAFP xref links)
# ---------------------------------------------------------------------------

def match_top_articles(perf: dict, db_path: str, count: int = 5,
                        items: list = None, qid_map: dict = None) -> list:
    """
    Articles most linked to THIS RESIDENT's missed questions.

    Personalization: counts only the questions this specific resident got wrong,
    not all questions in weak categories. This ensures the reading list reflects
    the resident's actual gaps rather than a popularity ranking of all articles.
    """
    if not db_path:
        return []

    # Build the set of QIDs this resident actually missed
    missed_qids: list = []
    if items and qid_map:
        missed_qids = [
            qid_map[i["item"]]
            for i in items
            if not i.get("correct") and i["item"] in qid_map
        ]

    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row

    if missed_qids:
        # Personalized path: count links to THIS resident's missed questions only
        ph = ",".join(["?"] * len(missed_qids))
        sql = f"""
            SELECT a.article_id, a.title, a.author1, a.year, a.source_type,
                   a.citation_count, a.unique_years, a.exam_years, a.clean_ref,
                   COUNT(DISTINCT qa.qid) AS weak_area_links,
                   COALESCE(ac.currency_status, 'unknown') AS currency_status
            FROM articles a
            JOIN qid_art_xref qa ON a.article_id = qa.article_id
            LEFT JOIN article_currency ac ON a.article_id = ac.article_id
            WHERE qa.qid IN ({ph})
              AND a.source_type != 'stub'
              AND a.article_id  != 'ART-0001'
              AND a.citation_count >= 2
            GROUP BY a.article_id
            ORDER BY weak_area_links DESC, a.citation_count DESC
            LIMIT ?
        """
        rows = db.execute(sql, missed_qids + [count]).fetchall()
    else:
        # Fallback: weak-area categories (no personalization, used when items unavailable)
        weak_systems    = [name for name, p in perf.get("body_system", {}).items() if p["rate"] < 0.70]
        weak_blueprints = [BLUEPRINT_PDF_TO_DB.get(name, name)
                           for name, p in perf.get("blueprint", {}).items() if p["rate"] < 0.70]
        db_system_names = []
        for ws in weak_systems:
            db_system_names.extend(BODYSYSTEM_PDF_TO_DB.get(ws, [ws]))

        params, clauses = [], []
        if db_system_names:
            bs_ph = ",".join(["?"] * len(db_system_names))
            clauses.append(f"(q.body_system_merged IN ({bs_ph}) OR q.body_system IN ({bs_ph}))")
            params.extend(db_system_names * 2)
        if weak_blueprints:
            bp_ph = ",".join(["?"] * len(weak_blueprints))
            clauses.append(f"q.blueprint IN ({bp_ph})")
            params.extend(weak_blueprints)
        where = " OR ".join(clauses) if clauses else "1=1"

        sql = f"""
            SELECT a.article_id, a.title, a.author1, a.year, a.source_type,
                   a.citation_count, a.unique_years, a.exam_years, a.clean_ref,
                   COUNT(DISTINCT q.qid) AS weak_area_links,
                   COALESCE(ac.currency_status, 'unknown') AS currency_status
            FROM articles a
            JOIN qid_art_xref qa ON a.article_id = qa.article_id
            JOIN questions q     ON qa.qid = q.qid
            LEFT JOIN article_currency ac ON a.article_id = ac.article_id
            WHERE ({where})
              AND a.source_type != 'stub'
              AND a.article_id  != 'ART-0001'
              AND a.citation_count >= 2
            GROUP BY a.article_id
            ORDER BY weak_area_links DESC, a.citation_count DESC
            LIMIT ?
        """
        rows = db.execute(sql, params + [count]).fetchall()

    db.close()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Score Interpretation — plain-language framing for program directors
# ---------------------------------------------------------------------------

SCORE_BANDS = [
    {"min": 480,  "label": "Strong",          "color": "green",  "fmce_prob": ">95%"},
    {"min": 440,  "label": "On Track",         "color": "blue",   "fmce_prob": ">85%"},
    {"min": 380,  "label": "Monitoring Zone",  "color": "amber",  "fmce_prob": "50–85%"},
    {"min":   0,  "label": "Below MPS",        "color": "red",    "fmce_prob": "<50%"},
]

TYPICAL_GAINS = {
    "PGY1": {"to_next": "40–60", "label": "PGY1→PGY2"},
    "PGY2": {"to_next": "25–35", "label": "PGY2→PGY3"},
    "PGY3": {"to_next": None,    "label": "PGY3 (certification year)"},
    "All":  {"to_next": None,    "label": ""},
}


def build_score_interpretation(thresholds: dict, ref: dict, pgy_level: str = "All") -> dict:
    """
    Assemble a plain-language score interpretation block for the report header.

    Draws from already-computed thresholds. Adds:
      - score_band: human-readable tier label + color hint
      - confidence_range_68: [low, high] based on SEM ±38
      - trajectory_note: gap to 440 threshold + expected gain
      - sub_score_caution: ABFM's own warning language

    This is a read-only assembly — no new DB queries.
    """
    t1 = thresholds.get("tier1_pass_probability", {})
    scaled    = t1.get("scaled_score", 0)
    perc      = t1.get("percentile_estimate")
    vs_mps    = t1.get("vs_mps", scaled - 380)
    nat_mean  = t1.get("national_mean", 434)
    nat_sd    = t1.get("national_sd", 85)
    sem       = ref.get("exam_specs", {}).get("sem_overall", 38)

    # Score band
    band = SCORE_BANDS[-1]
    for b in SCORE_BANDS:
        if scaled >= b["min"]:
            band = b
            break

    # Confidence range (±1 SEM = 68%)
    conf_low  = max(200, scaled - sem)
    conf_high = min(800, scaled + sem)

    # Gap to the "very reassuring" 440 threshold
    gap_to_440 = max(0, 440 - scaled)

    # Trajectory note
    gain_info = TYPICAL_GAINS.get(pgy_level, TYPICAL_GAINS["All"])
    if gain_info["to_next"] and gap_to_440 > 0:
        trajectory_note = (
            f"Gap to 440 threshold: {gap_to_440} points. "
            f"Typical {gain_info['label']} gain is {gain_info['to_next']} points."
        )
    elif gap_to_440 == 0:
        trajectory_note = "Score is at or above the 440 'very reassuring' threshold for FMCE passage."
    else:
        trajectory_note = gain_info.get("label", "")

    # National context
    if nat_sd and nat_sd > 0:
        vs_nat = scaled - nat_mean
        sign   = "+" if vs_nat >= 0 else ""
        nat_context = f"{sign}{vs_nat} vs. national mean ({nat_mean}) for {pgy_level}"
    else:
        nat_context = ""

    return {
        "scaled_score":       scaled,
        "score_band":         band["label"],
        "score_band_color":   band["color"],
        "fmce_probability":   band["fmce_prob"],
        "percentile_estimate": perc,
        "vs_mps":             vs_mps,
        "sem":                sem,
        "confidence_range_68": [conf_low, conf_high],
        "gap_to_440":         gap_to_440,
        "national_context":   nat_context,
        "trajectory_note":    trajectory_note,
        "sub_score_caution":  (
            "ABFM guidance: sub-scores are NOT sufficiently precise to confirm "
            "knowledge deficits — use to generate hypotheses only. "
            f"Typical sub-score SEM: Foundations ±187, Preventive ±109, Emergent ±97."
        ),
        "bsp_url": ref.get("notes", {}).get("bayesian_predictor_url",
                                            "https://rtm.theabfm.org/bayesian/predictor"),
    }


# ---------------------------------------------------------------------------
# MASTER: analyze_v3
# ---------------------------------------------------------------------------

def fetch_missed_items_detail(items: list, qid_map: dict, db_path: str) -> list:
    """
    Pull full question detail for every missed item from the ITE questions table.
    Returned list is ordered by item number and saved as missed_items_detail in
    the analysis JSON so the report builder can render an appendix.

    Fields per entry:
        item_number, qid, blueprint, body_system, exam_year,
        question_text, choices, correct_letter, correct_text, explanation, reference
    """
    if not db_path:
        return []

    missed = sorted(
        [i for i in items if not i["correct"]],
        key=lambda x: x["item"]
    )
    if not missed:
        return []

    missed_qids = [qid_map[i["item"]] for i in missed if i["item"] in qid_map]
    if not missed_qids:
        return []

    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    ph  = ",".join(["?"] * len(missed_qids))
    rows = db.execute(f"""
        SELECT qid, blueprint, body_system, exam_year,
               question_text, choices, correct_letter, correct_text,
               explanation, reference
        FROM questions
        WHERE qid IN ({ph})
        ORDER BY exam_year, qid
    """, missed_qids).fetchall()
    db.close()

    # Build a lookup so we can attach item_number
    qid_to_row = {row["qid"]: dict(row) for row in rows}

    result = []
    for i in missed:
        item_num = i["item"]
        qid = qid_map.get(item_num)
        if not qid or qid not in qid_to_row:
            # QID not found in DB (deleted item or year mismatch) — include stub
            result.append({
                "item_number":   item_num,
                "qid":           qid or "unknown",
                "blueprint":     i.get("blueprint"),
                "body_system":   i.get("body_system"),
                "exam_year":     None,
                "question_text": None,
                "choices":       None,
                "correct_letter": None,
                "correct_text":  None,
                "explanation":   None,
                "reference":     None,
                "db_found":      False,
            })
            continue

        row = qid_to_row[qid]
        result.append({
            "item_number":    item_num,
            "qid":            qid,
            "blueprint":      row.get("blueprint"),
            "body_system":    row.get("body_system"),
            "exam_year":      row.get("exam_year"),
            "question_text":  row.get("question_text"),
            "choices":        row.get("choices"),
            "correct_letter": row.get("correct_letter"),
            "correct_text":   row.get("correct_text"),
            "explanation":    row.get("explanation"),
            "reference":      row.get("reference"),
            "db_found":       True,
        })

    return result


def analyze_v3(parsed_data: dict, db_path: str, ref_path: str = None,
               pgy_level: str = "All", question_count: int = 20) -> dict:
    """
    Full v3 analysis pipeline.

    Args:
        parsed_data:    merged output from ite_parser (items, resident, exam_year)
        db_path:        path to ite_intelligence.db
        ref_path:       path to abfm_reference_2025.json (auto-detected if None)
        pgy_level:      PGY1/PGY2/PGY3/All for national benchmarking
        question_count: practice questions to select (default 20)
    """
    # Dynamic reference file — match to exam year; fall back to 2025 if not found.
    # This ensures national benchmarks and raw→scaled lookup use the correct year.
    if ref_path is None:
        year_str  = str(parsed_data.get("exam_year") or 2025)
        candidate = Path(__file__).parent / f"abfm_reference_{year_str}.json"
        ref_path  = str(candidate) if candidate.exists() else str(
            Path(__file__).parent / "abfm_reference_2025.json"
        )
        if not candidate.exists():
            print(f"  [WARN] No reference file for {year_str}, using abfm_reference_2025.json", flush=True)

    ref        = load_abfm_reference(ref_path)
    items      = parsed_data["items"]
    exam_year  = parsed_data.get("exam_year") or 2025
    qid_map    = build_qid_map(items, exam_year)

    # Normalize body system names on every item to canonical BODYSYSTEM_PDF_TO_DB keys.
    # Handles score-report aliases (e.g. "Musculoskeletal" → "Injuries/Musculoskeletal")
    # and whitespace variants so all downstream analysis uses consistent names.
    for item in items:
        if item.get("body_system"):
            item["body_system"] = _normalize_body_system(item["body_system"])

    # --- Core analysis layers ---
    perf        = basic_performance(items)
    thresholds  = compute_thresholds(perf, ref, pgy_level)
    score_interp = build_score_interpretation(thresholds, ref, pgy_level)
    difficulty  = difficulty_profile(items, qid_map)
    concepts    = concept_clustering(items, qid_map, db_path)
    clustering  = spatial_clustering(items)
    patterns    = cross_dimensional_patterns(items, perf)
    priorities  = yield_weighted_priorities(perf, ref)

    # --- DB-connected layers ---
    icd10_map   = icd10_weakness_map(items, qid_map, db_path)
    pathway_map = pathway_gap_map(icd10_map, db_path)

    # Build ICD-10 weakness profile for invisible scoring enrichment.
    # {icd10_code: miss_count} derived from actual missed ITE questions.
    # Passed to match_practice_questions_v3 as a scoring signal — never displayed.
    icd10_profile = {
        c["code"]: c["miss_count"]
        for c in (icd10_map or {}).get("icd10_clusters", [])
        if c.get("miss_count", 0) > 0
    }

    # --- Practice questions + top articles ---
    practice_qs  = match_practice_questions_v3(perf, priorities, qid_map,
                                                items, db_path, question_count,
                                                current_exam_year=exam_year,
                                                concepts=concepts,
                                                icd10_profile=icd10_profile)

    # --- Concept fingerprint annotation on practice questions ---
    # After T1/T2 selection, annotate each practice question with which
    # top-missed fingerprint concepts it tests.  T1 already grabs the right
    # clinical questions; this adds the "Concept: Hypertension" label so the
    # resident can see WHY each practice question is clinically relevant.
    #
    # Uses post-selection annotation (not score competition) because T1
    # priority_scores (range 13–90) dwarf concept relevance (~5).  Annotation
    # preserves the proven T1/T2 ranking while adding fingerprint traceability.
    if concepts and practice_qs:
        top_dx_keys    = list((concepts.get("top_diagnoses") or {}).keys())[:10]
        top_drug_keys  = list((concepts.get("top_drugs")     or {}).keys())[:5]
        # Normalized lowercase → canonical display name lookup
        fp_norm_map = {_normalize_concept(k).lower(): k
                       for k in top_dx_keys + top_drug_keys}
        fp_norm_set = set(fp_norm_map.keys())
        for q in practice_qs:
            try:
                raw = q.get("concept_tags")
                if not raw:
                    continue
                tags = json.loads(raw) if isinstance(raw, str) else {}
                q_norms: set = set()
                for d in tags.get("diagnoses", []):
                    q_norms.add(_normalize_concept(str(d)).lower())
                for d in tags.get("drugs", []):
                    q_norms.add(_normalize_concept(str(d)).lower())
                matched = fp_norm_set & q_norms
                if matched:
                    # Return canonical display names ordered by frequency
                    freq = concepts.get("top_diagnoses", {})
                    freq.update(concepts.get("top_drugs", {}))
                    q["fingerprint_concepts"] = sorted(
                        [fp_norm_map[m] for m in matched],
                        key=lambda c: freq.get(c, 0), reverse=True
                    )
            except (json.JSONDecodeError, TypeError, AttributeError):
                pass

    top_articles = match_top_articles(perf, db_path, count=15, items=items, qid_map=qid_map)

    # --- Missed item reference (for report appendix) ---
    missed_detail = fetch_missed_items_detail(items, qid_map, db_path)

    return {
        # Identity
        "resident":             parsed_data["resident"],
        "exam_year":            exam_year,
        "deleted_items":        parsed_data.get("deleted_items", []),
        "analysis_version":     "3.1",

        # Score interpretation (plain-language framing — NEW v3.1)
        "score_interpretation": score_interp,

        # Core layers
        "performance":          perf,
        "thresholds":           thresholds,
        "difficulty_profile":   difficulty,
        "concept_clustering":   concepts,        # NEW (replaces subcategory_analysis)
        "spatial_clustering":   clustering,
        "cross_dimensional_patterns": patterns,
        "yield_priorities":     priorities,

        # DB-connected layers
        "icd10_weakness_map":   icd10_map,       # REBUILT (direct)
        "pathway_gap_map":      pathway_map,     # NEW

        # Output
        "practice_questions":   practice_qs,     # REBUILT (both banks, globally ranked)
        "top_articles":         top_articles,
        "missed_items_detail":  missed_detail,   # NEW: full question data for appendix

        # Legacy compatibility keys (for v1 HTML report builder)
        "body_systems_available": parsed_data.get("body_systems_found", []),
    }


# ---------------------------------------------------------------------------
# Export utility
# ---------------------------------------------------------------------------

def export_analysis(analysis: dict, output_path: str):
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False, default=str)
    print(f"  Analysis exported: {output_path}")
