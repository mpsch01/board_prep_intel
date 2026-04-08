#!/usr/bin/env python3
"""
check_no_emails.py — Pre-commit guardrail
Scans tracked files for hard-coded personal email addresses.
Run before committing:  python check_no_emails.py

Exit code 0 = clean, 1 = email found.
"""

import re
import subprocess
import sys

# Exact strings to block
BLOCKED_STRINGS = [
    "scholl.michael.p@gmail.com",
]

# Files to skip (this script itself, and binary extensions)
SKIP_EXTENSIONS = {".db", ".pdf", ".png", ".jpg", ".xlsx", ".docx", ".pptx", ".zip", ".tar", ".gz"}
SKIP_FILES = {"check_no_emails.py"}


def get_tracked_files():
    """Get list of git-tracked files."""
    result = subprocess.run(
        ["git", "ls-files"], capture_output=True, text=True, cwd="."
    )
    return result.stdout.strip().split("\n") if result.stdout.strip() else []


def main():
    files = get_tracked_files()
    violations = []

    for filepath in files:
        # Skip binaries and self
        if any(filepath.endswith(ext) for ext in SKIP_EXTENSIONS):
            continue
        if filepath.split("/")[-1] in SKIP_FILES:
            continue

        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                for lineno, line in enumerate(f, 1):
                    for blocked in BLOCKED_STRINGS:
                        if blocked in line:
                            violations.append((filepath, lineno, blocked, line.strip()[:120]))
        except (OSError, IsADirectoryError):
            continue

    if violations:
        print(f"BLOCKED: Found {len(violations)} hard-coded email occurrence(s):\n")
        for path, lineno, email, preview in violations:
            print(f"  {path}:{lineno}  [{email}]")
            print(f"    {preview}\n")
        print("Fix: use os.environ.get('ITE_CONTACT_EMAIL', '') instead.")
        return 1
    else:
        print("OK: No hard-coded emails found in tracked files.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
