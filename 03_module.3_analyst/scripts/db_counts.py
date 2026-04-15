import sqlite3
from pathlib import Path
db = sqlite3.connect(str(Path(__file__).resolve().parent.parent.parent / "00_database" / "db" / "ite_intelligence.db"))
for t in ['articles','questions','aafp_questions','qid_art_xref','aafp_qid_art_xref','article_icd10','question_icd10','aafp_question_icd10','clinical_pathways','pubmed_pmid_cache','article_icd10_vec','question_icd10_vec','icd10_vec','article_currency','question_concepttag_vec','intersection_centroid_vec','question_full_vec','aafp_question_full_vec']:
    try: print(f"{t}: {db.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]}")
    except Exception as e: print(f"{t}: ERROR - {e}")
db.close()
