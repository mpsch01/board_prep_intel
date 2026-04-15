"""
critique_pdf_registry.py
=========================
Manages the Anthropic Files API registry for ITE exam PDFs.

Upload once → reference forever by file_id. The registry persists locally
so PDFs are never re-uploaded unnecessarily. Handles both critique books
and score report PDFs.

Files API retention: 30 days (auto-expires). The registry tracks expiry
dates and flags stale IDs so you know when to re-upload.

Usage:
    # Upload all critique PDFs (skips already-uploaded ones)
    python critique_pdf_registry.py --upload-all

    # Upload specific year
    python critique_pdf_registry.py --upload --year 2025

    # List registered files with status
    python critique_pdf_registry.py --list

    # Show file_id for a specific PDF (for use in scripts)
    python critique_pdf_registry.py --get --year 2025 --type critique

    # Delete a file from Anthropic + remove from registry
    python critique_pdf_registry.py --delete --year 2022 --type critique

    # Check which files are expired (older than 30 days)
    python critique_pdf_registry.py --check-expiry

Environment:
    ANTHROPIC_API_KEY: required
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta, timezone

# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
EXAM_DIR     = PROJECT_ROOT / "01_module.1_warehouse" / "ite_exams"
RESIDENT_DIR = PROJECT_ROOT / "03_module.3_analyst" / "resident_data"

# Registry lives alongside the other body_system_labels outputs
REGISTRY_PATH = (
    PROJECT_ROOT / "03_module.3_analyst" / "outputs" / "body_system_labels"
    / "pdf_file_registry.json"
)

# File retention on Anthropic's servers (days)
RETENTION_DAYS = 28   # use 28 as safe buffer before the 30-day expiry

# ── Known PDFs ─────────────────────────────────────────────────────────────────
# Maps (year, pdf_type) → relative path under EXAM_DIR or RESIDENT_DIR
EXAM_PDFS = {
    (2018, "critique"): EXAM_DIR / "2018_critique.pdf",
    (2019, "critique"): EXAM_DIR / "2019_critique.pdf",
    (2020, "critique"): EXAM_DIR / "2020_critique.pdf",
    (2021, "critique"): EXAM_DIR / "2021_critique.pdf",
    (2022, "critique"): EXAM_DIR / "2022_critique.pdf",
    (2023, "critique"): EXAM_DIR / "2023_critique.pdf",
    (2024, "critique"): EXAM_DIR / "2024_critique.pdf",
    (2025, "critique"): EXAM_DIR / "2025_critique.pdf",
    (2018, "mc"):       EXAM_DIR / "2018_MC.pdf",
    (2019, "mc"):       EXAM_DIR / "2019_MC.pdf",
    (2020, "mc"):       EXAM_DIR / "2020_MC.pdf",
    (2021, "mc"):       EXAM_DIR / "2021_MC.pdf",
    (2022, "mc"):       EXAM_DIR / "2022_MC.pdf",
    (2023, "mc"):       EXAM_DIR / "2023_MC.pdf",
    (2024, "mc"):       EXAM_DIR / "2024_MC.pdf",
    (2025, "mc"):       EXAM_DIR / "2025_MC.pdf",
}

SCORE_REPORT_PDFS = {
    (2022, "blueprint"): RESIDENT_DIR / "ITE_michael_scholl" / "inputs" / "scholl_2022_Item_Blueprint_Performance.PDF",
    (2023, "blueprint"): RESIDENT_DIR / "ITE_michael_scholl" / "inputs" / "scholl_2023_blueprint.PDF",
    (2024, "blueprint"): RESIDENT_DIR / "ITE_michael_scholl" / "inputs" / "scholl_2024_blueprint_report.PDF",
}

ALL_KNOWN_PDFS = {**EXAM_PDFS, **SCORE_REPORT_PDFS}


# ── Registry helpers ───────────────────────────────────────────────────────────

def load_registry() -> dict:
    """Load the file registry from disk. Returns empty dict if not found."""
    if REGISTRY_PATH.exists():
        with open(REGISTRY_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_registry(registry: dict) -> None:
    """Save the file registry to disk."""
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_PATH.write_text(json.dumps(registry, indent=2), encoding="utf-8")


def registry_key(year: int, pdf_type: str) -> str:
    return f"{year}_{pdf_type}"


def is_expired(entry: dict) -> bool:
    """Check if a registry entry is older than RETENTION_DAYS."""
    uploaded_at = entry.get("uploaded_at")
    if not uploaded_at:
        return True
    try:
        upload_dt = datetime.fromisoformat(uploaded_at)
        if upload_dt.tzinfo is None:
            upload_dt = upload_dt.replace(tzinfo=timezone.utc)
        expiry = upload_dt + timedelta(days=RETENTION_DAYS)
        return datetime.now(timezone.utc) > expiry
    except Exception:
        return True


def get_file_id(year: int, pdf_type: str) -> str | None:
    """
    Return the file_id for a given PDF if registered and not expired.
    Returns None if not registered or expired.
    """
    registry = load_registry()
    key = registry_key(year, pdf_type)
    entry = registry.get(key)
    if not entry:
        return None
    if is_expired(entry):
        print(f"  WARNING: {key} file_id is expired (uploaded {entry.get('uploaded_at', 'unknown')})")
        return None
    return entry.get("file_id")


# ── Upload ─────────────────────────────────────────────────────────────────────

def upload_pdf(client, year: int, pdf_type: str, force: bool = False) -> str | None:
    """
    Upload a PDF to the Anthropic Files API and register it.
    Returns file_id on success, None on failure.
    Skips if already registered and not expired (unless force=True).
    """
    registry = load_registry()
    key = registry_key(year, pdf_type)

    # Check existing registration
    if not force:
        existing = registry.get(key)
        if existing and not is_expired(existing):
            print(f"  SKIP  {key}: already registered (file_id={existing['file_id']}, "
                  f"uploaded={existing['uploaded_at'][:10]})")
            return existing["file_id"]

    # Find PDF path
    pdf_path = ALL_KNOWN_PDFS.get((year, pdf_type))
    if not pdf_path:
        print(f"  ERROR {key}: no known path for this (year={year}, type={pdf_type})")
        return None
    if not pdf_path.exists():
        print(f"  ERROR {key}: file not found at {pdf_path}")
        return None

    file_size_mb = pdf_path.stat().st_size / 1_048_576
    print(f"  UPLOAD {key}: {pdf_path.name} ({file_size_mb:.1f} MB)...", end=" ", flush=True)

    try:
        with open(pdf_path, "rb") as f:
            response = client.beta.files.upload(
                file=(pdf_path.name, f, "application/pdf"),
            )
        file_id = response.id
        print(f"✓ {file_id}")

        registry[key] = {
            "file_id":    file_id,
            "year":       year,
            "pdf_type":   pdf_type,
            "filename":   pdf_path.name,
            "size_mb":    round(file_size_mb, 2),
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        }
        save_registry(registry)
        return file_id

    except Exception as e:
        print(f"✗ ERROR: {e}")
        return None


# ── List / check ───────────────────────────────────────────────────────────────

def list_registry() -> None:
    """Print all registered files with status."""
    registry = load_registry()
    if not registry:
        print("Registry is empty. Run --upload-all to populate.")
        return

    print(f"{'Key':<25} {'File ID':<30} {'Uploaded':<12} {'Size':>8}  Status")
    print("-" * 95)
    for key, entry in sorted(registry.items()):
        file_id = entry.get("file_id", "?")
        uploaded = entry.get("uploaded_at", "?")[:10]
        size = f"{entry.get('size_mb', 0):.1f} MB"
        status = "EXPIRED" if is_expired(entry) else "OK"
        print(f"  {key:<23} {file_id:<30} {uploaded:<12} {size:>8}  {status}")

    ok_count      = sum(1 for e in registry.values() if not is_expired(e))
    expired_count = len(registry) - ok_count
    print(f"\n  {ok_count} active, {expired_count} expired")


def check_expiry() -> None:
    """Print any expired entries that need re-uploading."""
    registry = load_registry()
    expired = [(k, e) for k, e in registry.items() if is_expired(e)]
    if not expired:
        print("No expired files — all registrations are current.")
        return
    print(f"{len(expired)} expired file(s) need re-uploading:")
    for key, entry in expired:
        print(f"  {key}: uploaded {entry.get('uploaded_at', '?')[:10]}")
    print(f"\nRe-upload with: python critique_pdf_registry.py --upload-all --force")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Manage Anthropic Files API registry for ITE PDFs")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--upload-all",    action="store_true", help="Upload all known PDFs (skips registered)")
    group.add_argument("--upload",        action="store_true", help="Upload a specific PDF (use with --year and --type)")
    group.add_argument("--list",          action="store_true", help="List all registered files")
    group.add_argument("--get",           action="store_true", help="Print file_id for a specific PDF")
    group.add_argument("--check-expiry",  action="store_true", help="Show expired registrations")
    group.add_argument("--delete",        action="store_true", help="Delete a file from Anthropic + registry")

    parser.add_argument("--year",  type=int, help="Exam year (e.g. 2022)")
    parser.add_argument("--type",  type=str, choices=["critique", "mc", "blueprint"],
                        help="PDF type: critique, mc (exam), or blueprint (score report)")
    parser.add_argument("--force", action="store_true", help="Re-upload even if already registered")

    args = parser.parse_args()

    # List and check-expiry don't need API
    if args.list:
        list_registry()
        return
    if args.check_expiry:
        check_expiry()
        return
    if args.get:
        if not args.year or not args.type:
            parser.error("--get requires --year and --type")
        fid = get_file_id(args.year, args.type)
        if fid:
            print(fid)
        else:
            print(f"No valid registration for {args.year}_{args.type}")
            sys.exit(1)
        return

    # API operations require key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    from anthropic import Anthropic
    client = Anthropic(api_key=api_key)

    if args.upload_all:
        print(f"Uploading all known PDFs ({len(ALL_KNOWN_PDFS)} files)...")
        success, skipped, failed = 0, 0, 0
        for (year, pdf_type), path in sorted(ALL_KNOWN_PDFS.items()):
            key = registry_key(year, pdf_type)
            # Check if already registered first (without --force)
            if not args.force:
                registry = load_registry()
                existing = registry.get(key)
                if existing and not is_expired(existing):
                    print(f"  SKIP  {key}: already registered")
                    skipped += 1
                    continue
            if not path.exists():
                print(f"  SKIP  {key}: file not on disk ({path.name})")
                skipped += 1
                continue
            fid = upload_pdf(client, year, pdf_type, force=args.force)
            if fid:
                success += 1
            else:
                failed += 1
        print(f"\nDone: {success} uploaded, {skipped} skipped, {failed} failed")

    elif args.upload:
        if not args.year or not args.type:
            parser.error("--upload requires --year and --type")
        upload_pdf(client, args.year, args.type, force=args.force)

    elif args.delete:
        if not args.year or not args.type:
            parser.error("--delete requires --year and --type")
        registry = load_registry()
        key = registry_key(args.year, args.type)
        entry = registry.get(key)
        if not entry:
            print(f"No registration found for {key}")
            return
        file_id = entry["file_id"]
        try:
            client.beta.files.delete(file_id)
            print(f"Deleted from Anthropic: {file_id}")
        except Exception as e:
            print(f"Warning: could not delete from Anthropic: {e}")
        del registry[key]
        save_registry(registry)
        print(f"Removed from registry: {key}")


if __name__ == "__main__":
    main()
