import sqlite3

DB = r'C:\Users\mpsch\Desktop\board_prep_intel\00_database\db\ite_intelligence.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()

# Check what's actually in the article_id column
cur.execute("SELECT article_id, clean_ref, title FROM articles LIMIT 5")
print("=== Sample articles rows ===")
for row in cur.fetchall():
    print(f"  article_id={row[0]!r}  clean_ref={row[1]!r}  title={row[2][:60]!r}")

# Check if ART-0003 is in the DB
cur.execute("SELECT article_id, clean_ref, title FROM articles WHERE article_id = 'ART-0003'")
row = cur.fetchone()
print(f"\n=== ART-0003 lookup by article_id: {row}")

cur.execute("SELECT article_id, clean_ref, title FROM articles WHERE clean_ref = 'ART-0003'")
row = cur.fetchone()
print(f"=== ART-0003 lookup by clean_ref:  {row}")

conn.close()
