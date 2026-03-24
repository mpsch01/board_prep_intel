"""
migrate_to_unified.py
=====================
Transforms existing guideline_extractor_v2.3 outputs into the unified_v1.0 schema
and writes them directly to the ite_refs ingested/json/ destination,
replacing the empty navigator_v1 shells.

WHAT IT DOES:
  1. Loads the ITE manifest (maps PDF filename -> source_id -> destination JSON slug)
  2. For each of the 21 gold_list baseline outputs:
     a. Reads the v2.3 extracted JSON from outputs/gold_list_v23_baseline/
     b. Transforms to unified_v1.0 schema
     c. Wires in source_id from the manifest
     d. Adds empty governance scaffold
     e. Adds field_coverage_score via validator
     f. Writes to ite_refs/04_outputs/ingested/json/<slug>.json
  3. Writes a migration summary to outputs/migration_summary.json

USAGE:
  # Run from the guideline_extractor_v2/ project root
  python migrate_to_unified.py

  # Dry run -- shows what would be written without writing
  python migrate_to_unified.py --dry-run

  # Override source and destination paths
  python migrate_to_unified.py \
    --baseline outputs/gold_list_v23_baseline/ \
    --manifest C:/path/to/manifest.json \
    --dest C:/path/to/ite_refs/04_outputs/ingested/json/
"""

from __future__ import annotations
import argparse
import json
import os
import datetime
import sys

# Default paths (relative to guideline_extractor_v2/ project root)

DEFAULT_BASELINE_DIR = os.path.join(
    os.path.dirname(__file__), "outputs", "gold_list_v23_baseline"
)
DEFAULT_MANIFEST_PATH = (
    r"C:\Users\mpsch\Desktop\claude_knowledge\board_prep"
    r"\ite_refs\04_outputs\ingested\manifest.json"
)
DEFAULT_DEST_DIR = (
    r"C:\Users\mpsch\Desktop\claude_knowledge\board_prep"
    r"\ite_refs\04_outputs\ingested\json"
)

SCHEMA_VERSION = "unified_v1.0"
MIGRATION_NOTE = "Migrated from guideline_extractor_v2.3 baseline via migrate_to_unified.py"


# Coverage scoring (inline to avoid import path issues)

EXTRACTION_COVERAGE_FIELDS = [
    "summary", "population", "key_thresholds", "recommendations",
    "medications", "red_flags", "follow_up", "escalation_path",
]
POPULATION_SUBFIELDS = [
    "age_criteria", "risk_criteria", "disease_definition", "exclusions", "severity_staging"
]

def _is_populated(value) -> bool:
    if value is None: return False
    if isinstance(value, str): return len(value.strip()) > 0
    if isinstance(value, (list, dict)): return len(value) > 0
    return True

def compute_field_coverage(extraction: dict) -> float:
    if not isinstance(extraction, dict): return 0.0
    total, earned = 0.0, 0.0
    for field in EXTRACTION_COVERAGE_FIELDS:
        total += 1.0
        value = extraction.get(field)
        if field == "population":
            if isinstance(value, dict):
                sub_pop = sum(1 for sf in POPULATION_SUBFIELDS if _is_populated(value.get(sf)))
                earned += sub_pop / len(POPULATION_SUBFIELDS)
        else:
            if _is_populated(value): earned += 1.0
    return round(earned / total, 3) if total > 0 else 0.0


# Manifest loading

def load_manifest(manifest_path: str) -> dict:
    """
    Returns a dict keyed by PDF filename (e.g. '4.pdf') mapping to:
      { source_id, title, year, json_slug (basename of destination json) }
    """
    with open(manifest_path, "r", encoding="utf-8") as f:
        entries = json.load(f)

    mapping = {}
    for entry in entries:
        pdf_name = os.path.basename(entry.get("pdf", ""))
        json_path = entry.get("json", "")
        json_slug = os.path.basename(json_path)
        mapping[pdf_name] = {
            "source_id":  entry.get("source_id", ""),
            "title":      entry.get("title", ""),
            "year":       entry.get("year", None),
            "json_slug":  json_slug,
        }
    return mapping


# Schema transformation

