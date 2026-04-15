# db_connect.py — SQLite Immutable URI Utility

**Location:** `03_module.3_analyst/scripts/db_connect.py`  
**Added:** BATON 057 (2026-04-15)  
**Status:** Stable  

## What It Does

Provides a utility function `open_db()` for safely opening the SQLite database in a sandbox environment, with automatic immutable mode enabled to prevent journal file conflicts.

## Why It Exists

When running in Linux sandboxes with NTFS mounts, SQLite's default WAL (write-ahead log) and journal file handling can trigger permission errors:
- `-journal` file creation fails on NTFS mounts
- Multi-process SQLite access patterns can deadlock
- Immutable mode (`?immutable=1` URI parameter) forces read-only behavior and disables journal creation

## How to Use

```python
from scripts.db_connect import open_db

# Open the database with immutable=1 URI parameter
conn = open_db()

# Execute read-only queries
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM articles')
count = cursor.fetchone()[0]
```

## Key Features

- **Automatic URI construction:** Builds `sqlite:///path/to/db?immutable=1` automatically
- **Relative path handling:** Resolves paths relative to PROJECT_ROOT (via `Path(__file__).resolve().parent.parent.parent`)
- **Zero configuration:** No env vars or config files needed
- **Read-only safety:** Immutable mode prevents accidental writes (correct for analysis workflows)

## When to Use

- **DO use** for M3 analyst scripts, query-only workflows, sandbox testing
- **DO NOT use** for data-mutating operations (use direct connection instead)
- **Prefer this** whenever running in a Linux sandbox with mounted NTFS drives
- **Safe to copy** to new analyst scripts — self-contained and zero-dependency

## Related Files

- `00_database/db/ite_intelligence.db` — source of truth (protected)
- `02_module.2_processor/main.py` — uses direct `sqlite3.connect()` for mutations
- `03_module.3_analyst/scripts/*.py` — should import and use `open_db()`
