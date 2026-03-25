"""
build_icd10_tags.py — Intelligence 2.0 Layer 1: ICD-10 Diagnostic Linkage (v2 MCP-first)

Fully deterministic pipeline — zero API cost. Uses:
  1. concept_tags.diagnoses from DB (Claude-preprocessed per question)
  2. clinical_synonym_map.json (clinical term → ICD-10 search-friendly term)
  3. icd10_mcp_lookup.json (search term → MCP-verified ICD-10 code)

Four-phase script:
  Phase 1: build     — Extract diagnoses from concept_tags, translate, look up, insert
  Phase 2: crosswalk — Rebuild icd10_code_xref + icd10_rollup tables
  Phase 3: pathways  — Rebuild clinical_pathways from ENGINE_ROLE_MAP
  Phase 4: report    — Generate coverage report CSVs

Usage:
  python build_icd10_tags.py build                # → full Layer 1 rebuild (article_icd10)
  python build_icd10_tags.py crosswalk            # → rebuild icd10_code_xref + icd10_rollup
  python build_icd10_tags.py pathways             # → rebuild clinical_pathways
  python build_icd10_tags.py report               # → generate CSVs to readable_db_files/
  python build_icd10_tags.py all                  # → run all phases in order

v2.0 (2026-03-17): Rewritten for MCP-first approach. No Claude API calls.
v1.0 (2026-03-16): Original Batch API version (archived).
"""

import sqlite3
import json
import csv
import os
import sys
import argparse
from collections import defaultdict

# ── Config ──────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "..", "00_database", "db", "ite_intelligence.db"))
SCHEMAS_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "schemas"))
OUTPUT_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "readable_db_files"))
SYNONYM_MAP_PATH = os.path.join(SCHEMAS_DIR, "clinical_synonym_map.json")
MCP_LOOKUP_PATH = os.path.join(SCHEMAS_DIR, "icd10_mcp_lookup.json")

# ICD-10 chapter mapping (first letter → chapter)
ICD10_CHAPTERS = {
    "A": ("I", "Certain infectious and parasitic diseases"),
    "B": ("I", "Certain infectious and parasitic diseases"),
    "C": ("II", "Neoplasms"),
    "D": ("II-III", "Neoplasms / Blood diseases"),
    "E": ("IV", "Endocrine, nutritional and metabolic diseases"),
    "F": ("V", "Mental and behavioural disorders"),
    "G": ("VI", "Diseases of the nervous system"),
    "H": ("VII-VIII", "Diseases of the eye and ear"),
    "I": ("IX", "Diseases of the circulatory system"),
    "J": ("X", "Diseases of the respiratory system"),
    "K": ("XI", "Diseases of the digestive system"),
    "L": ("XII", "Diseases of the skin"),
    "M": ("XIII", "Diseases of the musculoskeletal system"),
    "N": ("XIV", "Diseases of the genitourinary system"),
    "O": ("XV", "Pregnancy, childbirth and the puerperium"),
    "P": ("XVI", "Certain conditions originating in the perinatal period"),
    "Q": ("XVII", "Congenital malformations"),
    "R": ("XVIII", "Symptoms and signs"),
    "S": ("XIX", "Injury and poisoning"),
    "T": ("XIX", "Injury and poisoning"),
    "V": ("XX", "External causes of morbidity"),
    "W": ("XX", "External causes of morbidity"),
    "X": ("XX", "External causes of morbidity"),
    "Y": ("XX", "External causes of morbidity"),
    "Z": ("XXI", "Factors influencing health status"),
}

# ENGINE_ROLE_MAP: (engine_type, relevance) → pathway_role
ENGINE_ROLE_MAP = {
    ("preventive_guideline", "primary"):   "screening_prevention",
    ("preventive_guideline", "secondary"): "monitoring",
    ("preventive_guideline", "related"):   "special_pops",
    ("diagnostic_guideline", "primary"):   "diagnosis",
    ("diagnostic_guideline", "secondary"): "monitoring",
    ("diagnostic_guideline", "related"):   "referral",
    ("chronic_guideline", "primary"):      "first_line",
    ("chronic_guideline", "secondary"):    "monitoring",
    ("chronic_guideline", "related"):      "second_line",
    ("acute_protocol", "primary"):         "first_line",
    ("acute_protocol", "secondary"):       "second_line",
    ("acute_protocol", "related"):         "referral",
    ("rct", "primary"):                    "first_line",
    ("rct", "secondary"):                  "second_line",
    ("rct", "related"):                    "special_pops",
}


