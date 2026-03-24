"""
acute_engine.py — Extraction engine for acute/emergency clinical protocols.
"""

from __future__ import annotations
from engines.base_engine import BaseEngine
from utils.prompt_builder import llm_extract


class AcuteProtocolEngine(BaseEngine):

    DOCUMENT_TYPE = "acute_protocol"

    def activate_modules(self) -> None:
        self.modules = [
            "urgency_triage",
            "stabilization_steps",
            "critical_thresholds",
            "emergency_medications",
            "escalation_triggers",
            "disposition",
        ]

    def extract(self, document_text: str) -> dict:
        self.activate_modules()

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
