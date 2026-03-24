import pandas as pd, sys
sys.stdout.reconfigure(encoding='utf-8')
df = pd.read_csv(r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\02_working\poll_questions_raw.csv')

# Fully intact = has all 4 choices
df['complete'] = (df['choice_A'].notna() & df['choice_B'].notna() &
                  df['choice_C'].notna() & df['choice_D'].notna())
print(f'Fully intact (A+B+C+D): {df.complete.sum()} / {len(df)}')
print(f'Missing only D:         {((df.choice_A.notna()) & (df.choice_B.notna()) & (df.choice_C.notna()) & (df.choice_D.isna())).sum()}')
print(f'Missing A or B:         {(df.choice_A.isna() | df.choice_B.isna()).sum()}')
print()

# Show a few incomplete ones to understand pattern
incomplete = df[~df.complete].head(4)
for _, r in incomplete.iterrows():
    print(f'=== Session {r.session_number} Q{r.question_num} p{r.page_num} ===')
    print(f'STEM: {str(r.stem)[:200]}')
    print(f'  A: {r.choice_A}  |  B: {r.choice_B}  |  C: {r.choice_C}  |  D: {r.choice_D}')
    print()
