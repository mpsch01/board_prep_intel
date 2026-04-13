#!/usr/bin/env python3
"""
test_v3_changes.py — Targeted validation of the 5 changes made to ite_analyzer_v3.py

Tests:
  1. _normalize_concept() — synonym map works for known variants
  2. concept_clustering() — ITE-only QIDs, normalization, threshold 4+
  3. _concept_selection() — returns both ITE + AAFP candidates
  4. match_practice_questions_v3() — concept-targeted questions present in pool
  5. Full analyze_v3() smoke test — no runtime errors end-to-end

Usage:
    cd 03_module.3_analyst/scripts
    python test_v3_changes.py
"""

import json
import sys
from pathlib import Path

SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH      = str(PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db")
REF_PATH     = str(SCRIPT_DIR / "abfm_reference_2025.json")

sys.path.insert(0, str(SCRIPT_DIR))
from ite_analyzer_v3 import (
    _normalize_concept, CONCEPT_SYNONYMS,
    concept_clustering, _concept_selection,
    match_practice_questions_v3, analyze_v3,
    BLUEPRINT_DB_TO_PDF, BODYSYSTEM_PDF_NORM,
)
import sqlite3

# ─── ANSI helpers ─────────────────────────────────────────────────────────────
PASS  = "\033[92m✓\033[0m"
FAIL  = "\033[91m✗\033[0m"
INFO  = "\033[94m·\033[0m"
WARN  = "\033[93m⚠\033[0m"

def ok(msg):  print(f"  {PASS} {msg}")
def fail(msg):print(f"  {FAIL} {msg}"); FAILURES.append(msg)
def info(msg):print(f"  {INFO} {msg}")
def warn(msg):print(f"  {WARN} {msg}")

FAILURES = []

# ─── TEST 1: _normalize_concept() ─────────────────────────────────────────────
print("\n━━━ TEST 1 — _normalize_concept() synonym map ━━━")

cases = [
    ("T2DM",                               "Type 2 Diabetes Mellitus"),
    ("type 2 diabetes",                    "Type 2 Diabetes Mellitus"),
    ("Type 2 Diabetes Mellitus",           "Type 2 Diabetes Mellitus"),
    ("dm type 2",                          "Type 2 Diabetes Mellitus"),
    ("HTN",                                "Hypertension"),
    ("hypertension",                       "Hypertension"),
    ("AAFP Board Review",                  "AAFP"),
    ("aafp family medicine board review",  "AAFP"),
    ("AHA/ACC",                            "ACC/AHA"),
    ("aha/acc 2019",                       "ACC/AHA 2019"),
    ("CHF",                                "Heart Failure"),
    ("congestive heart failure",           "Heart Failure"),
    ("COPD",                               "COPD"),
    ("chronic obstructive pulmonary disease", "COPD"),
    ("CKD",                                "Chronic Kidney Disease"),
    ("Some Unknown Term XYZ",              "Some Unknown Term XYZ"),   # passthrough
]

for inp, expected in cases:
    result = _normalize_concept(inp)
    if result == expected:
        ok(f'"{inp}" → "{result}"')
    else:
        fail(f'"{inp}" → got "{result}", expected "{expected}"')

# ─── BUILD SYNTHETIC PARSED_DATA FROM REAL DB QUESTIONS ─────────────────────
# The score_analysis.json files are analysis OUTPUTS (what analyze_v3 returns).
# The raw parsed_data input has "items" with item# + correct + blueprint + body_system.
# We synthesize it here from real 2024 ITE questions to get authentic concept_tags.
print("\n━━━ Building synthetic parsed_data from real 2024 ITE questions ━━━")

_db_build = sqlite3.connect(DB_PATH)
_db_build.row_factory = sqlite3.Row
# Pull 150 questions from 2024 with concept_tags, both blueprint + body_system populated
_rows = _db_build.execute("""
    SELECT qid, blueprint, body_system, body_system_merged, exam_year
    FROM questions
    WHERE exam_year = 2024
      AND blueprint IS NOT NULL AND blueprint != ''
      AND body_system IS NOT NULL AND body_system != ''
      AND concept_tags IS NOT NULL AND concept_tags != ''
    LIMIT 150
""").fetchall()
_db_build.close()

if not _rows:
    print("  WARN: No 2024 questions with concept_tags found — falling back to any year")
    _db_build = sqlite3.connect(DB_PATH)
    _db_build.row_factory = sqlite3.Row
    _rows = _db_build.execute("""
        SELECT qid, blueprint, body_system, body_system_merged, exam_year
        FROM questions
        WHERE blueprint IS NOT NULL AND blueprint != ''
          AND body_system IS NOT NULL AND body_system != ''
          AND concept_tags IS NOT NULL AND concept_tags != ''
        ORDER BY exam_year DESC LIMIT 150
    """).fetchall()
    _db_build.close()

import random; random.seed(42)
exam_year = 2025  # resident sat 2025 exam; test data is 2024 questions

# Build items list: 150 questions, ~45 marked incorrect (30% miss rate)
items = []
for idx, row in enumerate(_rows):
    # Convert DB blueprint label to PDF label for analyzer input
    pdf_bp = BLUEPRINT_DB_TO_PDF.get(row["blueprint"], row["blueprint"])
    # body_system from DB is already in PDF/canonical form
    correct = random.random() > 0.30  # ~30% incorrect
    items.append({
        "item":        idx + 1,
        "correct":     correct,
        "blueprint":   pdf_bp,
        "body_system": row["body_system"],
        "score":       random.randint(200, 800) if not correct else random.randint(400, 900),
        "_qid":        row["qid"],   # stash for debugging — not used by analyzer
    })

parsed_data = {
    "resident":          {"name": "Test Resident, M.D.", "abfm_id": "TEST-001", "program": "Test Program"},
    "exam_year":         exam_year,
    "items":             items,
    "deleted_items":     [],
    "body_systems_found": list({i["body_system"] for i in items}),
}

missed = [i for i in items if not i.get("correct")]
info(f"Synthetic items: {len(items)}  |  Missed: {len(missed)} ({round(len(missed)/len(items)*100)}%)  |  Exam year: {exam_year}")

# Build qid_map (replicating build_qid_map logic)
from ite_analyzer_v3 import build_qid_map, _normalize_body_system
for item in items:
    if item.get("body_system"):
        item["body_system"] = _normalize_body_system(item["body_system"])
qid_map = build_qid_map(items, exam_year)
info(f"QID map: {len(qid_map)} items resolved")

# ─── TEST 2: concept_clustering() ─────────────────────────────────────────────
print("\n━━━ TEST 2 — concept_clustering() ━━━")

concepts = concept_clustering(items, qid_map, DB_PATH)

top_dx    = concepts.get("top_diagnoses", {})
top_drugs = concepts.get("top_drugs", {})
top_guide = concepts.get("top_guidelines", {})
qid_map_c = concepts.get("concept_qid_map", {})
recurring = concepts.get("recurring_diagnoses", {})

info(f"Top diagnoses: {len(top_dx)}  →  {list(top_dx.items())[:5]}")
info(f"Top drugs:     {len(top_drugs)}  →  {list(top_drugs.items())[:5]}")
info(f"Top guidelines:{len(top_guide)}  →  {list(top_guide.items())[:5]}")
info(f"Recurring dx (≥4):  {len(recurring)} entries")
info(f"items_matched={concepts.get('items_matched')}  aafp_matched={concepts.get('aafp_items_matched')}")

# Check 1: normalization — no T2DM / HTN raw variants in output
bad_variants = ["T2DM", "t2dm", "type 2 diabetes", "HTN", "htn",
                "AAFP Board Review", "AHA/ACC", "CHF", "congestive heart failure"]
found_bad = [k for k in list(top_dx) + list(top_guide) if k in bad_variants]
if found_bad:
    fail(f"Normalization incomplete — raw variants still in output: {found_bad}")
else:
    ok("Normalization clean — no raw variant keys in top_diagnoses/top_guidelines")

# Check 2: QID maps contain only ITE QIDs (format QID-YYYY-NNNN)
all_qids_in_map = []
for category in qid_map_c.values():
    for qlist in category.values():
        all_qids_in_map.extend(qlist)

if all_qids_in_map:
    aafp_leaked = [q for q in all_qids_in_map if q.startswith("AAFP-")]
    ite_qids    = [q for q in all_qids_in_map if q.startswith("QID-")]
    if aafp_leaked:
        fail(f"AAFP QIDs leaked into concept_qid_map: {aafp_leaked[:5]}")
    else:
        ok(f"concept_qid_map contains only ITE QIDs ({len(ite_qids)} entries, 0 AAFP leaked)")
    # Check cap at 10
    over_cap = [(k, len(v)) for k, v in qid_map_c.get("diagnoses", {}).items() if len(v) > 10]
    if over_cap:
        fail(f"QID cap exceeded (>10): {over_cap[:3]}")
    else:
        ok("QID cap ≤10 per concept enforced")
else:
    warn("concept_qid_map is empty — no missed ITE QIDs resolved (check concept_tags population)")

# Check 3: recurring threshold ≥4
if recurring:
    below_4 = {k: v for k, v in recurring.items() if v < 4}
    if below_4:
        fail(f"Recurring threshold <4 entries found: {list(below_4.items())[:3]}")
    else:
        ok(f"Recurring threshold ≥4 enforced ({len(recurring)} entries)")
else:
    ok("Recurring diagnoses empty (threshold ≥4 — may be correct for this resident)")

# ─── TEST 3: _concept_selection() ─────────────────────────────────────────────
print("\n━━━ TEST 3 — _concept_selection() ━━━")

db = sqlite3.connect(DB_PATH)
db.row_factory = sqlite3.Row

concept_pool = {**dict(list(top_dx.items())[:5]), **dict(list(top_drugs.items())[:3])}
info(f"Concept pool for selection: {list(concept_pool.keys())}")

cs_candidates = _concept_selection(db, concept_pool, set())
db.close()

ite_cs  = [c for c in cs_candidates if c["source_bank"] == "ITE"]
aafp_cs = [c for c in cs_candidates if c["source_bank"] == "AAFP"]

info(f"Concept candidates: {len(cs_candidates)} total  |  ITE: {len(ite_cs)}  AAFP: {len(aafp_cs)}")

if len(cs_candidates) == 0:
    fail("_concept_selection() returned 0 candidates — normalization mismatch likely")
else:
    ok(f"_concept_selection() returned {len(cs_candidates)} candidates")

if len(ite_cs) > 0:
    ok(f"ITE questions present in concept selection ({len(ite_cs)})")
else:
    fail("No ITE questions in concept selection pool")

if len(aafp_cs) > 0:
    ok(f"AAFP questions present in concept selection ({len(aafp_cs)})")
else:
    warn("No AAFP questions in concept selection (may be normalization miss)")

# Verify targeting labels start with "Concept: "
bad_targeting = [c["targeting"] for c in cs_candidates if not c["targeting"].startswith("Concept: ")]
if bad_targeting:
    fail(f"Unexpected targeting labels: {bad_targeting[:3]}")
else:
    ok('All concept candidates have "Concept: ..." targeting labels')

# Sample top 3
for c in cs_candidates[:3]:
    info(f"  [{c['source_bank']}] {c['qid']} | targeting='{c['targeting']}' | score={c['relevance_score']}")

# ─── TEST 4: match_practice_questions_v3() with concepts ─────────────────────
print("\n━━━ TEST 4 — match_practice_questions_v3() concept wiring ━━━")

from ite_analyzer_v3 import load_abfm_reference, basic_performance, yield_weighted_priorities
ref  = load_abfm_reference(REF_PATH)
perf = basic_performance(items)
priorities = yield_weighted_priorities(perf, ref)

pqs = match_practice_questions_v3(perf, priorities, qid_map, items, DB_PATH,
                                   target_count=20, current_exam_year=exam_year,
                                   concepts=concepts)

concept_qs  = [q for q in pqs if (q.get("targeting") or "").startswith("Concept: ")]
ite_pqs     = [q for q in pqs if q.get("source_bank") == "ITE"]
aafp_pqs    = [q for q in pqs if q.get("source_bank") == "AAFP"]

info(f"Practice questions: {len(pqs)} total  |  ITE: {len(ite_pqs)}  AAFP: {len(aafp_pqs)}")
info(f"Concept-targeted:  {len(concept_qs)} questions")

if len(concept_qs) > 0:
    ok(f"Concept fingerprint → practice questions wired ({len(concept_qs)} concept-targeted Qs)")
    for q in concept_qs[:3]:
        info(f"  [{q['source_bank']}] {q['qid']} | '{q['targeting']}' | score={q['relevance_score']}")
else:
    fail("No concept-targeted questions in practice set — wiring failed")

if len(ite_pqs) > 0:
    ok(f"ITE questions present in practice set ({len(ite_pqs)})")
else:
    fail("No ITE questions in practice set")

if len(aafp_pqs) > 0:
    ok(f"AAFP questions present in practice set ({len(aafp_pqs)})")
else:
    warn("No AAFP questions in practice set")

# Check for year exclusion (current year questions should be excluded)
excl_year_in_set = [q for q in pqs if q.get("source_bank") == "ITE" and q.get("exam_year") == int(exam_year)]
if excl_year_in_set:
    fail(f"Current exam year ({exam_year}) ITE questions NOT excluded: {[q['qid'] for q in excl_year_in_set[:3]]}")
else:
    ok(f"Current exam year ({exam_year}) ITE questions correctly excluded")

# ─── TEST 5: Full analyze_v3() smoke test ─────────────────────────────────────
print("\n━━━ TEST 5 — Full analyze_v3() end-to-end smoke test ━━━")

try:
    result = analyze_v3(parsed_data, DB_PATH, REF_PATH)
    ok("analyze_v3() completed without exceptions")

    # Spot-check output keys
    required_keys = ["resident", "exam_year", "performance", "concept_clustering",
                     "practice_questions", "yield_priorities", "icd10_weakness_map",
                     "pathway_gap_map"]
    missing = [k for k in required_keys if k not in result]
    if missing:
        fail(f"Missing keys in analyze_v3() output: {missing}")
    else:
        ok(f"All {len(required_keys)} required output keys present")

    # Concept fingerprint cross-check
    out_concepts = result.get("concept_clustering", {})
    out_pqs      = result.get("practice_questions", [])
    out_concept_qs = [q for q in out_pqs if (q.get("targeting") or "").startswith("Concept: ")]

    info(f"analyze_v3 → top diagnoses: {list(out_concepts.get('top_diagnoses', {}).keys())[:5]}")
    info(f"analyze_v3 → practice Qs: {len(out_pqs)} total, {len(out_concept_qs)} concept-targeted")

    if out_concept_qs:
        ok("End-to-end: concept fingerprint → practice questions confirmed in full pipeline")
    else:
        warn("No concept-targeted questions in full pipeline output (may be concept_pool too small)")

except Exception as e:
    import traceback
    fail(f"analyze_v3() raised exception: {e}")
    traceback.print_exc()

# ─── SUMMARY ──────────────────────────────────────────────────────────────────
print("\n" + "━" * 60)
if FAILURES:
    print(f"\033[91m  FAILED — {len(FAILURES)} issue(s):\033[0m")
    for f in FAILURES:
        print(f"    • {f}")
else:
    print(f"\033[92m  ALL TESTS PASSED\033[0m")
print("━" * 60)
