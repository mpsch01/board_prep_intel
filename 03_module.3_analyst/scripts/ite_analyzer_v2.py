#!/usr/bin/env python3
"""
ITE Score Analyzer v2 — Turbocharged Edition

Multi-layer analysis engine with plugin architecture.

CORE LAYERS:
  1. Difficulty Profiling — classify misses by difficulty tier
  2. Subcategory Decomposition — performance by subcategory within body system
  3. Spatial Clustering — detect concentrated vs scattered weakness patterns
  4. Cross-Dimensional Pattern Detection — skill-type vs content-type weakness
  5. Yield-Weighted Prioritization — rank weaknesses by recoverable points

PLUGINS (modular, toggleable):
  P1. Concept Fingerprinting — cluster missed items by concept_tags
  P2. Explanation Mining — Claude API thematic analysis of missed explanations
  P3. ICD-10 Weakness Map — map weaknesses to ICD-10 hierarchies
  P5. Historical Trend Detector — year-over-year comparison
  P6. Cohort Comparator — program-level aggregation

THRESHOLD SYSTEM:
  Tier 1: FMCE pass probability from scaled score
  Tier 2: Relative performance (vs own mean ± 1 SD)
  Tier 3: Statistical confidence (SEM-aware flagging)
"""

import json
import sqlite3
import math
from collections import defaultdict, Counter
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Reference data loader
# ---------------------------------------------------------------------------

def load_abfm_reference(ref_path: str = None) -> dict:
    """Load ABFM reference data (benchmarks, conversion tables, SEM, etc.)."""
    if ref_path is None:
        ref_path = Path(__file__).parent / "abfm_reference_2025.json"
    with open(ref_path, encoding="utf-8") as f:
        return json.load(f)


def raw_to_scaled(raw_correct: int, ref: dict) -> int:
    """Convert raw score to ABFM scaled score."""
    lookup = ref.get("raw_to_scaled_lookup", [])
    if not lookup:
        return 0
    idx = max(0, min(raw_correct, len(lookup) - 1))
    return lookup[idx]


def classify_pass_tier(scaled: int, ref: dict) -> dict:
    """Classify a scaled score into FMCE pass probability tier."""
    tiers = ref.get("pass_probability_tiers", {})
    for tier_name, tier_def in tiers.items():
        lo = tier_def.get("scaled_min", 0)
        hi = tier_def.get("scaled_max", 9999)
        if lo <= scaled <= hi:
            return {"tier": tier_name, "description": tier_def["description"], "scaled": scaled}
    return {"tier": "unknown", "description": "", "scaled": scaled}


# ---------------------------------------------------------------------------
# Name mappings (same as v1, centralized)
# ---------------------------------------------------------------------------

BLUEPRINT_PDF_TO_DB = {
    "Acute Care": "Acute Care and Diagnosis",
    "Chronic Care": "Chronic Care Management",
    "Emergent/Urgent": "Emergent and Urgent Care",
    "Preventive": "Preventive Care",
    "Foundations": "Foundations of Care",
}
BLUEPRINT_DB_TO_PDF = {v: k for k, v in BLUEPRINT_PDF_TO_DB.items()}

BODYSYSTEM_PDF_TO_DB = {
    "Cardiovascular": ["Cardiovascular"],
    "Injuries/Musculoskeletal": ["Musculoskeletal"],
    "Respiratory": ["Respiratory"],
    "Psychiatric/Behavioral": ["Psychogenic"],
    "Sexual and Reproductive": ["Reproductive: Female", "Reproductive: Male"],
    "Endocrine": ["Endocrine"],
    "Gastrointestinal": ["Gastrointestinal"],
    "Hematologic/Immune": ["Hematologic/ Immune"],
    "Integumentary": ["Integumentary"],
    "Nephrologic": ["Nephrologic"],
    "Neurologic": ["Neurologic"],
    "Nonspecific": ["Nonspecific"],
    "Patient-Based Systems": ["Patient-Based Systems"],
    "Population-Based Care": ["Population-Based Care"],
    "Special Sensory": ["Special Sensory"],
}
BODYSYSTEM_DB_TO_PDF = {}
for pdf_name, db_names in BODYSYSTEM_PDF_TO_DB.items():
    for db_name in db_names:
        BODYSYSTEM_DB_TO_PDF[db_name] = pdf_name


# ---------------------------------------------------------------------------
# CORE LAYER 1: Difficulty Profiling
# ---------------------------------------------------------------------------

DIFFICULTY_TIERS = {
    "easy_miss":  {"min_score": 700, "label": "Easy Miss (score ≥700)", "interpretation": "Most examinees get these right — genuine knowledge gap"},
    "mid_range":  {"min_score": 300, "max_score": 699, "label": "Mid-Range (300-699)", "interpretation": "High-yield study targets — greatest ROI"},
    "hard_miss":  {"max_score": 299, "label": "Hard Miss (score <300)", "interpretation": "Most examinees miss these — low-yield to chase"},
}

def difficulty_profile(items: list) -> dict:
    """Classify missed items by difficulty tier, overall and per dimension."""
    missed = [i for i in items if not i["correct"]]

    def _tier(score):
        if score >= 700: return "easy_miss"
        if score >= 300: return "mid_range"
        return "hard_miss"

    # Overall difficulty distribution
    overall = Counter(_tier(i["score"]) for i in missed)

    # Per blueprint
    by_blueprint = defaultdict(lambda: Counter())
    for i in missed:
        by_blueprint[i.get("blueprint", "Unknown")][_tier(i["score"])] += 1

    # Per body system
    by_bodysystem = defaultdict(lambda: Counter())
    for i in missed:
        if i.get("body_system"):
            by_bodysystem[i["body_system"]][_tier(i["score"])] += 1

    # Flag: easy misses are the highest-priority items
    easy_misses = [i for i in missed if i["score"] >= 700]
    easy_misses.sort(key=lambda x: x["score"], reverse=True)

    return {
        "overall": dict(overall),
        "by_blueprint": {k: dict(v) for k, v in by_blueprint.items()},
        "by_bodysystem": {k: dict(v) for k, v in by_bodysystem.items()},
        "easy_misses": [{"item": i["item"], "score": i["score"],
                         "blueprint": i.get("blueprint"), "body_system": i.get("body_system")}
                        for i in easy_misses],
        "easy_miss_count": len(easy_misses),
        "mid_range_count": overall.get("mid_range", 0),
        "hard_miss_count": overall.get("hard_miss", 0),
        "tier_definitions": DIFFICULTY_TIERS,
    }


