"""
reextract_gold_list.py
======================
Re-extracts all 21 gold_list PDFs using the calibration v1 updated prompts
and writes the results directly to ite_refs/04_outputs/ingested/json/,
replacing the current unified_v1.0 files.

WHAT IT DOES:
  1. Archives the current unified_v1.0 JSON files to outputs/pre_calibration_archive/
  2. For each of the 21 gold_list PDFs:
     a. Extracts text from the PDF
     b. Runs the appropriate engine (doc type from manifest)
     c. Wraps in unified_v1.0 schema with source_id, governance scaffold, coverage score
     d. Writes to ite_refs/04_outputs/ingested/json/<slug>.json
  3. Runs calibration.py against the new outputs
  4. Writes a reextraction summary

USAGE:
  python reextract_gold_list.py             # full run, all 21 docs
  python reextract_gold_list.py --dry-run   # show plan without API calls
  python reextract_gold_list.py --skip-archive  # skip archiving (re-run safe)
"""

from __future__ import annotations
import argparse
import json
import os
import sys
import datetime
import shutil
import time

sys.path.insert(0, os.path.dirname(__file__))

from utils.preprocess import preprocess
from utils.prompt_builder import llm_extract
from calibration import score_document, run_calibration

# ── Paths ──────────────────────────────────────────────────────────────────

BASE          = os.path.dirname(__file__)
GOLD_LIST_DIR = os.path.join(BASE, "documents", "gold_list")
MANIFEST_PATH = r"C:\Users\mpsch\Desktop\claude_knowledge\board_prep\ite_refs\04_outputs\ingested\manifest.json"
DEST_DIR      = r"C:\Users\mpsch\Desktop\claude_knowledge\board_prep\ite_refs\04_outputs\ingested\json"
ARCHIVE_DIR   = os.path.join(BASE, "outputs", "pre_calibration_archive")
SUMMARY_PATH  = os.path.join(BASE, "outputs", "reextraction_summary.json")

SCHEMA_VERSION   = "unified_v1.0"
EXTRACTION_NOTE  = "Re-extracted with calibration_v1 prompts via reextract_gold_list.py"

# Doc type -> engine name mapping (for logging)
ENGINE_MAP = {
    "chronic_guideline":    "ChronicRiskEngine",
    "acute_protocol":       "AcuteProtocolEngine",
    "preventive_guideline": "PreventiveEngine",
    "diagnostic_guideline": "DiagnosticEngine",
    "rct":                  "RCTEngine",
    "unknown":              "ChronicRiskEngine",
}

# Coverage scoring (inline)
EXTRACTION_FIELDS = [
    "summary", "population", "key_thresholds", "recommendations",
    "medications", "red_flags", "follow_up", "escalation_path",
]
POP_SUBFIELDS = [
    "age_criteria", "risk_criteria", "disease_definition", "exclusions", "severity_staging"
]

def _pop(val) -> bool:
    if val is None: return False
    if isinstance(val, str): return len(val.strip()) > 0
    if isinstance(val, (list, dict)): return len(val) > 0
    return True

def coverage_score(extraction: dict) -> float:
    total, earned = 0.0, 0.0
    for field in EXTRACTION_FIELDS:
        total += 1.0
        val = extraction.get(field)
        if field == "population":
            if isinstance(val, dict):
                sub_pop = sum(1 for f in POP_SUBFIELDS if _pop(val.get(f)))
                earned += sub_pop / len(POP_SUBFIELDS)
        else:
            if _pop(val):
                earned += 1.0
    return round(earned / total, 3) if total > 0 else 0.0


def empty_governance():
    return {
        "badge": {"label": "", "rationale": "", "assigned_by": "", "assigned_date": ""},
        "cross_guideline_impact": {
            "modifies_pathways": [],
            "changes": {
                "treatment_thresholds": False, "new_drug_class": False,
                "screening_age": False, "monitoring_frequency": False,
                "risk_calculation": False
            },
            "notes": ""
        },
        "change_log": [],
        "internal_qc": {
            "summary_accurate": False, "population_complete": False,
            "thresholds_verified": False, "recommendations_graded": False,
            "medications_dosed": False, "red_flags_complete": False,
            "escalation_path_valid": False, "date_verified": ""
        }
    }


