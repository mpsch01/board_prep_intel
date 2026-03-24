"""
main.py -- CLI entry point for guideline_extractor_v2.3

Usage:
    # Single file
    python main.py --file documents/sample.txt

    # Batch directory (all PDFs + TXTs)
    python main.py --dir gold_list/

    # With custom output directory
    python main.py --dir gold_list/ --out outputs/calibration_run2/
"""

from __future__ import annotations
import argparse
import json
import os
import sys
import datetime

from core.ingestion import ingest_document
from utils.logger import load_session_summary


def process_file(file_path: str, out_dir: str) -> dict:
    """Process a single file and write output JSON."""
    print(f"  Processing: {os.path.basename(file_path)}")

    result = ingest_document(file_path)

    # Write output JSON
    stem = os.path.splitext(os.path.basename(file_path))[0]
    out_path = os.path.join(out_dir, f"{stem}_extracted.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    status  = "[ok]" if result["metadata"]["validation_passed"] else "[!]"
    doc_type = result["classification"]["document_type"]
    engine   = result["classification"]["engine_used"]
    conf     = result["classification"]["confidence"]
    warnings = result["metadata"]["validation_warnings"]
    recs     = len(result.get("extraction", {}).get("recommendations", []))
    thresh   = len(result.get("extraction", {}).get("key_thresholds", []))
    meds     = len(result.get("extraction", {}).get("medications", []))
    chunked  = result.get("extraction", {}).get("_chunked_extraction", False)
    title    = result["source"].get("title", "")[:50]

    chunked_tag = " [chunked]" if chunked else ""
    print(f"  {status} [{doc_type} -> {engine}]{chunked_tag} conf={conf:.2f} | recs={recs} thresh={thresh} meds={meds}")
    if title:
        print(f"    Title: {title}")
    if warnings:
        for w in warnings:
            print(f"    [!] {w}")

    return result


def batch_process(input_dir: str, out_dir: str) -> tuple[list, list]:
    """Process all PDFs and TXTs in a directory."""
    supported = (".pdf", ".txt", ".md")
    files = sorted([
        os.path.join(input_dir, f)
        for f in os.listdir(input_dir)
        if os.path.splitext(f)[1].lower() in supported
    ])

    if not files:
        print(f"No supported files found in: {input_dir}")
        return [], []

    print(f"\nBatch processing {len(files)} files from: {input_dir}")
    print(f"Output directory: {out_dir}\n")

    results = []
    failed  = []

    for fp in files:
        try:
            r = process_file(fp, out_dir)
            results.append(r)
        except Exception as e:
            print(f"  [x] ERROR: {os.path.basename(fp)} -- {e}")
            failed.append({"file": fp, "error": str(e)})

    return results, failed


def write_batch_summary(results: list, failed: list, out_dir: str) -> None:
    """Write a full batch run summary JSON including per_document detail."""
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()

    type_counts   = {}
    engine_counts = {}
    for r in results:
        t = r.get("classification", {}).get("document_type", "unknown")
        e = r.get("classification", {}).get("engine_used", "unknown")
        type_counts[t]   = type_counts.get(t, 0) + 1
        engine_counts[e] = engine_counts.get(e, 0) + 1

    total_recs   = sum(len(r.get("extraction", {}).get("recommendations", [])) for r in results)
    total_thresh = sum(len(r.get("extraction", {}).get("key_thresholds", [])) for r in results)
    total_meds   = sum(len(r.get("extraction", {}).get("medications", [])) for r in results)
    passed       = sum(1 for r in results if r.get("metadata", {}).get("validation_passed", False))
    chunked      = sum(1 for r in results if r.get("extraction", {}).get("_chunked_extraction", False))

    # Build per_document list
    per_document = []
    for r in results:
        per_document.append({
            "file_name":    r["source"].get("file_name", ""),
            "title":        r["source"].get("title", ""),
            "organization": r["source"].get("organization", ""),
            "year":         r["source"].get("publication_year", None),
            "document_type":  r["classification"].get("document_type", ""),
            "engine_used":    r["classification"].get("engine_used", ""),
            "confidence":     r["classification"].get("confidence", 0),
            "body_systems":   r["classification"].get("body_systems", []),
            "recommendations_count": len(r.get("extraction", {}).get("recommendations", [])),
            "thresholds_count":      len(r.get("extraction", {}).get("key_thresholds", [])),
            "medications_count":     len(r.get("extraction", {}).get("medications", [])),
            "red_flags_count":       len(r.get("extraction", {}).get("red_flags", [])),
            "chunked_extraction":    r.get("extraction", {}).get("_chunked_extraction", False),
            "validation_passed":     r["metadata"].get("validation_passed", False),
            "validation_warnings":   r["metadata"].get("validation_warnings", []),
            "raw_text_chars":        r["metadata"].get("raw_text_chars", 0),
            "run_id":                r["metadata"].get("run_id", ""),
            "extracted_at":          r["metadata"].get("extracted_at", ""),
        })

    summary = {
        "batch_timestamp":               ts,
        "engine_version":                "guideline_extractor_v2.3",
        "total_processed":               len(results),
        "total_failed":                  len(failed),
        "validation_passed":             passed,
        "validation_failed":             len(results) - passed,
        "chunked_extractions":           chunked,
        "document_type_breakdown":       type_counts,
        "engine_breakdown":              engine_counts,
        "total_recommendations_extracted": total_recs,
        "total_thresholds_extracted":    total_thresh,
        "total_medications_extracted":   total_meds,
        "failed_files":                  failed,
        "per_document":                  per_document,
    }

    summary_path = os.path.join(out_dir, "batch_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"\n{'='*60}")
    print(f"BATCH COMPLETE")
    print(f"  Processed:      {len(results)}")
    print(f"  Failed:         {len(failed)}")
    print(f"  Val. passed:    {passed}/{len(results)}")
    print(f"  Chunked:        {chunked}")
    print(f"  Doc types:      {type_counts}")
    print(f"  Engines used:   {engine_counts}")
    print(f"  Total recs:     {total_recs}")
    print(f"  Total thresh:   {total_thresh}")
    print(f"  Total meds:     {total_meds}")
    print(f"  Summary:        {summary_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Guideline Extractor v2.1 -- Clinical guideline extraction pipeline"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", type=str, help="Path to a single document (.pdf or .txt)")
    group.add_argument("--dir",  type=str, help="Path to directory of documents to batch process")

    parser.add_argument(
        "--out", type=str, default="outputs",
        help="Output directory for extracted JSON files (default: outputs/)"
    )

    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    if args.file:
        if not os.path.exists(args.file):
            print(f"ERROR: File not found: {args.file}")
            sys.exit(1)
        result = process_file(args.file, args.out)
        print("\nExtraction complete.")

    elif args.dir:
        if not os.path.isdir(args.dir):
            print(f"ERROR: Directory not found: {args.dir}")
            sys.exit(1)
        results, failed = batch_process(args.dir, args.out)
        write_batch_summary(results, failed, args.out)


if __name__ == "__main__":
    main()