# ---------------------------------------------------------------------------
# CORE LAYER 2: Subcategory Decomposition
# ---------------------------------------------------------------------------

def subcategory_decomposition(items: list, db_path: str = None) -> dict:
    """
    Performance by named subcategory (Management, Pharmacology, Diagnosis, etc.)
    within each blueprint. Uses item→QID→DB lookup to resolve subcategory names.
    Falls back to sub_col_index if DB is unavailable.
    """
    # --- Resolve named subcategories via DB ---
    item_subcategory = {}  # item_number → subcategory name
    if db_path:
        db = sqlite3.connect(db_path)
        db.row_factory = sqlite3.Row
        year = 2025  # TODO: make dynamic from parsed_data
        item_numbers = [i["item"] for i in items]
        qid_patterns = [f"QID-{year}-{item:04d}" for item in item_numbers]
        # Batch lookup
        batch_size = 100
        for start in range(0, len(qid_patterns), batch_size):
            batch = qid_patterns[start:start + batch_size]
            items_batch = item_numbers[start:start + batch_size]
            ph = ",".join(["?"] * len(batch))
            rows = db.execute(
                f"SELECT qid, subcategory FROM questions WHERE qid IN ({ph})", batch
            ).fetchall()
            qid_to_subcat = {r["qid"]: r["subcategory"] for r in rows if r["subcategory"]}
            for item_num, qid in zip(items_batch, batch):
                if qid in qid_to_subcat:
                    item_subcategory[item_num] = qid_to_subcat[qid]
        db.close()

    # --- Performance by named subcategory within each blueprint ---
    by_bp_subcat = defaultdict(lambda: defaultdict(lambda: {"correct": 0, "total": 0}))
    for i in items:
        bp = i.get("blueprint")
        if bp is None:
            continue
        subcat = item_subcategory.get(i["item"], f"subcol_{i.get('sub_col_index', '?')}")
        by_bp_subcat[bp][subcat]["total"] += 1
        if i["correct"]:
            by_bp_subcat[bp][subcat]["correct"] += 1

    result = {}
    for bp in sorted(by_bp_subcat.keys()):
        bp_result = {}
        for subcat in sorted(by_bp_subcat[bp].keys()):
            c = by_bp_subcat[bp][subcat]
            rate = c["correct"] / c["total"] if c["total"] else 0
            bp_result[subcat] = {
                "correct": c["correct"], "total": c["total"],
                "rate": round(rate, 3),
            }
        result[bp] = bp_result

    # --- Overall subcategory performance (across all blueprints) ---
    overall_subcat = defaultdict(lambda: {"correct": 0, "total": 0})
    for i in items:
        subcat = item_subcategory.get(i["item"])
        if subcat:
            overall_subcat[subcat]["total"] += 1
            if i["correct"]:
                overall_subcat[subcat]["correct"] += 1

    overall_result = {
        k: {**v, "rate": round(v["correct"] / v["total"], 3) if v["total"] else 0}
        for k, v in sorted(overall_subcat.items(), key=lambda x: x[1]["total"], reverse=True)
    }

    return {
        "by_blueprint_subcategory": result,
        "overall_subcategory": overall_result,
        "items_resolved": len(item_subcategory),
        "items_total": len(items),
    }


# ---------------------------------------------------------------------------
# CORE LAYER 3: Spatial Clustering
# ---------------------------------------------------------------------------

def spatial_clustering(items: list) -> dict:
    """
    Detect whether misses are concentrated or scattered.
    Analyze subcol concentration, consecutive miss runs, and score-band clustering.
    """
    missed = [i for i in items if not i["correct"]]
    all_sorted = sorted(items, key=lambda x: x["item"])

    # Subcol concentration per blueprint
    subcol_concentration = {}
    for bp in set(i.get("blueprint") for i in missed if i.get("blueprint")):
        bp_misses = [i for i in missed if i.get("blueprint") == bp]
        subcols = Counter(i.get("sub_col_index", -1) for i in bp_misses)
        total_misses = len(bp_misses)
        # Herfindahl index: 1.0 = all in one subcol, ~0.1 = evenly spread
        hhi = sum((c / total_misses) ** 2 for c in subcols.values()) if total_misses else 0
        dominant = subcols.most_common(1)[0] if subcols else (None, 0)
        subcol_concentration[bp] = {
            "total_misses": total_misses,
            "unique_subcols": len(subcols),
            "herfindahl": round(hhi, 3),
            "concentrated": hhi > 0.4,
            "dominant_subcol": dominant[0],
            "dominant_count": dominant[1],
        }

    # Consecutive miss runs (by item number order)
    runs = []
    current_run = []
    for i in all_sorted:
        if not i["correct"]:
            current_run.append(i["item"])
        else:
            if len(current_run) >= 3:
                runs.append(current_run)
            current_run = []
    if len(current_run) >= 3:
        runs.append(current_run)

    # Score-band clustering: do misses cluster in a particular difficulty range?
    miss_scores = [i["score"] for i in missed]
    if miss_scores:
        score_mean = sum(miss_scores) / len(miss_scores)
        score_sd = (sum((s - score_mean) ** 2 for s in miss_scores) / len(miss_scores)) ** 0.5
    else:
        score_mean = 0
        score_sd = 0

    return {
        "subcol_concentration": subcol_concentration,
        "consecutive_miss_runs": runs,
        "longest_run": max(len(r) for r in runs) if runs else 0,
        "miss_score_mean": round(score_mean),
        "miss_score_sd": round(score_sd),
    }


