"""
db_connect.py — Reliable SQLite connection helper for ITE Intelligence DB.

Problem solved:
    sqlite3.connect(path) requires write access to the DB directory to create
    journal/lock files. When running from outside the mounted Windows filesystem
    (e.g., the Cowork Linux sandbox), this fails with "unable to open database
    file" even though the file is readable.

Fix:
    Use SQLite URI mode with immutable=1. This tells SQLite the DB will not
    change during this connection — skips journal file creation entirely.
    Safe for all read-only diagnostic queries and analysis runs.

Usage:
    from db_connect import open_db, DB_PATH

    db = open_db()                   # opens production DB
    db = open_db("/custom/path.db")  # opens any other DB
    db.row_factory = sqlite3.Row     # already set by default
    db.close()

    # Or as a context manager:
    with open_db() as db:
        rows = db.execute("SELECT COUNT(*) FROM articles").fetchall()
"""

import sqlite3
from pathlib import Path

# Canonical DB path — resolved relative to this file so it works
# regardless of the calling script's working directory.
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH      = str(PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db")


def open_db(path: str = None, *, row_factory=True) -> sqlite3.Connection:
    """
    Open ite_intelligence.db (or any SQLite DB) using immutable URI mode.

    Args:
        path:        Absolute path to the DB file. Defaults to production DB.
        row_factory: If True (default), sets db.row_factory = sqlite3.Row
                     so columns are accessible by name.

    Returns:
        sqlite3.Connection — caller is responsible for db.close().

    Raises:
        FileNotFoundError: if the DB file does not exist at the resolved path.
        sqlite3.OperationalError: if the file cannot be opened.
    """
    db_path = Path(path) if path else Path(DB_PATH)

    if not db_path.exists():
        raise FileNotFoundError(f"DB not found: {db_path}")

    # URI mode with immutable=1 skips journal/lock file creation.
    # Safe for read-only use; do NOT use for write operations.
    uri = db_path.as_uri() + "?immutable=1"
    conn = sqlite3.connect(uri, uri=True)

    if row_factory:
        conn.row_factory = sqlite3.Row

    return conn


class _DBContext:
    """Context manager wrapper so open_db() works with `with` statements."""
    def __init__(self, path, row_factory):
        self._path = path
        self._row_factory = row_factory
        self._conn = None

    def __enter__(self):
        self._conn = open_db(self._path, row_factory=self._row_factory)
        return self._conn

    def __exit__(self, *_):
        if self._conn:
            self._conn.close()


def db(path: str = None, *, row_factory=True) -> _DBContext:
    """
    Context manager version of open_db(). Closes connection automatically.

    Usage:
        with db() as conn:
            rows = conn.execute("SELECT COUNT(*) FROM articles").fetchall()
    """
    return _DBContext(path, row_factory)


# ---------------------------------------------------------------------------
# Quick self-test when run directly
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print(f"DB path: {DB_PATH}")
    conn = open_db()
    tables = ["articles", "questions", "aafp_questions",
              "question_concepttag_vec", "intersection_centroid_vec"]
    for t in tables:
        try:
            n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            print(f"  {t}: {n:,} rows")
        except sqlite3.OperationalError as e:
            print(f"  {t}: ERROR — {e}")
    conn.close()
    print("OK")
