"""
pre_scan.py — Master library pre-flight scanner for guideline_extractor_v2

Scans a directory and classifies every file as:
  INGEST   — recognized prefix + PDF format, safe to run
  SKIP     — image file (.png/.jpg/.gif), no text to extract
  REVIEW   — unrecognized naming pattern, needs human review before ingest

Recognized prefixes (map to known journal/society sources):
  afp_, aafp_, acg_, ajkd_, apa_, gina_, hep_, idsa_, jacc_,
  neuro_, peds_, pulm_, rheum_, tox_, uspstf_, va_dod_

Usage:
  py -3.12 pre_scan.py --dir <path_to_folder>
  py -3.12 pre_scan.py --dir <path_to_folder> --recursive
  py -3.12 pre_scan.py --dir <path_to_folder> --copy-ingest <dest_dir>
"""

from __future__ import annotations
import argparse
import json
import os
import shutil

# ── Recognized source prefixes ──────────────────────────────────────────────
KNOWN_PREFIXES = [
    "afp_", "aafp_",        # American Family Physician
    "acg_",                  # American College of Gastroenterology
    "ajkd_",                 # American Journal of Kidney Diseases
    "apa_",                  # American Psychiatric Association
    "gina_",                 # Global Initiative for Asthma
    "hep_",                  # Hepatology journals
    "idsa_",                 # Infectious Disease Society of America
    "jacc_",                 # Journal of the American College of Cardiology
    "neuro_",                # Neurology journals
    "peds_", "ped_",         # Pediatrics journals
    "pulm_",                 # Pulmonology journals
    "rheum_",                # Rheumatology journals
    "tox_",                  # Toxicology / drug reference
    "uspstf_",               # US Preventive Services Task Force
    "va_dod_",               # VA/DoD clinical guidelines
    "endo_",                 # Endocrinology journals
    "nejm",                  # New England Journal of Medicine
    "acog_",                 # American College of OB/GYN
    "who_",                  # World Health Organization
    "ada_",                  # American Diabetes Association
    "periop_",               # Perioperative management guidelines
    "sluhn_",                # Institution-specific (flagged separately)
]

# Prefixes that are recognized but warrant a note
INSTITUTION_PREFIXES = ["sluhn_"]

# Entire folders to skip regardless of file contents (visual flowcharts, etc.)
EXCLUDED_FOLDERS = [
    "life_support_alogos",   # ACLS/BLS/PALS visual flowchart PDFs -- no extractable prose
]

# Specific filenames to skip (visual algorithms, reference tables, antibiograms)
EXCLUDED_FILES = [
    "sluhn_culture_guidelines.pdf",                      # Institution antibiogram
    "ada_standards-of-care-2025.pdf",                    # 35MB -- too large, exceeds pipeline scope
    "2024 ada injectable intensification algorithm.pdf", # Visual flowchart
    "aace_2019_diabetes_algorithm_03.2021.pdf",          # Visual algorithm, image-heavy
    "asthma clinicians at-a-glance 508_02-03-21.pdf",   # Summary reference sheet
    "backpainpcp_treatment_algorithm.pdf",               # Visual flowchart
    "vaccineschedule_uptodate_24.pdf",                   # CDC schedule table
    "vaccine_catch-up_4mo-6y_uptodate_24.pdf",          # CDC schedule table
    "vaccine_catch-up_7-18yo_uptodate_24.pdf",          # CDC schedule table
]

# Image extensions — always skip
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp"}

# Supported document extensions
DOC_EXTENSIONS = {".pdf", ".txt", ".md"}


def classify_file(fname: str) -> tuple[str, str]:
    """
    Returns (status, reason) where status is INGEST / SKIP / REVIEW.
    """
    ext = os.path.splitext(fname)[1].lower()
    lower = fname.lower()

    # Specific excluded filenames
    if lower in EXCLUDED_FILES:
        return "SKIP", "excluded file -- visual algorithm/table/reference sheet"

    # Images -- always skip
    if ext in IMAGE_EXTENSIONS:
        return "SKIP", "image file -- no text extractable"

    # Non-document extensions
    if ext not in DOC_EXTENSIONS:
        return "REVIEW", f"unsupported extension '{ext}'"

    # Check known prefixes
    for prefix in KNOWN_PREFIXES:
        if lower.startswith(prefix):
            if prefix in INSTITUTION_PREFIXES:
                return "REVIEW", f"institution-specific source (prefix: {prefix}) — verify format before ingest"
            return "INGEST", f"recognized prefix '{prefix}'"

    # PDF but unrecognized prefix — flag for review
    if ext == ".pdf":
        return "REVIEW", "PDF with unrecognized naming pattern — verify content type before ingest"

    return "REVIEW", "unrecognized file — manual check required"