# ---------------------------------------------------------------------------
# CORE LAYER 4: Cross-Dimensional Pattern Detection
# ---------------------------------------------------------------------------

def cross_dimensional_patterns(items: list, perf: dict) -> dict:
    """
    Detect patterns that span dimensions.
    - Skill-type weakness (e.g., Pharmacology weak across all systems)
    - Blueprint consistency (e.g., always better at Chronic than Acute)
    - Difficulty calibration (e.g., accuracy drops for items > threshold)
    """
    patterns = []

    # Pattern: Subcol consistency across blueprints
    # Do certain subcol indices perform consistently worse?
    subcol_rates = defaultdict(lambda: {"correct": 0, "total": 0})
    for i in items:
        sci = i.get("sub_col_index")
        if sci is not None:
            subcol_rates[sci]["total"] += 1
            if i["correct"]:
                subcol_rates[sci]["correct"] += 1

    overall_rate = perf["overall"]["pct"] / 100
    for sci, counts in sorted(subcol_rates.items()):
        if counts["total"] >= 5:
            rate = counts["correct"] / counts["total"]
            if rate < overall_rate - 0.15:
                patterns.append({
                    "type": "subcol_weakness",
                    "description": f"Subcategory column {sci} underperforms overall by {(overall_rate - rate)*100:.0f} percentage points ({counts['correct']}/{counts['total']} = {rate*100:.0f}%)",
                    "subcol_index": sci,
                    "rate": round(rate, 3),
                    "gap": round(overall_rate - rate, 3),
                })

    # Pattern: Blueprint consistency across body systems
    bp_rates = {k: v["rate"] for k, v in perf["blueprint"].items()}
    if bp_rates:
        best_bp = max(bp_rates, key=bp_rates.get)
        worst_bp = min(bp_rates, key=bp_rates.get)
        gap = bp_rates[best_bp] - bp_rates[worst_bp]
        if gap > 0.15:
            patterns.append({
                "type": "blueprint_gap",
                "description": f"Consistent {(gap*100):.0f}-point gap between {best_bp} ({bp_rates[best_bp]*100:.0f}%) and {worst_bp} ({bp_rates[worst_bp]*100:.0f}%)",
                "best": best_bp,
                "worst": worst_bp,
                "gap": round(gap, 3),
            })

    # Pattern: Difficulty calibration — accuracy by score bands
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

    # Check for "second-guessing" pattern: low accuracy on easy items
    easy_band_rate = band_rates.get(800, band_rates.get(1000, None))
    mid_band_rate = band_rates.get(400, band_rates.get(600, None))
    if easy_band_rate is not None and mid_band_rate is not None:
        if easy_band_rate < mid_band_rate:
            patterns.append({
                "type": "difficulty_inversion",
                "description": f"Paradoxical: accuracy on easy items ({easy_band_rate*100:.0f}%) is lower than mid-difficulty ({mid_band_rate*100:.0f}%). May indicate second-guessing on obvious answers.",
                "easy_rate": easy_band_rate,
                "mid_rate": mid_band_rate,
            })

    # Pattern: Body system spread — concentrated vs diffuse weakness
    bs_rates = {k: v["rate"] for k, v in perf.get("body_system", {}).items()}
    if bs_rates:
        weak_systems = [k for k, v in bs_rates.items() if v < overall_rate - 0.10]
        if len(weak_systems) >= 3:
            patterns.append({
                "type": "diffuse_weakness",
                "description": f"Weakness is spread across {len(weak_systems)} body systems, not concentrated. Suggests broad knowledge gaps rather than isolated deficits.",
                "weak_systems": weak_systems,
            })

    return {
        "patterns": patterns,
        "accuracy_by_difficulty_band": band_rates,
    }


# ---------------------------------------------------------------------------
# CORE LAYER 5: Yield-Weighted Prioritization
# ---------------------------------------------------------------------------

def yield_weighted_priorities(perf: dict, ref: dict) -> list:
    """
    Rank each weak dimension by recoverable points.
    Points recoverable = (target_rate - current_rate) × item_count
    """
    TARGET_RATE = 0.70
    priorities = []

    # Blueprint priorities (highest item counts = highest yield)
    for name, p in perf.get("blueprint", {}).items():
        if p["rate"] < TARGET_RATE:
            gap = TARGET_RATE - p["rate"]
            recoverable = round(gap * p["total"], 1)
            # Weight by blueprint exam percentage
            full_name = BLUEPRINT_PDF_TO_DB.get(name, name)
            weight_pct = ref.get("blueprint_weights", {}).get(full_name, {}).get("pct", 10)
            priorities.append({
                "dimension": name,
                "dimension_type": "blueprint",
                "current_rate": p["rate"],
                "target_rate": TARGET_RATE,
                "item_count": p["total"],
                "recoverable_items": recoverable,
                "exam_weight_pct": weight_pct,
                "priority_score": round(recoverable * (weight_pct / 10), 2),
            })

    # Body system priorities
    for name, p in perf.get("body_system", {}).items():
        if p["rate"] < TARGET_RATE:
            gap = TARGET_RATE - p["rate"]
            recoverable = round(gap * p["total"], 1)
            # SEM check — is this statistically meaningful?
            sem = ref.get("bodysystem_sem_page1", {}).get(name, 999)
            statistically_meaningful = p["total"] >= 8  # rough heuristic
            priorities.append({
                "dimension": name,
                "dimension_type": "body_system",
                "current_rate": p["rate"],
                "target_rate": TARGET_RATE,
                "item_count": p["total"],
                "recoverable_items": recoverable,
                "sem": sem,
                "statistically_meaningful": statistically_meaningful,
                "priority_score": round(recoverable * (2 if statistically_meaningful else 0.5), 2),
            })

    # Cross-tab priorities
    for key, p in perf.get("cross_tab", {}).items():
        if p["rate"] < TARGET_RATE and p["total"] >= 3:
            gap = TARGET_RATE - p["rate"]
            recoverable = round(gap * p["total"], 1)
            priorities.append({
                "dimension": key,
                "dimension_type": "cross_tab",
                "current_rate": p["rate"],
                "target_rate": TARGET_RATE,
                "item_count": p["total"],
                "recoverable_items": recoverable,
                "priority_score": round(recoverable * 1.5, 2),  # cross-tab gets bonus for specificity
            })

    priorities.sort(key=lambda x: x["priority_score"], reverse=True)
    return priorities


