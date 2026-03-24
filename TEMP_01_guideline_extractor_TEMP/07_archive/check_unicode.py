import re
with open('main.py', encoding='utf-8') as f:
    for i, line in enumerate(f, 1):
        for ch in line:
            if ord(ch) > 127:
                print(f"  line {i}: {repr(ch)} -- {line.rstrip()}")
