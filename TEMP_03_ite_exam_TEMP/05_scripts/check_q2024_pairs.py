import pandas as pd, sys
sys.stdout.reconfigure(encoding='utf-8')

PAIRS = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\ite_refs\02_working\question_ref_pairs.csv'
MASTER = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\ite_exam\03_database\ABFM_ITE_Master_v2.xlsx'

# Load master null Q2024
df = pd.read_excel(MASTER, dtype=str)
null_ref = df['Reference'].isna() | (df['Reference'].str.strip() == '') | (df['Reference'] == 'nan')
null_q24 = set(df[(df['ExamYear']=='2024') & null_ref]['QuestionID'].tolist())
print(f"Null Q2024 in master: {len(null_q24)}")

# Load pairs CSV  
pairs = pd.read_csv(PAIRS, dtype=str)
print(f"\nPairs CSV columns: {pairs.columns.tolist()}")
print(f"Pairs CSV rows: {len(pairs)}")

# Filter for Q2024 null IDs
q24_pairs = pairs[pairs['QuestionID'].isin(null_q24)]
print(f"\nQ2024 null IDs found in pairs CSV: {q24_pairs['QuestionID'].nunique()}")
if len(q24_pairs):
    print("\nSample:")
    print(q24_pairs.head(5).to_string())
