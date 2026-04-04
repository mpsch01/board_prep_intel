#!/usr/bin/env python3
"""
classify_ite_year.py
====================
Assigns body_system to ITE questions using SBERT embeddings + XGBoost.
Reads questions directly from ite_intelligence.db, updates in place.

Runs after extract_ite_year.py. Targets questions where body_system IS NULL
for the specified year — safe to re-run if classification is partial.

Usage:
    python classify_ite_year.py --year 2026
    python classify_ite_year.py --year 2026 --dry-run

Training data (from _archive_/04_reference_data/):
    Updated_QA_Categories.xlsx          — labeled question bank
    misclassified_manual_review.xlsx    — manual correction overrides (optional)
    body_system_labels_2022_2024.csv    — gold-standard body system labels (optional)

Model: sentence-transformers/all-MiniLM-L6-v2  +  XGBoostClassifier
       (~30-60s to load and encode training set)

Downstream (run after this script):
    blueprint_api_classifier_v2.py     → blueprint (API, NULL rows only)
    unified_keyword_extractor.py       → keywords
    build_ite_question_icd10.py        → ICD-10 linkage
    compute_embeddings.py --new-only   → question_vec
"""

import argparse
import sqlite3
import json
import os
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd
import nltk
from sentence_transformers import SentenceTransformer
from xgboost import XGBClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

nltk.download('stopwords', quiet=True)

# ── Paths ────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH      = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"
REF_DATA     = PROJECT_ROOT / "_archive_" / "04_reference_data"
LOG_DIR      = PROJECT_ROOT / "00_database" / "logs"

# ── Body system taxonomy ─────────────────────────────────────────────────────
STANDARD_CATEGORIES = {
    'Respiratory', 'Cardiovascular', 'Musculoskeletal', 'Gastrointestinal',
    'Special Sensory', 'Endocrine', 'Integumentary', 'Neurologic',
    'Reproductive:Female', 'Reproductive:Male', 'Hematologic/Immune',
    'Psychogenic', 'Nephrologic', 'Population-Based Care', 'Patient-Based Systems'
}

CATEGORY_MAP = {
    'cardiovascular':       'Cardiovascular',
    'endocrine':            'Endocrine',
    'gastrointestinal':     'Gastrointestinal',
    'gastroenterology':     'Gastrointestinal',
    'musculoskeletal':      'Musculoskeletal',
    'respiratory':          'Respiratory',
    'dermatology':          'Integumentary',
    'integumentary':        'Integumentary',
    'hematology':           'Hematologic/Immune',
    'hematologic/immune':   'Hematologic/Immune',
    'neurology':            'Neurologic',
    'neurologic':           'Neurologic',
    'ob/gyn':               'Reproductive:Female',
    'reproductive:female':  'Reproductive:Female',
    'reproductive:male':    'Reproductive:Male',
    'population health':    'Population-Based Care',
    'population-based care':'Population-Based Care',
    'psychiatry':           'Psychogenic',
    'psychogenic':          'Psychogenic',
    'urology':              'Nephrologic',
    'renal':                'Nephrologic',
    'nephrologic':          'Nephrologic',
    'special sensory':      'Special Sensory',
    'patient-based systems':'Patient-Based Systems',
}


def normalize_category(cat):
    if pd.isna(cat):
        return None
    return CATEGORY_MAP.get(str(cat).strip().lower())


def load_training_data() -> pd.DataFrame:
    """
    Loads and assembles training set from reference data files.
    Returns DataFrame with columns: [TrainingText, Normalized Category]
    """
    intel_path    = REF_DATA / "Updated_QA_Categories.xlsx"
    misclass_path = REF_DATA / "misclassified_manual_review.xlsx"
    body_sys_path = REF_DATA / "body_system_labels_2022_2024.csv"

    if not intel_path.exists():
        raise FileNotFoundError(f"Training data not found: {intel_path}")

    print("  Loading training data...")
    df_train = pd.read_excel(intel_path)

    for col in ["Question", "Normalized Category", "Answer Explanation"]:
        if col not in df_train.columns:
            raise ValueError(f"Training data missing column: '{col}'")

    df_train = df_train[["Question", "Answer Explanation", "Normalized Category"]].copy()
    df_train["Normalized Category"] = df_train["Normalized Category"].apply(normalize_category)
    df_train = df_train[df_train["Normalized Category"].isin(STANDARD_CATEGORIES)].copy()
    print(f"  Base training set: {len(df_train)} rows")

    # Manual correction overrides
    if misclass_path.exists():
        df_fix = pd.read_excel(misclass_path)
        df_fix = df_fix.rename(columns={"manual review": "Normalized Category"})
        df_fix["Normalized Category"] = df_fix["Normalized Category"].apply(normalize_category)
        df_fix = df_fix[df_fix["Normalized Category"].isin(STANDARD_CATEGORIES)].copy()
        df_fix["Answer Explanation"] = ""
        df_fix = df_fix[["Question", "Answer Explanation", "Normalized Category"]]
        df_train = pd.concat([df_train, df_fix], ignore_index=True)
        print(f"  +{len(df_fix)} manual corrections (total: {len(df_train)})")

    # Gold-standard labels (2022-2024)
    if body_sys_path.exists():
        df_bs = pd.read_csv(body_sys_path)
        df_bs = df_bs.rename(columns={"BodySystem": "Normalized Category"})
        df_bs["Answer Explanation"] = ""
        df_bs = df_bs[["Question", "Answer Explanation", "Normalized Category"]].dropna(subset=["Question"])
        df_bs = df_bs[df_bs["Normalized Category"].isin(STANDARD_CATEGORIES)].copy()
        df_train = pd.concat([df_train, df_bs], ignore_index=True)
        print(f"  +{len(df_bs)} gold-standard rows (total: {len(df_train)})")

    df_train["TrainingText"] = (
        df_train["Question"].astype(str) + " " +
        df_train["Answer Explanation"].fillna("").astype(str)
    ).str.strip()

    return df_train