# ---------------------------------------------------------------------------
# THRESHOLD SYSTEM
# ---------------------------------------------------------------------------

def compute_thresholds(perf: dict, ref: dict, pgy_level: str = "All") -> dict:
    """
    Three-tier threshold system:
      Tier 1: FMCE pass probability from scaled score
      Tier 2: Relative performance vs own mean (± 1 SD)
      Tier 3: Statistical confidence (SEM-aware)
    """
    overall = perf["overall"]
    scaled = raw_to_scaled(overall["correct"], ref)
    pass_tier = classify_pass_tier(scaled, ref)

    # National context
    benchmark = ref.get("national_benchmarks", {}).get(pgy_level, {})
    national_mean = benchmark.get("mean_scaled", 434)
    national_sd = benchmark.get("sd", 85)
    percentile_est = None
    if national_sd > 0:
        z = (scaled - national_mean) / national_sd
        # Approximate percentile from z-score
        percentile_est = round(50 * (1 + math.erf(z / math.sqrt(2))), 1)

    # Tier 2: Relative performance within resident's own dimensions
    all_rates = [p["rate"] for p in perf.get("blueprint", {}).values()]
    all_rates += [p["rate"] for p in perf.get("body_system", {}).values()]
    if all_rates:
        personal_mean = sum(all_rates) / len(all_rates)
        personal_sd = (sum((r - personal_mean) ** 2 for r in all_rates) / len(all_rates)) ** 0.5
    else:
        personal_mean = overall["pct"] / 100
        personal_sd = 0.1

    relative_thresholds = {
        "personal_mean": round(personal_mean, 3),
        "personal_sd": round(personal_sd, 3),
        "relative_weakness": round(personal_mean - personal_sd, 3),
        "relative_strength": round(personal_mean + personal_sd, 3),
    }

    # Classify each dimension
    dimension_classifications = {}
    for dim_type in ["blueprint", "body_system"]:
        for name, p in perf.get(dim_type, {}).items():
            if p["rate"] < personal_mean - personal_sd:
                classification = "relative_weakness"
            elif p["rate"] > personal_mean + personal_sd:
                classification = "relative_strength"
            else:
                classification = "within_range"
            dimension_classifications[name] = {
                "rate": p["rate"],
                "classification": classification,
                "items": p["total"],
            }

    # Tier 3: SEM awareness
    sem_flags = {}
    for name in perf.get("blueprint", {}):
        full_name = BLUEPRINT_PDF_TO_DB.get(name, name)
        sem = ref.get("blueprint_sem", {}).get(full_name, None)
        if sem:
            sem_flags[name] = {
                "sem": sem,
                "reliable": sem <= 100,
                "note": "Statistically reliable" if sem <= 100 else "Large SEM — interpret as hypothesis only"
            }
    for name in perf.get("body_system", {}):
        sem = ref.get("bodysystem_sem_page1", {}).get(name, None)
        if sem:
            sem_flags[name] = {
                "sem": sem,
                "reliable": sem <= 150,
                "note": "Statistically reliable" if sem <= 150 else "Large SEM — interpret as hypothesis only"
            }

    return {
        "tier1_pass_probability": {
            "scaled_score": scaled,
            "pass_tier": pass_tier,
            "national_mean": national_mean,
            "national_sd": national_sd,
            "percentile_estimate": percentile_est,
            "vs_mps": scaled - ref.get("exam_specs", {}).get("minimum_passing_standard", 380),
        },
        "tier2_relative": {
            "thresholds": relative_thresholds,
            "classifications": dimension_classifications,
        },
        "tier3_sem": sem_flags,
    }


# ---------------------------------------------------------------------------
# BASIC PERFORMANCE (same as v1, needed by layers above)
# ---------------------------------------------------------------------------

def basic_performance(items: list) -> dict:
    """Calculate per-dimension performance rates and cross-tab."""
    def _dim_perf(items_list, key):
        groups = defaultdict(lambda: {"correct": 0, "total": 0})
        for i in items_list:
            val = i.get(key)
            if val is None: continue
            groups[val]["total"] += 1
            if i["correct"]: groups[val]["correct"] += 1
        return {k: {"correct": v["correct"], "total": v["total"],
                     "rate": round(v["correct"]/v["total"], 3) if v["total"] else 0}
                for k, v in sorted(groups.items())}

    total = len(items)
    correct = sum(1 for i in items if i["correct"])

    blueprint = _dim_perf(items, "blueprint")
    body_system = _dim_perf([i for i in items if i.get("body_system")], "body_system")

    # Cross-tab
    cross_tab = defaultdict(lambda: {"correct": 0, "total": 0})
    for i in items:
        if i.get("body_system") and i.get("blueprint"):
            key = f"{i['body_system']} \u00d7 {i['blueprint']}"
            cross_tab[key]["total"] += 1
            if i["correct"]: cross_tab[key]["correct"] += 1

    cross_tab = {k: {**v, "rate": round(v["correct"]/v["total"], 3) if v["total"] else 0}
                 for k, v in sorted(cross_tab.items())}

    return {
        "overall": {"total": total, "correct": correct, "incorrect": total - correct,
                     "pct": round(correct / total * 100, 1) if total else 0},
        "blueprint": blueprint,
        "body_system": body_system,
        "cross_tab": cross_tab,
    }


