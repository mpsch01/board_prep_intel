import zipfile, sys
sys.stdout.reconfigure(encoding='utf-8')

docx = r'C:\Users\mpsch\Desktop\claude_knowledge\00_canonical\01_curriculum\ABFM_BoardPrep_ContentOutline_HY-Enriched_v6.docx'
with zipfile.ZipFile(docx) as z:
    xml = z.read('word/document.xml').decode('utf-8')

lines = xml.split('\n')
out = []
for i, line in enumerate(lines):
    if '1F3864' in line:
        out = lines[max(0,i-2):i+60]
        break

with open('_callout_snippet.txt','w',encoding='utf-8') as f:
    f.write('\n'.join(out))
print(f'Written {len(out)} lines')
