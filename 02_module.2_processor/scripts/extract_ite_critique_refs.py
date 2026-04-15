"""
extract_ite_critique_refs.py  v2
================================
Extract question-reference pairs from ITE critique PDFs.
PDF-native, zero API cost (pdfplumber only).

Usage:
    python extract_ite_critique_refs.py --pdf /path/to/2025_ITE_Critique.pdf --year 2025
    python extract_ite_critique_refs.py --pdf /path/to/2025_ITE_Critique.pdf --year 2025 --dry-run
    python extract_ite_critique_refs.py --pdf /path/to/2025_ITE_Critique.pdf --year 2025 --commit

Output modes:
    default   → writes <year>_critique_refs_staging.json to M2/outputs/ for review
    --dry-run → prints summary to console only, no files written
    --commit  → writes staging file AND inserts into DB
                (DELETEs existing question_ref_pairs rows for that year first)

Architecture:
    dispatch(year) → PARSERS.get(year, parse_modern)
    parse_modern() handles 2025+ one-item-per-page format.
    parse_stream() handles multi-item-per-page stream format (2024 and earlier).
    Add year-specific overrides to PARSERS dict if format changes.

2025+ PDF format (one item per page):
    Item N
    ANSWER: X
    [rationale text]
    References
    [citation 1, possibly line-wrapped]
    [citation 2, possibly line-wrapped]
    YYYY ITE RATIONALE BOOK – PAGE N

2024 PDF format (continuous stream, ~2 items per page):
    Item N\nANSWER: X\n[rationale]\nReference(s)\n[citations]\nItem N+1\n...
    References can span page breaks. USPSTF web citations end with "Updated Month Day, YEAR."
    rather than the journal year;volume pattern.

Matching strategy:
    1. Exact match against articles.clean_ref (case-sensitive strip)
    2. Fuzzy match (difflib SequenceMatcher) at threshold FUZZY_THRESHOLD
    3. Unmatched → clean_ref=None, match_status='unmatched'
"""

import re
import json
import sqlite3
import argparse
from pathlib import Path
from difflib import SequenceMatcher

import pdfplumber

# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH      = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"
OUT_DIR      = SCRIPT_DIR.parent / "outputs"

# ── Constants ──────────────────────────────────────────────────────────────────
FUZZY_THRESHOLD = 0.80   # min score for a fuzzy match to count
MIN_REF_LEN     = 20     # ignore citation fragments shorter than this


# ── Fallback citation scanner ──────────────────────────────────────────────────
# When the primary parser finds no reference section for a question block,
# this function does a secondary sweep of the raw block text looking for
# citation-like patterns. It is intentionally broad — better to flag a
# possible citation for manual review than to silently drop it.

# Signals that a line is likely part of a medical citation
_JOURNAL_YEAR   = re.compile(r'\b(19|20)\d{2};?\d*[\(\[]?\d*[\)\]]?:')  # year;vol or year;vol(issue):
_YEAR_AT_END    = re.compile(r'\b(19|20)\d{2}\.?\s*$')                   # ends with a year
_KNOWN_JOURNALS = re.compile(
    r'\b(Am Fam Physician|N Engl J Med|JAMA|Lancet|Ann Intern Med|'
    r'BMJ|Pediatrics|Circulation|Chest|J Clin|Cochrane|Obstet Gynecol|'
    r'J Am|Clin|Med|Health|Fam Pract|Acad Emerg|Emerg Med)\b',
    re.IGNORECASE
)
_USPSTF_SIGNAL  = re.compile(r'preventive services task force|uspstf|recommendation statement', re.IGNORECASE)
_AUTHOR_PATTERN = re.compile(r'^[A-Z][a-z]+(?: [A-Z][A-Za-z]*,?)+')     # "Smith AB," style opener