# ---------------------------------------------------------------------------
# PLUGIN 1: Concept Fingerprinting
# ---------------------------------------------------------------------------

def plugin_concept_fingerprint(items: list, db_path: str) -> dict:
    """
    Mine concept_tags from missed items' linked questions in the DB.
    Clusters missed items by diagnosis, drug, and guideline themes.
    """
    missed_items = [i["item"] for i in items if not i["correct"]]
    if not missed_items:
        return {"diagnoses": {}, "drugs": {}, "guidelines": {}}

    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row

    # Map item numbers to QIDs (item N → QID-{year}-{N:04d})
    # We'll try matching by the exam year from the analysis
    year = 2025  # TODO: make dynamic
    qid_patterns = [f"QID-{year}-{item:04d}" for item in missed_items]
    placeholders = ",".join(["?"] * len(qid_patterns))

    rows = db.execute(f"""
        SELECT qid, concept_tags, body_system, subcategory, blueprint
        FROM questions WHERE qid IN ({placeholders})
    """, qid_patterns).fetchall()

    diagnoses = Counter()
    drugs = Counter()
    guidelines = Counter()
    subcategories = Counter()

    for row in rows:
        tags_raw = row["concept_tags"]
        if tags_raw:
            try:
                tags = json.loads(tags_raw)
                for d in tags.get("diagnoses", []):
                    diagnoses[d] += 1
                for d in tags.get("drugs", []):
                    drugs[d] += 1
                for g in tags.get("guidelines", []):
                    guidelines[g] += 1
            except (json.JSONDecodeError, TypeError):
                pass
        if row["subcategory"]:
            subcategories[row["subcategory"]] += 1

    db.close()

    # Find concepts that appear 2+ times (recurring themes)
    return {
        "diagnoses": dict(diagnoses.most_common(15)),
        "drugs": dict(drugs.most_common(15)),
        "guidelines": dict(guidelines.most_common(10)),
        "subcategory_distribution": dict(subcategories.most_common()),
        "items_matched": len(rows),
        "items_queried": len(missed_items),
    }


# ---------------------------------------------------------------------------
# PLUGIN 3: ICD-10 Weakness Map
# ---------------------------------------------------------------------------

def plugin_icd10_map(items: list, db_path: str) -> dict:
    """
    Map weaknesses to ICD-10 codes via the article_icd10 table.
    Chain: missed items → linked articles → ICD-10 codes → chapter rollup.
    """
    missed_items = [i["item"] for i in items if not i["correct"]]
    if not missed_items:
        return {"icd10_clusters": [], "chapter_summary": {}}

    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row

    year = 2025
    qid_patterns = [f"QID-{year}-{item:04d}" for item in missed_items]
    placeholders = ",".join(["?"] * len(qid_patterns))

    # Chain: QID → article → ICD-10
    rows = db.execute(f"""
        SELECT DISTINCT ai.icd10_code, ai.icd10_desc, ai.relevance,
               ir.chapter, ir.chapter_desc,
               qa.qid
        FROM qid_art_xref qa
        JOIN article_icd10 ai ON qa.article_id = ai.article_id
        LEFT JOIN icd10_rollup ir ON SUBSTR(ai.icd10_code, 1, 3) = ir.parent_code
                                   OR SUBSTR(ai.icd10_code, 1, 1) = ir.chapter
        WHERE qa.qid IN ({placeholders})
          AND qa.article_id != 'ART-0001'
          AND ai.relevance = 'primary'
    """, qid_patterns).fetchall()

    db.close()

    icd10_counts = Counter()
    chapter_counts = Counter()
    code_details = {}

    for row in rows:
        code = row["icd10_code"]
        icd10_counts[code] += 1
        if code not in code_details:
            code_details[code] = {"description": row["icd10_desc"], "chapter": row["chapter"], "chapter_desc": row["chapter_desc"]}
        if row["chapter"]:
            chapter_counts[row["chapter"]] += 1

    return {
        "icd10_clusters": [{"code": code, "count": count, **code_details.get(code, {})}
                           for code, count in icd10_counts.most_common(20)],
        "chapter_summary": dict(chapter_counts.most_common()),
        "total_codes_found": len(icd10_counts),
    }


# ---------------------------------------------------------------------------
# PLUGIN 6: Cohort Comparator (stub — requires multiple residents)
# ---------------------------------------------------------------------------

def plugin_cohort_compare(all_analyses: list) -> dict:
    """
    Compare multiple residents' analyses to identify program-level patterns.
    Input: list of analysis dicts from multiple residents.
    """
    if len(all_analyses) < 2:
        return {"status": "insufficient_data", "message": "Need ≥2 residents for cohort comparison"}

    # Aggregate blueprint performance across residents
    bp_aggregate = defaultdict(lambda: {"rates": [], "residents": []})
    for a in all_analyses:
        name = a.get("resident", {}).get("name", "Unknown")
        for bp_name, bp_perf in a.get("performance", {}).get("blueprint", {}).items():
            bp_aggregate[bp_name]["rates"].append(bp_perf["rate"])
            bp_aggregate[bp_name]["residents"].append(name)

    program_weaknesses = []
    for bp_name, data in bp_aggregate.items():
        mean_rate = sum(data["rates"]) / len(data["rates"])
        weak_count = sum(1 for r in data["rates"] if r < 0.70)
        if weak_count >= len(data["rates"]) / 2:
            program_weaknesses.append({
                "dimension": bp_name,
                "mean_rate": round(mean_rate, 3),
                "weak_count": weak_count,
                "total_residents": len(data["rates"]),
                "interpretation": "Program-level curriculum gap — not individual weakness"
            })

    return {
        "status": "complete",
        "residents": len(all_analyses),
        "program_weaknesses": program_weaknesses,
        "bp_aggregate": {k: {"mean": round(sum(v["rates"])/len(v["rates"]), 3), "n": len(v["rates"])}
                         for k, v in bp_aggregate.items()},
    }


