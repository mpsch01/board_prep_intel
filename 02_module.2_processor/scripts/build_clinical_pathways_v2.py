"""
build_clinical_pathways_v2.py — Intelligence 2.0 Layer 3: Clinical Pathways (v2)

Blueprint-based routing. Replaces build_clinical_pathways.py (which used the
now-dropped subcategory column). Uses questions.blueprint (100% filled on both
banks) as the primary routing signal.

Key changes from v1:
  - Routing signal: subcategory → dropped. Blueprint → primary signal.
  - Coverage: ART-0002–ART-1397 → full range ART-0002–ART-1985
  - Both banks: ITE (qid_art_xref) + AAFP (aafp_qid_art_xref) vote per article
  - New columns: icd10_desc (was missing), source_bank (ITE/AAFP/both/none)
  - Replaced: engine_type column → blueprint column
  - Table is fully rebuilt (DROP + RECREATE — derived data, disposable)

Data flow:
  ITE:  questions.blueprint  × qid_art_xref      → blueprint votes per article
  AAFP: aafp_questions.blueprint × aafp_qid_art_xref → blueprint votes per article
  Combined dominant blueprint × article_icd10.relevance → pathway_role
  → clinical_pathways table

Three phases:
  Phase 1: profile  — Build blueprint profile per article (both banks)
  Phase 2: build    — Populate clinical_pathways table
  Phase 3: report   — CSVs + summary stats

Usage:
  python build_clinical_pathways_v2.py profile        # → per-article blueprint profiles
  python build_clinical_pathways_v2.py build          # → populates clinical_pathways table
  python build_clinical_pathways_v2.py report         # → writes CSVs
  python build_clinical_pathways_v2.py all            # → runs all three phases
"""

import sqlite3
import csv
import os
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

# Handle non-ASCII characters in article titles from DB
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ── Paths ────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH      = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"
OUTPUT_DIR   = PROJECT_ROOT / "00_database" / "readable_db_files"

# ── Blueprint → Pathway Role Map ─────────────────────────────────────────────
#
# Five ABFM blueprint categories cross with ICD-10 relevance to produce
# one of seven pathway roles.
#
# Design notes:
#   "Acute Care and Diagnosis"  — covers both diagnostic workup AND acute
#     treatment. primary → first_line (treatment is the dominant ABFM signal;
#     ABFM tests "what drug do you start?" not just "what test do you order").
#     secondary → second_line (escalation / alternative agents).
#     related → referral (when conditions are peripherally involved).
#
#   "Chronic Care Management"   — maps directly from old chronic_guideline.
#     primary → first_line (drug initiation, treatment algorithm).
#     secondary → monitoring (follow-up, titration, lab surveillance).
#     related → special_pops (modified management in subpopulations).
#
#   "Emergent and Urgent Care"  — time-critical protocols; same as old
#     acute_protocol but scoped to emergencies.
#     primary → first_line (immediate treatment).
#     secondary → second_line (escalation after initial failure).
#     related → special_pops (ED management of comorbid populations).
#
#   "Preventive Care"           — maps directly from old preventive_guideline.
#     primary/secondary → screening_prevention.
#     related → monitoring (surveillance / follow-up after screening).
#
#   "Foundations of Care"       — pathophysiology, ethics, communication,
#     interpretation. No strong treatment signal; roles lean diagnostic.
#     primary → diagnosis (understanding a condition = how to diagnose it).
#     secondary/related → monitoring (background knowledge for follow-up).
#
BLUEPRINT_ROLE_MAP = {
    ("Acute Care and Diagnosis",  "primary"):   "first_line",
    ("Acute Care and Diagnosis",  "secondary"): "second_line",
    ("Acute Care and Diagnosis",  "related"):   "referral",

    ("Chronic Care Management",   "primary"):   "first_line",
    ("Chronic Care Management",   "secondary"): "monitoring",
    ("Chronic Care Management",   "related"):   "special_pops",

    ("Emergent and Urgent Care",  "primary"):   "first_line",
    ("Emergent and Urgent Care",  "secondary"): "second_line",
    ("Emergent and Urgent Care",  "related"):   "special_pops",

    ("Preventive Care",           "primary"):   "screening_prevention",
    ("Preventive Care",           "secondary"): "screening_prevention",
    ("Preventive Care",           "related"):   "monitoring",

    ("Foundations of Care",       "primary"):   "diagnosis",
    ("Foundations of Care",       "secondary"): "monitoring",
    ("Foundations of Care",       "related"):   "monitoring",
}

