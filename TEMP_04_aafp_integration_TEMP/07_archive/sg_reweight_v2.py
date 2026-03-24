import pandas as pd, numpy as np, sys
sys.stdout.reconfigure(encoding='utf-8')

STUDY_GUIDE = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\ite_exam\02_working\high yield categories_table.xlsx'
RAW_DIR     = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\07_archive'

VOL_WEIGHT  = 0.50
TREND_WEIGHT= 0.50
VOL_FLOOR_Q = 4      # >= this many questions triggers floor
VOL_FLOOR_SCORE = 0.65  # minimum score for high-volume subcats

sg = pd.read_excel(STUDY_GUIDE, sheet_name='HighYield_Study_Guide')

vol = sg['Total_Questions_6yr']
slp = sg['Trend_Slope']
ys  = sg['Yield_Score']

# Normalize both axes to 0-1
vol_norm = (vol - vol.min()) / (vol.max() - vol.min())
slp_norm = (slp - slp.min()) / (slp.max() - slp.min())

# 50/50 blend
blended = (VOL_WEIGHT * vol_norm + TREND_WEIGHT * slp_norm)

# Scale to match original Yield_Score range (preserves interpretability)
ys_min, ys_max = ys.min(), ys.max()
b_min, b_max   = blended.min(), blended.max()
scaled = ((blended - b_min) / (b_max - b_min) * (ys_max - ys_min) + ys_min)

# Apply volume floor: >= 4 questions -> minimum 0.65
sg['Yield_Score_v2'] = scaled.round(4)
mask = sg['Total_Questions_6yr'] >= VOL_FLOOR_Q
sg.loc[mask, 'Yield_Score_v2'] = sg.loc[mask, 'Yield_Score_v2'].clip(lower=VOL_FLOOR_SCORE)
sg['Yield_Score_v2'] = sg['Yield_Score_v2'].round(4)

# Tier assignment
def tier(s):
    if s >= 1.0: return 'Tier 1'
    if s >= 0.5: return 'Tier 2'
    return 'Standard'

sg['Tier_orig'] = sg['Yield_Score'].apply(tier)
sg['Tier_v2']   = sg['Yield_Score_v2'].apply(tier)
sg['Tier_change'] = sg.apply(lambda r: '*** ' + r.Tier_orig + ' -> ' + r.Tier_v2
                              if r.Tier_orig != r.Tier_v2 else '', axis=1)

# ── Print comparison ──────────────────────────────────────────────────
cols = ['Subcategory','Total_Questions_6yr','Trend_Slope',
        'Yield_Score','Yield_Score_v2','Tier_orig','Tier_v2','Tier_change']

print('=== TOP 30 BY VOLUME: ORIGINAL vs V2 SCORE ===')
print(sg[cols].sort_values('Total_Questions_6yr', ascending=False).head(30).to_string())

print('\n=== TIER CHANGES ===')
changed = sg[sg['Tier_change'] != ''][cols].sort_values('Yield_Score', ascending=False)
if len(changed):
    print(changed.to_string())
else:
    print('No tier changes.')

print('\n=== TIER DISTRIBUTION (V2) ===')
for t in ['Tier 1','Tier 2','Standard']:
    n = (sg['Tier_v2'] == t).sum()
    print(f'  {t:10s}: {n:3d} subcategories')

print(f'\n  Volume floor applied to: {mask.sum()} subcategories (>= {VOL_FLOOR_Q} questions)')

# Save updated study guide data for use in downstream scripts
sg.to_csv(r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\07_archive\study_guide_v2_scores.csv',
          index=False, encoding='utf-8')
print('\nSaved: study_guide_v2_scores.csv')
