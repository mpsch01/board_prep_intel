"""
audit_holdout_body_system.py
Pull 2024-2025 questions still carrying deprecated pre-2023 body_system labels.
These are likely the human-review holdouts from the body_system QC pass.
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
    SELECT qid, exam_year, body_system, question_text, correct_text
    FROM questions
    WHERE exam_year >= 2024
    AND body_system IN ({placeholders})
    ORDER BY exam_year, body_system, qid
''', DEPRECATED).fetchall()

print(f"=== DEPRECATED BODY_SYSTEM LABELS IN 2024-2025 ({len(rows)} records) ===\n")
for r in rows:
    qid, year, bs, qtext, correct = r
    print(f"QID: {qid}  |  Year: {year}  |  Current label: [{bs}]")
    print(f"  Q: {(qtext or '')[:200]}")
    print(f"  A: {(correct or '')[:100]}")
    print()

db.close()
print(f"Total holdouts: {len(rows)}")
