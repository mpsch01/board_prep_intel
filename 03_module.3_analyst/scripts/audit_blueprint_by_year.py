"""
audit_blueprint_by_year.py
Audit blueprint distribution by year in the production DB.
Shows whether 2018-2023 have synthesized post-2023 canonical labels
or stale pre-2023 categories.
"""
import sqlite3
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"

db = sqlite3.connect(DB_PATH)

print("=== BLUEPRINT DISTRIBUTION BY YEAR ===")
rows = db.execute('''
    SELECT exam_year, blueprint, COUNT(*) as n
    FROM questions
    GROUP BY exam_year, blueprint
    ORDER BY exam_year, n DESC
''').fetchall()
for r in rows:
    print(f"  {r[0]}  |  {str(r[1]):<50}  |  n={r[2]}")

print()
print("=== DISTINCT BLUEPRINT LABELS PER YEAR ===")
rows = db.execute('''
    SELECT exam_year,
           COUNT(DISTINCT blueprint) as distinct_vals,
           GROUP_CONCAT(DISTINCT blueprint) as labels
    FROM questions
    GROUP BY exam_year
    ORDER BY exam_year
''').fetchall()
for r in rows:
    print(f"\n  {r[0]} ({r[1]} distinct value(s)):")
    for label in (r[2] or '').split(','):
        print(f"    - {label.strip()}")

print()
print("=== NULL / BLANK CHECK ===")
rows = db.execute('''
    SELECT exam_year,
           COUNT(*) as total,
           SUM(CASE WHEN blueprint IS NULL OR blueprint = '' THEN 1 ELSE 0 END) as missing
    FROM questions
    GROUP BY exam_year
    ORDER BY exam_year
''').fetchall()
for r in rows:
    status = "OK all filled" if r[2] == 0 else f"WARN {r[2]} missing"
    print(f"  {r[0]}: {r[1]} total — {status}")

print()
print("=== BODY_SYSTEM DISTRIBUTION BY YEAR ===")
rows = db.execute('''
    SELECT exam_year, body_system, COUNT(*) as n
    FROM questions
    GROUP BY exam_year, body_system
    ORDER BY exam_year, n DESC
''').fetchall()
for r in rows:
    print(f"  {r[0]}  |  {str(r[1]):<40}  |  n={r[2]}")

db.close()