# Valid pathway roles (unchanged from v1)
PATHWAY_ROLES = [
    "screening_prevention",
    "diagnosis",
    "first_line",
    "second_line",
    "monitoring",
    "referral",
    "special_pops",
]

# ── Fallback: source_type → synthetic blueprint ───────────────────────────────
# Used for articles with zero linked questions in either bank.
# Maps source_type substrings → blueprint equivalent.
RCT_SOURCE_TYPES = {"NEJM", "JAMA", "Lancet", "BMJ", "Annals", "Circulation", "Chest"}

CHRONIC_CATEGORIES = {
    "Cardiovascular", "Endocrine", "Nephrologic", "Psychiatric/Behavioral",
    "Neurologic", "Hematologic/Immune",
}
ACUTE_CATEGORIES = {
    "Respiratory", "Gastrointestinal", "Musculoskeletal",
    "Integumentary", "Reproductive:Female", "Reproductive:Male",
}
PREVENTIVE_CATEGORIES = {"Well-Patient Care", "Preventive Care"}

DEFAULT_BLUEPRINT = "Acute Care and Diagnosis"


def _fallback_blueprint(source_type: str, categories: str) -> str:
    """
    Assign a synthetic blueprint for articles with no question links.
    Mirrors the logic of v1's _resolve_no_subcategory but maps to blueprint names.
    """
    if source_type in RCT_SOURCE_TYPES:
        return "Acute Care and Diagnosis"
    cats = set(c.strip() for c in categories.split(",")) if categories else set()
    if "Preventive" in source_type or cats & PREVENTIVE_CATEGORIES:
        return "Preventive Care"
    if "Guideline" in source_type or "Textbook" == source_type:
        if cats & CHRONIC_CATEGORIES:
            return "Chronic Care Management"
        if cats & ACUTE_CATEGORIES:
            return "Acute Care and Diagnosis"
        return "Chronic Care Management"
    if cats & CHRONIC_CATEGORIES:
        return "Chronic Care Management"
    if cats & ACUTE_CATEGORIES:
        return "Acute Care and Diagnosis"
    return DEFAULT_BLUEPRINT


# ── Phase 1: Profile ──────────────────────────────────────────────────────────

