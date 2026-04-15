"""
verify_body_system_updates.py
==============================
Spot-checks that body_system UPDATE statements were applied correctly to the DB.
"""
import sqlite3
from pathlib import Path

SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH      = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"

db = sqlite3.connect(str(DB_PATH))

# 1. Psychogenic should be gone from non-training years
print("Psychogenic remaining (should be 0 for non-2022/2023 years):")
rows = db.execute(
    "SELECT exam_year, COUNT(*) n FROM questions "
    "WHERE body_system = 'Psychogenic' AND exam_year NOT IN (2022,2023) "
    "GROUP BY exam_year"
).fetchall()
if rows:
    for r in rows: print(f"  {r[0]}: {r[1]}  <-- still present!")
else:
    print("  None found. CLEAN.")

# 2. Psychiatric/Behavioral by year
print()
print("Psychiatric/Behavioral by year:")
for r in db.execute(
    "SELECT exam_year, COUNT(*) n FROM questions "
    "WHERE body_system = 'Psychiatric/Behavioral' "
    "GROUP BY exam_year ORDER BY exam_year"
):
    print(f"  {r[0]}: {r[1]}")

# 3. Sexual and Reproductive by year
print()
print("Sexual and Reproductive by year:")
for r in db.execute(
    "SELECT exam_year, COUNT(*) n FROM questions "
    "WHERE body_system = 'Sexual and Reproductive' "
    "GROUP BY exam_year ORDER BY exam_year"
):
    print(f"  {r[0]}: {r[1]}")

# 4. Spot-check specific QIDs
print()
print("Spot checks:")
spot_qids = ["QID-2018-0018", "QID-2018-0030", "QID-2025-0180", "QID-2025-0195"]
for qid in spot_qids:
    r = db.execute(
        "SELECT qid, body_system FROM questions WHERE qid = ?", (qid,)
    ).fetchone()
    if r:
        print(f"  {r[0]}: {r[1]}")

# 5. Full body_system distribution for non-training years
print()
print("Full distribution (2018-2021, 2024-2025):")
for r in db.execute(
    "SELECT body_system, COUNT(*) n FROM questions "
    "WHERE exam_year NOT IN (2022,2023) "
    "GROUP BY body_system ORDER BY n DESC"
):
    print(f"  {r[0]:<35} {r[1]}")

# 6. Sanity check — any old synthesized taxonomy names still present?
print()
print("Old taxonomy names still in DB (non-training years):")
old_names = [
    "Psychogenic", "Reproductive: Female", "Reproductive: Male",
    "Reproductive:Female", "Reproductive:Male",
    "Pulmonary/Critical Care", "Dermatologic",
    "Eyes, Ears, Nose & Throat", "Nephrologic/Urologic",
    "Population-Based/Preventive", "Maternity Care",
    "Nonspecific/Other", "Reproductive (Female)", "Reproductive (Male)",
    "Psychiatric", "Reproductive", "Musculoskeletal",
    "Hematologic/ Immune",
]
found_any = False
for name in old_names:
    rows = db.execute(
        "SELECT COUNT(*) n FROM questions "
        "WHERE body_system = ? AND exam_year NOT IN (2022,2023)",
        (name,)
    ).fetchone()
    if rows and rows[0] > 0:
        print(f"  '{name}': {rows[0]} remaining")
        found_any = True
if not found_any:
    print("  None found. All clean.")

db.close()
