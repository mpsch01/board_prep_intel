"""
audit_holdout_both_axes.py
Show blueprint + body_system for the 22 deprecated holdouts in 2024-2025.
Cross-reference both axes before finalizing corrections.
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
    SELECT qid, exam_year, body_system, blueprint, question_text
    FROM questions
    WHERE exam_year >= 2024
    AND body_system IN ({placeholders})
    ORDER BY exam_year, body_system, qid
''', DEPRECATED).fetchall()

print(f"{'QID':<20} {'Year':<6} {'body_system':<28} {'blueprint'}")
print("-" * 100)
for r in rows:
    qid, year, bs, bp, qtext = r
    print(f"{qid:<20} {year:<6} {str(bs):<28} {str(bp)}")

db.close()
