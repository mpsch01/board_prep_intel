
"""
convert_pdfs_to_json.py

Convert a directory of PDFs into:
- raw_txt/*.raw.txt  (full extracted text)
- json/*.json        (metadata + navigator_v1 scaffold + ingest pointers)
- manifest.json      (index of outputs)

USAGE (PowerShell):
  python convert_pdfs_to_json.py --pdf_dir "C:/Users/mpsch/Desktop/gold_list"

Optional:
  python convert_pdfs_to_json.py --pdf_dir "C:/Users/mpsch/Desktop/gold_list" --out_dir "C:/path/to/outputs"
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import date
from typing import Any, Dict, List, Optional

import pdfplumber


ENGINE_VERSION = "ite_pdf_to_json_v1.1"


def ensure_dirs(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def slugify(s: str, max_len: int = 80) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return (s[:max_len] if s else "doc")


def extract_first_page_text(pdf_path: str, max_chars: int = 4000) -> str:
    """Extract a chunk of first-page text to help infer title/year."""
    with pdfplumber.open(pdf_path) as pdf:
        if not pdf.pages:
            return ""
        page = pdf.pages[0]
        text = page.extract_text() or ""
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()[:max_chars]


def extract_full_text(pdf_path: str) -> str:
    """Extract full text from all pages (non-OCR)."""
    chunks: List[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text() or ""
            t = t.strip()
            if t:
                chunks.append(t)
    return "\n\n".join(chunks)


def parse_title_from_text(first_page_text: str) -> str:
    """
    Heuristic title extraction:
    - take up to first ~3 meaningful lines, stopping before credential/affiliation cues.
    """
    lines = [l.strip() for l in first_page_text.splitlines() if l.strip()]
    title_lines: List[str] = []

    stop_cred = re.compile(r"\b(MD|DO|PhD|MPH|MS|RN|PA-C|FACP|FAAFP|FAAP)\b")
    stop_affil = re.compile(r"\b(University|Residency|Center|Hospital|Department|College)\b", re.I)

    for l in lines[:15]:
        # remove obvious headers/footers if present
        if len(l) <= 2:
            continue
        if stop_cred.search(l):
            break
        if stop_affil.search(l) and title_lines:
            break
        title_lines.append(l)
        if len(title_lines) >= 3:
            break

    title = " ".join(title_lines)
    title = re.sub(r"\s+", " ", title).strip()
    return title[:200] if title else "Untitled"


def guess_year(text: str) -> Optional[int]:
    """
    Guess a publication year from early text.
    Looks for 1980-2026.
    """
    m = re.search(r"\b(19[89]\d|20[012]\d|202[0-6])\b", text)
    if not m:
        return None
    y = int(m.group(1))
    return y if 1980 <= y <= 2026 else None


def build_json_payload(
    *,
    title: str,
    year: Optional[int],
    source_id: str,
    pdf_file_name: str,
    pdf_path: str,
    raw_text_path: str,
) -> Dict[str, Any]:
    """
    Create JSON with:
    - core 'source' fields
    - 'ingest' pointers
    - 'navigator_v1' scaffold per your Guideline Navigator v1.0 concept
    - '_classification' placeholder
    """
    today = str(date.today())

    return {
        "engine_version": ENGINE_VERSION,
        "source": {
            "title": title,
            "source_id": source_id,
            "organization": "",
            "document_type": "",
            "publication_year": year,
            "version_number": "",
            "doi": "",
            "canonical_url": "",
            "date_ingested": today,
            "last_verified": "",
            "supersedes": "",
            "status": "active",
            "file_name": pdf_file_name,
        },
        "ingest": {
            "created": today,
            "pdf_path": pdf_path,
            "raw_text_path": raw_text_path,
        },
        "navigator_v1": {
            "section_2_badge": {"badge": "", "rationale": ""},
            "section_3_domain": {"primary_domain": "", "secondary_tags": []},
            "section_4_population": {
                "age_criteria": "",
                "risk_criteria": "",
                "disease_definition": "",
                "exclusions": "",
                "severity_staging": "",
                "staging_system_used": "",
            },
            "section_5_recommendations": [],
            "section_6_pathway_nodes": [],
            "section_7_cross_guideline_impact": {
                "modifies_pathways": [],
                "changes": {
                    "treatment_thresholds": False,
                    "new_drug_class": False,
                    "screening_age": False,
                    "monitoring_frequency": False,
                    "risk_calculation": False,
                },
            },
            "section_8_change_log": [],
            "section_9_internal_qc": {
                "metadata_complete": False,
                "badge_assigned_and_justified": False,
                "recommendations_separated": False,
                "thresholds_extracted_exactly": False,
                "cross_pathway_links_identified": False,
                "prior_version_archived": False,
                "date_verified_entered": False,
            },
        },
        "_classification": {
            "engine": ENGINE_VERSION,
            "tier": None,
            "body_systems": [],
            "notes": "",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert PDFs to JSON + raw text using a navigator_v1 scaffold."
    )
    parser.add_argument(
        "--pdf_dir",
        type=str,
        required=True,
        help= "Path to directory containing PDFs",
    )
    parser.add_argument(
        "--out_dir",
        type=str,
        default=r"C:/Users/mpsch/Desktop/claude_knowledge/board_prep/ite_refs/04_outputs/ingested",
        help="Output folder root (will create json/ and raw_txt/ inside).",
    )
    args = parser.parse_args()

    pdf_dir = os.path.abspath(args.pdf_dir)
    out_dir = os.path.abspath(args.out_dir)

    if not os.path.isdir(pdf_dir):
        print(f"ERROR: --pdf_dir does not exist or is not a directory:\n  {pdf_dir}")
        return 2

    ensure_dirs(out_dir)
    raw_dir = os.path.join(out_dir, "raw_txt")
    json_dir = os.path.join(out_dir, "json")
    ensure_dirs(raw_dir)
    ensure_dirs(json_dir)

    pdfs = [f for f in os.listdir(pdf_dir) if f.lower().endswith(".pdf")]
    pdfs.sort()

    if not pdfs:
        print(f"No PDFs found in: {pdf_dir}")
        return 0

    manifest: List[Dict[str, Any]] = []

    for fname in pdfs:
        pdf_path = os.path.join(pdf_dir, fname)

        try:
            first = extract_first_page_text(pdf_path)
            title = parse_title_from_text(first)
            year = guess_year(first)

            # stable-ish ID based on filename + inferred title
            hid = hashlib.sha1((title + "|" + fname).encode("utf-8")).hexdigest()[:10]
            source_id = f"ITE-{hid}"
            stem = f"{slugify(title)}-{hid}"

            raw_path = os.path.join(raw_dir, f"{stem}.raw.txt")
            full_text = extract_full_text(pdf_path)
            with open(raw_path, "w", encoding="utf-8") as f:
                f.write(full_text)

            data = build_json_payload(
                title=title,
                year=year,
                source_id=source_id,
                pdf_file_name=fname,
                pdf_path=pdf_path,
                raw_text_path=raw_path,
            )

            json_path = os.path.join(json_dir, f"{stem}.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            manifest.append(
                {
                    "pdf": pdf_path,
                    "json": json_path,
                    "raw": raw_path,
                    "title": title,
                    "year": year,
                    "source_id": source_id,
                }
            )

            print(f"Wrote: {os.path.basename(json_path)}")

        except Exception as e:
            print(f"ERROR processing {fname}: {e}", file=sys.stderr)

    manifest_path = os.path.join(out_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print("\nDone.")
    print(f"PDFs processed: {len(manifest)}")
    print(f"Output folder:  {out_dir}")
    print(f"Manifest:       {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())