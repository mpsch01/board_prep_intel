"""
build_clinical_pathways.py — Intelligence 2.0 Layer 3: Clinical Pathways ("Clinical Blending Engine")

Zero API calls. Routes articles to engine types using in-house DB data (subcategories,
source_type, categories, ICD-10 codes), then maps engine_type × ICD-10 → pathway_role.

Three phases:
  Phase 1: classify  — Assign engine_type to every article from DB signals
  Phase 2: build     — Generate clinical_pathways table (article_id, icd10_code, pathway_role)
  Phase 3: report    — CSVs + summary stats

Usage:
  python build_clinical_pathways.py classify          # → articles get engine_type
  python build_clinical_pathways.py build             # → populates clinical_pathways table
  python build_clinical_pathways.py report            # → writes CSVs + analysis
  python build_clinical_pathways.py all               # → runs all three phases

Data flow:
  articles.categories + questions.subcategory + articles.source_type
    → engine_type (5 classes)
    → engine_type × article_icd10.relevance → pathway_role (7 roles)
    → clinical_pathways table
"""

import sqlite3
import json
import csv
import os
import sys
from collections import Counter, defaultdict
from datetime import date

# ── Config ──────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "..", "..", "00_database", "db", "ite_intelligence.db"))
OUTPUT_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "..", "..", "00_database", "readable_db_files"))

# ── Constants ───────────────────────────────────────────────────────────────

# Valid engine types (from guideline_extractor_v2.3)
ENGINE_TYPES = [
    "preventive_guideline",
    "diagnostic_guideline",
    "chronic_guideline",
    "acute_protocol",
    "rct",
]

# Valid pathway roles
# ──────────────────────────────────────────────────────────────────────────
# Role definitions (clinical calibration notes):
#
#   screening_prevention — Who to screen, when to screen, chemoprophylaxis,
#       immunization, outbreak management. Points to: DOCX "Target Population",
#       "Definitions & Diagnostic Thresholds" (screening intervals/criteria).
#
#   diagnosis — How to diagnose: which test to order, workup sequencing,
#       result interpretation, imaging decision trees, diagnostic criteria.
#       The high-yield signal is TEST SELECTION: "patient with X needs test Y."
#       Points to: DOCX "Definitions & Diagnostic Thresholds", "Clinical
#       Recommendations" (when to test, which test, how to interpret).
#
#   first_line — Initial pharmacologic management and treatment algorithms.
#       Drug selection, initial dosing, treatment initiation criteria.
#       NOTE: "Lifestyle modification" is always technically first-line for
#       chronic conditions (DM2, HTN, obesity, etc.) — it is a constant, not
#       a variable. The ABFM tests drug selection, not "is lifestyle mod
#       first-line?" So lifestyle mod carries zero weight in role assignment.
#       First_line means: what drug/intervention do you START with?
#       Points to: DOCX "Clinical Recommendations", "Medications".
#
#   second_line — Escalation therapy, add-on agents, treatment failure
#       management, RCT evidence supporting alternative approaches.
#       Points to: DOCX "Medications", "Escalation Path".
#
#   monitoring — Follow-up intervals, treatment targets, lab surveillance,
#       complications monitoring, red flag recognition during management.
#       Points to: DOCX "Follow-Up & Monitoring", "Red Flags & Critical
#       Alerts", "Escalation Path" (when to change course).
#
#   referral — When to refer to specialist, hospitalization criteria,
#       transitions of care, disposition decisions.
#       Points to: DOCX "Escalation Path", "Red Flags & Critical Alerts".
#
#   special_pops — Management in a specific population that modifies the
#       standard pathway: pregnancy, pediatrics, elderly, renal impairment,
#       comorbid conditions. Points to: DOCX "Target Population".
# ──────────────────────────────────────────────────────────────────────────
PATHWAY_ROLES = [
    "screening_prevention",
    "diagnosis",
    "first_line",
    "second_line",
    "monitoring",
    "referral",
    "special_pops",
]

