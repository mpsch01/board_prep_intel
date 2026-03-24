import pandas as pd
df = pd.read_csv(r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\ite_refs\03_database\ITE_Reference_Tiers_Final.csv')

mr = df[df['Tier']=='Must-Read'].sort_values('CitationCount', ascending=False)
print(f"Must-Read count: {len(mr)}")
for _, r in mr.iterrows():
    print(f"  [{r['CitationCount']}x|{r['UniqueYears']}yr|{r['SourceType']}] {r['CleanRef'][:130]}")

print()
harr = df[df['CleanRef'].str.contains('Harrison', na=False)]
print(f"Harrison rows restored: {len(harr)}")
for _, r in harr.iterrows():
    print(f"  [{r['Tier']}|{r['CitationCount']}x] {r['CleanRef'][:130]}")

print()
print("Source type breakdown:")
print(df['SourceType'].value_counts().to_string())
print()
print("Tier breakdown:")
print(df['Tier'].value_counts().to_string())

# Check for any new issues - Other Journal with AFP articles
other_j_afp = df[(df['SourceType']=='Other Journal') & df['CleanRef'].str.lower().str.contains('am fam physician', na=False)]
print(f"\nAFP still in Other Journal: {len(other_j_afp)}")
for _, r in other_j_afp.iterrows():
    print(f"  {r['CleanRef'][:120]}")
