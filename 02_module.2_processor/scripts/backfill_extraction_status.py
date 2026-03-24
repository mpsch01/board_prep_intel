"""
backfill_extraction_status.py  v1.2
Matches enriched JSONs to articles via QID bridge:
  enriched JSON -> question_ids -> question_ref_pairs.clean_ref -> articles.clean_ref
Then sets extraction_status = 'extracted' for matched articles.
"""
import sys, json, sqlite3
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

DB_PATH      = Path(r"C:\Users\mpsch\Desktop\claude_knowledge\abfm_prep\02_ite_intelligence\db\ite_intelligence.db")
ENRICHED_DIR = Path(r"C:\Users\mpsch\Desktop\claude_knowledge\clinical_guidelines\03_enriched_JSON")

conn = sqlite3.connect(str(DB_PATH))
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Build QID -> clean_ref lookup from the DB
cur.execute("SELECT qid, clean_ref FROM question_ref_pairs")
qid_to_refs = {}
for row in cur.fetchall():
    qid_to_refs.setdefault(row['qid'], []).append(row['clean_ref'])

# Build clean_ref -> article_id lookup
cur.execute("SELECT clean_ref, article_id FROM articles")
ref_to_artid = {r['clean_ref']: r['article_id'] for r in cur.fetchall()}

print(f"DB loaded: {len(qid_to_refs)} QID->ref pairs, {len(ref_to_artid)} articles")

# Scan enriched JSONs, find article_ids via QID bridge
matched_article_ids = set()
unmatched = []

for jf in ENRICHED_DIR.glob("*.json"):
    try:
        with open(jf, encoding='utf-8') as f:
            d = json.load(f)
        qids = d.get('ite_intelligence', {}).get('question_ids', []) or []
        found = False
        for qid in qids:
            refs = qid_to_refs.get(qid, [])
            for ref in refs:
                art_id = ref_to_artid.get(ref)
                if art_id:
                    matched_article_ids.add(art_id)
                    found = True
        if not found:
            unmatched.append(jf.name)
    except Exception as e:
        print(f"  ERROR: {jf.name}: {e}")

print(f"Enriched JSONs matched to article_ids: {len(matched_article_ids)}")
print(f"Enriched JSONs with no match:          {len(unmatched)}")

# Update DB
updated = 0
for art_id in matched_article_ids:
    cur.execute("UPDATE articles SET extraction_status = 'extracted' WHERE article_id = ?", (art_id,))
    updated += 1

conn.commit()

cur.execute("SELECT extraction_status, COUNT(*) FROM articles GROUP BY extraction_status")
dist = dict(cur.fetchall())
conn.close()

print()
print("=" * 50)
print("DONE  v1.2")
print(f"  Updated to 'extracted': {updated}")
print(f"  Remaining 'pending':    {dist.get('pending', 0)}")
print()
if unmatched:
    print("Unmatched enriched JSONs (no QID link):")
    for f in unmatched:
        print(f"  {f}")