def build_profiles(db_path: Path) -> dict:
    """
    Build a blueprint profile for every cited, non-stub article.

    Returns:
        profiles: {article_id: {"blueprint": str, "source_bank": str, "vote_counts": Counter}}
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # All eligible articles: cited ITE articles + any article with AAFP question links
    # AAFP articles (ART-1938+) have citation_count=0 (ITE-only metric) but are
    # legitimate via aafp_qid_art_xref — include them explicitly.
    articles = {
        r["article_id"]: {"source_type": r["source_type"] or "", "categories": r["categories"] or ""}
        for r in c.execute("""
            SELECT article_id, source_type, categories
            FROM articles
            WHERE source_type != 'stub'
              AND article_id != 'ART-0001'
              AND (citation_count > 0
                   OR article_id IN (SELECT DISTINCT article_id FROM aafp_qid_art_xref))
        """)
    }

    # ITE question blueprint votes (via qid_art_xref)
    ite_votes = defaultdict(Counter)
    for r in c.execute("""
        SELECT x.article_id, q.blueprint
        FROM qid_art_xref x
        JOIN questions q ON x.qid = q.qid
        WHERE q.blueprint IS NOT NULL AND q.blueprint != ''
    """):
        ite_votes[r["article_id"]][r["blueprint"]] += 1

    # AAFP question blueprint votes (via aafp_qid_art_xref)
    aafp_votes = defaultdict(Counter)
    for r in c.execute("""
        SELECT x.article_id, q.blueprint
        FROM aafp_qid_art_xref x
        JOIN aafp_questions q ON x.aafp_qid = q.aafp_qid
        WHERE q.blueprint IS NOT NULL AND q.blueprint != ''
    """):
        aafp_votes[r["article_id"]][r["blueprint"]] += 1

    conn.close()

    profiles = {}
    stats = Counter()

    for aid, meta in articles.items():
        ite_c = ite_votes.get(aid, Counter())
        aafp_c = aafp_votes.get(aid, Counter())

        # Determine source_bank
        has_ite  = bool(ite_c)
        has_aafp = bool(aafp_c)
        if has_ite and has_aafp:
            source_bank = "both"
        elif has_ite:
            source_bank = "ITE"
        elif has_aafp:
            source_bank = "AAFP"
        else:
            source_bank = "none"

        # Combine votes across both banks
        combined = Counter()
        combined.update(ite_c)
        combined.update(aafp_c)

        if combined:
            dominant = combined.most_common(1)[0][0]
            stats["question_routed"] += 1
        else:
            dominant = _fallback_blueprint(meta["source_type"], meta["categories"])
            stats["fallback_routed"] += 1

        profiles[aid] = {
            "blueprint":   dominant,
            "source_bank": source_bank,
            "vote_counts": combined,
        }
        stats[dominant] += 1

    print(f"\n  Articles profiled: {len(profiles)}")
    print(f"  Question-routed:   {stats['question_routed']}")
    print(f"  Fallback-routed:   {stats['fallback_routed']}")
    print(f"\n  Blueprint distribution:")
    for bp, n in stats.most_common():
        if bp in ("question_routed", "fallback_routed"):
            continue
        pct = 100.0 * n / len(profiles) if profiles else 0
        print(f"    {bp:<40} {n:>5}  ({pct:.1f}%)")
    print(f"\n  Source bank distribution:")
    bank_counts = Counter(p["source_bank"] for p in profiles.values())
    for bank, n in bank_counts.most_common():
        print(f"    {bank:<10} {n}")

    return profiles


# ── Phase 2: Build ────────────────────────────────────────────────────────────

def build_pathways(db_path: Path, profiles: dict) -> int:
    """
    Populate clinical_pathways table.

    For each (article_id, icd10_code) in article_icd10:
      blueprint × relevance → pathway_role → INSERT into clinical_pathways
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # DROP and RECREATE table (full rebuild — derived data)
    c.execute("DROP TABLE IF EXISTS clinical_pathways")
    c.execute("""
        CREATE TABLE clinical_pathways (
            article_id    TEXT NOT NULL,
            icd10_code    TEXT NOT NULL,
            icd10_desc    TEXT,
            pathway_role  TEXT NOT NULL,
            blueprint     TEXT,
            source_bank   TEXT,
            relevance     TEXT,
            confidence    TEXT DEFAULT 'high',
            PRIMARY KEY (article_id, icd10_code)
        )
    """)

    # Load all ICD-10 assignments for eligible articles (same logic as build_profiles)
    icd10_rows = c.execute("""
        SELECT ai.article_id, ai.icd10_code, ai.icd10_desc, ai.relevance
        FROM article_icd10 ai
        JOIN articles a ON ai.article_id = a.article_id
        WHERE a.source_type != 'stub'
          AND a.article_id != 'ART-0001'
          AND (a.citation_count > 0
               OR a.article_id IN (SELECT DISTINCT article_id FROM aafp_qid_art_xref))
    """).fetchall()

    inserted = 0
    skipped  = 0
    role_counts = Counter()
    bank_counts = Counter()

    for row in icd10_rows:
        aid      = row["article_id"]
        code     = row["icd10_code"]
        desc     = row["icd10_desc"]
        relevance = row["relevance"] or "related"

        profile = profiles.get(aid)
        if not profile:
            skipped += 1
            continue

        blueprint   = profile["blueprint"]
        source_bank = profile["source_bank"]

        key = (blueprint, relevance)
        pathway_role = BLUEPRINT_ROLE_MAP.get(key, "first_line")  # safe default

        c.execute("""
            INSERT OR REPLACE INTO clinical_pathways
            (article_id, icd10_code, icd10_desc, pathway_role, blueprint, source_bank, relevance, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'high')
        """, (aid, code, desc, pathway_role, blueprint, source_bank, relevance))

        inserted += 1
        role_counts[pathway_role] += 1
        bank_counts[source_bank] += 1

    conn.commit()

    print(f"\n  Rows inserted:   {inserted}")
    print(f"  Rows skipped:    {skipped}  (article not in profiles)")
    print(f"  Distinct articles: {len(set(r['article_id'] for r in icd10_rows if profiles.get(r['article_id'])))}")
    print(f"  Distinct ICD-10:   {len(set(r['icd10_code'] for r in icd10_rows))}")

    print(f"\n  Pathway role distribution:")
    for role in PATHWAY_ROLES:
        n = role_counts.get(role, 0)
        pct = 100.0 * n / inserted if inserted else 0
        print(f"    {role:<25} {n:>5}  ({pct:.1f}%)")

    print(f"\n  Source bank distribution:")
    for bank, n in bank_counts.most_common():
        print(f"    {bank:<10} {n}")

    conn.close()
    return inserted


