"""
migrate_afp_batch.py
====================
Migrates the AFP/USPSTF/peds batch (outputs/afp_peds_uspstf_batch/) into the
unified_v1.0 schema and writes outputs to:
  board_prep/ite_refs/04_outputs/ingested/json/

Unlike migrate_to_unified.py (which relied on numeric PDF filenames + an existing
manifest), this script works directly from the extracted JSON files, which carry
their own source metadata. It:

  1. Reads each *_extracted.json from the AFP batch directory
  2. Generates a deterministic source_id using an "AFP-" prefix + 10-char hash
     derived from the title (consistent with ITE- hash pattern)
  3. Applies the unified_v1.0 schema transform
  4. Writes the output JSON to ingested/json/ using a sanitized title slug
  5. Appends new manifest entries to manifest.json (skips if source_id already present)
  6. Writes a migration summary to outputs/afp_batch_migration_summary.json

USAGE:
  cd C:\\Users\\mpsch\\Desktop\\claude_knowledge\\guideline_extractor_v2
  python migrate_afp_batch.py             # full live run
  python migrate_afp_batch.py --dry-run   # preview only
  python migrate_afp_batch.py --only 001,002,003   # test subset
"""

from __future__ import annotations
import argparse, datetime, hashlib, json, os, re, sys

# ── Default paths ──────────────────────────────────────────────────────────────

