"""
backfill_new_article_metadata.py
---------------------------------
Backfills / standardizes source_type, categories, tier, engine_type,
and auto_assigned across the entire articles table.

MODES:
  Default (no flags):   Process all 1,936 articles.
                        Tier always recalculated (retires Core/Supplementary/Must-Read).
                        source_type/engine_type recalculated for all.
                        categories filled only where missing.
  --dry-run:            Preview changes, no DB writes.
  --art-id-min N:       Restrict to ART-N and above (e.g. 1549 for new cohort only).

TIER LOGIC (Mikey directive, 2026-03-25; nomenclature updated 2026-03-26):
  VC gate (session_hy_inserts_v7.json) = SOLE criterion.
  Priority: warehouse physical location first, VC gate fallback for no-PDF articles.
    1. Article has PDF in 03_right_click/ → 'right_click'
    2. Article has PDF in VC_pass/        → 'VC_pass'
    3. Article has PDF in 01_local_lite/  → 'local_lite'
    4. Article has PDF in VC_fail/        → 'VC_fail'
    5. No PDF + VC-cited                  → 'VC_pass'  (pending PDF acquisition)
    6. No PDF + not VC-cited              → 'VC_fail'
  Legacy labels Core/Supplementary/Must-Read are retired.

SOURCE_TYPE:  Rule-based journal detection from clean_ref.
CATEGORIES:   Derived from body_system_merged of linked questions (qid_list). Fill-only.
ENGINE_TYPE:  Rule-based keyword inference from clean_ref.
"""

import sqlite3
import json
import re
import os
import argparse
from pathlib import Path
from collections import Counter

# ── Paths ────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
DB_PATH      = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"
VC_GATE_PATH = PROJECT_ROOT / "key_data_files" / "session_hy_inserts_v7.json"
WAREHOUSE    = PROJECT_ROOT / "01_module.1_warehouse"

TIER_FOLDERS = {
    "VC_fail":        "VC_fail",
    "01_local_lite":  "local_lite",
    "VC_pass":        "VC_pass",
    "03_right_click": "right_click",
}

# Vague source_type labels that the classifier should replace
VAGUE_SOURCE_TYPES = {
    "stub", "Other", "SpecialtyJournal", "Other Major Journal",
    "Endocrine Journal", "OB/GYN Journal", "Neuro Journal", "ObGyn",
}


# ── Source-type classification ────────────────────────────────────────────────
SOURCE_TYPE_RULES = [
    (r"Am Fam Physician|Am Fam Phys\b",             "AFP"),
    (r"N Engl J Med|New Engl.*Med",                 "NEJM"),
    (r"\bJAMA\b",                                   "JAMA"),
    (r"Ann Intern Med|Annals of Intern",             "Annals"),
    (r"\bLancet\b",                                 "Lancet"),
    (r"\bBMJ\b|Br Med J",                           "BMJ"),
    (r"\bPediatrics\b",                             "Pediatrics"),
    (r"\bCirculation\b|J Am Coll Cardiol|JACC\b",   "Circulation"),
    (r"\bChest\b",                                  "Chest"),
    (r"\bUSPSTF\b|US Preventive Services",          "Guideline/Org"),
    (r"\bAAP\b|American Academy of Ped",            "Guideline/Org"),
    (r"\bACOG\b|Am Coll Obstet",                    "Guideline/Org"),
    (r"\bAHA\b|American Heart Assoc",               "Guideline/Org"),
    (r"\bACC\b|Am Coll Cardiol",                    "Guideline/Org"),
    (r"\bACP\b|Am Coll Physicians",                 "Guideline/Org"),
    (r"\bACCP\b|Am Coll Chest",                     "Guideline/Org"),
    (r"\bIDSA\b|Infectious Diseases Soc",           "Guideline/Org"),
    (r"\bADA\b|American Diabetes Assoc",            "Guideline/Org"),
    (r"\bACS\b|American Cancer Soc",                "Guideline/Org"),
    (r"\bCDC\b|Centers for Disease",                "Guideline/Org"),
    (r"\bWHO\b|World Health Org",                   "Guideline/Org"),
    (r"\bNIH\b|National Institutes",                "Guideline/Org"),
    (r"\bASCO\b|\bAAFP\b|\bAAOS\b|Am Acad Ortho",  "Guideline/Org"),
    (r"\bAAN\b|Am Acad Neurol",                     "Guideline/Org"),
    (r"\bERS\b|European Respir|\bESC\b|European Soc Card", "Guideline/Org"),
    (r"Clinical Practice Guideline|Recommendation Statement|"
     r"Practice Guideline|Practice Bulle|Joint Commission",  "Guideline/Org"),
    (r"\bIn:\s|\bIn \w+.*eds?\.",                   "Textbook"),
    (r"\d+(st|nd|rd|th) ed",                        "Textbook"),
]

