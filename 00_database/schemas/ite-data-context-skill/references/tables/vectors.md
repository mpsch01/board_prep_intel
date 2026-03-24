# Vector Tables (sqlite-vec Extension)

**Extension required**: `sqlite-vec` (Python package: `sqlite_vec`)
**Embedding model**: OpenAI `text-embedding-3-small` (1,536 dimensions)
**Computed by**: `scripts/compute_embeddings.py`

## article_vec

**Type**: Virtual table (`vec0`)
**Key**: `article_id` (TEXT) — matches `articles.article_id`
**Embedding source**: Article title + organization + year concatenated with " | " separator
**Count**: 1,397 embeddings
**Purpose**: Originally used as semantic fallback (Strategy 5) in the v3 enrichment pipeline. **No longer used for enrichment in v4** — retained for potential analytical use (e.g., "find similar articles by meaning").

## question_vec

**Type**: Virtual table (`vec0`)
**Key**: `qid` (TEXT) — matches `questions.qid`
**Embedding source**: Question stem + concept_summary
**Count**: 1,189 embeddings
**Purpose**: Enables semantic question similarity search (e.g., "find questions similar to this one").

## Internal Tables

Each virtual table creates 4 internal tables (do not query directly):
- `*_chunks` — chunk metadata
- `*_info` — key-value config
- `*_rowids` — ID mapping
- `*_vector_chunks00` — raw vector blobs

## Usage Notes

- **Loading**: Must call `sqlite_vec.load(conn)` after `conn.enable_load_extension(True)`
- **Query syntax**: `WHERE embedding MATCH ? AND k = 5 ORDER BY distance`
- **Distance metric**: Cosine distance (lower = more similar)
- **Threshold**: `0.9972` (from `validate_vector_search.py` 75th percentile analysis)
- **Query embedding**: Must be packed as `struct.pack(f"{1536}f", *embedding_list)` — raw float32 bytes

## Example: Find similar articles

```python
import sqlite3, sqlite_vec, struct
from openai import OpenAI

conn = sqlite3.connect("ite_intelligence.db")
conn.enable_load_extension(True)
sqlite_vec.load(conn)

client = OpenAI()
resp = client.embeddings.create(model="text-embedding-3-small", input=["heart failure GDMT"])
emb = resp.data[0].embedding
query_blob = struct.pack(f"{len(emb)}f", *emb)

results = conn.execute("""
    SELECT article_id, distance
    FROM article_vec
    WHERE embedding MATCH ? AND k = 5
    ORDER BY distance
""", (query_blob,)).fetchall()

for aid, dist in results:
    art = conn.execute("SELECT canonical_filename, tier FROM articles WHERE article_id=?", (aid,)).fetchone()
    print(f"{aid} | {art[0]} | tier={art[1]} | distance={dist:.6f}")
```