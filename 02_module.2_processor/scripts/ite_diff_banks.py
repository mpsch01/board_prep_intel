#!/usr/bin/env python3
"""
ite_diff_banks.py

Diffs two ITE question bank CSVs by id.
Flags: MISSING_IN_LEFT, MISSING_IN_RIGHT, STEM_DRIFT, ANSWER_MISMATCH.

Usage:
    python ite_diff_banks.py --left old.csv --right new.csv --out diff.csv

Migrated from TEMP_06_ite_pipeline_TEMP (BATON 007)
"""

import argparse
import pandas as pd
from difflib import SequenceMatcher
from pathlib import Path

SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent


def sim(a, b):
    a = "" if pd.isna(a) else str(a)
    b = "" if pd.isna(b) else str(b)
    if not a and not b:
        return 1.0
    return SequenceMatcher(None, a[:400], b[:400]).ratio()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--left",  required=True)
    ap.add_argument("--right", required=True)
    ap.add_argument("--out",   required=True)
    a = ap.parse_args()

    left  = pd.read_csv(a.left,  dtype=str)
    right = pd.read_csv(a.right, dtype=str)

    m    = left.merge(right, on="id", how="outer", suffixes=("_left", "_right"))
    rows = []
    for _, r in m.iterrows():
        rid    = r["id"]
        status = []
        if pd.isna(r.get("stem_left")):  status.append("MISSING_IN_LEFT")
        if pd.isna(r.get("stem_right")): status.append("MISSING_IN_RIGHT")

        stem_sim = sim(r.get("stem_left", ""), r.get("stem_right", ""))
        if (pd.notna(r.get("stem_left")) and pd.notna(r.get("stem_right")) and stem_sim < 0.6):
            status.append("STEM_DRIFT")

        ans_l = r.get("correct_left", "")
        ans_r = r.get("correct_right", "")
        if (pd.notna(ans_l) and pd.notna(ans_r) and str(ans_l) != str(ans_r)):
            status.append("ANSWER_MISMATCH")

        rows.append({
            "id":                    rid,
            "status":                "|".join(status) if status else "OK",
            "stem_similarity_0to1":  round(stem_sim, 3),
            "left_correct":          ans_l,
            "right_correct":         ans_r,
            "left_stem_preview":     str(r.get("stem_left",  ""))[:160],
            "right_stem_preview":    str(r.get("stem_right", ""))[:160],
        })

    out = pd.DataFrame(rows).sort_values(["status", "id"])
    out.to_csv(a.out, index=False, encoding="utf-8")
    print(f"Wrote diff -> {a.out} ({out.shape[0]} rows)")
    ok_count  = (out["status"] == "OK").sum()
    bad_count = out.shape[0] - ok_count
    print(f"  OK: {ok_count} | Issues: {bad_count}")


if __name__ == "__main__":
    main()