def build_unified_doc(extraction: dict, entry: dict, doc_type: str, engine_name: str) -> dict:
    """Wrap raw extraction in unified_v1.0 structure."""
    cov = coverage_score(extraction)
    return {
        "schema_version": SCHEMA_VERSION,
        "source": {
            "source_id":        entry["source_id"],
            "title":            entry.get("title", ""),
            "organization":     extraction.get("_metadata", {}).get("organization", ""),
            "document_type":    doc_type,
            "publication_year": entry.get("year"),
            "version_number":   "",
            "doi":              "",
            "canonical_url":    "",
            "file_name":        os.path.basename(entry["pdf"]),
            "status":           "active",
            "supersedes":       "",
            "last_verified":    "",
        },
        "classification": {
            "document_type": doc_type,
            "engine_used":   engine_name,
            "confidence":    1.0,
        },
        "extraction": {
            "summary":           extraction.get("summary", ""),
            "population":        extraction.get("population", {}),
            "key_thresholds":    extraction.get("key_thresholds", []),
            "recommendations":   extraction.get("recommendations", []),
            "medications":       extraction.get("medications", []),
            "red_flags":         extraction.get("red_flags", []),
            "follow_up":         extraction.get("follow_up", ""),
            "escalation_path":   extraction.get("escalation_path", ""),
            "_chunked_extraction": extraction.get("_chunked_extraction", False),
            "_chunks_merged":    extraction.get("_chunks_merged", 0),
        },
        "governance": empty_governance(),
        "metadata": {
            "schema_version":       SCHEMA_VERSION,
            "run_id":               datetime.datetime.now().strftime("%Y%m%d_%H%M%S"),
            "extracted_at":         datetime.datetime.now().isoformat() + "Z",
            "engine_version":       "v2.3_calibration_v1",
            "validation_passed":    True,
            "validation_warnings":  [],
            "modules_activated":    ["calibration_v1"],
            "raw_text_chars":       0,
            "field_coverage_score": cov,
            "migration_note":       EXTRACTION_NOTE,
        }
    }


# ── Archive current JSONs ──────────────────────────────────────────────────

def archive_current(dry_run: bool):
    json_files = [f for f in os.listdir(DEST_DIR) if f.endswith(".json")]
    if not json_files:
        print("  No existing JSON files to archive.")
        return
    if not dry_run:
        os.makedirs(ARCHIVE_DIR, exist_ok=True)
    print(f"  Archiving {len(json_files)} current JSON files -> {ARCHIVE_DIR}")
    for fname in json_files:
        src = os.path.join(DEST_DIR, fname)
        dst = os.path.join(ARCHIVE_DIR, fname)
        if not dry_run:
            shutil.copy2(src, dst)
    if not dry_run:
        print(f"  Archive complete.")
    else:
        print(f"  [dry-run] Would archive {len(json_files)} files.")


# ── Main re-extraction ─────────────────────────────────────────────────────

