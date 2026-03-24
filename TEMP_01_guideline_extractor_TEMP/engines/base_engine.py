"""
base_engine.py — Abstract base class for all extraction engines.

Updated for unified_v1.0 schema:
  - Adds 'governance' block (empty scaffold, human-populated later)
  - Adds schema_version to metadata
  - source_id wired in from manifest at ingestion time
"""

from __future__ import annotations
from abc import ABC, abstractmethod
import datetime
import uuid


ENGINE_VERSION = "guideline_extractor_v2.3"
SCHEMA_VERSION = "unified_v1.0"


class BaseEngine(ABC):

    DOCUMENT_TYPE: str = "unknown"

    def __init__(self, screening_result: dict):
        self.screening = screening_result
        self.modules: list[str] = []
        self.output: dict = {}

    @abstractmethod
    def activate_modules(self) -> None:
        """Define which extraction modules this engine uses."""
        ...

    @abstractmethod
    def extract(self, document_text: str) -> dict:
        """Run extraction on document_text. Returns full structured output."""
        ...

    def _base_metadata(self) -> dict:
        return {
            "schema_version":       SCHEMA_VERSION,
            "run_id":               str(uuid.uuid4())[:8],
            "extracted_at":         datetime.datetime.utcnow().isoformat() + "Z",
            "engine_version":       ENGINE_VERSION,
            "modules_activated":    self.modules,
            "validation_passed":    None,
            "validation_warnings":  [],
            "field_coverage_score": None,   # computed by validator after extraction
            "raw_text_chars":       0,
            "migration_note":       "",
        }

    def _base_classification(self) -> dict:
        return {
            "engine_used":   self.__class__.__name__,
            "document_type": self.screening.get("document_type", "unknown"),
            "confidence":    self.screening.get("confidence", 0.0),
            "signals":       self.screening.get("signals", []),
            "body_systems":  self.screening.get("body_systems", []),
        }

    def _empty_governance(self) -> dict:
        """
        Returns an empty governance scaffold.
        All fields are human-populated after extraction review.
        Never LLM-generated.
        """
        return {
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
