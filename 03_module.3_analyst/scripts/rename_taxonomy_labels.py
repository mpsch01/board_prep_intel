"""
rename_taxonomy_labels.py
==========================
Post-process rename of category labels in classification output JSONs.
Updates our custom condensed names to the official post-2024 ABFM canonical names.

Custom name       -> Post-2024 ABFM canonical
-------------------------------------------------
Psychiatric       -> Psychiatric/Behavioral
Reproductive      -> Sexual and Reproductive
Musculoskeletal   -> Injuries/Musculoskeletal

Run this ONCE after the batch results are retrieved, before generating SQL.
"""

import json
from pathlib import Path

SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
OUTPUT_DIR   = PROJECT_ROOT / "03_module.3_analyst" / "outputs" / "body_system_labels"

RENAMES = {
    "Psychiatric":     "Psychiatric/Behavioral",
    "Reproductive":    "Sexual and Reproductive",
    "Musculoskeletal": "Injuries/Musculoskeletal",
}

FILES = [
    "claude_classifications.json",
    "upgraded_classifications.json",
]

FIELDS = ["body_system_proposed", "body_system_current_db", "alternative", "svm_prediction"]


def rename_file(path: Path) -> int:
    if not path.exists():
        print(f"  SKIP (not found): {path.name}")
        return 0
    data = json.loads(path.read_text(encoding="utf-8"))
    changed = 0
    for r in data.get("results", []):
        for field in FIELDS:
            old = r.get(field)
            if old in RENAMES:
                r[field] = RENAMES[old]
                changed += 1
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return changed


if __name__ == "__main__":
    print("Renaming taxonomy labels to post-2024 ABFM canonical names...")
    for fname in FILES:
        n = rename_file(OUTPUT_DIR / fname)
        print(f"  {fname}: {n} values renamed")
    print("Done.")
