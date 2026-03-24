import sqlite3

DB = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\ite_intelligence\db\ite_intelligence.db'
conn = sqlite3.connect(DB)
c = conn.cursor()

c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in c.fetchall()]
print("TABLES:", tables)

for t in tables:
    c.execute(f"PRAGMA table_info({t})")
    cols = c.fetchall()
    print(f"\n--- {t} ---")
    for col in cols:
        print(f"  {col[1]:30s} {col[2]}")

print()
for t in tables:
    c.execute(f"SELECT COUNT(*) FROM {t}")
    print(f"{t}: {c.fetchone()[0]} rows")

print("\nSample article:")
c.execute("SELECT * FROM articles LIMIT 1")
row = c.fetchone()
c.execute("PRAGMA table_info(articles)")
cols = [x[1] for x in c.fetchall()]
for k, v in zip(cols, row):
    print(f"  {k}: {str(v)[:100]}")

print("\nSample question:")
c.execute("SELECT * FROM questions LIMIT 1")
row = c.fetchone()
c.execute("PRAGMA table_info(questions)")
cols = [x[1] for x in c.fetchall()]
for k, v in zip(cols, row):
    print(f"  {k}: {str(v)[:120]}")

print("\nSample pairs:")
c.execute("SELECT * FROM question_ref_pairs LIMIT 3")
rows = c.fetchall()
c.execute("PRAGMA table_info(question_ref_pairs)")
cols2 = [x[1] for x in c.fetchall()]
for row in rows:
    print(" ", dict(zip(cols2, row)))

conn.close()