def fallback_citation_scan(block_text: str, qid: str) -> list[str]:
    """
    Secondary sweep for citation text when the primary parser found no reference section.
    Looks for lines that exhibit citation hallmarks: journal+year patterns, USPSTF signals,
    or known journal name substrings. Returns a list of candidate citation strings.

    These are logged with match_status='fallback_scan' so they can be reviewed manually
    rather than being automatically trusted.
    """
    lines     = [l.strip() for l in block_text.split('\n') if l.strip()]
    found     = []
    buffer    = []

    def flush():
        if buffer:
            candidate = ' '.join(buffer).strip()
            if len(candidate) >= MIN_REF_LEN:
                found.append(candidate)
            buffer.clear()

    for line in lines:
        is_citation_line = (
            _JOURNAL_YEAR.search(line) or
            _YEAR_AT_END.search(line) or
            _KNOWN_JOURNALS.search(line) or
            _USPSTF_SIGNAL.search(line)
        )
        is_new_block = re.match(r'^Item\s+\d+', line) or re.match(r'^ANSWER:', line)

        if is_new_block:
            flush()
        elif is_citation_line:
            buffer.append(line)
        elif buffer and line:
            # Possible continuation of a wrapped citation
            buffer.append(line)
        else:
            flush()

    flush()
    return found

# ── Dispatcher ─────────────────────────────────────────────────────────────────
# Add year-specific parser overrides here if ABFM changes their format.
# Key = int year, value = callable(pdf_path, year) -> list[dict]
def dispatch(pdf_path: Path, year: int) -> list[dict]:
    # PARSERS populated at bottom of file after all parsers are defined
    parser = PARSERS.get(year, parse_modern)
    return parser(pdf_path, year)


# ── Citation splitting ──────────────────────────────────────────────────────────
def split_citations(lines: list[str]) -> list[str]:
    """
    Reassemble line-wrapped citations from the References section.

    Strategy: accumulate lines into a buffer. Flush the buffer (start a new
    citation) when a line starts with a capital letter AND the current buffer
    looks complete. Two completion signals:

      1. Journal citation:  buffer contains year;volume  (e.g. '2002;136')
      2. Web/report citation: buffer ends with a 4-digit year + optional period
         (e.g. USPSTF entries ending 'Updated April 13, 2021.')

    This correctly handles:
      - Wrapped journal citations: 'Stone EG... Ann Intern Med.\n2002;136(9):641-651.'
      - Journal name continuations: 'Diabetes\nCare. 2025;...' → not flushed because
        '2025' is mid-buffer, not at end
      - USPSTF web citations: each ends with 'Updated Month Day, YEAR.' → flushed
        correctly when next USPSTF entry starts
    """
    journal_complete = re.compile(r'\b(19|20)\d{2};\d+')          # year;volume
    web_complete     = re.compile(r'\b(19|20)\d{2}\.?\s*$')        # year at end of buffer

    def is_complete(buf: str) -> bool:
        return bool(journal_complete.search(buf)) or bool(web_complete.search(buf))

    citations = []
    current   = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if re.match(r'^[A-Z]', line) and current:
            buf = ' '.join(current)
            if is_complete(buf):
                citations.append(buf.strip())
                current = [line]
            else:
                # Likely a journal name continuation (e.g. 'Care.', 'Medicine.')
                current.append(line)
        else:
            current.append(line)

    if current:
        citations.append(' '.join(current).strip())

    year_hint = re.compile(r'\b(19|20)\d{2}\b')
    return [c for c in citations if len(c) >= MIN_REF_LEN and year_hint.search(c)]


