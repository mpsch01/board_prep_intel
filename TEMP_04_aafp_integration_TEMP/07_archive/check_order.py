import sys
lines = open(r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\05_scripts\03_inject_into_outline.py').readlines()
for i,l in enumerate(lines,1):
    if any(x in l for x in ['def ', 'if __name__', 'main()']):
        print(f'{i:4d}: {l.rstrip()}')
