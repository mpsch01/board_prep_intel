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
    "Psychiatric/Behavioral":  ["Psychogenic"],
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
        if i.get("body_system") and i.get("blueprint"):
            key = f"{i['body_system']} × {i['blueprint']}"
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
    Uses concept_tags JSON from both question banks via the QID map.
    Also queries aafp_questions for any AAFP-side matches (future-proofing).
    """
    missed_items  = [i for i in items if not i["correct"]]
    missed_qids   = [qid_map[i["item"]] for i in missed_items if i["item"] in qid_map]

    diagnoses  = Counter()
    drugs      = Counter()
    guidelines = Counter()
    items_matched = 0

    # QID tracking per concept — for report appendix/fingerprint reference
    dx_qids    = defaultdict(list)
    drug_qids  = defaultdict(list)
    guide_qids = defaultdict(list)

    if missed_qids and db_path:
        db = sqlite3.connect(db_path)
        db.row_factory = sqlite3.Row

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
                            diagnoses[d] += 1
                            dx_qids[d].append(qid)
                        for d in tags.get("drugs", []):
                            drugs[d] += 1
                            drug_qids[d].append(qid)
                        for g in tags.get("guidelines", []):
                            guidelines[g] += 1
                            guide_qids[g].append(qid)
                        items_matched += 1
                    except (json.JSONDecodeError, TypeError):
                        pass
        db.close()

    # Recurring themes = appears ≥2 times
    recurring_diagnoses  = {k: v for k, v in diagnoses.items()  if v >= 2}
    recurring_drugs      = {k: v for k, v in drugs.items()      if v >= 2}

    return {
        "top_diagnoses":     dict(diagnoses.most_common(15)),
        "top_drugs":         dict(drugs.most_common(15)),
        "top_guidelines":    dict(guidelines.most_common(10)),
        "recurring_diagnoses": dict(sorted(recurring_diagnoses.items(), key=lambda x: x[1], reverse=True)),
        "recurring_drugs":   dict(sorted(recurring_drugs.items(), key=lambda x: x[1], reverse=True)),
        # QID maps — lets the report builder show which question IDs drove each concept
        "concept_qid_map": {
            "diagnoses":  dict(dx_qids),
            "drugs":      dict(drug_qids),
            "guidelines": dict(guide_qids),
        },
        "items_matched":     items_matched,
        "items_queried":     len(missed_qids),
        "coverage_pct":      round(items_matched / len(missed_qids) * 100, 1) if missed_qids else 0,
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
    patterns     = []
    overall_rate = perf["overall"]["pct"] / 100

    # Blueprint consistency gap
    bp_rates = {k: v["rate"] for k, v in perf["blueprint"].items()}
    if bp_rates:
        best_bp  = max(bp_rates, key=bp_rates.get)
        worst_bp = min(bp_rates, key=bp_rates.get)
        gap      = bp_rates[best_bp] - bp_rates[worst_bp]
        if gap > 0.15:
            patterns.append({
                "type": "blueprint_gap",
                "description": (
                    f"Consistent {gap*100:.0f}-point gap: "
                    f"{best_bp} ({bp_rates[best_bp]*100:.0f}%) vs "
                    f"{worst_bp} ({bp_rates[worst_bp]*100:.0f}%)"
                ),
                "best": best_bp, "worst": worst_bp, "gap": round(gap, 3),
            })

    # Difficulty calibration by score band
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
    if easy_rate is not None and mid_rate is not None and easy_rate < mid_rate:
        patterns.append({
            "type": "difficulty_inversion",
            "description": (
                f"Paradoxical: accuracy on easy items ({easy_rate*100:.0f}%) "
                f"lower than mid-difficulty ({mid_rate*100:.0f}%). "
                f"Possible second-guessing pattern."
            ),
            "easy_rate": easy_rate, "mid_rate": mid_rate,
        })

    # Diffuse weakness
    bs_rates    = {k: v["rate"] for k, v in perf.get("body_system", {}).items()}
    weak_systems = [k for k, v in bs_rates.items() if v < overall_rate - 0.10]
    if len(weak_systems) >= 3:
        patterns.append({
            "type": "diffuse_weakness",
            "description": (
                f"Weakness spread across {len(weak_systems)} body systems. "
                f"Broad knowledge gaps rather than isolated deficits."
            ),
            "weak_systems": weak_systems,
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

    for key, p in perf.get("cross_tab", {}).items():
        if p["rate"] < TARGET_RATE and p["total"] >= 3:
            gap         = TARGET_RATE - p["rate"]
            recoverable = round(gap * p["total"], 1)
            priorities.append({
                "dimension":        key,
                "dimension_type":   "cross_tab",
                "current_rate":     p["rate"],
                "target_rate":      TARGET_RATE,
                "item_count":       p["total"],
                "recoverable_items": recoverable,
                "priority_score":   round(recoverable * 1.5, 2),
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
        SELECT icd10_code, icd10_desc, pathway_role,
               COUNT(DISTINCT article_id) as article_count
        FROM clinical_pathways
        WHERE icd10_code IN ({ph})
        GROUP BY icd10_code, pathway_role
        ORDER BY icd10_code, article_count DESC
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
                  selected_qids: set, limit: int = 60) -> list:
    """Direct blueprint + body_system match from both banks."""
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

    # ITE bank
    ite_where, ite_params = _build_where("q", use_merged=True)
    sql_ite = f"""
        SELECT {_ITE_Q_COLS},
               COUNT(DISTINCT xa.article_id) AS linked_articles
        FROM questions q
        LEFT JOIN qid_art_xref xa ON q.qid = xa.qid AND xa.article_id != 'ART-0001'
        WHERE {" AND ".join(ite_where)} {excl_sql}
        GROUP BY q.qid
        ORDER BY linked_articles DESC
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


