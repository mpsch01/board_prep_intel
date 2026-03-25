"""
rebuild_acquisition_list.py
===========================
Rebuilds confirmed_present.csv and Core_Acquisition_List_Ranked.xlsx
from match_summary.csv produced by match_tiers_to_library.py.

Run after match_tiers_to_library.py completes.
Outputs land in archive_canonical/05_acquisition/ (canonical acquisition location).
"""
import sys, os
from pathlib import Path
import pandas as pd
sys.stdout.reconfigure(encoding="utf-8")

# ── PATHS ───────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent

OUT_DIR   = PROJECT_ROOT / "archive_canonical" / "05_acquisition"
TIERS_CSV = PROJECT_ROOT / "archive_canonical" / "04_reference_data" / "ABFM_ITE_ReferenceTiers_Expanded_v1369.csv"

summary  = pd.read_csv(OUT_DIR / "match_summary.csv")
tiers_df = pd.read_csv(TIERS_CSV)

# ── 1. confirmed_present.csv ─────────────────────────────────────────────────
matched = summary[summary["status"] == "MATCHED"].copy()
matched_merged = matched.merge(
    tiers_df[["CleanRef", "CitationCount", "UniqueYears", "BlueprintCategories"]].drop_duplicates("CleanRef"),
    left_on="clean_ref", right_on="CleanRef", how="left"
)
conf_cols = ["tier","source_type","confidence","matched_file","matched_folder",
             "citation_count","first_author","year","clean_ref","matched_path"]
matched_merged[conf_cols].sort_values(
    ["tier","confidence"], ascending=[True,False]
).to_csv(OUT_DIR / "confirmed_present.csv", index=False)
print(f"confirmed_present.csv: {len(matched)} rows")

# ── 2. Core_Acquisition_List_Ranked.xlsx ─────────────────────────────────────
# Not-found Core + Must-Read refs, ranked by citation count
not_found = summary[summary["status"] == "NOT_FOUND"].copy()
nf_merged = not_found.merge(
    tiers_df[["CleanRef","CitationCount","UniqueYears","BlueprintCategories","AutoAssigned"]].drop_duplicates("CleanRef"),
    left_on="clean_ref", right_on="CleanRef", how="left"
)
nf_merged["AutoAssigned"] = nf_merged["AutoAssigned"].fillna(False)
nf_merged["CitationCount"] = nf_merged["CitationCount"].fillna(nf_merged["citation_count"])
nf_merged = nf_merged.sort_values(
    ["tier","CitationCount"], ascending=[True,False]
).reset_index(drop=True)

# Priority tiers
def priority_tier(row):
    if row["tier"] == "Must-Read": return "MUST-READ"
    c = int(row.get("CitationCount", 0) or 0)
    if c >= 4: return "HIGH"
    if c >= 2: return "MEDIUM"
    if c >= 1: return "LOW"
    return "UNCONFIRMED"

nf_merged["PriorityTier"] = nf_merged.apply(priority_tier, axis=1)

acq_cols = ["PriorityTier","tier","source_type","CitationCount","UniqueYears",
            "first_author","year","clean_ref","BlueprintCategories","AutoAssigned"]
acq_df = nf_merged[acq_cols].rename(columns={
    "tier": "Tier", "source_type": "SourceType", "first_author": "FirstAuthor",
    "year": "Year", "clean_ref": "CleanRef"
})

# Write to xlsx with two sheets
acq_path = OUT_DIR / "ABFM_ITE_ReferenceAcquisitionList_Core_Ranked.xlsx"
with pd.ExcelWriter(acq_path, engine="openpyxl") as writer:
    acq_df.to_excel(writer, sheet_name="Ranked_List", index=False)

    summary_rows = []
    for pt in ["MUST-READ","HIGH","MEDIUM","LOW","UNCONFIRMED"]:
        grp = acq_df[acq_df["PriorityTier"] == pt]
        summary_rows.append({
            "PriorityTier": pt,
            "Count": len(grp),
            "AFP": len(grp[grp["SourceType"]=="AFP"]),
            "USPSTF": len(grp[grp["SourceType"]=="USPSTF"]),
            "Guideline_Org": len(grp[grp["SourceType"].isin(["Guideline","Guideline/Org"])]),
            "NEJM": len(grp[grp["SourceType"]=="NEJM"]),
            "JAMA": len(grp[grp["SourceType"]=="JAMA"]),
            "Other": len(grp[~grp["SourceType"].isin(["AFP","USPSTF","Guideline","Guideline/Org","NEJM","JAMA"])]),
        })
    pd.DataFrame(summary_rows).to_excel(writer, sheet_name="Summary", index=False)

print(f"ABFM_ITE_ReferenceAcquisitionList_Core_Ranked.xlsx: {len(acq_df)} rows")

pt_counts = acq_df["PriorityTier"].value_counts()
for pt in ["MUST-READ","HIGH","MEDIUM","LOW","UNCONFIRMED"]:
    print(f"  {pt}: {pt_counts.get(pt, 0)}")

print(f"\nOutputs written to: {OUT_DIR}")
print("Done.")
