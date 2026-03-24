"""
rename_to_codon.py — Migration Step 4: Rename PDFs to Codon Format
===================================================================
Codon Migration | ITE Intelligence 2.0

Reads match_staging_report.json (output of Step 1), then renames each
matched PDF to its codon filename from the articles table.

Safety:
  - DRY-RUN by default (shows what would change, touches nothing)
  - --execute flag required to actually rename
  - Generates rename_log.json for full rollback capability
  - Validates no target filename collisions before any rename
  - Skips omitted files and duplicate PDFs (picks canonical)

Duplicate handling:
  When multiple PDFs map to the same ART-ID, the script picks the
  canonical PDF (highest confidence match, or the one NOT flagged as
  a duplicate in manual_overrides.json) and skips the rest.

Run:
  python scripts/rename_to_codon.py                  # dry-run
  python scripts/rename_to_codon.py --execute         # actually rename
  python scripts/rename_to_codon.py --rollback        # undo using rename_log.json
"""

import json, os, sys, shutil, argparse
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR     = Path(__file__).resolve().parent.parent          # 02_ite_intelligence/
PROJ_ROOT    = BASE_DIR.parent.parent                          # claude_knowledge/
PDF_DIR      = PROJ_ROOT / "clinical_guidelines" / "01_pdf_guideline_library" / "pdf_non-codon"
REPORT_JSON  = BASE_DIR / "logs" / "match_staging_report.json"
OVERRIDES    = BASE_DIR / "manual_overrides.json"
LOG_DIR      = BASE_DIR / "logs"


