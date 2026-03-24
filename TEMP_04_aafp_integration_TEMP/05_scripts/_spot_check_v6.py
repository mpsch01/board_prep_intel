import zipfile, re
with zipfile.ZipFile(r'C:\Users\mpsch\Desktop\claude_knowledge\abfm_prep\04_aafp_integration\04_outputs\BoardPrep-ContentOutline_HY-ENRICHED-v6.docx') as z:
    xml = z.read('word/document.xml').decode('utf-8')

amber_headers = re.findall(r'AAFP Poll Questions[^<]{1,80}', xml)
print(f'Amber header blocks found: {len(amber_headers)}')
for h in amber_headers[:5]:
    print(f'  {h}')

print(f'Amber dark (7F4F24) occurrences: {xml.count("7F4F24")}')
print(f'Blue dark  (1F3864) occurrences: {xml.count("1F3864")}')
print(f'Poll attribution lines: {xml.count("Poll question")}')
print(f'See session slides flags: {xml.count("See session slides")}')