DEFAULT_BATCH_DIR = os.path.join(
    os.path.dirname(__file__), "outputs", "afp_peds_uspstf_batch"
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
SOURCE_PREFIX  = "AFP"
MIGRATION_NOTE = "Migrated from afp_peds_uspstf_batch via migrate_afp_batch.py"


# ── Source ID + slug ───────────────────────────────────────────────────────────

def make_source_id(title: str) -> str:
    """Deterministic AFP-<10hex> from title SHA-256."""
    digest = hashlib.sha256(title.strip().lower().encode("utf-8")).hexdigest()
    return f"{SOURCE_PREFIX}-{digest[:10]}"

def make_json_slug(title: str, source_id: str) -> str:
    """Sanitized title slug + 8-char hash suffix, matching existing naming convention."""
    clean = re.sub(r"[^a-z0-9\s]", " ", title.lower())
    slug  = "-".join(clean.split())[:80].rstrip("-")
    short = source_id.split("-")[-1][:8]
    return f"{slug}-{short}.json"


# ── Coverage scoring ───────────────────────────────────────────────────────────

EXTRACTION_COVERAGE_FIELDS = [
    "summary", "population", "key_thresholds", "recommendations",
    "medications", "red_flags", "follow_up", "escalation_path",
]
POPULATION_SUBFIELDS = [
    "age_criteria", "risk_criteria", "disease_definition", "exclusions", "severity_staging"
]

def _is_populated(v) -> bool:
    if v is None:                    return False
    if isinstance(v, str):           return len(v.strip()) > 0
    if isinstance(v, (list, dict)):  return len(v) > 0
    return True

def compute_field_coverage(extraction: dict) -> float:
    if not isinstance(extraction, dict): return 0.0
    total, earned = 0.0, 0.0
    for field in EXTRACTION_COVERAGE_FIELDS:
        total += 1.0
        val = extraction.get(field)
        if field == "population":
            if isinstance(val, dict):
                sub = sum(1 for sf in POPULATION_SUBFIELDS if _is_populated(val.get(sf)))
                earned += sub / len(POPULATION_SUBFIELDS)
        else:
            if _is_populated(val): earned += 1.0
    return round(earned / total, 3) if total > 0 else 0.0


# ── Schema transform ───────────────────────────────────────────────────────────

def transform_to_unified(v23_doc: dict, source_id: str) -> dict:
    src  = v23_doc.get("source",         {})
    clf  = v23_doc.get("classification", {})
    ext  = v23_doc.get("extraction",     {})
    meta = v23_doc.get("metadata",       {})

    unified_source = {
        "title":            src.get("title", ""),
        "organization":     src.get("organization", ""),
        "document_type":    src.get("document_type", clf.get("document_type", "unknown")),
        "publication_year": src.get("publication_year", None),
        "version_number":   src.get("version_number", ""),
        "doi":              src.get("doi", ""),
        "canonical_url":    "",
        "file_name":        src.get("file_name", ""),
        "source_id":        source_id,
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
        "summary":             ext.get("summary", ""),
        "population":          ext.get("population", {}),
        "key_thresholds":      ext.get("key_thresholds", []),
        "recommendations":     ext.get("recommendations", []),
        "medications":         ext.get("medications", []),
        "red_flags":           ext.get("red_flags", []),
        "follow_up":           ext.get("follow_up", ""),
        "escalation_path":     ext.get("escalation_path", ""),
        "_chunked_extraction": ext.get("_chunked_extraction", False),
        "_chunks_merged":      ext.get("_chunks_merged", None),
    }
    unified_governance = {
        "badge": {"label": "", "rationale": "", "assigned_by": "", "assigned_date": None},
        "cross_guideline_impact": {
            "modifies_pathways": [],
            "changes": {
                "treatment_thresholds": False, "new_drug_class": False,
                "screening_age": False, "monitoring_frequency": False,
                "risk_calculation": False,
            },
            "notes": "",
        },
        "change_log": [],
        "internal_qc": {
            "metadata_complete": False, "badge_assigned": False,
            "recommendations_reviewed": False, "thresholds_verified": False,
            "cross_pathway_links_reviewed": False, "prior_version_archived": False,
            "date_verified": None,
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
        "source": unified_source, "classification": unified_classification,
        "extraction": unified_extraction, "governance": unified_governance,
        "metadata": unified_metadata,
    }


# ── Manifest helpers ───────────────────────────────────────────────────────────

def load_manifest(path: str) -> list:
    if not os.path.exists(path): return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def existing_source_ids(manifest: list) -> set:
    return {e.get("source_id", "") for e in manifest}

def save_manifest(path: str, manifest: list) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)


# ── Main migration ─────────────────────────────────────────────────────────────

def run_migration(batch_dir, manifest_path, dest_dir,
                  dry_run=False, only=None):

    print(f"\n{'='*68}")
    print(f"  migrate_afp_batch.py  |  schema: {SCHEMA_VERSION}")
    print(f"{'='*68}")
    print(f"  Batch:    {batch_dir}")
    print(f"  Manifest: {manifest_path}")
    print(f"  Dest:     {dest_dir}")
    print(f"  Mode:     {'DRY RUN' if dry_run else 'LIVE'}")
    if only: print(f"  Filter:   {only}")
    print(f"{'='*68}\n")

    if not os.path.isdir(batch_dir):
        print(f"[ERROR] Batch dir not found: {batch_dir}"); sys.exit(1)

    all_files = sorted([
        f for f in os.listdir(batch_dir)
        if f.endswith("_extracted.json") and f != "batch_summary.json"
    ])
    if only:
        all_files = [f for f in all_files if any(f.startswith(p) for p in only)]

    print(f"  Found {len(all_files)} file(s) to process\n")

    manifest     = load_manifest(manifest_path)
    existing_ids = existing_source_ids(manifest)
    print(f"  Manifest: {len(manifest)} entries, {len(existing_ids)} unique source_ids\n")

    results, skipped, new_entries = [], [], []


    for fname in all_files:
        with open(os.path.join(batch_dir, fname), "r", encoding="utf-8") as f:
            v23_doc = json.load(f)

        title     = v23_doc.get("source", {}).get("title", "").strip()
        year      = v23_doc.get("source", {}).get("publication_year", None)
        file_name = v23_doc.get("source", {}).get("file_name", fname)

        if not title:
            print(f"  [SKIP] {fname} — no title")
            skipped.append({"file": fname, "reason": "no title"}); continue

        source_id = make_source_id(title)
        if source_id in existing_ids:
            print(f"  [SKIP] {fname} — already ingested ({source_id})")
            skipped.append({"file": fname, "reason": f"duplicate ({source_id})"}); continue

        json_slug = make_json_slug(title, source_id)
        dest_path = os.path.join(dest_dir, json_slug)
        unified   = transform_to_unified(v23_doc, source_id)

        cov   = unified["metadata"]["field_coverage_score"]
        recs  = len(unified["extraction"].get("recommendations", []))
        thresh= len(unified["extraction"].get("key_thresholds",  []))
        meds  = len(unified["extraction"].get("medications",     []))
        flags = len(unified["extraction"].get("red_flags",       []))

        print(f"  [ok] {fname[:55]}")
        print(f"       {source_id}  cov={cov:.2f}  recs={recs}  thresh={thresh}  meds={meds}  flags={flags}")
        print(f"       {title[:65]}")
        print(f"       -> {json_slug}\n")

        if not dry_run:
            os.makedirs(dest_dir, exist_ok=True)
            with open(dest_path, "w", encoding="utf-8") as f:
                json.dump(unified, f, indent=2, ensure_ascii=False)

        new_entries.append({
            "pdf": file_name, "json": dest_path, "raw": "",
            "title": title, "year": year,
            "source_id": source_id, "batch": "afp_peds_uspstf",
        })
        results.append({
            "batch_file": fname, "source_id": source_id,
            "dest_slug": json_slug, "title": title, "year": year,
            "document_type":        unified["classification"]["document_type"],
            "engine_used":          unified["classification"]["engine_used"],
            "confidence":           unified["classification"]["confidence"],
            "field_coverage_score": cov,
            "recommendations":      recs, "thresholds": thresh,
            "medications":          meds, "red_flags":  flags,
            "validation_passed":    unified["metadata"]["validation_passed"],
        })


    # ── Update manifest ────────────────────────────────────────────────────────
    if not dry_run and new_entries:
        manifest.extend(new_entries)
        save_manifest(manifest_path, manifest)
        print(f"  Manifest updated: +{len(new_entries)} entries (total: {len(manifest)})\n")

    # ── Summary ────────────────────────────────────────────────────────────────
    avg_cov    = (sum(r["field_coverage_score"] for r in results) / len(results)
                  if results else 0.0)
    total_recs   = sum(r["recommendations"] for r in results)
    total_thresh = sum(r["thresholds"]      for r in results)
    total_meds   = sum(r["medications"]     for r in results)
    total_flags  = sum(r["red_flags"]       for r in results)

    print(f"\n{'='*68}")
    print(f"  DONE  —  Migrated: {len(results)}  |  Skipped: {len(skipped)}")
    print(f"  Avg coverage: {avg_cov:.3f}")
    print(f"  recs={total_recs}  thresh={total_thresh}  meds={total_meds}  flags={total_flags}")
    print(f"{'='*68}\n")

    summary = {
        "migration_timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "schema_version": SCHEMA_VERSION, "dry_run": dry_run,
        "batch_dir": batch_dir, "manifest_path": manifest_path, "dest_dir": dest_dir,
        "filter_only": only,
        "total_migrated": len(results), "total_skipped": len(skipped),
        "avg_field_coverage": round(avg_cov, 3),
        "total_recommendations": total_recs, "total_thresholds": total_thresh,
        "total_medications": total_meds, "total_red_flags": total_flags,
        "skipped": skipped, "per_document": results,
    }
    summary_path = os.path.join(os.path.dirname(__file__),
                                "outputs", "afp_batch_migration_summary.json")
    os.makedirs(os.path.dirname(summary_path), exist_ok=True)
    if not dry_run:
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        print(f"  Summary: {summary_path}\n")
    else:
        print("  [DRY RUN] Summary not written.\n")
    return summary


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(
        description="Migrate AFP/USPSTF/peds batch JSONs to unified_v1.0 schema")
    p.add_argument("--batch",    default=DEFAULT_BATCH_DIR)
    p.add_argument("--manifest", default=DEFAULT_MANIFEST_PATH)
    p.add_argument("--dest",     default=DEFAULT_DEST_DIR)
    p.add_argument("--dry-run",  action="store_true")
    p.add_argument("--only",     default=None,
                   help="Comma-separated batch number prefixes, e.g. 001,002,003")
    args = p.parse_args()
    only = [x.strip() for x in args.only.split(",")] if args.only else None
    run_migration(args.batch, args.manifest, args.dest,
                  dry_run=args.dry_run, only=only)

if __name__ == "__main__":
    main()
