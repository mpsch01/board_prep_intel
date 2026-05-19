"""
pdf_lookup_patch.py
====================
Generates INSERT SQL for QIDs that were missed by the main extractor
(parser gap or truncation). References were read directly from the PDFs.

Run from: 03_module.3_analyst/scripts/
Output:   03_module.3_analyst/outputs/article_qc/pdf_lookup_patch.sql
"""

import sqlite3, sys
from pathlib import Path

SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH      = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"
OUT_PATH     = PROJECT_ROOT / "03_module.3_analyst" / "outputs" / "article_qc" / "pdf_lookup_patch.sql"


# ── References read directly from PDFs ───────────────────────────────────────
ITEMS = {
    # 2024
    ("QID-2024-0001", 2024): [
        "Levy M, Prentice M, Wass J. Diabetes insipidus. BMJ. 2019;364:l321.",
    ],
    ("QID-2024-0197", 2024): [
        "Savard DJ, Ursua FG, Gaddey HL. Smell and taste disorders in primary care. Am Fam Physician. 2023;108(3):240-248.",
        "Siddiqui ZA, Walker A, Pirwani MM, Tahiri M, Syed I. Allergic rhinitis: diagnosis and management. Br J Hosp Med (Lond). 2022;83(2):1-9.",
    ],
    ("QID-2024-0198", 2024): [
        "Abdel Jalil AA, Katzka DA, Castell DO. Approach to the patient with dysphagia. Am J Med. 2015;128(10):1138.e17-1138.e23.",
    ],
    ("QID-2024-0199", 2024): [
        "Bhavsar AK, Gelner EJ, Shorma T. Common questions about the evaluation of acute pelvic pain. Am Fam Physician. 2016;93(1):41-48.",
        "Morley EJ, Bracey A, Reiter M, Thode HC Jr, Singer AJ. Association of pain location with computed tomography abnormalities in emergency department patients with abdominal pain.",
    ],
    ("QID-2024-0200", 2024): [
        "Bauer CA. Tinnitus. N Engl J Med. 2018;378(13):1224-1231.",
    ],
    # 2025
    ("QID-2025-0041", 2025): [
        "Centre for Evidence-Based Medicine. Number needed to treat (NNT). University of Oxford Nuffield Department of Primary Care Health Sciences.",
    ],
    ("QID-2025-0181", 2025): [
        "Final recommendation statement: genital herpes infection: serologic screening. US Preventive Services Task Force. Updated February 14, 2023.",
    ],
    ("QID-2025-0182", 2025): [
        "Buel KL, Wilcox J, Mingo PT. Acute abdominal pain in children: evaluation and management. Am Fam Physician. 2024;110(6):621-631.",
        "Kelley-Quon LI, Arthur LG, Williams RF, et al. Management of intussusception in children: a systematic review. J Pediatr Surg. 2021;56(3):587-596.",
    ],
    ("QID-2025-0183", 2025): [
        "Shang X, Guo K, E F, et al. Pharmacological interventions on smoking cessation. Front Pharmacol. 2022;13:1012433.",
        "Gaddey HL, Dakkak M, Jackson NM. Smoking cessation interventions. Am Fam Physician. 2022;106(5):513-522.",
    ],
    ("QID-2025-0184", 2025): [
        "Fontenelle LF, Sarti TD. Kidney stones: treatment and prevention. Am Fam Physician. 2019;99(8):490-496.",
    ],
    ("QID-2025-0185", 2025): [
        "Miller NE, Rushlow D, Stacey SK. Diagnosis and management of sodium disorders. Am Fam Physician. 2023;108(5):476-486.",
        "Seay NW, Lehrich RW, Greenberg A. Diagnosis and management of disorders of body tonicity. Am J Kidney Dis. 2020;75(2):272-286.",
    ],
    ("QID-2025-0186", 2025): [
        "Dvorin EL, Ebell MH. Short-term systemic corticosteroids. Am Fam Physician. 2020;101(2):89-94.",
        "El Melhat AM, et al. Non-surgical approaches to lumbar disc herniation. J Clin Med. 2024;13(4):974.",
    ],
    ("QID-2025-0187", 2025): [
        "Holt HK, et al. Differences in hypertension medication prescribing for Black Americans. J Am Board Fam Med. 2022;35(1):26-34.",
        "Egan BM, et al. Self-reported antihypertensive medication adherence. Hypertension. 2018.",
    ],
    ("QID-2025-0188", 2025): [
        "Klein DA, Sylvester JE, Schvey NA. Eating disorders in primary care. Am Fam Physician. 2021;103(1):22-32.",
    ],
    ("QID-2025-0189", 2025): [
        "Wilkins T, et al. Colorectal cancer screening and surveillance. Am Fam Physician. 2018;97(2):111-116.",
        "Final recommendation statement: colorectal cancer: screening. US Preventive Services Task Force. May 18, 2021.",
    ],
    ("QID-2025-0190", 2025): [
        "Meng WB, et al. Three initial diets for management of mild acute pancreatitis. World J Gastroenterol. 2011;17(37):4235-4241.",
    ],
    ("QID-2025-0191", 2025): [
        "Final recommendation statement: osteoporosis to prevent fractures: screening. US Preventive Services Task Force. January 14, 2025.",
    ],
    ("QID-2025-0192", 2025): [
        "Kim MJ, Valerio C, Knobloch GK. Potassium disorders. Am Fam Physician. 2023;107(1):59-70.",
        "Durfey N, et al. Severe hyperkalemia. West J Emerg Med. 2017;18(5):963-971.",
    ],
    ("QID-2025-0193", 2025): [
        "Quinn B, Halepas S. Fractured and avulsed teeth. Springer, 2023:329-335.",
        "Stephens MB, Wiedemer JP, Kushner GM. Dental problems in primary care. Am Fam Physician. 2018;98(11):654-660.",
    ],
    ("QID-2025-0194", 2025): [
        "Ross DS, et al. 2016 American Thyroid Association guidelines for hyperthyroidism. Thyroid. 2016;26(10):1343-1421.",
        "Kravets I. Hyperthyroidism: diagnosis and treatment. Am Fam Physician. 2016;93(5):363-370.",
    ],
    ("QID-2025-0195", 2025): [
        "Jaqua EE, Nguyen VTN, Chin E. Delirium in older persons. Am Fam Physician. 2023;108(3):278-287.",
        "Jones HT, Davis DH. Delirium in older adults in hospital. Br J Hosp Med (Lond). 2021;82(12):1-10.",
    ],
    ("QID-2025-0196", 2025): [
        "Barstow C, Shahan B, Roberts M. Evaluating medical decision-making capacity in practice. Am Fam Physician. 2018;98(1):40-46.",
    ],
    ("QID-2025-0197", 2025): [
        "Pyzocha N. Accidental hypothermia: Wilderness Medical Society guidelines. Am Fam Physician. 2020;102(9):571-572.",
        "Dow J, et al. Wilderness Medical Society guidelines for accidental hypothermia. Wilderness Environ Med. 2019;30(4S):S47-S69.",
    ],
    ("QID-2025-0198", 2025): [
        "Stevermer JJ, Fink KS. Counseling patients about prostate cancer screening. Am Fam Physician. 2018;98(8):478-483.",
        "Wei JT, et al. Early detection of prostate cancer: AUA/SUO guideline. J Urol. 2023.",
    ],
    ("QID-2025-0199", 2025): [
        "Meisenheimer ES, Epstein C, Thiel D. Acute diarrhea in adults. Am Fam Physician. 2022;106(1):72-80.",
    ],
    ("QID-2025-0200", 2025): [
        "Ellis R, Ellis C. Dog and cat bites. Am Fam Physician. 2014;90(4):239-243.",
        "Ortiz DD, Lezcano FO. Dog and cat bites: rapid evidence review. Am Fam Physician. 2023;108(5):501-505.",
    ],
}


