import pandas as pd, sys
sys.stdout.reconfigure(encoding='utf-8')

STUDY_GUIDE = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\ite_exam\02_working\high yield categories_table.xlsx'

VOL_FLOOR_Q     = 4
VOL_FLOOR_SCORE = 0.65

sg = pd.read_excel(STUDY_GUIDE, sheet_name='HighYield_Study_Guide')

def tier(s):
    if s >= 1.0: return 'Tier 1'
    if s >= 0.5: return 'Tier 2'
    return 'Standard'

sg['Tier_orig']    = sg['Yield_Score'].apply(tier)
sg['Yield_Score_v2'] = sg['Yield_Score'].copy()

mask = (sg['Total_Questions_6yr'] >= VOL_FLOOR_Q) & (sg['Yield_Score'] < VOL_FLOOR_SCORE)
sg.loc[mask, 'Yield_Score_v2'] = VOL_FLOOR_SCORE

sg['Tier_v2']     = sg['Yield_Score_v2'].apply(tier)
sg['Tier_change'] = sg.apply(
    lambda r: f"*** {r.Tier_orig} -> {r.Tier_v2}" if r.Tier_orig != r.Tier_v2 else '', axis=1)

cols = ['Subcategory','Total_Questions_6yr','Trend_Slope',
        'Yield_Score','Yield_Score_v2','Tier_orig','Tier_v2','Tier_change']

print('=== SUBCATEGORIES AFFECTED BY VOLUME FLOOR ===')
floored = sg[mask].sort_values('Total_Questions_6yr', ascending=False)
print(floored[cols].to_string())

print('\n=== TIER CHANGES SUMMARY ===')
changed = sg[sg['Tier_change'] != ''][cols]
print(changed.to_string())

print('\n=== TIER DISTRIBUTION ===')
for t in ['Tier 1','Tier 2','Standard']:
    orig = (sg['Tier_orig'] == t).sum()
    new  = (sg['Tier_v2']   == t).sum()
    print(f'  {t:10s}: {orig:3d} -> {new:3d}  ({"+" if new>=orig else ""}{new-orig:+d})')

print(f'\n  Volume floor applied to {mask.sum()} subcategories (>={VOL_FLOOR_Q} Qs, score <{VOL_FLOOR_SCORE})')

sg.to_csv(
    r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\07_archive\study_guide_v2_scores.csv',
    index=False, encoding='utf-8')
print('\nSaved: study_guide_v2_scores.csv')
