#!/usr/bin/env python3
"""
ITE Score Report Parser
Extracts item-level performance data from ABFM ITE score report PDFs.

Uses PyMuPDF to read text spans with RGB color metadata — no OCR or vision model needed.
Color signatures are deterministic: red bold = incorrect, green non-bold = correct.

Usage:
    from ite_parser import parse_blueprint, parse_bodysystem, merge_results

    blueprint = parse_blueprint("Blueprint_Performance.pdf", config)
    bodysystem = parse_bodysystem("BodySystem_Performance.pdf", config)
    merged = merge_results(blueprint, bodysystem)
"""

import json
import re
import sys
from pathlib import Path

import fitz  # PyMuPDF


# ---------------------------------------------------------------------------
# PDF password helper
# ---------------------------------------------------------------------------

def _find_pdf_password(pdf_path: str) -> str | None:
    """
    Look for a resident password file in the same directory as the PDF.
    Convention: XY_PDF_PASSWORD.txt  (e.g. AP_PDF_PASSWORD.txt for Adona Pjetergjoka)
    Returns the password string (whitespace-stripped), or None if no file is found.
    """
    pdf_dir = Path(pdf_path).resolve().parent
    matches = list(pdf_dir.glob("*_PDF_PASSWORD.txt"))
    if matches:
        return matches[0].read_text(encoding="utf-8").strip()
    return None


def _open_pdf(pdf_path: str) -> fitz.Document:
    """
    Open a PDF with PyMuPDF, automatically applying a resident password if the
    document is encrypted and a *_PDF_PASSWORD.txt file exists in the same folder.
    Emits a console warning if the PDF needs a password but none is found, or if
    authentication fails.
    """
    doc = fitz.open(pdf_path)
    if doc.needs_pass:
        pw = _find_pdf_password(pdf_path)
        if pw:
            if doc.authenticate(pw):
                print(f"  [OK] Password applied: {Path(pdf_path).name}")
            else:
                print(f"  WARNING: Password found but authentication failed for {Path(pdf_path).name}")
        else:
            print(
                f"  WARNING: {Path(pdf_path).name} is password-protected "
                f"but no *_PDF_PASSWORD.txt found in {Path(pdf_path).resolve().parent.name}/"
            )
    return doc


# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------

