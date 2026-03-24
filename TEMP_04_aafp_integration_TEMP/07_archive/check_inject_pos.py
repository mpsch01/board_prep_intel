import zipfile, re

OUT = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\04_outputs\BoardPrep-ContentOutline_HY-ENRICHED.docx'

with zipfile.ZipFile(OUT) as z:
    xml = z.read('word/document.xml').decode('utf-8')

# Find the first session heading injection and show 800 chars before + after
m = re.search(r'Session 02: Peripheral Vascular Disease', xml)
if m:
    start = max(0, m.start() - 200)
    end   = min(len(xml), m.end() + 800)
    chunk = xml[start:end]
    # light pretty-print
    chunk = re.sub(r'(<(?:w:|w14:))', r'\n\1', chunk)
    print(chunk[:3000])
