"""
03_inject_into_outline_v2.py
============================
Injects ITE high-yield callout blocks into the BoardPrep content outline.
Reads session_hy_inserts_v5.json (question-driven schema).

v5 schema per session:
  session_id, session_title, question_count,
  questions: [{qid, year, focus, stem_preview, kw_score, kw_hits}]
  refs:      [{citation, tier, match_score, cited_by}]
  must_read_count, core_count, supplementary_count
"""

import zipfile, re, json, os, random

SRC_DOCX  = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\01_source\BoardPrep-ContentOutline_SESSION-MAPPED-v2.docx'
OUT_DOCX  = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\04_outputs\BoardPrep-ContentOutline_HY-ENRICHED-v2.docx'
JSON_PATH = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\02_working\session_hy_inserts_v5.json'

MAX_ITE_QS = 5
MAX_REFS   = 8   # show up to 8 refs (Must-Read + Core); Supplementary dropped

# Color palette
CLR_DARK   = '1F3864'   # dark navy — header bars
CLR_MID    = '2E75B6'   # mid blue — sub-headers
CLR_LIGHT  = 'D6E4F7'   # light blue — body rows
CLR_WHITE  = 'FFFFFF'
CLR_MUST   = 'FFF2CC'   # amber tint — must-read refs
CLR_CORE   = 'EBF3FB'   # pale blue — core refs
CLR_TEXT   = '000000'
CLR_SUB    = '444444'
CLR_NAVY   = '1F3864'

def rand_id():
    return ''.join(random.choices('0123456789ABCDEF', k=8))

def esc(t):
    return str(t).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;')

def styled_para(text, fill, text_color='000000', size=18, bold=False, italic=False,
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

def blank(space_before=40, space_after=40):
    return styled_para('', fill=CLR_WHITE, size=6,
                       space_before=space_before, space_after=space_after)

def build_callout(sess):
    sid    = sess['session_id']
    sname  = sess['session_title']
    q_list = sess.get('questions', [])[:MAX_ITE_QS]
    refs   = [r for r in sess.get('refs', [])
              if r['tier'] in ('Must-Read', 'Core')][:MAX_REFS]
    mr_ct  = sess.get('must_read_count', 0)
    core_ct= sess.get('core_count', 0)
    q_ct   = sess.get('question_count', 0)

    INDENT = 180
    paras  = []

    # ── Header bar ────────────────────────────────────────────────────
    paras.append(styled_para(
        f'  \u25A0  ITE HIGH-YIELD   \u2022   Session {int(sid)}: {sname}'
        f'   \u2022   {q_ct} questions   |   {mr_ct} must-read  {core_ct} core refs',
        fill=CLR_DARK, text_color=CLR_WHITE, size=19, bold=True,
        space_before=120, space_after=0,
        top_border=True, border_color=CLR_DARK))

    # ── ITE Questions sub-header ───────────────────────────────────────
    if q_list:
        paras.append(styled_para(
            '  ITE EXAM QUESTIONS',
            fill=CLR_MID, text_color=CLR_WHITE, size=16, bold=True,
            space_before=0, space_after=0))

        for i, q in enumerate(q_list, 1):
            yr    = q.get('year', '?')
            qid   = q.get('qid', '')
            focus = q.get('focus', '')
            score = q.get('kw_score', 0)
            hits  = q.get('kw_hits', 0)

            # Question ID + year row
            paras.append(styled_para(
                f'  Q{i}   {yr}   \u2022   {qid}   (match score: {score:.2f}, {hits} keyword hits)',
                fill=CLR_LIGHT, text_color=CLR_NAVY, size=15, bold=True,
                space_before=0, space_after=0, indent=INDENT))
            # Clinical focus row
            paras.append(styled_para(
                f'  {focus}',
                fill=CLR_LIGHT, text_color=CLR_SUB, size=14, italic=True,
                space_before=0, space_after=0, indent=INDENT))

    # ── References sub-header ─────────────────────────────────────────
    if refs:
        paras.append(styled_para(
            '  KEY REFERENCES',
            fill=CLR_MID, text_color=CLR_WHITE, size=16, bold=True,
            space_before=0, space_after=0))

        for r in refs:
            tier  = r['tier']
            cite  = r['citation']
            cited = ', '.join(r.get('cited_by', []))
            row_fill = CLR_MUST if tier == 'Must-Read' else CLR_CORE
            tier_tag = '\u2605 MUST-READ' if tier == 'Must-Read' else 'CORE'

            paras.append(styled_para(
                f'  [{tier_tag}]  {cite}',
                fill=row_fill, text_color=CLR_TEXT, size=14,
                space_before=0, space_after=0, indent=INDENT))
            paras.append(styled_para(
                f'  Cited by: {cited}',
                fill=row_fill, text_color=CLR_SUB, size=12, italic=True,
                space_before=0, space_after=0, indent=INDENT))

    # ── Bottom rule ───────────────────────────────────────────────────
    paras.append(styled_para(
        '', fill=CLR_DARK, size=4,
        space_before=0, space_after=0,
        bottom_border=True, border_color=CLR_DARK))

    paras.append(blank(space_before=60, space_after=60))

    return ''.join(paras)

def main():
    print('Loading v5 JSON inserts...')
    with open(JSON_PATH, encoding='utf-8') as f:
        inserts = json.load(f)
    print(f'  {len(inserts)} sessions loaded')

    print('Reading source DOCX...')
    with zipfile.ZipFile(SRC_DOCX, 'r') as z:
        files = {n: z.read(n) for n in z.namelist()}

    xml_str = files['word/document.xml'].decode('utf-8')

    # Pre-build all callout XML blocks
    callouts = {}
    for sess_id, sess in inserts.items():
        key = str(int(sess_id)).zfill(2)
        callouts[key] = build_callout(sess)
    print(f'  {len(callouts)} callout blocks built')

    # Inject after each Heading1 "Session N:" paragraph
    pattern = re.compile(
        r'(<w:p\b[^>]*>(?:(?!<w:p\b).)*?'
        r'<w:pStyle w:val="Heading1"/>(?:(?!<w:p\b).)*?'
        r'Session\s+(\d+):'
        r'(?:(?!</w:p>).)*?</w:p>)',
        re.DOTALL)

    injected = 0
    def inject(m):
        nonlocal injected
        skey = m.group(2).zfill(2)
        if skey in callouts:
            injected += 1
            return m.group(1) + callouts[skey]
        return m.group(1)

    new_xml = pattern.sub(inject, xml_str)
    print(f'  Sessions injected: {injected} / {len(inserts)}')

    files['word/document.xml'] = new_xml.encode('utf-8')
    os.makedirs(os.path.dirname(OUT_DOCX), exist_ok=True)
    with zipfile.ZipFile(OUT_DOCX, 'w', zipfile.ZIP_DEFLATED) as zout:
        for name, data in files.items():
            zout.writestr(name, data)

    size_mb = os.path.getsize(OUT_DOCX) / 1024 / 1024
    print(f'\nOutput: {OUT_DOCX}')
    print(f'Size:   {size_mb:.2f} MB')
    print('Done!')

if __name__ == '__main__':
    main()