def load_config(config_path: str = None) -> dict:
    """Load parser configuration from ite_parser_config.json."""
    if config_path is None:
        config_path = Path(__file__).parent / "ite_parser_config.json"
    with open(config_path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Constants derived from config (set at parse time)
# ---------------------------------------------------------------------------

# Subcol-0 reference x for each blueprint column (observed from calibration data)
SUBCOL0_X = {
    "Acute Care": 97.8,
    "Chronic Care": 227.9,
    "Emergent/Urgent": 358.0,
    "Preventive": 488.0,
    "Foundations": 618.0,
}


# ---------------------------------------------------------------------------
# Core extraction helpers
# ---------------------------------------------------------------------------

def _rgb_from_color_int(color_int: int) -> tuple:
    """Convert PyMuPDF integer color to (R, G, B) tuple."""
    r = (color_int >> 16) & 0xFF
    g = (color_int >> 8) & 0xFF
    b = color_int & 0xFF
    return (r, g, b)


def _calc_score(y: float, config: dict) -> int:
    """Convert y-coordinate to item difficulty score using linear formula."""
    slope = config["score_axis"]["slope"]
    intercept = config["score_axis"]["intercept"]
    raw = slope * y + intercept
    return max(0, min(1000, round(raw)))


def _classify_blueprint(x: float, config: dict) -> str | None:
    """Map x-coordinate to blueprint category name."""
    for name, col in config["blueprint_columns"].items():
        if col["x_min"] <= x <= col["x_max"]:
            return name
    return None


def _classify_bodysystem(x: float, columns: dict) -> str | None:
    """Map x-coordinate to body system name."""
    for name, col in columns.items():
        if col["x_min"] <= x <= col["x_max"]:
            return name
    return None


def _calc_subcol_index(x: float, blueprint: str, config: dict) -> int:
    """Calculate subcategory column index within a blueprint category."""
    base_x = SUBCOL0_X.get(blueprint)
    if base_x is None:
        return 0
    spacing = config.get("subcol_spacing_px", 15.56)
    idx = round((x - base_x) / spacing)
    max_idx = config["blueprint_columns"][blueprint]["subcol_count"] - 1
    return max(0, min(max_idx, idx))


def _extract_deleted_items(page) -> set:
    """Extract deleted item numbers from the notes section (black text)."""
    deleted = set()
    blocks = page.get_text("dict")["blocks"]
    for block in blocks:
        if "lines" not in block:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                text = span["text"]
                rgb = _rgb_from_color_int(span["color"])
                if rgb == (0, 0, 0) and "deleted" in text.lower():
                    # Pattern: "Questions 3, 23, 25, 36, 55, 59, 129, 142, and 171 were deleted"
                    numbers = re.findall(r'\b(\d{1,3})\b', text)
                    for n in numbers:
                        deleted.add(int(n))
    return deleted


def _extract_resident_info(page) -> dict:
    """Extract resident name and ABFM ID from header text."""
    info = {"name": "", "abfm_id": "", "program": ""}
    blocks = page.get_text("dict")["blocks"]
    for block in blocks:
        if "lines" not in block:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                text = span["text"].strip()
                rgb = _rgb_from_color_int(span["color"])
                if rgb != (0, 0, 0):
                    continue
                # ABFM ID and name line
                id_match = re.search(r'ABFM ID:\s*(\d+)', text)
                if id_match:
                    info["abfm_id"] = id_match.group(1)
                name_match = re.search(r'Name:\s*(.+?)$', text)
                if name_match:
                    info["name"] = name_match.group(1).strip()
                # Program line (standalone black text that's not notes)
                if "Program" in text and "Notes" not in text:
                    info["program"] = text.replace("Program", "").strip()
    return info


def _extract_items_from_page(page, config: dict, color_correct: tuple, color_incorrect: tuple) -> list:
    """
    Extract all item spans from a single PDF page.
    Returns list of dicts with: item, correct, x, y, score, excluded_p
    """
    items = []
    blocks = page.get_text("dict")["blocks"]

    for block in blocks:
        if "lines" not in block:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                text = span["text"].strip()
                if not text:
                    continue

                rgb = _rgb_from_color_int(span["color"])

                # Only process correct/incorrect colored items
                if rgb == tuple(color_correct):
                    correct = True
                elif rgb == tuple(color_incorrect):
                    correct = False
                else:
                    continue

                # Parse item number — may have P suffix (excluded from scoring)
                excluded_p = text.endswith("P") or text.endswith("p")
                num_text = text.rstrip("Pp")

                if not num_text.isdigit():
                    continue

                item_num = int(num_text)
                x, y = span["origin"]
                score = _calc_score(y, config)

                items.append({
                    "item": item_num,
                    "correct": correct,
                    "x": round(x, 1),
                    "y": round(y, 1),
                    "score": score,
                    "excluded_p": excluded_p,
                })

    return items


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_blueprint(pdf_path: str, config: dict) -> dict:
    """
    Parse a Blueprint Performance PDF.

    Returns dict with:
        - resident: {name, abfm_id, program}
        - exam_year: str (extracted from PDF text, e.g. "2024")
        - deleted_items: [int, ...]
        - items: [{item, correct, blueprint, score, sub_col_index, x, y, excluded_p}, ...]
        - summary: {total, correct, incorrect, pct}
    """
    doc = _open_pdf(pdf_path)
    page = doc[0]  # Blueprint is always single-page

    color_correct = config["color_signatures"]["correct"]["rgb"]
    color_incorrect = config["color_signatures"]["incorrect"]["rgb"]

    # Extract exam year directly from PDF page text — reliable across all years.
    # Pattern matches "2024 Item Performance Report" in the page header.
    # Falls back to config["source_report"] (e.g. "ABFM ITE 2024") if regex misses.
    page_text = page.get_text("text")
    year_match = re.search(r'(20\d{2})\s+Item Performance Report', page_text)
    if year_match:
        exam_year = year_match.group(1)
    else:
        src = config.get("source_report", "")
        year_fallback = re.search(r'(20\d{2})', src)
        exam_year = year_fallback.group(1) if year_fallback else ""

    # Extract metadata
    resident = _extract_resident_info(page)
    deleted = _extract_deleted_items(page)

    # Extract items
    raw_items = _extract_items_from_page(page, config, color_correct, color_incorrect)
    doc.close()

    # Classify each item into blueprint column + subcol
    items = []
    for item in raw_items:
        blueprint = _classify_blueprint(item["x"], config)
        if blueprint is None:
            print(f"  WARNING: Item {item['item']} at x={item['x']} didn't map to any blueprint column", file=sys.stderr)
            continue

        sub_col_index = _calc_subcol_index(item["x"], blueprint, config)

        items.append({
            "item": item["item"],
            "correct": item["correct"],
            "blueprint": blueprint,
            "score": item["score"],
            "sub_col_index": sub_col_index,
            "x": item["x"],
            "y": item["y"],
            "excluded_p": item["excluded_p"],
        })

    # Sort by item number
    items.sort(key=lambda i: i["item"])

    correct_count = sum(1 for i in items if i["correct"])

    return {
        "resident": resident,
        "exam_year": exam_year,
        "deleted_items": sorted(deleted),
        "items": items,
        "summary": {
            "total": len(items),
            "correct": correct_count,
            "incorrect": len(items) - correct_count,
            "pct": round(correct_count / len(items) * 100, 1) if items else 0,
        },
    }


def parse_bodysystem(pdf_path: str, config: dict) -> dict:
    """
    Parse a Body System Performance PDF (may be multi-page).

    Returns dict with:
        - items: [{item, correct, body_system, score, x, y}, ...]
        - systems_found: [str, ...]
    """
    doc = _open_pdf(pdf_path)

    color_correct = config["color_signatures"]["correct"]["rgb"]
    color_incorrect = config["color_signatures"]["incorrect"]["rgb"]

    all_items = []
    systems_found = set()

    for page_idx in range(len(doc)):
        page = doc[page_idx]

        # Detect which body systems are on this page via white column headers
        page_columns = _detect_bodysystem_columns(page, config)

        if not page_columns:
            continue

        systems_found.update(page_columns.keys())

        # Extract items from this page
        raw_items = _extract_items_from_page(page, config, color_correct, color_incorrect)

        for item in raw_items:
            body_system = _classify_bodysystem(item["x"], page_columns)
            if body_system is None:
                print(f"  WARNING: Body system item {item['item']} at x={item['x']} didn't map to any system on page {page_idx}", file=sys.stderr)
                continue

            all_items.append({
                "item": item["item"],
                "correct": item["correct"],
                "body_system": body_system,
                "score": item["score"],
                "x": item["x"],
                "y": item["y"],
            })

    doc.close()

    # Sort by item number
    all_items.sort(key=lambda i: i["item"])

    return {
        "items": all_items,
        "systems_found": sorted(systems_found),
    }


def _detect_bodysystem_columns(page, config: dict) -> dict:
    """
    Detect body system columns on a page by finding white text headers.
    Returns dict mapping system_name -> {x_min, x_max, header_x}.

    Compound header handling: ABFM PDFs sometimes render a single column
    label as two adjacent white text spans (e.g. "Psychiatric/" + "Behavioral"
    instead of "Psychiatric/Behavioral"). This function merges adjacent spans
    whose concatenated text matches a known canonical system name so the column
    map stays correct and no phantom "Psychiatric" / "Behavioral" columns appear.
    """
    # Known compound headers: first part → (canonical name, expected second part)
    # Extend if ABFM introduces additional multi-word column labels.
    COMPOUND_HEADERS = {
        "Psychiatric":          ("Psychiatric/Behavioral",    "Behavioral"),
        "Psychiatric/":         ("Psychiatric/Behavioral",    "Behavioral"),
        "Injuries":             ("Injuries/Musculoskeletal",  "Musculoskeletal"),
        "Injuries/":            ("Injuries/Musculoskeletal",  "Musculoskeletal"),
        "Sexual and":           ("Sexual and Reproductive",   "Reproductive"),
        "Sexual":               ("Sexual and Reproductive",   "and Reproductive"),
        "Population-Based":     ("Population-Based Care",     "Care"),
        "Patient-Based":        ("Patient-Based Systems",     "Systems"),
        "Hematologic/":         ("Hematologic/ Immune",       "Immune"),
    }

    blocks = page.get_text("dict")["blocks"]
    headers = []

    for block in blocks:
        if "lines" not in block:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                text = span["text"].strip()
                if not text:
                    continue
                rgb = _rgb_from_color_int(span["color"])
                if rgb == (255, 255, 255):
                    x = span["origin"][0]
                    headers.append({"name": text, "x": x})

    if not headers:
        return {}

    # Sort headers by x position
    headers.sort(key=lambda h: h["x"])

    # Merge adjacent spans that together form a known compound column name.
    merged = []
    i = 0
    while i < len(headers):
        h = headers[i]
        match = COMPOUND_HEADERS.get(h["name"])
        if match and i + 1 < len(headers):
            canonical_name, expected_next = match
            next_h = headers[i + 1]
            if next_h["name"] == expected_next or next_h["name"].startswith(expected_next.split()[0]):
                # Merge: use first span's x as the header anchor
                merged.append({"name": canonical_name, "x": h["x"]})
                i += 2
                continue
        merged.append(h)
        i += 1
    headers = merged

    # Build column boundaries: midpoint between adjacent headers, with margins
    columns = {}
    page_width = config["page_dimensions"]["width"]

    for i, header in enumerate(headers):
        # Left boundary
        if i == 0:
            x_min = 50  # generous left margin
        else:
            x_min = (headers[i - 1]["x"] + header["x"]) / 2

        # Right boundary
        if i == len(headers) - 1:
            x_max = page_width - 20  # generous right margin
        else:
            x_max = (header["x"] + headers[i + 1]["x"]) / 2

        columns[header["name"]] = {
            "header_x": header["x"],
            "x_min": x_min,
            "x_max": x_max,
        }

    return columns


def merge_results(blueprint: dict, bodysystem: dict) -> dict:
    """
    Merge blueprint and body system results on item number.

    All 191 items come from the blueprint PDF (with blueprint category).
    Items that also appear in the body system PDF get a body_system field.
    Cross-report validation: correct/incorrect must agree where items overlap.
    """
    # Build body system lookup
    bs_lookup = {}
    for item in bodysystem["items"]:
        bs_lookup[item["item"]] = item

    merged = []
    mismatches = []

    for bp_item in blueprint["items"]:
        item_num = bp_item["item"]
        entry = {
            "item": item_num,
            "correct": bp_item["correct"],
            "blueprint": bp_item["blueprint"],
            "body_system": None,
            "score": bp_item["score"],
            "sub_col_index": bp_item["sub_col_index"],
            "x": bp_item["x"],
            "y": bp_item["y"],
            "excluded_p": bp_item["excluded_p"],
        }

        if item_num in bs_lookup:
            bs_item = bs_lookup[item_num]
            entry["body_system"] = bs_item["body_system"]

            # Cross-report validation
            if bp_item["correct"] != bs_item["correct"]:
                mismatches.append(item_num)

        merged.append(entry)

    return {
        "resident": blueprint["resident"],
        "exam_year": blueprint.get("exam_year", ""),
        "deleted_items": blueprint["deleted_items"],
        "items": merged,
        "summary": blueprint["summary"],
        "body_systems_found": bodysystem.get("systems_found", []),
        "cross_report_overlap": len(bs_lookup),
        "cross_report_mismatches": mismatches,
    }


def parse_score_report(pdf_path: str) -> dict:
    """
    Parse the ABFM ITE Overall Score Report PDF (the summary report, not the item grids).

    The score report is a 2-page PDF:
        - Page 1: Instructions text (skipped)
        - Page 2: Data table with header + blueprint + body system sections

    Returns dict with:
        abfm_id, name, exam_year,
        scaled_score (actual ABFM value),
        standard_error, mps (380), vs_mps,
        pgy_level, pgy_mean_scaled, vs_pgy_mean,
        unanswered_items,
        blueprint_scaled: {category: {scaled, se, blueprint_pct}},
        body_system_scaled: {system: {scaled, se}}

    Raises ValueError if the PDF is not a recognizable score report.
    """
    doc = _open_pdf(pdf_path)

    if len(doc) < 2:
        raise ValueError(
            f"Score report should be 2 pages (instructions + data), found {len(doc)}. "
            f"Make sure you're passing the Score Report PDF, not the Blueprint or Body System PDF."
        )

    page = doc[1]  # page index 1 = page 2 (data page)
    text = page.get_text("text")
    doc.close()

    # Sanity check — score report has "Scaled Score:" in the header
    if "Scaled Score:" not in text:
        raise ValueError(
            "This PDF doesn't look like an ITE Score Report (no 'Scaled Score:' found on page 2). "
            "Check that you're passing the correct file."
        )

    MPS = 380  # constant — ABFM minimum passing standard

    result = {
        "abfm_id":           None,
        "name":              None,
        "exam_year":         None,
        "scaled_score":      None,
        "standard_error":    None,
        "mps":               MPS,
        "vs_mps":            None,
        "pgy_level":         None,
        "pgy_mean_scaled":   None,
        "vs_pgy_mean":       None,
        "unanswered_items":  0,
        "blueprint_scaled":  {},
        "body_system_scaled": {},
    }

    # --- Header fields ---
    m = re.search(r'ABFM ID:\s*(\d+)', text)
    if m:
        result["abfm_id"] = m.group(1)

    m = re.search(r'Scaled Score:\s*(\d+)', text)
    if m:
        result["scaled_score"] = int(m.group(1))

    m = re.search(r'Mean Scaled Score for PGY(\d+):\s*(\d+)', text)
    if m:
        result["pgy_level"]       = int(m.group(1))
        result["pgy_mean_scaled"] = int(m.group(2))

    m = re.search(r'Number of Unanswered Items:\s*(\d+)', text)
    if m:
        result["unanswered_items"] = int(m.group(1))

    # Exam year from page header ("2024 In-Training Examination")
    m = re.search(r'(\d{4})\s+In-Training Examination', text)
    if m:
        result["exam_year"] = m.group(1)

    # Resident name — "Firstname Lastname, M.D." pattern
    m = re.search(r'\n([A-Z][^,\n]+,\s*M\.D\.)', text)
    if m:
        result["name"] = m.group(1).strip()

    # Overall SE — "Overall Performance 100% 500 ±38" or "Overall Performance 500 ±38"
    m = re.search(r'Overall Performance\s+(?:\d+%\s+)?\d+\s+[±+](\d+)', text)
    if m:
        result["standard_error"] = int(m.group(1))

    # Derived fields
    if result["scaled_score"] is not None:
        result["vs_mps"] = result["scaled_score"] - MPS
    if result["scaled_score"] is not None and result["pgy_mean_scaled"] is not None:
        result["vs_pgy_mean"] = result["scaled_score"] - result["pgy_mean_scaled"]

    # --- Blueprint category rows ---
    # Format: "Category Name    35%    490    ±61"
    # Anchored to the canonical 5 category strings (avoids false matches)
    BP_CATEGORIES = (
        "Acute Care and Diagnosis",
        "Chronic Care Management",
        "Emergent and Urgent Care",
        "Preventive Care",
        "Foundations of Care",
    )
    bp_pat = re.compile(
        r'(' + '|'.join(re.escape(c) for c in BP_CATEGORIES) + r')'
        r'\s+(\d+)%\s+(\d+)\s+[±+](\d+)',
        re.IGNORECASE
    )
    for m in bp_pat.finditer(text):
        result["blueprint_scaled"][m.group(1)] = {
            "blueprint_pct": int(m.group(2)),
            "scaled":        int(m.group(3)),
            "se":            int(m.group(4)),
        }

    # --- Body system rows ---
    # Format: "System Name    560    ±137" (no blueprint % column)
    # Covers all known system names including 2024 variants
    BS_SYSTEMS = (
        "Cardiovascular", "Injuries/Musculoskeletal", "Musculoskeletal",
        "Respiratory", "Psychiatric/Behavioral", "Psychogenic",  # Psychogenic kept as alias for pre-2024 PDFs
        "Sexual and Reproductive", "Reproductive: Female", "Reproductive: Male",
        "Endocrine", "Gastrointestinal", "Population-Based Care", "Nonspecific",
        "Integumentary", "Patient-Based Systems", "Neurologic", "Nephrologic",
        "Hematologic/ Immune", "Hematologic/Immune", "Special Sensory",
    )
    bs_pat = re.compile(
        r'(' + '|'.join(re.escape(s) for s in BS_SYSTEMS) + r')'
        r'\s+(\d+)\s+[±+](\d+)',
        re.IGNORECASE
    )
    for m in bs_pat.finditer(text):
        result["body_system_scaled"][m.group(1)] = {
            "scaled": int(m.group(2)),
            "se":     int(m.group(3)),
        }

    return result


def export_json(data: dict, output_path: str):
    """Write parsed results to JSON file."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Exported: {output_path}")


# ---------------------------------------------------------------------------
# CLI entry point (standalone usage)
# ---------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Parse ABFM ITE score report PDFs")
    parser.add_argument("--blueprint", required=True, help="Path to Blueprint Performance PDF")
    parser.add_argument("--bodysystem", help="Path to Body System Performance PDF")
    parser.add_argument("--config", help="Path to ite_parser_config.json")
    parser.add_argument("--output", default="parsed_results.json", help="Output JSON path")
    args = parser.parse_args()

    config = load_config(args.config)

    print(f"Parsing blueprint: {args.blueprint}")
    blueprint = parse_blueprint(args.blueprint, config)
    print(f"  Items extracted: {blueprint['summary']['total']}")
    print(f"  Correct: {blueprint['summary']['correct']} ({blueprint['summary']['pct']}%)")
    print(f"  Deleted items: {blueprint['deleted_items']}")

    if args.bodysystem:
        print(f"\nParsing body system: {args.bodysystem}")
        bodysystem = parse_bodysystem(args.bodysystem, config)
        print(f"  Items extracted: {len(bodysystem['items'])}")
        print(f"  Systems found: {bodysystem['systems_found']}")

        print("\nMerging results...")
        result = merge_results(blueprint, bodysystem)
        print(f"  Cross-report overlap: {result['cross_report_overlap']} items")
        if result["cross_report_mismatches"]:
            print(f"  WARNING: Mismatches on items: {result['cross_report_mismatches']}")
        else:
            print("  Cross-report validation: PASS (all overlapping items agree)")
    else:
        result = {
            "resident": blueprint["resident"],
            "exam_year": blueprint.get("exam_year", ""),
            "deleted_items": blueprint["deleted_items"],
            "items": [{**i, "body_system": None} for i in blueprint["items"]],
            "summary": blueprint["summary"],
        }

    export_json(result, args.output)
    print(f"\nResident: {result['resident']['name']} (ABFM ID: {result['resident']['abfm_id']})")


if __name__ == "__main__":
    main()
