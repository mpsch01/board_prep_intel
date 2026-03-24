import pandas as pd, re

df = pd.read_csv(r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\ite_refs\03_database\ITE_Reference_Tiers_Final.csv')

# Check which original Must-Read refs are present
original_must_reads = [
    "Lung Cancer",
    "Abdominal Aortic Aneurysm",
    "Bright Futures",
    "Tuberculosis",
    "rhinosinusitis",
    "Hembree",
    "Higdon",
    "Influenza",
    "COPD",
    "spirometry",
    "hypertension using combination",
    "Croup",
    "decision-making capacity",
    "Incidentalomas",
    "Thyroid nodules",
    "Adhesive capsulitis",
    "Hand-foot",
    "PTSD",
    "Peripheral nerve",
    "bronchiolitis",
    "diverticulitis",
]

print("=== ORIGINAL 21 MUST-READ CHECK ===")
for term in original_must_reads:
    matches = df[df['CleanRef'].str.contains(term, case=False, na=False)]
    if len(matches) == 0:
        print(f"  !! MISSING: '{term}'")
    else:
        for _, r in matches[matches['Tier']=='Must-Read'].iterrows():
            print(f"  OK [{r['CitationCount']}x] {r['CleanRef'][:100]}")
        non_mr = matches[matches['Tier']!='Must-Read']
        if len(non_mr) > 0 and not matches['Tier'].eq('Must-Read').any():
            for _, r in non_mr.iterrows():
                print(f"  TIER-DROPPED [{r['Tier']}|{r['CitationCount']}x] {r['CleanRef'][:100]}")

# Check the AAA ref specifically - 7x seems inflated
print("\n=== AAA REF ===")
aaa = df[df['CleanRef'].str.contains('Aortic Aneurysm', case=False, na=False)]
for _, r in aaa.iterrows():
    print(f"  [{r['Tier']}|{r['CitationCount']}x|{r['UniqueYears']}yr] {r['CleanRef'][:130]}")

# Check lung cancer screening
print("\n=== LUNG CANCER SCREENING REF ===")
lc = df[df['CleanRef'].str.contains('Lung Cancer.*Screening|Cancer.*Lung', case=False, na=False)]
for _, r in lc.iterrows():
    print(f"  [{r['Tier']}|{r['CitationCount']}x|{r['UniqueYears']}yr] {r['CleanRef'][:130]}")
