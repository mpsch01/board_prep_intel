import pandas as pd, numpy as np, sys
sys.stdout.reconfigure(encoding='utf-8')
sg = pd.read_excel(r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\ite_exam\02_working\high yield categories_table.xlsx', sheet_name='HighYield_Study_Guide')

# Understand the existing Yield_Score formula by reverse-engineering it
# Normalize volume and slope independently and see how they correlate to Yield_Score
vol  = sg['Total_Questions_6yr']
slp  = sg['Trend_Slope']
ys   = sg['Yield_Score']

vol_norm = (vol - vol.min()) / (vol.max() - vol.min())
slp_norm = (slp - slp.min()) / (slp.max() - slp.min())

# Try various weightings and see which best reconstructs Yield_Score
from itertools import product
best_r2, best_w = 0, (0,0)
for vw in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
    tw = 1.0 - vw
    recon = vw * vol_norm + tw * slp_norm
    corr  = np.corrcoef(recon, ys)[0,1]**2
    if corr > best_r2:
        best_r2, best_w = corr, (vw, tw)

print(f'Best reconstruction: volume={best_w[0]:.1f} / trend={best_w[1]:.1f}  R²={best_r2:.4f}')
print()

# Show what a 50/50 rebalance looks like for top subcats by volume
sg['vol_norm'] = vol_norm
sg['slp_norm'] = slp_norm
sg['yield_50_50'] = (0.5 * vol_norm + 0.5 * slp_norm).round(4)

# Scale to match existing Yield_Score range roughly (0 to 1.6)
ys_min, ys_max = ys.min(), ys.max()
new_min = sg['yield_50_50'].min()
new_max = sg['yield_50_50'].max()
sg['yield_50_50_scaled'] = ((sg['yield_50_50'] - new_min) / (new_max - new_min) * (ys_max - ys_min) + ys_min).round(4)

cols = ['Subcategory','Total_Questions_6yr','Trend_Slope','Yield_Score','yield_50_50_scaled']
print('--- Top 30 by volume: original vs 50/50 score ---')
print(sg[cols].sort_values('Total_Questions_6yr', ascending=False).head(30).to_string())
print()
print('--- Tier boundary cases (original score 0.8-1.2) ---')
border = sg[(sg['Yield_Score'] >= 0.8) & (sg['Yield_Score'] <= 1.2)]
print(border[cols].sort_values('Yield_Score').to_string())
