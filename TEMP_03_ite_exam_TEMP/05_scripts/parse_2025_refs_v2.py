"""
parse_2025_refs_v2.py
=====================
Robust version: matches each critique block to its QID by comparing the
rationale text in 2025_ITE_Critique.txt against the Explanation field in
ABFM_ITE_AI_Tagged.csv.

Why: 2025 has 9 Deleted-Content questions in the DB; only some appear in
the critique book (ABFM may include deleted Qs in the book). Sequential
numbering fails when the count mismatches (197 blocks vs 200 DB rows).

Matching algorithm:
  For each critique block, take the first 120 chars of rationale text.
  For each Q2025-* in the CSV, take the first 120 chars of Explanation.
  Use SequenceMatcher to find best match (threshold >= 0.75).
  Unmatched blocks are flagged.

Outputs:
  ref_2025_extracted.csv     — QuestionID, RefIndex, Citation
  ref_2025_by_qid.csv        — QuestionID, References (pipe-separated)
  parse_2025_summary.txt     — run log
"""

import re, os, csv
from difflib import SequenceMatcher

BASE     = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep'
IN_TXT   = os.path.join(BASE, 'ite_exam', '02_working', '2025_ITE_Critique.txt')
IN_CSV   = os.path.join(BASE, 'ite_exam', '02_working', 'ABFM_ITE_AI_Tagged.csv')
OUT_CSV  = os.path.join(BASE, 'ite_exam', '02_working', 'ref_2025_extracted.csv')
OUT_QID  = os.path.join(BASE, 'ite_exam', '02_working', 'ref_2025_by_qid.csv')
LOG      = os.path.join(BASE, 'ite_exam', '02_working', 'parse_2025_summary.txt')

YEAR_PAT   = re.compile(r'\b(19|20)\d{2}\b')
MATCH_THRES = 0.72
PREVIEW_LEN = 180   # chars to compare for rationale matching

def normalize_ws(text):
    """Collapse whitespace for comparison."""
    return re.sub(r'\s+', ' ', (text or '').strip()).lower()

def split_into_blocks(text):
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    parts = re.split(r'(?:^|\n)ANSWER:\s*[A-E]\s*\n', text)
    return parts[1:]   # drop preamble

def get_block_preview(block_text):
    """Return normalised first PREVIEW_LEN chars of rationale (before References)."""
    ref_match = re.search(r'\nReferences?\s*\n', block_text, re.IGNORECASE)
    rationale = block_text[:ref_match.start()] if ref_match else block_text[:500]
    norm = normalize_ws(rationale)
    return norm[:PREVIEW_LEN]

def extract_refs_from_block(block_text):
    """Extract citation strings from References section of a critique block."""
    ref_match = re.search(r'\nReferences?\s*\n', block_text, re.IGNORECASE)
    if not ref_match:
        return []

    ref_block = block_text[ref_match.end():]
    lines     = ref_block.split('\n')
    citations = []
    current   = ''

    for line in lines:
        line = line.strip()
        if not line:
            if current and len(current) > 20:
                citations.append(current.strip())
                current = ''
            continue

        starts_upper = bool(re.match(r'^[A-Z][a-zA-Z\-\']+', line))
        has_year     = bool(YEAR_PAT.search(line))
        is_new_cite  = starts_upper and has_year

        if is_new_cite and current and len(current) > 20:
            citations.append(current.strip())
            current = line
        elif is_new_cite and not current:
            current = line
        else:
            current = (current + ' ' + line).strip() if current else line

    if current and len(current) > 20:
        citations.append(current.strip())

    return [c for c in citations if YEAR_PAT.search(c)]

