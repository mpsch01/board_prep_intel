import os, re

txt_dir = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\01_source\transcripts\txt'

for fname in ['04-hypertension.txt', '14-diabetes.txt', '31-musculoskeletal-medicine.txt']:
    path = os.path.join(txt_dir, fname)
    text = open(path, encoding='utf-8', errors='ignore').read()
    lines = text.split('\n')
    print(f'=== {fname} ({len(lines)} lines) ===')
    for i, line in enumerate(lines):
        l = line.strip()
        if (re.match(r'^[A-E][)\.]', l) or
            'year-old' in l or
            re.search(r'\bpoll\b|\bvignette\b|\bcase\b', l, re.I) or
            re.search(r'\bwhich one\b|\bwhich of\b|\bwhat is\b|\bwhat would\b|\bmost appropriate\b|\bbest next\b', l, re.I)):
            print(f'  L{i:4d}: {l[:110]}')
    print()
