"""
test_v23_pipeline.py — Step-through test of guideline_extractor_v2.3 pipeline

Runs each pipeline step individually and dumps output between steps
so you can see exactly what each stage produces.

Usage:
  py -3.12 test_v23_pipeline.py --file "path\to\Some_Article_2022#@#ART-0123@#@.pdf"

  # Or use a shorthand — just the codon PDF folder + filename:
  py -3.12 test_v23_pipeline.py --file "..\..\clinical_guidelines\01_pdf_guideline_library\pdf_codon\Gaitonde_Moore_2019#@#ART-0470@#@.pdf"

Output:
  - Prints each step's output to console with clear separators
  - Saves full result to outputs/test_v23_extraction.json
  - Saves step-by-step log to outputs/test_v23_step_log.json

Cost: ~3 Claude API calls (~$0.03 total)
"""

from __future__ import annotations
import argparse
import json
import os
import sys
import time

# ── Ensure imports work from project root ────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from utils.preprocess import preprocess
from utils.prompt_builder import extract_metadata, llm_screen
from utils.validator import validate_output
from utils.qid_filename_parser import parse_qids_from_path
from core.screening import screening_classifier, _prescreen_rct
from core.routing import route_document


def separator(title: str) -> None:
    print(f"\n{'='*70}")
    print(f"  STEP: {title}")
    print(f"{'='*70}\n")


def pause(msg: str = "Press ENTER to continue to next step...") -> None:
    input(f"\n  >>> {msg}")


