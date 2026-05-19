"""
add_missing_articles.py
========================
Adds genuinely new articles to the articles table and links them to their QIDs.

Source: references read directly from 2024/2025 ITE critique PDFs that had
no matching article in the DB.

Strategy:
  1. Normalize punctuation (colon vs period after authors) before lookup.
  2. If article already exists (different format) → link to existing ART-ID.
  3. If genuinely missing → INSERT with next available ART-ID.
  4. INSERT into qid_art_xref for every resolved article.

Run from: 03_module.3_analyst/scripts/
"""

import sqlite3, re, sys
from pathlib import Path
from difflib import SequenceMatcher

SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH      = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"
OUT_PATH     = PROJECT_ROOT / "03_module.3_analyst" / "outputs" / "article_qc" / "add_missing_articles.sql"


# ── Full citations from PDFs (corrected/complete) ─────────────────────────────
# Format: (qid, exam_year) → list of full citation strings
MISSING_REFS = {
    ("QID-2024-0199", 2024): [
        "Bhavsar AK, Gelner EJ, Shorma T. Common questions about the evaluation of acute pelvic pain. Am Fam Physician. 2016;93(1):41-48.",
        "Morley EJ, Bracey A, Reiter M, Thode HC Jr, Singer AJ. Association of pain location with computed tomography abnormalities in emergency department patients with abdominal pain. Am J Emerg Med. 2011;29(9):1069-1074.",
    ],
    ("QID-2024-0200", 2024): [
        "Bauer CA. Tinnitus. N Engl J Med. 2018;378(13):1224-1231.",
    ],
    ("QID-2025-0041", 2025): [
        "Centre for Evidence-Based Medicine. Number needed to treat (NNT). University of Oxford, Nuffield Department of Primary Care Health Sciences. Accessed 2025.",
    ],
    ("QID-2025-0181", 2025): [
        "Final recommendation statement: genital herpes infection: serologic screening. US Preventive Services Task Force. Updated February 14, 2023.",
    ],
    ("QID-2025-0183", 2025): [
        "Shang X, Guo K, E F, et al. Pharmacological interventions on smoking cessation: a systematic review and network meta-analysis. Front Pharmacol. 2022;13:1012433.",
        "Gaddey HL, Dakkak M, Jackson NM. Smoking cessation interventions. Am Fam Physician. 2022;106(5):513-522.",
    ],
    ("QID-2025-0185", 2025): [
        "Miller NE, Rushlow D, Stacey SK. Diagnosis and management of sodium disorders: hyponatremia and hypernatremia. Am Fam Physician. 2023;108(5):476-486.",
        "Seay NW, Lehrich RW, Greenberg A. Diagnosis and management of disorders of body tonicity–hyponatremia and hypernatremia: core curriculum 2020. Am J Kidney Dis. 2020;75(2):272-286.",
    ],
    ("QID-2025-0186", 2025): [
        "Dvorin EL, Ebell MH. Short-term systemic corticosteroids: appropriate use in primary care. Am Fam Physician. 2020;101(2):89-94.",
        "El Melhat AM, Youssef ASA, Zebdawi MR, Hafez MA, Khalil LH, Harrison DE. Non-surgical approaches to the management of lumbar disc herniation associated with radiculopathy: a narrative review. J Clin Med. 2024;13(4):974.",
    ],
    ("QID-2025-0187", 2025): [
        "Holt HK, Gildengorin G, Karliner L, Fontil V, Pramanik R, Potter MB. Differences in hypertension medication prescribing for Black Americans and their association with hypertension outcomes. J Am Board Fam Med. 2022;35(1):26-34.",
        "Egan BM, Yang J, Rakotz MK, et al. Self-reported antihypertensive medication adherence and office blood pressure in the Hypertension Recognition and Treatment study. Hypertension. 2018;72(4):e51-e56.",
    ],
    ("QID-2025-0188", 2025): [
        "Klein DA, Sylvester JE, Schvey NA. Eating disorders in primary care: diagnosis and management. Am Fam Physician. 2021;103(1):22-32.",
    ],
    ("QID-2025-0189", 2025): [
        "Wilkins T, McMechan D, Talukder A, Herline A. Colorectal cancer screening and surveillance in individuals at increased risk. Am Fam Physician. 2018;97(2):111-116.",
        "Final recommendation statement: colorectal cancer: screening. US Preventive Services Task Force. May 18, 2021.",
    ],
    ("QID-2025-0190", 2025): [
        "Meng WB, Li X, Li YM, Zhou WC, Zhu XL. Three initial diets for management of mild acute pancreatitis: a meta-analysis. World J Gastroenterol. 2011;17(37):4235-4241.",
    ],
    ("QID-2025-0191", 2025): [
        "Final recommendation statement: osteoporosis to prevent fractures: screening. US Preventive Services Task Force. January 14, 2025.",
    ],
    ("QID-2025-0192", 2025): [
        "Kim MJ, Valerio C, Knobloch GK. Potassium disorders: hypokalemia and hyperkalemia. Am Fam Physician. 2023;107(1):59-70.",
        "Durfey N, Lehnhof B, Bergeson A, et al. Severe hyperkalemia: can the electrocardiogram risk stratify for short-term adverse events? West J Emerg Med. 2017;18(5):963-971.",
    ],
    ("QID-2025-0193", 2025): [
        "Quinn B, Halepas S. Fractured and avulsed teeth. In: Niekrash CE, Ferneini EM, Goupil MT, eds. Dental Science for the Medical Professional. Springer, 2023:329-335.",
        "Stephens MB, Wiedemer JP, Kushner GM. Dental problems in primary care. Am Fam Physician. 2018;98(11):654-660.",
    ],
    ("QID-2025-0194", 2025): [
        "Ross DS, Burch HB, Cooper DS, et al. 2016 American Thyroid Association guidelines for diagnosis and management of hyperthyroidism and other causes of thyrotoxicosis. Thyroid. 2016;26(10):1343-1421.",
        "Kravets I. Hyperthyroidism: diagnosis and treatment. Am Fam Physician. 2016;93(5):363-370.",
    ],
    ("QID-2025-0195", 2025): [
        "Jaqua EE, Nguyen VTN, Chin E. Delirium in older persons: prevention, evaluation, and management. Am Fam Physician. 2023;108(3):278-287.",
        "Jones HT, Davis DH. What you need to know about: delirium in older adults in hospital. Br J Hosp Med (Lond). 2021;82(12):1-10.",
    ],
    ("QID-2025-0196", 2025): [
        "Barstow C, Shahan B, Roberts M. Evaluating medical decision-making capacity in practice. Am Fam Physician. 2018;98(1):40-46.",
    ],
    ("QID-2025-0197", 2025): [
        "Pyzocha N. Accidental hypothermia: guidelines from the Wilderness Medical Society. Am Fam Physician. 2020;102(9):571-572.",
        "Dow J, Giesbrecht GG, Danzl DF, et al. Wilderness Medical Society clinical practice guidelines for the out-of-hospital evaluation and treatment of accidental hypothermia: 2019 update. Wilderness Environ Med. 2019;30(4S):S47-S69.",
    ],
    ("QID-2025-0198", 2025): [
        "Stevermer JJ, Fink KS. Counseling patients about prostate cancer screening. Am Fam Physician. 2018;98(8):478-483.",
        "Wei JT, Barocas D, Carlsson S, et al. Early detection of prostate cancer: AUA/SUO guideline amendment 2023. J Urol. 2023;210(4):765-778.",
    ],
    ("QID-2025-0199", 2025): [
        "Meisenheimer ES, Epstein C, Thiel D. Acute diarrhea in adults. Am Fam Physician. 2022;106(1):72-80.",
    ],
    ("QID-2025-0200", 2025): [
        "Ellis R, Ellis C. Dog and cat bites. Am Fam Physician. 2014;90(4):239-243.",
        "Ortiz DD, Lezcano FO. Dog and cat bites: rapid evidence review. Am Fam Physician. 2023;108(5):501-505.",
    ],
}


