"""
extract_score_report_labels.py
==============================
Extracts per-question body system labels from ABFM ITE Item Performance Report
PDFs (the per-resident "blueprint category" score reports).

These reports are the ground truth source for body system classification —
ABFM explicitly places each question number under its assigned body system column.
This is the foundation of the body system QC pipeline.

Supported years: 2022, 2023 (same 16-category pre-2024 taxonomy)
NOT supported: 2024 (different 5-category service-area taxonomy in blueprint_report.PDF)

Input PDF format:
  Page 1 — 8 categories across the top:
    Respiratory | Cardiovascular | Musculoskeletal | Gastrointestinal |
    Special Sensory | Endocrine | Integumentary | Neurologic
  Page 2 — 8 categories across the top:
    Psychogenic | Reproductive:Female | Reproductive:Male | Nephrologic |
    Hematologic/Immune | Nonspecific | Population-Based Care | Patient-Based Systems
  Each question number (3-digit integer, optionally + P suffix) appears as plain text
  under its assigned column header. Y-position = score percentile (irrelevant).

Usage:
    cd PROJECT_ROOT/03_module.3_analyst/scripts/
    python extract_score_report_labels.py --year 2022 \\
        --pdf ../../03_module.3_analyst/resident_data/ITE_michael_scholl/inputs/scholl_2022_Item_Blueprint_Performance.PDF
    python extract_score_report_labels.py --year 2023 \\
        --pdf ../../03_module.3_analyst/resident_data/ITE_michael_scholl/inputs/scholl_2023_blueprint.PDF
    python extract_score_report_labels.py --year 2022 --year 2023 --auto
        (uses default Scholl PDF paths, outputs both years to OUTPUT_DIR)

Output:
    JSON file per year: score_report_labels_YYYY.json
    {
      "year": 2022,
      "source_pdf": "...",
      "total_questions": 195,
      "deleted_questions": [63, 97, 138, 157, 166],
      "labels": {
        "001": "Cardiovascular",
        "002": "Respiratory",
        ...
      }
    }

    Also prints a summary table to stdout.
"""

import re
import json
import argparse
from pathlib import Path
from collections import defaultdict

try:
    import pdfplumber
except ImportError:
    print("ERROR: pdfplumber not found. Install with: pip install pdfplumber --break-system-packages")
    raise

# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
RESIDENT_DIR = PROJECT_ROOT / "03_module.3_analyst" / "resident_data" / "ITE_michael_scholl" / "inputs"
OUTPUT_DIR   = PROJECT_ROOT / "03_module.3_analyst" / "outputs" / "body_system_labels"

# ── Default PDF paths per year ─────────────────────────────────────────────────
DEFAULT_PDFS = {
    2022: RESIDENT_DIR / "scholl_2022_Item_Blueprint_Performance.PDF",
    2023: RESIDENT_DIR / "scholl_2023_blueprint.PDF",
}

# ── Known category anchors ─────────────────────────────────────────────────────
# Maps the first distinctive word of each category header to the canonical name.
# Multi-word headers (e.g., "Special Sensory") are identified by their first word.
# "Reproductive:" appears twice — disambiguated by checking for "Female"/"Male" below.
CATEGORY_ANCHOR_MAP = {
    # Page 1 anchors
    "Respiratory":     "Respiratory",
    "Cardiovascular":  "Cardiovascular",
    "Musculoskeletal": "Musculoskeletal",
    "Gastrointestinal":"Gastrointestinal",
    "Special":         "Special Sensory",   # "Special Sensory" spans two words
    "Endocrine":       "Endocrine",
    "Integumentary":   "Integumentary",
    "Neurologic":      "Neurologic",
    # Page 2 anchors
    "Psychogenic":     "Psychogenic",
    "Nephrologic":     "Nephrologic",
    "Hematologic/":    "Hematologic/Immune",  # split as "Hematologic/" + "Immune"
    "Nonspecific":     "Nonspecific",
    "Population-Based":"Population-Based Care",
    "Patient-Based":   "Patient-Based Systems",
    # "Reproductive:" is handled specially due to duplication
}

# Y-threshold: header zone. Words above this are notes/title, below are data.
HEADER_Y_MAX   = 215.0   # category headers appear at top~203
DATA_Y_MIN     = 217.0   # question numbers start below the header band
SCORE_X_MAX    =  80.0   # score percentile labels (1000, 950...) are at x0 < 80

# Regex: 3-digit question number, optionally followed by P (psychometric exclusion)
Q_PATTERN = re.compile(r'^(\d{3})(P?)$')

