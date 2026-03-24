"""
04_inject_poll_questions.py
============================
Appends poll question callout blocks to the end of each session
in BoardPrep-ContentOutline_HY-ENRICHED-v5.docx -> v6.docx.

Design:
- Amber/gold color scheme to distinguish from blue ITE callout blocks
- Header: "AAFP Poll Questions — Session XX: [Title]"
- Each question: stem + A/B/C/D choices
- No correct answer shown (residents work it first)
- Attribution: "Poll question — AAFP Board Prep Session XX"
- Context-short questions get a note: "[See session slides for context]"
"""

import sys, zipfile, re, json, os
import xml.etree.ElementTree as ET
sys.stdout.reconfigure(encoding='utf-8')
sys.stdout.reconfigure(encoding='utf-8')

SRC_DOCX   = r'C:\Users\mpsch\Desktop\claude_knowledge\00_canonical\01_curriculum\ABFM_BoardPrep_ContentOutline_HY-Enriched_v5.docx'
OUT_DOCX   = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\04_outputs\BoardPrep-ContentOutline_HY-ENRICHED-v6.docx'
POLL_JSON  = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\03_poll_questions\poll_inserts.json'

# Amber/gold palette
CLR_AMBER_DARK  = '7F4F24'   # dark amber header text bg
CLR_AMBER_MID   = 'C07000'   # amber accent
CLR_AMBER_LIGHT = 'FFF2CC'   # light amber question bg
CLR_AMBER_BODY  = 'FAE3A0'   # slightly deeper for choice rows
CLR_WHITE       = 'FFFFFF'
CLR_DARK_TEXT   = '1A1A1A'

NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
W  = f'{{{NS}}}'

def w(tag):     return f'{W}{tag}'
def wattr(k):   return f'{W}{k}'

def shading_elem(fill):
    e = ET.Element(w('shd'))
    e.set(wattr('val'),  'clear')
    e.set(wattr('fill'), fill)
    e.set(wattr('color'),'auto')
    return e

def run(text, bold=False, size=18, color='000000', font='Arial'):
    r = ET.Element(w('r'))
    rpr = ET.SubElement(r, w('rPr'))
    if bold:
        ET.SubElement(rpr, w('b'))
    rFonts = ET.SubElement(rpr, w('rFonts'))
    rFonts.set(wattr('ascii'), font)
    rFonts.set(wattr('hAnsi'), font)
    sz = ET.SubElement(rpr, w('sz'))
    sz.set(wattr('val'), str(size))
    szCs = ET.SubElement(rpr, w('szCs'))
    szCs.set(wattr('val'), str(size))
    clr = ET.SubElement(rpr, w('color'))
    clr.set(wattr('val'), color)
    t = ET.SubElement(r, w('t'))
    t.text = text
    if text and (text[0] == ' ' or text[-1] == ' '):
        t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
    return r

def para(runs_list, bg=None, spacing_before=60, spacing_after=60, indent=None):
    p = ET.Element(w('p'))
    pPr = ET.SubElement(p, w('pPr'))
    sp = ET.SubElement(pPr, w('spacing'))
    sp.set(wattr('before'), str(spacing_before))
    sp.set(wattr('after'),  str(spacing_after))
    if bg:
        pPr.append(shading_elem(bg))
    if indent:
        ind = ET.SubElement(pPr, w('ind'))
        ind.set(wattr('left'), str(indent))
    for r in runs_list:
        p.append(r)
    return p

def build_poll_block(session_data):
    """Build the amber poll question callout block for one session."""
    sid   = session_data['session_id']
    title = session_data['session_title']
    qs    = session_data['questions']
    elems = []

    # ── Header bar ────────────────────────────────────────────────────────────
    elems.append(para(
        [run(f'  AAFP Poll Questions \u2014 Session {sid}: {title}',
             bold=True, size=20, color=CLR_WHITE, font='Arial')],
        bg=CLR_AMBER_DARK, spacing_before=120, spacing_after=0
    ))

    # ── Subheader ─────────────────────────────────────────────────────────────
    elems.append(para(
        [run(f'  {len(qs)} practice questions from the AAFP Board Prep presentation. '
             'Work each question before checking the answer key.',
             bold=False, size=17, color=CLR_AMBER_DARK, font='Arial')],
        bg=CLR_AMBER_LIGHT, spacing_before=0, spacing_after=0
    ))

    # ── Questions ─────────────────────────────────────────────────────────────
    for i, q in enumerate(qs, 1):
        stem  = q['stem']
        ctx   = q.get('context_short', False)
        pid   = q['poll_id']
        choices = q.get('choices', {})

        # Question number + stem
        stem_text = f'  {i}.  {stem}'
        if ctx:
            stem_text += '  [See session slides for full context]'
        elems.append(para(
            [run(stem_text, bold=False, size=18, color=CLR_DARK_TEXT, font='Arial')],
            bg=CLR_AMBER_LIGHT, spacing_before=80, spacing_after=0, indent=180
        ))

        # Answer choices
        for letter in ['A', 'B', 'C', 'D']:
            val = choices.get(letter)
            if val:
                elems.append(para(
                    [run(f'      {letter})  {val}',
                         bold=False, size=17, color='3D3D3D', font='Arial')],
                    bg=CLR_AMBER_BODY, spacing_before=20, spacing_after=0, indent=360
                ))

        # Attribution line
        elems.append(para(
            [run(f'      Poll question \u2014 AAFP Board Prep Session {sid}',
                 bold=False, size=15, color='888888', font='Arial')],
            bg=CLR_AMBER_LIGHT, spacing_before=20, spacing_after=60, indent=360
        ))

    # ── Footer spacer ─────────────────────────────────────────────────────────
    elems.append(para(
        [run('', size=14)],
        bg=CLR_AMBER_DARK, spacing_before=40, spacing_after=120
    ))

    return elems

