"""
extract_2025_refs_v2.py
Smart extraction with answer-letter alignment verification.
Uses CorrectAnswer from master to detect offset/mismatch from missing critique blocks.
Outputs ref_2025_extracted.csv and alignment_report.txt
"""
import re, sys, csv
import pandas as pd
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

BASE   = Path(__file__).parent.parent
MASTER = BASE / "03_database" / "ABFM_ITE_Master_v2.xlsx"
TXT    = BASE / "02_working" / "2025_ITE_Critique.txt"
OUT    = BASE / "02_working" / "ref_2025_extracted.csv"
REPORT = BASE / "02_working" / "ref_2025_alignment_report.txt"

# ── 1. Load master Q2025 rows ────────────────────────────────────────────────
print("Loading master...")
df = pd.read_excel(MASTER, dtype=str)
q25 = df[df["ExamYear"] == "2025"][["QuestionID", "CorrectAnswer"]].reset_index(drop=True)
print(f"  Q2025 rows in master: {len(q25)}")

# ── 2. Parse critique blocks ──────────────────────────────────────────────────
print(f"Parsing critique: {TXT}")
text = TXT.read_text(encoding="utf-8", errors="replace")

# Each block starts with ANSWER: X on its own line
blocks = re.split(r'(?=ANSWER:\s+[A-E]\s*[\r\n])', text)
critique_blocks = []
for block in blocks:
    block = block.strip()
    if not block.startswith("ANSWER:"):
        continue
    ans_match = re.match(r'ANSWER:\s+([A-E])', block)
    if not ans_match:
        continue
    answer = ans_match.group(1)

    ref_text = ""
    ref_match = re.search(r'References\s*[\r\n]+(.*?)$', block, re.DOTALL | re.IGNORECASE)
    if ref_match:
        ref_text = ref_match.group(1).strip()

    raw_refs = [r.strip() for r in ref_text.split('\n') if r.strip()]
    clean_refs = []
    for r in raw_refs:
        if re.match(r'^ANSWER:', r):
            break
        if len(r) > 10:
            clean_refs.append(r)

    critique_blocks.append({
        "block_num": len(critique_blocks) + 1,
        "answer": answer,
        "refs": " | ".join(clean_refs),
        "ref_count": len(clean_refs)
    })

print(f"  Critique blocks parsed: {len(critique_blocks)}")

# ── 3. Alignment check ────────────────────────────────────────────────────────
# Try sequential mapping first, track mismatches
report_lines = ["=== 2025 CRITIQUE ALIGNMENT REPORT ===\n"]
report_lines.append(f"Master Q2025 rows:   {len(q25)}")
report_lines.append(f"Critique blocks:     {len(critique_blocks)}\n")

# Walk through master and critique simultaneously, advancing critique ptr on match
master_ptr = 0
crit_ptr   = 0
assignments = {}   # QuestionID -> refs
mismatches  = []
skipped_crit = []

while master_ptr < len(q25) and crit_ptr < len(critique_blocks):
    qid     = q25.iloc[master_ptr]["QuestionID"]
    m_ans   = str(q25.iloc[master_ptr]["CorrectAnswer"]).strip().upper()
    c_ans   = critique_blocks[crit_ptr]["answer"].strip().upper()
    c_refs  = critique_blocks[crit_ptr]["refs"]

    if m_ans == c_ans:
        # Match — assign refs
        assignments[qid] = c_refs
        master_ptr += 1
        crit_ptr   += 1
    else:
        # Mismatch — check if next critique block matches (skip current)
        # Look ahead up to 3 blocks in critique
        found = False
        for lookahead in range(1, 4):
            next_c = crit_ptr + lookahead
            if next_c < len(critique_blocks):
                if critique_blocks[next_c]["answer"] == m_ans:
                    # The gap is in critique — master Q skipped a block
                    for skip in range(lookahead):
                        skipped_crit.append(crit_ptr + skip)
                    crit_ptr = next_c
                    found = True
                    break
        if not found:
            # Unclear mismatch — assign anyway with flag
            mismatches.append((master_ptr, qid, m_ans, c_ans, crit_ptr))
            assignments[qid] = c_refs  # assign anyway
            master_ptr += 1
            crit_ptr   += 1

# Assign remaining master rows with no critique match
while master_ptr < len(q25):
    qid = q25.iloc[master_ptr]["QuestionID"]
    assignments[qid] = ""
    master_ptr += 1

# ── 4. Report ──────────────────────────────────────────────────────────────────
report_lines.append(f"Assigned refs to: {sum(1 for v in assignments.values() if v)} questions")
report_lines.append(f"Skipped critique blocks: {len(skipped_crit)} (blocks {skipped_crit})")
report_lines.append(f"Answer mismatches: {len(mismatches)}")

if mismatches:
    report_lines.append("\nMISMATCHES (master_ans vs critique_ans):")
    for mp, qid, ma, ca, cp in mismatches:
        report_lines.append(f"  {qid} (master={ma}) vs critique block {cp} (critique={ca})")

if skipped_crit:
    report_lines.append(f"\nSKIPPED CRITIQUE BLOCKS: {skipped_crit}")
    for s in skipped_crit:
        b = critique_blocks[s]
        report_lines.append(f"  Block {b['block_num']}: answer={b['answer']}, refs={b['refs'][:80]}")

report_text = "\n".join(report_lines)
print(report_text)
REPORT.write_text(report_text, encoding="utf-8")

# ── 5. Write CSV ────────────────────────────────────────────────────────────────
rows = []
for i, row in q25.iterrows():
    qid = row["QuestionID"]
    refs = assignments.get(qid, "")
    rows.append({"QuestionID": qid, "ExamYear": 2025, "References": refs,
                 "RefCount": len(refs.split(" | ")) if refs else 0})

with open(OUT, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["QuestionID","ExamYear","References","RefCount"])
    writer.writeheader()
    writer.writerows(rows)

with_refs = sum(1 for r in rows if r["References"])
print(f"\nOutput: {OUT}")
print(f"Final: {with_refs}/200 questions have refs assigned")
print("Done.")