# ── Parser: 2025+ (one item per page) ──────────────────────────────────────────
def parse_modern(pdf_path: Path, year: int) -> list[dict]:
    """
    Default parser for 2025+ critique PDF format.

    Per-page structure:
        Item N          ← bold, top of page
        ANSWER: X
        [rationale]
        References      ← section marker
        [citations]
        YYYY ITE RATIONALE BOOK – PAGE N   ← footer, stripped
    """
    records    = []
    item_pat   = re.compile(r'^Item\s+(\d+)$', re.IGNORECASE)
    ref_marker = re.compile(r'^References?\s*$', re.IGNORECASE)
    footer_pat = re.compile(r'^\d{4}\s+ITE\s+RATIONALE\s+BOOK', re.IGNORECASE)

    with pdfplumber.open(pdf_path) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            text = page.extract_text()
            if not text:
                continue

            lines = text.split('\n')

            # Strip footer lines
            lines = [l for l in lines if not footer_pat.match(l.strip())]

            # Find "Item N"
            item_num = None
            for line in lines:
                m = item_pat.match(line.strip())
                if m:
                    item_num = int(m.group(1))
                    break

            if item_num is None:
                continue  # cover page or non-item page

            qid = f'QID-{year}-{item_num:04d}'

            # Find "References" marker
            ref_start_idx = None
            for i, line in enumerate(lines):
                if ref_marker.match(line.strip()):
                    ref_start_idx = i
                    break

            if ref_start_idx is None:
                # No 'References' section found — run fallback scan on this block
                candidates = fallback_citation_scan(block, qid)
                for ref_idx, raw_ref in enumerate(candidates, start=1):
                    records.append({
                        'qid'         : qid,
                        'ref_raw'     : raw_ref,
                        'ref_index'   : ref_idx,
                        'exam_year'   : year,
                        'match_status': 'fallback_scan',
                    })
                continue

            ref_lines = [l for l in lines[ref_start_idx + 1:] if l.strip()]

            for ref_idx, raw_ref in enumerate(split_citations(ref_lines), start=1):
                records.append({
                    'qid'      : qid,
                    'ref_raw'  : raw_ref,
                    'ref_index': ref_idx,
                    'exam_year': year,
                })

    return records


# ── Parser: stream format (2024 and earlier multi-item-per-page) ───────────────
def parse_stream(pdf_path: Path, year: int) -> list[dict]:
    """
    Parser for ITE critique PDFs where multiple items appear per page and
    references can span page breaks (2024 and earlier format).

    Strategy:
      1. Extract text from all pages (skip cover), join into one stream.
      2. Locate item boundaries by finding 'Item N\\nANSWER:' patterns.
      3. For each item block, find 'Reference(s)' heading and extract citations.
      4. Use split_citations() — handles both journal and web/USPSTF formats.
    """
    records   = []
    ref_marker = re.compile(r'^References?\s*$', re.IGNORECASE)

    # Step 1: extract full text stream (skip page 0 = cover)
    pages_text = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages[1:]:
            text = page.extract_text()
            if text:
                pages_text.append(text)
    full_text = '\n'.join(pages_text)

    # Step 2: find all item start positions
    # Match 'Item N\nANSWER: X' — specific enough to avoid false matches in rationale
    item_boundary = re.compile(
        r'\nItem\s+(\d+)\nANSWER:\s*[A-E]', re.IGNORECASE
    )
    matches = list(item_boundary.finditer(full_text))

    if not matches:
        print(f"  WARNING: No item boundaries found in {pdf_path.name}")
        return records

    # Step 3: slice content per item
    for i, m in enumerate(matches):
        item_num    = int(m.group(1))
        block_start = m.start()
        block_end   = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        block       = full_text[block_start:block_end]

        lines = block.split('\n')

        # Find References heading within this block
        ref_start_idx = None
        for j, line in enumerate(lines):
            if ref_marker.match(line.strip()):
                ref_start_idx = j
                break

        if ref_start_idx is None:
            # No section header found — fallback scan on the full block
            qid = f'QID-{year}-{item_num:04d}'
            candidates = fallback_citation_scan(block, qid)
            for ref_idx, raw_ref in enumerate(candidates, start=1):
                records.append({
                    'qid'         : qid,
                    'ref_raw'     : raw_ref,
                    'ref_index'   : ref_idx,
                    'exam_year'   : year,
                    'match_status': 'fallback_scan',
                })
            continue

        ref_lines = [l.strip() for l in lines[ref_start_idx + 1:] if l.strip()]
        qid       = f'QID-{year}-{item_num:04d}'

        for ref_idx, raw_ref in enumerate(split_citations(ref_lines), start=1):
            records.append({
                'qid'      : qid,
                'ref_raw'  : raw_ref,
                'ref_index': ref_idx,
                'exam_year': year,
            })

    return records


