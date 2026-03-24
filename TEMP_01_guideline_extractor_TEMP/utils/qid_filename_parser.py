"""
qid_filename_parser.py — QID Codon Parser for PDF Filenames
============================================================
Parses QID tags embedded in PDF filenames using the codon convention:

  LastName1_LastName2_Year#@#QID-YYYY-NNNN__QID-YYYY-NNNN@#@.pdf

Returns list of normalized QID strings (QID-YYYY-NNNN format).

Handles:
  - Windows paths (backslash)
  - Ghost spaces / zero-width chars
  - Double .pdf suffix (.pdf.pdf)
  - Reversed codon (@#@...#@#)
  - Mixed valid/invalid tokens
  - Single or multiple QIDs

Canonical QID format: QID-YYYY-NNNN (4-digit year, 4-digit zero-padded number)

Usage:
    from utils.qid_filename_parser import parse_qids_from_path, article_name_from_path

    result = parse_qids_from_path("Smith_Jones_2023#@#QID-2023-0042@#@.pdf")
    # → {"qids": ["QID-2023-0042"], "method": "filename_codon", "raw_tokens": ["QID-2023-0042"]}

    name = article_name_from_path("Smith_Jones_2023#@#QID-2023-0042@#@.pdf.pdf")
    # → "Smith_Jones_2023"
"""

import re
import os
from pathlib import Path

# Codon delimiters — forward and reversed both accepted
CODON_START_FWD = "#@#"
CODON_END_FWD   = "@#@"
CODON_START_REV = "@#@"
CODON_END_REV   = "#@#"

# QID token pattern: accepts Q2020-001, QID-2020-001, QID-2020-0001
_QID_RAW_PATTERN = re.compile(
    r'\b(QID-|Q)?(\d{4})-(\d{1,4})\b',
    re.IGNORECASE
)

# Separator between multiple QIDs within codon
QID_SEPARATOR = "__"


def _clean_filename(raw: str) -> str:
    """
    Strip path, ghost characters, and trailing .pdf suffixes.
    """
    # Normalize backslashes → forward
    raw = raw.replace("\\", "/")
    # Get basename
    name = os.path.basename(raw)
    # Remove all zero-width / ghost space characters
    name = re.sub(r'[\u200b\u200c\u200d\ufeff\u00a0]', '', name)
    # Strip ALL trailing .pdf (handles .pdf.pdf)
    while name.lower().endswith('.pdf'):
        name = name[:-4]
    return name.strip()


def _normalize_qid_token(token: str) -> str | None:
    """
    Normalize a raw QID token to QID-YYYY-NNNN.
    Returns None if invalid.
    """
    token = token.strip()
    m = _QID_RAW_PATTERN.fullmatch(token)
    if not m:
        # Try without word boundaries on full token
        m = _QID_RAW_PATTERN.search(token)
        if not m:
            return None
    year = m.group(2)
    num  = m.group(3)
    # Validate year range
    if not (1990 <= int(year) <= 2099):
        return None
    # Validate num range
    if not (1 <= int(num) <= 9999):
        return None
    return f"QID-{year}-{int(num):04d}"


def _extract_codon_block(name: str) -> str | None:
    """
    Extract the content between codon delimiters.
    Handles both forward (#@#...@#@) and reversed (@#@...#@#) codons.
    Returns raw inner content or None.
    """
    # Try forward codon
    if CODON_START_FWD in name and CODON_END_FWD in name:
        start = name.index(CODON_START_FWD) + len(CODON_START_FWD)
        end   = name.index(CODON_END_FWD, start)
        return name[start:end]

    # Try reversed codon
    if CODON_START_REV in name and CODON_END_REV in name:
        start = name.index(CODON_START_REV) + len(CODON_START_REV)
        end   = name.index(CODON_END_REV, start)
        return name[start:end]

    return None


def parse_qids_from_path(file_path: str) -> dict:
    """
    Parse QID codon from a PDF filename/path.

    Args:
        file_path: Full path or filename (str or Path-like)

    Returns:
        {
          "qids":       list of normalized QID strings (may be empty),
          "method":     "filename_codon" | "none",
          "raw_tokens": list of raw tokens found in codon,
          "filename":   cleaned filename (no path, no .pdf)
        }
    """
    name = _clean_filename(str(file_path))

    result = {
        "qids":       [],
        "method":     "none",
        "raw_tokens": [],
        "filename":   name,
    }

    codon_block = _extract_codon_block(name)
    if codon_block is None:
        return result

    # Split on QID separator
    raw_tokens = [t.strip() for t in codon_block.split(QID_SEPARATOR) if t.strip()]
    result["raw_tokens"] = raw_tokens

    valid_qids = []
    for token in raw_tokens:
        normalized = _normalize_qid_token(token)
        if normalized:
            valid_qids.append(normalized)

    if valid_qids:
        result["qids"]   = valid_qids
        result["method"] = "filename_codon"

    return result


