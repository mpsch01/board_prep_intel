#!/usr/bin/env python3
"""
02_ite_categorizer.py

Classifies ITE questions into the ABFM 15-category body system taxonomy
using SBERT embeddings + XGBoost. Appends PrimaryCategory column.

Usage:
    python 02_ite_categorizer.py              # classify ITE_{YEAR}_Raw.csv only
    python 02_ite_categorizer.py --all        # re-classify full master bank
    python 02_ite_categorizer.py --year 2026  # override exam year

Inputs (from _archive_/04_reference_data/):
    Updated_QA_Categories.xlsx
    misclassified_manual_review.xlsx
    body_system_labels_2022_2024.csv

I/O from _archive_/02_question_bank/:
    ITE_{YEAR}_Raw.csv  → ITE_{YEAR}_Categorized.csv
    ABFM_ITE_Master.csv → ABFM_ITE_Master.csv (in-place, when --all)

Migrated from TEMP_06_ite_pipeline_TEMP (BATON 007)
"""

import argparse
import pandas as pd
import os
import sys
import nltk
from pathlib import Path
from sentence_transformers import SentenceTransformer
from xgboost import XGBClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
REF_DATA     = PROJECT_ROOT / "_archive_" / "04_reference_data"
QBANK_DIR    = PROJECT_ROOT / "_archive_" / "02_question_bank"

# CONFIG — update for each new exam year (or override with --year)
EXAM_YEAR = "2025"

nltk.download('stopwords', quiet=True)

# Official ABFM body system taxonomy (15 categories)
STANDARD_CATEGORIES = {
    'Respiratory', 'Cardiovascular', 'Musculoskeletal', 'Gastrointestinal',
    'Special Sensory', 'Endocrine', 'Integumentary', 'Neurologic',
    'Reproductive:Female', 'Reproductive:Male', 'Hematologic/Immune',
    'Psychogenic', 'Nephrologic', 'Population-Based Care', 'Patient-Based Systems'
}

CATEGORY_MAP = {
    'cardiovascular':           'Cardiovascular',
    'endocrine':                'Endocrine',
    'gastrointestinal':         'Gastrointestinal',
    'gastroenterology':         'Gastrointestinal',
    'musculoskeletal':          'Musculoskeletal',
    'respiratory':              'Respiratory',
    'dermatology':              'Integumentary',
    'integumentary':            'Integumentary',
    'hematology':               'Hematologic/Immune',
    'hematologic/immune':       'Hematologic/Immune',
    'neurology':                'Neurologic',
    'neurologic':               'Neurologic',
    'ob/gyn':                   'Reproductive:Female',
    'reproductive:female':      'Reproductive:Female',
    'reproductive:male':        'Reproductive:Male',
    'population health':        'Population-Based Care',
    'population-based care':    'Population-Based Care',
    'psychiatry':               'Psychogenic',
    'psychogenic':              'Psychogenic',
    'urology':                  'Nephrologic',
    'renal':                    'Nephrologic',
    'nephrologic':              'Nephrologic',
    'special sensory':          'Special Sensory',
    'patient-based systems':    'Patient-Based Systems',
}


def normalize_category(cat):
    if pd.isna(cat):
        return None
    return CATEGORY_MAP.get(str(cat).strip().lower())


