"""
ab_test.py
==========
A/B test: compare extraction quality between baseline (pre-calibration)
prompts and the updated (calibration v1) prompts on a single document.

Uses the already-migrated unified_v1.0 JSON as the "before" result.
Re-extracts the same PDF with updated prompts as the "after" result.
Scores both and reports the delta.

USAGE:
  python ab_test.py                          # tests doc 4 (hypertension) by default
  python ab_test.py --pdf documents/gold_list/7.pdf   # test croup
  python ab_test.py --pdf documents/gold_list/17.pdf  # test IDSA rhinosinusitis (large)
  python ab_test.py --list                   # show all available gold_list docs
"""

from __future__ import annotations
import argparse
import json
import os
import sys
import datetime

# Allow imports from project root
sys.path.insert(0, os.path.dirname(__file__))

from utils.preprocess import preprocess
from utils.prompt_builder import llm_extract
from calibration import score_document


# ── Paths ──────────────────────────────────────────────────────────────────

BASE = os.path.dirname(__file__)
GOLD_LIST_DIR    = os.path.join(BASE, "documents", "gold_list")
BASELINE_DIR     = os.path.join(BASE, "outputs", "gold_list_v23_baseline")
UNIFIED_JSON_DIR = r"C:\Users\mpsch\Desktop\claude_knowledge\board_prep\ite_refs\04_outputs\ingested\json"
MANIFEST_PATH    = r"C:\Users\mpsch\Desktop\claude_knowledge\board_prep\ite_refs\04_outputs\ingested\manifest.json"
AB_RESULTS_DIR   = os.path.join(BASE, "outputs", "ab_test")


# ── Helpers ────────────────────────────────────────────────────────────────

def load_manifest() -> dict:
    """Returns dict: pdf_basename -> manifest entry."""
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        entries = json.load(f)
    return {os.path.basename(e["pdf"]): e for e in entries}


def find_unified_json(pdf_basename: str, manifest: dict) -> str | None:
    """Find the unified_v1.0 JSON path for a given PDF filename."""
    entry = manifest.get(pdf_basename)
    if not entry:
        return None
    slug = os.path.basename(entry["json"])
    path = os.path.join(UNIFIED_JSON_DIR, slug)
    return path if os.path.exists(path) else None


def load_unified_doc(json_path: str) -> dict:
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def unified_doc_to_score_input(doc: dict) -> dict:
    """
    calibration.score_document expects the full unified_v1.0 structure.
    The baseline JSONs ARE unified_v1.0 — pass through directly.
    """
    return doc


def extraction_to_unified_shell(extraction: dict, doc_type: str, engine_name: str, title: str) -> dict:
    """
    Wrap a raw extraction result in minimal unified_v1.0 structure
    so calibration.score_document can score it.
    """
    return {
        "source": {"source_id": "AB-TEST", "title": title},
        "classification": {
            "document_type": doc_type,
            "engine_used": engine_name,
            "confidence": 1.0
        },
        "extraction": extraction,
        "metadata": {"schema_version": "unified_v1.0", "field_coverage_score": 0.0},
        "governance": {}
    }


# ── Scoring delta display ──────────────────────────────────────────────────

def print_delta(before_scores: dict, after_scores: dict, title: str):
    qs_b = before_scores["quality_scores"]
    qs_a = after_scores["quality_scores"]

    print(f"\n  {'='*65}")
    print(f"  A/B TEST RESULTS: {title[:55]}")
    print(f"  {'='*65}")
    print(f"  {'Dimension':<22} {'Before':>8} {'After':>8} {'Delta':>8}")
    print(f"  {'-'*22} {'-'*8} {'-'*8} {'-'*8}")

    dims = [
        ("Overall",         "overall"),
        ("Recommendations", "recommendations"),
        ("Thresholds",      "thresholds"),
        ("Population",      "population"),
        ("Summary",         "summary"),
    ]
    if qs_b["medications"]["count"] > 0 or qs_a["medications"]["count"] > 0:
        dims.append(("Medications", "medications"))

    for label, key in dims:
        b = qs_b[key]["score"] if isinstance(qs_b[key], dict) else qs_b[key]
        a = qs_a[key]["score"] if isinstance(qs_a[key], dict) else qs_a[key]
        delta = a - b
        sign  = "+" if delta > 0 else ""
        flag  = " <<" if abs(delta) >= 0.05 else ""
        print(f"  {label:<22} {b:>8.3f} {a:>8.3f} {sign}{delta:>7.3f}{flag}")

    # Sub-metrics for recs and thresholds
    print(f"\n  Sub-metrics:")
    sub_pairs = [
        ("rec strength_rate",  qs_b["recommendations"]["strength_rate"],  qs_a["recommendations"]["strength_rate"]),
        ("rec evidence_rate",  qs_b["recommendations"]["evidence_rate"],   qs_a["recommendations"]["evidence_rate"]),
        ("thr unit_rate",      qs_b["thresholds"]["unit_rate"],            qs_a["thresholds"]["unit_rate"]),
        ("thr context_rate",   qs_b["thresholds"]["context_rate"],         qs_a["thresholds"]["context_rate"]),
        ("thr specific_rate",  qs_b["thresholds"]["specific_rate"],        qs_a["thresholds"]["specific_rate"]),
    ]
    for label, b, a in sub_pairs:
        delta = a - b
        sign  = "+" if delta > 0 else ""
        flag  = " <<" if abs(delta) >= 0.05 else ""
        print(f"  {label:<22} {b:>8.1%} {a:>8.1%} {sign}{delta*100:>6.1f}pp{flag}")

    print(f"\n  Counts (before / after):")
    print(f"  {'Recommendations':<22} {qs_b['recommendations']['count']:>8} {qs_a['recommendations']['count']:>8}")
    print(f"  {'Thresholds':<22} {qs_b['thresholds']['count']:>8} {qs_a['thresholds']['count']:>8}")
    print(f"  {'Medications':<22} {qs_b['medications']['count']:>8} {qs_a['medications']['count']:>8}")
    print(f"  {'='*65}\n")


