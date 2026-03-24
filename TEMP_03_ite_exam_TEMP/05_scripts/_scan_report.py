import zipfile, re, sys, shutil, os
sys.stdout.reconfigure(encoding='utf-8')
SRC = r'C:\Users\mpsch\Desktop\claude_knowledge\00_canonical\03_analysis\ABFM_ITE_Analysis_Report_2020-2025.docx'

with zipfile.ZipFile(SRC) as z:
    files = {n: z.read(n) for n in z.namelist()}

xml = files['word/document.xml'].decode('utf-8')

# Remove para 445 (paraId 6FC76446) — "References link each..." stale bullet
# Remove para 446 (paraId 0BEA3A8E) — "Coverage is complete..." stale bullet
para_pat = re.compile(r'<w:p\b[^>]*>.*?</w:p>', re.DOTALL)
paras = para_pat.findall(xml)

to_remove = []
for p in paras:
    if '6FC76446' in p or '0BEA3A8E' in p:
        to_remove.append(p)
        print(f'Removing para: {p[:100]}...')

for p in to_remove:
    xml = xml.replace(p, '', 1)

print(f'Removed {len(to_remove)} paragraphs')
files['word/document.xml'] = xml.encode('utf-8')

tmp = SRC + '.tmp'
with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
    for name, data in files.items():
        zout.writestr(name, data)
os.replace(tmp, SRC)
print('Done.')
