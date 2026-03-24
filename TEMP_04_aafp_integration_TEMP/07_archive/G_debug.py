import csv
PAIRS  = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\ite_refs\02_working\question_ref_pairs.csv'
ENRICH = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\ite_exam\03_database\ABFM_ITE_Enriched.csv'

pairs_by_year = {}
with open(PAIRS, newline='', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        yr = row['ExamYear']
        qid = row['QuestionID']
        if yr not in pairs_by_year:
            pairs_by_year[yr] = set()
        pairs_by_year[yr].add(qid)

enrich_by_year = {}
with open(ENRICH, newline='', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        yr = row['ExamYear']
        qid = row['Question ID']
        if yr not in enrich_by_year:
            enrich_by_year[yr] = set()
        enrich_by_year[yr].add(qid)

print('Year | Pairs sample QIDs              | Enriched sample QIDs')
for yr in sorted(enrich_by_year.keys()):
    ps = sorted(pairs_by_year.get(yr, set()))[:3]
    es = sorted(enrich_by_year.get(yr, set()))[:3]
    ov = len(pairs_by_year.get(yr,set()) & enrich_by_year.get(yr,set()))
    print(f'{yr}: pairs={ps} | enriched={es} | overlap={ov}')
