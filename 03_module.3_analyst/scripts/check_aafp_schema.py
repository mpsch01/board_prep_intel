import sqlite3
from pathlib import Path
db = sqlite3.connect(str(Path(__file__).resolve().parent.parent.parent / "00_database" / "db" / "ite_intelligence.db"))
print("aafp_questions columns:")
for row in db.execute("PRAGMA table_info(aafp_questions)"):
    print(f"  {row[1]:<30} {row[2]}")
print()
print("Sample row (first AAFP question):")
r = db.execute("SELECT * FROM aafp_questions LIMIT 1").fetchone()
cols = [d[0] for d in db.execute("PRAGMA table_info(aafp_questions)").fetchall()]
for col, val in zip(cols, r):
    v = str(val)[:80] if val else "NULL"
    print(f"  {col:<30} {v}")
db.close()