# Regex: note-section question numbers (e.g. "Questions 63, 97 were deleted...")
# We detect deleted questions from the notes text on each page.
DELETED_PATTERN = re.compile(r'Questions?\s+([\d,\s]+(?:and\s+\d+)?)\s+were\s+deleted')


def find_deleted_questions(words: list[dict]) -> list[int]:
    """
    Parse the notes section of a PDF page to find deleted question numbers.
    Notes appear above the chart (top < HEADER_Y_MAX).
    """
    note_text = " ".join(
        w["text"] for w in words
        if w["top"] < HEADER_Y_MAX - 10
    )
    deleted = []
    for m in DELETED_PATTERN.finditer(note_text):
        nums = re.findall(r'\d+', m.group(1))
        deleted.extend(int(n) for n in nums)
    return deleted


def build_column_map(words: list[dict]) -> list[tuple[str, float, float]]:
    """
    From the header row of one page, build a list of (category_name, x_left, x_right)
    tuples in left-to-right order.

    Strategy:
    1. Find all words in the header zone (top between 190 and HEADER_Y_MAX)
    2. Match each word to a known category anchor
    3. For "Reproductive:" which appears twice, look at the next word on the line
       slightly below to determine Female vs. Male
    4. Sort columns by x_left and assign boundaries as midpoints between adjacent columns
    """
    header_words = [w for w in words if 190 <= w["top"] <= HEADER_Y_MAX]

    # Collect (category_name, x0) pairs — one per column
    columns = {}  # x0 → category_name (de-duplicated by x0)

    for w in header_words:
        text = w["text"]
        if text in CATEGORY_ANCHOR_MAP:
            cat = CATEGORY_ANCHOR_MAP[text]
            columns[w["x0"]] = cat
        elif text == "Reproductive:":
            # Will be resolved to Female/Male below — store placeholder
            columns[w["x0"]] = f"_Reproductive_{w['x0']:.0f}"

    # Resolve Reproductive: Female vs. Male by finding "Female"/"Male" words
    # They appear a few points lower in the header zone
    female_words = [w for w in header_words if w["text"] == "Female"]
    male_words   = [w for w in header_words if w["text"] == "Male"]

    repro_placeholders = sorted(
        [(x0, cat) for x0, cat in columns.items() if cat.startswith("_Reproductive_")],
        key=lambda t: t[0]
    )

    if len(repro_placeholders) >= 1 and female_words:
        # First Reproductive: column is Female (leftmost)
        x0_female = repro_placeholders[0][0]
        columns[x0_female] = "Reproductive: Female"
    if len(repro_placeholders) >= 2 and male_words:
        x0_male = repro_placeholders[1][0]
        columns[x0_male] = "Reproductive: Male"

    # Sort by x0
    sorted_cols = sorted(columns.items(), key=lambda t: t[0])

    if not sorted_cols:
        return []

    # Assign x_left and x_right boundaries using MIDPOINTS between adjacent column
    # centers. The header x0 is the text anchor, but question numbers may be printed
    # anywhere within the column — sometimes closer to the neighboring column's header.
    # Using midpoints is more robust than "header_x0 - N".
    result = []
    xs = [x0 for x0, _ in sorted_cols]
    for i, (x0, cat) in enumerate(sorted_cols):
        if i == 0:
            # Leftmost column: anchor to just past score-axis labels so questions
            # printed slightly left of the header x0 (e.g. x0=97.5) are captured.
            x_left = SCORE_X_MAX + 1
        else:
            # Midpoint between this column center and the previous one
            x_left = (xs[i - 1] + xs[i]) / 2

        if i + 1 < len(sorted_cols):
            # Midpoint between this column center and the next one
            x_right = (xs[i] + xs[i + 1]) / 2
        else:
            x_right = 9999

        result.append((cat, x_left, x_right))

    return result


def assign_to_column(x0: float, columns: list[tuple]) -> str | None:
    """Given x0 of a word, return the category whose x-range it falls within."""
    for cat, x_left, x_right in columns:
        if x_left <= x0 < x_right:
            return cat
    return None


def extract_page_labels(page, deleted_set: set[int]) -> dict[str, str]:
    """
    Extract question → body_system mappings from one page.
    Returns {question_num_str: category_name}.
    Skips deleted questions and score-axis labels.
    """
    words = page.extract_words()
    columns = build_column_map(words)

    if not columns:
        return {}

    labels = {}
    for w in words:
        if w["top"] < DATA_Y_MIN:
            continue  # notes or header zone
        if w["x0"] <= SCORE_X_MAX:
            continue  # score percentile axis label (1000, 950, ...)

        m = Q_PATTERN.match(w["text"])
        if not m:
            continue

        q_num = int(m.group(1))
        if q_num in deleted_set:
            continue  # deleted question — skip

        cat = assign_to_column(w["x0"], columns)
        if cat:
            labels[f"{q_num:03d}"] = cat

    return labels


