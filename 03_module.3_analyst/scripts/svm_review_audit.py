"""
svm_review_audit.py
====================
Runs the SVM classifier on the human_review subset from claude_classifications.json
and checks where SVM and Claude agree. Agreement = strong signal to upgrade to
sql_ready. Disagreement = genuine uncertainty, keep in human_review.

Logic:
  - SVM agrees with Claude's proposal → upgrade to sql_ready (dual-classifier consensus)
  - SVM disagrees              → keep human_review (or flag if SVM is very confident)
  - SVM has no embedding        → keep human_review unchanged

Writes upgraded_classifications.json with the same structure as claude_classifications.json
but with route and svm_* fields updated.

Usage:
    python svm_review_audit.py
    python svm_review_audit.py --show-disagreements   # print cases where SVM ≠ Claude
    python svm_review_audit.py --dry-run              # print summary without writing file
"""

import json
import sqlite3
import struct
import argparse
from pathlib import Path
from collections import Counter, defaultdict

import numpy as np
from sklearn.svm import LinearSVC
from sklearn.preprocessing import LabelEncoder
from sklearn.calibration import CalibratedClassifierCV

# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH      = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"
OUTPUT_DIR   = PROJECT_ROOT / "03_module.3_analyst" / "outputs" / "body_system_labels"

CLASSIFICATIONS_FILE = OUTPUT_DIR / "claude_classifications.json"
TRAINING_SET_FILE    = OUTPUT_DIR / "body_system_training_set.json"
OUTPUT_FILE          = OUTPUT_DIR / "upgraded_classifications.json"

# Agreement threshold: if SVM agrees with Claude AND SVM probability >= this → upgrade
SVM_AGREE_PROB_MIN = 0.40   # intentionally low — SVM agreement alone is strong signal


def open_db(db_path: Path):
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def deserialize(blob: bytes) -> np.ndarray | None:
    if not blob:
        return None
    try:
        return np.frombuffer(blob, dtype=np.float32).copy()
    except Exception:
        return None


def load_embeddings(db_path: Path, qids: list[str],
                    table: str = "question_full_vec",
                    qid_col: str = "qid") -> dict[str, np.ndarray]:
    conn = open_db(db_path)
    placeholders = ",".join("?" * len(qids))
    rows = conn.execute(
        f"SELECT {qid_col}, embedding FROM {table} WHERE {qid_col} IN ({placeholders})",
        qids
    ).fetchall()
    conn.close()
    return {row[0]: deserialize(row[1]) for row in rows if row[1]}


def train_svm(training_questions: list, training_embeddings: dict):
    """Train a calibrated LinearSVC on the full training set."""
    X, y = [], []
    for q in training_questions:
        qid = q["qid"]
        emb = training_embeddings.get(qid)
        if emb is None:
            continue
        X.append(emb)
        y.append(q["body_system"])

    X = np.array(X)
    le = LabelEncoder()
    y_enc = le.fit_transform(y)

    base = LinearSVC(class_weight="balanced", max_iter=2000, C=1.0)
    clf  = CalibratedClassifierCV(base, cv=3)
    clf.fit(X, y_enc)

    print(f"  SVM trained on {len(X)} examples, {len(le.classes_)} classes")
    return clf, le


