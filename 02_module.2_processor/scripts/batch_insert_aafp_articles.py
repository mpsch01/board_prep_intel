#!/usr/bin/env python3
"""
batch_insert_aafp_articles.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Inserts AAFP acquisition-queue articles into the articles table and
directly links them to their AAFP citations.

Source:  00_database/readable_db_files/aafp_pubmed_acquisition_queue_*.csv
Target:  articles table (new rows ART-1938+)
         aafp_citations (match_status → 'aafp_acquisition')
         aafp_qid_art_xref (new rows)

Design rationale:
  Each row in the acquisition queue has a confirmed citation_id → PMID
  mapping established during the PubMed sweep (BATON 018). Rather than
  relying on the matcher to rediscover these links (which would fail for
  non-numeric page formats like ITC1-ITC19 or e964), we write the links
  directly here.  aafp_ref_match_v2.py --stats then acts as verification.

  clean_ref = aafp_citation_raw.raw_text — the canonical citation text
  already in the DB. This ensures S2 vol/page matching still works if
  a future ITE question cites the same article.

Run modes:
  python batch_insert_aafp_articles.py            ← full run
  python batch_insert_aafp_articles.py --dry-run  ← preview, no writes
  python batch_insert_aafp_articles.py --stats    ← show counts only
"""

import csv
import json
import re
import sqlite3
import sys
from pathlib import Path
from collections import defaultdict

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH      = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"
QUEUE_CSV    = PROJECT_ROOT / "00_database" / "readable_db_files" / \
               "aafp_pubmed_acquisition_queue_20260328.csv"

DRY_RUN = "--dry-run" in sys.argv
STATS   = "--stats"   in sys.argv

# ── Source-type rules (mirrors backfill_new_article_metadata.py) ──────────────
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
    (r"Cochrane Database",                          "Cochrane"),
    (r"\bUSPSTF\b|US Preventive Services",          "Guideline/Org"),
    (r"\bAAP\b|American Academy of Ped",            "Guideline/Org"),
    (r"\bACOG\b|Am Coll Obstet",                    "Guideline/Org"),
    (r"\bAHA\b|American Heart Assoc",               "Guideline/Org"),
    (r"\bACC\b|Am Coll Cardiol",                    "Guideline/Org"),
    (r"\bIDSA\b|Infectious Diseases Soc",           "Guideline/Org"),
    (r"\bADA\b|American Diabetes Assoc",            "Guideline/Org"),
    (r"Clinical Practice Guideline|Recommendation Statement|"
     r"Practice Guideline|Practice Bulle",          "Guideline/Org"),
]

def classify_source_type(ref: str) -> str:
    for pattern, label in SOURCE_TYPE_RULES:
        if re.search(pattern, ref, re.IGNORECASE):
            return label
    return "Other Journal"


# ── Engine-type rules ─────────────────────────────────────────────────────────
ENGINE_TYPE_RULES = [
    (r"randomized|randomised|placebo.controlled|double.blind|clinical trial", "rct"),
    (r"screen|prevention|preventive|immunization|vaccination|"
     r"USPSTF|Preventive Services",                                           "preventive_guideline"),
    (r"management of|managing|chronic|guideline.*diabetes|guideline.*hypert|"
     r"guideline.*asthma|guideline.*COPD|standards of (medical )?care",       "chronic_guideline"),
    (r"diagnosis|diagnostic|evaluation of|approach to|accuracy|sensitivity|"
     r"specificity|imaging|interpretation",                                   "diagnostic_guideline"),
]

def classify_engine_type(ref: str) -> str:
    for pattern, label in ENGINE_TYPE_RULES:
        if re.search(pattern, ref, re.IGNORECASE):
            return label
    return "acute_protocol"


# ── Body-system → category (from aafp_questions) ─────────────────────────────
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
    "gynecology":     "Reproductive:Female",
    "male":           "Reproductive:Male",  "urology": "Reproductive:Male",
    "nephrologic":    "Nephrologic",      "renal": "Nephrologic",
    "kidney":         "Nephrologic",
    "population":     "Population-Based Care", "preventive": "Population-Based Care",
    "geriatrics":     "Population-Based Care",
    "patient":        "Patient-Based Systems",
    "special sensory": "Special Sensory",
    "ophthalmology":  "Special Sensory",
    "otolaryngology": "Special Sensory",  "ent": "Special Sensory",
    "pediatric":      "Population-Based Care",
}