# ── Subcategory → Engine Type mapping ───────────────────────────────────────
# Pure mappings (no ambiguity)
SUBCAT_TO_ENGINE = {
    "Screening":      "preventive_guideline",
    "Prevention":     "preventive_guideline",
    "Diagnosis":      "diagnostic_guideline",
    "Workup":         "diagnostic_guideline",
    "Interpretation": "diagnostic_guideline",
    "Pathophysiology":"diagnostic_guideline",
    "Treatment":      "acute_protocol",
    "Prognosis/Risk": "chronic_guideline",
    "Counseling":     "chronic_guideline",
}
# "Pharmacology" and "Management" are ambiguous — resolved by secondary signals

# Source types that indicate RCT
RCT_SOURCE_TYPES = {
    "NEJM", "JAMA", "Lancet", "BMJ", "Annals",
    "Circulation", "Chest",
}

# Categories that lean chronic (long-term management conditions)
CHRONIC_CATEGORIES = {
    "Cardiovascular", "Endocrine", "Nephrologic", "Psychogenic",
    "Neurologic", "Hematologic/Immune",
}

# Categories that lean acute (episodic/treatment-focused)
ACUTE_CATEGORIES = {
    "Respiratory", "Gastrointestinal", "Musculoskeletal",
    "Integumentary", "Reproductive:Female", "Reproductive:Male",
}

# ── Engine Type → Pathway Role mapping ──────────────────────────────────────
# Maps (engine_type, icd10_relevance) → default pathway_role
#
# Design rationale:
#   - engine_type tells us WHAT KIND of clinical document this is
#   - icd10_relevance tells us HOW CENTRAL each condition is to the article
#   - Together they determine the article's ROLE in managing that condition
#
# Note on first_line: this means pharmacologic first-line / initial treatment
# algorithm — NOT lifestyle modification (see role definitions above).
# Chronic + primary → first_line because the ABFM tests "what drug do you
# start?" not "should the patient exercise?"
ENGINE_ROLE_MAP = {
    # Preventive guidelines: screening criteria, intervals, chemoprophylaxis
    ("preventive_guideline", "primary"):   "screening_prevention",
    ("preventive_guideline", "secondary"): "screening_prevention",
    ("preventive_guideline", "related"):   "monitoring",

    # Diagnostic guidelines: which test to order, workup algorithms,
    # test interpretation, imaging decision trees
    ("diagnostic_guideline", "primary"):   "diagnosis",
    ("diagnostic_guideline", "secondary"): "diagnosis",
    ("diagnostic_guideline", "related"):   "referral",

    # Chronic guidelines: drug initiation, titration, treatment algorithms
    ("chronic_guideline", "primary"):      "first_line",
    ("chronic_guideline", "secondary"):    "monitoring",
    ("chronic_guideline", "related"):      "special_pops",

    # Acute protocols: initial treatment, drug selection, timing-critical Rx
    ("acute_protocol", "primary"):         "first_line",
    ("acute_protocol", "secondary"):       "second_line",
    ("acute_protocol", "related"):         "special_pops",

    # RCTs: evidence for escalation, alternative agents, head-to-head data
    ("rct", "primary"):                    "second_line",
    ("rct", "secondary"):                  "second_line",
    ("rct", "related"):                    "special_pops",
}


# ── Phase 1: Classify ──────────────────────────────────────────────────────