def match_practice_questions_v3(perf: dict, priorities: list, qid_map: dict,
                                 items: list, db_path: str,
                                 target_count: int = 20,
                                 current_exam_year: int = None) -> list:
    """
    Select and globally rank practice questions from both ITE + AAFP banks.

    Strategy:
      1. For each top priority dimension, gather candidates from Tier 1 + 2
      2. If total candidates < target, invoke Tier 3 (vector similarity)
      3. Score all candidates globally with relevance_score
      4. Deduplicate, sort by relevance_score, return top target_count
      5. Every question labeled with source_bank + source_label
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

    # Tier 1 + Tier 1b (article co-link) + Tier 2 (ICD-10 seeded) per dimension
    for priority in active:
        dim            = priority["dimension"]
        dim_type       = priority["dimension_type"]
        priority_score = priority["priority_score"]

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

    # Concept-tag overlap bonus — applied in Python to avoid SQLite json_each
    # version dependency.  Candidates sharing concept tags with the resident's
    # specific wrong answers in their targeting dimension score higher.
    for qid, cand in all_candidates.items():
        try:
            raw_tags = cand.get("concept_tags")
            if not raw_tags:
                continue
            cand_tags = set(json.loads(raw_tags)) if isinstance(raw_tags, str) else set(raw_tags)
            dim_tags  = wrong_meta_by_dim.get(cand.get("targeting"), {}).get("concept_tags", set())
            overlap   = len(cand_tags & dim_tags)
            if overlap:
                cand["relevance_score"] = round(cand["relevance_score"] + 0.4 * min(overlap, 3), 3)
        except (json.JSONDecodeError, TypeError, AttributeError):
            pass

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

def match_top_articles(perf: dict, db_path: str, count: int = 5) -> list:
    """Highest-citation articles linked to weak dimensions. Both banks."""
    if not db_path:
        return []

    weak_systems    = [name for name, p in perf.get("body_system", {}).items() if p["rate"] < 0.70]
    weak_blueprints = [BLUEPRINT_PDF_TO_DB.get(name, name)
                       for name, p in perf.get("blueprint", {}).items() if p["rate"] < 0.70]

    db_system_names = []
    for ws in weak_systems:
        db_system_names.extend(BODYSYSTEM_PDF_TO_DB.get(ws, [ws]))

    params    = []
    clauses   = []
    if db_system_names:
        bs_ph = ",".join(["?"] * len(db_system_names))
        clauses.append(f"(q.body_system_merged IN ({bs_ph}) OR q.body_system IN ({bs_ph}))")
        params.extend(db_system_names * 2)
    if weak_blueprints:
        bp_ph = ",".join(["?"] * len(weak_blueprints))
        clauses.append(f"q.blueprint IN ({bp_ph})")
        params.extend(weak_blueprints)

    where = " OR ".join(clauses) if clauses else "1=1"

    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row

    # ITE-linked articles
    sql = f"""
        SELECT a.article_id, a.title, a.author1, a.year, a.source_type,
               a.citation_count, a.unique_years, a.exam_years, a.clean_ref,
               COUNT(DISTINCT q.qid) AS weak_area_links
        FROM articles a
        JOIN qid_art_xref qa ON a.article_id = qa.article_id
        JOIN questions q     ON qa.qid = q.qid
        WHERE ({where})
          AND a.source_type != 'stub'
          AND a.article_id  != 'ART-0001'
          AND a.citation_count >= 2
        GROUP BY a.article_id
        ORDER BY a.citation_count DESC, weak_area_links DESC
        LIMIT ?
    """
    rows = db.execute(sql, params + [count]).fetchall()
    db.close()

    return [dict(r) for r in rows]


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
    difficulty  = difficulty_profile(items, qid_map)
    concepts    = concept_clustering(items, qid_map, db_path)
    clustering  = spatial_clustering(items)
    patterns    = cross_dimensional_patterns(items, perf)
    priorities  = yield_weighted_priorities(perf, ref)

    # --- DB-connected layers ---
    icd10_map   = icd10_weakness_map(items, qid_map, db_path)
    pathway_map = pathway_gap_map(icd10_map, db_path)

    # --- Practice questions + top articles ---
    practice_qs  = match_practice_questions_v3(perf, priorities, qid_map,
                                                items, db_path, question_count,
                                                current_exam_year=exam_year)
    top_articles = match_top_articles(perf, db_path)

    # --- Missed item reference (for report appendix) ---
    missed_detail = fetch_missed_items_detail(items, qid_map, db_path)

    return {
        # Identity
        "resident":             parsed_data["resident"],
        "exam_year":            exam_year,
        "deleted_items":        parsed_data.get("deleted_items", []),
        "analysis_version":     "3.0",

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