def run_categorization(all_questions=False, year=EXAM_YEAR):
    intel_path    = REF_DATA  / "Updated_QA_Categories.xlsx"
    misclass_path = REF_DATA  / "misclassified_manual_review.xlsx"
    body_sys_path = REF_DATA  / "body_system_labels_2022_2024.csv"
    master_path   = QBANK_DIR / "ABFM_ITE_Master.csv"

    if all_questions:
        source_path  = master_path
        out_path     = master_path
        source_label = "Master bank"
    else:
        source_path  = QBANK_DIR / f"ITE_{year}_Raw.csv"
        out_path     = QBANK_DIR / f"ITE_{year}_Categorized.csv"
        source_label = f"Raw CSV ({year})"

    for p, label in [(source_path, source_label), (intel_path, "Training data")]:
        if not os.path.exists(p):
            print(f"ERROR {label} not found: {p}")
            return

    print(f"DEBUG: Loading data and SBERT model (this may take 30-60s)...")
    try:
        df_train = pd.read_excel(intel_path)
        df_new   = pd.read_csv(source_path)
    except Exception as e:
        print(f"ERROR loading data: {e}")
        return

    for col in ["Question", "Normalized Category", "Answer Explanation"]:
        if col not in df_train.columns:
            print(f"ERROR Training data missing required column: '{col}'")
            return

    df_train = df_train[["Question", "Answer Explanation", "Normalized Category"]].copy()
    print(f"INFO Base training set: {len(df_train)} rows")

    df_train["Normalized Category"] = df_train["Normalized Category"].apply(normalize_category)
    before = len(df_train)
    df_train = df_train[df_train["Normalized Category"].isin(STANDARD_CATEGORIES)].copy()
    print(f"INFO After taxonomy normalization: {len(df_train)} rows ({before - len(df_train)} unmappable dropped)")

    if os.path.exists(misclass_path):
        try:
            df_fix = pd.read_excel(misclass_path)
            df_fix = df_fix.rename(columns={"manual review": "Normalized Category"})
            df_fix["Normalized Category"] = df_fix["Normalized Category"].apply(normalize_category)
            df_fix = df_fix[df_fix["Normalized Category"].isin(STANDARD_CATEGORIES)].copy()
            df_fix["Answer Explanation"] = ""
            df_fix = df_fix[["Question", "Answer Explanation", "Normalized Category"]]
            df_train = pd.concat([df_train, df_fix], ignore_index=True)
            print(f"INFO Appended {len(df_fix)} manually corrected rows (total: {len(df_train)})")
        except Exception as e:
            print(f"WARNING Could not load misclassified_manual_review.xlsx: {e}")
    else:
        print("WARNING misclassified_manual_review.xlsx not found — skipping manual corrections")

    if os.path.exists(body_sys_path) and os.path.exists(master_path):
        try:
            df_bs     = pd.read_csv(body_sys_path)
            df_master = pd.read_csv(master_path)
            YEAR_OFFSET = {2020: 0, 2021: 200, 2022: 400, 2023: 600, 2024: 800, 2025: 0}
            df_bs["Question ID"] = df_bs.apply(
                lambda r: f"Q{int(r['Year'])}-{int(r['QuestionNum']) + YEAR_OFFSET.get(int(r['Year']), 0):03d}",
                axis=1
            )
            df_bs = df_bs.merge(df_master[["Question ID", "QuestionStem"]], on="Question ID", how="left")
            df_bs = df_bs.rename(columns={"QuestionStem": "Question", "BodySystem": "Normalized Category"})
            df_bs["Answer Explanation"] = ""
            df_bs = df_bs[["Question", "Answer Explanation", "Normalized Category"]].dropna(subset=["Question"])
            df_bs = df_bs[df_bs["Normalized Category"].isin(STANDARD_CATEGORIES)].copy()
            df_train = pd.concat([df_train, df_bs], ignore_index=True)
            print(f"INFO Appended {len(df_bs)} gold-standard body system rows (total: {len(df_train)})")
        except Exception as e:
            print(f"WARNING Could not load body_system_labels: {e}")
    else:
        print("WARNING body_system_labels or master bank not found — skipping gold rows")

    df_train["TrainingText"] = (
        df_train["Question"].astype(str) + " " +
        df_train["Answer Explanation"].fillna("").astype(str)
    ).str.strip()

    sbert = SentenceTransformer('all-MiniLM-L6-v2')
    print("DEBUG: Encoding training data...")
    X_train_all = sbert.encode(df_train["TrainingText"].tolist(), show_progress_bar=False)
    print("DEBUG: Encoding new questions...")
    X_new = sbert.encode(df_new["QuestionStem"].astype(str).tolist(), show_progress_bar=False)

    le = LabelEncoder()
    y_train_all = le.fit_transform(df_train["Normalized Category"])

    X_tr, X_val, y_tr, y_val = train_test_split(
        X_train_all, y_train_all, test_size=0.2, random_state=42, stratify=y_train_all
    )
    clf_eval = XGBClassifier()
    clf_eval.fit(X_tr, y_tr)
    val_acc = accuracy_score(y_val, clf_eval.predict(X_val))
    print(f"INFO Classifier accuracy on 20% validation split: {val_acc:.1%}")

    clf = XGBClassifier()
    clf.fit(X_train_all, y_train_all)

    n_label = "all questions" if all_questions else f"{year} questions"
    print(f"DEBUG: Applying categories to {n_label}...")
    df_new["PrimaryCategory"] = le.inverse_transform(clf.predict(X_new))

    try:
        df_new.to_csv(out_path, index=False)
    except OSError as e:
        print(f"ERROR writing output: {e}")
        return
    print(f"OK SUCCESS: {len(df_new)} questions categorized -> {out_path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="Re-classify entire master bank")
    ap.add_argument("--year", default=EXAM_YEAR, help="Exam year for single-year mode")
    args = ap.parse_args()
    run_categorization(all_questions=args.all, year=args.year)


if __name__ == "__main__":
    main()
