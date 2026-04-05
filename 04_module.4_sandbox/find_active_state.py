f = open(r'C:\Users\mpsch\Desktop\board_prep_intel\CLAUDE.md', encoding='utf-8')
lines = f.readlines()
f.close()
# Print lines 47-100
for i, l in enumerate(lines[46:110], start=47):
    print(f'{i}: {repr(l)}')
