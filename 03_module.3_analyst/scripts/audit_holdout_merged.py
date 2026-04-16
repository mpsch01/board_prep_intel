"""
audit_holdout_merged.py
Check body_system_merged for the 22 deprecated-label holdouts in 2024-2025.
Reveals whether the label merger already mapped them or left them as-is.
"""
import sqlite3
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"

DEPRECATED = ['Patient-Based Systems', 'Psychogenic', 'Reproductive: Female', 'Reproductive: Male']

db = sqlite3.connect(DB_PATH)

placeholders = ','.join('?' for _ in DEPRECATED)
rows = db.execute(f'''
    SELECT qid, exam_year, body_system, body_system_merged
    FROM questions
    WHERE exam_year >= 2024
    AND body_system IN ({placeholders})
    ORDER BY exam_year, body_system, qid
''', DEPRECATED).fetchall()

print(f"=== body_system vs body_system_merged for 2024-2025 holdouts ({len(rows)} records) ===\n")
print(f"{'QID':<20} {'Year':<6} {'body_system':<30} {'body_system_merged'}")
print("-" * 100)
for r in rows:
    qid, year, bs, bsm = r
    match = "✓" if bs != bsm else "SAME"
    print(f"{qid:<20} {year:<6} {str(bs):<30} {str(bsm)}  [{match}]")

print()
# Summary
same = sum(1 for r in rows if r[2] == r[3])
different = len(rows) - same
print(f"body_system == body_system_merged: {same} records (merger did NOT remap)")
print(f"body_system != body_system_merged: {different} records (merger DID remap)")

db.close()