def load_target_questions(conn: sqlite3.Connection, year: str) -> list[dict]:
    """Fetches questions for the given year where body_system is NULL."""
    cur = conn.execute(
        """SELECT qid, question_text, explanation
           FROM questions
           WHERE exam_year = ? AND body_system IS NULL
           ORDER BY qid""",
        (int(year),)
    )
    rows = [{"qid": r[0], "question_text": r[1], "explanation": r[2] or ""} for r in cur.fetchall()]
    return rows


def classify_and_update(conn: sqlite3.Connection, year: str,
                        dry_run: bool = False) -> dict:
    counts = {"classified": 0, "skipped": 0, "train_accuracy": None}

    # ── Load targets ─────────────────────────────────────────────────────────
    targets = load_target_questions(conn, year)
    if not targets:
        print(f"  No unclassified questions for {year}.")
        return counts

    print(f"  Target questions (body_system IS NULL, year={year}): {len(targets)}")

    # ── Load training data ────────────────────────────────────────────────────
    df_train = load_training_data()

    # ── SBERT encode ─────────────────────────────────────────────────────────
    print("  Loading SBERT model (all-MiniLM-L6-v2)...")
    sbert = SentenceTransformer('all-MiniLM-L6-v2')

    print("  Encoding training data...")
    X_train = sbert.encode(df_train["TrainingText"].tolist(), show_progress_bar=False)

    target_texts = [
        (t["question_text"] + " " + t["explanation"]).strip() for t in targets
    ]
    print(f"  Encoding {len(target_texts)} target questions...")
    X_target = sbert.encode(target_texts, show_progress_bar=False)

    # ── XGBoost train ─────────────────────────────────────────────────────────
    le = LabelEncoder()
    y_train = le.fit_transform(df_train["Normalized Category"])

    X_tr, X_val, y_tr, y_val = train_test_split(
        X_train, y_train, test_size=0.15, random_state=42, stratify=y_train
    )
    clf = XGBClassifier(n_estimators=200, max_depth=6,
                        use_label_encoder=False, eval_metric='mlogloss',
                        verbosity=0)
    clf.fit(X_tr, y_tr)

    val_acc = accuracy_score(y_val, clf.predict(X_val))
    counts["train_accuracy"] = round(val_acc, 4)
    print(f"  Validation accuracy: {val_acc:.1%}")

    # ── Predict + update ─────────────────────────────────────────────────────
    y_pred      = clf.predict(X_target)
    predictions = le.inverse_transform(y_pred)

    cur = conn.cursor()
    for target, predicted_category in zip(targets, predictions):
        if not dry_run:
            cur.execute(
                "UPDATE questions SET body_system = ? WHERE qid = ?",
                (predicted_category, target["qid"])
            )
        counts["classified"] += 1

    if not dry_run:
        conn.commit()

    return counts


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description="Classify body_system for ITE questions using SBERT + XGBoost"
    )
    ap.add_argument("--year",    required=True, help="Exam year, e.g. 2026")
    ap.add_argument("--dry-run", action="store_true",
                    help="Classify and report — no DB writes")
    args = ap.parse_args()
    year = args.year

    print(f"\n{'='*60}")
    print(f"  classify_ite_year.py  |  Year: {year}  |  dry-run: {args.dry_run}")
    print(f"{'='*60}\n")

    conn   = sqlite3.connect(DB_PATH)
    counts = classify_and_update(conn, year, dry_run=args.dry_run)
    conn.close()

    # ── Log ──────────────────────────────────────────────────────────────────
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    log_data = {
        "script":           "classify_ite_year.py",
        "year":             year,
        "dry_run":          args.dry_run,
        "timestamp":        ts,
        "counts":           counts,
        "next_steps": [
            "blueprint_api_classifier_v2.py        → blueprint",
            "unified_keyword_extractor.py          → keywords",
            "build_ite_question_icd10.py           → ICD-10",
            "compute_embeddings.py --new-only      → question_vec",
        ]
    }
    if not args.dry_run:
        import json as _json
        log_path = LOG_DIR / f"classify_ite_year_{year}_{ts}.json"
        log_path.write_text(_json.dumps(log_data, indent=2))
        print(f"  Log: {log_path.name}")

    # ── Summary ──────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  {'[DRY RUN] ' if args.dry_run else ''}Results for {year}:")
    print(f"    Classified : {counts['classified']}")
    if counts["train_accuracy"]:
        print(f"    Val acc    : {counts['train_accuracy']:.1%}")
    if not args.dry_run:
        print(f"\n  Next: python blueprint_api_classifier_v2.py")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
