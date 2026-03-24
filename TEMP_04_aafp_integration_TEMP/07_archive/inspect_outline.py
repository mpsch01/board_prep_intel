import zipfile, re

DOCX = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\01_source\BoardPrep-ContentOutline_SESSION-MAPPED-v2.docx'

with zipfile.ZipFile(DOCX) as z:
    xml = z.read('word/document.xml').decode('utf-8')

lines = xml.split('\n')

# Print first 120 lines
print('=== FIRST 120 LINES ===')
for i, l in enumerate(lines[:120]):
    print(f'{i+1:4d}: {l[:120]}')

# Find session markers - look for "Session" text patterns
print('\n=== SESSION MARKER LINES (first 20) ===')
count = 0
for i, l in enumerate(lines):
    if re.search(r'Session\s+\d+', l, re.IGNORECASE) and '<w:t' in l:
        print(f'{i+1:5d}: {l[:140]}')
        count += 1
        if count >= 20:
            break

# Sample paragraph styles used
print('\n=== PARAGRAPH STYLES USED ===')
styles = re.findall(r'<w:pStyle w:val="([^"]+)"', xml)
from collections import Counter
for style, cnt in Counter(styles).most_common(20):
    print(f'  {cnt:4d}x  {style}')