def main():
    parser = argparse.ArgumentParser(
        description="Step-through test of guideline_extractor_v2.3 pipeline"
    )
    parser.add_argument("--file", required=True, help="Path to a PDF file")
    parser.add_argument("--no-pause", action="store_true",
                        help="Run all steps without pausing")
    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"ERROR: File not found: {args.file}")
        sys.exit(1)

    out_dir = os.path.join(SCRIPT_DIR, "outputs")
    os.makedirs(out_dir, exist_ok=True)

    step_log = {
        "file": os.path.basename(args.file),
        "file_path": os.path.abspath(args.file),
        "steps": {}
    }

    print(f"\n{'#'*70}")
    print(f"  GUIDELINE EXTRACTOR v2.3 — STEP-THROUGH TEST")
    print(f"  File: {os.path.basename(args.file)}")
    print(f"{'#'*70}")

    # ── STEP 1: Preprocess (PDF → raw text) ──────────────────────────────
    separator("1. PREPROCESS (PDF → raw text)")
    print("  No API call — local pdfplumber extraction + text cleanup")

    t0 = time.time()
    text = preprocess(args.file)
    elapsed = time.time() - t0

    print(f"\n  Total characters: {len(text):,}")
    print(f"  Total lines:      {len(text.splitlines()):,}")
    print(f"  Time:             {elapsed:.2f}s")
    print(f"  Chunked?          {'YES (>{0:,} chars)'.format(15000) if len(text) > 15000 else 'No (single pass)'}")
    print(f"\n  --- First 800 chars ---")
    print(text[:800])
    print(f"\n  --- Last 300 chars ---")
    print(text[-300:])

    step_log["steps"]["1_preprocess"] = {
        "total_chars": len(text),
        "total_lines": len(text.splitlines()),
        "elapsed_sec": round(elapsed, 2),
        "first_500": text[:500],
    }

    if not args.no_pause:
        pause()

    # ── STEP 2: Metadata Extraction (Claude API call #1) ─────────────────
    separator("2. METADATA EXTRACTION (Claude API call #1)")
    print("  Sends first 2000 chars → Claude → title, org, year, doi")

    t0 = time.time()
    meta = extract_metadata(text)
    elapsed = time.time() - t0

    print(f"\n  Result ({elapsed:.2f}s):")
    for k, v in meta.items():
        print(f"    {k}: {v}")

    step_log["steps"]["2_metadata"] = {
        "result": meta,
        "elapsed_sec": round(elapsed, 2),
    }

    if not args.no_pause:
        pause()

    # ── STEP 3: Screening / Classification (Claude API call #2) ──────────
    separator("3. SCREENING CLASSIFIER (Claude API call #2)")
    print("  Sends first 5000 chars → Claude → document_type, confidence, signals")
    print(f"  RCT pre-screen heuristic: ", end="")

    rct_prescreen = _prescreen_rct(text[:5000])
    print(f"{'TRIGGERED (skipping LLM call)' if rct_prescreen else 'not triggered (using LLM)'}")

    t0 = time.time()
    screening_result = screening_classifier(text)
    elapsed = time.time() - t0

    print(f"\n  Result ({elapsed:.2f}s):")
    print(f"    document_type:             {screening_result['document_type']}")
    print(f"    confidence:                {screening_result['confidence']}")
    print(f"    signals:                   {screening_result['signals']}")
    print(f"    body_systems:              {screening_result['body_systems']}")
    print(f"    numeric_threshold_present: {screening_result.get('numeric_threshold_present', 'N/A')}")

    step_log["steps"]["3_screening"] = {
        "rct_prescreen_triggered": rct_prescreen,
        "result": screening_result,
        "elapsed_sec": round(elapsed, 2),
    }

    if not args.no_pause:
        pause()

    # ── STEP 4: Engine Routing (no API call) ─────────────────────────────
    separator("4. ENGINE ROUTING (no API call)")
    print("  Maps document_type → engine class → activates extraction modules")

    engine = route_document(screening_result)
    engine.activate_modules()

    print(f"\n    document_type:   {screening_result['document_type']}")
    print(f"    engine_class:    {engine.__class__.__name__}")
    print(f"    DOCUMENT_TYPE:   {engine.DOCUMENT_TYPE}")
    print(f"    modules:         {engine.modules}")

    step_log["steps"]["4_routing"] = {
        "engine_class": engine.__class__.__name__,
        "document_type": engine.DOCUMENT_TYPE,
        "modules_activated": engine.modules,
    }

    if not args.no_pause:
        pause()

    # ── STEP 5: Full Extraction (Claude API call #3 — the big one) ───────
    separator("5. FULL EXTRACTION (Claude API call #3)")
    print(f"  Sends {'chunked' if len(text) > 15000 else 'full'} document text → Claude")
    print(f"  Using {engine.__class__.__name__} prompt (engine-specific system + user prompt)")
    print(f"  Text length: {len(text):,} chars")
    print(f"  Estimated tokens: ~{len(text)//4:,}")
    print(f"\n  Running extraction... (this may take 10-30 seconds)")

    t0 = time.time()
    structured_output = engine.extract(text)
    elapsed = time.time() - t0

    # Populate source block with metadata (same as ingestion.py step 7)
    structured_output["source"].update({
        "title":            meta.get("title", ""),
        "organization":     meta.get("organization", ""),
        "publication_year": meta.get("publication_year", None),
        "version_number":   meta.get("version_number", ""),
        "doi":              meta.get("doi", ""),
        "file_name":        os.path.basename(args.file),
    })

    # Parse QIDs/ART-IDs from codon filename
    qid_result = parse_qids_from_path(args.file)
    structured_output["source"]["matched_qids"] = qid_result.get("qids", [])
    structured_output["source"]["qid_match_method"] = qid_result.get("method", "none")

    # Add governance scaffold
    from engines.base_engine import BaseEngine
    structured_output["governance"] = engine._empty_governance()

    extraction = structured_output.get("extraction", {})

    print(f"\n  Extraction complete ({elapsed:.2f}s):")
    print(f"    summary:            {str(extraction.get('summary', ''))[:150]}...")
    print(f"    recommendations:    {len(extraction.get('recommendations', []))} items")
    print(f"    key_thresholds:     {len(extraction.get('key_thresholds', []))} items")
    print(f"    medications:        {len(extraction.get('medications', []))} items")
    print(f"    red_flags:          {len(extraction.get('red_flags', []))} items")
    print(f"    follow_up:          {str(extraction.get('follow_up', ''))[:150]}...")
    print(f"    escalation_path:    {str(extraction.get('escalation_path', ''))[:150]}...")

    if extraction.get("_chunked_extraction"):
        print(f"    [CHUNKED] chunks_merged: {extraction.get('_chunks_merged', '?')}")

    # Print full recommendations
    recs = extraction.get("recommendations", [])
    if recs:
        print(f"\n  --- Recommendations ({len(recs)}) ---")
        for i, r in enumerate(recs[:10], 1):
            rec_text = r.get("recommendation", "")[:120]
            strength = r.get("strength", "?")
            evidence = r.get("evidence_level", "?")
            print(f"    {i}. [{strength} | {evidence}] {rec_text}")
        if len(recs) > 10:
            print(f"    ... and {len(recs) - 10} more")

    # Print key thresholds
    thresh = extraction.get("key_thresholds", [])
    if thresh:
        print(f"\n  --- Key Thresholds ({len(thresh)}) ---")
        for t in thresh[:8]:
            param = t.get("parameter", "?")
            val = t.get("value", "?")
            unit = t.get("unit", "")
            ctx = t.get("context", "")[:80]
            print(f"    • {param}: {val} {unit} — {ctx}")
        if len(thresh) > 8:
            print(f"    ... and {len(thresh) - 8} more")

    # Print medications
    meds = extraction.get("medications", [])
    if meds:
        print(f"\n  --- Medications ({len(meds)}) ---")
        for m in meds[:8]:
            drug = m.get("drug", "?")
            dose = m.get("dose", "?")
            indication = m.get("indication", "?")
            drug_class = m.get("class", "?")
            print(f"    • {drug} ({drug_class}): {dose} — {indication}")
        if len(meds) > 8:
            print(f"    ... and {len(meds) - 8} more")

    # Print red flags
    flags = extraction.get("red_flags", [])
    if flags:
        print(f"\n  --- Red Flags ({len(flags)}) ---")
        for f in flags[:6]:
            print(f"    ! {f[:120]}")

    step_log["steps"]["5_extraction"] = {
        "elapsed_sec": round(elapsed, 2),
        "summary_length": len(str(extraction.get("summary", ""))),
        "recommendations_count": len(recs),
        "thresholds_count": len(thresh),
        "medications_count": len(meds),
        "red_flags_count": len(flags),
        "chunked": extraction.get("_chunked_extraction", False),
    }

    if not args.no_pause:
        pause()

    # ── STEP 6: Validation ───────────────────────────────────────────────
    separator("6. VALIDATION (no API call)")

    warnings = validate_output(structured_output)
    structured_output["metadata"]["validation_passed"] = len(warnings) == 0
    structured_output["metadata"]["validation_warnings"] = warnings
    structured_output["metadata"]["raw_text_chars"] = len(text)

    coverage = structured_output["metadata"].get("field_coverage_score", "?")

    print(f"  Validation passed:    {len(warnings) == 0}")
    print(f"  Field coverage score: {coverage}")
    print(f"  Warnings:             {len(warnings)}")
    if warnings:
        for w in warnings:
            print(f"    [!] {w}")

    step_log["steps"]["6_validation"] = {
        "passed": len(warnings) == 0,
        "field_coverage_score": coverage,
        "warnings": warnings,
    }

    # ── Save outputs ─────────────────────────────────────────────────────
    separator("SAVE OUTPUTS")

    # Full extraction result
    result_path = os.path.join(out_dir, "test_v23_extraction.json")
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(structured_output, f, indent=2, ensure_ascii=False)
    print(f"  Full result:   {result_path}")

    # Step log
    log_path = os.path.join(out_dir, "test_v23_step_log.json")
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(step_log, f, indent=2, ensure_ascii=False)
    print(f"  Step log:      {log_path}")

    # Summary
    print(f"\n{'='*70}")
    print(f"  PIPELINE COMPLETE")
    print(f"{'='*70}")
    print(f"  File:           {os.path.basename(args.file)}")
    print(f"  Engine:         {engine.__class__.__name__} ({screening_result['document_type']})")
    print(f"  Confidence:     {screening_result['confidence']}")
    print(f"  Body systems:   {screening_result['body_systems']}")
    print(f"  Recommendations: {len(recs)}")
    print(f"  Thresholds:     {len(thresh)}")
    print(f"  Medications:    {len(meds)}")
    print(f"  Coverage:       {coverage}")
    print(f"  Validation:     {'PASSED' if len(warnings) == 0 else f'WARNINGS ({len(warnings)})'}")
    print(f"  Output:         {result_path}")
    print()


if __name__ == "__main__":
    main()
