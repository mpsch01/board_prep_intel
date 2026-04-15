"""
condense_taxonomy.py
====================
Maps the 16 pre-2024 ABFM body system categories from the score report labels
into the final training taxonomy:

  5 CONDENSED categories (aligned with the post-2023 ABFM taxonomy):
    Cardiovascular, Respiratory, Musculoskeletal, Psychiatric, Reproductive

  11 RETAINED categories (no post-2023 equivalent — remain distinct):
    Gastrointestinal, Endocrine, Integumentary, Neurologic, Nephrologic,
    Special Sensory, Hematologic/Immune, Nonspecific, Population-Based Care,
    Patient-Based Systems, Psychogenic [retained in pre-2024 name]

Wait — Psychogenic IS one of the 5 condensed (→ Psychiatric).
See CONDENSED_MAP below for the exact mapping.

Usage (as a module):
    from condense_taxonomy import condense, CONDENSED_MAP, FINAL_TAXONOMY

Usage (as a script):
    python condense_taxonomy.py --labels-dir ../../03_module.3_analyst/outputs/body_system_labels/
    Reads score_report_labels_YYYY.json files, outputs condensed versions.
"""

import json
import argparse
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
LABELS_DIR   = PROJECT_ROOT / "03_module.3_analyst" / "outputs" / "body_system_labels"

# ── Condensation map ───────────────────────────────────────────────────────────
# Pre-2024 category → final training taxonomy label
#
# 5 condensed (pre-2024 → post-2023 equivalent):
#   Musculoskeletal       → Musculoskeletal   (post-2023: "Injuries/Musculoskeletal")
#   Psychogenic           → Psychiatric        (post-2023: "Psychiatric/Behavioral")
#   Reproductive: Female  → Reproductive       (post-2023: "Sexual and Reproductive")
#   Reproductive: Male    → Reproductive       (post-2023: "Sexual and Reproductive")
#   Cardiovascular        → Cardiovascular     (same name, direct)
#   Respiratory           → Respiratory        (same name, direct)
#
# 10 retained (no post-2023 equivalent — kept with canonical name):
#   Gastrointestinal, Endocrine, Integumentary, Neurologic, Nephrologic,
#   Special Sensory, Hematologic/Immune, Nonspecific,
#   Population-Based Care, Patient-Based Systems

CONDENSED_MAP: dict[str, str] = {
    # === 6 condensed categories (post-2024 ABFM canonical names) ===
    "Cardiovascular":      "Cardiovascular",
    "Respiratory":         "Respiratory",
    "Musculoskeletal":     "Injuries/Musculoskeletal",
    "Psychogenic":         "Psychiatric/Behavioral",
    "Reproductive: Female":"Sexual and Reproductive",
    "Reproductive: Male":  "Sexual and Reproductive",

    # === 10 retained categories (unchanged) ===
    "Gastrointestinal":    "Gastrointestinal",
    "Endocrine":           "Endocrine",
    "Integumentary":       "Integumentary",
    "Neurologic":          "Neurologic",
    "Nephrologic":         "Nephrologic",
    "Special Sensory":     "Special Sensory",
    "Hematologic/Immune":  "Hematologic/Immune",
    "Nonspecific":         "Nonspecific",
    "Population-Based Care":   "Population-Based Care",
    "Patient-Based Systems":   "Patient-Based Systems",
}

# The full final taxonomy (16 input → 15 output, Reproductive: Female/Male collapse)
FINAL_TAXONOMY: list[str] = sorted(set(CONDENSED_MAP.values()))

# Which final categories were condensed from multiple pre-2024 names
CONDENSED_CATEGORIES: set[str] = {
    "Cardiovascular", "Respiratory", "Injuries/Musculoskeletal",
    "Psychiatric/Behavioral", "Sexual and Reproductive"
}

# Which final categories were retained unchanged
RETAINED_CATEGORIES: set[str] = set(FINAL_TAXONOMY) - CONDENSED_CATEGORIES


