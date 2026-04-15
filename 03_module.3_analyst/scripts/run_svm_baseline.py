"""
run_svm_baseline.py — SVM Body System Classification Baseline (Pass 1)

===============================================================================
OVERVIEW
===============================================================================
Trains a linear SVM classifier on 2022 labeled ITE questions and validates on
2023 using pre-computed question embeddings from the database. This is a fast
diagnostic baseline to evaluate whether embeddings + SVM alone can distinguish
body systems without Claude CoT enrichment.

Strategy: Year-over-year split (2022 train → 2023 test) provides real
generalization evaluation. Balanced class weights handle label imbalance
(Respiratory n=77, Neurologic n=1).

===============================================================================
INPUTS
===============================================================================
1. body_system_training_set.json
   Location: 03_module.3_analyst/outputs/body_system_labels/
   Structure:
     {
       "years": [2022, 2023],
       "questions": [
         {"qid": "QID-2022-0001", "exam_year": 2022,
          "body_system": "Respiratory", "question_text": "...", ...},
         ...
       ]
     }

2. ite_intelligence.db (question_full_vec table)
   Columns: qid TEXT, embedding BLOB
   Embedding format: raw bytes (float32 little-endian), deserialize with:
     np.frombuffer(blob, dtype=np.float32)

===============================================================================
OUTPUTS
===============================================================================
svm_baseline_results.json
  Location: 03_module.3_analyst/outputs/body_system_labels/
  Structure:
    {
      "model": "LinearSVC (C=1.0, class_weight=balanced)",
      "overall_accuracy": 0.XXX,
      "train_examples": 190,
      "test_examples": 203,
      "train_counts": {category: n, ...},
      "test_counts": {category: n, ...},
      "per_class_report": {
        category: {
          "precision": X,
          "recall": X,
          "f1_score": X,
          "support": n
        },
        ...
      },
      "confusion_pairs": [
        {"predicted": "A", "actual": "B", "count": n},
        ...
      ],
      "thin_classes": [
        {"category": "Neurologic", "test_count": 1, "recall": X},
        ...
      ]
    }

Plus human-readable table printed to stdout.

===============================================================================
USAGE
===============================================================================
Run from scripts/ directory:
  python run_svm_baseline.py

Optional arguments:
  --input-json PATH       Path to training set JSON (default: auto-locate)
  --output-dir PATH       Output directory (default: outputs/body_system_labels/)
  --verbose               Print debug info (embedding counts, missing QIDs)

Example:
  python run_svm_baseline.py --verbose
  python run_svm_baseline.py --input-json ../outputs/body_system_labels/body_system_training_set.json

===============================================================================
DESIGN NOTES
===============================================================================
- class_weight='balanced': Critical for imbalanced classes (Respiratory has
  77 samples, Neurologic has 1). SVM weights inversely to class frequency.
  
- probability=True: Enables probability estimates (for future confidence-based
  downstream filtering).
  
- Strategy 0 (codon parse) analog: This uses existing embeddings directly,
  analogous to the codon regex parse — fast, deterministic, no API calls.

- Confusion matrix reporting: Only shows pairs with >0 confusions (avoids
  verbose output for well-separated classes).

- Thin class flagging: Classes with <75% recall are flagged for manual review
  (likely need more training examples or better features).

===============================================================================
"""

import json
import sqlite3
import argparse
import numpy as np
from pathlib import Path
from collections import Counter, defaultdict
from sklearn.svm import LinearSVC
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    accuracy_score,
)


# ── Paths ──────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"
OUTPUT_DIR = PROJECT_ROOT / "03_module.3_analyst" / "outputs" / "body_system_labels"
DEFAULT_INPUT = OUTPUT_DIR / "body_system_training_set.json"


# ── Utility Functions ──────────────────────────────────────────────────────

def load_training_set(json_path):
    """Load body_system_training_set.json and return questions indexed by year."""
    with open(json_path) as f:
        data = json.load(f)
    
    questions = data.get("questions", [])
    
    # Split by exam_year
    by_year = defaultdict(list)
    for q in questions:
        year = q["exam_year"]
        by_year[year].append(q)
    
    return by_year