def body_system_to_category(body_system: str) -> str | None:
    if not body_system:
        return None
    bs = body_system.lower()
    for kw, cat in BODY_SYSTEM_TO_CATEGORY.items():
        if kw in bs:
            return cat
    return None


# ── Author parser ─────────────────────────────────────────────────────────────
def parse_authors(raw_text: str) -> tuple[str, str]:
    """Extract author1 and author2 from citation raw text."""
    # Pattern: "Surname I, Surname2 I2:" or "Surname I, Surname2 I2, et al:"
    m = re.match(r'^([A-Za-z\'\-]+)', raw_text.strip())
    author1 = m.group(1) if m else ''

    # Second author: after first comma + space, next word
    after_first = raw_text[len(author1):]
    m2 = re.search(r',\s+([A-Za-z\'\-]+)\s+[A-Z]', after_first)
    if m2:
        candidate = m2.group(1)
        # Don't capture "et al" as author2
        if candidate.lower() not in ('et', 'al'):
            author2 = candidate
        else:
            author2 = ''
    else:
        author2 = ''
    return author1, author2


# ── Canonical filename builder ────────────────────────────────────────────────
def build_canonical(author1: str, year: str, used_names: set) -> str:
    """Build Author_Year canonical filename, deduping with suffix if needed."""
    base = f"{author1}_{year}"
    if base not in used_names:
        used_names.add(base)
        return base
    # Collision — append _b, _c, ...
    for suffix in 'bcdefghij':
        candidate = f"{base}_{suffix}"
        if candidate not in used_names:
            used_names.add(candidate)
            return candidate
    return f"{base}_x"


# ── Next ART-ID ───────────────────────────────────────────────────────────────
def get_next_art_id(cur: sqlite3.Cursor) -> int:
    cur.execute("""
        SELECT MAX(CAST(SUBSTR(article_id, 5) AS INTEGER))
        FROM articles WHERE article_id LIKE 'ART-%'
    """)
    row = cur.fetchone()
    return (row[0] or 0) + 1