# ── Helpers ─────────────────────────────────────────────────────────────────

def load_json(path):
    """Load a JSON file. Exit with error if missing."""
    if not os.path.exists(path):
        print(f"ERROR: Required file not found: {path}")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_parent_code(icd10_code):
    """Extract 3-character parent code from a full ICD-10 code."""
    return icd10_code[:3] if len(icd10_code) >= 3 else icd10_code


# ── Phase 1: Build ──────────────────────────────────────────────────────────

def build_icd10(db_path, synonym_map, mcp_lookup):
    """
    Extract diagnoses from concept_tags, translate via synonym map,
    look up in MCP lookup, and insert into article_icd10.
    """
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Create table if not exists
    c.execute("""
        CREATE TABLE IF NOT EXISTS article_icd10 (
            article_id  TEXT NOT NULL,
            icd10_code  TEXT NOT NULL,
            icd10_desc  TEXT,
            relevance   TEXT,
            PRIMARY KEY (article_id, icd10_code)
        )
    """)
    c.execute("DELETE FROM article_icd10")

    # Get all cited, non-stub articles with their concept_tags via qid_art_xref
    c.execute("""
        SELECT x.article_id, q.concept_tags
        FROM qid_art_xref x
        JOIN questions q ON x.qid = q.qid
        JOIN articles a ON x.article_id = a.article_id
        WHERE q.concept_tags IS NOT NULL
          AND a.citation_count > 0
          AND a.source_type != 'stub'
          AND a.article_id != 'ART-0001'
    """)

    # Aggregate diagnoses per article
    article_diagnoses = defaultdict(list)
    for art_id, tags_json in c.fetchall():
        try:
            tags = json.loads(tags_json)
        except (json.JSONDecodeError, TypeError):
            continue
        for dx in tags.get("diagnoses", []):
            article_diagnoses[art_id].append(dx.lower().strip())

    # Build lowercase lookup index from MCP lookup
    lookup_index = {}
    for term, entry in mcp_lookup.items():
        lookup_index[term.lower().strip()] = entry

    # Lowercase synonym map
    syn_map = {k.lower().strip(): v.lower().strip() for k, v in synonym_map.items()}

    # Process each article
    total_codes = 0
    articles_tagged = 0
    no_match_terms = set()

    for art_id, dx_list in sorted(article_diagnoses.items()):
        # Deduplicate while preserving order
        seen_dx = []
        seen_set = set()
        for dx in dx_list:
            if dx not in seen_set:
                seen_dx.append(dx)
                seen_set.add(dx)

        # Translate and look up each diagnosis
        codes_for_article = {}  # icd10_code → (desc, order_index)
        for idx, dx in enumerate(seen_dx):
            # Apply synonym translation if available
            search_term = syn_map.get(dx, dx)

            # Look up in MCP lookup
            entry = lookup_index.get(search_term)
            if not entry:
                # Try original term if synonym didn't match
                entry = lookup_index.get(dx)
            if not entry:
                no_match_terms.add(dx)
                continue

            code = (entry.get("icd10_code") or "").strip()
            desc = (entry.get("icd10_desc") or "").strip()

            if not code:
                no_match_terms.add(dx)
                continue

            # Keep first occurrence (preserves priority ordering)
            if code not in codes_for_article:
                codes_for_article[code] = (desc, idx)

        if not codes_for_article:
            continue

        # Assign relevance based on order: first=primary, next 1-2=secondary, rest=related
        sorted_codes = sorted(codes_for_article.items(), key=lambda x: x[1][1])
        for rank, (code, (desc, _)) in enumerate(sorted_codes):
            if rank == 0:
                relevance = "primary"
            elif rank <= 2:
                relevance = "secondary"
            else:
                relevance = "related"

            c.execute("""
                INSERT OR REPLACE INTO article_icd10
                (article_id, icd10_code, icd10_desc, relevance)
                VALUES (?, ?, ?, ?)
            """, (art_id, code, desc, relevance))
            total_codes += 1

        articles_tagged += 1

    conn.commit()

    # Summary
    print(f"\nLayer 1 Build Complete (MCP-first, zero API cost):")
    print(f"  Articles tagged: {articles_tagged}")
    print(f"  Total ICD-10 codes inserted: {total_codes}")
    print(f"  Average codes per article: {total_codes / max(articles_tagged, 1):.1f}")
    print(f"  Unique no-match terms: {len(no_match_terms)}")

    # Relevance distribution
    c.execute("SELECT relevance, COUNT(*) FROM article_icd10 GROUP BY relevance ORDER BY COUNT(*) DESC")
    print("\n  Relevance distribution:")
    for r in c.fetchall():
        print(f"    {r[0]}: {r[1]}")

    # Save no-match terms for future synonym map expansion
    if no_match_terms:
        no_match_path = os.path.join(OUTPUT_DIR, "icd10_no_match_terms.txt")
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(no_match_path, "w", encoding="utf-8") as f:
            for term in sorted(no_match_terms):
                f.write(term + "\n")
        print(f"\n  No-match terms saved: {no_match_path}")
        print(f"  (Expand clinical_synonym_map.json to reduce these)")

    conn.close()
    return articles_tagged, total_codes


