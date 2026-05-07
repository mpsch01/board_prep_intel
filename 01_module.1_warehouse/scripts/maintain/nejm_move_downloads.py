"""Move downloaded NEJM PDFs from ~/Downloads into the right tier folders.

Pattern: filenames have format `Author_Year#@#ART-XXXX@#@.pdf`. We look up the
tier per article from `_nejm_with_dois.json` and move the file.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
TIER_ROOT = PROJECT_ROOT / "01_module.1_warehouse" / "citation_files" / "ITE"
PENDING = SCRIPT_DIR / "_nejm_with_dois.json"
DOWNLOADS = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Downloads"


def main() -> int:
    if not PENDING.exists():
        print(f"Missing {PENDING}")
        return 1
    entries = {e["article_id"]: e for e in json.loads(PENDING.read_text(encoding="utf-8"))}
    moved = skipped = bad = 0
    not_in_index = 0
    for pdf in DOWNLOADS.glob("*#@#ART-*@#@.pdf"):
        m = re.search(r"#@#(ART-\d+)@#@", pdf.name)
        if not m:
            continue
        art_id = m.group(1)
        # Skip if not in our pending list (e.g. JAMA stragglers)
        if art_id not in entries:
            print(f"NOT-IN-INDEX {art_id}: {pdf.name}")
            not_in_index += 1
            continue
        tier = entries[art_id].get("tier") or "VC_fail"
        if tier not in {"VC_pass", "VC_fail", "local_lite", "right_click"}:
            tier = "VC_fail"
        # Validate PDF
        try:
            head = pdf.read_bytes()[:8]
        except Exception as e:
            print(f"READ-ERR {art_id}: {e}")
            bad += 1
            continue
        if not head.startswith(b"%PDF"):
            print(f"NOT-PDF {art_id}: starts with {head!r}")
            bad += 1
            continue
        dest = TIER_ROOT / tier / pdf.name
        if dest.exists():
            # Skip if same size, replace if different
            if dest.stat().st_size == pdf.stat().st_size:
                pdf.unlink()
                print(f"DUPE     {art_id}: removed from Downloads (already in {tier}/)")
                skipped += 1
                continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(pdf), str(dest))
        print(f"MOVED    {art_id} -> {tier}/{pdf.name}")
        moved += 1
    print(f"\nSummary: {moved} moved, {skipped} dupes, {bad} bad PDFs, {not_in_index} not in NEJM index")
    return 0


if __name__ == "__main__":
    sys.exit(main())
