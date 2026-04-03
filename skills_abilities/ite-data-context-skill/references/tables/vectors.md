# Vector & Embedding Tables

Two categories of embedding storage exist in the DB, with different requirements:

---

## Category 1: sqlite-vec Virtual Tables (require extension)

**Extension required**: `sqlite-vec` (Python package: `sqlite_vec`)
**Embedding model**: OpenAI `text-embedding-3-small` (1,536 dimensions)
**Computed by**: `scripts/compute_embeddings.py`

### article_vec

**Type**: Virtual table (`vec0`)
**Key**: `article_id` (TEXT) — matches `articles.article_id`
**Embedding source**: Article title + organization + year concatenated with " | " separator
**Count**: 1,985 embeddings
**Purpose**: Semantic article similarity search (e.g., "find articles similar to this one by meaning"). No longer used for enrichment in v4 — retained for analytical use.

### question_vec

**Type**: Virtual table (`vec0`)
**Key**: `qid` (TEXT) — matches `questions.qid`
**Embedding source**: Question stem + concept_summary
**Count**: 1,629 embeddings (all 8 years)
**Purpose**: Semantic question similarity search.

### aafp_question_vec

**Type**: Virtual table (`vec0`)
**Key**: `aafp_qid` (TEXT) — matches `aafp_questions.aafp_qid`
**Embedding source**: Question stem + concept_summary
**Count**: 1,221 embeddings
**Purpose**: Semantic AAFP question similarity; `ite_nearest_qid` + `ite_nearest_dist` pre-computed on `aafp_questions`.

### Internal Tables (do not query directly)
Each virtual table creates 4 helper tables: `*_chunks`, `*_info`, `*_rowids`, `*_vector_chunks00`.

### Usage Notes (sqlite-vec tables)
- **Loading**: `conn.enable_load_extension(True); sqlite_vec.load(conn)`
- **Query syntax**: `WHERE embedding MATCH ? AND k = 5 ORDER BY distance`
- **Distance metric**: Cosine distance (lower = more similar)
- **Threshold**: `0.9972` (from `validate_vector_search.py` 75th percentile analysis)
- **Query embedding**: Must be packed as `struct.pack(f"{1536}f", *embedding_list)` — raw float32 bytes

---

## Category 2: BLOB Embedding Tables (no extension needed)

These store embeddings as raw BLOB columns in standard SQLite tables. No extension required — just `conn.execute()`.

### icd10_vec

**Table type**: Regular table (BLOB column)
**Key**: `icd10_code` (TEXT, PK)
**Count**: 2,219 rows (unique ICD-10 codes that appear in article_icd10)
**Schema**: `icd10_code`, `icd10_desc`, `embedding` (BLOB), `model` (TEXT), `dim` (INTEGER)
**Embedding source**: ICD-10 description text
**Purpose**: Find semantically similar ICD-10 codes; seed for condition-level search.

### article_icd10_vec

**Table type**: Regular table (BLOB column)
**Key**: `article_id` (TEXT, PK)
**Count**: 1,757 rows
**Schema**: `article_id`, `embedding` (BLOB), `code_count` (INTEGER), `model` (TEXT)
**Embedding source**: Aggregated from the ICD-10 codes assigned to each article
**Purpose**: Article-level ICD-10 semantic profile — find articles matching a clinical condition profile.

### question_icd10_vec

**Table type**: Regular table (BLOB column)
**Key**: `(qid, source_bank)` composite PK
**Count**: 2,747 rows (ITE + subset of AAFP questions)
**Schema**: `qid` (TEXT), `source_bank` (TEXT: `ITE` or `AAFP`), `embedding` (BLOB), `code_count` (INTEGER), `model` (TEXT)
**Embedding source**: Aggregated from the ICD-10 codes assigned to each question
**Purpose**: Question-level ICD-10 semantic profile — find questions semantically related to a condition.

---

## Example: Find similar articles (sqlite-vec)

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

## Example: Cosine similarity using BLOB tables (no extension)

```python
import sqlite3, numpy as np, struct

def decode_blob(blob, dim=1536):
    return np.array(struct.unpack(f"{dim}f", blob))

def cosine_sim(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

conn = sqlite3.connect("ite_intelligence.db")

# Get two article ICD-10 embeddings and compare
rows = conn.execute(
    "SELECT article_id, embedding FROM article_icd10_vec WHERE article_id IN ('ART-0470', 'ART-0123')"
).fetchall()

emb_a = decode_blob(rows[0][1])
emb_b = decode_blob(rows[1][1])
print(f"Cosine similarity: {cosine_sim(emb_a, emb_b):.4f}")
```