def main():
    parser = argparse.ArgumentParser(description="Audit human_review cases with SVM")
    parser.add_argument("--bank", choices=["ite", "aafp"], default="ite",
                        help="Which question bank to audit (default: ite)")
    parser.add_argument("--show-disagreements", action="store_true",
                        help="Print cases where SVM and Claude disagree")
    parser.add_argument("--show-upgrades", action="store_true",
                        help="Print upgraded cases with Claude reasoning")
    parser.add_argument("--verbose", action="store_true",
                        help="With --show-upgrades: also show full question stem, choices, and correct answer from DB")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print summary without writing output file")
    parser.add_argument("--min-svm-prob", type=float, default=SVM_AGREE_PROB_MIN,
                        help=f"Min SVM probability to count as agreement (default: {SVM_AGREE_PROB_MIN})")
    args = parser.parse_args()

    # ── Bank-specific config ───────────────────────────────────────────────────
    if args.bank == "aafp":
        CLASSIFICATIONS_FILE = OUTPUT_DIR / "aafp_classifications.json"
        OUTPUT_FILE          = OUTPUT_DIR / "aafp_upgraded_classifications.json"
        EMBED_TABLE          = "aafp_question_full_vec"
        EMBED_QID_COL        = "aafp_qid"
    else:
        CLASSIFICATIONS_FILE = OUTPUT_DIR / "claude_classifications.json"
        OUTPUT_FILE          = OUTPUT_DIR / "upgraded_classifications.json"
        EMBED_TABLE          = "question_full_vec"
        EMBED_QID_COL        = "qid"

    # ── Load data ──────────────────────────────────────────────────────────────
    print("[1/5] Loading training set...")
    with open(TRAINING_SET_FILE, encoding="utf-8") as f:
        training_data = json.load(f)
    training_questions = training_data["questions"]
    print(f"      {len(training_questions)} training questions")

    print("[2/5] Loading training embeddings...")
    train_qids = [q["qid"] for q in training_questions]
    training_embeddings = load_embeddings(DB_PATH, train_qids)
    print(f"      {len(training_embeddings)} embeddings loaded")

    print("[3/5] Training SVM on full 2022+2023 training set...")
    clf, le = train_svm(training_questions, training_embeddings)

    print(f"[4/5] Loading Claude classifications ({args.bank})...")
    with open(CLASSIFICATIONS_FILE, encoding="utf-8") as f:
        classifications = json.load(f)
    all_results = classifications["results"]

    hr_cases = [r for r in all_results if r["route"] == "human_review"]
    sql_cases = [r for r in all_results if r["route"] == "sql_ready"]
    flag_cases = [r for r in all_results if r["route"] == "flagged"]
    print(f"      {len(all_results)} total | {len(hr_cases)} human_review | "
          f"{len(sql_cases)} sql_ready | {len(flag_cases)} flagged")

    # ── Load embeddings for human_review cases ─────────────────────────────────
    hr_qids = [r["qid"] for r in hr_cases]
    print(f"[5/5] Loading embeddings for {len(hr_qids)} human_review cases ({EMBED_TABLE})...")
    hr_embeddings = load_embeddings(DB_PATH, hr_qids, table=EMBED_TABLE, qid_col=EMBED_QID_COL)
    print(f"      {len(hr_embeddings)} embeddings found")

    # ── Run SVM on human_review cases ──────────────────────────────────────────
    upgraded   = 0
    kept       = 0
    no_embed   = 0
    agree_cats = Counter()
    disagree_cases = []

    updated_results = []

    for r in all_results:
        if r["route"] != "human_review":
            updated_results.append(r)
            continue

        qid      = r["qid"]
        proposed = r["body_system_proposed"]
        emb      = hr_embeddings.get(qid)

        if emb is None:
            r["svm_prediction"]   = None
            r["svm_probability"]  = None
            r["svm_agrees"]       = None
            updated_results.append(r)
            no_embed += 1
            continue

        # SVM predict
        X = emb.reshape(1, -1)
        proba     = clf.predict_proba(X)[0]
        pred_idx  = int(np.argmax(proba))
        # Translate old taxonomy names to post-2024 canonical before comparing
        _SVM_RENAMES = {
            "Psychiatric":     "Psychiatric/Behavioral",
            "Reproductive":    "Sexual and Reproductive",
            "Musculoskeletal": "Injuries/Musculoskeletal",
        }
        pred_cat  = _SVM_RENAMES.get(le.classes_[pred_idx], le.classes_[pred_idx])
        pred_prob = float(proba[pred_idx])

        # Also get the probability for Claude's proposed category
        if proposed in le.classes_:
            claude_cat_idx  = list(le.classes_).index(proposed)
            claude_cat_prob = float(proba[claude_cat_idx])
        else:
            claude_cat_prob = 0.0

        agrees = (pred_cat == proposed) and (pred_prob >= args.min_svm_prob)

        r["svm_prediction"]        = pred_cat
        r["svm_probability"]       = round(pred_prob, 4)
        r["svm_claude_cat_prob"]   = round(claude_cat_prob, 4)
        r["svm_agrees"]            = agrees

        if agrees:
            r["route"]      = "sql_ready"
            r["route_note"] = f"upgraded: svm+claude agree (svm_prob={pred_prob:.2f})"
            upgraded += 1
            agree_cats[proposed] += 1
        else:
            disagree_cases.append({
                "qid":       qid,
                "claude":    proposed,
                "svm":       pred_cat,
                "svm_prob":  round(pred_prob, 4),
                "conf":      r["confidence"],
            })
            kept += 1

        updated_results.append(r)

    # ── Summary ────────────────────────────────────────────────────────────────
    print()
    print("=" * 60)
    print("SVM AUDIT RESULTS")
    print("=" * 60)
    print(f"Human review cases:      {len(hr_cases)}")
    print(f"  No embedding (kept):   {no_embed}")
    print(f"  SVM agrees -> upgraded: {upgraded}  ({100*upgraded//len(hr_cases) if hr_cases else 0}%)")
    print(f"  SVM disagrees (kept):  {kept}")
    print()

    final_sql    = len(sql_cases) + upgraded
    final_hr     = kept + no_embed
    final_flag   = len(flag_cases)
    total        = len(all_results)

    print("Updated routing:")
    print(f"  sql_ready:    {final_sql:4d}  ({100*final_sql//total}%)")
    print(f"  human_review: {final_hr:4d}  ({100*final_hr//total}%)")
    print(f"  flagged:      {final_flag:4d}  ({100*final_flag//total}%)")

    print()
    print("Categories most commonly upgraded:")
    for cat, n in agree_cats.most_common(10):
        print(f"  {cat:<30} {n}")

    if args.show_disagreements or len(disagree_cases) <= 30:
        print()
        print(f"SVM ≠ Claude cases ({len(disagree_cases)}) — these stay in human_review:")
        print(f"  {'QID':<18} {'Claude':<25} {'SVM':<25} {'SVM prob':>8}  {'conf':>5}")
        print(f"  {'-'*18} {'-'*25} {'-'*25} {'-'*8}  {'-'*5}")
        for d in sorted(disagree_cases, key=lambda x: x["svm_prob"], reverse=True):
            print(f"  {d['qid']:<18} {d['claude']:<25} {d['svm']:<25} "
                  f"{d['svm_prob']:>8.2f}  {d['conf']:>5.2f}")

    if args.show_upgrades:
        upgraded_cases = [r for r in updated_results if r.get("route_note", "").startswith("upgraded")]

        # Optionally load question content from DB for verbose mode
        q_content = {}
        if args.verbose and DB_PATH.exists():
            upgrade_qids = [r["qid"] for r in upgraded_cases]
            conn = open_db(DB_PATH)
            placeholders = ",".join("?" * len(upgrade_qids))
            rows = conn.execute(
                f"SELECT qid, question_text, choices, correct_letter, correct_text "
                f"FROM questions WHERE qid IN ({placeholders})",
                upgrade_qids
            ).fetchall()
            conn.close()
            for row in rows:
                choices_raw = row["choices"] or "[]"
                try:
                    choices = json.loads(choices_raw) if isinstance(choices_raw, str) else choices_raw
                except Exception:
                    choices = []
                q_content[row["qid"]] = {
                    "question_text": row["question_text"] or "",
                    "choices":       choices,
                    "correct_letter": row["correct_letter"] or "",
                    "correct_text":  row["correct_text"] or "",
                }

        print()
        print(f"UPGRADED cases — SVM + Claude agree ({len(upgraded_cases)} total)")
        print("=" * 80)

        for r in upgraded_cases:
            qid      = r["qid"]
            cat      = r["body_system_proposed"]
            claude_c = r["confidence"]
            svm_p    = r.get("svm_probability", 0)
            db_was   = r.get("body_system_current_db", "?")
            changed  = " [CHANGES DB]" if db_was != cat else " [confirms DB]"

            print(f"\n{qid}  ->  {cat}{changed}")
            print(f"  Claude conf: {claude_c:.2f}   SVM prob: {svm_p:.2f}   DB was: {db_was}")

            if args.verbose and qid in q_content:
                q = q_content[qid]
                stem = (q["question_text"] or "")[:350]
                print(f"  Q: {stem}{'...' if len(q['question_text']) > 350 else ''}")
                for c in q["choices"][:5]:
                    letter = c.get("letter", "?")
                    text   = (c.get("text", "") or "")[:80]
                    marker = " <-- CORRECT" if letter == q["correct_letter"] else ""
                    print(f"     {letter}) {text}{marker}")

            print(f"  Reasoning: {r.get('reasoning', '')}")
            if r.get("alternative"):
                print(f"  Alternative considered: {r['alternative']}")
            print("-" * 60)

    if not args.dry_run:
        output = {
            **classifications,
            "generated":      classifications["generated"],
            "svm_audit_date": str(Path(__file__).stat().st_mtime),
            "bank":           args.bank,
            "routing_summary": {
                "sql_ready":    final_sql,
                "human_review": final_hr,
                "flagged":      final_flag,
            },
            "results": sorted(updated_results, key=lambda r: (r.get("exam_year", 0), r["qid"])),
        }
        OUTPUT_FILE.write_text(json.dumps(output, indent=2), encoding="utf-8")
        print(f"\nWritten: {OUTPUT_FILE}")
    else:
        print("\n[DRY RUN] No file written.")


if __name__ == "__main__":
    main()
