"""
audit_engine_type_changes.py
-----------------------------
One-time audit: shows which engine_type changes in backfill_new_article_metadata.py
come from already-processed articles (right_click / local_lite warehouse tiers).
These are the ones worth protecting before running the full backfill.

Run:
  python audit_engine_type_changes.py
"""

import sqlite3, json, re, os
from pathlib import Path
from collections import Counter

SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
DB_PATH      = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"
WAREHOUSE    = PROJECT_ROOT / "01_module.1_warehouse"
CITATION_ITE = WAREHOUSE / "citation_files" / "ITE"

TIER_FOLDERS = {
    "VC_fail":     "VC_fail",
    "local_lite":  "local_lite",
    "VC_pass":     "VC_pass",
    "right_click": "right_click",
}

CODON_RE = re.compile(r"#@#(ART-\d+)@#@")

ENGINE_TYPE_RULES = [
    (r"randomized|randomised|placebo.controlled|double.blind|clinical trial", "rct"),
    (r"screen|prevention|preventive|immunization|vaccination|USPSTF|Preventive Services", "preventive_guideline"),
    (r"management of|managing|chronic|guideline.*diabetes|guideline.*hypert|"
     r"guideline.*asthma|guideline.*COPD|guideline.*heart fail|standards of (medical )?care", "chronic_guideline"),
    (r"diagnosis|diagnostic|evaluation of|approach to|accuracy|sensitivity|"
     r"specificity|imaging|laboratory|interpretation", "diagnostic_guideline"),
]

def classify_engine(ref):
    if not ref: return "acute_protocol"
    for pat, label in ENGINE_TYPE_RULES:
        if re.search(pat, ref, re.IGNORECASE): return label
    return "acute_protocol"

# ── Build warehouse tier map ──
tier_map = {}
for folder, label in TIER_FOLDERS.items():
    path = CITATION_ITE / folder
    if not path.exists():
        continue
    for f in os.listdir(path):
        m = CODON_RE.search(f)
        if m: tier_map[m.group(1)] = label

# ── Load articles ──
conn = sqlite3.connect(DB_PATH)
cur  = conn.cursor()
cur.execute("SELECT article_id, clean_ref, engine_type FROM articles ORDER BY article_id")
rows = cur.fetchall()
conn.close()

# ── Analyse ──
summary  = Counter()   # (wh_tier, would_change)
detail   = {"right_click": [], "local_lite": []}

for art_id, clean_ref, old_engine in rows:
    wh_tier    = tier_map.get(art_id, "no_pdf")
    new_engine = classify_engine(clean_ref)
    would_change = bool(old_engine) and (new_engine != old_engine)

    summary[(wh_tier, would_change)] += 1

    if wh_tier in ("right_click", "local_lite") and would_change:
        detail[wh_tier].append((art_id, old_engine, new_engine, (clean_ref or "")[:80]))

# ── Print ──
print("=== ENGINE_TYPE CHANGE BREAKDOWN BY WAREHOUSE TIER ===")
print(f"  {'Tier':<15} {'No change':>10} {'Would change':>13}")
print("  " + "-"*40)
for tier_label in ["right_click", "local_lite", "VC_pass", "VC_fail", "no_pdf"]:
    nc  = summary[(tier_label, False)]
    chg = summary[(tier_label, True)]
    flag = "  ** EXTRACTION-DERIVED **" if tier_label in ("right_click","local_lite") and chg else ""
    print(f"  {tier_label:<15} {nc:>10} {chg:>13}{flag}")

total_change = sum(v for (_, chg), v in summary.items() if chg)
protected    = sum(len(v) for v in detail.values())
print(f"\n  Total engine_type changes: {total_change}")
print(f"  From processed tiers (right_click + local_lite): {protected}")
print(f"  From unprocessed tiers (VC_pass + VC_fail + no_pdf): {total_change - protected}")

for tier_label in ("right_click", "local_lite"):
    rows_d = detail[tier_label]
    if not rows_d:
        print(f"\n  {tier_label.upper()}: no changes")
        continue
    print(f"\n=== {tier_label.upper()} changes ({len(rows_d)}) ===")
    # Group by old→new
    grouped = Counter((old, new) for _, old, new, _ in rows_d)
    print(f"  {'Old engine':<25} -> {'New engine':<25}  count")
    print("  " + "-"*60)
    for (old, new), cnt in sorted(grouped.items(), key=lambda x: -x[1]):
        print(f"  {old:<25} -> {new:<25}  {cnt}")
    print(f"\n  Sample articles:")
    for art_id, old, new, ref in rows_d[:6]:
        print(f"    {art_id}: {old} -> {new}")
        print(f"      {ref}")