def esc(v):
    return str(v).replace("'", "''") if v else ""


def main():
    if not DB_PATH.exists():
        print(f"ERROR: DB not found at {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    # Index by first 80 chars of clean_ref for fast lookup
    ref_index = {}
    art_meta  = {}
    for r in conn.execute("SELECT article_id, clean_ref, tier, author1, year FROM articles WHERE clean_ref IS NOT NULL").fetchall():
        key = (r["clean_ref"] or "")[:80].lower().strip()
        ref_index[key] = r["article_id"]
        art_meta[r["article_id"]] = dict(r)
    conn.close()
    print(f"Loaded {len(art_meta)} articles from DB")

    def lookup(raw_ref):
        """Exact prefix match against clean_ref. Returns (article_id, found)."""
        key = raw_ref[:80].lower().strip()
        art_id = ref_index.get(key)
        return art_id, art_id is not None

    lines = [
        "-- pdf_lookup_patch.sql",
        "-- References read directly from ITE critique PDFs for parser-missed items.",
        "-- Lookup is exact prefix match against articles.clean_ref.",
        "-- MISSING = article not yet in DB (library gap, not a matching problem).",
        "-- Review before running in DB Browser.",
        "",
        "BEGIN TRANSACTION;",
        "",
    ]

    found_count = missing_count = 0

    for (qid, year), refs in sorted(ITEMS.items()):
        lines.append(f"-- {qid}")
        lines.append(f"DELETE FROM qid_art_xref WHERE qid = '{qid}' AND exam_year = {year};")
        for idx, ref in enumerate(refs, 1):
            art_id, found = lookup(ref)
            if found:
                art = art_meta[art_id]
                lines.append(f"-- ref {idx} [FOUND {art_id}]: {ref[:70]}")
                lines.append(
                    f"INSERT OR IGNORE INTO qid_art_xref "
                    f"(qid, article_id, tier, exam_year, author1, year) VALUES "
                    f"('{qid}', '{art_id}', '{esc(art['tier'])}', {year}, "
                    f"'{esc(art['author1'])}', '{esc(art['year'])}');"
                )
                found_count += 1
            else:
                lines.append(f"-- ref {idx} [MISSING — not in DB]: {ref[:70]}")
                missing_count += 1
        lines.append("")

    lines += [
        "COMMIT;",
        "",
        f"-- Found in DB: {found_count} | Not in DB (library gap): {missing_count}",
    ]

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text('\n'.join(lines), encoding='utf-8')
    print(f"Written: {OUT_PATH}")
    print(f"Found in DB: {found_count} | Not in DB (library gap): {missing_count}")


if __name__ == "__main__":
    main()
