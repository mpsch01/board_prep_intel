import pandas as pd, sys
sys.stdout.reconfigure(encoding='utf-8')
df = pd.read_csv(r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\ite_exam\03_database\ABFM_ITE_Enriched.csv')
print('Columns:', list(df.columns))
print('Shape:', df.shape)
print(df[['qid','year','correct_answer','explanation','reference']].head(3).to_string())
