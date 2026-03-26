"""
rename_tier_labels_in_db.py
-----------------------------
One-time maintenance: renames tier column values in the articles table
to match the new warehouse folder nomenclature.

  non-codon  →  VC_fail
  codon      →  VC_pass

Run AFTER renaming the warehouse folders on the filesystem.

Usage:
    python scripts/maintain/rename_tier_labels_in_db.py --dry-run
    python scripts/maintain/rename_tier_labels_in_db.py
"""

import sqlite3
import argparse
from pathlib import Path
from datetime import datetime

SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
DB_PATH      = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"
LOG_DIR      = PROJECT_ROOT / "00_database" / "logs"

RENAMES = [
    ("non-codon", "VC_fail"),
    ("codon",     "VC_pass"),
]


def main():
    parser = argparse.ArgumentParser(description="Rename tier labels in articles table")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview counts without writing to DB")
    args = parser.parse_args()

    if not DB_PATH.exists():
        print(f"ERROR: DB not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    print("=" * 60)
    print("rename_tier_labels_in_db.py")
    print(f"  DB      : {DB_PATH}")
    print(f"  Dry run : {args.dry_run}")
    print()

    # ── Pre-run counts ──────────────────────────────────────────────
    cur.execute("SELECT tier, COUNT(*) FROM articles GROUP BY tier ORDER BY tier")
    pre = dict(cur.fetchall())
    print("Pre-run tier distribution:")
    for t, c in sorted(pre.items()):
        print(f"  {t:<20} {c}")
    print()

    if args.dry_run:
        print("[DRY RUN] Would rename:")
        for old, new in RENAMES:
            print(f"  '{old}' → '{new}'  ({pre.get(old, 0)} rows)")
        print("\nNo changes written.")
        conn.close()
        return

    # ── Execute renames ──────────────────────────────────────────────
    total_updated = 0
    for old, new in RENAMES:
        cur.execute("UPDATE articles SET tier = ? WHERE tier = ?", (new, old))
        n = cur.rowcount
        total_updated += n
        print(f"  '{old}' → '{new}'  ({n} rows updated)")

    conn.commit()

    # ── Post-run counts ──────────────────────────────────────────────
    cur.execute("SELECT tier, COUNT(*) FROM articles GROUP BY tier ORDER BY tier")
    post = dict(cur.fetchall())
    print()
    print("Post-run tier distribution:")
    for t, c in sorted(post.items()):
        print(f"  {t:<20} {c}")

    print(f"\nTotal rows updated: {total_updated}")

    # ── Log ──────────────────────────────────────────────────────────
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"rename_tier_labels_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(log_path, "w") as f:
        f.write("rename_tier_labels_in_db.py\n")
        f.write(f"Run: {datetime.now().isoformat()}\n")
        f.write(f"Total updated: {total_updated}\n")
        for old, new in RENAMES:
            f.write(f"  {old} -> {new}\n")
        f.write("\nPost-run:\n")
        for t, c in sorted(post.items()):
            f.write(f"  {t}: {c}\n")
    print(f"Log: {log_path}")

    conn.close()


if __name__ == "__main__":
    main()