def load_embeddings_from_db(qids, db_path, verbose=False):
    """
    Load embeddings from question_full_vec table.
    
    Args:
        qids: List of question IDs to load
        db_path: Path to ite_intelligence.db
        verbose: Print counts of found/missing
    
    Returns:
        {qid: np.array(float32), ...} dict
        Embeddings are deserialized from BLOB (float32 little-endian).
    """
    embeddings = {}
    missing = []
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    for qid in qids:
        cursor.execute(
            "SELECT embedding FROM question_full_vec WHERE qid = ?",
            (qid,)
        )
        row = cursor.fetchone()
        
        if row and row[0]:
            blob = row[0]
            # Deserialize: raw bytes → float32 numpy array
            embedding = np.frombuffer(blob, dtype=np.float32)
            embeddings[qid] = embedding
        else:
            missing.append(qid)
    
    conn.close()
    
    if verbose:
        print(f"[INFO] Loaded embeddings for {len(embeddings)} / {len(qids)} QIDs")
        if missing:
            print(f"[WARN] Missing embeddings for {len(missing)} QIDs:")
            for qid in missing[:10]:
                print(f"       {qid}")
            if len(missing) > 10:
                print(f"       ... and {len(missing) - 10} more")
    
    return embeddings


def build_svm_dataset(questions, embeddings, verbose=False):
    """
    Build feature matrix (X) and label vector (y) from questions and embeddings.
    
    Returns:
        (X, y, labels, qids, missing_count)
        X: (n_samples, embedding_dim) float32 array
        y: (n_samples,) array of label indices
        labels: list of unique body_system strings (defines label order)
        qids: list of QIDs corresponding to X rows
        missing_count: number of questions with no embedding
    """
    X_list = []
    y_list = []
    qids_list = []
    missing_count = 0
    
    # Get unique labels and build label → index mapping
    all_labels = set(q["body_system"] for q in questions)
    labels = sorted(list(all_labels))
    label_to_idx = {label: i for i, label in enumerate(labels)}
    
    for q in questions:
        qid = q["qid"]
        body_system = q["body_system"]
        
        if qid not in embeddings:
            missing_count += 1
            continue
        
        embedding = embeddings[qid]
        X_list.append(embedding)
        y_list.append(label_to_idx[body_system])
        qids_list.append(qid)
    
    X = np.array(X_list, dtype=np.float32)
    y = np.array(y_list)
    
    if verbose:
        print(f"[INFO] Built dataset: {len(qids_list)} samples, "
              f"{X.shape[1]} embedding dims")
        if missing_count:
            print(f"[WARN] {missing_count} questions skipped (no embedding)")
    
    return X, y, labels, qids_list, missing_count


# ── Main Pipeline ──────────────────────────────────────────────────────────

