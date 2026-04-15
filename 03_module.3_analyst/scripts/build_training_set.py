"""
build_training_set.py
=====================
Joins the ABFM-extracted body system labels (from condensed_labels_YYYY.json)
with question content from ite_intelligence.db to produce a training set for
the body system classification agent.

Input per question (DELIBERATELY MINIMAL — raw Q&A only):
  - question_text   (stem)
  - choices         (A through E)
  - correct_letter  (e.g. "B")
  - correct_text    (text of the correct answer)

Excluded intentionally (downstream of contaminated body_system):
  - concept_tags, blueprint, body_system (current DB value), ICD-10,
    explanation, citations, clinical_pathways

Output: body_system_training_set.json
  {
    "generated":    "2026-04-15",
    "years":        [2022, 2023],
    "total":        393,
    "taxonomy":     [...15 categories...],
    "class_counts": {"Respiratory": 77, ...},
    "questions": [
      {
        "qid":          "QID-2022-0001",
        "exam_year":    2022,
        "body_system_pre2024":  "Respiratory",
        "body_system":          "Respiratory",
        "question_text": "...",
        "choices":       [{"letter": "A", "text": "..."}, ...],
        "correct_letter": "B",
        "correct_text":  "..."
      },
      ...
    ]
  }

Usage:
    cd PROJECT_ROOT/03_module.3_analyst/scripts/
    python build_training_set.py
    python build_training_set.py --output-dir ../../03_module.3_analyst/outputs/body_system_labels/
"""

import json
import sqlite3
import argparse
from pathlib import Path
from datetime import date
from collections import Counter

# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH      = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"
LABELS_DIR   = PROJECT_ROOT / "03_module.3_analyst" / "outputs" / "body_system_labels"
OUTPUT_DIR   = LABELS_DIR   # write output alongside the label files

CONDENSED_LABEL_FILES = {
    2022: LABELS_DIR / "condensed_labels_2022.json",
    2023: LABELS_DIR / "condensed_labels_2023.json",
}


def load_condensed_labels(years: list[int]) -> dict[str, dict]:
    """
    Load condensed label files for the given years.
    Returns {qid_key: {"pre2024": cat, "final": cat, "year": year}}
    where qid_key is the zero-padded question number (e.g. "042").
    """
    all_labels = {}
    for year in years:
        path = CONDENSED_LABEL_FILES.get(year)
        if not path or not path.exists():
            print(f"WARNING: No condensed label file for {year}: {path}")
            continue
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        for q_num, final_cat in data["labels_final"].items():
            pre2024_cat = data["labels_pre2024"].get(q_num, final_cat)
            all_labels[(year, q_num)] = {
                "pre2024": pre2024_cat,
                "final":   final_cat,
                "year":    year,
            }
    return all_labels


def load_questions_from_db(years: list[int], db_path: Path) -> dict[tuple, dict]:
    """
    Load raw question content from the DB for the given exam years.
    Returns {(exam_year, zero_padded_q_num): {qid, question_text, choices, correct_letter, correct_text}}

    Question number mapping: QID-2022-0042 → q_num "042" (3-digit zero-padded,
    matching the format used in score report labels).
    """
    if not db_path.exists():
        raise FileNotFoundError(f"DB not found: {db_path}")

    conn = sqlite3.connect(f"file:{db_path}?immutable=1", uri=True)
    conn.row_factory = sqlite3.Row

    placeholders = ",".join("?" * len(years))
    rows = conn.execute(f"""
        SELECT qid, exam_year, question_text, choices,
               correct_letter, correct_text
        FROM questions
        WHERE exam_year IN ({placeholders})
        ORDER BY exam_year, qid
    """, years).fetchall()
    conn.close()

    questions = {}
    for row in rows:
        qid = row["qid"]
        # QID-2022-0042 → q_num "042"
        parts = qid.split("-")
        if len(parts) == 3:
            q_num_str = parts[2].lstrip("0") or "0"
            q_num_padded = q_num_str.zfill(3)
        else:
            continue

        # Parse choices JSON if it's a JSON string
        choices_raw = row["choices"]
        if isinstance(choices_raw, str):
            try:
                choices = json.loads(choices_raw)
            except Exception:
                choices = []
        else:
            choices = choices_raw or []

        questions[(row["exam_year"], q_num_padded)] = {
            "qid":          qid,
            "exam_year":    row["exam_year"],
            "question_text": row["question_text"] or "",
            "choices":      choices,
            "correct_letter": row["correct_letter"] or "",
            "correct_text": row["correct_text"] or "",
        }

    return questions


def build_training_set(years: list[int] = None) -> dict:
    """Build and return the full training set dict."""
    if years is None:
        years = [2022, 2023]

    print(f"Loading condensed labels for years: {years}")
    labels = load_condensed_labels(years)
    print(f"  Loaded {len(labels)} labeled questions")

    print(f"Loading question content from DB...")
    questions = load_questions_from_db(years, DB_PATH)
    print(f"  Loaded {len(questions)} questions from DB")

    # Join on (year, q_num)
    training = []
    missing_in_db  = []
    missing_labels = []

    for (year, q_num), label_info in sorted(labels.items()):
        q_key = (year, q_num)
        if q_key not in questions:
            missing_in_db.append((year, q_num))
            continue
        q = questions[q_key]
        training.append({
            "qid":                  q["qid"],
            "exam_year":            year,
            "body_system_pre2024":  label_info["pre2024"],
            "body_system":          label_info["final"],
            "question_text":        q["question_text"],
            "choices":              q["choices"],
            "correct_letter":       q["correct_letter"],
            "correct_text":         q["correct_text"],
        })

    if missing_in_db:
        print(f"WARNING: {len(missing_in_db)} labeled questions not found in DB:")
        for yr, qn in missing_in_db[:10]:
            print(f"  {yr} Q{qn}")

    class_counts = Counter(t["body_system"] for t in training)
    from condense_taxonomy import FINAL_TAXONOMY

    result = {
        "generated":    str(date.today()),
        "years":        years,
        "total":        len(training),
        "taxonomy":     FINAL_TAXONOMY,
        "class_counts": dict(sorted(class_counts.items())),
        "questions":    training,
    }

    return result


def print_summary(result: dict) -> None:
    print(f"\n=== Training Set Summary ===")
    print(f"Generated:  {result['generated']}")
    print(f"Years:      {result['years']}")
    print(f"Total Qs:   {result['total']}")
    print(f"Classes:    {len(result['taxonomy'])}")
    print()
    print("Class distribution:")
    for cat in result["taxonomy"]:
        n = result["class_counts"].get(cat, 0)
        bar = "█" * n
        print(f"  {cat:<30} {n:3d}  {bar}")
    print()
    # Warn about thin classes (< 10 examples)
    thin = [(cat, n) for cat, n in result["class_counts"].items() if n < 10]
    if thin:
        print(f"⚠ Thin classes (< 10 examples — watch these in validation):")
        for cat, n in sorted(thin, key=lambda x: x[1]):
            print(f"  {cat}: {n}")


def main():
    parser = argparse.ArgumentParser(description="Build body system classification training set")
    parser.add_argument("--years", type=int, nargs="+", default=[2022, 2023],
                        help="Exam years to include (default: 2022 2023)")
    parser.add_argument("--output-dir", type=str, default=str(OUTPUT_DIR),
                        help=f"Output directory (default: {OUTPUT_DIR})")
    args = parser.parse_args()

    result = build_training_set(args.years)
    print_summary(result)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "body_system_training_set.json"
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Written: {out_path}")


if __name__ == "__main__":
    main()
