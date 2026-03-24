"""
Pass-2 Fixes on ITE_Reference_Tiers_Clean.csv
Actions:
  1. Drop the single fragment stub '2009;34(7):697-700.'
  2. Reclassify AFP articles sitting in 'Other Journal'
  3. Reclassify guidelines sitting in 'Other Journal'
  4. Undo false textbook merges (restore individual page-range rows from master)
  5. Normalize USPSTF citation format (Format B -> Format A where possible)
  6. Re-apply tier logic after any count changes
  7. Save final clean file + produce change log
"""
import pandas as pd, re
from difflib import SequenceMatcher

clean = pd.read_csv(r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\ite_refs\02_working\ITE_Reference_Tiers_Clean.csv')
master = pd.read_csv(r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\ite_exam\03_database\ABFM_ITE_6_Year_Master.csv', low_memory=False)
change_log = []

print(f"Starting rows: {len(clean)}")

# ── FIX 1: Drop bare fragment stub ───────────────────────────────────────────
frag_mask = clean['CleanRef'].str.strip() == '2009;34(7):697-700.'
print(f"\n[Fix 1] Dropping {frag_mask.sum()} fragment stub(s)")
clean = clean[~frag_mask].reset_index(drop=True)
change_log.append(('Dropped fragment stub', '2009;34(7):697-700.', '', ''))

# ── FIX 2: AFP articles mislabeled as 'Other Journal' ────────────────────────
afp_mask = (clean['SourceType'] == 'Other Journal') & \
           (clean['CleanRef'].str.lower().str.contains('am fam physician', na=False))
print(f"\n[Fix 2] Reclassifying {afp_mask.sum()} AFP articles from 'Other Journal' -> 'AFP'")
for idx in clean[afp_mask].index:
    change_log.append(('SourceType AFP fix', clean.at[idx,'CleanRef'][:80], 'Other Journal', 'AFP'))
clean.loc[afp_mask, 'SourceType'] = 'AFP'

# ── FIX 3: Guidelines mislabeled as 'Other Journal' ──────────────────────────
guideline_kws = r'guideline|recommendation|task force|statement|consensus|uspstf|acip|cdc |mmwr|advisory committee'
other_j = clean['SourceType'] == 'Other Journal'
gl_mask = other_j & clean['CleanRef'].str.lower().str.contains(guideline_kws, regex=True, na=False)
# Exclude the Yawn/Kim COPD article - it's a journal review, not a guideline itself
not_yawn = ~clean['CleanRef'].str.contains('Yawn B, Kim V', na=False)
gl_mask = gl_mask & not_yawn
print(f"\n[Fix 3] Reclassifying {gl_mask.sum()} guidelines from 'Other Journal' -> 'Guideline/Org'")
for idx in clean[gl_mask].index:
    change_log.append(('SourceType Guideline fix', clean.at[idx,'CleanRef'][:80], 'Other Journal', 'Guideline/Org'))
clean.loc[gl_mask, 'SourceType'] = 'Guideline/Org'

# ── FIX 4: Undo false textbook merges ────────────────────────────────────────
# Textbooks cited for different page ranges are DIFFERENT references (different topics).
# The dedup merged them based on leading-string similarity. We need to:
#   a) remove the merged row
#   b) restore all original individual textbook rows from the master CSV

def extract_refs(explanation):
    if pd.isna(explanation): return []
    match = re.search(r'Ref:\s*(.+)', explanation, re.DOTALL)
    if not match: return []
    block = match.group(1).strip()
    parts = re.split(r'\s+\d+\)\s+', block)
    return [p.strip() for p in parts if p.strip()]

def normalize(s):
    return re.sub(r'[\s\.\:;,]+', ' ', s.lower()).strip()

master['ParsedRefs'] = master['Explanation'].apply(extract_refs)

# Get all original refs from master
all_orig_refs = []
for _, row in master.iterrows():
    for ref in row['ParsedRefs']:
        all_orig_refs.append(ref.strip())

orig_series = pd.Series(all_orig_refs)
orig_counts = orig_series.value_counts()

textbook_kws_list = [
    "harrison's principles", "goldman-cecil", "nelson textbook",
    "braunwald's heart disease", "habif's clinical dermatology", "habif tp: clinical dermatology",
    "fracture management for primary care", "rosen's emergency medicine",
    "sabiston textbook", "diagnostic and statistical manual", "dinulos jgh"
]

tb_mask = clean['CleanRef'].str.lower().str.contains('|'.join(textbook_kws_list), na=False)
tb_multi = clean[tb_mask & (clean['CitationCount'] > 1)]

print(f"\n[Fix 4] Undoing {len(tb_multi)} falsely merged textbook rows")
rows_to_restore = []
drop_indices = []

def assign_tier(count, years, src):
    if count >= 3 and years >= 3: return 'Must-Read'
    if count >= 2 and years >= 2 and src == 'Guideline/Org': return 'Must-Read'
    if count >= 2: return 'Core'
    if count == 1 and src in ('Guideline/Org','NEJM','JAMA','Annals','Lancet','Circulation'): return 'Core'
    return 'Supplementary'

for idx, merged_row in tb_multi.iterrows():
    merged_norm = normalize(merged_row['CleanRef'][:80])
    # find all original refs from master that fuzzy-match this textbook
    matches = []
    for orig_ref in orig_series.unique():
        orig_norm = normalize(orig_ref[:80])
        sim = SequenceMatcher(None, merged_norm, orig_norm).ratio()
        if sim >= 0.88:
            matches.append(orig_ref)
    
    if len(matches) <= 1:
        # Only 1 match — might be a legitimate multi-cite; leave it
        print(f"  Skipping (only 1 original match): {merged_row['CleanRef'][:80]}")
        continue
    
    print(f"  Restoring {len(matches)} rows for: {merged_row['CleanRef'][:80]}")
    drop_indices.append(idx)
    
    for orig in matches:
        cnt = orig_counts.get(orig, 1)
        # try to find year range
        yr_matches = re.findall(r'20\d\d|19\d\d', orig)
        yrs = len(set(yr_matches)) if yr_matches else 1
        src = merged_row['SourceType']
        tier = assign_tier(cnt, yrs, src)
        rows_to_restore.append({
            'CleanRef': orig,
            'CitationCount': cnt,
            'UniqueYears': yrs,
            'SourceType': src,
            'Categories': merged_row['Categories'],
            'BlueprintCategories': merged_row['BlueprintCategories'],
            'Tier': tier
        })
        change_log.append(('TextbookRestored', orig[:80], 'merged', f'{cnt}x|{tier}'))

if drop_indices:
    clean = clean.drop(index=drop_indices).reset_index(drop=True)
    restore_df = pd.DataFrame(rows_to_restore)
    clean = pd.concat([clean, restore_df], ignore_index=True)

print(f"  Rows after textbook restore: {len(clean)}")

# ── FIX 5: Normalize USPSTF Format B -> consistent style ─────────────────────
# Format B: "US Preventive Services Task Force. Final recommendation statement: topic..."
# Normalize to Format A: "Final Recommendation Statement: Topic. US Preventive Services Task Force, YEAR."
# Only do this for the simple "US PSTF. Final recommendation statement: X. Updated DATE." pattern

def normalize_uspstf(ref):
    pat = re.match(
        r'US Preventive Services Task Force\.\s*Final recommendation statement:\s*(.+?)\.\s*Updated\s+(.+?)[\.\s]*$',
        ref.strip(), re.IGNORECASE
    )
    if pat:
        topic = pat.group(1).strip()
        date_str = pat.group(2).strip().rstrip('.')
        yr_match = re.search(r'(\d{4})', date_str)
        yr = yr_match.group(1) if yr_match else date_str
        # Title-case the topic
        topic_tc = topic.title()
        return f"Final Recommendation Statement: {topic_tc}. US Preventive Services Task Force, {yr}."
    return ref  # leave unchanged if pattern doesn't match

uspstf_fmt_b = (
    clean['CleanRef'].str.contains(r'^US Preventive Services Task Force\.\s*Final recommendation', regex=True, na=False)
)
n_normalized = uspstf_fmt_b.sum()
print(f"\n[Fix 5] Normalizing {n_normalized} USPSTF Format-B refs")
for idx in clean[uspstf_fmt_b].index:
    orig = clean.at[idx, 'CleanRef']
    fixed = normalize_uspstf(orig)
    if fixed != orig:
        change_log.append(('USPSTF format normalized', orig[:80], '', fixed[:80]))
        clean.at[idx, 'CleanRef'] = fixed

# ── RE-APPLY TIER LOGIC ───────────────────────────────────────────────────────
clean['Tier'] = clean.apply(
    lambda r: assign_tier(r['CitationCount'], r['UniqueYears'], r['SourceType']), axis=1
)

# ── FINAL STATS ───────────────────────────────────────────────────────────────
print(f"\n=== FINAL STATS ===")
print(f"Total rows: {len(clean)}")
print(f"Tier breakdown:")
print(clean['Tier'].value_counts().to_string())
print(f"\nSource type breakdown:")
print(clean['SourceType'].value_counts().to_string())

# ── SAVE ──────────────────────────────────────────────────────────────────────
out = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\ite_refs\03_database\ITE_Reference_Tiers_Final.csv'
clean.to_csv(out, index=False)
print(f"\nSaved: {out}")

cl_df = pd.DataFrame(change_log, columns=['Action','Reference','OldValue','NewValue'])
cl_path = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\ite_exam\02_working\hygiene_change_log.csv'
cl_df.to_csv(cl_path, index=False)
print(f"Change log ({len(cl_df)} entries): {cl_path}")
