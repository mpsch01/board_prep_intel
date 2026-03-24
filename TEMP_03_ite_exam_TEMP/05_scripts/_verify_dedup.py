import zipfile, re, sys
sys.stdout.reconfigure(encoding='utf-8')

doc = r'C:\Users\mpsch\Desktop\claude_knowledge\00_canonical\02_question_bank\ABFM_ITE_QuestionBank_2020-2025.docx'
with zipfile.ZipFile(doc) as z:
    xml = z.read('word/document.xml').decode('utf-8')

# Count standalone REFERENCE paragraphs (should be ~1,200, one per question)
ref_paras = len(re.findall(r'>REFERENCE\s*<', xml))
# Count any remaining inline "Ref: " (should be 0)
remaining = len(re.findall(r'>Ref: ', xml))
# Count italic ref runs (standalone REFERENCE content)
italic_refs = len(re.findall(r'<w:i/>.*?Smith|<w:i/>.*?AFP|<w:i/>.*?Physician', xml, re.DOTALL))

print(f'Standalone REFERENCE paragraphs: {ref_paras}')
print(f'Remaining inline "Ref: " text:   {remaining}  (should be 0)')

# Show first question's REFERENCE para to verify it's intact
# Find first REFERENCE para
m = re.search(r'<w:p\b[^>]*>.*?>REFERENCE\s*<.*?</w:p>', xml, re.DOTALL)
if m:
    texts = re.findall(r'<w:t[^>]*>([^<]+)</w:t>', m.group())
    print(f'\nFirst REFERENCE para content: {" ".join(texts)}')
