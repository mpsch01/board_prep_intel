"""
screening.py -- LLM-based document classifier.

Replaces the single-keyword heuristic with a Claude API call
that returns document_type, confidence, signals, and body_systems.

v2.3: Added RCT pre-screen heuristic to catch NEJM/Lancet/JAMA articles
before LLM call. Journal headers are fragmented by pdfplumber column
extraction and lack Methods/randomization signal in the first 3000 chars,
causing LLM to return 'unknown'. Pre-screen checks for journal name patterns
and bumps screening window to 5000 chars.
"""

from __future__ import annotations
import re
from utils.preprocess import extract_first_chunk
from utils.prompt_builder import llm_screen


VALID_TYPES = {
    "chronic_guideline",
    "acute_protocol",
    "preventive_guideline",
    "diagnostic_guideline",
    "rct",
    "unknown",
}

# Journal name patterns that strongly indicate RCT/primary research
RCT_JOURNAL_PATTERNS = [
    r"new england journal of medicine",
    r"n\s*engl\s*j\s*med",
    r"nejm\.org",
    r"the lancet",
    r"lancet\.com",
    r"jama\b",
    r"journal of the american medical association",
    r"annals of internal medicine",
    r"bmj\b",
    r"british medical journal",
]

# Keywords within those journal articles that confirm RCT (not review/editorial)
RCT_CONTENT_PATTERNS = [
    r"\brandom\w+",
    r"\btrial\b",
    r"\bplacebo\b",
    r"\bhazard ratio\b",
    r"\bconfidence interval\b",
    r"\bp\s*[=<]\s*0\.\d+",
    r"\bintention.to.treat\b",
    r"\bprimary (end ?point|outcome)\b",
]


def _prescreen_rct(text: str) -> bool:
    """
    Fast heuristic: returns True if this looks like a primary research
    article from a major journal (NEJM, Lancet, JAMA, etc.) reporting
    a trial. Runs before the LLM call to avoid 'unknown' misclassification.
    """
    lower = text.lower()
    journal_match = any(re.search(p, lower) for p in RCT_JOURNAL_PATTERNS)
    if not journal_match:
        return False
    content_match = sum(1 for p in RCT_CONTENT_PATTERNS if re.search(p, lower))
    return content_match >= 2


def screening_classifier(text: str) -> dict:
    """
    Classify a document using Claude, with RCT pre-screen heuristic.

    Args:
        text: Full document text (first 5000 chars sent to screener)

    Returns:
        dict with keys:
            - document_type: str
            - confidence: float
            - signals: list[str]
            - body_systems: list[str]
            - numeric_threshold_present: bool
    """
    # v2.3: RCT pre-screen before LLM call
    if _prescreen_rct(text[:5000]):
        return {
            "document_type": "rct",
            "confidence": 0.90,
            "signals": ["journal name match", "trial content keywords detected"],
            "body_systems": [],
            "numeric_threshold_present": True,
        }

    # Pass 5000 chars to screener (up from 3000) for better signal coverage
    result = llm_screen(text[:5000])

    # Validate and normalize
    doc_type = result.get("document_type", "unknown")
    if doc_type not in VALID_TYPES:
        doc_type = "unknown"

    return {
        "document_type": doc_type,
        "confidence": float(result.get("confidence", 0.5)),
        "signals": result.get("signals", []),
        "body_systems": result.get("body_systems", []),
        "numeric_threshold_present": bool(result.get("numeric_threshold_present", False)),
    }


def screening_classifier_from_file(file_path: str) -> dict:
    """
    Convenience wrapper -- reads first chunk from file before screening.
    """
    chunk = extract_first_chunk(file_path, max_chars=5000)
    return screening_classifier(chunk)