# ── Main A/B logic ─────────────────────────────────────────────────────────

def run_ab_test(pdf_path: str):
    pdf_basename = os.path.basename(pdf_path)
    print(f"\n  A/B test: {pdf_basename}")

    # ── Load manifest and find matching unified JSON ──
    manifest = load_manifest()
    json_path = find_unified_json(pdf_basename, manifest)
    if not json_path:
        print(f"  [ERROR] No unified_v1.0 JSON found for {pdf_basename}")
        print(f"  Available PDFs in manifest: {sorted(manifest.keys())}")
        sys.exit(1)

    entry = manifest[pdf_basename]
    title = entry.get("title", pdf_basename)
    print(f"  Title:     {title}")
    print(f"  JSON:      {os.path.basename(json_path)}\n")

    # ── BEFORE: load existing unified_v1.0 (baseline) ──
    print("  [BEFORE] Loading baseline unified_v1.0 result...")
    before_doc = load_unified_doc(json_path)
    doc_type    = before_doc.get("classification", {}).get("document_type", "unknown")
    engine_name = before_doc.get("classification", {}).get("engine_used", "unknown")
    before_scores = score_document(before_doc)
    print(f"  Engine: {engine_name}  |  Doc type: {doc_type}")
    print(f"  Before overall quality: {before_scores['quality_scores']['overall']:.3f}")

    # ── AFTER: re-extract with updated prompts ──
    print(f"\n  [AFTER]  Re-extracting {pdf_basename} with calibration v1 prompts...")
    if not os.path.exists(pdf_path):
        print(f"  [ERROR] PDF not found: {pdf_path}")
        sys.exit(1)

    doc_text = preprocess(pdf_path)
    if not doc_text or len(doc_text) < 100:
        print(f"  [ERROR] Could not extract text from {pdf_path}")
        sys.exit(1)

    print(f"  Extracted {len(doc_text):,} chars. Running {engine_name}...")
    after_extraction = llm_extract(doc_text, doc_type)
    after_doc = extraction_to_unified_shell(after_extraction, doc_type, engine_name, title)
    after_scores = score_document(after_doc)
    print(f"  After overall quality:  {after_scores['quality_scores']['overall']:.3f}")

    # ── Print delta ──
    print_delta(before_scores, after_scores, title)

    # ── Save results ──
    os.makedirs(AB_RESULTS_DIR, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = pdf_basename.replace(".pdf", "")
    result_path = os.path.join(AB_RESULTS_DIR, f"ab_{stem}_{timestamp}.json")

    result = {
        "ab_test_timestamp": datetime.datetime.now().isoformat(),
        "pdf": pdf_basename,
        "title": title,
        "doc_type": doc_type,
        "engine": engine_name,
        "before_scores": before_scores["quality_scores"],
        "after_scores": after_scores["quality_scores"],
        "delta_overall": round(
            after_scores["quality_scores"]["overall"] - before_scores["quality_scores"]["overall"], 3
        ),
        "after_extraction": after_extraction,
    }

    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"  Result saved: {result_path}\n")

    return result


def list_available():
    manifest = load_manifest()
    print(f"\n  Available gold_list PDFs for A/B testing:\n")
    for pdf_name, entry in sorted(manifest.items()):
        print(f"  {pdf_name:<12}  {entry.get('title', '')[:60]}")
    print()


# ── CLI ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="A/B test: compare pre- vs post-calibration extraction quality on one document"
    )
    parser.add_argument(
        "--pdf", default=os.path.join(GOLD_LIST_DIR, "4.pdf"),
        help="Path to PDF to test (default: 4.pdf — Managing Hypertension)"
    )
    parser.add_argument(
        "--list", action="store_true",
        help="List available gold_list PDFs and exit"
    )
    args = parser.parse_args()

    if args.list:
        list_available()
        return

    run_ab_test(args.pdf)


if __name__ == "__main__":
    main()
