#!/usr/bin/env python3
import argparse, pandas as pd
from tagger_rules import tag_stem

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in_csv", required=True)
    ap.add_argument("--out_csv", required=True)
    a = ap.parse_args()

    df = pd.read_csv(a.in_csv, dtype=str)
    if "tags" not in df.columns: df["tags"] = ""
    if "confidence" not in df.columns: df["confidence"] = ""
    for i, row in df.iterrows():
        t, c = tag_stem(str(row.get("stem","")))
        if t: df.at[i, "tags"] = t
        if c: df.at[i, "confidence"] = c
    df.to_csv(a.out_csv, index=False, encoding="utf-8")
    print(f"Tagged -> {a.out_csv}")

if __name__ == "__main__":
    main()
