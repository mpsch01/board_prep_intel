"""
build_v6_resident.py  (v3 - CORRECTED)
=======================================
Produces BoardPrep-ContentOutline_HY-ENRICHED-v6-resident.docx

Structure per session:
  [Heading1: Session N: Title]
    -> [ITE callout]         immediately after heading (blue, with QIDs restored)
    -> [Session content]     full session body
    -> [Poll callout]        at END of session, before next heading (teal, max 5 Qs)

Fixes from prior run:
  - QIDs restored:  "Q1  [2021]  Q2021-291"
  - Poll position:  injected BEFORE each Heading1 (=end of prior session)
  - Poll count:     max 5 questions (first 5)
  - Poll numbering: clean "Q1 [Poll]" format, no odd right-side numbering
"""

import zipfile, re, json, os, random, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
SRC_DOCX  = SCRIPT_DIR.parent / "source" / "00_EX_content_outline_w_q.docx"
OUT_DOCX  = SCRIPT_DIR.parent / "outputs" / "BoardPrep-ContentOutline_HY-ENRICHED-v6-resident.docx"
ITE_JSON  = PROJECT_ROOT / "key_data_files" / "session_hy_inserts_v7.json"
POLL_JSON = PROJECT_ROOT / "key_data_files" / "poll_inserts.json"

MAX_ITE_QS  = 5
MAX_POLL_QS = 5
MAX_REFS    = 8

# ITE palette — blue
CLR_DARK  = '1F3864'
CLR_MID   = '2E75B6'
CLR_LIGHT = 'D6E4F7'
CLR_WHITE = 'FFFFFF'
CLR_MUST  = 'FFF2CC'
CLR_CORE  = 'EBF3FB'
CLR_TEXT  = '000000'
CLR_SUB   = '333333'
CLR_NAVY  = '1F3864'

# Poll palette — teal
CLR_T_DARK  = '1B6B5A'
CLR_T_MID   = '2E9E7E'
CLR_T_LIGHT = 'D4EDE7'
CLR_T_BODY  = 'A8D8CE'
CLR_T_TEXT  = '0D3D30'

def rand_id():
    return ''.join(random.choices('0123456789ABCDEF', k=8))

def esc(t):
    return str(t).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;')

def styled_para(text, fill, text_color='000000', size=20, bold=False, italic=False,
                indent=0, space_before=0, space_after=0,
                top_border=False, bottom_border=False, border_color='000000'):
    pid = rand_id()
    b   = '<w:b/><w:bCs/>' if bold else ''
    i   = '<w:i/><w:iCs/>' if italic else ''
    rpr = (f'<w:rFonts w:ascii="Aptos" w:hAnsi="Aptos"/>{b}{i}'
           f'<w:sz w:val="{size}"/><w:szCs w:val="{size}"/>'
           f'<w:color w:val="{text_color}"/>')
    shd = f'<w:shd w:val="clear" w:color="auto" w:fill="{fill}"/>'
    ind = f'<w:ind w:left="{indent}" w:right="0"/>' if indent else ''
    spc = f'<w:spacing w:before="{space_before}" w:after="{space_after}"/>'
    bdr_parts = []
    if top_border:
        bdr_parts.append(f'<w:top w:val="single" w:sz="12" w:color="{border_color}"/>')
    if bottom_border:
        bdr_parts.append(f'<w:bottom w:val="single" w:sz="4" w:color="{border_color}"/>')
    bdr = f'<w:pBdr>{"".join(bdr_parts)}</w:pBdr>' if bdr_parts else ''
    ppr = f'<w:pPr>{bdr}{shd}{spc}{ind}<w:rPr>{rpr}</w:rPr></w:pPr>'
    return (f'<w:p w14:paraId="{pid}" w14:textId="77777777" '
            f'w:rsidR="00CC0000" w:rsidRDefault="00CC0000">'
            f'{ppr}'
            f'<w:r><w:rPr>{rpr}</w:rPr>'
            f'<w:t xml:space="preserve">{esc(text)}</w:t></w:r>'
            f'</w:p>')

def blank():
    return styled_para('', fill=CLR_WHITE, size=6, space_before=60, space_after=60)

