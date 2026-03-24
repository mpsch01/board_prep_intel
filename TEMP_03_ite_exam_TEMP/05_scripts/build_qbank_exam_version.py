"""
build_qbank_exam_version.py
============================
Reads ABFM_ITE_QuestionBank_2020-2025.docx and produces a new docx:

  Part 1 — Questions only (no answers, no explanations)
  Part 2 — Answer Key (quick-reference: "1. A   2. C   3. B ...")
  Part 3 — Explanation Key (QID + letter + full explanation + reference)

Parses the existing docx XML directly.
"""

import zipfile, re, sys, os, shutil
import xml.etree.ElementTree as ET
sys.stdout.reconfigure(encoding='utf-8')

SRC  = r'C:\Users\mpsch\Desktop\claude_knowledge\00_canonical\02_question_bank\ABFM_ITE_QuestionBank_2020-2025.docx'
DST  = r'C:\Users\mpsch\Desktop\claude_knowledge\00_canonical\02_question_bank\ABFM_ITE_QuestionBank_2020-2025_ExamVersion.docx'

# ── Parse the source docx ────────────────────────────────────────────────────
print('Parsing source docx...')
with zipfile.ZipFile(SRC) as z:
    xml_bytes = z.read('word/document.xml')
    src_files = {n: z.read(n) for n in z.namelist()}

xml = xml_bytes.decode('utf-8')

# Extract all <w:t> text from a paragraph xml string
def para_text(p_xml):
    return ''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', p_xml))

# Split into paragraph strings
paras = re.findall(r'<w:p\b[^>]*>.*?</w:p>', xml, re.DOTALL)

# ── Walk paragraphs and collect question data ─────────────────────────────────
questions = []   # list of dicts
cur = None

for p_xml in paras:
    t = para_text(p_xml)

    # Header row: "#1   |   Q2020-001   |   2020   |   Endocrine"
    m = re.match(r'#(\d+)\s+\|\s+(Q\d{4}-\d+)\s+\|\s+(\d{4})\s+\|\s+(.+)', t.strip())
    if m:
        cur = {
            'num':         int(m.group(1)),
            'qid':         m.group(2),
            'year':        m.group(3),
            'body_system': m.group(4).strip(),
            'stem_paras':  [],    # raw xml paragraphs for stem + choices
            'answer':      '',
            'explanation': '',
            'reference':   '',
            'ref_tier':    '',
        }
        questions.append(cur)
        continue

    if cur is None:
        continue

    # Correct answer line
    if t.startswith('Correct Answer:'):
        cur['answer'] = t.replace('Correct Answer:', '').strip()
        continue

    # REFERENCE paragraph (italic citation)
    if 'REFERENCE' in t and len(t) > 9:
        # Text is "REFERENCE  citation [tier]"
        ref_full = re.sub(r'^REFERENCE\s*', '', t).strip()
        tier_m = re.search(r'\[(Must-Read|Core|Supplementary)\]', ref_full)
        cur['ref_tier'] = tier_m.group(1) if tier_m else ''
        cur['reference'] = re.sub(r'\s*\[.*?\]\s*$', '', ref_full).strip()
        continue

    # EXPLANATION paragraph — accumulate
    if 'EXPLANATION' in t:
        expl = re.sub(r'^EXPLANATION\s*', '', t).strip()
        cur['explanation'] = expl
        continue

    # If we have an answer already, this is continuation of explanation
    if cur['answer'] and not cur['reference']:
        if t.strip() and t.strip() not in ('', ' '):
            cur['explanation'] += ' ' + t.strip()
        continue

    # Otherwise it's part of the question stem/choices
    if not cur['answer']:
        cur['stem_paras'].append(p_xml)

print(f'  Parsed {len(questions)} questions')
print(f'  Sample: {questions[0]["qid"]} answer={questions[0]["answer"]} ref={questions[0]["reference"][:50]}')

# ── XML builder helpers ───────────────────────────────────────────────────────
import random

def rand_id():
    return ''.join(random.choices('0123456789ABCDEF', k=8))

def esc(t):
    return str(t).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;')

