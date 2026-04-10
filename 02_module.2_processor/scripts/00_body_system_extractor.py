#!/usr/bin/env python3
"""
00_body_system_extractor.py

Extracts question->body-system category mappings from ABFM ITE
Item Performance Report PDFs using bounding-box (x-coordinate) analysis.

Processes:
  - 2022_body-system.pdf  (2 pages, 15 official categories, ~195 questions)
  - 2023_body-system.pdf  (2 pages, 15 official categories, ~198 questions)
  - 2024_body-system.pdf  (1 page,  5 collapsed categories, ~193 questions)

Output: _archive_/04_reference_data/body_system_labels_2022_2024.csv
  Columns: Year, QuestionNum, BodySystem

Migrated from TEMP_06_ite_pipeline_TEMP (BATON 007)
"""

import re
import pdfplumber
import pandas as pd
from pathlib import Path

SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
REF_DATA     = PROJECT_ROOT / "_archive_" / "04_reference_data"

# -- Category lists ------------------------------------------------------------

# 2022 / 2023 – Page 1 (left->right order)
P1_CATS = [
    'Respiratory', 'Cardiovascular', 'Musculoskeletal', 'Gastrointestinal',
    'Special Sensory', 'Endocrine', 'Integumentary', 'Neurologic',
]

# 2022 / 2023 – Page 2 (left->right order)
P2_CATS = [
    'Reproductive:Female', 'Reproductive:Male', 'Hematologic/Immune',
    'Psychiatric/Behavioral', 'Nephrologic', 'Population-Based Care', 'Patient-Based Systems',
]

# 2024 – Page 1 only (5 collapsed categories)
P_2024_CATS = [
    'Cardiovascular', 'Injuries/Musculoskeletal', 'Respiratory',
    'Psychiatric/Behavioral', 'Sexual and Reproductive',
]

# Map 2024 collapsed -> official 15-category ABFM taxonomy
REMAP_2024 = {
    'Cardiovascular':           'Cardiovascular',
    'Injuries/Musculoskeletal': 'Musculoskeletal',
    'Respiratory':              'Respiratory',
    'Psychiatric/Behavioral':   'Psychiatric/Behavioral',
    'Sexual and Reproductive':  'Reproductive:Female',
}

# -- Anchor tokens (first distinctive word / prefix for each category) ---------
ANCHOR = {
    'Respiratory':           'respiratory',
    'Cardiovascular':        'cardiovascular',
    'Musculoskeletal':       'musculoskeletal',
    'Gastrointestinal':      'gastrointestinal',
    'Special Sensory':       'sensory',
    'Endocrine':             'endocrine',
    'Integumentary':         'integumentary',
    'Neurologic':            'neurologic',
    'Reproductive:Female':   'female',
    'Reproductive:Male':     'male',
    'Hematologic/Immune':    'hematologic',
    'Psychiatric/Behavioral': 'psychiatric',  # canonical anchor (was 'Psychogenic')
    'Nephrologic':           'nephrologic',
    'Population-Based Care': 'population',
    'Patient-Based Systems': 'patient',
    'Injuries/Musculoskeletal': 'injuries',
    'Psychiatric/Behavioral':   'psychiatric',
    'Sexual and Reproductive':  'sexual',
}

ANCHOR_FALLBACK = {
    'Special Sensory':       ['special'],
    'Hematologic/Immune':    ['immune'],
    'Population-Based Care': ['population-based'],
    'Patient-Based Systems': ['patient-based'],
    'Reproductive:Female':   ['reproductive'],
    'Reproductive:Male':     ['reproductive'],
}

DELETED = {
    2022: {63, 97, 138, 157, 166},
    2023: {67, 129},
    2024: {6, 64, 163, 167, 191},
}


# -- Helper functions ----------------------------------------------------------

def is_question_num(text: str) -> bool:
    m = re.fullmatch(r'0*([1-9]\d{0,2})', text.strip())
    if m:
        return 1 <= int(m.group(1)) <= 200
    return False


def parse_q(text: str) -> int:
    return int(re.sub(r'^0+', '', text.strip()) or '0')


def word_x_center(w) -> float:
    return (w['x0'] + w['x1']) / 2


def detect_headers(words, expected_cats):
    if not words:
        return {}

    max_y = max(w['bottom'] for w in words)
    threshold_y = max_y * 0.40
    header_words = [w for w in words if w['top'] <= threshold_y]

    token_hits: dict[str, list] = {}
    for w in header_words:
        t = w['text'].strip().lower()
        token_hits.setdefault(t, []).append(w)
    for t in token_hits:
        token_hits[t].sort(key=lambda w: w['x0'])

    headers = {}

    for cat in expected_cats:
        primary = ANCHOR.get(cat, cat.split()[0]).lower()
        fallbacks = ANCHOR_FALLBACK.get(cat, [])
        candidate_words = []

        for anchor in [primary] + fallbacks:
            if anchor in token_hits:
                candidate_words = token_hits[anchor]
                break
            for t, ws in token_hits.items():
                if t.startswith(anchor[:6]):
                    candidate_words = ws
                    break
            if candidate_words:
                break

        if not candidate_words:
            continue

        already_used_xs = {v for k, v in headers.items()
                           if ANCHOR.get(k) == primary}
        available = [w for w in candidate_words
                     if word_x_center(w) not in already_used_xs]
        if not available:
            available = candidate_words

        chosen = min(available, key=lambda w: w['x0'])
        headers[cat] = word_x_center(chosen)

    return headers