def normalize(s: str) -> str:
    """Normalize punctuation for comparison: colon→period after author block."""
    s = s.strip().lower()
    s = re.sub(r':\s+', '. ', s)   # colon → period
    s = re.sub(r'\s+', ' ', s)
    return s


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize(a)[:100], normalize(b)[:100]).ratio()


def parse_citation(ref: str) -> dict:
    """Extract author1, year, title, source_type from a citation string."""
    # Author: everything before first ". " or ": "
    author_match = re.match(r'^([^\.]+?)[\.:]', ref)
    author1 = author_match.group(1).split(',')[0].strip() if author_match else ""

    # Year: first 4-digit year
    year_match = re.search(r'\b(19|20)\d{2}\b', ref)
    year = year_match.group(0) if year_match else ""

    # Title: second segment after authors (before journal)
    segs = re.split(r'\.\s+', ref)
    title = segs[1].strip() if len(segs) > 1 else ref[:80]

    # Source type
    source_type = "Other Journal"
    if re.search(r'Am Fam Physician', ref, re.I):
        source_type = "AFP"
    elif re.search(r'N Engl J Med', ref, re.I):
        source_type = "NEJM"
    elif re.search(r'\bJAMA\b', ref, re.I):
        source_type = "JAMA"
    elif re.search(r'Ann Intern Med', ref, re.I):
        source_type = "Annals"
    elif re.search(r'Lancet', ref, re.I):
        source_type = "Lancet"
    elif re.search(r'BMJ', ref, re.I):
        source_type = "BMJ"
    elif re.search(r'Pediatrics', ref, re.I):
        source_type = "Pediatrics"
    elif re.search(r'Circulation', ref, re.I):
        source_type = "Circulation"
    elif re.search(r'Cochrane', ref, re.I):
        source_type = "Cochrane"
    elif re.search(r'Chest', ref, re.I):
        source_type = "Chest"
    elif re.search(r'Preventive Services Task Force|USPSTF|CDC|NIH|Springer|Oxford|Foundation', ref, re.I):
        source_type = "Guideline/Org"

    return {"author1": author1, "year": year, "title": title, "source_type": source_type}


