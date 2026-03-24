"""
validate_db_v2.py — ITE Intelligence DB v2 Quality Report
==========================================================
QC checkpoint after preprocessing. Answers:
  - Are all concept_tags populated? Any malformed?
  - Tag quality sample by tier (Must-Read, Core, Supplementary)
  - Top 20 exam-engine articles (most QIDs)
  - Orphan and coverage summary

RUN:
  python scripts/validate_db_v2.py
  python scripts/validate_db_v2.py --full   # show all malformed tags
"""

import sqlite3, json, argparse, sys
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH  = BASE_DIR / "db" / "ite_intelligence.db"

CONCEPT_TAG_KEYS = {"diagnoses", "drugs", "guidelines", "thresholds", "concept_summary"}


# ── Helpers ────────────────────────────────────────────────────────────────

def pct(n, total):
    return f"{n}/{total} ({100*n//total if total else 0}%)"

def bar(score, width=20):
    filled = int(score * width)
    return "█" * filled + "░" * (width - filled)

def parse_tags(raw):
    """Return parsed dict or None if unparseable."""
    if not raw:
        return None
    try:
        val = json.loads(raw) if isinstance(raw, str) else raw
        return val if isinstance(val, dict) else None
    except Exception:
        return None

def tag_quality(tags: dict) -> dict:
    """Score a single concept_tags dict. Returns counts per field."""
    return {
        "has_diagnoses":      bool(tags.get("diagnoses")),
        "has_drugs":          bool(tags.get("drugs")),
        "has_guidelines":     bool(tags.get("guidelines")),
        "has_thresholds":     bool(tags.get("thresholds")),
        "has_summary":        bool(tags.get("concept_summary", "").strip()),
        "diagnoses_count":    len(tags.get("diagnoses") or []),
        "drugs_count":        len(tags.get("drugs") or []),
        "thresholds_count":   len(tags.get("thresholds") or []),
    }



# ── Main sections ──────────────────────────────────────────────────────────

def section_coverage(cur, args):
    """Section 1: Overall coverage — how many questions have concept_tags."""
    print("\n" + "═"*60)
    print("  SECTION 1 — CONCEPT_TAGS COVERAGE")
    print("═"*60)

    cur.execute("SELECT COUNT(*) FROM questions")
    total_q = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM questions WHERE concept_tags IS NOT NULL AND concept_tags != ''")
    tagged = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM questions WHERE concept_tags IS NULL OR concept_tags = ''")
    missing = cur.fetchone()[0]

    malformed = 0
    empty_summary = 0
    cur.execute("SELECT qid, concept_tags FROM questions WHERE concept_tags IS NOT NULL AND concept_tags != ''")
    rows = cur.fetchall()
    for qid, raw in rows:
        tags = parse_tags(raw)
        if tags is None:
            malformed += 1
        elif not tags.get("concept_summary", "").strip():
            empty_summary += 1

    rate = tagged / total_q if total_q else 0
    print(f"  Total questions : {total_q}")
    print(f"  Tagged          : {pct(tagged, total_q)}  {bar(rate)}")
    print(f"  Missing tags    : {missing}")
    print(f"  Malformed JSON  : {malformed}")
    print(f"  Empty summary   : {empty_summary}")

    # Coverage by year
    print("\n  By exam year:")
    cur.execute("""
        SELECT exam_year,
               COUNT(*) as total,
               SUM(CASE WHEN concept_tags IS NOT NULL AND concept_tags != '' THEN 1 ELSE 0 END) as tagged
        FROM questions
        GROUP BY exam_year ORDER BY exam_year
    """)
    for year, tot, tag in cur.fetchall():
        r = tag/tot if tot else 0
        print(f"    {year}:  {pct(tag, tot)}  {bar(r, 12)}")

    return {"total": total_q, "tagged": tagged, "missing": missing,
            "malformed": malformed, "empty_summary": empty_summary}


def section_tag_quality(cur, args):
    """Section 2: Tag field population rates."""
    print("\n" + "═"*60)
    print("  SECTION 2 — TAG FIELD POPULATION RATES")
    print("═"*60)

    cur.execute("SELECT concept_tags FROM questions WHERE concept_tags IS NOT NULL AND concept_tags != ''")
    rows = cur.fetchall()
    n = len(rows)
    if n == 0:
        print("  No tagged questions found.")
        return

    counts = defaultdict(int)
    for (raw,) in rows:
        tags = parse_tags(raw)
        if tags is None:
            continue
        q = tag_quality(tags)
        for k, v in q.items():
            if isinstance(v, bool) and v:
                counts[k] += 1

    fields = ["has_diagnoses", "has_drugs", "has_guidelines", "has_thresholds", "has_summary"]
    labels = ["diagnoses",     "drugs",     "guidelines",     "thresholds",     "concept_summary"]
    for field, label in zip(fields, labels):
        c = counts[field]
        r = c / n
        print(f"  {label:<20} {pct(c, n)}  {bar(r, 15)}")



