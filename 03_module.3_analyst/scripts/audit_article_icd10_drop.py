"""
audit_article_icd10_drop.py
Check article_icd10 coverage after rebuild — explain the 68-row drop.
"""
import sqlite3
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"

db = sqlite3.connect(DB_PATH)

total = db.execute('SELECT COUNT(*) FROM article_icd10').fetchone()[0]
print(f"article_icd10 total rows: {total}")

untagged = db.execute('''
    SELECT COUNT(*) FROM articles a
    WHERE NOT EXISTS (
        SELECT 1 FROM article_icd10 x WHERE x.article_id = a.article_id
    )
''').fetchone()[0]
print(f"Articles with zero ICD-10 codes: {untagged} of {db.execute('SELECT COUNT(*) FROM articles').fetchone()[0]}")

print()
print("=== NEW ARTICLES (ART-1987+) ===")
new_arts = db.execute('''
    SELECT a.article_id, COUNT(x.icd10_code) as codes, a.title
    FROM articles a
    LEFT JOIN article_icd10 x ON x.article_id = a.article_id
    WHERE a.article_id >= 1987
    GROUP BY a.article_id
    ORDER BY a.article_id
''').fetchall()
for r in new_arts:
    print(f"  ART-{r[0]}: {r[1]} codes — {str(r[2])[:70]}")

print()
print("=== ARTICLES WITH ZERO CODES (sample of 20) ===")
zero_arts = db.execute('''
    SELECT a.article_id, a.title
    FROM articles a
    WHERE NOT EXISTS (
        SELECT 1 FROM article_icd10 x WHERE x.article_id = a.article_id
    )
    ORDER BY a.article_id
    LIMIT 20
''').fetchall()
for r in zero_arts:
    print(f"  ART-{r[0]}: {str(r[1])[:70]}")

db.close()
