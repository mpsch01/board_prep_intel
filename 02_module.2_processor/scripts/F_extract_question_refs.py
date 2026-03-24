"""
F_extract_question_refs.py  v3
==============================
Sources:
  2020-2023: ite_q&a_2020-2024_word.docx  (Ref: prefix inline, ANSWER: boundary)
  2024:      uploaded file (same docx, section starting at para 38032)
             uses Reference/References heading + bare citations, ANSWER: boundary
  2025:      2025_ITE_Critique.docx  (Item N ANSWER: boundary, References heading)

Output:
  question_ref_pairs.csv     - one row per question-ref link
  new_refs_2025.csv          - 2025 refs not in tier DB (new citations)
  ref_match_report.txt       - validation summary
"""

import zipfile, re, csv, os
from lxml import etree
from difflib import SequenceMatcher
from collections import defaultdict

# ── Paths ─────────────────────────────────────────────────────────────────────
# 2020-2024 combined docx (on user's machine — use the version already validated)
SRC_20_24 = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\ite_refs\01_source\ite_q&a_2020-2024_word.docx'
SRC_2025  = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\ite_exam\01_source\2025_ITE_Critique.docx'
TIER_CSV  = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\ite_refs\02_working\ITE_Reference_Tiers_Clean.csv'
OUT_DIR   = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\ite_refs\02_working'
OUT_CSV   = os.path.join(OUT_DIR, 'question_ref_pairs.csv')
OUT_RPT   = os.path.join(OUT_DIR, 'ref_match_report.txt')
OUT_NEW   = os.path.join(OUT_DIR, 'new_refs_unmatched.csv')

MATCH_THRESHOLD = 0.70

NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

# ── Helpers ───────────────────────────────────────────────────────────────────
def get_paragraphs(docx_path):
    with zipfile.ZipFile(docx_path) as z:
        xml = z.read('word/document.xml')
    root = etree.fromstring(xml)
    def pt(p): return ''.join(t.text or '' for t in p.findall('.//w:t', NS))
    return [pt(p) for p in root.findall('.//w:p', NS)]

