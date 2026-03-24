import pandas as pd, sys
sys.stdout.reconfigure(encoding='utf-8')
df = pd.read_excel(r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\ite_exam\03_database\ABFM_ITE_Master_v2.xlsx', dtype=str)
null_ref = df['Reference'].isna() | (df['Reference'].str.strip() == '') | (df['Reference'] == 'nan')
print('Null refs by year:')
for yr in ['2020','2021','2022','2023','2024','2025']:
    mask = (df['ExamYear'] == yr) & null_ref
    total = (df['ExamYear'] == yr).sum()
    print(f'  {yr}: {mask.sum()}/{total} null ({mask.sum()/total*100:.1f}%)')
print(f'\nTotal null: {null_ref.sum()}/1200')
nulls_2024 = df[(df['ExamYear']=='2024') & null_ref]['QuestionID'].tolist()
print(f'\n2024 null QIDs ({len(nulls_2024)}):')
print(nulls_2024[:20], '...' if len(nulls_2024) > 20 else '')
