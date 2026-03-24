"""
Pass-2 database hygiene audit on ITE_Reference_Tiers_Clean.csv
Checks: encoding, fragments, year-less refs, false-cluster merges (textbooks),
        miscategorized source types, tier-upgrade candidates, stale guideline years,
        category tag consistency, and USPSTF ref format fragmentation.
"""
import pandas as pd, re

df = pd.read_csv(r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\ite_refs\02_working\ITE_Reference_Tiers_Clean.csv')
print(f"=== PASS-2 HYGIENE AUDIT  ({len(df)} rows) ===\n")

issues = []  # collect (issue_type, idx, detail)

# ── 1. ENCODING CORRUPTION ────────────────────────────────────────────────────
# The regex was over-broad before — look for specific Windows-1252 artefacts only
bad_chars = re.compile(r'[\ufffd\x80-\x9f]|â€|Ã¢|Ã©|\?\?\?')
enc_mask = df['CleanRef'].str.contains(bad_chars, regex=True, na=False)
print(f"[1] Encoding-corrupted refs: {enc_mask.sum()}")
for _, r in df[enc_mask].iterrows():
    print(f"    {r['CleanRef'][:140]}")
    issues.append(('Encoding', r.name, r['CleanRef'][:100]))

# ── 2. FRAGMENT / STUB REFS ───────────────────────────────────────────────────
frag_mask = df['CleanRef'].str.strip().str.len() < 35
print(f"\n[2] Stub refs (<35 chars): {frag_mask.sum()}")
for _, r in df[frag_mask].iterrows():
    print(f"    [{r['Tier']}] '{r['CleanRef']}'")
    issues.append(('Fragment', r.name, r['CleanRef']))

# ── 3. NO 4-DIGIT YEAR ────────────────────────────────────────────────────────
no_year = ~df['CleanRef'].str.contains(r'\d{4}', regex=True, na=False)
print(f"\n[3] Refs with no 4-digit year: {no_year.sum()}")
for _, r in df[no_year].iterrows():
    print(f"    [{r['Tier']}] {r['CleanRef'][:140]}")
    issues.append(('NoYear', r.name, r['CleanRef'][:100]))

# ── 4. TEXTBOOKS MERGED AS IF SAME WORK (false cluster survivors) ─────────────
# Textbook refs with different page numbers SHOULD stay separate — the dedup
# may have incorrectly collapsed them if the leading ~130 chars matched.
# Flag any textbook ref that has CitationCount > 1 so we can inspect.
textbook_kws = ['principles of internal medicine', 'goldman-cecil', 'nelson textbook',
                'braunwald', "habif", 'fracture management', "rosen's emergency",
                'sabiston', 'clinical dermatology', 'diagnostic and statistical manual']
tb_mask = df['CleanRef'].str.lower().str.contains('|'.join(textbook_kws), na=False)
tb_multi = df[tb_mask & (df['CitationCount'] > 1)]
print(f"\n[4] Textbook refs incorrectly merged (CitationCount > 1): {len(tb_multi)}")
for _, r in tb_multi.iterrows():
    print(f"    [{r['CitationCount']}x | {r['Tier']}] {r['CleanRef'][:160]}")
    issues.append(('TextbookFalseMerge', r.name, r['CleanRef'][:100]))

# ── 5. MISCATEGORIZED SOURCE TYPES ───────────────────────────────────────────
# Re-scan Other Journal for missed guidelines/org docs
other_j = df[df['SourceType'] == 'Other Journal']
guideline_kws = r'guideline|recommendation|task force|statement|consensus|uspstf|acip|cdc |nih |mmwr|advisory committee|practice parameter'
missed_gl = other_j[other_j['CleanRef'].str.lower().str.contains(guideline_kws, regex=True, na=False)]
print(f"\n[5a] 'Other Journal' refs that look like guidelines: {len(missed_gl)}")
for _, r in missed_gl.iterrows():
    print(f"     {r['CleanRef'][:160]}")
    issues.append(('MisclassifiedGuideline', r.name, r['CleanRef'][:100]))

# AFP articles hiding in Other Journal
afp_in_other = other_j[other_j['CleanRef'].str.lower().str.contains('am fam physician', na=False)]
print(f"\n[5b] AFP articles still in 'Other Journal': {len(afp_in_other)}")
for _, r in afp_in_other.iterrows():
    print(f"     {r['CleanRef'][:160]}")
    issues.append(('AFPMisclassified', r.name, r['CleanRef'][:100]))

# ── 6. TIER UPGRADE CANDIDATES ────────────────────────────────────────────────
# After dedup & merging, some refs now have higher counts but weren't re-tiered
# (the script did re-tier, but let's verify no Supplementary has count >= 2)
supp_high = df[(df['Tier'] == 'Supplementary') & (df['CitationCount'] >= 2)]
print(f"\n[6] Supplementary refs with CitationCount >= 2 (missed tier upgrade): {len(supp_high)}")
for _, r in supp_high.iterrows():
    print(f"    [{r['CitationCount']}x] {r['CleanRef'][:140]}")
    issues.append(('MissedTierUpgrade', r.name, r['CleanRef'][:100]))

# ── 7. STALE / SUPERSEDED GUIDELINE YEARS ─────────────────────────────────────
# Flag high-value guidelines that are pre-2018 and still in Core/Must-Read
old_guideline = df[
    (df['SourceType'] == 'Guideline/Org') &
    (df['Tier'].isin(['Must-Read', 'Core'])) &
    (df['CleanRef'].str.extract(r'(\d{4})')[0].astype(float, errors='ignore') < 2018)
]
print(f"\n[7] Core/Must-Read guidelines from before 2018 (check if superseded): {len(old_guideline)}")
for _, r in old_guideline.iterrows():
    yr_match = re.search(r'(\d{4})', r['CleanRef'])
    yr = yr_match.group(1) if yr_match else '?'
    print(f"    [{yr} | {r['Tier']}] {r['CleanRef'][:160]}")
    issues.append(('StaleGuideline', r.name, r['CleanRef'][:100]))

# ── 8. USPSTF FRAGMENTED FORMAT (two citation styles mixed) ──────────────────
uspstf = df[df['CleanRef'].str.lower().str.contains('preventive services task force|uspstf', na=False)]
print(f"\n[8] USPSTF refs total: {len(uspstf)} — checking format consistency")
fmt_a = uspstf[uspstf['CleanRef'].str.contains('Final Recommendation Statement:', na=False)]
fmt_b = uspstf[uspstf['CleanRef'].str.contains('US Preventive Services Task Force', na=False) &
               ~uspstf['CleanRef'].str.contains('Final Recommendation Statement:', na=False)]
print(f"    Format A ('Final Recommendation Statement: Topic'): {len(fmt_a)}")
print(f"    Format B ('US Preventive Services Task Force. topic...'): {len(fmt_b)}")
if len(fmt_b) > 0:
    print("    Format B entries:")
    for _, r in fmt_b.iterrows():
        print(f"      [{r['Tier']}] {r['CleanRef'][:160]}")
        issues.append(('USPSTFFormatMismatch', r.name, r['CleanRef'][:100]))

# ── 9. DUPLICATE ARTICLE TITLES ACROSS DIFFERENT YEARS (updated guidelines) ──
# Same lead author + same journal + very similar title but different year
# Signals ABFM updated to a newer version mid-dataset
from difflib import SequenceMatcher
title_re = re.compile(r':\s*(.+?)\.\s*(?:Am Fam|N Engl|JAMA|Ann Intern|Lancet|BMJ)', re.IGNORECASE)
df['_title'] = df['CleanRef'].apply(lambda x: m.group(1).lower().strip() if (m := title_re.search(x)) else '')
df['_year'] = df['CleanRef'].str.extract(r';(\d{4})')[0]

# find pairs with same author last name + very similar title but different year
updated_pairs = []
for i, r1 in df[df['_title'] != ''].iterrows():
    for j, r2 in df[(df.index > i) & (df['_title'] != '')].iterrows():
        if r1['_year'] != r2['_year'] and r1['_year'] is not None and r2['_year'] is not None:
            sim = SequenceMatcher(None, r1['_title'], r2['_title']).ratio()
            if sim > 0.85:
                updated_pairs.append((i, j, sim, r1['CleanRef'][:100], r2['CleanRef'][:100], r1['_year'], r2['_year']))

print(f"\n[9] Likely updated article pairs (same title, different year): {len(updated_pairs)}")
for p in updated_pairs[:15]:
    print(f"    sim={p[2]:.2f}  [{p[5]}] {p[3]}")
    print(f"              [{p[6]}] {p[4]}")

# ── 10. MISSING BLUEPRINT CATEGORY ───────────────────────────────────────────
no_bp = df[df['BlueprintCategories'].isna() | (df['BlueprintCategories'].astype(str).str.strip().isin(['', 'nan']))]
print(f"\n[10] Refs with no BlueprintCategory: {len(no_bp)}")
print(f"     Tier breakdown: {no_bp['Tier'].value_counts().to_dict()}")
print(f"     (Supplementary missing BP is expected; flag Core/Must-Read only)")
no_bp_important = no_bp[no_bp['Tier'].isin(['Must-Read', 'Core'])]
print(f"     Core/Must-Read missing BP: {len(no_bp_important)}")

# ── 11. CATEGORY TAG CONSISTENCY ─────────────────────────────────────────────
# List all unique category values and flag any that look like typos or variants
all_cats = set()
for cats in df['Categories'].dropna():
    for c in str(cats).split(','):
        all_cats.add(c.strip())
print(f"\n[11] Unique Category values ({len(all_cats)} total):")
for c in sorted(all_cats):
    count = df['Categories'].str.contains(re.escape(c), na=False).sum()
    print(f"     '{c}': {count} refs")

# ── SUMMARY ───────────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print(f"HYGIENE ISSUE SUMMARY")
print(f"{'='*60}")
by_type = {}
for issue_type, idx, detail in issues:
    by_type[issue_type] = by_type.get(issue_type, 0) + 1
for k, v in sorted(by_type.items(), key=lambda x: -x[1]):
    print(f"  {k}: {v}")
print(f"\nTotal flagged items: {len(issues)}")
print(f"Clean rows: {len(df)}")

# Save issues log
issues_df = pd.DataFrame(issues, columns=['IssueType','RowIndex','RefSnippet'])
issues_df.to_csv(r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\ite_exam\02_working\hygiene_issues_log.csv', index=False)
print(f"\nIssues log saved: hygiene_issues_log.csv")
