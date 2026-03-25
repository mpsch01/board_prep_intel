"""
backfill_merge_source_fields.py — Merge backfill source fields into enriched JSONs
====================================================================================
One-time utility | 2026-03-25

The batch enrichment ran against the original (pre-backfill) extracted_json files,
so the enriched JSONs are missing the backfill fields from the Mac session:
  source.art_id, source.clean_ref, source.backfill_match_score,
  source.backfill_matched_on, source.backfill_date

This script reads those fields from the IMPORT_JSON_IMPORT/ files and merges
them into the matching extracted_json/ files, without touching ite_intelligence{}.

Run:
  python 02_module.2_processor/scripts/backfill_merge_source_fields.py
  python 02_module.2_processor/scripts/backfill_merge_source_fields.py --dry-run
"""

import json, glob, argparse
from pathlib import Path

SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent

IMPORT_DIR  = PROJECT_ROOT / "IMPORT" / "IMPORT_JSON_IMPORT"
TARGET_DIR  = PROJECT_ROOT / "extracted_json"

BACKFILL_FIELDS = ["art_id", "clean_ref", "backfill_match_score",
                   "backfill_matched_on", "backfill_date"]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    import_files = {p.name: p for p in IMPORT_DIR.glob("*.json")}
    target_files = {p.name: p for p in TARGET_DIR.glob("*.json")}

    matched = set(import_files) & set(target_files)
    print(f"Import files  : {len(import_files)}")
    print(f"Target files  : {len(target_files)}")
    print(f"Matched pairs : {len(matched)}")

    merged, skipped_no_artid, skipped_already, errors = 0, 0, 0, []

    for fname in sorted(matched):
        try:
            src = json.load(open(import_files[fname], encoding="utf-8"))
            tgt = json.load(open(target_files[fname], encoding="utf-8"))
        except Exception as e:
            errors.append((fname, str(e)))
            continue

        if not isinstance(src, dict) or not isinstance(tgt, dict):
            skipped_no_artid += 1
            continue
        src_source = src.get("source", {})
        if not src_source.get("art_id"):
            skipped_no_artid += 1
            continue

        tgt_source = tgt.setdefault("source", {})

        # Skip if already has correct art_id
        if tgt_source.get("art_id") == src_source.get("art_id"):
            skipped_already += 1
            continue

        # Merge backfill fields
        for field in BACKFILL_FIELDS:
            if src_source.get(field):
                tgt_source[field] = src_source[field]

        # Also carry citation_display if import has it and target doesn't
        if src_source.get("citation_display") and not tgt_source.get("citation_display"):
            tgt_source["citation_display"] = src_source["citation_display"]

        if not args.dry_run:
            with open(target_files[fname], "w", encoding="utf-8") as f:
                json.dump(tgt, f, indent=2, ensure_ascii=False)

        merged += 1
        if merged <= 5 or args.dry_run:
            print(f"  {'[DRY] ' if args.dry_run else ''}MERGED {fname[:60]} — art_id={src_source['art_id']}")

    print(f"\n{'DRY RUN — ' if args.dry_run else ''}COMPLETE")
    print(f"  Merged       : {merged}")
    print(f"  Already set  : {skipped_already}")
    print(f"  No art_id    : {skipped_no_artid}")
    print(f"  Errors       : {len(errors)}")
    if errors:
        for fname, err in errors[:5]:
            print(f"  ERR {fname[:50]}: {err}")

if __name__ == "__main__":
    main()
