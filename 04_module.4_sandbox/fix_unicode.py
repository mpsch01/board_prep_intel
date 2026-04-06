path = r'C:\Users\mpsch\Desktop\board_prep_intel\01_module.1_warehouse\scripts\maintain\unpaywall_scanner.py'
txt = open(path, encoding='utf-8').read()
txt = txt.replace('\u2713', '[OK]').replace('\u2717', '[X]')
open(path, 'w', encoding='utf-8').write(txt)
print('done')