def normalize(s):
    s = str(s).lower()
    s = re.sub(r':\s+', ' ', s)
    s = re.sub(r'\.\s+', ' ', s)
    s = re.sub(r'[^\w\s]', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()

def fuzzy_score(a, b):
    return SequenceMatcher(None, a, b).ratio()

def load_tier_db(path):
    rows = []
    with open(path, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            rows.append({
                'CleanRef': row['CleanRef'],
                'Tier':     row['Tier'],
                'norm':     normalize(row['CleanRef'])
            })
    return rows

def match_ref(raw_ref, tier_db):
    norm_raw = normalize(raw_ref)
    best_score, best_row = 0, None
    for row in tier_db:
        s = fuzzy_score(norm_raw, row['norm'])
        if s > best_score:
            best_score, best_row = s, row
    if best_score >= MATCH_THRESHOLD:
        return best_row['CleanRef'], best_row['Tier'], round(best_score, 3)
    return '', 'Unmatched', round(best_score, 3)

# ── Parser: 2020-2023 (Ref: inline format) ────────────────────────────────────
def parse_2020_2023(paras):
    """
    Year header paragraphs: '2020', '2021', '2022', '2023'
    Boundary: 'ANSWER: X'
    Refs: 'Ref: ...' paragraph, may continue to next para(s)
    Multiple refs inline: ' 2) ', ' 3) ' etc.
    Stop before 2024 section.
    """
    records = []
    answer_pat  = re.compile(r'^ANSWER:\s*[A-E]', re.IGNORECASE)
    year_pat    = re.compile(r'^(2020|2021|2022|2023)$')
    ref_pat     = re.compile(r'^Ref:\s*(.+)', re.DOTALL)
    num_split   = re.compile(r'\s+\d+\)\s+')
    page_num    = re.compile(r'^\d{1,3}$')

    current_year  = None
    year_q_count  = defaultdict(int)

    i = 0
    while i < len(paras):
        p = paras[i].strip()

        if year_pat.match(p):
            current_year = int(p)
            i += 1
            continue

        if answer_pat.match(p) and current_year:
            year_q_count[current_year] += 1
            i += 1
            continue

        m = ref_pat.match(p)
        if m and current_year and year_q_count[current_year] > 0:
            qid      = f'Q{current_year}-{year_q_count[current_year]:03d}'
            ref_text = m.group(1)
            j = i + 1
            while j < len(paras):
                nxt = paras[j].strip()
                if not nxt or answer_pat.match(nxt) or ref_pat.match(nxt) or year_pat.match(nxt):
                    break
                if page_num.match(nxt):
                    j += 1
                    continue
                ref_text += ' ' + nxt
                j += 1
            i = j
            for part in num_split.split(ref_text):
                part = re.sub(r'\s+\d+\s*$', '', part).strip()
                if len(part) > 20:
                    records.append((qid, current_year, part))
            continue

        i += 1

    return records

# ── Parser: 2024 (Reference heading format, ANSWER: boundary) ─────────────────
def parse_2024(paras, start_idx=38032):
    """
    Section starts at para start_idx ('2024' year marker).
    Boundary: 'ANSWER: X'
    Refs listed after 'Reference' or 'References' heading.
    Citations may split across paragraphs.
    """
    records = []

    answer_pat = re.compile(r'^ANSWER:\s*[A-E]', re.IGNORECASE)
    ref_head   = re.compile(r'^References?\s*$', re.IGNORECASE)
    cite_hint  = re.compile(r'[A-Z][a-zA-Z].*\b(19|20)\d\d\b')

    section    = paras[start_idx:]
    q_count    = 0
    in_refs    = False
    pending    = ''

    def flush(qid, text, out):
        text = text.strip()
        if text and cite_hint.search(text) and len(text) > 20:
            out.append((qid, 2024, text))

    i = 0
    while i < len(section):
        p = section[i].strip()

        if answer_pat.match(p):
            flush(f'Q2024-{q_count:03d}', pending, records)
            pending = ''
            in_refs  = False
            q_count += 1
            i += 1
            continue

        if ref_head.match(p) and q_count > 0:
            flush(f'Q2024-{q_count:03d}', pending, records)
            pending = ''
            in_refs  = True
            i += 1
            continue

        if in_refs and q_count > 0:
            if not p:
                flush(f'Q2024-{q_count:03d}', pending, records)
                pending = ''
                i += 1
                continue
            is_new = bool(re.match(r'^[A-Z][a-zA-Z]', p)) and bool(cite_hint.search(p))
            if is_new:
                flush(f'Q2024-{q_count:03d}', pending, records)
                pending = p
            else:
                pending += ' ' + p

        i += 1

    flush(f'Q2024-{q_count:03d}', pending, records)
    return records

# ── Parser: 2025 (Item N ANSWER: boundary) ────────────────────────────────────
def parse_2025(paras):
    records  = []
    item_pat = re.compile(r'^Item\s+(\d+)\s+ANSWER', re.IGNORECASE)
    ref_head = re.compile(r'^References?\s*$', re.IGNORECASE)
    cite_hint= re.compile(r'[A-Z][a-zA-Z].*\b(19|20)\d\d\b')

    current_qid = None
    in_refs      = False
    pending      = ''

    def flush(qid, text, out):
        text = text.strip()
        if text and cite_hint.search(text) and len(text) > 20:
            out.append((qid, 2025, text))

    i = 0
    while i < len(paras):
        p = paras[i].strip()

        m = item_pat.match(p)
        if m:
            flush(current_qid, pending, records)
            pending = ''
            in_refs  = False
            current_qid = f'Q2025-{int(m.group(1)):03d}'
            i += 1
            continue

        if ref_head.match(p) and current_qid:
            flush(current_qid, pending, records)
            pending = ''
            in_refs  = True
            i += 1
            continue

        if in_refs and current_qid:
            if not p:
                flush(current_qid, pending, records)
                pending = ''
                i += 1
                continue
            is_new = bool(re.match(r'^[A-Z][a-zA-Z]', p)) and bool(cite_hint.search(p))
            if is_new:
                flush(current_qid, pending, records)
                pending = p
            else:
                pending += ' ' + p

        i += 1

    flush(current_qid, pending, records)
    return records

# ── QID offset translation (pairs -> Enriched format) ─────────────────────────
YEAR_OFFSET = {2020: 0, 2021: 200, 2022: 400, 2023: 600, 2024: 800, 2025: 0}

def to_enriched_qid(qid, year):
    offset = YEAR_OFFSET.get(year, 0)
    if offset == 0:
        return qid
    m = re.match(r'(Q\d{4}-)(\d+)', qid)
    if m:
        return f'{m.group(1)}{int(m.group(2)) + offset:03d}'
    return qid

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print('Loading tier database...')
    tier_db = load_tier_db(TIER_CSV)
    print(f'  {len(tier_db)} refs in tier DB')

    print('\nParsing 2020-2023 (Ref: format)...')
    paras_all = get_paragraphs(SRC_20_24)
    recs_2023 = parse_2020_2023(paras_all)
    print(f'  {len(recs_2023)} pairs extracted')
    for yr in [2020,2021,2022,2023]:
        qs = set(r[0] for r in recs_2023 if r[1]==yr)
        rs = [r for r in recs_2023 if r[1]==yr]
        print(f'    {yr}: {len(qs)} questions, {len(rs)} refs')

    print('\nParsing 2024 (Reference heading format)...')
    recs_2024 = parse_2024(paras_all, start_idx=38032)
    print(f'  {len(recs_2024)} pairs extracted')
    qs_2024 = set(r[0] for r in recs_2024)
    print(f'  {len(qs_2024)} unique 2024 questions with refs')

    print('\nParsing 2025...')
    paras_2025 = get_paragraphs(SRC_2025)
    recs_2025  = parse_2025(paras_2025)
    print(f'  {len(recs_2025)} pairs extracted')
    qs_2025 = set(r[0] for r in recs_2025)
    print(f'  {len(qs_2025)} unique 2025 questions with refs')

    all_recs = recs_2023 + recs_2024 + recs_2025
    print(f'\nTotal pairs: {len(all_recs)}')

    print('\nFuzzy matching against tier DB...')
    results      = []
    unmatched    = []
    tier_counts  = defaultdict(int)
    qid_counter  = defaultdict(int)

    for qid, year, raw in all_recs:
        enriched_qid = to_enriched_qid(qid, year)
        qid_counter[enriched_qid] += 1
        ref_idx = qid_counter[enriched_qid]
        matched, tier, score = match_ref(raw, tier_db)
        results.append({
            'QuestionID':     enriched_qid,
            'QuestionID_raw': qid,
            'ExamYear':       year,
            'RefIndex':       ref_idx,
            'RefRaw':         raw,
            'RefMatched':     matched,
            'Tier':           tier,
            'MatchScore':     score
        })
        tier_counts[tier] += 1
        if tier == 'Unmatched':
            unmatched.append((enriched_qid, year, raw, score))

    # Write main CSV
    print(f'\nWriting {OUT_CSV}...')
    with open(OUT_CSV, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['QuestionID','QuestionID_raw','ExamYear','RefIndex','RefRaw','RefMatched','Tier','MatchScore'])
        w.writeheader()
        w.writerows(results)
    print(f'  {len(results)} rows written')

    # Write unmatched refs
    unmatched_refs = sorted(set(raw for _,yr,raw,_ in unmatched))
    print(f'Writing {OUT_NEW}...')
    with open(OUT_NEW, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['ExamYear','RefRaw','BestScore'])
        for qid, yr, raw, score in sorted(unmatched, key=lambda x: (x[1], x[2])):
            w.writerow([yr, raw, score])
    print(f'  {len(unmatched_refs)} unique unmatched refs written')

    # Write report
    print(f'Writing {OUT_RPT}...')
    with open(OUT_RPT, 'w', encoding='utf-8') as f:
        f.write('=== QUESTION-REF EXTRACTION REPORT v3 ===\n\n')
        f.write(f'2020-2023 pairs : {len(recs_2023)}\n')
        f.write(f'2024 pairs      : {len(recs_2024)}\n')
        f.write(f'2025 pairs      : {len(recs_2025)}\n')
        f.write(f'Total pairs     : {len(all_recs)}\n\n')
        f.write('TIER DISTRIBUTION:\n')
        for tier in ['Must-Read','Core','Supplementary','Unmatched']:
            f.write(f'  {tier:<15}: {tier_counts[tier]}\n')
        mr = (len(all_recs) - tier_counts["Unmatched"]) / len(all_recs) * 100
        f.write(f'\nMatch rate: {mr:.1f}%\n\n')
        f.write(f'=== UNMATCHED ({len(unmatched)}) ===\n\n')
        for qid, yr, raw, score in sorted(unmatched, key=lambda x: (x[1], x[2])):
            f.write(f'[{qid}/{yr}] best={score:.3f}\n  {raw[:250]}\n\n')

    print('\n=== SUMMARY ===')
    for tier in ['Must-Read','Core','Supplementary','Unmatched']:
        print(f'  {tier:<15}: {tier_counts[tier]}')
    print(f'  Match rate      : {(len(all_recs)-tier_counts["Unmatched"])/len(all_recs)*100:.1f}%')
    print('\nDone.')

if __name__ == '__main__':
    main()
