"""
build_topic_trends.py — FLAG 13 Layer 4a: Topic Trends
Generates three CSV files from ite_intelligence.db:
  A) body_system_trends.csv — body_system_merged × exam_year with linear slope
  B) body_system_subcategory_trends.csv — body_system_merged × subcategory × exam_year with slope
  C) concept_tag_trends.csv — top diagnoses + drugs (≥5 mentions) trended by year

All analysis uses body_system_merged (not body_system) per project convention.
No API calls — pure local SQL/Python over existing DB data.

Usage:
  python build_topic_trends.py
  python build_topic_trends.py --output-dir "C:\path\to\output"

Output:  Three CSVs in the same directory as this script (or --output-dir).
"""

import sqlite3
import json
import csv
import os
import argparse
from collections import Counter, defaultdict

# ── Config ──────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "..", "..", "00_database", "db", "ite_intelligence.db"))

# ── Helpers ─────────────────────────────────────────────────────────────────

def linear_slope(year_counts: dict, all_years: list) -> float:
    """Simple linear regression slope (questions per year).
    Returns slope rounded to 2 decimal places.
    Missing years treated as 0."""
    n = len(all_years)
    if n < 2:
        return 0.0
    xs = [float(y) for y in all_years]
    ys = [float(year_counts.get(y, 0)) for y in all_years]
    x_mean = sum(xs) / n
    y_mean = sum(ys) / n
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys))
    denominator = sum((x - x_mean) ** 2 for x in xs)
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 2)


def write_csv(filepath, headers, rows):
    """Write rows to CSV with UTF-8 BOM for Excel compatibility."""
    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    print(f"  Written: {filepath} ({len(rows)} rows)")


# ── Layer A: Body System × Year ────────────────────────────────────────────

def build_layer_a(cursor, all_years, output_dir):
    """Body system trends with counts, proportions, and slope."""
    print("\n[Layer A] Body System × Year trends...")

    cursor.execute("""
        SELECT exam_year, body_system_merged, COUNT(*) AS n
        FROM questions
        WHERE body_system_merged IS NOT NULL
        GROUP BY exam_year, body_system_merged
        ORDER BY body_system_merged, exam_year
    """)

    # Gather data
    data = defaultdict(dict)       # {body_system: {year: count}}
    year_totals = Counter()        # {year: total_questions}
    for year, bsm, n in cursor.fetchall():
        data[bsm][year] = n
        year_totals[year] += n

    # Build rows
    # Columns: body_system, <year_count>..., total, slope, <year_pct>...
    headers = (
        ["body_system"]
        + [str(y) for y in all_years]
        + ["total", "slope_per_yr"]
        + [f"{y}_pct" for y in all_years]
    )

    rows = []
    for bsm in sorted(data.keys()):
        year_counts = data[bsm]
        counts = [year_counts.get(y, 0) for y in all_years]
        total = sum(counts)
        slope = linear_slope(year_counts, all_years)
        pcts = [
            round(100.0 * year_counts.get(y, 0) / year_totals[y], 1) if year_totals[y] > 0 else 0.0
            for y in all_years
        ]
        rows.append([bsm] + counts + [total, slope] + pcts)

    # Sort by total descending
    rows.sort(key=lambda r: r[len(all_years) + 1], reverse=True)

    filepath = os.path.join(output_dir, "4a_body_system_trends.csv")
    write_csv(filepath, headers, rows)
    return filepath


# ── Layer B: Body System × Subcategory × Year ──────────────────────────────

def build_layer_b(cursor, all_years, output_dir):
    """Body system × subcategory trends with counts and slope."""
    print("\n[Layer B] Body System × Subcategory × Year trends...")

    cursor.execute("""
        SELECT exam_year, body_system_merged, subcategory, COUNT(*) AS n
        FROM questions
        WHERE body_system_merged IS NOT NULL AND subcategory IS NOT NULL
        GROUP BY exam_year, body_system_merged, subcategory
        ORDER BY body_system_merged, subcategory, exam_year
    """)

    # Gather data
    data = defaultdict(dict)  # {(bsm, subcat): {year: count}}
    for year, bsm, subcat, n in cursor.fetchall():
        data[(bsm, subcat)][year] = n

    # Build rows
    headers = (
        ["body_system", "subcategory"]
        + [str(y) for y in all_years]
        + ["total", "slope_per_yr"]
    )

    rows = []
    for (bsm, subcat) in sorted(data.keys()):
        year_counts = data[(bsm, subcat)]
        counts = [year_counts.get(y, 0) for y in all_years]
        total = sum(counts)
        slope = linear_slope(year_counts, all_years)
        rows.append([bsm, subcat] + counts + [total, slope])

    # Sort by body_system then total descending
    rows.sort(key=lambda r: (r[0], -r[len(all_years) + 2]))

    filepath = os.path.join(output_dir, "4a_body_system_subcategory_trends.csv")
    write_csv(filepath, headers, rows)
    return filepath


