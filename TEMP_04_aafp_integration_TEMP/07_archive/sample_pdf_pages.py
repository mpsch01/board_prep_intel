import pdfplumber, sys, re
sys.stdout.reconfigure(encoding='utf-8')

files = [
    r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\01_source\slides\04-SLIDES_hypertension.pdf',
    r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\01_source\slides\16-SLIDES_lower-gi-tract-diseases.pdf',
    r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\01_source\slides\39-SLIDES_behavioral-medicine-1.pdf',
]

# Patterns that signal a poll/question slide
Q_TRIGGERS = re.compile(r'(AES Question|Question \d+|Poll|Audience Response)', re.IGNORECASE)

for fp in files:
    fname = fp.split('\\')[-1]
    print(f'\n\n{"="*60}')
    print(f'FILE: {fname}')
    print('='*60)
    with pdfplumber.open(fp) as pdf:
        for i, page in enumerate(pdf.pages):
            txt = page.extract_text() or ''
            if Q_TRIGGERS.search(txt):
                print(f'\n--- PAGE {i+1} ---')
                print(txt[:1200])
                print('...')
