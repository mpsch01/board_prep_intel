"""
chronic_engine.py — Extraction engine for chronic disease management guidelines.
"""

from __future__ import annotations
from engines.base_engine import BaseEngine
from utils.prompt_builder import llm_extract


class ChronicRiskEngine(BaseEngine):

    DOCUMENT_TYPE = "chronic_guideline"

    def activate_modules(self) -> None:
        self.modules = [
            "disease_definition",
            "diagnostic_thresholds",
            "risk_stratification",
            "escalation_ladder",
            "medication_management",
            "monitoring_schedule",
        ]

    def extract(self, document_text: str) -> dict:
        self.activate_modules()

        # Run real LLM extraction
        extraction = llm_extract(document_text, self.DOCUMENT_TYPE)

        return {
            "source": {
                "title": "",
                "organization": "",
                "document_type": self.DOCUMENT_TYPE,
                "publication_year": None,
                "version_number": "",
                "doi": "",
                "file_name": "",
            },
            "classification": self._base_classification(),
            "extraction": extraction,
            "metadata": self._base_metadata(),
        }
