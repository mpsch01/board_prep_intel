"""
check_aafp_body_system.py
==========================
Shows the current AAFP body_system distribution and method breakdown
before re-running the classifier.
"""
import sqlite3
from pathlib import Path

SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH      = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"

db = sqlite3.connect(str(DB_PATH))

print("AAFP body_system distribution:")
for r in db.execute(
    "SELECT body_system, COUNT(*) n FROM aafp_questions "
    "GROUP BY body_system ORDER BY n DESC"
):
    print(f"  {str(r[0]):<35} {r[1]}")

print()
print("AAFP body_system_method distribution:")
for r in db.execute(
    "SELECT body_system_method, COUNT(*) n FROM aafp_questions "
    "GROUP BY body_system_method ORDER BY n DESC"
):
    print(f"  {str(r[0]):<20} {r[1]}")

print()
print("Sample of each method (5 per tier):")
for method in ["propagated", "neighbor", "keyword_freq"]:
    rows = db.execute(
        "SELECT aafp_qid, body_system FROM aafp_questions "
        "WHERE body_system_method = ? LIMIT 5", (method,)
    ).fetchall()
    print(f"\n  [{method}]")
    for r in rows:
        print(f"    {r[0]}: {r[1]}")

db.close()