def build_ite_callout(sess):
    """ITE block — clean, QIDs restored, larger text, no scores/tags/counts."""
    sid    = sess['session_id']
    sname  = sess['session_title']
    q_list = sess.get('questions', [])[:MAX_ITE_QS]
    refs   = [r for r in sess.get('refs', [])
              if r['tier'] in ('Must-Read', 'Core')][:MAX_REFS]
    INDENT = 180
    paras  = []

    # Header — no metadata counts
    paras.append(styled_para(
        f'  \u25A0  ITE HIGH-YIELD   \u2022   Session {int(sid)}: {sname}',
        fill=CLR_DARK, text_color=CLR_WHITE, size=24, bold=True,
        space_before=120, space_after=0,
        top_border=True, border_color=CLR_DARK))

    if q_list:
        paras.append(styled_para(
            '  ITE EXAM QUESTIONS',
            fill=CLR_MID, text_color=CLR_WHITE, size=20, bold=True,
            space_before=0, space_after=0))

        for i, q in enumerate(q_list, 1):
            yr    = q.get('year', '?')
            qid   = q.get('qid', '')
            focus = q.get('focus', '')
            # QID restored: "Q1  [2021]  Q2021-291"
            paras.append(styled_para(
                f'  Q{i}   [{yr}]   {qid}',
                fill=CLR_LIGHT, text_color=CLR_NAVY, size=20, bold=True,
                space_before=40, space_after=0, indent=INDENT))
            paras.append(styled_para(
                f'  {focus}',
                fill=CLR_LIGHT, text_color=CLR_SUB, size=19,
                space_before=0, space_after=20, indent=INDENT))

    if refs:
        paras.append(styled_para(
            '  KEY REFERENCES',
            fill=CLR_MID, text_color=CLR_WHITE, size=20, bold=True,
            space_before=0, space_after=0))
        for idx_r, r in enumerate(refs):
            is_must = r['tier'] == 'Must-Read'
            row_fill  = CLR_MUST if is_must else CLR_CORE
            tier_label = '\u2605 Must-Read' if is_must else 'Core'
            tier_color = 'B8860B' if is_must else '2E75B6'
            # Tier label row — small, colored, tight spacing
            paras.append(styled_para(
                f'   {tier_label}',
                fill=row_fill, text_color=tier_color, size=15, bold=True,
                space_before=28 if idx_r > 0 else 12, space_after=0,
                indent=INDENT, top_border=(idx_r > 0), border_color='C8C8C8'))
            # Citation row — full size, readable
            paras.append(styled_para(
                f'   {r["citation"]}',
                fill=row_fill, text_color=CLR_TEXT, size=18,
                space_before=0, space_after=8, indent=INDENT))

    paras.append(styled_para(
        '', fill=CLR_DARK, size=4, space_before=0, space_after=0,
        bottom_border=True, border_color=CLR_DARK))
    paras.append(blank())
    return ''.join(paras)


def build_poll_callout(sess):
    """Poll block — teal, mirrors ITE style, max 5 questions, goes at END of session."""
    sid    = sess['session_id']
    sname  = sess['session_title']
    qs     = sess.get('questions', [])[:MAX_POLL_QS]   # first 5 only
    INDENT = 180
    paras  = []

    # Header bar
    paras.append(styled_para(
        f'  \u25A0  AAFP BOARD PREP POLL QUESTIONS   \u2022   Session {int(sid)}: {sname}',
        fill=CLR_T_DARK, text_color=CLR_WHITE, size=24, bold=True,
        space_before=120, space_after=0,
        top_border=True, border_color=CLR_T_DARK))

    paras.append(styled_para(
        f'  PRACTICE QUESTIONS  ({len(qs)} questions)',
        fill=CLR_T_MID, text_color=CLR_WHITE, size=20, bold=True,
        space_before=0, space_after=0))

    for i, q in enumerate(qs, 1):
        stem    = q['stem']
        ctx     = q.get('context_short', False)
        choices = q.get('choices', {})

        # Q number row — clean label, no odd right-side text
        paras.append(styled_para(
            f'  Q{i}',
            fill=CLR_T_LIGHT, text_color=CLR_T_DARK, size=20, bold=True,
            space_before=40, space_after=0, indent=INDENT))

        # Stem
        stem_display = stem if not ctx else f'{stem}  [See session slides for context]'
        paras.append(styled_para(
            f'  {stem_display}',
            fill=CLR_T_LIGHT, text_color=CLR_T_TEXT, size=19,
            space_before=0, space_after=0, indent=INDENT))

        # Answer choices
        for letter in ['A', 'B', 'C', 'D']:
            val = choices.get(letter)
            if val:
                paras.append(styled_para(
                    f'     {letter})  {val}',
                    fill=CLR_T_BODY, text_color=CLR_T_TEXT, size=18,
                    space_before=0, space_after=0, indent=INDENT + 180))

        # Spacer between questions
        paras.append(styled_para(
            '', fill=CLR_T_LIGHT, size=6,
            space_before=0, space_after=24, indent=INDENT))

    paras.append(styled_para(
        '', fill=CLR_T_DARK, size=4, space_before=0, space_after=0,
        bottom_border=True, border_color=CLR_T_DARK))
    paras.append(blank())
    return ''.join(paras)

