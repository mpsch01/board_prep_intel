"""
diagnostic_engine.py — Extraction engine for diagnostic / workup guidelines.

Handles documents focused on:
- Diagnostic criteria and algorithms
- Test interpretation thresholds (FEV1/FVC, TSH, TST, Bethesda, etc.)
- Workup sequencing and imaging decision trees
- Incidentaloma management
- Decision-making frameworks

Examples from gold_list:
  PDF 6  — Office Spirometry
  PDF 8  — Medical Decision-Making Capacity
  PDF 9  — Thyroid Nodules
  PDF 11 — Incidentalomas
  PDF 14 — Peripheral Nerve Entrapment
  PDF 20 — TB Diagnosis Guidelines
"""

from __future__ import annotations
from engines.base_engine import BaseEngine
from utils.prompt_builder import llm_extract


class DiagnosticEngine(BaseEngine):

    DOCUMENT_TYPE = "diagnostic_guideline"

    def activate_modules(self) -> None:
        self.modules = [
            "diagnostic_criteria",
            "test_thresholds",
            "workup_algorithm",
            "result_interpretation",
            "referral_indications",
            "follow_up_imaging",
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