def transform_to_unified(v23_doc: dict, manifest_entry: dict) -> dict:
    """
    Transform a v2.3 extraction JSON into unified_v1.0 schema.
    Preserves all extracted content, adds governance scaffold, wires source_id.
    """

    src   = v23_doc.get("source",         {})
    clf   = v23_doc.get("classification", {})
    ext   = v23_doc.get("extraction",     {})
    meta  = v23_doc.get("metadata",       {})

    unified_source = {
        "title":            src.get("title", manifest_entry.get("title", "")),
        "organization":     src.get("organization", ""),
        "document_type":    src.get("document_type", clf.get("document_type", "unknown")),
        "publication_year": src.get("publication_year", manifest_entry.get("year", None)),
        "version_number":   src.get("version_number", ""),
        "doi":              src.get("doi", ""),
        "canonical_url":    "",
        "file_name":        src.get("file_name", ""),
        "source_id":        manifest_entry.get("source_id", ""),
        "status":           "active",
        "supersedes":       "",
        "last_verified":    None,
    }

    unified_classification = {
        "engine_used":   clf.get("engine_used", ""),
        "document_type": clf.get("document_type", "unknown"),
        "confidence":    clf.get("confidence", 0.0),
        "signals":       clf.get("signals", []),
        "body_systems":  clf.get("body_systems", []),
    }

    unified_extraction = {
        "summary":          ext.get("summary", ""),
        "population":       ext.get("population", {}),
        "key_thresholds":   ext.get("key_thresholds", []),
        "recommendations":  ext.get("recommendations", []),
        "medications":      ext.get("medications", []),
        "red_flags":        ext.get("red_flags", []),
        "follow_up":        ext.get("follow_up", ""),
        "escalation_path":  ext.get("escalation_path", ""),
        "_chunked_extraction": ext.get("_chunked_extraction", False),
        "_chunks_merged":      ext.get("_chunks_merged", None),
    }

    unified_governance = {
        "badge": {
            "label":         "",
            "rationale":     "",
            "assigned_by":   "",
            "assigned_date": None,
        },
        "cross_guideline_impact": {
            "modifies_pathways": [],
            "changes": {
                "treatment_thresholds": False,
                "new_drug_class":       False,
                "screening_age":        False,
                "monitoring_frequency": False,
                "risk_calculation":     False,
            },
            "notes": "",
        },
        "change_log": [],
        "internal_qc": {
            "metadata_complete":            False,
            "badge_assigned":               False,
            "recommendations_reviewed":     False,
            "thresholds_verified":          False,
            "cross_pathway_links_reviewed": False,
            "prior_version_archived":       False,
            "date_verified":                None,
        },
    }

    coverage = compute_field_coverage(unified_extraction)
    unified_metadata = {
        "schema_version":       SCHEMA_VERSION,
        "run_id":               meta.get("run_id", ""),
        "extracted_at":         meta.get("extracted_at", ""),
        "engine_version":       meta.get("engine_version", ""),
        "validation_passed":    meta.get("validation_passed", False),
        "validation_warnings":  meta.get("validation_warnings", []),
        "field_coverage_score": coverage,
        "modules_activated":    meta.get("modules_activated", []),
        "raw_text_chars":       meta.get("raw_text_chars", 0),
        "migration_note":       MIGRATION_NOTE,
    }

    return {
        "source":         unified_source,
        "classification": unified_classification,
        "extraction":     unified_extraction,
        "governance":     unified_governance,
        "metadata":       unified_metadata,
    }


# Main migration logic

