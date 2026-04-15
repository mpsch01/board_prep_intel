"""
generate_body_system_sql.py
============================
Reads upgraded_classifications.json and generates SQL UPDATE statements for
every sql_ready case where the proposed body_system differs from the current
DB value.

Only generates UPDATEs for actual changes — questions already correct are
noted as comments but not touched.

Output: body_system_updates.sql in the body_system_labels output directory.

REVIEW BEFORE RUNNING. Run section by section in DB Browser using SAVEPOINT.

Usage:
    python generate_body_system_sql.py
    python generate_body_system_sql.py --input upgraded_classifications.json
    python generate_body_system_sql.py --include-confirmed   # also include no-change as comments
"""

import json
import argparse
from pathlib import Path
from datetime import date
from collections import defaultdict, Counter

# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
OUTPUT_DIR   = PROJECT_ROOT / "03_module.3_analyst" / "outputs" / "body_system_labels"

DEFAULT_INPUT  = OUTPUT_DIR / "upgraded_classifications.json"
DEFAULT_OUTPUT = OUTPUT_DIR / "body_system_updates.sql"


def esc(s: str) -> str:
    return (s or "").replace("'", "''")


# ── Taxonomy normalization map ─────────────────────────────────────────────────
# Maps (current_db_value, proposed_value) pairs that represent pure taxonomy
# condensation/renaming — not genuine reclassifications. These are always correct
# and low-risk. Any pair NOT in this set is a real clinical reclassification.
TAXONOMY_NORM_TRANSITIONS: set[tuple] = {
    # Pre-2024 ABFM name → post-2024 canonical (Option B)
    ("Psychogenic",              "Psychiatric/Behavioral"),
    ("Psychiatric/Behavioral",   "Psychiatric/Behavioral"),   # already canonical
    ("Reproductive: Female",     "Sexual and Reproductive"),
    ("Reproductive: Male",       "Sexual and Reproductive"),
    ("Reproductive:Female",      "Sexual and Reproductive"),
    ("Reproductive:Male",        "Sexual and Reproductive"),
    ("Sexual and Reproductive",  "Sexual and Reproductive"),  # already canonical
    ("Musculoskeletal",          "Injuries/Musculoskeletal"),
    ("Injuries/Musculoskeletal", "Injuries/Musculoskeletal"), # already canonical
    # Old AI-synthesized taxonomy names (from enrich_ite_questions.py 2018-2019)
    ("Pulmonary/Critical Care",       "Respiratory"),
    ("Dermatologic",                  "Integumentary"),
    ("Eyes, Ears, Nose & Throat",     "Special Sensory"),
    ("Nephrologic/Urologic",          "Nephrologic"),
    ("Population-Based/Preventive",   "Population-Based Care"),
    ("Maternity Care",                "Sexual and Reproductive"),
    ("Nonspecific/Other",             "Nonspecific"),
    ("Reproductive (Female)",         "Sexual and Reproductive"),
    ("Reproductive (Male)",           "Sexual and Reproductive"),
    # Spacing/formatting variants
    ("Hematologic/ Immune",           "Hematologic/Immune"),
    # Our own custom names from the first classifier run → corrected to Option B
    ("Psychiatric",                   "Psychiatric/Behavioral"),
    ("Reproductive",                  "Sexual and Reproductive"),
}


def is_taxonomy_norm(current: str, proposed: str) -> bool:
    """Return True if this change is a taxonomy rename, not a real reclassification."""
    return (current, proposed) in TAXONOMY_NORM_TRANSITIONS


