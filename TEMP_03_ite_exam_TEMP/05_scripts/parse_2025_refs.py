"""
parse_2025_refs.py
==================
Extracts bibliographic references from 2025_ITE_Critique.txt and maps them
sequentially to QuestionIDs Q2025-001 through Q2025-200.

Structure of source file:
  [copyright preamble]
  ANSWER: X
  [rationale text]
  References
  Author A, et al. Title. Journal. Year;vol(issue):pages.
  Author B, et al. Title. Journal. Year;vol(issue):pages.
  ANSWER: Y
  ...

Output:
  ref_2025_extracted.csv  — columns: QuestionID, RefIndex, Citation
  ref_2025_by_qid.csv     — columns: QuestionID, References (pipe-separated)
  parse_2025_summary.txt  — run log + stats

Paths are relative to the board_prep root.
"""

import re, os, csv

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE    = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep'
IN_TXT  = os.path.join(BASE, 'ite_exam', '02_working', '2025_ITE_Critique.txt')
OUT_CSV = os.path.join(BASE, 'ite_exam', '02_working', 'ref_2025_extracted.csv')
OUT_QID = os.path.join(BASE, 'ite_exam', '02_working', 'ref_2025_by_qid.csv')
LOG     = os.path.join(BASE, 'ite_exam', '02_working', 'parse_2025_summary.txt')

YEAR_PAT   = re.compile(r'\b(19|20)\d{2}\b')
AUTHOR_PAT = re.compile(r'^[A-Z][a-zA-Z\-\']+')   # line starts with uppercase surname

def split_into_blocks(text):
    """
    Split full text on ANSWER: markers.
    Returns list of raw block strings (the copyright preamble is block[0]).
    Each subsequent block contains rationale + References section.
    """
    # Normalise line endings
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # Split on ANSWER: (with or without preceding newline)
    parts = re.split(r'(?:^|\n)ANSWER:\s*[A-E]\s*\n', text)
    return parts

def extract_refs_from_block(block_text):
    """
    Find the References section in a critique block and return list of citations.
    Strategy: everything after the first "References" header line.
    Each non-empty line that starts with an uppercase letter and contains a
    4-digit year is treated as a new citation.
    Lines without a year are continuation of the previous citation.
    """
    # Find the References header
    ref_match = re.search(r'\nReferences?\s*\n', block_text, re.IGNORECASE)
    if not ref_match:
        return []

    ref_block = block_text[ref_match.end():]
    lines = ref_block.split('\n')

    citations = []
    current   = ''
    for line in lines:
        line = line.strip()
        if not line:
            if current:
                citations.append(current.strip())
                current = ''
            continue

        # A new citation starts with an uppercase letter and/or contains a year
        is_new_citation = (
            AUTHOR_PAT.match(line) or
            (YEAR_PAT.search(line) and not current)
        )

        if is_new_citation and current and len(current) > 20:
            citations.append(current.strip())
            current = line
        elif is_new_citation and not current:
            current = line
        else:
            # Continuation line — append with space
            current = (current + ' ' + line).strip() if current else line

    # Flush last citation
    if current and len(current) > 20:
        citations.append(current.strip())

    # Filter: must contain a 4-digit year to be a real citation
    citations = [c for c in citations if YEAR_PAT.search(c)]
    return citations

def main():
    print(f'Reading {IN_TXT}...')
    with open(IN_TXT, encoding='utf-8', errors='replace') as f:
        text = f.read()

    blocks = split_into_blocks(text)
    print(f'  Total blocks (incl. preamble): {len(blocks)}')

    # blocks[0] = copyright preamble, blocks[1..200] = question blocks
    question_blocks = blocks[1:]
    n_qs = len(question_blocks)
    print(f'  Question blocks found: {n_qs}')

    if n_qs != 200:
        print(f'  WARNING: Expected 200, got {n_qs}. Verify source file.')

    rows_expanded  = []   # QuestionID, RefIndex, Citation
    rows_by_qid    = []   # QuestionID, References (pipe-separated)
    zero_ref_ids   = []
    multi_ref_ids  = []
    total_refs     = 0

    for i, block in enumerate(question_blocks):
        qnum  = i + 1
        qid   = f'Q2025-{qnum:03d}'
        refs  = extract_refs_from_block(block)
        total_refs += len(refs)

        if len(refs) == 0:
            zero_ref_ids.append(qid)
        if len(refs) > 2:
            multi_ref_ids.append((qid, len(refs)))

        for j, ref in enumerate(refs):
            rows_expanded.append({
                'QuestionID': qid,
                'RefIndex':   j + 1,
                'Citation':   ref
            })

        rows_by_qid.append({
            'QuestionID': qid,
            'References': ' | '.join(refs) if refs else ''
        })

    # Write expanded CSV
    print(f'\nWriting {OUT_CSV}...')
    with open(OUT_CSV, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['QuestionID', 'RefIndex', 'Citation'])
        w.writeheader()
        w.writerows(rows_expanded)
    print(f'  {len(rows_expanded)} citation rows written')

    # Write by-QID CSV
    print(f'Writing {OUT_QID}...')
    with open(OUT_QID, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['QuestionID', 'References'])
        w.writeheader()
        w.writerows(rows_by_qid)
    print(f'  {len(rows_by_qid)} QID rows written')

    # Write log
    summary_lines = [
        '=== parse_2025_refs.py SUMMARY ===',
        f'Source: {IN_TXT}',
        f'Question blocks found: {n_qs}',
        f'Total citations extracted: {total_refs}',
        f'Avg refs per question: {total_refs/n_qs:.2f}' if n_qs else '',
        '',
        f'Questions with 0 refs ({len(zero_ref_ids)}):',
    ]
    for z in zero_ref_ids:
        summary_lines.append(f'  {z}')
    summary_lines += [
        '',
        f'Questions with >2 refs ({len(multi_ref_ids)}):',
    ]
    for qid, cnt in multi_ref_ids:
        summary_lines.append(f'  {qid}: {cnt} refs')
    summary_lines += [
        '',
        'Outputs:',
        f'  {OUT_CSV}',
        f'  {OUT_QID}',
    ]

    with open(LOG, 'w', encoding='utf-8') as f:
        f.write('\n'.join(summary_lines))
    print(f'\nLog written to {LOG}')

    # Console summary
    print('\n=== SUMMARY ===')
    print(f'  Questions parsed   : {n_qs}')
    print(f'  Total refs found   : {total_refs}')
    print(f'  Avg refs/question  : {total_refs/n_qs:.2f}' if n_qs else '')
    print(f'  Questions w/ 0 refs: {len(zero_ref_ids)}')
    print(f'  Questions w/ >2 refs: {len(multi_ref_ids)}')
    print('\n  Sample (Q2025-001):')
    for row in rows_expanded[:4]:
        print(f'    [{row["RefIndex"]}] {row["Citation"][:100]}')
    print('\nDone.')

if __name__ == '__main__':
    main()
