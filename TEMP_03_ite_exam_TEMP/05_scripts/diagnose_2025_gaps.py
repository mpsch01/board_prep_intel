"""
diagnose_2025_gaps.py - Find the 3 missing ANSWER blocks
"""
import re, sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

BASE = Path(__file__).parent.parent
txt = (BASE / "02_working" / "2025_ITE_Critique.txt").read_text(encoding="utf-8", errors="replace")

# Count all ANSWER: occurrences 
all_answers = re.findall(r'ANSWER:\s+[A-E]', txt)
print(f"Total ANSWER: patterns found: {len(all_answers)}")

# The split regex requires ANSWER: + letter + \n
# Some may have \r\n or other whitespace
all_with_newline = re.findall(r'ANSWER:\s+[A-E]\s*[\r\n]', txt)
print(f"With newline after letter:    {len(all_with_newline)}")

# Find ANSWER: patterns NOT followed by newline
for m in re.finditer(r'ANSWER:\s+[A-E]', txt):
    pos = m.end()
    after = txt[pos:pos+5]
    if '\n' not in after and '\r' not in after:
        # Show context
        start = max(0, m.start()-50)
        end = min(len(txt), m.end()+100)
        print(f"\n  NON-NEWLINE ANSWER at pos {m.start()}:")
        print(f"  Context: {repr(txt[start:end])}")