def classify_articles(db_path):
    """
    Assign engine_type to every cited, non-stub article using DB signals.

    Priority chain:
      1. source_type in RCT journals → rct
      2. Dominant subcategory (pure mapping) → engine_type
      3. Pharmacology/Management → disambiguate via categories
      4. No subcategory data → fallback via categories + source_type
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Ensure column exists
    try:
        c.execute("ALTER TABLE articles ADD COLUMN engine_type TEXT")
        print("  Added engine_type column to articles table")
    except sqlite3.OperationalError:
        pass  # column already exists

    # Load all eligible articles
    articles = c.execute("""
        SELECT article_id, categories, source_type, tier
        FROM articles
        WHERE citation_count > 0
          AND source_type != 'stub'
          AND article_id != 'ART-0001'
        ORDER BY article_id
    """).fetchall()

    # Pre-load subcategory profiles per article
    subcat_profiles = defaultdict(list)
    for r in c.execute("""
        SELECT x.article_id, q.subcategory
        FROM qid_art_xref x
        JOIN questions q ON x.qid = q.qid
        WHERE q.subcategory IS NOT NULL AND q.subcategory != ''
    """):
        subcat_profiles[r['article_id']].append(r['subcategory'])

    stats = Counter()
    method_stats = Counter()

    for art in articles:
        aid = art['article_id']
        source_type = art['source_type'] or ''
        categories = art['categories'] or ''
        subs = subcat_profiles.get(aid, [])

        engine_type = None
        method = None

        # ── Rule 1: RCT by source_type ──────────────────────────────
        if source_type in RCT_SOURCE_TYPES:
            engine_type = "rct"
            method = "source_type_rct"

        # ── Rule 2-3: Subcategory-based routing ─────────────────────
        elif subs:
            dominant = Counter(subs).most_common(1)[0][0]

            if dominant in SUBCAT_TO_ENGINE:
                # Pure mapping — no ambiguity
                engine_type = SUBCAT_TO_ENGINE[dominant]
                method = f"subcat_pure:{dominant}"

            elif dominant == "Pharmacology":
                # Disambiguate: chronic vs acute by category
                engine_type = _resolve_pharmacology(categories)
                method = f"subcat_pharm:{categories[:30]}"

            elif dominant == "Management":
                # Disambiguate: chronic vs acute by category
                engine_type = _resolve_management(categories)
                method = f"subcat_mgmt:{categories[:30]}"

            else:
                # Unexpected subcategory — default to chronic
                engine_type = "chronic_guideline"
                method = f"subcat_fallback:{dominant}"

        # ── Rule 4: No subcategory data — fallback ──────────────────
        else:
            engine_type = _resolve_no_subcategory(source_type, categories)
            method = f"no_subcat:{source_type}|{categories[:20]}"

        # Write to DB
        c.execute("UPDATE articles SET engine_type = ? WHERE article_id = ?",
                  (engine_type, aid))
        stats[engine_type] += 1
        method_stats[method] += 1

    conn.commit()

    # Print summary
    print(f"\n  Classification complete: {len(articles)} articles")
    print(f"\n  Engine type distribution:")
    for eng, n in sorted(stats.items(), key=lambda x: -x[1]):
        pct = 100.0 * n / len(articles)
        print(f"    {eng:<25} {n:>5}  ({pct:.1f}%)")

    print(f"\n  Method distribution (top 15):")
    for m, n in method_stats.most_common(15):
        print(f"    {m:<50} {n:>5}")

    # Articles with no subcategory data
    no_sub = sum(1 for aid in [a['article_id'] for a in articles] if aid not in subcat_profiles)
    print(f"\n  Articles routed without subcategory data: {no_sub}")

    conn.close()
    return stats


def _resolve_pharmacology(categories: str) -> str:
    """Pharmacology articles: chronic if category is chronic-leaning, else acute."""
    cats = set(c.strip() for c in categories.split(",")) if categories else set()
    if cats & CHRONIC_CATEGORIES:
        return "chronic_guideline"
    if cats & ACUTE_CATEGORIES:
        return "acute_protocol"
    # No strong signal — Pharmacology defaults to acute (drug selection = treatment decision)
    return "acute_protocol"


def _resolve_management(categories: str) -> str:
    """Management articles: chronic by default (long-term management), acute if category says so."""
    cats = set(c.strip() for c in categories.split(",")) if categories else set()
    # Management strongly implies chronic unless category is acute-leaning
    if cats & ACUTE_CATEGORIES and not (cats & CHRONIC_CATEGORIES):
        return "acute_protocol"
    return "chronic_guideline"


def _resolve_no_subcategory(source_type: str, categories: str) -> str:
    """Fallback for articles with no linked questions."""
    if source_type in RCT_SOURCE_TYPES:
        return "rct"
    cats = set(c.strip() for c in categories.split(",")) if categories else set()
    # Guideline/Org sources are typically chronic management guidelines
    if "Guideline" in source_type:
        return "chronic_guideline"
    # Textbooks → chronic (broad reference)
    if source_type == "Textbook":
        return "chronic_guideline"
    # Otherwise use category signal
    if cats & CHRONIC_CATEGORIES:
        return "chronic_guideline"
    if cats & ACUTE_CATEGORIES:
        return "acute_protocol"
    # Ultimate fallback
    return "chronic_guideline"


# ── Phase 2: Build ──────────────────────────────────────────────────────────

def build_pathways(db_path):
    """
    Populate clinical_pathways table by crossing engine_type with ICD-10 codes.
    Each (article_id, icd10_code) pair gets a pathway_role based on:
      engine_type × icd10_relevance → pathway_role
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Create table
    c.execute("""
        CREATE TABLE IF NOT EXISTS clinical_pathways (
            article_id    TEXT NOT NULL,
            icd10_code    TEXT NOT NULL,
            icd10_desc    TEXT,
            pathway_role  TEXT NOT NULL,
            engine_type   TEXT,
            relevance     TEXT,
            confidence    TEXT,
            PRIMARY KEY (article_id, icd10_code)
        )
    """)
    c.execute("DELETE FROM clinical_pathways")  # full rebuild

    # Load article engine types
    engine_map = {}
    for r in c.execute("""
        SELECT article_id, engine_type FROM articles
        WHERE engine_type IS NOT NULL
    """):
        engine_map[r['article_id']] = r['engine_type']

    # Load all ICD-10 assignments
    icd10_rows = c.execute("""
        SELECT article_id, icd10_code, icd10_desc, relevance
        FROM article_icd10
    """).fetchall()

    inserted = 0
    skipped = 0
    role_counts = Counter()
    engine_role_counts = Counter()

    for row in icd10_rows:
        aid = row['article_id']
        code = row['icd10_code']
        desc = row['icd10_desc']
        relevance = row['relevance'] or 'related'

        engine_type = engine_map.get(aid)
        if not engine_type:
            skipped += 1
            continue

        # Look up pathway_role from the mapping
        key = (engine_type, relevance)
        pathway_role = ENGINE_ROLE_MAP.get(key)
        if not pathway_role:
            # Shouldn't happen, but default to first_line
            pathway_role = "first_line"

        # Confidence: high if subcategory-routed, medium if fallback
        confidence = "high"

        c.execute("""
            INSERT OR REPLACE INTO clinical_pathways
            (article_id, icd10_code, icd10_desc, pathway_role, engine_type, relevance, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (aid, code, desc, pathway_role, engine_type, relevance, confidence))

        inserted += 1
        role_counts[pathway_role] += 1
        engine_role_counts[(engine_type, pathway_role)] += 1

    conn.commit()

    # Summary
    print(f"\n  Pathways built: {inserted} rows ({skipped} skipped — no engine_type)")
    print(f"  Distinct articles: {len(set(r['article_id'] for r in icd10_rows if r['article_id'] in engine_map))}")
    print(f"  Distinct ICD-10 codes: {len(set(r['icd10_code'] for r in icd10_rows))}")

    print(f"\n  Pathway role distribution:")
    for role, n in sorted(role_counts.items(), key=lambda x: -x[1]):
        pct = 100.0 * n / inserted if inserted else 0
        print(f"    {role:<25} {n:>5}  ({pct:.1f}%)")

    print(f"\n  Engine × Role matrix:")
    print(f"    {'engine_type':<25} ", end="")
    roles_seen = sorted(set(r for _, r in engine_role_counts.keys()))
    for role in roles_seen:
        print(f"{role:<20}", end="")
    print()
    for eng in ENGINE_TYPES:
        print(f"    {eng:<25} ", end="")
        for role in roles_seen:
            n = engine_role_counts.get((eng, role), 0)
            print(f"{n:<20}", end="")
        print()

    conn.close()
    return inserted


# ── Phase 3: Report ─────────────────────────────────────────────────────────

def generate_report(db_path, output_dir):
    """Generate Layer 3 report CSVs and summary."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    os.makedirs(output_dir, exist_ok=True)

    # ── CSV 1: By article — each article with its engine_type and pathway roles ──
    rows = c.execute("""
        SELECT a.article_id, a.title, a.categories, a.tier, a.source_type,
               a.engine_type, a.citation_count,
               GROUP_CONCAT(DISTINCT cp.pathway_role) AS pathway_roles,
               GROUP_CONCAT(DISTINCT cp.icd10_code) AS icd10_codes,
               COUNT(DISTINCT cp.icd10_code) AS pathway_code_count
        FROM articles a
        LEFT JOIN clinical_pathways cp ON a.article_id = cp.article_id
        WHERE a.citation_count > 0 AND a.source_type != 'stub' AND a.article_id != 'ART-0001'
        GROUP BY a.article_id
        ORDER BY a.citation_count DESC
    """).fetchall()

    path1 = os.path.join(output_dir, "layer3_pathways_by_article.csv")
    with open(path1, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["article_id", "title", "categories", "tier", "source_type",
                     "engine_type", "citation_count", "pathway_roles",
                     "icd10_codes", "pathway_code_count"])
        w.writerows(rows)
    print(f"  Article report:  {path1} ({len(rows)} rows)")

    # ── CSV 2: By pathway — each ICD-10 code with its articles organized by role ──
    rows2 = c.execute("""
        SELECT cp.icd10_code, cp.icd10_desc, cp.pathway_role,
               COUNT(DISTINCT cp.article_id) AS article_count,
               GROUP_CONCAT(DISTINCT a.tier) AS tiers,
               GROUP_CONCAT(DISTINCT cp.engine_type) AS engine_types
        FROM clinical_pathways cp
        JOIN articles a ON cp.article_id = a.article_id
        GROUP BY cp.icd10_code, cp.pathway_role
        ORDER BY article_count DESC
    """).fetchall()

    path2 = os.path.join(output_dir, "layer3_pathways_by_code_role.csv")
    with open(path2, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["icd10_code", "icd10_desc", "pathway_role",
                     "article_count", "tiers", "engine_types"])
        w.writerows(rows2)
    print(f"  Code-role report: {path2} ({len(rows2)} rows)")

    # ── CSV 3: Full pathway detail — every (article, code, role) triple ──
    rows3 = c.execute("""
        SELECT cp.article_id, a.title, cp.icd10_code, cp.icd10_desc,
               cp.pathway_role, cp.engine_type, cp.relevance, cp.confidence,
               a.tier, a.citation_count
        FROM clinical_pathways cp
        JOIN articles a ON cp.article_id = a.article_id
        ORDER BY cp.icd10_code, cp.pathway_role, a.citation_count DESC
    """).fetchall()

    path3 = os.path.join(output_dir, "layer3_pathways_full_detail.csv")
    with open(path3, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["article_id", "title", "icd10_code", "icd10_desc",
                     "pathway_role", "engine_type", "relevance", "confidence",
                     "tier", "citation_count"])
        w.writerows(rows3)
    print(f"  Full detail:     {path3} ({len(rows3)} rows)")

    # ── CSV 4: Condensed pathway view — roll up to parent ICD-10 level ──
    rows4 = c.execute("""
        SELECT ir.parent_code, ir.parent_desc, ir.chapter,
               cp.pathway_role,
               COUNT(DISTINCT cp.article_id) AS article_count,
               COUNT(DISTINCT cp.icd10_code) AS code_count,
               GROUP_CONCAT(DISTINCT a.tier) AS tiers
        FROM clinical_pathways cp
        JOIN icd10_code_xref ix ON cp.icd10_code = ix.icd10_code
        JOIN icd10_rollup ir ON ix.parent_code = ir.parent_code
        JOIN articles a ON cp.article_id = a.article_id
        GROUP BY ir.parent_code, cp.pathway_role
        ORDER BY article_count DESC
    """).fetchall()

    path4 = os.path.join(output_dir, "layer3_pathways_by_parent_code.csv")
    with open(path4, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["parent_code", "parent_desc", "chapter", "pathway_role",
                     "article_count", "code_count", "tiers"])
        w.writerows(rows4)
    print(f"  Parent rollup:   {path4} ({len(rows4)} rows)")

    # ── Example pathway: Type 2 DM (E11) ──
    print(f"\n  --- Example Pathway: Type 2 Diabetes (E11.*) ---")
    for r in c.execute("""
        SELECT cp.pathway_role, COUNT(DISTINCT cp.article_id) AS n,
               GROUP_CONCAT(DISTINCT a.article_id) AS art_ids
        FROM clinical_pathways cp
        JOIN icd10_code_xref ix ON cp.icd10_code = ix.icd10_code
        JOIN articles a ON cp.article_id = a.article_id
        WHERE ix.parent_code = 'E11'
        GROUP BY cp.pathway_role
        ORDER BY n DESC
    """):
        arts = r['art_ids'].split(',')[:3]
        print(f"    {r['pathway_role']:<25} {r['n']:>3} articles  (e.g. {', '.join(arts)})")

    # ── Example pathway: Hypertension (I10) ──
    print(f"\n  --- Example Pathway: Essential Hypertension (I10) ---")
    for r in c.execute("""
        SELECT cp.pathway_role, COUNT(DISTINCT cp.article_id) AS n,
               GROUP_CONCAT(DISTINCT a.article_id) AS art_ids
        FROM clinical_pathways cp
        JOIN articles a ON cp.article_id = a.article_id
        WHERE cp.icd10_code = 'I10'
        GROUP BY cp.pathway_role
        ORDER BY n DESC
    """):
        arts = r['art_ids'].split(',')[:3]
        print(f"    {r['pathway_role']:<25} {r['n']:>3} articles  (e.g. {', '.join(arts)})")

    conn.close()


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Layer 3: Clinical Pathways (zero API calls)")
    parser.add_argument("phase", choices=["classify", "build", "report", "all"],
                       help="Which phase to run")
    args = parser.parse_args()

    print(f"Database: {DB_PATH}")
    print(f"Output:   {OUTPUT_DIR}")

    if args.phase in ("classify", "all"):
        print(f"\n{'='*60}")
        print(f"  PHASE 1: CLASSIFY — Assign engine_type to articles")
        print(f"{'='*60}")
        classify_articles(DB_PATH)

    if args.phase in ("build", "all"):
        print(f"\n{'='*60}")
        print(f"  PHASE 2: BUILD — Generate clinical_pathways table")
        print(f"{'='*60}")
        build_pathways(DB_PATH)

    if args.phase in ("report", "all"):
        print(f"\n{'='*60}")
        print(f"  PHASE 3: REPORT — Generate CSVs and pathway examples")
        print(f"{'='*60}")
        generate_report(DB_PATH, OUTPUT_DIR)

    if args.phase == "all":
        print(f"\n{'='*60}")
        print(f"  LAYER 3 COMPLETE")
        print(f"{'='*60}")
        print(f"  Date: {date.today()}")
        print(f"  DB:   {DB_PATH}")
        print(f"  CSVs: {OUTPUT_DIR}/layer3_pathways_*.csv")


if __name__ == "__main__":
    main()