def run_svm_baseline(
    input_json,
    db_path,
    output_dir,
    verbose=False
):
    """
    Full pipeline: load → split → train → evaluate → save results.
    """
    print("\n" + "="*80)
    print("SVM BODY SYSTEM BASELINE — Pass 1")
    print("="*80)
    
    # ──────────────────────────────────────────────────────────────────────
    # PHASE 1: Load training set
    # ──────────────────────────────────────────────────────────────────────
    print("\n[PHASE 1] Loading training set...")
    by_year = load_training_set(input_json)
    
    train_qs = by_year.get(2022, [])
    test_qs = by_year.get(2023, [])
    
    print(f"  2022 (train): {len(train_qs)} questions")
    print(f"  2023 (test):  {len(test_qs)} questions")
    
    # ──────────────────────────────────────────────────────────────────────
    # PHASE 2: Load embeddings
    # ──────────────────────────────────────────────────────────────────────
    print("\n[PHASE 2] Loading embeddings from database...")
    all_qids = [q["qid"] for q in train_qs + test_qs]
    embeddings = load_embeddings_from_db(all_qids, db_path, verbose=verbose)
    
    # ──────────────────────────────────────────────────────────────────────
    # PHASE 3: Build datasets
    # ──────────────────────────────────────────────────────────────────────
    print("\n[PHASE 3] Building training and test datasets...")
    
    X_train, y_train, train_labels, train_qids, train_missing = build_svm_dataset(
        train_qs, embeddings, verbose=verbose
    )
    X_test, y_test, test_labels, test_qids, test_missing = build_svm_dataset(
        test_qs, embeddings, verbose=verbose
    )
    
    # Align labels: use union of train + test labels, sorted
    all_labels = sorted(set(train_labels + test_labels))
    
    # Remap train and test labels to the combined label set
    train_label_map = {old_label: all_labels.index(old_label) for old_label in train_labels}
    test_label_map = {old_label: all_labels.index(old_label) for old_label in test_labels}
    
    y_train = np.array([train_label_map[train_labels[idx]] for idx in y_train])
    y_test = np.array([test_label_map[test_labels[idx]] for idx in y_test])
    
    print(f"  Train: {X_train.shape[0]} samples, {X_train.shape[1]} dims")
    print(f"  Test:  {X_test.shape[0]} samples, {X_test.shape[1]} dims")
    print(f"  Classes: {len(all_labels)} body systems")
    
    # ──────────────────────────────────────────────────────────────────────
    # PHASE 4: Train SVM
    # ──────────────────────────────────────────────────────────────────────
    print("\n[PHASE 4] Training LinearSVC with balanced class weights...")
    
    svm = LinearSVC(
        C=1.0,
        loss="squared_hinge",
        class_weight="balanced",
        max_iter=10000,
        random_state=42
    )
    svm.fit(X_train, y_train)
    print(f"  Model trained on {len(set(y_train))} classes")
    
    # ──────────────────────────────────────────────────────────────────────
    # PHASE 5: Evaluate on test set
    # ──────────────────────────────────────────────────────────────────────
    print("\n[PHASE 5] Evaluating on test set (2023 data)...")
    
    y_pred = svm.predict(X_test)
    overall_accuracy = accuracy_score(y_test, y_pred)
    print(f"  Overall Accuracy: {overall_accuracy:.3f}")
    
    # Per-class metrics
    class_report = classification_report(
        y_test,
        y_pred,
        target_names=all_labels,
        output_dict=True,
        zero_division=0
    )
    
    # Confusion matrix
    cm = confusion_matrix(y_test, y_pred, labels=range(len(all_labels)))
    
    # ──────────────────────────────────────────────────────────────────────
    # PHASE 6: Analyze results
    # ──────────────────────────────────────────────────────────────────────
    print("\n[PHASE 6] Analyzing confusion matrix and flagging thin classes...")
    
    # Build confusion pairs (actual → predicted with count > 0)
    confusion_pairs = []
    for true_idx in range(len(all_labels)):
        for pred_idx in range(len(all_labels)):
            if true_idx != pred_idx and cm[true_idx, pred_idx] > 0:
                confusion_pairs.append({
                    "actual": all_labels[true_idx],
                    "predicted": all_labels[pred_idx],
                    "count": int(cm[true_idx, pred_idx])
                })
    
    # Sort by count descending
    confusion_pairs.sort(key=lambda x: x["count"], reverse=True)
    
    # Flag thin classes (recall < 0.75)
    thin_classes = []
    for label in all_labels:
        recall = class_report[label]["recall"]
        support = int(class_report[label]["support"])
        if recall < 0.75 and support > 0:
            thin_classes.append({
                "category": label,
                "test_count": support,
                "recall": round(recall, 3)
            })
    
    thin_classes.sort(key=lambda x: x["recall"])
    
    # ──────────────────────────────────────────────────────────────────────
    # PHASE 7: Prepare output
    # ──────────────────────────────────────────────────────────────────────
    print("\n[PHASE 7] Preparing output JSON...")
    
    # Count class distribution
    train_counts = Counter(y_train)
    train_counts_dict = {
        all_labels[idx]: int(count)
        for idx, count in train_counts.items()
    }
    
    test_counts = Counter(y_test)
    test_counts_dict = {
        all_labels[idx]: int(count)
        for idx, count in test_counts.items()
    }
    
    # Clean class report (remove macro/weighted averages)
    per_class_report = {}
    for label in all_labels:
        if label in class_report:
            metrics = class_report[label]
            per_class_report[label] = {
                "precision": round(metrics["precision"], 3),
                "recall": round(metrics["recall"], 3),
                "f1_score": round(metrics["f1-score"], 3),
                "support": int(metrics["support"])
            }
    
    results = {
        "model": "LinearSVC (C=1.0, loss=squared_hinge, class_weight=balanced)",
        "overall_accuracy": round(overall_accuracy, 3),
        "train_examples": int(len(y_train)),
        "test_examples": int(len(y_test)),
        "embedding_dim": int(X_train.shape[1]),
        "classes": int(len(all_labels)),
        "train_counts": train_counts_dict,
        "test_counts": test_counts_dict,
        "per_class_report": per_class_report,
        "confusion_pairs": confusion_pairs[:20],  # Top 20 confusions
        "thin_classes": thin_classes
    }
    
    # ──────────────────────────────────────────────────────────────────────
    # PHASE 8: Save and print results
    # ──────────────────────────────────────────────────────────────────────
    print("\n[PHASE 8] Writing results to disk...")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    output_json = output_dir / "svm_baseline_results.json"
    
    with open(output_json, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"  ✓ Saved: {output_json}")
    
    # ──────────────────────────────────────────────────────────────────────
    # PHASE 9: Print human-readable summary
    # ──────────────────────────────────────────────────────────────────────
    print("\n" + "="*80)
    print("RESULTS SUMMARY")
    print("="*80)
    print(f"\nOverall Accuracy: {overall_accuracy:.1%}")
    print(f"Training set:     {len(y_train)} samples (2022)")
    print(f"Test set:         {len(y_test)} samples (2023)")
    
    # Class table
    print("\n" + "-"*80)
    print("PER-CLASS PERFORMANCE")
    print("-"*80)
    print(f"{'Body System':<25} {'Train':<8} {'Test':<8} {'Precision':<12} {'Recall':<12} {'F1':<8}")
    print("-"*80)
    
    for label in sorted(all_labels):
        train_n = train_counts_dict.get(label, 0)
        test_n = test_counts_dict.get(label, 0)
        metrics = per_class_report.get(label, {})
        precision = metrics.get("precision", 0)
        recall = metrics.get("recall", 0)
        f1 = metrics.get("f1_score", 0)
        
        # Flag if thin
        flag = " ⚠" if recall < 0.75 and test_n > 0 else ""
        
        print(f"{label:<25} {train_n:<8} {test_n:<8} "
              f"{precision:<12.3f} {recall:<12.3f} {f1:<8.3f}{flag}")
    
    print("-"*80)
    
    # Confusion pairs
    if confusion_pairs:
        print("\n" + "-"*80)
        print("TOP CONFUSION PAIRS (actual → predicted)")
        print("-"*80)
        for pair in confusion_pairs[:10]:
            print(f"  {pair['actual']:<20} → {pair['predicted']:<20} ({pair['count']} cases)")
    
    # Thin classes summary
    if thin_classes:
        print("\n" + "-"*80)
        print("⚠ CLASSES WITH RECALL < 75% (recommend manual review or more data)")
        print("-"*80)
        for tc in thin_classes:
            print(f"  {tc['category']:<20} recall={tc['recall']:.1%}  (n={tc['test_count']})")
    
    print("\n" + "="*80 + "\n")
    
    return results


# ── CLI ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="SVM Baseline for Body System Classification (Pass 1)"
    )
    parser.add_argument(
        "--input-json",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Path to body_system_training_set.json (default: {DEFAULT_INPUT})"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help=f"Output directory for results JSON (default: {OUTPUT_DIR})"
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=DB_PATH,
        help=f"Path to ite_intelligence.db (default: {DB_PATH})"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print debug info (embedding counts, missing QIDs)"
    )
    
    args = parser.parse_args()
    
    # Validate inputs
    if not args.input_json.exists():
        print(f"ERROR: Training set not found: {args.input_json}")
        print(f"       Run build_training_set.py first to generate it.")
        return 1
    
    if not args.db_path.exists():
        print(f"ERROR: Database not found: {args.db_path}")
        return 1
    
    # Run
    try:
        results = run_svm_baseline(
            input_json=args.input_json,
            db_path=args.db_path,
            output_dir=args.output_dir,
            verbose=args.verbose
        )
        return 0
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
