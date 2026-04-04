#!/usr/bin/env python3
"""
AAFP Filename Cleanup
======================
Fixes two issues from the initial download run:

  1. ALL-CAPS author names in 2017 files (e.g., MUNCIE_2017.pdf → Muncie_2017.pdf)
  2. False DB match: Williams_2022#@#ART-0121@#@.pdf is actually Celiac Disease,
     not Metabolic Surgery (ART-0121). Strips the incorrect ART-ID.

Usage:
  python aafp_cleanup_filenames.py
"""

import os
import re
import json
from pathlib import Path

SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent   # maintain/ → scripts/ → 01_module.1_warehouse/ → root
DEST_FOLDER  = PROJECT_ROOT / "01_module.1_warehouse" / "citation_files" / "ITE" / "VC_fail"
LOG_PATH     = DEST_FOLDER / "_download_log.json"

renames = []

for fname in os.listdir(DEST_FOLDER):
    if not fname.endswith('.pdf'):
        continue

    new_name = fname

    # --- Fix 1: ALL-CAPS author (e.g., MUNCIE_2017 → Muncie_2017) ---
    # Pattern: starts with 2+ uppercase letters before the underscore+year
    if re.match(r'^[A-Z]{2,}[_-]', fname):
        # Title-case just the author portion (before first underscore)
        parts    = fname.split('_', 1)
        new_name = parts[0].title() + '_' + parts[1]

    # --- Fix 2: Williams_2022 false match (Celiac Disease ≠ ART-0121) ---
    if fname == 'Williams_2022#@#ART-0121@#@.pdf':
        new_name = 'Williams_2022.pdf'

    if new_name != fname:
        renames.append((fname, new_name))

if not renames:
    print("No renames needed — everything looks clean.")
else:
    print(f"Found {len(renames)} files to rename:\n")
    for old, new in renames:
        src = os.path.join(DEST_FOLDER, old)
        dst = os.path.join(DEST_FOLDER, new)
        if os.path.exists(dst):
            print(f"  SKIP (target exists): {old} → {new}")
            continue
        os.rename(src, dst)
        print(f"  ✓  {old}  →  {new}")

    # Update the download log to reflect new filenames
    with open(LOG_PATH) as f:
        log = json.load(f)

    rename_map = {old: new for old, new in renames}

    for entry in log.get('downloaded', []):
        if entry.get('filename') in rename_map:
            old_fn = entry['filename']
            entry['filename'] = rename_map[old_fn]
            # Also strip the false ART-ID from Williams
            if old_fn == 'Williams_2022#@#ART-0121@#@.pdf':
                entry['art_id'] = None

    with open(LOG_PATH, 'w') as f:
        json.dump(log, f, indent=2)

    print(f"\nLog updated → {LOG_PATH}")

print("\nDone.")
