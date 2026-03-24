"""
routing.py — Routes screening results to the correct engine.
"""

from __future__ import annotations
from engines.chronic_engine import ChronicRiskEngine
from engines.acute_engine import AcuteProtocolEngine
from engines.preventive_engine import PreventiveEngine
from engines.diagnostic_engine import DiagnosticEngine
from engines.rct_engine import RCTEngine


ENGINE_MAP = {
    "chronic_guideline":    ChronicRiskEngine,
    "acute_protocol":       AcuteProtocolEngine,
    "preventive_guideline": PreventiveEngine,
    "diagnostic_guideline": DiagnosticEngine,
    "rct":                  RCTEngine,
    "unknown":              ChronicRiskEngine,
}


def route_document(screening_result: dict):
    """
    Select the appropriate engine class based on screening classification.
    Returns an instantiated engine object.
    """
    doc_type = screening_result.get("document_type", "unknown")
    engine_class = ENGINE_MAP.get(doc_type, ChronicRiskEngine)
    return engine_class(screening_result)
