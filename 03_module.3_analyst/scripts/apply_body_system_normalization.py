"""
apply_body_system_normalization.py
===================================
Three-part normalization pass for residual body_system inconsistencies:

  1. Musculoskeletal → Injuries/Musculoskeletal
     - 2022 and 2023 questions used the shortened label (48 records)
     - All other years correctly use "Injuries/Musculoskeletal"
     - Fix applies to both body_system AND body_system_merged

  2. QID-2021-0168 manual fix
     - Aspiration pneumonia question; should be Respiratory
     - Fix applies to both body_system AND body_system_merged

  3. DEFERRED-BODY-SYSTEM-MERGED-UPDATE — sync body_system_merged forward
     - For all records where body_system is canonical (not deprecated),
       set body_system_merged = body_system
     - Leaves intact records where body_system IS a deprecated label —
       those have body_system_merged = canonical forward-mapped value (correct)
     - Also fixes "Hematologic/ Immune" spacing variant in body_system_merged

Run: py 03_module.3_analyst/scripts/apply_body_system_normalization.py
"""

from pathlib import Path
import sqlite3

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"

# ─── Deprecated labels — body_system_merged stays as-is for these ────────────
# These are pre-2024 legacy labels intentionally preserved in body_system.
# body_system_merged for these records already holds the canonical forward value.
DEPRECATED_BODY_SYSTEMS = {
    "Musculoskeletal",           # → Injuries/Musculoskeletal (in body_system_merged)
    "Patient-Based Systems",     # → Population-Based Care / Nonspecific
    "Psychogenic",               # → Psychiatric/Behavioral
    "Reproductive: Female",      # → Sexual and Reproductive
    "Reproductive: Male",        # → Sexual and Reproductive
}

# ─── Fix 1: Musculoskeletal rename ────────────────────────────────────────────
MUSCULO_OLD = "Musculoskeletal"
MUSCULO_NEW = "Injuries/Musculoskeletal"

# ─── Fix 2: QID-2021-0168 manual correction ──────────────────────────────────
MANUAL_FIXES = [
    ("QID-2021-0168", "Respiratory", "Respiratory"),
]


def run():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # ── Pre-flight ────────────────────────────────────────────────────────────
    cur.execute("SELECT COUNT(*) FROM questions WHERE body_system = ?", (MUSCULO_OLD,))
    musculo_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM questions WHERE body_system != body_system_merged", )
    mismatch_total = cur.fetchone()[0]

    print("Pre-flight:")
    print(f"  body_system = '{MUSCULO_OLD}': {musculo_count} records")
    print(f"  body_system != body_system_merged: {mismatch_total} records")
    for qid, bs, bsm in MANUAL_FIXES:
        cur.execute("SELECT body_system, body_system_merged FROM questions WHERE qid = ?", (qid,))
        row = cur.fetchone()
        print(f"  {qid}: body_system='{row[0]}', body_system_merged='{row[1]}'")

    # ── Fix 1: Musculoskeletal rename ─────────────────────────────────────────
    print(f"\nFix 1: '{MUSCULO_OLD}' → '{MUSCULO_NEW}' in body_system + body_system_merged")
    cur.execute("""
        UPDATE questions
        SET body_system        = ?,
            body_system_merged = ?
        WHERE body_system = ?
    """, (MUSCULO_NEW, MUSCULO_NEW, MUSCULO_OLD))
    print(f"  Updated {cur.rowcount} records")

    # ── Fix 2: Manual corrections ──────────────────────────────────────────────
    print(f"\nFix 2: manual corrections")
    for qid, bs, bsm in MANUAL_FIXES:
        cur.execute("""
            UPDATE questions
            SET body_system        = ?,
                body_system_merged = ?
            WHERE qid = ?
        """, (bs, bsm, qid))
        print(f"  {qid}: → body_system='{bs}', body_system_merged='{bsm}' ({cur.rowcount} row)")

    # ── Fix 3: DEFERRED-BODY-SYSTEM-MERGED-UPDATE ────────────────────────────
    # For canonical body_system records, set body_system_merged = body_system.
    # Skip deprecated labels — their body_system_merged is intentionally the
    # forward-mapped canonical value.
    print(f"\nFix 3: sync body_system_merged → body_system for canonical records")
    deprecated_placeholders = ",".join("?" * len(DEPRECATED_BODY_SYSTEMS))
    cur.execute(f"""
        UPDATE questions
        SET body_system_merged = body_system
        WHERE body_system NOT IN ({deprecated_placeholders})
          AND body_system != body_system_merged
    """, list(DEPRECATED_BODY_SYSTEMS))
    print(f"  Updated {cur.rowcount} records")

    conn.commit()

    # ── Verification ───────────────────────────────────────────────────────────
    print(f"\nVerification:")

    cur.execute("SELECT COUNT(*) FROM questions WHERE body_system = ?", (MUSCULO_OLD,))
    remaining = cur.fetchone()[0]
    print(f"  '{MUSCULO_OLD}' in body_system: {remaining}  {'✅' if remaining == 0 else '❌ STILL PRESENT'}")

    cur.execute("SELECT COUNT(*) FROM questions WHERE body_system = ?", (MUSCULO_NEW,))
    new_count = cur.fetchone()[0]
    print(f"  '{MUSCULO_NEW}' total: {new_count}")

    for qid, bs, _ in MANUAL_FIXES:
        cur.execute("SELECT body_system, body_system_merged FROM questions WHERE qid = ?", (qid,))
        row = cur.fetchone()
        ok = "✅" if row[0] == bs else "❌"
        print(f"  {qid}: body_system='{row[0]}' {ok}")

    # Remaining mismatches should ONLY be deprecated-body_system records
    cur.execute("""
        SELECT body_system, body_system_merged, COUNT(*)
        FROM questions
        WHERE body_system != body_system_merged
        GROUP BY body_system, body_system_merged
        ORDER BY 3 DESC
    """)
    remaining_mismatches = cur.fetchall()
    print(f"\n  Remaining body_system != body_system_merged ({len(remaining_mismatches)} groups):")
    all_deprecated = True
    for bs, bsm, cnt in remaining_mismatches:
        deprecated_flag = "✅ intentional" if bs in DEPRECATED_BODY_SYSTEMS else "❌ UNEXPECTED"
        if bs not in DEPRECATED_BODY_SYSTEMS:
            all_deprecated = False
        print(f"    {bs!r} → {bsm!r}: {cnt}  [{deprecated_flag}]")
    if all_deprecated and remaining_mismatches:
        print(f"\n  ✅ All remaining mismatches are intentional deprecated-label forward-mappings")
    elif not remaining_mismatches:
        print(f"  ✅ No remaining mismatches")

    conn.close()
    print(f"\nDone.")


if __name__ == "__main__":
    run()