def extract_labels_from_pdf(pdf_path: Path, year: int) -> dict:
    """
    Extract all question → body_system labels from a blueprint PDF.
    Returns the full output dict (year, source, total, deleted, labels).
    """
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    all_labels  = {}
    all_deleted = set()

    with pdfplumber.open(str(pdf_path)) as pdf:
        for page_num, page in enumerate(pdf.pages):
            words = page.extract_words()

            # Collect deleted question numbers from this page's notes
            page_deleted = find_deleted_questions(words)
            all_deleted.update(page_deleted)

        # Second pass: extract labels now that we know all deleted questions
        for page_num, page in enumerate(pdf.pages):
            page_labels = extract_page_labels(page, all_deleted)
            # Later pages don't override earlier — but each Q appears on exactly one page
            for qid, cat in page_labels.items():
                if qid not in all_labels:
                    all_labels[qid] = cat

    return {
        "year":             year,
        "source_pdf":       str(pdf_path),
        "total_questions":  len(all_labels),
        "deleted_questions": sorted(all_deleted),
        "labels":           dict(sorted(all_labels.items())),
    }


def print_summary(result: dict) -> None:
    """Print a summary table of category counts."""
    year   = result["year"]
    labels = result["labels"]
    total  = result["total_questions"]
    deleted = result["deleted_questions"]

    counts = defaultdict(int)
    for cat in labels.values():
        counts[cat] += 1

    print(f"\n=== {year} Body System Labels ===")
    print(f"Questions extracted: {total}")
    print(f"Deleted (excluded): {deleted}")
    print(f"\nCategory breakdown:")
    for cat, n in sorted(counts.items(), key=lambda x: -x[1]):
        bar = "█" * n
        print(f"  {cat:<30} {n:3d}  {bar}")
    print()


def main():
    parser = argparse.ArgumentParser(description="Extract body system labels from ABFM score report PDFs")
    parser.add_argument("--year", type=int, action="append",
                        help="Exam year (2022 or 2023). Can specify multiple times.")
    parser.add_argument("--pdf", type=str,
                        help="Path to the blueprint PDF (required if not using --auto)")
    parser.add_argument("--auto", action="store_true",
                        help="Use default Scholl PDF paths for all supported years")
    parser.add_argument("--output-dir", type=str, default=None,
                        help=f"Output directory (default: {OUTPUT_DIR})")
    args = parser.parse_args()

    out_dir = Path(args.output_dir) if args.output_dir else OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    # Determine which years/PDFs to process
    tasks = []
    if args.auto:
        for yr, pdf_path in DEFAULT_PDFS.items():
            tasks.append((yr, pdf_path))
    elif args.year and args.pdf:
        if len(args.year) > 1:
            parser.error("--pdf can only be used with a single --year")
        tasks.append((args.year[0], Path(args.pdf)))
    elif args.year:
        for yr in args.year:
            if yr not in DEFAULT_PDFS:
                parser.error(f"No default PDF path for year {yr}. Use --pdf.")
            tasks.append((yr, DEFAULT_PDFS[yr]))
    else:
        parser.error("Specify --auto, or --year with optional --pdf")

    all_results = {}

    for year, pdf_path in tasks:
        print(f"\nProcessing {year}: {pdf_path.name}")
        result = extract_labels_from_pdf(pdf_path, year)
        print_summary(result)

        out_path = out_dir / f"score_report_labels_{year}.json"
        out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"Written: {out_path}")
        all_results[year] = result

    # Cross-year validation if both years processed
    if len(all_results) == 2:
        y1, y2 = sorted(all_results.keys())
        labels1 = set(all_results[y1]["labels"].values())
        labels2 = set(all_results[y2]["labels"].values())
        print(f"\n=== Cross-year taxonomy check ===")
        print(f"Categories in {y1}: {sorted(labels1)}")
        print(f"Categories in {y2}: {sorted(labels2)}")
        if labels1 == labels2:
            print("✓ Taxonomy is consistent across years")
        else:
            print(f"⚠ Taxonomy differs!")
            print(f"  Only in {y1}: {labels1 - labels2}")
            print(f"  Only in {y2}: {labels2 - labels1}")


if __name__ == "__main__":
    main()
