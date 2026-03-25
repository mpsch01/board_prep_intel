#!/usr/bin/env python3
"""
ite_merge_csv.py

Generic CLI utility — merges two question bank CSVs by id.
Incoming wins on conflict by default (--priority master to reverse).

Usage:
    python ite_merge_csv.py --master old.csv --incoming new.csv --out merged.csv
    python ite_merge_csv.py --master old.csv --incoming new.csv --out merged.csv --priority master

Migrated from TEMP_06_ite_pipeline_TEMP (BATON 007)
"""

import argparse
import pandas as pd
from pathlib import Path

SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--master",   required=True)
    ap.add_argument("--incoming", required=True)
    ap.add_argument("--out",      required=True)
    ap.add_argument("--priority", choices=["master", "incoming"], default="incoming",
                    help="Which dataset wins on id conflict (default: incoming)")
    a = ap.parse_args()

    master   = pd.read_csv(a.master,   dtype=str)
    incoming = pd.read_csv(a.incoming, dtype=str)

    cols = ["id", "year", "stem", "A", "B", "C", "D", "E", "F",
            "correct", "explanation", "tags", "confidence"]
    for df in (master, incoming):
        for c in cols:
            if c not in df.columns:
                df[c] = ""
        df[cols] = df[cols]

    by_id = {}
    for _, r in master.iterrows():
        by_id[str(r["id"])] = r.to_dict()
    for _, r in incoming.iterrows():
        rid = str(r["id"])
        if rid in by_id:
            if a.priority == "incoming":
                by_id[rid] = r.to_dict()
        else:
            by_id[rid] = r.to_dict()

    merged = pd.DataFrame(by_id.values())
    try:
        merged["id_num"] = merged["id"].astype(int)
        merged = merged.sort_values("id_num").drop(columns=["id_num"])
    except Exception:
        merged = merged.sort_values("id")

    merged.to_csv(a.out, index=False, encoding="utf-8")
    print(f"Merged -> {a.out} ({merged.shape[0]} rows)")


if __name__ == "__main__":
    main()
