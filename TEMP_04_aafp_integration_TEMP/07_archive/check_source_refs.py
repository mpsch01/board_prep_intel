import zipfile, re
from lxml import etree

NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

path = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\ite_refs\01_source\ite_q&a_2020-2024_word.docx'
with zipfile.ZipFile(path) as z:
    xml = z.read('word/document.xml')
root = etree.fromstring(xml)
def para_text(p):
    return ''.join(t.text or '' for t in p.findall('.//w:t', NS))
paras = [para_text(p) for p in root.findall('.//w:p', NS)]

# Find Ref: paragraphs and show next 3 paras to see continuation pattern
ref_indices = [i for i, p in enumerate(paras) if re.search(r'^Ref:', p.strip())]
print(f'Ref: paragraphs: {len(ref_indices)}')
print()
# Show first 5 multi-part refs
for i in ref_indices[:5]:
    print(f'[{i}] {paras[i][:300]}')
    for j in range(1, 4):
        nxt = paras[i+j].strip() if i+j < len(paras) else ''
        if nxt and not re.match(r'^\d+$', nxt):
            print(f'     +{j}: {nxt[:200]}')
        else:
            break
    print()