# ── Phase 2: Crosswalk ─────────────────────────────────────────────────────

def build_crosswalk(db_path):
    """Rebuild icd10_code_xref and icd10_rollup from article_icd10."""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # ── icd10_code_xref ──
    c.execute("DROP TABLE IF EXISTS icd10_code_xref")
    c.execute("""
        CREATE TABLE icd10_code_xref (
            icd10_code  TEXT PRIMARY KEY,
            parent_code TEXT NOT NULL
        )
    """)
    c.execute("""
        INSERT INTO icd10_code_xref (icd10_code, parent_code)
        SELECT DISTINCT icd10_code, SUBSTR(icd10_code, 1, 3) AS parent_code
        FROM article_icd10
    """)
    xref_count = c.execute("SELECT COUNT(*) FROM icd10_code_xref").fetchone()[0]

    # ── icd10_rollup ──
    c.execute("DROP TABLE IF EXISTS icd10_rollup")
    c.execute("""
        CREATE TABLE icd10_rollup (
            parent_code   TEXT PRIMARY KEY,
            chapter       TEXT,
            chapter_desc  TEXT,
            article_count INTEGER,
            total_citations INTEGER
        )
    """)

    # Compute rollup
    c.execute("""
        SELECT x.parent_code,
               COUNT(DISTINCT i.article_id) AS article_count,
               SUM(a.citation_count) AS total_citations
        FROM article_icd10 i
        JOIN icd10_code_xref x ON i.icd10_code = x.icd10_code
        JOIN articles a ON i.article_id = a.article_id
        GROUP BY x.parent_code
    """)

    for parent, art_count, cite_count in c.fetchall():
        first_char = parent[0].upper() if parent else ""
        chapter_info = ICD10_CHAPTERS.get(first_char, ("?", "Unknown"))
        c.execute("""
            INSERT INTO icd10_rollup (parent_code, chapter, chapter_desc, article_count, total_citations)
            VALUES (?, ?, ?, ?, ?)
        """, (parent, chapter_info[0], chapter_info[1], art_count, cite_count))

    rollup_count = c.execute("SELECT COUNT(*) FROM icd10_rollup").fetchone()[0]
    conn.commit()
    conn.close()

    print(f"\nCrosswalk Build Complete:")
    print(f"  icd10_code_xref: {xref_count} codes")
    print(f"  icd10_rollup: {rollup_count} parent categories")
    return xref_count, rollup_count


# ── Phase 3: Pathways ──────────────────────────────────────────────────────