def parse_legacy(pdf_path: Path, year: int) -> list[dict]:
    """
    Parser for ITE critique PDFs (2018–2023) where references use 'Ref:' inline
    prefix rather than a 'References' section header.

    Format observed in 2018–2023:
        Item N
        ANSWER: X
        [rationale text, possibly multi-line]
        Ref: Author A, Author B: Title. Journal Year;Vol(Issue):Pages.
        2) Author C: Second citation. Journal Year;Vol(Issue):Pages.
        Item N+1
        ANSWER: Y
        ...

    Strategy:
      1. Extract full text stream (skip cover page).
      2. Find item boundaries: 'Item N\\nANSWER: [A-E]'.
      3. Within each block, scan for lines starting with 'Ref:'.
      4. Collect continuation lines (wrapped citations) until next Item or EOF.
      5. Split numbered sub-citations (2), 3), etc.) into individual records.
    """
    records = []

    # Step 1: full text stream
    pages_text = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages[1:]:
            text = page.extract_text()
            if text:
                pages_text.append(text)
    full_text = '\n'.join(pages_text)

    # Step 2: item boundaries (same pattern as parse_stream)
    item_boundary = re.compile(
        r'\nItem\s+(\d+)\nANSWER:\s*[A-E]', re.IGNORECASE
    )
    matches = list(item_boundary.finditer(full_text))

    if not matches:
        print(f"  WARNING: No item boundaries found in {pdf_path.name}")
        return records

    # Step 3-5: per-item extraction
    for i, m in enumerate(matches):
        item_num  = int(m.group(1))
        block_end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        block     = full_text[m.start():block_end]
        lines     = block.split('\n')
        qid       = f'QID-{year}-{item_num:04d}'

        # Find the Ref: line within this block
        ref_lines = []
        in_ref    = False
        for line in lines:
            stripped = line.strip()
            if re.match(r'^Ref:\s+', stripped, re.IGNORECASE):
                in_ref = True
                # Strip the 'Ref: ' prefix
                ref_lines.append(stripped[5:].strip())
            elif in_ref:
                # Continuation line: keep if non-empty and not a new Item
                if re.match(r'^Item\s+\d+', stripped, re.IGNORECASE):
                    break
                if stripped:
                    ref_lines.append(stripped)
            # else: still in rationale, skip

        if not ref_lines:
            # No 'Ref:' line found — run fallback scan on the full block
            candidates = fallback_citation_scan(block, qid)
            for ref_idx, raw_ref in enumerate(candidates, start=1):
                records.append({
                    'qid'         : qid,
                    'ref_raw'     : raw_ref,
                    'ref_index'   : ref_idx,
                    'exam_year'   : year,
                    'match_status': 'fallback_scan',
                })
            continue

        # Reassemble the full Ref block as one string, then split numbered citations
        ref_block = ' '.join(ref_lines)

        # Split on numbered sub-citations: ' 2) ', ' 3) ', etc.
        # These appear inline within the Ref block
        sub_refs = re.split(r'\s+\d+\)\s+', ref_block)

        for ref_idx, raw_ref in enumerate(sub_refs, start=1):
            raw_ref = raw_ref.strip()
            if len(raw_ref) < 20:
                continue
            records.append({
                'qid'      : qid,
                'ref_raw'  : raw_ref,
                'ref_index': ref_idx,
                'exam_year': year,
            })

    return records


# ── Parser registry (populated after all parsers are defined) ──────────────────
PARSERS = {
    # 2024: multi-item-per-page stream, 'References' section header
    2024: parse_stream,
    # 2018–2023: multi-item-per-page, 'Ref:' inline prefix format
    2023: parse_legacy,
    2022: parse_legacy,
    2021: parse_legacy,
    2020: parse_legacy,
    2019: parse_legacy,
    2018: parse_legacy,
    # 2025+: one item per page → parse_modern (default, no entry needed)
}