# ── Phase 3: Report ───────────────────────────────────────────────────────────

def generate_report(db_path: Path, output_dir: Path):
    """Generate Layer 3 report CSVs and pathway examples."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    output_dir.mkdir(parents=True, exist_ok=True)

    # CSV 1: By article
    rows1 = c.execute("""
        SELECT a.article_id, a.title, a.categories, a.tier, a.source_type,
               cp.blueprint,  cp.source_bank, a.citation_count,
               GROUP_CONCAT(DISTINCT cp.pathway_role) AS pathway_roles,
               GROUP_CONCAT(DISTINCT cp.icd10_code)   AS icd10_codes,
               COUNT(DISTINCT cp.icd10_code)          AS pathway_code_count
        FROM articles a
        LEFT JOIN clinical_pathways cp ON a.article_id = cp.article_id
        WHERE a.citation_count > 0 AND a.source_type != 'stub' AND a.article_id != 'ART-0001'
        GROUP BY a.article_id
        ORDER BY a.citation_count DESC
    """).fetchall()

    p1 = output_dir / "layer3_pathways_by_article.csv"
    with open(p1, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["article_id","title","categories","tier","source_type",
                    "blueprint","source_bank","citation_count",
                    "pathway_roles","icd10_codes","pathway_code_count"])
        w.writerows(rows1)
    print(f"  Article report:   {p1.name} ({len(rows1)} rows)")

    # CSV 2: By ICD-10 code × role
    rows2 = c.execute("""
        SELECT cp.icd10_code, cp.icd10_desc, cp.pathway_role,
               COUNT(DISTINCT cp.article_id)  AS article_count,
               GROUP_CONCAT(DISTINCT a.tier)  AS tiers,
               GROUP_CONCAT(DISTINCT cp.blueprint) AS blueprints
        FROM clinical_pathways cp
        JOIN articles a ON cp.article_id = a.article_id
        GROUP BY cp.icd10_code, cp.pathway_role
        ORDER BY article_count DESC
    """).fetchall()

    p2 = output_dir / "layer3_pathways_by_code_role.csv"
    with open(p2, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["icd10_code","icd10_desc","pathway_role",
                    "article_count","tiers","blueprints"])
        w.writerows(rows2)
    print(f"  Code-role report: {p2.name} ({len(rows2)} rows)")

    # CSV 3: Full detail (every article × code × role triple)
    rows3 = c.execute("""
        SELECT cp.article_id, a.title, cp.icd10_code, cp.icd10_desc,
               cp.pathway_role, cp.blueprint, cp.source_bank, cp.relevance,
               a.tier, a.citation_count
        FROM clinical_pathways cp
        JOIN articles a ON cp.article_id = a.article_id
        ORDER BY cp.icd10_code, cp.pathway_role, a.citation_count DESC
    """).fetchall()

    p3 = output_dir / "layer3_pathways_full_detail.csv"
    with open(p3, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["article_id","title","icd10_code","icd10_desc",
                    "pathway_role","blueprint","source_bank","relevance",
                    "tier","citation_count"])
        w.writerows(rows3)
    print(f"  Full detail:      {p3.name} ({len(rows3)} rows)")

    # CSV 4: Rollup to parent ICD-10 level
    rows4 = c.execute("""
        SELECT ir.parent_code, ir.chapter_desc, ir.chapter,
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

    p4 = output_dir / "layer3_pathways_by_parent_code.csv"
    with open(p4, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["parent_code","chapter_desc","chapter","pathway_role",
                    "article_count","code_count","tiers"])
        w.writerows(rows4)
    print(f"  Parent rollup:    {p4.name} ({len(rows4)} rows)")

    # Example: Type 2 DM (E11)
    print(f"\n  --- Example Pathway: Type 2 Diabetes (E11.*) ---")
    for r in c.execute("""
        SELECT cp.pathway_role, COUNT(DISTINCT cp.article_id) AS n,
               GROUP_CONCAT(DISTINCT cp.article_id) AS art_ids
        FROM clinical_pathways cp
        JOIN icd10_code_xref ix ON cp.icd10_code = ix.icd10_code
        WHERE ix.parent_code = 'E11'
        GROUP BY cp.pathway_role ORDER BY n DESC
    """):
        arts = r["art_ids"].split(",")[:3]
        print(f"    {r['pathway_role']:<25} {r['n']:>3} articles  (e.g. {', '.join(arts)})")

    # Example: Essential HTN (I10)
    print(f"\n  --- Example Pathway: Essential Hypertension (I10) ---")
    for r in c.execute("""
        SELECT cp.pathway_role, COUNT(DISTINCT cp.article_id) AS n,
               GROUP_CONCAT(DISTINCT cp.article_id) AS art_ids
        FROM clinical_pathways cp
        WHERE cp.icd10_code = 'I10'
        GROUP BY cp.pathway_role ORDER BY n DESC
    """):
        arts = r["art_ids"].split(",")[:3]
        print(f"    {r['pathway_role']:<25} {r['n']:>3} articles  (e.g. {', '.join(arts)})")

    # AAFP coverage summary (new in v2)
    print(f"\n  --- AAFP article coverage (new in v2) ---")
    for r in c.execute("""
        SELECT source_bank, COUNT(DISTINCT article_id) AS articles, COUNT(*) AS rows
        FROM clinical_pathways
        GROUP BY source_bank ORDER BY rows DESC
    """):
        print(f"    {r['source_bank']:<10}  {r['articles']:>5} articles  {r['rows']:>6} rows")

    conn.close()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Layer 3 Clinical Pathways v2 — blueprint-based routing, both banks")
    parser.add_argument("phase",
                        choices=["profile", "build", "report", "all"],
                        help="Which phase to run")
    args = parser.parse_args()

    print(f"DB:     {DB_PATH}")
    print(f"Output: {OUTPUT_DIR}")

    profiles = {}

    if args.phase in ("profile", "all"):
        print(f"\n{'='*60}")
        print(f"  PHASE 1: PROFILE — Build blueprint profiles per article")
        print(f"{'='*60}")
        profiles = build_profiles(DB_PATH)

    if args.phase in ("build", "all"):
        print(f"\n{'='*60}")
        print(f"  PHASE 2: BUILD — Populate clinical_pathways table")
        print(f"{'='*60}")
        if not profiles:
            # Allow running build independently by loading profiles inline
            profiles = build_profiles(DB_PATH)
        build_pathways(DB_PATH, profiles)

    if args.phase in ("report", "all"):
        print(f"\n{'='*60}")
        print(f"  PHASE 3: REPORT — Generate CSVs and pathway examples")
        print(f"{'='*60}")
        generate_report(DB_PATH, OUTPUT_DIR)

    if args.phase == "all":
        print(f"\n{'='*60}")
        print(f"  LAYER 3 v2 COMPLETE — {date.today()}")
        print(f"{'='*60}")


if __name__ == "__main__":
    main()
