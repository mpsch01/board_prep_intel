"""
Fix: repack the docx cleanly so there's no duplicate word/document.xml entry.
"""
import zipfile, shutil, os

DOCX_IN  = r'C:/Users/mpsch/Desktop/claude_knowledge/board_prep/aafp_integration/01_source/BoardPrep-ContentOutline_SESSION-MAPPED-v2.docx'
DOCX_DIRTY = r'C:/Users/mpsch/Desktop/claude_knowledge/board_prep/aafp_integration/04_outputs/BoardPrep-ContentOutline_ITE-ENRICHED-v1.docx'
DOCX_CLEAN = r'C:/Users/mpsch/Desktop/claude_knowledge/board_prep/aafp_integration/04_outputs/BoardPrep-ContentOutline_ITE-ENRICHED-v1_clean.docx'

# Extract the new document.xml from the dirty file (last entry wins)
with zipfile.ZipFile(DOCX_DIRTY, 'r') as dirty:
    new_doc_xml = dirty.read('word/document.xml')

# Rebuild cleanly from original, replacing only document.xml
with zipfile.ZipFile(DOCX_IN, 'r') as orig, \
     zipfile.ZipFile(DOCX_CLEAN, 'w', compression=zipfile.ZIP_DEFLATED) as out:
    for item in orig.infolist():
        if item.filename == 'word/document.xml':
            out.writestr(item, new_doc_xml)
        else:
            out.writestr(item, orig.read(item.filename))

# Replace dirty with clean
os.remove(DOCX_DIRTY)
os.rename(DOCX_CLEAN, DOCX_DIRTY)
print("Clean repack complete.")
print(f"Output: {DOCX_DIRTY}")

# Verify
with zipfile.ZipFile(DOCX_DIRTY, 'r') as z:
    names = z.namelist()
    doc_count = names.count('word/document.xml')
    print(f"word/document.xml entries in zip: {doc_count}  (should be 1)")
    print(f"Total zip entries: {len(names)}")
