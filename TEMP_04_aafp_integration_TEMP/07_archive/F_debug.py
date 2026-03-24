import zipfile, re
from lxml import etree
from difflib import SequenceMatcher

NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

def get_paragraphs(path):
    with zipfile.ZipFile(path) as z:
        xml = z.read('word/document.xml')
    root = etree.fromstring(xml)
    def pt(p): return ''.join(t.text or '' for t in p.findall('.//w:t', NS))
    return [pt(p) for p in root.findall('.//w:p', NS)]

# --- ISSUE 1: find QIDs in 2020-2024 ---
paras = get_paragraphs(r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\ite_refs\01_source\ite_q&a_2020-2024_word.docx')
qid_pat = re.compile(r'Q(20\d\d)-0*(\d+)')
qid_hits = [(i, p) for i, p in enumerate(paras) if qid_pat.search(p)]
print(f'QID matches: {len(qid_hits)}')
for i, p in qid_hits[:10]:
    print(f'  [{i}] len={len(p)} | {repr(p[:100])}')

print()
# Check a few around the first Ref: paragraph (para 64)
print('Paras 55-68 (around first Ref: at 64):')
for i in range(55, 69):
    p = paras[i].strip()
    if p:
        print(f'  [{i}] len={len(paras[i])} | {repr(p[:120])}')

print()
# --- ISSUE 2: fuzzy mismatch 2025 format ---
import csv
tier_db = []
with open(r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\ite_refs\02_working\ITE_Reference_Tiers_Clean.csv', newline='', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        tier_db.append(row['CleanRef'])

# Example 2025 ref vs tier DB entry
ex_2025 = 'Silver S, Williams E, Plunkett ML. Common foot fractures. Am Fam Physician. 2024;109(2):119-129.'
# Find closest match
def norm(s):
    return re.sub(r'\s+', ' ', re.sub(r'[^\w\s]', ' ', s.lower())).strip()

scores = [(SequenceMatcher(None, norm(ex_2025), norm(t)).ratio(), t) for t in tier_db]
scores.sort(reverse=True)
print(f'2025 ref: {ex_2025}')
print('Top 5 matches in tier DB:')
for score, ref in scores[:5]:
    print(f'  {score:.3f} | {ref[:120]}')