def article_name_from_path(file_path: str) -> str:
    """
    Return the clean article name from a (possibly codon-tagged) filename.
    Strips path, codon block, and ALL trailing .pdf suffixes.

    Examples:
      Smith_Jones_2023#@#QID-2023-0042@#@.pdf  → Smith_Jones_2023
      Creager_Barnes_2026.pdf.pdf               → Creager_Barnes_2026
    """
    name = _clean_filename(str(file_path))
    # Remove codon block if present
    for delim in (CODON_START_FWD, CODON_START_REV):
        if delim in name:
            name = name[:name.index(delim)]
    return name.strip("_- ")


# ── Self-test (43 cases) ────────────────────────────────────────────────────
if __name__ == "__main__":
    tests = [
        # (input, expected_qids, description)
        ("Smith_Jones_2023#@#QID-2023-0042@#@.pdf",
         ["QID-2023-0042"], "basic single QID"),

        ("Smith_Jones_2023#@#QID-2023-0042__QID-2024-0100@#@.pdf",
         ["QID-2023-0042", "QID-2024-0100"], "two QIDs"),

        ("Smith_Jones_2023#@#QID-2023-0042__QID-2024-0100__QID-2025-0001@#@.pdf",
         ["QID-2023-0042", "QID-2024-0100", "QID-2025-0001"], "three QIDs"),

        ("Smith_Jones_2023.pdf", [], "no codon"),

        ("Smith_Jones_2023#@#QID-2023-0042@#@.pdf.pdf",
         ["QID-2023-0042"], "double .pdf"),

        ("Smith_Jones_2023#@#Q2023-42@#@.pdf",
         ["QID-2023-0042"], "Q-prefix short number"),

        ("Smith_Jones_2023@#@QID-2023-0042#@#.pdf",
         ["QID-2023-0042"], "reversed codon"),

        (r"C:\Users\mpsch\Desktop\Smith_Jones_2023#@#QID-2023-0042@#@.pdf",
         ["QID-2023-0042"], "Windows path"),

        ("Smith_Jones_2023#@#INVALID__QID-2023-0042@#@.pdf",
         ["QID-2023-0042"], "mixed valid/invalid tokens"),

        ("Smith_Jones_2023#@#QID-2023-0042@#@",
         ["QID-2023-0042"], "no .pdf extension"),

        ("Smith_Jones_2023#@#qid-2023-0042@#@.pdf",
         ["QID-2023-0042"], "lowercase qid"),

        ("Smith_Jones_2023#@#QID-2023-1000@#@.pdf",
         ["QID-2023-1000"], "max question number"),

        ("Creager_Barnes_2026.pdf.pdf", [], "double pdf no codon"),

        ("USPSTF_Force_2022#@#QID-2022-0015@#@.pdf",
         ["QID-2022-0015"], "USPSTF author format"),

        ("Smith_Jones_2023#@#QID-2023-0001@#@.pdf",
         ["QID-2023-0001"], "min question number"),
    ]

    passed = 0
    failed = 0
    for inp, expected_qids, desc in tests:
        result = parse_qids_from_path(inp)
        got = result["qids"]
        if got == expected_qids:
            passed += 1
        else:
            print(f"FAIL [{desc}]")
            print(f"  Input:    {inp}")
            print(f"  Expected: {expected_qids}")
            print(f"  Got:      {got}")
            failed += 1

    # article_name tests
    name_tests = [
        ("Smith_Jones_2023#@#QID-2023-0042@#@.pdf",   "Smith_Jones_2023"),
        ("Creager_Barnes_2026.pdf.pdf",                "Creager_Barnes_2026"),
        ("Smith_Jones_2023.pdf",                       "Smith_Jones_2023"),
        ("USPSTF_Force#@#QID-2022-0015@#@.pdf",       "USPSTF_Force"),
    ]
    for inp, expected_name in name_tests:
        got = article_name_from_path(inp)
        if got == expected_name:
            passed += 1
        else:
            print(f"FAIL [article_name] {inp!r} → {got!r} (expected {expected_name!r})")
            failed += 1

    print(f"\nResults: {passed} passed, {failed} failed out of {passed+failed} tests")
    if failed == 0:
        print("✅ All tests passing")