# ── DB matching ────────────────────────────────────────────────────────────────
def load_article_refs(db_path: Path) -> list[dict]:
    """Load all articles.clean_ref + article_id + tier for matching."""
    conn = sqlite3.connect(db_path)
    cur  = conn.cursor()
    cur.execute("SELECT article_id, clean_ref, tier FROM articles WHERE clean_ref IS NOT NULL")
    rows = [{'article_id': r[0], 'clean_ref': r[1], 'tier': r[2]} for r in cur.fetchall()]
    conn.close()
    return rows


def normalize(s: str) -> str:
    """Lightweight normalization for fuzzy comparison."""
    s = s.lower()
    s = re.sub(r'[:\-–—]', ' ', s)          # unify separators
    s = re.sub(r'[^\w\s]', ' ', s)           # strip punctuation
    s = re.sub(r'\s+', ' ', s)               # collapse whitespace
    return s.strip()


def match_ref(raw_ref: str, article_refs: list[dict]) -> dict:
    """
    Match a raw citation against the article DB.

    Returns a dict with: clean_ref, article_id, tier, match_score, match_status
    """
    raw_stripped  = raw_ref.strip()
    raw_norm      = normalize(raw_stripped)

    # Strategy 1: exact string match
    for row in article_refs:
        if row['clean_ref'].strip() == raw_stripped:
            return {
                'clean_ref'   : row['clean_ref'],
                'article_id'  : row['article_id'],
                'tier'        : row['tier'],
                'match_score' : 1.0,
                'match_status': 'matched',
            }

    # Strategy 2: fuzzy match
    best_score = 0.0
    best_row   = None
    for row in article_refs:
        score = SequenceMatcher(None, raw_norm, normalize(row['clean_ref'])).ratio()
        if score > best_score:
            best_score = score
            best_row   = row

    if best_score >= FUZZY_THRESHOLD and best_row:
        return {
            'clean_ref'   : best_row['clean_ref'],
            'article_id'  : best_row['article_id'],
            'tier'        : best_row['tier'],
            'match_score' : round(best_score, 4),
            'match_status': 'fuzzy_matched',
        }

    # Unmatched
    return {
        'clean_ref'   : None,
        'article_id'  : None,
        'tier'        : 'Unmatched',
        'match_score' : round(best_score, 4),
        'match_status': 'unmatched',
    }


# ── Assemble full QRP rows ─────────────────────────────────────────────────────
def build_qrp_rows(records: list[dict], article_refs: list[dict]) -> list[dict]:
    rows = []
    for rec in records:
        match = match_ref(rec['ref_raw'], article_refs)
        rows.append({
            'qid'         : rec['qid'],
            'clean_ref'   : match['clean_ref'],
            'ref_raw'     : rec['ref_raw'],
            'tier'        : match['tier'],
            'match_score' : match['match_score'],
            'ref_index'   : rec['ref_index'],
            'match_status': match['match_status'],
            'exam_year'   : rec['exam_year'],
            # metadata (not written to DB, for staging review only)
            '_article_id' : match['article_id'],
        })
    return rows


# ── Output ─────────────────────────────────────────────────────────────────────
def write_staging(rows: list[dict], year: int) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"{year}_critique_refs_staging.json"
    if out_path.exists():
        print(f"  Overwriting existing staging file: {out_path.name}")
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)
    return out_path