def build_pathways(db_path):
    """Rebuild clinical_pathways using ENGINE_ROLE_MAP."""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    c.execute("DROP TABLE IF EXISTS clinical_pathways")
    c.execute("""
        CREATE TABLE clinical_pathways (
            article_id   TEXT NOT NULL,
            icd10_code   TEXT NOT NULL,
            pathway_role TEXT NOT NULL,
            engine_type  TEXT,
            relevance    TEXT,
            confidence   TEXT DEFAULT 'high',
            PRIMARY KEY (article_id, icd10_code)
        )
    """)

    c.execute("""
        SELECT i.article_id, i.icd10_code, i.relevance, a.engine_type
        FROM article_icd10 i
        JOIN articles a ON i.article_id = a.article_id
        WHERE a.engine_type IS NOT NULL
    """)

    inserted = 0
    unmapped = 0
    for art_id, code, relevance, engine_type in c.fetchall():
        role = ENGINE_ROLE_MAP.get((engine_type, relevance))
        if not role:
            unmapped += 1
            continue
        c.execute("""
            INSERT OR REPLACE INTO clinical_pathways
            (article_id, icd10_code, pathway_role, engine_type, relevance, confidence)
            VALUES (?, ?, ?, ?, ?, 'high')
        """, (art_id, code, role, engine_type, relevance))
        inserted += 1

    conn.commit()
    conn.close()

    print(f"\nPathway Build Complete:")
    print(f"  clinical_pathways rows: {inserted}")
    print(f"  Unmapped (engine_type, relevance) pairs: {unmapped}")
    return inserted


# ── Phase 4: Report ─────────────────────────────────────────────────────────

