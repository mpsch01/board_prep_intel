"""
rct_engine.py — Extraction engine for randomized controlled trial articles.

Handles primary research articles reporting trial results (NEJM, Lancet, JAMA, etc.)
Distinct from clinical guidelines — extracts trial design, endpoints, and statistical results.

Examples from gold_list_2:
  NEJMoa1709118 — COMPASS trial (rivaroxaban + aspirin in stable CAD/PAD)
  NEJMoa2000052 — VOYAGER PAD trial (rivaroxaban after peripheral revascularization)
"""

from __future__ import annotations
from engines.base_engine import BaseEngine
from utils.prompt_builder import llm_extract


class RCTEngine(BaseEngine):

    DOCUMENT_TYPE = "rct"

    def activate_modules(self) -> None:
        self.modules = [
            "trial_design",
            "population_eligibility",
            "intervention_comparator",
            "primary_endpoints",
            "statistical_results",
            "safety_adverse_events",
            "clinical_implications",
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