def load_staging_report():
    """Load match staging report and return list of results."""
    if not REPORT_JSON.exists():
        print(f"ERROR: Staging report not found: {REPORT_JSON}")
        print("Run build_match_staging.py first.")
        sys.exit(1)
    with open(REPORT_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def load_duplicate_map():
    """Load duplicate PDF mapping from manual overrides."""
    if OVERRIDES.exists():
        with open(OVERRIDES, "r", encoding="utf-8") as f:
            ovr = json.load(f)
        return ovr.get("duplicates", {})
    return {}


def build_rename_plan(results, duplicate_map):
    """
    Build the rename plan from staging results.

    For duplicate ART-IDs: pick canonical PDF using priority rules:
      1. Manual overrides that are NOT flagged as duplicates win
      2. Higher confidence wins
      3. Shorter filename wins (tiebreaker)

    Returns:
      rename_plan: list of {old, new, article_id, method, confidence}
      skipped: list of {pdf, reason}
    """
    rename_plan = []
    skipped = []

    # Filter to active matched results only (exclude low-confidence matches)
    active_matched = [
        r for r in results
        if r.get("article_id") and r.get("match_method") != "omitted"
        and r.get("confidence") != "low"
    ]

    # Group by article_id to handle duplicates
    by_art_id = {}
    for r in active_matched:
        by_art_id.setdefault(r["article_id"], []).append(r)

    # Known duplicate PDFs from overrides
    known_dupes = set(duplicate_map.keys())

    conf_rank = {"high": 0, "medium": 1, "low": 2}

    for art_id, entries in sorted(by_art_id.items()):
        if len(entries) == 1:
            # Single PDF → straightforward rename
            r = entries[0]
            codon = r.get("codon_filename")
            if not codon:
                skipped.append({"pdf": r["pdf_filename"], "reason": "No codon_filename in DB"})
                continue
            rename_plan.append({
                "old": r["pdf_filename"],
                "new": codon,
                "article_id": art_id,
                "method": r["match_method"],
                "confidence": r["confidence"],
            })
        else:
            # Multiple PDFs → pick canonical, skip the rest
            # Sort: non-duplicate first, then by confidence, then by filename length
            def sort_key(r):
                is_known_dupe = 1 if r["pdf_filename"] in known_dupes else 0
                is_flagged_dupe = 1 if r.get("is_duplicate") else 0
                conf = conf_rank.get(r.get("confidence", "low"), 2)
                return (is_known_dupe, is_flagged_dupe, conf, len(r["pdf_filename"]))

            sorted_entries = sorted(entries, key=sort_key)
            canonical = sorted_entries[0]
            codon = canonical.get("codon_filename")

            if not codon:
                for r in entries:
                    skipped.append({"pdf": r["pdf_filename"], "reason": "No codon_filename in DB"})
                continue

            rename_plan.append({
                "old": canonical["pdf_filename"],
                "new": codon,
                "article_id": art_id,
                "method": canonical["match_method"],
                "confidence": canonical["confidence"],
            })

            for r in sorted_entries[1:]:
                skipped.append({
                    "pdf": r["pdf_filename"],
                    "reason": f"Duplicate of {canonical['pdf_filename']} → {art_id}",
                })

    # Add omitted files to skipped
    omitted = [r for r in results if r.get("match_method") == "omitted"]
    for r in omitted:
        skipped.append({"pdf": r["pdf_filename"], "reason": "Omitted from migration"})

    # Add low-confidence files to skipped (deferred for manual triage)
    low_conf = [
        r for r in results
        if r.get("confidence") == "low" and r.get("match_method") != "omitted"
        and r.get("article_id")
    ]
    for r in low_conf:
        skipped.append({"pdf": r["pdf_filename"], "reason": "Low confidence — deferred for triage"})

    return rename_plan, skipped


def validate_plan(rename_plan):
    """
    Validate the rename plan before execution.
    Returns list of error strings (empty = valid).
    """
    errors = []

    # Check for target filename collisions
    targets = Counter(r["new"] for r in rename_plan)
    for target, count in targets.items():
        if count > 1:
            sources = [r["old"] for r in rename_plan if r["new"] == target]
            errors.append(f"COLLISION: {count} files would rename to '{target}': {sources}")

    # Check source files exist
    for r in rename_plan:
        src = PDF_DIR / r["old"]
        if not src.exists():
            errors.append(f"MISSING: Source file not found: {r['old']}")

    # Check target files don't already exist
    for r in rename_plan:
        tgt = PDF_DIR / r["new"]
        if tgt.exists() and r["old"] != r["new"]:
            errors.append(f"EXISTS: Target already exists: {r['new']}")

    return errors


def execute_renames(rename_plan, dry_run=True):
    """
    Execute the rename plan.
    Returns rename_log (list of {old, new, article_id, status, timestamp}).
    """
    rename_log = []
    now = datetime.now(timezone.utc).isoformat()
    success = 0
    failed = 0

    for r in rename_plan:
        src = PDF_DIR / r["old"]
        tgt = PDF_DIR / r["new"]
        entry = {
            "old": r["old"],
            "new": r["new"],
            "article_id": r["article_id"],
            "method": r["method"],
            "confidence": r["confidence"],
            "timestamp": now,
        }

        if dry_run:
            entry["status"] = "dry_run"
            tag = "DRY-RUN"
        else:
            try:
                src.rename(tgt)
                entry["status"] = "renamed"
                tag = "RENAMED"
                success += 1
            except OSError as e:
                entry["status"] = f"error: {e}"
                tag = "ERROR"
                failed += 1

        rename_log.append(entry)
        print(f"  [{tag:7s}] {r['old'][:55]}")
        print(f"           → {r['new']}")

    if not dry_run:
        print(f"\n  Renamed: {success}  Failed: {failed}")

    return rename_log


def execute_rollback(log_path):
    """Undo renames using a rename_log.json file."""
    if not log_path.exists():
        print(f"ERROR: Rename log not found: {log_path}")
        sys.exit(1)

    with open(log_path, "r", encoding="utf-8") as f:
        log = json.load(f)

    renamed_entries = [e for e in log if e["status"] == "renamed"]
    if not renamed_entries:
        print("No renamed entries in log — nothing to roll back.")
        return

    print(f"Rolling back {len(renamed_entries)} renames...")
    success = 0
    failed = 0
    for entry in renamed_entries:
        src = PDF_DIR / entry["new"]   # current name (codon)
        tgt = PDF_DIR / entry["old"]   # original name
        try:
            src.rename(tgt)
            print(f"  [ROLLED BACK] {entry['new']} → {entry['old']}")
            success += 1
        except OSError as e:
            print(f"  [ERROR] {entry['new']}: {e}")
            failed += 1

    print(f"\n  Rolled back: {success}  Failed: {failed}")


def main():
    parser = argparse.ArgumentParser(description="Rename PDFs to codon format (Step 4)")
    parser.add_argument("--execute", action="store_true",
                        help="Actually rename files (default is dry-run)")
    parser.add_argument("--rollback", action="store_true",
                        help="Undo renames using rename_log.json")
    args = parser.parse_args()

    # Rollback mode
    if args.rollback:
        log_path = LOG_DIR / "rename_log.json"
        execute_rollback(log_path)
        return

    # Load data
    results = load_staging_report()
    duplicate_map = load_duplicate_map()

    # Build plan
    rename_plan, skipped = build_rename_plan(results, duplicate_map)

    mode = "EXECUTE" if args.execute else "DRY-RUN"
    print(f"CODON RENAME — {mode}")
    print("=" * 60)
    print(f"  Rename plan:  {len(rename_plan)} files")
    print(f"  Skipped:      {len(skipped)} files")
    print(f"    Omitted:    {sum(1 for s in skipped if 'Omitted' in s['reason'])}")
    print(f"    Duplicates: {sum(1 for s in skipped if 'Duplicate' in s['reason'])}")
    print(f"    Other:      {sum(1 for s in skipped if 'Omitted' not in s['reason'] and 'Duplicate' not in s['reason'])}")
    print()

    # Validate
    errors = validate_plan(rename_plan)
    if errors:
        print("VALIDATION ERRORS — cannot proceed:")
        for e in errors:
            print(f"  {e}")
        sys.exit(1)
    print(f"Validation passed: no collisions, all sources exist, no target conflicts.")
    print()

    # Execute (or dry-run)
    rename_log = execute_renames(rename_plan, dry_run=not args.execute)

    # Write rename log
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / "rename_log.json"
    log_data = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "mode": mode.lower(),
        "summary": {
            "planned": len(rename_plan),
            "skipped": len(skipped),
            "renamed": sum(1 for e in rename_log if e["status"] == "renamed"),
            "errors": sum(1 for e in rename_log if e["status"].startswith("error")),
        },
        "renames": rename_log,
        "skipped": skipped,
    }
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log_data, f, indent=2, ensure_ascii=False)
    print(f"\nRename log: {log_path}")

    if not args.execute:
        print(f"\nThis was a DRY RUN. To actually rename, run:")
        print(f"  python scripts/rename_to_codon.py --execute")
        print(f"\nTo undo after executing:")
        print(f"  python scripts/rename_to_codon.py --rollback")


if __name__ == "__main__":
    main()