def generate_report(db_path, output_dir):
    """Generate coverage report CSVs."""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    os.makedirs(output_dir, exist_ok=True)

    # 1. Article-level ICD-10 report
    c.execute("""
        SELECT a.article_id, a.title, a.categories, a.tier, a.citation_count,
               GROUP_CONCAT(i.icd10_code || ' (' || i.relevance || ')', '; ') AS codes,
               GROUP_CONCAT(i.icd10_desc, '; ') AS descriptions,
               COUNT(i.icd10_code) AS code_count
        FROM articles a
        LEFT JOIN article_icd10 i ON a.article_id = i.article_id
        WHERE a.citation_count > 0 AND a.source_type != 'stub' AND a.article_id != 'ART-0001'
        GROUP BY a.article_id
        ORDER BY a.citation_count DESC
    """)
    rows = c.fetchall()
    _write_csv(os.path.join(output_dir, "layer1_icd10_by_article.csv"),
               ["article_id", "title", "categories", "tier", "citation_count",
                "icd10_codes", "icd10_descriptions", "code_count"], rows)
    tagged = sum(1 for r in rows if r[7] and r[7] > 0)
    print(f"  layer1_icd10_by_article.csv: {len(rows)} rows ({tagged} tagged)")

    # 2. Code-level report
    c.execute("""
        SELECT i.icd10_code, i.icd10_desc, i.relevance,
               COUNT(DISTINCT i.article_id) AS article_count,
               GROUP_CONCAT(DISTINCT a.tier) AS tiers,
               SUM(a.citation_count) AS total_citations
        FROM article_icd10 i
        JOIN articles a ON i.article_id = a.article_id
        GROUP BY i.icd10_code, i.relevance
        ORDER BY article_count DESC
    """)
    rows = c.fetchall()
    _write_csv(os.path.join(output_dir, "layer1_icd10_by_code.csv"),
               ["icd10_code", "icd10_desc", "relevance", "article_count", "tiers", "total_citations"], rows)
    print(f"  layer1_icd10_by_code.csv: {len(rows)} rows")

    # 3. Rollup report
    c.execute("SELECT * FROM icd10_rollup ORDER BY article_count DESC")
    rows = c.fetchall()
    _write_csv(os.path.join(output_dir, "layer1_icd10_rollup.csv"),
               ["parent_code", "chapter", "chapter_desc", "article_count", "total_citations"], rows)
    print(f"  layer1_icd10_rollup.csv: {len(rows)} rows")

    # 4-7. Pathway reports
    c.execute("""
        SELECT cp.article_id, cp.icd10_code, cp.pathway_role, cp.engine_type, cp.relevance, cp.confidence,
               a.title, a.tier, a.citation_count,
               i.icd10_desc
        FROM clinical_pathways cp
        JOIN articles a ON cp.article_id = a.article_id
        LEFT JOIN article_icd10 i ON cp.article_id = i.article_id AND cp.icd10_code = i.icd10_code
        ORDER BY cp.article_id, cp.icd10_code
    """)
    rows = c.fetchall()
    _write_csv(os.path.join(output_dir, "layer3_pathways_full_detail.csv"),
               ["article_id", "icd10_code", "pathway_role", "engine_type", "relevance", "confidence",
                "title", "tier", "citation_count", "icd10_desc"], rows)
    print(f"  layer3_pathways_full_detail.csv: {len(rows)} rows")

    c.execute("""
        SELECT a.article_id, a.title, a.tier, a.citation_count, a.engine_type,
               GROUP_CONCAT(DISTINCT cp.pathway_role) AS roles,
               COUNT(DISTINCT cp.icd10_code) AS code_count
        FROM articles a
        JOIN clinical_pathways cp ON a.article_id = cp.article_id
        GROUP BY a.article_id
        ORDER BY a.citation_count DESC
    """)
    rows = c.fetchall()
    _write_csv(os.path.join(output_dir, "layer3_pathways_by_article.csv"),
               ["article_id", "title", "tier", "citation_count", "engine_type", "roles", "code_count"], rows)
    print(f"  layer3_pathways_by_article.csv: {len(rows)} rows")

    c.execute("""
        SELECT cp.icd10_code, i.icd10_desc, cp.pathway_role,
               COUNT(DISTINCT cp.article_id) AS article_count,
               GROUP_CONCAT(DISTINCT a.tier) AS tiers
        FROM clinical_pathways cp
        JOIN articles a ON cp.article_id = a.article_id
        LEFT JOIN (SELECT DISTINCT icd10_code, icd10_desc FROM article_icd10) i ON cp.icd10_code = i.icd10_code
        GROUP BY cp.icd10_code, cp.pathway_role
        ORDER BY article_count DESC
    """)
    rows = c.fetchall()
    _write_csv(os.path.join(output_dir, "layer3_pathways_by_code_role.csv"),
               ["icd10_code", "icd10_desc", "pathway_role", "article_count", "tiers"], rows)
    print(f"  layer3_pathways_by_code_role.csv: {len(rows)} rows")

    c.execute("""
        SELECT x.parent_code, r.chapter, r.chapter_desc, cp.pathway_role,
               COUNT(DISTINCT cp.article_id) AS article_count,
               SUM(a.citation_count) AS total_citations
        FROM clinical_pathways cp
        JOIN icd10_code_xref x ON cp.icd10_code = x.icd10_code
        JOIN icd10_rollup r ON x.parent_code = r.parent_code
        JOIN articles a ON cp.article_id = a.article_id
        GROUP BY x.parent_code, cp.pathway_role
        ORDER BY article_count DESC
    """)
    rows = c.fetchall()
    _write_csv(os.path.join(output_dir, "layer3_pathways_by_parent_code.csv"),
               ["parent_code", "chapter", "chapter_desc", "pathway_role", "article_count", "total_citations"], rows)
    print(f"  layer3_pathways_by_parent_code.csv: {len(rows)} rows")

    conn.close()


def _write_csv(path, headers, rows):
    """Write CSV with utf-8-sig encoding for Excel compatibility."""
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Layer 1: ICD-10 Diagnostic Linkage (v2 MCP-first)")
    parser.add_argument("phase", choices=["build", "crosswalk", "pathways", "report", "all"],
                       help="Which phase to run")
    args = parser.parse_args()

    print(f"Database:    {DB_PATH}")
    print(f"Synonym map: {SYNONYM_MAP_PATH}")
    print(f"MCP lookup:  {MCP_LOOKUP_PATH}")
    print(f"Output:      {OUTPUT_DIR}")
    print()

    if args.phase in ("build", "all"):
        synonym_map = load_json(SYNONYM_MAP_PATH)
        mcp_lookup = load_json(MCP_LOOKUP_PATH)
        build_icd10(DB_PATH, synonym_map, mcp_lookup)

    if args.phase in ("crosswalk", "all"):
        build_crosswalk(DB_PATH)

    if args.phase in ("pathways", "all"):
        build_pathways(DB_PATH)

    if args.phase in ("report", "all"):
        print("\nGenerating CSVs:")
        generate_report(DB_PATH, OUTPUT_DIR)

    print("\nDone.")


if __name__ == "__main__":
    main()
