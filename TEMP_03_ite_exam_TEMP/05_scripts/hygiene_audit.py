import re, pandas as pd
from difflib import SequenceMatcher
from collections import defaultdict

tiers = pd.read_csv(r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\ite_refs\07_archive\ITE_Reference_Tiers.csv')
print(f"Starting rows: {len(tiers)}")

refs_list = tiers['CleanRef'].tolist()
n = len(refs_list)

# ── UNION-FIND for fuzzy duplicate clustering ─────────────────────────────────
parent = list(range(n))

def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x

def union(a, b):
    a, b = find(a), find(b)
    if a != b:
        parent[b] = a

print("Running fuzzy match (this takes ~60s)...")
for i in range(n):
    for j in range(i+1, n):
        s = SequenceMatcher(None, refs_list[i].lower()[:130], refs_list[j].lower()[:130]).ratio()
        if s >= 0.90:
            union(i, j)

clusters = defaultdict(list)
for i in range(n):
    clusters[find(i)].append(i)

dup_clusters = {k: v for k, v in clusters.items() if len(v) > 1}
print(f"\nDuplicate clusters: {len(dup_clusters)}")
print(f"Extra rows to remove: {sum(len(v)-1 for v in dup_clusters.values())}")

# Show all clusters
for root, members in sorted(dup_clusters.items(), key=lambda x: -len(x[1])):
    rows = tiers.iloc[members]
    print(f"\n--- Cluster (n={len(members)}) ---")
    for _, r in rows.iterrows():
        print(f"  [{r['CitationCount']}x|{r['Tier']}] {r['CleanRef'][:140]}")

# ── MERGE: keep highest-citation row per cluster, sum counts ─────────────────
rows_to_drop = set()
merge_log = []

for root, members in dup_clusters.items():
    group = tiers.iloc[members].copy()
    # pick canonical: highest citation count; tie-break: longest ref string (more complete)
    group['_len'] = group['CleanRef'].str.len()
    canonical_idx = group.sort_values(['CitationCount','_len'], ascending=False).index[0]
    drop_idxs = [i for i in group.index if i != canonical_idx]

    # sum citation counts into canonical
    total_cites = group['CitationCount'].sum()
    total_years = group['UniqueYears'].max()
    merged_cats = ', '.join(sorted(set(
        c.strip() for cats in group['Categories'].dropna() for c in cats.split(',')
    )))
    merged_bp = ', '.join(sorted(set(
        c.strip() for cats in group['BlueprintCategories'].dropna() for c in str(cats).split(',')
    )))

    tiers.at[canonical_idx, 'CitationCount'] = total_cites
    tiers.at[canonical_idx, 'UniqueYears'] = total_years
    tiers.at[canonical_idx, 'Categories'] = merged_cats if merged_cats else None
    tiers['BlueprintCategories'] = tiers['BlueprintCategories'].astype(object)
    tiers.at[canonical_idx, 'BlueprintCategories'] = merged_bp if merged_bp.strip() else None

    rows_to_drop.update(drop_idxs)
    merge_log.append({
        'canonical': tiers.at[canonical_idx, 'CleanRef'][:120],
        'merged_count': total_cites,
        'dropped': len(drop_idxs)
    })

tiers_dedup = tiers.drop(index=list(rows_to_drop)).reset_index(drop=True)
print(f"\nRows after dedup: {len(tiers_dedup)}  (removed {len(rows_to_drop)})")

# ── RE-APPLY TIER LOGIC after merging counts ────────────────────────────────
def assign_tier(row):
    count = row['CitationCount']
    years = row['UniqueYears']
    src = row['SourceType']
    if count >= 3 and years >= 3:
        return 'Must-Read'
    if count >= 2 and years >= 2 and src == 'Guideline/Org':
        return 'Must-Read'
    if count >= 3 and src in ('Guideline/Org','NEJM','JAMA','Annals','Lancet'):
        return 'Must-Read'
    if count >= 2:
        return 'Core'
    if count == 1 and src in ('Guideline/Org','NEJM','JAMA','Annals','Lancet','Circulation'):
        return 'Core'
    return 'Supplementary'

tiers_dedup['Tier'] = tiers_dedup.apply(assign_tier, axis=1)
print("\nTier counts after dedup + re-tier:")
print(tiers_dedup['Tier'].value_counts())

# ── ISSUE 2: Encoding corruption (replacement chars) ─────────────────────────
encoding_issues = tiers_dedup[tiers_dedup['CleanRef'].str.contains(r'[â€œâ€™Ã\ufffd\u00e2\u0093\u0080\u009c]|\\?\\?\\?', regex=True, na=False)]
print(f"\nEncoding-corrupted refs: {len(encoding_issues)}")
for _, r in encoding_issues.head(10).iterrows():
    print(f"  {r['CleanRef'][:150]}")

# ── ISSUE 3: Truncated refs (end mid-sentence, no year/journal) ──────────────
truncated = tiers_dedup[~tiers_dedup['CleanRef'].str.contains(r'\d{4}', na=False)]
print(f"\nRefs with no 4-digit year (possibly truncated): {len(truncated)}")
for _, r in truncated.head(10).iterrows():
    print(f"  [{r['Tier']}] {r['CleanRef'][:150]}")

# ── ISSUE 4: Orphaned stray numbers / fragments ───────────────────────────────
fragments = tiers_dedup[tiers_dedup['CleanRef'].str.strip().str.len() < 30]
print(f"\nVery short refs (<30 chars, likely fragments): {len(fragments)}")
for _, r in fragments.iterrows():
    print(f"  [{r['Tier']}] '{r['CleanRef']}'")

# ── ISSUE 5: Misclassified SourceType (re-check after dedup) ─────────────────
print(f"\nSource type breakdown (post-dedup):")
print(tiers_dedup['SourceType'].value_counts())

# check 'Other Journal' entries that might be guidelines
other_j = tiers_dedup[tiers_dedup['SourceType']=='Other Journal']
guideline_keywords = ['guideline','recommendation','task force','statement','consensus','uspstf','acip','cdc','nih ']
missed_guidelines = other_j[other_j['CleanRef'].str.lower().str.contains('|'.join(guideline_keywords), na=False)]
print(f"\nPotential guidelines miscategorized as 'Other Journal': {len(missed_guidelines)}")
for _, r in missed_guidelines.head(10).iterrows():
    print(f"  {r['CleanRef'][:150]}")

# ── ISSUE 6: Blank/null Categories ───────────────────────────────────────────
no_cats = tiers_dedup[tiers_dedup['Categories'].isna() | (tiers_dedup['Categories'].str.strip() == '')]
print(f"\nRefs with missing Categories: {len(no_cats)}")

# ── ISSUE 7: Duplicate question-level ref assignment (questions citing same ref multiple times) ──
# Check original refs_df
print("\n--- Cross-checking: questions that cited same ref more than once ---")
# (done at refs_df level - load original data to check)
df_orig = pd.read_csv(r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\ite_exam\03_database\ABFM_ITE_6_Year_Master.csv', low_memory=False)

import re as re2
def extract_refs(explanation):
    if pd.isna(explanation): return []
    match = re2.search(r'Ref:\s*(.+)', explanation, re2.DOTALL)
    if not match: return []
    ref_block = match.group(1).strip()
    parts = re2.split(r'\s+\d+\)\s+', ref_block)
    return [p.strip() for p in parts if p.strip()]

df_orig['ParsedRefs'] = df_orig['Explanation'].apply(extract_refs)
multi_same = df_orig[df_orig['ParsedRefs'].apply(lambda x: len(x) != len(set(x)))]
print(f"Questions citing same ref twice within one question: {len(multi_same)}")

# Save cleaned file
out_path = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\ite_refs\02_working\ITE_Reference_Tiers_Clean.csv'
tiers_dedup.to_csv(out_path, index=False)
print(f"\nSaved cleaned file: {out_path}")
print(f"Final row count: {len(tiers_dedup)}")