# ── Stats mode ────────────────────────────────────────────────────────────────
def run_stats(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM articles WHERE article_id LIKE 'ART-%'")
    print(f"articles total: {cur.fetchone()[0]}")
    cur.execute("SELECT match_status, COUNT(*) FROM aafp_citations GROUP BY match_status ORDER BY COUNT(*) DESC")
    print("\naafp_citations match_status:")
    for row in cur.fetchall():
        print(f"  {row[0]:<25} {row[1]}")
    cur.execute("SELECT COUNT(*) FROM aafp_qid_art_xref")
    print(f"\naafp_qid_art_xref rows: {cur.fetchone()[0]}")
    cur.execute("SELECT COUNT(DISTINCT aafp_qid) FROM aafp_qid_art_xref")
    total_q = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM aafp_questions")
    grand = cur.fetchone()[0]
    print(f"Unique questions linked: {total_q}/{grand} ({total_q/grand*100:.1f}%)")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    if not QUEUE_CSV.exists():
        print(f"ERROR: Queue CSV not found:\n  {QUEUE_CSV}")
        sys.exit(1)

    # Load acquisition queue
    with open(QUEUE_CSV, newline='', encoding='utf-8') as f:
        queue_rows = list(csv.DictReader(f))
    print(f"Acquisition queue rows: {len(queue_rows)}")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # ── Fetch raw texts for all citation_ids ──
    cit_ids = [r['citation_id'] for r in queue_rows]
    ph = ','.join('?' * len(cit_ids))
    cur.execute(f"""
        SELECT cr.citation_id, cr.raw_text, ac.aafp_qid, ac.match_status
        FROM aafp_citation_raw cr
        JOIN aafp_citations ac ON cr.citation_id = ac.citation_id
        WHERE cr.citation_id IN ({ph})
    """, cit_ids)
    raw_map = {row['citation_id']: dict(row) for row in cur.fetchall()}
    print(f"Raw texts found:        {len(raw_map)}")

    # ── Fetch body_system for each aafp_qid ──
    aafp_qids = list({r['aafp_qid'] for r in queue_rows})
    ph2 = ','.join('?' * len(aafp_qids))
    cur.execute(f"SELECT aafp_qid, body_system FROM aafp_questions WHERE aafp_qid IN ({ph2})", aafp_qids)
    body_map = {row[0]: row[1] for row in cur.fetchall()}

    # ── Check which citations are already matched ──
    already_matched = {
        cid for cid, data in raw_map.items()
        if data['match_status'] != 'unmatched'
    }
    if already_matched:
        print(f"Already matched (skip): {len(already_matched)} — {', '.join(sorted(already_matched))}")

    # ── Determine starting ART-ID ──
    next_id = get_next_art_id(cur)
    print(f"Next ART-ID:            ART-{next_id:04d}")
    print()

    # ── Build article records ──
    used_canonical = set()
    # Also load existing canonical names to avoid collision with DB
    cur.execute("SELECT canonical_filename FROM articles WHERE canonical_filename IS NOT NULL")
    for row in cur.fetchall():
        if row[0]:
            used_canonical.add(row[0])

    articles_to_insert   = []   # (clean_ref, article_id, author1, author2, year, title, ...)
    citations_to_update  = []   # (article_id, citation_id)
    xref_to_insert       = []   # (aafp_qid, article_id)

    art_counter = next_id

    for row in queue_rows:
        cit_id = row['citation_id']
        aafp_qid = row['aafp_qid']

        if cit_id not in raw_map:
            print(f"  WARN: {cit_id} not found in aafp_citation_raw — skipping")
            continue

        if cit_id in already_matched:
            print(f"  SKIP: {cit_id} already matched ({raw_map[cit_id]['match_status']})")
            continue

        raw_text = raw_map[cit_id]['raw_text'].strip()
        if not raw_text:
            print(f"  WARN: {cit_id} has empty raw_text — skipping")
            continue

        article_id = f"ART-{art_counter:04d}"
        art_counter += 1

        # Authors from raw_text (more reliable than CSV for format matching)
        author1_raw, author2_raw = parse_authors(raw_text)
        # Year from CSV (authoritative)
        year = row['year'].strip()
        # Title from CSV
        title = row['title'].strip()

        # Canonical + codon filenames
        canonical = build_canonical(author1_raw or row['first_author'], year, used_canonical)
        codon = f"{canonical}#@#{article_id}@#@.pdf"

        # Source type + engine type from raw_text
        source_type  = classify_source_type(raw_text)
        engine_type  = classify_engine_type(raw_text)

        # Categories from aafp_questions.body_system
        body_sys = body_map.get(aafp_qid)
        categories = body_system_to_category(body_sys) if body_sys else None

        # Tier: VC_fail (no PDF yet; backfill script updates once PDFs arrive)
        tier = "VC_fail"

        # citation_display = raw_text (standard for AAFP-sourced articles)
        citation_display = raw_text

        articles_to_insert.append((
            raw_text,          # clean_ref (PRIMARY KEY)
            article_id,
            author1_raw,
            author2_raw or None,
            year,
            title,
            source_type,
            categories,
            None,              # blueprint_cats (leave NULL)
            tier,
            "Yes",             # auto_assigned
            0,                 # citation_count (ITE)
            0,                 # unique_years (ITE)
            '[]',              # exam_years JSON
            '[]',              # qid_list JSON
            canonical,
            codon,
            citation_display,
            "pending",         # extraction_status
            engine_type,
        ))
        citations_to_update.append((article_id, cit_id))
        xref_to_insert.append((aafp_qid, article_id))

    # ── Preview ──
    total_new = len(articles_to_insert)
    print(f"Articles to insert:     {total_new}")
    print(f"Citations to link:      {len(citations_to_update)}")
    print()

    # Source type breakdown
    from collections import Counter
    src_counts = Counter(a[6] for a in articles_to_insert)
    print("Source type distribution:")
    for src, cnt in src_counts.most_common():
        print(f"  {src:<25} {cnt}")
    print()

    if DRY_RUN:
        print("─── DRY RUN PREVIEW (first 10) ──────────────────────────────")
        for art in articles_to_insert[:10]:
            cref, art_id, a1, a2, yr, ttl, src, cat, _, tier, *rest = art
            canonical_f = rest[5]
            codon_f     = rest[6]
            print(f"  {art_id}  {a1} {yr}  [{src}]  tier={tier}")
            print(f"    clean_ref: {cref[:80]}")
            print(f"    codon:     {codon_f}")
            print(f"    cat:       {cat}")
            print()
        print(f"  ... and {max(0, total_new - 10)} more")
        print("\n[DRY RUN] No changes written.")
        conn.close()
        return

    # ── Insert articles ──
    inserted_arts = 0
    skipped_dupe  = 0
    for rec in articles_to_insert:
        try:
            cur.execute("""
                INSERT INTO articles (
                    clean_ref, article_id, author1, author2, year, title,
                    source_type, categories, blueprint_cats, tier,
                    auto_assigned, citation_count, unique_years,
                    exam_years, qid_list, canonical_filename, codon_filename,
                    citation_display, extraction_status, engine_type
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, rec)
            inserted_arts += 1
        except sqlite3.IntegrityError as e:
            skipped_dupe += 1
            print(f"  DUPE SKIP: {rec[1]} — {e}")

    print(f"Articles inserted:      {inserted_arts}")
    if skipped_dupe:
        print(f"Articles skipped (dupe): {skipped_dupe}")

    # ── Link aafp_citations ──
    updated_cit = 0
    for article_id, cit_id in citations_to_update:
        cur.execute("""
            UPDATE aafp_citations
            SET article_id = ?, match_status = 'aafp_acquisition'
            WHERE citation_id = ? AND match_status = 'unmatched'
        """, (article_id, cit_id))
        updated_cit += cur.rowcount
    print(f"aafp_citations updated: {updated_cit}")

    # ── Insert xref rows (dedupe) ──
    xref_seen = set()
    xref_inserted = 0
    for aafp_qid, article_id in xref_to_insert:
        key = (aafp_qid, article_id)
        if key in xref_seen:
            continue
        xref_seen.add(key)
        cur.execute("""
            INSERT OR IGNORE INTO aafp_qid_art_xref (aafp_qid, article_id, match_status)
            VALUES (?, ?, 'aafp_acquisition')
        """, (aafp_qid, article_id))
        xref_inserted += cur.rowcount
    print(f"aafp_qid_art_xref rows: {xref_inserted}")

    conn.commit()

    # ── Post-insert QC ──
    print()
    print("═══ POST-INSERT QC ═══════════════════════════════════════════")

    cur.execute("SELECT COUNT(*) FROM articles")
    total_arts = cur.fetchone()[0]
    print(f"articles total:         {total_arts}")

    cur.execute("SELECT match_status, COUNT(*) FROM aafp_citations GROUP BY match_status ORDER BY COUNT(*) DESC")
    print("\naafp_citations match_status:")
    total_cit = 0
    for row in cur.fetchall():
        print(f"  {row[0]:<25} {row[1]}")
        total_cit += row[1]

    cur.execute("SELECT COUNT(*) FROM aafp_qid_art_xref")
    xref_total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT aafp_qid) FROM aafp_qid_art_xref")
    unique_q = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM aafp_questions")
    grand_q = cur.fetchone()[0]
    print(f"\naafp_qid_art_xref:      {xref_total} rows")
    print(f"Unique questions linked: {unique_q}/{grand_q} ({unique_q/grand_q*100:.1f}%)")

    # New articles coverage
    cur.execute("""
        SELECT COUNT(*) FROM articles
        WHERE CAST(SUBSTR(article_id, 5) AS INTEGER) >= ?
    """, (next_id,))
    new_count = cur.fetchone()[0]
    cur.execute("""
        SELECT COUNT(*) FROM articles
        WHERE CAST(SUBSTR(article_id, 5) AS INTEGER) >= ?
        AND categories IS NOT NULL
    """, (next_id,))
    cat_filled = cur.fetchone()[0]
    print(f"\nNew articles (ART-{next_id:04d}+):")
    print(f"  total:       {new_count}")
    print(f"  categories:  {cat_filled}/{new_count} filled")

    conn.close()
    print(f"\n  DB -> {DB_PATH}")
    print("\nNext: python aafp_ref_match_v2.py --stats   ← verify totals")
    print("      python compute_embeddings.py --new-only")
    print("      python aafp_context_propagator.py")


if __name__ == "__main__":
    if "--help" in sys.argv:
        print(__doc__)
        sys.exit(0)
    if not DB_PATH.exists():
        print(f"ERROR: DB not found:\n  {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    try:
        if STATS:
            run_stats(conn)
        else:
            conn.close()
            main()
    except Exception:
        if not conn:
            pass
        else:
            conn.close()
        raise