def scan_directory(root: str, recursive: bool = False) -> list[dict]:
    results = []

    def process_file(fname: str, full_path: str, rel_path: str):
        # Check if any parent folder is in the excluded list
        parts = rel_path.replace("\\", "/").split("/")
        for part in parts[:-1]:  # all but the filename itself
            if part in EXCLUDED_FOLDERS:
                size = os.path.getsize(full_path)
                results.append({
                    "file": rel_path, "fname": fname, "full_path": full_path,
                    "status": "SKIP",
                    "reason": f"excluded folder '{part}'",
                    "size_kb": round(size / 1024, 1),
                })
                return
        status, reason = classify_file(fname)
        size = os.path.getsize(full_path)
        results.append({
            "file": rel_path, "fname": fname, "full_path": full_path,
            "status": status, "reason": reason,
            "size_kb": round(size / 1024, 1),
        })

    if recursive:
        for dirpath, _, filenames in os.walk(root):
            for fname in sorted(filenames):
                full_path = os.path.join(dirpath, fname)
                rel_path = os.path.relpath(full_path, root)
                process_file(fname, full_path, rel_path)
    else:
        for fname in sorted(os.listdir(root)):
            full_path = os.path.join(root, fname)
            if not os.path.isfile(full_path):
                continue
            process_file(fname, full_path, fname)

    return results


def print_report(results: list[dict], show_all: bool = False) -> None:
    ingest  = [r for r in results if r["status"] == "INGEST"]
    skip    = [r for r in results if r["status"] == "SKIP"]
    review  = [r for r in results if r["status"] == "REVIEW"]

    total_ingest_mb = sum(r["size_kb"] for r in ingest) / 1024

    print(f"\n{'='*65}")
    print(f"  PRE-SCAN REPORT")
    print(f"{'='*65}")
    print(f"  Total files scanned : {len(results)}")
    print(f"  INGEST              : {len(ingest)}  ({total_ingest_mb:.1f} MB)")
    print(f"  SKIP                : {len(skip)}")
    print(f"  REVIEW              : {len(review)}")
    print(f"{'='*65}")

    if review:
        print(f"\n{'-'*65}")
        print(f"  [!] REVIEW REQUIRED ({len(review)} files)")
        print(f"{'-'*65}")
        for r in review:
            print(f"  {r['file']:<50} {r['size_kb']:>8.1f} KB")
            print(f"    -> {r['reason']}")

    if skip:
        print(f"\n{'-'*65}")
        print(f"  [x] SKIPPED ({len(skip)} files -- images/unsupported)")
        print(f"{'-'*65}")
        for r in skip:
            print(f"  {r['file']}")

    if show_all and ingest:
        print(f"\n{'-'*65}")
        print(f"  [+] INGEST QUEUE ({len(ingest)} files)")
        print(f"{'-'*65}")
        for r in ingest:
            print(f"  {r['file']:<50} {r['size_kb']:>8.1f} KB")

    print(f"\n{'='*65}\n")


def copy_ingest_files(results: list[dict], dest_dir: str) -> None:
    ingest = [r for r in results if r["status"] == "INGEST"]
    os.makedirs(dest_dir, exist_ok=True)
    copied = 0
    skipped = 0
    for r in ingest:
        dest_path = os.path.join(dest_dir, r["fname"])
        if os.path.exists(dest_path):
            skipped += 1
            continue
        shutil.copy2(r["full_path"], dest_path)
        copied += 1
    print(f"  Copied {copied} files to {dest_dir}  ({skipped} already existed, skipped)")


def write_scan_report(results: list[dict], out_path: str) -> None:
    summary = {
        "total": len(results),
        "ingest": len([r for r in results if r["status"] == "INGEST"]),
        "skip":   len([r for r in results if r["status"] == "SKIP"]),
        "review": len([r for r in results if r["status"] == "REVIEW"]),
        "files": results,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"  Scan report written: {out_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Pre-scan clinical guideline library before ingest"
    )
    parser.add_argument("--dir", required=True, help="Directory to scan")
    parser.add_argument("--recursive", action="store_true", help="Scan subdirectories recursively")
    parser.add_argument("--show-ingest", action="store_true", help="Print full INGEST list in report")
    parser.add_argument("--copy-ingest", type=str, default=None,
                        help="Copy all INGEST files to this destination directory")
    parser.add_argument("--save-report", type=str, default=None,
                        help="Save scan results to this JSON file")
    args = parser.parse_args()

    if not os.path.isdir(args.dir):
        print(f"ERROR: Directory not found: {args.dir}")
        return

    print(f"  Scanning: {args.dir}{'  (recursive)' if args.recursive else ''}")
    results = scan_directory(args.dir, recursive=args.recursive)
    print_report(results, show_all=args.show_ingest)

    if args.copy_ingest:
        copy_ingest_files(results, args.copy_ingest)

    if args.save_report:
        write_scan_report(results, args.save_report)


if __name__ == "__main__":
    main()