def main():
    parser = argparse.ArgumentParser(
        description="Generate body_system UPDATE SQL from classification results"
    )
    parser.add_argument("--bank", choices=["ite", "aafp"], default="ite",
                        help="Which question bank (ite or aafp). Sets default input/output/table.")
    parser.add_argument("--input", type=str, default=None,
                        help="Input JSON (default: auto from --bank)")
    parser.add_argument("--output", type=str, default=None,
                        help="Output SQL file (default: auto from --bank)")
    parser.add_argument("--include-confirmed", action="store_true",
                        help="Include confirmed (no-change) cases as comments")
    args = parser.parse_args()

    # Resolve bank-specific defaults
    if args.bank == "aafp":
        default_input  = OUTPUT_DIR / "aafp_upgraded_classifications.json"
        default_output = OUTPUT_DIR / "aafp_body_system_updates.sql"
        db_table       = "aafp_questions"
        qid_column     = "aafp_qid"
    else:
        default_input  = OUTPUT_DIR / "upgraded_classifications.json"
        default_output = OUTPUT_DIR / "body_system_updates.sql"
        db_table       = "questions"
        qid_column     = "qid"

    input_path  = Path(args.input)  if args.input  else default_input
    output_path = Path(args.output) if args.output else default_output

    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}")
        print("Run svm_review_audit.py first to generate upgraded_classifications.json")
        return

    with open(input_path, encoding="utf-8") as f:
        data = json.load(f)

    results        = data.get("results", [])
    routing        = data.get("routing_summary", {})
    batch_id       = data.get("batch_id", "unknown")
    training_years = data.get("training_years", [2022, 2023])

    # ── Filter to sql_ready only ───────────────────────────────────────────────
    sql_ready  = [r for r in results if r["route"] == "sql_ready"]
    changes    = [r for r in sql_ready if r["body_system_proposed"] != r["body_system_current_db"]]
    confirmed  = [r for r in sql_ready if r["body_system_proposed"] == r["body_system_current_db"]]

    # Split changes into taxonomy normalization vs. real reclassifications
    tax_norm  = [r for r in changes if is_taxonomy_norm(r["body_system_current_db"], r["body_system_proposed"])]
    real_reclass = [r for r in changes if not is_taxonomy_norm(r["body_system_current_db"], r["body_system_proposed"])]

    print(f"sql_ready total:    {len(sql_ready)}")
    print(f"  Changes to make:  {len(changes)}  (proposed != current DB)")
    print(f"    Taxonomy norm:  {len(tax_norm)}  (safe, fast apply — naming standardization only)")
    print(f"    Reclassified:   {len(real_reclass)}  (clinical judgment — review before applying)")
    print(f"  Already correct:  {len(confirmed)}  (proposed == current DB, no UPDATE needed)")
    print(f"human_review:       {routing.get('human_review', '?')}  (manual review required)")
    print(f"flagged:            {routing.get('flagged', '?')}  (low confidence, do not touch)")

    # ── Change summary ─────────────────────────────────────────────────────────
    from_to = Counter()
    by_year = defaultdict(list)
    for r in changes:
        from_to[(r["body_system_current_db"], r["body_system_proposed"])] += 1
        by_year[r["exam_year"]].append(r)

    print(f"\nTop changes (current DB -> proposed):")
    for (frm, to), n in from_to.most_common(15):
        print(f"  {frm:<28} -> {to:<28}  {n}")

    # ── Build SQL ──────────────────────────────────────────────────────────────
    lines = [
        f"-- body_system_updates.sql",
        f"-- Generated:       {date.today()}",
        f"-- Source:          {input_path.name}",
        f"-- Batch ID:        {batch_id}",
        f"-- Training years:  {training_years}",
        f"-- Classifier:      Claude Sonnet 4.6 + SVM dual-agreement",
        f"--",
        f"-- SECTION 1 — TAXONOMY NORMALIZATION ({len(tax_norm)} changes)",
        f"--   Safe to apply without detailed review.",
        f"--   These are naming standardization only: Psychogenic -> Psychiatric/Behavioral,",
        f"--   Reproductive: Female/Male -> Sexual and Reproductive, spacing fixes, etc.",
        f"--   No clinical reclassification — same body system, corrected name.",
        f"--",
        f"-- SECTION 2 — CLINICAL RECLASSIFICATIONS ({len(real_reclass)} changes)",
        f"--   Review each before applying. These change the actual body system assignment.",
        f"--   Claude reasoning provided for every change.",
        f"--",
        f"-- sql_ready:       {len(sql_ready)}",
        f"--   Confirmed:     {len(confirmed)}  (already correct, no UPDATE)",
        f"-- human_review:    {routing.get('human_review', '?')}  (not included)",
        f"-- flagged:         {routing.get('flagged', '?')}  (not included)",
        f"--",
        f"-- How to apply in DB Browser:",
        f"--   1. Paste Section 1 (taxonomy norm) into Execute SQL tab → run → verify → Write Changes",
        f"--   2. Paste Section 2 year-by-year → run → spot-check → Write Changes (or Revert if wrong)",
        f"--   Nothing hits disk until you click Write Changes — safe to inspect before committing.",
        f"",
        f"BEGIN TRANSACTION;",
        f"",
    ]

    def write_change_block(lines: list, r: dict) -> None:
        """Append SQL comment + UPDATE for one change record."""
        qid      = r["qid"]
        proposed = r["body_system_proposed"]
        was      = r["body_system_current_db"]
        conf     = r["confidence"]
        reason   = (r.get("reasoning") or "").replace("\n", " ")[:200]
        route_note = r.get("route_note", "")
        how = "svm+claude" if "upgraded" in route_note else "claude-only"
        lines += [
            f"-- {qid}  |  {was} -> {proposed}  |  conf={conf:.2f}  [{how}]",
            f"-- {reason}",
            f"UPDATE {db_table} SET body_system = '{esc(proposed)}' "
            f"WHERE {qid_column} = '{esc(qid)}';",
            f"",
        ]

    # ── SECTION 1: Taxonomy normalization ──────────────────────────────────────
    tax_by_year = defaultdict(list)
    for r in tax_norm:
        tax_by_year[r["exam_year"]].append(r)

    lines += [
        f"-- {'#' * 60}",
        f"-- SECTION 1: TAXONOMY NORMALIZATION ({len(tax_norm)} changes)",
        f"-- Safe to apply as a block. No clinical judgment required.",
        f"-- {'#' * 60}",
        f"",
    ]
    for year in sorted(tax_by_year.keys()):
        year_tax = sorted(tax_by_year[year], key=lambda r: r["qid"])
        lines += [
            f"-- {year}  ({len(year_tax)} taxonomy updates)",
            f"",
        ]
        for r in year_tax:
            write_change_block(lines, r)

    # ── SECTION 2: Clinical reclassifications ──────────────────────────────────
    reclass_by_year = defaultdict(list)
    for r in real_reclass:
        reclass_by_year[r["exam_year"]].append(r)

    lines += [
        f"-- {'#' * 60}",
        f"-- SECTION 2: CLINICAL RECLASSIFICATIONS ({len(real_reclass)} changes)",
        f"-- Review each before applying. Grouped by year.",
        f"-- Suspicious transitions to check carefully:",
    ]
    # Flag transition pairs that appear > 2 times and aren't obviously correct
    reclass_from_to = Counter(
        (r["body_system_current_db"], r["body_system_proposed"]) for r in real_reclass
    )
    for (frm, to), n in reclass_from_to.most_common(10):
        lines.append(f"--   {frm:<30} -> {to:<30} ({n} cases)")
    lines += [f"-- {'#' * 60}", f""]

    for year in sorted(reclass_by_year.keys()):
        year_reclass = sorted(reclass_by_year[year], key=lambda r: r["qid"])
        lines += [
            f"-- {'=' * 60}",
            f"-- {year}  ({len(year_reclass)} reclassifications)",
            f"-- {'=' * 60}",
            f"",
        ]
        for r in year_reclass:
            write_change_block(lines, r)

    # Optional: confirmed (no-change) cases as comments
    if args.include_confirmed:
        confirmed_by_year = defaultdict(list)
        for r in confirmed:
            confirmed_by_year[r["exam_year"]].append(r)

        lines += [
            f"-- {'=' * 60}",
            f"-- CONFIRMED (no change needed) — {len(confirmed)} questions",
            f"-- These are already correct in the DB.",
            f"-- {'=' * 60}",
            f"",
        ]
        for year in sorted(confirmed_by_year.keys()):
            for r in sorted(confirmed_by_year[year], key=lambda r: r["qid"]):
                lines.append(
                    f"-- OK {r['qid']}: {r['body_system_proposed']} "
                    f"(conf={r['confidence']:.2f}) — no change needed"
                )
        lines.append("")

    lines += [
        f"COMMIT;",
        f"",
        f"-- {'=' * 60}",
        f"-- Summary",
        f"-- {'=' * 60}",
        f"-- Total UPDATEs: {len(changes)}",
    ]

    # Changes by year
    for year in sorted(by_year.keys()):
        lines.append(f"--   {year}: {len(by_year[year])} changes")

    lines += [
        f"--",
        f"-- Top transitions:",
    ]
    for (frm, to), n in from_to.most_common(10):
        lines.append(f"--   {frm:<28} -> {to:<28} ({n})")

    # ── Write output ───────────────────────────────────────────────────────────
    sql_text = "\n".join(lines)
    output_path.write_text(sql_text, encoding="utf-8")

    print(f"\nWritten: {output_path}")
    print(f"  {len(changes)} UPDATE statements across {len(by_year)} exam years")
    print(f"\nNext step: review in DB Browser, run with SAVEPOINT per year.")
    print(f"After applying, re-run resident analyses with clean body_system data.")


if __name__ == "__main__":
    main()
