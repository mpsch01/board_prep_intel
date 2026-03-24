import zipfile, re, sys
sys.stdout.reconfigure(encoding='utf-8')
doc = r'C:\Users\mpsch\Desktop\claude_knowledge\00_canonical\02_question_bank\ABFM_ITE_QuestionBank_2020-2025_ExamVersion.docx'
with zipfile.ZipFile(doc) as z:
    xml = z.read('word/document.xml').decode('utf-8')

def all_text(xml):
    return re.findall(r'<w:t[^>]*>([^<]+)</w:t>', xml)

texts = all_text(xml)

# Check parts present
print('PART 1 present:', any('PART 1' in t for t in texts))
print('PART 2 present:', any('PART 2' in t for t in texts))
print('PART 3 present:', any('PART 3' in t for t in texts))
print()

# Find first answer key row
for t in texts:
    if re.match(r'\d+\. [A-E]\s+\d+\.', t):
        print('Answer key sample row:', t[:80])
        break

# Find first explanation key entry
for t in texts:
    if re.match(r'#\d+\s+Q20\d\d-\d+\s+\([A-E]\)', t):
        print('Explanation key sample:', t)
        break

# Check no "Correct Answer:" in question section (before PART 2)
part2_pos = xml.find('PART 2')
correct_in_q_section = xml[:part2_pos].count('Correct Answer:')
print(f'\n"Correct Answer:" in question section: {correct_in_q_section}  (should be 0)')
print(f'"Correct Answer:" in full doc:         {xml.count("Correct Answer:")}  (should be 0 — moved to key)')