def p(text, size=18, bold=False, italic=False, color='000000', indent=0,
      sb=40, sa=40, align='', fill=''):
    pid = rand_id()
    b = '<w:b/><w:bCs/>' if bold else ''
    i = '<w:i/><w:iCs/>' if italic else ''
    rpr = (f'<w:rFonts w:ascii="Aptos" w:hAnsi="Aptos"/>{b}{i}'
           f'<w:sz w:val="{size}"/><w:szCs w:val="{size}"/>'
           f'<w:color w:val="{color}"/>')
    shd = f'<w:shd w:val="clear" w:color="auto" w:fill="{fill}"/>' if fill else ''
    jc  = f'<w:jc w:val="{align}"/>' if align else ''
    ind_xml = f'<w:ind w:left="{indent}"/>' if indent else ''
    spc = f'<w:spacing w:before="{sb}" w:after="{sa}"/>'
    ppr = f'<w:pPr>{shd}{jc}{spc}{ind_xml}<w:rPr>{rpr}</w:rPr></w:pPr>'
    body = (f'<w:r><w:rPr>{rpr}</w:rPr>'
            f'<w:t xml:space="preserve">{esc(text)}</w:t></w:r>') if text else ''
    return (f'<w:p w14:paraId="{pid}" w14:textId="77777777" '
            f'w:rsidR="00CC0000" w:rsidRDefault="00CC0000">{ppr}{body}</w:p>')

def page_break():
    pid = rand_id()
    return (f'<w:p w14:paraId="{pid}" w14:textId="77777777" '
            f'w:rsidR="00CC0000" w:rsidRDefault="00CC0000">'
            f'<w:r><w:br w:type="page"/></w:r></w:p>')

def section_header(text, fill='1F3864', text_color='FFFFFF', size=24):
    return p(f'  {text}', size=size, bold=True, color=text_color, fill=fill, sb=120, sa=0)

def divider():
    pid = rand_id()
    return (f'<w:p w14:paraId="{pid}" w14:textId="77777777" '
            f'w:rsidR="00CC0000" w:rsidRDefault="00CC0000">'
            f'<w:pPr><w:pBdr><w:bottom w:val="single" w:sz="4" '
            f'w:space="1" w:color="B0B0B0"/></w:pBdr>'
            f'<w:spacing w:before="40" w:after="40"/></w:pPr></w:p>')

def year_heading(year_label):
    pid = rand_id()
    return (f'<w:p w14:paraId="{pid}" w14:textId="77777777" '
            f'w:rsidR="00CC0000" w:rsidRDefault="00CC0000">'
            f'<w:pPr><w:pStyle w:val="Heading1"/>'
            f'<w:spacing w:before="160" w:after="80"/></w:pPr>'
            f'<w:r><w:rPr><w:rFonts w:ascii="Aptos" w:hAnsi="Aptos"/>'
            f'<w:sz w:val="26"/></w:rPr>'
            f'<w:t>{esc(year_label)}</w:t></w:r></w:p>')

# ── Build the new document body ───────────────────────────────────────────────
print('Building exam version...')
body_parts = []

# ── TITLE ─────────────────────────────────────────────────────────────────────
title_pid = rand_id()
body_parts.append(
    f'<w:p w14:paraId="{title_pid}" w14:textId="77777777" w:rsidR="00CC0000" w:rsidRDefault="00CC0000">'
    f'<w:pPr><w:spacing w:before="800"/><w:jc w:val="center"/></w:pPr>'
    f'<w:r><w:rPr><w:b/><w:sz w:val="44"/></w:rPr>'
    f'<w:t>ABFM ITE Question Bank</w:t></w:r></w:p>')
sub_pid = rand_id()
body_parts.append(
    f'<w:p w14:paraId="{sub_pid}" w14:textId="77777777" w:rsidR="00CC0000" w:rsidRDefault="00CC0000">'
    f'<w:pPr><w:jc w:val="center"/></w:pPr>'
    f'<w:r><w:rPr><w:sz w:val="26"/></w:rPr>'
    f'<w:t>In-Training Examination  |  2020\u20132025  |  1,200 Questions  |  Exam Version</w:t></w:r></w:p>')
body_parts.append(page_break())

# ══════════════════════════════════════════════════════════════════════════════
# PART 1 — QUESTIONS ONLY
# ══════════════════════════════════════════════════════════════════════════════
body_parts.append(section_header('\u25A0  PART 1 \u2014 QUESTIONS', fill='1F3864'))
body_parts.append(p(''))