# ── Layer C: Concept Tag Trends ─────────────────────────────────────────────

def build_layer_c(cursor, all_years, output_dir, min_mentions=5):
    """Top diagnoses and drugs from concept_tags, trended by year."""
    print(f"\n[Layer C] Concept Tag trends (≥{min_mentions} mentions)...")

    cursor.execute("""
        SELECT exam_year, concept_tags
        FROM questions
        WHERE concept_tags IS NOT NULL
    """)

    # Explode concept_tags into per-year counters
    dx_by_year = defaultdict(Counter)    # {year: Counter({diagnosis: count})}
    drug_by_year = defaultdict(Counter)  # {year: Counter({drug: count})}
    dx_total = Counter()
    drug_total = Counter()

    for year, tags_json in cursor.fetchall():
        try:
            tags = json.loads(tags_json)
        except (json.JSONDecodeError, TypeError):
            continue
        for dx in tags.get("diagnoses", []):
            dx_lower = dx.strip().lower()
            if dx_lower:
                dx_by_year[year][dx_lower] += 1
                dx_total[dx_lower] += 1
        for drug in tags.get("drugs", []):
            drug_lower = drug.strip().lower()
            if drug_lower:
                drug_by_year[year][drug_lower] += 1
                drug_total[drug_lower] += 1

    # Filter to ≥ min_mentions
    top_dx = {k for k, v in dx_total.items() if v >= min_mentions}
    top_drugs = {k for k, v in drug_total.items() if v >= min_mentions}

    print(f"  Diagnoses ≥{min_mentions}: {len(top_dx)} / {len(dx_total)} total distinct")
    print(f"  Drugs ≥{min_mentions}: {len(top_drugs)} / {len(drug_total)} total distinct")

    # Build rows
    headers = (
        ["tag_type", "tag_value"]
        + [str(y) for y in all_years]
        + ["total", "slope_per_yr", "years_present"]
    )

    rows = []
    for dx in sorted(top_dx):
        year_counts = {y: dx_by_year[y].get(dx, 0) for y in all_years}
        counts = [year_counts[y] for y in all_years]
        total = dx_total[dx]
        slope = linear_slope(year_counts, all_years)
        years_present = sum(1 for c in counts if c > 0)
        rows.append(["diagnosis", dx] + counts + [total, slope, years_present])

    for drug in sorted(top_drugs):
        year_counts = {y: drug_by_year[y].get(drug, 0) for y in all_years}
        counts = [year_counts[y] for y in all_years]
        total = drug_total[drug]
        slope = linear_slope(year_counts, all_years)
        years_present = sum(1 for c in counts if c > 0)
        rows.append(["drug", drug] + counts + [total, slope, years_present])

    # Sort by total descending within each tag_type
    rows.sort(key=lambda r: (r[0], -r[len(all_years) + 2]))

    filepath = os.path.join(output_dir, "4a_concept_tag_trends.csv")
    write_csv(filepath, headers, rows)
    return filepath


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="FLAG 13 Layer 4a: ITE Topic Trends")
    parser.add_argument("--output-dir", default=None, help="Output directory for CSVs")
    parser.add_argument("--min-mentions", type=int, default=5, help="Minimum mentions for Layer C (default: 5)")
    args = parser.parse_args()

    output_dir = args.output_dir or SCRIPT_DIR
    os.makedirs(output_dir, exist_ok=True)

    db_path = os.path.normpath(DB_PATH)
    print(f"Database: {db_path}")
    print(f"Output:   {output_dir}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get exam years
    cursor.execute("SELECT DISTINCT exam_year FROM questions ORDER BY exam_year")
    all_years = [r[0] for r in cursor.fetchall()]
    print(f"Exam years: {all_years}")

    # Build all three layers
    a_path = build_layer_a(cursor, all_years, output_dir)
    b_path = build_layer_b(cursor, all_years, output_dir)
    c_path = build_layer_c(cursor, all_years, output_dir, min_mentions=args.min_mentions)

    conn.close()

    print("\n── Summary ──────────────────────────────────────")
    print(f"  Layer A: {os.path.basename(a_path)}")
    print(f"  Layer B: {os.path.basename(b_path)}")
    print(f"  Layer C: {os.path.basename(c_path)}")
    print("  Done.")


if __name__ == "__main__":
    main()
