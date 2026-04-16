"""
apply_holdout_body_system_corrections.py
Apply confirmed body_system corrections for the 22 deprecated-label holdouts in 2024-2025.
Updates both body_system and body_system_merged.

Confirmed by Mikey 2026-04-15.
"""
import sqlite3
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"

CORRECTIONS = [
    # QID,                         body_system,              body_system_merged
    # --- Foundations of Care → Nonspecific ---
    ("QID-2024-0059", "Nonspecific",            "Nonspecific"),            # minor consent/legal
    ("QID-2024-0117", "Nonspecific",            "Nonspecific"),            # capacity/AMA
    ("QID-2024-0137", "Nonspecific",            "Nonspecific"),            # Medicaid/health policy
    ("QID-2024-0173", "Nonspecific",            "Nonspecific"),            # person-first language
    ("QID-2025-0020", "Nonspecific",            "Nonspecific"),            # autonomy/ethics (blood refusal)
    ("QID-2025-0118", "Nonspecific",            "Nonspecific"),            # cognitive bias/anchoring
    ("QID-2025-0161", "Nonspecific",            "Nonspecific"),            # counseling technique (Foundations, not Endocrine)
    ("QID-2025-0196", "Nonspecific",            "Nonspecific"),            # capacity/DPOA/ethics
    # --- Foundations of Care → Population-Based Care (population-level QI) ---
    ("QID-2025-0001", "Population-Based Care",  "Population-Based Care"),  # cervical cancer screening QI
    # --- Foundations of Care → Neurologic ---
    ("QID-2025-0179", "Neurologic",             "Neurologic"),             # SDOH protective against Alzheimer's
    # --- Preventive Care → Population-Based Care ---
    ("QID-2024-0083", "Population-Based Care",  "Population-Based Care"),  # fall prevention (tai chi)
    ("QID-2025-0034", "Population-Based Care",  "Population-Based Care"),  # shingles vaccine scheduling
    ("QID-2025-0143", "Population-Based Care",  "Population-Based Care"),  # smoking cessation counseling
    # --- Preventive Care → Neurologic ---
    ("QID-2024-0182", "Neurologic",             "Neurologic"),             # Alzheimer's risk/BP control
    # --- Preventive Care → Psychiatric/Behavioral ---
    ("QID-2025-0175", "Psychiatric/Behavioral", "Psychiatric/Behavioral"), # alcohol SBIRT
    # --- Preventive Care → Nonspecific ---
    ("QID-2025-0124", "Nonspecific",            "Nonspecific"),            # neonatal assessment (newborn visit)
    # --- Chronic Care Management → Nonspecific ---
    ("QID-2024-0172", "Nonspecific",            "Nonspecific"),            # hospice/palliative (Glycopyrrolate)
    # --- Chronic Care Management → Integumentary ---
    ("QID-2025-0066", "Integumentary",          "Integumentary"),          # melasma
    # --- Chronic Care Management → Sexual and Reproductive ---
    ("QID-2025-0037", "Sexual and Reproductive","Sexual and Reproductive"), # chronic prostatitis
    # --- Acute Care and Diagnosis → Nephrologic ---
    ("QID-2024-0012", "Nephrologic",            "Nephrologic"),            # urge urinary incontinence/Mirabegron
    # --- Emergent and Urgent Care → Psychiatric/Behavioral ---
    ("QID-2024-0127", "Psychiatric/Behavioral", "Psychiatric/Behavioral"), # post-op delirium/Risperidone
    # --- Acute Care and Diagnosis → Sexual and Reproductive ---
    ("QID-2025-0119", "Sexual and Reproductive","Sexual and Reproductive"), # heavy menstrual bleeding
]

def main():
    db = sqlite3.connect(DB_PATH)
    cursor = db.cursor()

    print(f"Applying {len(CORRECTIONS)} body_system corrections...\n")

    for qid, new_bs, new_bsm in CORRECTIONS:
        # Get current values
        row = cursor.execute(
            "SELECT body_system, body_system_merged FROM questions WHERE qid = ?", (qid,)
        ).fetchone()
        if not row:
            print(f"  WARNING: {qid} not found in DB — skipping")
            continue
        old_bs, old_bsm = row
        cursor.execute(
            "UPDATE questions SET body_system = ?, body_system_merged = ? WHERE qid = ?",
            (new_bs, new_bsm, qid)
        )
        print(f"  {qid}: [{old_bs}] → [{new_bs}]")

    db.commit()
    print(f"\nCommitted {len(CORRECTIONS)} updates.")

    # Verification: confirm no deprecated labels remain in 2024-2025
    deprecated = ['Patient-Based Systems', 'Psychogenic', 'Reproductive: Female', 'Reproductive: Male']
    placeholders = ','.join('?' for _ in deprecated)
    remaining = db.execute(f'''
        SELECT COUNT(*) FROM questions
        WHERE exam_year >= 2024
        AND body_system IN ({placeholders})
    ''', deprecated).fetchone()[0]

    if remaining == 0:
        print("\n✓ Verification passed — zero deprecated labels in 2024-2025.")
    else:
        print(f"\n⚠ WARNING: {remaining} deprecated labels still present in 2024-2025.")

    db.close()

if __name__ == "__main__":
    main()
