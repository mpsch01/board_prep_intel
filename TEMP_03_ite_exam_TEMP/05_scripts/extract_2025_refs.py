"""
extract_2025_refs.py  v4 (FINAL)
=================================
Extracts reference citations from 2025_ITE_Critique.docx, 200 questions.

v4 vs v3:
  - Fallback for no-year blocks: take text up to prose-bleed boundary
    (first sentence that looks like org/author followed by another sentence
     that looks like prose). For Q2025-041 (CEBM NNT webpage).
"""

import zipfile, re, sys, csv
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

BASE = Path(r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep')
SOURCE = BASE / 'ite_exam' / '01_source' / '2025_ITE_Critique.docx'
OUT_CSV  = BASE / 'ite_exam' / '02_working' / 'refs_2025_extracted.csv'
OUT_SUMM = BASE / 'ite_exam' / '02_working' / 'refs_2025_summary.txt'

print("Reading docx...")
with zipfile.ZipFile(SOURCE) as z:
    xml = z.read('word/document.xml').decode('utf-8')
text = re.sub(r'<[^>]+>', ' ', xml)
text = re.sub(r'\s+', ' ', text).strip()

ref_positions = [m.start() for m in re.finditer(r'References\b', text)]
print(f"Found {len(ref_positions)} 'References' markers")
assert len(ref_positions) == 200

NEXT_ITEM  = re.compile(r'\bItem\s+\d+\s+ANSWER\s*:\s*[A-E]\b')
YEAR_PAT   = re.compile(r'\b(19|20)\d{2}[.;:) ]')
# Prose bleed detector: sentence starts with common prose words
PROSE_START = re.compile(
    r'^(This|The|These|A |An |In |If |For |When |While |Although |However|'
    r'Because|Since|After|Before|Despite|Given|Based|Note|As |It |At |With )',
    re.IGNORECASE
)


def extract_refs_from_block(block_text):
    block = re.sub(r'^References\s*', '', block_text).strip()
    m = NEXT_ITEM.search(block)
    if m:
        block = block[:m.start()].strip()
    if not block:
        return []

    sentences = re.split(r'\.\s+(?=[A-Z])', block)
    citations = []
    current = ''

    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        candidate = (current.rstrip('.') + '. ' + sent).strip() if current else sent

        if YEAR_PAT.search(candidate):
            citations.append(candidate.strip())
            current = ''
        else:
            current = candidate
            if len(current) > 400:
                break

    if current.strip() and YEAR_PAT.search(current):
        citations.append(current.strip())

    # Fallback for no-year citations (webpages, CEBM, etc.)
    # If nothing found yet, scan sentences for ref-looking text before prose begins
    if not citations:
        ref_sentences = []
        for sent in sentences:
            sent = sent.strip()
            if not sent:
                continue
            # Stop at prose bleed
            if PROSE_START.match(sent) and ref_sentences:
                break
            ref_sentences.append(sent)
        if ref_sentences:
            candidate = '. '.join(ref_sentences).strip()
            if len(candidate) >= 20:
                citations.append(candidate)

    cleaned = []
    for c in citations:
        c = re.sub(r'\s+', ' ', c).strip()
        if len(c) >= 20:
            cleaned.append(c)
    return cleaned


rows = []
summary_lines = []
total_refs = 0
zero_ref_questions = []

for i, pos in enumerate(ref_positions):
    qnum = i + 1
    qid  = f'Q2025-{qnum:03d}'
    end  = ref_positions[i+1] if i+1 < len(ref_positions) else len(text)
    block = text[pos:end]
    refs  = extract_refs_from_block(block)
    total_refs += len(refs)

    if not refs:
        zero_ref_questions.append(qid)
        block_clean = re.sub(r'^References\s*', '', block).strip()
        m2 = NEXT_ITEM.search(block_clean)
        raw = block_clean[:m2.start()] if m2 else block_clean
        summary_lines.append(f"{qid}: 0 refs  *** CHECK ***")
        summary_lines.append(f"    RAW: {raw[:200]}")
    else:
        summary_lines.append(f"{qid}: {len(refs)} ref(s)")
        for j, ref in enumerate(refs, 1):
            summary_lines.append(f"    [{j}] {ref[:120]}")

    for j, ref in enumerate(refs, 1):
        rows.append({'QuestionID': qid, 'RefIndex': j, 'RawRef': ref})

print(f"\nExtraction complete:")
print(f"  Questions processed : 200")
print(f"  Total refs extracted: {total_refs}")
print(f"  Avg per question    : {total_refs/200:.1f}")
print(f"  Questions with 0 ref: {len(zero_ref_questions)}")
if zero_ref_questions:
    print(f"  Zero-ref QIDs       : {zero_ref_questions}")

with open(OUT_CSV, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=['QuestionID', 'RefIndex', 'RawRef'])
    writer.writeheader()
    writer.writerows(rows)
print(f"\nCSV: {OUT_CSV}  ({len(rows)} rows)")

header = [
    "2025 ITE Reference Extraction Summary  v4",
    f"Source: {SOURCE}",
    f"Total refs extracted: {total_refs}",
    f"Avg per question: {total_refs/200:.1f}",
    f"Zero-ref questions: {len(zero_ref_questions)}",
    "=" * 60, ""
]
with open(OUT_SUMM, 'w', encoding='utf-8') as f:
    f.write('\n'.join(header + summary_lines))
print(f"Summary: {OUT_SUMM}")
