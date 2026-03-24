"""
Script 03 v3: inject_hy_inserts.py
No tables. Pure styled paragraphs with shading/borders.
Layout: colored header bar + data lines + ITE questions + refs.
No poll questions.
"""

import zipfile, re, json, os, random

SRC_DOCX  = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\01_source\BoardPrep-ContentOutline_SESSION-MAPPED-v2.docx'
OUT_DOCX  = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\04_outputs\BoardPrep-ContentOutline_HY-ENRICHED.docx'
JSON_PATH = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\02_working\session_hy_inserts_v2_adjusted.json'

MAX_ITE_QS = 5
MAX_REFS   = 3

TIER = {
    'Tier 1':   {'hdr': '1F3864', 'body': 'D6E4F7', 'label': 'TIER 1  \u2605  HIGH-YIELD'},
    'Tier 2':   {'hdr': '2E75B6', 'body': 'DEEAF1', 'label': 'TIER 2  HIGH-YIELD'},
    'Standard': {'hdr': '595959', 'body': 'EDEDED', 'label': 'STANDARD'},
}

def rand_id():
    return ''.join(random.choices('0123456789ABCDEF', k=8))

def esc(t):
    return str(t).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;')

def styled_para(text, fill, text_color='000000', size=18, bold=False, italic=False,
                indent=0, space_before=0, space_after=0,
                top_border=None, bottom_border=None, border_color='000000'):
    """Single shaded paragraph — no tables, just a <w:p> with pPr shading."""
    pid = rand_id()

    b = '<w:b/><w:bCs/>' if bold else ''
    i = '<w:i/><w:iCs/>' if italic else ''
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

    ppr = (f'<w:pPr>{bdr}{shd}{spc}{ind}'
           f'<w:rPr>{rpr}</w:rPr></w:pPr>')

    return (f'<w:p w14:paraId="{pid}" w14:textId="77777777" '
            f'w:rsidR="00CC0000" w:rsidRDefault="00CC0000">'
            f'{ppr}'
            f'<w:r><w:rPr>{rpr}</w:rPr>'
            f'<w:t xml:space="preserve">{esc(text)}</w:t></w:r>'
            f'</w:p>')

def blank(fill='FFFFFF', size=8, space_before=0, space_after=0):
    return styled_para('', fill=fill, size=size,
                       space_before=space_before, space_after=space_after)

def build_callout(sess):
    tier   = sess['session_tier']
    c      = TIER[tier]
    hdr, body, label = c['hdr'], c['body'], c['label']

    snum   = sess['session_number']
    sname  = sess['session_name']
    score  = sess['best_yield_score']
    subcats= (sess.get('tier1_subcategories',[]) + sess.get('tier2_subcategories',[]))[:4]
    sub_str= ' | '.join(subcats) if subcats else 'General Review'
    top    = sess.get('top_subcategory', {})
    total  = top.get('total_qs_6yr', '-')
    avg    = top.get('avg_per_exam', '-')
    trend  = top.get('trend', '-')

    paras = []
    INDENT = 180   # left indent for body lines (twips)

    # ── Header bar ────────────────────────────────────────────────────
    paras.append(styled_para(
        f'  {label}   \u2022   Session {snum}: {sname}   \u2022   Yield Score: {score:.2f}',
        fill=hdr, text_color='FFFFFF', size=20, bold=True,
        space_before=120, space_after=0,
        top_border=True, border_color=hdr))

    # ── Stats row ─────────────────────────────────────────────────────
    paras.append(styled_para(
        f'  ITE Questions (6yr): {total}   |   Avg/Exam: {avg}   |   Trend: {trend}   |   Topics: {sub_str}',
        fill=body, text_color='000000', size=16,
        space_before=0, space_after=0))

    # ── ITE Questions ─────────────────────────────────────────────────
    ite_qs = sess.get('top_questions', [])[:MAX_ITE_QS]
    if ite_qs:
        paras.append(styled_para(
            '  ITE EXAM QUESTIONS',
            fill=hdr, text_color='FFFFFF', size=17, bold=True,
            space_before=0, space_after=0))

        for i, q in enumerate(ite_qs, 1):
            mr     = '  \u2192 MUST-READ' if str(q.get('is_must_read_ref','')) == 'True' else ''
            yr     = q.get('exam_year', '?')
            qid    = q.get('question_id', '')
            clust  = str(q.get('cluster', ''))

            # Q line
            paras.append(styled_para(
                f'  Q{i}   {yr}   \u2022   {qid}{mr}',
                fill=body, text_color='1F3864', size=15, bold=True,
                space_before=0, space_after=0, indent=INDENT))
            # Cluster line
            paras.append(styled_para(
                f'  {clust}',
                fill=body, text_color='444444', size=14, italic=True,
                space_before=0, space_after=0, indent=INDENT))

    # ── Must-read refs ────────────────────────────────────────────────
    refs = sess.get('must_read_refs', [])[:MAX_REFS]
    if refs:
        paras.append(styled_para(
            '  MUST-READ REFERENCES',
            fill=hdr, text_color='FFFFFF', size=17, bold=True,
            space_before=0, space_after=0))
        for ref in refs:
            cite = str(ref.get('citation', ''))
            cnt  = ref.get('citation_count', '')
            yrs  = ref.get('unique_years', '')
            paras.append(styled_para(
                f'  {cite}',
                fill=body, text_color='000000', size=14,
                space_before=0, space_after=0, indent=INDENT))
            paras.append(styled_para(
                f'  Cited {cnt}x   |   Years: {yrs}',
                fill=body, text_color='555555', size=13, italic=True,
                space_before=0, space_after=0, indent=INDENT))

    # ── Bottom border line ────────────────────────────────────────────
    paras.append(styled_para(
        '', fill=hdr, size=4,
        space_before=0, space_after=0,
        bottom_border=True, border_color=hdr))

    # ── Trailing spacer ───────────────────────────────────────────────
    paras.append(blank(fill='FFFFFF', size=8, space_before=60, space_after=60))

    return ''.join(paras)

def main():
    print('Loading JSON inserts...')
    with open(JSON_PATH, encoding='utf-8') as f:
        inserts = json.load(f)

    print('Reading source DOCX...')
    with zipfile.ZipFile(SRC_DOCX, 'r') as z:
        files = {n: z.read(n) for n in z.namelist()}

    xml_str = files['word/document.xml'].decode('utf-8')

    callouts = {}
    for snum, sess in inserts.items():
        callouts[snum.zfill(2)] = build_callout(sess)

    print(f'Built {len(callouts)} callout blocks')

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
    print(f'Sessions injected: {injected} / {len(inserts)}')

    files['word/document.xml'] = new_xml.encode('utf-8')
    os.makedirs(os.path.dirname(OUT_DOCX), exist_ok=True)
    with zipfile.ZipFile(OUT_DOCX, 'w', zipfile.ZIP_DEFLATED) as zout:
        for name, data in files.items():
            zout.writestr(name, data)

    size_mb = os.path.getsize(OUT_DOCX) / 1024 / 1024
    print(f'Output: {OUT_DOCX}')
    print(f'Size:   {size_mb:.2f} MB')
    print('Done!')


if __name__ == '__main__':
    main()
