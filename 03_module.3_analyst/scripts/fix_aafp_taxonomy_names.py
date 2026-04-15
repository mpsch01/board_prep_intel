"""
fix_aafp_taxonomy_names.py
===========================
Phase 1: Fixes taxonomy naming artifacts in aafp_questions.body_system.
Standardizes to post-2024 ABFM canonical names — same as ITE corrections.
Safe to apply — pure naming standardization, no clinical reclassification.
"""
import sqlite3
from pathlib import Path

SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH      = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"

db = sqlite3.connect(str(DB_PATH))

fixes = [
    ("Musculoskeletal",    "Injuries/Musculoskeletal"),
    ("Reproductive: Female", "Sexual and Reproductive"),
    ("Reproductive: Male",   "Sexual and Reproductive"),
    ("Reproductive:Female",  "Sexual and Reproductive"),
    ("Reproductive:Male",    "Sexual and Reproductive"),
    ("Hematologic/ Immune",  "Hematologic/Immune"),
    ("Psychogenic",          "Psychiatric/Behavioral"),
]

total = 0
for old, new in fixes:
    r = db.execute(
        "UPDATE aafp_questions SET body_system = ? WHERE body_system = ?",
        (new, old)
    )
    if r.rowcount > 0:
        print(f"  {old:<30} -> {new}  ({r.rowcount} rows)")
        total += r.rowcount

db.commit()
db.close()
print(f"\nTotal: {total} rows updated")
print("Run check_aafp_body_system.py to verify.")