# ---------------------------------------------------------------------------
# PRACTICE QUESTION MATCHING — 3-Tier Cascade
# ---------------------------------------------------------------------------
#
# Tier 1: Direct blueprint match (2024+ tagged questions only)
# Tier 2: Subcategory fingerprint match (pre-2024 untagged questions,
#          matched by subcategory profile characteristic of each blueprint)
# Tier 3: ICD-10 sibling match (any question sharing ICD-10 codes with
#          the weak dimension's tagged questions, via article chain)
#
# Each tier fires only if the previous tier didn't fill the minimum.
# Every selected question carries a match_tier tag for report transparency.
# ---------------------------------------------------------------------------

# Subcategory fingerprints derived from 2024-2025 tagged questions.
# Ordered by discriminative power: subcategories most characteristic of
# each blueprint, used for Tier 2 matching against untagged questions.
BLUEPRINT_SUBCATEGORY_FINGERPRINT = {
    "Preventive Care":          ["Screening", "Prevention", "Counseling"],
    "Emergent and Urgent Care":  ["Management", "Workup", "Interpretation"],
    "Chronic Care Management":   ["Pharmacology", "Treatment", "Prognosis/Risk"],
    "Acute Care and Diagnosis":  ["Diagnosis", "Workup", "Pathophysiology"],
    "Foundations of Care":       ["Management", "Screening", "Counseling"],
}

# Column spec reused by all tiers
_Q_COLUMNS = """q.qid, q.exam_year, q.body_system, q.body_system_merged,
                q.subcategory, q.blueprint, q.question_text, q.choices,
                q.correct_letter, q.correct_text, q.explanation, q.reference"""


def _row_to_dict(r, targeting: str, match_tier: int) -> dict:
    """Convert a DB row to the standard question dict."""
    return {
        "qid": r["qid"],
        "exam_year": r["exam_year"],
        "body_system": r["body_system"],
        "body_system_merged": r["body_system_merged"],
        "subcategory": r["subcategory"],
        "blueprint": r["blueprint"],
        "question_text": r["question_text"],
        "choices": r["choices"],
        "correct_letter": r["correct_letter"],
        "correct_text": r["correct_text"],
        "explanation": r["explanation"],
        "reference": r["reference"],
        "linked_articles": r["linked_articles"],
        "targeting": targeting,
        "match_tier": match_tier,
    }


def _not_in_clause(selected_qids: set) -> tuple:
    """Return (sql_fragment, params) for excluding already-selected QIDs."""
    if not selected_qids:
        return ("", [])
    ph = ",".join(["?"] * len(selected_qids))
    return (f"AND q.qid NOT IN ({ph})", list(selected_qids))


def _tier1_blueprint(db, dim: str, dim_type: str, alloc: int,
                     selected_qids: set) -> list:
    """Tier 1: Direct blueprint/body_system/cross_tab match."""
    where_parts = ["q.question_text IS NOT NULL AND q.question_text != ''"]
    params = []

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
        parts = dim.split(" \u00d7 ", 1)
        if len(parts) == 2:
            bs_part, bp_part = parts
            db_names = BODYSYSTEM_PDF_TO_DB.get(bs_part, [bs_part])
            db_bp = BLUEPRINT_PDF_TO_DB.get(bp_part, bp_part)
            bs_ph = ",".join(["?"] * len(db_names))
            where_parts.append(f"(q.body_system_merged IN ({bs_ph}) OR q.body_system IN ({bs_ph}))")
            where_parts.append("q.blueprint = ?")
            params.extend(db_names * 2)
            params.append(db_bp)

    excl_sql, excl_params = _not_in_clause(selected_qids)

    sql = f"""
        SELECT {_Q_COLUMNS},
               COUNT(DISTINCT qa.article_id) as linked_articles
        FROM questions q
        LEFT JOIN qid_art_xref qa ON q.qid = qa.qid AND qa.article_id != 'ART-0001'
        WHERE {" AND ".join(where_parts)} {excl_sql}
        GROUP BY q.qid
        ORDER BY q.exam_year DESC, linked_articles DESC
        LIMIT ?
    """
    params.extend(excl_params)
    params.append(alloc)
    return db.execute(sql, params).fetchall()


def _tier2_subcategory(db, dim: str, dim_type: str, alloc: int,
                       selected_qids: set, weak_body_systems: list = None) -> list:
    """
    Tier 2: Subcategory fingerprint match for untagged (pre-2024) questions.
    Uses the subcategory profile characteristic of the target blueprint
    to find clinically similar questions that lack a blueprint tag.
    """
    if dim_type == "blueprint":
        db_bp = BLUEPRINT_PDF_TO_DB.get(dim, dim)
    elif dim_type == "cross_tab":
        parts = dim.split(" \u00d7 ", 1)
        db_bp = BLUEPRINT_PDF_TO_DB.get(parts[1], parts[1]) if len(parts) == 2 else None
    else:
        return []

    if not db_bp:
        return []

    fingerprint = BLUEPRINT_SUBCATEGORY_FINGERPRINT.get(db_bp, [])
    if not fingerprint:
        return []

    where_parts = [
        "q.question_text IS NOT NULL AND q.question_text != ''",
        "(q.blueprint = '' OR q.blueprint IS NULL)",
    ]
    params = []

    fp_ph = ",".join(["?"] * len(fingerprint))
    where_parts.append(f"q.subcategory IN ({fp_ph})")
    params.extend(fingerprint)

    bs_names = []
    if dim_type == "cross_tab":
        parts = dim.split(" \u00d7 ", 1)
        if len(parts) == 2:
            bs_names = BODYSYSTEM_PDF_TO_DB.get(parts[0], [parts[0]])
    elif weak_body_systems:
        for ws in weak_body_systems:
            bs_names.extend(BODYSYSTEM_PDF_TO_DB.get(ws, [ws]))

    if bs_names:
        bs_ph = ",".join(["?"] * len(bs_names))
        where_parts.append(f"(q.body_system_merged IN ({bs_ph}) OR q.body_system IN ({bs_ph}))")
        params.extend(bs_names * 2)

    excl_sql, excl_params = _not_in_clause(selected_qids)

    sql = f"""
        SELECT {_Q_COLUMNS},
               COUNT(DISTINCT qa.article_id) as linked_articles
        FROM questions q
        LEFT JOIN qid_art_xref qa ON q.qid = qa.qid AND qa.article_id != 'ART-0001'
        WHERE {" AND ".join(where_parts)} {excl_sql}
        GROUP BY q.qid
        ORDER BY linked_articles DESC, q.exam_year DESC
        LIMIT ?
    """
    params.extend(excl_params)
    params.append(alloc)
    return db.execute(sql, params).fetchall()


