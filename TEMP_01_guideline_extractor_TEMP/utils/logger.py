"""
logger.py — Timestamped, per-run logging with session summary support.
Each run writes its own JSON file. A session summary is maintained separately.
"""

from __future__ import annotations
import json
import os
import datetime


LOG_DIR = "logs"


def _ensure_log_dir() -> None:
    os.makedirs(LOG_DIR, exist_ok=True)


def _timestamp() -> str:
    return datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")


def log_run(output: dict, run_id: str = None) -> str:
    """
    Write a single extraction run to its own timestamped JSON log file.

    Args:
        output: Full extraction output dict
        run_id: Optional run identifier

    Returns:
        Path to log file written
    """
    _ensure_log_dir()

    ts = _timestamp()
    rid = run_id or output.get("metadata", {}).get("run_id", "unknown")
    file_name = output.get("source", {}).get("file_name", "unknown")
    doc_type = output.get("classification", {}).get("document_type", "unknown")
    validation_passed = output.get("metadata", {}).get("validation_passed", None)
    warnings = output.get("metadata", {}).get("validation_warnings", [])

    log_entry = {
        "timestamp": ts,
        "run_id": rid,
        "file_name": file_name,
        "document_type": doc_type,
        "engine_used": output.get("classification", {}).get("engine_used", ""),
        "confidence": output.get("classification", {}).get("confidence", None),
        "body_systems": output.get("classification", {}).get("body_systems", []),
        "modules_activated": output.get("metadata", {}).get("modules_activated", []),
        "raw_text_chars": output.get("metadata", {}).get("raw_text_chars", 0),
        "validation_passed": validation_passed,
        "validation_warnings": warnings,
        "recommendations_count": len(output.get("extraction", {}).get("recommendations", [])),
        "thresholds_count": len(output.get("extraction", {}).get("key_thresholds", [])),
        "medications_count": len(output.get("extraction", {}).get("medications", [])),
    }

    log_path = os.path.join(LOG_DIR, f"run_{ts}_{rid}.json")
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log_entry, f, indent=2)

    # Also append to session log
    _append_to_session_log(log_entry)

    return log_path


def _append_to_session_log(entry: dict) -> None:
    """Append this run's summary to the running session log."""
    session_path = os.path.join(LOG_DIR, "session_log.jsonl")
    with open(session_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def load_session_summary() -> list[dict]:
    """Load all entries from the session log."""
    session_path = os.path.join(LOG_DIR, "session_log.jsonl")
    if not os.path.exists(session_path):
        return []
    entries = []
    with open(session_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return entries
