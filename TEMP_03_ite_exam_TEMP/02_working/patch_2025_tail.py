"""
patch_2025_tail.py — manually extract refs for Q2025-198/199/200 from end of critique file
and patch directly into the Excel
"""
import re, openpyxl
from pathlib import Path

XLSX    = Path(r"C:\Users\mpsch\Desktop\claude_knowledge\board_prep\ite_exam\03_database\ABFM_ITE_Master_v2.xlsx")
CRITIQUE = Path(r"C:\Users\mpsch\Desktop\claude_knowledge\board_prep\ite_exam\02_working\2025_ITE_Critique.txt")

text = CRITIQUE.read_text(encoding="utf-8", errors="replace")

# More robust split: include the ANSWER line itself in each chunk
chunks = re.split(r'\n(?=ANSWER:\s*[A-E]\s*\n)', text)
chunks = [c.strip() for c in chunks if re.match(r'ANSWER:\s*[A-E]', c.strip())]
print(f"Robust split: {len(chunks)} chunks")

# Show last 5 to verify
for i, c in enumerate(chunks[-5:], start=len(chunks)-4):
    lines = c.splitlines()
    ref_lines = []
    in_refs = False
    for l in lines:
        if re.match(r'^References\s*$', l.strip(), re.IGNORECASE):
            in_refs = True; continue
        if in_refs and l.strip():
            ref_lines.append(l.strip())
    print(f"\nChunk {i}: ANSWER={lines[0][:20]}")
    print(f"  Refs: {ref_lines}")

# Build full map
def extract_refs(chunk):
    lines = chunk.splitlines()
    in_refs = False
    refs = []
    for line in lines:
        s = line.strip()
        if re.match(r'^References\s*$', s, re.IGNORECASE):
            in_refs = True; continue
        if in_refs and s:
            refs.append(s)
    return refs

qid_refs = {f"Q2025-{i+1:03d}": extract_refs(c) for i, c in enumerate(chunks)}
print(f"\nTotal mapped: {len(qid_refs)}")
for qid in ["Q2025-195","Q2025-196","Q2025-197","Q2025-198","Q2025-199","Q2025-200"]:
    refs = qid_refs.get(qid, [])
    print(f"  {qid}: {len(refs)} refs → {refs[:1]}")

# Patch Excel
wb = openpyxl.load_workbook(XLSX)
ws = wb["Sheet1"]
header = [cell.value for cell in ws[1]]
col_qid = header.index("QuestionID") + 1
col_ref = header.index("Reference")  + 1

patched = 0
for row in ws.iter_rows(min_row=2, values_only=False):
    qid = row[col_qid - 1].value
    ref_cell = row[col_ref - 1]
    existing = ref_cell.value
    if existing and str(existing).strip() not in ("", "None"):
        continue
    if qid in qid_refs and qid_refs[qid]:
        ref_cell.value = " | ".join(qid_refs[qid])
        print(f"  Patched {qid}")
        patched += 1

wb.save(XLSX)
print(f"\nPatched {patched} cells. Saved.")