def _tier3_icd10_sibling(db, dim: str, dim_type: str, alloc: int,
                         selected_qids: set) -> list:
    """
    Tier 3: ICD-10 sibling match.
    Find questions that share ICD-10 codes (via article chain) with
    the tagged questions in this weak dimension.
    """
    icd_where = []
    icd_params = []

    if dim_type == "blueprint":
        db_bp = BLUEPRINT_PDF_TO_DB.get(dim, dim)
        icd_where.append("q.blueprint = ?")
        icd_params.append(db_bp)
    elif dim_type == "body_system":
        db_names = BODYSYSTEM_PDF_TO_DB.get(dim, [dim])
        ph = ",".join(["?"] * len(db_names))
        icd_where.append(f"(q.body_system_merged IN ({ph}) OR q.body_system IN ({ph}))")
        icd_params.extend(db_names * 2)
    elif dim_type == "cross_tab":
        parts = dim.split(" \u00d7 ", 1)
        if len(parts) == 2:
            db_names = BODYSYSTEM_PDF_TO_DB.get(parts[0], [parts[0]])
            db_bp = BLUEPRINT_PDF_TO_DB.get(parts[1], parts[1])
            bs_ph = ",".join(["?"] * len(db_names))
            icd_where.append(f"(q.body_system_merged IN ({bs_ph}) OR q.body_system IN ({bs_ph}))")
            icd_where.append("q.blueprint = ?")
            icd_params.extend(db_names * 2)
            icd_params.append(db_bp)

    if not icd_where:
        return []

    icd_sql = f"""
        SELECT DISTINCT ai.icd10_code
        FROM questions q
        JOIN qid_art_xref qa ON q.qid = qa.qid AND qa.article_id != 'ART-0001'
        JOIN article_icd10 ai ON qa.article_id = ai.article_id AND ai.relevance = 'primary'
        WHERE {" AND ".join(icd_where)}
    """
    icd_rows = db.execute(icd_sql, icd_params).fetchall()
    icd_codes = [r["icd10_code"] for r in icd_rows]

    if not icd_codes:
        return []

    code_ph = ",".join(["?"] * len(icd_codes))
    excl_sql, excl_params = _not_in_clause(selected_qids)

    sql = f"""
        SELECT {_Q_COLUMNS},
               COUNT(DISTINCT qa2.article_id) as linked_articles
        FROM questions q
        JOIN qid_art_xref qa ON q.qid = qa.qid AND qa.article_id != 'ART-0001'
        JOIN article_icd10 ai ON qa.article_id = ai.article_id AND ai.relevance = 'primary'
        LEFT JOIN qid_art_xref qa2 ON q.qid = qa2.qid AND qa2.article_id != 'ART-0001'
        WHERE q.question_text IS NOT NULL AND q.question_text != ''
          AND ai.icd10_code IN ({code_ph})
          {excl_sql}
        GROUP BY q.qid
        ORDER BY linked_articles DESC, q.exam_year DESC
        LIMIT ?
    """
    params = list(icd_codes) + excl_params + [alloc]
    return db.execute(sql, params).fetchall()


def match_practice_questions(perf: dict, priorities: list, db_path: str,
                            target_count: int = 10, items: list = None) -> list:
    """
    Select practice questions targeting the highest-priority weak areas.
    Uses yield-weighted priorities to allocate questions proportionally.

    3-tier cascade per priority dimension:
      Tier 1: Direct blueprint match (2024+ tagged questions)
      Tier 2: Subcategory fingerprint match (untagged questions, matched by
              subcategory profile characteristic of each blueprint)
      Tier 3: ICD-10 sibling match (questions sharing ICD-10 codes with
              the weak dimension's tagged questions, via article chain)

    Each question carries a match_tier field (1/2/3) for report transparency.
    """
    MIN_PER_WEAK = 5
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row

    selected = []
    selected_qids = set()

    weak_body_systems = [name for name, p in perf.get("body_system", {}).items()
                         if p["rate"] < 0.70]

    # Auto-expand target_count so every priority area gets at least MIN_PER_WEAK.
    # Two-pass allocation: everyone gets MIN_PER_WEAK guaranteed, then any
    # remaining budget is distributed proportionally with a per-area cap.
    active_priorities = priorities[:10]
    n_areas = len(active_priorities)
    min_needed = n_areas * MIN_PER_WEAK
    effective_target = max(target_count, min_needed)
    bonus_pool = effective_target - min_needed  # extra questions to distribute

    total_priority = sum(p["priority_score"] for p in active_priorities)
    if total_priority == 0:
        total_priority = 1

    # Cap: no single area gets more than 40% of the total budget
    max_per_area = max(MIN_PER_WEAK, round(effective_target * 0.4))

    for priority in active_priorities:
        dim = priority["dimension"]
        dim_type = priority["dimension_type"]
        bonus = round(bonus_pool * priority["priority_score"] / total_priority) if bonus_pool > 0 else 0
        alloc = min(MIN_PER_WEAK + bonus, max_per_area)
        still_need = alloc

        dim_selected = []

        # --- Tier 1: Direct match ---
        rows = _tier1_blueprint(db, dim, dim_type, still_need, selected_qids)
        for r in rows:
            if len(dim_selected) >= alloc:
                break
            selected_qids.add(r["qid"])
            dim_selected.append(_row_to_dict(r, dim, match_tier=1))

        still_need = alloc - len(dim_selected)

        # --- Tier 2: Subcategory fingerprint (if Tier 1 didn't fill alloc) ---
        if still_need > 0:
            rows = _tier2_subcategory(db, dim, dim_type, still_need,
                                      selected_qids, weak_body_systems)
            for r in rows:
                if len(dim_selected) >= alloc:
                    break
                selected_qids.add(r["qid"])
                dim_selected.append(_row_to_dict(r, dim, match_tier=2))

            still_need = alloc - len(dim_selected)

        # --- Tier 3: ICD-10 sibling (if still below alloc) ---
        if still_need > 0:
            rows = _tier3_icd10_sibling(db, dim, dim_type, still_need,
                                        selected_qids)
            for r in rows:
                if len(dim_selected) >= alloc:
                    break
                selected_qids.add(r["qid"])
                dim_selected.append(_row_to_dict(r, dim, match_tier=3))

        selected.extend(dim_selected)
        if len(selected) >= effective_target:
            break

    db.close()
    return selected


