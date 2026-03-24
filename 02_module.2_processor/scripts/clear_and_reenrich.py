"""
clear_and_reenrich.py
=====================
Step 1: Strip ite_intelligence block from all JSONs in the target folder.
Step 2: Run the enricher on the folder.

Usage:
  python scripts\clear_and_reenrich.py
  python scripts\clear_and_reenrich.py --dry-run   (preview only, no changes)
"""

import json, subprocess, sys, argparse
from pathlib import Path

SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
ENRICHED_DIR = SCRIPT_DIR.parent / "outputs"
ENRICHER     = Path(__file__).resolve().parent / "ite_intelligence_enricher.py"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    files = sorted(ENRICHED_DIR.glob("*_extracted.json"))
    print(f"Found {len(files)} extracted JSONs in target folder.")
    print()

    # ── Step 1: Clear ite_intelligence blocks ──────────────────────────────
    cleared = 0
    already_clear = 0
    for fpath in files:
        try:
            with open(fpath, encoding="utf-8") as f:
                doc = json.load(f)
        except Exception as e:
            print(f"  [WARN] Could not read {fpath.name}: {e}")
            continue

        if "ite_intelligence" not in doc:
            already_clear += 1
            continue

        if args.dry_run:
            print(f"  [DRY] Would clear: {fpath.name}")
            cleared += 1
            continue

        doc.pop("ite_intelligence")
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2, ensure_ascii=False)
        cleared += 1

    print(f"Step 1 complete: cleared {cleared} | already clear {already_clear}")
    print()

    if args.dry_run:
        print("DRY RUN — skipping enricher. Remove --dry-run to proceed.")
        return

    # ── Step 2: Run enricher ───────────────────────────────────────────────
    print("Step 2: Running enricher on all files...")
    print("-" * 60)
    result = subprocess.run(
        [sys.executable, str(ENRICHER), "--dir", str(ENRICHED_DIR)],
        cwd=str(ENRICHER.parent.parent)
    )
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()