def main():
    # ── Load critique blocks ───────────────────────────────────────────────────
    print(f'Reading critique file...')
    with open(IN_TXT, encoding='utf-8', errors='replace') as f:
        text = f.read()
    blocks = split_into_blocks(text)
    print(f'  {len(blocks)} critique blocks found')

    # ── Load Q2025 explanations from CSV ──────────────────────────────────────
    print(f'Loading Q2025 explanations from CSV...')
    q2025 = {}
    with open(IN_CSV, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if str(row.get('ExamYear', '')).strip() == '2025':
                qid  = row.get('Question ID', '').strip()
                expl = normalize_ws(row.get('Explanation', ''))[:PREVIEW_LEN]
                q2025[qid] = expl
    print(f'  {len(q2025)} Q2025 entries loaded')

    qids_sorted = sorted(q2025.keys())

    # ── Match each critique block to a QID ────────────────────────────────────
    print(f'\nMatching blocks to QIDs (threshold={MATCH_THRES})...')
    used_qids   = set()
    block_map   = {}   # block_idx → (qid, match_score)

    for bi, block in enumerate(blocks):
        preview = get_block_preview(block)
        best_score, best_qid = 0.0, None

        for qid in qids_sorted:
            if qid in used_qids:
                continue
            score = SequenceMatcher(None, preview, q2025[qid]).ratio()
            if score > best_score:
                best_score, best_qid = score, qid

        if best_score >= MATCH_THRES and best_qid:
            block_map[bi] = (best_qid, round(best_score, 3))
            used_qids.add(best_qid)
        else:
            block_map[bi] = (None, round(best_score, 3))

    matched   = sum(1 for v in block_map.values() if v[0])
    unmatched = len(blocks) - matched
    print(f'  Matched   : {matched}')
    print(f'  Unmatched : {unmatched}')

    # ── Extract refs and build output ─────────────────────────────────────────
    rows_expanded = []
    rows_by_qid   = {}

    zero_ref_qids = []

    for bi, block in enumerate(blocks):
        qid, mscore = block_map[bi]
        if not qid:
            print(f'  Block {bi+1:03d}: NO MATCH (best={mscore}) — skipping')
            continue

        refs = extract_refs_from_block(block)
        if not refs:
            zero_ref_qids.append(qid)

        for j, ref in enumerate(refs):
            rows_expanded.append({
                'QuestionID':   qid,
                'RefIndex':     j + 1,
                'Citation':     ref,
                'MatchScore':   mscore,
            })

        rows_by_qid[qid] = refs

    # ── Build by-QID rows for ALL Q2025 (including unmatched/no-ref) ──────────
    final_by_qid = []
    for qid in qids_sorted:
        refs = rows_by_qid.get(qid, [])
        final_by_qid.append({
            'QuestionID': qid,
            'References': ' | '.join(refs),
        })

    # ── Write outputs ──────────────────────────────────────────────────────────
    print(f'\nWriting {OUT_CSV}...')
    with open(OUT_CSV, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['QuestionID','RefIndex','Citation','MatchScore'])
        w.writeheader()
        w.writerows(rows_expanded)
    print(f'  {len(rows_expanded)} citation rows written')

    print(f'Writing {OUT_QID}...')
    with open(OUT_QID, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['QuestionID','References'])
        w.writeheader()
        w.writerows(final_by_qid)
    print(f'  {len(final_by_qid)} QID rows written')

    # ── Log ───────────────────────────────────────────────────────────────────
    total_refs  = len(rows_expanded)
    multi_refs  = [(qid, len(refs)) for qid, refs in rows_by_qid.items() if len(refs) > 2]
    missing_qids = [qid for qid in qids_sorted if qid not in rows_by_qid]

    summary = [
        '=== parse_2025_refs_v2.py SUMMARY ===',
        f'Critique blocks found    : {len(blocks)}',
        f'Blocks matched to QIDs   : {matched}',
        f'Blocks unmatched         : {unmatched}',
        f'Total citations extracted: {total_refs}',
        f'Avg refs per matched Q   : {total_refs/matched:.2f}' if matched else '',
        '',
        f'Q2025 IDs with 0 refs ({len(zero_ref_qids)}): {zero_ref_qids}',
        f'Q2025 IDs not in critique ({len(missing_qids)}): {missing_qids}',
        '',
        f'Qs with >2 refs ({len(multi_refs)}):',
    ]
    for qid, cnt in multi_refs[:20]:
        summary.append(f'  {qid}: {cnt} refs')
    with open(LOG, 'w', encoding='utf-8') as f:
        f.write('\n'.join(summary))

    print(f'\nLog: {LOG}')
    print(f'\n=== SUMMARY ===')
    print(f'  Matched     : {matched}/{len(blocks)}')
    print(f'  0-ref Qs    : {len(zero_ref_qids)}')
    print(f'  Missing IDs : {missing_qids}')
    print(f'  Total refs  : {total_refs}')
    print('\nDone.')

if __name__ == '__main__':
    main()