def main():
    print('Loading poll inserts...')
    with open(POLL_JSON, encoding='utf-8') as f:
        poll_data = json.load(f)
    print(f'  {len(poll_data)} sessions loaded')

    print('Reading source DOCX (v5)...')
    with zipfile.ZipFile(SRC_DOCX, 'r') as z:
        doc_xml  = z.read('word/document.xml')
        all_files = {name: z.read(name) for name in z.namelist()}

    # Parse
    ET.register_namespace('', NS)
    root = ET.fromstring(doc_xml)
    body = root.find(f'.//{w("body")}')
    paragraphs = list(body)

    # ── Find session anchor paragraphs ────────────────────────────────────────
    # Sessions are headed by a line matching "Session XX" in a heading style
    # or by the ITE callout header we injected. We look for the LAST paragraph
    # of each session's existing ITE callout (the blue footer bar) and insert
    # the poll block immediately after it.
    #
    # The ITE callout footer bar contains text matching:
    #   "ITE Questions — Session XX" pattern inside a dark-blue shaded para.
    # We identify these by scanning for paragraphs whose shading fill == 1F3864
    # (CLR_DARK from the inject script) that contain "Session" text.

    # Build lookup: session_id (zero-padded str) -> poll block elements
    def find_ite_footer_indices(paragraphs):
        """
        Return list of (insert_after_index, session_id) tuples.
        We look for the last paragraph in each ITE block — the dark-blue footer spacer.
        Strategy: find runs of consecutive paragraphs with fill=1F3864, take the last.
        """
        results = []
        i = 0
        while i < len(paragraphs):
            p = paragraphs[i]
            xml_str = ET.tostring(p, encoding='unicode')
            # Check if this paragraph is part of a blue callout block
            if '1F3864' in xml_str and 'Session' in xml_str:
                # Walk forward to find the end of this callout block
                block_start = i
                j = i
                while j < len(paragraphs):
                    pj_xml = ET.tostring(paragraphs[j], encoding='unicode')
                    if '1F3864' not in pj_xml and 'D6E4F7' not in pj_xml and '2E75B6' not in pj_xml:
                        break
                    j += 1
                block_end = j - 1

                # Extract session ID from text in this block
                sid_match = re.search(r'Session\s+(\d+)', xml_str)
                if sid_match:
                    sid = sid_match.group(1).zfill(2)
                    results.append((block_end, sid))
                    i = j
                    continue
            i += 1
        return results

    anchors = find_ite_footer_indices(paragraphs)
    print(f'  Found {len(anchors)} ITE callout blocks')

    # Deduplicate — keep last occurrence per session (in case of duplicates)
    seen = {}
    for idx, sid in anchors:
        seen[sid] = idx
    anchors_clean = sorted(seen.items(), key=lambda x: x[1], reverse=True)  # reverse for safe insertion

    # Insert poll blocks (reverse order so indices stay valid)
    inserted = 0
    skipped  = []
    for sid, insert_after in anchors_clean:
        if sid not in poll_data:
            skipped.append(sid)
            continue
        block_elems = build_poll_block(poll_data[sid])
        # Insert after insert_after index
        for offset, elem in enumerate(block_elems):
            body.insert(insert_after + 1 + offset, elem)
        inserted += 1

    print(f'  Sessions injected: {inserted}')
    if skipped:
        print(f'  Skipped (no poll data): {skipped}')

    # Serialize
    new_xml = ET.tostring(root, encoding='unicode', xml_declaration=False)
    new_xml = '<?xml version=\'1.0\' encoding=\'UTF-8\' standalone=\'yes\'?>\n' + new_xml

    # Write output
    os.makedirs(os.path.dirname(OUT_DOCX), exist_ok=True)
    with zipfile.ZipFile(SRC_DOCX, 'r') as zin:
        with zipfile.ZipFile(OUT_DOCX, 'w', zipfile.ZIP_DEFLATED) as zout:
            for item in zin.namelist():
                if item == 'word/document.xml':
                    zout.writestr(item, new_xml.encode('utf-8'))
                else:
                    zout.writestr(item, zin.read(item))

    size_mb = os.path.getsize(OUT_DOCX) / 1_048_576
    print(f'\nOutput: {OUT_DOCX}')
    print(f'Size:   {size_mb:.2f} MB')
    print('Done!')

if __name__ == '__main__':
    main()
