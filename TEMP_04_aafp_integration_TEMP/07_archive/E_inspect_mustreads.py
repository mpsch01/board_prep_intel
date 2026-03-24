import csv, json

REFS_CSV = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\ite_refs\03_database\ITE_Reference_Tiers_Final.csv'
KW_LIB   = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\keyword_library\session_keyword_library.json'

with open(REFS_CSV, encoding='utf-8') as f:
    refs = list(csv.DictReader(f))
with open(KW_LIB, encoding='utf-8') as f:
    lib = json.load(f)

must_reads = [r for r in refs if r['Tier'] == 'Must-Read']
print(f'Total must-read refs: {len(must_reads)}')
print()

import re
STOPWORDS = set("a about also am an and any are as at be been but by can could did do does each even for from get had have he her him his how if in into is it its just know let may more most much need no not of on one only or other our out per should so some that the their them then there these they this those though time to too two up us was way we well were what when where which who will with would year".split())

def tokenize(text):
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    return set(t for t in text.split() if t not in STOPWORDS and len(t) > 2)

def all_tokens(text):
    toks = list(tokenize(text))
    bigrams = {f'{toks[i]} {toks[i+1]}' for i in range(len(toks)-1)}
    return tokenize(text) | bigrams

for r in must_reads:
    rtoks = all_tokens(r['CleanRef'])
    # Score against all sessions
    best_sessions = []
    for snum, entry in lib.items():
        kw = {kw['term'].lower(): kw['composite'] for kw in entry['keywords'] if kw['composite'] >= 0.15}
        matched = [t for t in rtoks if t in kw]
        score = sum(kw[t] for t in matched)
        if score > 0:
            best_sessions.append((score, len(matched), snum, matched))
    best_sessions.sort(reverse=True)
    print(f"Ref: {r['CleanRef'][:80]}")
    print(f"  Cat: {r['Categories']}")
    if best_sessions:
        for sc, nm, snum, matched in best_sessions[:3]:
            print(f"  -> s{snum} score={sc:.3f} matches={nm} terms={matched[:4]}")
    else:
        print(f"  -> NO MATCHES")
    print()
