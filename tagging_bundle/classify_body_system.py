#!/usr/bin/env python3
"""
classify_body_system.py

Trains a TF-IDF + LinearSVC classifier on the 2022-2023 body system
gold standard labels extracted from ABFM score report PDFs.

Applies the classifier to:
  - 2020, 2021 (no PDFs available — fully predicted)
  - 2022 (5 missing), 2023 (2 missing), 2024 (125 missing)

Outputs:
  body_system_full.csv     — all 1200 questions with BodySystem label + source
  body_system_gaps.csv     — only the predicted rows (audit/review)

Source labels in body_system_labels_all.csv distinguish 2024 as using
slightly different category names (Injuries/Musculoskeletal, Psychiatric/Behavioral,
Sexual and Reproductive). These are kept as extracted for 2024; the classifier
uses the canonical 2022-2023 16-category vocabulary.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.pipeline import Pipeline
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.metrics import classification_report

# ── Paths ────────────────────────────────────────────────────────────────────
ITE_BASE   = Path(__file__).resolve().parents[1]
PIPE_BASE  = ITE_BASE.parent / "ite_pipeline/03_database"

SRC_ENRICHED = ITE_BASE / "03_database/ABFM_ITE_Enriched.xlsx"
SRC_LABELS   = PIPE_BASE / "body_system_labels_all.csv"
OUT_DIR      = ITE_BASE / "03_database"
RAW_DIR      = ITE_BASE / "03_database/raw_files"

RAW_DIR.mkdir(parents=True, exist_ok=True)

OUT_FULL = OUT_DIR / "body_system_full.csv"
OUT_GAPS = RAW_DIR / "body_system_predicted_only.csv"

# ── Load data ─────────────────────────────────────────────────────────────────
print("Loading enriched master database...")
df_master = pd.read_excel(SRC_ENRICHED)[["Question ID", "ExamYear", "QuestionStem", "Explanation"]]
df_master = df_master.rename(columns={"Question ID": "QuestionID"})
df_master["QuestionStem"]  = df_master["QuestionStem"].fillna("").astype(str)
df_master["Explanation"]   = df_master["Explanation"].fillna("").astype(str)
# Combine stem + explanation for richer text features
df_master["CombinedText"] = df_master["QuestionStem"] + " " + df_master["Explanation"]

print(f"  Master: {len(df_master)} questions across years {sorted(df_master['ExamYear'].unique())}")

print("\nLoading extracted body system labels...")
df_labels = pd.read_csv(SRC_LABELS)
print(f"  Labels: {len(df_labels)} rows  |  Years: {sorted(df_labels['Year'].unique())}")
print(f"  Categories: {df_labels['BodySystem'].nunique()}")

# ── Merge: attach labels via within-year position ────────────────────────────
# Master IDs use global sequential numbering (Q2022-401..Q2022-600) while
# label IDs use per-year numbering (Q2022-001..Q2022-200). Join on position.

# Add within-year rank (1-200) to master
df_master["WithinYearPos"] = df_master.groupby("ExamYear").cumcount() + 1

# Labels have QuestionNum (1-200) as the within-year position
df_labels_pos = df_labels.rename(columns={"Year": "LabelYear", "QuestionNum": "WithinYearPos"})

df_merged = df_master.merge(
    df_labels_pos[["LabelYear", "WithinYearPos", "BodySystem"]],
    left_on=["ExamYear", "WithinYearPos"],
    right_on=["LabelYear", "WithinYearPos"],
    how="left"
)

# "Extracted" = gold standard from PDF; "Predicted" = classifier output
df_merged["BodySystem_Source"] = df_merged["BodySystem"].apply(
    lambda x: "Extracted" if pd.notna(x) else "Predicted"
)

labeled   = df_merged[df_merged["BodySystem_Source"] == "Extracted"].copy()
unlabeled = df_merged[df_merged["BodySystem_Source"] == "Predicted"].copy()

print(f"\n  Labeled   (gold): {len(labeled)}")
print(f"  Unlabeled (need prediction): {len(unlabeled)}")
print(f"    2020: {(unlabeled['ExamYear']==2020).sum()}")
print(f"    2021: {(unlabeled['ExamYear']==2021).sum()}")
print(f"    2022: {(unlabeled['ExamYear']==2022).sum()}")
print(f"    2023: {(unlabeled['ExamYear']==2023).sum()}")
print(f"    2024: {(unlabeled['ExamYear']==2024).sum()}")

# ── Use ONLY 2022-2023 as training (canonical 16-category vocab) ───────────────
# 2024 labels use 5 slightly-different category names — exclude from training
train = labeled[labeled["LabelYear"].isin([2022, 2023])].copy()
print(f"\nTraining set: {len(train)} questions (2022-2023 only, canonical labels)")
print(f"  Label distribution:")
for cat, n in train["BodySystem"].value_counts().items():
    print(f"    {cat:35s}  {n}")

# ── Build classifier pipeline ─────────────────────────────────────────────────
pipeline = Pipeline([
    ("tfidf", TfidfVectorizer(
        ngram_range=(1, 2),
        min_df=1,
        max_features=8000,
        sublinear_tf=True,
        strip_accents="unicode",
        token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z0-9\-]{1,}\b",
    )),
    ("clf", LinearSVC(
        C=1.0,
        max_iter=2000,
        class_weight="balanced",
    )),
])

# ── Cross-validation (5-fold stratified) ──────────────────────────────────────
print("\nRunning 5-fold cross-validation on 2022-2023 training set...")
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
scores = cross_val_score(
    pipeline, train["CombinedText"], train["BodySystem"],
    cv=cv, scoring="accuracy"
)
print(f"  CV Accuracy: {scores.mean():.3f} ± {scores.std():.3f}")
print(f"  Fold scores: {[f'{s:.3f}' for s in scores]}")

# ── Fit final model on all 2022-2023 labeled data ────────────────────────────
print("\nFitting final model on full 2022-2023 training set...")
pipeline.fit(train["CombinedText"], train["BodySystem"])

# ── Predict unlabeled questions ───────────────────────────────────────────────
print(f"\nPredicting {len(unlabeled)} unlabeled questions...")
preds = pipeline.predict(unlabeled["CombinedText"])
unlabeled = unlabeled.copy()
unlabeled["BodySystem"] = preds
unlabeled["BodySystem_Source"] = "Predicted"

# ── Predict probabilities/confidence via decision function ────────────────────
decision = pipeline.decision_function(unlabeled["CombinedText"])
confidence = np.abs(decision).max(axis=1)  # max margin across classes
unlabeled["BodySystem_Confidence"] = np.round(confidence, 3)

# ── Stitch together: extracted gold + predictions ─────────────────────────────
labeled["BodySystem_Confidence"] = 1.000

df_full = pd.concat([labeled, unlabeled], ignore_index=True)
df_full = df_full.sort_values(["ExamYear", "QuestionID"]).reset_index(drop=True)

# Keep only useful columns
df_full = df_full[["QuestionID", "ExamYear", "BodySystem", "BodySystem_Source", "BodySystem_Confidence"]]

# ── Summary stats ─────────────────────────────────────────────────────────────
print("\n=== Final BodySystem Coverage ===")
for yr in sorted(df_full["ExamYear"].unique()):
    grp = df_full[df_full["ExamYear"] == yr]
    extracted = (grp["BodySystem_Source"] == "Extracted").sum()
    predicted = (grp["BodySystem_Source"] == "Predicted").sum()
    print(f"  {yr}: {extracted} extracted  +  {predicted} predicted  =  {len(grp)}/200")

print("\n  Label distribution (all 1200):")
for cat, n in df_full["BodySystem"].value_counts().items():
    print(f"    {cat:35s}  {n}")

print(f"\n  Median prediction confidence (predicted rows): "
      f"{unlabeled['BodySystem_Confidence'].median():.3f}")
print(f"  Low-confidence predictions (<0.5): "
      f"{(unlabeled['BodySystem_Confidence'] < 0.5).sum()}")

# ── Save outputs ──────────────────────────────────────────────────────────────
df_full.to_csv(OUT_FULL, index=False)
print(f"\n  Saved full coverage: {OUT_FULL.name}  ({len(df_full)} rows)")

df_gaps = df_full[df_full["BodySystem_Source"] == "Predicted"].copy()
df_gaps.to_csv(OUT_GAPS, index=False)
print(f"  Saved predicted-only: {OUT_GAPS.name}  ({len(df_gaps)} rows)")

print("\nDone.")