def condense(pre2024_category: str) -> str | None:
    """
    Map a pre-2024 ABFM body system category to the final training taxonomy label.
    Returns None if the category is unknown.
    """
    return CONDENSED_MAP.get(pre2024_category)


def condense_labels(labels: dict[str, str]) -> dict[str, str]:
    """
    Apply condensation to a full {qid: pre2024_category} dict.
    Returns {qid: final_category}.
    Skips any QIDs with unknown categories (prints a warning).
    """
    result = {}
    unknown = []
    for qid, cat in labels.items():
        final = condense(cat)
        if final is None:
            unknown.append((qid, cat))
        else:
            result[qid] = final
    if unknown:
        print(f"WARNING: {len(unknown)} QIDs had unknown pre-2024 categories:")
        for qid, cat in unknown[:10]:
            print(f"  {qid}: '{cat}'")
    return result


def print_taxonomy_summary() -> None:
    """Print the condensation map for documentation/review."""
    print("=== ABFM Body System Taxonomy Condensation ===")
    print(f"Pre-2024 categories: {len(CONDENSED_MAP)}")
    print(f"Final taxonomy:      {len(FINAL_TAXONOMY)} categories")
    print()
    print("Condensed (multiple → one):")
    reverse: dict[str, list] = {}
    for pre, final in CONDENSED_MAP.items():
        reverse.setdefault(final, []).append(pre)
    for final_cat, sources in sorted(reverse.items()):
        if len(sources) > 1 or CONDENSED_MAP[sources[0]] != sources[0]:
            src_str = " + ".join(f'"{s}"' for s in sources)
            print(f"  {src_str} → \"{final_cat}\"")
    print()
    print("Retained (unchanged):")
    for final_cat in sorted(RETAINED_CATEGORIES):
        print(f"  \"{final_cat}\"")
    print()
    print(f"Final taxonomy ({len(FINAL_TAXONOMY)} classes):")
    for cat in FINAL_TAXONOMY:
        tag = "[condensed]" if cat in CONDENSED_CATEGORIES else "[retained]"
        print(f"  {tag:<13} {cat}")


def main():
    parser = argparse.ArgumentParser(
        description="Apply taxonomy condensation to score report label JSONs"
    )
    parser.add_argument("--labels-dir", type=str, default=str(LABELS_DIR),
                        help="Directory containing score_report_labels_YYYY.json files")
    parser.add_argument("--summary", action="store_true",
                        help="Print taxonomy summary only, do not process files")
    args = parser.parse_args()

    print_taxonomy_summary()

    if args.summary:
        return

    labels_dir = Path(args.labels_dir)
    label_files = sorted(labels_dir.glob("score_report_labels_*.json"))

    if not label_files:
        print(f"No label files found in: {labels_dir}")
        return

    for lf in label_files:
        with open(lf, encoding="utf-8") as f:
            data = json.load(f)

        year   = data["year"]
        labels = data["labels"]
        condensed = condense_labels(labels)

        # Count by final category
        from collections import Counter
        counts = Counter(condensed.values())

        print(f"\n=== {year} — Condensed taxonomy ===")
        print(f"  Questions: {len(condensed)} / {len(labels)}")
        print("  Category breakdown:")
        for cat in FINAL_TAXONOMY:
            n = counts.get(cat, 0)
            tag = "[C]" if cat in CONDENSED_CATEGORIES else "   "
            bar = "█" * n
            print(f"    {tag} {cat:<30} {n:3d}  {bar}")

        # Write condensed output
        out = {
            "year":            year,
            "source_pdf":      data["source_pdf"],
            "total_questions": len(condensed),
            "deleted_questions": data["deleted_questions"],
            "condensation_map": "condense_taxonomy.CONDENSED_MAP",
            "labels_pre2024":  labels,
            "labels_final":    dict(sorted(condensed.items())),
        }
        out_path = labels_dir / f"condensed_labels_{year}.json"
        out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(f"  Written: {out_path}")


if __name__ == "__main__":
    main()