# ---------------------------------------------------------------------------
# TOP ARTICLES (enhanced from v1)
# ---------------------------------------------------------------------------

def match_top_articles(perf: dict, db_path: str, count: int = 3) -> list:
    """Find highest-citation articles linked to weak areas."""
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row

    weak_systems = [name for name, p in perf.get("body_system", {}).items() if p["rate"] < 0.70]
    weak_blueprints = [BLUEPRINT_PDF_TO_DB.get(name, name) for name, p in perf.get("blueprint", {}).items() if p["rate"] < 0.70]

    db_system_names = []
    for ws in weak_systems:
        db_system_names.extend(BODYSYSTEM_PDF_TO_DB.get(ws, [ws]))

    params = []
    bs_clause = ""
    bp_clause = ""
    if db_system_names:
        bs_ph = ",".join(["?"] * len(db_system_names))
        bs_clause = f"q.body_system_merged IN ({bs_ph})"
        params.extend(db_system_names)
    if weak_blueprints:
        bp_ph = ",".join(["?"] * len(weak_blueprints))
        bp_clause = f"q.blueprint IN ({bp_ph})"
        params.extend(weak_blueprints)

    where = " OR ".join(filter(None, [bs_clause, bp_clause])) or "1=1"

    sql = f"""
        SELECT a.article_id, a.title, a.author1, a.year, a.source_type,
               a.citation_count, a.unique_years, a.exam_years, a.clean_ref,
               COUNT(DISTINCT q.qid) as weak_area_links
        FROM articles a
        JOIN qid_art_xref qa ON a.article_id = qa.article_id
        JOIN questions q ON qa.qid = q.qid
        WHERE ({where})
          AND a.source_type != 'stub' AND a.article_id != 'ART-0001' AND a.citation_count >= 2
        GROUP BY a.article_id
        ORDER BY a.citation_count DESC, weak_area_links DESC
        LIMIT ?
    """
    params.append(count)

    rows = db.execute(sql, params).fetchall()
    db.close()

    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# MASTER ANALYSIS FUNCTION
# ---------------------------------------------------------------------------

def analyze_v2(parsed_data: dict, db_path: str, ref_path: str = None,
               pgy_level: str = "All", plugins: list = None,
               question_count: int = 10) -> dict:
    """
    Full v2 analysis pipeline.

    Args:
        parsed_data: merged output from ite_parser
        db_path: path to ite_intelligence.db
        ref_path: path to abfm_reference_2025.json
        pgy_level: PGY1/PGY2/PGY3/All for national benchmarking
        plugins: list of plugin names to enable ["concept", "icd10", "cohort"]
        question_count: number of practice questions to select
    """
    if plugins is None:
        plugins = ["concept", "icd10"]

    ref = load_abfm_reference(ref_path)
    items = parsed_data["items"]

    # Basic performance (foundation for all layers)
    perf = basic_performance(items)

    # Thresholds (ABFM-anchored)
    thresholds = compute_thresholds(perf, ref, pgy_level)

    # Core Layer 1: Difficulty profiling
    difficulty = difficulty_profile(items)

    # Core Layer 2: Subcategory decomposition (named subcategories via DB)
    subcategory = subcategory_decomposition(items, db_path)

    # Core Layer 3: Spatial clustering
    clustering = spatial_clustering(items)

    # Core Layer 4: Cross-dimensional patterns
    patterns = cross_dimensional_patterns(items, perf)

    # Core Layer 5: Yield-weighted priorities
    priorities = yield_weighted_priorities(perf, ref)

    # Plugins
    plugin_results = {}
    if "concept" in plugins:
        plugin_results["concept_fingerprint"] = plugin_concept_fingerprint(items, db_path)
    if "icd10" in plugins:
        plugin_results["icd10_map"] = plugin_icd10_map(items, db_path)

    # Practice questions (targeted by priorities)
    practice_questions = match_practice_questions(perf, priorities, db_path, question_count)

    # Top articles
    top_articles = match_top_articles(perf, db_path)

    return {
        "resident": parsed_data["resident"],
        "exam_year": parsed_data.get("exam_year", ""),
        "deleted_items": parsed_data.get("deleted_items", []),
        "performance": perf,
        "thresholds": thresholds,
        "difficulty_profile": difficulty,
        "subcategory_analysis": subcategory,
        "spatial_clustering": clustering,
        "cross_dimensional_patterns": patterns,
        "yield_priorities": priorities,
        "plugins": plugin_results,
        "practice_questions": practice_questions,
        "top_articles": top_articles,
        "body_systems_available": parsed_data.get("body_systems_found", []),
        "analysis_version": "2.0",
    }