def assign_questions(words, col_positions, header_y_threshold):
    results = []
    for w in words:
        if w['top'] <= header_y_threshold:
            continue
        if is_question_num(w['text']):
            q_num = parse_q(w['text'])
            x_mid = word_x_center(w)
            nearest_cat = min(col_positions.items(),
                              key=lambda kv: abs(kv[1] - x_mid))[0]
            results.append((q_num, nearest_cat))
    return results


# -- Core processing -----------------------------------------------------------

def process_pdf(pdf_path: Path, year: int, page_cat_lists: list) -> list:
    print(f"\n{'-'*60}")
    print(f"Processing {year}  >  {pdf_path.name}")

    deleted = DELETED.get(year, set())
    all_results = []

    with pdfplumber.open(str(pdf_path)) as pdf:
        n_pages = len(pdf.pages)
        print(f"  PDF pages: {n_pages}  |  Expected page configs: {len(page_cat_lists)}")

        for pg_idx, expected_cats in enumerate(page_cat_lists):
            if pg_idx >= n_pages:
                print(f"  WARNING: Page {pg_idx+1} expected but PDF only has {n_pages} -- skipping")
                continue

            page  = pdf.pages[pg_idx]
            words = page.extract_words()
            print(f"\n  Page {pg_idx+1}: {len(words)} words extracted")

            if not words:
                print("  WARNING: No words found on this page -- skipping")
                continue

            max_y            = max(w['bottom'] for w in words)
            header_threshold = max_y * 0.40

            col_positions = detect_headers(words, expected_cats)

            print(f"  Column headers detected ({len(col_positions)}/{len(expected_cats)}):")
            for cat in expected_cats:
                x = col_positions.get(cat)
                mark = f"x={x:6.1f}" if x is not None else "  NOT FOUND  <<<"
                print(f"    {mark}  {cat}")

            if not col_positions:
                print("  ERROR: No headers detected -- skipping page")
                continue

            page_results = assign_questions(words, col_positions, header_threshold)
            print(f"  Question assignments found: {len(page_results)}")
            all_results.extend(page_results)

    seen: set[int] = set()
    rows = []
    for q_num, cat in all_results:
        if q_num in deleted:
            continue
        if q_num not in seen:
            seen.add(q_num)
            rows.append((year, q_num, cat))

    print(f"\n  OK  {len(rows)} unique questions  |  {len(deleted)} deleted skipped")
    return rows


# -- Main ----------------------------------------------------------------------

def main():
    configs = [
        (REF_DATA / "2022_body-system.pdf", 2022, [P1_CATS, P2_CATS]),
        (REF_DATA / "2023_body-system.pdf", 2023, [P1_CATS, P2_CATS]),
        (REF_DATA / "2024_body-system.pdf", 2024, [P_2024_CATS]),
    ]

    all_rows = []
    for pdf_path, year, pages_cats in configs:
        if not pdf_path.exists():
            print(f"WARNING:  PDF not found: {pdf_path} -- skipping")
            continue
        rows = process_pdf(pdf_path, year, pages_cats)
        if year == 2024:
            rows = [(y, q, REMAP_2024.get(c, c)) for y, q, c in rows]
        all_rows.extend(rows)

    df = pd.DataFrame(all_rows, columns=["Year", "QuestionNum", "BodySystem"])

    print(f"\n{'='*60}")
    print("VALIDATION SUMMARY")
    print('='*60)

    for year in [2022, 2023, 2024]:
        yr_df    = df[df["Year"] == year]
        n_unique = yr_df["QuestionNum"].nunique()
        n_cats   = yr_df["BodySystem"].nunique()
        expected = 200 - len(DELETED.get(year, set()))

        print(f"\n{year}: {n_unique} questions across {n_cats} categories")

        dups = yr_df[yr_df.duplicated("QuestionNum", keep=False)]
        if len(dups):
            print(f"  WARNING:  DUPLICATES ({len(dups)} rows):")
            print(dups.sort_values("QuestionNum").to_string(index=False))
        else:
            print(f"  OK  No duplicate question numbers")

        coverage_ok = abs(n_unique - expected) <= 5
        mark = "OK" if coverage_ok else "WARNING:"
        print(f"  {mark}  Coverage: {n_unique}/{expected} questions (+-5 tolerance)")

        print(f"  Category distribution:")
        for cat, cnt in yr_df["BodySystem"].value_counts().items():
            print(f"    {cnt:3d}  {cat}")

    for year in [2022, 2023]:
        yr_df   = df[df["Year"] == year]
        found   = set(yr_df["QuestionNum"].tolist())
        deleted = DELETED.get(year, set())
        missing = set(range(1, 201)) - found - deleted
        if missing:
            print(f"\n  WARNING:  {year} questions NOT found (not deleted): {sorted(missing)}")
        else:
            print(f"\n  OK  {year}: all non-deleted questions accounted for")

    out_path = REF_DATA / "body_system_labels_2022_2024.csv"
    df.to_csv(out_path, index=False)
    print(f"\nOK  Saved {len(df)} rows -> {out_path}")


if __name__ == "__main__":
    main()
