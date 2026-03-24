"""
validator.py — Field-level output validation against the unified schema (unified_v1.0).

Validates both LLM-extracted fields and presence of governance scaffolding.
Returns a list of warnings rather than raising hard errors,
so partial extractions can still be logged and reviewed.

New in unified_v1.0:
  - Validates governance block presence
  - Computes field_coverage_score (fraction of extraction fields populated)
  - source.source_id presence check (links to ite_refs system)
"""

from __future__ import annotations


REQUIRED_TOP_LEVEL       = ["source", "classification", "extraction", "governance", "metadata"]
REQUIRED_CLASSIFICATION  = ["engine_used", "document_type", "confidence"]
REQUIRED_EXTRACTION      = ["summary", "population", "recommendations"]
REQUIRED_SOURCE          = ["document_type"]

# Extraction fields used for coverage scoring — all fields the engine is expected to populate
EXTRACTION_COVERAGE_FIELDS = [
    "summary",
    "population",
    "key_thresholds",
    "recommendations",
    "medications",
    "red_flags",
    "follow_up",
    "escalation_path",
]

# Population sub-fields
POPULATION_SUBFIELDS = [
    "age_criteria",
    "risk_criteria",
    "disease_definition",
    "exclusions",
    "severity_staging",
]


def _is_populated(value) -> bool:
    """Return True if a value is meaningfully populated (not empty/null)."""
    if value is None:
        return False
    if isinstance(value, str):
        return len(value.strip()) > 0
    if isinstance(value, (list, dict)):
        return len(value) > 0
    if isinstance(value, bool):
        return True  # booleans are always "populated"
    return True


def compute_field_coverage(extraction: dict) -> float:
    """
    Compute fraction of expected extraction fields that are populated.
    Returns 0.0-1.0.

    Scoring:
      - Each top-level extraction field counts as 1 point
      - population sub-fields contribute fractionally (5 sub-fields = 1 point total)
    """
    if not isinstance(extraction, dict):
        return 0.0

    total_points = 0.0
    earned_points = 0.0

    for field in EXTRACTION_COVERAGE_FIELDS:
        total_points += 1.0
        value = extraction.get(field)

        if field == "population":
            # Score population as fraction of sub-fields populated
            if isinstance(value, dict):
                sub_populated = sum(
                    1 for sf in POPULATION_SUBFIELDS
                    if _is_populated(value.get(sf))
                )
                earned_points += sub_populated / len(POPULATION_SUBFIELDS)
            # else: 0 points
        else:
            if _is_populated(value):
                earned_points += 1.0

    return round(earned_points / total_points, 3) if total_points > 0 else 0.0


def validate_output(output: dict) -> list[str]:
    """
    Validate extracted output dict against unified_v1.0 schema.

    Returns:
        List of warning strings (empty list = fully valid)
    Raises:
        TypeError if output is not a dict
    """
    if not isinstance(output, dict):
        raise TypeError(f"Output must be a dict, got {type(output).__name__}")

    warnings = []

    # Top-level keys
    for key in REQUIRED_TOP_LEVEL:
        if key not in output:
            warnings.append(f"Missing top-level key: '{key}'")

    # Source block
    source = output.get("source", {})
    if isinstance(source, dict):
        for key in REQUIRED_SOURCE:
            if not source.get(key):
                warnings.append(f"source.{key} is empty or missing")
        if not source.get("source_id"):
            warnings.append("source.source_id is missing — link to ite_refs manifest not established")
        if not source.get("title"):
            warnings.append("source.title is empty — metadata extraction may have failed")
    else:
        warnings.append("'source' is not a dict")

    # Classification block
    clf = output.get("classification", {})
    if isinstance(clf, dict):
        for key in REQUIRED_CLASSIFICATION:
            if key not in clf or clf[key] is None:
                warnings.append(f"classification.{key} is missing or null")
        confidence = clf.get("confidence", None)
        if confidence is not None and not (0.0 <= float(confidence) <= 1.0):
            warnings.append(f"classification.confidence out of range: {confidence}")
    else:
        warnings.append("'classification' is not a dict")

    # Extraction block
    extraction = output.get("extraction", {})
    if isinstance(extraction, dict):
        for key in REQUIRED_EXTRACTION:
            if not extraction.get(key):
                warnings.append(f"extraction.{key} is empty or missing")

        recs = extraction.get("recommendations", [])
        if isinstance(recs, list) and len(recs) == 0:
            warnings.append("extraction.recommendations is empty — no recommendations extracted")

        thresholds = extraction.get("key_thresholds", [])
        if isinstance(thresholds, list) and len(thresholds) == 0:
            warnings.append("extraction.key_thresholds is empty — no numeric thresholds extracted")

        # Compute and store coverage score in metadata
        coverage = compute_field_coverage(extraction)
        meta = output.get("metadata", {})
        if isinstance(meta, dict):
            meta["field_coverage_score"] = coverage
        if coverage < 0.5:
            warnings.append(
                f"extraction.field_coverage_score={coverage:.2f} — less than 50% of fields populated"
            )
    else:
        warnings.append("'extraction' is not a dict")

    # Governance block
    governance = output.get("governance", {})
    if not isinstance(governance, dict):
        warnings.append("'governance' block is missing or not a dict")
    # Governance fields are human-populated — we don't warn on empty, just on missing block

    # Metadata block
    meta = output.get("metadata", {})
    if not isinstance(meta, dict):
        warnings.append("'metadata' is not a dict")

    return warnings