def run_migration(baseline_dir: str, manifest_path: str, dest_dir: str, dry_run: bool = False):

    print(f"\n{'='*65}")
    print(f"  migrate_to_unified.py  |  schema: {SCHEMA_VERSION}")
    print(f"{'='*65}")
    print(f"  Baseline:   {baseline_dir}")
    print(f"  Manifest:   {manifest_path}")
    print(f"  Dest:       {dest_dir}")
    print(f"  Mode:       {'DRY RUN -- no files written' if dry_run else 'LIVE'}")
    print(f"{'='*65}\n")

    if not os.path.exists(manifest_path):
        print(f"[ERROR] Manifest not found: {manifest_path}")
        sys.exit(1)
    manifest = load_manifest(manifest_path)
    print(f"  Manifest loaded: {len(manifest)} entries\n")

    if not os.path.isdir(baseline_dir):
        print(f"[ERROR] Baseline directory not found: {baseline_dir}")
        sys.exit(1)

    baseline_files = sorted([
        f for f in os.listdir(baseline_dir)
        if f.endswith("_extracted.json")
    ])
    print(f"  Found {len(baseline_files)} baseline files\n")

    results = []
    skipped = []

    for fname in baseline_files:
        stem     = fname.replace("_extracted.json", "")
        pdf_name = f"{stem}.pdf"

        if pdf_name not in manifest:
            print(f"  [SKIP] {fname} -- no manifest entry for {pdf_name}")
            skipped.append({"file": fname, "reason": f"no manifest entry for {pdf_name}"})
            continue

        man_entry = manifest[pdf_name]
        dest_slug = man_entry["json_slug"]
        dest_path = os.path.join(dest_dir, dest_slug)

        baseline_path = os.path.join(baseline_dir, fname)
        with open(baseline_path, "r", encoding="utf-8") as f:
            v23_doc = json.load(f)

        unified  = transform_to_unified(v23_doc, man_entry)
        coverage = unified["metadata"]["field_coverage_score"]
        recs     = len(unified["extraction"].get("recommendations", []))
        thresh   = len(unified["extraction"].get("key_thresholds", []))
        meds     = len(unified["extraction"].get("medications", []))
        title    = unified["source"]["title"][:55]
        sid      = unified["source"]["source_id"]

        print(f"  [ok] {pdf_name} -> {dest_slug}")
        print(f"       source_id={sid}  coverage={coverage:.2f}  recs={recs}  thresh={thresh}  meds={meds}")
        print(f"       title: {title}")

        if not dry_run:
            os.makedirs(dest_dir, exist_ok=True)
            with open(dest_path, "w", encoding="utf-8") as f:
                json.dump(unified, f, indent=2, ensure_ascii=False)

        results.append({
            "pdf_name":             pdf_name,
            "source_id":            sid,
            "dest_slug":            dest_slug,
            "title":                unified["source"]["title"],
            "document_type":        unified["classification"]["document_type"],
            "engine_used":          unified["classification"]["engine_used"],
            "confidence":           unified["classification"]["confidence"],
            "field_coverage_score": coverage,
            "recommendations":      recs,
            "thresholds":           thresh,
            "medications":          meds,
            "red_flags":            len(unified["extraction"].get("red_flags", [])),
            "validation_passed":    unified["metadata"]["validation_passed"],
        })

    print(f"\n{'='*65}")
    print(f"  MIGRATION COMPLETE")
    print(f"  Migrated: {len(results)}  |  Skipped: {len(skipped)}")

    avg_coverage = (
        sum(r["field_coverage_score"] for r in results) / len(results)
        if results else 0.0
    )
    total_recs   = sum(r["recommendations"] for r in results)
    total_thresh = sum(r["thresholds"] for r in results)
    total_meds   = sum(r["medications"] for r in results)

    print(f"  Avg field coverage:  {avg_coverage:.2f}")
    print(f"  Total recs:          {total_recs}")
    print(f"  Total thresholds:    {total_thresh}")
    print(f"  Total medications:   {total_meds}")
    print(f"{'='*65}\n")

    summary = {
        "migration_timestamp":   datetime.datetime.utcnow().isoformat() + "Z",
        "schema_version":        SCHEMA_VERSION,
        "dry_run":               dry_run,
        "baseline_dir":          baseline_dir,
        "manifest_path":         manifest_path,
        "dest_dir":              dest_dir,
        "total_migrated":        len(results),
        "total_skipped":         len(skipped),
        "avg_field_coverage":    round(avg_coverage, 3),
        "total_recommendations": total_recs,
        "total_thresholds":      total_thresh,
        "total_medications":     total_meds,
        "skipped":               skipped,
        "per_document":          results,
    }

    summary_path = os.path.join(
        os.path.dirname(__file__), "outputs", "migration_summary.json"
    )
    os.makedirs(os.path.dirname(summary_path), exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"  Summary written: {summary_path}\n")

    if dry_run:
        print("  DRY RUN complete -- re-run without --dry-run to write files.\n")

    return summary


# CLI

def main():
    parser = argparse.ArgumentParser(
        description="Migrate guideline_extractor_v2.3 outputs to unified_v1.0 schema"
    )
    parser.add_argument(
        "--baseline", default=DEFAULT_BASELINE_DIR,
        help="Path to v2.3 baseline outputs directory (default: outputs/gold_list_v23_baseline/)"
    )
    parser.add_argument(
        "--manifest", default=DEFAULT_MANIFEST_PATH,
        help="Path to ITE manifest.json"
    )
    parser.add_argument(
        "--dest", default=DEFAULT_DEST_DIR,
        help="Destination directory (ite_refs ingested/json/)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be written without writing any files"
    )
    args = parser.parse_args()
    run_migration(args.baseline, args.manifest, args.dest, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
