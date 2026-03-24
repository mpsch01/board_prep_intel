"""
preprocess.py — Document ingestion with PDF, TXT, and ZIP-bundle support.

Handles:
  - Standard PDFs (.pdf) via pdfplumber
  - Plain text / markdown (.txt, .md)
  - ZIP bundles disguised as .pdf containing numbered .txt files
    (format used by JACC, NEJM, USPSTF project files)
  - Plain-text clinical guidelines stored as raw text inside .pdf extension
"""

from __future__ import annotations
import os
import re
import zipfile


def preprocess(file_path: str) -> str:
    """
    Load and normalize a document. Auto-detects format by magic bytes.
    Returns cleaned full-text string.
    """
    # Detect by magic bytes first (more reliable than extension)
    with open(file_path, "rb") as f:
        magic = f.read(8)

    if magic[:4] == b"PK\x03\x04":
        # ZIP archive — extract all numbered .txt files in order
        return _extract_zip_bundle(file_path)
    elif magic[:4] == b"%PDF":
        # True PDF binary
        return _extract_pdf(file_path)
    else:
        # Plain text (including text masquerading as .pdf)
        return _extract_text(file_path)


def _extract_zip_bundle(file_path: str) -> str:
    """
    Extract text from a ZIP bundle containing numbered .txt files.
    Files are sorted numerically (1.txt, 2.txt, ...) and concatenated.
    """
    with zipfile.ZipFile(file_path, "r") as z:
        txt_names = sorted(
            [n for n in z.namelist() if n.endswith(".txt")],
            key=lambda n: int(os.path.splitext(os.path.basename(n))[0])
                          if os.path.splitext(os.path.basename(n))[0].isdigit()
                          else 0
        )
        if not txt_names:
            raise ValueError(f"ZIP bundle contains no .txt files: {file_path}")

        chunks = []
        for name in txt_names:
            text = z.read(name).decode("utf-8", errors="replace").strip()
            if text:
                chunks.append(text)

    full_text = "\n\n".join(chunks)
    return _clean_text(full_text)


def _extract_pdf(file_path: str) -> str:
    try:
        import pdfplumber
    except ImportError:
        raise ImportError("pdfplumber required for PDF support. Run: pip install pdfplumber")

    chunks = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            text = text.strip()
            if text:
                chunks.append(text)

    full_text = "\n\n".join(chunks)
    return _clean_text(full_text)


def _extract_text(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        return _clean_text(f.read())


def _clean_text(text: str) -> str:
    """Normalize whitespace and remove control characters."""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_first_chunk(file_path: str, max_chars: int = 3000) -> str:
    """
    Return only the first N characters of the document.
    Used by screening classifier to avoid sending the entire doc.
    """
    return preprocess(file_path)[:max_chars]
