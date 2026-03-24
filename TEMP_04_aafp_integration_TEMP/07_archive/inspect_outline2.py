import zipfile, re
from xml.etree import ElementTree as ET
from collections import Counter

DOCX = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\01_source\BoardPrep-ContentOutline_SESSION-MAPPED-v2.docx'

NS = {
    'w':  'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'w14':'http://schemas.microsoft.com/office/word/2010/wordml',
}

with zipfile.ZipFile(DOCX) as z:
    raw = z.read('word/document.xml')

tree = ET.fromstring(raw)
body = tree.find('.//w:body', NS)
paras = body.findall('w:p', NS)

print(f'Total paragraphs: {len(paras)}')

# Collect style + text for each paragraph
def para_text(p):
    return ''.join(t.text or '' for t in p.findall('.//w:t', NS))

def para_style(p):
    pr = p.find('w:pPr/w:pStyle', NS)
    return pr.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val') if pr is not None else 'Normal'

# Show style distribution
styles = [para_style(p) for p in paras]
print('\n=== STYLE COUNTS ===')
for s, c in Counter(styles).most_common():
    print(f'  {c:4d}x  {s}')

# Show first 5 of each style with text sample
print('\n=== STYLE SAMPLES ===')
seen = {}
for p in paras:
    s = para_style(p)
    txt = para_text(p).strip()
    if s not in seen and txt:
        seen[s] = txt
        print(f'  [{s}] {txt[:120]}')

# Find session heading paragraphs
print('\n=== SESSION HEADINGS (Heading1 style) ===')
for i, p in enumerate(paras):
    if para_style(p) == 'Heading1':
        txt = para_text(p).strip()
        print(f'  para[{i:4d}]  {txt[:100]}')

# Show a few paragraphs around first session heading to understand context
print('\n=== CONTEXT AROUND FIRST SESSION (paras 0-30) ===')
for i, p in enumerate(paras[:30]):
    s = para_style(p)
    txt = para_text(p).strip()[:90]
    print(f'  [{i:3d}] ({s:12s}) {txt}')