def main():
    print('Loading inserts...')
    with open(ITE_JSON, encoding='utf-8') as f:
        ite_data = json.load(f)
    with open(POLL_JSON, encoding='utf-8') as f:
        poll_data = json.load(f)
    print(f'  ITE: {len(ite_data)} sessions | Poll: {len(poll_data)} sessions')

    print('Reading source DOCX (v3)...')
    with zipfile.ZipFile(SRC_DOCX, 'r') as z:
        files = {n: z.read(n) for n in z.namelist()}
    xml_str = files['word/document.xml'].decode('utf-8')

    # Strip any existing injected callout paragraphs
    fill_pat = re.compile(
        r'<w:p\b[^>]*>(?:(?!<w:p\b).)*?'
        r'w:fill="(?:1F3864|2E75B6|D6E4F7|FFF2CC|EBF3FB|1B6B5A|2E9E7E|D4EDE7|A8D8CE)"'
        r'(?:(?!</w:p>).)*?</w:p>', re.DOTALL)
    xml_clean = fill_pat.sub('', xml_str)
    print(f'  Stripped {len(fill_pat.findall(xml_str))} existing callout paragraphs')

    # Build all callout strings keyed by zero-padded session id
    ite_blocks  = {str(int(k)).zfill(2): build_ite_callout(v) for k, v in ite_data.items()}
    poll_blocks = {str(int(k)).zfill(2): build_poll_callout(v) for k, v in poll_data.items()}
    print(f'  Built {len(ite_blocks)} ITE + {len(poll_blocks)} Poll blocks')

    # ── INJECTION STRATEGY ────────────────────────────────────────────────────
    # ITE block: inject AFTER each Heading1 "Session N:" paragraph
    # Poll block: inject BEFORE each Heading1 "Session N:" paragraph
    #             (= end of the PREVIOUS session's content)
    #             Special case: poll for session 49 (last) appended at body end
    #
    # We do this in two passes on the XML string.

    heading_pat = re.compile(
        r'(<w:p\b[^>]*>(?:(?!<w:p\b).)*?'
        r'<w:pStyle w:val="Heading1"/>(?:(?!<w:p\b).)*?'
        r'Session\s+(\d+):'
        r'(?:(?!</w:p>).)*?</w:p>)', re.DOTALL)

    ite_injected  = 0
    poll_injected = 0

    # Pass 1: inject ITE block AFTER heading, and poll block for PREVIOUS session BEFORE heading
    prev_sid = None

    def inject_both(m):
        nonlocal ite_injected, poll_injected, prev_sid
        heading_xml = m.group(1)
        cur_sid     = m.group(2).zfill(2)

        before = ''
        if prev_sid and prev_sid in poll_blocks:
            before = poll_blocks[prev_sid]
            poll_injected += 1

        after = ''
        if cur_sid in ite_blocks:
            after = ite_blocks[cur_sid]
            ite_injected += 1

        prev_sid = cur_sid
        return before + heading_xml + after

    new_xml = heading_pat.sub(inject_both, xml_clean)

    # Pass 2: append last session's poll block before </w:body>
    last_sid = max(poll_blocks.keys(), key=int)
    if last_sid in poll_blocks:
        new_xml = new_xml.replace('</w:body>', poll_blocks[last_sid] + '</w:body>', 1)
        poll_injected += 1

    print(f'  ITE injected: {ite_injected} | Poll injected: {poll_injected}')

    files['word/document.xml'] = new_xml.encode('utf-8')
    os.makedirs(os.path.dirname(OUT_DOCX), exist_ok=True)
    with zipfile.ZipFile(OUT_DOCX, 'w', zipfile.ZIP_DEFLATED) as zout:
        for name, data in files.items():
            zout.writestr(name, data)

    size_mb = os.path.getsize(OUT_DOCX) / 1024 / 1024
    print(f'\nOutput: {OUT_DOCX}  ({size_mb:.2f} MB)')
    print('Done!')

if __name__ == '__main__':
    main()
