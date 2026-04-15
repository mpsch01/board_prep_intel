"""
fix_taxonomy_names.py
=====================
Fixes remaining taxonomy naming artifacts in the questions table
that were missed by body_system_updates.sql due to the rename collision.

Safe to run — these are pure name standardizations, not clinical reclassifications.
"""
import sqlite3
from pathlib import Path

SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH      = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"

db = sqlite3.connect(str(DB_PATH))

# Musculoskeletal -> Injuries/Musculoskeletal (non-training years only)
# 2022/2023 keep ABFM-original name
r1 = db.execute(
    "UPDATE questions SET body_system = 'Injuries/Musculoskeletal' "
    "WHERE body_system = 'Musculoskeletal' AND exam_year NOT IN (2022, 2023)"
)
print(f"Musculoskeletal -> Injuries/Musculoskeletal: {r1.rowcount} rows")

# Hematologic/ Immune spacing fix (all years — this is a data artifact)
r2 = db.execute(
    "UPDATE questions SET body_system = 'Hematologic/Immune' "
    "WHERE body_system = 'Hematologic/ Immune'"
)
print(f"Hematologic/ Immune spacing fix: {r2.rowcount} rows")

db.commit()
db.close()
print("Done. Run verify_body_system_updates.py to confirm.")
