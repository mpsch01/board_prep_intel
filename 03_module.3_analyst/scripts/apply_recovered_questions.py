"""
apply_recovered_questions.py
----------------------------
Applies the recovered_questions_insert.sql to the DB and prints a verification report.
Run from project root: python 03_module.3_analyst/scripts/apply_recovered_questions.py
"""
import sqlite3
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"
SQL_PATH = SCRIPT_DIR / "recovered_questions_insert.sql"

print("Applying recovered questions...")
print(f"DB:  {DB_PATH}")
print(f"SQL: {SQL_PATH}")
print()

db = sqlite3.connect(DB_PATH)
sql = SQL_PATH.read_text(encoding="utf-8")

# Strip the verification SELECT at the end — executescript doesn't return rows
# Split on COMMIT and run transaction separately
parts = sql.split("COMMIT;")
transaction_sql = parts[0] + "COMMIT;"

db.executescript(transaction_sql)

# Verification
print("Verification — inserted rows:")
rows = db.execute("""
    SELECT qid, exam_year, correct_letter, SUBSTR(question_text, 1, 70) as preview
    FROM questions
    WHERE qid IN (
        'QID-2020-0134','QID-2020-0138','QID-2021-0050','QID-2021-0168',
        'QID-2022-0175','QID-2023-0004','QID-2024-0017','QID-2024-0117',
        'QID-2024-0140','QID-2024-0187'
    )
    ORDER BY qid
""").fetchall()

for r in rows:
    print(f"  {r[0]} | {r[1]} | ans={r[2]} | {r[3]}...")

print()
print(f"Rows confirmed: {len(rows)}/10")

# Updated year counts
print()
print("Updated question counts per year:")
year_counts = db.execute("""
    SELECT exam_year, COUNT(*) as total, MIN(qid) as first, MAX(qid) as last
    FROM questions GROUP BY exam_year ORDER BY exam_year
""").fetchall()
for r in year_counts:
    print(f"  {r[0]}: {r[1]} questions ({r[2]} – {r[3]})")

db.close()
print()
print("Done.")
