import zipfile, re
from xml.etree import ElementTree as ET

DOCX = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\01_source\BoardPrep-ContentOutline_SESSION-MAPPED-v2.docx'
NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

with zipfile.ZipFile(DOCX) as z:
    raw = z.read('word/document.xml')

# Pretty-print just the XML around para 82 (Session 02 heading) + next 6 paras
# We'll do a regex slice since ET doesn't preserve whitespace well for output
xml_str = raw.decode('utf-8')

# Find all <w:p ...>...</w:p> blocks
para_blocks = re.findall(r'<w:p[ >].*?</w:p>', xml_str, re.DOTALL)
print(f'Total para blocks found by regex: {len(para_blocks)}')

# Print para 82, 83, 84, 85 (session heading + first few content paras)
for idx in [82, 83, 84, 85, 86, 87]:
    print(f'\n=== para[{idx}] ===')
    block = para_blocks[idx]
    # Light pretty-print: insert newlines before tags
    pretty = re.sub(r'(<w:)', r'\n\1', block)
    print(pretty[:1200])