def run_reextraction(dry_run: bool = False, skip_archive: bool = False):
    print(f"\n{'='*65}")
    print(f"  reextract_gold_list.py  |  calibration_v1 prompts")
    print(f"{'='*65}")
    print(f"  Gold list:  {GOLD_LIST_DIR}")
    print(f"  Dest:       {DEST_DIR}")
    print(f"  Archive:    {ARCHIVE_DIR}")
    if dry_run:
        print(f"  MODE:       DRY RUN (no API calls, no writes)")
    print(f"{'='*65}\n")

    # Load manifest
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest_list = json.load(f)
    manifest = {os.path.basename(e["pdf"]): e for e in manifest_list}
    print(f"  Manifest loaded: {len(manifest)} entries\n")

    # Archive existing outputs first
    if not skip_archive:
        archive_current(dry_run)
        print()

    # Find all PDFs
    pdf_files = sorted([f for f in os.listdir(GOLD_LIST_DIR)
                        if f.endswith(".pdf") and not f.endswith("_extracted.json")])
    print(f"  Found {len(pdf_files)} PDFs to re-extract\n")

    results = []
    failed  = []
    total   = len(pdf_files)

    for idx, pdf_name in enumerate(pdf_files, 1):
        pdf_path = os.path.join(GOLD_LIST_DIR, pdf_name)
        entry = manifest.get(pdf_name)

        if not entry:
            print(f"  [{idx:2}/{total}] SKIP  {pdf_name} — not in manifest")
            failed.append({"pdf": pdf_name, "reason": "not in manifest"})
            continue

        title    = entry.get("title", pdf_name)
        dest_slug = os.path.basename(entry["json"])
        dest_path = os.path.join(DEST_DIR, dest_slug)

        print(f"  [{idx:2}/{total}] {pdf_name:<10}  {title[:50]}")

        if dry_run:
            print(f"            -> {dest_slug}")
            results.append({"pdf": pdf_name, "title": title, "status": "dry_run"})
            continue

        # Extract text
        try:
            doc_text = preprocess(pdf_path)
        except Exception as e:
            print(f"            FAILED text extraction: {e}")
            failed.append({"pdf": pdf_name, "reason": f"preprocess: {e}"})
            continue

        if not doc_text or len(doc_text) < 100:
            print(f"            FAILED empty text")
            failed.append({"pdf": pdf_name, "reason": "empty text"})
            continue

        # Determine doc_type from existing unified JSON (preserve routing decision)
        existing_path = dest_path
        doc_type = "unknown"
        if os.path.exists(existing_path):
            try:
                with open(existing_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                doc_type = existing.get("classification", {}).get("document_type", "unknown")
            except Exception:
                pass
        # Fallback: check archive
        if doc_type == "unknown":
            archive_path = os.path.join(ARCHIVE_DIR, dest_slug)
            if os.path.exists(archive_path):
                try:
                    with open(archive_path, "r", encoding="utf-8") as f:
                        archived = json.load(f)
                    doc_type = archived.get("classification", {}).get("document_type", "unknown")
                except Exception:
                    pass

        engine_name = ENGINE_MAP.get(doc_type, "ChronicRiskEngine")
        print(f"            engine={engine_name}  chars={len(doc_text):,}")

        # Run extraction
        t0 = time.time()
        try:
            extraction = llm_extract(doc_text, doc_type)
        except Exception as e:
            print(f"            FAILED extraction: {e}")
            failed.append({"pdf": pdf_name, "reason": f"extraction: {e}"})
            continue
        elapsed = time.time() - t0

        # Build unified doc
        unified = build_unified_doc(extraction, entry, doc_type, engine_name)
        cov     = unified["metadata"]["field_coverage_score"]

        # Score quality
        quality = score_document(unified)
        overall = quality["quality_scores"]["overall"]

        recs  = len(extraction.get("recommendations", []))
        thresh= len(extraction.get("key_thresholds", []))
        meds  = len(extraction.get("medications", []))

        print(f"            coverage={cov:.2f}  quality={overall:.3f}  "
              f"recs={recs} thresh={thresh} meds={meds}  ({elapsed:.1f}s)")

        # Write to destination
        with open(dest_path, "w", encoding="utf-8") as f:
            json.dump(unified, f, indent=2, ensure_ascii=False)

        results.append({
            "pdf":                  pdf_name,
            "source_id":            entry["source_id"],
            "dest_slug":            dest_slug,
            "title":                title,
            "document_type":        doc_type,
            "engine_used":          engine_name,
            "field_coverage_score": cov,
            "overall_quality":      overall,
            "recommendations":      recs,
            "thresholds":           thresh,
            "medications":          meds,
            "elapsed_s":            round(elapsed, 1),
            "status":               "success",
        })

    # ── Summary ──────────────────────────────────────────────────────────
    print(f"\n  {'='*65}")
    n_ok = len([r for r in results if r.get("status") == "success"])
    print(f"  COMPLETE: {n_ok}/{total} succeeded, {len(failed)} failed")

    if not dry_run and n_ok > 0:
        avg_cov     = sum(r["field_coverage_score"] for r in results if r.get("status") == "success") / n_ok
        avg_quality = sum(r["overall_quality"]      for r in results if r.get("status") == "success") / n_ok
        total_recs  = sum(r["recommendations"]      for r in results if r.get("status") == "success")
        total_thr   = sum(r["thresholds"]           for r in results if r.get("status") == "success")
        total_meds  = sum(r["medications"]          for r in results if r.get("status") == "success")
        print(f"  avg field_coverage:  {avg_cov:.3f}")
        print(f"  avg quality:         {avg_quality:.3f}")
        print(f"  total recs/thr/meds: {total_recs}/{total_thr}/{total_meds}")

        summary = {
            "reextraction_timestamp": datetime.datetime.now().isoformat() + "Z",
            "prompts_version":        "calibration_v1",
            "total_attempted":        total,
            "total_succeeded":        n_ok,
            "total_failed":           len(failed),
            "avg_field_coverage":     round(avg_cov, 3),
            "avg_overall_quality":    round(avg_quality, 3),
            "total_recommendations":  total_recs,
            "total_thresholds":       total_thr,
            "total_medications":      total_meds,
            "failed":                 failed,
            "per_document":           results,
        }
        with open(SUMMARY_PATH, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        print(f"  Summary: {SUMMARY_PATH}")
    print(f"  {'='*65}\n")

    if not dry_run and n_ok > 0:
        print("  Running calibration against new outputs...\n")
        run_calibration(
            source_dir  = DEST_DIR,
            prompts_dir = os.path.join(BASE, "prompts"),
            report_dir  = os.path.join(BASE, "outputs", "calibration"),
        )

    return results, failed


# ── CLI ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Re-extract all 21 gold_list PDFs with calibration_v1 prompts"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Show plan without making API calls or writing files")
    parser.add_argument("--skip-archive", action="store_true",
                        help="Skip archiving current JSON files (safe to re-run)")
    args = parser.parse_args()
    run_reextraction(dry_run=args.dry_run, skip_archive=args.skip_archive)


if __name__ == "__main__":
    main()
