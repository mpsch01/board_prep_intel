src = open('03_inject_into_outline_v3.py', encoding='utf-8').read()
# Replace SRC (v3) and OUT (v4) explicitly, then fix JSON
src = src.replace(
    "SRC_DOCX  = r'C:\\Users\\mpsch\\Desktop\\claude_knowledge\\board_prep\\aafp_integration\\04_outputs\\BoardPrep-ContentOutline_HY-ENRICHED-v3.docx'",
    "SRC_DOCX  = r'C:\\Users\\mpsch\\Desktop\\claude_knowledge\\board_prep\\aafp_integration\\04_outputs\\BoardPrep-ContentOutline_HY-ENRICHED-v4.docx'"
).replace(
    "OUT_DOCX  = r'C:\\Users\\mpsch\\Desktop\\claude_knowledge\\board_prep\\aafp_integration\\04_outputs\\BoardPrep-ContentOutline_HY-ENRICHED-v4.docx'",
    "OUT_DOCX  = r'C:\\Users\\mpsch\\Desktop\\claude_knowledge\\board_prep\\aafp_integration\\04_outputs\\BoardPrep-ContentOutline_HY-ENRICHED-v5.docx'"
).replace(
    'session_hy_inserts_v6.json',
    'session_hy_inserts_v7.json'
)
open('03_inject_v5_temp.py', 'w', encoding='utf-8').write(src)
print('Patched script written')
