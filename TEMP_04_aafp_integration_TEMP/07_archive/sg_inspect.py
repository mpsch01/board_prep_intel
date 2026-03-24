import pandas as pd, sys
sys.stdout.reconfigure(encoding='utf-8')
sg = pd.read_excel(r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\ite_exam\02_working\high yield categories_table.xlsx', sheet_name='HighYield_Study_Guide')
print('COLUMNS:', sg.columns.tolist())
print()
cols = ['Subcategory','Total_Questions_6yr','Avg_Per_Exam','Trend_Slope','Yield_Score']
print(sg[cols].sort_values('Total_Questions_6yr', ascending=False).head(30).to_string())
print()
print('--- Yield_Score stats ---')
print(sg['Yield_Score'].describe())
print()
print('--- Total_Questions_6yr stats ---')
print(sg['Total_Questions_6yr'].describe())
