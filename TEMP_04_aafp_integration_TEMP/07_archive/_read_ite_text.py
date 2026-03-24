import zipfile, sys, re
sys.stdout.reconfigure(encoding='utf-8')

docx = r'C:\Users\mpsch\Desktop\claude_knowledge\00_canonical\01_curriculum\ABFM_BoardPrep_ContentOutline_HY-Enriched_v6.docx'
with zipfile.ZipFile(docx) as z:
    xml = z.read('word/document.xml').decode('utf-8')

# Find the ITE block for session 02 and print ~300 chars of raw text content
# to understand the question display format
texts = re.findall(r'<w:t[^>]*>([^<]+)</w:t>', xml)
in_block = False
block_texts = []
for t in texts:
    if 'ITE HIGH-YIELD' in t and 'Session 2' in t:
        in_block = True
    if in_block:
        block_texts.append(t)
    if in_block and 'AAFP Poll' in t:
        break
    if len(block_texts) > 80:
        break

for t in block_texts:
    if t.strip():
        print(repr(t))