def classify_source_type(clean_ref: str) -> str:
    if not clean_ref:
        return "Other"
    for pattern, label in SOURCE_TYPE_RULES:
        if re.search(pattern, clean_ref, re.IGNORECASE):
            return label
    return "Other Journal"


# ── Engine-type classification ────────────────────────────────────────────────
ENGINE_TYPE_RULES = [
    (r"randomized|randomised|placebo.controlled|double.blind|clinical trial", "rct"),
    (r"screen|prevention|preventive|immunization|vaccination|"
     r"USPSTF|Preventive Services",                                           "preventive_guideline"),
    (r"management of|managing|chronic|guideline.*diabetes|guideline.*hypert|"
     r"guideline.*asthma|guideline.*COPD|guideline.*heart fail|"
     r"standards of (medical )?care",                                         "chronic_guideline"),
    (r"diagnosis|diagnostic|evaluation of|approach to|accuracy|sensitivity|"
     r"specificity|imaging|laboratory|interpretation",                        "diagnostic_guideline"),
]
ENGINE_DEFAULT = "acute_protocol"

def classify_engine_type(clean_ref: str) -> str:
    if not clean_ref:
        return ENGINE_DEFAULT
    for pattern, label in ENGINE_TYPE_RULES:
        if re.search(pattern, clean_ref, re.IGNORECASE):
            return label
    return ENGINE_DEFAULT


# ── Body-system → categories ──────────────────────────────────────────────────
BODY_SYSTEM_TO_CATEGORY = {
    "cardiovascular": "Cardiovascular",   "cardiac": "Cardiovascular",
    "respiratory":    "Respiratory",      "pulmonary": "Respiratory",
    "gastrointestinal": "Gastrointestinal", "gi": "Gastrointestinal",
    "musculoskeletal": "Musculoskeletal",  "orthopedic": "Musculoskeletal",
    "endocrine":      "Endocrine",        "diabetes": "Endocrine",
    "hematologic":    "Hematologic/Immune", "immune": "Hematologic/Immune",
    "infectious":     "Hematologic/Immune",
    "integumentary":  "Integumentary",    "dermatology": "Integumentary",
    "skin":           "Integumentary",
    "psychogenic":    "Psychogenic",      "psychiatry": "Psychogenic",
    "mental":         "Psychogenic",
    "neurologic":     "Neurologic",       "neuro": "Neurologic",
    "reproductive":   "Reproductive:Female", "obstetrics": "Reproductive:Female",
    "gynecology":     "Reproductive:Female", "ob/gyn": "Reproductive:Female",
    "male":           "Reproductive:Male",   "urology": "Reproductive:Male",
    "nephrologic":    "Nephrologic",      "renal": "Nephrologic",
    "kidney":         "Nephrologic",
    "population":     "Population-Based Care", "preventive": "Population-Based Care",
    "geriatrics":     "Population-Based Care",
    "patient":        "Patient-Based Systems", "systems": "Patient-Based Systems",
    "special sensory": "Special Sensory",  "ophthalmology": "Special Sensory",
    "otolaryngology": "Special Sensory",   "ent": "Special Sensory",
}

def body_system_to_category(body_system: str):
    if not body_system:
        return None
    bs_lower = body_system.lower()
    for keyword, category in BODY_SYSTEM_TO_CATEGORY.items():
        if keyword in bs_lower:
            return category
    return None


# ── Warehouse scanner ─────────────────────────────────────────────────────────
CODON_RE = re.compile(r"#@#(ART-\d+)@#@")

