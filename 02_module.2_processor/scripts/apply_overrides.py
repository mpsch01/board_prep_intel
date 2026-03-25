import sys, csv, json, os
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

# ── PATHS ───────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent

OVERRIDES_PATH = SCRIPT_DIR / "crosswalk_overrides.json"
CROSSWALK_PATH = PROJECT_ROOT / "archive_canonical" / "04_reference_data" / "linked_refs_crosswalk_v2.csv"
OUTPUT_PATH    = PROJECT_ROOT / "archive_canonical" / "04_reference_data" / "linked_refs_crosswalk_final.csv"

with open(OVERRIDES_PATH, encoding='utf-8') as f:
    overrides = json.load(f)

# null_overrides use fragment/substring matching (same logic as build_crosswalk_v2.py)
null_fragments = [e['citation'] for e in overrides.get('null_overrides', []) if 'citation' in e]
manual_pins    = overrides.get('manual_pins', [])

def is_nulled(cit):
    return any(frag.lower() in cit.lower() for frag in null_fragments)

def get_pin(cit):
    for pin in manual_pins:
        frag = pin.get('citation_fragment', '')
        if frag and frag.lower() in cit.lower():
            return pin
    return None

with open(CROSSWALK_PATH, encoding='utf-8') as f:
    reader = csv.DictReader(f)
    fieldnames = list(reader.fieldnames)
    rows = list(reader)

applied_pins  = []
applied_nulls = []

for row in rows:
    cit = row.get('citation', '')

    # Null overrides take priority
    if is_nulled(cit) and row.get('match_status') == 'MATCHED':
        row['match_status']       = 'NO_MATCH'
        row['match_quality']      = 'NULLED'
        row['match_score']        = '0'
        row['matched_json_title'] = ''
        row['matched_json_file']  = ''
        row['matched_json_path']  = ''
        row['matched_label']      = ''
        applied_nulls.append(cit[:80])

    # Manual pins — apply to NO_MATCH rows where a pin exists
    elif row.get('match_status') == 'NO_MATCH':
        pin = get_pin(cit)
        if pin and pin.get('json_file'):
            row['match_status']       = 'MATCHED'
            row['match_quality']      = 'manual_pin'
            row['match_score']        = '99'
            row['matched_json_title'] = pin.get('json_title', '')
            row['matched_json_file']  = pin.get('json_file', '')
            row['matched_json_path']  = pin.get('json_path', '')
            row['matched_label']      = 'manual_pin'
            applied_pins.append(cit[:80])

with open(OUTPUT_PATH, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f'apply_overrides complete.')
print(f'  Pins applied:  {len(applied_pins)}')
for p in applied_pins: print(f'    + {p}')
print(f'  Nulls applied: {len(applied_nulls)}')
for n in applied_nulls: print(f'    x {n}')
print()

matched   = [r for r in rows if r.get('match_status') == 'MATCHED']
no_match  = [r for r in rows if r.get('match_status') == 'NO_MATCH']
must_read = [r for r in rows if r.get('tier') == 'Must-Read']
mr_matched = [r for r in must_read if r.get('match_status') == 'MATCHED']

print(f'--- FINAL CROSSWALK SUMMARY ---')
print(f'Total citations : {len(rows)}')
print(f'Matched         : {len(matched)}')
print(f'No match        : {len(no_match)}')
print(f'Must-Read       : {len(mr_matched)}/{len(must_read)}')
print(f'Output          : {OUTPUT_PATH}')