def section_tier_sample(cur, args):
    """Section 3: Quality sample by tier — 2 questions per tier."""
    print("\n" + "═"*60)
    print("  SECTION 3 — QUALITY SAMPLE BY TIER")
    print("═"*60)

    tiers = ["Must-Read", "Core", "Supplementary"]
    for tier in tiers:
        cur.execute("""
            SELECT q.qid, q.exam_year, q.body_system, q.concept_tags, a.tier
            FROM questions q
            JOIN question_ref_pairs qrp ON q.qid = qrp.qid
            JOIN articles a ON qrp.clean_ref = a.clean_ref
            WHERE a.tier = ? AND q.concept_tags IS NOT NULL AND q.concept_tags != ''
            GROUP BY q.qid
            ORDER BY RANDOM() LIMIT 2
        """, (tier,))
        rows = cur.fetchall()
        print(f"\n  ── {tier} ({'no tagged results' if not rows else str(len(rows)) + ' samples'}) ──")
        for qid, year, body, raw, _ in rows:
            tags = parse_tags(raw)
            if not tags:
                continue
            print(f"    QID: {qid}  |  Year: {year}  |  System: {body}")
            dx = tags.get("diagnoses", [])
            print(f"    Diagnoses : {', '.join(dx[:3]) if dx else '—'}")
            rx = tags.get("drugs", [])
            print(f"    Drugs     : {', '.join(rx[:3]) if rx else '—'}")
            thresh = tags.get("thresholds", [])
            print(f"    Thresholds: {', '.join(thresh[:3]) if thresh else '—'}")
            summ = tags.get("concept_summary", "")
            print(f"    Summary   : {summ[:120]}{'...' if len(summ) > 120 else ''}")
            print()


def section_exam_engines(cur, args):
    """Section 4: Top 20 exam-engine articles by QID count."""
    print("\n" + "═"*60)
    print("  SECTION 4 — TOP 20 EXAM ENGINE ARTICLES")
    print("═"*60)
    print(f"  {'Rank':<5} {'Article ID':<12} {'Canonical Name':<35} {'Tier':<15} {'QIDs':<6} {'Years'}")
    print("  " + "-"*85)

    cur.execute("""
        SELECT article_id, canonical_filename, tier, citation_count,
               unique_years, exam_years, qid_list
        FROM articles
        WHERE qid_list IS NOT NULL AND qid_list != '[]'
        ORDER BY citation_count DESC, unique_years DESC
        LIMIT 20
    """)
    rows = cur.fetchall()
    for rank, (art_id, canon, tier, cites, uniq_yrs, exam_yrs_raw, qid_raw) in enumerate(rows, 1):
        try:
            years = json.loads(exam_yrs_raw) if exam_yrs_raw else []
            years_str = " ".join(str(y) for y in sorted(years))
        except Exception:
            years_str = "?"
        canon_short = (canon or "")[:33]
        print(f"  {rank:<5} {art_id:<12} {canon_short:<35} {(tier or ''):<15} {cites:<6} {years_str}")



def section_malformed(cur, args):
    """Section 5: Malformed tag audit."""
    print("\n" + "═"*60)
    print("  SECTION 5 — MALFORMED TAG AUDIT")
    print("═"*60)

    cur.execute("SELECT qid, exam_year, concept_tags FROM questions WHERE concept_tags IS NOT NULL AND concept_tags != ''")
    rows = cur.fetchall()
    malformed = []
    for qid, year, raw in rows:
        tags = parse_tags(raw)
        if tags is None:
            malformed.append((qid, year, str(raw)[:80]))
        elif not CONCEPT_TAG_KEYS.issubset(set(tags.keys())):
            missing_keys = CONCEPT_TAG_KEYS - set(tags.keys())
            malformed.append((qid, year, f"missing keys: {missing_keys}"))

    if not malformed:
        print("  ✓ No malformed tags found. All tagged questions have valid JSON and required keys.")
    else:
        limit = len(malformed) if args.full else min(10, len(malformed))
        print(f"  Found {len(malformed)} malformed entries (showing {limit}):")
        for qid, year, detail in malformed[:limit]:
            print(f"    {qid}  ({year})  →  {detail}")
        if not args.full and len(malformed) > 10:
            print(f"    ... and {len(malformed) - 10} more. Run with --full to see all.")


def section_article_coverage(cur, args):
    """Section 6: Article extraction status summary."""
    print("\n" + "═"*60)
    print("  SECTION 6 — ARTICLE EXTRACTION STATUS")
    print("═"*60)

    cur.execute("SELECT extraction_status, COUNT(*) FROM articles GROUP BY extraction_status")
    for status, count in cur.fetchall():
        print(f"  {(status or 'NULL'):<20} {count}")

    cur.execute("SELECT COUNT(*) FROM articles WHERE qid_list IS NULL OR qid_list = '[]'")
    orphans = cur.fetchone()[0]
    print(f"\n  Orphan articles (no linked QIDs): {orphans}")
    print(f"  (Expected ~54 — Harrison's pages, generic USPSTF refs)")

    cur.execute("SELECT COUNT(*) FROM articles WHERE codon_filename IS NOT NULL AND codon_filename != ''")
    with_codon = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM articles")
    total_art = cur.fetchone()[0]
    print(f"\n  Articles with codon_filename : {pct(with_codon, total_art)}")


# ── Entry point ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="ITE DB v2 Validation Report")
    parser.add_argument("--full", action="store_true", help="Show all malformed tags (not just first 10)")
    args = parser.parse_args()

    if not DB_PATH.exists():
        print(f"[ERROR] DB not found: {DB_PATH}")
        sys.exit(1)

    print(f"\n{'═'*60}")
    print(f"  ITE INTELLIGENCE DB v2 — VALIDATION REPORT")
    print(f"  DB: {DB_PATH}")
    print(f"{'═'*60}")

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    section_coverage(cur, args)
    section_tag_quality(cur, args)
    section_tier_sample(cur, args)
    section_exam_engines(cur, args)
    section_malformed(cur, args)
    section_article_coverage(cur, args)

    con.close()
    print("\n" + "═"*60)
    print("  VALIDATION COMPLETE")
    print("═"*60 + "\n")


if __name__ == "__main__":
    main()
