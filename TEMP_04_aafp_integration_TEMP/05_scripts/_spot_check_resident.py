import zipfile, re, sys
sys.stdout.reconfigure(encoding='utf-8')
doc = r'C:\Users\mpsch\Desktop\claude_knowledge\abfm_prep\04_aafp_integration\04_outputs\BoardPrep-ContentOutline_HY-ENRICHED-v6-resident.docx'
with zipfile.ZipFile(doc) as z:
    xml = z.read('word/document.xml').decode('utf-8')
texts = re.findall(r'<w:t[^>]*>([^<]+)</w:t>', xml)

# Check Must-Read / Core tier labels present
must_read_labels = [t for t in texts if '\u2605 Must-Read' in t]
core_labels = [t for t in texts if t.strip() == 'Core']
print(f'Must-Read tier labels: {len(must_read_labels)}')
print(f'Core tier labels: {len(core_labels)}')

# Check no [Poll] row appears without choices following it (dedup check)
poll_q_rows = [t for t in texts if re.match(r'^  Q\d+$', t)]
print(f'Poll Q rows: {len(poll_q_rows)}  (should be <= 240, was 311 before)')

# Sample: find a Must-Read label and the citation that follows it
for i, t in enumerate(texts):
    if '\u2605 Must-Read' in t:
        print(f'\nSample ref block:')
        print(f'  label: {t}')
        print(f'  cite:  {texts[i+1][:80] if i+1 < len(texts) else "?"}')
        break
