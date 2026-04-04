import sqlite3
from pathlib import Path

SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent   # scripts/ → agents/ → skills_abilities/ → root

DB_PATH = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

afp_authors = [
    ('Abraham', '2014'),
    ('Braun', '2015'),
    ('Brink', '2018'),
    ('Croke', '2020'),
    ('Ebell', '2020'),
    ('Gaddey', '2022'),
    ('Hauk', '2017'),
    ('Heath', '2022'),
    ('Kalra', '2014'),
    ('Plensdorf', '2017'),
    ('Randel', '2015'),
    ('Searight', '2018'),
    ('Viera', '2015'),
]

print(f"{'Author':<20} {'Year':<6} {'ART-ID':<12} {'Source':<8} {'Title'}")
print('-' * 90)

for author, year in afp_authors:
    cur.execute('''
        SELECT article_id, author1, year, title, source_type, codon_filename
        FROM articles
        WHERE author1 LIKE ? AND year = ?
    ''', (f'%{author}%', year))
    rows = cur.fetchall()
    if rows:
        for row in rows:
            print(f"{row['author1']:<20} {row['year']:<6} {row['article_id']:<12} {str(row['source_type']):<8} {(row['title'] or '')[:40]}")
    else:
        print(f"{author:<20} {year:<6} NOT FOUND")

conn.close()