"""
preventive_engine.py — Extraction engine for preventive medicine and screening guidelines.
"""

from __future__ import annotations
from engines.base_engine import BaseEngine
from utils.prompt_builder import llm_extract


class PreventiveEngine(BaseEngine):

    DOCUMENT_TYPE = "preventive_guideline"

    def activate_modules(self) -> None:
        self.modules = [
            "screening_population",
            "screening_intervals",
            "risk_stratification",
            "preventive_medications",
            "counseling_interventions",
            "positive_screen_pathway",
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
