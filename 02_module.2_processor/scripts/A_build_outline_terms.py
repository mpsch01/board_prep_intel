"""
Script A: build_outline_terms.py

Parses BoardPrep-ContentOutline_SESSION-MAPPED-v2.docx XML per session.
Extracts all heading and bullet text for each session block.
Output: outline_terms.json
"""

import zipfile, re, json, os
from xml.etree import ElementTree as ET

DOCX     = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\01_source\BoardPrep-ContentOutline_SESSION-MAPPED-v2.docx'
OUT_JSON = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\keyword_library\raw_files\outline_terms.json'

NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

def para_text(p):
    return ''.join(t.text or '' for t in p.findall('.//w:t', NS)).strip()

def para_style(p):
    pr = p.find('w:pPr/w:pStyle', NS)
    if pr is not None:
        return pr.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val', 'Normal')
    return 'Normal'

def extract_terms(raw_text):
    """Split outline text into candidate terms, preserving abbreviations."""
    # Strip leading outline numbering (A., 1., ii., etc.)
    text = re.sub(r'^[A-Za-z0-9]{1,3}[\.\)]\s*', '', raw_text)

    # Split on concept-separating delimiters
    parts = re.split(r'[/&;]|(?:\s*,\s*)|\s+(?:and|or|vs\.?)\s+', text, flags=re.IGNORECASE)

    terms = []
    for part in parts:
        # Extract parenthetical abbreviations AND the full term separately
        abbrev_match = re.search(r'\(([A-Z]{2,6})\)', part)
        if abbrev_match:
            abbrev = abbrev_match.group(1)
            full   = re.sub(r'\s*\([^)]*\)', '', part).strip()
            if len(full) > 2:
                terms.append(full)
            terms.append(abbrev)
        else:
            cleaned = re.sub(r'\s*\([^)]*\)', '', part).strip()
            if len(cleaned) > 2 and not cleaned.isdigit():
                terms.append(cleaned)

    return terms


# ── parse docx ─────────────────────────────────────────────────────────
with zipfile.ZipFile(DOCX) as z:
    raw = z.read('word/document.xml')

tree  = ET.fromstring(raw)
body  = tree.find('.//w:body', NS)
paras = body.findall('w:p', NS)
print(f'Total paragraphs: {len(paras)}')

# Find Heading1 session anchors
session_starts = []
for i, p in enumerate(paras):
    if para_style(p) == 'Heading1':
        txt = para_text(p)
        m   = re.match(r'Session\s+(\d+):\s*(.+)', txt)
        if m:
            session_starts.append((i, m.group(1).zfill(2), m.group(2).strip()))

print(f'Sessions found: {len(session_starts)}')

# Collect terms per session
results = {}
for idx, (start_i, snum, sname) in enumerate(session_starts):
    end_i = session_starts[idx + 1][0] if idx + 1 < len(session_starts) else len(paras)

    all_terms  = []
    raw_lines  = []

    for p in paras[start_i + 1 : end_i]:
        txt = para_text(p)
        if not txt:
            continue
        raw_lines.append(txt)
        all_terms.extend(extract_terms(txt))

    # Deduplicate preserving order, case-insensitive
    seen, unique_terms = set(), []
    for t in all_terms:
        key = t.lower().strip()
        if key and key not in seen and len(key) > 2:
            seen.add(key)
            unique_terms.append(t.strip())

    results[snum] = {
        'session_name':    sname,
        'term_count':      len(unique_terms),
        'raw_line_count':  len(raw_lines),
        'terms':           unique_terms
    }
    print(f'  {snum}: {sname[:45]:45s} | {len(raw_lines):4d} lines | {len(unique_terms):4d} terms')

# ── write ──────────────────────────────────────────────────────────────
with open(OUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

total = sum(v['term_count'] for v in results.values())
print(f'\nDone. Output: {OUT_JSON}')
print(f'Total unique terms across all sessions: {total}')