cur_year = None
for q in questions:
    yr = q['year']
    if yr != cur_year:
        body_parts.append(year_heading(f'{yr}  (200 questions)'))
        cur_year = yr

    # Gray header bar: "#1   |   Q2020-001   |   2020   |   Endocrine"
    pid = rand_id()
    body_parts.append(
        f'<w:tbl>'
        f'<w:tblPr><w:tblStyle w:val="TableGrid"/><w:tblW w:w="0" w:type="auto"/>'
        f'<w:tblLook w:val="04A0"/></w:tblPr>'
        f'<w:tblGrid><w:gridCol w:w="9360"/></w:tblGrid>'
        f'<w:tr w:rsidR="00CC0000" w14:paraId="{pid}" w14:textId="77777777">'
        f'<w:tc><w:tcPr><w:tcW w:w="9360" w:type="dxa"/>'
        f'<w:shd w:val="clear" w:color="auto" w:fill="D9D9D9"/></w:tcPr>'
        f'<w:p w14:paraId="{rand_id()}" w14:textId="77777777" w:rsidR="00CC0000" w:rsidRDefault="00CC0000">'
        f'<w:pPr><w:spacing w:before="20" w:after="20"/></w:pPr>'
        f'<w:r><w:rPr><w:b/><w:sz w:val="16"/></w:rPr>'
        f'<w:t>#{q["num"]}   |   {q["qid"]}   |   {q["year"]}   |   {esc(q["body_system"])}</w:t>'
        f'</w:r></w:p></w:tc></w:tr></w:tbl>')

    # Stem + choices (copy original paragraphs verbatim — no answer/explanation)
    for sp in q['stem_paras']:
        body_parts.append(sp)

    body_parts.append(divider())

body_parts.append(page_break())

# ══════════════════════════════════════════════════════════════════════════════
# PART 2 — ANSWER KEY (compact letter grid)
# ══════════════════════════════════════════════════════════════════════════════
body_parts.append(section_header('\u25A0  PART 2 \u2014 ANSWER KEY', fill='1F3864'))
body_parts.append(p('Correct answer letter only. See Part 3 for explanations.',
                    size=16, color='444444', sb=20, sa=40))

# Group by year, then print in rows of 10
from itertools import groupby
for yr, group in groupby(questions, key=lambda q: q['year']):
    yr_qs = list(group)
    body_parts.append(p(str(yr), size=20, bold=True, color='1F3864', sb=80, sa=20))
    # Build rows of 10
    row_size = 10
    for i in range(0, len(yr_qs), row_size):
        chunk = yr_qs[i:i+row_size]
        line = '   '.join(f'{q["num"]}. {q["answer"]}' for q in chunk)
        body_parts.append(p(line, size=18, color='000000', sb=0, sa=0))
    body_parts.append(p('', sb=20, sa=20))

body_parts.append(page_break())

# ══════════════════════════════════════════════════════════════════════════════
# PART 3 — EXPLANATION KEY
# ══════════════════════════════════════════════════════════════════════════════
body_parts.append(section_header('\u25A0  PART 3 \u2014 EXPLANATION KEY', fill='1F3864'))
body_parts.append(p(''))

cur_year = None
for q in questions:
    yr = q['year']
    if yr != cur_year:
        body_parts.append(year_heading(f'{yr}'))
        cur_year = yr

    # Header: "#1   Q2020-001   (C)"
    body_parts.append(p(
        f'#{q["num"]}   {q["qid"]}   ({q["answer"]})',
        size=17, bold=True, color='1A5676', fill='EBF3FB', sb=60, sa=0, indent=120))

    # Explanation text
    if q['explanation']:
        body_parts.append(p(q['explanation'], size=17, color='000000',
                            sb=0, sa=0, indent=120))

    # Reference
    if q['reference']:
        tier_str = f'  [{q["ref_tier"]}]' if q['ref_tier'] else ''
        body_parts.append(p(
            f'{q["reference"]}{tier_str}',
            size=16, italic=True, color='444444', sb=20, sa=40, indent=120))

    body_parts.append(divider())

# ── Assemble and write ────────────────────────────────────────────────────────
# Wrap in the original document shell (preserves namespaces, styles, fonts)
# Replace just the body content
body_xml = '\n'.join(body_parts)

# Reconstruct full document — keep original header/namespaces, replace body
new_xml = re.sub(
    r'(<w:body>).*?(</w:body>)',
    r'\1' + body_xml + r'<w:sectPr/>\2',
    xml, flags=re.DOTALL)

print(f'Writing exam version docx...')
src_files['word/document.xml'] = new_xml.encode('utf-8')

with zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED) as zout:
    for name, data in src_files.items():
        zout.writestr(name, data)

size_mb = os.path.getsize(DST) / 1024 / 1024
print(f'Output: {DST}')
print(f'Size:   {size_mb:.2f} MB  (vs {os.path.getsize(SRC)/1024/1024:.2f} MB source)')
print('Done.')
