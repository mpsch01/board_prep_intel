"""
build_crosswalk_index.py  v2.0 (post-codon migration)
Builds crosswalk_index.json by parsing ART-IDs directly from codon filenames.

Post-migration, every matched PDF has the format: Author_Year#@#ART-XXXX@#@.pdf
This script simply:
  1. Scans 01_pdf_guideline_library/ for all PDFs
  2. Parses ART-ID from codon filenames (non-codon files logged as unmatched)
  3. Looks up article metadata from ite_intelligence.db
  4. Writes crosswalk_index.json + crosswalk_report.txt

No more 3-pass matching, slug normalization, or derivative scanning.
"""

import sys, json, re, sqlite3
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

# ── Paths (relative to script location — no hardcoded Windows paths) ─────
BASE_DIR     = Path(__file__).resolve().parent.parent          # M1/scripts/
ROOT         = BASE_DIR.parent.parent                          # board_prep_intel/
DB_PATH      = ROOT / "00_database" / "db" / "ite_intelligence.db"
CITATION_ITE = ROOT / "01_module.1_warehouse" / "citation_files" / "ITE"
TIER_DIRS    = ["VC_fail", "local_lite", "VC_pass", "right_click"]
OUT_JSON     = ROOT / "00_database" / "crosswalk" / "crosswalk_index.json"
OUT_REPORT   = ROOT / "00_database" / "crosswalk" / "crosswalk_report.txt"

# ── Build crosswalk ──────────────────────────────────────────────────────
pdfs = sorted(
    f
    for tier in TIER_DIRS
    for f in ((CITATION_ITE / tier).iterdir() if (CITATION_ITE / tier).exists() else [])
    if f.suffix.lower() == '.pdf'
)
conn = sqlite3.connect(DB_PATH)
cur  = conn.cursor()

crosswalk = []
codon_matched = 0
unmatched = []

for pdf in pdfs:
    m = re.search(r'#@#(ART-\d+)@#@', pdf.name)
    if not m:
        unmatched.append(pdf.name)
        crosswalk.append({
            "pdf_filename": pdf.name,
            "article_id": None,
            "clean_ref": None,
            "tier": None,
            "citation_count": 0,
            "exam_years": [],
            "match_status": "no_codon"
        })
        continue

    art_id = m.group(1)
    cur.execute("""
        SELECT clean_ref, tier, citation_display
        FROM articles WHERE article_id=?
    """, (art_id,))
    row = cur.fetchone()

    if not row:
        unmatched.append(pdf.name)
        crosswalk.append({
            "pdf_filename": pdf.name,
            "article_id": art_id,
            "clean_ref": None,
            "tier": None,
            "citation_count": 0,
            "exam_years": [],
            "match_status": "art_id_not_in_db"
        })
        continue

    clean_ref, tier, citation_display = row

    # Get linked question count and exam years
    cur.execute("""
        SELECT DISTINCT q.exam_year
        FROM question_ref_pairs p
        JOIN questions q ON p.qid = q.qid
        WHERE p.clean_ref = ?
        ORDER BY q.exam_year
    """, (clean_ref,))
    exam_years = [r[0] for r in cur.fetchall()]

    cur.execute("""
        SELECT COUNT(*) FROM question_ref_pairs WHERE clean_ref=?
    """, (clean_ref,))
    citation_count = cur.fetchone()[0]

    codon_matched += 1
    crosswalk.append({
        "pdf_filename": pdf.name,
        "article_id": art_id,
        "clean_ref": clean_ref,
        "tier": tier,
        "citation_count": citation_count,
        "exam_years": exam_years,
        "match_status": "codon_matched"
    })

conn.close()

# ── Write JSON ───────────────────────────────────────────────────────────
with open(OUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(crosswalk, f, indent=2)

# ── Report ───────────────────────────────────────────────────────────────
total = len(crosswalk)
pct = lambda n: f"{100*n//total}%" if total else "0%"

lines = [
    f"CROSSWALK INDEX v2.0 — COVERAGE REPORT",
    f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
    "=" * 52,
    f"Total PDFs:        {total}",
    f"Codon matched:     {codon_matched} ({pct(codon_matched)})",
    f"Unmatched:         {len(unmatched)} ({pct(len(unmatched))})",
    "",
    "UNMATCHED FILES (no codon name or ART-ID not in DB)",
    "-" * 40,
]
for name in unmatched:
    lines.append(f"  {name}")

with open(OUT_REPORT, 'w', encoding='utf-8') as f:
    f.write("\n".join(lines))

# ── Console output ───────────────────────────────────────────────────────
print("=" * 52)
print(f"CROSSWALK INDEX v2.0 (codon-only)")
print(f"  Total PDFs:      {total}")
print(f"  Codon matched:   {codon_matched} ({pct(codon_matched)})")
print(f"  Unmatched:       {len(unmatched)}")
print(f"  Output: {OUT_JSON}")
print(f"  Report: {OUT_REPORT}")