def esc(v):
    return str(v).replace("'", "''") if v else ""


def main():
    if not DB_PATH.exists():
        print(f"ERROR: DB not found at {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    # Load all existing articles for lookup
    all_articles = conn.execute(
        "SELECT article_id, clean_ref, tier, author1, year FROM articles"
    ).fetchall()
    all_articles = [dict(r) for r in all_articles]

    # Get next available ART-ID
    max_id = conn.execute(
        "SELECT MAX(CAST(SUBSTR(article_id, 5) AS INTEGER)) FROM articles WHERE article_id LIKE 'ART-%'"
    ).fetchone()[0] or 1986
    next_id = max_id + 1

    conn.close()
    print(f"Loaded {len(all_articles)} articles | Next ART-ID: ART-{next_id}")

    lines = [
        "-- add_missing_articles.sql",
        "-- Adds new articles for citations in 2024-2025 ITE critiques not in DB.",
        "-- Also inserts qid_art_xref links for all resolved articles.",
        "-- REVIEW BEFORE RUNNING.",
        "",
        "BEGIN TRANSACTION;",
        "",
        "-- ═══════════════════════════════════════════════════════",
        "-- SECTION 1: New articles",
        "-- ═══════════════════════════════════════════════════════",
        "",
    ]

    # Track newly assigned ART-IDs
    ref_to_art_id = {}
    new_articles = 0
    existing_found = 0

    all_refs = []
    for (qid, year), refs in MISSING_REFS.items():
        for ref in refs:
            if ref not in [r for r, _ in all_refs]:
                all_refs.append((ref, (qid, year)))

    processed_refs = set()

    for (qid, year), refs in sorted(MISSING_REFS.items()):
        for ref in refs:
            if ref in processed_refs:
                continue
            processed_refs.add(ref)

            # Check if already in DB (fuzzy match with normalization)
            best_score, best_art = 0.0, None
            for art in all_articles:
                s = similarity(ref, art["clean_ref"] or "")
                if s > best_score:
                    best_score, best_art = s, art

            if best_score >= 0.88 and best_art:
                # Already exists with different formatting
                ref_to_art_id[ref] = best_art["article_id"]
                lines += [
                    f"-- EXISTING [{best_art['article_id']} score={best_score:.2f}]: {ref[:70]}",
                    f"-- Matched to: {(best_art['clean_ref'] or '')[:70]}",
                    "",
                ]
                existing_found += 1
            else:
                # Genuinely new
                art_id = f"ART-{next_id}"
                next_id += 1
                ref_to_art_id[ref] = art_id
                parsed = parse_citation(ref)

                lines += [
                    f"-- NEW {art_id}: {ref[:70]}",
                    f"INSERT INTO articles (article_id, clean_ref, citation_display, title, author1, year, source_type, tier, citation_count, unique_years, auto_assigned) VALUES (",
                    f"  '{art_id}',",
                    f"  '{esc(ref)}',",
                    f"  '{esc(ref)}',",
                    f"  '{esc(parsed['title'][:200])}',",
                    f"  '{esc(parsed['author1'])}',",
                    f"  '{esc(parsed['year'])}',",
                    f"  '{esc(parsed['source_type'])}',",
                    f"  'VC_fail',",
                    f"  0, 0, 'Y'",
                    f");",
                    "",
                ]
                new_articles += 1

    lines += [
        "",
        "-- ═══════════════════════════════════════════════════════",
        "-- SECTION 2: qid_art_xref links",
        "-- ═══════════════════════════════════════════════════════",
        "",
    ]

    for (qid, year), refs in sorted(MISSING_REFS.items()):
        lines.append(f"-- {qid}")
        lines.append(f"DELETE FROM qid_art_xref WHERE qid = '{qid}' AND exam_year = {year};")
        for idx, ref in enumerate(refs, 1):
            art_id = ref_to_art_id.get(ref)
            if art_id:
                lines += [
                    f"-- ref {idx}: {ref[:60]}",
                    f"INSERT OR IGNORE INTO qid_art_xref (qid, article_id, tier, exam_year, author1, year) "
                    f"VALUES ('{qid}', '{art_id}', 'VC_fail', {year}, '', '');",
                ]
        lines.append("")

    lines += [
        "COMMIT;",
        "",
        f"-- Summary: {new_articles} new articles inserted | {existing_found} matched to existing",
    ]

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text('\n'.join(lines), encoding='utf-8')
    print(f"Written: {OUT_PATH}")
    print(f"New articles: {new_articles} | Matched existing: {existing_found}")
    print(f"Next ART-ID after this run: ART-{next_id}")


if __name__ == "__main__":
    main()
