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
        - deleted_items: [int, ...]
        - items: [{item, correct, blueprint, score, sub_col_index, x, y, excluded_p}, ...]
        - summary: {total, correct, incorrect, pct}
    """
    doc = fitz.open(pdf_path)
    page = doc[0]  # Blueprint is always single-page

    color_correct = config["color_signatures"]["correct"]["rgb"]
    color_incorrect = config["color_signatures"]["incorrect"]["rgb"]

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
        "exam_year": config.get("source_report", "").split()[-1] if config.get("source_report") else "",
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
    doc = fitz.open(pdf_path)

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
    """
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
