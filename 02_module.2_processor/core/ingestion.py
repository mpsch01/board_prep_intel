"""
ingestion.py — Main pipeline orchestrator.
Preprocess → Screen → Route → Extract → Validate → Log

v2 update: QID tagging via qid_filename_parser (Phase 2 ITE Intelligence)
"""

from __future__ import annotations
import os
from utils.preprocess import preprocess
from utils.logger import log_run
from utils.validator import validate_output
from utils.prompt_builder import extract_metadata
from utils.qid_filename_parser import parse_qids_from_path   # ← Phase 2 addition
from core.screening import screening_classifier
from core.routing import route_document


def ingest_document(file_path: str, run_id: str = None) -> dict:
    """
    Full extraction pipeline for a single document.

    Args:
        file_path: Path to .pdf or .txt file
        run_id: Optional run identifier for logging

    Returns:
        Validated structured extraction dict
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Document not found: {file_path}")

    # 1. Preprocess
    text = preprocess(file_path)

    # 2. Extract metadata (title, org, year) from document header
    meta = extract_metadata(text)

    # 3. Screen / classify
    screening_result = screening_classifier(text)

    # 4. Route to engine
    engine = route_document(screening_result)

    # 5. Extract
    structured_output = engine.extract(text)

    # 6. Parse QIDs from filename (Phase 2 ITE Intelligence)
    qid_result = parse_qids_from_path(file_path)                # ← Phase 2 addition
    matched_qids     = qid_result.get("qids", [])               # ← Phase 2 addition
    qid_match_method = qid_result.get("method", "none")         # ← Phase 2 addition

    # 7. Populate source block with real metadata
    structured_output["source"].update({
        "title":            meta.get("title", ""),
        "organization":     meta.get("organization", ""),
        "publication_year": meta.get("publication_year", None),
        "version_number":   meta.get("version_number", ""),
        "doi":              meta.get("doi", ""),
        "file_name":        os.path.basename(file_path),
        "matched_qids":     matched_qids,                       # ← Phase 2 addition
        "qid_match_method": qid_match_method,                   # ← Phase 2 addition
    })

    # 8. Validate
    warnings = validate_output(structured_output)
    structured_output["metadata"]["validation_passed"] = len(warnings) == 0
    structured_output["metadata"]["validation_warnings"] = warnings
    structured_output["metadata"]["raw_text_chars"] = len(text)
    if run_id:
        structured_output["metadata"]["run_id"] = run_id

    # 9. Log
    log_run(structured_output, run_id=run_id)

    return structured_output