def commit_to_db(rows: list[dict], db_path: Path, year: int) -> int:
    """
    Delete existing question_ref_pairs for the given year, then insert new rows.
    Returns count of rows inserted.
    """
    conn = sqlite3.connect(db_path)
    cur  = conn.cursor()

    cur.execute("DELETE FROM question_ref_pairs WHERE exam_year = ?", (year,))
    deleted = cur.rowcount

    db_rows = [
        (
            r['qid'],
            r['clean_ref'],
            r['ref_raw'],
            r['tier'],
            r['match_score'],
            r['ref_index'],
            r['match_status'],
            r['exam_year'],
        )
        for r in rows
    ]

    cur.executemany(
        """
        INSERT INTO question_ref_pairs
            (qid, clean_ref, ref_raw, tier, match_score, ref_index, match_status, exam_year)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        db_rows,
    )
    inserted = cur.rowcount
    conn.commit()
    conn.close()

    print(f"  Deleted {deleted} existing {year} QRP rows.")
    print(f"  Inserted {inserted} new rows.")
    return inserted


# ── Summary ────────────────────────────────────────────────────────────────────
def print_summary(rows: list[dict], year: int):
    total       = len(rows)
    matched     = sum(1 for r in rows if r['match_status'] == 'matched')
    fuzzy       = sum(1 for r in rows if r['match_status'] == 'fuzzy_matched')
    unmatched   = sum(1 for r in rows if r['match_status'] == 'unmatched')
    questions   = len(set(r['qid'] for r in rows))
    no_ref_qs   = 200 - questions  # assumes 200-question exam; adjust if needed

    print(f"\n{'='*55}")
    print(f"  {year} ITE Critique — Extraction Summary")
    print(f"{'='*55}")
    print(f"  Questions with refs  : {questions}")
    print(f"  Questions without refs: {no_ref_qs}  (no References section)")
    print(f"  Total QRP rows       : {total}")
    print(f"  {'─'*40}")
    print(f"  Exact matched        : {matched}  ({matched/total*100:.1f}%)")
    print(f"  Fuzzy matched        : {fuzzy}   ({fuzzy/total*100:.1f}%)")
    print(f"  Unmatched            : {unmatched}   ({unmatched/total*100:.1f}%)")
    print(f"  Match rate           : {(matched+fuzzy)/total*100:.1f}%")
    print(f"{'='*55}\n")

    if unmatched > 0:
        print(f"  Unmatched citations ({unmatched}):")
        for r in rows:
            if r['match_status'] == 'unmatched':
                print(f"    [{r['qid']}] score={r['match_score']:.3f}  {r['ref_raw'][:100]}")
        print()


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Extract question-reference pairs from ITE critique PDFs."
    )
    parser.add_argument('--pdf',      required=True, type=Path,
                        help="Path to the ITE critique PDF")
    parser.add_argument('--year',     required=True, type=int,
                        help="Exam year (e.g. 2025)")
    parser.add_argument('--dry-run',  action='store_true',
                        help="Print summary only; do not write any files")
    parser.add_argument('--commit',   action='store_true',
                        help="Insert into DB after writing staging file")
    parser.add_argument('--threshold', type=float, default=FUZZY_THRESHOLD,
                        help=f"Fuzzy match threshold (default: {FUZZY_THRESHOLD})")
    args = parser.parse_args()

    if not args.pdf.exists():
        print(f"ERROR: PDF not found: {args.pdf}")
        return

    print(f"\nParsing {args.pdf.name} (year={args.year})...")
    records = dispatch(args.pdf, args.year)
    print(f"  {len(records)} citation records extracted from PDF")

    print(f"Loading article refs from DB ({DB_PATH.name})...")
    article_refs = load_article_refs(DB_PATH)
    print(f"  {len(article_refs)} articles loaded")

    print("Matching citations...")
    rows = build_qrp_rows(records, article_refs)

    print_summary(rows, args.year)

    if args.dry_run:
        print("DRY RUN — no files written.")
        return

    staging_path = write_staging(rows, args.year)
    print(f"Staging file written: {staging_path}")

    if args.commit:
        print(f"\nCOMMIT mode — writing to DB ({DB_PATH.name})...")
        existing = sqlite3.connect(DB_PATH)
        cur = existing.cursor()
        cur.execute("SELECT COUNT(*) FROM question_ref_pairs WHERE exam_year=?", (args.year,))
        existing_count = cur.fetchone()[0]
        existing.close()

        if existing_count > 0:
            print(f"  WARNING: {existing_count} existing QRP rows for {args.year} will be DELETED.")
            confirm = input("  Type 'yes' to confirm: ").strip().lower()
            if confirm != 'yes':
                print("  Aborted. Staging file preserved.")
                return

        commit_to_db(rows, DB_PATH, args.year)
        print("Done.")
    else:
        print("Review the staging file, then re-run with --commit to insert into DB.")


if __name__ == '__main__':
    main()