def build_warehouse_tier_map(warehouse_path: Path) -> dict:
    """Scan all 4 warehouse tiers. Returns {art_id: tier_label}."""
    tier_map = {}
    for folder, label in TIER_FOLDERS.items():
        folder_path = warehouse_path / folder
        if not folder_path.exists():
            continue
        for fname in os.listdir(folder_path):
            if not fname.endswith(".pdf"):
                continue
            m = CODON_RE.search(fname)
            if m:
                tier_map[m.group(1)] = label
    return tier_map


# ── VC gate ───────────────────────────────────────────────────────────────────
def load_vc_gate(path: Path) -> set:
    data = json.loads(path.read_text(encoding="utf-8"))
    keys = set()
    for session in data.values():
        for ref in session.get("refs", []):
            citation = ref.get("citation", "").strip()
            if not citation:
                continue
            first_word = citation.split()[0].rstrip(",:").lower()
            year_match = re.search(r"\b(20\d{2}|19\d{2})\b", citation)
            year = year_match.group(1) if year_match else ""
            keys.add(f"{first_word}_{year}")
    return keys

def citation_key(clean_ref: str):
    if not clean_ref:
        return None
    first_word = clean_ref.strip().split()[0].rstrip(",:").lower()
    year_match = re.search(r"\b(20\d{2}|19\d{2})\b", clean_ref)
    year = year_match.group(1) if year_match else ""
    return f"{first_word}_{year}"


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Standardize article metadata across full DB")
    parser.add_argument("--dry-run",    action="store_true",
                        help="Preview changes without writing")
    parser.add_argument("--art-id-min", type=int, default=1,
                        help="Restrict to ART-N and above (default: 1 = all)")
    args = parser.parse_args()

    print(f"DB:         {DB_PATH}")
    print(f"VC gate:    {VC_GATE_PATH}")
    print(f"Warehouse:  {WAREHOUSE}")
    print(f"Min ART-ID: {args.art_id_min}")
    print(f"Dry run:    {args.dry_run}")
    print()

    # ── Load reference data ──
    vc_keys   = load_vc_gate(VC_GATE_PATH)
    tier_map  = build_warehouse_tier_map(WAREHOUSE)
    print(f"VC gate keys:       {len(vc_keys)}")
    print(f"Warehouse ART-IDs:  {len(tier_map)}")
    from collections import Counter as C
    wh_dist = C(tier_map.values())
    for label in ["right_click","VC_pass","local_lite","VC_fail"]:
        print(f"  {label:<15} {wh_dist.get(label,0)}")
    print()

    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    cur.execute("""
        SELECT article_id, clean_ref, qid_list, source_type, categories,
               tier, engine_type, auto_assigned
        FROM articles
        WHERE CAST(SUBSTR(article_id, 5) AS INTEGER) >= ?
        ORDER BY CAST(SUBSTR(article_id, 5) AS INTEGER)
    """, (args.art_id_min,))
    articles = cur.fetchall()
    print(f"Articles to process: {len(articles)}")
    print()

    cur.execute("SELECT qid, body_system_merged FROM questions")
    q_body = {r[0]: r[1] for r in cur.fetchall()}

    updates = []
    stats   = {
        "source_type":          Counter(),
        "tier":                 Counter(),
        "engine_type":          Counter(),
        "tier_source":          Counter(),   # warehouse vs vc_gate vs fallback
        "categories_missing":   0,
        "source_type_changed":  0,
        "tier_changed":         0,
        "engine_changed":       0,
        "categories_filled":    0,
    }

    for row in articles:
        (article_id, clean_ref, qid_list,
         old_source, old_cats, old_tier, old_engine, old_auto) = row

        # ── tier (always recalculated) ──
        if article_id in tier_map:
            tier = tier_map[article_id]
            stats["tier_source"]["warehouse"] += 1
        else:
            ck   = citation_key(clean_ref)
            tier = "VC_pass" if (ck and ck in vc_keys) else "VC_fail"
            stats["tier_source"]["vc_gate_fallback"] += 1
        if tier != old_tier:
            stats["tier_changed"] += 1

        # ── source_type (recalculate for all; classifier is consistent) ──
        source_type = classify_source_type(clean_ref)
        if source_type != old_source:
            stats["source_type_changed"] += 1

        # ── engine_type ──
        # Protect extraction-derived values for fully-processed tiers.
        # right_click and local_lite were processed by the actual extraction engine
        # — that value is ground truth. Recalculate only for unprocessed articles.
        warehouse_tier = tier_map.get(article_id)
        if warehouse_tier in ("right_click", "local_lite") and old_engine:
            engine_type = old_engine
        else:
            engine_type = classify_engine_type(clean_ref)
        if engine_type != old_engine:
            stats["engine_changed"] += 1

        # ── categories (fill missing only; keep existing richer values) ──
        categories = old_cats
        if not old_cats or old_cats.strip() == "":
            if qid_list:
                try:
                    qids = json.loads(qid_list)
                except (json.JSONDecodeError, TypeError):
                    qids = [q.strip() for q in qid_list.split(",") if q.strip()]
                cat_votes = Counter()
                for qid in qids:
                    bs  = q_body.get(qid)
                    cat = body_system_to_category(bs) if bs else None
                    if cat:
                        cat_votes[cat] += 1
                if cat_votes:
                    categories = cat_votes.most_common(1)[0][0]
                    stats["categories_filled"] += 1
        if not categories:
            stats["categories_missing"] += 1

        # ── auto_assigned ──
        auto_assigned = old_auto if old_auto else "Yes"

        stats["source_type"][source_type] += 1
        stats["tier"][tier]               += 1
        stats["engine_type"][engine_type] += 1

        updates.append((source_type, categories, tier, engine_type,
                        auto_assigned, article_id))

    # ── Summary ──
    total = len(updates)
    print("=== PROPOSED CHANGES ===")
    print(f"\nTier — always recalculated ({stats['tier_changed']} changing from old value):")
    for k, v in stats["tier"].most_common():
        print(f"  {k:<20} {v:>5}  ({v/total*100:.1f}%)")
    print(f"  (source: {stats['tier_source']['warehouse']} from warehouse scan, "
          f"{stats['tier_source']['vc_gate_fallback']} from VC gate fallback)")

    print(f"\nSource_type — {stats['source_type_changed']} articles reclassified:")
    for k, v in stats["source_type"].most_common():
        print(f"  {k:<25} {v}")

    print(f"\nEngine_type — {stats['engine_changed']} articles updated:")
    for k, v in stats["engine_type"].most_common():
        print(f"  {k:<25} {v}")

    print(f"\nCategories — {stats['categories_filled']} gaps filled, "
          f"{stats['categories_missing']} still unresolvable, "
          f"existing values preserved")

    if args.dry_run:
        print("\n[DRY RUN] No changes written.")
        print("\nSample rows (first 8):")
        for u in updates[:8]:
            art_id = u[-1]
            print(f"  {art_id}: src={u[0]}, tier={u[2]}, engine={u[3]}, cat={u[1]}")
    else:
        print(f"\nWriting {total} updates to DB...")
        cur.executemany("""
            UPDATE articles
            SET source_type   = ?,
                categories    = ?,
                tier          = ?,
                engine_type   = ?,
                auto_assigned = ?
            WHERE article_id  = ?
        """, updates)
        conn.commit()
        print(f"Done. {total} rows updated.")

        # ── QC: full-table column coverage ──
        print()
        print("=== POST-UPDATE QC: Full Table Column Coverage ===")
        cols = ["source_type", "categories", "tier", "engine_type", "auto_assigned"]
        cur.execute("SELECT COUNT(*) FROM articles")
        grand_total = cur.fetchone()[0]
        print(f"{'Column':<20} {'Filled':>8} {'Total':>7} {'%':>7}")
        print("-" * 45)
        for col in cols:
            cur.execute(f"""SELECT COUNT(*) FROM articles
                WHERE {col} IS NOT NULL
                AND CAST({col} AS TEXT) NOT IN ('','0','pending','Core',
                    'Supplementary','Must-Read')""")
            filled = cur.fetchone()[0]
            pct = round(filled / grand_total * 100, 1)
            print(f"  {col:<20} {filled:>7} {grand_total:>7} {pct:>6}%")

        print()
        print("=== TIER DISTRIBUTION (full table) ===")
        cur.execute("SELECT tier, COUNT(*) FROM articles GROUP BY tier ORDER BY COUNT(*) DESC")
        for r in cur.fetchall():
            print(f"  {str(r[0]):<20} {r[1]}")

    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
